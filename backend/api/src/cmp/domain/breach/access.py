# ruff: noqa: E501 - the table in the docstring is read as a table; wrapped, it is not.
"""Breach-only logins: who may hold a ticket, and for how long (S3-09).

A breach ticket can go to somebody with no console login (BD-04, ADR 0023).
The DPO - or a holder adding a colleague - gives a name, an email and
optionally a mobile; the address must be internal (BD-12), and is looked up by
its keyed hash:

| The address belongs to | Then |
|---|---|
| an active member of staff | an ordinary ticket, as in S3-08 |
| a data principal's account | temporary access on that account: role `breach_holder`, the old role kept on the grant |
| a breach-only login already, for another breach | a second grant; the first one's old role is carried over |
| nobody | a new account: pending, `employee`, role `breach_holder`, made for this breach |

Somebody given a login sets a password with the reset flow's code, exactly as
an invitation works, and signs in with the emailed second factor like all
staff (ADR 0006). The email names no breach (BD-18).

Access ends when the breach closes, when the DPO withdraws that holder's
ticket, or when an administrator deactivates the account (BD-15). Ending one
grant:

1. If the person holds a grant on another breach, only this one ends.
2. Otherwise, if their role is still `breach_holder`: an account made for the
   breach is switched off; one that existed goes back to the role it held.
   The password goes either way.
3. `person_type` is never touched (BD-16) - this is not `end_staff_access`.
4. If an administrator has meanwhile given the person a real role, it stays.
5. Every session is revoked once the transaction has committed.
"""

from __future__ import annotations

from typing import Any

from cmp.auth.authentication import service as auth_service
from cmp.auth.sessions import service as sessions
from cmp.core import after_commit
from cmp.core.config import settings
from cmp.core.enums import PersonType, UserStatus
from cmp.core.errors import Conflict, ValidationFailed
from cmp.core.permissions import Role
from cmp.core.security import hash_password, new_token
from cmp.db.repositories import breach_tickets as repo
from cmp.db.repositories import users as user_repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.infrastructure.dkms import unseal_value
from cmp.validation import normalise_mobile

Row = dict[str, Any]

#: Why a grant ended.
BREACH_CLOSED = "breach_closed"
TICKET_WITHDRAWN = "ticket_withdrawn"
ACCOUNT_DEACTIVATED = "account_deactivated"

#: Roles that already sign in to the console in full: an ordinary ticket.
_STAFF = frozenset(r.value for r in Role) - {Role.DATA_SUBJECT.value, Role.BREACH_HOLDER.value}


def internal(email: str | None) -> bool:
    """BD-12: the address's domain is on BREACH_TICKET_EMAIL_DOMAINS."""
    domain = str(email).rsplit("@", 1)[-1].lower() if email and "@" in str(email) else ""
    return domain in {d.lower() for d in settings.breach_ticket_email_domains}


def refuse_external() -> None:
    raise ValidationFailed(
        "Breach tickets go to internal staff only: this email address is not on one of the "
        "organisation's own domains",
        field="email",
    )


async def opened_email(user: Row) -> str | None:
    value = await unseal_value("auth_user", "email", user.get("email"))
    return str(value) if value else None


async def resolve(
    conn: Conn, *, full_name: str | None, email: str, mobile: str | None
) -> tuple[Row, bool]:
    """The account an address belongs to, made if there is none. Returns it and
    whether it was made now. The caller has checked the domain and holds the
    breach row."""
    email = (email or "").strip().lower()
    found = await user_repo.by_email(conn, email)
    if found:
        if str(found["status"]) in (UserStatus.SUSPENDED.value,):
            raise ValidationFailed(
                "That account is suspended; an administrator can reactivate it", field="email"
            )
        return found, False
    name = (full_name or "").strip()
    if not name:
        raise ValidationFailed(
            "Give their name: nobody has an account at this address", field="full_name"
        )
    made = await user_repo.create(
        conn,
        full_name=name,
        email=email,
        role=Role.BREACH_HOLDER.value,
        mobile=normalise_mobile(mobile) if mobile else None,
        person_type=PersonType.EMPLOYEE.value,
        status=UserStatus.PENDING.value,
        # Unusable until they set their own through the reset flow, as with
        # every provisioned account.
        password_hash=hash_password(new_token(32)),
    )
    return made, True


def needs_grant(user: Row) -> bool:
    """Anyone who does not already sign in to the console in full."""
    return not (str(user["role"]) in _STAFF and str(user["status"]) == UserStatus.ACTIVE.value)


