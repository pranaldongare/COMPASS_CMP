"""Legal holds: what may not be erased until the hold is released (S2-03).

The DPO's alone. A hold covers one asset or one person, stops the erasure
executor on every item it covers - visibly, on the item - and is released once.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, status
from pydantic import Field

from cmp.api.dependencies import LegalHoldReader, LegalHoldWriter
from cmp.db.pool import connection, transaction
from cmp.db.repositories import legal_holds as hold_repo
from cmp.domain.rights import holds
from cmp.schemas.common import Out, Schema

router = APIRouter(prefix="/legal-holds", tags=["legal holds"])


class LegalHoldIn(Schema):
    #: Exactly one of the two: an asset, or a person.
    asset_uuid: UUID | None = None
    subject_uuid: UUID | None = None
    reason: Annotated[str, Field(min_length=1, max_length=2000)]


class LegalHoldOut(Out):
    hold_uuid: UUID
    asset_uuid: UUID | None
    source_asset_ref: str | None
    subject_uuid: UUID | None
    subject_name: str | None
    reason: str
    placed_at: datetime
    placed_by_name: str | None
    released_at: datetime | None
    released_by_name: str | None


@router.get("", response_model=list[LegalHoldOut], summary="Holds, active first")
async def list_holds(
    principal: LegalHoldReader,
    active: Annotated[bool, Query(description="Only holds not yet released")] = True,
) -> list[dict[str, Any]]:
    async with connection() as conn:
        return await hold_repo.list_holds(conn, active_only=active)


@router.post(
    "",
    response_model=LegalHoldOut,
    status_code=status.HTTP_201_CREATED,
    summary="Stop erasure of an asset or a person",
)
async def place_hold(body: LegalHoldIn, principal: LegalHoldWriter) -> dict[str, Any]:
    async with transaction() as conn:
        return await holds.place(
            conn,
            asset_uuid=str(body.asset_uuid) if body.asset_uuid else None,
            subject_uuid=str(body.subject_uuid) if body.subject_uuid else None,
            reason=body.reason,
            actor_id=principal.user_id,
        )


@router.post(
    "/{hold_uuid}/release",
    response_model=LegalHoldOut,
    summary="Release a hold; what it stopped carries on",
)
async def release_hold(hold_uuid: UUID, principal: LegalHoldWriter) -> dict[str, Any]:
    async with transaction() as conn:
        return await holds.release(conn, hold_uuid=str(hold_uuid), actor_id=principal.user_id)
