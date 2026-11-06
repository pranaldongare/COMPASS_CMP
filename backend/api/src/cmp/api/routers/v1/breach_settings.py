"""How the office hears of a breach (0058).

Who is told of a report from the public link, and where the organisation's
board is mailed. Kept by the administrator, the DPO and Legal, who may all
reach this page; the administrator sees no breach by it. See
`cmp.domain.breach.settings`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter
from pydantic import Field

from cmp.api.dependencies import BreachSettingsReader, BreachSettingsWriter
from cmp.db.pool import connection, transaction
from cmp.domain.breach import settings
from cmp.schemas.common import Out, Schema

router = APIRouter(prefix="/breach-settings", tags=["breach settings"])


class BreachRoleOut(Out):
    role: str
    title: str


class BoardRecipientOut(Out):
    recipient_uuid: UUID
    #: Sealed.
    full_name: str | None
    #: Sealed.
    email: str
    added_at: datetime
    added_by_name: str | None


class BreachSettingsOut(Out):
    #: The roles told of a report from the public link.
    intake_roles: list[str]
    #: Every role that may be chosen.
    roles: list[BreachRoleOut]
    #: Always told, whatever is chosen.
    officers: list[str]
    board_recipients: list[BoardRecipientOut]
    #: The public link, to give out.
    report_link: str


class IntakeRolesIn(Schema):
    roles: Annotated[list[str], Field(max_length=20)]


class BoardRecipientIn(Schema):
    full_name: Annotated[str, Field(max_length=200)] | None = None
    email: Annotated[str, Field(min_length=3, max_length=255)]


@router.get("", response_model=BreachSettingsOut, summary="Who hears of a breach, and how")
async def get_settings(principal: BreachSettingsReader) -> dict[str, Any]:
    async with connection() as conn:
        return await settings.overview(conn)


@router.put(
    "/intake-roles",
    response_model=BreachSettingsOut,
    summary="Which roles are told of a report from the public link",
)
async def set_intake_roles(body: IntakeRolesIn, principal: BreachSettingsWriter) -> dict[str, Any]:
    async with transaction() as conn:
        return await settings.set_intake_roles(conn, roles=body.roles, actor_id=principal.user_id)


@router.post(
    "/board-recipients",
    response_model=BreachSettingsOut,
    summary="Add an address to the organisation's board",
)
async def add_board_recipient(
    body: BoardRecipientIn, principal: BreachSettingsWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        return await settings.add_board_recipient(
            conn, full_name=body.full_name, email=body.email, actor_id=principal.user_id
        )


@router.delete(
    "/board-recipients/{recipient_uuid}",
    response_model=BreachSettingsOut,
    summary="Take an address off the organisation's board",
)
async def remove_board_recipient(
    recipient_uuid: UUID, principal: BreachSettingsWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        return await settings.remove_board_recipient(
            conn, recipient_uuid=str(recipient_uuid), actor_id=principal.user_id
        )
