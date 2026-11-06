"""How the office has set the breach workflow up (0058).

Two things, kept by the administrator, the DPO and Legal:

* **who is told of a report from the public link**: a list of roles. The two
  officers are always on it - a report nobody who may claim it hears of would
  wait for ever. Anybody else it names is told a report arrived, and can do no
  more about it than their role already allows.
* **the organisation's board**: the addresses its reports are mailed to.

Neither says anything about a breach, so the administrator may keep them
without seeing one. The trail says what changed, never an address.
"""

from __future__ import annotations

from typing import Any

from pydantic import TypeAdapter, ValidationError

from cmp.core.config import settings as app_settings
from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.db.repositories import incident_reports as repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.domain.breach import intake, reports
from cmp.validation.contacts import Email

Row = dict[str, Any]

_EMAIL = TypeAdapter(Email)


async def _trail(conn: Conn, *, actor_id: int, detail: dict[str, Any]) -> None:
    await audit.record(
        conn,
        event=Event.BREACH_SETTINGS_CHANGED,
        entity_type="breach_settings",
        entity_id=1,
        actor_user_id=actor_id,
        detail=detail,
    )


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
    try:
        address = str(_EMAIL.validate_python((email or "").strip())).lower()
    except ValidationError:
        raise ValidationFailed("That is not an email address", field="email") from None
    made = await repo.add_board_recipient(
        conn,
        full_name=(full_name or "").strip() or None,
        email=address,
        added_by=actor_id,
    )
    if made is None:
        raise Conflict("That address is on the list already", code="recipient_exists")
    await _trail(
        conn,
        actor_id=actor_id,
        detail={"board_recipient": "added", "recipient": str(made["recipient_uuid"])},
    )
    return await overview(conn)


async def remove_board_recipient(conn: Conn, *, recipient_uuid: str, actor_id: int) -> Row:
    gone = await repo.remove_board_recipient(conn, recipient_uuid, removed_by=actor_id)
    if gone is None:
        raise NotFound("Recipient")
    await _trail(
        conn,
        actor_id=actor_id,
        detail={"board_recipient": "removed", "recipient": recipient_uuid},
    )
    await reports.taken_off(conn, recipient_uuid)
    return await overview(conn)
