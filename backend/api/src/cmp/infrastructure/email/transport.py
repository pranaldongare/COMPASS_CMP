"""Where an email actually goes.

One protocol, three implementations. The point of the seam is that everything
above it — the templates, the tasks, the retry policy — is written once and
does not change when the transport does.

Five settings configure it, and nothing else (docs/email/README.md):
SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD and SENDER_EMAIL. With
SMTP_SERVER set, email goes to that server; without it, to the local outbox.

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

Every email is sent twice over in one message: laid out in HTML with the
platform's header and footer (`layout.py`), and as plain text for a client
that shows no HTML.
"""

from __future__ import annotations

import re
import smtplib
import ssl
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path
from typing import Protocol, runtime_checkable

from cmp.core.config import settings
from cmp.core.logging import get_logger
from cmp.infrastructure.email import layout

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


def sender_name() -> str:
    """The name shown beside SENDER_EMAIL."""
    return f"{settings.organisation_name} Privacy Office"


def compose(*, sender: str, to: str, subject: str, body: str) -> EmailMessage:
    """The message as it goes out: the laid-out HTML and the plain text in one
    message, from the Privacy Office by name, with a date and an id, and marked
    automatic so an out-of-office reply is not sent back (RFC 3834)."""
    organisation = settings.organisation_name
    domain = sender.rpartition("@")[2] or "localhost"
    message = EmailMessage()
    message["From"] = formataddr((sender_name(), sender))
    message["To"] = to
    message["Subject"] = subject
    message["Date"] = formatdate(usegmt=True)
    message["Message-ID"] = make_msgid(domain=domain)
    message["Auto-Submitted"] = "auto-generated"
    message.set_content(layout.render_text(body=body, organisation=organisation))
    message.add_alternative(
        layout.render_html(subject=subject, body=body, organisation=organisation), subtype="html"
    )
    return message


class ConsoleEmailTransport:
    """Development. Writes to a local outbox file and logs the fact.

    This exists because one-time codes are deliberately absent from the logs,
    which makes the local sign-in loop impossible to complete without somewhere
    to read them. Same idea as running MailHog beside a dev stack, minus the
    container. Each email is also saved as an HTML file beside the outbox
    (`var/outbox-html/`), so its layout can be opened in a browser.

    Hard-gated on environment, twice: the guard runs before anything is
    formatted, so there is no code path where a production process assembles a
    plaintext file of verification codes and then decides not to write it.
    """

    def __init__(self, outbox_path: str | None = None) -> None:
        self._path = (
            Path(outbox_path) if outbox_path else Path(settings.upload_root).parent / "outbox.log"
        )

    def send(self, *, to: str, subject: str, body: str) -> dict[str, object]:
        if settings.is_production or settings.environment == "staging":
            # Not "return delivered": a transport that writes nothing and says
            # it did turns a misconfiguration into silent loss.
            raise RuntimeError("The console email transport does not deliver outside local/test")
        self._write(to=to, subject=subject, body=body)
        preview = self._preview(subject=subject, body=body)
        from cmp.infrastructure import devcodes

        devcodes.record(channel="email", to=to, text=f"{subject}\n{body}")
        log.info(
            "email.delivered",
            to=obscure(to),
            subject=subject,
            transport="console",
            preview=preview,
        )
        return {"channel": "email", "transport": "console", "delivered": True, "preview": preview}

    def _write(self, *, to: str, subject: str, body: str) -> None:
        try:
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

    def _preview(self, *, subject: str, body: str) -> str | None:
        """The laid-out email as a file to open in a browser. The recipient is
        not in its name; a code in it is development's, never production's."""
        try:
            folder = self._path.parent / "outbox-html"
            folder.mkdir(parents=True, exist_ok=True)
            slug = re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-")[:60] or "email"
            stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
            target = folder / f"{stamp}-{slug}.html"
            target.write_text(
                layout.render_html(
                    subject=subject, body=body, organisation=settings.organisation_name
                ),
                encoding="utf-8",
            )
            return str(target)
        except OSError as exc:  # pragma: no cover — a convenience, never fatal
            log.warning("email.preview_unavailable", error=str(exc))
            return None


