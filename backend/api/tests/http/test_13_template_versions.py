"""Template versions over HTTP (0053, ADR 0033).

The Legal PoC opens version 1 of a template, writes its locked text and its
purposes, previews it, and approves it; version 2 opens as a copy; version 1
is retired. A purpose still a draft blocks approval with a 409 naming it; a
text missing a slot, a 422 naming the slot. A DPO office template has none.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.http.conftest import SessionFactory, fresh
from tests.http.contract import call
from tests.http.world import World, build

T = "/notice-templates/{template_uuid}"
V = T + "/versions"
N = V + "/{number}"
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


async def _purpose(http: httpx.AsyncClient, legal: Any, *, activate: bool) -> str:
    made = await call(
        http,
        "POST",
        "/purposes",
        session=legal,
        expect=201,
        check_sealed=False,
        json={
            "purpose_code": f"P-{_code('V')}",
            "name": "Wellness sessions",
            "description": "Running the sessions.",
            "uses": "Scheduling.",
            "lawful_basis": "consent_s6",
            "data_categories": ["name"],
            "retention_days": 365,
            "retention_basis": "business_policy",
            "erasure_trigger": "withdrawal",
        },
    )
    uuid = str(made.json()["purpose_uuid"])
    if activate:
        await call(
            http,
            "POST",
            f"/purposes/{uuid}/activate",
            template="/purposes/{purpose_uuid}/activate",
            session=legal,
        )
    return uuid


async def _template(http: httpx.AsyncClient, legal: Any) -> str:
    category = await call(
        http,
        "POST",
        "/hr/categories",
        session=legal,
        expect=201,
        json={"category_code": _code("C"), "name": "Wellness"},
    )
    made = await call(
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
            "category_uuid": category.json()["category_uuid"],
        },
    )
    return str(made.json()["template_uuid"])


async def test_legal_opens_writes_approves_and_retires_a_version(
    http: httpx.AsyncClient, world: World, session_for: SessionFactory
) -> None:
    legal = await session_for("legal")
    template = await _template(http, legal)
    active = await _purpose(http, legal, activate=True)
    draft_purpose = await _purpose(http, legal, activate=False)
    base = f"/notice-templates/{template}/versions"

    one = await call(http, "POST", base, template=V, session=legal, expect=201)
    assert one.json()["version"] == 1 and one.json()["status"] == "draft"
    await call(
        http,
        "PATCH",
        f"{base}/1",
        template=N,
        session=legal,
        json={"slot_guidance": "Say what the sessions are and when.", "slot_max_length": 600},
    )
    await call(
        http,
        "PUT",
        f"{base}/1/languages/english",
        template=N + "/languages/{code}",
        session=legal,
        json={"locked_text": "No slots here."},
    )
    await call(
        http,
        "PUT",
        f"{base}/1/purposes",
        template=N + "/purposes",
        session=legal,
        json={
            "purposes": [
                {"purpose_uuid": active, "is_mandatory": True},
                {"purpose_uuid": draft_purpose},
            ]
        },
    )

    # A purpose still a draft: 409, named.
    refused = await call(
        http, "POST", f"{base}/1/approve", template=N + "/approve", session=legal, expect=409
    )
    assert refused.json()["error"]["code"] == "purpose_not_active"
    await call(
        http,
        "PUT",
        f"{base}/1/purposes",
        template=N + "/purposes",
        session=legal,
        json={"purposes": [{"purpose_uuid": active, "is_mandatory": True}]},
    )
    # A text without its slots: 422, naming the slot.
    refused = await call(
        http, "POST", f"{base}/1/approve", template=N + "/approve", session=legal, expect=422
    )
    assert refused.json()["error"]["language"] == "english"
    assert refused.json()["error"]["placeholder"] == "{{purposes}}"
    await call(
        http,
        "PUT",
        f"{base}/1/languages/english",
        template=N + "/languages/{code}",
        session=legal,
        json={"locked_text": LOCKED},
    )

    preview = await call(
        http,
        "GET",
        f"{base}/1/preview",
        template=N + "/preview",
        session=legal,
        params={"description": "A week of sessions."},
    )
    again = await call(
        http,
        "GET",
        f"{base}/1/preview",
        template=N + "/preview",
        session=legal,
        params={"description": "A week of sessions."},
    )
    assert preview.json() == again.json()
    assert "A week of sessions." in preview.json()[0]["text"]

    approved = await call(http, "POST", f"{base}/1/approve", template=N + "/approve", session=legal)
    assert approved.json()["status"] == "approved"
    assert approved.json()["languages"][0]["content_hash"]

    two = await call(http, "POST", base, template=V, session=legal, expect=201)
    assert two.json()["version"] == 2
    assert two.json()["languages"][0]["locked_text"] == LOCKED
    await call(
        http,
        "PUT",
        f"{base}/2/languages/hindi",
        template=N + "/languages/{code}",
        session=legal,
        json={"locked_text": LOCKED},
    )
    await call(
        http,
        "DELETE",
        f"{base}/2/languages/hindi",
        template=N + "/languages/{code}",
        session=legal,
    )

    listed = await call(http, "GET", base, template=V, session=legal)
    assert [v["version"] for v in listed.json()] == [2, 1]
    got = await call(http, "GET", f"{base}/1", template=N, session=legal)
    assert got.json()["status"] == "approved"
    retired = await call(
        http,
        "POST",
        f"{base}/1/status",
        template=N + "/status",
        session=legal,
        json={"status": "retired"},
    )
    assert retired.json()["status"] == "retired"

    # The DPO: the template is not there for them.
    await call(http, "GET", base, template=V, session=world.dpo, expect=404)


async def test_a_dpo_office_template_has_no_versions(http: httpx.AsyncClient, world: World) -> None:
    made = await call(
        http,
        "POST",
        "/notice-templates",
        session=world.dpo,
        expect=201,
        json={
            "title": "Gait studies",
            "withdraw_url": "https://example.org/withdraw",
            "exercise_rights_url": "https://example.org/rights",
            "board_complaint_url": "https://example.org/board",
            "dpo_contact": "dpo@example.org",
        },
    )
    template = made.json()["template_uuid"]
    refused = await call(
        http,
        "POST",
        f"/notice-templates/{template}/versions",
        template=V,
        session=world.dpo,
        expect=409,
    )
    assert refused.json()["error"]["code"] == "template_not_versioned"
