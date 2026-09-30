"""Notices to the people a breach touched, by email and SMS (S3-03).

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
"""

from __future__ import annotations

import asyncio
from typing import Any

from celery import shared_task

from cmp.core.logging import get_logger
from cmp.core.messages import Message
from cmp.db.pool import close_pool, open_pool, transaction
from cmp.infrastructure.dkms.client import DkmsUnavailable
from cmp.infrastructure.messaging import deliver

log = get_logger("cmp.tasks.breach")

#: Worth trying again: the transport or the key service may be back.
RETRYABLE = (ConnectionError, TimeoutError, OSError, DkmsUnavailable)
MAX_RETRIES = 5


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
    job = _job(delivery_uuid)
    if job is None:
        return {"skipped": True}
    contact = job["email"] if job["channel"] == "email" else job["mobile"]
    if not contact:
        # The contact was removed between the send and now.
        _record(delivery_uuid, "failed", {"error": "NoContact", "attempts": 1})
        return {"failed": "NoContact"}
    try:
        deliver(
            Message.BREACH_NOTICE,
            to=contact,
            breach_reference=job["reference"],
            what_happened=job["what_happened"],
            consequences=job["consequences"],
            measures=job["measures"],
            protective_steps=job["protective_steps"],
            contact=job["contact"],
        )
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
    _record(delivery_uuid, "delivered", {})
    return {"delivered": True}
