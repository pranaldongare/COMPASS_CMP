"""Messages about a rights request.

Six, and every one goes through a template so the set can be reviewed
together: an acknowledgement, a verification code, "your response is ready",
a closure with its reasons, a nomination's invitation, and a ticket to a
holder. The codes ride the high-priority queue with the other one-time codes;
the rest are courtesy messages that must not fail the request that queued
them, which is why the service dispatches them as optional.
"""

from __future__ import annotations

from typing import Any

from celery import shared_task

from cmp.core.logging import get_logger
from cmp.infrastructure.email import build_email_transport, templates
from cmp.infrastructure.sms import build_sms_transport

log = get_logger("cmp.tasks.notifications")

RETRY_KW: dict[str, Any] = {
    "autoretry_for": (ConnectionError, TimeoutError, OSError),
    "retry_backoff": 5,
    "retry_backoff_max": 300,
    "retry_jitter": True,
    "max_retries": 5,
    "acks_late": True,
}


def _deliver(*, to: str, subject: str, body: str) -> dict[str, Any]:
    """Email where the contact is an address, SMS where it is a number."""
    if "@" not in to:
        return dict(build_sms_transport().send(to=to, body=body))
    return dict(build_email_transport().send(to=to, subject=subject, body=body))


@shared_task(name="cmp.notifications.send_rights_acknowledgement", **RETRY_KW)
def send_rights_acknowledgement(
    contact: str, reference: str, request_type: str, due_on: str, period_days: int
) -> dict[str, Any]:
    subject, body = templates.rights_acknowledgement(reference, request_type, due_on, period_days)
    return _deliver(to=contact, subject=subject, body=body)


@shared_task(name="cmp.notifications.send_rights_verification_code", **RETRY_KW)
def send_rights_verification_code(contact: str, code: str, reference: str) -> dict[str, Any]:
    subject, body = templates.rights_verification_code(code, reference)
    return _deliver(to=contact, subject=subject, body=body)


@shared_task(name="cmp.notifications.send_nomination_code", **RETRY_KW)
def send_nomination_code(contact: str, code: str) -> dict[str, Any]:
    subject, body = templates.nomination_code(code)
    return _deliver(to=contact, subject=subject, body=body)


@shared_task(name="cmp.notifications.send_rights_response_ready", **RETRY_KW)
def send_rights_response_ready(
    contact: str, reference: str, expires_on: str | None
) -> dict[str, Any]:
    subject, body = templates.rights_response_ready(reference, expires_on)
    return _deliver(to=contact, subject=subject, body=body)


@shared_task(name="cmp.notifications.send_rights_response", **RETRY_KW)
def send_rights_response(
    contact: str,
    reference: str,
    outcome: str,
    response_text: str,
    digest: str,
    expires_on: str | None,
    account_url: str,
) -> dict[str, Any]:
    subject, body = templates.rights_response(
        reference, outcome, response_text, digest, expires_on, account_url
    )
    return _deliver(to=contact, subject=subject, body=body)


@shared_task(name="cmp.notifications.send_rights_closed", **RETRY_KW)
def send_rights_closed(
    contact: str, reference: str, outcome: str, explanation: str
) -> dict[str, Any]:
    subject, body = templates.rights_closed(reference, outcome, explanation)
    return _deliver(to=contact, subject=subject, body=body)


@shared_task(name="cmp.notifications.send_nomination_invitation", **RETRY_KW)
def send_nomination_invitation(
    contact: str, principal_name: str, accept_url: str, expires_on: str
) -> dict[str, Any]:
    subject, body = templates.nomination_invitation(principal_name, accept_url, expires_on)
    return _deliver(to=contact, subject=subject, body=body)


@shared_task(name="cmp.notifications.send_nomination_accepted", **RETRY_KW)
def send_nomination_accepted(
    contact: str, principal_name: str, reference: str, nominee_url: str
) -> dict[str, Any]:
    subject, body = templates.nomination_accepted(principal_name, reference, nominee_url)
    return _deliver(to=contact, subject=subject, body=body)


@shared_task(name="cmp.notifications.send_ticket_message", **RETRY_KW)
def send_ticket_message(
    contact: str, reference: str, holder_label: str, author: str, body: str, where: str | None
) -> dict[str, Any]:
    subject, text = templates.ticket_message(reference, holder_label, author, body, where)
    return _deliver(to=contact, subject=subject, body=text)


@shared_task(name="cmp.notifications.send_holder_instruction", **RETRY_KW)
def send_holder_instruction(
    contact: str,
    reference: str,
    holder_label: str,
    instruction: str,
    due_on: str,
    brief_text: str = "",
) -> dict[str, Any]:
    subject, body = templates.holder_instruction(
        reference, holder_label, instruction, due_on, brief_text
    )
    return _deliver(to=contact, subject=subject, body=body)
