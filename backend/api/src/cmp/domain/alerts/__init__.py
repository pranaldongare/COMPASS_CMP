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
from cmp.core.permissions import ROLE_TITLES
from cmp.db.redis import K_CACHE, get_redis
from cmp.db.redis import key as rkey
from cmp.db.repositories import alerts as repo
from cmp.db.repositories import users as user_repo
from cmp.db.sql import Conn

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


async def rights_received(conn: Conn, request: Row) -> None:
    """A request arrived from outside the office: every DPO. Never her words."""
    from cmp.tasks.notifications import alerts as tasks

    if request.get("channel") == "staff_logged":
        return
    for email in await _role(conn, "dpo"):
        _queue(
            tasks.send_rights_request_received,
            email,
            str(request["reference"]),
            KINDS.get(str(request["request_type"]), str(request["request_type"])),
            CHANNELS.get(str(request["channel"]), str(request["channel"])),
            day(request.get("due_at")),
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
    when there is nothing on it. Returns how many requests it listed."""
    from cmp.tasks.notifications import alerts as tasks

    rows = await repo.rights_due_within(conn, RIGHTS_DUE_WITHIN_DAYS)
    if not rows:
        return 0
    at = now or datetime.now(UTC)
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
    for email in await _role(conn, "dpo"):
        _queue(tasks.send_rights_due_digest, email, len(rows), "\n".join(lines))
    return len(rows)


# -------------------------------------------------------------------- breach


async def breach_duties(conn: Conn, *, now: datetime | None = None) -> int:
    """Every dated duty of an open breach that is about to fall due, or has:
    every DPO, once per duty per stage. Returns how many alerts it queued.

    "About to" is the last sixth of the duty's window, at least five minutes:
    ten minutes of the board's thirty, an hour of CERT-In's six, twelve of the
    report's seventy-two. Each alert is remembered for thirty days in Redis, so
    the sweep running every five minutes says each thing once.
    """
    from cmp.domain.breach import clock
    from cmp.domain.breach import service as breach_service
    from cmp.tasks.notifications import alerts as tasks

    at = now or datetime.now(UTC)
    queued = 0
    redis = get_redis()
    dpos: list[str] | None = None
    for breach in await repo.open_breaches_with_dated_duties(conn):
        duties = await breach_service.duties_of(conn, int(breach["breach_id"]))
        for kind, (row, folded) in duties.items():
            due = folded.get("due_at")
            if folded.get("state") != clock.State.OUTSTANDING or due is None:
                continue
            anchored = row.get("anchored_at") or row.get("created_at") or due
            lead = max(timedelta(minutes=5), (due - anchored) / 6)
            if at >= due:
                stage, state = "overdue", f"overdue since {moment(due)}"
            elif at >= due - lead:
                minutes = int((due - at).total_seconds() // 60) or 1
                left = f"{minutes} minutes" if minutes < 120 else f"{minutes // 60} hours"
                stage, state = "due_soon", f"due in {left}"
            else:
                continue
            marker = rkey(K_CACHE, "alert", "breach_duty", str(row["obligation_id"]), stage)
            if not await redis.set(marker, "1", nx=True, ex=30 * 24 * 3600):
                continue
            if dpos is None:
                dpos = await _role(conn, "dpo")
            for email in dpos:
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

    words = {"done": "done", "partial": "partly done", "failed": "could not be done"}
    for email in await _role(conn, "dpo"):
        _queue(
            tasks.send_breach_ticket_returned,
            email,
            str(breach.get("breach_reference") or breach["reference"]),
            holder_name,
            words.get(outcome, outcome),
            str(breach["breach_uuid"]),
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
