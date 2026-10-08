"""Her copy of a consent record.

A receipt is not a courtesy; it is the subject's copy of the evidence. It
carries the artefact reference so she can quote it when exercising a right,
and lists the purposes individually: "you agreed to 3 purposes" is not a
record of what somebody agreed to, and this message is often the only copy
they keep.

Since 2026-10-08 the receipt also carries her record as a file,
`consent-record.txt`: what she agreed to and refused, when, by which action,
against which notice version and language, and the fingerprint of the exact
text she was shown - hers to keep, so a file of it is no disclosure.
"""

from __future__ import annotations

from typing import Any

from celery import shared_task

from cmp.core.config import settings
from cmp.core.messages import Message
from cmp.infrastructure.dkms.client import DkmsUnavailable
from cmp.infrastructure.email import Attachment
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


@shared_task(name="cmp.notifications.send_consent_receipt", **RETRY_KW)
def send_consent_receipt(
    contact: str,
    consent_uuid: str,
    project_name: str,
    purposes: list[str] | None = None,
    record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    names = list(purposes or [])
    files = [consent_record(consent_uuid, project_name, names, record)] if record else []
    return deliver(
        Message.CONSENT_RECEIPT,
        to=contact,
        # By email only: `deliver` leaves it off a text message.
        attachments=files,
        project_name=project_name,
        reference=consent_uuid,
        purposes="\n".join(f"  - {name}" for name in names) or "  (the purposes on the notice)",
        purpose_count=len(names) if names else "the",
        withdraw_url=f"{settings.public_base_url.rstrip('/')}/my-consents",
    )


def consent_record(
    consent_uuid: str, project_name: str, granted: list[str], record: dict[str, Any]
) -> Attachment:
    """Her consent record as a file to keep. No contact, no name: the record,
    not the person."""
    refused = list(record.get("refused") or [])
    lines = [
        f"{settings.organisation_name} - your consent record",
        "",
        f"Reference:   {consent_uuid}",
        f"Project:     {project_name}",
        f"Notice:      {record.get('notice', '')} ({record.get('language', '')})",
        f"Recorded at: {record.get('at', '')}",
        f"How:         {str(record.get('action', '')).replace('_', ' ')}",
        "",
        "You agreed to:",
        *([f"  - {n}" for n in granted] or ["  (nothing)"]),
        "",
        "You did not agree to:",
        *([f"  - {n}" for n in refused] or ["  (nothing)"]),
        "",
        "Fingerprint of the notice text you were shown (SHA-256):",
        f"  {record.get('sha256', '')}",
        "",
        "You can withdraw at any time from your account:",
        f"  {settings.public_base_url.rstrip('/')}/my-consents",
        "",
    ]
    return Attachment("consent-record.txt", "text/plain", "\n".join(lines).encode("utf-8"))
