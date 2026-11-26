"""Retention reviews (0076, ADR 0047).

`/retention` is the officers' register: a review per project or HR activity,
purpose and month, its people counted, its actions answered and accepted, and
the settings. `/retention-actions` is each person's own: what they were asked,
and their answer. Neither is a ticket, and neither is on the portal - an
outside holder answers by its link (`public.retention_links`).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, File, Query, Response, UploadFile
from pydantic import Field

from cmp.api.dependencies import (
    RetentionActionWriter,
    RetentionReader,
    RetentionSettingReader,
    RetentionSettingWriter,
    RetentionWriter,
)
from cmp.db.pool import across_offices, connection, transaction
from cmp.domain.retention import actions, certificate, service
from cmp.schemas.common import Out, Schema

router = APIRouter(prefix="/retention", tags=["retention"])
actions_router = APIRouter(prefix="/retention-actions", tags=["retention"])


class RetentionActionOut(Out):
    action_uuid: UUID
    review_uuid: UUID
    reference: str
    review_kind: str
    #: owner | processor
    kind: str
    #: Who is asked: a person, or a processor.
    label: str
    #: console | link | none (nobody to ask yet)
    channel: str
    #: Sealed.
    assignee_name: str | None
    #: open | answered | accepted | sent_back | not_needed
    status: str
    #: erased | anonymised | kept | not_held | reviewed
    outcome: str | None
    #: Why anonymised or kept. Sealed at rest; opened.
    reason: str | None
    keep_until: date | None
    #: Validity, owner: invite the people to consent again.
    reconsent: bool | None
    due_at: datetime
    answered_at: datetime | None
    #: Sealed.
    answered_by_name: str | None
    accepted_at: datetime | None
    #: Sealed.
    accepted_by_name: str | None
    sent_back_reason: str | None
    #: The proof attached, if any: its file name (sealed) and SHA-256.
    evidence_name: str | None = None
    evidence_hash: str | None = None
    overdue: bool


class RetentionReviewOut(Out):
    review_uuid: UUID
    reference: str
    #: validity | retention
    kind: str
    #: upcoming | due | in_progress | closed
    status: str
    office: str
    cohort: date
    project_uuid: UUID
    project_name: str
    project_status: str
    is_activity: bool
    purpose_code: str
    purpose_name: str
    retention_days: int | None
    validity_days: int | None
    lapse_behaviour: str
    notify_before_erasure: bool
    #: People in the review now; held by a legal hold; consented again.
    people: int
    held: int
    renewed: int
    first_due_at: datetime | None
    last_due_at: datetime | None
    actions: int
    actions_open: int
    actions_to_review: int
    #: Validity: asked | confirmed | declined | sent
    reconsent: str | None
    opened_at: datetime | None
    closed_at: datetime | None
    #: Sealed.
    closed_by_name: str | None
    close_note: str | None


class RetentionPersonOut(Out):
    consent_uuid: UUID
    consent_no: int
    person_no: int
    due_at: datetime
    #: withdrawal | validity
    ended_by: str
    #: in | held | renewed
    state: str
    notified_at: datetime | None
    invited_at: datetime | None


class RetentionReviewDetailOut(RetentionReviewOut):
    people_list: list[RetentionPersonOut]
    actions_list: list[RetentionActionOut]


class RetentionSettingsOut(Out):
    reminder_days: list[int]
    notice_hours: int
    action_days: int
    escalate_after_days: int
    updated_at: datetime | None
    #: Sealed.
    updated_by_name: str | None


class RetentionSettingsIn(Schema):
    reminder_days: list[int] = Field(min_length=1, max_length=5)
    notice_hours: int = Field(ge=0, le=720)
    action_days: int = Field(ge=1, le=365)
    escalate_after_days: int = Field(ge=1, le=365)


class RetentionReasonIn(Schema):
    reason: Annotated[str, Field(min_length=1, max_length=2000)]


class RetentionCloseIn(Schema):
    note: Annotated[str, Field(max_length=2000)] | None = None


class RetentionAnswerIn(Schema):
    #: Retention: erased | anonymised | kept | not_held.
    outcome: str | None = Field(default=None, max_length=16)
    #: Required for anonymised and kept.
    reason: Annotated[str, Field(max_length=2000)] | None = None
    #: Kept: when it will be looked at again.
    keep_until: date | None = None
    #: Validity: invite the people to consent again.
    reconsent: bool | None = None


class RetentionHolderReviewOut(Out):
    reference: str
    kind: str
    project_name: str
    is_activity: bool
    purpose_code: str
    purpose_name: str
    people: int
    first_due_at: datetime | None
    last_due_at: datetime | None
    retention_days: int | None
    validity_days: int | None
    status: str


class RetentionHolderActionOut(Out):
    action: RetentionActionOut
    review: RetentionHolderReviewOut


class RetentionSweepOut(Out):
    reviews_made: int
    people_added: int
    holds_changed: int
    renewed: int
    fell_due: int
    actions_opened: int
    reminders: int
    chased: int
    escalated: int
    people_told: int


async def store_proof(evidence: UploadFile) -> tuple[str, str, str | None]:
    """Keep a file attached to a retention answer: its reference, its SHA-256,
    and the name it came with. Checked as every evidence file is."""
    from cmp.api.routers.v1.rights import _safe_name
    from cmp.core.security import file_hash
    from cmp.infrastructure.storage.service import storage
    from cmp.validation.files import EVIDENCE, check_upload

    payload = await evidence.read()
    check_upload(payload, evidence.content_type, EVIDENCE)
    name = _safe_name(evidence.filename)
    ref = storage().save(payload, subdir="retention", suggested_name=name or "proof")
    return ref, file_hash(payload), name


def proof_response(payload: bytes, filename: str, recorded: str) -> Response:
    from cmp.api.routers.v1.rights import _attachment_response

    out = _attachment_response(payload, filename, recorded)
    out.headers["Cache-Control"] = "no-store"
    return out


# ----------------------------------------------------------------- register
@router.get("/reviews", response_model=list[RetentionReviewOut], summary="The retention reviews")
async def list_reviews(
    principal: RetentionReader,
    kind: Annotated[str | None, Query(max_length=12)] = None,
    status: Annotated[str | None, Query(max_length=12)] = None,
) -> list[dict[str, Any]]:
    async with connection() as conn:
        return await service.register(conn, kind=kind, status=status)


@router.post("/refresh", response_model=RetentionSweepOut, summary="Look for what falls due, now")
async def refresh(principal: RetentionWriter) -> dict[str, Any]:
    """What the night does, at once: across both offices, as the night does -
    it decides nothing an officer could not see tomorrow."""
    async with transaction() as conn, across_offices(conn):
        return await service.daily(conn)


@router.get(
    "/settings", response_model=RetentionSettingsOut, summary="Reminders, notice and deadlines"
)
async def get_settings(principal: RetentionSettingReader) -> dict[str, Any]:
    async with connection() as conn:
        return await service.settings_view(conn)


@router.put(
    "/settings", response_model=RetentionSettingsOut, summary="Set reminders, notice and deadlines"
)
async def put_settings(
    body: RetentionSettingsIn, principal: RetentionSettingWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        return await service.save_settings(
            conn,
            reminder_days=body.reminder_days,
            notice_hours=body.notice_hours,
            action_days=body.action_days,
            escalate_after_days=body.escalate_after_days,
            actor_id=principal.user_id,
        )


@router.get("/reviews/{review_uuid}", response_model=RetentionReviewDetailOut, summary="One review")
async def get_review(review_uuid: UUID, principal: RetentionReader) -> dict[str, Any]:
    async with connection() as conn:
        return await service.detail(conn, str(review_uuid))


@router.post(
    "/reviews/{review_uuid}/actions/{action_uuid}/accept",
    response_model=RetentionActionOut,
    summary="Accept an answer",
)
async def accept(
    review_uuid: UUID, action_uuid: UUID, principal: RetentionWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        await service.review(conn, str(review_uuid))
        return await actions.accept(
            conn, str(review_uuid), str(action_uuid), actor_id=principal.user_id
        )


@router.post(
    "/reviews/{review_uuid}/actions/{action_uuid}/send-back",
    response_model=RetentionActionOut,
    summary="Send an answer back, saying what is missing",
)
async def send_back(
    review_uuid: UUID, action_uuid: UUID, body: RetentionReasonIn, principal: RetentionWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        await service.review(conn, str(review_uuid))
        return await actions.send_back(
            conn,
            str(review_uuid),
            str(action_uuid),
            reason=body.reason,
            actor_id=principal.user_id,
        )


@router.post(
    "/reviews/{review_uuid}/actions/{action_uuid}/not-needed",
    response_model=RetentionActionOut,
    summary="Set an action aside: nobody need answer it",
)
async def not_needed(
    review_uuid: UUID, action_uuid: UUID, principal: RetentionWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        await service.review(conn, str(review_uuid))
        return await actions.mark_not_needed(
            conn, str(review_uuid), str(action_uuid), actor_id=principal.user_id
        )


@router.post(
    "/reviews/{review_uuid}/close", response_model=RetentionReviewOut, summary="Close a review"
)
async def close(
    review_uuid: UUID, body: RetentionCloseIn, principal: RetentionWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        row = await actions.close(
            conn, str(review_uuid), note=body.note, actor_id=principal.user_id
        )
        return service.review_view(row)


@router.get(
    "/reviews/{review_uuid}/certificate",
    summary="The certificate of a closed review, as PDF or CSV",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}, "text/csv": {}}}},
)
async def get_certificate(
    review_uuid: UUID,
    principal: RetentionReader,
    format: Annotated[str, Query(pattern="^(pdf|csv)$")] = "pdf",
) -> Response:
    """Which consents, why each ended, who was asked and what each answered,
    who accepted it and who closed the review. Consents by number; every
    download on the trail."""
    async with transaction() as conn:
        payload, filename, mime = await certificate.download(
            conn, str(review_uuid), format, actor_id=principal.user_id
        )
    return Response(
        content=payload,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.get(
    "/reviews/{review_uuid}/actions/{action_uuid}/evidence",
    summary="The proof attached to an answer",
    response_class=Response,
)
async def get_evidence(
    review_uuid: UUID, action_uuid: UUID, principal: RetentionReader
) -> Response:
    """Every download on the trail; the recorded and the served SHA-256 in the
    headers, so a changed file shows."""
    async with transaction() as conn:
        await service.review(conn, str(review_uuid))
        payload, name, digest = await actions.evidence(
            conn, str(action_uuid), actor_id=principal.user_id, review_uuid=str(review_uuid)
        )
    return proof_response(payload, name, digest)


# ------------------------------------------------------------- one's own
@actions_router.get("", response_model=list[RetentionActionOut], summary="What I am asked to do")
async def my_actions(principal: RetentionActionWriter) -> list[dict[str, Any]]:
    """Read across both offices: what is asked of a person is theirs, whichever
    office's project it is - the query names them."""
    async with connection() as conn, across_offices(conn):
        return await actions.mine(conn, principal.user_id)


