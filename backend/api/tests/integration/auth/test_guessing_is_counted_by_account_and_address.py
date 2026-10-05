"""Guessing is counted against the account, and against the address it comes from.

Three gaps the backend guide listed (2026-09-28), closed together because they
are one control:

* **The lockout counted what was typed, not the account.** An account signed
  in to by email or by username had two counters, so an attacker had twice
  the guesses the lockout allowed - and the typed login sat in Redis in the
  clear.
* **No address was limited.** The per-account lockout stops guessing at one
  account; it does nothing against one address trying a few passwords at
  every account it can name. Failed attempts from one address at sign-in, at
  the code sign-in and at password reset now have a budget.
* **A code's failure count expired after ten minutes, whatever the code's
  own life.** A 48-hour invitation code got five fresh guesses every ten
  quiet minutes.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.auth.authentication import otp
from cmp.auth.authentication import service as auth_service
from cmp.auth.rate_limit import service as ratelimit
from cmp.core.config import settings
from cmp.core.context import RequestContext, use_context
from cmp.core.errors import BadRequest, RateLimited, Unauthenticated
from cmp.core.security import hash_password, new_token
from cmp.db.redis import K_OTP_ATTEMPTS, key
from tests.conftest import hashed

pytestmark = pytest.mark.integration

PASSWORD = "a-real-passphrase-2026"


async def _staff_with_username(conn: Any, seeded: dict[str, Any]) -> tuple[dict[str, Any], str]:
    dpo = seeded["users"]["dpo"]
    username = f"lock{new_token(4)}"
    await conn.execute(
        "UPDATE auth_user SET username = %s, username_hash = %s, password_hash = %s WHERE id = %s",
        (username, hashed("username", username), hash_password(PASSWORD), dpo["id"]),
    )
    return dpo, username


async def _sign_in(conn: Any, login: str, password: str) -> dict[str, Any]:
    return await auth_service.authenticate(
        conn, login=login, password=password, ip_address="127.0.0.1", user_agent="test"
    )


async def test_email_and_username_share_one_lockout(
    conn: Any, seeded: dict[str, Any], redis_conn: Any
) -> None:
    dpo, username = await _staff_with_username(conn, seeded)
    account = ratelimit.account_key(str(dpo["uuid"]))
    await ratelimit.clear_login_failures(account)
    try:
        with use_context(RequestContext(request_id="t", ip_address=f"10.9.{new_token(1)}.1")):
            for attempt in range(settings.login_max_attempts):
                login = "dpo@test.local" if attempt % 2 else username
                with pytest.raises(Unauthenticated):
                    await _sign_in(conn, login, "not-the-password")
            with pytest.raises(RateLimited):
                await _sign_in(conn, "dpo@test.local", PASSWORD)
            with pytest.raises(RateLimited):
                await _sign_in(conn, username, PASSWORD)
    finally:
        await ratelimit.clear_login_failures(account)


async def test_a_typed_login_is_not_kept_in_the_clear(
    conn: Any, seeded: dict[str, Any], redis_conn: Any
) -> None:
    nobody = f"nobody-{new_token(4)}@test.local"
    with (
        use_context(RequestContext(request_id="t", ip_address="10.9.0.2")),
        pytest.raises(Unauthenticated),
    ):
        await _sign_in(conn, nobody, "whatever-it-is")
    keys = [k async for k in redis_conn.scan_iter(match="*")]
    assert not [k for k in keys if nobody in str(k)]


async def test_a_password_reset_lifts_the_lockout(
    conn: Any, seeded: dict[str, Any], redis_conn: Any
) -> None:
    dpo = seeded["users"]["dpo"]
    account = ratelimit.account_key(str(dpo["uuid"]))
    for _ in range(settings.login_max_attempts):
        await ratelimit.record_login_failure(account)
    assert await ratelimit.is_locked_out(account)

    issued = await otp.issue(otp.Scope.CONTACT_VERIFY, f"reset:{dpo['uuid']}")
    await auth_service.confirm_password_reset(
        conn, email="dpo@test.local", code=issued.code, new_password="a-fresh-passphrase-2026"
    )
    assert not await ratelimit.is_locked_out(account)


@pytest.mark.parametrize("door", ["password", "code", "reset"])
async def test_one_address_has_a_budget_of_failures(
    conn: Any,
    seeded: dict[str, Any],
    redis_conn: Any,
    monkeypatch: pytest.MonkeyPatch,
    door: str,
) -> None:
    """Each failure names a different account, so no account's lockout is
    reached - only the address's budget is."""
    monkeypatch.setattr(settings, "auth_failures_per_address", 3)
    address = f"10.8.{new_token(1)}.{door[0]}"

    async def fail_once() -> None:
        other = f"x{new_token(4)}@test.local"
        if door == "password":
            await _sign_in(conn, other, "not-the-password")
        elif door == "code":
            await auth_service.verify_subject_otp(
                conn, contact=other, code="123456", ip_address=address, user_agent="t"
            )
        else:
            await auth_service.confirm_password_reset(
                conn, email=other, code="123456", new_password="a-fresh-passphrase-2026"
            )

    with use_context(RequestContext(request_id="t", ip_address=address)):
        for _ in range(3):
            with pytest.raises((Unauthenticated, BadRequest)):
                await fail_once()
        with pytest.raises(RateLimited):
            await fail_once()
    # Another address is not affected.
    with (
        use_context(RequestContext(request_id="t", ip_address=f"{address}9")),
        pytest.raises((Unauthenticated, BadRequest)),
    ):
        await fail_once()


async def test_a_long_lived_code_keeps_its_failures_as_long_as_it_lives(redis_conn: Any) -> None:
    identity = f"invite-{new_token(6)}"
    two_days = 48 * 60 * 60
    await otp.issue(otp.Scope.CONTACT_VERIFY, identity, ttl_s=two_days)
    assert await otp.verify(otp.Scope.CONTACT_VERIFY, identity, "000000") is False

    ttl = await redis_conn.ttl(key(K_OTP_ATTEMPTS, otp.Scope.CONTACT_VERIFY, identity))
    assert ttl > settings.otp_ttl_s, "the failure count would reset before the code expires"
    await otp.discard(otp.Scope.CONTACT_VERIFY, identity)
