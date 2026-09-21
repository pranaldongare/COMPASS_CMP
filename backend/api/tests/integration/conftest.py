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
    try:
        yield client
    finally:
        await close_redis()
