"""Signing in through the organisation on a consent link (ADR 0034).

An `sso` link offers one way in: the organisation's identity provider. What
the provider asserts is matched to an account on the employee ID - the
organisation's own number for the person, which the HRMS knows - and never
on anything typed in the open:

* **One account carries the ID**: it is signed in, whatever its role, as a
  data principal (`open_principal_session`): SSO on a consent link is worth
  exactly what a code is.
* **None does**: the person is an employee the register has not met. Their
  account cannot exist without a mobile (`trg_subject_needs_mobile`), so the
  assertion is held - sealed, fifteen minutes - until they confirm one by
  code, and only then is the account created, as an employee, carrying the
  ID, the name and the address the organisation asserted (open point F-7).
* **The asserted address belongs to another account** - one with a different
  ID, or none (open point F-10) - or the confirmed mobile does: refused with
  a neutral message, audited, and left to the administrator.

The provider not answering is reported as that, never as an invalid link
(review UX-3); an assertion that does not validate is the same neutral page
an invalid link gets. Nothing here records a claim.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Any

from cmp.auth.authentication import otp
from cmp.auth.authentication.service import open_principal_session
from cmp.auth.rate_limit import service as ratelimit
from cmp.auth.sessions import service as sessions
from cmp.core.config import settings
from cmp.core.enums import PersonType
from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.core.logging import get_logger
from cmp.db.repositories import consent as consent_repo
from cmp.db.repositories import users as user_repo
from cmp.db.sql import Conn, unique_violation
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.domain.consent.service import resolve_link
from cmp.infrastructure.identity import oidc
from cmp.infrastructure.identity import state as sso_state
from cmp.validation import normalise_mobile

log = get_logger("cmp.sso")

#: Said for every identity that cannot be signed in automatically. It names no
#: account and no reason: the administrator, who can see both, resolves it.
CONFLICT = (
    "We could not sign you in with your organisation account. Please contact the "
    "administrator, quoting this link."
)


class SsoUnavailable(Exception):
    """The organisation's sign-in is switched off, or its provider did not answer."""


@dataclass
class Outcome:
    """Where the callback leaves the person, for the portal to show."""

    #: `signed_in`, `mobile_needed`, `conflict`, `invalid`, `unavailable` or
    #: `cancelled`.
    kind: str
    link_token: str
    session_token: str | None = None
    session: sessions.Session | None = None
    pending_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


async def _sso_link(conn: Conn, token: str) -> dict[str, Any]:
    link = await resolve_link(conn, token)
    if link.get("audience_mode") != "sso":
        # A code link has no organisation sign-in; asked for one, it is not there.
        raise NotFound("Consent link")
    return link


async def start(conn: Conn, *, token: str) -> str:
    """Where to send the browser: the provider's sign-in, with this sign-in's
    state, nonce and PKCE challenge, which the server keeps."""
    await _sso_link(conn, token)
    if not oidc.configured():
        raise SsoUnavailable("not configured")
    verifier, challenge = oidc.pkce_pair()
    nonce = secrets.token_urlsafe(32)
    state = await sso_state.begin(link_token=token, nonce=nonce, verifier=verifier)
    try:
        return await oidc.authorize_url(state=state, nonce=nonce, challenge=challenge)
    except oidc.ProviderUnavailable as exc:
        raise SsoUnavailable(str(exc)) from exc


async def callback(
    conn: Conn,
    *,
    state: str,
    code: str | None,
    error: str | None,
    ip_address: str | None,
    user_agent: str | None,
) -> Outcome:
    """Continue the sign-in `state` names. Unknown or used: `NotFound`."""
    started = await sso_state.take(state)
    if not started:
        raise NotFound("Sign-in")
    token = str(started["link_token"])
    if error or not code:
        # The person cancelled at the provider, or the provider refused.
        return Outcome("cancelled", token)
    try:
        id_token = await oidc.exchange(code=code, verifier=str(started["verifier"]))
        claims = await oidc.validate(id_token, nonce=str(started["nonce"]))
    except oidc.ProviderUnavailable:
        return Outcome("unavailable", token)
    except oidc.AssertionInvalid as exc:
        log.warning("sso.assertion_refused", reason=str(exc))
        await audit.record(
            conn,
            event=Event.SSO_ASSERTION_REFUSED,
            entity_type="auth_user",
            entity_id=0,
            detail={"cause": "the assertion did not validate"},
        )
        return Outcome("invalid", token)
    try:
        link = await _sso_link(conn, token)
    except Exception:
        return Outcome("invalid", token)

    account = await user_repo.by_employee_id(conn, claims.employee_id)
    holder = await user_repo.by_contact(conn, claims.email) if claims.email else None
    if holder and (account is None or holder["id"] != account["id"]):
        await _conflict(conn, link, holder["id"], "the asserted address is on another account")
        return Outcome("conflict", token)
    if account and account["status"] not in ("active", "pending"):
        await _conflict(conn, link, account["id"], "the account is switched off")
        return Outcome("conflict", token)

    if account is None:
        pending_id = await sso_state.hold(
            {"employee_id": claims.employee_id, "email": claims.email, "name": claims.name},
            link_token=token,
        )
        return Outcome("mobile_needed", token, pending_id=pending_id)

    if account["status"] == "pending":
        await user_repo.set_status(conn, account["id"], "active")
    raw, session = await open_principal_session(
        user=account, ip_address=ip_address, user_agent=user_agent
    )
    await _signed_in(conn, link, account["id"], created=False)
    return Outcome("signed_in", token, session_token=raw, session=session)


