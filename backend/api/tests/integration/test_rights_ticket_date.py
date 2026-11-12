"""A rights ticket's answer-by date can be moved, with the reason (2026-11-12).

A breach ticket's date could be moved by either side, with a reason; a rights
ticket's could only be set when it was sent, or again when it was sent back.
Now the office or the holder moves it while the ticket waits, and:

* the reason is required, the date is ahead, differs from the one it has,
  and never falls after the response the ticket feeds;
* it is on the ticket's thread and contact log in words, and on the trail
  with the two dates, which side moved it and that a reason was given - the
  words stay on the ticket (ADR 0015), and a member of staff reading the
  trail is shown them from there;
* the other side is told;
* a ticket that had its final reminder waits again from the new date.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.core.permissions import Role
from cmp.db.repositories import audit as audit_repo
from cmp.db.repositories import entities as entity_repo
from cmp.db.repositories import rights as repo
from cmp.domain.rights import service
from cmp.domain.rights import tickets as ticket_view
from tests.conftest import plain
from tests.integration.test_rights_flows import (
    _consent,
    _export_with_her,
    _portal_request,
    _started,
)

pytestmark = pytest.mark.integration

DPO = Role.DPO


async def _ticketed(
    conn: Any, seeded: dict[str, Any], *, in_console: bool = False
) -> tuple[dict[str, Any], dict[str, Any]]:
    """A request with one ticket sent - by email, or to the seeded RCO's console."""
    dpo = int(seeded["users"]["dpo"]["id"])
    consent = await _consent(conn, seeded)
    await _export_with_her(conn, seeded, consent["consent_id"])
    row = await _started(conn, seeded, await _portal_request(conn, seeded, "access"))
    [holder] = await service.derive_holders(conn, row, role=DPO, actor_id=dpo)
    await service.confirm_holder(
        conn,
        row,
        holder_uuid=str(holder["holder_uuid"]),
        responder_name="Records team",
        responder_contact="records@processor.example",
        role=DPO,
        actor_id=dpo,
    )
    await service.issue_tickets(conn, row, instruction=None, due_at=None, role=DPO, actor_id=dpo)
    if in_console:
        await repo.update_holder(
            conn,
            int(holder["holder_id"]),
            channel="portal",
            responder_user_id=int(seeded["users"]["rco"]["id"]),
        )
    row = await service.reload(conn, row)
    fresh = await repo.holder_by_uuid(conn, int(row["request_id"]), str(holder["holder_uuid"]))
    assert fresh is not None and fresh["ticket_status"] == "issued"
    return row, fresh


def _between(row: dict[str, Any], holder: dict[str, Any]) -> datetime:
    """A date after the ticket's and before the response's."""
    return holder["due_at"] + (row["due_at"] - holder["due_at"]) / 2


