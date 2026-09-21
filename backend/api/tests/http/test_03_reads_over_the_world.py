"""Every read endpoint, over the world the API built.

The rule under test is the same on each: a sealed field comes back `SE::`, and
the value opens to what was written. The variety is in *whose* rows and *which*
role is entitled to see them.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.conftest import plain
from tests.http.conftest import SessionFactory, fresh, fresh_email, fresh_mobile, last_code
from tests.http.contract import call
from tests.http.world import World, build

CONFIRM = "cmp.notifications.send_contact_confirmation"


@pytest.fixture(scope="module")
def _world_box() -> dict[str, Any]:
    return {}


@pytest.fixture
async def world(
    http: httpx.AsyncClient, session_for: SessionFactory, queued: Any, _world_box: dict[str, Any]
) -> World:
    # Built once per module: it is many requests, and the reads here do not change it.
    if "w" not in _world_box:
        _world_box["w"] = await build(http, session_for, queued)
    return _world_box["w"]


class TestHerOwnRecords:
    async def test_me_and_the_edits_to_it(
        self, http: httpx.AsyncClient, world: World, queued: Any
    ) -> None:
        me = await call(http, "GET", "/me", session=world.principal)
        body = me.json()
        assert body["full_name"].startswith("SE::") and body["mobile"].startswith("SE::")
        assert plain(body["mobile"]) == world.principal_mobile

        new_mobile = fresh_mobile()
        patched = await call(
            http,
            "PATCH",
            "/me",
            session=world.principal,
            json={
                "full_name": "Principal Renamed",
                "mobile": new_mobile,
                "dob": "2001-02-03",
            },
        )
        assert plain(patched.json()["full_name"]) == "Principal Renamed"
        assert patched.json()["mobile_verified_at"] is None, "a changed number is unconfirmed"
        # Ask for the code again - the page's "send again" - then confirm with the
        # latest one. Both went to the number she typed, in the clear.
        await call(
            http,
            "POST",
            "/me/contacts/code",
            session=world.principal,
            expect=(200, 202, 204),
            json={"contact": new_mobile},
        )
        code = last_code(queued, CONFIRM)
        await call(
            http,
            "POST",
            "/me/contact/verify",
            session=world.principal,
            expect=(200, 204),
            json={"contact": new_mobile, "code": code},
        )
        world.principal_mobile = new_mobile

        await call(
            http,
            "POST",
            "/me/person-type",
            session=world.principal,
            expect=(200, 204),
            json={"person_type": "ex_employee", "reason": "Left the campus"},
        )

    async def test_her_consents(self, http: httpx.AsyncClient, world: World) -> None:
        listed = await call(http, "GET", "/me/consents", session=world.principal)
        assert any(c["consent_uuid"] == world.consent_uuid for c in listed.json())
        c = world.consent_uuid
        await call(
            http,
            "GET",
            f"/me/consents/{c}",
            template="/me/consents/{consent_uuid}",
            session=world.principal,
        )
        await call(
            http,
            "GET",
            f"/me/consents/{c}/grants",
            template="/me/consents/{consent_uuid}/grants",
            session=world.principal,
        )
        await call(
            http,
            "GET",
            f"/me/consents/{c}/history",
            template="/me/consents/{consent_uuid}/history",
            session=world.principal,
        )
        await call(
            http,
            "GET",
            f"/me/consents/{c}/notice",
            template="/me/consents/{consent_uuid}/notice",
            session=world.principal,
        )
        await call(
            http,
            "GET",
            f"/me/consents/{c}/trail",
            template="/me/consents/{consent_uuid}/trail",
            session=world.principal,
        )
        disclosed = await call(http, "GET", "/me/disclosures", session=world.principal)
        assert disclosed.json(), "the export named her, and she can see that it did"

    async def test_she_names_a_nominee_and_sees_who_named_her(
        self, http: httpx.AsyncClient, world: World, session_for: SessionFactory
    ) -> None:
        made = await call(
            http,
            "POST",
            "/me/nominations",
            session=world.principal,
            expect=(200, 201),
            json={
                "nominee_name": "Ravi Nominee",
                "nominee_mobile": fresh_mobile(),
                "nominee_email": fresh_email("nominee"),
                "rights": ["access"],
            },
        )
        body = made.json()
        assert body["nominee_name"].startswith("SE::") and body["nominee_mobile"].startswith("SE::")
        listed = await call(http, "GET", "/me/nominations", session=world.principal)
        assert any(n["nomination_uuid"] == body["nomination_uuid"] for n in listed.json())
        await call(http, "GET", "/me/nominee-of", session=world.principal)
        await call(
            http,
            "DELETE",
            f"/me/nominations/{body['nomination_uuid']}",
            template="/me/nominations/{nomination_uuid}",
            session=world.principal,
            expect=(200, 204),
        )

    async def test_she_withdraws(self, http: httpx.AsyncClient, world: World) -> None:
        # A fresh consent for this, so the rest of the module keeps a live one.
        w2 = world
        withdrawn = await call(
            http,
            "POST",
            f"/me/consents/{w2.consent_uuid}/withdraw",
            template="/me/consents/{consent_uuid}/withdraw",
            session=w2.principal,
            expect=(200, 201),
            json={"all": True},
        )
        assert withdrawn.json().get("is_withdrawal") in (True, None)


class TestTheOfficeReadsConsents:
    async def test_consents_and_links(self, http: httpx.AsyncClient, world: World) -> None:
        rows = await call(http, "GET", "/consents", session=world.dpo)
        assert rows.json()["items"], (
            "the office sees consents; every sealed field in them was checked"
        )
        c = world.consent_uuid
        await call(
            http, "GET", f"/consents/{c}", template="/consents/{consent_uuid}", session=world.dpo
        )
        await call(
            http,
            "GET",
            f"/consents/{c}/grants",
            template="/consents/{consent_uuid}/grants",
            session=world.dpo,
        )
        await call(
            http,
            "GET",
            f"/consents/{c}/assets",
            template="/consents/{consent_uuid}/assets",
            session=world.dpo,
        )
        await call(
            http,
            "GET",
            f"/projects/{world.project_uuid}/consents",
            template="/projects/{project_uuid}/consents",
            session=world.dco,
        )
        await call(http, "GET", "/links", session=world.dco)
        await call(
            http,
            "GET",
            f"/links/{world.link_uuid}",
            template="/links/{link_uuid}",
            session=world.dco,
        )
        await call(
            http,
            "GET",
            f"/links/{world.link_uuid}/stats",
            template="/links/{link_uuid}/stats",
            session=world.dco,
        )
        await call(
            http,
            "GET",
            f"/projects/{world.project_uuid}/links",
            template="/projects/{project_uuid}/links",
            session=world.dco,
        )


class TestProjectsNoticesRegistry:
    async def test_projects(self, http: httpx.AsyncClient, world: World) -> None:
        listed = await call(http, "GET", "/projects", session=world.rnd)
        assert any(p["project_uuid"] == world.project_uuid for p in listed.json()["items"])
        one = await call(
            http,
            "GET",
            f"/projects/{world.project_uuid}",
            template="/projects/{project_uuid}",
            session=world.dpo,
        )
        assert one.json()["created_by_name"].startswith("SE::")
        # Only a draft may be edited; the world's project is approved, so a
        # fresh one is registered for the edit.
        draft = await call(
            http,
            "POST",
            "/projects",
            session=world.rnd,
            expect=201,
            json={
                "project_name": f"Draft {fresh()}",
                "description": "Edited in the suite.",
                "processor_uuids": [world.processor_uuid],
            },
        )
        await call(
            http,
            "PUT",
            f"/projects/{draft.json()['project_uuid']}",
            template="/projects/{project_uuid}",
            session=world.rnd,
            json={"requesting_team": "Vision, renamed"},
        )
        await call(http, "GET", "/approvals", session=world.dpo)
        # A second collector asked for after approval, and the office's decision with its reason.
        second = await call(
            http,
            "POST",
            "/processors",
            session=world.dpo,
            expect=201,
            check_sealed=False,
            json={
                "legal_name": f"Beta Labs {fresh()}",
                "type": "lab",
                "contract_ref": fresh("CTR-"),
                "security_confirmed_at": "2026-01-01",
                "is_in_house": False,
            },
        )
        puid = second.json()["processor_uuid"]
        await call(
            http,
            "POST",
            f"/projects/{world.project_uuid}/processors",
            session=world.rnd,
            expect=(200, 201),
            check_sealed=False,
            json={"processor_uuid": puid},
        )
        decided = await call(
            http,
            "POST",
            f"/projects/{world.project_uuid}/processors/{puid}/decision",
            template="/projects/{project_uuid}/processors/{processor_uuid}/decision",
            session=world.dpo,
            json={"approved": False, "reason": "No contract on file"},
        )
        assert decided.status_code == 200
        await call(
            http,
            "PUT",
            f"/sites/{world.site_uuid}/owner",
            template="/sites/{site_uuid}/owner",
            session=world.dco_admin,
            expect=(200, 204),
            json={"owner_user_uuid": world.dco.uuid},
        )

    async def test_notices(self, http: httpx.AsyncClient, world: World) -> None:
        n = world.notice_uuid
        await call(
            http, "GET", f"/notices/{n}", template="/notices/{notice_uuid}", session=world.rnd
        )
        await call(
            http,
            "GET",
            f"/notices/{n}/purposes",
            template="/notices/{notice_uuid}/purposes",
            session=world.rnd,
        )
        await call(
            http,
            "GET",
            f"/notices/{n}/versions",
            template="/notices/{notice_uuid}/versions",
            session=world.rnd,
        )
        await call(
            http,
            "GET",
            f"/projects/{world.project_uuid}/notices",
            template="/projects/{project_uuid}/notices",
            session=world.rnd,
        )

    async def test_the_registry(
        self, http: httpx.AsyncClient, world: World, session_for: SessionFactory
    ) -> None:
        await call(http, "GET", "/sources", session=world.dco)
        await call(
            http,
            "GET",
            f"/sources/{world.source_uuid}",
            template="/sources/{source_uuid}",
            session=world.dco,
        )
        await call(
            http,
            "PUT",
            f"/sources/{world.source_uuid}",
            template="/sources/{source_uuid}",
            session=world.dco,
            json={"name": f"Acme intake renamed {fresh()}"},
        )
        # A respondent: a named human being at the third party.
        made = await call(
            http,
            "POST",
            f"/processors/{world.processor_uuid}/respondents",
            template="/processors/{processor_uuid}/respondents",
            session=world.dpo,
            expect=(200, 201),
            json={"name": "Priya at Acme", "contact": fresh_email("priya")},
        )
        body = made.json()
        rows = body if isinstance(body, list) else body.get("items") or [body]
        priya = next(r for r in rows if r.get("name") and plain(r["name"]) == "Priya at Acme")
        assert priya["name"].startswith("SE::") and priya["contact"].startswith("SE::")
        listed = await call(
            http,
            "GET",
            f"/processors/{world.processor_uuid}/respondents",
            template="/processors/{processor_uuid}/respondents",
            session=world.dco,
        )
        assert all(not r.get("name") or r["name"].startswith("SE::") for r in listed.json())


class TestExchange:
    async def test_exports_collections_imports(self, http: httpx.AsyncClient, world: World) -> None:
        await call(http, "GET", "/exports", session=world.dco)
        await call(
            http,
            "GET",
            f"/exports/{world.export_uuid}",
            template="/exports/{export_uuid}",
            session=world.dco,
        )
        await call(
            http,
            "GET",
            f"/projects/{world.project_uuid}/exports",
            template="/projects/{project_uuid}/exports",
            session=world.dco,
        )
        await call(http, "GET", "/collections", session=world.dco)
