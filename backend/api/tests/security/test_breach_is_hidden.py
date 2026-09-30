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
