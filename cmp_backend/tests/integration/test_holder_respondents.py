"""Respondents on a processor, and the channel a holder's ticket travels by.

An in-house processor's respondent is an account, and a ticket to them is on
the portal: in their console, returned by them. A third party's is a name and
an address, and the ticket is a mail the Privacy Office sends and tracks by
hand on the holder's contact log. A holder inherits its processor's respondent
so the DPO is not retyping who answers for whom on every request.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from cmp.core.errors import Conflict, NotFound
from cmp.db.repositories import registry as registry_repo
from cmp.db.repositories import rights as repo
from cmp.db.sql import fetch_one
from cmp.domain.rights import service


async def _processor(conn: Any, *, name: str, in_house: bool) -> dict[str, Any]:
    row = await registry_repo.create_processor(
        conn,
        legal_name=name,
        type_="lab",
        contract_ref=f"CT-{name[:8]}",
        security_confirmed_at="2026-01-01",
        is_in_house=in_house,
    )
    return dict(row)


async def _request(conn: Any, seeded: dict[str, Any]) -> dict[str, Any]:
    """An access request from her account: verified by the session, so the
    clock is running and the DPO can start work on it."""
    row = await service.create(
        conn,
        request_type="access",
        channel="portal",
        request_text="What do you hold about me, and who has it.",
        submitted_contact="subject@test.local",
        subject_user_id=seeded["subject"]["id"],
        actor_id=seeded["subject"]["id"],
        verification_method="session",
    )
    return dict(row)


class TestRespondents:
    async def test_a_holder_inherits_its_processors_respondent(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        third_party = await _processor(conn, name="Acme Vision Ltd", in_house=False)
        await registry_repo.add_respondent(
            conn,
            int(third_party["processor_id"]),
            name="Priya at Acme",
            contact="privacy@acme.example",
            user_id=None,
        )
        in_house = await _processor(conn, name="Our Own Lab", in_house=True)
        dco = seeded["users"]["dco"]
        await registry_repo.add_respondent(
            conn, int(in_house["processor_id"]), name="x", contact="x", user_id=int(dco["id"])
        )

        row = await _request(conn, seeded)
        mailed = await service.add_holder(
            conn,
            row,
            label="",
            processor_uuid=str(third_party["processor_uuid"]),
            responder_name=None,
            responder_contact=None,
            role="dpo",
            actor_id=seeded["users"]["dpo"]["id"],
        )
        assert mailed["channel"] == "email"
        assert mailed["responder_name"] == "Priya at Acme"
        assert mailed["responder_contact"] == "privacy@acme.example"
        assert mailed["responder_user_id"] is None

        portal = await service.add_holder(
            conn,
            row,
            label="",
            processor_uuid=str(in_house["processor_uuid"]),
            responder_name=None,
            responder_contact=None,
            role="dpo",
            actor_id=seeded["users"]["dpo"]["id"],
        )
        assert portal["channel"] == "portal"
        assert portal["responder_user_id"] == int(dco["id"])
        assert portal["responder_contact"] == "dco@test.local"

    async def test_a_third_party_may_be_represented_by_one_of_our_own_accounts(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        """A third party's respondent is usually a person at the third party,
        reached by mail. It may also be one of our own people who represents
        that third party here - and then the ticket is on the portal, like any
        internal one. The repository holds no opinion; the route holds the
        rule, and this pins what the holder inherits."""
        third_party = await _processor(conn, name="Represented Ltd", in_house=False)
        await registry_repo.add_respondent(
            conn,
            int(third_party["processor_id"]),
            name="x",
            contact="x",
            user_id=int(seeded["users"]["dco"]["id"]),
        )
        row = await _request(conn, seeded)
        holder = await service.add_holder(
            conn,
            row,
            label="",
            processor_uuid=str(third_party["processor_uuid"]),
            responder_name=None,
            responder_contact=None,
            role="dpo",
            actor_id=seeded["users"]["dpo"]["id"],
        )
        assert holder["is_in_house"] is False
        assert holder["channel"] == "portal"
        assert holder["responder_user_id"] == int(seeded["users"]["dco"]["id"])

    async def test_typing_over_an_account_makes_it_email_again(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        in_house = await _processor(conn, name="Our Other Lab", in_house=True)
        await registry_repo.add_respondent(
            conn,
            int(in_house["processor_id"]),
            name="x",
            contact="x",
            user_id=int(seeded["users"]["dco"]["id"]),
        )
        row = await _request(conn, seeded)
        holder = await service.add_holder(
            conn,
            row,
            label="",
            processor_uuid=str(in_house["processor_uuid"]),
            responder_name=None,
            responder_contact=None,
            role="dpo",
            actor_id=seeded["users"]["dpo"]["id"],
        )
        assert holder["channel"] == "portal"
        again = await service.confirm_holder(
            conn,
            row,
            holder_uuid=str(holder["holder_uuid"]),
            responder_name="Somebody Else",
            responder_contact="else@example.org",
            role="dpo",
            actor_id=seeded["users"]["dpo"]["id"],
        )
        assert again["channel"] == "email"
        assert again["responder_user_id"] is None

    async def test_a_removed_respondent_is_no_longer_offered(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        p = await _processor(conn, name="Gone Soon Ltd", in_house=False)
        rs = await registry_repo.add_respondent(
            conn, int(p["processor_id"]), name="A", contact="a@example.org", user_id=None
        )
        assert len(await registry_repo.respondents_of(conn, int(p["processor_id"]))) == 1
        await registry_repo.remove_respondent(conn, int(rs["respondent_id"]))
        assert await registry_repo.respondents_of(conn, int(p["processor_id"])) == []


class TestChannels:
    async def _issued(self, conn: Any, seeded: dict[str, Any]) -> tuple[dict[str, Any], dict, dict]:
        third_party = await _processor(conn, name="Mailed Ltd", in_house=False)
        await registry_repo.add_respondent(
            conn,
            int(third_party["processor_id"]),
            name="Mail Person",
            contact="mail@third.example",
            user_id=None,
        )
        in_house = await _processor(conn, name="Portal Lab", in_house=True)
        await registry_repo.add_respondent(
            conn,
            int(in_house["processor_id"]),
            name="x",
            contact="x",
            user_id=int(seeded["users"]["dco"]["id"]),
        )
        row = await _request(conn, seeded)
        dpo = seeded["users"]["dpo"]["id"]
        await service.add_holder(
            conn,
            row,
            label="",
            processor_uuid=str(third_party["processor_uuid"]),
            responder_name=None,
            responder_contact=None,
            role="dpo",
            actor_id=dpo,
        )
        await service.add_holder(
            conn,
            row,
            label="",
            processor_uuid=str(in_house["processor_uuid"]),
            responder_name=None,
            responder_contact=None,
            role="dpo",
            actor_id=dpo,
        )
        row = await service.classify(
            conn, row, request_type="access", note=None, role="dpo", actor_id=dpo
        )
        row = await service.transition(
            conn, row, to="in_progress", reason=None, role="dpo", actor_id=dpo
        )
        holders = await service.issue_tickets(
            conn, row, instruction=None, due_at=None, role="dpo", actor_id=dpo
        )
        by_label = {h["label"]: dict(h) for h in holders}
        return dict(await service.reload(conn, row)), by_label["Mailed Ltd"], by_label["Portal Lab"]

    async def test_issuing_logs_the_mail_and_puts_the_portal_ticket_in_front_of_the_team(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        row, mailed, portal = await self._issued(conn, seeded)
        assert [e["kind"] for e in mailed["contact_log"]] == ["mail_sent"]
        assert mailed["contact_log"][0]["to"] == "mail@third.example"
        assert [e["kind"] for e in portal["contact_log"]] == ["ticket_on_portal"]

        mine = await service.tickets_for(conn, int(seeded["users"]["dco"]["id"]))
        assert [str(t["holder_uuid"]) for t in mine] == [str(portal["holder_uuid"])]
        assert mine[0]["reference"] == row["reference"]
        # Not the DPO's, and not anybody else's.
        assert await service.tickets_for(conn, int(seeded["users"]["dpo"]["id"])) == []

    async def test_the_team_returns_its_own_ticket_and_nobody_elses(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        _row, mailed, portal = await self._issued(conn, seeded)
        dco = int(seeded["users"]["dco"]["id"])
        with pytest.raises(NotFound):
            await service.return_own_ticket(
                conn,
                user_id=dco,
                holder_uuid=str(mailed["holder_uuid"]),
                summary="not mine",
                evidence_ref=None,
                evidence_hash=None,
            )
        done = await service.return_own_ticket(
            conn,
            user_id=dco,
            holder_uuid=str(portal["holder_uuid"]),
            summary="Nothing held beyond the consent record itself.",
            evidence_ref=None,
            evidence_hash=None,
        )
        assert done["ticket_status"] == "returned"
        assert done["contact_log"][-1]["kind"] == "returned_on_portal"
        with pytest.raises(Conflict):
            await service.return_own_ticket(
                conn,
                user_id=dco,
                holder_uuid=str(portal["holder_uuid"]),
                summary="again",
                evidence_ref=None,
                evidence_hash=None,
            )

    async def test_the_dpo_tracks_a_mailed_holder_by_hand(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        row, mailed, portal = await self._issued(conn, seeded)
        dpo = seeded["users"]["dpo"]["id"]
        chased = await service.log_contact(
            conn,
            row,
            holder_uuid=str(mailed["holder_uuid"]),
            kind="chased",
            note="Phoned their privacy desk.",
            send=False,
            role="dpo",
            actor_id=dpo,
        )
        resent = await service.log_contact(
            conn,
            row,
            holder_uuid=str(chased["holder_uuid"]),
            kind="note",
            note=None,
            send=True,
            role="dpo",
            actor_id=dpo,
        )
        kinds = [e["kind"] for e in resent["contact_log"]]
        assert kinds == ["mail_sent", "chased", "mail_sent"]
        assert resent["contact_log"][1]["note"] == "Phoned their privacy desk."
        # There is no mail to send to a team on the portal.
        with pytest.raises(Conflict):
            await service.log_contact(
                conn,
                row,
                holder_uuid=str(portal["holder_uuid"]),
                kind="note",
                note=None,
                send=True,
                role="dpo",
                actor_id=dpo,
            )
        # And the request itself still knows who returned what.
        held = await fetch_one(
            conn,
            "SELECT count(*) AS n FROM rights_request_holder WHERE request_id = %s",
            (row["request_id"],),
        )
        assert held["n"] == 2


class TestThread:
    async def _issued(self, conn: Any, seeded: dict[str, Any]) -> tuple[dict[str, Any], dict]:
        in_house = await _processor(conn, name="Thread Lab", in_house=True)
        await registry_repo.add_respondent(
            conn,
            int(in_house["processor_id"]),
            name="x",
            contact="x",
            user_id=int(seeded["users"]["dco"]["id"]),
        )
        row = await _request(conn, seeded)
        dpo = seeded["users"]["dpo"]["id"]
        await service.add_holder(
            conn,
            row,
            label="",
            processor_uuid=str(in_house["processor_uuid"]),
            responder_name=None,
            responder_contact=None,
            role="dpo",
            actor_id=dpo,
        )
        row = await service.classify(
            conn, row, request_type="access", note=None, role="dpo", actor_id=dpo
        )
        row = await service.transition(
            conn, row, to="in_progress", reason=None, role="dpo", actor_id=dpo
        )
        holders = await service.issue_tickets(
            conn, row, instruction=None, due_at=None, role="dpo", actor_id=dpo
        )
        return dict(await service.reload(conn, row)), dict(holders[0])

    async def test_the_ticket_opens_with_the_brief_and_the_instruction(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        _row, holder = await self._issued(conn, seeded)
        assert holder["brief"]["subject"]["full_name"] == "Test Subject"
        assert holder["brief"]["subject"]["email"] == "subject@test.local"
        # Nothing on the platform names this brand-new processor yet, and the
        # brief says so rather than leaving the team to guess.
        assert holder["brief"]["consents"] == []
        text = service.brief_text(holder["brief"])
        assert "Test Subject" in text and "holds no consent" in text

        dco = int(seeded["users"]["dco"]["id"])
        detail = await service.ticket_detail_for(conn, dco, str(holder["holder_uuid"]))
        assert [m["kind"] for m in detail["messages"]] == ["brief", "instruction"]
        assert [m["author_side"] for m in detail["messages"]] == ["system", "office"]
        # Reading it is what marks it read.
        assert detail["ticket"]["unread_for_holder"] == 0

    async def test_each_side_hears_the_other(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        row, holder = await self._issued(conn, seeded)
        dco = int(seeded["users"]["dco"]["id"])
        dpo = int(seeded["users"]["dpo"]["id"])
        ref = str(holder["holder_uuid"])

        # The team asks a question. The office has it unread; the dashboard queues it.
        after = await service.post_holder_message(
            conn, user_id=dco, holder_uuid=ref, body="Do you mean the 2025 batch as well?"
        )
        assert after["messages"][-1]["author_side"] == "holder"
        office = await repo.holder_by_uuid(conn, int(row["request_id"]), ref)
        assert office["unread_for_office"] == 1
        waiting = await repo.holders_awaiting_office(conn)
        assert ref in {str(w["holder_uuid"]) for w in waiting}

        # The office reads and answers. Reading clears its count; answering
        # gives the team one unread, which their own read then clears.
        thread = await service.thread_for_office(conn, row, holder_uuid=ref, role="dpo")
        assert thread["holder"]["unread_for_office"] == 0
        await service.post_office_message(
            conn,
            row,
            holder_uuid=ref,
            body="Yes - everything since 2024.",
            role="dpo",
            actor_id=dpo,
        )
        mine = await repo.ticket_for_user(conn, dco, ref)
        assert mine["unread_for_holder"] == 1
        detail = await service.ticket_detail_for(conn, dco, ref)
        assert detail["ticket"]["unread_for_holder"] == 0
        assert [m["kind"] for m in detail["messages"]] == [
            "brief",
            "instruction",
            "message",
            "message",
        ]

        # The return joins the thread too, and is the last word from the team.
        done = await service.return_own_ticket(
            conn,
            user_id=dco,
            holder_uuid=ref,
            summary="Nothing beyond the 2024 batch.",
            evidence_ref=None,
            evidence_hash=None,
        )
        assert done["ticket_status"] == "returned"
        thread = await service.thread_for_office(conn, row, holder_uuid=ref, role="dpo")
        assert thread["messages"][-1]["kind"] == "return"
        assert thread["messages"][-1]["author_side"] == "holder"

    async def test_a_file_travels_with_a_message_on_either_side(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        """A message can carry a file - an extract, a screenshot of a record, a
        signed confirmation - and the file is found again by the message it
        came with, on whichever side asks for it."""
        row, holder = await self._issued(conn, seeded)
        dco = int(seeded["users"]["dco"]["id"])
        dpo = int(seeded["users"]["dpo"]["id"])
        ref = str(holder["holder_uuid"])

        after = await service.post_holder_message(
            conn,
            user_id=dco,
            holder_uuid=ref,
            body="Extract of what we hold, attached.",
            evidence_ref="rights/extract.csv",
            evidence_hash="a" * 64,
        )
        sent = after["messages"][-1]
        assert sent["author_side"] == "holder" and sent["evidence_hash"] == "a" * 64
        found = await repo.message_by_uuid(
            conn, int(holder["holder_id"]), str(sent["message_uuid"])
        )
        assert found is not None and found["evidence_ref"] == "rights/extract.csv"

        back = await service.post_office_message(
            conn,
            row,
            holder_uuid=ref,
            body="The template to use is attached.",
            role="dpo",
            actor_id=dpo,
            evidence_ref="rights/template.pdf",
            evidence_hash="b" * 64,
        )
        assert back["messages"][-1]["author_side"] == "office"
        assert back["messages"][-1]["evidence_hash"] == "b" * 64
        # A message with no file has none to find.
        plain = await service.post_holder_message(conn, user_id=dco, holder_uuid=ref, body="Noted.")
        with pytest.raises(NotFound):
            await service.message_attachment(
                conn,
                holder=holder,
                message_uuid=str(plain["messages"][-1]["message_uuid"]),
                actor_id=dco,
            )

    async def test_the_thread_is_append_only(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        _row, holder = await self._issued(conn, seeded)
        with pytest.raises(Exception, match="append-only"):
            await conn.execute(
                "UPDATE rights_ticket_message SET body = 'edited' WHERE holder_id = %s",
                (holder["holder_id"],),
            )


class TestLifecycle:
    """What makes a ticket robust: it can be withdrawn, reassigned and
    reminded, each on the record, and the platform reminds on a cadence."""

    async def _issued(self, conn: Any, seeded: dict[str, Any]) -> tuple[dict[str, Any], dict]:
        in_house = await _processor(conn, name="Lifecycle Lab", in_house=True)
        await registry_repo.add_respondent(
            conn,
            int(in_house["processor_id"]),
            name="x",
            contact="x",
            user_id=int(seeded["users"]["dco"]["id"]),
        )
        row = await _request(conn, seeded)
        dpo = seeded["users"]["dpo"]["id"]
        await service.add_holder(
            conn,
            row,
            label="",
            processor_uuid=str(in_house["processor_uuid"]),
            responder_name=None,
            responder_contact=None,
            role="dpo",
            actor_id=dpo,
        )
        row = await service.classify(
            conn, row, request_type="access", note=None, role="dpo", actor_id=dpo
        )
        row = await service.transition(
            conn, row, to="in_progress", reason=None, role="dpo", actor_id=dpo
        )
        holders = await service.issue_tickets(
            conn, row, instruction=None, due_at=None, role="dpo", actor_id=dpo
        )
        return dict(await service.reload(conn, row)), dict(holders[0])

    async def test_withdrawn_is_neither_a_return_nor_a_gap(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        row, holder = await self._issued(conn, seeded)
        dpo = int(seeded["users"]["dpo"]["id"])
        dco = int(seeded["users"]["dco"]["id"])
        gone = await service.withdraw_ticket(
            conn,
            row,
            holder_uuid=str(holder["holder_uuid"]),
            reason="Named in error - this lab never held her data.",
            role="dpo",
            actor_id=dpo,
        )
        assert gone["ticket_status"] == "withdrawn"
        assert gone["contact_log"][-1]["kind"] == "withdrawn"
        thread = await service.thread_for_office(
            conn, row, holder_uuid=str(holder["holder_uuid"]), role="dpo"
        )
        assert thread["messages"][-1]["kind"] == "status"
        # Out of the team's open work, and not something to remind or return.
        assert all(
            t["ticket_status"] != "issued"
            for t in await service.tickets_for(conn, dco)
            if str(t["holder_uuid"]) == str(holder["holder_uuid"])
        )
        with pytest.raises(Conflict):
            await service.remind_holder(
                conn, row, holder_uuid=str(holder["holder_uuid"]), role="dpo", actor_id=dpo
            )
        with pytest.raises(Conflict):
            await service.return_own_ticket(
                conn,
                user_id=dco,
                holder_uuid=str(holder["holder_uuid"]),
                summary="too late",
                evidence_ref=None,
                evidence_hash=None,
            )

    async def test_reassigning_redelivers_and_resets_seen(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        row, holder = await self._issued(conn, seeded)
        dpo = int(seeded["users"]["dpo"]["id"])
        dco = int(seeded["users"]["dco"]["id"])
        ref = str(holder["holder_uuid"])
        # The team opens it: seen.
        await service.ticket_detail_for(conn, dco, ref)
        seen = await repo.holder_by_uuid(conn, int(row["request_id"]), ref)
        assert seen["seen_at"] is not None

        moved = await service.reassign_holder(
            conn,
            row,
            holder_uuid=ref,
            respondent_uuid=None,
            responder_name="Somebody Else",
            responder_contact="else@third.example",
            role="dpo",
            actor_id=dpo,
        )
        assert moved["channel"] == "email"
        assert moved["responder_contact"] == "else@third.example"
        assert moved["seen_at"] is None, "the new person has not seen it"
        kinds = [c["kind"] for c in moved["contact_log"]]
        assert kinds[-2:] == ["reassigned", "mail_sent"], kinds
        assert moved["contact_log"][-1]["to"] == "else@third.example"
        # Gone from the old person's inbox.
        assert ref not in {str(t["holder_uuid"]) for t in await service.tickets_for(conn, dco)}

    async def test_a_reminder_is_on_the_record(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        row, holder = await self._issued(conn, seeded)
        dpo = int(seeded["users"]["dpo"]["id"])
        nudged = await service.remind_holder(
            conn, row, holder_uuid=str(holder["holder_uuid"]), role="dpo", actor_id=dpo
        )
        assert nudged["reminders_sent"] == 1 and nudged["last_reminded_at"] is not None
        assert nudged["contact_log"][-1]["kind"] == "reminder"
        thread = await service.thread_for_office(
            conn, row, holder_uuid=str(holder["holder_uuid"]), role="dpo"
        )
        assert thread["messages"][-1]["kind"] == "status"
        assert "Reminder sent" in thread["messages"][-1]["body"]

    async def test_the_platform_reminds_on_a_cadence_and_once_a_day(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        from datetime import time, timedelta

        row, holder = await self._issued(conn, seeded)
        due = holder["due_at"].date()
        ref = str(holder["holder_uuid"])

        async def count() -> int:
            fresh = await repo.holder_by_uuid(conn, int(row["request_id"]), ref)
            return int(fresh["reminders_sent"])

        # Too early: nothing. Three days before: one. The same day again: none.
        assert await service.sweep_tickets(conn, today=due - timedelta(days=10)) == 0
        assert await service.sweep_tickets(conn, today=due - timedelta(days=3)) >= 1
        assert await count() == 1
        # Stamped on the simulated day, as the sweep would have stamped it.
        await repo.update_holder(
            conn,
            int(holder["holder_id"]),
            last_reminded_at=datetime.combine(due - timedelta(days=3), time(12), tzinfo=UTC),
        )
        assert await service.sweep_tickets(conn, today=due - timedelta(days=3)) == 0
        # Reset the day-stamp to test the calendar alone.
        await repo.update_holder(conn, int(holder["holder_id"]), last_reminded_at=None)
        assert await service.sweep_tickets(conn, today=due - timedelta(days=1)) == 0
        assert await service.sweep_tickets(conn, today=due) >= 1
        await repo.update_holder(conn, int(holder["holder_id"]), last_reminded_at=None)
        assert await service.sweep_tickets(conn, today=due + timedelta(days=2)) == 0
        assert await service.sweep_tickets(conn, today=due + timedelta(days=3)) >= 1
        assert await count() == 3

    async def test_a_file_keeps_its_name(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        row, holder = await self._issued(conn, seeded)
        dco = int(seeded["users"]["dco"]["id"])
        after = await service.post_holder_message(
            conn,
            user_id=dco,
            holder_uuid=str(holder["holder_uuid"]),
            body="Extract attached.",
            evidence_ref="rights/x.csv",
            evidence_hash="c" * 64,
            evidence_name="gait-extract-2026.csv",
        )
        assert after["messages"][-1]["evidence_name"] == "gait-extract-2026.csv"
        done = await service.return_own_ticket(
            conn,
            user_id=dco,
            holder_uuid=str(holder["holder_uuid"]),
            summary="Returned with the signed confirmation.",
            evidence_ref="rights/y.pdf",
            evidence_hash="d" * 64,
            evidence_name="confirmation-signed.pdf",
        )
        assert done["return_evidence_name"] == "confirmation-signed.pdf"
        assert row["reference"]
