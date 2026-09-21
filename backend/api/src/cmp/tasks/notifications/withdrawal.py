"""Confirming a withdrawal.

Says what stopped and what did not, because the distinction is the one people
get wrong: withdrawing stops future processing for those purposes, and does not
by itself delete what was already collected. Erasure is a separate request, and
the message says so rather than letting somebody assume.
"""

from __future__ import annotations

from typing import Any

from celery import shared_task

from cmp.core.config import settings
from cmp.core.messages import Message
from cmp.infrastructure.messaging import deliver

RETRY_KW: dict[str, Any] = {
    "autoretry_for": (ConnectionError, TimeoutError, OSError),
    "retry_backoff": 5,
    "retry_backoff_max": 300,
    "retry_jitter": True,
    "max_retries": 5,
    "acks_late": True,
}


@shared_task(name="cmp.notifications.send_withdrawal_confirmation", **RETRY_KW)
def send_withdrawal_confirmation(
    contact: str, consent_uuid: str, stopped: list[str], continuing: list[str]
) -> dict[str, Any]:
    return deliver(
        Message.WITHDRAWAL_CONFIRMATION,
        to=contact,
        reference=consent_uuid,
        stopped=", ".join(stopped) or "every purpose",
        continuing=", ".join(continuing),
        continuing_note=(
            "Still in force: " + ", ".join(continuing) + "."
            if continuing
            else "Nothing on this notice continues under your consent."
        ),
        rights_url=f"{settings.public_base_url.rstrip('/')}/rights",
    )