@actions_router.get(
    "/{action_uuid}", response_model=RetentionHolderActionOut, summary="One of mine"
)
async def my_action(action_uuid: UUID, principal: RetentionActionWriter) -> dict[str, Any]:
    async with connection() as conn, across_offices(conn):
        return await actions.detail_for_holder(conn, str(action_uuid), user_id=principal.user_id)


@actions_router.post(
    "/{action_uuid}/answer", response_model=RetentionActionOut, summary="Answer it"
)
async def answer(
    action_uuid: UUID, body: RetentionAnswerIn, principal: RetentionActionWriter
) -> dict[str, Any]:
    async with transaction() as conn, across_offices(conn):
        return await actions.answer(
            conn,
            str(action_uuid),
            user_id=principal.user_id,
            outcome=body.outcome,
            reason=body.reason,
            keep_until=body.keep_until,
            reconsent=body.reconsent,
        )


@actions_router.post(
    "/{action_uuid}/evidence",
    response_model=RetentionActionOut,
    summary="Attach proof before answering",
)
async def add_evidence(
    action_uuid: UUID,
    principal: RetentionActionWriter,
    evidence: Annotated[UploadFile, File(description="The proof, max 25 MB")],
) -> dict[str, Any]:
    """A deletion log, a screenshot, a letter: one file, replaced by the next,
    while the answer is still to give."""
    async with connection() as conn, across_offices(conn):
        await actions.detail_for_holder(conn, str(action_uuid), user_id=principal.user_id)
    ref, digest, name = await store_proof(evidence)
    async with transaction() as conn, across_offices(conn):
        return await actions.attach(
            conn, str(action_uuid), user_id=principal.user_id, ref=ref, digest=digest, name=name
        )


@actions_router.get(
    "/{action_uuid}/evidence",
    summary="The proof I attached",
    response_class=Response,
)
async def my_evidence(action_uuid: UUID, principal: RetentionActionWriter) -> Response:
    async with transaction() as conn, across_offices(conn):
        payload, name, digest = await actions.evidence(
            conn, str(action_uuid), actor_id=principal.user_id, owner_id=principal.user_id
        )
    return proof_response(payload, name, digest)
