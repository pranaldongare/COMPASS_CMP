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
from cmp.infrastructure.dkms.client import DkmsUnavailable
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
