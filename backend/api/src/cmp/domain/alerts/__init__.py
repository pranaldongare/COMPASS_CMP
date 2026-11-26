"""Who is emailed about the work, and when (2026-10-08).

Each function here is called by the module whose event it is - a project
moving, a request arriving, a ticket returned, a role changed - inside that
module's transaction, and queues one task per recipient, which runs after the
commit (`dispatch_optional`). A message that cannot be queued is logged and
lost, never a failure of the act it describes: the record is written either
way, and the console's bell still shows it.

Addresses are read sealed and opened only at `deliver()`. Copies are the
office's choice per message (Message templates); nothing here adds one.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any, Final

from cmp.core.logging import get_logger
from cmp.core.permissions import OFFICE_TITLES, ROLE_TITLES
from cmp.db.redis import K_CACHE, get_redis
from cmp.db.redis import key as rkey
from cmp.db.repositories import alerts as repo
from cmp.db.repositories import users as user_repo
from cmp.db.sql import Conn
from cmp.infrastructure.dkms import unseal_value

log = get_logger("cmp.alerts")

Row = dict[str, Any]

#: How far ahead the daily list looks for rights requests.
RIGHTS_DUE_WITHIN_DAYS: Final = 7

KINDS: Final[dict[str, str]] = {
    "access": "access",
    "erasure": "erasure",
    "grievance": "grievance",
    "correction": "correction",
}
CHANNELS: Final[dict[str, str]] = {
    "portal": "the portal",
    "public_form": "the public form",
    "nominee": "a nominee",
    "staff_logged": "the Privacy Office",
}
#: What was done to the organisation's board list, as the officers' mail says it.
LIST_CHANGES: Final[dict[str, str]] = {
    "added": "added this address to",
    "removed": "took this address off",
    "mandatory": "made this address mandatory on",
    "optional": "made this address optional again on",
}


def _queue(task: Any, *args: Any) -> None:
    from cmp.tasks.dispatch import dispatch_optional

    dispatch_optional(task, *args)


def day(value: date | datetime | None) -> str:
    if value is None:
        return "-"
    return f"{value.day} {value:%B %Y}"


def moment(value: datetime) -> str:
    v = value.astimezone(UTC)
    return f"{v.day} {v:%B %Y}, {v:%H:%M} UTC"


async def _role(conn: Conn, role: str) -> list[str]:
    return await user_repo.active_emails_for_role(conn, role)


async def _person(conn: Conn, user_id: int | None) -> Row | None:
    if not user_id:
        return None
    person = await user_repo.by_id(conn, int(user_id))
    return person if person and person.get("email") else None


# ------------------------------------------------------------------ projects


async def project_moved(
    conn: Conn, *, project: Row, to: str, reason: str | None, actor_id: int
) -> None:
    """Submitted: every DPO. Approved, sent back, closed: the project's owner."""
    from cmp.tasks.notifications import alerts as tasks

    name = str(project["project_name"])
    uuid = str(project["project_uuid"])
    if to == "pending_approval":
        actor = await user_repo.by_id(conn, actor_id)
        by = str(actor["full_name"]) if actor and actor.get("full_name") else "An R&D User"
        for email in await _role(conn, "dpo"):
            _queue(tasks.send_project_submitted, email, name, by, uuid)
        return
    if to == "approved" and project.get("created_by") == actor_id:
        # An HR activity goes live by its creator's own act (ADR 0033);
        # nobody needs telling what they have just done.
        return
    owner = await _person(conn, project.get("created_by"))
    if owner is None:
        return
    if to == "approved":
        _queue(tasks.send_project_approved, owner["email"], owner["full_name"], name, uuid)
    elif to == "in_draft":
        _queue(
            tasks.send_project_sent_back,
            owner["email"],
            owner["full_name"],
            name,
            uuid,
            reason or "",
        )
    elif to == "closed":
        _queue(
            tasks.send_project_closed, owner["email"], owner["full_name"], name, uuid, reason or ""
        )


async def collector_assigned(conn: Conn, *, project: Row, dco_user_id: int | None) -> None:
    """The project's collection is now this person's."""
    from cmp.tasks.notifications import alerts as tasks

    person = await _person(conn, dco_user_id)
    if person is None:
        return
    _queue(
        tasks.send_project_collector_assigned,
        person["email"],
        person["full_name"],
        str(project["project_name"]),
        str(project["project_uuid"]),
    )


# -------------------------------------------------------------------- rights


async def _officers(conn: Conn, office: str | None) -> list[str]:
    """The officers of an office - the DPO's, the Legal PoC's - or of both,
    for a request in the shared intake (ADR 0032, 0055)."""
    return await user_repo.officer_emails(conn, office)


async def rights_received(conn: Conn, request: Row) -> None:
    """A request arrived from outside the office: every officer of its office,
    or of both while it is in the shared intake. Never her words."""
    from cmp.tasks.notifications import alerts as tasks

    if request.get("channel") == "staff_logged":
        return
    for email in await _officers(conn, request.get("office_code")):
        _queue(
            tasks.send_rights_request_received,
            email,
            str(request["reference"]),
            KINDS.get(str(request["request_type"]), str(request["request_type"])),
            CHANNELS.get(str(request["channel"]), str(request["channel"])),
            day(request.get("due_at")),
            str(request["request_uuid"]),
        )