async def test_the_office_moves_the_date_and_the_reason_is_on_the_thread_and_the_trail(
    conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[tuple[Any, ...]] = []
    monkeypatch.setattr(service, "_dispatch", lambda *a: sent.append(a))
    dpo = int(seeded["users"]["dpo"]["id"])
    row, holder = await _ticketed(conn, seeded)
    assert "change_date" in {
        m["move"] for m in ticket_view.moves(holder, request_status=row["status"])
    }
    was, when = holder["due_at"], _between(row, holder)

    moved = await service.change_ticket_date(
        conn,
        row,
        holder_uuid=str(holder["holder_uuid"]),
        due_at=when,
        reason="  Their archive is offline until Friday.  ",
        role=DPO,
        actor_id=dpo,
    )
    assert moved["due_at"] == when and moved["ticket_status"] == "issued"

    # In words, on the thread and the contact log.
    messages = await repo.messages_of(conn, int(holder["holder_id"]))
    last = messages[-1]
    assert last["author_side"] == "office" and last["kind"] == "status"
    said = plain(last["body"])
    assert said == (
        f"Answer by changed from {was.day} {was:%B %Y} to {when.day} {when:%B %Y}: "
        "Their archive is offline until Friday."
    )
    assert moved["contact_log"][-1]["kind"] == "date_changed"

    # On the trail: both dates, the side, and that a reason was given - with
    # the message that keeps the words, and none of the words (ADR 0015).
    trail = await audit_repo.for_reference(conn, row["reference"], limit=30)
    [event] = [e for e in trail if e["event_type"] == "rights.ticket_date_changed"]
    detail = event["detail"]
    assert detail["side"] == "office" and detail["label"] == holder["label"]
    assert "channel" not in detail
    assert detail["date_before"] == was.isoformat() and detail["date_after"] == when.isoformat()
    assert detail["reason_given"] is True and "reason" not in detail
    assert detail["message_uuid"] == str(last["message_uuid"])
    assert "archive" not in str(detail) and "SE::" not in str(detail)
    assert event["actor_uuid"] == seeded["users"]["dpo"]["uuid"]

    # Whoever reads the trail is shown the words, from the ticket: sealed, and
    # the same sentence the thread holds, with the reason after the dates.
    [shown] = await entity_repo.attach(conn, [dict(event)], reader_role=DPO)
    assert shown["reason"].startswith("SE::")
    assert ticket_view.date_change_reason(plain(shown["reason"])) == (
        "Their archive is offline until Friday."
    )
    # A data principal reading her own trail is not: these are not her words to read.
    [hers] = await entity_repo.attach(conn, [dict(event)], for_subject=True)
    assert "reason" not in hers
    # A trail row about anything else carries no reason at all.
    other = next(e for e in trail if e["event_type"] != "rights.ticket_date_changed")
    [plain_row] = await entity_repo.attach(conn, [dict(other)], reader_role=DPO)
    assert "reason" not in plain_row

    # The holder is told, the way a ticket message reaches them.
    assert any(a[0] in ("send_ticket_message", "send_holder_link") for a in sent)


async def test_a_date_needs_a_reason_and_has_to_make_sense(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    row, holder = await _ticketed(conn, seeded)

    async def move(due_at: datetime, reason: str = "More time") -> Any:
        return await service.change_ticket_date(
            conn,
            row,
            holder_uuid=str(holder["holder_uuid"]),
            due_at=due_at,
            reason=reason,
            role=DPO,
            actor_id=dpo,
        )

    with pytest.raises(ValidationFailed) as no_reason:
        await move(_between(row, holder), "   ")
    assert no_reason.value.field == "reason"
    with pytest.raises(ValidationFailed, match="already passed"):
        await move(datetime.now(UTC) - timedelta(hours=1))
    with pytest.raises(ValidationFailed, match="after the response itself"):
        await move(row["due_at"] + timedelta(days=1))
    with pytest.raises(ValidationFailed, match="already has"):
        await move(holder["due_at"] + timedelta(minutes=5))
    with pytest.raises(NotFound):
        await service.change_ticket_date(
            conn,
            row,
            holder_uuid="00000000-0000-4000-8000-000000000000",
            due_at=_between(row, holder),
            reason="More time",
            role=DPO,
            actor_id=dpo,
        )
    # Nothing was moved or recorded by any of them.
    same = await repo.holder_by_uuid(conn, int(row["request_id"]), str(holder["holder_uuid"]))
    assert same is not None and same["due_at"] == holder["due_at"]
    trail = await audit_repo.for_reference(conn, row["reference"], limit=30)
    assert not [e for e in trail if e["event_type"] == "rights.ticket_date_changed"]


async def test_the_holder_moves_their_own_date_and_the_office_is_told(
    conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[tuple[Any, ...]] = []
    monkeypatch.setattr(service, "_dispatch", lambda *a: sent.append(a))
    rco = int(seeded["users"]["rco"]["id"])
    row, holder = await _ticketed(conn, seeded, in_console=True)
    mine = await repo.ticket_for_user(conn, rco, str(holder["holder_uuid"]))
    assert mine is not None and ticket_view.holder_view(mine)["may_change_date"] is True
    when = _between(row, holder)

    moved = await service.change_own_ticket_date(
        conn, user_id=rco, holder_uuid=str(holder["holder_uuid"]), due_at=when, reason="On leave"
    )
    assert moved["due_at"] == when
    last = (await repo.messages_of(conn, int(holder["holder_id"])))[-1]
    assert last["author_side"] == "holder" and plain(last["body"]).endswith(": On leave")
    trail = await audit_repo.for_reference(conn, row["reference"], limit=30)
    [event] = [e for e in trail if e["event_type"] == "rights.ticket_date_changed"]
    assert event["detail"]["side"] == "holder" and event["detail"]["channel"] == "portal"
    assert event["actor_uuid"] == seeded["users"]["rco"]["uuid"]
    assert event["detail"]["reason_given"] is True and "reason" not in event["detail"]
    [shown] = await entity_repo.attach(conn, [dict(event)], reader_role=DPO)
    assert ticket_view.date_change_reason(plain(shown["reason"])) == "On leave"
    # The office's officers hear of it.
    assert [a for a in sent if a[0] == "send_ticket_message"]

    # By the ticket's link nobody with an account did it: no actor, channel `link`.
    again = await repo.ticket_for_user(conn, rco, str(holder["holder_uuid"]))
    assert again is not None
    await service.change_date_as_holder(
        conn, again, author_id=None, due_at=when - timedelta(days=1), reason="Sooner after all"
    )
    trail = await audit_repo.for_reference(conn, row["reference"], limit=30)
    by_link = next(
        e
        for e in trail
        if e["event_type"] == "rights.ticket_date_changed" and e["detail"].get("channel") == "link"
    )
    assert by_link["actor_uuid"] is None and by_link["detail"]["side"] == "holder"

    # Somebody else's ticket is not found, not forbidden.
    with pytest.raises(NotFound):
        await service.change_own_ticket_date(
            conn,
            user_id=int(seeded["users"]["dco"]["id"]),
            holder_uuid=str(holder["holder_uuid"]),
            due_at=when + timedelta(days=1),
            reason="Not mine",
        )


async def test_only_a_ticket_that_waits_on_its_holder_has_a_date_to_move(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    rco = int(seeded["users"]["rco"]["id"])
    row, holder = await _ticketed(conn, seeded, in_console=True)
    await service.return_own_ticket(
        conn,
        user_id=rco,
        holder_uuid=str(holder["holder_uuid"]),
        summary="Exported everything",
        outcome="done",
        evidence_ref=None,
        evidence_hash=None,
    )
    answered = await repo.ticket_for_user(conn, rco, str(holder["holder_uuid"]))
    assert answered is not None and ticket_view.holder_view(answered)["may_change_date"] is False
    assert "change_date" not in {
        m["move"] for m in ticket_view.moves(answered, request_status="awaiting_holders")
    }
    with pytest.raises(Conflict):
        await service.change_own_ticket_date(
            conn,
            user_id=rco,
            holder_uuid=str(holder["holder_uuid"]),
            due_at=_between(row, holder),
            reason="Too late",
        )
    with pytest.raises(Conflict):
        await service.change_ticket_date(
            conn,
            await service.reload(conn, row),
            holder_uuid=str(holder["holder_uuid"]),
            due_at=_between(row, holder),
            reason="Too late",
            role=DPO,
            actor_id=dpo,
        )


async def test_a_ticket_past_its_final_reminder_waits_again_from_the_new_date(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    row, holder = await _ticketed(conn, seeded)
    # Overdue, and the final reminder sent.
    await repo.update_holder(
        conn, int(holder["holder_id"]), due_at=datetime.now(UTC) - timedelta(days=2)
    )
    await service.escalate_ticket(
        conn, row, holder_uuid=str(holder["holder_uuid"]), role=DPO, actor_id=dpo
    )
    late = await repo.holder_by_uuid(conn, int(row["request_id"]), str(holder["holder_uuid"]))
    assert late is not None and ticket_view.state(late) == "final_reminder"

    when = datetime.now(UTC) + timedelta(days=3)
    moved = await service.change_ticket_date(
        conn,
        await service.reload(conn, row),
        holder_uuid=str(holder["holder_uuid"]),
        due_at=when,
        reason="They asked for three more days",
        role=DPO,
        actor_id=dpo,
    )
    assert moved["ticket_status"] == "issued" and moved["escalated_at"] is None
    assert ticket_view.state(moved) == "waiting"
