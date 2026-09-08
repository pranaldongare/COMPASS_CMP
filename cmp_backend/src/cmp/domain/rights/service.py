"""Rights requests: the only writer.

Every change to a request passes through here, so the audit row and the change
it describes share one transaction - a request that moved without a trail, or
a trail that names a move that rolled back, cannot happen.

The flows this implements are the five on the Privacy Engineering diagrams:
access (s.11), erasure (s.12(3)) with redaction for assets holding more than
one person, nomination (s.14) and grievance (s.13). Correction (s.12) shares
the generic path. Where the diagrams leave a question open, the default taken
here is stated at the point it applies, and it is always the one that can be
widened later without unwinding a record.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from cmp.auth.authentication import otp
from cmp.auth.rate_limit import service as ratelimit
from cmp.core.config import settings
from cmp.core.enums import Disposition, NominationStatus
from cmp.core.enums import RightsItemState as ItemState
from cmp.core.enums import RightsRequestChannel as Channel
from cmp.core.enums import RightsRequestOutcome as Outcome
from cmp.core.enums import RightsRequestStatus as Status
from cmp.core.enums import RightsRequestType as Kind
from cmp.core.enums import RightsScopeDecision as Decision
from cmp.core.enums import RightsTicketStatus as Ticket
from cmp.core.errors import BadRequest, Conflict, Forbidden, NotFound, ValidationFailed
from cmp.core.logging import get_logger
from cmp.core.permissions import Role
from cmp.core.security import new_token, token_fingerprint
from cmp.db.repositories import registry as registry_repo
from cmp.db.repositories import rights as repo
from cmp.db.repositories import users as user_repo
from cmp.db.sql import Conn, fetch_one
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.domain.rights import clock
from cmp.domain.rights import state_machine as sm
from cmp.domain.rights.state_machine import RequestFacts
from cmp.validation import choice, mask_contact, normalise_contact, normalise_mobile

log = get_logger("cmp.rights")

Row = dict[str, Any]

#: The one message a stranger gets from the public form, whatever happened.
#: Whether we hold records for the contact, whether a code went out, whether
#: it verified: none of it is confirmed to the person typing.
NEUTRAL_MESSAGE = (
    "Thank you. Your request has been recorded. If we hold records for the contact "
    "you gave, a verification code has been sent to it."
)


# --------------------------------------------------------------------- facts
def facts_of(row: Row) -> RequestFacts:
    """The snapshot the state machine decides on."""
    return RequestFacts(
        request_type=str(row["request_type"]),
        verified=row["verification_status"] == "verified",
        verification_failed=row["verification_status"] == "failed",
        classified=row["classified_at"] is not None,
        intent_confirmed=row["intent_confirmed_at"] is not None,
        nominee=row["channel"] == Channel.NOMINEE,
        event_evidenced=row["trigger_evidenced_at"] is not None,
        about_dpo=bool(row["about_dpo"]),
        reviewer_assigned=row["reviewer_user_id"] is not None,
        holders_confirmed=int(row["holders_confirmed"] or 0),
        tickets_issued=int(row["tickets_issued"] or 0),
        tickets_outstanding=int(row["tickets_outstanding"] or 0),
        tickets_unescalated=int(row["tickets_unescalated"] or 0),
        items_undecided=int(row["items_undecided"] or 0),
    )


def clock_of(row: Row) -> dict[str, Any]:
    return clock.compute(
        row["received_at"], row["due_at"], closed=row["status"] == Status.CLOSED
    ).as_dict()


async def require(conn: Conn, request_uuid: str, *, role: Role | str, user_id: int) -> Row:
    """The scoped lookup. Out of scope is 404, never 403."""
    row = await repo.by_uuid(conn, request_uuid, role=role, user_id=user_id)
    if not row:
        raise NotFound("Rights request")
    return row


async def reload(conn: Conn, row: Row) -> Row:
    fresh = await repo.by_id(conn, int(row["request_id"]))
    assert fresh is not None
    return fresh


def _may_act(row: Row, role: Role | str) -> None:
    if not sm.may_act(role, facts_of(row)):
        raise Forbidden("This request is not yours to act on")


def _open(row: Row) -> None:
    if row["status"] == Status.CLOSED:
        raise Conflict(
            f"{row['reference']} is closed. Disagreement with the outcome is a grievance, "
            "which is a new request linked to this one.",
            code="request_closed",
        )


def _before_collation(row: Row) -> None:
    _open(row)
    if Status(row["status"]) not in sm.OPEN_BEFORE_COLLATION:
        raise Conflict(
            "A response is being prepared. Finish it rather than closing the request early.",
            code="request_collating",
        )


async def _record(
    conn: Conn,
    row: Row,
    event: str,
    *,
    detail: dict[str, Any] | None = None,
    actor_user_id: int | None = None,
    entity_type: str = "rights_request",
    entity_id: int | None = None,
) -> None:
    await audit.record(
        conn,
        event=event,
        entity_type=entity_type,
        entity_id=entity_id if entity_id is not None else int(row["request_id"]),
        subject_user_id=row.get("subject_user_id"),
        actor_user_id=actor_user_id,
        detail={"reference": row["reference"], **(detail or {})},
    )


def contact_for(row: Row) -> str | None:
    """Where a message about this request goes.

    A nominee acting is written to, not the principal - she may be exactly as
    incapacitated as claimed. Otherwise the stored contact where there is one,
    and what was typed on the form where there is not.
    """
    if row["channel"] == Channel.NOMINEE:
        return row.get("nominee_contact")
    return row.get("subject_email") or row.get("submitted_contact")


def _dispatch(task_name: str, *args: Any) -> None:
    """Queue a notification without failing the request that queued it."""
    from cmp.tasks import dispatch
    from cmp.tasks.notifications import rights as tasks

    dispatch.dispatch_optional(getattr(tasks, task_name), *args)


# ------------------------------------------------------------------- receipt
async def create(
    conn: Conn,
    *,
    request_type: Kind | str,
    channel: Channel | str,
    request_text: str,
    submitted_contact: str,
    submitted_name: str | None = None,
    subject_user_id: int | None = None,
    actor_id: int | None = None,
    verification_method: str | None = None,
    verification_note: str | None = None,
    linked_request_id: int | None = None,
    nomination_id: int | None = None,
    trigger_event: str | None = None,
    trigger_evidence_ref: str | None = None,
    trigger_evidence_hash: str | None = None,
    about_dpo: bool = False,
) -> Row:
    """Make the record. Dashboard, notice link, email, nominee: all the same row.

    The clock starts here. `due_at` is computed from the published period and
    written to the row, so the deadline of this request is what it was told,
    whatever the setting says later.
    """
    kind = choice(Kind, request_type, field="request_type")
    now = datetime.now(UTC)
    verified = verification_method in ("session", "code", "manual")
    row = await repo.create(
        conn,
        request_type=kind.value,
        channel=Channel(channel).value,
        subject_user_id=subject_user_id,
        submitted_name=submitted_name,
        submitted_contact=submitted_contact,
        request_text=request_text,
        due_at=clock.due_for(kind, now),
        created_by=actor_id,
        verification_method=verification_method,
        verification_status="verified" if verified else "pending",
        verified_by=actor_id if verification_method == "manual" else None,
        verification_note=verification_note,
        linked_request_id=linked_request_id,
        nomination_id=nomination_id,
        trigger_event=trigger_event,
        trigger_evidence_ref=trigger_evidence_ref,
        trigger_evidence_hash=trigger_evidence_hash,
        about_dpo=about_dpo,
    )
    full = await reload(conn, row)
    await _record(
        conn,
        full,
        Event.RIGHTS_REQUEST_RECEIVED,
        actor_user_id=actor_id,
        detail={
            "request_type": kind.value,
            "channel": str(channel),
            "due_at": full["due_at"].isoformat(),
            "verification": full["verification_status"],
            "linked": full.get("linked_reference"),
        },
    )
    if verified:
        full = await acknowledge(conn, full, actor_id=actor_id)
    return full


async def acknowledge(conn: Conn, row: Row, *, actor_id: int | None) -> Row:
    """Reference number, expected date, and what she will receive.

    Idempotent: the first acknowledgement sets the timestamp; a re-send keeps
    it, because "when was she told" is the date the clock checkpoint is about.
    """
    if row["acknowledged_at"] is None:
        await repo.update(conn, int(row["request_id"]), acknowledged_at=datetime.now(UTC))
        row = await reload(conn, row)
    await _record(conn, row, Event.RIGHTS_ACKNOWLEDGED, actor_user_id=actor_id)
    contact = contact_for(row)
    if contact:
        _dispatch(
            "send_rights_acknowledgement",
            contact,
            row["reference"],
            str(row["request_type"]),
            row["due_at"].date().isoformat(),
            clock.response_period_days(str(row["request_type"])),
        )
    return row


# -------------------------------------------------------------- public form
async def submit_public(
    conn: Conn,
    *,
    request_type: Kind | str,
    contact: str,
    name: str | None,
    request_text: str,
    ip_address: str | None,
) -> dict[str, Any]:
    """A request from somebody who is not signed in.

    Recorded whether or not the contact matches anyone. If it does, a code goes
    to the *stored* channel for that person - never to the contact typed on the
    form, which is the whole point of verifying - and the reply is the same
    neutral sentence either way.
    """
    contact = contact.strip()
    await ratelimit.enforce(
        "rights_public_contact",
        contact.lower(),
        limit=settings.otp_requests_per_contact_per_hour,
        window_s=3600,
        message="Too many requests for this contact. Try again later.",
    )
    if ip_address:
        await ratelimit.enforce(
            "rights_public_ip", ip_address, limit=20, window_s=3600, fail_open=True
        )

    matched = await user_repo.by_contact(conn, contact)
    subject_id = (
        int(matched["id"]) if matched and matched.get("role") == Role.DATA_SUBJECT.value else None
    )
    row = await create(
        conn,
        request_type=request_type,
        channel=Channel.PUBLIC_FORM,
        request_text=request_text,
        submitted_contact=contact,
        submitted_name=name,
        subject_user_id=subject_id,
    )
    if subject_id is not None and matched is not None:
        await _issue_code(conn, row, to=str(matched.get("email") or matched.get("mobile")))
    return {"reference": row["reference"], "message": NEUTRAL_MESSAGE}


async def _issue_code(conn: Conn, row: Row, *, to: str) -> None:
    issued = await otp.issue(otp.Scope.RIGHTS_VERIFY, row["reference"])
    _dispatch("send_rights_verification_code", to, issued.code, row["reference"])
    await _record(conn, row, Event.RIGHTS_VERIFICATION_CODE_SENT, actor_user_id=None)


async def verify_public_code(conn: Conn, *, reference: str, code: str) -> dict[str, Any]:
    """The second half of the public form. One message for every failure."""
    row = await repo.by_reference(conn, reference.strip().upper())
    if not row or row["verification_status"] != "pending" or row["subject_user_id"] is None:
        # No code was ever issued for this reference. Same words as a wrong code:
        # distinguishing them would say whether the contact matched somebody.
        raise BadRequest("Invalid or expired code", code="otp_invalid", field="code")
    await otp.require(otp.Scope.RIGHTS_VERIFY, row["reference"], code)
    row = await _mark_verified(conn, row, method="code", actor_id=None, note=None)
    return {
        "ok": True,
        "reference": row["reference"],
        "message": (
            "Thank you, your identity is verified. You will hear from us by "
            f"{row['due_at'].date().isoformat()}."
        ),
    }


async def _mark_verified(
    conn: Conn, row: Row, *, method: str, actor_id: int | None, note: str | None
) -> Row:
    await repo.update(
        conn,
        int(row["request_id"]),
        verification_status="verified",
        verification_method=method,
        verified_at=datetime.now(UTC),
        verified_by=actor_id,
        verification_note=note,
    )
    row = await reload(conn, row)
    await _record(
        conn, row, Event.RIGHTS_VERIFIED, actor_user_id=actor_id, detail={"method": method}
    )
    return await acknowledge(conn, row, actor_id=actor_id)


# ------------------------------------------------------- staff: verification
async def send_verification_code(conn: Conn, row: Row, *, role: Role | str, actor_id: int) -> Row:
    """A code to the channel we already hold for her - never one she supplies now."""
    _may_act(row, role)
    _before_collation(row)
    if row["verification_status"] == "verified":
        raise Conflict("Identity is already verified", code="already_verified")
    if row["subject_user_id"] is None:
        raise ValidationFailed(
            "The contact matches nobody we hold records for, so there is no stored channel "
            "to send a code to. Verify manually with a reason, or close as not verified.",
            field="subject_user_id",
        )
    to = row.get("subject_email") or row.get("subject_mobile")
    if not to:
        raise ValidationFailed("The account has no contact channel on file")
    await _issue_code(conn, row, to=str(to))
    return await reload(conn, row)


async def confirm_verification_code(
    conn: Conn, row: Row, *, code: str, role: Role | str, actor_id: int
) -> Row:
    """The DPO enters a code she read back over the phone."""
    _may_act(row, role)
    _before_collation(row)
    if row["verification_status"] == "verified":
        raise Conflict("Identity is already verified", code="already_verified")
    await otp.require(otp.Scope.RIGHTS_VERIFY, row["reference"], code)
    return await _mark_verified(conn, row, method="code", actor_id=actor_id, note=None)


async def verify_manually(
    conn: Conn, row: Row, *, note: str, role: Role | str, actor_id: int
) -> Row:
    """Manual, with the reason recorded. The reason is the control."""
    _may_act(row, role)
    _before_collation(row)
    if not note.strip():
        raise ValidationFailed("Say how identity was established", field="note")
    if row["verification_status"] == "verified":
        raise Conflict("Identity is already verified", code="already_verified")
    return await _mark_verified(conn, row, method="manual", actor_id=actor_id, note=note.strip())


async def fail_verification(
    conn: Conn, row: Row, *, note: str | None, role: Role | str, actor_id: int | None
) -> Row:
    """No match, or verification not satisfied. Closed and audited.

    Nothing is confirmed either way to the requester: the message they get is
    neutral, and they may try again with a new request.
    """
    if actor_id is not None:
        _may_act(row, role)
    _before_collation(row)
    now = datetime.now(UTC)
    await repo.update(
        conn,
        int(row["request_id"]),
        verification_status="failed",
        verification_note=note,
        status=Status.CLOSED.value,
        outcome=Outcome.NOT_VERIFIED.value,
        closed_at=now,
    )
    row = await reload(conn, row)
    await _record(conn, row, Event.RIGHTS_VERIFICATION_FAILED, actor_user_id=actor_id)
    await _record(
        conn, row, Event.RIGHTS_CLOSED, actor_user_id=actor_id, detail={"outcome": "not_verified"}
    )
    contact = contact_for(row)
    if contact and row["channel"] != Channel.PUBLIC_FORM:
        _dispatch(
            "send_rights_closed",
            contact,
            row["reference"],
            "not_verified",
            "We could not verify the identity behind this request, so it has been closed. "
            "You may submit a new request at any time.",
        )
    return row


# ------------------------------------------------------ staff: classification
async def classify(
    conn: Conn,
    row: Row,
    *,
    request_type: Kind | str,
    note: str | None,
    role: Role | str,
    actor_id: int,
) -> Row:
    """Confirm what this is. The DPO can reclassify anything that arrived as free text.

    The clock is not restarted by a reclassification: it started when the
    request arrived, whatever it was called.
    """
    _may_act(row, role)
    _before_collation(row)
    kind = choice(Kind, request_type, field="request_type")
    cols: dict[str, Any] = {"classified_at": datetime.now(UTC), "classified_by": actor_id}
    if kind.value != row["request_type"]:
        cols["original_type"] = row["original_type"] or row["request_type"]
        cols["request_type"] = kind.value
    await repo.update(conn, int(row["request_id"]), **cols)
    row = await reload(conn, row)
    await _record(
        conn,
        row,
        Event.RIGHTS_CLASSIFIED,
        actor_user_id=actor_id,
        detail={"request_type": kind.value, "note": note},
    )
    return row


async def refuse(conn: Conn, row: Row, *, reason: str, role: Role | str, actor_id: int) -> Row:
    """Not a rights request, or refused. A refusal is still a response.

    Reason given in writing, plus the grievance route - the notification
    carries both, because a refusal without a route onward is a dead end the
    Act does not permit.
    """
    _may_act(row, role)
    _before_collation(row)
    if not reason.strip():
        raise ValidationFailed("A refusal needs its reason, in writing", field="reason")
    now = datetime.now(UTC)
    await repo.update(
        conn,
        int(row["request_id"]),
        status=Status.CLOSED.value,
        outcome=Outcome.REFUSED.value,
        refusal_reason=reason.strip(),
        response_text=reason.strip(),
        responded_at=now,
        responded_by=actor_id,
        closed_at=now,
    )
    row = await reload(conn, row)
    await _record(
        conn, row, Event.RIGHTS_CLOSED, actor_user_id=actor_id, detail={"outcome": "refused"}
    )
    contact = contact_for(row)
    if contact:
        _dispatch("send_rights_closed", contact, row["reference"], "refused", reason.strip())
    return row


async def reclassify_as_withdrawal(
    conn: Conn, row: Row, *, note: str | None, role: Role | str, actor_id: int
) -> Row:
    """She meant withdrawal.

    Different right, different outcome: withdrawal stops processing going
    forward and does not reach data already collected. Handled under s.6(4),
    from her own consent record, not under s.12(3) here.
    """
    _may_act(row, role)
    _before_collation(row)
    if row["request_type"] != Kind.ERASURE:
        raise Conflict("Only an erasure request can turn out to be a withdrawal")
    now = datetime.now(UTC)
    explanation = (
        "Withdrawing consent stops future processing for the purposes withdrawn. It does "
        "not delete data already collected - that is erasure, which is a separate request. "
        "You can withdraw from your consent record at any time; if you also want data "
        "erased, submit an erasure request and we will confirm which you mean."
    )
    await repo.update(
        conn,
        int(row["request_id"]),
        status=Status.CLOSED.value,
        outcome=Outcome.RECLASSIFIED_WITHDRAWAL.value,
        response_text=explanation,
        responded_at=now,
        responded_by=actor_id,
        closed_at=now,
    )
    row = await reload(conn, row)
    await _record(
        conn,
        row,
        Event.RIGHTS_CLOSED,
        actor_user_id=actor_id,
        detail={"outcome": "reclassified_withdrawal", "note": note},
    )
    contact = contact_for(row)
    if contact:
        _dispatch(
            "send_rights_closed", contact, row["reference"], "reclassified_withdrawal", explanation
        )
    return row


async def confirm_intent(conn: Conn, row: Row, *, role: Role | str, actor_id: int) -> Row:
    """Erasure, not withdrawal: the DPO confirms which she means before anything is deleted."""
    _may_act(row, role)
    _before_collation(row)
    if row["request_type"] != Kind.ERASURE:
        raise Conflict("Only an erasure request carries this confirmation")
    await repo.update(conn, int(row["request_id"]), intent_confirmed_at=datetime.now(UTC))
    row = await reload(conn, row)
    await _record(conn, row, Event.RIGHTS_INTENT_CONFIRMED, actor_user_id=actor_id)
    return row


async def record_event_evidence(
    conn: Conn, row: Row, *, evidenced: bool, note: str | None, role: Role | str, actor_id: int
) -> Row:
    """Is the triggering event - death or incapacity - evidenced to our standard?

    The Act gives no standard of proof, so ours has to be published and applied
    consistently; the note records how this case met it or did not. A refusal
    goes to the nominee with the reason. She is not contacted.
    """
    _may_act(row, role)
    _before_collation(row)
    if row["channel"] != Channel.NOMINEE:
        raise Conflict("Only a request made by a nominee carries a triggering event")
    if evidenced:
        await repo.update(conn, int(row["request_id"]), trigger_evidenced_at=datetime.now(UTC))
        row = await reload(conn, row)
        await _record(
            conn, row, Event.RIGHTS_EVENT_EVIDENCED, actor_user_id=actor_id, detail={"note": note}
        )
        return row
    return await refuse(
        conn,
        row,
        reason=(
            "The event that would let a nominee act - death or incapacity - is not "
            "evidenced to the standard we publish."
            + (f" {note.strip()}" if note and note.strip() else "")
        ),
        role=role,
        actor_id=actor_id,
    )


async def escalate(conn: Conn, row: Row, *, role: Role | str, actor_id: int) -> Row:
    """The complaint is about the DPO. Accountability cannot review itself.

    Marking it hands the request to the administrator's scope and locks the
    DPO out of deciding it. Who the independent reviewer should be is an open
    question for Legal; the administrator is the default because it is the one
    role that already supervises the platform and holds no project.
    """
    _may_act(row, role)
    _open(row)
    if row["request_type"] != Kind.GRIEVANCE:
        raise Conflict("Only a grievance can be escalated to an independent reviewer")
    await repo.update(
        conn, int(row["request_id"]), escalated_at=row["escalated_at"] or datetime.now(UTC)
    )
    await conn.execute(
        "UPDATE rights_request SET about_dpo = true WHERE request_id = %s", (row["request_id"],)
    )
    row = await reload(conn, row)
    await _record(conn, row, Event.RIGHTS_ESCALATED, actor_user_id=actor_id)
    return row


async def assign_reviewer(
    conn: Conn, row: Row, *, reviewer_uuid: str, role: Role | str, actor_id: int
) -> Row:
    """An administrator names the reviewer for a grievance about the DPO."""
    if Role(role) is not Role.ADMIN:
        raise Forbidden("Only an administrator assigns the independent reviewer")
    _open(row)
    if not row["about_dpo"]:
        raise Conflict("This grievance is not about the DPO, so the DPO reviews it")
    reviewer = await user_repo.by_uuid(conn, reviewer_uuid)
    if not reviewer or reviewer["status"] != "active":
        raise NotFound("User")
    if reviewer["role"] == Role.DPO.value:
        raise ValidationFailed(
            "The reviewer of a complaint about the DPO cannot be the DPO", field="reviewer_uuid"
        )
    if reviewer["role"] != Role.ADMIN.value:
        raise ValidationFailed(
            "Only an administrator can reach escalated grievances; choose one",
            field="reviewer_uuid",
        )
    await repo.update(
        conn,
        int(row["request_id"]),
        reviewer_user_id=reviewer["id"],
        escalated_at=row["escalated_at"] or datetime.now(UTC),
    )
    row = await reload(conn, row)
    await _record(
        conn,
        row,
        Event.RIGHTS_REVIEWER_ASSIGNED,
        actor_user_id=actor_id,
        detail={"reviewer": reviewer_uuid},
    )
    return row


# --------------------------------------------------------------- transitions
def transitions(row: Row, *, role: Role | str) -> list[dict[str, object]]:
    return sm.available(row["status"], role, facts_of(row))


async def transition(
    conn: Conn, row: Row, *, to: str, reason: str | None, role: Role | str, actor_id: int
) -> Row:
    """Move a request along the path. The state machine is the gate."""
    choice(Status, to, field="to")
    match = sm.validate(
        current=row["status"], target=to, role=role, facts=facts_of(row), reason=reason
    )
    if match.via == "respond":
        raise Conflict("Closure is made by responding, which records the outcome as well")
    await repo.update(conn, int(row["request_id"]), status=match.to.value)
    before = row["status"]
    row = await reload(conn, row)
    await _record(
        conn,
        row,
        Event.RIGHTS_STATUS_CHANGED,
        actor_user_id=actor_id,
        detail={"from": before, "to": match.to.value, "reason": reason},
    )
    return row


# ------------------------------------------------------------------- holders
async def derive_holders(conn: Conn, row: Row, *, role: Role | str, actor_id: int) -> list[Row]:
    """Who holds her data, from export_line and asset_consent. The DPO confirms."""
    _may_act(row, role)
    _open(row)
    if row["subject_user_id"] is None:
        raise ValidationFailed(
            "Holders are derived from the records we hold about a person, and this request "
            "is not linked to one. Verify identity first, or add holders by hand."
        )
    candidates = await repo.derive_holder_candidates(conn, int(row["subject_user_id"]))
    added = 0
    for c in candidates:
        result = await repo.add_holder(
            conn,
            int(row["request_id"]),
            processor_id=int(c["processor_id"]),
            label=str(c["legal_name"]),
            derived_from="export_line" if c["exports"] else "asset_consent",
            evidence={"exports": list(c["exports"]), "assets": list(c["assets"])},
        )
        if result.get("inserted"):
            added += 1
            # Who answers for this processor, if the registry knows. The DPO
            # can still pick another of its respondents when confirming.
            await _apply_respondent(conn, int(result["holder_id"]), int(c["processor_id"]))
    await _record(
        conn,
        row,
        Event.RIGHTS_HOLDERS_DERIVED,
        actor_user_id=actor_id,
        detail={"candidates": len(candidates), "added": added},
    )
    return await repo.holders_of(conn, int(row["request_id"]))


async def add_holder(
    conn: Conn,
    row: Row,
    *,
    label: str,
    processor_uuid: str | None,
    responder_name: str | None,
    responder_contact: str | None,
    role: Role | str,
    actor_id: int,
) -> Row:
    """What the records miss, added and confirmed in one step - the DPO is the source."""
    _may_act(row, role)
    _open(row)
    processor_id: int | None = None
    if processor_uuid:
        processor = await fetch_one(
            conn,
            "SELECT processor_id, legal_name FROM processor WHERE processor_uuid = %s",
            (processor_uuid,),
        )
        if not processor:
            raise NotFound("Processor")
        processor_id = int(processor["processor_id"])
        label = label.strip() or str(processor["legal_name"])
    if not label.strip():
        raise ValidationFailed("Name the holder", field="label")
    result = await repo.add_holder(
        conn,
        int(row["request_id"]),
        processor_id=processor_id,
        label=label.strip(),
        derived_from="manual",
        evidence={},
        responder_name=responder_name,
        responder_contact=responder_contact,
    )
    await repo.update_holder(
        conn, int(result["holder_id"]), confirmed_at=datetime.now(UTC), confirmed_by=actor_id
    )
    if processor_id is not None and not (responder_name or responder_contact):
        await _apply_respondent(conn, int(result["holder_id"]), processor_id)
    await _record(
        conn,
        row,
        Event.RIGHTS_HOLDER_ADDED,
        actor_user_id=actor_id,
        entity_type="rights_request_holder",
        entity_id=int(result["holder_id"]),
        detail={"label": label.strip()},
    )
    holder = await repo.holder_by_uuid(conn, int(row["request_id"]), str(result["holder_uuid"]))
    assert holder is not None
    return holder


async def confirm_holder(
    conn: Conn,
    row: Row,
    *,
    holder_uuid: str,
    responder_name: str | None,
    responder_contact: str | None,
    role: Role | str,
    actor_id: int,
    respondent_uuid: str | None = None,
) -> Row:
    _may_act(row, role)
    _open(row)
    holder = await repo.holder_by_uuid(conn, int(row["request_id"]), holder_uuid)
    if not holder:
        raise NotFound("Holder")
    cols: dict[str, Any] = {}
    if holder["confirmed_at"] is None:
        cols.update(confirmed_at=datetime.now(UTC), confirmed_by=actor_id)
    if respondent_uuid:
        # One of the processor's registered respondents, chosen by the DPO.
        # Decides the channel with it: an account answers on the portal.
        if holder["processor_id"] is None:
            raise ValidationFailed(
                "Only a registered processor has respondents to choose from", field="respondent"
            )
        chosen = await registry_repo.respondent_by_uuid(
            conn, int(holder["processor_id"]), respondent_uuid
        )
        if chosen is None:
            raise NotFound("Respondent")
        cols.update(_respondent_columns(chosen))
    else:
        if responder_name is not None:
            cols["responder_name"] = responder_name
        if responder_contact is not None:
            cols["responder_contact"] = responder_contact
        if (responder_name or responder_contact) and holder.get("channel") == "portal":
            # Typing over an account's details means: not the portal after all.
            cols.update(respondent_id=None, responder_user_id=None, channel="email")
    await repo.update_holder(conn, int(holder["holder_id"]), **cols)
    await _record(
        conn,
        row,
        Event.RIGHTS_HOLDER_CONFIRMED,
        actor_user_id=actor_id,
        entity_type="rights_request_holder",
        entity_id=int(holder["holder_id"]),
        detail={"label": holder["label"]},
    )
    fresh = await repo.holder_by_uuid(conn, int(row["request_id"]), holder_uuid)
    assert fresh is not None
    return fresh


def _default_instruction(row: Row) -> str:
    kind = Kind(row["request_type"])
    if kind is Kind.ERASURE:
        return (
            f"Erasure request {row['reference']}: erase the personal data you hold for the "
            "person named, or where an asset also holds other people, remove her from it "
            "and return evidence of what was removed and how. Confirm using the form provided."
        )
    if kind is Kind.CORRECTION:
        return (
            f"Correction request {row['reference']}: correct the personal data you hold for "
            "the person named as instructed, and confirm what was changed."
        )
    return (
        f"Access request {row['reference']}: return a summary of the personal data you hold "
        "for the person named, the processing you carry out on it, and anyone you have "
        "shared it with. Use the structured return form."
    )


async def issue_tickets(
    conn: Conn,
    row: Row,
    *,
    instruction: str | None,
    due_at: datetime | None,
    role: Role | str,
    actor_id: int,
) -> list[Row]:
    """One ticket per confirmed holder, with a named responder and an early date.

    The default due date is halfway through the period - early on purpose, so
    a holder that misses it can be escalated once and the response still go
    out on time. Issuing moves the request to awaiting holders.
    """
    _may_act(row, role)
    _open(row)
    if Status(row["status"]) not in (Status.IN_PROGRESS, Status.AWAITING_HOLDERS):
        raise Conflict("Tickets are issued once work has started and before collation")
    holders = await repo.holders_of(conn, int(row["request_id"]))
    to_issue = [
        h for h in holders if h["confirmed_at"] is not None and h["ticket_status"] == "pending"
    ]
    if not to_issue:
        raise Conflict(
            "No confirmed holder is waiting for a ticket. Confirm the holders first.",
            code="no_holders",
        )
    when = due_at or clock.compute(row["received_at"], row["due_at"]).halfway_at
    if when > row["due_at"]:
        raise ValidationFailed("A ticket cannot fall due after the response itself", field="due_at")
    text = (instruction or "").strip() or _default_instruction(row)
    now = datetime.now(UTC)
    for h in to_issue:
        await repo.update_holder(
            conn,
            int(h["holder_id"]),
            ticket_status=Ticket.ISSUED.value,
            instruction=text,
            issued_at=now,
            due_at=when,
        )
        await _record(
            conn,
            row,
            Event.RIGHTS_TICKET_ISSUED,
            actor_user_id=actor_id,
            entity_type="rights_request_holder",
            entity_id=int(h["holder_id"]),
            detail={"label": h["label"], "due_at": when.isoformat()},
        )
        await _deliver_ticket(
            conn, h, reference=str(row["reference"]), text=text, due=when, actor_id=actor_id
        )
    if row["status"] == Status.IN_PROGRESS:
        fresh = await reload(conn, row)
        await transition(
            conn,
            fresh,
            to=Status.AWAITING_HOLDERS.value,
            reason=None,
            role=role,
            actor_id=actor_id,
        )
    return await repo.holders_of(conn, int(row["request_id"]))


async def return_ticket(
    conn: Conn,
    row: Row,
    *,
    holder_uuid: str,
    summary: str,
    evidence_ref: str | None,
    evidence_hash: str | None,
    role: Role | str,
    actor_id: int,
) -> Row:
    """What came back: a confirmation of what was done and how - not an assurance."""
    _may_act(row, role)
    _open(row)
    holder = await repo.holder_by_uuid(conn, int(row["request_id"]), holder_uuid)
    if not holder:
        raise NotFound("Holder")
    if holder["ticket_status"] not in (Ticket.ISSUED, Ticket.ESCALATED):
        raise Conflict("This holder has no open ticket to return", code="ticket_not_open")
    if not summary.strip():
        raise ValidationFailed("Record what the holder returned", field="summary")
    await repo.update_holder(
        conn,
        int(holder["holder_id"]),
        ticket_status=Ticket.RETURNED.value,
        returned_at=datetime.now(UTC),
        return_summary=summary.strip(),
        return_evidence_ref=evidence_ref,
        return_evidence_hash=evidence_hash,
    )
    await _record(
        conn,
        row,
        Event.RIGHTS_TICKET_RETURNED,
        actor_user_id=actor_id,
        entity_type="rights_request_holder",
        entity_id=int(holder["holder_id"]),
        detail={"label": holder["label"], "evidence_sha256": evidence_hash},
    )
    fresh = await repo.holder_by_uuid(conn, int(row["request_id"]), holder_uuid)
    assert fresh is not None
    return fresh


async def escalate_ticket(
    conn: Conn, row: Row, *, holder_uuid: str, role: Role | str, actor_id: int
) -> Row:
    """A holder missed its date. Escalate once; the clock does not pause."""
    _may_act(row, role)
    _open(row)
    holder = await repo.holder_by_uuid(conn, int(row["request_id"]), holder_uuid)
    if not holder:
        raise NotFound("Holder")
    if holder["ticket_status"] != Ticket.ISSUED:
        raise Conflict(
            "Only an issued ticket can be escalated, and only once", code="ticket_not_open"
        )
    await repo.update_holder(
        conn,
        int(holder["holder_id"]),
        ticket_status=Ticket.ESCALATED.value,
        escalated_at=datetime.now(UTC),
    )
    await _record(
        conn,
        row,
        Event.RIGHTS_TICKET_ESCALATED,
        actor_user_id=actor_id,
        entity_type="rights_request_holder",
        entity_id=int(holder["holder_id"]),
        detail={"label": holder["label"]},
    )
    to = _ticket_address(holder)
    if to:
        _dispatch(
            "send_holder_instruction",
            to,
            row["reference"],
            str(holder["label"]),
            "ESCALATION - the date for this ticket has passed. " + str(holder["instruction"] or ""),
            (holder["due_at"] or datetime.now(UTC)).date().isoformat(),
        )
    await repo.append_contact(
        conn,
        int(holder["holder_id"]),
        _contact_entry("escalated", to=to, by=actor_id, note="Escalation sent" if to else None),
    )
    fresh = await repo.holder_by_uuid(conn, int(row["request_id"]), holder_uuid)
    assert fresh is not None
    return fresh


# ------------------------------------------------- respondents and channels
def _respondent_columns(rs: Row) -> dict[str, Any]:
    """The holder columns a chosen respondent sets. An account means the
    portal; a name and address mean email."""
    if rs.get("user_id"):
        return {
            "respondent_id": int(rs["respondent_id"]),
            "responder_user_id": int(rs["user_id"]),
            "responder_name": str(rs.get("user_name") or rs["name"]),
            "responder_contact": str(rs.get("user_email") or rs["contact"]),
            "channel": "portal",
        }
    return {
        "respondent_id": int(rs["respondent_id"]),
        "responder_user_id": None,
        "responder_name": str(rs["name"]),
        "responder_contact": str(rs["contact"]),
        "channel": "email",
    }


async def _apply_respondent(conn: Conn, holder_id: int, processor_id: int) -> None:
    """The processor's first respondent, where it has one. Nothing otherwise."""
    respondents = await registry_repo.respondents_of(conn, processor_id)
    if respondents:
        await repo.update_holder(conn, holder_id, **_respondent_columns(respondents[0]))