async def rights_transferred(conn: Conn, request: Row, *, from_office: str) -> None:
    """Moved to another office: that office's officers, with the sender's
    reason as the row holds it - sealed on the queue too, opened at delivery
    (0055)."""
    from cmp.tasks.notifications import alerts as tasks

    for email in await _officers(conn, request.get("office_code")):
        _queue(
            tasks.send_rights_transfer_received,
            email,
            str(request["reference"]),
            KINDS.get(str(request["request_type"]), str(request["request_type"])),
            day(request.get("received_at")),
            day(request.get("due_at")),
            OFFICE_TITLES.get(from_office, from_office),
            str(request["transfer_reason"]),
            str(request["request_uuid"]),
        )


async def grievance_about_dpo(conn: Conn, request: Row) -> None:
    """A grievance about the DPO's own handling: every administrator."""
    from cmp.tasks.notifications import alerts as tasks

    for email in await _role(conn, "admin"):
        _queue(
            tasks.send_rights_grievance_about_dpo,
            email,
            str(request["reference"]),
            str(request["request_uuid"]),
        )


async def rights_due(conn: Conn, *, now: datetime | None = None) -> int:
    """The daily list: open requests overdue or due within a week. Nothing
    when there is nothing on it, one per office. Returns how many requests it
    listed."""
    rows = await repo.rights_due_within(conn, RIGHTS_DUE_WITHIN_DAYS)
    if not rows:
        return 0
    at = now or datetime.now(UTC)
    # One list per office, of its own requests; the shared intake's go to both.
    for office in ("rnd", "hr"):
        mine = [r for r in rows if r.get("office_code") in (office, None)]
        if mine:
            await _digest(conn, office, mine, at)
    # What is already late goes to the administrators as well (2026-11-20).
    await rights_overdue(conn, rows, at)
    return len(rows)


async def _digest(conn: Conn, office: str, rows: list[Row], at: datetime) -> None:
    from cmp.tasks.notifications import alerts as tasks

    lines = []
    for r in rows:
        days = (r["due_at"].date() - at.date()).days
        state = (
            f"overdue by {-days} day{'s' if days != -1 else ''}"
            if days < 0
            else "due today"
            if days == 0
            else f"due in {days} day{'s' if days != 1 else ''}"
        )
        lines.append(f"  - {r['reference']} {r['request_type']}, due {day(r['due_at'])} - {state}")
    for email in await _officers(conn, office):
        _queue(tasks.send_rights_due_digest, email, len(rows), "\n".join(lines))


# -------------------------------------------------------------------- breach


