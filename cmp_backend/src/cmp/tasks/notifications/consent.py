"""Her copy of a consent record.

A receipt is not a courtesy; it is the subject's copy of the evidence. It
carries the artefact reference so she can quote it when exercising a right,
and lists the purposes individually: "you agreed to 3 purposes" is not a
record of what somebody agreed to, and this message is often the only copy
they keep.
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


@shared_task(name="cmp.notifications.send_consent_receipt", **RETRY_KW)
def send_consent_receipt(
    contact: str, consent_uuid: str, project_name: str, purposes: list[str] | None = None
) -> dict[str, Any]:
    names = list(purposes or [])
    return deliver(
        Message.CONSENT_RECEIPT,
        to=contact,
        project_name=project_name,
        reference=consent_uuid,
        purposes="\n".join(f"  - {name}" for name in names) or "  (the purposes on the notice)",
        purpose_count=len(names) if names else "the",
        withdraw_url=f"{settings.public_base_url.rstrip('/')}/my-consents",
    )
