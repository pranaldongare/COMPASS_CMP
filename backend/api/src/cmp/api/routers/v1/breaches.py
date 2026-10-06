"""Incidents and personal data breaches: the register and its duties (S3-01, S3-06).

An incident is logged first (`POST /breaches`); validation records whether it
is a personal data breach, and the first *yes* records it as one (ADR 0022).
The DPO's alone, and hidden: any other role is answered 404 on every route
here, not 403 (`BreachReader`, `BreachWriter`). The platform records, derives
and tracks; people contain, determine and submit. Nothing here talks to the
Board or to CERT-In - a submission is recorded after a person has made it,
with the reference the regulator returned.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, Response, UploadFile, status
from pydantic import AwareDatetime, Field

from cmp.api import uploads
from cmp.api.dependencies import BreachReader, BreachWriter
from cmp.db.pool import connection, transaction
from cmp.domain.breach import affected, board, notices, service, tickets
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
    #: When the submission or report was made, as entered.
    occurred_at: AwareDatetime
    #: What the regulator returned. Required for every duty but the
    #: organisation's board, where there may be none.
    reference: Annotated[str, Field(max_length=200)] | None = None
    #: The organisation's board only, and required there: to whom it was
    #: reported. Sealed.
    reported_to: Annotated[str, Field(max_length=2000)] | None = None
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
    #: On a report to the organisation's board: to whom. Sealed.
    reported_to: str | None
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
    #: The organisation's board: to whom it was reported. Sealed.
    reported_to: str | None
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
    #: What it is quoted by: the breach reference once recorded, the incident's
    #: until then.
    reference: str
    #: INC-YYYY-NNNN, from logging onwards (a row logged before 0038 carries BR-).
    incident_reference: str
    #: BR-YYYY-NNNN, issued by the first determination of yes. None until then.
    breach_reference: str | None
    title: str
    status: str
    detected_at: datetime
    location: BreachLocationOut
    determination: str
    obligations: list[BreachDutyOut]
    #: When anything last happened to it - a write to it, its notices or its
    #: tickets - from the audit trail. For "recent activity" in the register.
    last_activity_at: datetime
    #: Its tickets still with a holder or the office (issued or returned), and
    #: those past their answer-by.
    tickets_open: int
    tickets_overdue: int


class BreachOut(Out):
    breach_uuid: UUID
    #: What it is quoted by: the breach reference once recorded, the incident's
    #: until then.
    reference: str
    #: INC-YYYY-NNNN, from logging onwards (a row logged before 0038 carries BR-).
    incident_reference: str
    #: BR-YYYY-NNNN, issued by the first determination of yes. None until then.
    breach_reference: str | None
    #: When the first yes recorded it as a breach, and who made it.
    breach_recorded_at: datetime | None
    breach_recorded_by_name: str | None
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


@router.get(
    "", response_model=list[BreachSummaryOut], summary="Every incident and breach, open first"
)
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
    summary="Log an incident as it was noticed",
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


@router.get(
    "/{breach_uuid}", response_model=BreachOut, summary="One incident or breach, with every duty"
)
async def get_breach(breach_uuid: UUID, principal: BreachReader) -> dict[str, Any]:
    async with connection() as conn:
        return await service.detail(conn, str(breach_uuid))


@router.post(
    "/{breach_uuid}/determinations",
    response_model=BreachOut,
    summary="Validate: is it a personal data breach? The first yes records it",
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
    summary=(
        "Record a submission made, with the regulator's reference - or, for the "
        "organisation's board, the report made and to whom"
    ),
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
            reported_to=body.reported_to,
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


# ------------------------------------------------------------ who it touched (S3-02)


class BreachScopeIn(Schema):
    #: processor, data_source or platform.
    kind: str
    processor_uuid: UUID | None = None
    source_uuid: UUID | None = None
    #: platform only: the affected tables, from `platform_tables`.
    tables: Annotated[list[str], Field(max_length=50)] = Field(default_factory=list)
    #: platform only: rows written from and until. Either may be open.
    since: AwareDatetime | None = None
    until: AwareDatetime | None = None


class BreachPreviewIn(Schema):
    scopes: Annotated[list[BreachScopeIn], Field(min_length=1, max_length=20)]


class BreachAffectedIn(Schema):
    scopes: Annotated[list[BreachScopeIn], Field(max_length=20)] = Field(default_factory=list)
    #: People the records place in scope who were not touched, by uuid.
    exclude: Annotated[list[UUID], Field(max_length=5000)] = Field(default_factory=list)
    #: People the records cannot show, by uuid.
    add: Annotated[list[UUID], Field(max_length=5000)] = Field(default_factory=list)
    note: _Text | None = None


class BreachEvidenceOut(Out):
    exports: list[str] = Field(default_factory=list)
    assets: list[str] = Field(default_factory=list)
    tables: list[str] = Field(default_factory=list)


class BreachPersonOut(Out):
    person_uuid: UUID
    full_name: str | None
    role: str
    has_email: bool
    has_mobile: bool
    #: processor, data_source, platform or dpo (added by hand).
    found_by: str
    evidence: BreachEvidenceOut


class BreachAffectedPersonOut(BreachPersonOut):
    affected_uuid: UUID
    #: The revision that first listed them.
    revision: int


class BreachCandidateOut(BreachPersonOut):
    already_listed: bool


class BreachPreviewOut(Out):
    scopes: list[dict[str, Any]]
    derived: int
    already_listed: int
    would_add: int
    #: The first people found, as a sample. `derived` is the count.
    people: list[BreachCandidateOut]


class BreachAffectedRevisionOut(Out):
    revision_uuid: UUID
    revision: int
    scopes: list[dict[str, Any]]
    derived: int
    added_by_hand: int
    excluded: int
    newly_listed: int
    note: str | None
    confirmed_at: datetime
    confirmed_by_name: str | None


class BreachAffectedOut(Out):
    total: int
    revisions: list[BreachAffectedRevisionOut]
    people: list[BreachAffectedPersonOut]
    next_cursor: str | None
    #: The tables a platform scope may name.
    platform_tables: list[str]


def _scopes(scopes: list[BreachScopeIn]) -> list[dict[str, Any]]:
    return [s.model_dump() for s in scopes]


@router.get(
    "/{breach_uuid}/affected",
    response_model=BreachAffectedOut,
    summary="Who the breach touched, as confirmed, with every revision",
)
async def list_affected(
    breach_uuid: UUID,
    principal: BreachReader,
    cursor: Annotated[str | None, Query(max_length=64)] = None,
) -> dict[str, Any]:
    async with connection() as conn:
        return await affected.listing(conn, breach_uuid=str(breach_uuid), after=cursor)


@router.post(
    "/{breach_uuid}/affected/preview",
    response_model=BreachPreviewOut,
    summary="What the records show for these scopes, before confirming",
)
async def preview_affected(
    breach_uuid: UUID, body: BreachPreviewIn, principal: BreachReader
) -> dict[str, Any]:
    async with connection() as conn:
        return await affected.preview(
            conn, breach_uuid=str(breach_uuid), scopes=_scopes(body.scopes)
        )


@router.post(
    "/{breach_uuid}/affected",
    response_model=BreachAffectedOut,
    summary="Confirm who the breach touched: a new revision, adding only the newly found",
)
async def confirm_affected(
    breach_uuid: UUID, body: BreachAffectedIn, principal: BreachWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        return await affected.confirm(
            conn,
            breach_uuid=str(breach_uuid),
            scopes=_scopes(body.scopes),
            exclude=[str(u) for u in body.exclude],
            add=[str(u) for u in body.add],
            note=body.note,
            actor_id=principal.user_id,
        )


# --------------------------------------------------- telling the people (S3-03)

_Words = Annotated[str, Field(max_length=4000)]


class BreachNoticeIn(Schema):
    """The five things Rule 7(1) requires. A draft may leave any empty;
    approval may not. Written to be sent to everyone listed: name nobody."""

    what_happened: _Words | None = None
    consequences: _Words | None = None
    measures: _Words | None = None
    protective_steps: _Words | None = None
    contact: _Words | None = None


class BreachNoticeOut(Out):
    notice_uuid: UUID
    version: int
    #: draft or approved. An approved notice does not change.
    state: str
    what_happened: str | None
    consequences: str | None
    measures: str | None
    protective_steps: str | None
    contact: str | None
    created_at: datetime
    created_by_name: str | None
    updated_at: datetime
    approved_at: datetime | None
    approved_by_name: str | None


class BreachDeliveryCountOut(Out):
    notice_uuid: UUID
    version: int
    #: portal, email or sms.
    channel: str
    #: queued, delivered or failed: each person's latest attempt.
    status: str
    people: int
    last_at: datetime


class BreachDeliveryFailureOut(Out):
    version: int
    channel: str
    attempt: int
    detail: dict[str, Any]
    recorded_at: datetime
    person_uuid: UUID
    full_name: str | None


class BreachNoticeContentOut(Out):
    key: str
    label: str


class BreachNoticesOut(Out):
    versions: list[BreachNoticeOut]
    #: Rule 7(2)(b)(vi): per version and channel, how many people are in each state.
    account: list[BreachDeliveryCountOut]
    failures: list[BreachDeliveryFailureOut]
    listed: int
    #: Listed people with no version yet whose every channel has an outcome.
    unnotified: int
    contents: list[BreachNoticeContentOut]
    duty: str
    #: Why nothing may be sent yet - the incident is not recorded as a breach -
    #: or None. Approval and who is listed are said by the fields above.
    send_blocked_by: str | None


@router.get(
    "/{breach_uuid}/notices",
    response_model=BreachNoticesOut,
    summary="Every version of the notice, and the account of who received which",
)
async def list_notices(breach_uuid: UUID, principal: BreachReader) -> dict[str, Any]:
    async with connection() as conn:
        return await notices.overview(conn, breach_uuid=str(breach_uuid))


@router.post(
    "/{breach_uuid}/notices",
    response_model=BreachNoticesOut,
    status_code=status.HTTP_201_CREATED,
    summary="Start the next version of the notice, as a draft",
)
async def draft_notice(
    breach_uuid: UUID, body: BreachNoticeIn, principal: BreachWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        return await notices.draft(
            conn, breach_uuid=str(breach_uuid), words=body.model_dump(), actor_id=principal.user_id
        )


@router.put(
    "/{breach_uuid}/notices/{notice_uuid}",
    response_model=BreachNoticesOut,
    summary="Edit a draft notice",
)
async def edit_notice(
    breach_uuid: UUID, notice_uuid: UUID, body: BreachNoticeIn, principal: BreachWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        return await notices.edit(
            conn,
            breach_uuid=str(breach_uuid),
            notice_uuid=str(notice_uuid),
            words=body.model_dump(),
            actor_id=principal.user_id,
        )


@router.post(
    "/{breach_uuid}/notices/{notice_uuid}/approve",
    response_model=BreachNoticesOut,
    summary="Approve the words; refused while any of the five is empty",
)
async def approve_notice(
    breach_uuid: UUID, notice_uuid: UUID, principal: BreachWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        return await notices.approve(
            conn,
            breach_uuid=str(breach_uuid),
            notice_uuid=str(notice_uuid),
            actor_id=principal.user_id,
        )


@router.post(
    "/{breach_uuid}/notices/send",
    response_model=BreachNoticesOut,
    summary=(
        "Send the approved notice to everyone listed who lacks it; never twice, "
        "never before the breach is recorded"
    ),
)
async def send_notice(breach_uuid: UUID, principal: BreachWriter) -> dict[str, Any]:
    async with transaction() as conn:
        return await notices.send(conn, breach_uuid=str(breach_uuid), actor_id=principal.user_id)


# ------------------------------------------------ the Board's documents (S3-04)


class BreachIntimationOut(Out):
    """Rule 7(2)(a), drafted from the register. The platform never submits it."""

    document: str
    basis: str
    reference: str
    incident_reference: str
    breach_reference: str | None
    title: str
    generated_at: datetime
    determination: str
    detected_at: datetime
    began_at: datetime | None
    became_aware_at: datetime | None
    location: BreachLocationOut
    nature_extent: str | None
    likely_impact: str | None
    #: The assessment revision the draft was read from.
    assessment_revision: int | None
    #: What 7(2)(a) asks for that the register does not yet hold.
    missing: list[str]
    duty: BreachDutyOut | None


class BreachReportFactOut(Out):
    #: ii, iii, iv or v.
    item: str
    label: str
    text: str | None


class BreachChannelCountOut(Out):
    channel: str
    delivered: int
    queued: int
    failed: int


class BreachNoticeVersionCountOut(Out):
    version: int
    approved_at: datetime | None
    channels: list[BreachChannelCountOut]


class BreachNoticeAccountOut(Out):
    """Rule 7(2)(b)(vi). Present whether or not anything was sent."""

    sent: bool
    statement: str
    listed: int
    notified: int
    versions: list[BreachNoticeVersionCountOut]


class BreachReportOut(Out):
    """Rule 7(2)(b), all six items, drafted from the register."""

    document: str
    basis: str
    reference: str
    incident_reference: str
    breach_reference: str | None
    title: str
    generated_at: datetime
    determination: str
    detected_at: datetime
    began_at: datetime | None
    became_aware_at: datetime | None
    location: BreachLocationOut
    #: (i) updated and detailed information.
    determinations: list[BreachDeterminationOut]
    assessment: BreachAssessmentOut | None
    assessment_revisions: int
    #: (ii) to (v).
    facts: list[BreachReportFactOut]
    #: (vi) the account of notices to principals.
    notices: BreachNoticeAccountOut
    missing: list[str]
    duty: BreachDutyOut | None
    duties: list[BreachDutyOut]


@router.get(
    "/{breach_uuid}/board/intimation",
    response_model=BreachIntimationOut,
    summary="Draft the Board's initial intimation (Rule 7(2)(a)) from the register",
)
async def board_intimation(breach_uuid: UUID, principal: BreachReader) -> dict[str, Any]:
    async with connection() as conn:
        return await board.intimation(conn, breach_uuid=str(breach_uuid))


@router.get(
    "/{breach_uuid}/board/report",
    response_model=BreachReportOut,
    summary="Draft the Board's detailed report (Rule 7(2)(b)), all six items",
)
async def board_report(breach_uuid: UUID, principal: BreachReader) -> dict[str, Any]:
    async with connection() as conn:
        return await board.report(conn, breach_uuid=str(breach_uuid))


# ------------------------------------ the organisation's board (S3-07)


class OrgBoardDutyOut(Out):
    """A duty as the brief carries it: its clock, and nobody's name."""

    duty: str
    label: str
    basis: str
    state: str
    due_at: datetime | None
    anchored_at: datetime | None
    completed_at: datetime | None
    clock: BreachClockOut


