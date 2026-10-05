"""The breach register is the DPO's, and invisible to everyone else (S3-01).

A 403 on `/breaches/{uuid}` would tell a caller walking uuids that the uuid is
a breach - which is the fact the grant withholds. So the breach guards answer
every other role 404, as a row out of scope does (ADR 0004). The HTTP suite
proves the same on the wire.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from cmp.api.dependencies.authorization import RequireResource
from cmp.auth.authorization import resources
from cmp.auth.authorization.evaluator import can_read, can_write
from cmp.auth.identity.principal import Principal
from cmp.core.errors import Forbidden, NotFound
from cmp.core.permissions import Role

OTHERS = [r for r in Role if r is not Role.DPO]


def _principal(role: Role) -> Principal:
    return Principal(user_id=1, uuid=str(uuid4()), role=role, session=MagicMock())


def test_only_the_dpo_holds_the_register() -> None:
    assert can_read(resources.BREACH, Role.DPO) and can_write(resources.BREACH, Role.DPO)
    for role in OTHERS:
        assert not can_read(resources.BREACH, role), role


@pytest.mark.parametrize("role", OTHERS)
@pytest.mark.parametrize("write", [False, True])
async def test_every_other_role_is_told_it_is_not_there(role: Role, write: bool) -> None:
    guard = RequireResource(resources.BREACH, write=write, hidden=True)
    with pytest.raises(NotFound):
        await guard(_principal(role))


@pytest.mark.parametrize("write", [False, True])
async def test_the_dpo_passes(write: bool) -> None:
    guard = RequireResource(resources.BREACH, write=write, hidden=True)
    principal: Any = await guard(_principal(Role.DPO))
    assert principal.role is Role.DPO


async def test_an_ordinary_resource_still_answers_403() -> None:
    """`hidden` is the breach's, not a change to every guard."""
    with pytest.raises(Forbidden):
        await RequireResource(resources.LEGAL_HOLD)(_principal(Role.DCO))


# ------------------------------------------------------------ breach tickets (S3-08)

STAFF = [r for r in Role if r is not Role.DATA_SUBJECT]


@pytest.mark.parametrize("role", STAFF)
def test_every_member_of_staff_may_hold_a_breach_ticket_and_only_their_own(role: Role) -> None:
    """`breach_ticket` is OWN for every staff role - the same rows as `ticket` -
    and OWN is the holder in the WHERE clause."""
    from cmp.auth.authorization.evaluator import scope_of

    assert can_read(resources.BREACH_TICKET, role) and can_write(resources.BREACH_TICKET, role)
    assert scope_of(resources.BREACH_TICKET, role).value == "own"


def test_a_data_principal_holds_none() -> None:
    assert not can_read(resources.BREACH_TICKET, Role.DATA_SUBJECT)


@pytest.mark.parametrize("role", [r for r in OTHERS if r is not Role.DATA_SUBJECT])
async def test_a_holder_is_still_told_the_register_is_not_there(role: Role) -> None:
    """Holding a ticket opens the ticket, not the breach: the managing routes are
    `breach`, and they answer every holder but the DPO 404."""
    assert can_read(resources.BREACH_TICKET, role)
    with pytest.raises(NotFound):
        await RequireResource(resources.BREACH, hidden=True)(_principal(role))


# ---------------------------------------------------- the breach-only login (S3-09)


def test_the_breach_only_login_holds_its_tickets_and_nothing_else() -> None:
    from cmp.core.permissions import MATRIX, nav_for

    granted = sorted(r for r, grants in MATRIX.items() if Role.BREACH_HOLDER in grants)
    assert granted == ["breach_ticket", "ticket"]
    assert list(nav_for(Role.BREACH_HOLDER)) == ["tickets", "notifications", "profile"]


@pytest.mark.parametrize("write", [False, True])
async def test_the_breach_only_login_is_told_the_register_is_not_there(write: bool) -> None:
    with pytest.raises(NotFound):
        await RequireResource(resources.BREACH, write=write, hidden=True)(
            _principal(Role.BREACH_HOLDER)
        )


async def test_the_breach_only_login_is_not_staff_for_staff_wide_routes() -> None:
    """Delegation and the collection-owner lookup are behind RequireStaff."""
    from cmp.api.dependencies.authorization import RequireRole
    from cmp.api.dependencies.common import STAFF_ROLES

    with pytest.raises(Forbidden):
        await RequireRole(*STAFF_ROLES)(_principal(Role.BREACH_HOLDER))


def test_the_breach_only_login_always_steps_up() -> None:
    """Even under a configured list written before the role existed."""
    from cmp.auth.authorization.roles import requires_mfa

    assert requires_mfa(Role.BREACH_HOLDER, configured=("dpo", "admin"))


async def test_no_picker_offers_a_breach_only_login(conn: Any, seeded: dict[str, Any]) -> None:
    from cmp.db.repositories import users as user_repo

    await conn.execute(
        "UPDATE auth_user SET role = 'breach_holder' WHERE id = %s",
        (seeded["users"]["rnd_user"]["id"],),
    )
    staff = await user_repo.staff_directory(conn)
    assert str(seeded["users"]["rnd_user"]["uuid"]) not in {str(s["uuid"]) for s in staff}
