"""DataVault over HTTP (0070).

The administrator alone keeps the connection, and its key never comes back.
The DPO checks a rights request in DataVault - the call itself is answered
here by a stand-in, since no DataVault exists in a test - and reads what it
listed. A holder's ticket route answers with nothing for a ticket that is not
a project's DCO Admin's. The connection is switched off again at the end:
this suite commits, and the next run starts from "not set up".

And how a request starts (2026-11-13): as the office moves it to in progress
the platform finds who holds her data by itself, and where a project's DCO
Admin is among them it asks DataVault too - the task is seen queued here, and
run in `tests/integration/test_datavault_check.py`.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from cmp.infrastructure import datavault as dv
from tests.http.conftest import (
    Session,
    SessionFactory,
    fresh,
    fresh_email,
    fresh_mobile,
    last_code,
)
from tests.http.contract import call
from tests.http.world import CONSENT_CODE, World, build

CONNECTION = "/datavault-connection"
RIGHTS = "/requests/{request_uuid}"
KEY = "dv-http-key-0123456789"
#: The platform's own call to DataVault, as the worker would be asked for it.
CHECK = "cmp.datavault.check_request"


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


async def test_the_connection_is_the_administrator_s_and_a_request_is_checked(
    http: httpx.AsyncClient, world: World, queued: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    for who in (world.dpo, world.dco_admin, world.rnd):
        await call(http, "GET", CONNECTION, session=who, expect=403)
        await call(http, "PUT", CONNECTION, session=who, expect=403, json={"enabled": False})

    made = await call(
        http,
        "POST",
        "/me/requests",
        session=world.principal,
        expect=201,
        json={"request_type": "access", "request_text": f"What is in DataVault? {fresh()}"},
    )
    ruuid = made.json()["request_uuid"]
    reference = made.json()["reference"]
    try:
        # Switched off: the request says so, and a check is refused.
        await call(
            http,
            "PUT",
            CONNECTION,
            session=world.admin,
            json={"base_url": None, "enabled": False, "clear_api_key": True},
        )
        before = await call(
            http,
            "GET",
            f"/requests/{ruuid}/datavault",
            template=RIGHTS + "/datavault",
            session=world.dpo,
        )
        assert before.json()["configured"] is False and before.json()["may_check"] is False
        refused = await call(
            http,
            "POST",
            f"/requests/{ruuid}/datavault/check",
            template=RIGHTS + "/datavault/check",
            session=world.dpo,
            expect=409,
        )
        assert refused.json()["error"]["code"] == "datavault_not_configured"

        saved = await call(
            http,
            "PUT",
            CONNECTION,
            session=world.admin,
            json={"base_url": "https://datavault.test/api/", "api_key": KEY, "enabled": True},
        )
        assert saved.json()["base_url"] == "https://datavault.test/api"
        assert saved.json()["api_key_set"] is True and KEY not in saved.text
        read = await call(http, "GET", CONNECTION, session=world.admin)
        assert KEY not in read.text and "api_key_sealed" not in read.text
        await call(
            http,
            "PUT",
            CONNECTION,
            session=world.admin,
            expect=422,
            json={"base_url": "https://u:p@datavault.test", "enabled": True},
        )

        asked: list[dict[str, Any]] = []

        async def stand_in(**kwargs: Any) -> list[dv.Held]:
            asked.append(kwargs)
            return [
                dv.Held(
                    asset_ref="DV-IMG-000101",
                    consent_ref=world.consent_uuid,
                    project_ref=world.project_uuid,
                    mid="4909",
                    datapath="/vault/img/000101",
                ),
                dv.Held("DV-AUD-000103", "not-a-consent", None, None, None),
            ]

        monkeypatch.setattr(dv, "lookup", stand_in)
        checked = await call(
            http,
            "POST",
            f"/requests/{ruuid}/datavault/check",
            template=RIGHTS + "/datavault/check",
            session=world.dpo,
        )
        [sent] = asked
        assert sent["request_ref"] == reference and isinstance(sent["person_no"], int)
        assert sent["api_key"] == KEY and sent["base_url"] == "https://datavault.test/api"
        body = checked.json()
        assert body["answer"]["outcome"] == "answered" and body["answer"]["asset_count"] == 2
        first, second = body["assets"]
        assert first["consent_uuid"] == world.consent_uuid
        assert first["project_uuid"] == world.project_uuid
        assert (first["mid"], first["datapath"]) == ("4909", "/vault/img/000101")
        assert second["consent_uuid"] is None and second["consent_ref"] == "not-a-consent"
        assert "consent_id" not in first and "project_id" not in first, "no surrogate keys by name"

        again = await call(
            http,
            "GET",
            f"/requests/{ruuid}/datavault",
            template=RIGHTS + "/datavault",
            session=world.dpo,
        )
        assert [a["asset_ref"] for a in again.json()["assets"]] == [
            "DV-IMG-000101",
            "DV-AUD-000103",
        ]
        # Nobody but the office that answers the request.
        await call(
            http,
            "GET",
            f"/requests/{ruuid}/datavault",
            template=RIGHTS + "/datavault",
            session=world.dco_admin,
            expect=(403, 404),
        )
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/datavault/check",
            template=RIGHTS + "/datavault/check",
            session=world.rnd,
            expect=(403, 404),
        )

        # A ticket that is not theirs, or not a DCO Admin's: nothing listed.
        nothing = await call(
            http,
            "GET",
            f"/tickets/{ruuid}/datavault",
            template="/tickets/{holder_uuid}/datavault",
            session=world.dco_admin,
        )
        assert nothing.json() == {"asked_at": None, "assets": []}
    finally:
        await call(
            http,
            "PUT",
            CONNECTION,
            session=world.admin,
            json={"base_url": None, "enabled": False, "clear_api_key": True},
        )


# ------------------------------------------------------- as a request starts
async def _newcomer(
    http: httpx.AsyncClient, world: World, queued: Any, session_for: SessionFactory
) -> Session:
    """Somebody who consents on the world's link after its export was made. No
    export line and no asset names her, so nobody holds her data on record and
    the project's DCO Admin is who answers for it (0069)."""
    tag = fresh("N")
    mobile, email = fresh_mobile(), fresh_email("newcomer.")
    link = f"/c/{world.link_token}"
    await call(
        http,
        "POST",
        f"{link}/register",
        template="/c/{token}/register",
        expect=(200, 201),
        json={
            "full_name": f"Newcomer {tag}",
            "mobile": mobile,
            "email": email,
            "organization_id": f"STU-{tag}",
            "person_type": "external",
            "dob": "1991-03-09",
        },
    )
    cookies: dict[str, str] = {}
    for contact in (mobile, email):
        await call(
            http, "POST", f"{link}/otp", template="/c/{token}/otp", json={"contact": contact}
        )
        verified = await call(
            http,
            "POST",
            f"{link}/otp/verify",
            template="/c/{token}/otp/verify",
            json={"contact": contact, "code": last_code(queued, CONSENT_CODE, position=1)},
        )
        cookies.update(dict(verified.cookies))
    # The notice is served to her, signed in, before she decides.
    await call(
        http,
        "GET",
        f"{link}/notice",
        template="/c/{token}/notice",
        params={"language_code": "english"},
        cookies=cookies,
    )
    await call(
        http,
        "POST",
        f"{link}/consent",
        template="/c/{token}/consent",
        expect=(200, 201),
        cookies=cookies,
        headers={"X-CSRF-Token": cookies.get("cmp_csrf", "")},
        json={
            "language_code": "english",
            "grants": {world.purpose_uuid: True},
            "action_type": "checkbox_click",
        },
    )
    from cmp.db.pool import connection
    from cmp.db.repositories import users as user_repo

    async with connection() as conn:
        row = await user_repo.by_contact(conn, mobile)
    assert row is not None
    return await session_for("data_subject", user=dict(row))


