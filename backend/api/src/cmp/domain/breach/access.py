# ruff: noqa: E501 - the table in the docstring is read as a table; wrapped, it is not.
"""Temporary logins: who may hold a ticket, and for how long (S3-09).

Since 0049 a rights ticket gives one too, to a colleague on an internal domain
with no console login (`grant_for_holder`): the same role, the same
invitation, the same off switch, recorded in the same table. Its grant ends
when the request closes, or the ticket is withdrawn or sent to somebody else.

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

A grant is the window in which they act. It ends when the breach closes or
when the DPO withdraws that holder's ticket (BD-15), and ending it changes
nothing about the account: the login stays, and the ticket stays theirs to
read (decided 2026-10-06, replacing BD-16's switch-off). Read-only needs no
check of its own - a withdrawn or closed ticket, and every ticket on a closed
breach, already refuses every write. A person who also holds a real role
keeps it, and their tickets with it.

The one off switch is the administrator's **End temporary access**
(`remove`): every open grant ends, and the account goes back to what it was
before its first grant - switched off if it was made for a breach, its
previous role otherwise - with the password cleared. `person_type` is never
touched (BD-16) - this is not `end_staff_access`. The caller revokes the
sessions once the transaction has committed.
"""

from __future__ import annotations

from typing import Any

from cmp.auth.authentication import service as auth_service
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
REQUEST_CLOSED = "request_closed"
REASSIGNED = "reassigned"

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
) -> bool:
    """Give `user` the breach-only role for this breach, and tell them how to
    sign in if they cannot yet. True if that email went; False if they already
    sign in, and the caller tells them a ticket is waiting instead. The caller
    holds the breach row."""

    async def add(previous: str | None, account_created: bool) -> Row | None:
        return await repo.add_grant(
            conn,
            breach_id=int(breach["breach_id"]),
            user_id=int(user["id"]),
            ticket_id=ticket_id,
            account_created=account_created,
            previous_role=previous,
            granted_by=actor_id,
        )

    return await _grant(
        conn,
        user=user,
        created=created,
        actor_id=actor_id,
        cause=cause,
        reference=str(breach["reference"]),
        add=add,
        already="on this breach",
    )


async def grant_for_holder(
    conn: Conn,
    *,
    holder_id: int,
    reference: str,
    user: Row,
    created: bool,
    actor_id: int,
    cause: str = "rights_ticket",
) -> bool:
    """A temporary login for one rights ticket (0049): as `grant`, for the
    holder of a ticket on request `reference`. The caller holds the request."""

    async def add(previous: str | None, account_created: bool) -> Row | None:
        return await repo.add_holder_grant(
            conn,
            holder_id=holder_id,
            user_id=int(user["id"]),
            account_created=account_created,
            previous_role=previous,
            granted_by=actor_id,
        )

    return await _grant(
        conn,
        user=user,
        created=created,
        actor_id=actor_id,
        cause=cause,
        reference=reference,
        add=add,
        already="on this ticket",
    )


async def _grant(
    conn: Conn,
    *,
    user: Row,
    created: bool,
    actor_id: int,
    cause: str,
    reference: str,
    add: Any,
    already: str,
) -> bool:
    user_id = int(user["id"])
    role = str(user["role"])
    if role == Role.BREACH_HOLDER.value:
        # Held one before: carry over what the account was before its first.
        first = await repo.first_grant_of(conn, user_id)
        previous = first["previous_role"] if first else None
        account_created = bool(first["account_created"]) if first else created
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
    made = await add(previous, account_created)
    if made is None:
        raise Conflict(f"This person already holds access {already}", code="access_exists")
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
        detail={"reference": reference, "cause": cause},
    )
    fresh = await user_repo.by_id(conn, user_id)
    assert fresh is not None
    if role == Role.BREACH_HOLDER.value and str(fresh["status"]) == UserStatus.ACTIVE.value:
        # They already sign in: the waiting notice will do.
        return False
    await auth_service.invite_breach_holder(conn, user=fresh)
    return True


async def end(conn: Conn, grant_row: Row, *, cause: str, actor_id: int | None) -> None:
    """End one grant. The account is left as it is: the login stays, to read."""
    user_id = int(grant_row["user_id"])
    await repo.end_grant(conn, int(grant_row["access_id"]), cause=cause, ended_by=actor_id)
    await audit.record(
        conn,
        event=Event.USER_TEMPORARY_ACCESS_ENDED,
        entity_type="auth_user",
        entity_id=user_id,
        subject_user_id=user_id,
        actor_user_id=actor_id,
        detail={"reference": await _reference(conn, grant_row), "cause": cause},
    )


async def _reference(conn: Conn, grant_row: Row) -> str:
    if grant_row.get("reference"):
        return str(grant_row["reference"])
    if grant_row.get("holder_id"):
        from cmp.db.repositories import rights as rights_repo

        return await rights_repo.reference_of_holder(conn, int(grant_row["holder_id"])) or ""
    from cmp.db.repositories import breaches as breach_repo

    row = await breach_repo.by_breach_id(conn, int(grant_row["breach_id"]))
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


async def end_for_holder(conn: Conn, holder_id: int, *, cause: str, actor_id: int | None) -> int:
    """A rights ticket's temporary login ends: withdrawn, or sent to somebody else."""
    rows = await repo.open_holder_grants(conn, holder_id)
    for row in rows:
        await end(conn, row, cause=cause, actor_id=actor_id)
    return len(rows)


async def end_on_request(conn: Conn, request_id: int, *, actor_id: int | None) -> int:
    """The request closed: every rights ticket's temporary login on it ends."""
    rows = await repo.open_grants_on_request(conn, request_id)
    for row in rows:
        await end(conn, row, cause=REQUEST_CLOSED, actor_id=actor_id)
    return len(rows)


async def remove(conn: Conn, user: Row, *, actor_id: int) -> bool:
    """An administrator's End temporary access: the one off switch. Every open
    grant ends, and the account goes back to what it was before its first -
    switched off if made for a breach, its previous role otherwise - with the
    password cleared. True if the account was kept. The caller revokes every
    session after the commit."""
    user_id = int(user["id"])
    for row in await repo.open_grants_for_user(conn, user_id):
        await end(conn, row, cause=ACCOUNT_DEACTIVATED, actor_id=actor_id)
    first = await repo.first_grant_of(conn, user_id)
    await user_repo.clear_password(conn, user_id)
    if first is None or first["account_created"]:
        await user_repo.set_status(conn, user_id, UserStatus.DEACTIVATED.value)
        return False
    await user_repo.set_role(conn, user_id, str(first["previous_role"] or Role.DATA_SUBJECT.value))
    return True
