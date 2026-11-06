"""The breach workflow of 2026-11-06 over HTTP (ADR 0037).

The public link: a code to the address typed, then the report with it. It waits
in the shared intake, on no clock, until an officer claims or dismisses it.
Who hears of it, and who is on the organisation's board, is kept by the
administrator, the DPO and Legal; nobody else reaches it. A breach ticket's
date moves on either side, with a reason.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest

from cmp.auth.authentication import otp
from cmp.auth.rate_limit import service as ratelimit
from cmp.core.config import settings
from tests.conftest import plain
from tests.http.conftest import DOMAIN, SessionFactory
from tests.http.contract import assert_sealed, call
from tests.http.world import World, build

B = "/breaches/{breach_uuid}"


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


@pytest.fixture(autouse=True)
def internal(monkeypatch: pytest.MonkeyPatch) -> None:
    """This suite's accounts are on its own reserved domain."""
    monkeypatch.setattr(settings, "breach_ticket_email_domains", (DOMAIN,))


def _body(**over: Any) -> dict[str, Any]:
    return {
        "name": "Asha Rao",
        "email": "reporter@http-suite.test",
        "title": "A laptop left on a train",
        "incident_details": "It had the participant list on it",
        **over,
    }


async def _report(http: httpx.AsyncClient, **over: Any) -> str:
    body = _body(**over)
    issued = await otp.issue(otp.Scope.INCIDENT_REPORT, ratelimit.contact_key(body["email"]))
    made = await call(
        http, "POST", "/incident-reports", json={**body, "code": issued.code}, expect=201
    )
    reference: str = made.json()["reference"]
    assert reference.startswith("INC-")
    return reference


async def _waiting(http: httpx.AsyncClient, session: Any) -> list[dict[str, Any]]:
    """The last page, where a report just made is: oldest first, and whatever
    this database already had waiting comes before it."""
    first = await call(http, "GET", "/breaches/intake", session=session)
    offset = max(0, int(first.json()["total"]) - 200)
    last = await call(
        http,
        "GET",
        "/breaches/intake",
        session=session,
        params={"limit": 200, "offset": offset},
    )
    items: list[dict[str, Any]] = last.json()["items"]
    return items


class TestThePublicLink:
    async def test_a_code_needs_no_account_and_says_nothing(
        self, http: httpx.AsyncClient, queued: Any
    ) -> None:
        sent = await call(
            http, "POST", "/incident-reports/code", json={"email": "someone@http-suite.test"}
        )
        assert sent.json()["ok"] is True
        assert any(q[0].endswith("send_incident_report_code") for q in queued)

    async def test_a_wrong_code_takes_nothing(self, http: httpx.AsyncClient) -> None:
        await call(
            http,
            "POST",
            "/incident-reports",
            json={**_body(), "code": "000000"},
            expect=400,
        )

    async def test_a_report_tells_the_office_and_the_reporter(
        self, http: httpx.AsyncClient, queued: Any
    ) -> None:
        await _report(http)
        names = [q[0] for q in queued]
        assert any(n.endswith("send_incident_reported") for n in names)
        assert any(n.endswith("send_incident_report_received") for n in names)


