"""The registry imports are the administrator's alone (2026-10-14).

Filling the registry from a spreadsheet creates processors and sources in bulk,
under any processor, so it is gated on the role and not on the matrix: a DCO
Admin may register a source one at a time, but not fifty from a file.
"""

from __future__ import annotations

from fastapi.routing import APIRoute

from cmp.api.dependencies.authorization import RequireRole
from cmp.api.routers.v1.registry import router
from cmp.core.permissions import Role

IMPORTS = {
    ("GET", "/processors/import/template"),
    ("POST", "/processors/import/check"),
    ("POST", "/processors/import"),
    ("GET", "/sources/import/template"),
    ("POST", "/sources/import/check"),
    ("POST", "/sources/import"),
}


def _gates() -> dict[tuple[str, str], list[RequireRole]]:
    out: dict[tuple[str, str], list[RequireRole]] = {}
    for route in router.routes:
        assert isinstance(route, APIRoute)
        found: list[RequireRole] = []
        stack = [route.dependant]
        while stack:
            dependant = stack.pop()
            for sub in dependant.dependencies:
                if isinstance(sub.call, RequireRole):
                    found.append(sub.call)
                stack.append(sub)
        for method in route.methods or ():
            out[(method, route.path)] = found
    return out


def test_every_import_route_admits_the_administrator_alone() -> None:
    gates = _gates()
    for key in IMPORTS:
        assert key in gates, f"{key} is not a route any more"
        assert gates[key], f"{key} has no role gate"
        for gate in gates[key]:
            assert gate.roles == frozenset({Role.ADMIN}), f"{key} admits {gate.roles}"


def test_import_is_not_read_as_a_uuid() -> None:
    """`/processors/import/...` is declared before `/processors/{processor_uuid}/...`."""
    paths = [r.path for r in router.routes if isinstance(r, APIRoute)]
    assert paths.index("/processors/import/template") < paths.index(
        "/processors/{processor_uuid}/respondents"
    )
    assert paths.index("/sources/import/template") < paths.index("/sources/{source_uuid}/batches")
