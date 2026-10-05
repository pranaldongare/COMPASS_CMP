"""Telling a member of staff a breach ticket is waiting (S3-08).

One message, and it says nothing about the breach: no reference, no title, no
words from the ticket (BD-18). Whoever opens it signs in to the console, where
the ticket is. Kept apart from `breach.py`, which sends the principals' notice
and nothing else - a source test holds each to its one junction.

The address and the name are passed sealed and opened here, at `deliver()`,
like every other message: plaintext never sits in the broker.
"""

from __future__ import annotations

from typing import Any

from celery import shared_task

from cmp.core.config import settings
from cmp.core.messages import Message
from cmp.infrastructure.messaging import deliver
from cmp.tasks.notifications.rights import RETRY_KW


@shared_task(name="cmp.notifications.send_breach_ticket_waiting", **RETRY_KW)
def send_breach_ticket_waiting(email: str, full_name: str) -> dict[str, Any]:
    return deliver(
        Message.BREACH_TICKET_WAITING,
        to=email,
        full_name=full_name,
        console_url=f"{settings.console_base_url.rstrip('/')}/tickets",
    )
