"""Rights requests - the DPO's surface (`/requests`) and the data principal's (`/me`).

Two routers in one module because they are two views of one record. The staff
router is gated on the `rights_request` resource: the DPO sees every request,
and the administrator sees only grievances escalated away from the DPO. The
principal's router is gated `RequireDataSubject` and takes her id from the
session and nothing from the path that could name somebody else.

Every write goes through `cmp.domain.rights.service`. Nothing here decides
anything about a request; it parses, calls, and shapes the answer.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile, status
from pydantic import Field

from cmp.api.dependencies import (
    Paging,
    RequireDataSubject,
    RequireResource,
    RightsReader,
    RightsWriter,
    reject_unknown_filters,
)
from cmp.core.errors import NotFound, ValidationFailed
from cmp.core.pagination import PageRequest
from cmp.core.security import file_hash
from cmp.db.pool import connection, transaction
from cmp.db.repositories import audit as audit_repo
from cmp.db.repositories import entities as entity_repo
from cmp.db.repositories import rights as repo
from cmp.db.repositories import users as user_repo
from cmp.domain.rights import service
from cmp.infrastructure.storage.service import storage
from cmp.schemas.common import LongText, OtpCode, Out, Page, Schema, ShortText
from cmp.validation import Email, Mobile
from cmp.validation.contacts import Contact
from cmp.validation.files import EVIDENCE, check_upload
from cmp.validation.strings import ReasonText

router = APIRouter(prefix="/requests", tags=["rights"])
subject_router = APIRouter(prefix="/me", tags=["me"])

request_paging = Paging(repo.LIST_SORTS, "-received_at")


# ------------------------------------------------------------------- shapes
class ClockOut(Out):
    received_at: datetime
    due_at: datetime
    acknowledge_by: datetime
    tickets_by: datetime
    halfway_at: datetime
    collate_by: datetime
    days_remaining: int
    overdue: bool
    at_risk: bool
    progress: float
    checkpoints: list[dict[str, Any]]
    next_checkpoint: str | None


class RequestRow(Out):
    request_uuid: UUID
    reference: str
    request_type: str
    original_type: str | None
    status: str
    outcome: str | None
    channel: str
    subject_uuid: UUID | None
    subject_name: str | None
    submitted_name: str | None
    submitted_contact: str
    received_at: datetime
    due_at: datetime
    acknowledged_at: datetime | None
    verification_status: str
    about_dpo: bool
    linked_reference: str | None
    holder_count: int
    tickets_outstanding: int
    closed_at: datetime | None
    clock: ClockOut


class RequestOut(RequestRow):
    request_text: str
    subject_email: str | None
    subject_mobile: str | None
    verification_method: str | None
    verified_at: datetime | None
    verified_by_name: str | None
    verification_note: str | None
    classified_at: datetime | None
    refusal_reason: str | None
    intent_confirmed_at: datetime | None
    linked_request_uuid: UUID | None
    linked_request_type: str | None
    nomination_uuid: UUID | None
    nominee_name: str | None
    nominee_contact: str | None
    trigger_event: str | None
    trigger_evidence_hash: str | None
    trigger_evidenced_at: datetime | None
    reviewer_uuid: UUID | None
    reviewer_name: str | None
    escalated_at: datetime | None
    grievance_upheld: bool | None
    remedy_text: str | None
    response_text: str | None
    response_file_hash: str | None
    responded_at: datetime | None
    download_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    holders_confirmed: int
    tickets_issued: int
    tickets_returned: int
    item_count: int
    items_undecided: int


class HolderOut(Out):
    holder_uuid: UUID
    label: str
    derived_from: str
    evidence: dict[str, Any]
    processor_uuid: UUID | None
    processor_name: str | None
    is_in_house: bool | None
    confirmed_at: datetime | None
    confirmed_by_name: str | None
    ticket_status: str
    instruction: str | None
    responder_name: str | None
    responder_contact: str | None
    issued_at: datetime | None
    due_at: datetime | None
    escalated_at: datetime | None
    returned_at: datetime | None
    return_summary: str | None
    return_evidence_hash: str | None
    created_at: datetime
    #: How this holder is reached. "portal": the responder has an account here
    #: and the ticket is in their console. "email": the instruction is mailed
    #: and the Privacy Office tracks it by hand, on `contact_log`.
    channel: str = "email"
    respondent_uuid: UUID | None = None
    responder_user_uuid: UUID | None = None
    responder_user_name: str | None = None
    contact_log: list[dict[str, Any]] = Field(default_factory=list)
    #: What the platform knew when the ticket was issued: the person, and the
    #: records naming this holder. Written by the platform, kept as it stood.
    brief: dict[str, Any] | None = None
    message_count: int = 0
    #: Messages from the holder the office has not read yet.
    unread_for_office: int = 0


class MessageOut(Out):
    message_uuid: UUID
    author_side: str
    author_name: str | None
    kind: str
    body: str
    evidence_hash: str | None
    created_at: datetime


class ThreadOut(Out):
    holder: HolderOut
    messages: list[MessageOut]


class ContactIn(Schema):
    """One line on a holder's contact log, optionally sending the mail too."""

    kind: str = "note"
    note: Annotated[str | None, Field(default=None, max_length=2000)] = None
    #: Re-send the instruction to the address on record, and log that it went.
    send: bool = False


