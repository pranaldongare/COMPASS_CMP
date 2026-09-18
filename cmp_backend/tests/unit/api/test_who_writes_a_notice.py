"""Which acts on a notice belong to whom.

The R&D User still brings the notice, because they are the one who knows what
the study collects. They bring it as a filled-in document, or by picking one the
Privacy Office has already approved. What they no longer do is compose one: the
wording, the purposes attached to it and the text of each rendition are the
office's, and a notice assembled by the author and then reviewed by the office
was a review of somebody else's transcription.

The division is by *act*, not by resource, so both guards appear on notice
routes and neither the permission matrix nor a glance at the module tells you
which is which. This file is that answer, and it fails if a route moves sides
without somebody deciding to move it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.routing import APIRoute

from cmp.api.dependencies.authorization import RequireResource, RequireRole
from cmp.api.routers.v1.notices import router
from cmp.core.permissions import Role

#: What an author may do: bring a document, re-bring a corrected one, or start
#: from a notice the office has approved.
THE_AUTHORS = {
    ("POST", "/projects/{project_uuid}/notices/import"),
    ("POST", "/projects/{project_uuid}/notices/import/validate"),
    ("POST", "/projects/{project_uuid}/notices/copy"),
}

#: What only the office may do. Composing, and everything that changes what the
#: notice says or carries, plus the two acts that were always theirs.
THE_OFFICES = {
    ("POST", "/projects/{project_uuid}/notices"),
    ("PUT", "/notices/{notice_uuid}"),
    ("POST", "/notices/{notice_uuid}/purposes"),
    ("PUT", "/notices/{notice_uuid}/purposes/{purpose_uuid}"),
    ("DELETE", "/notices/{notice_uuid}/purposes/{purpose_uuid}"),
    ("POST", "/notices/{notice_uuid}/languages"),
    ("PUT", "/notices/{notice_uuid}/languages/{code}"),
    ("POST", "/notices/{notice_uuid}/languages/{code}/approve"),
    ("POST", "/notices/{notice_uuid}/publish"),
    ("POST", "/notices/{notice_uuid}/purposes/activate"),
}


def _guards(route: APIRoute) -> list[Callable[..., Any]]:
    found: list[Callable[..., Any]] = []
    stack = [route.dependant]
    while stack:
        dependant = stack.pop()
        for sub in dependant.dependencies:
            if sub.call is not None:
                found.append(sub.call)
            stack.append(sub)
    return found


def _writes() -> dict[tuple[str, str], list[Callable[..., Any]]]:
    out: dict[tuple[str, str], list[Callable[..., Any]]] = {}
    for route in router.routes:
        assert isinstance(route, APIRoute)
        for method in route.methods:
            if method in ("GET", "HEAD", "OPTIONS"):
                continue
            out[(method, route.path)] = _guards(route)
    return out


def test_the_office_alone_composes_a_notice() -> None:
    writes = _writes()
    for key in THE_OFFICES:
        assert key in writes, f"{key} is not a route any more"
        gates = [g for g in _guards_of(writes, key) if isinstance(g, RequireRole)]
        assert gates, f"{key} has no role gate"
        for gate in gates:
            assert gate.roles == frozenset({Role.DPO}), f"{key} admits {gate.roles}"


def test_the_author_still_brings_one() -> None:
    writes = _writes()
    for key in THE_AUTHORS:
        assert key in writes, f"{key} is not a route any more"
        guards = _guards_of(writes, key)
        assert any(isinstance(g, RequireResource) for g in guards), f"{key} lost its guard"
        assert not [g for g in guards if isinstance(g, RequireRole)], (
            f"{key} became role-gated; an author can no longer bring a notice"
        )


def test_every_write_is_on_one_side_or_the_other() -> None:
    """A new route is a decision somebody has to take, not a default."""
    assert set(_writes()) == THE_AUTHORS | THE_OFFICES


def _guards_of(
    writes: dict[tuple[str, str], list[Callable[..., Any]]], key: tuple[str, str]
) -> list[Callable[..., Any]]:
    return writes[key]