async def _conflict(conn: Conn, link: dict[str, Any], user_id: int, cause: str) -> None:
    await audit.record(
        conn,
        event=Event.SSO_IDENTITY_CONFLICT,
        entity_type="auth_user",
        entity_id=user_id,
        subject_user_id=user_id,
        detail={"link": str(link["link_uuid"]), "cause": cause},
    )


async def _signed_in(conn: Conn, link: dict[str, Any], user_id: int, *, created: bool) -> None:
    detail = {"link": str(link["link_uuid"])}
    if created:
        await audit.record(
            conn,
            event=Event.SSO_ACCOUNT_CREATED,
            entity_type="auth_user",
            entity_id=user_id,
            subject_user_id=user_id,
            actor_user_id=user_id,
            detail=detail,
        )
    await audit.record(
        conn,
        event=Event.SSO_SIGNED_IN,
        entity_type="auth_user",
        entity_id=user_id,
        subject_user_id=user_id,
        actor_user_id=user_id,
        detail=detail,
    )
    await audit.record(
        conn,
        event=Event.LOGIN_SUCCEEDED,
        entity_type="auth_user",
        entity_id=user_id,
        subject_user_id=user_id,
        actor_user_id=user_id,
        detail={"method": "sso", "acting_as": "data_subject"},
    )


async def _pending(token: str, pending_id: str | None) -> dict[str, Any]:
    held = await sso_state.pending(pending_id) if pending_id else None
    if not held or held.get("link_token") != token:
        # Expired, or another link's: start again from the link.
        raise NotFound("Sign-in")
    return held


async def send_mobile_code(conn: Conn, *, token: str, pending_id: str | None, mobile: str) -> None:
    """A code to the mobile an employee's new account will carry."""
    await _pending(token, pending_id)
    link = await _sso_link(conn, token)
    number = normalise_mobile(mobile)
    if not number:
        raise ValidationFailed("Enter a mobile number", field="mobile")
    await ratelimit.enforce(
        "sso_mobile",
        ratelimit.contact_key(number),
        limit=settings.otp_requests_per_contact_per_hour,
        window_s=3600,
        message="Too many code requests for this number.",
    )
    if await user_repo.by_contact(conn, number):
        raise Conflict(CONFLICT, code="sso_conflict", field="mobile")
    issued = await otp.issue(otp.Scope.SSO_MOBILE, f"{pending_id}:{number}")
    from cmp.tasks.authentication import send_consent_code
    from cmp.tasks.dispatch import dispatch_required

    dispatch_required(send_consent_code, number, issued.code, link["project_name"])


async def confirm_mobile(
    conn: Conn,
    *,
    token: str,
    pending_id: str | None,
    mobile: str,
    code: str,
    ip_address: str | None,
    user_agent: str | None,
) -> tuple[str, sessions.Session]:
    """The code came back: the employee's account is created, active, with the
    confirmed mobile, the asserted address and employee ID, and signed in."""
    held = await _pending(token, pending_id)
    link = await _sso_link(conn, token)
    number = normalise_mobile(mobile)
    if not number:
        raise ValidationFailed("Enter a mobile number", field="mobile")
    await otp.require(otp.Scope.SSO_MOBILE, f"{pending_id}:{number}", code)

    claims = held["claims"]
    if await user_repo.by_employee_id(conn, str(claims["employee_id"])):
        # Created by another tab in the meantime: sign that one in instead of a
        # second account the unique index would refuse anyway.
        raise Conflict(CONFLICT, code="sso_conflict")
    consumed = await consent_repo.increment_use(conn, link["link_id"])
    if not consumed:
        raise NotFound("Consent link")
    try:
        user = await user_repo.create(
            conn,
            full_name=str(claims.get("name") or "Employee"),
            email=claims.get("email"),
            mobile=number,
            organization_id=str(claims["employee_id"]),
            role="data_subject",
            person_type=PersonType.EMPLOYEE.value,
            status="active",
            registered_via_link_id=link["link_id"],
        )
    except Exception as exc:
        if unique_violation(exc):
            raise Conflict(CONFLICT, code="sso_conflict") from exc
        raise
    user = await user_repo.mark_contact_verified(conn, user["id"], "mobile")
    if claims.get("email"):
        # The organisation asserted it; that is as good as a code to it.
        user = await user_repo.mark_contact_verified(conn, user["id"], "email")
    await sso_state.release(str(pending_id))
    raw, session = await open_principal_session(
        user=user, ip_address=ip_address, user_agent=user_agent
    )
    await _signed_in(conn, link, user["id"], created=True)
    return raw, session
