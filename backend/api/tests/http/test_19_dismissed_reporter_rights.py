"""A dismissed report from the public link, and its reporter's rights, over HTTP (0065).

The world's data principal reports an incident through the public link and an
office dismisses it. Her erasure request, once started, lists it and nobody
else's, sealed, and the officer erases her name and email from it: the
dismissed list then shows the report with neither, and keeps the reason and
who dismissed it. Nobody but the officers reaches it. A reporter with no
account asks on the public form, is sent a code at the address the report came
from, and is found and erased the same way.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from cmp.auth.authentication import otp
from cmp.auth.rate_limit import service as ratelimit
from tests.conftest import plain
from tests.http.conftest import SessionFactory, fresh, fresh_email, last_code
from tests.http.contract import call
from tests.http.world import World, build

RIGHTS = "/requests/{request_uuid}"
ERASE = RIGHTS + "/public-reports/erase"
VERIFY = "cmp.notifications.send_rights_verification_code"


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


async def _dismissed(http: httpx.AsyncClient, world: World, email: str, title: str) -> str:
    """A report through the public link from this address, dismissed by the DPO."""
    issued = await otp.issue(otp.Scope.INCIDENT_REPORT, ratelimit.contact_key(email))
    made = await call(
        http,
        "POST",
        "/incident-reports",
        expect=201,
        json={
            "name": "Walker Public",
            "email": email,
            "title": title,
            "incident_details": "It had the participant list on it",
            "code": issued.code,
        },
    )
    reference = str(made.json()["reference"])
    first = await call(http, "GET", "/breaches/intake", session=world.dpo)
    offset = max(0, int(first.json()["total"]) - 200)
    page = await call(
        http,
        "GET",
        "/breaches/intake",
        session=world.dpo,
        params={"limit": 200, "offset": offset},
    )
    [mine] = [r for r in page.json()["items"] if r["reference"] == reference]
    await call(
        http,
        "POST",
        f"/breaches/intake/{mine['report_uuid']}/dismiss",
        template="/breaches/intake/{report_uuid}/dismiss",
        session=world.dpo,
        json={"reason": "Not a breach of ours"},
    )
    return reference


async def _started(http: httpx.AsyncClient, world: World, ruuid: str, kind: str) -> None:
    """Classified, erasure meant, in an office's queue, and in progress."""
    dpo = world.dpo
    await call(
        http,
        "POST",
        f"/requests/{ruuid}/classify",
        template=RIGHTS + "/classify",
        session=dpo,
        json={"request_type": kind, "note": "As stated."},
    )
    if kind == "erasure":
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/intent",
            template=RIGHTS + "/intent",
            session=dpo,
            expect=(200, 204),
        )
    shown = await call(http, "GET", f"/requests/{ruuid}", template=RIGHTS, session=dpo)
    if shown.json()["office"] is None:
        await call(
            http, "POST", f"/requests/{ruuid}/claim", template=RIGHTS + "/claim", session=dpo
        )
    await call(
        http,
        "POST",
        f"/requests/{ruuid}/transition",
        template=RIGHTS + "/transition",
        session=dpo,
        json={"to": "in_progress"},
    )


async def _dismissed_list(http: httpx.AsyncClient, world: World) -> dict[str, dict[str, Any]]:
    kept = await call(http, "GET", "/breaches/intake/dismissed", session=world.dpo)
    return {r["reference"]: r for r in kept.json()}


async def _her_request(http: httpx.AsyncClient, world: World, kind: str, **over: Any) -> str:
    made = await call(
        http,
        "POST",
        "/me/requests",
        session=world.principal,
        expect=(200, 201),
        json={"request_type": kind, "request_text": f"About what I reported {fresh()}", **over},
    )
    return str(made.json()["request_uuid"])


