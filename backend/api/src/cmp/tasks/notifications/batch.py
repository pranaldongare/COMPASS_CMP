"""Sending one message to many recipients.

Bounded by a soft time limit and reports partial delivery honestly rather than
raising on the first failure - a batch that stops at recipient three has still
delivered to two, and pretending otherwise would have them notified twice on the
retry.
"""

from __future__ import annotations

from typing import Any

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from cmp.core.config import settings
from cmp.core.logging import get_logger
from cmp.core.messages import Message
from cmp.infrastructure.email.transport import obscure
from cmp.infrastructure.messaging import deliver

log = get_logger("cmp.tasks.notifications")

RETRY_KW: dict[str, Any] = {
    "autoretry_for": (ConnectionError, TimeoutError, OSError),
    "retry_backoff": 5,
    "retry_backoff_max": 300,
    "retry_jitter": True,
    "max_retries": 5,
    "acks_late": True,
}


@shared_task(name="cmp.notifications.send_office_note", bind=True, **RETRY_KW)
def send_office_note(
    self: Any, recipients: list[str], event: str, occurred_on: str
) -> dict[str, Any]:
    """A notification resent by the office, to one person or several.

    Partial failure is reported rather than retried wholesale: retrying the whole
    batch would re-deliver to everyone who already received it.
    """
    delivered, failed = 0, []
    try:
        for address in recipients:
            try:
                deliver(
                    Message.OFFICE_NOTE,
                    to=address,
                    event=event,
                    occurred_on=occurred_on,
                    console_url=settings.console_base_url.rstrip("/"),
                )
                delivered += 1
            except (ConnectionError, TimeoutError, OSError) as exc:
                failed.append({"to": obscure(address), "error": type(exc).__name__})
    except SoftTimeLimitExceeded:
        log.warning(
            "notification.batch_timed_out",
            delivered=delivered,
            remaining=len(recipients) - delivered,
        )
        raise

    if failed:
        log.warning("notification.batch_partial", delivered=delivered, failed=len(failed))
    return {"delivered": delivered, "failed": failed}
