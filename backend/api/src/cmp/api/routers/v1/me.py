"""Data subject - /me. 12 endpoints.

Everything here is scoped to the caller by the query, not by a check after the
fact. There is no path by which a data subject reads another subject's record,
because no query here accepts a subject identifier.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import Field

from cmp.api.dependencies import CurrentUser, RequireDataSubject
from cmp.auth.authentication import service as auth_service
from cmp.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from cmp.db.pool import connection, transaction
from cmp.db.repositories import audit as audit_repo
from cmp.db.repositories import consent as consent_repo
from cmp.db.repositories import entities as entity_repo
from cmp.db.repositories import exchange as exchange_repo
from cmp.db.repositories import users as user_repo
from cmp.db.sql import unique_violation
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.domain.consent import service as consent_service
from cmp.infrastructure.dkms.blind import index_of
from cmp.schemas.common import Acknowledged, Mobile, OtpCode, Out, Schema, ShortText
from cmp.validation import Email, normalise_mobile

router = APIRouter(prefix="/me", tags=["me"])


class MeProfile(Out):
    uuid: UUID
    full_name: str
    #: None for a data principal who registered with a mobile alone.
    email: str | None
    mobile: str | None
    organization_id: str | None
    person_type: str | None
    status: str
    #: A string, not a date: it is served as stored, and it is stored sealed.
    #: The portal opens it. `is_minor` is the answer the server can still give.
    dob: str | None
    #: Derived by the database from `minor_until`, so every reader gets the same
    #: answer on the same day. `None` means the date of birth is unknown - which
    #: is not the same as adult, and must not be rendered as one.
    is_minor: bool | None
    created_at: Any
    #: A second address she added herself. Signs her in once confirmed - the
    #: way an ex-employee still reaches their own consents after the corporate
    #: mailbox is gone.
    secondary_email: str | None
    mobile_verified_at: datetime | None
    email_verified_at: datetime | None
    secondary_email_verified_at: datetime | None


class UpdateMe(Schema):
    full_name: ShortText | None = None
    #: A new or changed mobile is unconfirmed until a code sent to it comes
    #: back; the code goes out as part of this request.
    mobile: Mobile | None = None
    #: Set or replace the second address. Removing it is `DELETE /me/secondary-email`.
    secondary_email: Email | None = None
    #: Editable because accounts created through a consent link never had one
    #: asked for, and the alternative is a data principal who cannot correct a
    #: field that decides whether section 9 applies to them.
    dob: date | None = None


class PersonTypeChange(Schema):
    person_type: str
    reason: Annotated[str | None, Field(default=None, max_length=500)] = None


class ContactVerify(Schema):
    contact: Annotated[str, Field(min_length=3, max_length=255)]
    code: OtpCode


class ContactCodeRequest(Schema):
    #: One of the contacts on the caller's own account. Anything else is refused,
    #: so this cannot be used to send codes to a stranger.
    contact: Annotated[str, Field(min_length=3, max_length=255)]


class ConsentSummary(Out):
    consent_uuid: UUID
    project_uuid: UUID
    project_name: str
    notice_uuid: UUID
    notice_code: str
    version: int
    language_code: str
    affirmative_action_at: Any
    is_withdrawal: bool
    granted_count: int
    purpose_count: int


class WithdrawRequest(Schema):
    purposes: list[UUID] | None = None
    all: bool = False


# The person's own row and contacts admit every full session, whichever hat it
# wears. A member of staff on the console is the same data principal as on the
# portal (ADR 0013), and a mobile or a personal address is theirs to add and
# confirm from either. Everything below that is about *being* a data principal
# - consents, requests, disclosures, notifications - stays `RequireDataSubject`.
@router.get("", response_model=MeProfile)
async def get_me(principal: CurrentUser) -> dict[str, Any]:
    async with connection() as conn:
        user = await user_repo.by_id(conn, principal.user_id)
        if not user:
            raise NotFound("Account")
        return user


@router.patch("", response_model=MeProfile)
async def update_me(body: UpdateMe, principal: CurrentUser) -> dict[str, Any]:
    """Her own details. A contact she gives here is sent a code in the same
    request, and cannot sign her in until it comes back."""
    async with transaction() as conn:
        before = await user_repo.by_id(conn, principal.user_id)
        if not before:
            raise NotFound("Account")
        try:
            updated = await user_repo.update_profile(
                conn,
                principal.user_id,
                full_name=body.full_name,
                mobile=body.mobile,
                organization_id=None,
                dob=body.dob.isoformat() if body.dob else None,
            )
        except Exception as exc:
            if unique_violation(exc):
                raise Conflict(
                    "That mobile belongs to another account", code="contact_taken"
                ) from exc
            raise

        # A code goes out whenever she gives a mobile that is still unconfirmed
        # afterwards - not only when the digits changed.
        #
        # Keying this on "changed" made the commonest case silent. An account
        # often already carries an unconfirmed number: an administrator set it
        # on the register, or she typed it and never answered the code. She
        # opens the account page, and the edit box is pre-filled with that very
        # number - so the natural act, opening it and pressing save, changed
        # nothing, sent nothing, and left her at a code box waiting for a
        # message that was never going to arrive.
        #
        # A number already confirmed is left alone: re-sending would unconfirm
        # a contact that has already proved itself.
        if body.mobile is not None and updated.get("mobile_verified_at") is None:
            if index_of("mobile", normalise_mobile(body.mobile)) != (
                before.get("mobile_hash") or None
            ):
                await audit.record(
                    conn,
                    event=Event.USER_CONTACT_CHANGED,
                    entity_type="auth_user",
                    entity_id=principal.user_id,
                    subject_user_id=principal.user_id,
                    detail={"medium": "mobile", "action": "set"},
                )
            await auth_service.request_contact_code(conn, user=updated, contact=str(body.mobile))
        if body.secondary_email is not None:
            updated = await auth_service.add_secondary_email(
                conn, user=updated, email=str(body.secondary_email)
            )
        await audit.record(
            conn,
            event=Event.USER_UPDATED,
            entity_type="auth_user",
            entity_id=principal.user_id,
            subject_user_id=principal.user_id,
            detail={"self_service": True},
        )
    return updated


@router.post(
    "/contacts/code",
    response_model=Acknowledged,
    summary="A code to confirm one of my contacts",
)
async def contact_code(body: ContactCodeRequest, principal: CurrentUser) -> dict[str, Any]:
    async with transaction() as conn:
        user = await user_repo.by_id(conn, principal.user_id)
        if not user:
            raise NotFound("Account")
        await auth_service.request_contact_code(conn, user=user, contact=body.contact)
    return {"ok": True, "message": "A code is on its way."}


@router.post("/contact/verify", response_model=Acknowledged, summary="Confirm one of my contacts")
async def verify_contact(body: ContactVerify, principal: CurrentUser) -> dict[str, Any]:
    """The code came back, so the contact is hers and may now sign her in."""
    async with transaction() as conn:
        user = await user_repo.by_id(conn, principal.user_id)
        if not user:
            raise NotFound("Account")
        await auth_service.confirm_contact(conn, user=user, contact=body.contact, code=body.code)
    return {"ok": True, "message": "Contact confirmed."}


@router.delete("/secondary-email", response_model=Acknowledged, summary="Remove my second address")
async def remove_secondary_email(principal: CurrentUser) -> dict[str, Any]:
    async with transaction() as conn:
        user = await user_repo.by_id(conn, principal.user_id)
        if not user:
            raise NotFound("Account")
        await auth_service.remove_secondary_email(conn, user=user)
    return {"ok": True, "message": "Second address removed."}


@router.post("/person-type", response_model=Acknowledged)
async def change_person_type(body: PersonTypeChange, principal: CurrentUser) -> dict[str, Any]:
    """`role` is authorisation, `person_type` is identity.

    They are separate columns because a DPO is *also* an employee. A type change
    must never alter permissions, and this endpoint does not touch `role`.
    """
    from cmp.core.permissions import Role

    valid = {"external", "employee", "ex_employee", "vendor"}
    if body.person_type not in valid:
        raise ValidationFailed("Unknown person type", field="person_type")

    if principal.role not in (Role.DATA_SUBJECT, Role.DPO, Role.ADMIN):
        raise Forbidden("Your role does not permit this action")

    async with transaction() as conn:
        user = await user_repo.by_id(conn, principal.user_id)
        if not user:
            raise NotFound("Account")

        await user_repo.set_person_type(conn, principal.user_id, body.person_type)
        await user_repo.record_person_type_change(
            conn,
            user_id=principal.user_id,
            from_type=user["person_type"],
            to_type=body.person_type,
            reason=body.reason,
            changed_by=principal.user_id,
        )
        await audit.record(
            conn,
            event=Event.USER_PERSON_TYPE_CHANGED,
            entity_type="person_type_history",
            entity_id=principal.user_id,
            subject_user_id=principal.user_id,
            detail={"from": user["person_type"], "to": body.person_type},
        )
    return {"ok": True, "message": "Person type updated. Your permissions are unchanged."}


@router.get("/consents", response_model=list[ConsentSummary])
async def my_consents(principal: RequireDataSubject) -> list[dict[str, Any]]:
    async with connection() as conn:
        return await consent_repo.consents_of_user(conn, principal.user_id)


async def _own_consent(conn: Any, consent_uuid: str, user_id: int) -> dict[str, Any]:
    artefact = await consent_repo.artefact_by_uuid(conn, consent_uuid)
    if not artefact or artefact["auth_user_id"] != user_id:
        # Scope enforced by the ownership test, surfaced as 404.
        raise NotFound("Consent record")
    return artefact


@router.get("/consents/{consent_uuid}")
async def my_consent(consent_uuid: UUID, principal: RequireDataSubject) -> dict[str, Any]:
    async with connection() as conn:
        artefact = await _own_consent(conn, str(consent_uuid), principal.user_id)
        grants = await consent_repo.grants_of(conn, artefact["consent_id"])
        return {
            "consent_uuid": artefact["consent_uuid"],
            "project_name": artefact["project_name"],
            "notice_code": artefact["notice_code"],
            "version": artefact["version"],
            "language_code": artefact["language_code"],
            "site_label": artefact["site_label"],
            "served_at": artefact["served_at"],
            "affirmative_action_at": artefact["affirmative_action_at"],
            "action_type": artefact["action_type"],
            "is_withdrawal": artefact["is_withdrawal"],
            "notice_content_hash": artefact["notice_content_hash"],
            "grants": grants,
        }


@router.get("/consents/{consent_uuid}/notice", summary="The words she actually saw")
async def my_consent_notice(consent_uuid: UUID, principal: RequireDataSubject) -> dict[str, Any]:
    """Reads the copied `notice_content_hash`, not the live notice.

    Joining live to notice_language would let a later correction silently
    repoint her record at words she never saw.
    """
    async with connection() as conn:
        artefact = await _own_consent(conn, str(consent_uuid), principal.user_id)
        served = await consent_repo.served_notice_text(conn, artefact["consent_id"])
        if not served:
            raise NotFound("Notice text")
        return {
            **served,
            "integrity": (
                "verified"
                if served["hash_matches"]
                else "The stored text no longer matches the hash recorded at capture. "
                "Report this to the Privacy Office."
            ),
        }


@router.get("/consents/{consent_uuid}/grants")
async def my_consent_grants(
    consent_uuid: UUID, principal: RequireDataSubject
) -> list[dict[str, Any]]:
    async with connection() as conn:
        artefact = await _own_consent(conn, str(consent_uuid), principal.user_id)
        return await consent_repo.grants_of(conn, artefact["consent_id"])


@router.get("/consents/{consent_uuid}/history", summary="The supersession chain")
async def my_consent_history(
    consent_uuid: UUID, principal: RequireDataSubject
) -> list[dict[str, Any]]:
    """Every grant and withdrawal in order, so she can see the whole sequence."""
    async with connection() as conn:
        artefact = await _own_consent(conn, str(consent_uuid), principal.user_id)
        return await consent_repo.history_chain(
            conn, user_id=principal.user_id, notice_id=artefact["notice_id"]
        )


@router.get("/consents/{consent_uuid}/trail", summary="What was recorded about this consent")
async def my_consent_trail(
    consent_uuid: UUID, principal: RequireDataSubject
) -> list[dict[str, Any]]:
    """The audit trail for one consent, in her own words rather than the DPO's.

    The same rows the DPO's audit trail shows and the same entity resolver, so
    there is one record and two views of it rather than two records that can
    disagree. What differs is the scope: only artefacts in *her* chain for this
    notice, which `_own_consent` has already proved is hers.

    **Refused and withdrawn consents have trails too**, and this is the endpoint
    that shows them. A decision to refuse is a decision the Act protects — s.6(1)
    requires consent to be freely given, and "freely" is not demonstrable if the
    person cannot see that their refusal was recorded, when, and against which
    notice. A system that only evidences agreement is a system that quietly
    treats refusal as an absence.
    """
    async with connection() as conn:
        artefact = await _own_consent(conn, str(consent_uuid), principal.user_id)

        # The whole chain, not just the artefact she opened: giving, amending
        # and withdrawing are separate rows, and the trail of one link is not
        # the trail of the consent.
        chain = await consent_repo.history_chain(
            conn, user_id=principal.user_id, notice_id=artefact["notice_id"]
        )
        rows = await audit_repo.for_consent(conn, [c["consent_id"] for c in chain])
        # Her routes, not the staff console's. Every endpoint under /me reads
        # this way, and it is the whole of the fix for a data principal who
        # followed a link about her own consent and landed on the register.
        return await entity_repo.attach(conn, rows, for_subject=True)


@router.post("/consents/{consent_uuid}/withdraw")
async def withdraw(
    consent_uuid: UUID,
    body: WithdrawRequest,
    request: Request,
    principal: RequireDataSubject,
) -> dict[str, Any]:
    """Withdraw some purposes or all of them."""
    if not body.all and not body.purposes:
        raise ValidationFailed("Name the purposes to withdraw, or set all", field="purposes")
    async with transaction() as conn:
        return await consent_service.withdraw(
            conn,
            consent_uuid=str(consent_uuid),
            user_id=principal.user_id,
            purpose_uuids=[str(p) for p in (body.purposes or [])],
            withdraw_all=body.all,
            ip_address=request.client.host if request.client else None,
        )


@router.get("/disclosures", summary="Who was my data shared with (s.11(1)(b))")
async def my_disclosures(principal: RequireDataSubject) -> list[dict[str, Any]]:
    """Answered from export_line, not by parsing an archived CSV."""
    async with connection() as conn:
        return await exchange_repo.disclosures_for_user(conn, principal.user_id)


@router.get("/notifications")
async def my_notifications(
    principal: RequireDataSubject,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict[str, Any]:
    """Notifications a data subject can see, derived from her own audit trail.

    There is no notifications table in the 22; the events that concern her are
    already recorded, and deriving the feed means it can never disagree with the
    record.
    """
    async with connection() as conn:
        rows = await audit_repo.for_subject(conn, principal.user_id, limit=limit)
        # "What happened to my data" has to name the thing it happened to. The
        # same resolver the DPO's audit trail uses, on the same rows - but
        # resolving to *her* pages. The label is the same for both readers; the
        # link cannot be, because half of these have no page she may open.
        rows = await entity_repo.attach(conn, rows, for_subject=True)
    return {"items": rows, "next_cursor": None, "total": len(rows)}
