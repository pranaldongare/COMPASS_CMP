"""HR activities - 6 endpoints (ADR 0033).

An activity is a project of the Legal office, made by an HR PoC from an
approved template version of a category assigned to them, and live as it is
created: its notice composed and published, its one site registered, its
open link minted, all in one transaction. Its consents are read where every
project's are (`/projects/{uuid}/consents`), and its link is re-minted or
revoked where every link is (`/links/{uuid}/...`).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import Field

from cmp.api.dependencies import RequireResource, RequireRole, reject_unknown_filters
from cmp.core.errors import NotFound
from cmp.core.permissions import Role
from cmp.core.security import unseal_token
from cmp.db.pool import connection, transaction
from cmp.db.repositories import hr_activities as repo
from cmp.domain.consent import service as consent_service
from cmp.domain.hr import activities
from cmp.schemas.common import Out, Schema, ShortText

router = APIRouter(prefix="/hr/activities", tags=["hr"])

#: Every role that reads projects; the office and the HR PoC's categories
#: narrow it in the query (ADR 0032, 0033).
ActivityReader = Annotated[Any, Depends(RequireResource("project"))]
#: Creating and upgrading an activity is the HR PoC's act.
HrPoc = Annotated[Any, Depends(RequireRole(Role.HR_USER))]
#: Closing one is the HR PoC's or Legal's.
ActivityCloser = Annotated[Any, Depends(RequireRole(Role.HR_USER, Role.LEGAL))]


class OptionPurpose(Out):
    purpose_uuid: UUID
    purpose_code: str
    name: str
    is_mandatory: bool
    display_order: int


class OptionVersion(Out):
    version_uuid: UUID
    version: int
    template_uuid: UUID
    template_code: str
    template_title: str
    slot_guidance: str | None
    slot_max_length: int
    reconsent_required: bool
    purposes: list[OptionPurpose]


class OptionCategory(Out):
    category_uuid: UUID
    category_code: str
    name: str
    versions: list[OptionVersion]


class ActivityOut(Out):
    activity_uuid: UUID
    name: str
    description: str | None
    status: str
    category_uuid: UUID
    category_code: str
    category_name: str
    version_uuid: UUID
    template_version: int
    version_status: str
    reconsent_required: bool
    template_uuid: UUID
    template_code: str
    template_title: str
    created_by_uuid: UUID
    created_by_name: str
    notice_uuid: UUID | None
    notice_code: str | None
    notice_version: int | None
    consent_count: int
    link_status: str | None
    created_at: datetime
    updated_at: datetime


class ActivityLink(Out):
    link_uuid: UUID
    status: str
    expires_at: datetime
    use_count: int
    audience_mode: str
    #: The path to share; the console puts it after the portal's address.
    url_path: str | None


class ActivityDetail(ActivityOut):
    link: ActivityLink | None


class ActivityIn(Schema):
    category_uuid: UUID
    template_version_uuid: UUID
    purpose_uuids: list[UUID] = Field(min_length=1, max_length=50)
    name: ShortText
    #: The only free text: within the version's limit, no {{, no link.
    description: Annotated[str, Field(min_length=1, max_length=4000)]
    audience_mode: Literal["sso", "otp"]
    link_expires_at: datetime


class ActivityCreated(Out):
    activity_uuid: UUID
    notice_uuid: UUID | None
    link_uuid: UUID
    url_path: str
    expires_at: datetime
    audience_mode: str


class UpgradeIn(Schema):
    template_version_uuid: UUID
    purpose_uuids: list[UUID] = Field(min_length=1, max_length=50)
    description: Annotated[str, Field(min_length=1, max_length=4000)]


class UpgradeOut(Out):
    activity_uuid: UUID
    notice_uuid: UUID
    version: int
    #: How many participants were asked to consent again.
    reconsent_requested: int


class CloseIn(Schema):
    reason: Annotated[str | None, Field(default=None, max_length=2000)] = None


class Closed(Out):
    project_uuid: UUID
    to: str
    links_revoked: int


@router.get("", response_model=list[ActivityOut], summary="HR activities in scope")
async def list_activities(
    request: Request,
    principal: ActivityReader,
    activity_status: Annotated[str | None, Query(alias="status")] = None,
    category: Annotated[UUID | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> list[dict[str, Any]]:
    """Legal's all; an HR PoC's, of the categories assigned to them."""
    reject_unknown_filters(request, {"status", "category", "q"})
    async with connection() as conn:
        return await repo.list_activities(
            conn,
            role=principal.role,
            user_id=principal.user_id,
            status=activity_status,
            category_uuid=str(category) if category else None,
            q=q,
        )


@router.get(
    "/options",
    response_model=list[OptionCategory],
    summary="What an activity can be made from",
)
async def activity_options(principal: HrPoc) -> list[dict[str, Any]]:
    """The HR PoC's active categories, each with its templates' approved
    versions and their purposes, the mandatory ones marked."""
    async with connection() as conn:
        return await activities.options(conn, role=principal.role, user_id=principal.user_id)


@router.post(
    "",
    response_model=ActivityCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Create an activity, live, with its link",
)
async def create_activity(body: ActivityIn, principal: HrPoc) -> dict[str, Any]:
    """One transaction: project, site, notice composed and published, link.
    A purpose off the version's list or a mandatory one left out, a
    description outside the slot: 422 and nothing written. A retired version:
    409."""
    async with transaction() as conn:
        return await activities.create(
            conn,
            actor_id=principal.user_id,
            role=principal.role,
            category_uuid=str(body.category_uuid),
            template_version_uuid=str(body.template_version_uuid),
            purpose_uuids=[str(u) for u in body.purpose_uuids],
            name=body.name,
            description=body.description,
            audience_mode=body.audience_mode,
            link_expires_at=body.link_expires_at,
        )


@router.get("/{activity_uuid}", response_model=ActivityDetail)
async def get_activity(activity_uuid: UUID, principal: ActivityReader) -> dict[str, Any]:
    async with connection() as conn:
        found = await repo.by_uuid(
            conn, str(activity_uuid), role=principal.role, user_id=principal.user_id
        )
        if not found:
            raise NotFound("Activity")
        link = await repo.live_link(conn, int(found["project_id"]))
    if link:
        token = unseal_token(link.pop("token_sealed", None))
        link = {**link, "url_path": consent_service.link_path(token) if token else None}
    return {**found, "link": link}


@router.post(
    "/{activity_uuid}/upgrade",
    response_model=UpgradeOut,
    summary="Move an activity to another approved version",
)
async def upgrade_activity(
    activity_uuid: UUID, body: UpgradeIn, principal: HrPoc
) -> dict[str, Any]:
    """A new notice version, published; the live link moves to it. A version
    flagged for re-consent asks every participant again, after commit."""
    async with transaction() as conn:
        return await activities.upgrade(
            conn,
            str(activity_uuid),
            actor_id=principal.user_id,
            role=principal.role,
            template_version_uuid=str(body.template_version_uuid),
            purpose_uuids=[str(u) for u in body.purpose_uuids],
            description=body.description,
        )


@router.post("/{activity_uuid}/close", response_model=Closed, summary="Close an activity")
async def close_activity(
    activity_uuid: UUID, body: CloseIn, principal: ActivityCloser
) -> dict[str, Any]:
    """Its link stops resolving; consents given stand."""
    async with transaction() as conn:
        result = await activities.close(
            conn,
            str(activity_uuid),
            actor_id=principal.user_id,
            role=principal.role,
            reason=body.reason,
        )
    return result
