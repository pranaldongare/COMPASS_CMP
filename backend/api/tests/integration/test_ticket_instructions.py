"""Each holder its own instruction, and an erasure ticket's item list (2026-10-08).

Before a ticket is sent the office may write what this holder is asked,
starting from the standard words; once sent it is fixed. An erasure ticket
lists the items its holder holds and what to do with each - including items
found before the holder was, which become its own when it is asked.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.errors import Conflict
from cmp.db.repositories import rights as repo
from cmp.domain.rights import service
from tests.conftest import plain
from tests.integration.test_rights_flows import DPO, _asset_with_her, _consent, _portal_request

pytestmark = pytest.mark.integration


async def _erasure_with_an_item(conn: Any, seeded: dict[str, Any]) -> tuple[dict, dict]:
    """An erasure whose one item is decided before anybody holds it."""
    dpo = seeded["users"]["dpo"]["id"]
    consent = await _consent(conn, seeded)
    await _asset_with_her(conn, seeded, consent["consent_id"], bystanders=0, ref="INS1")
    row = await _portal_request(conn, seeded, "erasure")
    row = await service.classify(
        conn, row, request_type="erasure", note=None, role=DPO, actor_id=dpo
    )
    row = await service.confirm_intent(conn, row, role=DPO, actor_id=dpo)
    row = await service.transition(conn, row, to="in_progress", reason=None, role=DPO, actor_id=dpo)
    [item] = await service.derive_scope(conn, row, role=DPO, actor_id=dpo)
    assert item["holder_id"] is None
    await service.decide_item(
        conn,
        row,
        item_uuid=str(item["item_uuid"]),
        decision="erase",
        basis="She asked; nothing binds it",
        retain_until=None,
        holder_uuid=None,
        role=DPO,
        actor_id=dpo,
    )
    return row, item


async def _holder_at_the_processor(conn: Any, seeded: dict[str, Any], row: dict) -> dict:
    dpo = seeded["users"]["dpo"]["id"]
    processor = await conn.execute(
        "SELECT processor_uuid FROM processor WHERE processor_id = %s",
        (seeded["processors"]["external"]["processor_id"],),
    )
    processor_uuid = str((await processor.fetchone())["processor_uuid"])
    holders = await service.add_holder(
        conn,
        row,
        label="",
        processor_uuid=processor_uuid,
        responder_name="Rig Keeper",
        responder_contact="rig@vendor.example",
        role=DPO,
        actor_id=dpo,
    )
    holder = holders if isinstance(holders, dict) else holders[-1]
    return dict(
        await service.confirm_holder(
            conn,
            row,
            holder_uuid=str(holder["holder_uuid"]),
            responder_name=None,
            responder_contact=None,
            role=DPO,
            actor_id=dpo,
        )
    )


async def test_a_holder_is_asked_in_the_offices_own_words_until_the_ticket_goes(
    conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, sent: list[Any]
) -> None:
    dpo = seeded["users"]["dpo"]["id"]
    row, item = await _erasure_with_an_item(conn, seeded)
    assert "each item listed on this ticket" in service.default_instruction(row)
    holder = await _holder_at_the_processor(conn, seeded, row)

    own = "Erase the rig footage of 3 September, and the backup tape."
    saved = await service.set_instruction(
        conn,
        row,
        holder_uuid=str(holder["holder_uuid"]),
        instruction=own,
        role=DPO,
        actor_id=dpo,
    )
    # Sealed at rest, like every instruction.
    assert str(saved["instruction"]).startswith("SE::") and plain(saved["instruction"]) == own

    await service.issue_tickets(
        conn,
        await service.reload(conn, row),
        instruction="Words for everybody else",
        due_at=None,
        role=DPO,
        actor_id=dpo,
    )
    issued = await repo.holder_by_uuid(conn, int(row["request_id"]), str(holder["holder_uuid"]))
    assert issued is not None and plain(issued["instruction"]) == own
    # An outside holder is sent the link, and nothing of what it is asked.
    assert not [s for s in sent if s[0] == "send_holder_instruction"]
    [(_task, args)] = [s for s in sent if s[0] == "send_holder_link"]
    assert "/ticket/" in args[5] and not any(own in str(a) for a in args)

    # The item found before the holder is its own now, and on its ticket.
    [listed] = await repo.items_for_holder(conn, int(issued["holder_id"]))
    assert listed["item_uuid"] == item["item_uuid"] and listed["decision"] == "erase"

    with pytest.raises(Conflict) as fixed:
        await service.set_instruction(
            conn,
            row,
            holder_uuid=str(holder["holder_uuid"]),
            instruction="Too late",
            role=DPO,
            actor_id=dpo,
        )
    assert fixed.value.code == "ticket_already_sent"


async def test_empty_words_go_back_to_the_standard_ones(
    conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, sent: list[Any]
) -> None:
    dpo = seeded["users"]["dpo"]["id"]
    row, _item = await _erasure_with_an_item(conn, seeded)
    holder = await _holder_at_the_processor(conn, seeded, row)
    for words in ("Something else", "   "):
        await service.set_instruction(
            conn,
            row,
            holder_uuid=str(holder["holder_uuid"]),
            instruction=words,
            role=DPO,
            actor_id=dpo,
        )
    await service.issue_tickets(
        conn, await service.reload(conn, row), instruction=None, due_at=None, role=DPO, actor_id=dpo
    )
    issued = await repo.holder_by_uuid(conn, int(row["request_id"]), str(holder["holder_uuid"]))
    assert issued is not None
    assert plain(issued["instruction"]).startswith(f"Erasure request {row['reference']}")
