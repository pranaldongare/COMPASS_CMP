"""A holder's email, and a request that goes back from collating (2026-10-08).

Whoever answers for a holder needs an email address - the ticket is emailed
once it is sent - so a holder is not added, confirmed or sent a ticket
without one. Until it is sent the address can be changed; after, a mistyped
one is corrected and the ticket goes again to the right address, nobody at
the wrong one written to. And a request moved to collating too early goes
back, with a reason the trail keeps as a code.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.config import settings
from cmp.core.errors import Conflict, NotFound, TransitionNotPermitted, ValidationFailed
from cmp.core.security import unseal_token
from cmp.db.repositories import rights as repo
from cmp.domain.rights import holder_link, service
from tests.conftest import plain
from tests.integration.test_holder_reach import _sent_to
from tests.integration.test_rights_flows import DPO, _portal_request, _started

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _internal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "breach_ticket_email_domains", ("test.local",))


async def test_a_holder_is_not_added_without_an_email_address(
    conn: Any, seeded: dict[str, Any], request_context: Any
) -> None:
    row = await _started(conn, seeded, await _portal_request(conn, seeded, "access"))
    dpo = seeded["users"]["dpo"]["id"]
    for contact in (None, "", "not-an-address"):
        with pytest.raises(ValidationFailed) as refused:
            await service.add_holder(
                conn,
                row,
                label="Records team",
                processor_uuid=None,
                responder_name="Keeper",
                responder_contact=contact,
                role=DPO,
                actor_id=dpo,
            )
        assert refused.value.field == "responder_contact"


async def test_a_ticket_is_not_sent_to_a_holder_with_nobody_to_send_to(
    conn: Any, seeded: dict[str, Any], request_context: Any, sent: list[Any]
) -> None:
    """A holder confirmed before the rule, with no address, stops the sending."""
    dpo = seeded["users"]["dpo"]["id"]
    row = await _started(conn, seeded, await _portal_request(conn, seeded, "access"))
    added = await service.add_holder(
        conn,
        row,
        label="Records team",
        processor_uuid=None,
        responder_name="Keeper",
        responder_contact="keeper@vendor.example",
        role=DPO,
        actor_id=dpo,
    )
    holder = added if isinstance(added, dict) else added[-1]
    await conn.execute(
        "UPDATE rights_request_holder SET responder_contact = NULL WHERE holder_id = %s",
        (int(holder["holder_id"]),),
    )
    with pytest.raises(Conflict) as refused:
        await service.issue_tickets(
            conn,
            await service.reload(conn, row),
            instruction=None,
            due_at=None,
            role=DPO,
            actor_id=dpo,
        )
    assert refused.value.code == "holder_without_address"
    assert not [s for s in sent if s[0] in ("send_holder_link", "send_holder_instruction")]


async def test_who_answers_changes_until_the_ticket_is_sent_and_not_after(
    conn: Any, seeded: dict[str, Any], request_context: Any, sent: list[Any]
) -> None:
    dpo = seeded["users"]["dpo"]["id"]
    row, holder = await _sent_to(conn, seeded, name="Keeper", contact="keeper@vendor.example")
    with pytest.raises(Conflict) as fixed:
        await service.confirm_holder(
            conn,
            row,
            holder_uuid=str(holder["holder_uuid"]),
            responder_name=None,
            responder_contact="other@vendor.example",
            role=DPO,
            actor_id=dpo,
        )
    assert fixed.value.code == "ticket_already_sent"


async def test_a_mistyped_address_is_corrected_and_the_ticket_goes_again(
    conn: Any, seeded: dict[str, Any], request_context: Any, sent: list[Any]
) -> None:
    dpo = seeded["users"]["dpo"]["id"]
    row, holder = await _sent_to(conn, seeded, name="Keeper", contact="keepr@vendor.example")
    old = unseal_token(holder["link_token_sealed"])
    assert old
    sent.clear()
    corrected = await service.correct_contact(
        conn,
        row,
        holder_uuid=str(holder["holder_uuid"]),
        responder_name=None,
        responder_contact="keeper@vendor.example",
        role=DPO,
        actor_id=dpo,
    )
    assert plain(corrected["responder_contact"]) == "keeper@vendor.example"
    assert plain(corrected["responder_name"]) == "Keeper"  # kept
    # The right address gets the ticket again; the wrong one is written to by nobody.
    to = [plain(args[0]) for name, args in sent if name.startswith("send_")]
    assert to == ["keeper@vendor.example"]
    # A new link; the one sent to the wrong address no longer opens anything.
    with pytest.raises(NotFound):
        await holder_link.open_link(conn, old)
    new = unseal_token(corrected["link_token_sealed"])
    assert new and new != old
    assert "corrected" in [e["kind"] for e in corrected["contact_log"]]
    trail = await conn.execute(
        "SELECT 1 FROM audit_log WHERE event_type = 'rights.holder_contact_corrected' "
        "AND entity_id = %s",
        (int(holder["holder_id"]),),
    )
    assert await trail.fetchone() is not None

    with pytest.raises(ValidationFailed):
        await service.correct_contact(
            conn,
            row,
            holder_uuid=str(holder["holder_uuid"]),
            responder_name=None,
            responder_contact="still wrong",
            role=DPO,
            actor_id=dpo,
        )


async def test_collating_goes_back_with_a_reason_and_a_holder_can_then_be_asked(
    conn: Any, seeded: dict[str, Any], request_context: Any, sent: list[Any]
) -> None:
    dpo = seeded["users"]["dpo"]["id"]
    row = await _started(conn, seeded, await _portal_request(conn, seeded, "access"))
    row = await service.transition(conn, row, to="collating", reason=None, role=DPO, actor_id=dpo)
    # No ticket was ever sent, so back is to in progress - and only with a reason.
    for reason in (None, "", "because"):
        with pytest.raises((TransitionNotPermitted, ValidationFailed)):
            await service.transition(
                conn, row, to="in_progress", reason=reason, role=DPO, actor_id=dpo
            )
    with pytest.raises(TransitionNotPermitted):
        await service.transition(
            conn, row, to="awaiting_holders", reason="new_holder", role=DPO, actor_id=dpo
        )
    back = await service.transition(
        conn, row, to="in_progress", reason="new_holder", role=DPO, actor_id=dpo
    )
    assert back["status"] == "in_progress"
    trail = await conn.execute(
        """SELECT detail_json FROM audit_log WHERE event_type = 'rights.status_changed'
            AND entity_id = %s ORDER BY log_id DESC LIMIT 1""",
        (int(row["request_id"]),),
    )
    detail = (await trail.fetchone())["detail_json"]
    assert detail["from"] == "collating" and detail["why"] == "new_holder"

    # Now the holder the office missed can be added and asked.
    await service.add_holder(
        conn,
        back,
        label="Missed archive",
        processor_uuid=None,
        responder_name="Archivist",
        responder_contact="archive@vendor.example",
        role=DPO,
        actor_id=dpo,
    )
    issued = await service.issue_tickets(
        conn,
        await service.reload(conn, back),
        instruction=None,
        due_at=None,
        role=DPO,
        actor_id=dpo,
    )
    assert [h["ticket_status"] for h in issued] == ["issued"]
    assert (await service.reload(conn, back))["status"] == "awaiting_holders"
    assert await repo.holders_of(conn, int(row["request_id"]))
