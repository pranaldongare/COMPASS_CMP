"""The Legal office's registry over HTTP (0052, ADR 0033).

The Legal PoC writes a category, names two processors on it, writes an HR
purpose and activates it; the DPO reaches none of it. The administrator
assigns an HR PoC to one category, who lists that one and not another. A
Legal office template names its category; a DPO office template names none.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.http.conftest import SessionFactory, fresh
from tests.http.contract import call
from tests.http.world import World, build

C = "/hr/categories/{category_uuid}"
TEMPLATE = {
    "title": "Wellness sessions",
    "withdraw_url": "https://example.org/withdraw",
    "exercise_rights_url": "https://example.org/rights",
    "board_complaint_url": "https://example.org/board",
    "dpo_contact": "legal@example.org",
}
PURPOSE = {
    "name": "Wellness programme",
    "description": "Running the wellness programme.",
    "uses": "Scheduling sessions and measuring take-up.",
    "lawful_basis": "consent_s6",
    "data_categories": ["name", "health_questionnaire"],
    "retention_days": 365,
    "retention_basis": "business_policy",
    "erasure_trigger": "withdrawal",
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


def _code() -> str:
    return fresh("C").upper().replace("-", "_")[:24]


async def _category(http: httpx.AsyncClient, legal: Any) -> dict[str, Any]:
    made = await call(
        http,
        "POST",
        "/hr/categories",
        session=legal,
        expect=201,
        json={"category_code": _code(), "name": "Employee wellness"},
    )
    return dict(made.json())


async def test_the_legal_poc_keeps_a_category_the_dpo_never_sees(
    http: httpx.AsyncClient, world: World, session_for: SessionFactory
) -> None:
    legal = await session_for("legal")
    category = await _category(http, legal)
    uuid = category["category_uuid"]
    assert category["office_code"] == "hr"

    processors = await call(
        http,
        "PUT",
        f"/hr/categories/{uuid}/processors",
        template=f"{C}/processors",
        session=legal,
        json={
            "processors": [
                {
                    "processor_uuid": world.processor_uuid,
                    "processor_role": "vendor",
                    "respondent_user_uuid": legal.uuid,
                },
            ]
        },
    )
    assert [p["processor_role"] for p in processors.json()] == ["vendor"]
    listed = await call(
        http, "GET", f"/hr/categories/{uuid}/processors", template=f"{C}/processors", session=legal
    )
    assert listed.json()[0]["respondent_uuid"] == legal.uuid

    renamed = await call(
        http,
        "PATCH",
        f"/hr/categories/{uuid}",
        template=C,
        session=legal,
        json={"name": "Wellness and health"},
    )
    assert renamed.json()["name"] == "Wellness and health"
    detail = await call(http, "GET", f"/hr/categories/{uuid}", template=C, session=legal)
    assert detail.json()["processor_count"] == 1

    purpose = await call(
        http,
        "POST",
        "/purposes",
        session=legal,
        expect=201,
        check_sealed=False,
        json={**PURPOSE, "purpose_code": f"P-{_code()}"[:20]},
    )
    purpose_uuid = purpose.json()["purpose_uuid"]
    assert purpose.json()["office_code"] == "hr"
    await call(
        http,
        "POST",
        f"/purposes/{purpose_uuid}/activate",
        template="/purposes/{purpose_uuid}/activate",
        session=legal,
    )

    # The DPO: the categories and the purpose are not there for them.
    await call(http, "GET", "/hr/categories", session=world.dpo, expect=404)
    await call(http, "GET", f"/hr/categories/{uuid}", template=C, session=world.dpo, expect=404)
    await call(
        http,
        "GET",
        f"/purposes/{purpose_uuid}/versions",
        template="/purposes/{purpose_uuid}/versions",
        session=world.dpo,
        expect=404,
    )
    dpo_purposes = await call(http, "GET", "/purposes", session=world.dpo, params={"limit": 200})
    assert purpose_uuid not in {p["purpose_uuid"] for p in dpo_purposes.json()["items"]}

    retired = await call(
        http,
        "POST",
        f"/hr/categories/{uuid}/status",
        template=f"{C}/status",
        session=legal,
        json={"status": "retired"},
    )
    assert retired.json()["status"] == "retired"


async def test_an_hr_poc_lists_the_category_they_are_assigned_to(
    http: httpx.AsyncClient, world: World, session_for: SessionFactory
) -> None:
    legal = await session_for("legal")
    wellness = await _category(http, legal)
    csr = await _category(http, legal)
    poc = await session_for("hr_user")

    await call(
        http,
        "PUT",
        f"/users/{poc.uuid}/categories",
        template="/users/{user_uuid}/categories",
        session=world.admin,
        json={"category_uuids": [wellness["category_uuid"]]},
    )
    pocs = await call(
        http,
        "GET",
        "/users/hr-pocs",
        session=legal,
        params={"category": wellness["category_uuid"]},
    )
    assert [p["uuid"] for p in pocs.json()] == [poc.uuid]

    mine = await call(http, "GET", "/hr/categories", session=poc)
    codes = {c["category_code"] for c in mine.json()}
    assert wellness["category_code"] in codes
    assert csr["category_code"] not in codes
    await call(
        http, "GET", f"/hr/categories/{csr['category_uuid']}", template=C, session=poc, expect=404
    )
    await call(
        http,
        "POST",
        "/hr/categories",
        session=poc,
        expect=403,
        json={"category_code": _code(), "name": "Not theirs to write"},
    )


async def test_a_template_names_its_category_in_the_legal_office_only(
    http: httpx.AsyncClient, world: World, session_for: SessionFactory
) -> None:
    legal = await session_for("legal")
    category = await _category(http, legal)

    await call(http, "POST", "/notice-templates", session=legal, expect=422, json=TEMPLATE)
    made = await call(
        http,
        "POST",
        "/notice-templates",
        session=legal,
        expect=201,
        json={**TEMPLATE, "category_uuid": category["category_uuid"]},
    )
    assert made.json()["category_code"] == category["category_code"]
    await call(
        http,
        "POST",
        "/notice-templates",
        session=world.dpo,
        expect=422,
        json={**TEMPLATE, "category_uuid": category["category_uuid"]},
    )

    theirs = await call(
        http,
        "GET",
        "/notice-templates",
        session=legal,
        params={"category": category["category_uuid"]},
    )
    assert [t["template_uuid"] for t in theirs.json()] == [made.json()["template_uuid"]]
    dpo_list = await call(http, "GET", "/notice-templates", session=world.dpo)
    assert made.json()["template_uuid"] not in {t["template_uuid"] for t in dpo_list.json()}
