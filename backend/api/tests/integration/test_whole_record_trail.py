"""A record's trail is the record's and its parts' (2026-11-12).

The trail names the table each row was written against. Asked about a breach,
it answered with the breach's own rows and left out a ticket assigned on it, a
date moved on that ticket, and what became of each mail of a report - "the
breach's audit trail is minimal". Now:

* filtered to one breach, request or project, the trail also reads the rows
  of what belongs to it - a breach's tickets and the public report it began
  as, a request's holders and items, a project's sites, approvals, links,
  notices, exports and imports - and nobody else's;
* a ticket's own trail is still only the ticket's;
* each mail of a report leaves a row on the breach when it goes or fails,
  naming the list's entry by its uuid and never the address (ADR 0015);
* a ticket's rows carry the breach's reference.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from cmp.core.config import settings
from cmp.core.pagination import PageRequest
from cmp.db.repositories import audit as audit_repo
from cmp.db.repositories import audit_lookup
from cmp.db.repositories import rights as rights_repo
from cmp.db.sql import fetch_one
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.domain.breach import tickets
from tests.integration.test_breach_reports import (
    _board,
    _breach,
    _finalise,
    _nobody_on_the_list,  # noqa: F401 - the board's list starts empty
    _not_reached,
    _queued,
    _reached,
)
from tests.integration.test_breach_tickets import _assign, _id, _recorded
from tests.integration.test_rights_ticket_date import _between, _ticketed

pytestmark = pytest.mark.integration

PAGE = PageRequest(limit=200, cursor=None, sort_field="occurred_at", descending=False)


@pytest.fixture(autouse=True)
def internal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "breach_ticket_email_domains", ("test.local",))


async def _about(conn: Any, entity_type: str, entity_id: int) -> list[dict[str, Any]]:
    rows, _, total = await audit_repo.search(
        conn, PAGE, audit_repo.AuditFilters(entity_type=entity_type, entity_id=entity_id)
    )
    assert total == len(rows)
    return rows


async def _breach_id(conn: Any, uuid: str) -> int:
    found = await audit_lookup.id_for_uuid(conn, "breach", uuid)
    assert found is not None
    return found


async def test_a_breachs_trail_reads_its_tickets_too_and_only_its_own(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _recorded(conn, seeded)
    other = await _recorded(conn, seeded)
    ticket = (await _assign(conn, seeded, uuid))["ticket"]
    theirs = (await _assign(conn, seeded, other, role="rco"))["ticket"]
    await tickets.office_change_date(
        conn,
        breach_uuid=uuid,
        ticket_uuid=str(ticket["ticket_uuid"]),
        answer_by=(datetime.now(UTC) + timedelta(days=4)).date(),
        reason="The log rotates on Friday",
        actor_id=_id(seeded, "dpo"),
    )

    rows = await _about(conn, "breach", await _breach_id(conn, uuid))
    events = [r["event_type"] for r in rows]
    # The breach's own, and what was done on its ticket.
    assert "breach.recorded" in events and "breach.determined" in events
    assert "breach_ticket.assigned" in events and "breach_ticket.date_changed" in events
    # In the order it happened: a trail is a story.
    assert events.index("breach.determined") < events.index("breach_ticket.assigned")
    assert events.index("breach_ticket.assigned") < events.index("breach_ticket.date_changed")
    # Each ticket row says which breach it is on, and carries no words.
    recorded = await fetch_one(
        conn,
        """SELECT r.reference FROM breach_recording r JOIN breach b USING (breach_id)
            WHERE b.breach_uuid = %s""",
        (uuid,),
    )
    assert recorded is not None
    reference = recorded["reference"]
    on_ticket = [r for r in rows if r["entity_type"] == "breach_ticket"]
    assert {r["detail"]["reference"] for r in on_ticket} == {reference}
    assert "rotates" not in str([r["detail"] for r in on_ticket])
    # The other breach's ticket is not this breach's.
    assert str(theirs["ticket_uuid"]) not in {r["detail"].get("ticket") for r in on_ticket}

    # A ticket's own trail is the ticket's alone.
    ticket_id = await audit_lookup.id_for_uuid(conn, "breach_ticket", str(ticket["ticket_uuid"]))
    assert ticket_id is not None
    own = await _about(conn, "breach_ticket", ticket_id)
    assert {r["entity_type"] for r in own} == {"breach_ticket"}
    assert [r["event_type"] for r in own] == [
        "breach_ticket.assigned",
        "breach_ticket.date_changed",
    ]

    # The type alone is still the table alone: every breach's own rows.
    typed, _, _ = await audit_repo.search(conn, PAGE, audit_repo.AuditFilters(entity_type="breach"))
    assert {r["entity_type"] for r in typed} == {"breach"}


async def test_each_mail_of_a_report_leaves_a_row_on_the_breach(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _board(conn, seeded, "chair@example.org", "member@example.org")
    uuid = await _breach(conn, seeded)
    await _finalise(conn, seeded, uuid, "org_board")
    first, second = await _queued(conn, uuid)

    await _reached(conn, first)
    await _reached(conn, first)  # recorded twice, it is there once
    await _not_reached(conn, second)

    rows = await _about(conn, "breach", await _breach_id(conn, uuid))
    went = [r for r in rows if r["event_type"] == Event.BREACH_REPORT_DELIVERED]
    failed = [r for r in rows if r["event_type"] == Event.BREACH_REPORT_FAILED]
    assert len(went) == 1 and len(failed) == 1
    for row in (*went, *failed):
        detail = row["detail"]
        assert detail["kind"] == "org_board" and detail["version"] == 1
        assert row["actor_uuid"] is None, "the worker's entry, nobody's"
        # The list's entry by its uuid; the address is never written.
        assert len(detail["recipient"]) == 36
        assert "example.org" not in str(detail) and "SE::" not in str(detail)
    assert failed[0]["detail"]["error"] == "SMTPDataError"
    assert went[0]["detail"]["recipient"] != failed[0]["detail"]["recipient"]
    # After the report was finalised, in the story.
    events = [r["event_type"] for r in rows]
    assert events.index("breach.report_finalised") < events.index(Event.BREACH_REPORT_DELIVERED)


async def test_a_requests_trail_reads_its_holders_tickets(
    conn: Any, seeded: dict[str, Any]
) -> None:
    from cmp.core.permissions import Role
    from cmp.domain.rights import service as rights

    row, holder = await _ticketed(conn, seeded)
    await rights.change_ticket_date(
        conn,
        row,
        holder_uuid=str(holder["holder_uuid"]),
        due_at=_between(row, holder),
        reason="Their archive is offline",
        role=Role.DPO,
        actor_id=_id(seeded, "dpo"),
    )
    rows = await _about(conn, "rights_request", int(row["request_id"]))
    kinds = {r["entity_type"] for r in rows}
    assert {"rights_request", "rights_request_holder"} <= kinds
    assert "rights.ticket_date_changed" in [r["event_type"] for r in rows]
    assert {r["detail"]["reference"] for r in rows} == {row["reference"]}

    # One holder's ticket can be asked about by its uuid.
    holder_id = await audit_lookup.id_for_uuid(
        conn, "rights_request_holder", str(holder["holder_uuid"])
    )
    assert holder_id == int(holder["holder_id"])
    own = await _about(conn, "rights_request_holder", holder_id)
    assert own and {r["entity_type"] for r in own} == {"rights_request_holder"}
    assert await rights_repo.holder_by_uuid(
        conn, int(row["request_id"]), str(holder["holder_uuid"])
    )


async def test_a_projects_trail_reads_its_sites_and_notices_and_not_every_visit(
    conn: Any, seeded: dict[str, Any]
) -> None:
    project_id = int(seeded["project"]["project_id"])
    dpo = _id(seeded, "dpo")
    link = await fetch_one(
        conn,
        "SELECT link_id FROM consent_link WHERE site_id = %s LIMIT 1",
        (seeded["site"]["site_id"],),
    )
    assert link is not None
    for event, entity_type, entity_id in (
        (Event.PROJECT_UPDATED, "project", project_id),
        (Event.SITE_CREATED, "project_site", int(seeded["site"]["site_id"])),
        (Event.NOTICE_PUBLISHED, "notice", int(seeded["notice"]["notice_id"])),
        (Event.LINK_CREATED, "consent_link", int(link["link_id"])),
        (Event.LINK_OPENED, "consent_link", int(link["link_id"])),
    ):
        await audit.record(
            conn, event=event, entity_type=entity_type, entity_id=entity_id, actor_user_id=dpo
        )

    rows = await _about(conn, "project", project_id)
    events = {r["event_type"] for r in rows}
    assert {"project.updated", "site.created", "notice.published", "link.created"} <= events
    # Every visit to a link is the link's own trail, not the project's story.
    assert "link.opened" not in events
