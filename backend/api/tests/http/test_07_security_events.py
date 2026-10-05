"""A refused request keeps its evidence (review 2026-10-01, SEC-3).

A failed sign-in wrote its audit row on the request's connection and then
raised - and the raise rolled the transaction back, row and all. The lockout
counter in Redis survived; the durable record of who was being guessed at did
not. The same was true of a wrong second-factor code, and a refusal by the
permission matrix was never recorded at all, though the security documents
say every 403 is.

Only a request answers this: the evidence has to outlive the rollback of the
transaction the request ran in, and the service-level suites roll everything
back.
"""

from __future__ import annotations

from typing import Any

import httpx

from cmp.core.config import settings
from tests.conftest import plain
from tests.http.conftest import Session, SessionFactory, last_code
from tests.http.contract import call

PASSWORD = "HttpSuite!2026"
MFA = "cmp.notifications.send_mfa_code"


async def _events(committed: Any, user_id: int, event: str) -> list[dict[str, Any]]:
    cur = await committed.execute(
        """SELECT detail_json FROM audit_log
            WHERE event_type = %s AND (subject_user_id = %s OR actor_user_id = %s)
            ORDER BY log_id""",
        (event, user_id, user_id),
    )
    return [dict(r)["detail_json"] for r in await cur.fetchall()]


async def _wrong(http: httpx.AsyncClient, staff: Session) -> None:
    await call(
        http,
        "POST",
        "/auth/login",
        expect=401,
        json={"login": plain(staff.user["email"]), "password": "not-the-password"},
    )


async def test_a_wrong_password_is_recorded(
    http: httpx.AsyncClient, session_for: SessionFactory, committed: Any
) -> None:
    dco = await session_for("dco")
    await _wrong(http, dco)
    [failed] = await _events(committed, int(dco.user["id"]), "auth.login_failed")
    assert failed["cause"] == "bad_password" and failed["failures"] == 1


async def test_a_lockout_is_recorded(
    http: httpx.AsyncClient, session_for: SessionFactory, committed: Any, redis_conn: Any
) -> None:
    from cmp.auth.rate_limit import service as ratelimit

    rco = await session_for("rco")
    try:
        for _ in range(settings.login_max_attempts):
            await _wrong(http, rco)
        assert len(await _events(committed, int(rco.user["id"]), "auth.login_failed")) == (
            settings.login_max_attempts
        )
        assert await _events(committed, int(rco.user["id"]), "auth.login_locked_out")
    finally:
        await ratelimit.clear_login_failures(plain(rco.user["email"]))


async def test_a_wrong_second_factor_is_recorded(
    http: httpx.AsyncClient, session_for: SessionFactory, committed: Any, queued: Any
) -> None:
    dco = await session_for("dco")
    first = await call(
        http,
        "POST",
        "/auth/login",
        json={"login": plain(dco.user["email"]), "password": PASSWORD},
    )
    partial = dict(first.cookies)
    code = last_code(queued, MFA)
    wrong = "000000" if code != "000000" else "111111"
    await call(
        http,
        "POST",
        "/auth/mfa/verify",
        cookies=partial,
        headers={"X-CSRF-Token": partial["cmp_csrf"]},
        json={"code": wrong},
        expect=400,
    )
    assert await _events(committed, int(dco.user["id"]), "auth.mfa_failed")


async def test_a_refusal_by_the_matrix_is_recorded(
    http: httpx.AsyncClient, session_for: SessionFactory, committed: Any
) -> None:
    dco = await session_for("dco")
    await call(http, "GET", "/audit", cookies=dco.cookies, expect=403)
    [denied] = await _events(committed, int(dco.user["id"]), "auth.access_denied")
    assert denied["role"] == "dco"
    assert denied["resource"] == "GET /audit"


async def test_a_hidden_refusal_is_recorded_and_still_says_not_found(
    http: httpx.AsyncClient, session_for: SessionFactory, committed: Any
) -> None:
    """A breach is hidden from a role without the grant: 404, not 403. What the
    caller is told does not change; what the trail records does."""
    rco = await session_for("rco")
    await call(http, "GET", "/breaches", cookies=rco.cookies, expect=404)
    [denied] = await _events(committed, int(rco.user["id"]), "auth.access_denied")
    assert denied["cause"] == "hidden"