def _ticket_address(holder: Row) -> str | None:
    """Where a ticket's message goes. An account's own address on the portal
    channel - a courtesy copy; the ticket itself is in their console."""
    if holder.get("channel") == "portal":
        return (
            str(holder.get("responder_user_email") or holder.get("responder_contact") or "") or None
        )
    return str(holder.get("responder_contact") or "") or None


def _contact_entry(
    kind: str, *, to: str | None, by: int | None, note: str | None = None
) -> dict[str, Any]:
    return {
        "at": datetime.now(UTC).isoformat(),
        "kind": kind,
        "to": to,
        "by": by,
        "note": note,
    }


async def _deliver_ticket(
    conn: Conn, holder: Row, *, reference: str, text: str, due: datetime, actor_id: int
) -> None:
    """Send the instruction the way this holder is reached, and write down
    that it was sent. On the portal the ticket is in the team's console the
    moment it is issued; the message is a copy so they hear about it."""
    to = _ticket_address(holder)
    if to:
        _dispatch(
            "send_holder_instruction",
            to,
            reference,
            str(holder["label"]),
            text,
            due.date().isoformat(),
        )
    kind = "ticket_on_portal" if holder.get("channel") == "portal" else "mail_sent"
    await repo.append_contact(
        conn,
        int(holder["holder_id"]),
        _contact_entry(
            kind,
            to=to,
            by=actor_id,
            note="Instruction sent" if to else "No address on record - nothing was sent",
        ),
    )


