"""The account register's writes, made by an administrator.

Moved out of `api/routers/v1/users.py` (review 2026-10-01, ARCH-5): the routes
wrote through the repository and recorded their own audit rows. Services are
the only writers and the only callers of `audit.record()`
(`docs/architecture/layers.md`). The rules are unchanged.

Ending sessions stays with the caller, after the commit: a session revoked
inside a transaction that then rolled back would sign somebody out for a
change that never happened.
"""

from __future__ import annotations

from typing import Any

from cmp.auth.authentication import service as auth_service
from cmp.core.enums import UserStatus
from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.core.permissions import Role
from cmp.core.security import hash_password, new_token
from cmp.db.repositories import registry as registry_repo
from cmp.db.repositories import users as repo
from cmp.db.sql import Conn, unique_violation
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.infrastructure.dkms.blind import index_of
from cmp.validation import normalise_mobile

#: Roles that can hold a data source. Ownership is accountability for
#: collection, so it belongs to the people who do it: a DCO for a third party's
#: collection, an RCO for the R&D team's own.
SOURCE_OWNING_ROLES = frozenset({Role.DCO.value, Role.RCO.value})


def _known_role(role: str) -> None:
    if role not in {r.value for r in Role}:
        raise ValidationFailed("Unknown role", field="role")


async def create_staff(
    conn: Conn,
    *,
    full_name: str,
    email: str,
    role: str,
    username: str | None,
    mobile: str | None,
    organization_id: str | None,
    person_type: str | None,
    source_uuids: list[str],
) -> tuple[dict[str, Any], list[str]]:
    """Provision a staff account, with the sources it is accountable for.

    Returns the account and the codes of the sources assigned to it.

    A provisioned account starts with a random unusable password and is
    activated through the reset flow. Emailing an initial password puts a live
    credential in a mailbox.
    """
    _known_role(role)
    if role == Role.DATA_SUBJECT.value:
        raise ValidationFailed(
            "Data subjects register through a consent link, not here", field="role"
        )
    if source_uuids and role not in SOURCE_OWNING_ROLES:
        raise ValidationFailed(
            "Only a Data Collection Owner or an R&D Collection Owner can be "
            "accountable for a data source",
            field="source_uuids",
        )

    try:
        user = await repo.create(
            conn,
            full_name=full_name,
            email=email,
            role=role,
            username=username,
            mobile=mobile,
            organization_id=organization_id,
            person_type=person_type,
            status="pending",
            password_hash=hash_password(new_token(32)),
        )
    except Exception as exc:
        if unique_violation(exc):
            raise Conflict(
                "An account with that email, username or organisation id exists",
                code="user_exists",
            ) from exc
        raise

    assigned: list[str] = []
    for source_uuid in source_uuids:
        source = await registry_repo.source_by_uuid(conn, source_uuid)
        if not source:
            raise NotFound("Data source")
        # An in-house source needs an RCO and a third party's needs a DCO.
        # Checked here as well as on the source endpoint because this path
        # writes ownership too, and a rule enforced in one of two places is a
        # rule with a way round it.
        wanted = Role.RCO.value if source.get("is_in_house") else Role.DCO.value
        if role != wanted:
            raise ValidationFailed(
                f"{source['source_code']} is collected "
                + ("in-house" if source.get("is_in_house") else "by a third party")
                + f", so a {wanted} is accountable for it",
                field="source_uuids",
            )
        await registry_repo.set_source_owner(conn, source["source_id"], user["id"])
        assigned.append(source["source_code"])

    await audit.record(
        conn,
        event=Event.USER_CREATED,
        entity_type="auth_user",
        entity_id=user["id"],
        subject_user_id=user["id"],
        detail={"role": role, "sources": assigned},
    )

    # An account nobody has been told about is an account nobody can use, so
    # the last step of creating one is writing to its owner. Inside the
    # transaction on purpose: the message is queued only once the row is
    # committed, and a rollback sends nothing.
    await auth_service.invite_staff(conn, user=user)
    # A number typed here is a claim about somebody else's phone. It is sent a
    # code the way any new contact is, so the person learns the number is on
    # their account and can confirm it; until then it signs nobody in.
    if mobile:
        await auth_service.request_contact_code_on_behalf(conn, user=user, contact=str(mobile))
    return user, assigned


