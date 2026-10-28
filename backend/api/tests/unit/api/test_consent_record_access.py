"""Who may take a consent record away as a PDF (2026-10-15).

Staff who read consents in full - the DPO, a DCO, a DCO Admin, an RCO, and on
the HR track the Legal PoC and an HR PoC (ADR 0033), each in their own scope -
and the person, for her own. Not the R&D User, whose access to
consents is the project's summary counts: a PDF names the person.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.routing import APIRoute

from cmp.api.dependencies.authorization import RequireRole
from cmp.api.routers.v1.consents import router as consents
from cmp.api.routers.v1.me import router as me
from cmp.core.permissions import Role

STAFF = frozenset({Role.DPO, Role.DCO, Role.DCO_ADMIN, Role.RCO, Role.LEGAL, Role.HR_USER})


def _guards(router: Any, path: str) -> list[Callable[..., Any]]:
    """Every guard on every route at `path` - the GET and POST of the archive alike."""
    routes = [r for r in router.routes if isinstance(r, APIRoute) and r.path == path]
    assert routes, f"{path} is not a route"
    found: list[Callable[..., Any]] = []
    stack = [r.dependant for r in routes]
    while stack:
        dependant = stack.pop()
        for sub in dependant.dependencies:
            if sub.call is not None:
                found.append(sub.call)
            stack.append(sub)
    return found


def test_staff_records_admit_the_consent_readers_and_not_the_rnd_user() -> None:
    for path in ("/consents/{consent_uuid}/record", "/consent-records"):
        gates = [g for g in _guards(consents, path) if isinstance(g, RequireRole)]
        methods = {
            m
            for r in consents.routes
            if isinstance(r, APIRoute) and r.path == path
            for m in r.methods
        }
        assert len(gates) == len(methods), f"{path}: a method without its role gate"
        assert all(g.roles == STAFF for g in gates), path
        assert Role.RND_USER not in gates[0].roles


def test_her_own_record_is_hers_under_the_data_principal_gate() -> None:
    """The same gate as every other /me/consents route."""
    gate = [
        g for g in _guards(me, "/me/consents/{consent_uuid}/record") if isinstance(g, RequireRole)
    ]
    others = [g for g in _guards(me, "/me/consents/{consent_uuid}") if isinstance(g, RequireRole)]
    assert gate and others
    assert gate[0].roles == others[0].roles


def test_the_archive_is_not_read_as_a_consent_uuid() -> None:
    paths = [r.path for r in consents.routes if isinstance(r, APIRoute)]
    assert "/consent-records" in paths
