"""A returned ticket counts only when it says the work was done (review DPDP-1).

A holder's return was taken as the work done, whatever it said: an erasure's
holder copy was recorded erased, and a correction could close complete, on a
ticket returned "unable to erase". A return now carries the holder's outcome -
done, partial or failed - and only done counts. Sending the ticket back asks
the holder again, and clears what it said.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.errors import ValidationFailed
from cmp.core.permissions import Role
from cmp.db.repositories import rights as repo
from cmp.domain.rights import service
from tests.integration.test_a_closed_request_claims_only_what_happened import _respond
from tests.integration.test_erasure_that_erases import _attempts, _decide_and_apply, _started
from tests.integration.test_rights_flows import _consent, _export_with_her, _portal_request

pytestmark = pytest.mark.integration

DPO = Role.DPO


async def _return(
    conn: Any, seeded: dict[str, Any], row: dict[str, Any], holder: dict[str, Any], outcome: str
) -> None:
    await service.return_ticket(
        conn,
        row,
        holder_uuid=str(holder["holder_uuid"]),
        summary="Unable to erase: the copy is in a sealed archive.",
        outcome=outcome,
        evidence_ref=None,
        evidence_hash=None,
        role=DPO,
        actor_id=seeded["users"]["dpo"]["id"],
    )


async def test_an_erasure_the_holder_could_not_do_is_not_done(
    conn: Any, seeded: dict[str, Any]
) -> None:
    row, holder, item, _ = await _started(conn, seeded, ref="DPDP1-FAIL")
    await _decide_and_apply(conn, seeded, row, item, "erase")
    await _return(conn, seeded, row, holder, "failed")

    fresh = await repo.item_by_uuid(conn, int(row["request_id"]), str(item["item_uuid"]))
    assert fresh is not None and fresh["executed_at"] is None
    holder_copy = [a for a in await _attempts(conn, item) if a["store"] == "holder_copy"][-1]
    assert holder_copy["status"] == "failed"
    assert holder_copy["detail"]["reason"] == "holder_reported_failed"

    row = await service.reload(conn, row)
    with pytest.raises(ValidationFailed) as refused:
        await _respond(conn, seeded, row, "complete")
    assert refused.value.code == "response_partial_required"


async def test_sent_back_and_returned_done_it_is_done(conn: Any, seeded: dict[str, Any]) -> None:
    dpo = seeded["users"]["dpo"]["id"]
    row, holder, item, _ = await _started(conn, seeded, ref="DPDP1-RETRY")
    await _decide_and_apply(conn, seeded, row, item, "erase")
    await _return(conn, seeded, row, holder, "partial")
    row = await service.reload(conn, row)
    await service.send_back_ticket(
        conn,
        row,
        holder_uuid=str(holder["holder_uuid"]),
        reason="Please confirm the archive copy too.",
        due_at=None,
        role=DPO,
        actor_id=dpo,
    )
    again = await repo.holder_by_uuid(conn, int(row["request_id"]), str(holder["holder_uuid"]))
    assert again is not None and again["return_outcome"] is None, "sent back, nothing said yet"

    await _return(conn, seeded, await service.reload(conn, row), holder, "done")
    fresh = await repo.item_by_uuid(conn, int(row["request_id"]), str(item["item_uuid"]))
    assert fresh is not None and fresh["executed_at"] is not None


async def _correction_ticketed(conn: Any, seeded: dict[str, Any]) -> tuple[Any, Any]:
    dpo = seeded["users"]["dpo"]["id"]
    consent = await _consent(conn, seeded)
    await _export_with_her(conn, seeded, consent["consent_id"])
    row = await _portal_request(conn, seeded, "correction")
    row = await service.classify(
        conn, row, request_type="correction", note=None, role=DPO, actor_id=dpo
    )
    row = await service.transition(conn, row, to="in_progress", reason=None, role=DPO, actor_id=dpo)
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
    return await service.reload(conn, row), holder


async def test_a_correction_the_holder_did_only_partly_cannot_close_complete(
    conn: Any, seeded: dict[str, Any]
) -> None:
    row, holder = await _correction_ticketed(conn, seeded)
    await _return(conn, seeded, row, holder, "partial")
    row = await service.reload(conn, row)
    with pytest.raises(ValidationFailed, match="Reported as not fully done"):
        await _respond(conn, seeded, row, "complete")
    closed = await _respond(conn, seeded, row, "partial")
    assert closed["outcome"] == "partial"


async def test_a_correction_returned_done_closes_complete(
    conn: Any, seeded: dict[str, Any]
) -> None:
    row, holder = await _correction_ticketed(conn, seeded)
    await _return(conn, seeded, row, holder, "done")
    closed = await _respond(conn, seeded, await service.reload(conn, row), "complete")
    assert closed["outcome"] == "complete"


async def test_an_outcome_must_be_one_of_three(conn: Any, seeded: dict[str, Any]) -> None:
    row, holder = await _correction_ticketed(conn, seeded)
    with pytest.raises(ValidationFailed) as refused:
        await _return(conn, seeded, row, holder, "probably")
    assert refused.value.field == "outcome"
