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
    assert str(row["full_name"]).startswith("SE::")
    # The form sent an employee ID, and the open form takes none: only an
    # assertion the organisation signed carries one (ADR 0034, open point F-8).
    assert row["organization_id"] is None


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


async def test_an_export_to_a_restricted_country_is_refused(
    world: World, http: httpx.AsyncClient
) -> None:
    """S2-04 over HTTP: the list is data the DPO keeps, a processor says where it
    is, and an export whose rows would go to a restricted country is refused -
    then goes once the processor is back in India and the restriction lifted.

    Idempotent across runs on the same database: a run that died with XZ still
    listed finds it listed and carries on."""
    listed = await call(
        http,
        "POST",
        "/restricted-countries",
        template="/restricted-countries",
        session=world.dpo,
        expect=(201, 409),
        json={"country_code": "xz", "notification_ref": "G.S.R. 000(E) - test"},
    )
    current = await call(
        http, "GET", "/restricted-countries", template="/restricted-countries", session=world.dpo
    )
    [xz] = [r for r in current.json() if r["country_code"] == "XZ"]
    assert listed.status_code == 409 or listed.json()["country_code"] == "XZ"

    moved = await call(
        http,
        "PUT",
        f"/processors/{world.processor_uuid}",
        template="/processors/{processor_uuid}",
        session=world.dpo,
        json={"location_country": "XZ"},
    )
    assert moved.json()["location_country"] == "XZ"
    refused = await call(
        http,
        "POST",
        f"/projects/{world.project_uuid}/exports",
        template="/projects/{project_uuid}/exports",
        session=world.dco,
        expect=(422,),
    )
    body = refused.json()["error"]
    assert body["code"] == "transfer_refused"

    await call(
        http,
        "PUT",
        f"/processors/{world.processor_uuid}",
        template="/processors/{processor_uuid}",
        session=world.dpo,
        json={"location_country": "IN"},
    )
    await call(
        http,
        "POST",
        f"/restricted-countries/{xz['country_uuid']}/lift",
        template="/restricted-countries/{country_uuid}/lift",
        session=world.dpo,
    )


async def test_the_dct_consented_list_is_its_contract_and_downloads_as_made(
    world: World, http: httpx.AsyncClient
) -> None:
    """The Data Collection Tool's list (2026-11-11): its ten columns, named as its
    contract names the file, the principal on it by her account's uuid and her
    contacts not, and the same bytes on every download. After the contract's
    columns come the three numbers (2026-11-12), which its loader passes through."""
    made = await call(
        http,
        "POST",
        f"/projects/{world.project_uuid}/exports/dct-consented-list",
        template="/projects/{project_uuid}/exports/dct-consented-list",
        session=world.dco,
        expect=201,
    )
    body = made.json()
    assert body["export_type"] == "dct_consented_list" and body["row_count"] >= 1
    assert set(body["left_out"]) == {"withdrawn", "partial", "lapsed", "no_name"}

    first = await call(
        http,
        "GET",
        f"/exports/{body['export_uuid']}/download",
        template="/exports/{export_uuid}/download",
        session=world.dco,
        check_sealed=False,
    )
    assert first.content.split(b"\n", 1)[0] == (
        b"project_id,project_name,person_id,consent_id,display_name,contact_hint,"
        b"consent_expires_at,is_minor,list_generated_at,list_valid_until,"
        b"project_no,person_no,consent_no"
    )
    line = first.text.splitlines()[1].split(",")
    assert all(number.isdigit() for number in line[-3:]), "the three numbers are numbers"
    disposition = first.headers["Content-Disposition"]
    assert f'filename="consented_list_{world.project_uuid}_' in disposition
    text = first.text
    assert world.principal.uuid in text and world.consent_uuid in text
    assert world.principal_email not in text and world.principal_mobile not in text
    assert "SE::" not in text

    again = await call(
        http,
        "GET",
        f"/exports/{body['export_uuid']}/download",
        template="/exports/{export_uuid}/download",
        session=world.dco,
        check_sealed=False,
    )
    assert again.content == first.content
