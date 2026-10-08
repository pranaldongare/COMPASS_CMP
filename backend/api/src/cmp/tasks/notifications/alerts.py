"""The office's and staff's own emails about their work (2026-10-08).

A project waiting for approval, approved, sent back or closed; a collector
named; a rights request arriving, falling due or about the DPO; a breach duty
falling due; a breach ticket answered; a role changed, console access ended,
cover arranged. Before, staff saw these only in the console's bell, if they
looked.

Each task sends one junction to one address, passed sealed and opened at
`deliver()` like every other message, so no plaintext sits in the broker. The
domain fans out - one task per recipient - after its transaction commits
(`cmp.domain.notifications`). Copies are the office's choice per message, in
Message templates.
"""

from __future__ import annotations

from typing import Any

from celery import shared_task

from cmp.core.config import settings
from cmp.core.messages import Message
from cmp.infrastructure.messaging import deliver
from cmp.tasks.notifications.rights import RETRY_KW


def console(path: str) -> str:
    return f"{settings.console_base_url.rstrip('/')}{path}"


@shared_task(name="cmp.notifications.send_project_submitted", **RETRY_KW)
def send_project_submitted(
    to: str, project_name: str, submitted_by: str, project_uuid: str
) -> dict[str, Any]:
    return deliver(
        Message.PROJECT_SUBMITTED,
        to=to,
        project_name=project_name,
        submitted_by=submitted_by,
        project_url=console(f"/projects/{project_uuid}"),
    )


@shared_task(name="cmp.notifications.send_project_approved", **RETRY_KW)
def send_project_approved(
    to: str, full_name: str, project_name: str, project_uuid: str
) -> dict[str, Any]:
    return deliver(
        Message.PROJECT_APPROVED,
        to=to,
        full_name=full_name,
        project_name=project_name,
        project_url=console(f"/projects/{project_uuid}"),
    )


@shared_task(name="cmp.notifications.send_project_sent_back", **RETRY_KW)
def send_project_sent_back(
    to: str, full_name: str, project_name: str, project_uuid: str, reason: str
) -> dict[str, Any]:
    return deliver(
        Message.PROJECT_SENT_BACK,
        to=to,
        full_name=full_name,
        project_name=project_name,
        reason=reason or "-",
        project_url=console(f"/projects/{project_uuid}"),
    )


@shared_task(name="cmp.notifications.send_project_closed", **RETRY_KW)
def send_project_closed(
    to: str, full_name: str, project_name: str, project_uuid: str, reason: str
) -> dict[str, Any]:
    return deliver(
        Message.PROJECT_CLOSED,
        to=to,
        full_name=full_name,
        project_name=project_name,
        reason=reason or "-",
        project_url=console(f"/projects/{project_uuid}"),
    )


@shared_task(name="cmp.notifications.send_project_collector_assigned", **RETRY_KW)
def send_project_collector_assigned(
    to: str, full_name: str, project_name: str, project_uuid: str
) -> dict[str, Any]:
    return deliver(
        Message.PROJECT_COLLECTOR_ASSIGNED,
        to=to,
        full_name=full_name,
        project_name=project_name,
        project_url=console(f"/projects/{project_uuid}"),
    )


@shared_task(name="cmp.notifications.send_rights_request_received", **RETRY_KW)
def send_rights_request_received(
    to: str, reference: str, request_type: str, channel: str, due_date: str, request_uuid: str
) -> dict[str, Any]:
    return deliver(
        Message.RIGHTS_REQUEST_RECEIVED,
        to=to,
        reference=reference,
        request_type=request_type,
        channel=channel,
        due_date=due_date,
        request_url=console(f"/requests/{request_uuid}"),
    )


@shared_task(name="cmp.notifications.send_rights_due_digest", **RETRY_KW)
def send_rights_due_digest(to: str, count: int, items: str) -> dict[str, Any]:
    return deliver(
        Message.RIGHTS_DUE_DIGEST,
        to=to,
        count=str(count),
        items=items,
        requests_url=console("/requests"),
    )


@shared_task(name="cmp.notifications.send_rights_grievance_about_dpo", **RETRY_KW)
def send_rights_grievance_about_dpo(to: str, reference: str, request_uuid: str) -> dict[str, Any]:
    return deliver(
        Message.RIGHTS_GRIEVANCE_ABOUT_DPO,
        to=to,
        reference=reference,
        request_url=console(f"/requests/{request_uuid}"),
    )


@shared_task(name="cmp.notifications.send_breach_duty_due", **RETRY_KW)
def send_breach_duty_due(
    to: str, breach_reference: str, duty: str, due_at: str, state: str, breach_uuid: str
) -> dict[str, Any]:
    return deliver(
        Message.BREACH_DUTY_DUE,
        to=to,
        breach_reference=breach_reference,
        duty=duty,
        due_at=due_at,
        state=state,
        breach_url=console(f"/breaches/{breach_uuid}"),
    )


@shared_task(name="cmp.notifications.send_breach_ticket_returned", **RETRY_KW)
def send_breach_ticket_returned(
    to: str, breach_reference: str, holder_name: str, outcome: str, breach_uuid: str
) -> dict[str, Any]:
    return deliver(
        Message.BREACH_TICKET_RETURNED,
        to=to,
        breach_reference=breach_reference,
        holder_name=holder_name,
        outcome=outcome,
        breach_url=console(f"/breaches/{breach_uuid}#tickets"),
    )


@shared_task(name="cmp.notifications.send_staff_role_changed", **RETRY_KW)
def send_staff_role_changed(
    to: str, full_name: str, old_role: str, new_role: str
) -> dict[str, Any]:
    return deliver(
        Message.STAFF_ROLE_CHANGED,
        to=to,
        full_name=full_name,
        old_role=old_role,
        new_role=new_role,
    )


@shared_task(name="cmp.notifications.send_staff_access_ended", **RETRY_KW)
def send_staff_access_ended(to: str, full_name: str) -> dict[str, Any]:
    return deliver(Message.STAFF_ACCESS_ENDED, to=to, full_name=full_name)


@shared_task(name="cmp.notifications.send_delegation_arranged", **RETRY_KW)
def send_delegation_arranged(
    to: str,
    delegator_name: str,
    delegate_name: str,
    role_title: str,
    starts_on: str,
    ends_on: str,
) -> dict[str, Any]:
    return deliver(
        Message.DELEGATION_ARRANGED,
        to=to,
        delegator_name=delegator_name,
        delegate_name=delegate_name,
        role_title=role_title,
        starts_on=starts_on,
        ends_on=ends_on,
    )
