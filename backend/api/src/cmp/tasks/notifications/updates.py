"""The messages the notification review of 2026-11-20 added.

Security notices to a member of staff about their own account; a contact
changed, to the contacts already there; a nominee acting, declining or being
withdrawn; a request under way; the office's word on collectors, sites,
suspensions, withdrawals and lapsed consent; breach ticket messages both ways,
a breach recorded or its duties changed, report and notice mail that did not
arrive; and the oversight alarms - a broken audit chain, DataVault refusing an
instruction, a sensitive setting changed.

As everywhere else, each task sends one junction to one address, passed sealed
and opened at `deliver()`; the domain fans out one task per recipient after its
transaction commits (`cmp.domain.alerts`).
"""

from __future__ import annotations

from typing import Any

from celery import shared_task

from cmp.core.config import settings
from cmp.core.messages import Message
from cmp.infrastructure.messaging import deliver
from cmp.tasks.notifications.rights import _RIGHT_NAMES, RETRY_KW


def console(path: str) -> str:
    return f"{settings.console_base_url.rstrip('/')}{path}"


# ------------------------------------------------------------------ security
@shared_task(name="cmp.notifications.send_password_changed", **RETRY_KW)
def send_password_changed(to: str, full_name: str, how: str, when: str) -> dict[str, Any]:
    return deliver(Message.PASSWORD_CHANGED, to=to, full_name=full_name, how=how, when=when)


@shared_task(name="cmp.notifications.send_mfa_reset", **RETRY_KW)
def send_mfa_reset(to: str, full_name: str, when: str) -> dict[str, Any]:
    return deliver(Message.MFA_RESET, to=to, full_name=full_name, when=when)


@shared_task(name="cmp.notifications.send_account_locked", **RETRY_KW)
def send_account_locked(
    to: str, full_name: str, failures: int, minutes: int, when: str
) -> dict[str, Any]:
    return deliver(
        Message.ACCOUNT_LOCKED,
        to=to,
        full_name=full_name,
        failures=failures,
        minutes=minutes,
        when=when,
    )


@shared_task(name="cmp.notifications.send_sessions_revoked", **RETRY_KW)
def send_sessions_revoked(to: str, full_name: str, when: str) -> dict[str, Any]:
    return deliver(Message.SESSIONS_REVOKED, to=to, full_name=full_name, when=when)


@shared_task(name="cmp.notifications.send_contact_changed", **RETRY_KW)
def send_contact_changed(to: str, change: str, actor: str, when: str) -> dict[str, Any]:
    return deliver(Message.CONTACT_CHANGED, to=to, change=change, actor=actor, when=when)


# ------------------------------------------------------------------ accounts
@shared_task(name="cmp.notifications.send_staff_access_restored", **RETRY_KW)
def send_staff_access_restored(to: str, full_name: str) -> dict[str, Any]:
    return deliver(Message.STAFF_ACCESS_RESTORED, to=to, full_name=full_name)


@shared_task(name="cmp.notifications.send_delegation_ended", **RETRY_KW)
def send_delegation_ended(
    to: str,
    delegator_name: str,
    delegate_name: str,
    role_title: str,
    ended_by: str,
    when: str,
) -> dict[str, Any]:
    return deliver(
        Message.DELEGATION_ENDED,
        to=to,
        delegator_name=delegator_name,
        delegate_name=delegate_name,
        role_title=role_title,
        ended_by=ended_by,
        when=when,
    )


# -------------------------------------------------------------------- rights
@shared_task(name="cmp.notifications.send_nominee_request_made", **RETRY_KW)
def send_nominee_request_made(
    to: str,
    full_name: str,
    nominee_name: str,
    request_type: str,
    reference: str,
    trigger_event: str,
) -> dict[str, Any]:
    grounds = (
        "you have passed away" if trigger_event == "death" else "you are unable to act for yourself"
    )
    return deliver(
        Message.NOMINEE_REQUEST_MADE,
        to=to,
        full_name=full_name or "",
        nominee_name=nominee_name,
        request_kind=_RIGHT_NAMES.get(request_type, "request"),
        reference=reference,
        grounds=grounds,
    )


@shared_task(name="cmp.notifications.send_nomination_declined", **RETRY_KW)
def send_nomination_declined(to: str, full_name: str, nominee_name: str) -> dict[str, Any]:
    return deliver(
        Message.NOMINATION_DECLINED, to=to, full_name=full_name or "", nominee_name=nominee_name
    )


@shared_task(name="cmp.notifications.send_nomination_revoked", **RETRY_KW)
def send_nomination_revoked(to: str, principal_name: str) -> dict[str, Any]:
    return deliver(Message.NOMINATION_REVOKED, to=to, principal_name=principal_name)


@shared_task(name="cmp.notifications.send_rights_in_progress", **RETRY_KW)
def send_rights_in_progress(
    to: str, reference: str, request_type: str, due_on: str
) -> dict[str, Any]:
    return deliver(
        Message.RIGHTS_IN_PROGRESS,
        to=to,
        reference=reference,
        request_kind=_RIGHT_NAMES.get(request_type, "request"),
        due_on=due_on,
    )


