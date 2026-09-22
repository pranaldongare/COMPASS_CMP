"""Audit - 7 endpoints, all reads.

No mutating verb exists on this resource for any role. Not hidden - absent. The
route is not registered here, the grant is revoked from the application role
(migration 0003), and a database trigger refuses the statement (migration 0002).

The Privacy Office is audited by this table. A DPO who can edit her own audit
trail makes it worthless as evidence.

What the trail can be asked, since September 2026: who did it (actor, by
person or by role), whom it concerns (subject), what it was about (an entity,
named by its public uuid), what kind of thing happened (an event type or the
group it belongs to), when, and a free-text term over the recorded detail. The
same filters drive the list, the summary and the CSV export, so the three
always describe one question. `lookup` is the picker behind "about": a few
letters of a name, and the record to filter on.
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from cmp.api.dependencies import Paging, RequireDPOorAdmin, reject_unknown_filters
from cmp.core.csv_safety import text_cell
from cmp.core.errors import NotFound, ValidationFailed
from cmp.core.pagination import PageRequest
from cmp.core.permissions import Role
from cmp.db.pool import connection, transaction
from cmp.db.repositories import audit as repo
from cmp.db.repositories import audit_lookup
from cmp.db.repositories import entities as entity_repo
from cmp.domain.audit import service as audit_service
from cmp.domain.audit import vocabulary as vocab
from cmp.domain.audit.service import Event
from cmp.schemas.common import Out, Page
from cmp.validation import choice

router = APIRouter(prefix="/audit", tags=["audit"])

audit_paging = Paging(repo.LIST_SORTS, "-occurred_at")

FILTER_PARAMS = {
    "actor",
    "actor_role",
    "subject",
    "entity_type",
    "entity_id",
    "entity",
    "event_type",
    "event_group",
    "from",
    "to",
    "q",
}


class AuditEntry(Out):
    log_uuid: UUID
    event_type: str
    entity_type: str
    entity_id: int
    occurred_at: datetime
    detail: dict[str, Any] | None = None
    actor_uuid: UUID | None = None
    actor_name: str | None = None
    actor_role: str | None = None
    subject_uuid: UUID | None = None
    subject_name: str | None = None

    # The trail records `notice#42` because that reference stays valid forever.
    # These four turn it into something a person can read and click, resolved at
    # read time so a rename shows the current name rather than a stale copy.
    # They are null where the row has since been deleted - the trail outlives
    # what it describes, and that is the point of it.
    entity_uuid: str | None = None
    entity_label: str | None = None
    #: Where the label names a person: the pieces, the name among them sealed,
    #: for the reader to open and join. `entity_label` is then the plain part.
    entity_label_parts: list[str] | None = None
    entity_noun: str | None = None
    entity_href: str | None = None


class VerifyResult(Out):
    intact: bool
    rows_checked: int
    last_log_id: int | None
    first_break: dict[str, Any] | None
    message: str


class Count(Out):
    key: str
    count: int


class DayCount(Out):
    day: str
    count: int


class AuditSummary(Out):
    total: int
    first_at: datetime | None
    last_at: datetime | None
    by_event: list[Count]
    by_group: list[Count]
    by_actor_role: list[Count]
    by_day: list[DayCount]
    days: int


class LookupHit(Out):
    kind: str
    entity_type: str
    #: Which filter this answer feeds: `subject`, `actor` or `entity`.
    filter: str
    uuid: str
    label: str
    hint: str | None


class VocabularyEntityType(Out):
    value: str
    label: str
    filterable_by_uuid: bool


class VocabularyGroup(Out):
    value: str
    label: str


class VocabularyEventType(Out):
    value: str
    group: str
    group_label: str
    label: str


class VocabularyLookup(Out):
    kind: str
    label: str
    filter: str


class Vocabulary(Out):
    entity_types: list[VocabularyEntityType]
    event_groups: list[VocabularyGroup]
    event_types: list[VocabularyEventType]
    lookups: list[VocabularyLookup]


# ------------------------------------------------------------------ filters
Actor = Annotated[UUID | None, Query()]
ActorRole = Annotated[str | None, Query(max_length=20)]
Subject = Annotated[UUID | None, Query()]
EntityType = Annotated[str | None, Query(max_length=60)]
EntityId = Annotated[int | None, Query(ge=1)]
Entity = Annotated[UUID | None, Query(description="The entity's public uuid; needs entity_type")]
EventType = Annotated[str | None, Query(max_length=80)]
EventGroup = Annotated[str | None, Query(max_length=40, pattern=r"^[a-z_]+$")]
DateFrom = Annotated[datetime | None, Query(alias="from")]
DateTo = Annotated[datetime | None, Query(alias="to")]
Term = Annotated[str | None, Query(max_length=120)]


async def _filters(
    conn: Any,
    *,
    actor: UUID | None,
    actor_role: str | None,
    subject: UUID | None,
    entity_type: str | None,
    entity_id: int | None,
    entity: UUID | None,
    event_type: str | None,
    event_group: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    q: str | None,
) -> repo.AuditFilters:
    """Turn the query string into the repository's filters, resolving the
    public uuid of an entity to the id the trail stores."""
    if entity_type and entity_type not in audit_service.ENTITY_TYPES:
        raise ValidationFailed(
            "Unknown entity type",
            field="entity_type",
            details={"allowed": sorted(audit_service.ENTITY_TYPES)},
        )
    if entity is not None:
        if not entity_type:
            raise ValidationFailed("entity needs entity_type", field="entity")
        resolved = await audit_lookup.id_for_uuid(conn, entity_type, str(entity))
        if resolved is None:
            # An unknown uuid matches nothing, rather than everything: the
            # list must not silently widen because a filter did not resolve.
            resolved = -1
        entity_id = resolved
    if date_from and date_to and date_from > date_to:
        raise ValidationFailed("from must not be after to", field="from")
    return repo.AuditFilters(
        actor_uuid=str(actor) if actor else None,
        actor_role=choice(Role, actor_role, field="actor_role").value if actor_role else None,
        subject_uuid=str(subject) if subject else None,
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        event_group=event_group,
        date_from=date_from,
        date_to=date_to,
        q=q,
    )


@router.get("", response_model=Page[AuditEntry], summary="Search the trail")
async def search(
    request: Request,
    principal: RequireDPOorAdmin,
    page: Annotated[PageRequest, Depends(audit_paging)],
    actor: Actor = None,
    actor_role: ActorRole = None,
    subject: Subject = None,
    entity_type: EntityType = None,
    entity_id: EntityId = None,
    entity: Entity = None,
    event_type: EventType = None,
    event_group: EventGroup = None,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    q: Term = None,
) -> dict[str, Any]:
    reject_unknown_filters(request, FILTER_PARAMS)
    async with connection() as conn:
        filters = await _filters(
            conn,
            actor=actor,
            actor_role=actor_role,
            subject=subject,
            entity_type=entity_type,
            entity_id=entity_id,
            entity=entity,
            event_type=event_type,
            event_group=event_group,
            date_from=date_from,
            date_to=date_to,
            q=q,
        )
        items, cursor, total = await repo.search(conn, page, filters)
        # One query per entity type on the page, not one per row.
        items = await entity_repo.attach(conn, items)
    return {"items": items, "next_cursor": cursor, "total": total}


@router.get(
    "/summary", response_model=AuditSummary, summary="The shape of the rows a filter selects"
)
async def summary(
    request: Request,
    principal: RequireDPOorAdmin,
    actor: Actor = None,
    actor_role: ActorRole = None,
    subject: Subject = None,
    entity_type: EntityType = None,
    entity_id: EntityId = None,
    entity: Entity = None,
    event_type: EventType = None,
    event_group: EventGroup = None,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    q: Term = None,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> dict[str, Any]:
    """Counts by event, by group, by the actor's role and by day, over exactly
    the rows the same filters would list."""
    reject_unknown_filters(request, FILTER_PARAMS | {"days"})
    async with connection() as conn:
        filters = await _filters(
            conn,
            actor=actor,
            actor_role=actor_role,
            subject=subject,
            entity_type=entity_type,
            entity_id=entity_id,
            entity=entity,
            event_type=event_type,
            event_group=event_group,
            date_from=date_from,
            date_to=date_to,
            q=q,
        )
        result = await repo.summary(conn, filters, days=days)
    result["by_day"] = [
        {"day": r["day"].isoformat(), "count": r["count"]} for r in result["by_day"]
    ]
    return result


@router.get("/vocabulary", response_model=Vocabulary, summary="What the trail can be filtered by")
async def vocabulary(principal: RequireDPOorAdmin) -> dict[str, Any]:
    """Every entity type and event type the trail may carry, with labels, and
    the pickers the console offers. Served rather than hard-coded on the
    client, so a new event appears in the filters the day it lands."""
    return vocab.vocabulary()


@router.get("/lookup", response_model=list[LookupHit], summary="Find a record to filter on")
async def lookup(
    principal: RequireDPOorAdmin,
    kind: Annotated[str, Query(max_length=30)],
    q: Annotated[str, Query(min_length=1, max_length=100)],
) -> list[dict[str, Any]]:
    """A few letters of a name, and up to ten records of that kind. Each answer
    says which filter it feeds: a person is a subject or an actor, everything
    else is the entity an event was recorded against."""
    if kind not in audit_lookup.LOOKUP_KINDS:
        raise ValidationFailed(
            "Unknown lookup kind",
            field="kind",
            details={"allowed": sorted(audit_lookup.LOOKUP_KINDS)},
        )
    async with connection() as conn:
        return await audit_lookup.lookup(conn, kind, q)


EXPORT_COLUMNS = (
    "occurred_at",
    "event_type",
    "actor_name",
    "actor_role",
    "subject_name",
    "entity_type",
    "entity_id",
    "entity_label",
    "detail",
    "log_uuid",
)


@router.get("/export.csv", summary="Download the rows a filter selects, as CSV")
async def export_csv(
    request: Request,
    principal: RequireDPOorAdmin,
    actor: Actor = None,
    actor_role: ActorRole = None,
    subject: Subject = None,
    entity_type: EntityType = None,
    entity_id: EntityId = None,
    entity: Entity = None,
    event_type: EventType = None,
    event_group: EventGroup = None,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    q: Term = None,
) -> Response:
    """Newest first, at most `EXPORT_LIMIT` rows, free-text cells neutralised
    against spreadsheet formulas. The download is itself recorded in the
    trail, with the filters used: reading the evidence is an act on it."""
    reject_unknown_filters(request, FILTER_PARAMS)
    async with transaction() as conn:
        filters = await _filters(
            conn,
            actor=actor,
            actor_role=actor_role,
            subject=subject,
            entity_type=entity_type,
            entity_id=entity_id,
            entity=entity,
            event_type=event_type,
            event_group=event_group,
            date_from=date_from,
            date_to=date_to,
            q=q,
        )
        rows = await repo.export_rows(conn, filters)
        rows = await entity_repo.attach(conn, rows)
        await audit_service.record(
            conn,
            event=Event.AUDIT_EXPORTED,
            entity_type="audit_log",
            entity_id=0,
            actor_user_id=principal.user_id,
            detail={
                "rows": len(rows),
                "filters": {k: v for k, v in request.query_params.items() if v},
            },
        )

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(EXPORT_COLUMNS)
    for r in rows:
        writer.writerow(
            [
                r["occurred_at"].isoformat(),
                r["event_type"],
                text_cell(r.get("actor_name")),
                r.get("actor_role") or "",
                text_cell(r.get("subject_name")),
                r["entity_type"],
                r["entity_id"],
                text_cell(r.get("entity_label")),
                text_cell(audit_service.canonical_detail(r.get("detail") or {})),
                str(r["log_uuid"]),
            ]
        )
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M")
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="audit-trail-{stamp}.csv"',
            "X-Row-Count": str(len(rows)),
            "X-Row-Limit": str(repo.EXPORT_LIMIT),
        },
    )


@router.get("/verify", response_model=VerifyResult, summary="Verify the hash chain")
async def verify(
    principal: RequireDPOorAdmin,
    from_log_id: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """Recompute the chain and report the first row that does not verify.

    Every row carries a digest over its own content and its predecessor's digest.
    Editing row N changes its digest, which no longer matches what N+1 recorded,
    so the answer is not "something changed" but "the trail is sound up to
    exactly here".
    """
    async with connection() as conn:
        result = await audit_service.verify_chain(conn, from_log_id=from_log_id)

    if result["intact"]:
        message = f"Chain intact across {result['rows_checked']} rows."
    else:
        brk = result["first_break"]
        message = (
            f"Chain broken at log {brk['log_id']} ({brk['occurred_at']}): {brk['reason']}. "
            "Rows before this point still verify."
        )
    return {**result, "message": message}


@router.get("/{log_uuid}", response_model=AuditEntry)
async def get_entry(log_uuid: UUID, principal: RequireDPOorAdmin) -> dict[str, Any]:
    async with connection() as conn:
        entry = await repo.by_uuid(conn, str(log_uuid))
        if not entry:
            raise NotFound("Audit entry")
        (enriched,) = await entity_repo.attach(conn, [entry])
        return enriched
