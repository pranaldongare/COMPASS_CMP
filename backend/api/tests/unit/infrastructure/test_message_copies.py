"""Copies and files at the one point every message passes (2026-10-08).

A message the catalogue marks copyable goes to the office's copy addresses
too, opened from their sealed form; any other never does, whatever the table
holds. Files go only on a message marked attachable. SMS carries neither.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.messages import ATTACHABLE, CATALOGUE, COPYABLE, Message
from cmp.infrastructure import messaging
from cmp.infrastructure.email import Attachment, NullEmailTransport

#: A message that carries a code or a link, or a person's own record, is never
#: copyable - a copy would hand somebody else what is hers.
NEVER_COPIED = {
    Message.MFA_CODE,
    Message.LOGIN_CODE,
    Message.REGISTRATION_CODE,
    Message.CONSENT_CODE,
    Message.PASSWORD_RESET,
    Message.STAFF_INVITATION,
    Message.CONTACT_CONFIRMATION,
    Message.CONTACT_ADDED_FOR_YOU,
    Message.CONSENT_RECEIPT,
    Message.WITHDRAWAL_CONFIRMATION,
    Message.RIGHTS_VERIFICATION_CODE,
    Message.RIGHTS_RESPONSE,
    Message.NOMINATION_CODE,
    Message.NOMINATION_INVITATION,
    Message.BREACH_NOTICE,
    Message.BREACH_NOTICE_DIRECT,
    Message.BREACH_TICKET_ACCESS,
    Message.HOLDER_TICKET_LINK,
    Message.HOLDER_TICKET_CODE,
}


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> NullEmailTransport:
    null = NullEmailTransport()
    monkeypatch.setattr("cmp.infrastructure.email.build_email_transport", lambda: null)
    monkeypatch.setattr(messaging, "load_overrides", lambda: {})
    monkeypatch.setattr(
        messaging,
        "load_copies",
        lambda: {m.value: ["team@corp.example"] for m in Message},
    )
    return null


def _vars(key: Message) -> dict[str, Any]:
    [j] = [j for j in CATALOGUE if j.key is key]
    return dict(j.samples)


def test_nothing_with_a_code_a_link_or_her_own_record_is_copyable() -> None:
    assert not (COPYABLE & NEVER_COPIED)
    assert set(Message) >= ATTACHABLE


def test_a_copyable_message_goes_to_its_copies(sent: NullEmailTransport) -> None:
    key = next(iter(COPYABLE))
    messaging.deliver(key, to="holder@corp.example", **_vars(key))
    [one] = sent.sent
    assert one["cc"] == ["team@corp.example"]


def test_a_message_that_is_not_copyable_never_is(sent: NullEmailTransport) -> None:
    messaging.deliver(Message.MFA_CODE, to="dpo@corp.example", **_vars(Message.MFA_CODE))
    [one] = sent.sent
    assert one["cc"] == []


def test_files_only_on_a_message_that_carries_them(sent: NullEmailTransport) -> None:
    receipt = Attachment("receipt.txt", "text/plain", b"record")
    messaging.deliver(
        Message.CONSENT_RECEIPT,
        to="asha@example.org",
        attachments=[receipt],
        **_vars(Message.CONSENT_RECEIPT),
    )
    assert sent.sent[0]["attachments"] == [receipt]
    with pytest.raises(ValueError, match="does not carry files"):
        messaging.deliver(
            Message.MFA_CODE, to="a@corp.example", attachments=[receipt], **_vars(Message.MFA_CODE)
        )


def test_the_deployments_own_copies_join_the_offices_on_a_copyable_email(
    sent: NullEmailTransport, monkeypatch: pytest.MonkeyPatch
) -> None:
    """EMAIL_CC_ADDRESSES (2026-10-08): on every copyable email, after the
    office's copies, each address once and never the recipient's own."""
    from cmp.core.config import settings

    monkeypatch.setattr(
        settings,
        "email_cc_addresses",
        ("audit@corp.example", "team@corp.example", "holder@corp.example"),
    )
    key = next(iter(COPYABLE))
    messaging.deliver(key, to="holder@corp.example", **_vars(key))
    [one] = sent.sent
    assert one["cc"] == ["team@corp.example", "audit@corp.example"]


def test_the_deployments_copies_never_go_on_a_code_a_link_or_her_record(
    sent: NullEmailTransport, monkeypatch: pytest.MonkeyPatch
) -> None:
    from cmp.core.config import settings

    monkeypatch.setattr(settings, "email_cc_addresses", ("audit@corp.example",))
    for key in (Message.MFA_CODE, Message.HOLDER_TICKET_LINK, Message.CONSENT_RECEIPT):
        messaging.deliver(key, to="person@corp.example", **_vars(key))
    assert [m["cc"] for m in sent.sent] == [[], [], []]


@pytest.mark.parametrize(
    ("raw", "ok"),
    [
        ("Audit@Corp.example, team@corp.example,audit@corp.example", True),
        ("", True),
        ("not-an-address", False),
        ("a@x.io,b@x.io,c@x.io,d@x.io,e@x.io,f@x.io", False),
    ],
)
def test_email_cc_addresses_is_checked_at_startup(raw: str, ok: bool) -> None:
    from pydantic import ValidationError

    from cmp.core.config import Settings

    if ok:
        parsed = Settings(email_cc_addresses=raw).email_cc_addresses  # type: ignore[arg-type]
        assert all(a == a.lower() for a in parsed) and len(parsed) == len(set(parsed))
    else:
        with pytest.raises(ValidationError):
            Settings(email_cc_addresses=raw)  # type: ignore[arg-type]


def test_test_mode_sends_every_email_only_to_the_redirect_addresses(
    sent: NullEmailTransport, monkeypatch: pytest.MonkeyPatch
) -> None:
    """EMAIL_REDIRECT_TO (2026-10-08): the recipient and the copies get
    nothing; the configured inboxes get it, saying whom it was for."""
    from cmp.core.config import settings

    monkeypatch.setattr(settings, "email_redirect_to", ("uat@corp.example", "qa@corp.example"))
    key = next(iter(COPYABLE))
    messaging.deliver(key, to="holder@corp.example", **_vars(key))
    messaging.deliver(Message.MFA_CODE, to="dpo@corp.example", **_vars(Message.MFA_CODE))
    first, second = sent.sent
    for one in (first, second):
        assert one["to"] == "uat@corp.example" and one["cc"] == ["qa@corp.example"]
        assert one["subject"].startswith("[TEST] ")
        assert one["body"].startswith("TEST MODE")
    assert "This email was for holder@corp.example, copied to team@corp.example." in first["body"]
    assert "This email was for dpo@corp.example." in second["body"]


def test_test_mode_turns_a_text_into_an_email_to_the_redirect_addresses(
    sent: NullEmailTransport, monkeypatch: pytest.MonkeyPatch
) -> None:
    from cmp.core.config import settings

    def no_sms() -> Any:
        raise AssertionError("no text may be sent in test mode")

    monkeypatch.setattr("cmp.infrastructure.sms.build_sms_transport", no_sms)
    monkeypatch.setattr(settings, "email_redirect_to", ("uat@corp.example",))
    messaging.deliver(Message.LOGIN_CODE, to="+919000000001", **_vars(Message.LOGIN_CODE))
    [one] = sent.sent
    assert one["to"] == "uat@corp.example" and one["cc"] == []
    assert one["subject"].startswith("[TEST] Text message for +919000000001")
    assert "This text message was for +919000000001." in one["body"]


def test_production_refuses_test_mode() -> None:
    from pydantic import ValidationError

    from cmp.core.config import Settings

    with pytest.raises(ValidationError, match="EMAIL_REDIRECT_TO"):
        Settings(
            environment="production",
            secret_key="x" * 40,
            postgres_password="a-real-password",
            cookie_secure=True,
            debug=False,
            cors_origins="https://console.corp.example",
            smtp_host="smtp.corp.example",
            notification_email_from="privacy@corp.example",
            email_redirect_to="uat@corp.example",
        )  # type: ignore[arg-type]