CONTACT_KINDS: frozenset[str] = frozenset({"mail_sent", "chased", "reply_noted", "note"})


async def log_contact(
    conn: Conn,
    row: Row,
    *,
    holder_uuid: str,
    kind: str,
    note: str | None,
    send: bool,
    role: Role | str,
    actor_id: int,
) -> Row:
    """What passed between the Privacy Office and a holder reached by email.

    The mail itself lives in an inbox; this is the record on the request that
    it was sent, chased, or answered - so the trail is here and not in one
    person's mailbox. `send` re-sends the instruction to the address on record
    and logs that it did.
    """
    _may_act(row, role)
    _open(row)
    holder = await repo.holder_by_uuid(conn, int(row["request_id"]), holder_uuid)
    if not holder:
        raise NotFound("Holder")
    if kind not in CONTACT_KINDS:
        raise ValidationFailed("Say what kind of contact this was", field="kind")
    to: str | None = None
    if send:
        if holder.get("channel") == "portal":
            raise Conflict(
                "This holder answers on the portal; there is no mail to send", code="portal_holder"
            )
        to = _ticket_address(holder)
        if not to:
            raise ValidationFailed(
                "No address on record for this holder", field="responder_contact"
            )
        if not holder.get("issued_at"):
            raise Conflict("Issue the ticket first, then send or chase it", code="ticket_not_open")
        _dispatch(
            "send_holder_instruction",
            to,
            row["reference"],
            str(holder["label"]),
            str(holder.get("instruction") or _default_instruction(row)),
            (holder["due_at"] or datetime.now(UTC)).date().isoformat(),
        )
        kind = "mail_sent"
    await repo.append_contact(
        conn,
        int(holder["holder_id"]),
        _contact_entry(kind, to=to, by=actor_id, note=(note or "").strip() or None),
    )
    await _record(
        conn,
        row,
        Event.RIGHTS_HOLDER_CONTACTED,
        actor_user_id=actor_id,
        entity_type="rights_request_holder",
        entity_id=int(holder["holder_id"]),
        detail={"label": holder["label"], "kind": kind, "sent": bool(to)},
    )
    fresh = await repo.holder_by_uuid(conn, int(row["request_id"]), holder_uuid)
    assert fresh is not None
    return fresh


