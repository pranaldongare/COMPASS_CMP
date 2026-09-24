"""A closed request never claims what did not happen (S2-02).

An erasure decision changes her disposition on the `asset_consent` row, and
until the executor exists (S2-03) nothing is deleted anywhere. A request could
still close as `complete`, and a complete erasure reads to her as "erased". So
`complete` is now a claim that has to be earned, item by item:

* an item counts as done only with evidence that it was carried out - a
  quarantine applied is its own evidence, since the flag *is* the act; an
  erase or a redaction needs the execution record S2-03 writes;
* a correction or erasure request with nothing done at all - no item, no
  holder's return - cannot call itself complete either;
* otherwise the request closes `partial`, and the response names what was done
  and what was not, in words that do not say "erased" for what was not.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from cmp.core.errors import TransitionNotPermitted, ValidationFailed
from cmp.core.permissions import Role
from cmp.domain.rights import package, service
from tests.integration.test_rights_flows import _asset_with_her, _consent, _portal_request

pytestmark = pytest.mark.integration

DPO = Role.DPO


async def _erasure_in_scope(
    conn: Any, seeded: dict[str, Any], *, refs: tuple[str, ...]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """An erasure request, started, with one scope item per asset in `refs`.

    No holder is derived, so no item waits for a holder's confirmation: applying
    one changes the disposition at once - which is exactly the case that used to
    close as complete with nothing deleted.
    """
    dpo = seeded["users"]["dpo"]["id"]
    consent = await _consent(conn, seeded)
    for ref in refs:
        await _asset_with_her(conn, seeded, consent["consent_id"], bystanders=0, ref=ref)
    row = await _portal_request(conn, seeded, "erasure")
    row = await service.classify(
        conn, row, request_type="erasure", note=None, role=DPO, actor_id=dpo
    )
    row = await service.confirm_intent(conn, row, role=DPO, actor_id=dpo)
    row = await service.transition(conn, row, to="in_progress", reason=None, role=DPO, actor_id=dpo)
    items = await service.derive_scope(conn, row, role=DPO, actor_id=dpo)
    return row, items


async def _decide(
    conn: Any, seeded: dict[str, Any], row: dict[str, Any], item: dict[str, Any], decision: str
) -> None:
    await service.decide_item(
        conn,
        row,
        item_uuid=str(item["item_uuid"]),
        decision=decision,
        basis="She asked",
        retain_until=(datetime.now(UTC).date() + timedelta(days=200))
        if decision == "retain"
        else None,
        holder_uuid=None,
        role=DPO,
        actor_id=seeded["users"]["dpo"]["id"],
    )


async def _apply(
    conn: Any, seeded: dict[str, Any], row: dict[str, Any], item: dict[str, Any]
) -> None:
    await service.apply_item(
        conn, row, item_uuid=str(item["item_uuid"]), role=DPO, actor_id=seeded["users"]["dpo"]["id"]
    )


async def _collating(conn: Any, seeded: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    return await service.transition(
        conn,
        await service.reload(conn, row),
        to="collating",
        reason=None,
        role=DPO,
        actor_id=seeded["users"]["dpo"]["id"],
    )


async def _respond(
    conn: Any, seeded: dict[str, Any], row: dict[str, Any], outcome: str
) -> dict[str, Any]:
    return await service.respond(
        conn,
        row,
        outcome=outcome,
        response_text="Our answer.",
        role=DPO,
        actor_id=seeded["users"]["dpo"]["id"],
    )


async def _record(conn: Any, seeded: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    payload, _, _ = await service.download(
        conn, row, actor_id=seeded["users"]["dpo"]["id"], as_subject=False
    )
    return json.loads(payload)


async def test_an_item_only_dispositioned_cannot_close_as_complete(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """The defect, as the backlog states it: decided, applied, nothing deleted,
    and the request still called itself complete."""
    row, [item] = await _erasure_in_scope(conn, seeded, refs=("S1",))
    await _decide(conn, seeded, row, item, "erase")
    await _apply(conn, seeded, row, item)
    row = await _collating(conn, seeded, row)

    with pytest.raises(ValidationFailed) as refused:
        await _respond(conn, seeded, row, "complete")

    assert refused.value.code == "response_partial_required"
    assert "ASSET-S1" in refused.value.message, "the refusal names what is not done"


async def test_it_closes_partial_and_the_response_names_what_remains(
    conn: Any, seeded: dict[str, Any]
) -> None:
    row, [item] = await _erasure_in_scope(conn, seeded, refs=("S2",))
    await _decide(conn, seeded, row, item, "erase")
    await _apply(conn, seeded, row, item)
    row = await _respond(conn, seeded, await _collating(conn, seeded, row), "partial")

    assert row["outcome"] == "partial"
    record = await _record(conn, seeded, row)
    [entry] = record["execution"]["items"]
    assert entry["asset"] == "ASSET-S2"
    assert entry["decision"] == "erase"
    assert entry["done"] is False
    assert record["execution"]["not_done"] == ["ASSET-S2"]
    digest = package.digest_text(record)
    assert "NOT YET DONE" in digest and "ASSET-S2" in digest
    assert "erased" not in entry["outcome"].lower().replace("not yet erased", "")


async def test_an_undecided_item_never_reaches_the_response(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """Already held by the state machine, and pinned here because this guard
    leans on it: an item nobody decided cannot be carried out, and a request
    holding one cannot be answered at all, whatever the outcome."""
    row, _items = await _erasure_in_scope(conn, seeded, refs=("S3",))
    row = await _collating(conn, seeded, row)
    with pytest.raises(TransitionNotPermitted):
        await _respond(conn, seeded, row, "partial")


async def test_a_retained_item_is_named_not_claimed(conn: Any, seeded: dict[str, Any]) -> None:
    row, [item] = await _erasure_in_scope(conn, seeded, refs=("S4",))
    await _decide(conn, seeded, row, item, "retain")
    row = await _collating(conn, seeded, row)

    with pytest.raises(ValidationFailed):
        await _respond(conn, seeded, row, "complete")
    row = await _respond(conn, seeded, row, "partial")
    [entry] = (await _record(conn, seeded, row))["execution"]["items"]
    assert entry["done"] is False and "retained until" in entry["outcome"].lower()


async def test_a_quarantine_applied_is_done_and_closes_complete_as_today(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """Quarantine is the platform's own flag; applying it is carrying it out. It
    is still not erasure, and the record says which it was."""
    row, [item] = await _erasure_in_scope(conn, seeded, refs=("S5",))
    await _decide(conn, seeded, row, item, "quarantine")
    await _apply(conn, seeded, row, item)
    row = await _respond(conn, seeded, await _collating(conn, seeded, row), "complete")

    assert row["outcome"] == "complete"
    [entry] = (await _record(conn, seeded, row))["execution"]["items"]
    assert entry["done"] is True
    assert "not erased" in entry["outcome"].lower()


async def test_an_erasure_with_nothing_done_at_all_cannot_claim_complete(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """No item and no holder's return: nothing was erased, so it is not complete.
    `no_records` is the honest answer, and it stays open."""
    row, items = await _erasure_in_scope(conn, seeded, refs=())
    assert items == []
    row = await _collating(conn, seeded, row)
    with pytest.raises(ValidationFailed) as refused:
        await _respond(conn, seeded, row, "complete")
    assert refused.value.code == "response_partial_required"
    row = await _respond(conn, seeded, row, "no_records")
    assert row["outcome"] == "no_records"


async def test_a_correction_nobody_carried_out_cannot_claim_complete(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = seeded["users"]["dpo"]["id"]
    row = await _portal_request(conn, seeded, "correction")
    row = await service.classify(
        conn, row, request_type="correction", note=None, role=DPO, actor_id=dpo
    )
    row = await service.transition(conn, row, to="in_progress", reason=None, role=DPO, actor_id=dpo)
    row = await _collating(conn, seeded, row)

    with pytest.raises(ValidationFailed) as refused:
        await _respond(conn, seeded, row, "complete")
    assert refused.value.code == "response_partial_required"
    row = await _respond(conn, seeded, row, "partial")
    assert row["outcome"] == "partial"


async def test_an_access_request_is_untouched(conn: Any, seeded: dict[str, Any]) -> None:
    """Access asks for a copy, not a change; nothing here is about execution."""
    dpo = seeded["users"]["dpo"]["id"]
    row = await _portal_request(conn, seeded, "access")
    row = await service.classify(
        conn, row, request_type="access", note=None, role=DPO, actor_id=dpo
    )
    row = await service.transition(conn, row, to="in_progress", reason=None, role=DPO, actor_id=dpo)
    row = await _respond(conn, seeded, await _collating(conn, seeded, row), "complete")
    assert row["outcome"] == "complete"
