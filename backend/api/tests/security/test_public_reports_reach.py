"""Who reaches the reports a person sent through the public link, through her
rights request (0065).

The erasure names no report: it finds them again by her proved addresses, so a
caller cannot point it at somebody else's. Only the rights writers reach the
route at all, and of them only the officers are shown the reports or may erase
them; the administrator, who may hold a request about the office, is told they
are not there. Nothing is found before identity is verified, and erasing one
person leaves every other report as it was.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute

from cmp.api.dependencies.authorization import RequireResource
from cmp.api.routers.v1 import rights
from cmp.auth.authorization import resources
from cmp.auth.identity.principal import Principal
from cmp.core.errors import Conflict, Forbidden, NotFound
from cmp.core.permissions import Role
from cmp.domain.rights import public_reports, service
from tests.integration.test_public_reports_and_rights import (
    _dismissed,
    _from_the_form,
    _person,
    _report_row,
    _request,
)

PATH = "/requests/{request_uuid}/public-reports/erase"
WRITERS = (Role.DPO, Role.LEGAL, Role.ADMIN)


def _route() -> APIRoute:
    [route] = [r for r in rights.router.routes if isinstance(r, APIRoute) and r.path == PATH]
    return route


def _gate() -> RequireResource:
    found: list[Callable[..., Any]] = []
    stack = [_route().dependant]
    while stack:
        dependant = stack.pop()
        for sub in dependant.dependencies:
            if sub.call is not None:
                found.append(sub.call)
            stack.append(sub)
    [gate] = [g for g in found if isinstance(g, RequireResource)]
    return gate


def _principal(role: Role) -> Principal:
    return Principal(user_id=1, uuid=str(uuid4()), role=role, session=MagicMock())


def test_the_erasure_names_the_request_and_nothing_else() -> None:
    route = _route()
    assert route.methods == {"POST"}
    assert [p.name for p in route.dependant.path_params] == ["request_uuid"]
    assert route.dependant.query_params == [] and route.dependant.body_params == []


def test_it_is_a_write_on_the_request() -> None:
    gate = _gate()
    assert (gate.resource, gate.write) == (resources.RIGHTS_REQUEST, True)


@pytest.mark.parametrize("role", [r for r in Role if r not in WRITERS])
async def test_every_role_but_the_rights_writers_is_refused(role: Role) -> None:
    with pytest.raises(Forbidden):
        await _gate()(_principal(role))


def test_nothing_shown_is_the_office_s_own_note_or_a_row_s_key() -> None:
    fields = set(rights.PublicReportOut.model_fields)
    assert not fields & {
        "dismissal_reason",
        "dismissed_by",
        "dismissed_by_name",
        "report_id",
        "reporter_email_hash",
        "reporter_erased_by",
        "reporter_erased_request_id",
    }


@pytest.mark.integration
async def test_the_administrator_is_shown_none_and_told_they_are_not_there(
    conn: Any, seeded: dict[str, Any], redis_conn: Any
) -> None:
    person = await _person(conn)
    mine = await _dismissed(conn, seeded, person["email"])
    row = await _request(conn, seeded, person)
    await conn.execute(
        "UPDATE rights_request SET about_dpo = true WHERE request_id = %s",
        (int(row["request_id"]),),
    )
    admin = int(seeded["users"]["admin"]["id"])
    row = await service.require(conn, str(row["request_uuid"]), role=Role.ADMIN, user_id=admin)
    assert await public_reports.view(conn, row, role=Role.ADMIN) is None
    with pytest.raises(NotFound):
        await public_reports.erase(conn, row, role=Role.ADMIN, actor_id=admin)
    assert (await _report_row(conn, mine))["reporter_email"] is not None


@pytest.mark.integration
async def test_an_unverified_request_finds_nothing(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Typing her address on the public form is not her: until the code comes
    back, nothing is found and nothing is erased."""
    monkeypatch.setattr(service, "_dispatch", lambda *a: None)
    person = await _person(conn)
    mine = await _dismissed(conn, seeded, person["email"])
    row = await _from_the_form(conn, seeded, redis_conn, person["email"])
    found = await public_reports.found(conn, row)
    assert found["looked"] is False and found["open"] == []
    shown = await public_reports.view(conn, row, role=Role.DPO)
    assert shown is not None and shown["items"] == [] and shown["may_erase"] is False
    with pytest.raises(Conflict) as refused:
        await public_reports.erase(conn, row, role=Role.DPO, actor_id=seeded["users"]["dpo"]["id"])
    assert refused.value.code == "request_not_started"
    assert (await _report_row(conn, mine))["reporter_email"] is not None


@pytest.mark.integration
async def test_one_person_s_erasure_leaves_another_s_row_identical(
    conn: Any, seeded: dict[str, Any], redis_conn: Any
) -> None:
    person = await _person(conn)
    await _dismissed(conn, seeded, person["email"])
    neighbour = await _person(conn)
    theirs = await _dismissed(conn, seeded, neighbour["email"])
    before = await _report_row(conn, theirs)
    await public_reports.erase(
        conn,
        await _request(conn, seeded, person),
        role=Role.DPO,
        actor_id=seeded["users"]["dpo"]["id"],
    )
    assert await _report_row(conn, theirs) == before
