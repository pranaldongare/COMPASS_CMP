"""Every link the platform hands out opens a page that exists.

The audit and notification resolver builds links from a template per record
type - one for staff, one for the data principal. Two of them pointed at pages
that have never existed (`/profile` on the portal, `/cover` on the console), and
nothing noticed: a link to nowhere compiles, serialises and renders. This reads
the pages the two frontends actually have, from their source, and checks every
template against them.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from cmp.db.repositories.entities import _SPECS

ROOT = Path(__file__).resolve().parents[5]
FRONTEND = ROOT / "frontend"


def _routes(app: Path) -> list[list[str]]:
    """Each page.tsx as its URL segments; route groups dropped, [param] kept."""
    out = []
    for page in app.rglob("page.tsx"):
        parts = [p for p in page.relative_to(app).parent.parts if not p.startswith("(")]
        out.append(parts)
    return out


def _opens(href: str, routes: list[list[str]]) -> bool:
    path = href.split("?")[0].split("#")[0].strip("/")
    segments = [s for s in path.split("/") if s]
    for route in routes:
        if len(route) != len(segments):
            continue
        if all(
            r.startswith("[") or r == s or "{" in s for r, s in zip(route, segments, strict=True)
        ):
            return True
    return False


@pytest.fixture(scope="module")
def console() -> list[list[str]]:
    app = FRONTEND / "console" / "src" / "app"
    if not app.exists():
        pytest.skip("the console source is not beside the API")
    return _routes(app)


@pytest.fixture(scope="module")
def portal() -> list[list[str]]:
    app = FRONTEND / "portal" / "src" / "app"
    if not app.exists():
        pytest.skip("the portal source is not beside the API")
    return _routes(app)


def test_every_staff_link_opens_a_console_page(console: list[list[str]]) -> None:
    dead = [
        f"{name}: {spec.href}"
        for name, spec in _SPECS.items()
        if spec.href and not _opens(spec.href, console)
    ]
    assert not dead, f"links to pages the console does not have: {dead}"


def test_every_principal_link_opens_a_portal_page(portal: list[list[str]]) -> None:
    dead = [
        f"{name}: {spec.subject_href}"
        for name, spec in _SPECS.items()
        if spec.subject_href and not _opens(spec.subject_href, portal)
    ]
    assert not dead, f"links to pages the portal does not have: {dead}"


def test_the_route_reader_sees_the_known_pages(
    console: list[list[str]], portal: list[list[str]]
) -> None:
    """Guards the guard: a reader that found nothing would pass everything."""
    assert _opens("/requests/{uuid}", console) and _opens("/delegate", console)
    assert _opens("/account", portal) and not _opens("/profile", portal)
    assert re.match(r"^\[", next(r[-1] for r in console if r[:1] == ["requests"] and len(r) == 2))
