"""Offices - 1 endpoint (ADR 0032).

The two governance offices, for the administrator's picker when an account is
provisioned or its role changes. Which rows an office holds is never answered
here: that is the office wall, applied to every connection by the pool.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter

from cmp.api.dependencies import RequireStaff
from cmp.db.pool import connection
from cmp.db.repositories import offices as repo
from cmp.schemas.common import Out

router = APIRouter(prefix="/offices", tags=["offices"])


class OfficeOut(Out):
    office_uuid: UUID
    office_code: str
    name: str


@router.get("", response_model=list[OfficeOut], summary="The offices an account can work in")
async def list_offices(principal: RequireStaff) -> list[dict[str, Any]]:
    async with connection() as conn:
        return await repo.list_offices(conn)
