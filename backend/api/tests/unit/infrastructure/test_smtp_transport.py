"""The SMTP transport (2026-10-06): how it connects, what it sends, and which
failures a retry can mend.

Five settings and nothing else: SMTP_SERVER, SMTP_PORT, SMTP_USERNAME,
SMTP_PASSWORD, SENDER_EMAIL. A fake server stands in for smtplib's client,
recording what the transport asked of it. The port decides the way in - 465
SSL, 587 STARTTLS, anything else plain - a login only when one is set, and
the message carries both the laid-out HTML and the plain text, a named
sender, a date, an id and the auto-reply guard. A refusal that will not change
(a wrong login, a 5xx, an untrusted certificate) is `EmailRejected`, which no
task retries; a passing failure stays an `OSError`, which they do.
"""

from __future__ import annotations

import smtplib
import ssl
from typing import Any, ClassVar

import pytest

from cmp.core.config import Settings
from cmp.infrastructure.email import transport as t
from cmp.infrastructure.email.transport import EmailRejected, SmtpEmailTransport


class FakeServer:
    """Records the conversation; raises what a test tells it to."""

    made: ClassVar[list[FakeServer]] = []

    def __init__(self, host: str, port: int, timeout: float, context: Any = None) -> None:
        self.host, self.port, self.timeout, self.context = host, port, timeout, context
        self.calls: list[str] = []
        self.sent: list[Any] = []
        FakeServer.made.append(self)

    fail: ClassVar[dict[str, BaseException]] = {}

    def _maybe(self, step: str) -> None:
        self.calls.append(step)
        if step in FakeServer.fail:
            raise FakeServer.fail[step]

    def ehlo(self) -> None:
        self._maybe("ehlo")

    def starttls(self, context: Any = None) -> None:
        self._maybe("starttls")

    def login(self, user: str, password: str) -> None:
        self._maybe(f"login:{user}")

    def send_message(self, message: Any) -> dict[str, Any]:
        self._maybe("send")
        self.sent.append(message)
        return {}

    def close(self) -> None:
        self.calls.append("close")

    def __enter__(self) -> FakeServer:
        return self

    def __exit__(self, *_: Any) -> None:
        self.calls.append("quit")


class FakeSSLServer(FakeServer):
    pass


@pytest.fixture(autouse=True)
def fake_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeServer.made = []
    FakeServer.fail = {}
    monkeypatch.setattr(t.smtplib, "SMTP", FakeServer)
    monkeypatch.setattr(t.smtplib, "SMTP_SSL", FakeSSLServer)


def transport(**kw: Any) -> SmtpEmailTransport:
    return SmtpEmailTransport(
        kw.pop("host", "mail.corp.example"),
        kw.pop("port", 587),
        sender="privacy@corp.example",
        timeout_s=7,
        **kw,
    )


def send(tx: SmtpEmailTransport) -> dict[str, object]:
    return tx.send(to="asha.rao@corp.example", subject="Your code", body="482913 is your code.")


def test_starttls_upgrades_before_the_login_and_sends_once() -> None:
    result = send(transport(username="svc-cmp", password="secret"))
    [server] = FakeServer.made
    assert server.calls == ["ehlo", "starttls", "ehlo", "login:svc-cmp", "send", "quit"]
    assert (server.host, server.port, server.timeout) == ("mail.corp.example", 587, 7)
    assert result["delivered"] is True and str(result["message_id"]).endswith("@corp.example>")


def test_ssl_is_encrypted_from_the_first_byte() -> None:
    send(transport(port=465, username="svc-cmp", password="secret"))
    [server] = FakeServer.made
    assert isinstance(server, FakeSSLServer) and isinstance(server.context, ssl.SSLContext)
    assert server.calls == ["login:svc-cmp", "send", "quit"]


def test_a_plain_relay_without_a_login_only_sends() -> None:
    send(transport(port=25))
    [server] = FakeServer.made
    assert server.calls == ["send", "quit"]


