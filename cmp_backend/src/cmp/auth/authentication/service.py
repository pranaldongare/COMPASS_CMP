"""Authentication services.

Three sign-in paths, deliberately different because the populations are:

* **Staff password sign-in**, optionally stepped up with MFA. Staff have
  credentials, are provisioned by an administrator, and never self-register.
* **Data-subject OTP sign-in.** A data subject has no password - `password_hash`
  is nullable for exactly this reason. Issuing them a credential to manage would
  be a liability for both sides, and they sign in rarely.
* **The public consent flow**, which establishes a subject session against a
  link token and is handled in `cmp.domain.consent`.

Timing and message discipline: a failed sign-in says the same thing whether the
account does not exist, the password is wrong, or the account is deactivated. The
alternative turns the login form into an account-enumeration oracle.
"""

from __future__ import annotations

from typing import Any

from cmp.auth.authentication import otp
from cmp.auth.authorization.roles import requires_mfa
from cmp.auth.rate_limit import service as ratelimit
from cmp.auth.sessions import service as sessions
from cmp.core.config import settings
from cmp.core.errors import (
    BadRequest,
    Conflict,
    Forbidden,
    RateLimited,
    Unauthenticated,
    ValidationFailed,
)
from cmp.core.logging import get_logger
from cmp.core.permissions import Role, nav_for, writes_for
from cmp.core.security import hash_password, password_needs_rehash, verify_password
from cmp.db.repositories import users as user_repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.validation import is_mobile, normalise_mobile

log = get_logger("cmp.auth")

# One sentence for every failure mode of sign-in.
_GENERIC_FAILURE = "Those credentials are not valid"


async def authenticate(
    conn: Conn, *, login: str, password: str, ip_address: str | None, user_agent: str | None
) -> dict[str, Any]:
    """Verify a staff password. Returns a session descriptor, possibly partial.

    Lockout is checked before the password is examined, so a locked account
    cannot be probed at all, and the failure counter is keyed on the account.
    """
    locked_for = await ratelimit.is_locked_out(login)
    if locked_for:
        log.warning("auth.attempt_while_locked")
        raise RateLimited("Too many failed attempts. Try again later.", retry_after_s=locked_for)

    user = await user_repo.credentials_by_login(conn, login)

    # Always run a verification, even with no user, so the response time does not
    # distinguish "no such account" from "wrong password".
    ok = verify_password(password, user["password_hash"] if user else None)

    if not user or not ok:
        fails = await ratelimit.record_login_failure(login)
        if user:
            await audit.record(
                conn,
                event=Event.LOGIN_FAILED,
                entity_type="auth_user",
                entity_id=user["id"],
                subject_user_id=user["id"],
                actor_user_id=user["id"],
                detail={"reason": "bad_password", "failures": fails},
            )
        if fails >= settings.login_max_attempts and user:
            await audit.record(
                conn,
                event=Event.LOGIN_LOCKED_OUT,
                entity_type="auth_user",
                entity_id=user["id"],
                subject_user_id=user["id"],
                actor_user_id=user["id"],
                detail={"failures": fails},
            )
        raise Unauthenticated(_GENERIC_FAILURE)

    # Status is checked only after the password is known to be correct. Checking
    # first would tell an unauthenticated caller that an account exists.
    if user["status"] != "active":
        await audit.record(
            conn,
            event=Event.LOGIN_FAILED,
            entity_type="auth_user",
            entity_id=user["id"],
            subject_user_id=user["id"],
            actor_user_id=user["id"],
            detail={"reason": f"status_{user['status']}"},
        )
        raise Unauthenticated(_GENERIC_FAILURE)

    if user["role"] == Role.DATA_SUBJECT.value:
        # Data subjects have no password path. If one somehow has a hash, the
        # password route is still not theirs.
        raise Unauthenticated(_GENERIC_FAILURE)

    await ratelimit.clear_login_failures(login)

    # Opportunistic upgrade when the cost parameters move on.
    if password_needs_rehash(user["password_hash"]):
        await user_repo.set_password(conn, user["id"], hash_password(password))
        log.info("auth.password_rehashed", user_id=user["id"])

    mfa_needed = requires_mfa(user["role"])

    token, session = await sessions.create(
        user_id=user["id"],
        user_uuid=str(user["uuid"]),
        role=user["role"],
        ip_address=ip_address,
        user_agent=user_agent,
        partial=mfa_needed,
        mfa_verified=not mfa_needed,
    )

    if mfa_needed:
        issued = await otp.issue(otp.Scope.STAFF_MFA, str(user["uuid"]), ttl_s=settings.mfa_ttl_s)
        # Delivery is a side effect and belongs off the request path.
        from cmp.tasks.authentication import send_mfa_code
        from cmp.tasks.dispatch import dispatch_required

        dispatch_required(send_mfa_code, str(user["uuid"]), user["email"], issued.code)
    else:
        await audit.record(
            conn,
            event=Event.LOGIN_SUCCEEDED,
            entity_type="auth_user",
            entity_id=user["id"],
            subject_user_id=user["id"],
            actor_user_id=user["id"],
            detail={"mfa": False},
        )

    return {
        "token": token,
        "session": session,
        "mfa_required": mfa_needed,
        "user": user,
        "max_age": settings.mfa_ttl_s if mfa_needed else settings.session_ttl_s,
    }


