"""Consent records and the registry's workbooks over HTTP.

Operations the inventory listed only from increment 8: the consent record as
a PDF, for the office (ADR 0031) and for the person it is about, and the
blank workbooks the administrator fills in for a registry import
(46cccef). Each answers its file to the role that may have it and nothing
to one that may not.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.http.conftest import SessionFactory
from tests.http.contract import call
from tests.http.world import World, build


@pytest.fixture(scope="module")
def _world_box() -> dict[str, Any]:
    return {}


@pytest.fixture
async def world(
    http: httpx.AsyncClient, session_for: SessionFactory, queued: Any, _world_box: dict[str, Any]
) -> World:
    if "w" not in _world_box:
        _world_box["w"] = await build(http, session_for, queued)
    return _world_box["w"]


async def test_the_consent_record_is_a_pdf_for_the_office_and_for_her(
    http: httpx.AsyncClient, world: World
) -> None:
    office = await call(
        http,
        "GET",
        f"/consents/{world.consent_uuid}/record",
        template="/consents/{consent_uuid}/record",
        session=world.dpo,
    )
    assert office.headers["content-type"].startswith("application/pdf")
    assert office.content.startswith(b"%PDF")
    hers = await call(
        http,
        "GET",
        f"/me/consents/{world.consent_uuid}/record",
        template="/me/consents/{consent_uuid}/record",
        session=world.principal,
    )
    assert hers.content.startswith(b"%PDF")
    # The R&D User is not among the roles that may have it.
    await call(
        http,
        "GET",
        f"/consents/{world.consent_uuid}/record",
        template="/consents/{consent_uuid}/record",
        session=world.rnd,
        expect=403,
    )


@pytest.mark.parametrize("kind", ["processors", "sources"])
async def test_the_import_workbook_is_the_administrator_s(
    http: httpx.AsyncClient, world: World, kind: str
) -> None:
    blank = await call(
        http, "GET", f"/{kind}/import/template", session=world.admin, params={"sample": "true"}
    )
    assert "spreadsheetml" in blank.headers["content-type"]
    assert blank.content.startswith(b"PK")
    await call(http, "GET", f"/{kind}/import/template", session=world.dpo, expect=403)
