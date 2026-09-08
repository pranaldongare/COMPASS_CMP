"""Public information, and the rights entry points that need no account.

Separate from the consent flow because the audience is different. The flow is
walked once by somebody standing at a collection site with a link in their hand;
these are for somebody who has *lost* the link, or who wants to check what a
notice said months later, or who is deciding whether to complain - and, since
the rights module, for somebody making a request who never signs in.

Three properties hold across every route here:

* **Unauthenticated, and rate limited per address and per contact.**
* **No individual is revealed.** The request form answers with one neutral
  sentence whether or not the contact matches anyone we hold records for; the
  verification step answers "invalid or expired code" whether the code was
  wrong or never issued. Rule 3 puts the grievance route and the Board link in
  every notice, so these forms have an entry point even for someone who never
  had an account.
* **Capability tokens never reach a log.** A nomination's acceptance link is
  scrubbed by the access-log middleware like a consent link is.

Rule 9 and Rule 14(1). The Board complaint route is stated alongside the internal
grievance process, never instead of it: telling somebody only about the internal
route misstates the remedy available to them.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, File, Form, Request, Response, UploadFile, status
from pydantic import Field

from cmp.auth.rate_limit import service as ratelimit
from cmp.core.config import settings
from cmp.core.errors import NotFound
from cmp.core.security import file_hash
from cmp.db.pool import connection, transaction
from cmp.db.repositories import notices as notice_repo
from cmp.domain.rights import service as rights_service
from cmp.infrastructure.storage.service import storage
from cmp.schemas.common import Acknowledged, LongText, OtpCode, Out, Schema, ShortText
from cmp.validation.contacts import Contact
from cmp.validation.files import EVIDENCE, check_upload

router = APIRouter(tags=["public information"])


def _no_referrer(response: Response) -> None:
    """Keep a notice URL out of the next site's referrer header.

    A data subject who follows a link off the notice page should not hand the
    destination a URL saying which project they were reading about.
    """
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"


def _address(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("/notice/{notice_uuid}", summary="Public notice viewer")
async def public_notice(
    notice_uuid: UUID, response: Response, language_code: str = "english"
) -> dict[str, Any]:
    """A published notice is a public document. Drafts are not visible here."""
    _no_referrer(response)
    async with connection() as conn:
        from cmp.db.sql import fetch_one

        notice = await fetch_one(
            conn,
            """SELECT n.notice_id, n.notice_uuid, n.notice_code, n.version, n.status,
                      n.withdraw_url, n.exercise_rights_url, n.board_complaint_url,
                      n.dpo_contact, n.recipients_text, n.published_at,
                      p.project_name
               FROM notice n JOIN project p ON p.project_id = n.project_id
               WHERE n.notice_uuid = %s AND n.status IN ('published','superseded')""",
            (str(notice_uuid),),
        )
        if not notice:
            raise NotFound("Notice")

        language = await notice_repo.language_row(
            conn, notice_id=notice["notice_id"], language_code=language_code
        )
        languages = await notice_repo.languages_of(conn, notice["notice_id"])
        purposes = await notice_repo.purposes_of(conn, notice["notice_id"])

    notice.pop("notice_id")
    return {
        "notice": notice,
        "language_code": language["language_code"] if language else None,
        "rendered_text": language["rendered_text"] if language else None,
        "content_hash": language["content_hash"] if language else None,
        "available_languages": [
            x["language_code"] for x in languages if x["approved_at"] is not None
        ],
        "purposes": [
            {
                "name": p["name"],
                "description": p["description"],
                "uses": p["uses"],
                "lawful_basis": p["lawful_basis"],
                "data_categories": p["data_categories"],
                "retention_period": str(p["retention_period"]),
            }
            for p in purposes
        ],
        "superseded": notice["status"] == "superseded",
    }


@router.get("/rights", summary="How to make a rights request - Rule 9, Rule 14(1)")
async def rights(response: Response) -> dict[str, Any]:
    """Published so a data subject who has lost her notice can still find us.

    The Board complaint route is stated alongside ours, not instead of it: telling
    someone only about the internal grievance process misstates the remedy
    available to her.
    """
    _no_referrer(response)
    period = settings.rights_response_period_days
    grievance_period = settings.grievance_response_period_days
    return {
        "dpo_contact": settings.notification_email_from,
        "how_to_exercise": [
            {
                "right": "Access",
                "section": "s.11",
                "description": (
                    "A summary of your personal data being processed, the "
                    "processing activities, and the identities of anyone it has "
                    "been shared with."
                ),
            },
            {
                "right": "Correction and erasure",
                "section": "s.12",
                "description": (
                    "Correction of inaccurate data, completion of incomplete data, "
                    "and erasure where the purpose is served or consent is withdrawn."
                ),
            },
            {
                "right": "Grievance redressal",
                "section": "s.13",
                "description": "Raise a grievance with us before approaching the Board.",
            },
            {
                "right": "Nominate",
                "section": "s.14",
                "description": (
                    "Nominate someone to exercise these rights on your behalf in "
                    "the event of death or incapacity."
                ),
            },
        ],
        "withdraw_consent": (
            "Sign in with the email or mobile you registered, open the consent "
            "record, and withdraw it in whole or per purpose. Withdrawal is as "
            "easy as giving consent was."
        ),
        "response_period_days": period,
        "grievance_period_days": grievance_period,
        "response_time": (
            f"We respond to a request within {period} days of receiving it, and to a "
            f"grievance within {grievance_period} days. The clock starts when the "
            "request reaches us, not when we finish confirming who sent it."
        ),
        "board_complaint": (
            "If you are not satisfied with our response you may complain to the "
            "Data Protection Board of India. The route to the Board is independent "
            "of our grievance process."
        ),
    }


# ------------------------------------------------------------ the request form
class PublicRequestIn(Schema):
    """From the notice link. Nothing here identifies anyone to the caller."""

    request_type: str
    contact: Contact
    name: ShortText | None = None
    request_text: LongText


class PublicRequestOut(Out):
    reference: str
    message: str


class PublicVerifyIn(Schema):
    reference: Annotated[str, Field(min_length=6, max_length=24)]
    code: OtpCode


class PublicVerifyOut(Out):
    ok: bool
    reference: str
    message: str


@router.post(
    "/rights/requests",
    response_model=PublicRequestOut,
    status_code=status.HTTP_201_CREATED,
    summary="Make a request without an account",
)
async def public_request(
    body: PublicRequestIn, request: Request, response: Response
) -> dict[str, Any]:
    """Recorded either way. A code goes to the channel we already hold - if we hold one."""
    _no_referrer(response)
    if body.request_type not in ("access", "correction", "erasure", "grievance"):
        from cmp.core.errors import ValidationFailed

        raise ValidationFailed(
            "Choose access, correction, erasure or grievance", field="request_type"
        )
    async with transaction() as conn:
        return await rights_service.submit_public(
            conn,
            request_type=body.request_type,
            contact=body.contact,
            name=body.name,
            request_text=body.request_text,
            ip_address=_address(request),
        )


@router.post("/rights/requests/verify", response_model=PublicVerifyOut, summary="Confirm the code")
async def public_verify(
    body: PublicVerifyIn, request: Request, response: Response
) -> dict[str, Any]:
    _no_referrer(response)
    await ratelimit.enforce(
        "rights_verify_ip", _address(request), limit=30, window_s=3600, fail_open=True
    )
    async with transaction() as conn:
        return await rights_service.verify_public_code(
            conn, reference=body.reference, code=body.code
        )


# -------------------------------------------------------------- nominations
class NominationView(Out):
    #: The reference the nominee will need to act, shown to him on acceptance.
    #: Alone it authorises nothing: acting still needs a code sent to a
    #: contact she recorded.
    nomination_uuid: UUID
    principal_name: str
    nominee_name: str
    rights: list[str]
    accept_expires_at: Any
    #: The recorded contacts, masked - the nominee chooses where the code goes.
    mediums: list[dict[str, str]]


class NominationCodeIn(Schema):
    medium: str


class NominationActIn(Schema):
    code: OtpCode


@router.get(
    "/rights/nominations/{token}", response_model=NominationView, summary="The acceptance link"
)
async def nomination_view(token: str, request: Request, response: Response) -> dict[str, Any]:
    """What he is being asked to accept. Every failure is the same 404."""
    _no_referrer(response)
    await ratelimit.enforce("nomination_view_ip", _address(request), limit=60, window_s=60)
    async with connection() as conn:
        row = await rights_service.nomination_from_token(conn, token)
    return {**row, "mediums": rights_service.nomination_mediums(row)}


@router.post(
    "/rights/nominations/{token}/code",
    response_model=Acknowledged,
    summary="A code to one of the contacts recorded on the nomination",
)
async def nomination_code(
    token: str, body: NominationCodeIn, request: Request, response: Response
) -> dict[str, Any]:
    _no_referrer(response)
    await ratelimit.enforce("nomination_act_ip", _address(request), limit=20, window_s=3600)
    async with connection() as conn:
        result = await rights_service.send_nomination_code(conn, token, medium=body.medium)
    return {"ok": True, "message": result["message"]}


@router.post(
    "/rights/nominations/{token}/accept", response_model=Acknowledged, summary="Accept a nomination"
)
async def nomination_accept(
    token: str, body: NominationActIn, request: Request, response: Response
) -> dict[str, Any]:
    _no_referrer(response)
    await ratelimit.enforce("nomination_act_ip", _address(request), limit=20, window_s=3600)
    async with transaction() as conn:
        row = await rights_service.accept_nomination(conn, token, code=body.code)
    return {
        "ok": True,
        "message": (
            f"You are now {row['principal_name']}'s nominee. Nothing happens until the event "
            "she named - death or incapacity - and you will need to evidence it when it does. "
            f"Your nomination reference is {row['nomination_uuid']}; it has also been sent to "
            "the contacts recorded for you, with the page where you act. There is no account "
            "to sign in to."
        ),
    }


@router.post(
    "/rights/nominations/{token}/decline",
    response_model=Acknowledged,
    summary="Decline a nomination",
)
async def nomination_decline(
    token: str, body: NominationActIn, request: Request, response: Response
) -> dict[str, Any]:
    _no_referrer(response)
    await ratelimit.enforce("nomination_act_ip", _address(request), limit=20, window_s=3600)
    async with transaction() as conn:
        await rights_service.decline_nomination(conn, token, code=body.code)
    return {
        "ok": True,
        "message": "Declined. The person who nominated you will see that it is not usable.",
    }


class NomineeStartIn(Schema):
    nomination_uuid: UUID
    contact: Contact


@router.post(
    "/rights/nominee/start", response_model=Acknowledged, summary="A nominee identifies himself"
)
async def nominee_start(
    body: NomineeStartIn, request: Request, response: Response
) -> dict[str, Any]:
    """The code goes to the contact *she* recorded, not the one he types now."""
    _no_referrer(response)
    await ratelimit.enforce("nominee_start_ip", _address(request), limit=20, window_s=3600)
    async with connection() as conn:
        result = await rights_service.nominee_start(
            conn, nomination_uuid=str(body.nomination_uuid), contact=body.contact
        )
    return {"ok": True, "message": result["message"]}


class NomineeRequestOut(Out):
    reference: str
    message: str


@router.post(
    "/rights/nominee/requests",
    response_model=NomineeRequestOut,
    status_code=status.HTTP_201_CREATED,
    summary="A nominee makes a request on her behalf",
)
async def nominee_request(
    request: Request,
    response: Response,
    nomination_uuid: Annotated[UUID, Form()],
    code: Annotated[str, Form(min_length=4, max_length=10)],
    request_type: Annotated[str, Form()],
    request_text: Annotated[str, Form(min_length=1, max_length=20_000)],
    trigger_event: Annotated[str, Form()],
    evidence: Annotated[
        UploadFile | None, File(description="Evidence of death or incapacity")
    ] = None,
) -> dict[str, Any]:
    """Runs as normal once the DPO has decided the event is evidenced."""
    _no_referrer(response)
    await ratelimit.enforce("nominee_request_ip", _address(request), limit=10, window_s=3600)
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
        row = await rights_service.nominee_submit(
            conn,
            nomination_uuid=str(nomination_uuid),
            code=code,
            request_type=request_type,
            request_text=request_text,
            trigger_event=trigger_event,
            evidence_ref=evidence_ref,
            evidence_hash=evidence_hash,
        )
    return {
        "reference": row["reference"],
        "message": (
            f"Recorded as {row['reference']}. The Privacy Office will first decide whether "
            "the event is evidenced, then handle the request as normal and respond to you."
        ),
    }
