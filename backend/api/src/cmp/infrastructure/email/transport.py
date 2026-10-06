"""Where an email actually goes.

One protocol, three implementations, chosen by configuration. The point of the
seam is that everything above it — the templates, the tasks, the retry policy —
is written once and does not change when the transport does.

Whatever a deployment plugs in here must keep four properties, and they are
properties of the *transport*, not of the caller:

* **An explicit timeout.** Never infinite. A hung SMTP connection holds a worker
  slot until somebody notices, and nobody notices.
* **No secret in the log.** The code being delivered is never logged — that is
  the entire point of storing it as a keyed hash — and the recipient is
  obscured. What is logged is that a delivery happened, to roughly whom.
* **Raise on failure.** The Celery task carries the retry policy. A transport
  that swallows an error and returns quietly turns a retryable outage into
  silent data loss.
* **Idempotence is not assumed.** `acks_late` means a task can be redelivered,
  so a transport must tolerate being asked to send the same message twice.
"""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from typing import Final, Protocol, runtime_checkable

from cmp.core.config import settings
from cmp.core.logging import get_logger

log = get_logger("cmp.infrastructure.email")


@runtime_checkable
class EmailTransport(Protocol):
    """The one method anything above this layer may call."""

    def send(self, *, to: str, subject: str, body: str) -> dict[str, object]:
        """Deliver, or raise.

        The return value is for the task's result backend and the audit log —
        it says what happened, not whether it worked. Failure is an exception.
        """
        ...


def obscure(contact: str) -> str:
    """Enough of a recipient to answer "did it go out", not enough to be a list.

    An access log that records full addresses is a contact database with extra
    steps, and it will be read by more people than the address book would be.
    """
    if "@" in contact:
        name, _, domain = contact.partition("@")
        head = name[:2] if len(name) > 2 else name[:1]
        return f"{head}***@{domain}"
    return f"***{contact[-3:]}" if len(contact) > 3 else "***"


class ConsoleEmailTransport:
    """Development. Writes to a local outbox file and logs the fact.

    This exists because one-time codes are deliberately absent from the logs,
    which makes the local sign-in loop impossible to complete without somewhere
    to read them. Same idea as running MailHog beside a dev stack, minus the
    container.

    Hard-gated on environment, twice: the guard runs before anything is
    formatted, so there is no code path where a production process assembles a
    plaintext file of verification codes and then decides not to write it.
    """

    def __init__(self, outbox_path: str | None = None) -> None:
        from pathlib import Path

        self._path = (
            Path(outbox_path) if outbox_path else Path(settings.upload_root).parent / "outbox.log"
        )

    def send(self, *, to: str, subject: str, body: str) -> dict[str, object]:
        if settings.is_production or settings.environment == "staging":
            # Not "return delivered": a transport that writes nothing and says
            # it did turns a misconfiguration into silent loss.
            raise RuntimeError("The console email transport does not deliver outside local/test")
        self._write(to=to, subject=subject, body=body)
        from cmp.infrastructure import devcodes

        devcodes.record(channel="email", to=to, text=f"{subject}\n{body}")
        log.info(
            "email.delivered",
            to=obscure(to),
            subject=subject,
            transport="console",
        )
        return {"channel": "email", "transport": "console", "delivered": True}

    def _write(self, *, to: str, subject: str, body: str) -> None:
        try:
            from datetime import UTC, datetime

            self._path.parent.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(UTC).isoformat(timespec="seconds")
            entry = (
                f"\n{'=' * 78}\n"
                f"{stamp}  [email]  to: {to}\n"
                f"subject: {subject}\n{'-' * 78}\n{body}\n"
            )
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(entry)
        except OSError as exc:  # pragma: no cover — a convenience, never fatal
            log.warning("email.outbox_unavailable", error=str(exc))


