"""The world is built through the API, and every write on the way was checked."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.conftest import plain
from tests.http.conftest import SessionFactory
from tests.http.contract import call
from tests.http.world import World, build


@pytest.fixture
async def world(http: httpx.AsyncClient, session_for: SessionFactory, queued: Any) -> World:
    return await build(http, session_for, queued)


async def test_the_world_stands(world: World, committed: Any) -> None:
    """Every id the later files rely on exists, and the principal's row is sealed."""
    assert world.project_uuid and world.notice_uuid and world.link_token and world.consent_uuid
    from cmp.db.sql import fetch_one

    row = await fetch_one(
        committed,
        "SELECT full_name, email, mobile, organization_id FROM auth_user WHERE uuid = %s",
        (world.principal.uuid,),
    )
    assert row is not None
    for column, expected in (
        ("mobile", world.principal_mobile),
        ("email", world.principal_email),
    ):
        assert str(row[column]).startswith("SE::"), f"{column} is sealed in the row"
        assert plain(row[column]) == expected, f"{column} opens to what she typed"
    assert str(row["full_name"]).startswith("SE::") and str(row["organization_id"]).startswith(
        "SE::"
    )


async def test_her_consent_carries_a_sealed_address(world: World, committed: Any) -> None:
    from cmp.db.sql import fetch_one

    row = await fetch_one(
        committed,
        "SELECT ip_address FROM consent_artefact WHERE consent_uuid = %s",
        (world.consent_uuid,),
    )
    assert row is not None and str(row["ip_address"]).startswith("SE::")
    assert plain(row["ip_address"]) == "127.0.0.1"


async def test_the_export_opened_her_columns_for_the_file(
    world: World, http: httpx.AsyncClient
) -> None:
    """The CSV is for whoever collects; the sealed columns open on the way into it."""
    csv = await call(
        http,
        "GET",
        f"/exports/{world.export_uuid}/download",
        template="/exports/{export_uuid}/download",
        session=world.dco,
        check_sealed=False,
    )
    text = csv.text
    assert world.principal_email in text and "SE::" not in text
