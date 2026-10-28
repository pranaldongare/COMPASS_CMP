"""Notice templates (0044): the DPO's notices before there is a project, and
the Legal office's for each category of HR activity (0052).

Writing a template is an officer's, like writing a notice: the DPO's in the
DPO office, the Legal PoC's in the Legal office, each reading and writing only
their own office's (ADR 0032), so every route that changes one is
`TemplateWriter`. Reading one by its ID is wider: the R&D User the DPO gave
`TPL-0007` to looks it up before attaching it to their project, so that route
takes the notice author's guard. Attaching itself is
`POST /projects/{project_uuid}/notices/from-template`, beside the other ways a
notice reaches a project, in the notices router.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import Field

from cmp.api.dependencies import (
    RequireResource,
    TemplateReader,
    TemplateWriter,
    reject_unknown_filters,
)
from cmp.core.enums import NoticeAudience
from cmp.core.errors import ValidationFailed
from cmp.db.pool import connection, transaction
from cmp.db.repositories import notice_templates as repo
from cmp.domain.notices import templates as service
from cmp.domain.notices import versions
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
    #: The category a Legal office template belongs to (0052); required there,
    #: refused for a DPO office template.
    category_uuid: UUID | None = None


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
    #: The office it belongs to (ADR 0032) and, for the Legal office's, its
    #: category (0052).
    office_code: str
    category_uuid: UUID | None = None
    category_code: str | None = None
    category_name: str | None = None
    #: How many versions a Legal office template has (0053); 0 for the DPO's.
    version_count: int = 0


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
    summary="The office's notice templates, newest first",
)
async def list_templates(
    request: Request,
    principal: TemplateReader,
    template_status: Annotated[str | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    category: Annotated[UUID | None, Query()] = None,
) -> list[dict[str, Any]]:
    """`category` keeps one category's: the Legal office's templates for it."""
    reject_unknown_filters(request, {"status", "q", "category"})
    if template_status not in (None, "", *service.STATUSES):
        raise ValidationFailed("status must be active or retired", field="status")
    async with connection() as conn:
        return await repo.list_all(
            conn,
            status=template_status or None,
            q=q,
            category_uuid=str(category) if category else None,
        )


@router.post(
    "/notice-templates",
    response_model=TemplateDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Write a notice template, before any project exists",
)
async def create_template(body: TemplateIn, principal: TemplateWriter) -> dict[str, Any]:
    """In the caller's office; a Legal office template names its category."""
    if not principal.office:
        raise ValidationFailed("This account works in no office", field="office")
    async with transaction() as conn:
        return await service.create(
            conn,
            actor_id=principal.user_id,
            office=str(principal.office),
            category_uuid=str(body.category_uuid) if body.category_uuid else None,
            role=principal.role,
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
async def get_template(template_uuid: UUID, principal: TemplateReader) -> dict[str, Any]:
    async with connection() as conn:
        return await service.detail(conn, await service.require(conn, str(template_uuid)))


@router.put("/notice-templates/{template_uuid}", response_model=TemplateDetail)
async def update_template(
    template_uuid: UUID, body: TemplateUpdate, principal: TemplateWriter
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
    template_uuid: UUID, body: TemplateStatusIn, principal: TemplateWriter
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
    template_uuid: UUID, body: TemplatePurposeIn, principal: TemplateWriter
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
    template_uuid: UUID, purpose_uuid: UUID, principal: TemplateWriter
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
    template_uuid: UUID, code: str, body: TemplateLanguageIn, principal: TemplateWriter
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
    template_uuid: UUID, code: str, principal: TemplateWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        template = await service.require(conn, str(template_uuid))
        return await service.remove_language(conn, template, language_code=code)


# ================================================================ versions
#
# The Legal office's templates are versioned (0053, ADR 0033): a version is
# the legal text Legal approves once, and every activity made from it
# inherits that approval. A DPO office template is not (409).

V = "/notice-templates/{template_uuid}/versions"


class VersionLanguageOut(Out):
    language_code: str
    locked_text: str
    #: Set when the version is approved; an activity checks it before use.
    content_hash: str | None
    updated_at: datetime
    updated_by_name: str


class VersionPurposeOut(Out):
    purpose_uuid: UUID
    purpose_code: str
    name: str
    status: str
    lawful_basis: str
    data_categories: list[str]
    is_mandatory: bool
    display_order: int


class VersionOut(Out):
    version_uuid: UUID
    version: int
    status: str
    reconsent_required: bool
    slot_guidance: str | None
    slot_max_length: int
    withdraw_url: str
    exercise_rights_url: str
    board_complaint_url: str
    dpo_contact: str
    applicable_to: str | None
    template_uuid: UUID
    template_code: str
    template_title: str
    category_uuid: UUID | None
    category_code: str | None
    created_by_name: str
    created_at: datetime
    updated_at: datetime
    approved_by_name: str | None
    approved_at: datetime | None
    retired_at: datetime | None
    language_count: int
    purpose_count: int
    #: How many activities were made from it.
    activity_count: int


class VersionDetail(VersionOut):
    languages: list[VersionLanguageOut]
    purposes: list[VersionPurposeOut]


class VersionUpdate(Schema):
    reconsent_required: bool | None = None
    #: Shown to the HR PoC beside the description box.
    slot_guidance: Annotated[str | None, Field(default=None, max_length=2000)] = None
    slot_max_length: Annotated[int | None, Field(default=None, ge=100, le=4000)] = None
    withdraw_url: HttpUrl | None = None
    exercise_rights_url: HttpUrl | None = None
    board_complaint_url: HttpUrl | None = None
    dpo_contact: Annotated[str | None, Field(default=None, min_length=3, max_length=255)] = None
    applicable_to: NoticeAudience | None = None


class VersionLanguageIn(Schema):
    #: The legal text, with `{{purposes}}` and `{{description}}` exactly once each.
    locked_text: NoticeText


class VersionPurposeIn(Schema):
    purpose_uuid: UUID
    is_mandatory: bool = False
    display_order: Annotated[int | None, Field(default=None, ge=0, le=999)] = None


class VersionPurposesIn(Schema):
    #: The whole list, in order: what is not named is taken off.
    purposes: list[VersionPurposeIn] = Field(default_factory=list, max_length=50)


class VersionStatusIn(Schema):
    status: Annotated[str, Field(pattern="^retired$", description="retired")]


class VersionPreview(Out):
    language_code: str
    text: str
    content_hash: str


async def _version(conn: Any, template_uuid: UUID, number: int) -> tuple[Any, Any]:
    template = await service.require(conn, str(template_uuid))
    return template, await versions.require(conn, template, number)


@router.get(V, response_model=list[VersionOut], summary="A Legal office template's versions")
async def list_versions(template_uuid: UUID, principal: TemplateReader) -> list[dict[str, Any]]:
    async with connection() as conn:
        template = await service.require(conn, str(template_uuid))
        return await versions.list_versions(conn, template)


@router.post(
    V,
    response_model=VersionDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Open the next version as a draft",
)
async def open_version(template_uuid: UUID, principal: TemplateWriter) -> dict[str, Any]:
    """A copy of the last version's content, or the template's links and
    contact for the first. One draft at a time."""
    async with transaction() as conn:
        template = await service.require(conn, str(template_uuid))
        return await versions.open_version(conn, template, actor_id=principal.user_id)


@router.get(f"{V}/{{number}}", response_model=VersionDetail)
async def get_version(
    template_uuid: UUID, number: int, principal: TemplateReader
) -> dict[str, Any]:
    async with connection() as conn:
        _, version = await _version(conn, template_uuid, number)
        return await versions.detail(conn, version)


@router.patch(f"{V}/{{number}}", response_model=VersionDetail, summary="Edit a draft version")
async def update_version(
    template_uuid: UUID, number: int, body: VersionUpdate, principal: TemplateWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        _, version = await _version(conn, template_uuid, number)
        return await versions.update(conn, version, fields=body.model_dump(exclude_unset=True))


@router.put(
    f"{V}/{{number}}/languages/{{code}}",
    response_model=VersionDetail,
    summary="A draft version's locked text in one language",
)
async def set_version_language(
    template_uuid: UUID,
    number: int,
    code: str,
    body: VersionLanguageIn,
    principal: TemplateWriter,
) -> dict[str, Any]:
    async with transaction() as conn:
        _, version = await _version(conn, template_uuid, number)
        return await versions.set_language(
            conn,
            version,
            language_code=code,
            locked_text=body.locked_text,
            actor_id=principal.user_id,
        )


@router.delete(f"{V}/{{number}}/languages/{{code}}", response_model=VersionDetail)
async def remove_version_language(
    template_uuid: UUID, number: int, code: str, principal: TemplateWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        _, version = await _version(conn, template_uuid, number)
        return await versions.remove_language(conn, version, language_code=code)


@router.put(
    f"{V}/{{number}}/purposes",
    response_model=VersionDetail,
    summary="The purposes an activity may choose, and which are mandatory",
)
async def set_version_purposes(
    template_uuid: UUID, number: int, body: VersionPurposesIn, principal: TemplateWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        _, version = await _version(conn, template_uuid, number)
        return await versions.set_purposes(
            conn,
            version,
            purposes=[
                {
                    "purpose_uuid": str(p.purpose_uuid),
                    "is_mandatory": p.is_mandatory,
                    **({"display_order": p.display_order} if p.display_order is not None else {}),
                }
                for p in body.purposes
            ],
        )


@router.post(
    f"{V}/{{number}}/approve",
    response_model=VersionDetail,
    summary="Approve a draft version: hashed and frozen",
)
async def approve_version(
    template_uuid: UUID, number: int, principal: TemplateWriter
) -> dict[str, Any]:
    """Refused while a purpose is not active (409), or a language lacks a slot
    or the English text is missing (422). Then every activity made from it
    inherits this approval."""
    async with transaction() as conn:
        template, version = await _version(conn, template_uuid, number)
        return await versions.approve(conn, template, version, actor_id=principal.user_id)


@router.post(
    f"{V}/{{number}}/status",
    response_model=VersionDetail,
    summary="Retire an approved version",
)
async def set_version_status(
    template_uuid: UUID, number: int, body: VersionStatusIn, principal: TemplateWriter
) -> dict[str, Any]:
    """No new activity starts on a retired version; those on it go on."""
    async with transaction() as conn:
        _, version = await _version(conn, template_uuid, number)
        return await versions.retire(conn, version, actor_id=principal.user_id)


@router.get(
    f"{V}/{{number}}/preview",
    response_model=list[VersionPreview],
    summary="What an activity made from it would serve",
)
async def preview_version(
    template_uuid: UUID,
    number: int,
    principal: TemplateReader,
    description: Annotated[str | None, Query(max_length=4000)] = None,
) -> list[dict[str, Any]]:
    """Every purpose on the list and the description given (or a sample), per
    language, with the hash that text would carry."""
    async with connection() as conn:
        _, version = await _version(conn, template_uuid, number)
        return await versions.preview(conn, version, description=description)
