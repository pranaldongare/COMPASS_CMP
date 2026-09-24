"""A page polling in the background is not somebody using it.

The console refreshes a few counts every minute (tickets waiting, unread
threads) and every request slid the session's idle window, so a console tab
left open was never idle: the 30-minute timeout could not fire. A request
marked `X-CMP-Background: 1` is still authenticated, and a session past either
limit is still refused - it just does not count as activity.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from cmp.auth.sessions import service as sessions
from cmp.core.constants import BACKGROUND_HEADER
from cmp.db.redis import get_redis

pytestmark = pytest.mark.integration


def _key(raw: str) -> str:
    from cmp.core.security import token_fingerprint

    return sessions._skey(token_fingerprint(raw))


async def _session(seeded: dict[str, Any], *, idle_for: float) -> str:
    raw, _created = await sessions.create(
        user_id=seeded["users"]["dpo"]["id"],
        user_uuid=str(seeded["users"]["dpo"]["uuid"]),
        role="dpo",
        ip_address="127.0.0.1",
        user_agent="test",
        mfa_verified=True,
    )
    await get_redis().hset(_key(raw), "last_seen_at", str(time.time() - idle_for))
    return raw


async def _last_seen(raw: str) -> float:
    return float(await get_redis().hget(_key(raw), "last_seen_at"))


async def test_a_background_load_does_not_slide_the_idle_window(
    seeded: dict[str, Any], redis_conn: Any
) -> None:
    raw = await _session(seeded, idle_for=600)
    before = await _last_seen(raw)

    assert await sessions.load(raw, touch=False) is not None, "still signed in"
    assert await _last_seen(raw) == before, "a poll is not activity"

    assert await sessions.load(raw) is not None
    assert await _last_seen(raw) > before, "a real request still is"
    await sessions.destroy(raw)


async def test_a_background_load_still_refuses_an_idle_session(
    seeded: dict[str, Any], redis_conn: Any
) -> None:
    raw = await _session(seeded, idle_for=10_000_000)
    assert await sessions.load(raw, touch=False) is None


def test_the_header_is_the_one_the_console_sends() -> None:
    assert BACKGROUND_HEADER == "X-CMP-Background"