# ---------------------------------------------------- the respondent's side
async def tickets_for(conn: Conn, user_id: int) -> list[Row]:
    """The tickets addressed to this member of staff, open ones first."""
    return await repo.tickets_for_user(conn, user_id)


async def return_own_ticket(
    conn: Conn,
    *,
    user_id: int,
    holder_uuid: str,
    summary: str,
    evidence_ref: str | None,
    evidence_hash: str | None,
) -> Row:
    """A team returns its own ticket on the portal.

    The same record the DPO would write on their behalf, made by the person
    it was addressed to. Scope is the predicate: a ticket not addressed to
    this account is not found, not forbidden.
    """
    holder = await repo.ticket_for_user(conn, user_id, holder_uuid)
    if not holder:
        raise NotFound("Ticket")
    if holder["ticket_status"] not in (Ticket.ISSUED, Ticket.ESCALATED):
        raise Conflict("This ticket is not open", code="ticket_not_open")
    if not summary.strip():
        raise ValidationFailed("Say what was done", field="summary")
    row = await repo.by_id(conn, int(holder["request_id"]))
    assert row is not None
    await repo.update_holder(
        conn,
        int(holder["holder_id"]),
        ticket_status=Ticket.RETURNED.value,
        returned_at=datetime.now(UTC),
        return_summary=summary.strip(),
        return_evidence_ref=evidence_ref,
        return_evidence_hash=evidence_hash,
    )
    await repo.append_contact(
        conn,
        int(holder["holder_id"]),
        _contact_entry("returned_on_portal", to=None, by=user_id),
    )
    await _record(
        conn,
        row,
        Event.RIGHTS_TICKET_RETURNED,
        actor_user_id=user_id,
        entity_type="rights_request_holder",
        entity_id=int(holder["holder_id"]),
        detail={"label": holder["label"], "evidence_sha256": evidence_hash, "channel": "portal"},
    )
    fresh = await repo.ticket_for_user(conn, user_id, holder_uuid)
    assert fresh is not None
    return fresh


