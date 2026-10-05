"""The registry's writes: purposes, processors and their respondents, data sources.

Moved out of `api/routers/v1/registry.py` (review 2026-10-01, ARCH-5), where
each route wrote through the repository and recorded its own audit row. The
rule in `docs/architecture/layers.md` is that services are the only writers
and the only callers of `audit.record()`, so that HTTP, a task and a future
integration all reach the same behaviour. The rules below are unchanged; only
where they live has moved.

Registry rows are suspended, never deleted. A deleted processor orphans every
collection that named it, and "who processed this?" stops having an answer.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from cmp.core.errors import Conflict, NotFound, PurposeInUse, ValidationFailed
from cmp.core.permissions import Role
from cmp.db.repositories import registry as repo
from cmp.db.repositories import users as users_repo
from cmp.db.sql import Conn, unique_violation
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.infrastructure.dkms import opened


# =============================================================== purposes
async def create_purpose(conn: Conn, *, fields: dict[str, Any], actor_id: int) -> dict[str, Any]:
    try:
        purpose = await repo.create_purpose(conn, created_by=actor_id, **fields)
    except Exception as exc:
        if unique_violation(exc):
            raise Conflict("That purpose code already exists", code="purpose_code_taken") from exc
        raise
    await audit.record(
        conn,
        event=Event.PURPOSE_CREATED,
        entity_type="purpose",
        entity_id=purpose["purpose_id"],
        detail={"purpose_code": fields["purpose_code"], "lawful_basis": fields["lawful_basis"]},
    )
    return purpose


async def _purpose(conn: Conn, purpose_uuid: str) -> dict[str, Any]:
    purpose = await repo.purpose_by_uuid(conn, purpose_uuid)
    if not purpose:
        raise NotFound("Purpose")
    return purpose


async def update_purpose(
    conn: Conn, purpose_uuid: str, *, fields: dict[str, Any]
) -> dict[str, Any]:
    purpose = await _purpose(conn, purpose_uuid)
    if purpose["status"] != "draft":
        raise Conflict(
            "Only a draft purpose may be edited. Create a new version instead.",
            code="purpose_not_draft",
            details={"status": purpose["status"]},
        )
    updated = await repo.update_purpose(conn, purpose["purpose_id"], **fields)
    await audit.record(
        conn, event=Event.PURPOSE_UPDATED, entity_type="purpose", entity_id=purpose["purpose_id"]
    )
    return updated


async def activate_purpose(conn: Conn, purpose_uuid: str) -> None:
    purpose = await _purpose(conn, purpose_uuid)
    if purpose["status"] == "active":
        raise Conflict("That purpose is already active", code="purpose_active")
    await repo.set_purpose_status(conn, purpose["purpose_id"], "active")
    await audit.record(
        conn, event=Event.PURPOSE_ACTIVATED, entity_type="purpose", entity_id=purpose["purpose_id"]
    )


async def retire_purpose(conn: Conn, purpose_uuid: str) -> None:
    """Blocked while the purpose is attached to a published notice.

    Retiring it would leave a live notice offering a purpose the registry says
    no longer exists, and the consents already given against it unexplainable.
    """
    purpose = await _purpose(conn, purpose_uuid)
    if await repo.purpose_is_published_anywhere(conn, purpose["purpose_id"]):
        usage = await repo.purpose_usage(conn, purpose["purpose_id"])
        raise PurposeInUse(
            "This purpose is attached to a published notice and cannot be retired",
            details={
                "notices": [
                    {
                        "notice_code": u["notice_code"],
                        "version": u["version"],
                        "project": u["project_name"],
                        "status": u["status"],
                    }
                    for u in usage
                    if u["status"] in ("published", "superseded")
                ]
            },
        )
    await repo.set_purpose_status(conn, purpose["purpose_id"], "retired")
    await audit.record(
        conn, event=Event.PURPOSE_RETIRED, entity_type="purpose", entity_id=purpose["purpose_id"]
    )


# ============================================================== processors
async def _processor(conn: Conn, processor_uuid: str) -> dict[str, Any]:
    processor = await repo.processor_by_uuid(conn, processor_uuid)
    if not processor:
        raise NotFound("Processor")
    return processor


async def create_processor(
    conn: Conn,
    *,
    legal_name: str,
    type_: str,
    contract_ref: str,
    security_confirmed_at: date,
    is_in_house: bool,
    location_country: str | None,
) -> dict[str, Any]:
    processor = await repo.create_processor(
        conn,
        legal_name=legal_name,
        type_=type_,
        contract_ref=contract_ref,
        security_confirmed_at=security_confirmed_at,
        is_in_house=is_in_house,
        location_country=location_country,
    )
    await audit.record(
        conn,
        event=Event.PROCESSOR_CREATED,
        entity_type="processor",
        entity_id=processor["processor_id"],
        detail={
            "legal_name": legal_name,
            "contract_ref": contract_ref,
            "is_in_house": is_in_house,
            "location_country": location_country,
        },
    )
    return processor


async def update_processor(
    conn: Conn,
    processor_uuid: str,
    *,
    legal_name: str | None,
    contract_ref: str | None,
    security_confirmed_at: date | None,
    location_country: str | None,
) -> dict[str, Any]:
    processor = await _processor(conn, processor_uuid)
    updated = await repo.update_processor(
        conn,
        processor["processor_id"],
        legal_name=legal_name,
        contract_ref=contract_ref,
        security_confirmed_at=security_confirmed_at,
        location_country=location_country,
    )
    await audit.record(
        conn,
        event=Event.PROCESSOR_UPDATED,
        entity_type="processor",
        entity_id=processor["processor_id"],
    )
    return updated


async def suspend_processor(conn: Conn, processor_uuid: str) -> None:
    processor = await _processor(conn, processor_uuid)
    await repo.suspend_processor(conn, processor["processor_id"])
    await audit.record(
        conn,
        event=Event.PROCESSOR_SUSPENDED,
        entity_type="processor",
        entity_id=processor["processor_id"],
    )


async def add_respondent(
    conn: Conn,
    processor_uuid: str,
    *,
    name: str | None,
    contact: str | None,
    user_uuid: str | None,
) -> dict[str, Any]:
    """A respondent is how a holder's ticket gets answered.

    An account answers on the portal: the ticket is in front of them when they
    sign in, and they return it there. A name and an address are mailed, and
    the Privacy Office tracks the exchange by hand.

    An in-house processor's respondent must be an account - our own team has
    no reason to be reached by mail. A third party's may be either. Usually it
    is somebody at the third party, reached by mail; sometimes one of our own
    people represents that third party here, and naming their account puts the
    ticket on the portal like any internal one. The rule is held here rather
    than left to whoever fills the form.
    """
    processor = await _processor(conn, processor_uuid)
    user_id: int | None = None
    name = (name or "").strip()
    contact = (contact or "").strip()
    if user_uuid is not None:
        account = await users_repo.by_uuid(conn, user_uuid)
        if not account or account["role"] == "data_subject" or account["status"] != "active":
            raise ValidationFailed("Choose an active member of staff", field="user_uuid")
        user_id = int(account["id"])
        # Opened: the respondent row seals its own copy under its own type,
        # and a ciphertext copied across would be sealed under the wrong one.
        person = await opened("auth_user", account)
        name = str(person["full_name"])
        contact = str(person["email"])
    elif processor["is_in_house"]:
        raise ValidationFailed(
            "An in-house processor's respondent must be a CMP account, so they "
            "answer on the portal",
            field="user_uuid",
        )
    else:
        if not name:
            raise ValidationFailed("Name the respondent", field="name")
        if not contact:
            raise ValidationFailed("An address to send the instruction to", field="contact")
    created = await repo.add_respondent(
        conn, int(processor["processor_id"]), name=name, contact=contact, user_id=user_id
    )
    await audit.record(
        conn,
        event=Event.PROCESSOR_RESPONDENT_ADDED,
        entity_type="processor",
        entity_id=int(processor["processor_id"]),
        detail={"respondent": str(created["respondent_uuid"]), "portal": user_id is not None},
    )
    fresh = await repo.respondent_by_uuid(
        conn, int(processor["processor_id"]), str(created["respondent_uuid"])
    )
    assert fresh is not None
    return fresh


async def remove_respondent(conn: Conn, processor_uuid: str, respondent_uuid: str) -> None:
    processor = await _processor(conn, processor_uuid)
    rs = await repo.respondent_by_uuid(conn, int(processor["processor_id"]), respondent_uuid)
    if not rs:
        raise NotFound("Respondent")
    await repo.remove_respondent(conn, int(rs["respondent_id"]))
    await audit.record(
        conn,
        event=Event.PROCESSOR_RESPONDENT_REMOVED,
        entity_type="processor",
        entity_id=int(processor["processor_id"]),
        detail={"respondent": respondent_uuid},
    )


# ================================================================= sources
async def _source(conn: Conn, source_uuid: str) -> dict[str, Any]:
    source = await repo.source_by_uuid(conn, source_uuid)
    if not source:
        raise NotFound("Data source")
    return source


def refuse_foreign_processor(role: Any, processor: dict[str, Any]) -> None:
    """A collection owner registers under their own kind of processor, or not at all.

    A DCO is accountable for what a third party collects and an RCO for what
    the R&D team collects itself, so a DCO registering an in-house rig - or the
    reverse - would be creating a source they could never be given. Everyone
    else is registering on somebody's behalf and is unconstrained.
    """
    wanted_in_house = {Role.DCO: False, Role.RCO: True}.get(role)
    if wanted_in_house is None:
        return
    if bool(processor["is_in_house"]) is not wanted_in_house:
        raise ValidationFailed(
            (
                "An R&D Collection Owner registers sources under an in-house processor"
                if wanted_in_house
                else "A Data Collection Owner registers sources under a third-party processor"
            ),
            field="processor_uuid",
        )


async def create_source(
    conn: Conn,
    *,
    role: Any,
    user_id: int,
    source_code: str,
    name: str,
    source_role: str,
    exchange_mode: str,
    id_scheme: str | None,
    processor_uuid: str | None,
    site_uuid: str | None,
    is_authoritative_for: list[str],
) -> dict[str, Any]:
    """`is_authoritative_for` lists the data elements this source owns.

    Without it, a nightly identity sync will overwrite a value corrected under a
    rights request and nobody will notice.
    """
    processor_id = None
    if processor_uuid:
        processor = await _processor(conn, processor_uuid)
        if processor["status"] != "active":
            raise ValidationFailed(
                f"{processor['legal_name']} is {processor['status']} and cannot take "
                "new data sources",
                field="processor_uuid",
            )
        refuse_foreign_processor(role, processor)
        processor_id = processor["processor_id"]

    # A collection owner has to say which processor it belongs to. Without
    # one the source is unroutable - it can never appear under any project's
    # processors, so no site could ever deploy it.
    if processor_id is None and role in (Role.DCO, Role.RCO):
        raise ValidationFailed(
            "Choose the processor this data source belongs to",
            field="processor_uuid",
        )

    site_id = None
    if site_uuid:
        from cmp.db.repositories import projects as project_repo

        site = await project_repo.site_by_uuid(conn, site_uuid, role=role, user_id=user_id)
        if not site:
            raise NotFound("Site")
        site_id = site["site_id"]

    try:
        source = await repo.create_source(
            conn,
            source_code=source_code,
            name=name,
            source_role=source_role,
            exchange_mode=exchange_mode,
            id_scheme=id_scheme,
            processor_id=processor_id,
            site_id=site_id,
            is_authoritative_for=is_authoritative_for,
        )
    except Exception as exc:
        if unique_violation(exc):
            raise Conflict("That source code already exists", code="source_code_taken") from exc
        raise

    await audit.record(
        conn,
        event=Event.SOURCE_CREATED,
        entity_type="data_source",
        entity_id=source["source_id"],
        detail={"source_code": source_code, "authoritative_for": is_authoritative_for},
    )
    return source


async def update_source(
    conn: Conn,
    source_uuid: str,
    *,
    name: str | None,
    id_scheme: str | None,
    is_authoritative_for: list[str] | None,
) -> dict[str, Any]:
    source = await _source(conn, source_uuid)
    updated = await repo.update_source(
        conn,
        source["source_id"],
        name=name,
        id_scheme=id_scheme,
        is_authoritative_for=is_authoritative_for,
    )
    await audit.record(
        conn, event=Event.SOURCE_UPDATED, entity_type="data_source", entity_id=source["source_id"]
    )
    return updated


async def assign_source_owner(
    conn: Conn, source_uuid: str, *, owner_user_uuid: str | None
) -> dict[str, Any]:
    """Hand a source to a DCO or an RCO. Every project using it follows.

    Which role fits which source is checked, because the distinction carries
    meaning: an RCO is accountable for collection the R&D team does itself, a
    DCO for a third party's. `trg_source_owner` re-derives the routing of every
    project deploying this source, so this one write is the whole change;
    `projects_moved` says how many that was.
    """
    source = await _source(conn, source_uuid)

    owner_id = None
    if owner_user_uuid is not None:
        owner = await users_repo.by_uuid(conn, owner_user_uuid)
        if not owner:
            raise NotFound("User")
        if owner["status"] != "active":
            raise ValidationFailed("That account is not active", field="owner_user_uuid")

        in_house = bool(source.get("is_in_house"))
        wanted = Role.RCO if in_house else Role.DCO
        if owner["role"] != wanted.value:
            raise ValidationFailed(
                (
                    "Collection from this source is in-house, so an R&D Collection "
                    "Owner is accountable for it"
                    if in_house
                    else "Collection from this source is by a third party, so a Data "
                    "Collection Owner is accountable for it"
                ),
                field="owner_user_uuid",
            )
        owner_id = owner["id"]

    moved = await repo.projects_using_source(conn, source["source_id"])
    updated = await repo.set_source_owner(conn, source["source_id"], owner_id)

    await audit.record(
        conn,
        event=Event.SOURCE_OWNER_ASSIGNED,
        entity_type="data_source",
        entity_id=source["source_id"],
        subject_user_id=owner_id,
        detail={
            "source_code": source["source_code"],
            "owner": owner_user_uuid,
            "projects_moved": moved,
        },
    )
    return {**updated, "projects_moved": moved}


async def suspend_source(conn: Conn, source_uuid: str) -> None:
    source = await _source(conn, source_uuid)
    await repo.suspend_source(conn, source["source_id"])
    await audit.record(
        conn,
        event=Event.SOURCE_SUSPENDED,
        entity_type="data_source",
        entity_id=source["source_id"],
    )
