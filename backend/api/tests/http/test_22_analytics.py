"""Analytics and reports over HTTP (ADR 0045).

Who reaches which part: management the scorecard, both offices or one; an
officer their own office's and not the other's; the administrator audit and
health and no scorecard; a researcher their own work only; a data principal
nothing. A report asked for over HTTP is queued (202), listed, and deleted by
whoever may read it; targets are the administrator's to set.
"""

from __future__ import annotations

import httpx

from tests.http.conftest import SessionFactory
from tests.http.contract import call

FIG = "/analytics/figures"


async def test_each_role_reaches_its_own_part(
    http: httpx.AsyncClient, session_for: SessionFactory
) -> None:
    boss = await session_for("management")
    dpo = await session_for("dpo")
    admin = await session_for("admin")
    rnd = await session_for("rnd_user")
    her = await session_for("data_subject")

    cat = (await call(http, "GET", "/analytics/catalogue", session=boss)).json()
    assert cat["may_choose_office"] is True and "management" in cat["sections"]
    for office in ("rnd", "hr"):
        out = await call(
            http, "GET", FIG, session=boss, params={"section": "management", "office": office}
        )
        assert out.json()["office"] == office
    await call(http, "GET", FIG, session=boss, params={"section": "health"}, expect=403)

    mine = (await call(http, "GET", FIG, session=dpo, params={"section": "management"})).json()
    assert mine["office"] == "rnd"
    await call(
        http,
        "GET",
        FIG,
        session=dpo,
        params={"section": "management", "office": "hr"},
        expect=403,
    )

    await call(http, "GET", FIG, session=admin, params={"section": "health"})
    await call(http, "GET", FIG, session=admin, params={"section": "management"}, expect=403)
    await call(
        http,
        "GET",
        "/analytics/audit-reports/privileged",
        session=admin,
        params={"period": "last_7_days"},
    )
    await call(http, "GET", "/analytics/audit-reports/privileged", session=boss, expect=403)

    await call(http, "GET", FIG, session=rnd, params={"section": "mine"})
    await call(http, "GET", FIG, session=rnd, params={"section": "management"}, expect=403)

    for path in ("/analytics/catalogue", FIG, "/reports", "/analytics/settings"):
        await call(http, "GET", path, session=her, expect=403)


async def test_targets_are_the_administrators_and_reports_are_kept_until_deleted(
    http: httpx.AsyncClient, session_for: SessionFactory
) -> None:
    boss = await session_for("management")
    admin = await session_for("admin")
    body = {"target": 90, "amber": 80}
    key = "rights.on_time_rate"
    await call(
        http,
        "PUT",
        f"/analytics/targets/{key}",
        template="/analytics/targets/{key}",
        session=boss,
        expect=403,
        json=body,
    )
    try:
        saved = (
            await call(
                http,
                "PUT",
                f"/analytics/targets/{key}",
                template="/analytics/targets/{key}",
                session=admin,
                json=body,
            )
        ).json()
        assert next(t for t in saved["targets"] if t["key"] == key)["target"] == 90
    finally:
        await call(
            http,
            "DELETE",
            f"/analytics/targets/{key}",
            template="/analytics/targets/{key}",
            session=admin,
        )

    made = (
        await call(
            http,
            "POST",
            "/reports",
            session=boss,
            expect=202,
            json={"kind": "management_scorecard", "format": "pdf", "period": "last_month"},
        )
    ).json()
    assert made["status"] == "queued"
    listed = (await call(http, "GET", "/reports", session=boss)).json()
    assert made["report_uuid"] in {r["report_uuid"] for r in listed}
    await call(
        http,
        "POST",
        "/reports",
        session=admin,
        expect=403,
        json={"kind": "management_scorecard", "format": "pdf"},
    )
    await call(
        http,
        "DELETE",
        f"/reports/{made['report_uuid']}",
        template="/reports/{report_uuid}",
        session=boss,
    )