class EmailRejected(RuntimeError):
    """The mail server refused for good: a wrong login, an address or a sender
    it will not take, a certificate that does not verify, a protocol it does
    not speak. Not an `OSError`, so no task retries it - the same request
    would be refused again. A passing failure - the server unreachable or
    busy, a 4xx - stays the `OSError` smtplib raised, and is retried."""


#: How the connection is protected; see SMTP_SECURITY.
SECURITY_MODES: Final = ("starttls", "ssl", "none")


class SmtpEmailTransport:
    """Production, via SMTP.

    Not wired by default: a deployment sets `EMAIL_TRANSPORT=smtp` and the SMTP
    settings, and `build_email_transport` returns this instead. Left explicit
    rather than auto-detected, because "it silently started emailing people" is
    not a surprise anybody wants.

    One connection per message, opened and closed here: a worker sends a
    message now and then, and a pooled connection a server dropped while it
    sat idle is a failure the next message would find. The three ways in:

    * `starttls` - connect in the clear (usually 587), upgrade with STARTTLS,
      then log in. A server that cannot upgrade is refused, never used plain.
    * `ssl` - encrypted from the first byte (usually 465).
    * `none` - plain, for an internal relay (usually 25). A login over it is
      sent in the clear, so it is for a relay on a trusted network only.

    Certificates are always verified - against the system's authorities and,
    if set, `SMTP_CA_FILE` for a relay an internal authority signed.
    """

    def __init__(
        self,
        host: str,
        port: int,
        *,
        username: str = "",
        password: str = "",
        security: str = "starttls",
        sender: str = "",
        sender_name: str = "",
        ca_file: str = "",
        timeout_s: float | None = None,
    ) -> None:
        if security not in SECURITY_MODES:
            raise ValueError(f"SMTP security must be one of {', '.join(SECURITY_MODES)}")
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._security = security
        self._sender = sender or settings.notification_email_from
        self._sender_name = sender_name
        self._ca_file = ca_file
        # Never infinite. A hung connection holds a worker slot indefinitely.
        self._timeout = timeout_s or settings.external_http_timeout_s

    # ---------------------------------------------------------------- message

    def compose(self, *, to: str, subject: str, body: str) -> EmailMessage:
        """The message as it goes out: plain text in UTF-8, a named sender, a
        date and an id, and marked automatic so an out-of-office reply is not
        sent back to an address nobody reads (RFC 3834)."""
        domain = self._sender.rpartition("@")[2] or "localhost"
        message = EmailMessage()
        message["From"] = (
            formataddr((self._sender_name, self._sender)) if self._sender_name else self._sender
        )
        message["To"] = to
        message["Subject"] = subject
        message["Date"] = formatdate(usegmt=True)
        message["Message-ID"] = make_msgid(domain=domain)
        message["Auto-Submitted"] = "auto-generated"
        message.set_content(body)
        return message

    # ------------------------------------------------------------- connection

    def _tls(self) -> ssl.SSLContext:
        context = ssl.create_default_context()
        if self._ca_file:
            context.load_verify_locations(cafile=self._ca_file)
        return context

    def _connect(self) -> smtplib.SMTP:
        if self._security == "ssl":
            return smtplib.SMTP_SSL(
                self._host, self._port, timeout=self._timeout, context=self._tls()
            )
        client = smtplib.SMTP(self._host, self._port, timeout=self._timeout)
        if self._security == "starttls":
            try:
                client.ehlo()
                client.starttls(context=self._tls())
                client.ehlo()
            except BaseException:
                client.close()
                raise
        return client

    # ------------------------------------------------------------------ send

    def send(self, *, to: str, subject: str, body: str) -> dict[str, object]:
        message = self.compose(to=to, subject=subject, body=body)
        where = {
            "to": obscure(to),
            "server": f"{self._host}:{self._port}",
            "security": self._security,
        }
        try:
            with self._connect() as client:
                if self._username:
                    client.login(self._username, self._password)
                refused = client.send_message(message)
        except smtplib.SMTPAuthenticationError as exc:
            log.error("email.rejected", reason="login refused", code=exc.smtp_code, **where)
            raise EmailRejected(
                f"The mail server refused the login for SMTP_USERNAME (code {exc.smtp_code})"
            ) from exc
        except smtplib.SMTPNotSupportedError as exc:
            # STARTTLS or AUTH not offered: a setting, not an outage.
            log.error("email.rejected", reason="not supported by the server", **where)
            raise EmailRejected(
                f"The mail server does not support what SMTP_SECURITY={self._security} "
                f"and the login need: {exc}"
            ) from exc
        except ssl.SSLCertVerificationError as exc:
            log.error("email.rejected", reason="certificate not trusted", **where)
            raise EmailRejected(
                "The mail server's certificate did not verify; set SMTP_CA_FILE to the "
                "authority that signed it"
            ) from exc
        except smtplib.SMTPRecipientsRefused as exc:
            codes = [code for code, _ in exc.recipients.values()]
            if all(code >= 500 for code in codes):
                log.error("email.rejected", reason="recipient refused", code=codes[0], **where)
                raise EmailRejected(
                    f"The mail server refused the recipient (code {codes[0]})"
                ) from exc
            log.warning("email.deferred", reason="recipient deferred", code=codes[0], **where)
            raise
        except smtplib.SMTPResponseException as exc:
            # Sender refused, data refused, anything with a reply code: 5xx is
            # the server's final word, 4xx is "try later".
            if exc.smtp_code >= 500:
                log.error("email.rejected", reason="refused", code=exc.smtp_code, **where)
                raise EmailRejected(
                    f"The mail server refused the message (code {exc.smtp_code})"
                ) from exc
            log.warning("email.deferred", reason="busy", code=exc.smtp_code, **where)
            raise
        except OSError as exc:
            # Unreachable, timed out, dropped: retried by the task.
            log.warning("email.unavailable", error=type(exc).__name__, **where)
            raise

        if refused:  # pragma: no cover - one recipient: refused raises above
            raise EmailRejected("The mail server refused the recipient")
        log.info(
            "email.delivered",
            to=obscure(to),
            subject=subject,
            transport="smtp",
            message_id=message["Message-ID"],
        )
        return {
            "channel": "email",
            "transport": "smtp",
            "delivered": True,
            "message_id": message["Message-ID"],
        }


