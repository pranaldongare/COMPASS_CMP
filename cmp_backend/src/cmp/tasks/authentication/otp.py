"""Delivering the codes somebody is waiting for.

All five route to `high_priority`, and that queue exists for exactly this.
Somebody is looking at a code entry box right now; a code queued behind a
document export is a failed sign-in and a support call.

These use `dispatch_required`, not `dispatch_optional` - if the broker is
unreachable the request fails with a 503 rather than returning 200 and leaving
the user waiting for a message that will never arrive.

The words come from `cmp.core.messages`, or from what the office put in their
place; nothing here writes a sentence.
"""

from __future__ import annotations

from typing import Any

from celery import shared_task

from cmp.core.config import settings
from cmp.core.messages import Message
from cmp.infrastructure.messaging import deliver

# Retry on transport failure with exponential backoff and jitter. Without jitter,
# a gateway outage produces a synchronised retry storm the moment it recovers.
RETRY_KW: dict[str, Any] = {
    "autoretry_for": (ConnectionError, TimeoutError, OSError),
    "retry_backoff": 5,
    "retry_backoff_max": 300,
    "retry_jitter": True,
    "max_retries": 5,
    "acks_late": True,
}


@shared_task(name="cmp.notifications.send_mfa_code", **RETRY_KW)
def send_mfa_code(user_uuid: str, email: str, code: str) -> dict[str, Any]:
    return deliver(Message.MFA_CODE, to=email, code=code, minutes=settings.mfa_ttl_s // 60)


@shared_task(name="cmp.notifications.send_login_code", **RETRY_KW)
def send_login_code(user_uuid: str, contact: str, code: str) -> dict[str, Any]:
    return deliver(Message.LOGIN_CODE, to=contact, code=code, minutes=settings.otp_ttl_s // 60)


@shared_task(name="cmp.notifications.send_registration_code", **RETRY_KW)
def send_registration_code(user_uuid: str, contact: str, code: str) -> dict[str, Any]:
    """One per medium given at sign-up: every medium is authenticated."""
    return deliver(
        Message.REGISTRATION_CODE, to=contact, code=code, minutes=settings.otp_ttl_s // 60
    )


@shared_task(name="cmp.notifications.send_consent_code", **RETRY_KW)
def send_consent_code(contact: str, code: str, project_name: str = "") -> dict[str, Any]:
    return deliver(
        Message.CONSENT_CODE,
        to=contact,
        code=code,
        minutes=settings.otp_ttl_s // 60,
        project_name=project_name or "this project",
    )


@shared_task(name="cmp.notifications.send_password_reset", **RETRY_KW)
def send_password_reset(user_uuid: str, email: str, code: str) -> dict[str, Any]:
    return deliver(Message.PASSWORD_RESET, to=email, code=code, minutes=15)