async def verify_mfa(conn: Conn, *, user_uuid: str, code: str, token: str) -> dict[str, Any]:
    """Complete a stepped-up sign-in.

    The partial session is what authorises this call; the code is what completes
    it. Both are required, which is what makes it a second factor rather than a
    second password.
    """
    try:
        await otp.require(otp.Scope.STAFF_MFA, user_uuid, code)
    except (BadRequest, RateLimited):
        user = await _user_by_uuid_id(conn, user_uuid)
        if user:
            await audit.record(
                conn,
                event=Event.MFA_FAILED,
                entity_type="auth_user",
                entity_id=user["id"],
                subject_user_id=user["id"],
                actor_user_id=user["id"],
            )
        raise

    session = await sessions.promote(token)
    if session is None:
        raise Unauthenticated("Your session has expired. Sign in again.")

    user = await _user_by_uuid_id(conn, user_uuid)
    if user:
        await audit.record(
            conn,
            event=Event.MFA_VERIFIED,
            entity_type="auth_user",
            entity_id=user["id"],
            subject_user_id=user["id"],
            actor_user_id=user["id"],
        )
        await audit.record(
            conn,
            event=Event.LOGIN_SUCCEEDED,
            entity_type="auth_user",
            entity_id=user["id"],
            subject_user_id=user["id"],
            actor_user_id=user["id"],
            detail={"mfa": True},
        )
    return {"session": session, "max_age": settings.session_ttl_s}


async def resend_mfa(conn: Conn, *, user_uuid: str, email: str) -> None:
    await ratelimit.enforce(
        "mfa_resend",
        user_uuid,
        limit=3,
        window_s=600,
        message="Too many code requests. Wait a few minutes.",
    )
    issued = await otp.issue(otp.Scope.STAFF_MFA, user_uuid, ttl_s=settings.mfa_ttl_s)
    from cmp.tasks.authentication import send_mfa_code
    from cmp.tasks.dispatch import dispatch_required

    dispatch_required(send_mfa_code, user_uuid, email, issued.code)


# --------------------------------------------------- data subject OTP sign-in
async def request_subject_otp(conn: Conn, *, contact: str) -> None:
    """Issue a sign-in code to a data subject.

    Always returns success. Whether the contact is registered is not something an
    unauthenticated caller may learn - that would turn this into a membership
    oracle for "who consented to this project".
    """
    await ratelimit.enforce(
        "subject_otp",
        contact.lower(),
        limit=settings.otp_requests_per_contact_per_hour,
        window_s=3600,
        message="Too many code requests for this contact.",
    )

    user = await user_repo.by_contact(conn, contact)
    if not user or user["status"] not in ("active", "pending"):
        log.info("auth.otp_requested_unknown_contact")
        return

    issued = await otp.issue(otp.Scope.SUBJECT_LOGIN, str(user["uuid"]))
    from cmp.tasks.authentication import send_login_code
    from cmp.tasks.dispatch import dispatch_required

    dispatch_required(send_login_code, str(user["uuid"]), contact, issued.code)

    await audit.record(
        conn,
        event=Event.OTP_REQUESTED,
        entity_type="auth_user",
        entity_id=user["id"],
        subject_user_id=user["id"],
        actor_user_id=user["id"],
    )


