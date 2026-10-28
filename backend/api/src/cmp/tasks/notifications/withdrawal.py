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


@shared_task(name="cmp.notifications.send_hr_withdrawal_notice", **RETRY_KW)
def send_hr_withdrawal_notice(
    email: str,
    activity_name: str,
    category_name: str,
    principal_ref: str,
    stopped: list[str],
    continuing: list[str],
    consent_reference: str,
    activity_uuid: str,
) -> dict[str, Any]:
    """One respondent of an HR activity, told a participant withdrew (ADR 0033).

    `principal_ref` may arrive sealed - an employee ID is - and is opened by
    `deliver` with the address, at the one moment it is written into a message.
    """
    return deliver(
        Message.HR_WITHDRAWAL_NOTICE,
        to=email,
        activity_name=activity_name,
        category_name=category_name,
        principal_ref=principal_ref,
        stopped=", ".join(stopped) or "every purpose",
        continuing=", ".join(continuing) or "none",
        consent_reference=consent_reference,
        register_url=(
            f"{settings.console_base_url.rstrip('/')}/hr-activities/{activity_uuid}#consents"
        ),
    )