async def _started(http: httpx.AsyncClient, world: World, her: Session) -> dict[str, Any]:
    """Her access request, found valid by the DPO and moved to in progress:
    the request as the office then reads it."""
    made = await call(
        http,
        "POST",
        "/me/requests",
        session=her,
        expect=201,
        json={"request_type": "access", "request_text": f"What do you hold of me? {fresh()}"},
    )
    ruuid = made.json()["request_uuid"]
    await call(
        http,
        "POST",
        f"/requests/{ruuid}/classify",
        template=RIGHTS + "/classify",
        session=world.dpo,
        json={"request_type": "access"},
    )
    before = await call(http, "GET", f"/requests/{ruuid}", template=RIGHTS, session=world.dpo)
    assert before.json()["holders"] == [] and before.json()["holders_derived_at"] is None, (
        "nothing is read before the office has found the request valid"
    )
    moved = await call(
        http,
        "POST",
        f"/requests/{ruuid}/transition",
        template=RIGHTS + "/transition",
        session=world.dpo,
        json={"to": "in_progress"},
    )
    assert moved.json()["status"] == "in_progress"
    after = await call(http, "GET", f"/requests/{ruuid}", template=RIGHTS, session=world.dpo)
    return dict(after.json())


async def _connection(http: httpx.AsyncClient, world: World, *, on: bool) -> None:
    body: dict[str, Any] = (
        {"base_url": "https://datavault.test/api", "api_key": KEY, "enabled": True}
        if on
        else {"base_url": None, "enabled": False, "clear_api_key": True}
    )
    await call(http, "PUT", CONNECTION, session=world.admin, json=body)


