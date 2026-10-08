"""How a rights ticket's holder is reached, and answers (0049, 2026-10-08).

Internal, with no console login: a temporary login, as a breach ticket's
holder, ended with the ticket and given back if it reopens; the
administrator's off switch ends it too. Internal staff: the ticket in My tasks,
no login made. External: a link carrying nothing of the request, a code to the
address on the ticket, an hour on that ticket only, and an answer that waits
for the office; a ticket sent to somebody else gets a new link and the old one
stops working.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.config import settings
from cmp.core.errors import NotFound, Unauthenticated
from cmp.core.security import unseal_token
from cmp.db.repositories import rights as repo
from cmp.db.repositories import users as user_repo
from cmp.domain.breach import access
from cmp.domain.rights import holder_link, reach, service
from cmp.domain.rights import tickets as ticket_view
from tests.conftest import plain
from tests.integration.test_rights_flows import DPO, _portal_request, _started

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _internal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "breach_ticket_email_domains", ("test.local",))


async def _sent_to(
    conn: Any, seeded: dict[str, Any], *, name: str, contact: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """An access request with one holder named by hand, its ticket sent."""
    dpo = seeded["users"]["dpo"]["id"]
    row = await _started(conn, seeded, await _portal_request(conn, seeded, "access"))
    added = await service.add_holder(
        conn,
        row,
        label="Records team",
        processor_uuid=None,
        responder_name=name,
        responder_contact=contact,
        role=DPO,
        actor_id=dpo,
    )
    holder = added if isinstance(added, dict) else added[-1]
    await service.confirm_holder(
        conn,
        row,
        holder_uuid=str(holder["holder_uuid"]),
        responder_name=None,
        responder_contact=None,
        role=DPO,
        actor_id=dpo,
    )
    await service.issue_tickets(
        conn, await service.reload(conn, row), instruction=None, due_at=None, role=DPO, actor_id=dpo
    )
    fresh = await repo.holder_by_uuid(conn, int(row["request_id"]), str(holder["holder_uuid"]))
    assert fresh is not None
    return dict(await service.reload(conn, row)), dict(fresh)


async def _grants(conn: Any, holder_id: int) -> list[dict[str, Any]]:
    cur = await conn.execute(
        "SELECT * FROM breach_temporary_access WHERE holder_id = %s ORDER BY access_id",
        (holder_id,),
    )
    return list(await cur.fetchall())


class TestAnInternalHolderWithNoLogin:
    async def test_is_given_a_temporary_login_and_the_ticket_in_my_tasks(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, sent: list[Any]
    ) -> None:
        _row, holder = await _sent_to(
            conn, seeded, name="Meera Iyer", contact="meera.records@test.local"
        )
        assert holder["channel"] == "portal" and holder["link_token_sealed"] is None
        account = await user_repo.by_email(conn, "meera.records@test.local")
        assert account is not None and account["role"] == "breach_holder"
        assert int(holder["responder_user_id"]) == int(account["id"])
        [grant] = await _grants(conn, int(holder["holder_id"]))
        assert grant["ended_at"] is None and grant["account_created"] is True
        assert grant["breach_id"] is None and grant["ticket_id"] is None
        assert holder["temporary_access"] == "pending"
        # Internal: the email in full, and where to answer.
        [(_name, args)] = [s for s in sent if s[0] == "send_holder_instruction"]
        assert args[-1].endswith(f"/tickets?ticket={holder['holder_uuid']}")
        mine = await service.tickets_for(conn, int(account["id"]))
        assert [str(t["holder_uuid"]) for t in mine] == [str(holder["holder_uuid"])]

    async def test_the_login_ends_with_the_ticket_and_comes_back_when_it_reopens(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, sent: list[Any]
    ) -> None:
        dpo = seeded["users"]["dpo"]["id"]
        row, holder = await _sent_to(
            conn, seeded, name="Ravi Menon", contact="ravi.records@test.local"
        )
        await service.withdraw_ticket(
            conn,
            row,
            holder_uuid=str(holder["holder_uuid"]),
            reason="Sent in error",
            role=DPO,
            actor_id=dpo,
        )
        [ended] = await _grants(conn, int(holder["holder_id"]))
        assert ended["end_cause"] == "ticket_withdrawn"

        from datetime import UTC, datetime, timedelta

        await service.reopen_ticket(
            conn,
            await service.reload(conn, row),
            holder_uuid=str(holder["holder_uuid"]),
            due_on=datetime.now(UTC).date() + timedelta(days=3),
            role=DPO,
            actor_id=dpo,
        )
        grants = await _grants(conn, int(holder["holder_id"]))
        assert [g["end_cause"] for g in grants] == ["ticket_withdrawn", None]

        # The request closes: the login ends; the ticket stays theirs to read.
        await conn.execute(
            "UPDATE rights_request_holder SET due_at = now() - interval '1 day' "
            "WHERE holder_id = %s",
            (int(holder["holder_id"]),),
        )
        await service.escalate_ticket(
            conn,
            await service.reload(conn, row),
            holder_uuid=str(holder["holder_uuid"]),
            role=DPO,
            actor_id=dpo,
        )
        await service.transition(
            conn,
            await service.reload(conn, row),
            to="collating",
            reason=None,
            role=DPO,
            actor_id=dpo,
        )
        await service.respond(
            conn,
            await service.reload(conn, row),
            outcome="partial",
            response_text="What we hold, less one team's part.",
            role=DPO,
            actor_id=dpo,
        )
        assert [g["end_cause"] for g in await _grants(conn, int(holder["holder_id"]))] == [
            "ticket_withdrawn",
            "request_closed",
        ]

    async def test_the_administrators_off_switch_ends_a_rights_login_too(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, sent: list[Any]
    ) -> None:
        _row, holder = await _sent_to(
            conn, seeded, name="Asha Rao", contact="asha.records@test.local"
        )
        account = await user_repo.by_email(conn, "asha.records@test.local")
        assert account is not None
        kept = await access.remove(conn, account, actor_id=seeded["users"]["admin"]["id"])
        assert kept is False
        [grant] = await _grants(conn, int(holder["holder_id"]))
        assert grant["end_cause"] == "account_deactivated"
        after = await user_repo.by_id(conn, int(account["id"]))
        assert after is not None and after["status"] == "deactivated"


async def test_internal_staff_answer_in_the_console_with_no_login_made(
    conn: Any, seeded: dict[str, Any], request_context: Any, sent: list[Any]
) -> None:
    dco = seeded["users"]["dco"]
    _row, holder = await _sent_to(conn, seeded, name="Test dco", contact="dco@test.local")
    assert holder["channel"] == "portal" and int(holder["responder_user_id"]) == int(dco["id"])
    assert await _grants(conn, int(holder["holder_id"])) == []


class TestAnExternalHolder:
    async def _issued(
        self, conn: Any, seeded: dict[str, Any], sent: list[Any]
    ) -> tuple[dict[str, Any], dict[str, Any], str]:
        row, holder = await _sent_to(conn, seeded, name="Rig Keeper", contact="rig@vendor.example")
        raw = unseal_token(holder["link_token_sealed"])
        assert raw and holder["channel"] == "email"
        return row, holder, raw

    async def test_is_sent_a_link_and_nothing_of_the_request(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, sent: list[Any]
    ) -> None:
        _row, holder, raw = await self._issued(conn, seeded, sent)
        assert not [s for s in sent if s[0] == "send_holder_instruction"]
        [(_name, args)] = [s for s in sent if s[0] == "send_holder_link"]
        assert plain(args[0]) == "rig@vendor.example" and args[5].endswith(f"/ticket/{raw}")
        assert holder["instruction"] and plain(holder["instruction"]) not in " ".join(
            str(a) for a in args
        )

    async def test_opens_with_a_code_to_the_ticket_address_and_answers_for_review(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, sent: list[Any]
    ) -> None:
        row, holder, raw = await self._issued(conn, seeded, sent)
        opened = await holder_link.open_link(conn, raw)
        assert opened["holder_uuid"] == holder["holder_uuid"]
        assert await reach.masked_address(opened) != "rig@vendor.example"

        with pytest.raises(Unauthenticated):
            await holder_link.holder_in(conn, raw, None)
        await holder_link.send_code(conn, raw)
        [(_name, args)] = [s for s in sent if s[0] == "send_holder_ticket_code"]
        assert plain(args[0]) == "rig@vendor.example"
        cookie = await holder_link.verify(conn, raw, str(args[1]))
        ticket = await holder_link.holder_in(conn, raw, cookie)
        # The cookie opens this link's ticket and no other link.
        with pytest.raises(NotFound):
            await holder_link.holder_in(conn, raw[:-2] + "zz", cookie)

        sent.clear()
        detail = await holder_link.write(
            conn,
            ticket,
            body="Which dates?",
            evidence_ref=None,
            evidence_hash=None,
            evidence_name=None,
        )
        assert detail["messages"][-1]["author_side"] == "holder"
        assert "send_ticket_message" in [n for n, _ in sent]  # the office is told

        answered = await holder_link.answer(
            conn,
            await holder_link.holder_in(conn, raw, cookie),
            summary="Two files, deleted.",
            outcome="done",
            evidence_ref=None,
            evidence_hash=None,
            evidence_name=None,
        )
        assert ticket_view.holder_view(answered["ticket"])["state"] == "review"
        fresh = await service.reload(conn, row)
        assert fresh["tickets_to_review"] == 1
        assert answered["ticket"]["accepted_at"] is None

    async def test_sent_to_somebody_else_the_old_link_stops_working(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, sent: list[Any]
    ) -> None:
        row, holder, raw = await self._issued(conn, seeded, sent)
        await service.reassign_holder(
            conn,
            row,
            holder_uuid=str(holder["holder_uuid"]),
            respondent_uuid=None,
            responder_name="New Keeper",
            responder_contact="new@vendor.example",
            role=DPO,
            actor_id=seeded["users"]["dpo"]["id"],
        )
        with pytest.raises(NotFound):
            await holder_link.open_link(conn, raw)
        moved = await repo.holder_by_uuid(conn, int(row["request_id"]), str(holder["holder_uuid"]))
        assert moved is not None
        new_raw = unseal_token(moved["link_token_sealed"])
        assert new_raw and new_raw != raw
        assert (await holder_link.open_link(conn, new_raw))["holder_uuid"] == holder["holder_uuid"]