class OrgBoardTouchedOut(Out):
    listed: int
    notified: int


class OrgBoardBriefOut(Out):
    """For the organisation's board, drafted from the register. The platform
    never reports to the board; a person does, and the DPO records it."""

    document: str
    basis: str
    reference: str
    incident_reference: str
    breach_reference: str | None
    title: str
    generated_at: datetime
    detected_at: datetime
    began_at: datetime | None
    location: BreachLocationOut
    #: pending, yes or no.
    validation: str
    became_aware_at: datetime | None
    cert_in_reportable: bool
    duties: list[OrgBoardDutyOut]
    #: Counts only: who it touched is never named here.
    touched: OrgBoardTouchedOut
    missing: list[str]
    #: The organisation's board duty itself, as the others: its clock only.
    duty: OrgBoardDutyOut | None


@router.get(
    "/{breach_uuid}/org-board/brief",
    response_model=OrgBoardBriefOut,
    summary="Draft the brief for the organisation's board from the register",
)
async def org_board_brief(breach_uuid: UUID, principal: BreachReader) -> dict[str, Any]:
    async with connection() as conn:
        return await board.org_board_brief(conn, breach_uuid=str(breach_uuid))


# ------------------------------------------------------------ breach tickets (S3-08)


class BreachTicketIn(Schema):
    """Either a member of staff, by `user_uuid`, or - S3-09 - somebody named by
    `email` (with `full_name`, and a `mobile` if known), who is given a
    breach-only login if they have no console account."""

    #: An active member of staff, on one of BREACH_TICKET_EMAIL_DOMAINS.
    user_uuid: UUID | None = None
    full_name: Annotated[str, Field(max_length=200)] | None = None
    email: Annotated[str, Field(max_length=320)] | None = None
    mobile: Annotated[str, Field(max_length=32)] | None = None
    #: What they are asked to do. Sealed.
    instruction: Annotated[str, Field(min_length=1, max_length=20_000)]
    #: Optional date to answer by; shown to both sides.
    answer_by: date | None = None


