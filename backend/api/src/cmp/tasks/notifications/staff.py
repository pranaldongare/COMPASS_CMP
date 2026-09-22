"""Messages to a person about what an administrator did to their account.

Distinct from `tasks.authentication` even though both of these carry a code.
Those exist because somebody is looking at a code box right now, which is why
they are urgent and required. An invitation, or word that a mobile was put on
your account, is read when its recipient next looks at their phone or mail, so
both go on the `notifications` queue and must never fail the request that
wrote the row: the row is committed, and telling an administrator it was not
would be false.

The cost of that choice is that a dropped message is invisible to the person it
was for, so `POST /users/{uuid}/invite` sends the invitation again and the
account page's "Send a code" replaces the other.
"""

from __future__ import annotations

from typing import Any

from celery import shared_task

from cmp.core.messages import Message
from cmp.infrastructure.dkms.client import DkmsUnavailable
from cmp.infrastructure.messaging import deliver

RETRY_KW: dict[str, Any] = {
    # `DkmsUnavailable` among them: every message opens a sealed recipient
    # before it can be addressed, so a key service that blinks would
    # otherwise lose the code outright rather than send it a moment later.
    "autoretry_for": (ConnectionError, TimeoutError, OSError, DkmsUnavailable),
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


@shared_task(name="cmp.notifications.send_contact_added_for_you", **RETRY_KW)
def send_contact_added_for_you(
    user_uuid: str, contact: str, code: str, hours: int
) -> dict[str, Any]:
    """A contact an administrator has just put on somebody's account.

    The person did not ask for this message and is not waiting at a code box,
    so the code lasts hours, like an invitation, and the message says what
    happened before it says what to do.
    """
    return deliver(Message.CONTACT_ADDED_FOR_YOU, to=contact, code=code, hours=hours)
