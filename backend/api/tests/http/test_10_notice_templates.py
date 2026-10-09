"""Notice templates over HTTP (0044).

The DPO writes a template with no project, gives its purposes and its text,
and hands out its ID. The R&D User looks the ID up and attaches it to their own
project, which makes that project's draft notice. Writing a template is the
DPO's alone; a retired one is refused when attached.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.http.conftest import SessionFactory, fresh
from tests.http.contract import call
from tests.http.world import World, build

T = "/notice-templates/{template_uuid}"
BODY = {
    "withdraw_url": "https://example.org/withdraw",
    "exercise_rights_url": "https://example.org/rights",
    "board_complaint_url": "https://example.org/board",
    "dpo_contact": "dpo@example.org",
    "applicable_to": "data_subject",
}


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


async def _project(http: httpx.AsyncClient, world: World) -> str:
    made = await call(
        http,
        "POST",
        "/projects",
        session=world.rnd,
        expect=201,
        json={
            # Short enough that the unique part survives into the notice
            # code (20 characters), so runs do not share one base.
            "project_name": f"Tpl {fresh('T')}",
            "description": "Gait video collection.",
            "processor_uuids": [world.processor_uuid],
            "requesting_team": "Computer Vision",
        },
    )
    return str(made.json()["project_uuid"])


class TestNoticeTemplates:
    async def test_written_by_the_dpo_and_attached_by_its_id(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        made = await call(
            http,
            "POST",
            "/notice-templates",
            session=world.dpo,
            expect=201,
            json={**BODY, "title": "Gait studies", "rendered_text": "We collect gait video."},
        )
        template = made.json()
        code, uuid = template["template_code"], template["template_uuid"]
        assert code.startswith("TPL-")

        await call(
            http,
            "POST",
            f"/notice-templates/{uuid}/purposes",
            template=f"{T}/purposes",
            session=world.dpo,
            expect=201,
            json={"purpose_uuid": world.purpose_uuid, "is_mandatory": True},
        )
        shown = await call(
            http,
            "PUT",
            f"/notice-templates/{uuid}/languages/hindi",
            template=f"{T}/languages/{{code}}",
            session=world.dpo,
            json={"rendered_text": "हम चलने का वीडियो एकत्र करते हैं।"},
        )
        assert {lang["language_code"] for lang in shown.json()["languages"]} == {
            "english",
            "hindi",
        }
        removed = await call(
            http,
            "DELETE",
            f"/notice-templates/{uuid}/languages/hindi",
            template=f"{T}/languages/{{code}}",
            session=world.dpo,
        )
        assert [lang["language_code"] for lang in removed.json()["languages"]] == ["english"]
        renamed = await call(
            http,
            "PUT",
            f"/notice-templates/{uuid}",
            template=T,
            session=world.dpo,
            json={"title": "Gait studies, adults"},
        )
        assert renamed.json()["title"] == "Gait studies, adults"
        listed = await call(http, "GET", "/notice-templates", session=world.dpo)
        assert code in [t["template_code"] for t in listed.json()]

        # The R&D User looks it up by the ID they were given, then attaches it.
        found = await call(
            http,
            "GET",
            f"/notice-templates/by-code/{code.lower()}",
            template="/notice-templates/by-code/{template_code}",
            session=world.rnd,
        )
        assert found.json()["title"] == "Gait studies, adults"
        assert "notices" not in found.json()
        project = await _project(http, world)
        notice = await call(
            http,
            "POST",
            f"/projects/{project}/notices/from-template",
            template="/projects/{project_uuid}/notices/from-template",
            session=world.rnd,
            expect=201,
            json={"template_code": code},
        )
        assert notice.json()["template_code"] == code
        assert notice.json()["status"] == "draft"
        assert notice.json()["project_uuid"] == project

        detail = await call(http, "GET", f"/notice-templates/{uuid}", template=T, session=world.dpo)
        assert detail.json()["used_count"] == 1
        assert detail.json()["notices"][0]["notice_uuid"] == notice.json()["notice_uuid"]

        # A purpose taken off the template stays on the notice made from it.
        detached = await call(
            http,
            "DELETE",
            f"/notice-templates/{uuid}/purposes/{world.purpose_uuid}",
            template=f"{T}/purposes/{{purpose_uuid}}",
            session=world.dpo,
        )
        assert detached.json()["purposes"] == []

        # Retired: found, and refused.
        await call(
            http,
            "POST",
            f"/notice-templates/{uuid}/status",
            template=f"{T}/status",
            session=world.dpo,
            json={"status": "retired"},
        )
        refused = await call(
            http,
            "POST",
            f"/projects/{project}/notices/from-template",
            template="/projects/{project_uuid}/notices/from-template",
            session=world.rnd,
            expect=409,
            json={"template_code": code},
        )
        assert refused.json()["error"]["code"] == "template_retired"

    async def test_only_the_dpo_writes_one(self, http: httpx.AsyncClient, world: World) -> None:
        for session in (world.rnd, world.admin, world.dco):
            await call(
                http,
                "POST",
                "/notice-templates",
                session=session,
                expect=(403, 404),
                json={**BODY, "title": "Not mine to write"},
            )
            await call(http, "GET", "/notice-templates", session=session, expect=(403, 404))

    async def test_an_unknown_id_is_not_found(self, http: httpx.AsyncClient, world: World) -> None:
        await call(
            http,
            "GET",
            "/notice-templates/by-code/TPL-9999",
            template="/notice-templates/by-code/{template_code}",
            session=world.rnd,
            expect=404,
        )