async def resend_invitation(conn: Conn, user_uuid: str) -> dict[str, Any]:
    """Only for an account that has not been activated.

    Sending one to an active account would be an administrator resetting a
    colleague's password from a distance; that is a different act, and its
    owner already has "Forgotten your password?".
    """
    user = await repo.require_by_uuid(conn, user_uuid)
    if user["status"] != UserStatus.PENDING.value:
        raise ValidationFailed(
            "That account is already activated. Its owner can set a new password "
            'with "Forgotten your password?" on the sign-in page.',
            field="status",
        )
    await auth_service.invite_staff(conn, user=user)
    return user


async def update_profile(
    conn: Conn,
    user_uuid: str,
    *,
    full_name: str | None,
    mobile: str | None,
    organization_id: str | None,
) -> dict[str, Any]:
    """Name, mobile, organisation id. A mobile that changes is unconfirmed
    again and is sent a code, as it would be had the person typed it."""
    user = await repo.require_by_uuid(conn, user_uuid)
    try:
        updated = await repo.update_profile(
            conn,
            user["id"],
            full_name=full_name,
            mobile=mobile,
            organization_id=organization_id,
        )
    except Exception as exc:
        if unique_violation(exc):
            raise Conflict("That mobile belongs to another account", code="contact_taken") from exc
        raise
    given = {"full_name": full_name, "mobile": mobile, "organization_id": organization_id}
    await audit.record(
        conn,
        event=Event.USER_UPDATED,
        entity_type="auth_user",
        entity_id=user["id"],
        subject_user_id=user["id"],
        detail={"fields": sorted(k for k, v in given.items() if v is not None)},
    )

    # "Changed" is decided on the blind index: the stored number is sealed
    # and differs on every write.
    mobile_changed = mobile is not None and index_of("mobile", normalise_mobile(mobile)) != (
        user.get("mobile_hash") or None
    )
    if mobile_changed:
        await audit.record(
            conn,
            event=Event.USER_CONTACT_CHANGED,
            entity_type="auth_user",
            entity_id=user["id"],
            subject_user_id=user["id"],
            detail={"medium": "mobile", "action": "set", "by": "administrator"},
        )
        await auth_service.request_contact_code_on_behalf(conn, user=updated, contact=str(mobile))
    return updated


async def change_role(
    conn: Conn, user_uuid: str, *, role: str, reason: str | None, actor_id: int
) -> dict[str, Any]:
    _known_role(role)
    user = await repo.require_by_uuid(conn, user_uuid)
    if user["role"] == role:
        raise Conflict("That user already holds this role", code="role_unchanged")
    if user["id"] == actor_id:
        # Self-demotion is how an organisation ends up with no administrator.
        raise Conflict("You cannot change your own role", code="self_role_change")

    await repo.set_role(conn, user["id"], role)
    await audit.record(
        conn,
        event=Event.USER_ROLE_CHANGED,
        entity_type="auth_user",
        entity_id=user["id"],
        subject_user_id=user["id"],
        detail={"from": user["role"], "to": role, "reason_given": bool(reason)},
    )
    return user


async def deactivate(conn: Conn, user_uuid: str, *, actor_id: int) -> tuple[dict[str, Any], bool]:
    """End a member of staff's access, or switch a data principal's account off.

    Returns the account and whether it was kept (as a data principal). Two
    different acts behind one button, and the row's role says which. For staff
    the role and the password go and the person stays, active, as a data
    principal - the consents they gave and the rights they hold are theirs
    under the Act whether or not they still work here. For a data principal
    there is nothing to keep them as, and the account is switched off.
    """
    user = await repo.require_by_uuid(conn, user_uuid)
    if user["id"] == actor_id:
        raise Conflict("You cannot deactivate your own account", code="self_deactivate")
    if user["role"] != Role.DATA_SUBJECT.value:
        await auth_service.end_staff_access(conn, user=user, actor_user_id=actor_id)
        return user, True
    await repo.set_status(conn, user["id"], "deactivated")
    await audit.record(
        conn,
        event=Event.USER_DEACTIVATED,
        entity_type="auth_user",
        entity_id=user["id"],
        subject_user_id=user["id"],
    )
    return user, False


async def reactivate(conn: Conn, user_uuid: str) -> dict[str, Any]:
    user = await repo.require_by_uuid(conn, user_uuid)
    await repo.set_status(conn, user["id"], "active")
    await audit.record(
        conn,
        event=Event.USER_REACTIVATED,
        entity_type="auth_user",
        entity_id=user["id"],
        subject_user_id=user["id"],
    )
    return user


