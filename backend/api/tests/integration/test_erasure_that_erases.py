"""Erasure that erases (S2-03).

An erasure item is carried out store by store: the holder's copy, confirmed by
its returned ticket, and the platform's own pointer to the asset. Quarantine
comes first, `executed_at` last, and a legal hold stops it. What proves the
processing was lawful - consent artefacts and the audit trail - survives.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.errors import Conflict
from cmp.core.permissions import Role
from cmp.db.repositories import rights as repo
from cmp.domain.rights import erasure, holds, service
from tests.integration.test_rights_flows import _asset_with_her, _consent, _portal_request

pytestmark = pytest.mark.integration

DPO = Role.DPO


async def _started(
    conn: Any, seeded: dict[str, Any], *, bystanders: int = 0, ref: str
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], int]:
    """An erasure request with one asset in scope and its holder ticketed.

    Returns the request, the holder, the scope item and her asset_consent id.
    """
    dpo = seeded["users"]["dpo"]["id"]
    consent = await _consent(conn, seeded)
    ac = await _asset_with_her(conn, seeded, consent["consent_id"], bystanders=bystanders, ref=ref)
    await conn.execute(
        "UPDATE data_asset SET storage_ref = %s WHERE asset_id = "
        "(SELECT asset_id FROM asset_consent WHERE asset_consent_id = %s)",
        (f"s3://lab/{ref}.mp4", ac),
    )
    row = await _portal_request(conn, seeded, "erasure")
    row = await service.classify(
        conn, row, request_type="erasure", note=None, role=DPO, actor_id=dpo
    )
    row = await service.confirm_intent(conn, row, role=DPO, actor_id=dpo)
    row = await service.transition(conn, row, to="in_progress", reason=None, role=DPO, actor_id=dpo)
    [holder] = await service.derive_holders(conn, row, role=DPO, actor_id=dpo)
    await service.confirm_holder(
        conn,
        row,
        holder_uuid=str(holder["holder_uuid"]),
        responder_name=None,
        responder_contact=None,
        role=DPO,
        actor_id=dpo,
    )
    [item] = await service.derive_scope(conn, row, role=DPO, actor_id=dpo)
    await service.issue_tickets(conn, row, instruction=None, due_at=None, role=DPO, actor_id=dpo)
    row = await service.reload(conn, row)
    return row, holder, item, ac


async def _decide_and_apply(
    conn: Any, seeded: dict[str, Any], row: dict[str, Any], item: dict[str, Any], decision: str
) -> dict[str, Any]:
    dpo = seeded["users"]["dpo"]["id"]
    await service.decide_item(
        conn,
        row,
        item_uuid=str(item["item_uuid"]),
        decision=decision,
        basis="She asked",
        retain_until=None,
        holder_uuid=None,
        role=DPO,
        actor_id=dpo,
    )
    return await service.apply_item(
        conn, row, item_uuid=str(item["item_uuid"]), role=DPO, actor_id=dpo
    )


async def _return(
    conn: Any, seeded: dict[str, Any], row: dict[str, Any], holder: dict[str, Any]
) -> None:
    await service.return_ticket(
        conn,
        row,
        holder_uuid=str(holder["holder_uuid"]),
        summary="Deleted from the lab store and its replicas.",
        evidence_ref=None,
        evidence_hash="f00d",
        role=DPO,
        actor_id=seeded["users"]["dpo"]["id"],
    )


async def _pointer(conn: Any, ac: int) -> str | None:
    row = await (
        await conn.execute(
            "SELECT storage_ref FROM data_asset WHERE asset_id = "
            "(SELECT asset_id FROM asset_consent WHERE asset_consent_id = %s)",
            (ac,),
        )
    ).fetchone()
    return row["storage_ref"]


async def _attempts(conn: Any, item: dict[str, Any]) -> list[dict[str, Any]]:
    cur = await conn.execute(
        """SELECT store, status, detail FROM rights_item_execution
            WHERE item_id = %s ORDER BY execution_id""",
        (int(item["item_id"]),),
    )
    return list(await cur.fetchall())


async def _item(conn: Any, row: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    fresh = await repo.item_by_uuid(conn, int(row["request_id"]), str(item["item_uuid"]))
    assert fresh is not None
    return fresh


# --------------------------------------------------------------- the stores
async def test_the_holders_copy_waits_for_its_ticket_then_is_done(
    conn: Any, seeded: dict[str, Any]
) -> None:
    row, holder, item, _ac = await _started(conn, seeded, ref="X1")
    applied = await _decide_and_apply(conn, seeded, row, item, "erase")

    # Quarantine first; nothing is claimed while the lab still holds it.
    assert applied["disposition"] == "quarantined" and applied["executed_at"] is None
    first = {a["store"]: a for a in await _attempts(conn, item)}
    assert first["holder_copy"]["status"] == "waiting"
    assert first["holder_copy"]["detail"]["reason"] == "awaiting_return"

    await _return(conn, seeded, row, holder)

    done = await _item(conn, row, item)
    assert done["disposition"] == "erased" and done["executed_at"] is not None
    last = [a for a in await _attempts(conn, item) if a["store"] == "holder_copy"][-1]
    assert last["status"] == "done" and last["detail"]["evidence_sha256"] == "f00d"


async def test_the_platform_forgets_where_an_erased_asset_lived(
    conn: Any, seeded: dict[str, Any]
) -> None:
    row, holder, item, ac = await _started(conn, seeded, ref="X2")
    await _return(conn, seeded, row, holder)
    await _decide_and_apply(conn, seeded, row, item, "erase")

    assert await _pointer(conn, ac) is None
    pointer = [a for a in await _attempts(conn, item) if a["store"] == "platform_pointer"]
    assert pointer[-1]["status"] == "done" and pointer[-1]["detail"]["pointer_cleared"] is True


async def test_a_redaction_keeps_the_asset_for_the_others_in_it(
    conn: Any, seeded: dict[str, Any]
) -> None:
    row, holder, item, ac = await _started(conn, seeded, bystanders=2, ref="X3")
    await _return(conn, seeded, row, holder)
    done = await _decide_and_apply(conn, seeded, row, item, "redact")

    assert done["disposition"] == "redacted" and done["executed_at"] is not None
    assert await _pointer(conn, ac) == "s3://lab/X3.mp4", "the others' asset is not forgotten"
    assert {a["store"] for a in await _attempts(conn, item)} == {"holder_copy"}


# ------------------------------------------------------------ failure, retry
async def test_a_failed_store_is_recorded_and_retried_until_it_succeeds(
    conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    row, holder, item, ac = await _started(conn, seeded, ref="X4")
    await _return(conn, seeded, row, holder)

    async def broken(_conn: Any, _asset_id: int) -> bool:
        raise RuntimeError("storage is down: s3://lab/X4.mp4")

    monkeypatch.setattr(repo, "clear_asset_pointer", broken)
    failed = await _decide_and_apply(conn, seeded, row, item, "erase")

    assert failed["executed_at"] is None and failed["disposition"] == "quarantined"
    pointer = [a for a in await _attempts(conn, item) if a["store"] == "platform_pointer"]
    assert pointer[-1]["status"] == "failed"
    assert pointer[-1]["detail"] == {"error": "RuntimeError"}, "the class, never the message"

    monkeypatch.undo()
    swept = await erasure.execute_pending(conn)
    assert swept["finished"] >= 1
    done = await _item(conn, row, item)
    assert done["executed_at"] is not None and done["disposition"] == "erased"
    assert await _pointer(conn, ac) is None


async def test_the_sweep_does_not_repeat_itself(conn: Any, seeded: dict[str, Any]) -> None:
    """Waiting on the same holder, day after day, is one row - not one a day."""
    row, _holder, item, _ac = await _started(conn, seeded, ref="X5")
    await _decide_and_apply(conn, seeded, row, item, "erase")
    before = len(await _attempts(conn, item))
    await erasure.execute_pending(conn)
    await erasure.execute_pending(conn)
    assert len(await _attempts(conn, item)) == before


async def test_the_dpo_can_retry_now_and_nothing_else_can_be_retried(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = seeded["users"]["dpo"]["id"]
    row, holder, item, _ac = await _started(conn, seeded, ref="X6")
    await _decide_and_apply(conn, seeded, row, item, "erase")
    await _return(conn, seeded, row, holder)  # executes on return
    with pytest.raises(Conflict) as done_already:
        await service.execute_item(
            conn, row, item_uuid=str(item["item_uuid"]), role=DPO, actor_id=dpo
        )
    assert done_already.value.code == "item_not_executable"


# --------------------------------------------------------------- legal hold
async def test_a_held_asset_is_left_alone_until_the_hold_is_released(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = seeded["users"]["dpo"]["id"]
    row, holder, item, ac = await _started(conn, seeded, ref="X7")
    await _return(conn, seeded, row, holder)
    hold = await holds.place(
        conn,
        asset_uuid=str(item["asset_uuid"]),
        subject_uuid=None,
        reason="Evidence in a live matter",
        actor_id=dpo,
    )

    held = await _decide_and_apply(conn, seeded, row, item, "erase")
    assert held["executed_at"] is None and held["disposition"] == "quarantined"
    assert await _pointer(conn, ac) == "s3://lab/X7.mp4"
    [only] = await _attempts(conn, item)
    assert only["store"] == "legal_hold" and only["status"] == "held"
    assert only["detail"]["hold"] == str(hold["hold_uuid"])

    await holds.release(conn, hold_uuid=str(hold["hold_uuid"]), actor_id=dpo)
    done = await _item(conn, row, item)
    assert done["executed_at"] is not None and await _pointer(conn, ac) is None


async def test_a_hold_on_the_person_covers_every_item_of_hers(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = seeded["users"]["dpo"]["id"]
    row, holder, item, _ac = await _started(conn, seeded, ref="X8")
    await _return(conn, seeded, row, holder)
    subject = await (
        await conn.execute("SELECT uuid FROM auth_user WHERE id = %s", (seeded["subject"]["id"],))
    ).fetchone()
    await holds.place(
        conn, asset_uuid=None, subject_uuid=str(subject["uuid"]), reason="Regulator", actor_id=dpo
    )
    held = await _decide_and_apply(conn, seeded, row, item, "erase")
    assert held["executed_at"] is None


async def test_a_hold_is_placed_once_and_released_once(conn: Any, seeded: dict[str, Any]) -> None:
    dpo = seeded["users"]["dpo"]["id"]
    _row, _holder, item, _ac = await _started(conn, seeded, ref="X9")
    hold = await holds.place(
        conn, asset_uuid=str(item["asset_uuid"]), subject_uuid=None, reason="Matter", actor_id=dpo
    )
    raw = await (
        await conn.execute(
            "SELECT reason FROM legal_hold WHERE hold_uuid = %s", (str(hold["hold_uuid"]),)
        )
    ).fetchone()
    assert str(raw["reason"]).startswith("SE::"), "the reason is sealed"

    async with conn.transaction():
        with pytest.raises(Exception, match="only the release"):
            async with conn.transaction():
                await conn.execute(
                    "UPDATE legal_hold SET reason = 'changed' WHERE hold_uuid = %s",
                    (str(hold["hold_uuid"]),),
                )
    await holds.release(conn, hold_uuid=str(hold["hold_uuid"]), actor_id=dpo)
    with pytest.raises(Conflict):
        await holds.release(conn, hold_uuid=str(hold["hold_uuid"]), actor_id=dpo)


# ------------------------------------------------------------ what survives
async def test_evidence_survives_an_erasure_untouched(conn: Any, seeded: dict[str, Any]) -> None:
    """Consent artefacts and the trail prove the processing was lawful; erasure
    changes neither a row of them."""
    row, holder, item, _ac = await _started(conn, seeded, ref="XA")
    snapshot = """SELECT md5(string_agg(t::text, '|' ORDER BY {pk})) AS digest, count(*) AS n
                  FROM {table} t WHERE {pk} <= %s"""
    marks: dict[str, tuple[Any, Any]] = {}
    for table, pk in (("consent_artefact", "consent_id"), ("audit_log", "log_id")):
        top = await (await conn.execute(f"SELECT max({pk}) AS m FROM {table}")).fetchone()
        got = await (
            await conn.execute(snapshot.format(table=table, pk=pk), (top["m"],))
        ).fetchone()
        marks[table] = (top["m"], (got["digest"], got["n"]))

    await _return(conn, seeded, row, holder)
    done = await _decide_and_apply(conn, seeded, row, item, "erase")
    assert done["executed_at"] is not None

    for table, pk in (("consent_artefact", "consent_id"), ("audit_log", "log_id")):
        top, before = marks[table]
        after = await (await conn.execute(snapshot.format(table=table, pk=pk), (top,))).fetchone()
        assert (after["digest"], after["n"]) == before, f"{table} rows changed"


async def test_the_execution_record_is_append_only(conn: Any, seeded: dict[str, Any]) -> None:
    row, _holder, item, _ac = await _started(conn, seeded, ref="XB")
    await _decide_and_apply(conn, seeded, row, item, "erase")
    async with conn.transaction():
        with pytest.raises(Exception, match="is append-only"):
            async with conn.transaction():
                await conn.execute(
                    "UPDATE rights_item_execution SET status = 'done' WHERE item_id = %s",
                    (int(item["item_id"]),),
                )


# ------------------------------------------------ the S2-02 guard, now satisfied
async def test_a_fully_executed_erasure_closes_as_complete(
    conn: Any, seeded: dict[str, Any]
) -> None:
    row, holder, item, _ac = await _started(conn, seeded, ref="XC")
    await _return(conn, seeded, row, holder)
    await _decide_and_apply(conn, seeded, row, item, "erase")
    row = await service.reload(conn, row)
    assert row["status"] == "collating"
    closed = await service.respond(
        conn,
        row,
        outcome="complete",
        response_text="Erased at the lab and on the platform.",
        role=DPO,
        actor_id=seeded["users"]["dpo"]["id"],
    )
    assert closed["outcome"] == "complete"
