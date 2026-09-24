"""Erasure that erases: carrying a decided item out, store by store (S2-03).

Deciding an item used to be the end of it: applying set her disposition on
`asset_consent`, and every copy of the asset stayed where it was. This is the
step after the decision - and after quarantine, which stays the first step,
because data made unreachable can be restored if the decision was a mistake
and data that is gone cannot.

**Which stores hold an item.** The platform never holds an asset's bytes: a
recording lives at the data source that collected it, and `data_asset.storage_ref`
is that source's own pointer to it. So an item is held in two places, and
`docs/domain/personal-data.md` is the inventory that says so:

* **the holder's copy** - only the holder can erase it, so the instruction goes
  out on the request's ticket and the store counts as done when the ticket
  comes back returned, with its evidence. Until then it is *waiting*, visibly.
* **the platform's pointer** - for an erasure, where nobody else is in the
  asset, the platform forgets where the asset lived. A redaction keeps the
  asset for the other people in it, so it keeps the pointer too.

What is not erased, by decision: consent artefacts and the audit trail, which
prove the processing was lawful when it happened; and the evidence files that
carry a copy - the export CSVs a processor was sent and the response packages
she was given - which are records of what happened, like the trail. Her
`asset_consent` row stays as the record of what was done to her appearance.

**A legal hold stops it.** A hold on the asset, or on her, is recorded against
the item as `held` and nothing else is attempted until it is released.

**Every attempt is a row** in `rights_item_execution`, append-only: done,
waiting, failed or held, and why - never a value about her. A store that fails
is retried by the daily sweep and by the DPO on demand, and stays visible until
it succeeds. When every applicable store is done the item gets `executed_at`,
and her disposition moves from quarantined to erased or redacted. That is the
evidence S2-02's guard reads before a response may say "complete".
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Final

from cmp.core.enums import Disposition
from cmp.core.enums import RightsItemState as ItemState
from cmp.core.enums import RightsScopeDecision as Decision
from cmp.core.enums import RightsTicketStatus as Ticket
from cmp.core.logging import get_logger
from cmp.db.repositories import legal_holds as hold_repo
from cmp.db.repositories import rights as repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event

log = get_logger("cmp.rights.erasure")

Row = dict[str, Any]

HOLDER_COPY: Final = "holder_copy"
PLATFORM_POINTER: Final = "platform_pointer"
LEGAL_HOLD: Final = "legal_hold"

#: What each decision has to reach. A retained item, once its floor passes, is
#: erased like any other.
STORES: Final[dict[str, tuple[str, ...]]] = {
    Decision.ERASE: (HOLDER_COPY, PLATFORM_POINTER),
    Decision.RETAIN: (HOLDER_COPY, PLATFORM_POINTER),
    Decision.REDACT: (HOLDER_COPY,),
}

#: Her disposition once the item is carried out.
FINAL: Final[dict[str, Disposition]] = {
    Decision.ERASE: Disposition.ERASED,
    Decision.RETAIN: Disposition.ERASED,
    Decision.REDACT: Disposition.REDACTED,
}


def needs_execution(item: Row) -> bool:
    return (
        item.get("state") == ItemState.APPLIED
        and item.get("executed_at") is None
        and item.get("decision") in STORES
    )


async def execute(conn: Conn, request: Row, item: Row, *, actor_id: int | None) -> Row:
    """Carry one item as far as it can go now. Idempotent: done stores are skipped."""
    if not needs_execution(item):
        return item
    item_id = int(item["item_id"])
    latest = await repo.latest_executions(conn, item_id)

    hold = await hold_repo.active_covering(
        conn, asset_id=int(item["asset_id"]), subject_user_id=request.get("subject_user_id")
    )
    if hold:
        await _note(
            conn,
            latest,
            item_id,
            LEGAL_HOLD,
            "held",
            {"hold": str(hold["hold_uuid"]), "covers": "asset" if hold["asset_id"] else "person"},
            actor_id,
        )
        return item

    # A hold that stopped this item has since been released: say so on the
    # hold's own line, so nothing reading the latest attempt at each store goes
    # on showing it held.
    stopped = latest.get(LEGAL_HOLD)
    if stopped and stopped.get("status") == "held":
        released = dict(stopped.get("detail") or {}).get("hold")
        await _note(conn, latest, item_id, LEGAL_HOLD, "done", {"released": released}, actor_id)

    decision = str(item["decision"])
    for store in STORES[decision]:
        if latest.get(store, {}).get("status") == "done":
            continue
        try:
            async with conn.transaction():
                status, detail = await _attempt(conn, request, item, store)
        except Exception as exc:
            # The savepoint is gone; the failure is recorded outside it. The
            # class name only: a message could quote a value.
            status, detail = "failed", {"error": type(exc).__name__}
            log.warning("rights.erasure_failed", item=str(item["item_uuid"]), store=store)
        await _note(conn, latest, item_id, store, status, detail, actor_id)
        latest[store] = {"status": status, "detail": detail}

    if all(latest.get(s, {}).get("status") == "done" for s in STORES[decision]):
        await _finish(conn, request, item, actor_id=actor_id)
    fresh = await repo.item_by_uuid(conn, int(item["request_id"]), str(item["item_uuid"]))
    assert fresh is not None
    return fresh


async def execute_request(conn: Conn, request: Row, *, actor_id: int | None) -> int:
    """Every item of one request that still has work to do. Returns how many finished."""
    finished = 0
    for item in await repo.items_of(conn, int(request["request_id"])):
        if needs_execution(item):
            done = await execute(conn, request, item, actor_id=actor_id)
            finished += int(done.get("executed_at") is not None)
    return finished


async def execute_pending(conn: Conn) -> dict[str, int]:
    """The sweep's pass: everything applied and not yet carried out, retried."""
    attempted = finished = 0
    for item in await repo.items_awaiting_execution(conn):
        request = await repo.by_id(conn, int(item["request_id"]))
        if not request:
            continue
        attempted += 1
        done = await execute(conn, request, item, actor_id=None)
        finished += int(done.get("executed_at") is not None)
    return {"attempted": attempted, "finished": finished}