async def record_forced_sign_out(conn: Conn, user_uuid: str) -> dict[str, Any]:
    """The record of an administrator ending somebody's sessions; the caller ends them."""
    user = await repo.require_by_uuid(conn, user_uuid)
    await audit.record(
        conn,
        event=Event.USER_SESSIONS_REVOKED,
        entity_type="auth_user",
        entity_id=user["id"],
        subject_user_id=user["id"],
        detail={"forced": True},
    )
    return user


async def reset_mfa(conn: Conn, user_uuid: str) -> dict[str, Any]:
    from cmp.auth.authentication import otp

    user = await repo.require_by_uuid(conn, user_uuid)
    await otp.discard(otp.Scope.STAFF_MFA, user_uuid)
    await audit.record(
        conn,
        event=Event.USER_MFA_RESET,
        entity_type="auth_user",
        entity_id=user["id"],
        subject_user_id=user["id"],
    )
    return user


# ------------------------------------------------- her own account, by herself
PERSON_TYPES = frozenset({"external", "employee", "ex_employee", "vendor"})


async def update_own_profile(
    conn: Conn,
    user_id: int,
    *,
    full_name: str | None,
    mobile: str | None,
    dob: str | None,
    secondary_email: str | None,
) -> dict[str, Any]:
    """Her own details. A contact she gives here is sent a code in the same
    request, and cannot sign her in until it comes back."""
    before = await repo.by_id(conn, user_id)
    if not before:
        raise NotFound("Account")
    try:
        updated = await repo.update_profile(
            conn,
            user_id,
            full_name=full_name,
            mobile=mobile,
            organization_id=None,
            dob=dob,
        )
    except Exception as exc:
        if unique_violation(exc):
            raise Conflict("That mobile belongs to another account", code="contact_taken") from exc
        raise

    # A code goes out whenever she gives a mobile that is still unconfirmed
    # afterwards - not only when the digits changed.
    #
    # Keying this on "changed" made the commonest case silent. An account often
    # already carries an unconfirmed number: an administrator set it on the
    # register, or she typed it and never answered the code. She opens the
    # account page, and the edit box is pre-filled with that very number - so
    # the natural act, opening it and pressing save, changed nothing, sent
    # nothing, and left her at a code box waiting for a message that was never
    # going to arrive.
    #
    # A number already confirmed is left alone: re-sending would unconfirm a
    # contact that has already proved itself.
    if mobile is not None and updated.get("mobile_verified_at") is None:
        if index_of("mobile", normalise_mobile(mobile)) != (before.get("mobile_hash") or None):
            await audit.record(
                conn,
                event=Event.USER_CONTACT_CHANGED,
                entity_type="auth_user",
                entity_id=user_id,
                subject_user_id=user_id,
                detail={"medium": "mobile", "action": "set"},
            )
        await auth_service.request_contact_code(conn, user=updated, contact=str(mobile))
    if secondary_email is not None:
        updated = await auth_service.add_secondary_email(conn, user=updated, email=secondary_email)
    await audit.record(
        conn,
        event=Event.USER_UPDATED,
        entity_type="auth_user",
        entity_id=user_id,
        subject_user_id=user_id,
        detail={"self_service": True},
    )
    return updated


async def change_own_person_type(
    conn: Conn, user_id: int, *, person_type: str, reason: str | None
) -> None:
    """`role` is authorisation, `person_type` is identity.

    They are separate columns because a DPO is *also* an employee. A type
    change must never alter permissions, and this does not touch `role`.
    """
    if person_type not in PERSON_TYPES:
        raise ValidationFailed("Unknown person type", field="person_type")
    user = await repo.by_id(conn, user_id)
    if not user:
        raise NotFound("Account")
    await repo.set_person_type(conn, user_id, person_type)
    await repo.record_person_type_change(
        conn,
        user_id=user_id,
        from_type=user["person_type"],
        to_type=person_type,
        reason=reason,
        changed_by=user_id,
    )
    await audit.record(
        conn,
        event=Event.USER_PERSON_TYPE_CHANGED,
        entity_type="person_type_history",
        entity_id=user_id,
        subject_user_id=user_id,
        detail={"from": user["person_type"], "to": person_type},
    )
