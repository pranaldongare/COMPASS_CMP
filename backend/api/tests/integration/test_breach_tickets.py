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
from cmp.db.repositories import audit as audit_repo
from cmp.db.repositories import breaches as breach_repo
from cmp.db.sql import fetch_all, fetch_one
from cmp.domain.breach import service, tickets
from cmp.tasks import dispatch as dispatch_mod
from tests.conftest import plain
from tests.integration.test_breach_register import tell_org_board

pytestmark = pytest.mark.integration

#: BD-13, spelled out here and not read from the code: widening what a holder
#: is given has to change this test.
HOLDER_KEYS = {
    "ticket_uuid",
    "breach_reference",
    "instruction",
    "state",
    "answer_by",
    "created_at",
    "unread",
    "last_activity_at",
    "moves",
    "may_add_colleague",
    "may_change_date",
}


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
    answer-by. Not the title, where, validation, assessment, who it affected,
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


async def test_the_register_counts_each_breachs_tickets_and_its_last_activity(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """For the register's filters: open tickets (issued or returned), those
    past their answer-by, and when anything last happened, from the trail."""
    uuid = await _recorded(conn, seeded)
    t = str((await _assign(conn, seeded, uuid))["ticket"]["ticket_uuid"])
    await _return(conn, seeded, t)
    late = str(
        (await _assign(conn, seeded, uuid, role="rco", answer_by=_today()))["ticket"]["ticket_uuid"]
    )
    # Past its answer-by: written as it would have been yesterday.
    await conn.execute(
        """INSERT INTO breach_ticket (breach_id, holder_user_id, assigned_by, instruction,
                                      answer_by)
           SELECT breach_id, %s, assigned_by, instruction, current_date - 1
             FROM breach_ticket WHERE ticket_uuid = %s""",
        (_id(seeded, "rnd_user"), late),
    )
    [row] = [
        r for r in await service.register(conn, status="open") if str(r["breach_uuid"]) == uuid
    ]
    assert (row["tickets_open"], row["tickets_overdue"]) == (3, 1)
    assert row["last_activity_at"] is not None

    await _move(conn, seeded, uuid, t, "close")
    [row] = [
        r for r in await service.register(conn, status="open") if str(r["breach_uuid"]) == uuid
    ]
    assert (row["tickets_open"], row["tickets_overdue"]) == (2, 1)


async def test_every_staff_dashboard_lists_their_breach_tickets(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _recorded(conn, seeded)
    t = str((await _assign(conn, seeded, uuid, role="rnd_user"))["ticket"]["ticket_uuid"])
    count, items = await dashboard._tickets_for_me(conn, _id(seeded, "rnd_user"))
    [item] = [i for i in items if i.get("href") == f"/tickets?breach_ticket={t}"]
    assert item["reference"].startswith("BR-") and count >= 1
    assert "Lab share" not in json.dumps(item)


class TestTheDateMayMove:
    """Item 9 (0061): either side, with a reason, on the record."""

    async def test_the_holder_moves_it_and_the_office_is_told(
        self, conn: Any, seeded: dict[str, Any], mailed: list[Any], request_context: Any
    ) -> None:
        uuid = await _recorded(conn, seeded)
        first, second = _today() + timedelta(days=2), _today() + timedelta(days=9)
        made = await _assign(conn, seeded, uuid, answer_by=first)
        ticket = str(made["ticket"]["ticket_uuid"])
        mailed.clear()
        moved = await tickets.holder_change_date(
            conn,
            user_id=_id(seeded, "dco"),
            ticket_uuid=ticket,
            answer_by=second,
            reason="The log vendor answers on Monday",
        )
        assert moved["ticket"]["answer_by"] == second
        assert moved["ticket"]["state"] == "issued", "it moves no state"
        assert mailed, "the office is told"
        assert {m[0] for m in mailed} == {"cmp.notifications.send_breach_ticket_date_changed"}

    async def test_the_office_moves_it_and_the_mail_names_no_breach(
        self, conn: Any, seeded: dict[str, Any], mailed: list[Any], request_context: Any
    ) -> None:
        uuid = await _recorded(conn, seeded)
        made = await _assign(conn, seeded, uuid, answer_by=_today() + timedelta(days=2))
        ticket = str(made["ticket"]["ticket_uuid"])
        mailed.clear()
        moved = await tickets.office_change_date(
            conn,
            breach_uuid=uuid,
            ticket_uuid=ticket,
            answer_by=_today() + timedelta(days=5),
            reason="More time agreed",
            actor_id=_id(seeded, "dpo"),
        )
        assert moved["ticket"]["answer_by"] == _today() + timedelta(days=5)
        [(_, args)] = mailed
        assert args[1] == "/tickets", "no breach in the mail"

    async def test_it_is_on_the_events_the_thread_and_the_trail(
        self, conn: Any, seeded: dict[str, Any], mailed: list[Any], request_context: Any
    ) -> None:
        uuid = await _recorded(conn, seeded)
        first, second = _today() + timedelta(days=2), _today() + timedelta(days=9)
        made = await _assign(conn, seeded, uuid, answer_by=first)
        ticket = str(made["ticket"]["ticket_uuid"])
        await tickets.holder_change_date(
            conn,
            user_id=_id(seeded, "dco"),
            ticket_uuid=ticket,
            answer_by=second,
            reason="The log vendor answers on Monday",
        )
        detail = await tickets.office_detail(conn, breach_uuid=uuid, ticket_uuid=ticket)
        [event] = [e for e in detail["ticket"]["events"] if e["kind"] == "date_changed"]
        assert (event["date_before"], event["date_after"]) == (first, second)
        assert str(event["reason"]).startswith("SE::"), "sealed"
        assert plain(event["reason"]) == "The log vendor answers on Monday"
        assert event["actor_name"]
        status = [m for m in detail["messages"] if m["kind"] == "status"]
        assert "The log vendor answers on Monday" in plain(status[-1]["body"])
        row = await fetch_one(
            conn,
            """SELECT detail_json FROM audit_log WHERE event_type = 'breach_ticket.date_changed'
                ORDER BY log_id DESC LIMIT 1""",
        )
        assert row is not None
        trail = row["detail_json"]
        assert trail["date_before"] == first.isoformat()
        assert trail["date_after"] == second.isoformat()
        assert "vendor" not in json.dumps(trail), "the reason is not on the trail in words"

    async def test_it_is_the_only_new_thing_on_the_holders_thread(
        self, conn: Any, seeded: dict[str, Any], mailed: list[Any], request_context: Any
    ) -> None:
        uuid = await _recorded(conn, seeded)
        made = await _assign(conn, seeded, uuid, answer_by=_today() + timedelta(days=2))
        ticket = str(made["ticket"]["ticket_uuid"])
        holder = {"user_id": _id(seeded, "dco"), "ticket_uuid": ticket}
        before = (await tickets.my_detail(conn, **holder))["messages"]
        await tickets.office_change_date(
            conn,
            breach_uuid=uuid,
            ticket_uuid=ticket,
            answer_by=_today() + timedelta(days=5),
            reason="More time agreed",
            actor_id=_id(seeded, "dpo"),
        )
        after = await tickets.my_detail(conn, **holder)
        assert set(after["ticket"]) == HOLDER_KEYS
        [added] = after["messages"][len(before) :]
        assert added["kind"] == "status"
        assert "More time agreed" in plain(added["body"])

    async def test_what_it_was_is_read_under_the_lock(
        self,
        conn: Any,
        seeded: dict[str, Any],
        mailed: list[Any],
        request_context: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The office moves it while the holder's change waits for the breach
        row: the holder's records what the office moved it to."""
        uuid = await _recorded(conn, seeded)
        first = _today() + timedelta(days=2)
        moved_to = _today() + timedelta(days=4)
        made = await _assign(conn, seeded, uuid, answer_by=first)
        ticket = str(made["ticket"]["ticket_uuid"])
        real = service.locked_open

        async def the_office_got_there_first(conn: Any, breach_uuid: str) -> Any:
            monkeypatch.setattr(service, "locked_open", real)
            await tickets.office_change_date(
                conn,
                breach_uuid=uuid,
                ticket_uuid=ticket,
                answer_by=moved_to,
                reason="More time agreed",
                actor_id=_id(seeded, "dpo"),
            )
            return await real(conn, breach_uuid)

        monkeypatch.setattr(service, "locked_open", the_office_got_there_first)
        await tickets.holder_change_date(
            conn,
            user_id=_id(seeded, "dco"),
            ticket_uuid=ticket,
            answer_by=_today() + timedelta(days=9),
            reason="The vendor answers on Monday",
        )
        detail = await tickets.office_detail(conn, breach_uuid=uuid, ticket_uuid=ticket)
        events = [e for e in detail["ticket"]["events"] if e["kind"] == "date_changed"]
        assert [e["date_before"] for e in events] == [first, moved_to]

    async def test_each_side_hears_of_the_others_change_in_the_bell_and_not_its_own(
        self, conn: Any, seeded: dict[str, Any], mailed: list[Any], request_context: Any
    ) -> None:
        uuid = await _recorded(conn, seeded)
        made = await _assign(conn, seeded, uuid, answer_by=_today() + timedelta(days=2))
        ticket = str(made["ticket"]["ticket_uuid"])

        async def moved(feed: Any, **kw: Any) -> list[dict[str, Any]]:
            rows = await feed(conn, **kw)
            return [
                r
                for r in rows
                if r["event_type"] == "breach_ticket.date_changed"
                and r["detail"]["ticket"] == ticket
            ]

        async def the_holders() -> list[dict[str, Any]]:
            return await moved(
                audit_repo.breach_ticket_events_for_holder, holder_user_id=_id(seeded, "dco")
            )

        async def the_offices() -> list[dict[str, Any]]:
            return await moved(audit_repo.breach_ticket_events_for_office, office=None)

        await tickets.holder_change_date(
            conn,
            user_id=_id(seeded, "dco"),
            ticket_uuid=ticket,
            answer_by=_today() + timedelta(days=5),
            reason="The vendor answers on Monday",
        )
        assert [r["detail"]["side"] for r in await the_offices()] == ["holder"]
        assert await the_holders() == [], "they know: they did it"

        await tickets.office_change_date(
            conn,
            breach_uuid=uuid,
            ticket_uuid=ticket,
            answer_by=_today() + timedelta(days=7),
            reason="More time agreed",
            actor_id=_id(seeded, "dpo"),
        )
        assert [r["detail"]["side"] for r in await the_holders()] == ["office"]
        assert [r["detail"]["side"] for r in await the_offices()] == ["holder"]

    async def test_a_closed_breach_keeps_it(
        self, conn: Any, seeded: dict[str, Any], mailed: list[Any], request_context: Any
    ) -> None:
        uuid = await _recorded(conn, seeded)
        made = await _assign(conn, seeded, uuid, answer_by=_today() + timedelta(days=2))
        ticket = str(made["ticket"]["ticket_uuid"])
        breach = await service.require(conn, uuid)
        await breach_repo.set_status(conn, int(breach["breach_id"]), to="closed")
        later = _today() + timedelta(days=5)
        with pytest.raises(Conflict) as by_the_holder:
            await tickets.holder_change_date(
                conn,
                user_id=_id(seeded, "dco"),
                ticket_uuid=ticket,
                answer_by=later,
                reason="x",
            )
        assert by_the_holder.value.code == "breach_closed"
        with pytest.raises(Conflict) as by_the_office:
            await tickets.office_change_date(
                conn,
                breach_uuid=uuid,
                ticket_uuid=ticket,
                answer_by=later,
                reason="x",
                actor_id=_id(seeded, "dpo"),
            )
        assert by_the_office.value.code == "breach_closed"

    async def test_a_ticket_with_no_date_may_be_given_one(
        self, conn: Any, seeded: dict[str, Any], mailed: list[Any], request_context: Any
    ) -> None:
        uuid = await _recorded(conn, seeded)
        made = await _assign(conn, seeded, uuid)
        moved = await tickets.office_change_date(
            conn,
            breach_uuid=uuid,
            ticket_uuid=str(made["ticket"]["ticket_uuid"]),
            answer_by=_today() + timedelta(days=1),
            reason="Needed for the 72-hour report",
            actor_id=_id(seeded, "dpo"),
        )
        assert moved["ticket"]["answer_by"] == _today() + timedelta(days=1)

    async def test_what_is_refused(
        self, conn: Any, seeded: dict[str, Any], mailed: list[Any], request_context: Any
    ) -> None:
        uuid = await _recorded(conn, seeded)
        by = _today() + timedelta(days=2)
        made = await _assign(conn, seeded, uuid, answer_by=by)
        ticket = str(made["ticket"]["ticket_uuid"])
        common = {"user_id": _id(seeded, "dco"), "ticket_uuid": ticket}
        with pytest.raises(ValidationFailed) as no_reason:
            await tickets.holder_change_date(
                conn, **common, answer_by=by + timedelta(days=1), reason=" "
            )
        assert no_reason.value.field == "reason"
        with pytest.raises(ValidationFailed) as past:
            await tickets.holder_change_date(
                conn, **common, answer_by=_today() - timedelta(days=1), reason="x"
            )
        assert past.value.field == "answer_by"
        with pytest.raises(ValidationFailed, match="already has"):
            await tickets.holder_change_date(conn, **common, answer_by=by, reason="x")

    async def test_a_ticket_that_is_not_open_keeps_its_date(
        self, conn: Any, seeded: dict[str, Any], mailed: list[Any], request_context: Any
    ) -> None:
        uuid = await _recorded(conn, seeded)
        made = await _assign(conn, seeded, uuid)
        ticket = str(made["ticket"]["ticket_uuid"])
        await tickets.office_move(
            conn,
            breach_uuid=uuid,
            ticket_uuid=ticket,
            move="withdraw",
            reason="Not needed",
            actor_id=_id(seeded, "dpo"),
        )
        with pytest.raises(Conflict) as refused:
            await tickets.holder_change_date(
                conn,
                user_id=_id(seeded, "dco"),
                ticket_uuid=ticket,
                answer_by=_today() + timedelta(days=1),
                reason="x",
            )
        assert refused.value.code == "ticket_not_open"
        detail = await tickets.my_detail(conn, user_id=_id(seeded, "dco"), ticket_uuid=ticket)
        assert detail["ticket"]["may_change_date"] is False

    async def test_nobody_else_moves_a_holders_date(
        self, conn: Any, seeded: dict[str, Any], mailed: list[Any], request_context: Any
    ) -> None:
        uuid = await _recorded(conn, seeded)
        made = await _assign(conn, seeded, uuid)
        with pytest.raises(NotFound):
            await tickets.holder_change_date(
                conn,
                user_id=_id(seeded, "rco"),
                ticket_uuid=str(made["ticket"]["ticket_uuid"]),
                answer_by=_today() + timedelta(days=1),
                reason="x",
            )

    async def test_the_database_refuses_a_date_nothing_recorded(
        self, conn: Any, seeded: dict[str, Any], mailed: list[Any], request_context: Any
    ) -> None:
        uuid = await _recorded(conn, seeded)
        made = await _assign(conn, seeded, uuid)
        with pytest.raises(psycopg.errors.RestrictViolation):
            await conn.execute(
                "UPDATE breach_ticket SET answer_by = current_date + 3 WHERE ticket_uuid = %s",
                (str(made["ticket"]["ticket_uuid"]),),
            )
