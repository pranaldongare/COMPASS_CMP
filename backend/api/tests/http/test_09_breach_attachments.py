"""Files kept with an incident, over HTTP (2026-10-06).

The DPO attaches the email that reported an incident and a screenshot; the
response carries each one's name and note sealed, its hash and its size; a
download returns the bytes with the hash recorded beside the hash of what was
read. A file type that could run is refused, and every other role is told
the incident is not there.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest

from tests.conftest import plain
from tests.http.conftest import SessionFactory
from tests.http.contract import call
from tests.http.world import World, build

B = "/breaches/{breach_uuid}"
A = f"{B}/attachments"

EMAIL = b"From: someone@example.org\r\nSubject: A list that is not mine\r\n\r\nHello.\r\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


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


async def _incident(http: httpx.AsyncClient, world: World) -> str:
    made = await call(
        http,
        "POST",
        "/breaches",
        session=world.dpo,
        expect=201,
        json={
            "title": "A contact list sent to the wrong address",
            "detected_at": (datetime.now(UTC) - timedelta(minutes=15)).isoformat(),
            "location_kind": "platform",
        },
    )
    return str(made.json()["breach_uuid"])


class TestAttachments:
    async def test_the_dpo_keeps_files_and_reads_them_back(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        uuid = await _incident(http, world)
        first = await call(
            http,
            "POST",
            f"/breaches/{uuid}/attachments",
            template=A,
            session=world.dpo,
            expect=201,
            data={"kind": "email", "note": "The report, as it came"},
            files={"file": ("report.eml", EMAIL, "message/rfc822")},
        )
        [att] = first.json()["attachments"]
        assert att["kind"] == "email" and att["size_bytes"] == len(EMAIL)
        assert att["sha256"] == hashlib.sha256(EMAIL).hexdigest()
        assert str(att["file_name"]).startswith("SE::") and str(att["note"]).startswith("SE::")
        assert plain(att["file_name"]) == "report.eml"

        second = await call(
            http,
            "POST",
            f"/breaches/{uuid}/attachments",
            template=A,
            session=world.dpo,
            expect=201,
            data={"kind": "proof"},
            files={"file": ("screen.png", PNG, "image/png")},
        )
        assert [a["kind"] for a in second.json()["attachments"]] == ["email", "proof"]

        got = await call(
            http,
            "GET",
            f"/breaches/{uuid}/attachments/{att['attachment_uuid']}",
            template=f"{A}/{{attachment_uuid}}",
            session=world.dpo,
        )
        assert got.content == EMAIL
        assert got.headers["X-Recorded-SHA256"] == got.headers["X-Content-SHA256"] == att["sha256"]
        assert "report.eml" in got.headers["Content-Disposition"]

    async def test_a_file_that_could_run_is_refused(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        uuid = await _incident(http, world)
        await call(
            http,
            "POST",
            f"/breaches/{uuid}/attachments",
            template=A,
            session=world.dpo,
            expect=422,
            data={"kind": "other"},
            files={"file": ("run.sh", b"#!/bin/sh\necho hi\n", "application/x-sh")},
        )

    async def test_every_other_role_is_told_it_is_not_there(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        uuid = await _incident(http, world)
        for session in (world.admin, world.dco, world.rnd):
            await call(
                http,
                "POST",
                f"/breaches/{uuid}/attachments",
                template=A,
                session=session,
                expect=404,
                data={"kind": "email"},
                files={"file": ("report.eml", EMAIL, "message/rfc822")},
            )
