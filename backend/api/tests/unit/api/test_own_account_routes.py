"""Which sessions the routes under `/me` admit.

Two kinds of route share the prefix. The person's own row and contacts - read
it, change a name or a mobile, add a second email, ask for and answer a
confirmation code - belong to whoever is signed in, whichever hat the session
wears: a member of staff on the console is the same data principal as on the
portal (ADR 0013), and a mobile an administrator put on their account is
theirs to confirm from either. Everything that is about *being* a data
principal - consents, requests, disclosures, notifications - stays hers alone.

Read from the router rather than exercised over HTTP, because the distinction
is a property of the route table and a table is cheapest to check as one.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.routing import APIRoute

from cmp.api.dependencies.authentication import current_principal
from cmp.api.dependencies.authorization import RequireRole
from cmp.api.routers.v1.me import router
from cmp.core.permissions import Role

OWN_ACCOUNT = {
    ("GET", "/me"),
    ("PATCH", "/me"),
    ("POST", "/me/contacts/code"),
    ("POST", "/me/contact/verify"),
    ("DELETE", "/me/secondary-email"),
    ("POST", "/me/person-type"),
}


def _guards(route: APIRoute) -> list[Callable[..., Any]]:
    """Every dependency callable on the route, however deeply nested."""
    found: list[Callable[..., Any]] = []
    stack = [route.dependant]
    while stack:
        dependant = stack.pop()
        for sub in dependant.dependencies:
            if sub.call is not None:
                found.append(sub.call)
            stack.append(sub)
    return found


def _routes() -> list[tuple[str, str, APIRoute]]:
    out = []
    for route in router.routes:
        assert isinstance(route, APIRoute)
        for method in route.methods:
            out.append((method, route.path, route))
    return out


def test_the_own_account_routes_admit_every_full_session() -> None:
    seen = set()
    for method, path, route in _routes():
        if (method, path) not in OWN_ACCOUNT:
            continue
        seen.add((method, path))
        guards = _guards(route)
        assert current_principal in guards, f"{method} {path} does not require a session"
        gates = [g for g in guards if isinstance(g, RequireRole)]
        assert not gates, f"{method} {path} is gated by role: {gates}"
    assert seen == OWN_ACCOUNT, f"routes missing from the table: {OWN_ACCOUNT - seen}"


def test_everything_else_under_me_stays_the_data_principals_alone() -> None:
    for method, path, route in _routes():
        if (method, path) in OWN_ACCOUNT:
            continue
        gates = [g for g in _guards(route) if isinstance(g, RequireRole)]
        assert gates, f"{method} {path} has no role gate"
        for gate in gates:
            assert gate.roles == frozenset({Role.DATA_SUBJECT}), f"{method} {path}: {gate.roles}"
