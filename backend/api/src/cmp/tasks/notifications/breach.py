"""Notices to the people a breach affected, by email and SMS (S3-03).

One task per queued delivery. It sends the approved words through the
`breach_notice` junction and records what happened on the delivery record -
`delivered`, or `failed` with the error's class once the retries are spent -
and then re-reads the principals' duty, which completes when every listed
person has an outcome on every channel.

A transport or key-service failure is retried, five times from five seconds
and doubling, like every message here. A failure no retry will mend - a
contact that cannot be opened, or none at all - is recorded at once. Either
way the record says it failed rather than the message being lost: Rule
7(2)(b)(vi) asks for the account of notices, and a silent drop would make
that account wrong.

A delivery can have two tasks: Send again queues a lost one a second time, and
when the workers come back from an outage both start together. Reading that no
outcome is recorded does not stop that, so each task claims what it sends to
in Redis first. A task that loses stands down and records nothing, since the
winner will; the outcome is read again under the claim, so nothing is sent once
it is recorded.

A worker killed mid-task is not a second sender. Its message comes back under
the same task id, and takes its own claim back: standing down there would leave
a mail unsent with nothing left to send it. The cost is the one every task here
accepts, a second copy, for a kill that came after the send, or a broker
connection lost in the middle of one, when the message comes back while the
first run is still going. A claim nobody comes back for runs out by itself, and
a Send again pressed before it does stands down with it.
"""

from __future__ import annotations

import asyncio
from typing import Any, Final

from celery import shared_task
from redis.exceptions import RedisError

from cmp.core.logging import get_logger
from cmp.core.messages import Message
from cmp.db.pool import close_pool, open_pool, transaction
from cmp.infrastructure.dkms.client import DkmsUnavailable
from cmp.infrastructure.messaging import _redis, deliver

log = get_logger("cmp.tasks.breach")

#: Worth trying again: the transport, the key service or the claim's store may
#: be back.
RETRYABLE = (ConnectionError, TimeoutError, OSError, DkmsUnavailable, RedisError)
MAX_RETRIES = 5

#: Above `task_time_limit`, so a running task never outlives its claim, and
#: below `STALE_AFTER`, so a task that started on time and died has let go by
#: the time its delivery reads as held up.
CLAIM_TTL_S: Final = 660


def _run(coro: Any) -> Any:
    import sys

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def wrapper() -> Any:
        await open_pool()
        try:
            return await coro()
        finally:
            await close_pool()

    return asyncio.run(wrapper())


def take_claim(key: str, owner: str) -> bool:
    """Whether the task `owner` names may send: nobody holds the claim, or it
    does already and has come back. A Redis error is a retryable failure, not a
    send: without a claim there is no telling who else is sending."""
    client = _redis()
    return bool(client.set(key, owner, nx=True, ex=CLAIM_TTL_S)) or client.get(key) == owner


def keep_claim(key: str, ttl_s: int) -> None:
    """Hold on past the run: its mail has gone and is not on the record yet."""
    try:
        _redis().expire(key, ttl_s)
    except RedisError as exc:
        log.warning("breach.claim_not_kept", error=type(exc).__name__)


def drop_claim(key: str) -> None:
    """For the retry, or the next attempt. If this cannot be done the claim
    runs out by itself."""
    try:
        _redis().delete(key)
    except RedisError as exc:
        log.warning("breach.claim_not_dropped", error=type(exc).__name__)


def _claim(delivery_uuid: str, owner: str) -> str | None:
    """This delivery's claim once taken, or None: nothing to send, or another
    task has it."""
    from cmp.domain.breach import notices

    async def work() -> str | None:
        async with transaction() as conn:
            return await notices.claim_key(conn, delivery_uuid)

    key: str | None = _run(work)
    return key if key and take_claim(key, owner) else None


def _job(delivery_uuid: str) -> dict[str, Any] | None:
    from cmp.domain.breach import notices

    async def work() -> dict[str, Any] | None:
        async with transaction() as conn:
            return await notices.job(conn, delivery_uuid)

    result: dict[str, Any] | None = _run(work)
    return result


def _record(delivery_uuid: str, status: str, detail: dict[str, Any]) -> None:
    from cmp.core.context import RequestContext, use_context
    from cmp.domain.breach import notices

    async def work() -> None:
        with use_context(RequestContext(request_id=f"task:breach_notice:{delivery_uuid}")):
            async with transaction() as conn:
                await notices.record_result(
                    conn, delivery_uuid=delivery_uuid, status=status, detail=detail
                )

    _run(work)


@shared_task(
    bind=True, name="cmp.notifications.send_breach_notice", max_retries=MAX_RETRIES, acks_late=True
)
def send_breach_notice(self: Any, delivery_uuid: str) -> dict[str, Any]:
    held: str | None = None
    sent = False
    try:
        held = _claim(delivery_uuid, self.request.id)
        if held is None:
            return {"skipped": True}
        job = _job(delivery_uuid)
        if job is None:
            return {"skipped": True}
        contact = job["email"] if job["channel"] == "email" else job["mobile"]
        if not contact:
            # The contact was removed between the send and now.
            _record(delivery_uuid, "failed", {"error": "NoContact", "attempts": 1})
            return {"failed": "NoContact"}
        words = {
            "breach_reference": job["reference"],
            "what_happened": job["what_happened"],
            "consequences": job["consequences"],
            "measures": job["measures"],
            "protective_steps": job["protective_steps"],
            "contact": job["contact"],
        }
        if job.get("contact_id"):
            # Somebody with no account (0045) is told in full, with no account
            # to point to.
            deliver(Message.BREACH_NOTICE_DIRECT, to=contact, **words)
        else:
            deliver(Message.BREACH_NOTICE, to=contact, **words)
        sent = True
    except RETRYABLE as exc:
        tries = int(self.request.retries) + 1
        if tries > MAX_RETRIES:
            _record(delivery_uuid, "failed", {"error": type(exc).__name__, "attempts": tries})
            return {"failed": type(exc).__name__}
        raise self.retry(exc=exc, countdown=min(300, 5 * 2**self.request.retries)) from exc
    except Exception as exc:
        log.error("breach.notice_failed", delivery=delivery_uuid, error=type(exc).__name__)
        _record(delivery_uuid, "failed", {"error": type(exc).__name__, "attempts": 1})
        return {"failed": type(exc).__name__}
    finally:
        # Kept once it has gone: the claim runs out, and until then a task that
        # read before the outcome was recorded still stands down.
        if held and not sent:
            drop_claim(held)
    _record(delivery_uuid, "delivered", {})
    return {"delivered": True}
