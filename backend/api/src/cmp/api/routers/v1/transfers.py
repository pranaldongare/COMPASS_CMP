"""The Government's restricted-country list, as the Privacy Office keeps it (S2-04).

Data, not code: a country, the notification that restricts it, and - once -
when it was lifted. What belongs on it is Legal's to say; the platform holds it
and applies it to every export (`cmp.domain.exchange.transfer`).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, status
from pydantic import Field

from cmp.api.dependencies import TransferListReader, TransferListWriter
from cmp.db.pool import connection, transaction
from cmp.db.repositories import exchange as repo
from cmp.domain.exchange import transfer
from cmp.schemas.common import CountryCode, Out, Schema

router = APIRouter(prefix="/restricted-countries", tags=["cross-border transfers"])


class RestrictionIn(Schema):
    country_code: CountryCode
    #: The Government notification that lists it, as it is cited.
    notification_ref: Annotated[str, Field(min_length=1, max_length=500)]


class RestrictionOut(Out):
    country_uuid: UUID
    country_code: str
    notification_ref: str
    listed_at: datetime
    listed_by_name: str | None
    lifted_at: datetime | None
    lifted_by_name: str | None


@router.get("", response_model=list[RestrictionOut], summary="The restricted list")
async def list_restrictions(
    principal: TransferListReader,
    active: Annotated[bool, Query(description="Only restrictions in force")] = True,
) -> list[dict[str, Any]]:
    async with connection() as conn:
        return await repo.restricted_list(conn, active_only=active)


@router.post(
    "",
    response_model=RestrictionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Restrict transfers to a country",
)
async def restrict(body: RestrictionIn, principal: TransferListWriter) -> dict[str, Any]:
    async with transaction() as conn:
        return await transfer.restrict(
            conn,
            country_code=body.country_code,
            notification_ref=body.notification_ref,
            actor_id=principal.user_id,
        )


@router.post(
    "/{country_uuid}/lift",
    response_model=RestrictionOut,
    summary="Lift a restriction",
)
async def lift(country_uuid: UUID, principal: TransferListWriter) -> dict[str, Any]:
    async with transaction() as conn:
        return await transfer.lift(conn, country_uuid=str(country_uuid), actor_id=principal.user_id)
