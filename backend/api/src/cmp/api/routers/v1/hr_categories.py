"""HR categories - 7 endpoints (ADR 0033).

The Legal office's registry: a category of HR activity, the processors that
hold the data collected under it, and the HR PoCs assigned to it. The Legal
PoC keeps them; an HR PoC reads the ones assigned to them; the administrator
reads all, to assign HR PoCs (`PUT /users/{uuid}/categories`).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request, status
from pydantic import Field, StringConstraints, field_validator

from cmp.api.dependencies import HrCategoryReader, HrCategoryWriter, reject_unknown_filters
from cmp.core.errors import ValidationFailed
from cmp.db.pool import connection, transaction
from cmp.db.repositories import hr_categories as repo
from cmp.domain.hr import categories
from cmp.schemas.common import LongText, Out, Schema, ShortText

router = APIRouter(prefix="/hr/categories", tags=["hr"])

#: Short and stable: WELLNESS, CSR, BGV. The database holds the same shape.
CategoryCode = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Z0-9_]{1,23}$")]


class CategoryOut(Out):
    category_uuid: UUID
    category_code: str
    name: str
    description: str | None
    status: str
    office_code: str
    processor_count: int
    poc_count: int
    template_count: int
    created_at: datetime
    updated_at: datetime
    retired_at: datetime | None


class CategoryProcessorOut(Out):
    processor_uuid: UUID
    legal_name: str
    is_in_house: bool
    processor_status: str
    #: What the processor is to the category: `hrms`, `database` or `vendor`.
    processor_role: str
    #: Who answers for it on the category's requests; None means the
    #: activity's HR PoC.
    respondent_uuid: UUID | None
    respondent_name: str | None
    respondent_email: str | None
    added_at: datetime


class CategoryPocOut(Out):
    uuid: UUID
    full_name: str
    email: str | None
    status: str
    assigned_at: datetime


class CategoryDetailOut(CategoryOut):
    processors: list[CategoryProcessorOut]
    pocs: list[CategoryPocOut]


class CategoryIn(Schema):
    category_code: CategoryCode
    name: ShortText
    description: LongText | None = None

    @field_validator("category_code", mode="before")
    @classmethod
    def _upper(cls, v: Any) -> Any:
        return v.strip().upper() if isinstance(v, str) else v


class CategoryUpdate(Schema):
    """Name and description. The code is how templates, activities and the
    trail name the category, so it does not change."""

    name: ShortText | None = None
    description: LongText | None = None


class CategoryStatusIn(Schema):
    status: Literal["active", "retired"]


class CategoryProcessorIn(Schema):
    processor_uuid: UUID
    processor_role: Literal["hrms", "database", "vendor"]
    respondent_user_uuid: UUID | None = None


class CategoryProcessorsIn(Schema):
    #: The whole set, not a change to it: what is not named is removed.
    processors: list[CategoryProcessorIn] = Field(default_factory=list, max_length=50)


@router.get("", response_model=list[CategoryOut], summary="The Legal office's categories")
async def list_categories(
    request: Request,
    principal: HrCategoryReader,
    category_status: Annotated[Literal["active", "retired"] | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> list[dict[str, Any]]:
    """An HR PoC's are the ones assigned to them."""
    reject_unknown_filters(request, {"status", "q"})
    async with connection() as conn:
        return await repo.list_categories(
            conn, role=principal.role, user_id=principal.user_id, status=category_status, q=q
        )


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(body: CategoryIn, principal: HrCategoryWriter) -> dict[str, Any]:
    """In the caller's office: the Legal office's."""
    if not principal.office:
        raise ValidationFailed("This account works in no office", field="office")
    async with transaction() as conn:
        return await categories.create(
            conn,
            category_code=body.category_code,
            name=body.name,
            description=body.description,
            office=str(principal.office),
            actor_id=principal.user_id,
        )


@router.get("/{category_uuid}", response_model=CategoryDetailOut)
async def get_category(category_uuid: UUID, principal: HrCategoryReader) -> dict[str, Any]:
    async with connection() as conn:
        category = await categories.find(
            conn, str(category_uuid), role=principal.role, user_id=principal.user_id
        )
        return {
            **category,
            "processors": await repo.processors_of(conn, category["category_id"]),
            "pocs": await repo.pocs_of(conn, category["category_id"]),
        }


@router.patch("/{category_uuid}", response_model=CategoryOut)
async def update_category(
    category_uuid: UUID, body: CategoryUpdate, principal: HrCategoryWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        return await categories.update(
            conn,
            str(category_uuid),
            name=body.name,
            description=body.description,
            role=principal.role,
            user_id=principal.user_id,
        )


@router.post("/{category_uuid}/status", response_model=CategoryOut, summary="Retire or reactivate")
async def set_category_status(
    category_uuid: UUID, body: CategoryStatusIn, principal: HrCategoryWriter
) -> dict[str, Any]:
    """A retired category takes no new template; what was given under it stands."""
    async with transaction() as conn:
        return await categories.set_status(
            conn,
            str(category_uuid),
            status=body.status,
            role=principal.role,
            user_id=principal.user_id,
        )


@router.get("/{category_uuid}/processors", response_model=list[CategoryProcessorOut])
async def list_category_processors(
    category_uuid: UUID, principal: HrCategoryReader
) -> list[dict[str, Any]]:
    async with connection() as conn:
        category = await categories.find(
            conn, str(category_uuid), role=principal.role, user_id=principal.user_id
        )
        return await repo.processors_of(conn, category["category_id"])


@router.put(
    "/{category_uuid}/processors",
    response_model=list[CategoryProcessorOut],
    summary="Set the processors that hold a category's data",
)
async def set_category_processors(
    category_uuid: UUID, body: CategoryProcessorsIn, principal: HrCategoryWriter
) -> list[dict[str, Any]]:
    """The whole set. One dropped is marked removed, not deleted; a respondent
    must be an active member of staff of the Legal office."""
    async with transaction() as conn:
        return await categories.set_processors(
            conn,
            str(category_uuid),
            processors=[
                {
                    "processor_uuid": str(p.processor_uuid),
                    "processor_role": p.processor_role,
                    "respondent_user_uuid": (
                        str(p.respondent_user_uuid) if p.respondent_user_uuid else None
                    ),
                }
                for p in body.processors
            ],
            role=principal.role,
            actor_id=principal.user_id,
        )
