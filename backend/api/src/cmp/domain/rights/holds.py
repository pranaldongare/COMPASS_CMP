"""Placing and releasing a legal hold (S2-03).

A hold stops erasure of what it covers - one asset, or everything about one
person - and says so on every item it stops. It is the DPO's to place, with a
reason, and to release; releasing it lets the executor carry on at once rather
than waiting for the next sweep.

The trail records that a hold was placed or released, on what kind of thing,
and that a reason was given - never the reason (ADR 0015); the reason is sealed
on the hold itself.
"""

from __future__ import annotations

from typing import Any

from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.db.repositories import legal_holds as hold_repo
from cmp.db.repositories import rights as rights_repo
from cmp.db.repositories import users as user_repo
from cmp.db.sql import Conn, fetch_one
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.domain.rights import erasure

Row = dict[str, Any]


async def place(
    conn: Conn,
    *,
    asset_uuid: str | None,
    subject_uuid: str | None,
    reason: str,
    actor_id: int,
) -> Row:
    if (asset_uuid is None) == (subject_uuid is None):
        raise ValidationFailed("A hold covers one asset or one person, not both and not neither")
    if not reason.strip():
        raise ValidationFailed("Say why the erasure must stop", field="reason")
    asset_id: int | None = None
    subject_id: int | None = None
    if asset_uuid is not None:
        asset = await fetch_one(
            conn, "SELECT asset_id FROM data_asset WHERE asset_uuid = %s", (asset_uuid,)
        )
        if not asset:
            raise NotFound("Asset")
        asset_id = int(asset["asset_id"])
    else:
        person = await user_repo.by_uuid(conn, str(subject_uuid))
        if not person:
            raise NotFound("Person")
        subject_id = int(person["id"])
    held = await hold_repo.place(
        conn,
        asset_id=asset_id,
        subject_user_id=subject_id,
        reason=reason.strip(),
        placed_by=actor_id,
    )
    await audit.record(
        conn,
        event=Event.LEGAL_HOLD_PLACED,
        entity_type="legal_hold",
        entity_id=int(held["hold_id"]),
        subject_user_id=subject_id,
        actor_user_id=actor_id,
        detail={"covers": "asset" if asset_id else "person", "reason_given": True},
    )
    return held


async def release(conn: Conn, *, hold_uuid: str, actor_id: int) -> Row:
    held = await hold_repo.by_uuid(conn, hold_uuid)
    if not held:
        raise NotFound("Legal hold")
    if held["released_at"] is not None:
        raise Conflict("This hold has already been released", code="hold_released")
    row = await fetch_one(
        conn,
        "SELECT asset_id, subject_user_id FROM legal_hold WHERE hold_id = %s",
        (int(held["hold_id"]),),
    )
    assert row is not None
    await hold_repo.release(conn, int(held["hold_id"]), released_by=actor_id)
    await audit.record(
        conn,
        event=Event.LEGAL_HOLD_RELEASED,
        entity_type="legal_hold",
        entity_id=int(held["hold_id"]),
        subject_user_id=row["subject_user_id"],
        actor_user_id=actor_id,
        detail={"covers": "asset" if row["asset_id"] else "person"},
    )
    # What the hold was stopping may go ahead now.
    for item in await rights_repo.items_awaiting_execution(conn):
        if row["asset_id"] is not None and int(item["asset_id"]) != int(row["asset_id"]):
            continue
        request = await rights_repo.by_id(conn, int(item["request_id"]))
        if not request:
            continue
        if row["subject_user_id"] is not None and request.get("subject_user_id") != int(
            row["subject_user_id"]
        ):
            continue
        await erasure.execute(conn, request, item, actor_id=actor_id)
    fresh = await hold_repo.by_uuid(conn, hold_uuid)
    assert fresh is not None
    return fresh