def test_the_message_names_its_sender_and_is_marked_automatic() -> None:
    send(transport(port=25))
    [message] = FakeServer.made[0].sent
    assert message["From"] == "COMPASS Privacy Office <privacy@corp.example>"
    assert message["To"] == "asha.rao@corp.example"
    assert message["Subject"] == "Your code"
    assert message["Auto-Submitted"] == "auto-generated"
    assert message["Date"] and message["Message-ID"]
    # Both: the laid-out HTML, and the text for a client that shows none.
    assert message.get_content_type() == "multipart/alternative"
    text = message.get_body(preferencelist=("plain",)).get_content()
    page = message.get_body(preferencelist=("html",)).get_content()
    assert text.startswith("482913 is your code.") and "COMPASS Privacy Office" in text
    assert "<h1" in page and "Your code" in page and "Privacy Office" in page


@pytest.mark.parametrize(
    ("step", "error"),
    [
        ("login:svc-cmp", smtplib.SMTPAuthenticationError(535, b"Authentication failed")),
        ("send", smtplib.SMTPSenderRefused(550, b"Not allowed", "privacy@corp.example")),
        ("send", smtplib.SMTPRecipientsRefused({"asha.rao@corp.example": (550, b"No such user")})),
        ("starttls", smtplib.SMTPNotSupportedError("STARTTLS extension not supported")),
        ("starttls", ssl.SSLCertVerificationError("certificate verify failed")),
    ],
)
def test_a_refusal_no_retry_will_mend_is_not_retried(step: str, error: BaseException) -> None:
    FakeServer.fail = {step: error}
    with pytest.raises(EmailRejected) as refused:
        send(transport(username="svc-cmp", password="secret"))
    assert not isinstance(refused.value, OSError), "tasks retry OSError; this must not be one"
    assert "secret" not in str(refused.value)


@pytest.mark.parametrize(
    ("step", "error"),
    [
        ("send", smtplib.SMTPServerDisconnected("Connection unexpectedly closed")),
        ("send", smtplib.SMTPDataError(451, b"Try again later")),
        ("send", smtplib.SMTPRecipientsRefused({"asha.rao@corp.example": (450, b"Mailbox busy")})),
        ("ehlo", TimeoutError("timed out")),
    ],
)
def test_a_passing_failure_is_left_for_the_task_to_retry(step: str, error: BaseException) -> None:
    FakeServer.fail = {step: error}
    with pytest.raises(OSError):
        send(transport(username="svc-cmp", password="secret"))


def test_a_failed_upgrade_closes_the_connection() -> None:
    FakeServer.fail = {"starttls": smtplib.SMTPNotSupportedError("no STARTTLS")}
    with pytest.raises(EmailRejected):
        send(transport(port=587))
    assert FakeServer.made[0].calls[-1] == "close"


def test_the_port_decides_the_connection() -> None:
    assert [t.connection_for(p) for p in (465, 587, 25, 2525)] == [
        "ssl",
        "starttls",
        "plain",
        "plain",
    ]


def test_the_five_settings_build_the_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    """SMTP_SERVER set is all it takes to send for real."""
    s = Settings(
        _env_file=None,  # type: ignore[call-arg]
        SMTP_SERVER="relay.corp.example",
        SMTP_PORT=25,
        SMTP_USERNAME="",
        SMTP_PASSWORD="",
        SENDER_EMAIL="privacy@corp.example",
    )
    assert s.email_mode == "smtp"
    monkeypatch.setattr(t, "settings", s)
    built = t.build_email_transport()
    assert isinstance(built, SmtpEmailTransport)
    built.send(to="asha.rao@corp.example", subject="s", body="b")
    [server] = FakeServer.made
    assert (server.host, server.port, server.calls) == ("relay.corp.example", 25, ["send", "quit"])
    assert server.sent[0]["From"] == "COMPASS Privacy Office <privacy@corp.example>"


def test_without_a_server_email_goes_to_the_outbox() -> None:
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.email_mode == "console"


def test_production_refuses_a_placeholder_sender() -> None:
    with pytest.raises(ValueError, match="NOTIFICATION_EMAIL_FROM"):
        Settings(
            _env_file=None,  # type: ignore[call-arg]
            ENVIRONMENT="production",
            SMTP_SERVER="relay.corp.example",
            SMS_TRANSPORT="http",
            NOTIFICATION_EMAIL_FROM="privacy@example.org",
            SECRET_KEY="x" * 64,
            POSTGRES_PASSWORD="a-real-one",
            COOKIE_SECURE=True,
            CORS_ORIGINS="https://console.corp.example",
        )
