"""Messages to a member of staff about their own account.

Distinct from `tasks.authentication` even though this one carries a code.
Those five exist because somebody is looking at a code box right now, which is
why they are urgent and required. An invitation is read when its recipient next
opens their mail, so it goes on the `notifications` queue and must never fail
the request that provisioned the account: the account is written and committed,
and telling an administrator it was not created would be false.

The cost of that choice is that a dropped invitation is invisible to the person
waiting for it, so `POST /users/{uuid}/invite` exists to send it again.
"""

from __future__ import annotations

from typing import Any

from celery import shared_task

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


@shared_task(name="cmp.notifications.send_staff_invitation", **RETRY_KW)
def send_staff_invitation(
    user_uuid: str,
    email: str,
    full_name: str,
    role_title: str,
    code: str,
    reset_url: str,
    hours: int,
) -> dict[str, Any]:
    """Tell somebody an account exists for them, and how to set its password."""
    return deliver(
        Message.STAFF_INVITATION,
        to=email,
        full_name=full_name,
        role_title=role_title,
        code=code,
        reset_url=reset_url,
        hours=hours,
    )
