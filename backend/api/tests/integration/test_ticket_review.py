"""Rights tickets, reworked (2026-10-08).

An answer from a holder waits for the office: it counts - toward collating,
toward an erasure - only once accepted. An answer the office records for a
holder counts as recorded. A withdrawn ticket reopens with a new date; a holder
found by mistake goes before anything is sent to it; a final reminder is only
for a ticket past its date; a team is told when its ticket is answered for it,
accepted, or moved; nobody writes on a closed request.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from cmp.core.errors import Conflict
from cmp.db.repositories import rights as repo
from cmp.domain.rights import service
from tests.integration.test_holder_respondents import TestChannels

pytestmark = pytest.mark.integration


async def _issued(conn: Any, seeded: dict[str, Any]) -> tuple[dict, dict, dict]:
    return await TestChannels._issued(TestChannels(), conn, seeded)


def _dpo(seeded: dict[str, Any]) -> int:
    return int(seeded["users"]["dpo"]["id"])


async def test_a_teams_answer_waits_for_review_and_counts_once_accepted(
    conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, sent: list[Any]
) -> None:
    row, mailed, portal = await _issued(conn, seeded)
    dco = int(seeded["users"]["dco"]["id"])
    await service.withdraw_ticket(
        conn,
        row,
        holder_uuid=str(mailed["holder_uuid"]),
        reason="Holds nothing",
        role="dpo",
        actor_id=_dpo(seeded),
    )
    answered = await service.return_own_ticket(
        conn,
        user_id=dco,
        holder_uuid=str(portal["holder_uuid"]),
        summary="Nothing held.",
        outcome="done",
        evidence_ref=None,
        evidence_hash=None,
    )
    assert answered["accepted_at"] is None
    fresh = await service.reload(conn, row)
    assert fresh["status"] == "awaiting_holders" and fresh["tickets_to_review"] == 1
    [holder] = [
        h
        for h in await repo.holders_of(conn, int(row["request_id"]))
        if h["holder_uuid"] == portal["holder_uuid"]
    ]
    assert holder["accepted_at"] is None

    sent.clear()
    accepted = await service.accept_ticket(
        conn, fresh, holder_uuid=str(portal["holder_uuid"]), role="dpo", actor_id=_dpo(seeded)
    )
    assert accepted["accepted_at"] is not None
    assert (await service.reload(conn, row))["status"] == "collating"
    # The team is told, in the console.
    assert [n for n, _ in sent] == ["send_ticket_message"]
    with pytest.raises(Conflict):
        await service.accept_ticket(
            conn,
            await service.reload(conn, row),
            holder_uuid=str(portal["holder_uuid"]),
            role="dpo",
            actor_id=_dpo(seeded),
        )


async def test_an_answer_the_office_records_counts_as_recorded_and_the_team_is_told(
    conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, sent: list[Any]
) -> None:
    row, _mailed, portal = await _issued(conn, seeded)
    sent.clear()
    recorded = await service.return_ticket(
        conn,
        row,
        holder_uuid=str(portal["holder_uuid"]),
        summary="Told us by phone: nothing.",
        outcome="done",
        evidence_ref=None,
        evidence_hash=None,
        role="dpo",
        actor_id=_dpo(seeded),
    )
    assert recorded["accepted_at"] is not None
    assert "send_ticket_message" in [n for n, _ in sent]


async def test_a_withdrawn_ticket_reopens_with_a_new_date(
    conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, sent: list[Any]
) -> None:
    row, mailed, _portal = await _issued(conn, seeded)
    await service.withdraw_ticket(
        conn,
        row,
        holder_uuid=str(mailed["holder_uuid"]),
        reason="By mistake",
        role="dpo",
        actor_id=_dpo(seeded),
    )
    due = (datetime.now(UTC) + timedelta(days=5)).date()
    sent.clear()
    reopened = await service.reopen_ticket(
        conn,
        await service.reload(conn, row),
        holder_uuid=str(mailed["holder_uuid"]),
        due_on=due,
        role="dpo",
        actor_id=_dpo(seeded),
    )
    assert reopened["ticket_status"] == "issued" and reopened["due_at"].date() == due
    # An outside holder is told by its link, in words that carry nothing of the request.
    [(_name, args)] = [(n, a) for n, a in sent if n == "send_holder_link"]
    assert args[3] == "The Privacy Office has opened this ticket again."
    with pytest.raises(Conflict):
        await service.reopen_ticket(
            conn,
            await service.reload(conn, row),
            holder_uuid=str(mailed["holder_uuid"]),
            due_on=due,
            role="dpo",
            actor_id=_dpo(seeded),
        )


async def test_a_final_reminder_only_once_overdue(
    conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, sent: list[Any]
) -> None:
    row, mailed, _portal = await _issued(conn, seeded)
    with pytest.raises(Conflict) as early:
        await service.escalate_ticket(
            conn, row, holder_uuid=str(mailed["holder_uuid"]), role="dpo", actor_id=_dpo(seeded)
        )
    assert early.value.code == "ticket_not_overdue"
    await repo.update_holder(
        conn, int(mailed["holder_id"]), due_at=datetime.now(UTC) - timedelta(days=2)
    )
    sent.clear()
    done = await service.escalate_ticket(
        conn, row, holder_uuid=str(mailed["holder_uuid"]), role="dpo", actor_id=_dpo(seeded)
    )
    assert done["ticket_status"] == "escalated"
    [(_name, args)] = [s for s in sent if s[0] == "send_ticket_reminder"]
    assert args[-1] is True  # marked final


async def test_a_holder_found_by_mistake_goes_before_anything_is_sent(
    conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
) -> None:
    row, mailed, _portal = await _issued(conn, seeded)
    with pytest.raises(Conflict) as sent_already:
        await service.remove_holder(
            conn, row, holder_uuid=str(mailed["holder_uuid"]), role="dpo", actor_id=_dpo(seeded)
        )
    assert sent_already.value.code == "holder_in_use"
    extra = await service.add_holder(
        conn,
        row,
        label="Somebody else",
        processor_uuid=None,
        responder_name="A. Person",
        responder_contact="a.person@example.org",
        role="dpo",
        actor_id=_dpo(seeded),
    )
    await service.remove_holder(
        conn, row, holder_uuid=str(extra["holder_uuid"]), role="dpo", actor_id=_dpo(seeded)
    )
    assert str(extra["holder_uuid"]) not in {
        str(h["holder_uuid"]) for h in await repo.holders_of(conn, int(row["request_id"]))
    }


async def test_moving_a_ticket_tells_whoever_had_it(
    conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, sent: list[Any]
) -> None:
    row, mailed, _portal = await _issued(conn, seeded)
    sent.clear()
    await service.reassign_holder(
        conn,
        row,
        holder_uuid=str(mailed["holder_uuid"]),
        respondent_uuid=None,
        responder_name="New Person",
        responder_contact="new.person@third.example",
        role="dpo",
        actor_id=_dpo(seeded),
    )
    told = [args for name, args in sent if name == "send_holder_link"]
    assert told and "passed this ticket to someone else" in told[0][3]
