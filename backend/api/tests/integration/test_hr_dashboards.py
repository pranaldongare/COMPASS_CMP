"""The Legal PoC's and the HR PoC's dashboards (increment 8, D-10).

The Legal PoC's reads like the DPO's on its own office: its requests - the
shared intake's among them, to claim - and its breaches, then what only it
has: live activities, its consents, template versions still in draft. The
DPO's dashboard counts none of it. An HR PoC's counts the activities of
their categories, their consents, and a link about to stop taking consent,
which is the one thing on it that asks for action.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from cmp.api.routers.v1 import dashboard
from cmp.core.permissions import Role
from cmp.db.repositories import rights as rights_repo
from cmp.domain.consent import service as consent_service
from cmp.domain.hr import activities
from cmp.domain.notices import templates, versions
from tests.integration.hr_world import approved_version, legal_office
from tests.integration.test_rights_by_office import _as_office, _from_portal, _person

pytestmark = pytest.mark.integration


@pytest.fixture
async def office(conn: Any, seeded: dict[str, Any], request_context: Any) -> dict[str, Any]:
    world = await legal_office(conn, seeded)
    version = await approved_version(conn, world)
    made = await activities.create(
        conn,
        actor_id=int(world["poc"]["id"]),
        role=Role.HR_USER,
        category_uuid=str(world["category"]["category_uuid"]),
        template_version_uuid=str(version["version_uuid"]),
        purpose_uuids=[str(world["purposes"]["sessions"]["purpose_uuid"])],
        name=f"Wellness {world['tag']}",
        description="Four lunchtime sessions.",
        audience_mode="otp",
        # Ends within the week: the HR PoC's one call to action.
        link_expires_at=datetime.now(UTC) + timedelta(days=3),
    )
    person = await _person(conn)
    token = str(made["url_path"]).rsplit("/", 1)[-1]
    served = await consent_service.serve_notice(
        conn, token=token, language_code="english", user_id=person
    )
    await consent_service.capture(
        conn,
        token=token,
        user_id=person,
        language_code="english",
        grants={str(p["purpose_uuid"]): True for p in served["purposes"]},
        action_type="checkbox_click",
        ip_address=None,
    )
    # A version opened and not approved; a request in the Legal office's
    # queue, and one in the shared intake.
    template = await templates.require(conn, str(world["template"]["template_uuid"]))
    await versions.open_version(conn, template, actor_id=int(world["legal"]["id"]))
    held = await _from_portal(conn, person, office="hr")
    intake = await _from_portal(conn, await _person(conn))
    return {"world": world, "made": made, "held": held, "intake": intake}


async def test_the_legal_poc_reads_its_own_office(conn: Any, office: dict[str, Any]) -> None:
    await _as_office(conn, "hr")
    data = await dashboard._legal(conn)
    counts = data["counts"]
    assert counts["activities_live"] >= 1
    assert counts["total_consents"] >= 1
    assert counts["versions_in_draft"] >= 1
    assert counts["requests_in_intake"] >= 1
    queues = {q["name"]: q["items"] for q in data["queues"]}
    references = {r["reference"] for r in queues["Rights requests, soonest due first"]}
    assert {office["held"]["reference"], office["intake"]["reference"]} <= references
    tag = office["world"]["template"]["template_code"]
    assert any(str(r["reference"]).startswith(tag) for r in queues["Template versions in draft"])
    rows = {r["key"] for r in dashboard._attention("legal", counts, data["queues"])}
    assert {"requests_in_intake", "versions_in_draft"} <= rows

    # The DPO office's reads do not reach the Legal office's request; the
    # shared intake's they do.
    await _as_office(conn, "rnd")
    dpo = int(office["world"]["legal"]["id"])
    assert (
        await rights_repo.by_uuid(
            conn, str(office["held"]["request_uuid"]), role=Role.DPO, user_id=dpo
        )
        is None
    )
    assert (
        await rights_repo.by_uuid(
            conn, str(office["intake"]["request_uuid"]), role=Role.DPO, user_id=dpo
        )
        is not None
    )


async def test_the_hr_poc_reads_their_activities(conn: Any, office: dict[str, Any]) -> None:
    await _as_office(conn, "hr")
    data = await dashboard._hr_user(conn, int(office["world"]["poc"]["id"]))
    counts = data["counts"]
    assert counts["activities_live"] == 1
    assert counts["consents"] == 1
    assert counts["links_expiring_7d"] == 1
    [ending] = next(q["items"] for q in data["queues"] if q["name"].startswith("Activity links"))
    assert ending["name"] == f"Wellness {office['world']['tag']}"
    assert ending["href"] == f"/hr-activities/{office['made']['activity_uuid']}"
    rows = {r["key"] for r in dashboard._attention("hr_user", counts, data["queues"])}
    assert "links_expiring_7d" in rows
