"""A message whose recipient cannot be opened fails loudly and is retried.

Every message is addressed to a contact sealed in the database; the worker
opens it on the way out. If the key service cannot be reached, the message
is not sent - and the request that queued it has already answered "a code
has been sent". That is the one failure invisible from outside, so two
things must hold: one log line that names the service, and a retry, because
a service that blinks must not cost somebody their sign-in code.
"""

from __future__ import annotations

from typing import Any

import pytest
from structlog.testing import capture_logs

from cmp.core.messages import Message
from cmp.infrastructure.dkms.client import DkmsUnavailable, SealedValueUnreadable
from cmp.infrastructure.messaging import deliver


def test_the_failure_names_the_service_and_is_raised(monkeypatch: Any) -> None:
    def refuse(_: list[str]) -> list[str]:
        raise DkmsUnavailable("http://10.0.0.5:32688/bulk_decrypt: Connection refused")

    monkeypatch.setattr("cmp.infrastructure.dkms.unseal_values_sync", refuse)
    monkeypatch.setattr("cmp.infrastructure.dkms.unseal_variables_sync", refuse)

    with capture_logs() as logs, pytest.raises(DkmsUnavailable):
        deliver(Message.MFA_CODE, to="SE::REsBAg-not-openable", code="123456", minutes=5)

    said = " ".join(str(line) for line in logs)
    assert "message.not_sent" in said
    assert "10.0.0.5:32688" in said, "the operator has to be told which service"
    assert "123456" not in said, "a code never reaches a log line"


def test_every_message_task_retries_when_the_key_service_blinks() -> None:
    """Otherwise the code is lost outright rather than sent a moment later."""
    from cmp.tasks.authentication import otp
    from cmp.tasks.notifications import batch, consent, rights, staff, withdrawal

    for module in (otp, staff, rights, consent, batch, withdrawal):
        assert DkmsUnavailable in module.RETRY_KW["autoretry_for"], module.__name__


def test_a_sealed_recipient_with_the_service_switched_off_says_so(monkeypatch: Any) -> None:
    """The failure reported from a Windows worker on 2026-09-23.

    `DKMS_ENABLED` was false in the worker's environment while the rows were
    sealed, so `unseal_values_sync` returned the ciphertext unchanged, the
    channel was chosen by looking for an `@` in it, and the task died with
    "'mfa_code' is not sent by sms" - which names neither the cause nor
    anything a person could act on. Nobody could sign in.

    Not retried: the flag is read when the worker starts, so the same worker
    answers the same way every time until somebody changes it and restarts.
    """
    monkeypatch.setattr("cmp.core.config.settings.dkms_enabled", False)

    with pytest.raises(SealedValueUnreadable) as raised:
        deliver(Message.MFA_CODE, to="SE::REsBAg-sealed", code="123456", minutes=5)

    said = str(raised.value)
    assert "DKMS_ENABLED" in said, "the setting to change has to be in the message"
    assert "worker" in said, "and which process to change it in"
    assert "123456" not in said


# --------------------------------------------------- a key service of any make
#
# Reported from a second machine on 2026-09-24: the deployed key service
# writes its own envelope - it begins with the bytes 0x19 0xEF, not "DK",
# and names no data type - so `type_of` read nothing from any value it had
# sealed, every sign-in code failed as "no readable envelope", and each
# failure was retried five times over minutes although no retry could help.
# The service itself offered `/auto_decrypt`, which reads its own envelope.

import base64  # noqa: E402

import httpx  # noqa: E402

#: A value as the deployed service writes it: its magic, no type byte.
FOREIGN = "SE::" + base64.urlsafe_b64encode(b"\x19\xef" + bytes(range(40))).decode()


class _Service:
    """A key service at the far end of `httpx`, recording what it was sent."""

    def __init__(self, answer: Any) -> None:
        self.answer = answer
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def install(self, monkeypatch: Any) -> _Service:
        import json

        real = httpx.Client

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            self.calls.append((request.url.path, body))
            return self.answer(request.url.path, body)

        def client(**kwargs: Any) -> httpx.Client:
            return real(transport=httpx.MockTransport(handler), **kwargs)

        monkeypatch.setattr("cmp.infrastructure.dkms.client.httpx.Client", client)
        monkeypatch.setattr("cmp.core.config.settings.dkms_enabled", True)
        return self


