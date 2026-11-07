"""The organisation's board list, as the window reads it and the officers hear of it (0064).

The window reads the list through a breach, so only the officers reach it, and
every other role is told the breach is not there. Only those who keep the list
under Breach settings mark an entry mandatory. The officers' mail when the list
changes names the address and no breach, so it may cross the wall between the
offices, and nothing the list serves carries its row's key or its blind index.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute

from cmp.api.dependencies.authorization import RequireResource
from cmp.api.routers.v1 import breach_settings, breaches
from cmp.auth.authorization import resources
from cmp.auth.authorization.evaluator import can_write
from cmp.auth.identity.principal import Principal
from cmp.core.errors import Forbidden, NotFound
from cmp.core.messages import ATTACHABLE, COPYABLE, Message, junction
from cmp.core.permissions import Role

OFFICERS = (Role.DPO, Role.LEGAL)
KEEPERS = (Role.ADMIN, Role.DPO, Role.LEGAL)


def _principal(role: Role) -> Principal:
    return Principal(user_id=1, uuid=str(uuid4()), role=role, session=MagicMock())


def _guard(router: Any, method: str, path: str) -> RequireResource:
    [route] = [
        r
        for r in router.routes
        if isinstance(r, APIRoute) and r.path == path and method in r.methods
    ]
    found: list[Callable[..., Any]] = []
    stack = [route.dependant]
    while stack:
        dependant = stack.pop()
        for sub in dependant.dependencies:
            if sub.call is not None:
                found.append(sub.call)
            stack.append(sub)
    [gate] = [g for g in found if isinstance(g, RequireResource)]
    return gate


WINDOW = _guard(breaches.router, "GET", "/breaches/{breach_uuid}/reports/recipients")
MARK = _guard(
    breach_settings.router, "PUT", "/breach-settings/board-recipients/{recipient_uuid}/mandatory"
)


def test_the_window_reads_the_list_behind_the_breach() -> None:
    assert (WINDOW.resource, WINDOW.write, WINDOW.hidden) == (resources.BREACH, False, True)


@pytest.mark.parametrize("role", [r for r in Role if r not in OFFICERS])
async def test_every_other_role_is_told_the_breach_is_not_there(role: Role) -> None:
    with pytest.raises(NotFound):
        await WINDOW(_principal(role))


@pytest.mark.parametrize("role", OFFICERS)
async def test_the_officers_read_it(role: Role) -> None:
    principal: Any = await WINDOW(_principal(role))
    assert principal.role is role


def test_only_those_who_keep_the_list_mark_an_entry() -> None:
    assert (MARK.resource, MARK.write) == (resources.BREACH_SETTINGS, True)
    assert sorted(r.value for r in Role if can_write(resources.BREACH_SETTINGS, r)) == sorted(
        r.value for r in KEEPERS
    )


@pytest.mark.parametrize("role", [r for r in Role if r not in KEEPERS])
async def test_nobody_else_marks_one(role: Role) -> None:
    with pytest.raises(Forbidden):
        await MARK(_principal(role))


def test_the_officers_mail_names_no_breach_and_is_copied_to_nobody() -> None:
    said = junction(Message.BREACH_BOARD_LIST_CHANGED)
    assert said.variable_names == {
        "actor_name",
        "actor_role",
        "change",
        "recipient_name",
        "recipient_email",
        "changed_at",
        "console_url",
        "organisation",
    }
    assert not any("breach" in v or "reference" in v for v in said.variable_names)
    assert said.key not in COPYABLE and said.key not in ATTACHABLE


@pytest.mark.parametrize(
    "model",
    [
        breaches.BreachBoardListEntryOut,
        breaches.BreachDocumentMailRecipientOut,
        breach_settings.BoardRecipientOut,
    ],
    ids=lambda m: m.__name__,
)
def test_nothing_served_carries_the_rows_key_or_its_index(model: Any) -> None:
    assert not set(model.model_fields) & {"recipient_id", "email_hash", "addressee_id"}
