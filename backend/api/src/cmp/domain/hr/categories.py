"""The Legal office's categories: written, retired, their processors, their HR PoCs.

The Legal PoC keeps the categories of their office and the processors on each;
the administrator assigns HR PoCs to them, as they assign a DCO's processors.
A category is retired, never deleted: templates and, later, activities and the
consents given under them name it.
"""

from __future__ import annotations

from typing import Any

from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.core.permissions import Role
from cmp.db.repositories import hr_categories as repo
from cmp.db.repositories import registry as registry_repo
from cmp.db.repositories import users as users_repo
from cmp.db.sql import Conn, unique_violation
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event

#: What a processor is to a category: the HR system of record, a database the
#: data is copied into, or a vendor that runs the activity.
PROCESSOR_ROLES = ("hrms", "database", "vendor")

#: The accounts that may answer for a category's processor. Not a data
#: principal and not a breach-only login (S3-09, BD-19), as for a processor's
#: respondent.
_NOT_A_RESPONDENT = frozenset({Role.DATA_SUBJECT.value, Role.BREACH_HOLDER.value})


async def create(
    conn: Conn,
    *,
    category_code: str,
    name: str,
    description: str | None,
    office: str,
    actor_id: int,
) -> dict[str, Any]:
    try:
        category = await repo.create(
            conn,
            category_code=category_code,
            name=name,
            description=description,
            office=office,
            created_by=actor_id,
        )
    except Exception as exc:
        if unique_violation(exc):
            raise Conflict("That category code already exists", code="category_code_taken") from exc
        raise
    await audit.record(
        conn,
        event=Event.HR_CATEGORY_CREATED,
        entity_type="hr_category",
        entity_id=category["category_id"],
        detail={"category_code": category_code},
    )
    return category


async def find(conn: Conn, category_uuid: str, *, role: Role | str, user_id: int) -> dict[str, Any]:
    """A category the caller may read, or 404: one outside their office or,
    for an HR PoC, outside their assignments, is not there for them."""
    category = await repo.by_uuid(conn, category_uuid, role=role, user_id=user_id)
    if not category:
        raise NotFound("Category")
    return category


async def update(
    conn: Conn,
    category_uuid: str,
    *,
    name: str | None,
    description: str | None,
    role: Role | str,
    user_id: int,
) -> dict[str, Any]:
    category = await find(conn, category_uuid, role=role, user_id=user_id)
    await repo.update(conn, category["category_id"], name=name, description=description)
    await audit.record(
        conn,
        event=Event.HR_CATEGORY_UPDATED,
        entity_type="hr_category",
        entity_id=category["category_id"],
    )
    fresh = await repo.by_id(conn, category["category_id"])
    assert fresh is not None
    return fresh


async def set_status(
    conn: Conn, category_uuid: str, *, status: str, role: Role | str, user_id: int
) -> dict[str, Any]:
    """Retire or reactivate. A retired category takes no new template and,
    from increment 3, no new activity; what was given under it stands."""
    category = await find(conn, category_uuid, role=role, user_id=user_id)
    if category["status"] == status:
        raise Conflict(f"That category is already {status}", code="category_status_unchanged")
    await repo.lock(conn, category["category_id"])
    await repo.set_status(conn, category["category_id"], status)
    await audit.record(
        conn,
        event=Event.HR_CATEGORY_RETIRED if status == "retired" else Event.HR_CATEGORY_REACTIVATED,
        entity_type="hr_category",
        entity_id=category["category_id"],
    )
    fresh = await repo.by_id(conn, category["category_id"])
    assert fresh is not None
    return fresh


async def _respondent(conn: Conn, user_uuid: str | None, *, office: str) -> int | None:
    """An active member of staff of the category's office: the tickets they
    will answer are that office's, and a session in another office reads none
    of them."""
    if not user_uuid:
        return None
    user = await users_repo.by_uuid(conn, user_uuid)
    if not user:
        raise NotFound("User")
    if user["role"] in _NOT_A_RESPONDENT or user["status"] != "active":
        raise ValidationFailed(
            "The respondent must be an active member of staff", field="respondent_user_uuid"
        )
    if user.get("office_code") != office:
        raise ValidationFailed(
            "The respondent must work in the category's office", field="respondent_user_uuid"
        )
    return int(user["id"])


