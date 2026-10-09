"""Users and provisioning - 11 endpoints.

There is no self-registration for staff and no DELETE. Accounts deactivate,
never delete: deleting orphans the audit trail, and an audit row whose actor
cannot be resolved is an audit row that proves nothing.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import Field

from cmp.api.dependencies import (
    Paging,
    RequireAdmin,
    RequireDPOorAdmin,
    RequireRole,
    RequireStaff,
    reject_unknown_filters,
)
from cmp.auth.sessions import service as sessions
from cmp.core.pagination import PageRequest
from cmp.core.permissions import Role
from cmp.db.pool import connection, transaction
from cmp.db.repositories import registry as registry_repo
from cmp.db.repositories import users as repo
from cmp.domain.users import service as users
from cmp.schemas.common import Acknowledged, Mobile, Out, Page, Schema, ShortText
from cmp.validation import Email

router = APIRouter(prefix="/users", tags=["users"])

user_paging = Paging(repo.LIST_SORTS, "-created_at")


class CollectorProcessor(Out):
    """A processor a DCO or an RCO collects for (0050)."""

    processor_uuid: UUID
    legal_name: str
    is_in_house: bool
    status: str


class UserOut(Out):
    uuid: UUID
    username: str | None
    full_name: str
    #: None for a data principal who registered with a mobile alone. Staff
    #: always have one; the register lists both kinds of account.
    email: str | None
    mobile: str | None
    organization_id: str | None
    role: str
    person_type: str | None
    status: str
    created_at: Any
    updated_at: Any
    #: Present only on the create response, naming what was assigned in the same
    #: request. The full list lives at `/sources?owner=…`, which stays right as
    #: sources change hands.
    sources: list[str] | None = None
    #: The processors a DCO or an RCO collects for: they see those processors'
    #: data sources and no others (0050). On one account's page only; `None`
    #: on the register and for every other role.
    processors: list[CollectorProcessor] | None = None


class CreateUser(Schema):
    full_name: ShortText
    email: Email
    role: str
    username: Annotated[str | None, Field(default=None, max_length=120)] = None
    mobile: Mobile | None = None
    organization_id: Annotated[str | None, Field(default=None, max_length=60)] = None
    person_type: str | None = None
    #: The data sources this person will be accountable for, assigned as part of
    #: creating them.
    #:
    #: Here because it is the moment somebody knows the answer. An account
    #: created without sources is a Data Collection Owner who owns nothing, does
    #: not appear in any routing, and is discovered to be idle later - so the
    #: question is asked while the person creating the account still has the
    #: context to answer it.
    #:
    #: Only for the roles that can hold one. A DPO or an administrator owning a
    #: rig would be a category error, and is refused rather than ignored.
    source_uuids: list[UUID] = Field(default_factory=list)
    #: The processors this DCO or RCO collects for (0050) - third parties for a
    #: DCO, in-house teams for an RCO. The processor of every source above is
    #: added whether or not it is named here.
    processor_uuids: list[UUID] = Field(default_factory=list)


class SetProcessors(Schema):
    #: The whole set, not a change to it: what is not named is taken away.
    processor_uuids: list[UUID] = Field(default_factory=list, max_length=50)


class UpdateUser(Schema):
    full_name: ShortText | None = None
    mobile: Mobile | None = None
    organization_id: Annotated[str | None, Field(default=None, max_length=60)] = None


class RoleChange(Schema):
    role: str
    reason: Annotated[str | None, Field(default=None, max_length=500)] = None


class PersonTypeHistoryOut(Out):
    history_uuid: UUID
    from_type: str | None
    to_type: str
    reason: str | None
    changed_at: Any
    changed_by_uuid: UUID
    changed_by_name: str


class CollectionOwner(Out):
    """Somebody who can be accountable for a data source.

    Four fields, and the role is one of them because it constrains the choice
    rather than merely describing it: an RCO owns in-house collection and a DCO
    a third party's, so the two are not interchangeable.
    """

    uuid: UUID
    full_name: str
    email: str
    role: str


@router.get(
    "/staff",
    response_model=list[CollectionOwner],
    summary="Active staff, for naming a processor's respondent",
)
async def staff_directory(
    principal: Annotated[Any, Depends(RequireRole(Role.DPO, Role.ADMIN))],
) -> list[dict[str, Any]]:
    """Naming who answers a rights-request ticket for an in-house processor
    means picking an account. Four fields, active staff only, and only for the
    two roles that manage the registry - not a way around the register."""
    async with connection() as conn:
        return await repo.staff_directory(conn)


@router.get(
    "/collection-owners",
    response_model=list[CollectionOwner],
    summary="Active DCOs and RCOs, for source ownership",
)
async def collection_owners(
    principal: RequireStaff, processor: Annotated[UUID | None, Query()] = None
) -> list[dict[str, Any]]:
    """The ownership lookup.

    Making somebody accountable for a data source means picking a person, and
    the people who do it - a DCO Admin routing a project, an R&D owner naming an
    RCO - cannot read the account register. Without this the operation is
    unsatisfiable: the form has nothing to offer.

    Scoped to exactly what the choice needs - active DCOs and RCOs, four fields -
    so it is not a way around the register's own restrictions. Declared before
    `/users/{uuid}` so the literal path is matched first.

    `processor` keeps those who collect for it (0050): the people one of its
    sources can be handed to.
    """
    async with connection() as conn:
        return await repo.collection_owners(
            conn, processor_uuid=str(processor) if processor else None
        )


@router.get("", response_model=Page[UserOut], summary="The staff and subject register")
async def list_users(
    request: Request,
    principal: RequireDPOorAdmin,
    page: Annotated[PageRequest, Depends(user_paging)],
    role: Annotated[str | None, Query()] = None,
    user_status: Annotated[str | None, Query(alias="status")] = None,
    person_type: Annotated[str | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    person: Annotated[UUID | None, Query()] = None,
) -> dict[str, Any]:
    """`person` is one account by uuid: the destination of a link that names someone."""
    reject_unknown_filters(request, {"role", "status", "person_type", "q", "person"})
    async with connection() as conn:
        items, cursor, total = await repo.list_users(
            conn,
            page,
            role=role,
            status=user_status,
            person_type=person_type,
            q=q,
            person=str(person) if person else None,
        )
    return {"items": items, "next_cursor": cursor, "total": total}


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(body: CreateUser, principal: RequireAdmin) -> dict[str, Any]:
    """Provision a staff account. Administrators only - no self-registration."""
    async with transaction() as conn:
        user, assigned = await users.create_staff(
            conn,
            full_name=body.full_name,
            email=str(body.email),
            role=body.role,
            username=body.username,
            mobile=body.mobile,
            organization_id=body.organization_id,
            person_type=body.person_type,
            source_uuids=[str(u) for u in body.source_uuids],
            processor_uuids=[str(u) for u in body.processor_uuids],
            actor_id=principal.user_id,
        )
    return {**user, "sources": assigned}


@router.post(
    "/{user_uuid}/invite",
    response_model=Acknowledged,
    summary="Send the invitation again",
)
async def resend_invitation(user_uuid: UUID, principal: RequireAdmin) -> dict[str, Any]:
    """Write to somebody again about the account waiting for them.

    Needed because the invitation is dispatched optionally - the account is
    created whether or not the message could be queued - and a message nobody
    received is invisible to everybody except the person waiting for it.
    """
    async with transaction() as conn:
        user = await users.resend_invitation(conn, str(user_uuid))
    return {"ok": True, "message": f"A new invitation is on its way to {user['email']}."}


@router.get("/{user_uuid}", response_model=UserOut)
async def get_user(user_uuid: UUID, principal: RequireDPOorAdmin) -> dict[str, Any]:
    async with connection() as conn:
        user = await repo.require_by_uuid(conn, str(user_uuid))
        if user["role"] in users.SOURCE_OWNING_ROLES:
            user = {
                **user,
                "processors": await registry_repo.processors_of_collector(conn, user["id"]),
            }
        return user


@router.put(
    "/{user_uuid}/processors",
    response_model=list[CollectorProcessor],
    summary="Set the processors a DCO or an RCO collects for",
)
async def set_processors(
    user_uuid: UUID, body: SetProcessors, principal: RequireAdmin
) -> list[dict[str, Any]]:
    """The whole set (0050). A DCO or an RCO sees the data sources of these
    processors and no others, and registers new ones only under them. A
    processor whose sources they are still accountable for is not taken away:
    hand the sources on first, on each source."""
    async with transaction() as conn:
        return await users.set_processors(
            conn,
            str(user_uuid),
            processor_uuids=[str(u) for u in body.processor_uuids],
            actor_id=principal.user_id,
        )


@router.patch("/{user_uuid}", response_model=UserOut)
async def update_user(user_uuid: UUID, body: UpdateUser, principal: RequireAdmin) -> dict[str, Any]:
    """Name, mobile, organisation id. A changed mobile is sent a code."""
    async with transaction() as conn:
        return await users.update_profile(
            conn,
            str(user_uuid),
            full_name=body.full_name,
            mobile=body.mobile,
            organization_id=body.organization_id,
        )


@router.post("/{user_uuid}/role", response_model=Acknowledged, summary="Change a role")
async def change_role(user_uuid: UUID, body: RoleChange, principal: RequireAdmin) -> dict[str, Any]:
    async with transaction() as conn:
        user = await users.change_role(
            conn, str(user_uuid), role=body.role, reason=body.reason, actor_id=principal.user_id
        )
    # A role change must not leave a session carrying the old role's permissions.
    revoked = await sessions.revoke_all(user["id"])
    return {"ok": True, "message": f"Role changed. {revoked} session(s) terminated."}


@router.post("/{user_uuid}/deactivate", response_model=Acknowledged)
async def deactivate(user_uuid: UUID, principal: RequireAdmin) -> dict[str, Any]:
    """End a member of staff's access, or switch a data principal's account off.

    For staff the role and the password go and the person stays as a data
    principal; a data principal's account is switched off (`users.deactivate`).
    """
    async with transaction() as conn:
        user, kept = await users.deactivate(conn, str(user_uuid), actor_id=principal.user_id)
    revoked = await sessions.revoke_all(user["id"])
    if kept:
        what = "Temporary access" if user["role"] == Role.BREACH_HOLDER.value else "Staff access"
        return {
            "ok": True,
            "message": (
                f"{what} ended. {user['full_name']} keeps their account as a data "
                f"principal. {revoked} session(s) terminated."
            ),
        }
    return {"ok": True, "message": f"Deactivated. {revoked} session(s) terminated."}


@router.post("/{user_uuid}/reactivate", response_model=Acknowledged)
async def reactivate(user_uuid: UUID, principal: RequireAdmin) -> dict[str, Any]:
    async with transaction() as conn:
        await users.reactivate(conn, str(user_uuid))
    return {"ok": True, "message": "Reactivated."}


@router.delete("/{user_uuid}/sessions", response_model=Acknowledged, summary="Force logout")
async def force_logout(user_uuid: UUID, principal: RequireAdmin) -> dict[str, Any]:
    async with transaction() as conn:
        user = await users.record_forced_sign_out(conn, str(user_uuid))
    revoked = await sessions.revoke_all(user["id"])
    return {"ok": True, "message": f"{revoked} session(s) terminated."}


@router.post("/{user_uuid}/mfa/reset", response_model=Acknowledged)
async def reset_mfa(user_uuid: UUID, principal: RequireAdmin) -> dict[str, Any]:
    async with transaction() as conn:
        user = await users.reset_mfa(conn, str(user_uuid))
    await sessions.revoke_all(user["id"])
    return {"ok": True, "message": "MFA reset. The user must sign in again."}


@router.get("/{user_uuid}/person-type-history", response_model=list[PersonTypeHistoryOut])
async def person_type_history(
    user_uuid: UUID, principal: RequireDPOorAdmin
) -> list[dict[str, Any]]:
    """A type change never creates a second account.

    If an employee becomes a volunteer and gets a new row, her rights requests
    return half her data and nobody notices until she complains.
    """
    async with connection() as conn:
        user = await repo.require_by_uuid(conn, str(user_uuid))
        return await repo.person_type_history(conn, user["id"])
