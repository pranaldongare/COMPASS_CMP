"""The breach register over HTTP (S3-01).

The DPO walks every route: record, determine, assess, mark CERT-In, record a
submission, extend the report, close refused and allowed. Every other role is
answered 404 - on the register, on a breach that exists, and on a write - so a
caller cannot tell a breach from a uuid that was never one. Two determinations
sent at once create each duty once.

Everything the office writes about a breach is sealed. `title` and `note` are
generic names the contract cannot check by name alone, so they are checked
here, where a breach is read.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest

from tests.conftest import plain
from tests.http.conftest import SessionFactory
from tests.http.contract import call
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


def _at(hours_ago: float) -> str:
    return (datetime.now(UTC) - timedelta(hours=hours_ago)).isoformat()


def _sealed(body: dict[str, Any]) -> None:
    assert str(body["title"]).startswith("SE::")
    if body["location"]["detail"] is not None:
        assert str(body["location"]["detail"]).startswith("SE::")
    for duty in body["obligations"]:
        for event in duty["events"]:
            assert event["note"] is None or str(event["note"]).startswith("SE::")


async def _record(http: httpx.AsyncClient, world: World, **extra: Any) -> dict[str, Any]:
    made = await call(
        http,
        "POST",
        "/breaches",
        session=world.dpo,
        expect=201,
        json={
            "title": "Backup copied to a personal drive",
            "detected_at": _at(5),
            "began_at": _at(30),
            "location_kind": "processor",
            "processor_uuid": world.processor_uuid,
            "location_detail": "The lab's nightly export share",
            **extra,
        },
    )
    body: dict[str, Any] = made.json()
    _sealed(body)
    return body


class TestTheRegister:
    async def test_the_dpo_walks_every_route(self, http: httpx.AsyncClient, world: World) -> None:
        breach = await _record(http, world)
        uuid = breach["breach_uuid"]
        path = f"/breaches/{uuid}"
        assert breach["location"]["processor_uuid"] == world.processor_uuid

        marked = await call(
            http, "POST", f"{path}/cert-in", template=f"{B}/cert-in", session=world.dpo
        )
        [cert_in] = marked.json()["obligations"]
        assert cert_in["duty"] == "cert_in"
        assert 0 < cert_in["clock"]["seconds_remaining"] <= 3600

        determined = await call(
            http,
            "POST",
            f"{path}/determinations",
            template=f"{B}/determinations",
            session=world.dpo,
            json={"outcome": "yes", "reasoning": "Names and mobiles", "became_aware_at": _at(4)},
        )
        body = determined.json()
        assert {d["duty"] for d in body["obligations"]} == {
            "cert_in",
            "board_intimation",
            "board_report",
            "principals",
        }
        assert str(body["determinations"][0]["reasoning"]).startswith("SE::")

        assessed = await call(
            http,
            "POST",
            f"{path}/assessments",
            template=f"{B}/assessments",
            session=world.dpo,
            json={
                "nature_extent": "One nightly export",
                "caused_by_findings": "A contractor's sync client",
                "categories": [{"category": "Mobile", "sealed": True, "key_exposed": False}],
            },
        )
        assert str(assessed.json()["assessment"]["caused_by_findings"]).startswith("SE::")
        await call(
            http, "GET", f"{path}/assessments", template=f"{B}/assessments", session=world.dpo
        )

        for duty in ("cert_in", "board_intimation"):
            done = await call(
                http,
                "POST",
                f"{path}/obligations/{duty}/complete",
                template=f"{B}/obligations/{{duty}}/complete",
                session=world.dpo,
                json={"occurred_at": _at(1), "reference": f"REF-{duty}", "note": "Filed by hand"},
            )
            _sealed(done.json())
        extended = await call(
            http,
            "POST",
            f"{path}/obligations/board_report/extension",
            template=f"{B}/obligations/board_report/extension",
            session=world.dpo,
            json={"requested_at": _at(1), "allowed_until": _at(-24 * 10)},
        )
        report = next(d for d in extended.json()["obligations"] if d["duty"] == "board_report")
        assert report["extended_until"] is not None

        moves = await call(
            http, "GET", f"{path}/transitions", template=f"{B}/transitions", session=world.dpo
        )
        [close] = moves.json()["available"]
        assert close["to"] == "closed" and close["allowed"] is False
        await call(
            http,
            "POST",
            f"{path}/transition",
            template=f"{B}/transition",
            session=world.dpo,
            json={"to": "closed"},
            expect=409,
        )
        # An unknown duty is a 422 naming the choices, never a 500.
        await call(
            http,
            "POST",
            f"{path}/obligations/nonsense/complete",
            template=f"{B}/obligations/{{duty}}/complete",
            session=world.dpo,
            json={"occurred_at": _at(1), "reference": "x"},
            expect=422,
        )

        listed = await call(http, "GET", "/breaches", session=world.dpo, params={"status": "open"})
        assert uuid in {b["breach_uuid"] for b in listed.json()}
        for b in listed.json():
            _sealed(b)
        one = await call(http, "GET", path, template=B, session=world.dpo)
        _sealed(one.json())

    async def test_a_breach_determined_no_can_close(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        breach = await _record(http, world, location_kind="platform", processor_uuid=None)
        path = f"/breaches/{breach['breach_uuid']}"
        await call(
            http,
            "POST",
            f"{path}/determinations",
            template=f"{B}/determinations",
            session=world.dpo,
            json={"outcome": "no", "reasoning": "Test data only"},
        )
        closed = await call(
            http,
            "POST",
            f"{path}/transition",
            template=f"{B}/transition",
            session=world.dpo,
            json={"to": "closed"},
        )
        assert closed.json()["status"] == "closed"
        assert closed.json()["status_history"][-1]["changed_by_name"].startswith("SE::")


class TestWhoItTouched:
    async def test_derive_preview_confirm_and_list(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        breach = await _record(http, world)
        path = f"/breaches/{breach['breach_uuid']}"
        scope = {"kind": "processor", "processor_uuid": world.processor_uuid}
        shown = await call(
            http,
            "POST",
            f"{path}/affected/preview",
            template=f"{B}/affected/preview",
            session=world.dpo,
            json={"scopes": [scope]},
        )
        assert shown.json()["derived"] >= 1, "the world exported to its processor"
        confirmed = await call(
            http,
            "POST",
            f"{path}/affected",
            template=f"{B}/affected",
            session=world.dpo,
            json={
                "scopes": [scope],
                "add": [world.principal.uuid] if world.principal else [],
                "note": "From the export log",
            },
        )
        body = confirmed.json()
        assert body["total"] >= 1 and body["revisions"][0]["note"].startswith("SE::")
        assert all(
            p["full_name"] is None or p["full_name"].startswith("SE::") for p in body["people"]
        )
        listed = await call(
            http, "GET", f"{path}/affected", template=f"{B}/affected", session=world.dpo
        )
        assert listed.json()["total"] == body["total"]
        assert "consent_artefact" in listed.json()["platform_tables"]
        await call(
            http,
            "POST",
            f"{path}/affected/preview",
            template=f"{B}/affected/preview",
            session=world.dpo,
            json={"scopes": [{"kind": "platform", "tables": ["pg_authid"]}]},
            expect=422,
        )


class TestTellingThePeople:
    async def test_draft_approve_send_twice_and_she_reads_it(
        self, http: httpx.AsyncClient, world: World, queued: Any
    ) -> None:
        assert world.principal is not None
        breach = await _record(http, world, location_kind="platform", processor_uuid=None)
        path = f"/breaches/{breach['breach_uuid']}"
        await call(
            http,
            "POST",
            f"{path}/affected",
            template=f"{B}/affected",
            session=world.dpo,
            json={"add": [world.principal.uuid]},
        )
        words = {
            "what_happened": "A list was sent to the wrong address.",
            "consequences": "Your mobile number may have been seen.",
            "measures": "The recipient deleted it.",
            "protective_steps": "Ignore calls that mention the study.",
        }
        drafted = await call(
            http,
            "POST",
            f"{path}/notices",
            template=f"{B}/notices",
            session=world.dpo,
            json=words,
            expect=201,
        )
        notice = drafted.json()["versions"][-1]["notice_uuid"]
        # Four of five: a draft may be incomplete; an approval may not.
        await call(
            http,
            "POST",
            f"{path}/notices/{notice}/approve",
            template=f"{B}/notices/{{notice_uuid}}/approve",
            session=world.dpo,
            expect=422,
        )
        await call(
            http,
            "POST",
            f"{path}/notices/send",
            template=f"{B}/notices/send",
            session=world.dpo,
            expect=409,
        )
        await call(
            http,
            "PUT",
            f"{path}/notices/{notice}",
            template=f"{B}/notices/{{notice_uuid}}",
            session=world.dpo,
            json={**words, "contact": "privacy@example.org"},
        )
        await call(
            http,
            "POST",
            f"{path}/notices/{notice}/approve",
            template=f"{B}/notices/{{notice_uuid}}/approve",
            session=world.dpo,
        )
        await asyncio.gather(
            call(
                http,
                "POST",
                f"{path}/notices/send",
                template=f"{B}/notices/send",
                session=world.dpo,
            ),
            call(
                http,
                "POST",
                f"{path}/notices/send",
                template=f"{B}/notices/send",
                session=world.dpo,
            ),
        )
        account = await call(
            http, "GET", f"{path}/notices", template=f"{B}/notices", session=world.dpo
        )
        portal = [r for r in account.json()["account"] if r["channel"] == "portal"]
        assert sum(r["people"] for r in portal) == 1, "two sends at once wrote her account once"
        assert len([q for q in queued if q[0].endswith("send_breach_notice")]) >= 1
        mine = await call(http, "GET", "/me/breach-notices", session=world.principal)
        assert [n["reference"] for n in mine.json()] == [breach["reference"]]
        assert str(mine.json()[0]["contact"]).startswith("SE::"), "sealed, opened by her portal"
        assert plain(mine.json()[0]["contact"]) == "privacy@example.org"


class TestTheBoardAndTheDashboard:
    async def test_documents_and_the_dashboard(self, http: httpx.AsyncClient, world: World) -> None:
        breach = await _record(http, world, location_kind="platform", processor_uuid=None)
        path = f"/breaches/{breach['breach_uuid']}"
        intimation = await call(
            http,
            "GET",
            f"{path}/board/intimation",
            template=f"{B}/board/intimation",
            session=world.dpo,
        )
        assert intimation.json()["basis"] == "Rule 7(2)(a)"
        assert str(intimation.json()["title"]).startswith("SE::")
        report = await call(
            http, "GET", f"{path}/board/report", template=f"{B}/board/report", session=world.dpo
        )
        body = report.json()
        assert body["notices"]["sent"] is False
        assert body["notices"]["statement"].startswith("No notice has yet been sent")

        mine = await call(http, "GET", "/dashboard", session=world.dpo)
        assert breach["breach_uuid"] in {b["breach_uuid"] for b in mine.json()["breaches"]}
        assert all(str(b["title"]).startswith("SE::") for b in mine.json()["breaches"])
        theirs = await call(http, "GET", "/dashboard", session=world.admin)
        assert theirs.json()["breaches"] == [], "nobody else learns a breach is open"


class TestHiddenFromEveryoneElse:
    async def test_every_other_role_is_told_it_is_not_there(
        self, http: httpx.AsyncClient, world: World, session_for: SessionFactory
    ) -> None:
        breach = await _record(http, world, location_kind="platform", processor_uuid=None)
        real = f"/breaches/{breach['breach_uuid']}"
        never = "/breaches/00000000-0000-4000-8000-000000000000"
        principal = world.principal or await session_for("data_subject")
        for who in (world.admin, world.rnd, world.dco, world.dco_admin, world.rco, principal):
            listed = await call(http, "GET", "/breaches", session=who, expect=404)
            seen = await call(http, "GET", real, template=B, session=who, expect=404)
            unseen = await call(http, "GET", never, template=B, session=who, expect=404)
            # The same answer, but for the request id every error carries.
            same = [
                {k: v for k, v in r.json()["error"].items() if k != "request_id"}
                for r in (seen, unseen)
            ]
            assert same[0] == same[1], "a real breach reads exactly like no breach"
            assert listed.status_code == 404
            await call(
                http, "GET", f"{real}/affected", template=f"{B}/affected", session=who, expect=404
            )
            await call(
                http, "GET", f"{real}/notices", template=f"{B}/notices", session=who, expect=404
            )
            await call(
                http,
                "GET",
                f"{real}/board/report",
                template=f"{B}/board/report",
                session=who,
                expect=404,
            )
            await call(
                http,
                "POST",
                f"{real}/determinations",
                template=f"{B}/determinations",
                session=who,
                json={"outcome": "no", "reasoning": "x"},
                expect=404,
            )


class TestTheRace:
    async def test_two_determinations_at_once_create_each_duty_once(
        self, http: httpx.AsyncClient, world: World
    ) -> None:
        breach = await _record(http, world, location_kind="platform", processor_uuid=None)
        path = f"/breaches/{breach['breach_uuid']}"
        body = {"outcome": "yes", "reasoning": "Confirmed", "became_aware_at": _at(2)}
        first, second = await asyncio.gather(
            call(
                http,
                "POST",
                f"{path}/determinations",
                template=f"{B}/determinations",
                session=world.dpo,
                json=body,
            ),
            call(
                http,
                "POST",
                f"{path}/determinations",
                template=f"{B}/determinations",
                session=world.dpo,
                json=body,
            ),
        )
        assert first.status_code == second.status_code == 200
        final = await call(http, "GET", path, template=B, session=world.dpo)
        duties = [d["duty"] for d in final.json()["obligations"]]
        assert sorted(duties) == ["board_intimation", "board_report", "principals"]
        assert len(final.json()["determinations"]) == 2