@shared_task(name="cmp.notifications.send_rights_reviewer_assigned", **RETRY_KW)
def send_rights_reviewer_assigned(
    to: str, full_name: str, reference: str, request_uuid: str
) -> dict[str, Any]:
    return deliver(
        Message.RIGHTS_REVIEWER_ASSIGNED,
        to=to,
        full_name=full_name,
        reference=reference,
        request_url=console(f"/requests/{request_uuid}"),
    )


@shared_task(name="cmp.notifications.send_rights_overdue_escalation", **RETRY_KW)
def send_rights_overdue_escalation(to: str, count: int, requests: str) -> dict[str, Any]:
    return deliver(Message.RIGHTS_OVERDUE_ESCALATION, to=to, count=count, requests=requests)


@shared_task(name="cmp.notifications.send_rights_retention_floor_passed", **RETRY_KW)
def send_rights_retention_floor_passed(to: str, count: int, requests: str) -> dict[str, Any]:
    return deliver(Message.RIGHTS_RETENTION_FLOOR_PASSED, to=to, count=count, requests=requests)


# ------------------------------------------------------------------ projects
@shared_task(name="cmp.notifications.send_processor_requested", **RETRY_KW)
def send_processor_requested(
    to: str, project_name: str, processor_name: str, requested_by: str, project_uuid: str
) -> dict[str, Any]:
    return deliver(
        Message.PROCESSOR_REQUESTED,
        to=to,
        project_name=project_name,
        processor_name=processor_name,
        requested_by=requested_by,
        project_url=console(f"/projects/{project_uuid}"),
    )


@shared_task(name="cmp.notifications.send_processor_decided", **RETRY_KW)
def send_processor_decided(
    to: str,
    full_name: str,
    project_name: str,
    processor_name: str,
    approved: bool,
    reason: str,
    project_uuid: str,
) -> dict[str, Any]:
    return deliver(
        Message.PROCESSOR_DECIDED,
        to=to,
        full_name=full_name,
        project_name=project_name,
        processor_name=processor_name,
        decision="approved" if approved else "not approved",
        reason=reason or "-",
        project_url=console(f"/projects/{project_uuid}"),
    )


@shared_task(name="cmp.notifications.send_registry_suspended", **RETRY_KW)
def send_registry_suspended(
    to: str, full_name: str, kind: str, name: str, project_name: str, project_uuid: str
) -> dict[str, Any]:
    return deliver(
        Message.REGISTRY_SUSPENDED,
        to=to,
        full_name=full_name,
        kind=kind,
        name=name,
        project_name=project_name,
        project_url=console(f"/projects/{project_uuid}"),
    )


@shared_task(name="cmp.notifications.send_site_deactivated", **RETRY_KW)
def send_site_deactivated(
    to: str,
    full_name: str,
    project_name: str,
    site_label: str,
    links_revoked: int,
    project_uuid: str,
) -> dict[str, Any]:
    return deliver(
        Message.SITE_DEACTIVATED,
        to=to,
        full_name=full_name,
        project_name=project_name,
        site_label=site_label,
        links_revoked=links_revoked,
        project_url=console(f"/projects/{project_uuid}"),
    )


# ------------------------------------------------------------------- consent
@shared_task(name="cmp.notifications.send_rnd_withdrawal_notice", **RETRY_KW)
def send_rnd_withdrawal_notice(
    to: str,
    project_name: str,
    principal_ref: str,
    stopped: list[str],
    continuing: list[str],
    consent_reference: str,
    project_uuid: str,
) -> dict[str, Any]:
    return deliver(
        Message.RND_WITHDRAWAL_NOTICE,
        to=to,
        project_name=project_name,
        principal_ref=principal_ref,
        stopped=", ".join(stopped) or "-",
        continuing=", ".join(continuing) or "none",
        consent_reference=consent_reference,
        project_url=console(f"/projects/{project_uuid}"),
    )


@shared_task(name="cmp.notifications.send_retention_lapsed", **RETRY_KW)
def send_retention_lapsed(
    to: str, quarantined: int, erase_due: int, purposes: str
) -> dict[str, Any]:
    return deliver(
        Message.RETENTION_LAPSED,
        to=to,
        quarantined=quarantined,
        erase_due=erase_due,
        purposes=purposes,
    )


@shared_task(name="cmp.notifications.send_hr_template_version_decided", **RETRY_KW)
def send_hr_template_version_decided(
    to: str, full_name: str, template_name: str, decision: str
) -> dict[str, Any]:
    next_step = (
        "You may now move your activities to this version."
        if decision == "approved"
        else "Activities still on it keep running, but no new activity may use it; please "
        "move them to a current version."
    )
    return deliver(
        Message.HR_TEMPLATE_VERSION_DECIDED,
        to=to,
        full_name=full_name,
        template_name=template_name,
        decision=decision,
        next_step=next_step,
    )