class TestTheSharedIntake:
    async def test_an_office_claims_it_and_it_becomes_an_incident_on_no_clock(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        reference = await _report(http, cyber_attack="yes")
        [mine] = [r for r in await _waiting(http, world.dpo) if r["reference"] == reference]
        assert str(mine["title"]).startswith("SE::") and plain(mine["title"])
        assert str(mine["reporter_email"]).startswith("SE::")
        assert "logged" not in mine, "the long text is read a report at a time"
        full = await call(
            http,
            "GET",
            f"/breaches/intake/{mine['report_uuid']}",
            template="/breaches/intake/{report_uuid}",
            session=world.dpo,
        )
        told = full.json()["logged"]["incident_details"]
        assert str(told).startswith("SE::") and plain(told)
        claimed = await call(
            http,
            "POST",
            f"/breaches/intake/{mine['report_uuid']}/claim",
            template="/breaches/intake/{report_uuid}/claim",
            session=world.dpo,
            expect=201,
        )
        body = claimed.json()
        assert body["incident_reference"] == reference
        assert body["obligations"] == [], "nothing runs until validation, whatever they said"
        assert body["reported"]["cyber_attack"] == "yes"
        await call(
            http,
            "GET",
            f"/breaches/intake/{mine['report_uuid']}",
            template="/breaches/intake/{report_uuid}",
            session=world.dpo,
            expect=409,
        )
        await call(
            http,
            "POST",
            f"/breaches/intake/{mine['report_uuid']}/claim",
            template="/breaches/intake/{report_uuid}/claim",
            session=world.dpo,
            expect=409,
        )

    async def test_a_report_is_dismissed_with_a_reason(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        reference = await _report(http)
        [mine] = [r for r in await _waiting(http, world.dpo) if r["reference"] == reference]
        path = f"/breaches/intake/{mine['report_uuid']}/dismiss"
        template = "/breaches/intake/{report_uuid}/dismiss"
        await call(http, "POST", path, template=template, session=world.dpo, json={}, expect=422)
        await call(
            http, "POST", path, template=template, session=world.dpo, json={"reason": "A test"}
        )
        assert reference not in {r["reference"] for r in await _waiting(http, world.dpo)}
        kept = await call(http, "GET", "/breaches/intake/dismissed", session=world.dpo)
        [dismissed] = [r for r in kept.json() if r["reference"] == reference]
        assert plain(dismissed["dismissal_reason"]) == "A test"
        assert plain(dismissed["reporter_email"]) == "reporter@http-suite.test"
        assert dismissed["dismissed_by_name"] and dismissed["dismissed_at"]
        await call(http, "GET", "/breaches/intake/dismissed", session=world.dco, expect=404)

    async def test_a_page_is_bounded_and_says_how_many_wait(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        await _report(http)
        page = await call(http, "GET", "/breaches/intake", session=world.dpo)
        body = page.json()
        assert (body["limit"], body["offset"]) == (50, 0)
        assert body["total"] >= 1 and len(body["items"]) <= 50
        for bad in ({"limit": 201}, {"limit": 0}, {"offset": -1}, {"offset": 10**30}):
            await call(http, "GET", "/breaches/intake", session=world.dpo, params=bad, expect=422)

    async def test_both_offices_read_the_shared_intake(
        self, http: httpx.AsyncClient, world: World, session_for: SessionFactory
    ) -> None:
        reference = await _report(http)
        legal = await session_for("legal")
        for officer in (world.dpo, legal):
            [mine] = [r for r in await _waiting(http, officer) if r["reference"] == reference]
            await call(
                http,
                "GET",
                f"/breaches/intake/{mine['report_uuid']}",
                template="/breaches/intake/{report_uuid}",
                session=officer,
            )

    async def test_nobody_else_reads_the_intake(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        for who in (world.dco, world.admin, world.rnd):
            await call(http, "GET", "/breaches/intake", session=who, expect=404)
            await call(
                http,
                "GET",
                "/breaches/intake/00000000-0000-4000-8000-000000000000",
                template="/breaches/intake/{report_uuid}",
                session=who,
                expect=404,
            )
        await call(http, "GET", "/breaches/intake", expect=401)


class TestACertInMarkMadeInError:
    async def test_it_is_set_aside_after_a_no_and_the_incident_closes(
        self, http: httpx.AsyncClient, world: World, session_for: SessionFactory
    ) -> None:
        made = await call(
            http,
            "POST",
            "/breaches",
            session=world.dpo,
            expect=201,
            json={
                "title": "An alarm that was only a test",
                "detected_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
                "location_kind": "platform",
                "cyber_attack": "yes",
            },
        )
        path = f"/breaches/{made.json()['breach_uuid']}"
        aside = f"{path}/cert-in/not-applicable"
        template = f"{B}/cert-in/not-applicable"
        word = {"reason": "The scanner set it off"}
        early = await call(
            http, "POST", aside, template=template, session=world.dpo, json=word, expect=409
        )
        assert "cert_in_not_validated_no" in early.text
        await call(
            http,
            "POST",
            f"{path}/determinations",
            template=f"{B}/determinations",
            session=world.dpo,
            json={"outcome": "no", "reasoning": "Nothing was reached"},
        )
        await call(http, "POST", aside, template=template, session=world.dpo, json={}, expect=422)
        legal = await session_for("legal")
        for who in (legal, world.dco):
            await call(http, "POST", aside, template=template, session=who, json=word, expect=404)
        done = await call(http, "POST", aside, template=template, session=world.dpo, json=word)
        [duty] = [d for d in done.json()["obligations"] if d["duty"] == "cert_in"]
        assert duty["state"] == "not_applicable"
        assert plain(duty["events"][-1]["note"]) == word["reason"]
        assert str(duty["events"][-1]["note"]).startswith("SE::")
        back = await call(
            http, "POST", f"{path}/cert-in", template=f"{B}/cert-in", session=world.dpo
        )
        [duty] = [d for d in back.json()["obligations"] if d["duty"] == "cert_in"]
        assert duty["state"] == "outstanding"
        await call(http, "POST", aside, template=template, session=world.dpo, json=word)
        closed = await call(
            http,
            "POST",
            f"{path}/transition",
            template=f"{B}/transition",
            session=world.dpo,
            json={"to": "closed"},
        )
        assert closed.json()["status"] == "closed"


class TestTheOfficersBell:
    async def test_the_legal_office_hears_what_a_holder_does_on_its_ticket(
        self, http: httpx.AsyncClient, world: World, session_for: SessionFactory
    ) -> None:
        legal = await session_for("legal")
        made = await call(
            http,
            "POST",
            "/breaches",
            session=legal,
            expect=201,
            json={
                "title": "A shared drive open to all staff",
                "detected_at": (datetime.now(UTC) - timedelta(hours=2)).isoformat(),
                "location_kind": "platform",
            },
        )
        uuid = str(made.json()["breach_uuid"])
        path = f"/breaches/{uuid}"
        await call(
            http,
            "POST",
            f"{path}/determinations",
            template=f"{B}/determinations",
            session=legal,
            json={
                "outcome": "yes",
                "reasoning": "Yes",
                "became_aware_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            },
        )
        when = datetime.now(UTC).date() + timedelta(days=2)
        ticket = await call(
            http,
            "POST",
            f"{path}/tickets",
            template=f"{B}/tickets",
            session=legal,
            expect=201,
            json={"user_uuid": world.dco.uuid, "instruction": "Keep it", "answer_by": str(when)},
        )
        id_ = ticket.json()["ticket"]["ticket_uuid"]
        await call(
            http,
            "POST",
            f"/breach-tickets/{id_}/resolve-by",
            template="/breach-tickets/{ticket_uuid}/resolve-by",
            session=world.dco,
            json={"answer_by": str(when + timedelta(days=3)), "reason": "The vendor is away"},
        )

        async def heard(session: Any) -> list[dict[str, Any]]:
            # Untyped, so the documented list cannot name it: its rules, by hand.
            bell = await call(http, "GET", "/notifications", session=session, check_sealed=False)
            assert_sealed(bell.json(), where="GET /notifications", endpoint="/notifications")
            items: list[dict[str, Any]] = bell.json()["items"]
            return [r for r in items if r["event_type"] == "breach_ticket.date_changed"]

        [told] = [r for r in await heard(legal) if r["entity_uuid"] == uuid]
        assert told["entity_href"] == f"/breaches/{uuid}#tickets", "and it opens"
        others = [r for r in await heard(world.dpo) if r["entity_uuid"] == uuid]
        assert others == [], "that office's alone"


class TestBreachSettings:
    async def test_the_three_who_keep_it_keep_it(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        for who in (world.admin, world.dpo):
            read = await call(http, "GET", "/breach-settings", session=who)
            assert read.json()["report_link"].endswith("/report-incident")
        roles = await call(
            http,
            "PUT",
            "/breach-settings/intake-roles",
            session=world.admin,
            json={"roles": ["rnd_user"]},
        )
        assert roles.json()["intake_roles"] == ["dpo", "legal", "rnd_user"]
        await call(
            http,
            "PUT",
            "/breach-settings/intake-roles",
            session=world.admin,
            json={"roles": []},
        )

        added = await call(
            http,
            "POST",
            "/breach-settings/board-recipients",
            session=world.admin,
            json={"full_name": "The Vice Chair", "email": "vice.chair@http-suite.test"},
        )
        [mine] = [
            r
            for r in added.json()["board_recipients"]
            if plain(r["email"]) == "vice.chair@http-suite.test"
        ]
        assert str(mine["email"]).startswith("SE::"), "sealed; the console opens it"
        assert "email_hash" not in mine, "the blind index stays on the server"
        await call(
            http,
            "DELETE",
            f"/breach-settings/board-recipients/{mine['recipient_uuid']}",
            template="/breach-settings/board-recipients/{recipient_uuid}",
            session=world.dpo,
        )

    async def test_nobody_else_reaches_it(self, http: httpx.AsyncClient, world: World) -> None:
        for who in (world.dco, world.rnd):
            await call(http, "GET", "/breach-settings", session=who, expect=403)
        await call(http, "GET", "/breach-settings", expect=401)


class TestTheDateOnATicket:
    async def test_either_side_moves_it_saying_why(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        made = await call(
            http,
            "POST",
            "/breaches",
            session=world.dpo,
            expect=201,
            json={
                "title": "A share left open",
                "detected_at": (datetime.now(UTC) - timedelta(hours=2)).isoformat(),
                "location_kind": "platform",
            },
        )
        uuid = made.json()["breach_uuid"]
        path = f"/breaches/{uuid}"
        await call(
            http,
            "POST",
            f"{path}/determinations",
            template=f"{B}/determinations",
            session=world.dpo,
            json={
                "outcome": "yes",
                "reasoning": "Yes",
                "became_aware_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            },
        )
        first = datetime.now(UTC).date() + timedelta(days=2)
        ticket = await call(
            http,
            "POST",
            f"{path}/tickets",
            template=f"{B}/tickets",
            session=world.dpo,
            expect=201,
            json={
                "user_uuid": world.dco.uuid,
                "instruction": "Keep the log",
                "answer_by": str(first),
            },
        )
        id_ = ticket.json()["ticket"]["ticket_uuid"]
        moved = await call(
            http,
            "POST",
            f"/breach-tickets/{id_}/resolve-by",
            template="/breach-tickets/{ticket_uuid}/resolve-by",
            session=world.dco,
            json={"answer_by": str(first + timedelta(days=3)), "reason": "The vendor is away"},
        )
        assert moved.json()["ticket"]["answer_by"] == str(first + timedelta(days=3))
        back = await call(
            http,
            "POST",
            f"{path}/tickets/{id_}/resolve-by",
            template=f"{B}/tickets/{{ticket_uuid}}/resolve-by",
            session=world.dpo,
            json={"answer_by": str(first + timedelta(days=1)), "reason": "Needed sooner"},
        )
        body = back.json()
        assert body["ticket"]["answer_by"] == str(first + timedelta(days=1))
        changes = [e for e in body["ticket"]["events"] if e["kind"] == "date_changed"]
        assert len(changes) == 2 and all(str(e["reason"]).startswith("SE::") for e in changes)
        await call(
            http,
            "POST",
            f"/breach-tickets/{id_}/resolve-by",
            template="/breach-tickets/{ticket_uuid}/resolve-by",
            session=world.rco,
            json={"answer_by": str(first), "reason": "Not mine"},
            expect=404,
        )
