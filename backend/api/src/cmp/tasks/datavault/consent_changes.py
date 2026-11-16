"""Telling DataVault of consent changes, unattended (0071).

Two tasks, both on the `default` queue:

* `deliver_consent_changes` - every minute, and straight after a consent is
  saved: read the consents not read yet and queue what DataVault must hear,
  then deliver every message that is due.
* `queue_consent_lapses` - nightly, after the retention sweep: queue a message
  for each consent with a purpose whose validity has run out since DataVault
  was last told, a page at a time until none is left. The minute's run
  delivers them.

Each chain is read, and each answer written, in a transaction of its own; no
transaction is open while DataVault is waited on. A chain or a message that
cannot be worked is logged and passed over, so that one bad row does not stop
every other; the next run meets it again. One run at a time: a second one
started meanwhile finds the lock taken and leaves, and the next minute's
picks up whatever it would have found. With consent changes switched off both
do nothing at all.

A worker may be the only one there is, sending sign-in codes too. So a run
that finds DataVault not answering stops delivering at once, and the runs of
the next minute - however many consents are saved in it - deliver nothing
(`PAUSE`): DataVault is waited on for one try a minute at most while it is
down. Reading consents and queueing messages go on meanwhile.
"""

from __future__ import annotations

from typing import Any

from celery import shared_task

from cmp.auth.rate_limit import service as ratelimit
from cmp.core.logging import get_logger
from cmp.db.pool import across_offices, connection, transaction
from cmp.tasks.maintenance.rights import _run

log = get_logger("cmp.tasks.datavault")

#: Set when DataVault did not answer: no run delivers while it stands.
PAUSE = "datavault_consent_changes_paused"
PAUSE_S = 60


@shared_task(name="cmp.datavault.deliver_consent_changes", acks_late=True)
def deliver_consent_changes() -> dict[str, Any]:
    async def work() -> dict[str, Any]:
        from cmp.core.context import RequestContext, use_context
        from cmp.db.redis import K_LOCK, get_redis, key
        from cmp.domain.datavault import connection as settings
        from cmp.domain.datavault import consent_changes as changes
        from cmp.infrastructure.datavault import ChangeResult

        async with ratelimit.lock("datavault_consent_changes", ttl_s=300) as acquired:
            if not acquired:
                return {"skipped": True}
            with use_context(RequestContext(request_id="task:datavault_consent_changes")):
                async with connection() as conn, across_offices(conn):
                    link = await settings.for_consent_changes(conn)
                    if link is None:
                        return {"off": True}
                    chains = await changes.unread(conn, link)
                queued = broken = 0
                for c in chains:
                    try:
                        async with transaction() as conn, across_offices(conn):
                            queued += await changes.note_chain(
                                conn,
                                link,
                                user_id=int(c["auth_user_id"]),
                                notice_id=int(c["notice_id"]),
                            )
                    except Exception as failed_on:
                        broken += 1
                        log.error(
                            "datavault.consent_chain_unread",
                            first_unread=int(c["first_unread"]),
                            error=type(failed_on).__name__,
                        )
                done: dict[str, Any] = {"read": len(chains), "queued": queued}
                redis = get_redis()
                pause = key(K_LOCK, PAUSE)
                if await redis.exists(pause):
                    return {**done, "broken": broken, "paused": True}
                async with connection() as conn, across_offices(conn):
                    rows = await changes.due(conn)

                async def record(row: dict[str, Any], answer: ChangeResult | str) -> None:
                    async with transaction() as conn, across_offices(conn):
                        if isinstance(answer, str):
                            await changes.undelivered(conn, row, failure=answer)
                        else:
                            await changes.delivered(conn, row, answer)

                outcome = await changes.deliver(link, rows, record=record)
                if outcome["paused"]:
                    await redis.set(pause, "1", ex=PAUSE_S)
            return {**done, **outcome, "broken": broken + int(outcome["broken"])}

    result: dict[str, Any] = _run(work)
    if result.get("queued") or result.get("delivered") or result.get("failed"):
        log.info("datavault.consent_changes", **result)
    return result


@shared_task(name="cmp.datavault.queue_consent_lapses", acks_late=True)
def queue_consent_lapses() -> dict[str, Any]:
    async def work() -> dict[str, Any]:
        from cmp.core.context import RequestContext, use_context
        from cmp.domain.datavault import connection as settings
        from cmp.domain.datavault import consent_changes as changes

        async with ratelimit.lock("datavault_consent_lapses", ttl_s=3600) as acquired:
            if not acquired:
                return {"skipped": True}
            with use_context(RequestContext(request_id="beat:datavault_consent_lapses")):
                async with connection() as conn, across_offices(conn):
                    link = await settings.for_consent_changes(conn)
                if link is None:
                    return {"off": True}
                found = queued = broken = 0
                after_id = 0
                for _ in range(changes.LAPSE_PAGES):
                    async with connection() as conn, across_offices(conn):
                        page = await changes.lapsed(conn, link, after_id=after_id)
                    if not page:
                        break
                    found += len(page)
                    for row in page:
                        try:
                            async with transaction() as conn, across_offices(conn):
                                queued += await changes.note_lapse(conn, link, row)
                        except Exception as failed_on:
                            broken += 1
                            log.error(
                                "datavault.consent_lapse_unread",
                                consent=int(row["consent_id"]),
                                error=type(failed_on).__name__,
                            )
                    after_id = int(page[-1]["consent_id"])
                    if len(page) < changes.LAPSE_PAGE:
                        break
            return {"lapsed": found, "queued": queued, "broken": broken}

    result: dict[str, Any] = _run(work)
    log.info("datavault.consent_lapses", **result)
    return result