class TicketOut(Out):
    """A ticket as its respondent sees it: what is asked, of whom, by when."""

    holder_uuid: UUID
    request_uuid: UUID
    reference: str
    request_type: str
    request_status: str
    label: str
    subject_name: str | None
    instruction: str | None
    ticket_status: str
    issued_at: datetime | None
    due_at: datetime | None
    escalated_at: datetime | None
    returned_at: datetime | None
    return_summary: str | None
    return_evidence_hash: str | None
    brief: dict[str, Any] | None = None
    message_count: int = 0
    #: Messages from the office the team has not read yet.
    unread_for_holder: int = 0


class TicketDetailOut(Out):
    ticket: TicketOut
    messages: list[MessageOut]


class ItemOut(Out):
    item_uuid: UUID
    other_subjects: int
    state: str
    decision: str | None
    basis: str | None
    retain_until: date | None
    floor_passed_at: datetime | None
    decided_at: datetime | None
    decided_by_name: str | None
    applied_at: datetime | None
    disposition: str | None
    disposition_at: datetime | None
    subject_role: str
    asset_uuid: UUID
    asset_type: str
    source_asset_ref: str
    source_code: str
    source_name: str
    processor_name: str | None
    project_uuid: UUID
    project_name: str
    collected_on: date
    holder_uuid: UUID | None
    holder_label: str | None
    holder_ticket_status: str | None


class RequestDetail(RequestOut):
    holders: list[HolderOut]
    items: list[ItemOut]
    transitions: list[dict[str, Any]]


class TransitionsOut(Out):
    current: str
    available: list[dict[str, Any]]


class SubjectRequestOut(Out):
    """What she sees of her own request. No verification notes, no holders -
    the holders are in the response itself, and the notes are ours."""

    request_uuid: UUID
    reference: str
    request_type: str
    status: str
    outcome: str | None
    channel: str
    request_text: str
    received_at: datetime
    due_at: datetime
    acknowledged_at: datetime | None
    verification_status: str
    responded_at: datetime | None
    response_text: str | None
    refusal_reason: str | None
    remedy_text: str | None
    grievance_upheld: bool | None
    download_available: bool
    download_expires_at: datetime | None
    linked_reference: str | None
    closed_at: datetime | None
    clock: ClockOut


class NominationOut(Out):
    nomination_uuid: UUID
    nominee_name: str
    nominee_mobile: str | None
    nominee_email: str | None
    rights: list[str]
    status: str
    accept_expires_at: datetime | None
    accepted_at: datetime | None
    declined_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class NomineeOfOut(Out):
    """A nomination that names the caller. The other side of `NominationOut`."""

    nomination_uuid: UUID
    principal_name: str
    rights: list[str]
    status: str
    #: Which of the caller's own contacts the principal recorded.
    contact: str
    accept_expires_at: datetime | None
    accepted_at: datetime | None
    created_at: datetime


# ------------------------------------------------------------------- inputs
class LogRequest(Schema):
    """A request that arrived by email, logged by the DPO. Same record as the others."""

    request_type: str
    contact: Contact
    name: ShortText | None = None
    request_text: LongText
    #: Link to the account it concerns, where the DPO knows it. Verification is
    #: still recorded separately - knowing who wrote is not the same as having
    #: checked.
    subject_uuid: UUID | None = None
    about_dpo: bool = False


class NoteIn(Schema):
    note: ReasonText | None = None


class ManualVerifyIn(Schema):
    note: Annotated[str, Field(min_length=3, max_length=1000)]


class CodeIn(Schema):
    code: OtpCode


class ClassifyIn(Schema):
    request_type: str
    note: ReasonText | None = None


class RefuseIn(Schema):
    reason: Annotated[str, Field(min_length=3, max_length=5000)]


class EvidenceIn(Schema):
    evidenced: bool
    note: ReasonText | None = None


class ReviewerIn(Schema):
    reviewer_uuid: UUID


class TransitionIn(Schema):
    to: str
    reason: ReasonText | None = None


class HolderIn(Schema):
    label: ShortText | None = None
    processor_uuid: UUID | None = None
    responder_name: ShortText | None = None
    responder_contact: Contact | None = None


class ConfirmHolderIn(Schema):
    #: One of the processor's registered respondents. Chosen instead of typing
    #: a name and address; decides the channel with it.
    respondent_uuid: UUID | None = None
    responder_name: ShortText | None = None
    responder_contact: Contact | None = None


class IssueTicketsIn(Schema):
    instruction: LongText | None = None
    due_at: datetime | None = None


class DecideIn(Schema):
    decision: str
    basis: Annotated[str, Field(min_length=3, max_length=5000)]
    retain_until: date | None = None
    holder_uuid: UUID | None = None


class RespondIn(Schema):
    outcome: str
    response_text: LongText