async def set_processors(
    conn: Conn,
    category_uuid: str,
    *,
    processors: list[dict[str, Any]],
    role: Role | str,
    actor_id: int,
) -> list[dict[str, Any]]:
    """Make the category's processors exactly these.

    Each names a processor, what it is to the category and, optionally, who
    answers for it; with none, the activity's HR PoC does. One dropped from
    the list is marked removed, not deleted: who held the category's data
    last year is still part of the answer to "who has my data".
    """
    category = await find(conn, category_uuid, role=role, user_id=actor_id)
    if category["status"] != "active":
        raise Conflict("A retired category's processors are fixed", code="category_retired")
    await repo.lock(conn, category["category_id"])

    wanted: dict[int, dict[str, Any]] = {}
    for item in processors:
        processor = await registry_repo.processor_by_uuid(conn, str(item["processor_uuid"]))
        if not processor:
            raise NotFound("Processor")
        if processor["status"] != "active":
            raise ValidationFailed(
                f"{processor['legal_name']} is not active", field="processor_uuid"
            )
        if item["processor_role"] not in PROCESSOR_ROLES:
            raise ValidationFailed("Unknown processor role", field="processor_role")
        if processor["processor_id"] in wanted:
            raise ValidationFailed(
                f"{processor['legal_name']} is named twice", field="processor_uuid"
            )
        wanted[processor["processor_id"]] = {
            "processor_uuid": str(processor["processor_uuid"]),
            "processor_role": item["processor_role"],
            "respondent_user_id": await _respondent(
                conn, item.get("respondent_user_uuid"), office=str(category["office_code"])
            ),
        }

    before = await repo.processors_of(conn, category["category_id"])
    held = {row["processor_id"]: row for row in before}
    for processor_id, row in held.items():
        if processor_id not in wanted:
            await repo.remove_processor(conn, row["category_processor_id"], removed_by=actor_id)
    for processor_id, want in wanted.items():
        current = held.get(processor_id)
        if current is None:
            await repo.add_processor(
                conn,
                category_id=category["category_id"],
                processor_id=processor_id,
                processor_role=want["processor_role"],
                respondent_user_id=want["respondent_user_id"],
                added_by=actor_id,
            )
        elif (current["processor_role"], current["respondent_user_id"]) != (
            want["processor_role"],
            want["respondent_user_id"],
        ):
            await repo.change_processor(
                conn,
                current["category_processor_id"],
                processor_role=want["processor_role"],
                respondent_user_id=want["respondent_user_id"],
            )

    await audit.record(
        conn,
        event=Event.HR_CATEGORY_PROCESSORS_SET,
        entity_type="hr_category",
        entity_id=category["category_id"],
        detail={
            "from": [
                {"processor": str(r["processor_uuid"]), "role": r["processor_role"]} for r in before
            ],
            "to": [
                {"processor": w["processor_uuid"], "role": w["processor_role"]}
                for w in wanted.values()
            ],
        },
    )
    return await repo.processors_of(conn, category["category_id"])


async def set_user_categories(
    conn: Conn, user_uuid: str, *, category_uuids: list[str], actor_id: int, actor_role: str
) -> list[dict[str, Any]]:
    """Make an HR PoC's categories exactly these.

    Only an HR PoC runs activities in a category; another role is refused
    rather than given assignments it would never use. A retired category is
    refused as a new assignment and kept as an existing one.
    """
    user = await users_repo.require_by_uuid(conn, user_uuid)
    if user["role"] != Role.HR_USER.value:
        raise ValidationFailed("Only an HR PoC is assigned to categories", field="category_uuids")
    before = await repo.categories_of_user(conn, user["id"])
    already = {str(c["category_uuid"]) for c in before}
    wanted: list[dict[str, Any]] = []
    for category_uuid in dict.fromkeys(category_uuids):
        category = await repo.by_uuid(conn, category_uuid, role=actor_role, user_id=actor_id)
        if not category:
            raise NotFound("Category")
        if category["status"] != "active" and category_uuid not in already:
            raise ValidationFailed(
                f"{category['category_code']} is retired", field="category_uuids"
            )
        wanted.append(category)
    await repo.set_user_categories(
        conn, user["id"], [c["category_id"] for c in wanted], assigned_by=actor_id
    )
    await audit.record(
        conn,
        event=Event.USER_CATEGORIES_SET,
        entity_type="auth_user",
        entity_id=user["id"],
        subject_user_id=user["id"],
        detail={
            "from": [str(c["category_code"]) for c in before],
            "to": [str(c["category_code"]) for c in wanted],
            # An account belongs to no office's trail; the categories do.
            "office": user.get("office_code"),
        },
    )
    return await repo.categories_of_user(conn, user["id"])
