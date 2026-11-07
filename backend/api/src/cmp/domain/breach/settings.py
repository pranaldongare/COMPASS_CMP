"""How the office has set the breach workflow up (0058).

Two things, kept by the administrator, the DPO and Legal:

* **who is told of a report from the public link**: a list of roles. The two
  officers are always on it - a report nobody who may claim it hears of would
  wait for ever. Anybody else it names is told a report arrived, and can do no
  more about it than their role already allows.
* **the organisation's board**: the addresses each report's send window offers
  (2026-11-07). The sender may leave out any that is not mandatory, or add one
  for that report alone. An entry may be made mandatory: it then goes with
  every report and cannot be taken off the list until it is made optional
  again. Every change to the list mails the officers of both offices, naming
  the address, since anybody who keeps the list could otherwise add their own
  and tell nobody (ADR 0037). It names no breach, so it crosses the wall
  between the offices.

Neither says anything about a breach, so the administrator may keep them
without seeing one. The trail says what changed, never an address.
"""

from __future__ import annotations

from typing import Any

from cmp.core.config import settings as app_settings
from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.db.repositories import incident_reports as repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.domain.breach import intake, reports

Row = dict[str, Any]


async def _trail(conn: Conn, *, actor_id: int, detail: dict[str, Any]) -> None:
    await audit.record(
        conn,
        event=Event.BREACH_SETTINGS_CHANGED,
        entity_type="breach_settings",
        entity_id=1,
        actor_user_id=actor_id,
        detail=detail,
    )


async def _officers_told(conn: Conn, *, change: str, recipient: Row, actor_id: int) -> None:
    from cmp.domain import alerts

    await alerts.board_list_changed(conn, change=change, recipient=recipient, actor_id=actor_id)


async def _broker() -> None:
    """The officers' mail is the check on the list, so a change it could not
    be queued for is refused, before anything is written. A broker lost between
    this and the commit is logged at error by `dispatch_optional`."""
    from cmp.tasks.dispatch import ensure_broker

    await ensure_broker()


async def overview(conn: Conn) -> Row:
    found = await repo.settings(conn)
    return {
        "intake_roles": list(found["intake_roles"]),
        "roles": intake.role_titles(),
        "officers": list(intake.OFFICERS),
        "board_recipients": await repo.board_recipients(conn),
        "report_link": report_link(),
    }


def report_link() -> str:
    """The one public link: given out to anybody, on any page, for ever."""
    return f"{app_settings.public_base_url.rstrip('/')}/report-incident"


async def set_intake_roles(conn: Conn, *, roles: list[str], actor_id: int) -> Row:
    known = {r["role"] for r in intake.role_titles()}
    unknown = sorted(set(roles) - known)
    if unknown:
        raise ValidationFailed(f"Not a role: {', '.join(unknown)}", field="roles")
    chosen = sorted({*roles, *intake.OFFICERS})
    await repo.set_intake_roles(conn, chosen, updated_by=actor_id)
    await _trail(conn, actor_id=actor_id, detail={"intake_roles": chosen})
    return await overview(conn)


async def add_board_recipient(
    conn: Conn, *, full_name: str | None, email: str, actor_id: int
) -> Row:
    address = reports.board_address(email, field="email")
    name = reports.board_name(full_name, field="full_name")
    await _broker()
    made = await repo.add_board_recipient(conn, full_name=name, email=address, added_by=actor_id)
    if made is None:
        raise Conflict("That address is on the list already", code="recipient_exists")
    await _trail(
        conn,
        actor_id=actor_id,
        detail={"board_recipient": "added", "recipient": str(made["recipient_uuid"])},
    )
    await _officers_told(conn, change="added", recipient=made, actor_id=actor_id)
    return await overview(conn)


async def remove_board_recipient(conn: Conn, *, recipient_uuid: str, actor_id: int) -> Row:
    """Taken off, it is offered to no report again. A mandatory entry must be
    made optional first: every report goes to it until somebody says it need
    not, and that is a change of its own, which both officers hear of."""
    found = await repo.board_recipient(conn, recipient_uuid, lock=True)
    if found is None:
        raise NotFound("Recipient")
    if found["mandatory"]:
        raise Conflict(
            "This address is mandatory, so every report goes to it. Make it optional before "
            "taking it off the list",
            code="recipient_mandatory",
        )
    await _broker()
    gone = await repo.remove_board_recipient(conn, recipient_uuid, removed_by=actor_id)
    assert gone is not None, "held since it was read"
    await _trail(
        conn,
        actor_id=actor_id,
        detail={"board_recipient": "removed", "recipient": recipient_uuid},
    )
    await _officers_told(conn, change="removed", recipient=found, actor_id=actor_id)
    await reports.taken_off(conn, recipient_uuid)
    return await overview(conn)


async def set_board_recipient_mandatory(
    conn: Conn, *, recipient_uuid: str, mandatory: bool, actor_id: int
) -> Row:
    """Make an entry go with every report, or let the sender leave it out
    again. A finalise holds the list while it reads it, so this waits for one
    under way, and applies from the next. Unchanged, it records nothing and
    tells nobody."""
    found = await repo.board_recipient(conn, recipient_uuid, lock=True)
    if found is None:
        raise NotFound("Recipient")
    if bool(found["mandatory"]) == mandatory:
        return await overview(conn)
    await _broker()
    await repo.mark_board_recipient(
        conn, int(found["recipient_id"]), mandatory=mandatory, recorded_by=actor_id
    )
    await _trail(
        conn,
        actor_id=actor_id,
        detail={
            "board_recipient": "made_mandatory" if mandatory else "made_optional",
            "recipient": recipient_uuid,
        },
    )
    await _officers_told(
        conn, change="mandatory" if mandatory else "optional", recipient=found, actor_id=actor_id
    )
    return await overview(conn)
