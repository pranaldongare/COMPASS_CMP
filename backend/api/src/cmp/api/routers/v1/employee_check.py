"""VerifyEmail and the organisation's email domains (0075, ADR 0046): the
administrator's page.

`/employee-check` - where VerifyEmail is reached, its key (never served),
whether it is on, and whether staff on other domains may sign in unchecked.
`/employee-check/domains` - the organisation's own domains: who is checked,
and who counts as inside the organisation for breach and rights tickets.
`/employee-check/test` - ask about one address now, recording nothing against
any account.

None of this is on the portal, so none of it is in the relay's allow-list: the
portal's sign-in reaches the API as it always has, and the API asks VerifyEmail
from inside (ADR 0035, 0046).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter
from pydantic import Field

from cmp.api.dependencies import EmployeeCheckReader, EmployeeCheckWriter
from cmp.db.pool import connection, transaction
from cmp.domain.employees import check
from cmp.schemas.common import Out, Schema

router = APIRouter(prefix="/employee-check", tags=["employee-check"])


class DomainOut(Out):
    domain: str
    added_at: datetime
    #: Sealed.
    added_by_name: str | None


class EmployeeCheckOut(Out):
    #: Where VerifyEmail is: /VerifyEmail is added to it.
    base_url: str | None
    #: Whether a key is stored. The key itself is never served.
    api_key_set: bool
    api_key_header: str
    enabled: bool
    #: Staff on none of the domains sign in to the console unchecked.
    allow_other_domains: bool
    domains: list[DomainOut]
    updated_at: datetime | None
    #: Sealed.
    updated_by_name: str | None


class EmployeeCheckIn(Schema):
    base_url: Annotated[str, Field(max_length=500)] | None = None
    #: A new key. Left out: the key that is stored stays.
    api_key: Annotated[str, Field(min_length=1, max_length=4000)] | None = None
    #: Remove the stored key. Ignored when `api_key` is given.
    clear_api_key: bool = False
    api_key_header: Annotated[str, Field(min_length=1, max_length=64)] | None = None
    enabled: bool = False
    allow_other_domains: bool = True


class DomainIn(Schema):
    domain: Annotated[str, Field(min_length=3, max_length=253)]


class TestIn(Schema):
    email: Annotated[str, Field(min_length=3, max_length=320)]


class TestOut(Out):
    #: active, inactive or failed.
    result: str
    #: In words.
    message: str
    on_company_domain: bool


@router.get("", response_model=EmployeeCheckOut, summary="VerifyEmail and the domains")
async def get_settings(principal: EmployeeCheckReader) -> dict[str, Any]:
    async with connection() as conn:
        return await check.overview(conn)


@router.put(
    "", response_model=EmployeeCheckOut, summary="Set VerifyEmail's address, key and switches"
)
async def put_settings(body: EmployeeCheckIn, principal: EmployeeCheckWriter) -> dict[str, Any]:
    async with transaction() as conn:
        return await check.save(
            conn,
            base_url=body.base_url,
            api_key=body.api_key,
            clear_api_key=body.clear_api_key,
            api_key_header=body.api_key_header,
            enabled=body.enabled,
            allow_other_domains=body.allow_other_domains,
            actor_id=principal.user_id,
        )


@router.post("/domains", response_model=list[DomainOut], status_code=201, summary="Add a domain")
async def add_domain(body: DomainIn, principal: EmployeeCheckWriter) -> list[dict[str, Any]]:
    async with transaction() as conn:
        return await check.add_domain(conn, body.domain, actor_id=principal.user_id)


@router.delete("/domains/{domain}", response_model=list[DomainOut], summary="Remove a domain")
async def remove_domain(domain: str, principal: EmployeeCheckWriter) -> list[dict[str, Any]]:
    async with transaction() as conn:
        return await check.remove_domain(conn, domain, actor_id=principal.user_id)


@router.post("/test", response_model=TestOut, summary="Ask VerifyEmail about one address now")
async def test_address(body: TestIn, principal: EmployeeCheckWriter) -> dict[str, Any]:
    async with transaction() as conn:
        return await check.test_address(conn, body.email, actor_id=principal.user_id)
