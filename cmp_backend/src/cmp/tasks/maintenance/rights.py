"""The daily pass over rights requests.

Two things, both of which a person would otherwise have to remember:

* A request from the public form whose contact never verified is closed as
  unverified after a grace period, and audited. The neutral reply the
  requester received said nothing either way; the record should.
* A retained item whose retention floor has passed is noted, so the erasure
  the floor deferred reaches the DPO's queue rather than waiting for somebody
  to re-read an old response.

Nothing here erases. The floor passing is a fact the sweep records; applying
the erasure is a decision the DPO makes, from the queue, with the trail intact.
"""

from __future__ import annotations

import asyncio
from typing import Any

from celery import shared_task

from cmp.auth.rate_limit import service as ratelimit
from cmp.core.logging import get_logger
from cmp.db.pool import close_pool, open_pool, transaction
from cmp.db.redis import close_redis, open_redis

log = get_logger("cmp.tasks.maintenance")


def _run(coro: Any) -> Any:
    import sys

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def wrapper() -> Any:
        await open_pool()
        await open_redis()
        try:
            return await coro()
        finally:
            await close_redis()
            await close_pool()

    return asyncio.run(wrapper())


@shared_task(name="cmp.maintenance.sweep_rights_requests", acks_late=True)
def sweep_rights_requests() -> dict[str, Any]:
    async def work() -> dict[str, Any]:
        async with ratelimit.lock("sweep_rights_requests", ttl_s=300) as acquired:
            if not acquired:
                log.info("maintenance.skipped", task="sweep_rights_requests")
                return {"skipped": True}

            from cmp.core.context import RequestContext, use_context
            from cmp.domain.rights import service

            with use_context(RequestContext(request_id="beat:sweep_rights_requests")):
                async with transaction() as conn:
                    result = await service.sweep(conn)
            log.info("maintenance.rights_swept", **result)
            return dict(result)

    return _run(work)
