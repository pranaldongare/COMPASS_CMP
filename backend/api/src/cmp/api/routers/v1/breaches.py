"""Personal data breaches: the register and its duties (S3-01).

The DPO's alone, and hidden: any other role is answered 404 on every route
here, not 403 (`BreachReader`, `BreachWriter`). The platform records, derives
and tracks; people contain, determine and submit. Nothing here talks to the
Board or to CERT-In - a submission is recorded after a person has made it,
with the reference the regulator returned.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, status
from pydantic import AwareDatetime, Field

from cmp.api.dependencies import BreachReader, BreachWriter
from cmp.db.pool import connection, transaction
from cmp.domain.breach import service
from cmp.schemas.common import Out, Schema

router = APIRouter(prefix="/breaches", tags=["breaches"])

_Text = Annotated[str, Field(max_length=8000)]


# -------------------------------------------------------------------- inputs


class BreachIn(Schema):
    title: Annotated[str, Field(min_length=1, max_length=300)]
    #: When it was first noticed. Entered, never defaulted: it anchors CERT-In.
    detected_at: AwareDatetime
    #: When it started, if known.
    began_at: AwareDatetime | None = None
    #: platform, processor, data_source or other.
    location_kind: str
    processor_uuid: UUID | None = None
    source_uuid: UUID | None = None
    location_detail: _Text | None = None


class BreachDeterminationIn(Schema):
    #: pending, yes or no.
    outcome: str
    reasoning: Annotated[str, Field(min_length=1, max_length=8000)]
    #: With *yes* only: when the organisation became aware a personal data
    #: breach had occurred. Anchors every DPDP duty.
    became_aware_at: AwareDatetime | None = None


class BreachCategoryIn(Schema):
    category: Annotated[str, Field(min_length=1, max_length=200)]
    #: Whether the exposed values were sealed.
    sealed: bool
    #: Whether the key that seals them was exposed too.
    key_exposed: bool = False


class BreachAssessmentIn(Schema):
    began_at: AwareDatetime | None = None
    #: 7(1)(a), 7(2)(a): what happened, and how far it reached.
    nature_extent: _Text | None = None
    #: 7(2)(a): the likely impact.
    likely_impact: _Text | None = None
    #: 7(1)(b): the consequences likely for the people affected.
    consequences: _Text | None = None
    categories: Annotated[list[BreachCategoryIn], Field(max_length=100)] = Field(
        default_factory=list
    )
    #: 7(2)(b)(ii): the events, circumstances and reasons.
    circumstances: _Text | None = None
    #: 7(1)(c), 7(2)(b)(iii): implemented, being implemented, or proposed.
    mitigation: _Text | None = None
    #: 7(1)(d): what people can do to protect themselves.
    protective_steps: _Text | None = None
    #: 7(2)(b)(iv): findings on the person who caused it. Sealed.
    caused_by_findings: _Text | None = None
    #: 7(2)(b)(v): remedial measures against recurrence.
    remedial_measures: _Text | None = None
    #: 7(1)(e): who answers principals' questions.
    contact_point: _Text | None = None


class BreachCompletionIn(Schema):
    #: When the submission was made, as entered.
    occurred_at: AwareDatetime
    #: What the regulator returned.
    reference: Annotated[str, Field(min_length=1, max_length=200)]
    note: _Text | None = None


class BreachExtensionIn(Schema):
    requested_at: AwareDatetime
    #: The date the Board allowed. Becomes the detailed report's due time.
    allowed_until: AwareDatetime
    reference: Annotated[str, Field(max_length=200)] | None = None
    note: _Text | None = None


class BreachTransitionIn(Schema):
    to: str
    reason: _Text | None = None


# ------------------------------------------------------------------- outputs


class BreachLocationOut(Out):
    kind: str
    processor_uuid: UUID | None
    processor_name: str | None
    source_uuid: UUID | None
    source_name: str | None
    detail: str | None


class BreachClockOut(Out):
    #: No statutory hours: shown as time elapsed, against the internal target.
    without_delay: bool
    seconds_remaining: int | None
    overdue: bool
    seconds_elapsed: int | None
    #: When the internal target falls, if one is configured.
    target_at: datetime | None
    past_target: bool


class BreachDutyEventOut(Out):
    event_uuid: UUID
    kind: str
    occurred_at: datetime | None
    reference: str | None
    note: str | None
    due_at: datetime | None
    requested_at: datetime | None
    determination_uuid: UUID | None
    recorded_at: datetime
    recorded_by_name: str | None


class BreachDutyOut(Out):
    obligation_uuid: UUID
    duty: str
    label: str
    basis: str
    created_at: datetime
    #: outstanding, done or not_applicable.
    state: str
    due_at: datetime | None
    anchored_at: datetime | None
    completed_at: datetime | None
    reference: str | None
    extended_until: datetime | None
    extension_requested_at: datetime | None
    clock: BreachClockOut
    events: list[BreachDutyEventOut]


class BreachDeterminationOut(Out):
    determination_uuid: UUID
    outcome: str
    reasoning: str
    became_aware_at: datetime | None
    determined_at: datetime
    determined_by_name: str | None


class BreachCategoryOut(Out):
    category: str
    sealed: bool
    key_exposed: bool


class BreachAssessmentOut(Out):
    assessment_uuid: UUID
    revision: int
    began_at: datetime | None
    nature_extent: str | None
    likely_impact: str | None
    consequences: str | None
    categories: list[BreachCategoryOut]
    circumstances: str | None
    mitigation: str | None
    protective_steps: str | None
    caused_by_findings: str | None
    remedial_measures: str | None
    contact_point: str | None
    revised_at: datetime
    revised_by_name: str | None


class BreachStatusChangeOut(Out):
    from_status: str | None
    to_status: str
    reason: str | None
    changed_at: datetime
    changed_by_name: str | None


class BreachTransitionOut(Out):
    to: str
    allowed: bool
    blocked_by: str | None
    blockers: list[str]
    reason_required: bool


class BreachTransitionsOut(Out):
    current: str
    available: list[BreachTransitionOut]


class BreachSummaryOut(Out):
    breach_uuid: UUID
    reference: str
    title: str
    status: str
    detected_at: datetime
    location: BreachLocationOut
    determination: str
    obligations: list[BreachDutyOut]


class BreachOut(Out):
    breach_uuid: UUID
    reference: str
    title: str
    status: str
    detected_at: datetime
    became_aware_at: datetime | None
    began_at: datetime | None
    began_at_recorded: datetime | None
    location: BreachLocationOut
    recorded_at: datetime
    recorded_by_name: str | None
    #: pending, yes or no: the latest determination.
    determination: str
    determinations: list[BreachDeterminationOut]
    assessment: BreachAssessmentOut | None
    assessment_revisions: int
    obligations: list[BreachDutyOut]
    status_history: list[BreachStatusChangeOut]
    transitions: list[BreachTransitionOut]
    #: The internal target for "without delay", in hours. None while unset.
    without_delay_target_hours: float | None


# -------------------------------------------------------------------- routes


@router.get("", response_model=list[BreachSummaryOut], summary="The register, open first")
async def list_breaches(
    principal: BreachReader,
    status_: Annotated[str | None, Query(alias="status", description="open or closed")] = None,
) -> list[dict[str, Any]]:
    async with connection() as conn:
        return await service.register(conn, status=status_)


@router.post(
    "",
    response_model=BreachOut,
    status_code=status.HTTP_201_CREATED,
    summary="Record a breach as it was noticed",
)
async def record_breach(body: BreachIn, principal: BreachWriter) -> dict[str, Any]:
    async with transaction() as conn:
        return await service.record(
            conn,
            title=body.title,
            detected_at=body.detected_at,
            began_at=body.began_at,
            location_kind=body.location_kind,
            processor_uuid=str(body.processor_uuid) if body.processor_uuid else None,
            source_uuid=str(body.source_uuid) if body.source_uuid else None,
            location_detail=body.location_detail,
            actor_id=principal.user_id,
        )


@router.get("/{breach_uuid}", response_model=BreachOut, summary="One breach, with every duty")
async def get_breach(breach_uuid: UUID, principal: BreachReader) -> dict[str, Any]:
    async with connection() as conn:
        return await service.detail(conn, str(breach_uuid))


@router.post(
    "/{breach_uuid}/determinations",
    response_model=BreachOut,
    summary="Record whether it is a personal data breach",
)
async def determine(
    breach_uuid: UUID, body: BreachDeterminationIn, principal: BreachWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        return await service.determine(
            conn,
            breach_uuid=str(breach_uuid),
            outcome=body.outcome,
            reasoning=body.reasoning,
            became_aware_at=body.became_aware_at,
            actor_id=principal.user_id,
        )


@router.get(
    "/{breach_uuid}/assessments",
    response_model=list[BreachAssessmentOut],
    summary="Every revision of the assessment, newest first",
)
async def list_assessments(breach_uuid: UUID, principal: BreachReader) -> list[dict[str, Any]]:
    async with connection() as conn:
        return await service.assessments(conn, breach_uuid=str(breach_uuid))


@router.post(
    "/{breach_uuid}/assessments",
    response_model=BreachOut,
    summary="Revise what is known; the previous revision stays",
)
async def assess(
    breach_uuid: UUID, body: BreachAssessmentIn, principal: BreachWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        return await service.assess(
            conn,
            breach_uuid=str(breach_uuid),
            began_at=body.began_at,
            categories=[c.model_dump() for c in body.categories],
            text=body.model_dump(exclude={"began_at", "categories"}),
            actor_id=principal.user_id,
        )


@router.post(
    "/{breach_uuid}/cert-in",
    response_model=BreachOut,
    summary="Mark as a reportable cyber incident: CERT-In in six hours from detection",
)
async def mark_cert_in(breach_uuid: UUID, principal: BreachWriter) -> dict[str, Any]:
    async with transaction() as conn:
        return await service.mark_cert_in(
            conn, breach_uuid=str(breach_uuid), actor_id=principal.user_id
        )


@router.post(
    "/{breach_uuid}/obligations/{duty}/complete",
    response_model=BreachOut,
    summary="Record a submission made, with the regulator's reference",
)
async def complete_duty(
    breach_uuid: UUID, duty: str, body: BreachCompletionIn, principal: BreachWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        return await service.complete_duty(
            conn,
            breach_uuid=str(breach_uuid),
            duty=duty,
            occurred_at=body.occurred_at,
            reference=body.reference,
            note=body.note,
            actor_id=principal.user_id,
        )


@router.post(
    "/{breach_uuid}/obligations/board_report/extension",
    response_model=BreachOut,
    summary="Record the longer period the Board allowed for the detailed report",
)
async def extend_report(
    breach_uuid: UUID, body: BreachExtensionIn, principal: BreachWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        return await service.extend_report(
            conn,
            breach_uuid=str(breach_uuid),
            requested_at=body.requested_at,
            allowed_until=body.allowed_until,
            reference=body.reference,
            note=body.note,
            actor_id=principal.user_id,
        )


@router.get(
    "/{breach_uuid}/transitions",
    response_model=BreachTransitionsOut,
    summary="Whether it may close, and what stands in the way",
)
async def transitions(breach_uuid: UUID, principal: BreachReader) -> dict[str, Any]:
    async with connection() as conn:
        return await service.transitions_for(conn, breach_uuid=str(breach_uuid))


@router.post(
    "/{breach_uuid}/transition", response_model=BreachOut, summary="Close or reopen a breach"
)
async def transition(
    breach_uuid: UUID, body: BreachTransitionIn, principal: BreachWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        return await service.transition(
            conn,
            breach_uuid=str(breach_uuid),
            to=body.to,
            reason=body.reason,
            actor_id=principal.user_id,
        )
