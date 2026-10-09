"""Registry - purposes (8), processors and sources (7).

Registry rows are suspended, never deleted. A deleted processor orphans every
collection that named it, and "who processed this?" stops having an answer.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import Field, field_validator, model_validator

from cmp.api.dependencies import (
    CurrentUser,
    Paging,
    RequireDPO,
    RequireDPOorAdmin,
    RequireResource,
    RequireRole,
    reject_unknown_filters,
)
from cmp.core.errors import NotFound
from cmp.core.pagination import PageRequest
from cmp.core.permissions import Role
from cmp.db.pool import connection, transaction
from cmp.db.repositories import registry as repo
from cmp.domain.registry import service as registry
from cmp.schemas.common import (
    Acknowledged,
    CodeText,
    CountryCode,
    LongText,
    Out,
    Page,
    Schema,
    ShortText,
)
from cmp.validation import Email

router = APIRouter(tags=["registry"])

purpose_paging = Paging(repo.PURPOSE_SORTS, "-created_at")
processor_paging = Paging(repo.PROCESSOR_SORTS, "-created_at")
source_paging = Paging(repo.SOURCE_SORTS, "-created_at")

ReadRegistry = Annotated[Any, Depends(RequireResource("purpose"))]


# =============================================================== purposes
class PurposeOut(Out):
    purpose_uuid: UUID
    purpose_code: str
    version: int
    status: str
    name: str
    description: str
    uses: str
    lawful_basis: str
    s7_clause: str | None
    data_categories: list[str]
    retention_period: Any
    retention_basis: str
    erasure_trigger: str
    consent_validity_period: Any = None
    cross_border_permitted: bool
    permitted_for_minors: bool
    lapse_behaviour: str
    created_at: Any
    updated_at: Any


class PurposeIn(Schema):
    purpose_code: CodeText
    name: ShortText
    description: LongText
    uses: LongText
    lawful_basis: str
    s7_clause: str | None = None
    data_categories: Annotated[list[str], Field(min_length=1, max_length=50)]
    retention_days: Annotated[int, Field(ge=1, le=36_500)]
    retention_basis: str
    erasure_trigger: str
    consent_validity_days: Annotated[int | None, Field(default=None, ge=1, le=36_500)] = None
    cross_border_permitted: bool = False
    permitted_for_minors: bool = False
    lapse_behaviour: str = "quarantine"

    @field_validator("data_categories")
    @classmethod
    def _non_empty_items(cls, v: list[str]) -> list[str]:
        cleaned = [c.strip() for c in v if c and c.strip()]
        if not cleaned:
            # Rule 3(b)(i) requires the categories itemised. An empty list is not
            # an itemisation, and the database now refuses it too (migration 0004).
            raise ValueError("At least one data category is required (Rule 3(b)(i))")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Data categories must be distinct")
        return cleaned

    @model_validator(mode="after")
    def _s7_coherence(self) -> PurposeIn:
        """Mirrors the CHECK constraint, so the user gets a field error not a 500."""
        if self.lawful_basis == "legitimate_use_s7" and not self.s7_clause:
            raise ValueError("An s.7 purpose must name the clause it relies on")
        if self.lawful_basis == "consent_s6" and self.s7_clause:
            raise ValueError("A consent purpose must not carry an s.7 clause")
        return self


class PurposeUpdate(Schema):
    name: ShortText | None = None
    description: LongText | None = None
    uses: LongText | None = None
    lawful_basis: str | None = None
    s7_clause: str | None = None
    data_categories: list[str] | None = None
    retention_days: Annotated[int | None, Field(default=None, ge=1, le=36_500)] = None
    retention_basis: str | None = None
    erasure_trigger: str | None = None
    consent_validity_days: Annotated[int | None, Field(default=None, ge=1, le=36_500)] = None
    cross_border_permitted: bool | None = None
    permitted_for_minors: bool | None = None
    lapse_behaviour: str | None = None


def _purpose_fields(body: PurposeIn | PurposeUpdate) -> dict[str, Any]:
    data = body.model_dump(exclude_unset=False)
    retention = data.pop("retention_days", None)
    validity = data.pop("consent_validity_days", None)
    data["retention_period"] = timedelta(days=retention) if retention else None
    data["consent_validity_period"] = timedelta(days=validity) if validity else None
    data.pop("purpose_code", None) if isinstance(body, PurposeUpdate) else None
    return data


@router.get("/purposes", response_model=Page[PurposeOut])
async def list_purposes(
    request: Request,
    principal: ReadRegistry,
    page: Annotated[PageRequest, Depends(purpose_paging)],
    purpose_status: Annotated[str | None, Query(alias="status")] = None,
    lawful_basis: Annotated[str | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> dict[str, Any]:
    reject_unknown_filters(request, {"status", "lawful_basis", "q"})
    async with connection() as conn:
        items, cursor, total = await repo.list_purposes(
            conn, page, status=purpose_status, lawful_basis=lawful_basis, q=q
        )
    return {"items": items, "next_cursor": cursor, "total": total}


@router.post("/purposes", response_model=PurposeOut, status_code=status.HTTP_201_CREATED)
async def create_purpose(body: PurposeIn, principal: RequireDPO) -> dict[str, Any]:
    async with transaction() as conn:
        return await registry.create_purpose(
            conn, fields=_purpose_fields(body), actor_id=principal.user_id
        )


@router.get("/purposes/{purpose_uuid}", response_model=PurposeOut)
async def get_purpose(purpose_uuid: UUID, principal: ReadRegistry) -> dict[str, Any]:
    async with connection() as conn:
        purpose = await repo.purpose_by_uuid(conn, str(purpose_uuid))
        if not purpose:
            raise NotFound("Purpose")
        return purpose


@router.put("/purposes/{purpose_uuid}", response_model=PurposeOut, summary="Draft only")
async def update_purpose(
    purpose_uuid: UUID, body: PurposeUpdate, principal: RequireDPO
) -> dict[str, Any]:
    async with transaction() as conn:
        return await registry.update_purpose(conn, str(purpose_uuid), fields=_purpose_fields(body))


@router.post("/purposes/{purpose_uuid}/activate", response_model=Acknowledged)
async def activate_purpose(purpose_uuid: UUID, principal: RequireDPO) -> dict[str, Any]:
    async with transaction() as conn:
        await registry.activate_purpose(conn, str(purpose_uuid))
    return {"ok": True, "message": "Purpose activated and available to notices."}


@router.post("/purposes/{purpose_uuid}/retire", response_model=Acknowledged)
async def retire_purpose(purpose_uuid: UUID, principal: RequireDPO) -> dict[str, Any]:
    """Blocked while the purpose is attached to a published notice (409 `purpose_in_use`)."""
    async with transaction() as conn:
        await registry.retire_purpose(conn, str(purpose_uuid))
    return {"ok": True, "message": "Purpose retired. It can no longer be attached."}


@router.get("/purposes/{purpose_uuid}/versions", response_model=list[PurposeOut])
async def purpose_versions(
    purpose_uuid: UUID, principal: RequireDPOorAdmin
) -> list[dict[str, Any]]:
    async with connection() as conn:
        purpose = await repo.purpose_by_uuid(conn, str(purpose_uuid))
        if not purpose:
            raise NotFound("Purpose")
        return await repo.purpose_versions(conn, purpose["purpose_code"])


@router.get("/purposes/{purpose_uuid}/usage", summary="Notices referencing this purpose")
async def purpose_usage(purpose_uuid: UUID, principal: RequireDPOorAdmin) -> dict[str, Any]:
    """How the UI knows retirement is blocked before the user tries."""
    async with connection() as conn:
        purpose = await repo.purpose_by_uuid(conn, str(purpose_uuid))
        if not purpose:
            raise NotFound("Purpose")
        usage = await repo.purpose_usage(conn, purpose["purpose_id"])
        live = await repo.purpose_is_published_anywhere(conn, purpose["purpose_id"])
    return {"items": usage, "retirable": not live, "total": len(usage)}


# ============================================================== processors
class ProcessorOut(Out):
    processor_uuid: UUID
    legal_name: str
    type: str
    contract_ref: str
    security_confirmed_at: date
    status: str
    is_in_house: bool = False
    #: Where the processor is (S2-04). Null until recorded, and an export to it
    #: is refused until it is: a transfer the platform cannot place is one it
    #: cannot say is lawful under s.16.
    location_country: str | None = None
    created_at: Any


class ProcessorIn(Schema):
    legal_name: ShortText
    type: str
    contract_ref: Annotated[str, Field(min_length=1, max_length=120)]
    security_confirmed_at: date
    #: Whether this is the organisation collecting for itself.
    #:
    #: It decides where an approved project goes: a third party's project goes to
    #: a DCO Admin to be routed, an in-house one goes back to the R&D owner to
    #: name the sources and an RCO. Separate from `type`, which says what kind of
    #: thing a processor is and not whose it is - a lab can be either.
    is_in_house: bool = False
    #: ISO 3166-1 alpha-2. Optional here; an export to a processor without one
    #: is refused (S2-04).
    location_country: CountryCode | None = None

    @field_validator("security_confirmed_at")
    @classmethod
    def _not_future(cls, v: date) -> date:
        # Rule 6(1)(f): the confirmation is a thing that happened, not a plan.
        # UTC rather than the server's local date: otherwise the same value is
        # accepted or rejected depending on which side of midnight the server is.
        if v > datetime.now(UTC).date():
            raise ValueError("Security confirmation cannot be dated in the future")
        return v


class RespondentOut(Out):
    """Who answers a rights-request ticket for a processor."""

    respondent_uuid: UUID
    name: str
    contact: str
    #: Set when the respondent is an account here: an in-house team's contact,
    #: reached on the portal rather than by email.
    user_uuid: UUID | None = None
    user_role: str | None = None
    created_at: Any


class RespondentIn(Schema):
    #: An account here (`user_uuid`), or a name and an address. An in-house
    #: processor's respondent must be an account. A third party's may be
    #: either: usually a person at the third party, reached by mail, but
    #: sometimes one of our own people who represents them here - and then
    #: the ticket goes to the portal like any internal one.
    name: ShortText | None = None
    contact: Email | None = None
    user_uuid: UUID | None = None


class ProcessorUpdate(Schema):
    legal_name: ShortText | None = None
    contract_ref: Annotated[str | None, Field(default=None, max_length=120)] = None
    security_confirmed_at: date | None = None
    location_country: CountryCode | None = None


@router.get("/processors", response_model=Page[ProcessorOut])
async def list_processors(
    request: Request,
    principal: Annotated[Any, Depends(RequireResource("processor"))],
    page: Annotated[PageRequest, Depends(processor_paging)],
    processor_status: Annotated[str | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    mine: Annotated[bool, Query()] = False,
) -> dict[str, Any]:
    """`mine` is a DCO's or an RCO's own processors (0050) - and those of
    whoever they cover for: the ones whose data sources they see and may add
    to. For any other role it changes nothing."""
    reject_unknown_filters(request, {"status", "q", "mine"})
    collector = principal.user_id if mine and registry.is_collector(principal.role) else None
    async with connection() as conn:
        items, cursor, total = await repo.list_processors(
            conn, page, status=processor_status, q=q, collector_user_id=collector
        )
    return {"items": items, "next_cursor": cursor, "total": total}


@router.post("/processors", response_model=ProcessorOut, status_code=status.HTTP_201_CREATED)
async def create_processor(
    body: ProcessorIn,
    principal: Annotated[Any, Depends(RequireResource("processor", write=True))],
) -> dict[str, Any]:
    async with transaction() as conn:
        return await registry.create_processor(
            conn,
            legal_name=body.legal_name,
            type_=body.type,
            contract_ref=body.contract_ref,
            security_confirmed_at=body.security_confirmed_at,
            is_in_house=body.is_in_house,
            location_country=body.location_country,
        )


@router.get(
    "/processors/{processor_uuid}/respondents",
    response_model=list[RespondentOut],
    summary="Who answers a rights-request ticket for this processor",
)
async def list_respondents(
    processor_uuid: UUID,
    principal: Annotated[Any, Depends(RequireResource("processor"))],
) -> list[dict[str, Any]]:
    async with connection() as conn:
        processor = await repo.processor_by_uuid(conn, str(processor_uuid))
        if not processor:
            raise NotFound("Processor")
        return await repo.respondents_of(conn, int(processor["processor_id"]))


@router.post(
    "/processors/{processor_uuid}/respondents",
    response_model=RespondentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Name a respondent for this processor",
)
async def add_respondent(
    processor_uuid: UUID,
    body: RespondentIn,
    principal: Annotated[Any, Depends(RequireRole(Role.DPO, Role.ADMIN))],
) -> dict[str, Any]:
    """An account answers on the portal; a name and an address are mailed.

    The rules - an in-house processor's respondent must be an account - are the
    service's (`registry.add_respondent`).
    """
    async with transaction() as conn:
        return await registry.add_respondent(
            conn,
            str(processor_uuid),
            name=body.name,
            contact=body.contact,
            user_uuid=str(body.user_uuid) if body.user_uuid else None,
        )


@router.delete(
    "/processors/{processor_uuid}/respondents/{respondent_uuid}",
    response_model=Acknowledged,
    summary="Remove a respondent",
)
async def remove_respondent(
    processor_uuid: UUID,
    respondent_uuid: UUID,
    principal: Annotated[Any, Depends(RequireRole(Role.DPO, Role.ADMIN))],
) -> dict[str, Any]:
    async with transaction() as conn:
        await registry.remove_respondent(conn, str(processor_uuid), str(respondent_uuid))
    return {"ok": True, "message": "Removed. Tickets already sent to them are unchanged."}


@router.get("/processors/{processor_uuid}", response_model=ProcessorOut)
async def get_processor(
    processor_uuid: UUID,
    principal: Annotated[Any, Depends(RequireResource("processor"))],
) -> dict[str, Any]:
    async with connection() as conn:
        processor = await repo.processor_by_uuid(conn, str(processor_uuid))
        if not processor:
            raise NotFound("Processor")
        return processor


@router.put("/processors/{processor_uuid}", response_model=ProcessorOut)
async def update_processor(
    processor_uuid: UUID,
    body: ProcessorUpdate,
    principal: Annotated[Any, Depends(RequireResource("processor", write=True))],
) -> dict[str, Any]:
    async with transaction() as conn:
        return await registry.update_processor(
            conn,
            str(processor_uuid),
            legal_name=body.legal_name,
            contract_ref=body.contract_ref,
            security_confirmed_at=body.security_confirmed_at,
            location_country=body.location_country,
        )


@router.post("/processors/{processor_uuid}/suspend", response_model=Acknowledged)
async def suspend_processor(
    processor_uuid: UUID,
    principal: Annotated[Any, Depends(RequireResource("processor", write=True))],
) -> dict[str, Any]:
    async with transaction() as conn:
        await registry.suspend_processor(conn, str(processor_uuid))
    return {"ok": True, "message": "Processor suspended. Existing records are unchanged."}


# ================================================================= sources
class SourceOut(Out):
    source_uuid: UUID
    source_code: str
    name: str
    source_role: str
    exchange_mode: str
    id_scheme: str | None
    is_authoritative_for: list[str]
    status: str
    #: Who operates this source.
    #:
    #: Selected by every query behind this model and, until the contract test
    #: covered `DataSource`, not declared here - so the payload lost it and the
    #: registry's Processor column read "first party" for every row, including
    #: the third-party ones it exists to distinguish.
    processor_uuid: UUID | None = None
    processor_name: str | None = None
    #: Whose collection this is, carried down from the processor.
    #:
    #: Declared here and not only selected: a response model drops what it does
    #: not name, so a column can be joined, returned by the query and silently
    #: absent from the payload. It decides which role may own the source, so the
    #: screen that asks was offering the wrong list of people.
    is_in_house: bool | None = None
    #: Who is accountable for collection from this source. `has_owner` is
    #: separate from the name so a caller can act on an unowned source without
    #: having to treat a missing name as meaningful - a source between owners is
    #: a normal state, not an error.
    has_owner: bool = False
    owner_user_uuid: UUID | None = None
    owner_name: str | None = None
    owner_role: str | None = None
    created_at: Any


class SourceIn(Schema):
    source_code: CodeText
    name: ShortText
    source_role: str
    exchange_mode: str
    id_scheme: Annotated[str | None, Field(default=None, max_length=120)] = None
    processor_uuid: UUID | None = None
    site_uuid: UUID | None = None
    is_authoritative_for: list[str] = Field(default_factory=list)


class SourceUpdate(Schema):
    name: ShortText | None = None
    id_scheme: Annotated[str | None, Field(default=None, max_length=120)] = None
    is_authoritative_for: list[str] | None = None


async def _in_reach(conn: Any, source_uuid: UUID, principal: Any) -> None:
    """A source outside a DCO's or an RCO's processors is not found (0050)."""
    source = await repo.source_by_uuid(conn, str(source_uuid))
    if not source:
        raise NotFound("Data source")
    await registry.require_in_reach(conn, source, role=principal.role, user_id=principal.user_id)


@router.get("/sources", response_model=Page[SourceOut])
async def list_sources(
    request: Request,
    principal: Annotated[Any, Depends(RequireResource("data_source"))],
    page: Annotated[PageRequest, Depends(source_paging)],
    source_status: Annotated[str | None, Query(alias="status")] = None,
    source_role: Annotated[str | None, Query()] = None,
    processor: Annotated[UUID | None, Query()] = None,
    unmapped: Annotated[bool, Query()] = False,
    unowned: Annotated[bool, Query()] = False,
    in_house: Annotated[bool | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> dict[str, Any]:
    """`processor` narrows the list to the sources one processor operates.

    That filter is what makes the collection-site form a cascade rather than two
    unrelated dropdowns: pick who operates the site, then pick from what they
    actually run, instead of scrolling a registry-wide list and hoping.

    `unmapped` is the opposite question: which sources has nobody said who
    operates. A source the organisation runs itself legitimately has no
    processor - requiring one would mean inventing a processor record for your
    own organisation - so this is a gap to review rather than an error to
    prevent, and a filter is how a reviewable gap is surfaced.

    `unowned` is the DCO Admin's and the R&D owner's working list: sources nobody
    is accountable for yet. `in_house` splits the registry the way routing does -
    what we collect ourselves from what somebody else collects for us.

    **A DCO or an RCO sees only the sources of their own processors** (0050) -
    those the administrator assigned them, and those of anybody they cover for.
    """
    reject_unknown_filters(
        request,
        {"status", "source_role", "processor", "unmapped", "unowned", "in_house", "q"},
    )
    async with connection() as conn:
        items, cursor, total = await repo.list_sources(
            conn,
            page,
            status=source_status,
            source_role=source_role,
            processor_uuid=str(processor) if processor else None,
            unmapped=unmapped,
            unowned=unowned,
            in_house=in_house,
            q=q,
            collector_user_id=(
                principal.user_id if registry.is_collector(principal.role) else None
            ),
        )
    return {"items": items, "next_cursor": cursor, "total": total}


@router.post("/sources", response_model=SourceOut, status_code=status.HTTP_201_CREATED)
async def create_source(
    body: SourceIn,
    principal: Annotated[Any, Depends(RequireResource("data_source", write=True))],
) -> dict[str, Any]:
    """`is_authoritative_for` lists the data elements this source owns.

    **A collection owner may only register under their own kind of processor**
    (`registry.refuse_foreign_processor`): a DCO under a third party's, an RCO
    under an in-house one. Everyone else registers on somebody's behalf.
    """
    async with transaction() as conn:
        return await registry.create_source(
            conn,
            role=principal.role,
            user_id=principal.user_id,
            source_code=body.source_code,
            name=body.name,
            source_role=body.source_role,
            exchange_mode=body.exchange_mode,
            id_scheme=body.id_scheme,
            processor_uuid=str(body.processor_uuid) if body.processor_uuid else None,
            site_uuid=str(body.site_uuid) if body.site_uuid else None,
            is_authoritative_for=body.is_authoritative_for,
        )


@router.get("/sources/{source_uuid}", response_model=SourceOut)
async def get_source(
    source_uuid: UUID,
    principal: Annotated[Any, Depends(RequireResource("data_source"))],
) -> dict[str, Any]:
    async with connection() as conn:
        source = await repo.source_by_uuid(conn, str(source_uuid))
        if not source:
            raise NotFound("Data source")
        await registry.require_in_reach(
            conn, source, role=principal.role, user_id=principal.user_id
        )
        return source


@router.put("/sources/{source_uuid}", response_model=SourceOut)
async def update_source(
    source_uuid: UUID,
    body: SourceUpdate,
    principal: Annotated[Any, Depends(RequireResource("data_source", write=True))],
) -> dict[str, Any]:
    async with transaction() as conn:
        await _in_reach(conn, source_uuid, principal)
        return await registry.update_source(
            conn,
            str(source_uuid),
            name=body.name,
            id_scheme=body.id_scheme,
            is_authoritative_for=body.is_authoritative_for,
        )


class SourceOwnerIn(Schema):
    """Who is accountable for collection from this source.

    `null` takes it back, which is a real operation: somebody leaves and their
    sources have to sit unowned until they are picked up, rather than being
    silently parked with whoever happens to be assigned next.
    """

    owner_user_uuid: UUID | None = None


@router.put("/sources/{source_uuid}/owner", summary="Assign the person accountable for a source")
async def assign_source_owner(
    source_uuid: UUID,
    body: SourceOwnerIn,
    principal: Annotated[Any, Depends(RequireResource("data_source", write=True))],
) -> dict[str, Any]:
    """Hand a source to a DCO or an RCO. Every project using it follows.

    This is where a person is named, and it is the *only* place. Everywhere else
    - registering a site, routing an approved project - picks a source, and the
    owner comes with it. `projects_moved` says how many projects followed.
    """
    async with transaction() as conn:
        await _in_reach(conn, source_uuid, principal)
        return await registry.assign_source_owner(
            conn,
            str(source_uuid),
            owner_user_uuid=str(body.owner_user_uuid) if body.owner_user_uuid else None,
        )


@router.post("/sources/{source_uuid}/suspend", response_model=Acknowledged)
async def suspend_source(
    source_uuid: UUID,
    principal: Annotated[Any, Depends(RequireResource("data_source", write=True))],
) -> dict[str, Any]:
    async with transaction() as conn:
        await _in_reach(conn, source_uuid, principal)
        await registry.suspend_source(conn, str(source_uuid))
    return {"ok": True, "message": "Source suspended. Imports from it are refused."}


@router.get("/sources/{source_uuid}/batches")
async def source_batches(
    source_uuid: UUID,
    principal: CurrentUser,
    page: Annotated[PageRequest, Depends(Paging(("received_at",), "-received_at"))],
) -> dict[str, Any]:
    from cmp.db.repositories import exchange as exchange_repo

    async with connection() as conn:
        source = await repo.source_by_uuid(conn, str(source_uuid))
        if not source:
            raise NotFound("Data source")
        await registry.require_in_reach(
            conn, source, role=principal.role, user_id=principal.user_id
        )
        items, cursor, total = await exchange_repo.list_batches(
            conn,
            page,
            role=principal.role,
            user_id=principal.user_id,
            source_uuid=str(source_uuid),
        )
    return {"items": items, "next_cursor": cursor, "total": total}