async def _attempt(conn: Conn, request: Row, item: Row, store: str) -> tuple[str, Row]:
    if store == HOLDER_COPY:
        return await _holder_copy(conn, request, item)
    if store == PLATFORM_POINTER:
        forgot = await repo.clear_asset_pointer(conn, int(item["asset_id"]))
        return "done", {"pointer_cleared": forgot}
    raise ValueError(f"no such store: {store}")


async def _holder_copy(conn: Conn, request: Row, item: Row) -> tuple[str, Row]:
    """Done when the holder of the asset's source has returned its ticket."""
    holder = None
    if item.get("holder_id"):
        holder = await repo.holder_by_id(conn, int(item["holder_id"]))
    elif item.get("source_processor_id"):
        holder = await repo.holder_for_processor(
            conn, int(request["request_id"]), int(item["source_processor_id"])
        )
    if holder is None:
        return "waiting", {"reason": "no_holder"}
    status = str(holder["ticket_status"])
    if status == Ticket.RETURNED:
        return "done", {
            "holder": str(holder["holder_uuid"]),
            "returned_at": str(holder["returned_at"]),
            "evidence_sha256": holder.get("return_evidence_hash"),
        }
    reason = {
        Ticket.PENDING: "ticket_not_issued",
        Ticket.WITHDRAWN: "ticket_withdrawn",
        Ticket.UNRETURNED: "ticket_unreturned",
    }.get(Ticket(status), "awaiting_return")
    return "waiting", {"holder": str(holder["holder_uuid"]), "reason": reason}


async def _note(
    conn: Conn,
    latest: dict[str, Row],
    item_id: int,
    store: str,
    status: str,
    detail: Row,
    actor_id: int | None,
) -> None:
    """Record an attempt - unless it says exactly what the last one said.

    The sweep runs daily over everything waiting; a row a day saying "still
    waiting for the same holder" is noise, not history.
    """
    last = latest.get(store)
    if last and last.get("status") == status and dict(last.get("detail") or {}) == detail:
        return
    await repo.add_execution(
        conn, item_id, store=store, status=status, detail=detail, attempted_by=actor_id
    )
    latest[store] = {"status": status, "detail": detail}


async def _finish(conn: Conn, request: Row, item: Row, *, actor_id: int | None) -> None:
    final = FINAL[str(item["decision"])]
    await repo.update_item(conn, int(item["item_id"]), executed_at=datetime.now(UTC))
    changed = await repo.set_disposition(conn, int(item["asset_consent_id"]), final.value)
    await audit.record(
        conn,
        event=Event.RIGHTS_ITEM_EXECUTED,
        entity_type="rights_request_item",
        entity_id=int(item["item_id"]),
        subject_user_id=request.get("subject_user_id"),
        actor_user_id=actor_id,
        detail={
            "reference": request["reference"],
            "asset": str(item["asset_uuid"]),
            "disposition": final.value,
            "stores": list(STORES[str(item["decision"])]),
        },
    )
    if changed:
        await audit.record(
            conn,
            event=Event.ASSET_DISPOSITION_CHANGED,
            entity_type="asset_consent",
            entity_id=int(changed["asset_consent_id"]),
            subject_user_id=request.get("subject_user_id"),
            actor_user_id=actor_id,
            detail={
                "reference": request["reference"],
                "asset": str(item["asset_uuid"]),
                "disposition": final.value,
                "other_subjects_untouched": int(item["other_subjects"]),
            },
        )