class NullEmailTransport:
    """Accepts and discards. For tests that assert on behaviour, not delivery."""

    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    def send(self, *, to: str, subject: str, body: str) -> dict[str, object]:
        self.sent.append({"to": to, "subject": subject, "body": body})
        return {"channel": "email", "transport": "null", "delivered": True}


def smtp_security() -> str:
    """SMTP_SECURITY, or - unset - what SMTP_USE_TLS has always meant."""
    if settings.smtp_security:
        return settings.smtp_security
    return "starttls" if settings.smtp_use_tls else "none"


def sender_name() -> str:
    """The name beside the sender's address."""
    return settings.notification_email_from_name or f"{settings.organisation_name} Privacy Office"


def build_email_transport() -> EmailTransport:
    """Pick the transport this environment is configured for.

    Defaults to the console outbox. A deployment that wants real mail says so
    explicitly — defaulting to SMTP would mean a misconfigured staging box
    emailing real people the first time somebody signs in.
    """
    if settings.email_transport == "smtp":
        return SmtpEmailTransport(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            # Unwrapped at the last possible moment. SecretStr keeps it out of
            # reprs, tracebacks and structlog output everywhere above this line.
            password=settings.smtp_password.get_secret_value(),
            security=smtp_security(),
            sender=settings.notification_email_from,
            sender_name=sender_name(),
            ca_file=settings.smtp_ca_file,
            timeout_s=settings.smtp_timeout_s,
        )
    if settings.email_transport == "null":
        return NullEmailTransport()
    return ConsoleEmailTransport()