@shared_task(name="cmp.notifications.send_hr_respondent_changed", **RETRY_KW)
def send_hr_respondent_changed(
    to: str, full_name: str, category_name: str, added: bool
) -> dict[str, Any]:
    return deliver(
        Message.HR_RESPONDENT_CHANGED,
        to=to,
        full_name=full_name,
        category_name=category_name,
        change="added as" if added else "removed as",
    )


# -------------------------------------------------------------------- breach
@shared_task(name="cmp.notifications.send_breach_ticket_message", **RETRY_KW)
def send_breach_ticket_message(to: str, holder_name: str) -> dict[str, Any]:
    """BD-18: names no breach, and carries no word of the message."""
    return deliver(
        Message.BREACH_TICKET_MESSAGE,
        to=to,
        holder_name=holder_name or "colleague",
        tickets_url=console("/tickets"),
    )


@shared_task(name="cmp.notifications.send_breach_ticket_holder_replied", **RETRY_KW)
def send_breach_ticket_holder_replied(
    to: str, breach_reference: str, holder_name: str, breach_uuid: str
) -> dict[str, Any]:
    return deliver(
        Message.BREACH_TICKET_HOLDER_REPLIED,
        to=to,
        breach_reference=breach_reference,
        holder_name=holder_name,
        breach_url=console(f"/breaches/{breach_uuid}#tickets"),
    )


@shared_task(name="cmp.notifications.send_breach_recorded", **RETRY_KW)
def send_breach_recorded(
    to: str, breach_reference: str, what: str, actor: str, breach_uuid: str
) -> dict[str, Any]:
    return deliver(
        Message.BREACH_RECORDED,
        to=to,
        breach_reference=breach_reference,
        what=what,
        actor=actor,
        breach_url=console(f"/breaches/{breach_uuid}"),
    )


@shared_task(name="cmp.notifications.send_breach_duty_changed", **RETRY_KW)
def send_breach_duty_changed(
    to: str, breach_reference: str, change: str, actor: str, breach_uuid: str
) -> dict[str, Any]:
    return deliver(
        Message.BREACH_DUTY_CHANGED,
        to=to,
        breach_reference=breach_reference,
        change=change,
        actor=actor,
        breach_url=console(f"/breaches/{breach_uuid}"),
    )


@shared_task(name="cmp.notifications.send_breach_report_undelivered", **RETRY_KW)
def send_breach_report_undelivered(
    to: str, breach_reference: str, report_title: str, error: str, breach_uuid: str
) -> dict[str, Any]:
    return deliver(
        Message.BREACH_REPORT_UNDELIVERED,
        to=to,
        breach_reference=breach_reference,
        report_title=report_title,
        error=error or "-",
        breach_url=console(f"/breaches/{breach_uuid}#reports"),
    )


@shared_task(name="cmp.notifications.send_breach_notices_undelivered", **RETRY_KW)
def send_breach_notices_undelivered(
    to: str, breach_reference: str, breach_uuid: str
) -> dict[str, Any]:
    return deliver(
        Message.BREACH_NOTICES_UNDELIVERED,
        to=to,
        breach_reference=breach_reference,
        breach_url=console(f"/breaches/{breach_uuid}#notices"),
    )


@shared_task(name="cmp.notifications.send_temporary_access_ended", **RETRY_KW)
def send_temporary_access_ended(to: str, full_name: str) -> dict[str, Any]:
    return deliver(Message.TEMPORARY_ACCESS_ENDED, to=to, full_name=full_name or "colleague")


# ----------------------------------------------------------------- oversight
@shared_task(name="cmp.notifications.send_audit_chain_broken", **RETRY_KW)
def send_audit_chain_broken(to: str, position: str, when: str) -> dict[str, Any]:
    return deliver(Message.AUDIT_CHAIN_BROKEN, to=to, position=position, when=when)


@shared_task(name="cmp.notifications.send_datavault_problem", **RETRY_KW)
def send_datavault_problem(to: str, what: str, failure: str, when: str) -> dict[str, Any]:
    return deliver(Message.DATAVAULT_PROBLEM, to=to, what=what, failure=failure, when=when)


@shared_task(name="cmp.notifications.send_settings_changed", **RETRY_KW)
def send_settings_changed(to: str, setting: str, actor: str, when: str) -> dict[str, Any]:
    return deliver(Message.SETTINGS_CHANGED, to=to, setting=setting, actor=actor, when=when)


@shared_task(name="cmp.notifications.send_report_ready", **RETRY_KW)
def send_report_ready(
    to: str, report_title: str, period: str, file_ref: str, fmt: str
) -> dict[str, Any]:
    """A scheduled report, attached (ADR 0045). Only to an account of a role
    that may read it: the schedule's roles are checked when it is set up."""
    from cmp.infrastructure.email import Attachment
    from cmp.infrastructure.report_files import MIME
    from cmp.infrastructure.storage.service import read_upload

    data = read_upload(file_ref)
    name = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in report_title)[:80]
    return deliver(
        Message.REPORT_READY,
        to=to,
        attachments=[
            Attachment(
                filename=f"{name.strip('-') or 'report'}.{fmt}",
                content_type=MIME[fmt].split(";")[0],
                data=data,
            )
        ],
        report_title=report_title,
        period=period,
    )
