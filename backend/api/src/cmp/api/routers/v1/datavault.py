"""DataVault (0070): the administrator's connection, and a rights request's
check of what DataVault holds of the person.

Two routers of its own. `/datavault-connection` is the administrator's.
`/requests/{uuid}/datavault` sits beside the rights routes and is bounded as
they are - the request is loaded through the same scoped lookup, so one that
is not the caller's office's is 404 here too. See `cmp.domain.datavault`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import Field

from cmp.api.dependencies import (
    DataVaultConnectionReader,
    DataVaultConnectionWriter,
    RequireResource,
    RightsReader,
    RightsWriter,
)
from cmp.db.pool import across_offices, connection, transaction
from cmp.domain.datavault import checks
from cmp.domain.datavault import connection as settings
from cmp.domain.rights import service as rights
from cmp.schemas.common import Out, Schema

connection_router = APIRouter(prefix="/datavault-connection", tags=["datavault"])
request_router = APIRouter(prefix="/requests", tags=["datavault"])
ticket_router = APIRouter(prefix="/tickets", tags=["datavault"])


# -------------------------------------------------------------- the connection
class ConnectionOut(Out):
    base_url: str | None
    #: Whether a key is stored. The key itself is never served.
    api_key_set: bool
    api_key_header: str
    enabled: bool
    updated_at: datetime | None
    #: Sealed.
    updated_by_name: str | None


class ConnectionIn(Schema):
    base_url: Annotated[str, Field(max_length=500)] | None = None
    #: A new key. Left out: the key that is stored stays.
    api_key: Annotated[str, Field(min_length=1, max_length=4000)] | None = None
    #: Remove the stored key. Ignored when `api_key` is given.
    clear_api_key: bool = False
    api_key_header: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    enabled: bool = False


@connection_router.get(
    "", response_model=ConnectionOut, summary="Where DataVault is reached, and whether it is on"
)
async def get_connection(principal: DataVaultConnectionReader) -> dict[str, Any]:
    async with connection() as conn:
        return await settings.overview(conn)


@connection_router.put(
    "", response_model=ConnectionOut, summary="Set DataVault's address, its key, and switch it on"
)
async def put_connection(
    body: ConnectionIn, principal: DataVaultConnectionWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        return await settings.save(
            conn,
            base_url=body.base_url,
            api_key=body.api_key,
            clear_api_key=body.clear_api_key,
            api_key_header=body.api_key_header,
            enabled=body.enabled,
            actor_id=principal.user_id,
        )


# ------------------------------------------------------------------ the check
class HeldAssetOut(Out):
    #: DataVault's own identifier for the asset.
    asset_ref: str
    #: The consent and the project as DataVault named them.
    consent_ref: str | None
    project_ref: str | None
    #: Ours, where what DataVault named is one of this person's; else null.
    consent_uuid: UUID | None
    consent_no: int | None
    project_uuid: UUID | None
    project_no: int | None
    project_name: str | None
    mid: str | None
    datapath: str | None


class CheckOut(Out):
    check_uuid: UUID
    asked_at: datetime
    #: The platform asked by itself, when holders were found.
    automatic: bool
    #: Sealed. Null for an automatic check.
    asked_by_name: str | None
    outcome: str
    #: A short code when it was not answered, and the same in words.
    failure: str | None
    failure_said: str | None
    asset_count: int


class RequestDataVaultOut(Out):
    #: DataVault has an address and is switched on.
    configured: bool
    #: This caller may ask now.
    may_check: bool
    #: Why the request cannot be asked about, when DataVault is set up.
    why_not: str | None
    #: The last check DataVault answered, with what it listed.
    answer: CheckOut | None
    assets: list[HeldAssetOut]
    #: The last attempt, if it failed after that answer (or with none).
    last_failure: CheckOut | None


class TicketDataVaultOut(Out):
    """What DataVault listed for the project a DCO Admin's ticket is about.
    `asked_at` null: not such a ticket, or DataVault has not answered yet."""

    asked_at: datetime | None
    assets: list[HeldAssetOut]


@request_router.get(
    "/{request_uuid}/datavault",
    response_model=RequestDataVaultOut,
    summary="What DataVault last said it holds of this request's person",
)
async def request_datavault(request_uuid: UUID, principal: RightsReader) -> dict[str, Any]:
    async with connection() as conn:
        row = await rights.require(
            conn, str(request_uuid), role=principal.role, user_id=principal.user_id
        )
        return await checks.overview(conn, row, role=principal.role)


@request_router.post(
    "/{request_uuid}/datavault/check",
    response_model=RequestDataVaultOut,
    summary="Check in DataVault: ask it now what it holds of this request's person",
)
async def check_in_datavault(request_uuid: UUID, principal: RightsWriter) -> dict[str, Any]:
    """One call to DataVault, made while the caller waits and recorded whether
    or not it is answered. No transaction is open during the call."""
    async with connection() as conn:
        row = await rights.require(
            conn, str(request_uuid), role=principal.role, user_id=principal.user_id
        )
        what = await checks.prepare(conn, row, role=principal.role)
    answer = await checks.ask(what)
    async with transaction() as conn:
        await checks.store(conn, what, answer, actor_id=principal.user_id)
        row = await rights.require(
            conn, str(request_uuid), role=principal.role, user_id=principal.user_id
        )
        return await checks.overview(conn, row, role=principal.role)


# ------------------------------------------------------------ a holder's ticket
@ticket_router.get(
    "/{holder_uuid}/datavault",
    response_model=TicketDataVaultOut,
    summary="On a DCO Admin's ticket: the assets DataVault listed for their project",
)
async def ticket_datavault(
    holder_uuid: UUID, principal: Annotated[Any, Depends(RequireResource("ticket"))]
) -> dict[str, Any]:
    """Bounded by the holder's own account, as every ticket route is: a ticket
    addressed to somebody else, or one that is not a project's DCO Admin's,
    answers with nothing listed."""
    async with connection() as conn, across_offices(conn):
        found = await checks.for_ticket(conn, str(holder_uuid), principal.user_id)
    return found or {"asked_at": None, "assets": []}