async def verify_subject_otp(
    conn: Conn, *, contact: str, code: str, ip_address: str | None, user_agent: str | None
) -> dict[str, Any]:
    user = await user_repo.by_contact(conn, contact)
    if not user:
        # Same message and roughly the same work as a wrong code.
        raise BadRequest("Invalid or expired code", code="otp_invalid", field="code")

    await otp.require(otp.Scope.SUBJECT_LOGIN, str(user["uuid"]), code)

    user = await user_repo.mark_contact_verified(
        conn, user["id"], "mobile" if is_mobile(contact) else "email"
    )
    if user["status"] == "pending":
        # A code proves the medium it came to. Sign-up authenticates every
        # medium she gave, so a pending account with one still unanswered is
        # not finished - and finishing it is the sign-up page's job. The codes
        # go out again so that she can.
        if user_repo.unverified_mediums(user):
            await _send_registration_codes(user)
            raise BadRequest(
                "Your account is not finished. Enter the codes we have just sent to your "
                "mobile and email on the sign-up page.",
                code="registration_incomplete",
                field="code",
            )
        await user_repo.set_status(conn, user["id"], "active")

    token, session = await sessions.create(
        user_id=user["id"],
        user_uuid=str(user["uuid"]),
        role=user["role"],
        ip_address=ip_address,
        user_agent=user_agent,
        mfa_verified=True,
    )
    await audit.record(
        conn,
        event=Event.OTP_VERIFIED,
        entity_type="auth_user",
        entity_id=user["id"],
        subject_user_id=user["id"],
        actor_user_id=user["id"],
    )
    await audit.record(
        conn,
        event=Event.LOGIN_SUCCEEDED,
        entity_type="auth_user",
        entity_id=user["id"],
        subject_user_id=user["id"],
        actor_user_id=user["id"],
        detail={"method": "otp"},
    )
    return {"token": token, "session": session, "user": user, "max_age": settings.session_ttl_s}


# ------------------------------------------------------------------ password
async def change_password(
    conn: Conn, *, user_id: int, current_password: str, new_password: str
) -> None:
    user = await user_repo.by_id(conn, user_id)
    if not user:
        raise Unauthenticated("Sign in to continue")

    creds = await user_repo.credentials_by_login(conn, user["email"])
    if not creds or not verify_password(current_password, creds["password_hash"]):
        raise Unauthenticated("Your current password is not correct")

    if current_password == new_password:
        raise BadRequest(
            "The new password must differ from the current one",
            code="password_unchanged",
            field="new_password",
        )

    await user_repo.set_password(conn, user_id, hash_password(new_password))
    await audit.record(
        conn,
        event=Event.PASSWORD_CHANGED,
        entity_type="auth_user",
        entity_id=user_id,
        subject_user_id=user_id,
        actor_user_id=user_id,
    )
    # Every other session is invalidated. A password change is usually a response
    # to suspicion, and leaving other sessions alive defeats the point.
    await sessions.revoke_all(user_id)


async def request_password_reset(conn: Conn, *, email: str) -> None:
    """Always succeeds from the caller's point of view - see request_subject_otp."""
    await ratelimit.enforce(
        "pwreset",
        email.lower(),
        limit=3,
        window_s=3600,
        message="Too many reset requests.",
    )
    user = await user_repo.by_email(conn, email)
    if not user or user["role"] == Role.DATA_SUBJECT.value or user["status"] != "active":
        log.info("auth.reset_requested_unknown")
        return

    issued = await otp.issue(otp.Scope.CONTACT_VERIFY, f"reset:{user['uuid']}", ttl_s=900)
    from cmp.tasks.authentication import send_password_reset
    from cmp.tasks.dispatch import dispatch_required

    dispatch_required(send_password_reset, str(user["uuid"]), user["email"], issued.code)
    await audit.record(
        conn,
        event=Event.PASSWORD_RESET_REQUESTED,
        entity_type="auth_user",
        entity_id=user["id"],
        subject_user_id=user["id"],
        actor_user_id=user["id"],
    )