async def test_as_work_begins_the_platform_finds_the_holders_and_asks_datavault(
    http: httpx.AsyncClient,
    world: World,
    queued: Any,
    session_for: SessionFactory,
    committed: Any,
) -> None:
    her = await _newcomer(http, world, queued, session_for)
    asked = lambda: [args for name, args in queued if name == CHECK]  # noqa: E731

    try:
        # DataVault not set up: the holders are found all the same, and
        # nothing is asked of anybody.
        await _connection(http, world, on=False)
        first = await _started(http, world, her)
        assert first["holders_derived_at"] is not None, "read as the work began"
        [holder] = first["holders"]
        assert holder["derived_from"] == "project_owner" and holder["is_activity"] is False
        assert holder["project_uuid"] == world.project_uuid
        assert holder["confirmed_at"] is None, "found is not confirmed: the office does that"
        assert asked() == []

        # Set up: the same start now asks DataVault too, once, for that request.
        await _connection(http, world, on=True)
        second = await _started(http, world, her)
        assert [h["derived_from"] for h in second["holders"]] == ["project_owner"]
        row = await (
            await committed.execute(
                "SELECT request_id FROM rights_request WHERE request_uuid = %s",
                (second["request_uuid"],),
            )
        ).fetchone()
        assert asked() == [(row["request_id"],)]

        # The trail says the platform read the records, for the officer who
        # started the work; a press of the button afterwards says nothing of it.
        ruuid = second["request_uuid"]
        pressed = await call(
            http,
            "POST",
            f"/requests/{ruuid}/holders/derive",
            template=RIGHTS + "/holders/derive",
            session=world.dpo,
            expect=(200, 201),
        )
        assert [h["holder_uuid"] for h in pressed.json()] == [
            h["holder_uuid"] for h in second["holders"]
        ], "reading again adds nobody twice"
        trail = await call(
            http,
            "GET",
            "/audit",
            session=world.dpo,
            params={"event_type": "rights.holders_derived", "from": world.built_at},
        )
        mine = [
            e["detail"]
            for e in trail.json()["items"]
            if e["detail"].get("reference") == second["reference"]
        ]
        assert sorted(d.get("automatic", False) for d in mine) == [False, True]

        # A grievance asks no holder anything: starting one reads nothing.
        grievance = await call(
            http,
            "POST",
            "/me/requests",
            session=her,
            expect=201,
            json={"request_type": "grievance", "request_text": f"About my request {fresh()}"},
        )
        guuid = grievance.json()["request_uuid"]
        await call(
            http,
            "POST",
            f"/requests/{guuid}/classify",
            template=RIGHTS + "/classify",
            session=world.dpo,
            json={"request_type": "grievance"},
        )
        await call(
            http,
            "POST",
            f"/requests/{guuid}/transition",
            template=RIGHTS + "/transition",
            session=world.dpo,
            json={"to": "in_progress"},
        )
        read = await call(http, "GET", f"/requests/{guuid}", template=RIGHTS, session=world.dpo)
        assert read.json()["holders"] == [] and read.json()["holders_derived_at"] is None
    finally:
        await _connection(http, world, on=False)