# --------------------------------------------------------------------- scope
async def derive_scope(conn: Conn, row: Row, *, role: Role | str, actor_id: int) -> list[Row]:
    """What can go, what must stay: every active appearance of her in an asset."""
    _may_act(row, role)
    _open(row)
    if row["request_type"] != Kind.ERASURE:
        raise Conflict("Only an erasure request has a scope to derive")
    if row["subject_user_id"] is None:
        raise ValidationFailed("The request is not linked to a person we hold records for")
    holders = await repo.holders_of(conn, int(row["request_id"]))
    holder_by_processor = {
        int(h["processor_id"]): int(h["holder_id"]) for h in holders if h["processor_id"]
    }
    candidates = await repo.derive_scope_candidates(conn, int(row["subject_user_id"]))
    added = 0
    for c in candidates:
        created = await repo.add_item(
            conn,
            int(row["request_id"]),
            asset_consent_id=int(c["asset_consent_id"]),
            holder_id=holder_by_processor.get(int(c["processor_id"]))
            if c["processor_id"]
            else None,
            other_subjects=int(c["other_subjects"]),
        )
        if created:
            added += 1
    await _record(
        conn,
        row,
        Event.RIGHTS_SCOPE_DERIVED,
        actor_user_id=actor_id,
        detail={"candidates": len(candidates), "added": added},
    )
    return await repo.items_of(conn, int(row["request_id"]))


