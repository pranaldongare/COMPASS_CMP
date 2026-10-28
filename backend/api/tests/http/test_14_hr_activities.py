"""HR activities over HTTP (ADR 0033).

Legal sets up a category with its HR system, two purposes and a template
whose version 1 is approved; the administrator assigns an HR PoC to the
category; the HR PoC creates an activity from the version - 201 with its
link - reads it, its consents and its transitions, upgrades it to version 2
and closes it. A purpose off the list is 422 with nothing written; the DPO
finds none of it.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest

from tests.http.conftest import SessionFactory, fresh
from tests.http.contract import call
from tests.http.world import World, build

A = "/hr/activities/{activity_uuid}"
V = "/notice-templates/{template_uuid}/versions"
LOCKED = "We will use your data for:\n{{purposes}}\n\nAbout this activity: {{description}}"


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


def _code(prefix: str) -> str:
    return fresh(prefix).upper().replace("-", "_")[:20]


async def _purpose(http: httpx.AsyncClient, legal: Any, name: str) -> str:
    made = await call(
        http,
        "POST",
        "/purposes",
        session=legal,
        expect=201,
        check_sealed=False,
        json={
            "purpose_code": f"P-{_code('A')}",
            "name": name,
            "description": f"{name}.",
            "uses": "Running the programme.",
            "lawful_basis": "consent_s6",
            "data_categories": ["name"],
            "retention_days": 365,
            "retention_basis": "business_policy",
            "erasure_trigger": "withdrawal",
        },
    )
    uuid = str(made.json()["purpose_uuid"])
    await call(
        http,
        "POST",
        f"/purposes/{uuid}/activate",
        template="/purposes/{purpose_uuid}/activate",
        session=legal,
    )
    return uuid


async def _legal_office(
    http: httpx.AsyncClient, world: World, session_for: SessionFactory
) -> dict[str, Any]:
    legal = await session_for("legal")
    poc = await session_for("hr_user")
    hrms = await call(
        http,
        "POST",
        "/processors",
        session=world.dpo,
        expect=201,
        check_sealed=False,
        json={
            "legal_name": f"HR Systems {fresh('H')}",
            "type": "lab",
            "contract_ref": f"CTR-{fresh('H')}",
            "security_confirmed_at": datetime.now(UTC).date().isoformat(),
            "is_in_house": True,
            "location_country": "IN",
        },
    )
    category = (
        await call(
            http,
            "POST",
            "/hr/categories",
            session=legal,
            expect=201,
            json={"category_code": _code("W"), "name": "Wellness"},
        )
    ).json()
    await call(
        http,
        "PUT",
        f"/hr/categories/{category['category_uuid']}/processors",
        template="/hr/categories/{category_uuid}/processors",
        session=legal,
        json={
            "processors": [
                {"processor_uuid": hrms.json()["processor_uuid"], "processor_role": "hrms"}
            ]
        },
    )
    await call(
        http,
        "PUT",
        f"/users/{poc.uuid}/categories",
        template="/users/{user_uuid}/categories",
        session=world.admin,
        json={"category_uuids": [category["category_uuid"]]},
    )
    sessions = await _purpose(http, legal, "Wellness sessions")
    survey = await _purpose(http, legal, "Follow-up survey")
    template = (
        await call(
            http,
            "POST",
            "/notice-templates",
            session=legal,
            expect=201,
            json={
                "title": "Wellness sessions",
                "withdraw_url": "https://example.org/withdraw",
                "exercise_rights_url": "https://example.org/rights",
                "board_complaint_url": "https://example.org/board",
                "dpo_contact": "legal@example.org",
                "applicable_to": "employee",
                "category_uuid": category["category_uuid"],
            },
        )
    ).json()["template_uuid"]
    versions = []
    for n, reconsent in ((1, False), (2, True)):
        base = f"/notice-templates/{template}/versions"
        version = await call(http, "POST", base, template=V, session=legal, expect=201)
        await call(
            http,
            "PATCH",
            f"{base}/{n}",
            template=V + "/{number}",
            session=legal,
            json={"reconsent_required": reconsent},
        )
        await call(
            http,
            "PUT",
            f"{base}/{n}/languages/english",
            template=V + "/{number}/languages/{code}",
            session=legal,
            json={"locked_text": LOCKED},
        )
        await call(
            http,
            "PUT",
            f"{base}/{n}/purposes",
            template=V + "/{number}/purposes",
            session=legal,
            json={
                "purposes": [
                    {"purpose_uuid": sessions, "is_mandatory": True},
                    {"purpose_uuid": survey},
                ]
            },
        )
        await call(
            http, "POST", f"{base}/{n}/approve", template=V + "/{number}/approve", session=legal
        )
        versions.append(str(version.json()["version_uuid"]))
    return {
        "legal": legal,
        "poc": poc,
        "category": category["category_uuid"],
        "versions": versions,
        "sessions": sessions,
        "survey": survey,
    }


async def test_an_hr_poc_runs_an_activity_from_start_to_close(
    http: httpx.AsyncClient, world: World, session_for: SessionFactory
) -> None:
    hr = await _legal_office(http, world, session_for)
    poc = hr["poc"]

    options = await call(http, "GET", "/hr/activities/options", session=poc)
    [mine] = [c for c in options.json() if c["category_uuid"] == hr["category"]]
    assert {v["version_uuid"] for v in mine["versions"]} == set(hr["versions"])

    body = {
        "category_uuid": hr["category"],
        "template_version_uuid": hr["versions"][0],
        "purpose_uuids": [hr["sessions"], hr["survey"]],
        "name": f"Wellness week {fresh('A')}",
        "description": "Four lunchtime sessions on sleep and stress.",
        "audience_mode": "sso",
        "link_expires_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
    }
    refused = await call(
        http,
        "POST",
        "/hr/activities",
        session=poc,
        expect=422,
        json={**body, "purpose_uuids": [hr["survey"]]},
    )
    assert refused.json()["error"]["field"] == "purpose_uuids"

    made = await call(http, "POST", "/hr/activities", session=poc, expect=201, json=body)
    activity = made.json()["activity_uuid"]
    assert made.json()["url_path"].startswith("/c/")
    assert made.json()["audience_mode"] == "sso"

    listed = await call(http, "GET", "/hr/activities", session=poc)
    assert activity in {a["activity_uuid"] for a in listed.json()}
    detail = await call(http, "GET", f"/hr/activities/{activity}", template=A, session=poc)
    assert detail.json()["status"] == "approved"
    assert detail.json()["link"]["audience_mode"] == "sso"
    assert detail.json()["link"]["url_path"] == made.json()["url_path"]

    legal_view = await call(http, "GET", "/hr/activities", session=hr["legal"])
    assert activity in {a["activity_uuid"] for a in legal_view.json()}
    await call(http, "GET", f"/hr/activities/{activity}", template=A, session=world.dpo, expect=404)

    consents = await call(
        http,
        "GET",
        f"/projects/{activity}/consents",
        template="/projects/{project_uuid}/consents",
        session=poc,
    )
    assert consents.json()["items"] == []

    upgraded = await call(
        http,
        "POST",
        f"/hr/activities/{activity}/upgrade",
        template=A + "/upgrade",
        session=poc,
        json={
            "template_version_uuid": hr["versions"][1],
            "purpose_uuids": [hr["sessions"]],
            "description": "Four lunchtime sessions, and a follow-up call.",
        },
    )
    assert upgraded.json()["version"] == 2

    closed = await call(
        http,
        "POST",
        f"/hr/activities/{activity}/close",
        template=A + "/close",
        session=poc,
        json={"reason": "The week is over."},
    )
    assert closed.json()["to"] == "closed"