class EmailRejected(RuntimeError):
    """The mail server refused for good: a wrong login, an address or a sender
    it will not take, a certificate that does not verify, a protocol it does
    not speak. Not an `OSError`, so no task retries it - the same request
    would be refused again. A passing failure - the server unreachable or
    busy, a 4xx - stays the `OSError` smtplib raised, and is retried."""


def connection_for(port: int) -> str:
    """How a port is spoken to: 465 is SSL from the first byte, 587 is
    STARTTLS, anything else (25) a plain connection to an internal relay."""
    if port == 465:
        return "ssl"
    if port == 587:
        return "starttls"
    return "plain"


class SmtpEmailTransport:
    """Production, via SMTP: the server, port, login and sender of the five
    settings. One connection per message, opened and closed here.

    How the connection is protected follows the port (`connection_for`).
    On 587 the server must upgrade with STARTTLS - one that cannot is refused,
    never used unencrypted; on 465 it is encrypted from the start. Either way
    the server's certificate is verified against the system's authorities. On
    25 the connection is plain, as an internal relay expects - and so is any
    login over it, so that is for a relay on a trusted network.
    """

    def __init__(
        self,
        host: str,
        port: int,
        *,
        username: str = "",
        password: str = "",
        sender: str = "",
        timeout_s: float | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._sender = sender or settings.notification_email_from
        self._mode = connection_for(port)
        # Never infinite. A hung connection holds a worker slot indefinitely.
        self._timeout = timeout_s or settings.external_http_timeout_s

    def _connect(self) -> smtplib.SMTP:
        if self._mode == "ssl":
            return smtplib.SMTP_SSL(
                self._host, self._port, timeout=self._timeout, context=ssl.create_default_context()
            )
        client = smtplib.SMTP(self._host, self._port, timeout=self._timeout)
        if self._mode == "starttls":
            try:
                client.ehlo()
                client.starttls(context=ssl.create_default_context())
                client.ehlo()
            except BaseException:
                client.close()
                raise
        return client

    def send(self, *, to: str, subject: str, body: str) -> dict[str, object]:
        message = compose(sender=self._sender, to=to, subject=subject, body=body)
        where = {
            "to": obscure(to),
            "server": f"{self._host}:{self._port}",
            "connection": self._mode,
        }
        try:
            with self._connect() as client:
                if self._username:
                    client.login(self._username, self._password)
                client.send_message(message)
        except smtplib.SMTPAuthenticationError as exc:
            log.error("email.rejected", reason="login refused", code=exc.smtp_code, **where)
            raise EmailRejected(
                f"The mail server refused the login for SMTP_USERNAME (code {exc.smtp_code})"
            ) from exc
        except smtplib.SMTPNotSupportedError as exc:
            # STARTTLS or AUTH not offered: a setting, not an outage.
            log.error("email.rejected", reason="not supported by the server", **where)
            raise EmailRejected(
                f"The mail server on port {self._port} does not support what this needs ({exc}); "
                "check SMTP_PORT: 465 for SSL, 587 for STARTTLS, 25 for a plain relay"
            ) from exc
        except ssl.SSLCertVerificationError as exc:
            log.error("email.rejected", reason="certificate not trusted", **where)
            raise EmailRejected(
                "The mail server's certificate did not verify against this machine's "
                "authorities; add its authority to the system's certificates"
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


def build_email_transport() -> EmailTransport:
    """The mail server when SMTP_SERVER is set, otherwise the local outbox.

    The outbox is the default on purpose: a misconfigured staging box that
    writes to a file is a far better failure than one emailing real people
    the first time somebody signs in - and outside local and test it refuses
    to run at all.
    """
    mode = settings.email_mode
    if mode == "smtp":
        return SmtpEmailTransport(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            # Unwrapped at the last possible moment. SecretStr keeps it out of
            # reprs, tracebacks and structlog output everywhere above this line.
            password=settings.smtp_password.get_secret_value(),
            sender=settings.notification_email_from,
        )
    if mode == "null":
        return NullEmailTransport()
    return ConsoleEmailTransport()