async def grant(
    conn: Conn,
    *,
    breach: Row,
    user: Row,
    ticket_id: int,
    created: bool,
    actor_id: int,
    cause: str,
) -> None:
    """Give `user` the breach-only role for this breach, and tell them how to
    sign in. The caller holds the breach row."""
    user_id = int(user["id"])
    elsewhere = await repo.open_grants_for_user(conn, user_id)
    role = str(user["role"])
    if role == Role.BREACH_HOLDER.value:
        # A second breach: carry over what the first grant will put back.
        previous = elsewhere[0]["previous_role"] if elsewhere else None
        account_created = bool(elsewhere[0]["account_created"]) if elsewhere else created
    elif role in _STAFF:
        # A member of staff whose account is not active - switched off, or
        # never activated - is not given a second way in through a ticket.
        raise ValidationFailed(
            "That member of staff's account is not active; an administrator can reactivate it",
            field="email",
        )
    else:
        previous = None if created else role
        account_created = created
    made = await repo.add_grant(
        conn,
        breach_id=int(breach["breach_id"]),
        user_id=user_id,
        ticket_id=ticket_id,
        account_created=account_created,
        previous_role=previous,
        granted_by=actor_id,
    )
    if made is None:
        raise Conflict("This person already holds access on this breach", code="access_exists")
    if role != Role.BREACH_HOLDER.value:
        await user_repo.set_role(conn, user_id, Role.BREACH_HOLDER.value)
    if account_created and str(user["status"]) == UserStatus.DEACTIVATED.value:
        # Switched off when an earlier grant ended: back to pending, and a new
        # password through the reset flow.
        await user_repo.set_status(conn, user_id, UserStatus.PENDING.value)
    await audit.record(
        conn,
        event=Event.USER_TEMPORARY_ACCESS_GRANTED,
        entity_type="auth_user",
        entity_id=user_id,
        subject_user_id=user_id,
        actor_user_id=actor_id,
        detail={"reference": breach["reference"], "cause": cause},
    )
    fresh = await user_repo.by_id(conn, user_id)
    assert fresh is not None
    if elsewhere and role == Role.BREACH_HOLDER.value and str(fresh["status"]) == "active":
        # They already sign in for another breach: the waiting notice will do.
        return
    await auth_service.invite_breach_holder(conn, user=fresh)


async def end(conn: Conn, grant_row: Row, *, cause: str, actor_id: int | None) -> None:
    """End one grant, and put the account back if it was the last."""
    user_id = int(grant_row["user_id"])
    await repo.end_grant(conn, int(grant_row["access_id"]), cause=cause, ended_by=actor_id)
    still = await repo.open_grants_for_user(conn, user_id)
    user = await user_repo.by_id(conn, user_id)
    assert user is not None
    breach_ref = await _reference(conn, int(grant_row["breach_id"]))
    if not still and str(user["role"]) == Role.BREACH_HOLDER.value:
        if grant_row["account_created"]:
            await user_repo.set_status(conn, user_id, UserStatus.DEACTIVATED.value)
        else:
            await user_repo.set_role(
                conn, user_id, str(grant_row["previous_role"] or Role.DATA_SUBJECT.value)
            )
        await user_repo.clear_password(conn, user_id)
    await audit.record(
        conn,
        event=Event.USER_TEMPORARY_ACCESS_ENDED,
        entity_type="auth_user",
        entity_id=user_id,
        subject_user_id=user_id,
        actor_user_id=actor_id,
        detail={"reference": breach_ref, "cause": cause, "kept": bool(still)},
    )
    # After the commit: a session revoked inside a transaction that then rolls
    # back has ended access that was never ended.
    await after_commit.defer_async(lambda: sessions.revoke_all(user_id))


async def _reference(conn: Conn, breach_id: int) -> str:
    from cmp.db.repositories import breaches as breach_repo

    row = await breach_repo.by_breach_id(conn, breach_id)
    return str(row["reference"]) if row else ""


async def end_on_breach(conn: Conn, breach_id: int, *, actor_id: int) -> int:
    """The breach closed: every grant on it ends, in the closing transaction."""
    rows = await repo.open_grants_on(conn, breach_id)
    for row in rows:
        await end(conn, row, cause=BREACH_CLOSED, actor_id=actor_id)
    return len(rows)


async def end_for_ticket(conn: Conn, breach_id: int, user_id: int, *, actor_id: int) -> None:
    """The DPO withdrew this holder's ticket (BD-15)."""
    row = await repo.open_grant(conn, breach_id, user_id)
    if row:
        await end(conn, row, cause=TICKET_WITHDRAWN, actor_id=actor_id)


async def end_for_account(conn: Conn, user_id: int, *, actor_id: int) -> int:
    """An administrator deactivated the account (BD-15): every grant ends."""
    rows = await repo.open_grants_for_user(conn, user_id)
    for row in rows:
        await end(conn, row, cause=ACCOUNT_DEACTIVATED, actor_id=actor_id)
    return len(rows)