async def breach_duties(conn: Conn, *, now: datetime | None = None) -> int:
    """Every dated duty of an open breach that is about to fall due, or has:
    the officers of its office, once per duty per stage. Returns how many
    alerts it queued.

    "About to" is the last sixth of the duty's window, at least five minutes:
    ten minutes of the board's thirty, an hour of CERT-In's six, twelve of the
    report's seventy-two. Each alert is remembered for thirty days in Redis, so
    the sweep running every five minutes says each thing once. The memory is of
    this due time: a duty reinstated or extended is a new clock, and says it
    again.
    """
    from cmp.domain.breach import clock
    from cmp.domain.breach import service as breach_service
    from cmp.tasks.notifications import alerts as tasks

    at = now or datetime.now(UTC)
    queued = 0
    redis = get_redis()
    officers: dict[str | None, list[str]] = {}
    for breach in await repo.open_breaches_with_dated_duties(conn):
        duties = await breach_service.duties_of(conn, int(breach["breach_id"]))
        for kind, (row, folded) in duties.items():
            due = folded.get("due_at")
            if folded.get("state") != clock.State.OUTSTANDING or due is None:
                continue
            # The folded anchor: a reinstated duty runs from its own moment.
            anchored = folded.get("anchored_at") or row.get("created_at") or due
            lead = max(timedelta(minutes=5), (due - anchored) / 6)
            if at >= due:
                stage, state = "overdue", f"overdue since {moment(due)}"
            elif at >= due - lead:
                minutes = int((due - at).total_seconds() // 60) or 1
                left = f"{minutes} minutes" if minutes < 120 else f"{minutes // 60} hours"
                stage, state = "due_soon", f"due in {left}"
            else:
                continue
            marker = rkey(
                K_CACHE, "alert", "breach_duty", str(row["obligation_id"]), stage, due.isoformat()
            )
            if not await redis.set(marker, "1", nx=True, ex=30 * 24 * 3600):
                continue
            office = breach.get("office_code")
            if office not in officers:
                officers[office] = await _officers(conn, office)
            for email in officers[office]:
                _queue(
                    tasks.send_breach_duty_due,
                    email,
                    str(breach["reference"]),
                    clock.LABELS.get(kind, kind),
                    moment(due),
                    state,
                    str(breach["breach_uuid"]),
                )
                queued += 1
    return queued


async def breach_ticket_returned(
    conn: Conn, *, breach: Row, holder_name: str, outcome: str
) -> None:
    from cmp.tasks.notifications import alerts as tasks

    words = {"done": "completed", "partial": "partially done", "failed": "not applicable"}
    for email in await _officers(conn, breach.get("office_code") or "rnd"):
        _queue(
            tasks.send_breach_ticket_returned,
            email,
            str(breach.get("breach_reference") or breach["reference"]),
            holder_name,
            words.get(outcome, outcome),
            str(breach["breach_uuid"]),
        )


async def breach_ticket_date_changed(conn: Conn, *, breach: Row) -> None:
    from cmp.tasks.notifications.breach_tickets import send_breach_ticket_date_changed

    for email in await _officers(conn, breach.get("office_code") or "rnd"):
        _queue(send_breach_ticket_date_changed, email, f"/breaches/{breach['breach_uuid']}#tickets")


async def incident_reported(conn: Conn, *, report: Row) -> None:
    """A report from the public link: to everyone in the roles the office has
    named, who are told it is there and nothing of what it says; and to the
    reporter, who is told its number."""
    from cmp.db.repositories import incident_reports as reports
    from cmp.tasks.notifications import incident_reports as tasks

    roles = (await reports.settings(conn))["intake_roles"]
    emails = await reports.active_emails(conn, list(roles))
    if not emails:
        # It waits on no clock, so nothing else would ever raise this.
        log.error(
            "incident_report.nobody_to_tell", reference=str(report["reference"]), roles=list(roles)
        )
    for email in emails:
        _queue(
            tasks.send_incident_reported,
            email,
            str(report["reference"]),
            moment(report["received_at"]),
        )
    _queue(
        tasks.send_incident_report_received,
        str(report["reporter_email"]),
        str(report["reporter_name"]),
        str(report["reference"]),
    )


async def breach_transferred(conn: Conn, *, breach: Row, from_office: str) -> None:
    """Reassigned to another office: that office's officers, with the sender's
    reason as the row holds it - sealed on the queue too, opened at delivery
    (0073)."""
    from cmp.tasks.notifications import incident_reports as tasks

    for email in await _officers(conn, breach.get("office_code")):
        _queue(
            tasks.send_breach_transfer_received,
            email,
            str(breach["reference"]),
            OFFICE_TITLES.get(from_office, from_office),
            str(breach["transfer_reason"]),
            str(breach["breach_uuid"]),
        )


async def incident_escalated(conn: Conn, *, report: Row, emails: list[str], now: datetime) -> None:
    """A report nobody has taken up: to management, the escalation list. That
    it waits and since when, and nothing of what it says (0073)."""
    from cmp.tasks.notifications import incident_reports as tasks

    minutes = max(1, int((now - report["received_at"]).total_seconds() // 60))
    waited = f"{minutes} minutes" if minutes < 120 else f"{minutes // 60} hours"
    for email in emails:
        _queue(
            tasks.send_incident_report_escalated,
            email,
            str(report["reference"]),
            moment(report["received_at"]),
            waited,
        )


async def board_list_changed(conn: Conn, *, change: str, recipient: Row, actor_id: int) -> None:
    """An address added to the organisation's board list, taken off it, made
    mandatory or optional again: to every active officer of both offices, the
    one who made it included, naming who did it and the address. Anybody who
    keeps the list could otherwise add their own and nobody would know; an
    inbox told of a change its owner did not make is the alarm against a
    stolen session. It names no breach, so it may cross the wall between the
    offices, and the list is no office's. The name and address stay sealed as
    read and are opened at `deliver()`."""
    from cmp.core.permissions import OFFICER_OF
    from cmp.db.repositories import incident_reports as reports
    from cmp.tasks.notifications import alerts as tasks

    emails = await reports.active_emails(conn, list(OFFICER_OF.values()))
    if not emails:
        # The change stands: the list is kept by the administrator too, and a
        # list nobody can be told of is a fault to raise, not a reason to refuse.
        log.error("breach_settings.nobody_to_tell", change=change)
        return
    actor = await user_repo.by_id(conn, actor_id)
    assert actor is not None
    for email in emails:
        _queue(
            tasks.send_breach_board_list_changed,
            email,
            actor["full_name"],
            ROLE_TITLES.get(str(actor["role"]), str(actor["role"])),
            LIST_CHANGES[change],
            recipient["full_name"] or "No name given",
            recipient["email"],
            moment(datetime.now(UTC)),
        )


# ------------------------------------------------------------------ accounts


async def role_changed(conn: Conn, *, user: Row, old_role: str, new_role: str) -> None:
    from cmp.tasks.notifications import alerts as tasks

    if not user.get("email"):
        return
    _queue(
        tasks.send_staff_role_changed,
        user["email"],
        user["full_name"],
        ROLE_TITLES.get(old_role, old_role),
        ROLE_TITLES.get(new_role, new_role),
    )


async def staff_access_ended(conn: Conn, *, user: Row) -> None:
    from cmp.tasks.notifications import alerts as tasks

    if user.get("email"):
        _queue(tasks.send_staff_access_ended, user["email"], user["full_name"])


async def delegation_arranged(
    conn: Conn,
    *,
    delegator_id: int,
    delegate_id: int,
    role: str,
    starts_at: datetime | None,
    ends_at: datetime | None,
) -> None:
    """Both people: the one covered and the one covering."""
    from cmp.tasks.notifications import alerts as tasks

    delegator = await _person(conn, delegator_id)
    delegate = await _person(conn, delegate_id)
    if delegator is None or delegate is None:
        return
    for person in (delegator, delegate):
        _queue(
            tasks.send_delegation_arranged,
            person["email"],
            delegator["full_name"],
            delegate["full_name"],
            ROLE_TITLES.get(role, role),
            day(starts_at or datetime.now(UTC)),
            day(ends_at) if ends_at else "until it is ended",
        )


# ======================================================= 2026-11-20 additions
# Every event the notification review found nobody was told of. Same rules as
# above: one task per recipient, queued after the commit; addresses sealed as
# read, opened at `deliver()`; never a person's words, never a breach named to
# a ticket's holder (BD-18).


def _now() -> str:
    return moment(datetime.now(UTC))


async def _name(conn: Conn, user_id: int | None, fallback: str = "A member of staff") -> str:
    person = await user_repo.by_id(conn, int(user_id)) if user_id else None
    return str(person["full_name"]) if person and person.get("full_name") else fallback


async def _actor(conn: Conn, user_id: int | None) -> str:
    """Who did it, with their role: "Dee Pee (Data Protection Officer)"."""
    person = await user_repo.by_id(conn, int(user_id)) if user_id else None
    if not person:
        return "the platform"
    role = ROLE_TITLES.get(str(person.get("role")), str(person.get("role") or ""))
    return f"{person.get('full_name') or 'A member of staff'} ({role})"


def _unique(emails: list[str]) -> list[str]:
    seen: list[str] = []
    for e in emails:
        if e and e not in seen:
            seen.append(e)
    return seen


async def _oversight(conn: Conn) -> list[str]:
    """Every active administrator and officer: the people who answer for the
    platform as a whole."""
    out: list[str] = []
    for role in ("admin", "dpo", "legal"):
        out += await _role(conn, role)
    return _unique(out)


async def _once(*parts: str, hours: int) -> bool:
    """True the first time in `hours` this is said; False after."""
    try:
        marker = rkey(K_CACHE, "alert", *parts)
        return bool(await get_redis().set(marker, "1", nx=True, ex=hours * 3600))
    except Exception as exc:  # no memory: say it rather than stay silent
        log.warning("alerts.once_unavailable", error=str(exc))
        return True


# ------------------------------------------------------------------ security


async def password_changed(conn: Conn, *, user: Row, how: str) -> None:
    from cmp.tasks.notifications import updates as tasks

    if user.get("email") and user.get("role") != "data_subject":
        _queue(tasks.send_password_changed, user["email"], user["full_name"] or "", how, _now())


async def mfa_reset(conn: Conn, *, user: Row) -> None:
    from cmp.tasks.notifications import updates as tasks

    if user.get("email"):
        _queue(tasks.send_mfa_reset, user["email"], user["full_name"] or "", _now())


async def account_locked(conn: Conn, *, user: Row, failures: int, minutes: int) -> None:
    from cmp.tasks.notifications import updates as tasks

    if user.get("email"):
        _queue(
            tasks.send_account_locked,
            user["email"],
            user.get("full_name") or "",
            failures,
            minutes,
            _now(),
        )


async def sessions_revoked(conn: Conn, *, user: Row) -> None:
    from cmp.tasks.notifications import updates as tasks

    if user.get("email"):
        _queue(tasks.send_sessions_revoked, user["email"], user["full_name"] or "", _now())


#: What changed, as the notice says it, by medium and action.
CONTACT_CHANGES: Final[dict[tuple[str, str], str]] = {
    ("mobile", "set"): "a mobile number was added to or changed on your account",
    ("secondary_email", "set"): "a second email address was added to or changed on your account",
    ("secondary_email", "removed"): "the second email address was removed from your account",
}


async def contact_changed(
    conn: Conn, *, before: Row, medium: str, action: str, by_admin: bool
) -> None:
    """A security notice to every confirmed contact the account already had,
    other than the one that changed: the alarm against a contact being swapped
    by somebody holding the session. The new contact is never named."""
    from cmp.tasks.notifications import updates as tasks

    change = CONTACT_CHANGES.get((medium, action))
    if change is None:
        return

    def confirmed(medium_: str) -> str | None:
        value = before.get(medium_)
        if not value:
            return None
        # A member of staff's primary email is confirmed by the invitation.
        staff_email = medium_ == "email" and before.get("role") != "data_subject"
        return str(value) if (before.get(f"{medium_}_verified_at") or staff_email) else None

    # Every confirmed contact the account had - the one replaced or removed
    # included, since whoever held it should know it went.
    to = [c for c in (confirmed("email"), confirmed("mobile"), confirmed("secondary_email")) if c]
    actor = "an administrator" if by_admin else "the account holder, from the account page"
    when = _now()
    for contact in _unique(to):
        _queue(tasks.send_contact_changed, contact, change, actor, when)


# ------------------------------------------------------------------ accounts


async def access_restored(conn: Conn, *, user: Row) -> None:
    from cmp.tasks.notifications import updates as tasks

    if user.get("email") and user.get("role") != "data_subject":
        _queue(tasks.send_staff_access_restored, user["email"], user["full_name"] or "")


async def delegation_ended(conn: Conn, *, row: Row, actor_id: int) -> None:
    """Both people, whoever ended it."""
    from cmp.tasks.notifications import updates as tasks

    delegator = await _person(conn, row.get("delegator_user_id"))
    delegate = await _person(conn, row.get("delegate_user_id"))
    if delegator is None or delegate is None:
        return
    role = str(row.get("role") or delegator.get("role") or "")
    by = await _name(conn, actor_id, "An administrator")
    when = _now()
    for person in (delegator, delegate):
        _queue(
            tasks.send_delegation_ended,
            person["email"],
            delegator["full_name"],
            delegate["full_name"],
            ROLE_TITLES.get(role, role),
            by,
            when,
        )


async def temporary_access_ended(conn: Conn, *, user_id: int) -> None:
    from cmp.tasks.notifications import updates as tasks

    person = await _person(conn, user_id)
    if person:
        _queue(tasks.send_temporary_access_ended, person["email"], person.get("full_name") or "")


# -------------------------------------------------------------------- rights


async def _principal_contact(conn: Conn, user_id: int | None) -> tuple[str | None, str]:
    from cmp.domain.consent.service import receipt_contact

    person = await user_repo.by_id(conn, int(user_id)) if user_id else None
    if not person:
        return None, ""
    return receipt_contact(person), str(person.get("full_name") or "")


async def nominee_request_made(
    conn: Conn, *, nomination: Row, request: Row, trigger_event: str
) -> None:
    """Her safeguard: the nominee she appointed has acted in her name. On a
    claim of incapacity only - on a claim of death there is nobody to write to,
    and writing anyway would be its own cruelty (as the acknowledgement)."""
    from cmp.tasks.notifications import updates as tasks

    if trigger_event != "incapacity":
        return
    contact, name = await _principal_contact(conn, nomination.get("principal_user_id"))
    if not contact:
        return
    _queue(
        tasks.send_nominee_request_made,
        contact,
        name,
        str(nomination.get("nominee_name") or "Your nominee"),
        str(request["request_type"]),
        str(request["reference"]),
        trigger_event,
    )


async def nomination_declined(conn: Conn, *, nomination: Row) -> None:
    from cmp.tasks.notifications import updates as tasks

    contact, name = await _principal_contact(conn, nomination.get("principal_user_id"))
    if contact:
        _queue(
            tasks.send_nomination_declined,
            contact,
            name,
            str(nomination.get("nominee_name") or "The person you nominated"),
        )


async def nomination_revoked(conn: Conn, *, nomination: Row) -> None:
    """Every contact she recorded for him: whichever he reads."""
    from cmp.tasks.notifications import updates as tasks

    principal = await _name(
        conn, nomination.get("principal_user_id"), "The person who nominated you"
    )
    for contact in (nomination.get("nominee_mobile"), nomination.get("nominee_email")):
        if contact:
            _queue(tasks.send_nomination_revoked, str(contact), principal)


async def rights_in_progress(conn: Conn, *, request: Row, contact: str | None) -> None:
    from cmp.tasks.notifications import updates as tasks

    if contact and request.get("due_at"):
        _queue(
            tasks.send_rights_in_progress,
            contact,
            str(request["reference"]),
            str(request["request_type"]),
            day(request["due_at"]),
        )


async def reviewer_assigned(conn: Conn, *, request: Row, reviewer: Row) -> None:
    from cmp.tasks.notifications import updates as tasks

    if reviewer.get("email"):
        _queue(
            tasks.send_rights_reviewer_assigned,
            reviewer["email"],
            reviewer.get("full_name") or "",
            str(request["reference"]),
            str(request["request_uuid"]),
        )


async def rights_overdue(conn: Conn, rows: list[Row], at: datetime) -> int:
    """The administrators' word on what is already late. Nothing when nothing is."""
    from cmp.tasks.notifications import updates as tasks

    late = [r for r in rows if r["due_at"] < at]
    if not late:
        return 0
    lines = []
    for r in late:
        days = max(1, (at.date() - r["due_at"].date()).days)
        office = OFFICE_TITLES.get(str(r.get("office_code")), "the shared intake")
        lines.append(
            f"  - {r['reference']} {r['request_type']}, {office}: "
            f"overdue by {days} day{'s' if days != 1 else ''}"
        )
    for email in await _role(conn, "admin"):
        _queue(tasks.send_rights_overdue_escalation, email, len(late), "\n".join(lines))
    return len(late)


async def retention_floors_passed(
    conn: Conn, by_request: dict[int, Row], counts: dict[int, int]
) -> None:
    """The office's word that retained items reached the end of their period."""
    from cmp.tasks.notifications import updates as tasks

    by_office: dict[str | None, list[str]] = {}
    total: dict[str | None, int] = {}
    for request_id, request in by_request.items():
        office = request.get("office_code")
        n = counts.get(request_id, 0)
        by_office.setdefault(office, []).append(
            f"  - {request['reference']}: {n} item{'s' if n != 1 else ''}"
        )
        total[office] = total.get(office, 0) + n
    for office, lines in by_office.items():
        for email in await _officers(conn, office):
            _queue(tasks.send_rights_retention_floor_passed, email, total[office], "\n".join(lines))


# ------------------------------------------------------------------ projects


async def processor_requested(
    conn: Conn, *, project: Row, processor_name: str, actor_id: int
) -> None:
    from cmp.db.repositories import alerts as alerts_repo
    from cmp.tasks.notifications import updates as tasks

    people = await alerts_repo.project_people(conn, int(project["project_id"]))
    office = people.get("office_code") if people else None
    by = await _name(conn, actor_id, "An R&D User")
    for email in await _officers(conn, office or "rnd"):
        _queue(
            tasks.send_processor_requested,
            email,
            str(project["project_name"]),
            processor_name,
            by,
            str(project["project_uuid"]),
        )


async def processor_decided(
    conn: Conn, *, project: Row, processor_name: str, approved: bool, reason: str | None
) -> None:
    from cmp.tasks.notifications import updates as tasks

    owner = await _person(conn, project.get("created_by"))
    if owner:
        _queue(
            tasks.send_processor_decided,
            owner["email"],
            owner["full_name"],
            str(project["project_name"]),
            processor_name,
            approved,
            reason or "",
            str(project["project_uuid"]),
        )


async def _project_team(conn: Conn, project: Row) -> list[Row]:
    """The project's owner and its collector, each once."""
    out: list[Row] = []
    for user_id in (project.get("owner_id"), project.get("dco_id")):
        person = await _person(conn, user_id)
        if person and all(p["id"] != person["id"] for p in out):
            out.append(person)
    return out


async def registry_suspended(conn: Conn, *, kind: str, name: str, projects: list[Row]) -> None:
    from cmp.tasks.notifications import updates as tasks

    for project in projects:
        for person in await _project_team(conn, project):
            _queue(
                tasks.send_registry_suspended,
                person["email"],
                person["full_name"],
                kind,
                name,
                str(project["project_name"]),
                str(project["project_uuid"]),
            )


async def site_deactivated(
    conn: Conn, *, project_id: int, site_label: str, links_revoked: int
) -> None:
    from cmp.db.repositories import alerts as alerts_repo
    from cmp.tasks.notifications import updates as tasks

    project = await alerts_repo.project_people(conn, project_id)
    if not project:
        return
    for person in await _project_team(conn, project):
        _queue(
            tasks.send_site_deactivated,
            person["email"],
            person["full_name"],
            str(project["project_name"]),
            site_label,
            links_revoked,
            str(project["project_uuid"]),
        )


async def collectors_moved(conn: Conn, *, before: dict[int, int | None], after: list[Row]) -> None:
    """A source's owner changed in the registry, and with it the collector of
    every project collecting from it (by trigger): each new collector is told,
    as when the owner is set on one project."""
    for project in after:
        was = before.get(int(project["project_id"]))
        if project.get("dco_id") and project["dco_id"] != was:
            await collector_assigned(conn, project=project, dco_user_id=int(project["dco_id"]))


# ------------------------------------------------------------------- consent


async def rnd_withdrawal(
    conn: Conn,
    *,
    notice_id: int,
    user: Row | None,
    consent_reference: str,
    stopped: list[str],
    continuing: list[str],
) -> int:
    """A withdrawal on an R&D project: its owner and collector are told to stop
    processing, as an HR activity's respondents are (ADR 0033). The participant
    by her principal ID only."""
    from cmp.db.repositories import alerts as alerts_repo
    from cmp.tasks.notifications import updates as tasks

    project = await alerts_repo.project_of_notice(conn, notice_id)
    if not project or not user or project.get("office_code") != "rnd" or not stopped:
        return 0
    team = await _project_team(conn, project)
    for person in team:
        _queue(
            tasks.send_rnd_withdrawal_notice,
            person["email"],
            str(project["project_name"]),
            str(user["uuid"]),
            stopped,
            continuing,
            consent_reference,
            str(project["project_uuid"]),
        )
    return len(team)


async def retention_lapsed(conn: Conn, *, by_purpose: dict[str, dict[str, int]]) -> None:
    """The nightly word on consent whose validity ran out: per office, counts
    and purpose codes, never a person."""
    from cmp.db.repositories import alerts as alerts_repo
    from cmp.tasks.notifications import updates as tasks

    offices = {
        str(r["purpose_code"]): str(r["office_code"])
        for r in await alerts_repo.purposes_lapsed_offices(conn, list(by_purpose))
    }
    grouped: dict[str, dict[str, Any]] = {}
    for code, counts in by_purpose.items():
        g = grouped.setdefault(offices.get(code, "rnd"), {"q": 0, "e": 0, "codes": []})
        g["q"] += counts.get("quarantined", 0)
        g["e"] += counts.get("erase_due", 0)
        g["codes"].append(code)
    for office, g in grouped.items():
        for email in await _officers(conn, office):
            _queue(
                tasks.send_retention_lapsed, email, g["q"], g["e"], ", ".join(sorted(g["codes"]))
            )


async def hr_template_version_decided(conn: Conn, *, version: Row, decision: str) -> None:
    """The HR PoCs of the category the template serves."""
    from cmp.db.repositories import alerts as alerts_repo
    from cmp.tasks.notifications import updates as tasks

    template_id = int(version["template_id"])
    title = await alerts_repo.template_title(conn, template_id)
    name = f"{title or 'The consent template'} v{version.get('version')}"
    for user_id in await alerts_repo.hr_pocs_for_template(conn, template_id):
        person = await _person(conn, user_id)
        if person:
            _queue(
                tasks.send_hr_template_version_decided,
                person["email"],
                person["full_name"],
                name,
                decision,
            )


async def hr_respondents_changed(
    conn: Conn, *, category_name: str, added: set[int], removed: set[int]
) -> None:
    from cmp.tasks.notifications import updates as tasks

    for ids, was_added in ((added, True), (removed, False)):
        for user_id in sorted(ids):
            person = await _person(conn, user_id)
            if person:
                _queue(
                    tasks.send_hr_respondent_changed,
                    person["email"],
                    person["full_name"],
                    category_name,
                    was_added,
                )


# -------------------------------------------------------------------- breach


def _breach_ref(breach: Row) -> str:
    return str(breach.get("breach_reference") or breach.get("reference") or "")


async def breach_ticket_office_wrote(conn: Conn, *, ticket: Row) -> None:
    """The holder: a message waits. Names no breach and quotes nothing (BD-18)."""
    from cmp.tasks.notifications import updates as tasks

    if ticket.get("holder_email"):
        _queue(
            tasks.send_breach_ticket_message,
            str(ticket["holder_email"]),
            str(ticket.get("holder_name") or ""),
        )


async def breach_ticket_holder_wrote(conn: Conn, *, ticket: Row) -> None:
    from cmp.tasks.notifications import updates as tasks

    for email in await _officers(conn, ticket.get("office_code") or "rnd"):
        _queue(
            tasks.send_breach_ticket_holder_replied,
            email,
            _breach_ref(ticket),
            str(ticket.get("holder_name") or "The holder"),
            str(ticket["breach_uuid"]),
        )


async def breach_recorded(conn: Conn, *, breach: Row, what: str, actor_id: int | None) -> None:
    """The breach office's officers, the one who did it excepted: they know."""
    from cmp.tasks.notifications import updates as tasks

    actor = await user_repo.by_id(conn, int(actor_id)) if actor_id else None
    mine = str(actor["email"]) if actor and actor.get("email") else None
    by = await _name(conn, actor_id, "the platform")
    for email in await _officers(conn, breach.get("office_code") or "rnd"):
        if mine is not None and email == mine:
            continue
        _queue(
            tasks.send_breach_recorded,
            email,
            _breach_ref(breach),
            what,
            by,
            str(breach["breach_uuid"]),
        )


async def breach_duty_changed(
    conn: Conn, *, breach: Row, change: str, actor_id: int | None
) -> None:
    from cmp.tasks.notifications import updates as tasks

    by = await _name(conn, actor_id, "the platform")
    for email in await _officers(conn, breach.get("office_code") or "rnd"):
        _queue(
            tasks.send_breach_duty_changed,
            email,
            _breach_ref(breach),
            change,
            by,
            str(breach["breach_uuid"]),
        )


async def breach_report_undelivered(
    conn: Conn, *, breach: Row, report_title: str, error: str
) -> None:
    from cmp.tasks.notifications import updates as tasks

    for email in await _officers(conn, breach.get("office_code") or "rnd"):
        _queue(
            tasks.send_breach_report_undelivered,
            email,
            _breach_ref(breach),
            report_title,
            error,
            str(breach["breach_uuid"]),
        )


async def breach_notices_undelivered(conn: Conn, *, breach: Row) -> bool:
    """At most once every six hours per breach: a list of thousands that fails
    is one thing to look at, not thousands of mails."""
    from cmp.tasks.notifications import updates as tasks

    if not await _once("breach_notices_failed", str(breach["breach_uuid"]), hours=6):
        return False
    for email in await _officers(conn, breach.get("office_code") or "rnd"):
        _queue(
            tasks.send_breach_notices_undelivered,
            email,
            _breach_ref(breach),
            str(breach["breach_uuid"]),
        )
    return True


# ----------------------------------------------------------------- oversight


async def audit_chain_broken(conn: Conn, *, position: str) -> None:
    """Every administrator and officer: a trail nobody can erase that no longer
    adds up is the alarm the trail exists to raise."""
    from cmp.tasks.notifications import updates as tasks

    when = _now()
    for email in await _oversight(conn):
        _queue(tasks.send_audit_chain_broken, email, position, when)


async def datavault_problem(
    conn: Conn, *, what: str, failure: str, office: str | None, marker: str
) -> None:
    """The administrators, who keep the connection (0070), and the office whose
    instruction it was. Once a day per instruction."""
    from cmp.tasks.notifications import updates as tasks

    if not await _once("datavault", marker, hours=24):
        return
    to = await _role(conn, "admin") + await _officers(conn, office)
    when = _now()
    for email in _unique(to):
        _queue(tasks.send_datavault_problem, email, what, failure, when)


async def setting_changed(conn: Conn, *, setting: str, actor_id: int | None) -> None:
    """Every administrator and officer, the one who changed it included: an
    inbox told of a change its owner did not make is the alarm against a
    stolen session (as the board list's, 0064)."""
    from cmp.tasks.notifications import updates as tasks

    actor = await _actor(conn, actor_id)
    when = _now()
    for email in await _oversight(conn):
        _queue(tasks.send_settings_changed, email, setting, actor, when)


# ------------------------------------------------- retention reviews (ADR 0047)
_KIND_WORDS = {
    "validity": "Consent validity runs out",
    "retention": "Data must be erased or anonymised",
}


def _review_path(review: Row) -> str:
    return f"/retention/{review['review_uuid']}"


async def _review_officers(conn: Conn, review: Row) -> list[str]:
    return await _officers(conn, review.get("office"))


async def retention_action_asked(conn: Conn, *, action: Row, review: Row) -> None:
    """The one asked, in the console. A link is sent by `retention_link_sent`;
    an action with nobody to ask tells the office instead."""
    from cmp.tasks.notifications import updates as tasks

    if action["channel"] == "link":
        from cmp.domain.retention import links

        await links.send(conn, action=action, review=review)
        return
    if action["channel"] != "console":
        return
    person = await _person(conn, action.get("user_id"))
    if person is None:
        return
    if review["kind"] == "validity":
        ask = (
            "Their consent's validity is running out and the project is still active. "
            "Say whether they should be invited to consent again."
        )
    elif action["kind"] == "owner":
        ask = (
            "The period their data may be kept has run out. Confirm it is erased - or "
            "anonymised, or kept, with the reason - from the project's own systems and sites."
        )
    else:
        ask = (
            f"The period their data may be kept has run out. Confirm {action['label']} has "
            "erased it - or anonymised or kept it, with the reason."
        )
    _queue(
        tasks.send_retention_action_asked,
        person["email"],
        person["full_name"],
        review["reference"],
        review["project_name"],
        review["purpose_name"],
        int(review["people"]),
        ask,
        day(action["due_at"]),
        f"/retention-actions/{action['action_uuid']}",
    )


async def retention_action_answered(conn: Conn, *, review: Row, label: str) -> None:
    from cmp.tasks.notifications import updates as tasks

    for email in await _review_officers(conn, review):
        _queue(
            tasks.send_retention_action_answered,
            email,
            review["reference"],
            label,
            _review_path(review),
        )


async def retention_action_sent_back(conn: Conn, *, action: Row, review: Row) -> None:
    from cmp.tasks.notifications import updates as tasks

    reason = await unseal_value(
        "retention_action", "sent_back_reason", action.get("sent_back_reason")
    )
    if action["channel"] == "link":
        from cmp.domain.retention import links

        await links.send(conn, action=action, review=review, again=str(reason or ""))
        return
    person = await _person(conn, action.get("user_id"))
    if person is not None:
        _queue(
            tasks.send_retention_action_sent_back,
            person["email"],
            review["reference"],
            str(reason or ""),
            day(action["due_at"]),
            f"/retention-actions/{action['action_uuid']}",
        )


async def retention_review_reminder(conn: Conn, *, review: Row, days_left: int) -> None:
    """The officers, and the project's owner."""
    from cmp.db.repositories import retention as retention_repo
    from cmp.tasks.notifications import updates as tasks

    to = set(await _review_officers(conn, review))
    owner = await retention_repo.owner_of(conn, review)
    person = await _person(conn, owner["id"]) if owner else None
    if person is not None:
        to.add(str(person["email"]))
    for email in sorted(to):
        _queue(
            tasks.send_retention_review_reminder,
            email,
            _KIND_WORDS[review["kind"]],
            review["reference"],
            review["project_name"],
            review["purpose_name"],
            int(review["people"]),
            days_left,
            _review_path(review),
        )


async def retention_action_overdue_holder(conn: Conn, *, action: Row, review: Row) -> None:
    from cmp.tasks.notifications import updates as tasks

    if action["channel"] == "link":
        from cmp.domain.retention import links

        await links.send(conn, action=action, review=review, overdue=True)
        return
    person = await _person(conn, action.get("user_id"))
    if person is not None:
        _queue(
            tasks.send_retention_action_overdue,
            person["email"],
            review["reference"],
            day(action["due_at"]),
            f"/retention-actions/{action['action_uuid']}",
        )


async def retention_action_escalated(conn: Conn, *, action: Row, review: Row) -> None:
    from cmp.tasks.notifications import updates as tasks

    for email in await _review_officers(conn, review):
        _queue(
            tasks.send_retention_action_escalated,
            email,
            review["reference"],
            str(action["label"]),
            day(action["due_at"]),
            _review_path(review),
        )


async def retention_erasure_notices(conn: Conn, *, people: list[Row]) -> int:
    """Each person, before their data is erased, at the contact her receipts
    go to. Marked told whether or not a contact was found: there is nobody to
    tell again."""
    from cmp.db.repositories import retention as retention_repo
    from cmp.domain.consent.service import receipt_contact
    from cmp.tasks.notifications import updates as tasks

    told: list[int] = []
    for p in people:
        person = await user_repo.by_id(conn, int(p["auth_user_id"]))
        contact = receipt_contact(person) if person else None
        if contact:
            _queue(
                tasks.send_retention_erasure_notice,
                contact,
                str(p["project_name"]),
                str(p["purpose_name"]),
                day(p["due_at"]),
            )
        told.append(int(p["member_id"]))
    await retention_repo.mark_people(conn, told, "notified_at")
    return len(told)


async def retention_reconsent_invitations(conn: Conn, *, review: Row, link: str) -> int:
    """Everybody still in the review, invited to consent again, at the contact
    her receipts go to."""
    from cmp.db.repositories import retention as retention_repo
    from cmp.domain.consent.service import receipt_contact
    from cmp.tasks.notifications import updates as tasks

    invited: list[int] = []
    for p in await retention_repo.people_of(conn, int(review["review_id"])):
        if p["invited_at"] is not None:
            continue
        person = await user_repo.by_id(conn, int(p["auth_user_id"]))
        contact = receipt_contact(person) if person else None
        if contact:
            _queue(
                tasks.send_retention_reconsent_invite,
                contact,
                str(review["project_name"]),
                str(review["purpose_name"]),
                day(p["due_at"]),
                link,
            )
        invited.append(int(p["member_id"]))
    await retention_repo.mark_people(conn, invited, "invited_at")
    return len(invited)
