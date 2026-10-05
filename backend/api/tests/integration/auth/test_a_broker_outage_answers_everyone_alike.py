"""A broker outage answers a code request the same way for everybody.

The three neutral forms - sign-in by code, password reset, a consent link's
code - say the same sentence whether or not the contact is registered. But a
code for somebody registered was queued with `dispatch_required`, which
answers 503 when the broker is down, while a stranger's request returned
before anything was queued: 503 for a registered contact, 200 for anyone
else. An outage turned each form into the oracle it was written not to be.

Each now checks the broker before it looks anybody up, so an outage is a 503
for every caller, and the portal can say "try again" without saying who is
registered (review 2026-10-01, UX-3).
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.auth.authentication import service as auth_service
from cmp.core.errors import ServiceUnavailable
from cmp.domain.consent import service as consent_service
from cmp.tasks import dispatch
from tests.integration.test_consent_link_identity import a_link

pytestmark = pytest.mark.integration


@pytest.fixture
def broker_down(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_: Any, **__: Any) -> None:
        raise OSError("connection refused")

    monkeypatch.setattr(dispatch, "_touch_broker", refuse)


async def test_sign_in_by_code(conn: Any, seeded: dict[str, Any], broker_down: None) -> None:
    for contact in ("subject@test.local", "nobody-at-all@test.local"):
        with pytest.raises(ServiceUnavailable):
            await auth_service.request_subject_otp(conn, contact=contact)


async def test_password_reset(conn: Any, seeded: dict[str, Any], broker_down: None) -> None:
    for email in ("dpo@test.local", "nobody-at-all@test.local"):
        with pytest.raises(ServiceUnavailable):
            await auth_service.request_password_reset(conn, email=email)


async def test_a_consent_links_code(conn: Any, seeded: dict[str, Any], broker_down: None) -> None:
    token = await a_link(conn, seeded)
    for contact in ("subject@test.local", "nobody-at-all@test.local"):
        with pytest.raises(ServiceUnavailable):
            await consent_service.send_contact_code(conn, token=token, contact=contact)


async def test_with_the_broker_up_a_stranger_is_still_told_nothing(
    conn: Any, seeded: dict[str, Any]
) -> None:
    assert await auth_service.request_subject_otp(conn, contact="nobody-at-all@test.local") is None
