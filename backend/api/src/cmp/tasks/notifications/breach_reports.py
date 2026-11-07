"""A report on a breach, mailed to the organisation's board (0059).

One task per address, recording what happened on the delivery - `delivered`, or
`failed` with the error's class once the retries are spent - as a notice to a
principal does (`breach.py`), so the office can see who has not been reached.
The report is read from its row when the task runs and travels in no message
to the broker: its words and its PDF are made here, so opening them is retried
like the sending. An address taken off the list by then is recorded failed and
not mailed; one added for that report alone is never taken off. The words are
quoted in the mail: what the office wrote, and a stranger before it, becomes no
button or link. Nothing here goes to a regulator.

Each task claims the report and the address before it sends, as a notice's does
(`breach.py`). The claim is on the address and not the delivery, because a lost
delivery is queued again under a new uuid.

**A mail that has gone is never sent again to get it on the record.** What
follows `deliver` is only recording, so if that fails it is left to
`record_breach_report_result`, which retries the recording and nothing else,
while the claim is kept for it. The account is written first and committed, and
the board's duty is re-read after it in a transaction of its own, so a key
service that cannot open a name for the duty cannot undo the account of a mail.
If the re-read still fails, Try again runs it for an `org_board` report.
"""

from __future__ import annotations

from typing import Any, Final

from celery import shared_task

from cmp.core.logging import get_logger
from cmp.core.messages import Message
from cmp.db.pool import transaction
from cmp.domain.breach.reports import Kind
from cmp.infrastructure.email import Attachment, quoted
from cmp.infrastructure.messaging import deliver
from cmp.tasks.dispatch import dispatch_optional
from cmp.tasks.notifications.breach import (
    MAX_RETRIES,
    RETRYABLE,
    _run,
    drop_claim,
    keep_claim,
    take_claim,
)

log = get_logger("cmp.tasks.breach_reports")

#: About a quarter of an hour, from five seconds, doubling, at most five
#: minutes: what a lock held by a long upload or a key-service blip needs.
RECORD_RETRIES: Final = 8

#: Longer than the recording is retried, so Try again finds the claim held and
#: stands down rather than mailing the person again.
CLAIM_KEPT_S: Final = 3600


def _claim(delivery_uuid: str, owner: str) -> str | None:
    """This delivery's claim once taken, or None: nothing to send, or another
    task has it."""
    from cmp.domain.breach import reports

    async def work() -> str | None:
        async with transaction() as conn:
            return await reports.claim_key(conn, delivery_uuid)

    key: str | None = _run(work)
    return key if key and take_claim(key, owner) else None


def _job(delivery_uuid: str) -> dict[str, Any] | None:
    from cmp.domain.breach import reports

    async def work() -> dict[str, Any] | None:
        async with transaction() as conn:
            return await reports.job(conn, delivery_uuid)

    result: dict[str, Any] | None = _run(work)
    return result


async def _recording(delivery_uuid: str, status: str, detail: dict[str, Any]) -> None:
    """The account, then the duty, each committed by itself."""
    from cmp.core.context import RequestContext, use_context
    from cmp.domain.breach import reports

    with use_context(RequestContext(request_id=f"task:breach_report:{delivery_uuid}")):
        async with transaction() as conn:
            await reports.record_result(
                conn, delivery_uuid=delivery_uuid, status=status, detail=detail
            )
        async with transaction() as conn:
            await reports.settle(conn, delivery_uuid=delivery_uuid)


def _record(delivery_uuid: str, status: str, detail: dict[str, Any]) -> None:
    async def work() -> None:
        await _recording(delivery_uuid, status, detail)

    _run(work)


def _outcome(delivery_uuid: str, status: str, detail: dict[str, Any]) -> bool:
    """Record an outcome, or leave it to the task that retries that alone.
    Whether it is on the record."""
    try:
        _record(delivery_uuid, status, detail)
    except Exception as exc:
        log.error(
            "breach.report_unrecorded",
            delivery=delivery_uuid,
            status=status,
            error=type(exc).__name__,
        )
        dispatch_optional(record_breach_report_result, delivery_uuid, status, detail)
        return False
    return True


@shared_task(
    bind=True, name="cmp.notifications.send_breach_report", max_retries=MAX_RETRIES, acks_late=True
)
def send_breach_report(self: Any, delivery_uuid: str) -> dict[str, Any]:
    held: str | None = None
    sent = False
    try:
        held = _claim(delivery_uuid, self.request.id)
        if held is None:
            return {"skipped": True}
        # Read under the claim: a task that held it may have finished since.
        job = _job(delivery_uuid)
        if job is None:
            return {"skipped": True}
        if job["removed"]:
            _outcome(delivery_uuid, "failed", {"error": "RecipientRemoved", "attempts": 1})
            return {"failed": "RecipientRemoved"}
        words = {
            "to": job["email"],
            "attachments": [Attachment(job["file_name"], "application/pdf", job["pdf"])],
            "breach_reference": job["reference"],
            "report_title": job["report_title"],
            "report_text": quoted(job["report_text"]),
        }
        if job["kind"] == Kind.ORG_BOARD:
            deliver(Message.BREACH_BOARD_REPORT, **words)
        else:
            deliver(Message.BREACH_REPORT_FINALISED, **words)
        sent = True
    except RETRYABLE as exc:
        tries = int(self.request.retries) + 1
        if tries > MAX_RETRIES:
            _outcome(delivery_uuid, "failed", {"error": type(exc).__name__, "attempts": tries})
            return {"failed": type(exc).__name__}
        raise self.retry(exc=exc, countdown=min(300, 5 * 2**self.request.retries)) from exc
    except Exception as exc:
        log.error("breach.report_failed", delivery=delivery_uuid, error=type(exc).__name__)
        _outcome(delivery_uuid, "failed", {"error": type(exc).__name__, "attempts": 1})
        return {"failed": type(exc).__name__}
    finally:
        # Kept once it has gone: the claim runs out, and until then a task that
        # read before the outcome was recorded still stands down.
        if held and not sent:
            drop_claim(held)
    if not _outcome(delivery_uuid, "delivered", {}) and held:
        keep_claim(held, CLAIM_KEPT_S)
    return {"delivered": True}


@shared_task(
    bind=True,
    name="cmp.notifications.record_breach_report_result",
    max_retries=RECORD_RETRIES,
    acks_late=True,
)
def record_breach_report_result(
    self: Any, delivery_uuid: str, status: str, detail: dict[str, Any]
) -> dict[str, Any]:
    """An outcome, and only that: this never goes back through `deliver`. An
    outcome already there is left as it is and the duty is still re-read, so it
    may run as often as it has to."""
    try:
        _record(delivery_uuid, status, detail)
    except Exception as exc:
        log.error(
            "breach.report_unrecorded",
            delivery=delivery_uuid,
            status=status,
            error=type(exc).__name__,
        )
        raise self.retry(exc=exc, countdown=min(300, 5 * 2**self.request.retries)) from exc
    return {"recorded": status}