async def confirm_password_reset(conn: Conn, *, email: str, code: str, new_password: str) -> None:
    user = await user_repo.by_email(conn, email)
    if not user:
        raise BadRequest("Invalid or expired code", code="otp_invalid", field="code")

    await otp.require(otp.Scope.CONTACT_VERIFY, f"reset:{user['uuid']}", code)
    await user_repo.set_password(conn, user["id"], hash_password(new_password))
    await audit.record(
        conn,
        event=Event.PASSWORD_RESET_COMPLETED,
        entity_type="auth_user",
        entity_id=user["id"],
        subject_user_id=user["id"],
        actor_user_id=user["id"],
    )
    await sessions.revoke_all(user["id"])


# --------------------------------------------------------------------- /me
async def me_payload(conn: Conn, *, user_id: int, session: sessions.Session) -> dict[str, Any]:
    """What GET /auth/me returns.

    The SPA cannot render first paint without it: identity, role, permitted
    navigation and session expiry, in one call. Anything the frontend would
    otherwise have to guess belongs here.
    """
    user = await user_repo.by_id(conn, user_id)
    if not user:
        raise Unauthenticated("Your account is no longer available")
    if user["status"] != "active":
        # A session outlives a deactivation by however long it takes the next
        # request to arrive. This closes that window.
        await sessions.revoke_all(user_id)
        raise Forbidden("This account is not active", code="account_inactive")

    from datetime import UTC, datetime

    return {
        "uuid": str(user["uuid"]),
        "full_name": user["full_name"],
        "email": user["email"],
        "mobile": user.get("mobile"),
        "role": user["role"],
        "person_type": user["person_type"],
        "status": user["status"],
        # Carried on first paint so the interface does not need a second call to
        # find out whether it is dealing with a child's account.
        "dob": user["dob"],
        "is_minor": user["is_minor"],
        "mfa_verified": session.mfa_verified,
        "session_expires_at": datetime.fromtimestamp(session.expires_at, tz=UTC),
        "nav": nav_for(user["role"]),
        "writes": writes_for(user["role"]),
    }


async def _user_by_uuid_id(conn: Conn, user_uuid: str) -> dict[str, Any] | None:
    return await user_repo.by_uuid(conn, user_uuid)


async def register_data_subject(
    conn: Conn,
    *,
    full_name: str,
    mobile: str,
    dob: str,
    email: str | None = None,
) -> None:
    """Self-registration, for a data principal and nobody else.

    The role is written here as a literal rather than taken from the request.
    An unauthenticated caller choosing their own role is how an open sign-up form
    becomes a privilege escalation, and no amount of validation downstream is as
    reliable as never reading the field.

    **A contact that already belongs to an active account is refused, and the
    refusal names which one.** This is a product decision taken with its cost
    in view: sign-up is unauthenticated, so a form that says "this mobile is
    taken" lets anyone test whether a person is a data principal here - which,
    for a consent register, is close to "who is in this study". The brakes
    that remain are the per-contact limit above and the per-address limit on
    the route. What it buys is a form that can be corrected: the earlier,
    neutral behaviour sent the existing account a *sign-in* code while the form
    advanced to the *registration*-code step, where that code could never
    verify, and the person was stuck without knowing why.

    A registration that was started and never finished is not a conflict: the
    same codes are sent again so it can be completed.

    Date of birth is required here, unlike on accounts created through a consent
    link. Section 9 makes it the input to whether this is a child's account, and
    a self-registration is the one moment the platform can ask.
    """
    mobile = normalise_mobile(mobile)
    email = email.strip().lower() if email and email.strip() else None
    if not mobile:
        raise ValidationFailed("A mobile number is required", field="mobile")
    for contact in (mobile, email):
        if contact:
            await ratelimit.enforce(
                "subject_register",
                contact,
                limit=settings.otp_requests_per_contact_per_hour,
                window_s=3600,
                message="Too many registration attempts for this contact.",
            )

    existing = await user_repo.by_contact(conn, mobile)
    taken = "mobile"
    if not existing and email:
        existing = await user_repo.by_contact(conn, email)
        taken = "email"
    if existing:
        if existing["status"] == "pending":
            # Started and never finished: the same codes again, so she can.
            await _send_registration_codes(existing)
            log.info("auth.register_resumed")
            return
        # Named field, so the form can put the message on the input that has
        # to change and offer sign-in with it.
        log.info("auth.register_contact_taken", field=taken)
        raise Conflict(
            f"An account already exists with this {taken}. Sign in with it instead, "
            f"or use a different {taken}.",
            code="contact_taken",
            field=taken,
        )

    user = await user_repo.create(
        conn,
        full_name=full_name,
        email=email,
        mobile=mobile,
        role=Role.DATA_SUBJECT.value,
        person_type="external",
        status="pending",
        dob=dob,
    )
    await audit.record(
        conn,
        event=Event.USER_CREATED,
        entity_type="auth_user",
        entity_id=user["id"],
        detail={
            "role": Role.DATA_SUBJECT.value,
            "via": "self_registration",
            # The date itself is personal data and does not belong in a log that
            # every DPO can read. Whether it made them a child is the fact the
            # trail needs, and it is the fact section 9 turns on.
            "is_minor": user["is_minor"],
        },
    )

    await _send_registration_codes(user)
    log.info("auth.registered", is_minor=user["is_minor"])