async def decide_item(
    conn: Conn,
    row: Row,
    *,
    item_uuid: str,
    decision: Decision | str,
    basis: str,
    retain_until: date | None,
    holder_uuid: str | None,
    role: Role | str,
    actor_id: int,
) -> Row:
    """What happens to one appearance of her, and the legal basis for it.

    Decision D-09 is enforced here: an asset holding other people is never
    erased. It is redacted, or quarantined if removal cannot be assured.
    """
    _may_act(row, role)
    _open(row)
    decided = choice(Decision, decision, field="decision")
    item = await repo.item_by_uuid(conn, int(row["request_id"]), item_uuid)
    if not item:
        raise NotFound("Scope item")
    if item["state"] == ItemState.APPLIED:
        raise Conflict("This item has been applied; the decision stands", code="item_applied")
    if not basis.strip():
        raise ValidationFailed("State the basis for the decision", field="basis")
    if decided is Decision.ERASE and int(item["other_subjects"]) > 0:
        raise ValidationFailed(
            f"This asset also holds {item['other_subjects']} other "
            f"{'person' if int(item['other_subjects']) == 1 else 'people'}. Erasing it would "
            "destroy their validly given consent along with her contribution. Choose "
            "redaction, or quarantine if removal cannot be assured.",
            field="decision",
            code="asset_holds_others",
        )
    if decided is Decision.RETAIN:
        if retain_until is None:
            raise ValidationFailed("Say until when the data must be retained", field="retain_until")
        if retain_until <= datetime.now(UTC).date():
            raise ValidationFailed(
                "A retention floor in the past is not a floor", field="retain_until"
            )
    cols: dict[str, Any] = {
        "decision": decided.value,
        "basis": basis.strip(),
        "retain_until": retain_until if decided is Decision.RETAIN else None,
        "decided_at": datetime.now(UTC),
        "decided_by": actor_id,
        "state": ItemState.DECIDED.value,
    }
    if holder_uuid:
        holder = await repo.holder_by_uuid(conn, int(row["request_id"]), holder_uuid)
        if not holder:
            raise NotFound("Holder")
        cols["holder_id"] = int(holder["holder_id"])
    await repo.update_item(conn, int(item["item_id"]), **cols)
    await _record(
        conn,
        row,
        Event.RIGHTS_SCOPE_DECIDED,
        actor_user_id=actor_id,
        entity_type="rights_request_item",
        entity_id=int(item["item_id"]),
        detail={
            "asset": str(item["asset_uuid"]),
            "decision": decided.value,
            "retain_until": retain_until.isoformat() if retain_until else None,
        },
    )
    fresh = await repo.item_by_uuid(conn, int(row["request_id"]), item_uuid)
    assert fresh is not None
    return fresh


_DISPOSITION_FOR = {
    Decision.ERASE: Disposition.ERASED,
    Decision.REDACT: Disposition.REDACTED,
    Decision.QUARANTINE: Disposition.QUARANTINED,
    # A retained item is erased when its floor passes; applying it is that.
    Decision.RETAIN: Disposition.ERASED,
}


async def apply_item(
    conn: Conn, row: Row, *, item_uuid: str, role: Role | str, actor_id: int | None
) -> Row:
    """Set her junction row. The asset survives; her contribution is recorded gone.

    Erasure and redaction wait for the holder's confirmation where a holder is
    named - the platform records what happened, it does not delete files a lab
    holds. Quarantine is immediate: it is the platform's own flag, and it is
    what stops an asset being released while the DPO decides.
    """
    if actor_id is not None:
        _may_act(row, role)
    item = await repo.item_by_uuid(conn, int(row["request_id"]), item_uuid)
    if not item:
        raise NotFound("Scope item")
    if item["decision"] is None:
        raise Conflict("Decide the item before applying it", code="item_undecided")
    if item["state"] == ItemState.APPLIED:
        return item
    choice = Decision(item["decision"])
    if choice is Decision.RETAIN and (
        item["retain_until"] is None or item["retain_until"] > datetime.now(UTC).date()
    ):
        raise Conflict(
            f"Retained until {item['retain_until']}. The floor binds even against her request; "
            "it is applied when it passes.",
            code="retention_floor",
        )
    if (
        choice in (Decision.ERASE, Decision.REDACT)
        and item["holder_id"] is not None
        and item["holder_ticket_status"] != Ticket.RETURNED
    ):
        raise Conflict(
            f"{item['holder_label']} has not confirmed what was removed. Record the "
            "holder's return first - the platform records erasure, it does not perform it.",
            code="holder_not_confirmed",
        )
    disposition = _DISPOSITION_FOR[choice]
    changed = await repo.set_disposition(conn, int(item["asset_consent_id"]), disposition.value)
    await repo.update_item(
        conn,
        int(item["item_id"]),
        state=ItemState.APPLIED.value,
        applied_at=datetime.now(UTC),
    )
    await _record(
        conn,
        row,
        Event.RIGHTS_SCOPE_APPLIED,
        actor_user_id=actor_id,
        entity_type="rights_request_item",
        entity_id=int(item["item_id"]),
        detail={"asset": str(item["asset_uuid"]), "disposition": disposition.value},
    )
    if changed:
        await audit.record(
            conn,
            event=Event.ASSET_DISPOSITION_CHANGED,
            entity_type="asset_consent",
            entity_id=int(changed["asset_consent_id"]),
            subject_user_id=row.get("subject_user_id"),
            actor_user_id=actor_id,
            detail={
                "reference": row["reference"],
                "asset": str(item["asset_uuid"]),
                "disposition": disposition.value,
                "other_subjects_untouched": int(item["other_subjects"]),
            },
        )
    fresh = await repo.item_by_uuid(conn, int(row["request_id"]), item_uuid)
    assert fresh is not None
    return fresh


# ------------------------------------------------------------------ response
async def respond(
    conn: Conn,
    row: Row,
    *,
    outcome: Outcome | str,
    response_text: str,
    role: Role | str,
    actor_id: int,
) -> Row:
    """Release and close. Nothing releases automatically; the DPO signs off here.

    An access response is a file she downloads, authenticated and for a limited
    time, from her own dashboard - not an attachment. A holder that never
    returned its ticket is named in the response as the gap, and the outcome
    then has to say `partial`: an answer with a hole in it is still on time,
    and it must not call itself complete.
    """
    _may_act(row, role)
    result = choice(Outcome, outcome, field="outcome")
    if result not in (Outcome.COMPLETE, Outcome.PARTIAL, Outcome.NO_RECORDS):
        raise ValidationFailed(
            "A response is complete, partial, or reports no records", field="outcome"
        )
    if not response_text.strip():
        raise ValidationFailed("Write the response", field="response_text")
    sm.validate(current=row["status"], target=Status.CLOSED.value, role=role, facts=facts_of(row))
    holders = await repo.holders_of(conn, int(row["request_id"]))
    unreturned = [h for h in holders if h["ticket_status"] in (Ticket.ISSUED, Ticket.ESCALATED)]
    if unreturned and result is not Outcome.PARTIAL:
        raise ValidationFailed(
            "A holder has not returned its ticket: "
            + ", ".join(str(h["label"]) for h in unreturned)
            + ". The response can go out on time, but it is partial and the gap is named.",
            field="outcome",
            code="response_partial_required",
        )

    now = datetime.now(UTC)
    file_ref: str | None = None
    file_hash: str | None = None
    expires: datetime | None = None
    if row["request_type"] == Kind.ACCESS and result is not Outcome.NO_RECORDS:
        from cmp.core.security import file_hash as digest
        from cmp.domain.rights import package
        from cmp.infrastructure.storage.service import storage

        payload = await package.build_access_package(
            conn,
            row,
            holders=holders,
            response_text=response_text.strip(),
            generated_at=now,
        )
        file_hash = digest(payload)
        file_ref = storage().save(
            payload, subdir="responses", suggested_name=f"{row['reference']}.json"
        )
        expires = now + timedelta(days=settings.rights_download_ttl_days)

    gap = await repo.mark_unreturned(conn, int(row["request_id"]))
    await repo.update(
        conn,
        int(row["request_id"]),
        status=Status.CLOSED.value,
        outcome=result.value,
        response_text=response_text.strip(),
        response_file_ref=file_ref,
        response_file_hash=file_hash,
        responded_at=now,
        responded_by=actor_id,
        download_expires_at=expires,
        closed_at=now,
    )
    row = await reload(conn, row)
    await _record(
        conn,
        row,
        Event.RIGHTS_RESPONDED,
        actor_user_id=actor_id,
        detail={
            "outcome": result.value,
            "file_sha256": file_hash,
            "holders_unreturned": gap,
            "on_time": now <= row["due_at"],
        },
    )
    await _record(
        conn, row, Event.RIGHTS_CLOSED, actor_user_id=actor_id, detail={"outcome": result.value}
    )
    contact = contact_for(row)
    if contact:
        _dispatch(
            "send_rights_response_ready",
            contact,
            row["reference"],
            expires.date().isoformat() if expires else None,
        )
    return row


