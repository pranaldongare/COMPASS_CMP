"""A breach's people from a list somebody sends us, over HTTP (2026-10-07).

The DPO downloads the template, checks a filled-in file (nothing written),
takes it, and reads back the contacts with no account - name, email and
mobile sealed - and the upload, whose file name is sealed too. A spreadsheet
is refused with how to save it as CSV. Every other role is told the breach is
not there.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest

from tests.conftest import plain
from tests.http.conftest import SessionFactory
from tests.http.contract import call
from tests.http.world import World, build

B = "/breaches/{breach_uuid}"
PEOPLE = b"name,email,mobile\nAsha Rao,asha.list@example.org,+91 98765 40001\nRavi,,+919876540002\n"


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


async def _breach(http: httpx.AsyncClient, world: World) -> str:
    made = await call(
        http,
        "POST",
        "/breaches",
        session=world.dpo,
        expect=201,
        json={
            "title": "A contact list sent to the wrong address",
            "detected_at": (datetime.now(UTC) - timedelta(minutes=30)).isoformat(),
            "location_kind": "platform",
        },
    )
    uuid = str(made.json()["breach_uuid"])
    await call(
        http,
        "POST",
        f"/breaches/{uuid}/determinations",
        template=f"{B}/determinations",
        session=world.dpo,
        json={
            "outcome": "yes",
            "reasoning": "Names and mobiles",
            "became_aware_at": (datetime.now(UTC) - timedelta(minutes=20)).isoformat(),
        },
    )
    return uuid


class TestBreachLists:
    async def test_the_dpo_checks_and_takes_a_list_of_people(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        uuid = await _breach(http, world)
        template = await call(
            http,
            "GET",
            f"/breaches/{uuid}/affected/upload/template?kind=contacts",
            template=f"{B}/affected/upload/template",
            session=world.dpo,
        )
        assert template.text.lstrip("﻿").startswith("name,email,mobile")
        assert "attachment" in template.headers["Content-Disposition"]

        checked = await call(
            http,
            "POST",
            f"/breaches/{uuid}/affected/upload/check",
            template=f"{B}/affected/upload/check",
            session=world.dpo,
            data={"kind": "contacts"},
            files={"file": ("people.csv", PEOPLE, "text/csv")},
        )
        assert checked.json()["new_contacts"] == 2 and checked.json()["errors"] == []

        taken = await call(
            http,
            "POST",
            f"/breaches/{uuid}/affected/upload",
            template=f"{B}/affected/upload",
            session=world.dpo,
            expect=201,
            data={"kind": "contacts"},
            # Windows labels a .csv as Excel's.
            files={"file": ("people.csv", PEOPLE, "application/vnd.ms-excel")},
        )
        assert taken.json()["new_contacts"] == 2 and taken.json()["upload_uuid"]

        listed = await call(
            http,
            "GET",
            f"/breaches/{uuid}/affected/contacts",
            template=f"{B}/affected/contacts",
            session=world.dpo,
        )
        body = listed.json()
        assert body["total"] == 2
        first = body["contacts"][0]
        assert str(first["email"]).startswith("SE::")
        assert plain(first["email"]) == "asha.list@example.org"
        assert str(body["uploads"][0]["file_name"]).startswith("SE::")

        notices = await call(
            http,
            "GET",
            f"/breaches/{uuid}/notices",
            template=f"{B}/notices",
            session=world.dpo,
        )
        assert notices.json()["listed"] == 2 and notices.json()["contacts"] == 2

    async def test_a_spreadsheet_is_refused_with_how_to_save_it(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        uuid = await _breach(http, world)
        refused = await call(
            http,
            "POST",
            f"/breaches/{uuid}/affected/upload/check",
            template=f"{B}/affected/upload/check",
            session=world.dpo,
            expect=422,
            data={"kind": "contacts"},
            files={
                "file": (
                    "people.xlsx",
                    b"PK\x03\x04 a workbook",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert "Save it as CSV" in refused.text

    async def test_every_other_role_is_told_it_is_not_there(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        uuid = await _breach(http, world)
        for session in (world.admin, world.rnd, world.dco):
            await call(
                http,
                "POST",
                f"/breaches/{uuid}/affected/upload",
                template=f"{B}/affected/upload",
                session=session,
                expect=404,
                data={"kind": "contacts"},
                files={"file": ("people.csv", PEOPLE, "text/csv")},
            )
            await call(
                http,
                "GET",
                f"/breaches/{uuid}/affected/contacts",
                template=f"{B}/affected/contacts",
                session=session,
                expect=404,
            )