class BreachTicketReasonIn(Schema):
    #: Why. Sealed, and written on the thread for the holder to read.
    reason: Annotated[str, Field(min_length=1, max_length=8000)]


class BreachTicketMoveOut(Out):
    #: send_back, close, withdraw or reopen (the office); return (the holder).
    move: str
    reason_required: bool


class BreachTicketEventOut(Out):
    event_uuid: UUID
    #: returned, sent_back, closed, withdrawn or reopened.
    kind: str
    #: With a return: done, partial or failed.
    outcome: str | None
    summary: str | None
    reason: str | None
    occurred_at: datetime
    actor_name: str | None


class BreachTicketMessageOut(Out):
    message_uuid: UUID
    #: office, holder or system.
    author_side: str
    author_name: str | None
    #: instruction, message, return or status.
    kind: str
    body: str
    evidence_hash: str | None
    evidence_name: str | None
    created_at: datetime


class BreachTicketOut(Out):
    """A breach ticket as the office reads it."""

    ticket_uuid: UUID
    holder_uuid: UUID
    holder_name: str | None
    assigned_by_name: str | None
    #: Set when a holder added this person as a colleague (S3-09).
    parent_ticket_uuid: UUID | None
    added_by_name: str | None
    #: issued, returned, closed or withdrawn.
    state: str
    answer_by: date | None
    #: Issued and past its answer-by date.
    overdue: bool
    created_at: datetime
    #: The holder's messages the office has not read.
    unread: int
    last_activity_at: datetime | None
    events: list[BreachTicketEventOut]
    #: What the office may do now. None on a closed breach.
    moves: list[BreachTicketMoveOut]
    may_write: bool
    #: The holder's breach-only login (S3-09): pending, active or ended. None
    #: for a member of staff.
    temporary_access: str | None