async def _send_registration_codes(user: dict[str, Any]) -> None:
    """A code to every medium on the account. Each is authenticated at sign-up."""
    from cmp.tasks.authentication import send_registration_code
    from cmp.tasks.dispatch import dispatch_required

    for medium in ("mobile", "email"):
        contact = user.get(medium)
        if contact:
            issued = await otp.issue(otp.Scope.SUBJECT_REGISTER, f"{user['uuid']}:{medium}")
            dispatch_required(send_registration_code, str(user["uuid"]), str(contact), issued.code)


async def confirm_registration(
    conn: Conn,
    *,
    mobile: str,
    mobile_code: str | None,
    email_code: str | None,
    ip_address: str | None,
    user_agent: str | None,
) -> dict[str, Any]:
    """Finish sign-up: every medium she gave answers with its code, then she is in.

    Both codes are checked before either is spent, so a wrong email code does
    not burn a right mobile code and leave her unable to retry. A medium that
    has already answered - a retry after a partial success - needs no code.
    Failures are the same sentence whatever the reason, as everywhere a
    stranger can type a contact.
    """
    user = await user_repo.by_contact(conn, normalise_mobile(mobile))
    if (
        not user
        or user["role"] != Role.DATA_SUBJECT.value
        or user["status"] not in ("pending", "active")
    ):
        raise BadRequest("Invalid or expired code", code="otp_invalid", field="mobile_code")
    uuid = str(user["uuid"])
    outstanding = user_repo.unverified_mediums(user)
    codes = {"mobile": mobile_code, "email": email_code}
    for medium in outstanding:
        if not codes[medium]:
            where = "mobile" if medium == "mobile" else "email as well"
            raise ValidationFailed(
                f"Enter the code we sent to your {where}", field=f"{medium}_code"
            )
    for medium in outstanding:
        await otp.require(
            otp.Scope.SUBJECT_REGISTER,
            f"{uuid}:{medium}",
            str(codes[medium]),
            field=f"{medium}_code",
            consume=False,
        )
    for medium in outstanding:
        await otp.discard(otp.Scope.SUBJECT_REGISTER, f"{uuid}:{medium}")
        user = await user_repo.mark_contact_verified(conn, user["id"], medium)
    if user["status"] == "pending":
        await user_repo.set_status(conn, user["id"], "active")
        refreshed = await user_repo.by_id(conn, user["id"])
        assert refreshed is not None
        user = refreshed
    token, session = await sessions.create(
        user_id=user["id"],
        user_uuid=uuid,
        role=user["role"],
        ip_address=ip_address,
        user_agent=user_agent,
        mfa_verified=True,
    )
    await audit.record(
        conn,
        event=Event.OTP_VERIFIED,
        entity_type="auth_user",
        entity_id=user["id"],
        subject_user_id=user["id"],
        actor_user_id=user["id"],
        detail={"flow": "registration", "mediums": outstanding},
    )
    await audit.record(
        conn,
        event=Event.LOGIN_SUCCEEDED,
        entity_type="auth_user",
        entity_id=user["id"],
        subject_user_id=user["id"],
        actor_user_id=user["id"],
        detail={"method": "registration"},
    )
    return {"token": token, "session": session, "user": user, "max_age": settings.session_ttl_s}