class GrievanceDecisionIn(Schema):
    upheld: bool
    remedy_text: Annotated[str | None, Field(default=None, max_length=5000)] = None
    response_text: LongText
    rerun: bool = False


class SubjectRequestIn(Schema):
    request_type: str
    request_text: LongText
    about_dpo: bool = False


class DisputeIn(Schema):
    text: LongText
    about_dpo: bool = False


class NominationIn(Schema):
    nominee_name: ShortText
    nominee_mobile: Mobile
    nominee_email: Email | None = None
    rights: list[str]


# ------------------------------------------------------------------ helpers
def _with_clock(row: dict[str, Any]) -> dict[str, Any]:
    return {**row, "clock": service.clock_of(row)}


async def _detail(conn: Any, row: dict[str, Any], role: Any) -> dict[str, Any]:
    return {
        **_with_clock(row),
        "holders": await repo.holders_of(conn, int(row["request_id"])),
        "items": await repo.items_of(conn, int(row["request_id"])),
        "transitions": service.transitions(row, role=role),
    }


def _subject_view(row: dict[str, Any]) -> dict[str, Any]:
    expires = row.get("download_expires_at")
    return {
        **_with_clock(row),
        "download_available": bool(
            row.get("response_file_ref") and expires and expires > datetime.now(expires.tzinfo)
        ),
    }


async def _trail(conn: Any, reference: str, *, for_subject: bool) -> list[dict[str, Any]]:
    rows = await audit_repo.for_reference(conn, reference, limit=200)
    return await entity_repo.attach(conn, rows, for_subject=for_subject)


# ------------------------------------------------------------- staff: list
@router.get("", response_model=Page[RequestRow], summary="Every request in scope")
async def list_requests(
    request: Request,
    principal: RightsReader,
    paging: Annotated[PageRequest, Depends(request_paging)],
    request_type: Annotated[str | None, Query(alias="type")] = None,
    status_: Annotated[str | None, Query(alias="status")] = None,
    overdue: Annotated[bool, Query()] = False,
    q: Annotated[str | None, Query(max_length=120)] = None,
) -> dict[str, Any]:
    """The register. Soonest due is the sort that matters; newest first is the default."""
    reject_unknown_filters(request, ("type", "status", "overdue", "q"))
    async with connection() as conn:
        items, cursor, total = await repo.list_requests(
            conn,
            paging,
            role=principal.role,
            user_id=principal.user_id,
            request_type=request_type,
            status=status_,
            overdue=overdue,
            q=q,
        )
    return {"items": [_with_clock(r) for r in items], "next_cursor": cursor, "total": total}


@router.post(
    "",
    response_model=RequestOut,
    status_code=status.HTTP_201_CREATED,
    summary="Log a request received by email",
)
async def log_request(body: LogRequest, principal: RightsWriter) -> dict[str, Any]:
    """Email to the DPO makes the same record as the dashboard and the notice link.

    Verification stays pending: the DPO records how identity was established
    as a separate act, with a reason, so the record says *how* rather than
    only that somebody was satisfied.
    """
    async with transaction() as conn:
        subject_id: int | None = None
        if body.subject_uuid:
            subject = await user_repo.by_uuid(conn, str(body.subject_uuid))
            if not subject or subject["role"] != "data_subject":
                raise NotFound("Data principal")
            subject_id = int(subject["id"])
        row = await service.create(
            conn,
            request_type=body.request_type,
            channel="staff_logged",
            request_text=body.request_text,
            submitted_contact=body.contact,
            submitted_name=body.name,
            subject_user_id=subject_id,
            actor_id=principal.user_id,
            about_dpo=body.about_dpo,
        )
        return _with_clock(row)


@router.get("/{request_uuid}", response_model=RequestDetail)
async def get_request(request_uuid: UUID, principal: RightsReader) -> dict[str, Any]:
    async with connection() as conn:
        row = await service.require(
            conn, str(request_uuid), role=principal.role, user_id=principal.user_id
        )
        return await _detail(conn, row, principal.role)


@router.get("/{request_uuid}/transitions", response_model=TransitionsOut)
async def get_transitions(request_uuid: UUID, principal: RightsReader) -> dict[str, Any]:
    """What may happen next for this role, and why anything else is blocked."""
    async with connection() as conn:
        row = await service.require(
            conn, str(request_uuid), role=principal.role, user_id=principal.user_id
        )
    return {"current": row["status"], "available": service.transitions(row, role=principal.role)}


@router.get("/{request_uuid}/trail", summary="Everything recorded about this request")
async def get_trail(request_uuid: UUID, principal: RightsReader) -> list[dict[str, Any]]:
    async with connection() as conn:
        row = await service.require(
            conn, str(request_uuid), role=principal.role, user_id=principal.user_id
        )
        return await _trail(conn, str(row["reference"]), for_subject=False)


async def _load(conn: Any, request_uuid: UUID, principal: Any) -> dict[str, Any]:
    return await service.require(
        conn, str(request_uuid), role=principal.role, user_id=principal.user_id
    )


