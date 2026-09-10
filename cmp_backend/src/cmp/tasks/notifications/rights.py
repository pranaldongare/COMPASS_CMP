"""Messages about a rights request.

Every one goes through a junction in `cmp.core.messages`, so the set can be
reviewed and reworded together: an acknowledgement, a verification code,
"your response is ready", the response, a closure with its reasons, the
nomination messages, and the tickets to holders. The codes ride the
high-priority queue with the other one-time codes; the rest are courtesy
messages that must not fail the request that queued them, which is why the
service dispatches them as optional.

What stays here is the arithmetic a template should not have to do: turning
an outcome into a sentence, a day count into "due in 3 days", an optional
window into a clause or nothing.
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

_RIGHT_NAMES = {
    "access": "access request",
    "correction": "correction request",
    "erasure": "erasure request",
    "grievance": "grievance",
}

_RESPONSE_HEADLINES = {
    "complete": "Our response to your request is complete.",
    "partial": (
        "Our response to your request is partial: one or more parties have not returned "
        "what they hold, and the gap is named below."
    ),
    "no_records": (
        "No party beyond the platform itself holds records about you. What the platform "
        "holds is set out below in full."
    ),
}

_CLOSED_HEADLINES = {
    "refused": "we are not able to act on it as a rights request",
    "reclassified_withdrawal": "it has been handled as a withdrawal of consent",
    "not_verified": "we could not verify the identity behind it",
    "upheld": "your grievance has been upheld",
    "not_upheld": "your grievance has not been upheld",
}


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'s' if n != 1 else ''}"


@shared_task(name="cmp.notifications.send_rights_acknowledgement", **RETRY_KW)
def send_rights_acknowledgement(
    contact: str, reference: str, request_type: str, due_on: str, period_days: int
) -> dict[str, Any]:
    return deliver(
        Message.RIGHTS_ACKNOWLEDGEMENT,
        to=contact,
        reference=reference,
        request_kind=_RIGHT_NAMES.get(request_type, "request"),
        due_on=due_on,
        period_days=period_days,
    )


@shared_task(name="cmp.notifications.send_rights_verification_code", **RETRY_KW)
def send_rights_verification_code(contact: str, code: str, reference: str) -> dict[str, Any]:
    return deliver(
        Message.RIGHTS_VERIFICATION_CODE,
        to=contact,
        code=code,
        minutes=settings.otp_ttl_s // 60,
        reference=reference,
    )


@shared_task(name="cmp.notifications.send_nomination_code", **RETRY_KW)
def send_nomination_code(contact: str, code: str) -> dict[str, Any]:
    return deliver(Message.NOMINATION_CODE, to=contact, code=code, minutes=settings.otp_ttl_s // 60)


@shared_task(name="cmp.notifications.send_rights_response_ready", **RETRY_KW)
def send_rights_response_ready(
    contact: str, reference: str, expires_on: str | None
) -> dict[str, Any]:
    return deliver(
        Message.RIGHTS_RESPONSE_READY,
        to=contact,
        reference=reference,
        availability=f"It is available until {expires_on}." if expires_on else "",
    )


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
    """The response itself, in the mail - not a note that it exists.

    The decision, the Privacy Office's words, and the record the platform
    holds about her. The full file is downloaded from her account, where it is
    authenticated and time-limited; the mail carries what a person needs to
    read to know what was answered.
    """
    availability = (
        f"The full record, as a file, is available from your account until {expires_on}: "
        f"{account_url}"
        if expires_on
        else f"The full record is available from your account: {account_url}"
    )
    return deliver(
        Message.RIGHTS_RESPONSE,
        to=contact,
        reference=reference,
        headline=_RESPONSE_HEADLINES.get(outcome, "Our response to your request is below."),
        response_text=response_text,
        digest=digest,
        availability=availability,
    )


@shared_task(name="cmp.notifications.send_rights_closed", **RETRY_KW)
def send_rights_closed(
    contact: str, reference: str, outcome: str, explanation: str
) -> dict[str, Any]:
    return deliver(
        Message.RIGHTS_CLOSED,
        to=contact,
        reference=reference,
        headline=_CLOSED_HEADLINES.get(outcome, "it has been closed"),
        explanation=explanation,
    )


@shared_task(name="cmp.notifications.send_nomination_invitation", **RETRY_KW)
def send_nomination_invitation(
    contact: str, principal_name: str, accept_url: str, expires_on: str
) -> dict[str, Any]:
    return deliver(
        Message.NOMINATION_INVITATION,
        to=contact,
        principal_name=principal_name,
        accept_url=accept_url,
        expires_on=expires_on,
    )


@shared_task(name="cmp.notifications.send_nomination_accepted", **RETRY_KW)
def send_nomination_accepted(
    contact: str,
    principal_name: str,
    reference: str,
    nominee_url: str,
    sign_in_url: str | None = None,
) -> dict[str, Any]:
    return deliver(
        Message.NOMINATION_ACCEPTED,
        to=contact,
        principal_name=principal_name,
        reference=reference,
        nominee_url=nominee_url,
        sign_in_url=sign_in_url or f"{settings.public_base_url.rstrip('/')}/sign-in",
    )


@shared_task(name="cmp.notifications.send_ticket_reminder", **RETRY_KW)
def send_ticket_reminder(
    contact: str, reference: str, holder_label: str, due_on: str, days: int, where: str | None
) -> dict[str, Any]:
    if days > 0:
        timing = f"Due in {_plural(days, 'day')}"
        when = f"is due in {_plural(days, 'day')}, on {due_on}"
    elif days == 0:
        timing = "Due today"
        when = f"is due today, {due_on}"
    else:
        timing = f"Overdue by {_plural(-days, 'day')}"
        when = f"was due on {due_on} and is {_plural(-days, 'day')} overdue"
    return deliver(
        Message.TICKET_REMINDER,
        to=contact,
        reference=reference,
        holder_label=holder_label,
        timing=timing,
        when=when,
        return_route=(
            f"Return it on the portal: {where}"
            if where
            else "Reply to this message with your return."
        ),
    )


@shared_task(name="cmp.notifications.send_ticket_message", **RETRY_KW)
def send_ticket_message(
    contact: str, reference: str, holder_label: str, author: str, body: str, where: str | None
) -> dict[str, Any]:
    return deliver(
        Message.TICKET_MESSAGE,
        to=contact,
        reference=reference,
        holder_label=holder_label,
        author=author,
        message=body,
        return_route=f"Reply on the portal: {where}" if where else "Reply to this message.",
    )


@shared_task(name="cmp.notifications.send_holder_instruction", **RETRY_KW)
def send_holder_instruction(
    contact: str,
    reference: str,
    holder_label: str,
    instruction: str,
    due_on: str,
    brief_text: str = "",
) -> dict[str, Any]:
    return deliver(
        Message.HOLDER_INSTRUCTION,
        to=contact,
        reference=reference,
        holder_label=holder_label,
        instruction=instruction,
        due_on=due_on,
        brief=brief_text,
    )
