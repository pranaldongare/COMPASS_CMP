"""Messages about a report from the public link (0058).

The reporter's code, the word to them that it arrived, and the word to the
office. The office's says a report has come and nothing of what it says. Every
address and name travels sealed and is opened at `deliver()`, like every other
message: plaintext never sits in the broker.
"""

from __future__ import annotations

from typing import Any

from celery import shared_task

from cmp.core.config import settings
from cmp.core.messages import Message
from cmp.infrastructure.messaging import deliver
from cmp.tasks.notifications.rights import RETRY_KW


@shared_task(name="cmp.notifications.send_incident_report_code", **RETRY_KW)
def send_incident_report_code(email: str, code: str) -> dict[str, Any]:
    return deliver(
        Message.INCIDENT_REPORT_CODE, to=email, code=code, minutes=settings.otp_ttl_s // 60
    )


@shared_task(name="cmp.notifications.send_incident_report_received", **RETRY_KW)
def send_incident_report_received(email: str, full_name: str, reference: str) -> dict[str, Any]:
    return deliver(
        Message.INCIDENT_REPORT_RECEIVED,
        to=email,
        full_name=full_name,
        incident_reference=reference,
    )


@shared_task(name="cmp.notifications.send_incident_reported", **RETRY_KW)
def send_incident_reported(email: str, reference: str, received_at: str) -> dict[str, Any]:
    return deliver(
        Message.INCIDENT_REPORTED,
        to=email,
        incident_reference=reference,
        received_at=received_at,
        breaches_url=f"{settings.console_base_url.rstrip('/')}/breaches",
    )
