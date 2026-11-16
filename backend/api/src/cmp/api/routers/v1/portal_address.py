"""`/portal-address` - the address links to the portal start with (0072).

The administrator's page. Everybody else learns the address in use from
`GET /auth/me` (`portal_url`), which is what the console puts in front of a
consent link when it is copied.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter
from pydantic import Field

from cmp.api.dependencies import PortalAddressReader, PortalAddressWriter
from cmp.core import portal_address as held
from cmp.db.pool import connection, transaction
from cmp.domain import portal_address
from cmp.schemas.common import Out, Schema

router = APIRouter(prefix="/portal-address", tags=["portal address"])


class PortalAddressOut(Out):
    #: What the administrator set. Null: the configured address is used.
    portal_url: str | None
    #: The address from configuration (`PUBLIC_BASE_URL`).
    configured_url: str
    #: What links start with now: the one set, else the configured one.
    in_use: str
    updated_at: datetime | None
    #: Sealed.
    updated_by_name: str | None


class PortalAddressIn(Schema):
    #: Scheme, host and port, no path. Null or empty: use the configured one.
    portal_url: Annotated[str, Field(max_length=300)] | None = None


@router.get("", response_model=PortalAddressOut, summary="The address portal links start with")
async def get_portal_address(principal: PortalAddressReader) -> dict[str, Any]:
    async with connection() as conn:
        return await portal_address.overview(conn)


@router.put("", response_model=PortalAddressOut, summary="Set the address portal links start with")
async def put_portal_address(
    body: PortalAddressIn, principal: PortalAddressWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        saved = await portal_address.save(
            conn, portal_url=body.portal_url, actor_id=principal.user_id
        )
    # Committed: this process uses it from the next link on; the others, and
    # the worker, within `held.TTL_S`.
    held.remember(saved["portal_url"])
    return saved
