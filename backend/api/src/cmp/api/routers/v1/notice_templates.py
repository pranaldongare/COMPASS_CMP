"""Notice templates (0044): the DPO's notices before there is a project.

Writing a template is the Privacy Office's, like writing a notice, so every
route that changes one is `RequireDPO`. Reading one by its ID is wider: the
R&D User the DPO gave `TPL-0007` to looks it up before attaching it to their
project, so that route takes the notice author's guard. Attaching itself is
`POST /projects/{project_uuid}/notices/from-template`, beside the other ways a
notice reaches a project, in the notices router.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import Field

from cmp.api.dependencies import RequireDPO, RequireResource, reject_unknown_filters
from cmp.core.enums import NoticeAudience
from cmp.core.errors import ValidationFailed
from cmp.db.pool import connection, transaction
from cmp.db.repositories import notice_templates as repo
from cmp.domain.notices import templates as service
from cmp.schemas.common import HttpUrl, NoticeText, Out, Schema

router = APIRouter(tags=["notice templates"])

NoticeAuthor = Annotated[Any, Depends(RequireResource("notice", write=True))]


class TemplateIn(Schema):
    #: What the DPO calls it, so the list reads as a list: "Gait studies, adults".
    title: Annotated[str, Field(min_length=3, max_length=200)]
    withdraw_url: HttpUrl
    exercise_rights_url: HttpUrl
    board_complaint_url: HttpUrl = Field(
        description="The Data Protection Board portal, NOT the internal grievance form"
    )
    dpo_contact: Annotated[str, Field(min_length=3, max_length=255)]
    applicable_to: NoticeAudience | None = None
    note: Annotated[str | None, Field(default=None, max_length=4000)] = None
    #: The first text, if the DPO has it to hand. More languages are added after.
    rendered_text: NoticeText | None = None
    language_code: Annotated[str | None, Field(default=None, max_length=40)] = None


class TemplateUpdate(Schema):
    title: Annotated[str | None, Field(default=None, min_length=3, max_length=200)] = None
    withdraw_url: HttpUrl | None = None
    exercise_rights_url: HttpUrl | None = None
    board_complaint_url: HttpUrl | None = None
    dpo_contact: Annotated[str | None, Field(default=None, min_length=3, max_length=255)] = None
    applicable_to: NoticeAudience | None = None
    note: Annotated[str | None, Field(default=None, max_length=4000)] = None


class TemplatePurposeIn(Schema):
    purpose_uuid: UUID
    display_order: Annotated[int, Field(default=0, ge=0, le=999)] = 0
    is_mandatory: bool = False


class TemplateLanguageIn(Schema):
    rendered_text: NoticeText


class TemplateStatusIn(Schema):
    status: Annotated[str, Field(description="active or retired")]


class TemplateOut(Out):
    template_uuid: UUID
    #: The ID the DPO gives out: `TPL-0007`.
    template_code: str
    title: str
    withdraw_url: str
    exercise_rights_url: str
    board_complaint_url: str
    dpo_contact: str
    applicable_to: str | None
    note: str | None
    status: str
    created_by_name: str
    created_at: datetime
    updated_at: datetime
    retired_at: datetime | None
    purpose_count: int
    language_count: int
    #: How many project notices were made from it.
    used_count: int


class TemplatePurposeOut(Out):
    purpose_uuid: UUID
    purpose_code: str
    name: str
    status: str
    lawful_basis: str
    data_categories: list[str]
    display_order: int
    is_mandatory: bool


class TemplateLanguageOut(Out):
    language_code: str
    rendered_text: str
    updated_at: datetime
    updated_by_name: str


class TemplateNoticeOut(Out):
    """A project notice made from the template."""

    notice_uuid: UUID
    notice_code: str
    version: int
    status: str
    created_at: datetime
    project_uuid: UUID
    project_name: str


class TemplateDetail(TemplateOut):
    purposes: list[TemplatePurposeOut]
    languages: list[TemplateLanguageOut]
    notices: list[TemplateNoticeOut]


class TemplateFound(TemplateOut):
    """What the R&D User sees before attaching one: what it carries, not where
    else it was used."""

    purposes: list[TemplatePurposeOut]
    languages: list[TemplateLanguageOut]


@router.get(
    "/notice-templates",
    response_model=list[TemplateOut],
    summary="The DPO's notice templates, newest first",
)
async def list_templates(
    request: Request,
    principal: RequireDPO,
    template_status: Annotated[str | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> list[dict[str, Any]]:
    reject_unknown_filters(request, {"status", "q"})
    if template_status not in (None, "", *service.STATUSES):
        raise ValidationFailed("status must be active or retired", field="status")
    async with connection() as conn:
        return await repo.list_all(conn, status=template_status or None, q=q)


@router.post(
    "/notice-templates",
    response_model=TemplateDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Write a notice template, before any project exists",
)
async def create_template(body: TemplateIn, principal: RequireDPO) -> dict[str, Any]:
    async with transaction() as conn:
        return await service.create(
            conn,
            actor_id=principal.user_id,
            title=body.title,
            withdraw_url=body.withdraw_url,
            exercise_rights_url=body.exercise_rights_url,
            board_complaint_url=body.board_complaint_url,
            dpo_contact=body.dpo_contact,
            applicable_to=body.applicable_to or None,
            note=body.note,
            language_code=body.language_code,
            rendered_text=body.rendered_text,
        )


@router.get(
    "/notice-templates/by-code/{template_code}",
    response_model=TemplateFound,
    summary="Look up a template by the ID the DPO gave out, before attaching it",
)
async def find_template(template_code: str, principal: NoticeAuthor) -> dict[str, Any]:
    async with connection() as conn:
        return await service.find(conn, template_code)


@router.get("/notice-templates/{template_uuid}", response_model=TemplateDetail)
async def get_template(template_uuid: UUID, principal: RequireDPO) -> dict[str, Any]:
    async with connection() as conn:
        return await service.detail(conn, await service.require(conn, str(template_uuid)))


@router.put("/notice-templates/{template_uuid}", response_model=TemplateDetail)
async def update_template(
    template_uuid: UUID, body: TemplateUpdate, principal: RequireDPO
) -> dict[str, Any]:
    async with transaction() as conn:
        template = await service.require(conn, str(template_uuid))
        return await service.update(
            conn,
            template,
            actor_id=principal.user_id,
            **body.model_dump(exclude_unset=True),
        )


@router.post(
    "/notice-templates/{template_uuid}/status",
    response_model=TemplateDetail,
    summary="Retire a template, or bring it back",
)
async def set_template_status(
    template_uuid: UUID, body: TemplateStatusIn, principal: RequireDPO
) -> dict[str, Any]:
    async with transaction() as conn:
        template = await service.require(conn, str(template_uuid))
        return await service.set_status(conn, template, status=body.status)


@router.post(
    "/notice-templates/{template_uuid}/purposes",
    response_model=TemplateDetail,
    status_code=status.HTTP_201_CREATED,
)
async def attach_template_purpose(
    template_uuid: UUID, body: TemplatePurposeIn, principal: RequireDPO
) -> dict[str, Any]:
    async with transaction() as conn:
        template = await service.require(conn, str(template_uuid))
        return await service.attach_purpose(
            conn,
            template,
            purpose_uuid=str(body.purpose_uuid),
            display_order=body.display_order,
            is_mandatory=body.is_mandatory,
        )


@router.delete(
    "/notice-templates/{template_uuid}/purposes/{purpose_uuid}",
    response_model=TemplateDetail,
)
async def detach_template_purpose(
    template_uuid: UUID, purpose_uuid: UUID, principal: RequireDPO
) -> dict[str, Any]:
    async with transaction() as conn:
        template = await service.require(conn, str(template_uuid))
        return await service.detach_purpose(conn, template, purpose_uuid=str(purpose_uuid))


@router.put(
    "/notice-templates/{template_uuid}/languages/{code}",
    response_model=TemplateDetail,
    summary="The template's text in one language, added or replaced",
)
async def set_template_language(
    template_uuid: UUID, code: str, body: TemplateLanguageIn, principal: RequireDPO
) -> dict[str, Any]:
    async with transaction() as conn:
        template = await service.require(conn, str(template_uuid))
        return await service.set_language(
            conn,
            template,
            language_code=code,
            rendered_text=body.rendered_text,
            actor_id=principal.user_id,
        )


@router.delete(
    "/notice-templates/{template_uuid}/languages/{code}",
    response_model=TemplateDetail,
)
async def remove_template_language(
    template_uuid: UUID, code: str, principal: RequireDPO
) -> dict[str, Any]:
    async with transaction() as conn:
        template = await service.require(conn, str(template_uuid))
        return await service.remove_language(conn, template, language_code=code)