async def decide_grievance(
    conn: Conn,
    row: Row,
    *,
    upheld: bool,
    remedy_text: str | None,
    response_text: str,
    rerun: bool,
    role: Role | str,
    actor_id: int,
) -> dict[str, Any]:
    """Is it upheld? Either way, reasoned and in writing, with the Board route.

    Disagreement is not refusal: "not upheld" is a legitimate outcome and it
    carries the route to the Data Protection Board. Upheld means a remedy - and
    where the grievance was about a request, `rerun` re-opens that request as
    a new one linked to this decision, at no cost to her.
    """
    _may_act(row, role)
    _open(row)
    if row["request_type"] != Kind.GRIEVANCE:
        raise Conflict("Only a grievance is decided this way")
    if row["about_dpo"] and Role(role) is not Role.ADMIN:
        raise Forbidden("A complaint about the DPO is decided by the independent reviewer")
    if row["about_dpo"] and row["reviewer_user_id"] not in (None, actor_id):
        raise Forbidden("Another reviewer has been assigned to this grievance")
    if Status(row["status"]) is Status.RECEIVED:
        raise Conflict("Start the grievance before deciding it", code="request_not_started")
    if not response_text.strip():
        raise ValidationFailed("Write the decision", field="response_text")
    if upheld and not (remedy_text or "").strip():
        raise ValidationFailed("An upheld grievance names its remedy", field="remedy_text")

    now = datetime.now(UTC)
    result = Outcome.UPHELD if upheld else Outcome.NOT_UPHELD
    await repo.update(
        conn,
        int(row["request_id"]),
        grievance_upheld=upheld,
        remedy_text=(remedy_text or "").strip() or None,
        response_text=response_text.strip(),
        responded_at=now,
        responded_by=actor_id,
        status=Status.CLOSED.value,
        outcome=result.value,
        closed_at=now,
    )
    row = await reload(conn, row)
    await _record(
        conn,
        row,
        Event.RIGHTS_GRIEVANCE_DECIDED,
        actor_user_id=actor_id,
        detail={"upheld": upheld, "rerun": rerun},
    )
    await _record(
        conn, row, Event.RIGHTS_CLOSED, actor_user_id=actor_id, detail={"outcome": result.value}
    )

    rerun_row: Row | None = None
    if upheld and rerun and row["linked_request_id"]:
        original = await repo.by_id(conn, int(row["linked_request_id"]))
        if original:
            rerun_row = await create(
                conn,
                request_type=str(original["request_type"]),
                channel=Channel.STAFF_LOGGED,
                request_text=(
                    f"Re-run of {original['reference']}, ordered by grievance {row['reference']}. "
                    f"Original request: {original['request_text']}"
                ),
                submitted_contact=str(original["submitted_contact"]),
                submitted_name=original.get("submitted_name"),
                subject_user_id=original.get("subject_user_id"),
                actor_id=actor_id,
                verification_method="manual",
                verification_note=f"Identity carried over from {original['reference']}",
                linked_request_id=int(row["request_id"]),
            )
            await repo.update(
                conn, int(rerun_row["request_id"]), classified_at=now, classified_by=actor_id
            )
            rerun_row = await reload(conn, rerun_row)

    contact = contact_for(row)
    if contact:
        _dispatch(
            "send_rights_closed",
            contact,
            row["reference"],
            result.value,
            response_text.strip()
            + (f"\n\nRemedy: {(remedy_text or '').strip()}" if upheld else ""),
        )
    return {"request": row, "rerun": rerun_row}


async def download(
    conn: Conn, row: Row, *, actor_id: int | None, as_subject: bool
) -> tuple[bytes, str, str]:
    """The released response. Audited on every read - a download is a disclosure."""
    if not row.get("response_file_ref"):
        raise NotFound("Response file")
    if as_subject:
        expires = row.get("download_expires_at")
        if expires is None or expires < datetime.now(UTC):
            raise Conflict(
                "The download period for this response has passed. Ask the Privacy Office "
                "to release it again.",
                code="download_expired",
            )
    from cmp.infrastructure.storage.service import read_upload

    payload = read_upload(str(row["response_file_ref"]))
    await _record(
        conn,
        row,
        Event.RIGHTS_RESPONSE_DOWNLOADED,
        actor_user_id=actor_id,
        detail={"as_subject": as_subject},
    )
    return payload, f"{row['reference']}.json", str(row["response_file_hash"] or "")


async def dispute(conn: Conn, row: Row, *, subject_user_id: int, text: str, about_dpo: bool) -> Row:
    """She disputes the response: a grievance under s.13, linked to this request."""
    if row["subject_user_id"] != subject_user_id:
        raise NotFound("Rights request")
    if row["status"] != Status.CLOSED:
        raise Conflict("A response has not been given yet. A grievance follows a response.")
    if not text.strip():
        raise ValidationFailed("Say what was wrong with the handling", field="text")
    return await create(
        conn,
        request_type=Kind.GRIEVANCE,
        channel=Channel.PORTAL,
        request_text=text.strip(),
        submitted_contact=str(row["submitted_contact"]),
        submitted_name=row.get("subject_name"),
        subject_user_id=subject_user_id,
        actor_id=subject_user_id,
        verification_method="session",
        linked_request_id=int(row["request_id"]),
        about_dpo=about_dpo,
    )


# --------------------------------------------------------------- nominations
def nominee_url(nomination_uuid: str) -> str:
    """Where the nominee acts, with the reference already filled in."""
    return f"{settings.public_base_url.rstrip('/')}/rights/nominee?nomination={nomination_uuid}"


def _accept_url(raw_token: str) -> str:
    return f"{settings.public_base_url.rstrip('/')}/rights/nominations/{raw_token}"


async def nominate(
    conn: Conn,
    *,
    principal_user_id: int,
    nominee_name: str,
    nominee_mobile: str,
    rights: list[str],
    nominee_email: str | None = None,
) -> Row:
    """She names somebody, signed in. Pending until he accepts.

    One live nomination at a time - whether more than one should be allowed is
    an open question, and one nominee is the answer that cannot produce two
    people claiming the same standing. Partial scope is allowed: which of her
    rights he may exercise is her decision, per right.
    """
    wanted = sorted({choice(Kind, r, field="rights").value for r in rights})
    if not wanted:
        raise ValidationFailed("Choose at least one right the nominee may exercise", field="rights")
    mobile = normalise_mobile(nominee_mobile) if nominee_mobile else ""
    email = nominee_email.strip().lower() if nominee_email and nominee_email.strip() else None
    if not nominee_name.strip():
        raise ValidationFailed("The nominee needs a name", field="nominee_name")
    if not mobile:
        raise ValidationFailed("The nominee needs a mobile number", field="nominee_mobile")
    if await repo.live_nomination_of(conn, principal_user_id):
        raise Conflict(
            "You already have a nomination in place. Revoke it first to name somebody else.",
            code="nomination_exists",
        )
    principal = await user_repo.by_id(conn, principal_user_id)
    if not principal:
        raise NotFound("User")
    own = {
        str(principal["email"] or "").lower(),
        normalise_mobile(str(principal["mobile"] or "")),
    } - {""}
    if mobile in own or (email and email in own):
        raise ValidationFailed(
            "A nominee has to be somebody other than you", field="nominee_mobile"
        )

    raw = new_token()
    expires = datetime.now(UTC) + timedelta(days=settings.nomination_accept_ttl_days)
    created = await repo.create_nomination(
        conn,
        principal_user_id=principal_user_id,
        nominee_name=nominee_name.strip(),
        nominee_mobile=mobile,
        nominee_email=email,
        rights=wanted,
        accept_token_hash=token_fingerprint(raw),
        accept_expires_at=expires,
    )
    row = await repo.nomination_by_uuid(conn, str(created["nomination_uuid"]))
    assert row is not None
    await audit.record(
        conn,
        event=Event.NOMINATION_CREATED,
        entity_type="nomination",
        entity_id=int(row["nomination_id"]),
        subject_user_id=principal_user_id,
        actor_user_id=principal_user_id,
        detail={"rights": wanted, "expires_at": expires.isoformat()},
    )
    # The same single-use link to every contact she recorded: whichever he
    # opens, he then proves that contact before it counts.
    for contact in (mobile, email):
        if contact:
            _dispatch(
                "send_nomination_invitation",
                contact,
                str(principal["full_name"]),
                _accept_url(raw),
                expires.date().isoformat(),
            )
    return row


def nomination_mediums(row: Row) -> list[dict[str, str]]:
    """The recorded contacts, masked: what the acceptance page may show before
    anything is proven, and what the nominee chooses between for the code."""
    return [
        {"kind": kind, "masked": mask_contact(str(contact))}
        for kind, contact in (
            ("mobile", row.get("nominee_mobile")),
            ("email", row.get("nominee_email")),
        )
        if contact
    ]


def _recorded_contact(row: Row, typed: str) -> str | None:
    """The recorded contact the typed one matches, as recorded - or nothing."""
    wanted = normalise_contact(typed)
    mobile = row.get("nominee_mobile")
    if mobile and normalise_mobile(str(mobile)) == wanted:
        return str(mobile)
    email = row.get("nominee_email")
    if email and str(email).lower() == wanted:
        return str(email)
    return None


async def send_nomination_code(conn: Conn, raw_token: str, *, medium: str) -> dict[str, Any]:
    """A code to one of the contacts *she* recorded, chosen by the nominee.

    The link proves possession of the link. The code proves the person holding
    it is reachable at a contact the principal chose for them, which is what
    accepting - or declining - on that person's behalf has to rest on.
    """
    row = await nomination_from_token(conn, raw_token)
    contact = {"mobile": row.get("nominee_mobile"), "email": row.get("nominee_email")}.get(medium)
    if not contact:
        raise ValidationFailed(
            "Choose one of the contacts recorded on the nomination", field="medium"
        )
    await ratelimit.enforce(
        "nomination_code",
        str(row["nomination_uuid"]),
        limit=settings.otp_requests_per_contact_per_hour,
        window_s=3600,
        message="Too many code requests for this nomination. Try again later.",
    )
    issued = await otp.issue(otp.Scope.NOMINATION_ACCEPT, str(row["nomination_uuid"]))
    _dispatch("send_nomination_code", str(contact), issued.code)
    masked = mask_contact(str(contact))
    return {
        "ok": True,
        "to": str(contact),
        "masked": masked,
        "message": f"A code has been sent to {masked}.",
    }


