"""Integration-suite fixtures.

Every integration test gets a Redis connection whether or not it asks for
one. The consent service keeps its record of a notice having been served in
Redis, and a test that walks the flow through the service would otherwise
have to remember to request the fixture - and the one that forgot would fail
with "Redis is not connected" from deep inside `capture`, which reads as a
service bug.

Overrides the root `redis_conn` with the same body so a test that does ask
for it by name gets this one instance rather than a second client.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest


@pytest.fixture(autouse=True)
async def redis_conn() -> AsyncIterator[Any]:
    from cmp.db.redis import close_redis, open_redis

    client = await open_redis()
    # Failed sign-ins count against the address they came from, and every
    # test's requests come from the one address the request context gives.
    # The budget outlives the test transaction; a full run would spend it.
    from cmp.db.redis import K_RATE

    async for k in client.scan_iter(match=f"{K_RATE}:*_fail_ip:127.0.0.1"):
        await client.delete(k)
    try:
        yield client
    finally:
        await close_redis()


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, tuple[Any, ...]]]:
    """What a test queued, by task name and arguments, instead of queueing it."""
    from cmp.tasks import dispatch as dispatch_mod

    out: list[tuple[str, tuple[Any, ...]]] = []

    def capture(task: Any, *args: Any, **kwargs: Any) -> str:
        out.append((task.name.rsplit(".", 1)[-1], args))
        return "queued-in-a-test"

    monkeypatch.setattr(dispatch_mod, "dispatch_optional", capture)
    return out
