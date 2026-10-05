"""Breach tickets (S3-08, ADR 0023).

The DPO asks the people who must act; they answer on a thread and return the
ticket; only the DPO closes it. Internal staff only, on a recorded breach, one
ticket per person. A holder sees their ticket and nothing of the register.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from typing import Any

import psycopg
import pytest

from cmp.api.routers.v1 import dashboard
from cmp.core.config import settings
from cmp.core.errors import Conflict, NotFound, TransitionNotPermitted, ValidationFailed
from cmp.db.sql import fetch_all, fetch_one
from cmp.domain.breach import service, tickets
from cmp.domain.breach.tickets import HOLDER_KEYS
from cmp.tasks import dispatch as dispatch_mod
from tests.conftest import plain
from tests.integration.test_breach_register import tell_org_board

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def internal(monkeypatch: pytest.MonkeyPatch) -> None:
    """The seeded staff are on test.local; that is the organisation here."""
    monkeypatch.setattr(settings, "breach_ticket_email_domains", ("test.local",))


@pytest.fixture
def mailed(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, tuple[Any, ...]]]:
    sent: list[tuple[str, tuple[Any, ...]]] = []

    def capture(task: Any, *args: Any, **kwargs: Any) -> str:
        sent.append((task.name, args))
        return "queued-in-a-test"

    monkeypatch.setattr(dispatch_mod, "dispatch_optional", capture)
    return sent


def _today() -> date:
    return datetime.now(UTC).date()


def _id(seeded: dict[str, Any], role: str) -> int:
    return int(seeded["users"][role]["id"])


def _uuid(seeded: dict[str, Any], role: str) -> str:
    return str(seeded["users"][role]["uuid"])


async def _recorded(conn: Any, seeded: dict[str, Any]) -> str:
    """An incident validated yes: a recorded breach, open."""
    made = await service.record(
        conn,
        title="Lab share left open",
        detected_at=datetime.now(UTC) - timedelta(hours=2),
        began_at=None,
        location_kind="platform",
        processor_uuid=None,
        source_uuid=None,
        location_detail=None,
        actor_id=_id(seeded, "dpo"),
    )
    uuid = str(made["breach_uuid"])
    await service.determine(
        conn,
        breach_uuid=uuid,
        outcome="yes",
        reasoning="Names on the share",
        became_aware_at=datetime.now(UTC) - timedelta(hours=1),
        actor_id=_id(seeded, "dpo"),
    )
    return uuid


async def _assign(
    conn: Any, seeded: dict[str, Any], uuid: str, role: str = "dco", **kw: Any
) -> dict[str, Any]:
    return await tickets.assign(
        conn,
        breach_uuid=uuid,
        user_uuid=_uuid(seeded, role),
        instruction=kw.pop("instruction", "Confirm the share's access log is preserved"),
        answer_by=kw.pop("answer_by", None),
        actor_id=_id(seeded, "dpo"),
    )


async def _return(conn: Any, seeded: dict[str, Any], ticket_uuid: str, role: str = "dco") -> Any:
    return await tickets.return_ticket(
        conn,
        user_id=_id(seeded, role),
        ticket_uuid=ticket_uuid,
        summary="Log exported and kept",
        outcome="done",
    )


async def _move(
    conn: Any, seeded: dict[str, Any], uuid: str, ticket_uuid: str, move: str, reason: Any = None
) -> dict[str, Any]:
    return await tickets.office_move(
        conn,
        breach_uuid=uuid,
        ticket_uuid=ticket_uuid,
        move=move,
        reason=reason,
        actor_id=_id(seeded, "dpo"),
    )


async def test_a_ticket_waits_for_the_breach_to_be_recorded(
    conn: Any, seeded: dict[str, Any], mailed: list[Any]
) -> None:
    """Written first. A ticket reaches a person on the breach's account, so -
    like the principals' notice - it waits for the first yes (BD-10)."""
    made = await service.record(
        conn,
        title="Something odd in the logs",
        detected_at=datetime.now(UTC) - timedelta(minutes=10),
        began_at=None,
        location_kind="platform",
        processor_uuid=None,
        source_uuid=None,
        location_detail=None,
        actor_id=_id(seeded, "dpo"),
    )
    with pytest.raises(Conflict) as refused:
        await _assign(conn, seeded, str(made["breach_uuid"]))
    assert refused.value.code == "breach_not_recorded"
    assert not mailed