async def nomination_from_token(conn: Conn, raw_token: str) -> Row:
    """The acceptance link, resolved. Every failure is the same 404."""
    row = await repo.nomination_by_token_hash(conn, token_fingerprint(raw_token))
    if (
        not row
        or row["status"] != NominationStatus.PENDING
        or row["accept_expires_at"] is None
        or row["accept_expires_at"] < datetime.now(UTC)
    ):
        raise NotFound("Nomination")
    return row


async def accept_nomination(conn: Conn, raw_token: str, *, code: str) -> Row:
    """He accepts. Now it is effective, and she can see that it is."""
    row = await nomination_from_token(conn, raw_token)
    # The link alone proves the link. The code proves a recorded contact.
    await otp.require(otp.Scope.NOMINATION_ACCEPT, str(row["nomination_uuid"]), code)
    await repo.update_nomination(
        conn,
        int(row["nomination_id"]),
        status=NominationStatus.ACTIVE.value,
        accepted_at=datetime.now(UTC),
        accept_token_hash=None,
    )
    await audit.record(
        conn,
        event=Event.NOMINATION_ACCEPTED,
        entity_type="nomination",
        entity_id=int(row["nomination_id"]),
        subject_user_id=int(row["principal_user_id"]),
        actor_user_id=None,
    )
    fresh = await repo.nomination_by_uuid(conn, str(row["nomination_uuid"]))
    assert fresh is not None
    # The reference and the page where he acts, to every contact recorded for
    # him. He will need them on a day that may be years off, and until this
    # was sent the reference existed nowhere he could see it: the nominee page
    # asked for it, he could not supply it, and the neutral reply then told
    # him nothing - which read as "the code never arrives".
    ref = str(fresh["nomination_uuid"])
    for contact in (fresh.get("nominee_mobile"), fresh.get("nominee_email")):
        if contact:
            _dispatch(
                "send_nomination_accepted",
                str(contact),
                str(fresh["principal_name"]),
                ref,
                nominee_url(ref),
            )
    return fresh


async def decline_nomination(conn: Conn, raw_token: str, *, code: str) -> Row:
    row = await nomination_from_token(conn, raw_token)
    # The link alone proves the link. The code proves a recorded contact.
    await otp.require(otp.Scope.NOMINATION_ACCEPT, str(row["nomination_uuid"]), code)
    await repo.update_nomination(
        conn,
        int(row["nomination_id"]),
        status=NominationStatus.DECLINED.value,
        declined_at=datetime.now(UTC),
        accept_token_hash=None,
    )
    await audit.record(
        conn,
        event=Event.NOMINATION_DECLINED,
        entity_type="nomination",
        entity_id=int(row["nomination_id"]),
        subject_user_id=int(row["principal_user_id"]),
        actor_user_id=None,
    )
    fresh = await repo.nomination_by_uuid(conn, str(row["nomination_uuid"]))
    assert fresh is not None
    return fresh


async def revoke_nomination(conn: Conn, *, nomination_uuid: str, principal_user_id: int) -> Row:
    """Revocable by her at any time. Revoking twice is a no-op, not an error."""
    row = await repo.nomination_by_uuid(conn, nomination_uuid)
    if not row or int(row["principal_user_id"]) != principal_user_id:
        raise NotFound("Nomination")
    if row["status"] in (NominationStatus.REVOKED, NominationStatus.DECLINED):
        return row
    await repo.update_nomination(
        conn,
        int(row["nomination_id"]),
        status=NominationStatus.REVOKED.value,
        revoked_at=datetime.now(UTC),
        accept_token_hash=None,
    )
    await audit.record(
        conn,
        event=Event.NOMINATION_REVOKED,
        entity_type="nomination",
        entity_id=int(row["nomination_id"]),
        subject_user_id=principal_user_id,
        actor_user_id=principal_user_id,
    )
    fresh = await repo.nomination_by_uuid(conn, nomination_uuid)
    assert fresh is not None
    return fresh


async def nominee_start(conn: Conn, *, nomination_uuid: str, contact: str) -> dict[str, Any]:
    """The nominee identifies himself. The code goes to the contact *she* recorded.

    Checked against what she recorded, not against what he now tells us: if
    the contact he types is not the one on the nomination, nothing is sent,
    and the reply does not say so.
    """
    await ratelimit.enforce(
        "nominee_start",
        nomination_uuid,
        limit=settings.otp_requests_per_contact_per_hour,
        window_s=3600,
    )
    row = await repo.nomination_by_uuid(conn, nomination_uuid)
    matched = (
        _recorded_contact(row, contact)
        if row and row["status"] == NominationStatus.ACTIVE
        else None
    )
    if matched:
        issued = await otp.issue(otp.Scope.NOMINEE_VERIFY, nomination_uuid)
        _dispatch(
            "send_rights_verification_code",
            matched,
            issued.code,
            f"nomination {nomination_uuid[:8]}",
        )
    return {
        "ok": True,
        "sent_to": matched,
        "message": (
            "If that nomination is in place and the contact matches the one recorded, a "
            "verification code has been sent to it."
        ),
    }


async def nominee_submit(
    conn: Conn,
    *,
    nomination_uuid: str,
    code: str,
    request_type: Kind | str,
    request_text: str,
    trigger_event: str,
    evidence_ref: str | None,
    evidence_hash: str | None,
) -> Row:
    """The nominee makes a request. It then runs as normal, and the DPO decides
    first whether the triggering event is evidenced."""
    row = await repo.nomination_by_uuid(conn, nomination_uuid)
    if not row or row["status"] != NominationStatus.ACTIVE:
        raise BadRequest("Invalid or expired code", code="otp_invalid", field="code")
    await otp.require(otp.Scope.NOMINEE_VERIFY, nomination_uuid, code)
    kind = choice(Kind, request_type, field="request_type")
    if kind.value not in list(row["rights"]):
        raise ValidationFailed(
            "That right was not included in the nomination", field="request_type"
        )
    if trigger_event not in ("death", "incapacity"):
        raise ValidationFailed(
            "Say whether the event is death or incapacity", field="trigger_event"
        )
    created = await create(
        conn,
        request_type=kind,
        channel=Channel.NOMINEE,
        request_text=request_text,
        submitted_contact=str(row["nominee_mobile"] or row["nominee_email"]),
        submitted_name=str(row["nominee_name"]),
        subject_user_id=int(row["principal_user_id"]),
        verification_method="code",
        nomination_id=int(row["nomination_id"]),
        trigger_event=trigger_event,
        trigger_evidence_ref=evidence_ref,
        trigger_evidence_hash=evidence_hash,
    )
    await audit.record(
        conn,
        event=Event.NOMINATION_INVOKED,
        entity_type="nomination",
        entity_id=int(row["nomination_id"]),
        subject_user_id=int(row["principal_user_id"]),
        actor_user_id=None,
        detail={
            "reference": created["reference"],
            "request_type": kind.value,
            "event": trigger_event,
        },
    )
    return created


# --------------------------------------------------------------------- sweep
async def sweep(conn: Conn, *, today: date | None = None) -> dict[str, int]:
    """The daily pass: close what never verified, and note floors that have passed.

    Idempotent. Both queries select only what has not been handled, so a task
    redelivered by Celery does the same work twice and changes nothing the
    second time.
    """
    day = today or datetime.now(UTC).date()
    closed = 0
    for row in await repo.unverified_public_older_than(conn, settings.rights_unverified_close_days):
        await fail_verification(
            conn,
            row,
            note=f"No verification within {settings.rights_unverified_close_days} days of receipt",
            role=Role.DPO,
            actor_id=None,
        )
        closed += 1
    floors = 0
    for item in await repo.retained_items_past_floor(conn, day):
        await repo.update_item(conn, int(item["item_id"]), floor_passed_at=datetime.now(UTC))
        request = await repo.by_id(conn, int(item["request_id"]))
        if request:
            await _record(
                conn,
                request,
                Event.RIGHTS_FLOOR_PASSED,
                actor_user_id=None,
                entity_type="rights_request_item",
                entity_id=int(item["item_id"]),
                detail={
                    "asset": str(item["asset_uuid"]),
                    "retain_until": str(item["retain_until"]),
                },
            )
        floors += 1
    log.info("rights.sweep", closed_unverified=closed, floors_passed=floors)
    return {"closed_unverified": closed, "floors_passed": floors}