# --------------------------------------------------------- staff: the path
@router.post(
    "/{request_uuid}/acknowledge",
    response_model=RequestOut,
    summary="Send (or re-send) the acknowledgement",
)
async def acknowledge(request_uuid: UUID, principal: RightsWriter) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return _with_clock(await service.acknowledge(conn, row, actor_id=principal.user_id))


@router.post(
    "/{request_uuid}/verification/code",
    response_model=RequestOut,
    summary="Send a code to the stored channel",
)
async def send_code(request_uuid: UUID, principal: RightsWriter) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return _with_clock(
            await service.send_verification_code(
                conn, row, role=principal.role, actor_id=principal.user_id
            )
        )


@router.post(
    "/{request_uuid}/verification/confirm",
    response_model=RequestOut,
    summary="Enter the code she read back",
)
async def confirm_code(request_uuid: UUID, body: CodeIn, principal: RightsWriter) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return _with_clock(
            await service.confirm_verification_code(
                conn, row, code=body.code, role=principal.role, actor_id=principal.user_id
            )
        )


@router.post(
    "/{request_uuid}/verification/manual",
    response_model=RequestOut,
    summary="Verified by hand, with the reason recorded",
)
async def verify_manually(
    request_uuid: UUID, body: ManualVerifyIn, principal: RightsWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return _with_clock(
            await service.verify_manually(
                conn, row, note=body.note, role=principal.role, actor_id=principal.user_id
            )
        )


@router.post(
    "/{request_uuid}/verification/fail",
    response_model=RequestOut,
    summary="No match, or verification not satisfied",
)
async def fail_verification(
    request_uuid: UUID, body: NoteIn, principal: RightsWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return _with_clock(
            await service.fail_verification(
                conn, row, note=body.note, role=principal.role, actor_id=principal.user_id
            )
        )


@router.post(
    "/{request_uuid}/classify",
    response_model=RequestOut,
    summary="Confirm, or reclassify, what this is",
)
async def classify(request_uuid: UUID, body: ClassifyIn, principal: RightsWriter) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return _with_clock(
            await service.classify(
                conn,
                row,
                request_type=body.request_type,
                note=body.note,
                role=principal.role,
                actor_id=principal.user_id,
            )
        )


@router.post(
    "/{request_uuid}/refuse",
    response_model=RequestOut,
    summary="Not a rights request, or refused - with reasons",
)
async def refuse(request_uuid: UUID, body: RefuseIn, principal: RightsWriter) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return _with_clock(
            await service.refuse(
                conn, row, reason=body.reason, role=principal.role, actor_id=principal.user_id
            )
        )


@router.post(
    "/{request_uuid}/withdrawal",
    response_model=RequestOut,
    summary="She meant withdrawal, not erasure",
)
async def as_withdrawal(
    request_uuid: UUID, body: NoteIn, principal: RightsWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return _with_clock(
            await service.reclassify_as_withdrawal(
                conn, row, note=body.note, role=principal.role, actor_id=principal.user_id
            )
        )


@router.post(
    "/{request_uuid}/intent", response_model=RequestOut, summary="She means erasure - confirmed"
)
async def confirm_intent(request_uuid: UUID, principal: RightsWriter) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return _with_clock(
            await service.confirm_intent(conn, row, role=principal.role, actor_id=principal.user_id)
        )


@router.post(
    "/{request_uuid}/event", response_model=RequestOut, summary="Is the triggering event evidenced?"
)
async def event_evidence(
    request_uuid: UUID, body: EvidenceIn, principal: RightsWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return _with_clock(
            await service.record_event_evidence(
                conn,
                row,
                evidenced=body.evidenced,
                note=body.note,
                role=principal.role,
                actor_id=principal.user_id,
            )
        )


@router.get("/{request_uuid}/event/evidence", summary="Download the triggering-event evidence")
async def event_evidence_file(request_uuid: UUID, principal: RightsReader) -> Response:
    async with connection() as conn:
        row = await _load(conn, request_uuid, principal)
    if not row.get("trigger_evidence_ref"):
        raise NotFound("Evidence")
    payload = storage().read(str(row["trigger_evidence_ref"]))
    return Response(
        content=payload,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{row["reference"]}-event-evidence"',
            "X-Recorded-SHA256": str(row.get("trigger_evidence_hash") or ""),
            "X-Content-SHA256": file_hash(payload),
        },
    )


@router.post(
    "/{request_uuid}/escalate", response_model=RequestOut, summary="The complaint is about the DPO"
)
async def escalate(request_uuid: UUID, principal: RightsWriter) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return _with_clock(
            await service.escalate(conn, row, role=principal.role, actor_id=principal.user_id)
        )


@router.post(
    "/{request_uuid}/reviewer", response_model=RequestOut, summary="Name the independent reviewer"
)
async def assign_reviewer(
    request_uuid: UUID, body: ReviewerIn, principal: RightsWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return _with_clock(
            await service.assign_reviewer(
                conn,
                row,
                reviewer_uuid=str(body.reviewer_uuid),
                role=principal.role,
                actor_id=principal.user_id,
            )
        )


@router.post("/{request_uuid}/transition", response_model=RequestOut)
async def transition(
    request_uuid: UUID, body: TransitionIn, principal: RightsWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return _with_clock(
            await service.transition(
                conn,
                row,
                to=body.to,
                reason=body.reason,
                role=principal.role,
                actor_id=principal.user_id,
            )
        )


# ------------------------------------------------------------ staff: holders
@router.post(
    "/{request_uuid}/holders/derive",
    response_model=list[HolderOut],
    summary="Holders derived from export_line and asset_consent",
)
async def derive_holders(request_uuid: UUID, principal: RightsWriter) -> list[dict[str, Any]]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return await service.derive_holders(
            conn, row, role=principal.role, actor_id=principal.user_id
        )


@router.post(
    "/{request_uuid}/holders",
    response_model=HolderOut,
    status_code=status.HTTP_201_CREATED,
    summary="A holder the records missed",
)
async def add_holder(request_uuid: UUID, body: HolderIn, principal: RightsWriter) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return await service.add_holder(
            conn,
            row,
            label=body.label or "",
            processor_uuid=str(body.processor_uuid) if body.processor_uuid else None,
            responder_name=body.responder_name,
            responder_contact=body.responder_contact,
            role=principal.role,
            actor_id=principal.user_id,
        )


@router.post("/{request_uuid}/holders/{holder_uuid}/confirm", response_model=HolderOut)
async def confirm_holder(
    request_uuid: UUID, holder_uuid: UUID, body: ConfirmHolderIn, principal: RightsWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return await service.confirm_holder(
            conn,
            row,
            holder_uuid=str(holder_uuid),
            responder_name=body.responder_name,
            responder_contact=body.responder_contact,
            role=principal.role,
            actor_id=principal.user_id,
            respondent_uuid=str(body.respondent_uuid) if body.respondent_uuid else None,
        )


@router.get(
    "/{request_uuid}/holders/{holder_uuid}/thread",
    response_model=ThreadOut,
    summary="The ticket's thread, as the office reads it",
)
async def holder_thread(
    request_uuid: UUID, holder_uuid: UUID, principal: RightsWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return await service.thread_for_office(
            conn, row, holder_uuid=str(holder_uuid), role=principal.role
        )


async def _attachment(evidence: UploadFile | None) -> tuple[str | None, str | None]:
    """Store a file attached to a message, if there is one."""
    if evidence is None:
        return None, None
    payload = await evidence.read()
    check_upload(payload, evidence.content_type, EVIDENCE)
    return (
        storage().save(payload, subdir="rights", suggested_name=evidence.filename or "attachment"),
        file_hash(payload),
    )


def _attachment_response(payload: bytes, filename: str, recorded: str) -> Response:
    return Response(
        content=payload,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Recorded-SHA256": recorded,
            "X-Content-SHA256": file_hash(payload),
        },
    )


@router.post(
    "/{request_uuid}/holders/{holder_uuid}/thread",
    response_model=ThreadOut,
    summary="Write to the holder on the ticket, with a file if it helps",
)
async def post_to_holder(
    request_uuid: UUID,
    holder_uuid: UUID,
    principal: RightsWriter,
    body: Annotated[str, Form(min_length=1, max_length=20_000)],
    evidence: Annotated[UploadFile | None, File(description="Optional file, max 25 MB")] = None,
) -> dict[str, Any]:
    """Kept on the thread, and the holder is told the way it is reached: on the
    portal with a copy by mail, or by mail alone."""
    evidence_ref, evidence_hash = await _attachment(evidence)
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return await service.post_office_message(
            conn,
            row,
            holder_uuid=str(holder_uuid),
            body=body,
            role=principal.role,
            actor_id=principal.user_id,
            evidence_ref=evidence_ref,
            evidence_hash=evidence_hash,
        )


@router.get(
    "/{request_uuid}/holders/{holder_uuid}/messages/{message_uuid}/evidence",
    summary="Download a file attached to a message on the ticket",
)
async def holder_message_attachment(
    request_uuid: UUID, holder_uuid: UUID, message_uuid: UUID, principal: RightsReader
) -> Response:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        holder = await repo.holder_by_uuid(conn, int(row["request_id"]), str(holder_uuid))
        if not holder:
            raise NotFound("Holder")
        payload, filename, recorded = await service.message_attachment(
            conn, holder=holder, message_uuid=str(message_uuid), actor_id=principal.user_id
        )
    return _attachment_response(payload, filename, recorded)


@router.post(
    "/{request_uuid}/holders/{holder_uuid}/contact",
    response_model=HolderOut,
    summary="Record a mail sent, a chase, or a reply - and optionally send the mail",
)
async def log_contact(
    request_uuid: UUID, holder_uuid: UUID, body: ContactIn, principal: RightsWriter
) -> dict[str, Any]:
    """The trail for a holder reached by email, kept on the request rather than
    in one person's inbox."""
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return await service.log_contact(
            conn,
            row,
            holder_uuid=str(holder_uuid),
            kind=body.kind,
            note=body.note,
            send=body.send,
            role=principal.role,
            actor_id=principal.user_id,
        )


@router.post(
    "/{request_uuid}/tickets",
    response_model=list[HolderOut],
    summary="Issue a ticket to every confirmed holder",
)
async def issue_tickets(
    request_uuid: UUID, body: IssueTicketsIn, principal: RightsWriter
) -> list[dict[str, Any]]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return await service.issue_tickets(
            conn,
            row,
            instruction=body.instruction,
            due_at=body.due_at,
            role=principal.role,
            actor_id=principal.user_id,
        )


@router.post(
    "/{request_uuid}/holders/{holder_uuid}/return",
    response_model=HolderOut,
    summary="Record what the holder returned",
)
async def return_ticket(
    request_uuid: UUID,
    holder_uuid: UUID,
    principal: RightsWriter,
    summary: Annotated[str, Form(min_length=1, max_length=20_000)],
    evidence: Annotated[UploadFile | None, File(description="Optional evidence, max 25 MB")] = None,
) -> dict[str, Any]:
    evidence_ref: str | None = None
    evidence_hash: str | None = None
    if evidence is not None:
        payload = await evidence.read()
        check_upload(payload, evidence.content_type, EVIDENCE)
        evidence_hash = file_hash(payload)
        evidence_ref = storage().save(
            payload, subdir="rights", suggested_name=evidence.filename or "evidence"
        )
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return await service.return_ticket(
            conn,
            row,
            holder_uuid=str(holder_uuid),
            summary=summary,
            evidence_ref=evidence_ref,
            evidence_hash=evidence_hash,
            role=principal.role,
            actor_id=principal.user_id,
        )


@router.get(
    "/{request_uuid}/holders/{holder_uuid}/evidence", summary="Download a holder's return evidence"
)
async def holder_evidence(
    request_uuid: UUID, holder_uuid: UUID, principal: RightsReader
) -> Response:
    async with connection() as conn:
        row = await _load(conn, request_uuid, principal)
        holder = await repo.holder_by_uuid(conn, int(row["request_id"]), str(holder_uuid))
    if not holder or not holder.get("return_evidence_ref"):
        raise NotFound("Evidence")
    payload = storage().read(str(holder["return_evidence_ref"]))
    return Response(
        content=payload,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{row["reference"]}-{holder_uuid}-evidence"'
            ),
            "X-Recorded-SHA256": str(holder.get("return_evidence_hash") or ""),
            "X-Content-SHA256": file_hash(payload),
        },
    )


@router.post(
    "/{request_uuid}/holders/{holder_uuid}/escalate",
    response_model=HolderOut,
    summary="A holder missed its date - escalate once",
)
async def escalate_ticket(
    request_uuid: UUID, holder_uuid: UUID, principal: RightsWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return await service.escalate_ticket(
            conn, row, holder_uuid=str(holder_uuid), role=principal.role, actor_id=principal.user_id
        )


# -------------------------------------------------------------- staff: scope
@router.post(
    "/{request_uuid}/scope/derive",
    response_model=list[ItemOut],
    summary="Every appearance of her in a collected asset",
)
async def derive_scope(request_uuid: UUID, principal: RightsWriter) -> list[dict[str, Any]]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return await service.derive_scope(
            conn, row, role=principal.role, actor_id=principal.user_id
        )


@router.put(
    "/{request_uuid}/scope/{item_uuid}",
    response_model=ItemOut,
    summary="What can go, what must stay, and why",
)
async def decide_item(
    request_uuid: UUID, item_uuid: UUID, body: DecideIn, principal: RightsWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return await service.decide_item(
            conn,
            row,
            item_uuid=str(item_uuid),
            decision=body.decision,
            basis=body.basis,
            retain_until=body.retain_until,
            holder_uuid=str(body.holder_uuid) if body.holder_uuid else None,
            role=principal.role,
            actor_id=principal.user_id,
        )


@router.post(
    "/{request_uuid}/scope/{item_uuid}/apply",
    response_model=ItemOut,
    summary="Set her junction row - the asset survives",
)
async def apply_item(
    request_uuid: UUID, item_uuid: UUID, principal: RightsWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return await service.apply_item(
            conn, row, item_uuid=str(item_uuid), role=principal.role, actor_id=principal.user_id
        )


# ----------------------------------------------------------- staff: closure
@router.post("/{request_uuid}/respond", response_model=RequestOut, summary="Release and close")
async def respond(request_uuid: UUID, body: RespondIn, principal: RightsWriter) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        return _with_clock(
            await service.respond(
                conn,
                row,
                outcome=body.outcome,
                response_text=body.response_text,
                role=principal.role,
                actor_id=principal.user_id,
            )
        )


@router.post("/{request_uuid}/decide", summary="Decide a grievance")
async def decide_grievance(
    request_uuid: UUID, body: GrievanceDecisionIn, principal: RightsWriter
) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        result = await service.decide_grievance(
            conn,
            row,
            upheld=body.upheld,
            remedy_text=body.remedy_text,
            response_text=body.response_text,
            rerun=body.rerun,
            role=principal.role,
            actor_id=principal.user_id,
        )
    rerun = result["rerun"]
    return {
        "request": RequestOut.model_validate(_with_clock(result["request"])).model_dump(),
        "rerun_reference": rerun["reference"] if rerun else None,
        "rerun_uuid": rerun["request_uuid"] if rerun else None,
    }


@router.get("/{request_uuid}/download", summary="The released response file")
async def download_response(request_uuid: UUID, principal: RightsReader) -> Response:
    async with transaction() as conn:
        row = await _load(conn, request_uuid, principal)
        payload, filename, recorded = await service.download(
            conn, row, actor_id=principal.user_id, as_subject=False
        )
    return _file(payload, filename, recorded)


def _file(payload: bytes, filename: str, recorded: str) -> Response:
    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Recorded-SHA256": recorded,
            "X-Content-SHA256": file_hash(payload),
            "Cache-Control": "no-store",
        },
    )


# ---------------------------------------------------------- the principal
@subject_router.get("/requests", response_model=list[SubjectRequestOut], summary="My requests")
async def my_requests(principal: RequireDataSubject) -> list[dict[str, Any]]:
    async with connection() as conn:
        rows = await repo.for_subject(conn, principal.user_id)
    return [_subject_view(r) for r in rows]


@subject_router.post(
    "/requests",
    response_model=SubjectRequestOut,
    status_code=status.HTTP_201_CREATED,
    summary="Make a request, signed in",
)
async def make_request(body: SubjectRequestIn, principal: RequireDataSubject) -> dict[str, Any]:
    """From the dashboard. The session is the verification, so the clock starts
    and the acknowledgement goes out in the same moment."""
    if body.request_type not in ("access", "correction", "erasure", "grievance"):
        raise ValidationFailed(
            "Choose access, correction, erasure or grievance", field="request_type"
        )
    async with transaction() as conn:
        me = await user_repo.by_id(conn, principal.user_id)
        if not me:
            raise NotFound("User")
        row = await service.create(
            conn,
            request_type=body.request_type,
            channel="portal",
            request_text=body.request_text,
            submitted_contact=str(me.get("email") or me.get("mobile") or ""),
            submitted_name=str(me.get("full_name") or ""),
            subject_user_id=principal.user_id,
            actor_id=principal.user_id,
            verification_method="session",
            about_dpo=body.about_dpo,
        )
    return _subject_view(row)


async def _mine(conn: Any, request_uuid: UUID, user_id: int) -> dict[str, Any]:
    row = await repo.subject_request(conn, str(request_uuid), user_id)
    if not row:
        raise NotFound("Rights request")
    return row


@subject_router.get("/requests/{request_uuid}", response_model=SubjectRequestOut)
async def my_request(request_uuid: UUID, principal: RequireDataSubject) -> dict[str, Any]:
    async with connection() as conn:
        return _subject_view(await _mine(conn, request_uuid, principal.user_id))


@subject_router.get("/requests/{request_uuid}/trail", summary="What was recorded about my request")
async def my_request_trail(
    request_uuid: UUID, principal: RequireDataSubject
) -> list[dict[str, Any]]:
    async with connection() as conn:
        row = await _mine(conn, request_uuid, principal.user_id)
        return await _trail(conn, str(row["reference"]), for_subject=True)


@subject_router.get(
    "/requests/{request_uuid}/download", summary="The response, while the window is open"
)
async def my_download(request_uuid: UUID, principal: RequireDataSubject) -> Response:
    async with transaction() as conn:
        row = await _mine(conn, request_uuid, principal.user_id)
        payload, filename, recorded = await service.download(
            conn, row, actor_id=principal.user_id, as_subject=True
        )
    return _file(payload, filename, recorded)


@subject_router.post(
    "/requests/{request_uuid}/dispute",
    response_model=SubjectRequestOut,
    status_code=status.HTTP_201_CREATED,
    summary="Dispute the response - a grievance under s.13",
)
async def dispute(
    request_uuid: UUID, body: DisputeIn, principal: RequireDataSubject
) -> dict[str, Any]:
    async with transaction() as conn:
        row = await _mine(conn, request_uuid, principal.user_id)
        created = await service.dispute(
            conn,
            row,
            subject_user_id=principal.user_id,
            text=body.text,
            about_dpo=body.about_dpo,
        )
    return _subject_view(created)


@subject_router.get(
    "/nominations", response_model=list[NominationOut], summary="Whom I have nominated"
)
async def my_nominations(principal: RequireDataSubject) -> list[dict[str, Any]]:
    async with connection() as conn:
        return await repo.nominations_of(conn, principal.user_id)


@subject_router.get(
    "/nominee-of",
    response_model=list[NomineeOfOut],
    summary="Who has nominated me",
)
async def nominations_naming_me(principal: RequireDataSubject) -> list[dict[str, Any]]:
    """Nominations where the caller is the nominee.

    A data principal can be somebody else's nominee too, and until this
    existed her account said nothing about it. Matched on her own recorded
    contacts, since a nomination names a person by contact and not by account.
    Acting still goes through the nominee page and a code to that contact -
    being signed in here is not that proof.
    """
    async with connection() as conn:
        me = await user_repo.by_id(conn, principal.user_id)
        if me is None:
            return []
        rows = await repo.nominations_naming(conn, mobile=me.get("mobile"), email=me.get("email"))
        out: list[dict[str, Any]] = []
        for row in rows:
            mine_mobile = me.get("mobile")
            matched = (
                str(row["nominee_mobile"])
                if mine_mobile and row.get("nominee_mobile") == mine_mobile
                else str(row.get("nominee_email") or "")
            )
            out.append({**row, "contact": matched})
        return out


@subject_router.post(
    "/nominations",
    response_model=NominationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Nominate somebody - s.14",
)
async def nominate(body: NominationIn, principal: RequireDataSubject) -> dict[str, Any]:
    async with transaction() as conn:
        return await service.nominate(
            conn,
            principal_user_id=principal.user_id,
            nominee_name=body.nominee_name,
            nominee_mobile=body.nominee_mobile,
            nominee_email=str(body.nominee_email) if body.nominee_email else None,
            rights=body.rights,
        )


@subject_router.delete(
    "/nominations/{nomination_uuid}", response_model=NominationOut, summary="Revoke a nomination"
)
async def revoke_nomination(nomination_uuid: UUID, principal: RequireDataSubject) -> dict[str, Any]:
    async with transaction() as conn:
        return await service.revoke_nomination(
            conn, nomination_uuid=str(nomination_uuid), principal_user_id=principal.user_id
        )


# ------------------------------------------------------ the respondent's side
ticket_router = APIRouter(prefix="/tickets", tags=["tickets"])

TicketReader = Annotated[Any, Depends(RequireResource("ticket"))]
TicketWriter = Annotated[Any, Depends(RequireResource("ticket", write=True))]


@ticket_router.get("", response_model=list[TicketOut], summary="Tickets addressed to me")
async def my_tickets(principal: TicketReader) -> list[dict[str, Any]]:
    """The portal channel's inbox: the holders of a rights request that are one
    of our own teams answer here, not by email. Scope OWN - only what is
    addressed to this account, and only what the instruction says."""
    async with connection() as conn:
        return await service.tickets_for(conn, principal.user_id)


@ticket_router.get(
    "/{holder_uuid}",
    response_model=TicketDetailOut,
    summary="One ticket, with its brief and thread",
)
async def my_ticket(holder_uuid: UUID, principal: TicketReader) -> dict[str, Any]:
    """Reading it marks the office's messages read."""
    async with transaction() as conn:
        return await service.ticket_detail_for(conn, principal.user_id, str(holder_uuid))


@ticket_router.post(
    "/{holder_uuid}/messages",
    response_model=TicketDetailOut,
    summary="Write to the Privacy Office on my ticket, with a file if it helps",
)
async def message_office(
    holder_uuid: UUID,
    principal: TicketWriter,
    body: Annotated[str, Form(min_length=1, max_length=20_000)],
    evidence: Annotated[UploadFile | None, File(description="Optional file, max 25 MB")] = None,
) -> dict[str, Any]:
    """Kept on the thread, and every DPO is told."""
    evidence_ref, evidence_hash = await _attachment(evidence)
    async with transaction() as conn:
        return await service.post_holder_message(
            conn,
            user_id=principal.user_id,
            holder_uuid=str(holder_uuid),
            body=body,
            evidence_ref=evidence_ref,
            evidence_hash=evidence_hash,
        )


@ticket_router.get(
    "/{holder_uuid}/messages/{message_uuid}/evidence",
    summary="Download a file attached to a message on my ticket",
)
async def my_message_attachment(
    holder_uuid: UUID, message_uuid: UUID, principal: TicketReader
) -> Response:
    async with transaction() as conn:
        holder = await repo.ticket_for_user(conn, principal.user_id, str(holder_uuid))
        if not holder:
            raise NotFound("Ticket")
        payload, filename, recorded = await service.message_attachment(
            conn, holder=holder, message_uuid=str(message_uuid), actor_id=principal.user_id
        )
    return _attachment_response(payload, filename, recorded)


@ticket_router.post(
    "/{holder_uuid}/return",
    response_model=TicketOut,
    summary="Return a ticket addressed to me",
)
async def return_my_ticket(
    holder_uuid: UUID,
    principal: TicketWriter,
    summary: Annotated[str, Form(min_length=1, max_length=20_000)],
    evidence: Annotated[UploadFile | None, File(description="Optional evidence, max 25 MB")] = None,
) -> dict[str, Any]:
    evidence_ref: str | None = None
    evidence_hash: str | None = None
    if evidence is not None:
        payload = await evidence.read()
        check_upload(payload, evidence.content_type, EVIDENCE)
        evidence_hash = file_hash(payload)
        evidence_ref = storage().save(
            payload, subdir="rights", suggested_name=evidence.filename or "evidence"
        )
    async with transaction() as conn:
        return await service.return_own_ticket(
            conn,
            user_id=principal.user_id,
            holder_uuid=str(holder_uuid),
            summary=summary,
            evidence_ref=evidence_ref,
            evidence_hash=evidence_hash,
        )