async def test_assigning_opens_a_ticket_and_tells_the_holder_nothing_of_the_breach(
    conn: Any, seeded: dict[str, Any], mailed: list[Any]
) -> None:
    uuid = await _recorded(conn, seeded)
    by = _today() + timedelta(days=3)
    made = await _assign(conn, seeded, uuid, answer_by=by)
    ticket = made["ticket"]
    assert ticket["state"] == "issued" and ticket["answer_by"] == by
    assert [m["move"] for m in ticket["moves"]] == ["withdraw"]
    [opening] = made["messages"]
    assert opening["kind"] == "instruction" and opening["author_side"] == "office"
    assert str(opening["body"]).startswith("SE::"), "sealed; the console opens it"
    assert plain(made["instruction"]) == "Confirm the share's access log is preserved"

    # BD-18: the email is the waiting notice, and carries no breach detail.
    [(task, args)] = mailed
    assert task == "cmp.notifications.send_breach_ticket_waiting"
    assert all("BR-" not in str(a) and "INC-" not in str(a) for a in args)


async def test_only_internal_staff_may_hold_one(
    conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    uuid = await _recorded(conn, seeded)
    monkeypatch.setattr(settings, "breach_ticket_email_domains", ("organisation.example",))
    with pytest.raises(ValidationFailed) as refused:
        await _assign(conn, seeded, uuid)
    assert "internal staff" in refused.value.message
    assert "test.local" not in refused.value.message and "@" not in refused.value.message

    monkeypatch.setattr(settings, "breach_ticket_email_domains", ("test.local",))
    with pytest.raises(ValidationFailed):
        await tickets.assign(
            conn,
            breach_uuid=uuid,
            user_uuid=str(seeded["subject"]["uuid"]),
            instruction="x",
            answer_by=None,
            actor_id=_id(seeded, "dpo"),
        )
    with pytest.raises(NotFound):
        await tickets.assign(
            conn,
            breach_uuid=uuid,
            user_uuid="00000000-0000-4000-8000-000000000000",
            instruction="x",
            answer_by=None,
            actor_id=_id(seeded, "dpo"),
        )
    with pytest.raises(ValidationFailed):
        await _assign(conn, seeded, uuid, answer_by=_today() - timedelta(days=1))


async def test_one_ticket_per_person_per_breach(conn: Any, seeded: dict[str, Any]) -> None:
    uuid = await _recorded(conn, seeded)
    await _assign(conn, seeded, uuid)
    with pytest.raises(Conflict) as again:
        await _assign(conn, seeded, uuid, instruction="And another thing")
    assert again.value.code == "ticket_exists"
    with pytest.raises(psycopg.errors.UniqueViolation):
        async with conn.transaction():
            await conn.execute(
                """INSERT INTO breach_ticket (breach_id, holder_user_id, assigned_by, instruction)
                   SELECT breach_id, holder_user_id, assigned_by, 'SE::x' FROM breach_ticket
                    WHERE breach_id = (SELECT breach_id FROM breach WHERE breach_uuid = %s)""",
                (uuid,),
            )


async def test_the_holder_sees_their_ticket_and_nothing_of_the_register(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """BD-13: the reference, the instruction, the thread, the state, the
    answer-by. Not the title, where, validation, assessment, who it touched,
    notices, duties or anybody else's ticket."""
    uuid = await _recorded(conn, seeded)
    await _assign(conn, seeded, uuid, role="dco")
    await _assign(conn, seeded, uuid, role="rco")

    [mine] = await tickets.mine(conn, user_id=_id(seeded, "dco"))
    assert set(mine) == HOLDER_KEYS
    assert mine["breach_reference"].startswith("BR-")
    detail = await tickets.my_detail(
        conn, user_id=_id(seeded, "dco"), ticket_uuid=str(mine["ticket_uuid"])
    )
    assert set(detail) == {"ticket", "messages"} and set(detail["ticket"]) == HOLDER_KEYS
    text = json.dumps(detail, default=str)
    breach = await service.detail(conn, uuid)
    for withheld in (breach["title"], breach["incident_reference"], "Names on the share"):
        assert str(withheld) not in text

    # Another holder's ticket is not found: OWN is the WHERE clause.
    [theirs] = await tickets.mine(conn, user_id=_id(seeded, "rco"))
    with pytest.raises(NotFound):
        await tickets.my_detail(
            conn, user_id=_id(seeded, "dco"), ticket_uuid=str(theirs["ticket_uuid"])
        )
    with pytest.raises(NotFound):
        await _return(conn, seeded, str(theirs["ticket_uuid"]), role="dco")


async def test_every_move_in_the_table_and_every_refusal(
    conn: Any, seeded: dict[str, Any], mailed: list[Any]
) -> None:
    uuid = await _recorded(conn, seeded)
    made = await _assign(conn, seeded, uuid)
    t = str(made["ticket"]["ticket_uuid"])

    # issued: the office may only withdraw; close and send back are refused.
    for move in ("close", "send_back"):
        with pytest.raises(Conflict) as refused:
            await _move(conn, seeded, uuid, t, move, reason="x")
        assert refused.value.code == "ticket_move_not_allowed"
    with pytest.raises(Conflict):
        await _move(conn, seeded, uuid, t, "return")

    returned = await _return(conn, seeded, t)
    assert returned["ticket"]["state"] == "returned" and returned["ticket"]["moves"] == []
    with pytest.raises(Conflict):
        await _return(conn, seeded, t)

    with pytest.raises(ValidationFailed):
        await _move(conn, seeded, uuid, t, "send_back", reason=" ")
    back = await _move(conn, seeded, uuid, t, "send_back", reason="Which log?")
    assert back["ticket"]["state"] == "issued"
    assert back["messages"][-1]["kind"] == "status"
    assert plain(back["messages"][-1]["body"]) == "Sent back by the Privacy Office: Which log?"

    await _return(conn, seeded, t)
    closed = await _move(conn, seeded, uuid, t, "close")
    assert closed["ticket"]["state"] == "closed"
    assert [m["move"] for m in closed["ticket"]["moves"]] == ["reopen"]
    with pytest.raises(Conflict):
        await tickets.holder_message(
            conn, user_id=_id(seeded, "dco"), ticket_uuid=t, body="One more thing"
        )

    reopened = await _move(conn, seeded, uuid, t, "reopen", reason="The log was incomplete")
    assert reopened["ticket"]["state"] == "issued"
    withdrawn = await _move(conn, seeded, uuid, t, "withdraw", reason="Assigned in error")
    assert withdrawn["ticket"]["state"] == "withdrawn"
    with pytest.raises(ValidationFailed):
        await _move(conn, seeded, uuid, t, "nonsense")

    # Assigned, sent back and reopened each told the holder; nothing else did.
    assert [name for name, _ in mailed].count("cmp.notifications.send_breach_ticket_waiting") == 3


async def test_a_return_says_what_was_done(conn: Any, seeded: dict[str, Any]) -> None:
    uuid = await _recorded(conn, seeded)
    t = str((await _assign(conn, seeded, uuid))["ticket"]["ticket_uuid"])
    with pytest.raises(ValidationFailed):
        await tickets.return_ticket(
            conn, user_id=_id(seeded, "dco"), ticket_uuid=t, summary="x", outcome="maybe"
        )
    with pytest.raises(ValidationFailed):
        await tickets.return_ticket(
            conn, user_id=_id(seeded, "dco"), ticket_uuid=t, summary=" ", outcome="done"
        )
    done = await tickets.return_ticket(
        conn, user_id=_id(seeded, "dco"), ticket_uuid=t, summary="Half of it", outcome="partial"
    )
    assert done["messages"][-1]["kind"] == "return"
    office = await tickets.for_breach(conn, breach_uuid=uuid)
    [event] = office[0]["events"]
    assert event["kind"] == "returned" and event["outcome"] == "partial"
    assert str(event["summary"]).startswith("SE::")


async def test_both_sides_write_and_each_counts_what_it_has_not_read(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _recorded(conn, seeded)
    t = str((await _assign(conn, seeded, uuid))["ticket"]["ticket_uuid"])
    [mine] = await tickets.mine(conn, user_id=_id(seeded, "dco"))
    assert mine["unread"] == 1, "the instruction"
    await tickets.holder_message(
        conn, user_id=_id(seeded, "dco"), ticket_uuid=t, body="Looking now"
    )
    [office] = await tickets.for_breach(conn, breach_uuid=uuid)
    assert office["unread"] == 1
    read = await tickets.office_detail(conn, breach_uuid=uuid, ticket_uuid=t)
    assert read["ticket"]["unread"] == 0
    await tickets.office_message(
        conn, breach_uuid=uuid, ticket_uuid=t, body="Thank you", actor_id=_id(seeded, "dpo")
    )
    [again] = await tickets.mine(conn, user_id=_id(seeded, "dco"))
    assert again["unread"] == 1
    with pytest.raises(ValidationFailed):
        await tickets.holder_message(conn, user_id=_id(seeded, "dco"), ticket_uuid=t, body="  ")


async def test_the_breach_does_not_close_while_a_ticket_is_open(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """BD-17, and a closed breach refuses every ticket write."""
    uuid = await _recorded(conn, seeded)
    t = str((await _assign(conn, seeded, uuid))["ticket"]["ticket_uuid"])
    await tell_org_board(conn, seeded, uuid)
    await service.determine(
        conn,
        breach_uuid=uuid,
        outcome="no",
        reasoning="Not personal data after all",
        became_aware_at=None,
        actor_id=_id(seeded, "dpo"),
    )
    with pytest.raises(TransitionNotPermitted) as refused:
        await service.transition(
            conn, breach_uuid=uuid, to="closed", reason=None, actor_id=_id(seeded, "dpo")
        )
    assert refused.value.details["blockers"] == ["1 breach ticket is still open"]

    await _return(conn, seeded, t)
    with pytest.raises(TransitionNotPermitted):
        await service.transition(
            conn, breach_uuid=uuid, to="closed", reason=None, actor_id=_id(seeded, "dpo")
        )
    await _move(conn, seeded, uuid, t, "close")
    closed = await service.transition(
        conn, breach_uuid=uuid, to="closed", reason=None, actor_id=_id(seeded, "dpo")
    )
    assert closed["status"] == "closed"
    with pytest.raises(Conflict) as locked:
        await _move(conn, seeded, uuid, t, "reopen", reason="x")
    assert locked.value.code == "breach_closed"
    [mine] = await tickets.mine(conn, user_id=_id(seeded, "dco"))
    assert mine["moves"] == [], "nothing is offered on a closed breach"


async def test_the_trail_names_the_holder_and_carries_no_words(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _recorded(conn, seeded)
    t = str((await _assign(conn, seeded, uuid))["ticket"]["ticket_uuid"])
    await tickets.holder_message(
        conn, user_id=_id(seeded, "dco"), ticket_uuid=t, body="The vendor is Acme Ltd"
    )
    await _return(conn, seeded, t)
    await _move(conn, seeded, uuid, t, "send_back", reason="Send the vendor ticket")
    rows = await fetch_all(
        conn,
        """SELECT l.event_type, l.detail_json::text AS detail, l.subject_user_id
             FROM audit_log l JOIN breach_ticket bt ON bt.ticket_id = l.entity_id
            WHERE l.entity_type = 'breach_ticket' AND bt.ticket_uuid = %s ORDER BY l.log_id""",
        (t,),
    )
    assert [r["event_type"] for r in rows] == [
        "breach_ticket.assigned",
        "breach_ticket.message",
        "breach_ticket.returned",
        "breach_ticket.sent_back",
    ]
    assert {r["subject_user_id"] for r in rows} == {_id(seeded, "dco")}
    for words in ("Acme", "vendor", "access log", "Log exported"):
        assert all(words not in r["detail"] for r in rows)


async def test_every_word_is_sealed_at_rest(conn: Any, seeded: dict[str, Any]) -> None:
    uuid = await _recorded(conn, seeded)
    t = str((await _assign(conn, seeded, uuid))["ticket"]["ticket_uuid"])
    await _return(conn, seeded, t)
    await _move(conn, seeded, uuid, t, "send_back", reason="More, please")
    row = await fetch_one(
        conn,
        """SELECT bt.instruction,
                  (SELECT array_agg(body) FROM breach_ticket_message m
                    WHERE m.ticket_id = bt.ticket_id) AS bodies,
                  (SELECT array_agg(coalesce(summary, reason)) FROM breach_ticket_event e
                    WHERE e.ticket_id = bt.ticket_id) AS words
             FROM breach_ticket bt WHERE bt.ticket_uuid = %s""",
        (t,),
    )
    assert row is not None
    assert str(row["instruction"]).startswith("SE::")
    assert all(str(b).startswith("SE::") for b in row["bodies"])
    assert all(str(w).startswith("SE::") for w in row["words"])


class TestTheRecordCannotBeEdited:
    """Raw SQL, past the service: the database holds the rule."""

    async def test_a_ticket_changes_only_its_read_markers(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        uuid = await _recorded(conn, seeded)
        t = str((await _assign(conn, seeded, uuid))["ticket"]["ticket_uuid"])
        await conn.execute(
            "UPDATE breach_ticket SET office_read_at = now() WHERE ticket_uuid = %s", (t,)
        )
        with pytest.raises(psycopg.errors.RestrictViolation):
            async with conn.transaction():
                await conn.execute(
                    "UPDATE breach_ticket SET answer_by = current_date WHERE ticket_uuid = %s",
                    (t,),
                )
        with pytest.raises(psycopg.errors.RestrictViolation):
            async with conn.transaction():
                await conn.execute("DELETE FROM breach_ticket WHERE ticket_uuid = %s", (t,))

    async def test_events_and_thread_are_append_only(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        uuid = await _recorded(conn, seeded)
        t = str((await _assign(conn, seeded, uuid))["ticket"]["ticket_uuid"])
        await _return(conn, seeded, t)
        for table, column in (
            ("breach_ticket_event", "occurred_at"),
            ("breach_ticket_message", "created_at"),
        ):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                async with conn.transaction():
                    await conn.execute(f"UPDATE {table} SET {column} = now()")

    async def test_a_return_needs_an_outcome_and_a_reason_needs_words(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        uuid = await _recorded(conn, seeded)
        t = str((await _assign(conn, seeded, uuid))["ticket"]["ticket_uuid"])
        for kind, outcome, summary, reason in (
            ("returned", None, "SE::x", None),
            ("returned", "done", None, None),
            ("sent_back", None, None, None),
            ("closed", "done", None, None),
        ):
            with pytest.raises(psycopg.errors.CheckViolation):
                async with conn.transaction():
                    await conn.execute(
                        """INSERT INTO breach_ticket_event
                             (ticket_id, kind, outcome, summary, reason, actor_user_id)
                           SELECT ticket_id, %s, %s, %s, %s, %s FROM breach_ticket
                            WHERE ticket_uuid = %s""",
                        (kind, outcome, summary, reason, _id(seeded, "dpo"), t),
                    )


async def test_the_dpo_dashboard_counts_returned_and_overdue(
    conn: Any, seeded: dict[str, Any]
) -> None:
    before = (await dashboard._dpo(conn))["counts"]
    uuid = await _recorded(conn, seeded)
    t = str((await _assign(conn, seeded, uuid))["ticket"]["ticket_uuid"])
    await _return(conn, seeded, t)
    late = str(
        (await _assign(conn, seeded, uuid, role="rco", answer_by=_today()))["ticket"]["ticket_uuid"]
    )
    await conn.execute(
        """INSERT INTO breach_ticket (breach_id, holder_user_id, assigned_by, instruction,
                                      answer_by)
           SELECT breach_id, %s, assigned_by, instruction, current_date - 1
             FROM breach_ticket WHERE ticket_uuid = %s""",
        (_id(seeded, "rnd_user"), late),
    )
    after = (await dashboard._dpo(conn))["counts"]
    assert after["breach_tickets_returned"] == before["breach_tickets_returned"] + 1
    assert after["breach_tickets_overdue"] == before["breach_tickets_overdue"] + 1


async def test_every_staff_dashboard_lists_their_breach_tickets(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _recorded(conn, seeded)
    t = str((await _assign(conn, seeded, uuid, role="rnd_user"))["ticket"]["ticket_uuid"])
    count, items = await dashboard._tickets_for_me(conn, _id(seeded, "rnd_user"))
    [item] = [i for i in items if i.get("href") == f"/tickets?breach_ticket={t}"]
    assert item["reference"].startswith("BR-") and count >= 1
    assert "Lab share" not in json.dumps(item)
