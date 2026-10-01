"""One phone, one quota, however it is typed (review 2026-10-01, SEC-2).

The account lookup normalises a mobile - "+91 98765 00001", "+919876500001",
"+91-98765-00001", "(+91) 98765 00001" are one person - but the code-request
throttles were keyed on the text as typed. Four spellings were four quotas, so
an attacker could have four times the codes sent, and since each new code
resets the guess counter, four times the guesses. The throttle now keys on the
contact's normalised keyed hash, the same identity the lookup finds.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.auth.authentication import service as auth_service
from cmp.auth.rate_limit import service as ratelimit
from cmp.core.config import settings
from cmp.core.errors import RateLimited
from cmp.db.redis import K_RATE
from cmp.db.redis import key as rkey
from cmp.domain.rights import service as rights_service
from cmp.tasks import dispatch as dispatch_mod

pytestmark = pytest.mark.integration

SPELLINGS = ["+91 98765 04321", "+919876504321", "+91-98765-04321", "(+91) 98765 04321"]


@pytest.fixture(autouse=True)
def no_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dispatch_mod, "dispatch_required", lambda *a, **k: "test")
    monkeypatch.setattr(dispatch_mod, "dispatch_optional", lambda *a, **k: "test")


async def _clear(redis_conn: Any, bucket: str) -> None:
    await redis_conn.delete(rkey(K_RATE, bucket, ratelimit.contact_key(SPELLINGS[0])))


def test_every_spelling_has_one_key() -> None:
    assert len({ratelimit.contact_key(s) for s in SPELLINGS}) == 1
    assert ratelimit.contact_key("Someone@Example.org ") == ratelimit.contact_key(
        "someone@example.org"
    )
    assert "98765" not in ratelimit.contact_key(SPELLINGS[0]), "no contact in the clear in Redis"


async def test_sign_in_codes_share_one_quota_across_spellings(
    conn: Any, redis_conn: Any, request_context: Any
) -> None:
    await _clear(redis_conn, "subject_otp")
    for i in range(settings.otp_requests_per_contact_per_hour):
        await auth_service.request_subject_otp(conn, contact=SPELLINGS[i % len(SPELLINGS)])
    with pytest.raises(RateLimited):
        await auth_service.request_subject_otp(conn, contact=SPELLINGS[-1])
    await _clear(redis_conn, "subject_otp")


async def test_public_rights_requests_share_one_quota_across_spellings(
    conn: Any, redis_conn: Any, request_context: Any
) -> None:
    await _clear(redis_conn, "rights_public_contact")
    for i in range(settings.otp_requests_per_contact_per_hour):
        await rights_service.submit_public(
            conn,
            request_type="access",
            name="Someone",
            contact=SPELLINGS[i % len(SPELLINGS)],
            request_text="What do you hold about me?",
            ip_address=None,
        )
    with pytest.raises(RateLimited):
        await rights_service.submit_public(
            conn,
            request_type="access",
            name="Someone",
            contact=SPELLINGS[-1],
            request_text="What do you hold about me?",
            ip_address=None,
        )
    await _clear(redis_conn, "rights_public_contact")