class TestAReporterWithAnAccount:
    async def test_her_erasure_finds_her_report_and_takes_her_name_and_email_off_it(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        mine = await _dismissed(http, world, world.principal_email, "A laptop left on a train")
        theirs = await _dismissed(http, world, fresh_email("reporter"), "Someone else's")

        ruuid = await _her_request(http, world, "erasure")
        await _started(http, world, ruuid, "erasure")

        one = await call(http, "GET", f"/requests/{ruuid}", template=RIGHTS, session=world.dpo)
        found = one.json()["public_reports"]
        listed = {i["reference"]: i for i in found["items"]}
        assert mine in listed and theirs not in listed
        assert found["looked"] is True and found["may_erase"] is True
        assert str(listed[mine]["reporter_email"]).startswith("SE::")
        assert plain(listed[mine]["reporter_email"]) == world.principal_email
        assert plain(listed[mine]["title"]) == "A laptop left on a train"
        assert "report(s) they sent through the public link" in one.json()["complete_blocked_by"]

        erased = await call(
            http,
            "POST",
            f"/requests/{ruuid}/public-reports/erase",
            template=ERASE,
            session=world.dpo,
        )
        [item] = [i for i in erased.json()["items"] if i["reference"] == mine]
        assert item["reporter_name"] is None and item["reporter_email"] is None
        assert item["reporter_erased_at"]
        assert erased.json()["total"] == 0 and erased.json()["may_erase"] is False

        again = await call(
            http,
            "POST",
            f"/requests/{ruuid}/public-reports/erase",
            template=ERASE,
            session=world.dpo,
            json={},
        )
        assert again.json() == erased.json(), "nothing left to erase changes nothing"

        dismissed = await _dismissed_list(http, world)
        assert dismissed[mine]["reporter_name"] is None
        assert dismissed[mine]["reporter_email"] is None
        assert dismissed[mine]["reporter_erased_at"]
        assert plain(dismissed[mine]["dismissal_reason"]) == "Not a breach of ours"
        assert dismissed[mine]["dismissed_by_name"]
        assert plain(dismissed[theirs]["reporter_email"]).startswith("reporter")
        assert dismissed[theirs]["reporter_erased_at"] is None

    async def test_nobody_but_the_officers_erases(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        ruuid = await _her_request(http, world, "erasure")
        path = f"/requests/{ruuid}/public-reports/erase"
        await call(http, "POST", path, template=ERASE, session=world.dco, expect=403)
        await call(http, "POST", path, template=ERASE, session=world.admin, expect=404)
        await call(http, "POST", path, template=ERASE, expect=401)
        # Not started yet: verified by her session, not classified.
        refused = await call(http, "POST", path, template=ERASE, session=world.dpo, expect=409)
        assert refused.json()["error"]["code"] == "request_not_started"

    async def test_an_access_request_lists_them_and_does_not_erase(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        mine = await _dismissed(http, world, world.principal_email, "A list on a printer")
        ruuid = await _her_request(http, world, "access")
        await _started(http, world, ruuid, "access")
        one = await call(http, "GET", f"/requests/{ruuid}", template=RIGHTS, session=world.dpo)
        assert mine in {i["reference"] for i in one.json()["public_reports"]["items"]}
        refused = await call(
            http,
            "POST",
            f"/requests/{ruuid}/public-reports/erase",
            template=ERASE,
            session=world.dpo,
            expect=409,
        )
        assert refused.json()["error"]["code"] == "not_erasure"

    async def test_the_administrator_on_a_request_about_the_office_is_shown_none(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        ruuid = await _her_request(http, world, "erasure", about_dpo=True)
        one = await call(http, "GET", f"/requests/{ruuid}", template=RIGHTS, session=world.admin)
        assert one.json()["public_reports"] is None
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/public-reports/erase",
            template=ERASE,
            session=world.admin,
            expect=404,
        )


class TestAReporterWithNoAccount:
    async def test_a_code_goes_to_the_report_s_address_and_her_name_comes_off(
        self, http: httpx.AsyncClient, world: World, queued: Any
    ) -> None:
        address = fresh_email("walker")
        mine = await _dismissed(http, world, address, "A badge found in the car park")
        made = await call(
            http,
            "POST",
            "/rights/requests",
            expect=(200, 201),
            json={
                "request_type": "erasure",
                "contact": address.upper(),
                "name": "Walker Public",
                "request_text": "Please take my name off what I sent",
            },
        )
        reference = made.json()["reference"]
        [sent] = [args for name, args in queued if name == VERIFY and args[2] == reference]
        assert plain(sent[0]) == address, "the address stored on the report"
        code = last_code(queued, VERIFY, position=1)
        await call(
            http, "POST", "/rights/requests/verify", json={"reference": reference, "code": code}
        )

        listed = await call(http, "GET", "/requests", session=world.dpo, params={"q": reference})
        ruuid = next(r for r in listed.json()["items"] if r["reference"] == reference)[
            "request_uuid"
        ]
        await _started(http, world, ruuid, "erasure")
        one = await call(http, "GET", f"/requests/{ruuid}", template=RIGHTS, session=world.dpo)
        assert [i["reference"] for i in one.json()["public_reports"]["items"]] == [mine]
        await call(
            http,
            "POST",
            f"/requests/{ruuid}/public-reports/erase",
            template=ERASE,
            session=world.dpo,
        )
        assert (await _dismissed_list(http, world))[mine]["reporter_email"] is None