class BreachTicketDetailOut(Out):
    ticket: BreachTicketOut
    instruction: str
    messages: list[BreachTicketMessageOut]


_TICKET = "/{breach_uuid}/tickets/{ticket_uuid}"


@router.get(
    "/{breach_uuid}/tickets",
    response_model=list[BreachTicketOut],
    summary="Every ticket on a breach: holder, state, answer-by, unread, who added whom",
)
async def list_tickets(breach_uuid: UUID, principal: BreachReader) -> list[dict[str, Any]]:
    async with connection() as conn:
        return await tickets.for_breach(conn, breach_uuid=str(breach_uuid))


@router.post(
    "/{breach_uuid}/tickets",
    response_model=BreachTicketDetailOut,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a ticket to a member of staff; only on a recorded breach",
)
async def assign_ticket(
    breach_uuid: UUID, body: BreachTicketIn, principal: BreachWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        return await tickets.assign(
            conn,
            breach_uuid=str(breach_uuid),
            user_uuid=str(body.user_uuid) if body.user_uuid else None,
            full_name=body.full_name,
            email=body.email,
            mobile=body.mobile,
            instruction=body.instruction,
            answer_by=body.answer_by,
            actor_id=principal.user_id,
        )


@router.get(
    _TICKET,
    response_model=BreachTicketDetailOut,
    summary="One ticket, its thread, and the moves the server allows",
)
async def get_ticket(
    breach_uuid: UUID, ticket_uuid: UUID, principal: BreachReader
) -> dict[str, Any]:
    """Reading it marks the holder's messages read."""
    async with transaction() as conn:
        return await tickets.office_detail(
            conn, breach_uuid=str(breach_uuid), ticket_uuid=str(ticket_uuid)
        )


@router.post(
    f"{_TICKET}/messages",
    response_model=BreachTicketDetailOut,
    summary="Write to the holder on the ticket, with a file if it helps",
)
async def message_holder(
    breach_uuid: UUID,
    ticket_uuid: UUID,
    principal: BreachWriter,
    body: Annotated[str, Form(min_length=1, max_length=20_000)],
    evidence: Annotated[UploadFile | None, File(description="Optional file, max 25 MB")] = None,
) -> dict[str, Any]:
    stored = await uploads.stored(evidence, subdir="breach")
    async with transaction() as conn:
        return await tickets.office_message(
            conn,
            breach_uuid=str(breach_uuid),
            ticket_uuid=str(ticket_uuid),
            body=body,
            actor_id=principal.user_id,
            evidence=stored,
        )


@router.get(
    f"{_TICKET}/messages/{{message_uuid}}/evidence",
    summary="Download a file attached to a message on the ticket",
)
async def ticket_file(
    breach_uuid: UUID, ticket_uuid: UUID, message_uuid: UUID, principal: BreachReader
) -> Response:
    async with transaction() as conn:
        payload, name, recorded = await tickets.office_attachment(
            conn,
            breach_uuid=str(breach_uuid),
            ticket_uuid=str(ticket_uuid),
            message_uuid=str(message_uuid),
            actor_id=principal.user_id,
        )
    return uploads.download(payload, name, recorded)


async def _move(
    breach_uuid: UUID, ticket_uuid: UUID, move: str, reason: str | None, actor_id: int
) -> dict[str, Any]:
    async with transaction() as conn:
        return await tickets.office_move(
            conn,
            breach_uuid=str(breach_uuid),
            ticket_uuid=str(ticket_uuid),
            move=move,
            reason=reason,
            actor_id=actor_id,
        )


@router.post(
    f"{_TICKET}/send-back",
    response_model=BreachTicketDetailOut,
    summary="Send a returned ticket back to its holder, saying why",
)
async def send_back_ticket(
    breach_uuid: UUID, ticket_uuid: UUID, body: BreachTicketReasonIn, principal: BreachWriter
) -> dict[str, Any]:
    return await _move(breach_uuid, ticket_uuid, "send_back", body.reason, principal.user_id)


@router.post(
    f"{_TICKET}/close",
    response_model=BreachTicketDetailOut,
    summary="Close a returned ticket: the DPO's alone",
)
async def close_ticket(
    breach_uuid: UUID, ticket_uuid: UUID, principal: BreachWriter
) -> dict[str, Any]:
    return await _move(breach_uuid, ticket_uuid, "close", None, principal.user_id)


@router.post(
    f"{_TICKET}/withdraw",
    response_model=BreachTicketDetailOut,
    summary="Withdraw a ticket, saying why",
)
async def withdraw_ticket(
    breach_uuid: UUID, ticket_uuid: UUID, body: BreachTicketReasonIn, principal: BreachWriter
) -> dict[str, Any]:
    return await _move(breach_uuid, ticket_uuid, "withdraw", body.reason, principal.user_id)


@router.post(
    f"{_TICKET}/reopen",
    response_model=BreachTicketDetailOut,
    summary="Reopen a closed or withdrawn ticket, saying why",
)
async def reopen_ticket(
    breach_uuid: UUID, ticket_uuid: UUID, body: BreachTicketReasonIn, principal: BreachWriter
) -> dict[str, Any]:
    return await _move(breach_uuid, ticket_uuid, "reopen", body.reason, principal.user_id)