def test_a_value_sealed_by_another_key_service_is_opened_by_that_service(monkeypatch: Any) -> None:
    """The envelope names no type, so the service is asked to read its own."""
    from cmp.infrastructure.dkms.client import unseal_values_sync

    service = _Service(
        lambda path, body: httpx.Response(200, json={"data": {"v0": "priya@example.org"}})
    ).install(monkeypatch)

    assert unseal_values_sync([FOREIGN, "plain"]) == ["priya@example.org", "plain"]
    assert service.calls == [("/auto_decrypt", {"payload": {"v0": FOREIGN}})]


def test_a_sign_in_code_reaches_an_address_sealed_by_another_key_service(
    monkeypatch: Any,
) -> None:
    """The report, end to end: the code is delivered, not retried to death."""
    _Service(
        lambda path, body: httpx.Response(200, json={"data": {"v0": "priya@example.org"}})
    ).install(monkeypatch)
    sent: list[str] = []
    monkeypatch.setattr(
        "cmp.infrastructure.email.transport.ConsoleEmailTransport.send",
        lambda self, **kw: sent.append(kw["to"]) or {"transport": "console"},
    )

    deliver(Message.MFA_CODE, to=FOREIGN, code="123456", minutes=5)

    assert sent == ["priya@example.org"]


def test_a_value_whose_envelope_names_its_type_goes_by_the_contract_alone(
    monkeypatch: Any,
) -> None:
    """`/bulk_decrypt`, with `{data, key, method}` and nothing a strict
    service would refuse - no `on_error`."""
    from cmp.infrastructure.dkms.client import unseal_values_sync

    ours = "SE::" + base64.urlsafe_b64encode(b"DK\x01\x02" + bytes(40)).decode()
    service = _Service(
        lambda path, body: httpx.Response(200, json={"data": [{"EMAIL": "a@example.org"}]})
    ).install(monkeypatch)

    assert unseal_values_sync([ours]) == ["a@example.org"]
    path, body = service.calls[0]
    assert path == "/bulk_decrypt"
    assert set(body) == {"data", "key", "method"}


@pytest.mark.parametrize(
    ("status", "error", "says"),
    [
        (404, "SealedValueUnreadable", "/auto_decrypt"),
        (422, "SealedValueUnreadable", "could not open"),
        (503, "DkmsUnavailable", "503"),
    ],
)
def test_a_refusal_is_final_and_an_outage_is_retried(
    monkeypatch: Any, status: int, error: str, says: str
) -> None:
    """A 4xx will be the same 4xx on every retry; a 5xx may not be."""
    from cmp.infrastructure.dkms import client as dkms_client

    _Service(lambda path, body: httpx.Response(status, json={})).install(monkeypatch)

    with pytest.raises(getattr(dkms_client, error)) as raised:
        dkms_client.unseal_values_sync([FOREIGN])

    assert says in str(raised.value)


def test_an_unreachable_service_is_an_outage(monkeypatch: Any) -> None:
    from cmp.infrastructure.dkms.client import unseal_values_sync

    def refuse(path: str, body: Any) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    _Service(refuse).install(monkeypatch)

    with pytest.raises(DkmsUnavailable):
        unseal_values_sync([FOREIGN])


def test_a_value_handed_back_still_sealed_is_not_mistaken_for_an_address(
    monkeypatch: Any,
) -> None:
    """A service that answers 200 and returns the value as it went."""
    from cmp.infrastructure.dkms.client import unseal_values_sync

    _Service(lambda path, body: httpx.Response(200, json={"data": {"v0": FOREIGN}})).install(
        monkeypatch
    )

    with pytest.raises(SealedValueUnreadable):
        unseal_values_sync([FOREIGN])


def test_no_message_task_retries_what_no_retry_will_open() -> None:
    """Five retries of a value that cannot be opened is minutes spent finding
    out what the first attempt already said."""
    from cmp.tasks.authentication import otp
    from cmp.tasks.notifications import batch, consent, rights, staff, withdrawal

    for module in (otp, staff, rights, consent, batch, withdrawal):
        retried = module.RETRY_KW["autoretry_for"]
        assert not any(issubclass(SealedValueUnreadable, e) for e in retried), module.__name__
