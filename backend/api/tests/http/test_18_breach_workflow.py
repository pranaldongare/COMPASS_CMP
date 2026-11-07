"""The breach workflow of 2026-11-06 over HTTP (ADR 0037).

The public link: a code to the address typed, then the report with it. It waits
in the shared intake, on no clock, until an officer claims or dismisses it.
Who hears of it, and who is on the organisation's board, is kept by the
administrator, the DPO and Legal; nobody else reaches it. An entry on the list
may be made mandatory, and both offices' officers hear of every change to it
(2026-11-07). The sender chooses who each report goes to, and a report to
CERT-In before a yes waits for it. A breach ticket's date moves on either side,
with a reason.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import httpx
import pytest

from cmp.auth.authentication import otp
from cmp.auth.rate_limit import service as ratelimit
from cmp.core.config import settings
from cmp.db.pool import transaction
from cmp.db.repositories import incident_reports
from tests.conftest import plain
from tests.http.conftest import DOMAIN, SessionFactory, fresh_email
from tests.http.contract import assert_sealed, call
from tests.http.test_06_breaches import everyone, on_the_board
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
    async def test_it_is_set_aside_whatever_validation_says_and_the_incident_closes(
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
        await call(http, "POST", aside, template=template, session=world.dpo, json={}, expect=422)
        legal = await session_for("legal")
        for who in (legal, world.dco):
            await call(http, "POST", aside, template=template, session=who, json=word, expect=404)
        done = await call(http, "POST", aside, template=template, session=world.dpo, json=word)
        assert done.json()["determinations"] == [], "set aside before any validation"
        [duty] = [d for d in done.json()["obligations"] if d["duty"] == "cert_in"]
        assert duty["state"] == "not_applicable"
        assert plain(duty["events"][-1]["note"]) == word["reason"]
        assert str(duty["events"][-1]["note"]).startswith("SE::")
        assert duty["events"][-1]["determination_uuid"] is None
        again = await call(
            http, "POST", aside, template=template, session=world.dpo, json=word, expect=409
        )
        assert "duty_not_outstanding" in again.text
        back = await call(
            http, "POST", f"{path}/cert-in", template=f"{B}/cert-in", session=world.dpo
        )
        [duty] = [d for d in back.json()["obligations"] if d["duty"] == "cert_in"]
        assert duty["state"] == "outstanding"
        assert {k: duty["events"][-1][k] for k in ("kind", "determination_uuid")} == {
            "kind": "reinstated",
            "determination_uuid": None,
        }
        await call(
            http,
            "POST",
            f"{path}/determinations",
            template=f"{B}/determinations",
            session=world.dpo,
            json={"outcome": "no", "reasoning": "Nothing was reached"},
        )
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
        self, http: httpx.AsyncClient, world: World, queued: Any
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

        address = fresh_email("vice.chair.")
        added = await call(
            http,
            "POST",
            "/breach-settings/board-recipients",
            session=world.admin,
            json={"full_name": "The Vice Chair", "email": address},
        )
        [mine] = [r for r in added.json()["board_recipients"] if plain(r["email"]) == address]
        assert str(mine["email"]).startswith("SE::"), "sealed; the console opens it"
        assert "email_hash" not in mine, "the blind index stays on the server"
        assert (mine["mandatory"], mine["mandatory_changed_at"]) == (False, None)

        entry = f"/breach-settings/board-recipients/{mine['recipient_uuid']}"
        template = "/breach-settings/board-recipients/{recipient_uuid}"
        before = len(queued)
        marked = await call(
            http,
            "PUT",
            f"{entry}/mandatory",
            template=f"{template}/mandatory",
            session=world.admin,
            json={"mandatory": True},
        )
        [mine] = [
            r
            for r in marked.json()["board_recipients"]
            if r["recipient_uuid"] == mine["recipient_uuid"]
        ]
        assert mine["mandatory"] is True and mine["mandatory_changed_at"]
        assert str(mine["mandatory_changed_by_name"]).startswith("SE::")
        refused = await call(
            http, "DELETE", entry, template=template, session=world.dpo, expect=409
        )
        assert "recipient_mandatory" in refused.text
        for who in (world.dco, world.rnd):
            await call(
                http,
                "PUT",
                f"{entry}/mandatory",
                template=f"{template}/mandatory",
                session=who,
                json={"mandatory": False},
                expect=403,
            )
        await call(
            http,
            "PUT",
            f"{entry}/mandatory",
            template=f"{template}/mandatory",
            session=world.dpo,
            json={"mandatory": False},
        )
        await call(http, "DELETE", entry, template=template, session=world.dpo)
        await call(
            http,
            "PUT",
            f"{entry}/mandatory",
            template=f"{template}/mandatory",
            session=world.dpo,
            json={"mandatory": True},
            expect=404,
        )

        told = [a for n, a in queued[before:] if n.endswith("send_breach_board_list_changed")]
        async with transaction() as conn:
            officers = await incident_reports.active_emails(conn, ["dpo", "legal"])
            trail = await (
                await conn.execute(
                    """SELECT detail_json FROM audit_log
                        WHERE event_type = 'breach_settings.changed'
                          AND detail_json->>'recipient' = %s
                        ORDER BY log_id""",
                    (str(mine["recipient_uuid"]),),
                )
            ).fetchall()
        assert sorted(str(a[0]) for a in told) == sorted(officers * 3), "both offices, each time"
        assert [a[3] for a in told[:: len(officers)]] == [
            "made this address mandatory on",
            "made this address optional again on",
            "took this address off",
        ]
        assert [r["detail_json"]["board_recipient"] for r in trail] == [
            "added",
            "made_mandatory",
            "made_optional",
            "removed",
        ]
        assert "@" not in str(trail), "the trail names no address"

    async def test_nobody_else_reaches_it(self, http: httpx.AsyncClient, world: World) -> None:
        for who in (world.dco, world.rnd):
            await call(http, "GET", "/breach-settings", session=who, expect=403)
        await call(http, "GET", "/breach-settings", expect=401)


async def _incident(
    http: httpx.AsyncClient, world: World, *, title: str, cyber_attack: str | None = None
) -> str:
    made = await call(
        http,
        "POST",
        "/breaches",
        session=world.dpo,
        expect=201,
        json={
            "title": title,
            "detected_at": (datetime.now(UTC) - timedelta(hours=2)).isoformat(),
            "location_kind": "platform",
            **({"cyber_attack": cyber_attack} if cyber_attack else {}),
        },
    )
    return f"/breaches/{made.json()['breach_uuid']}"


async def _yes(http: httpx.AsyncClient, world: World, path: str) -> None:
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


async def _written(http: httpx.AsyncClient, world: World, path: str, kind: str) -> str:
    """A draft of this kind with every section said, by its path."""
    drafted = await call(
        http,
        "POST",
        f"{path}/reports",
        template=f"{B}/reports",
        session=world.dpo,
        json={"kind": kind},
        expect=201,
    )
    [view] = [k for k in drafted.json()["kinds"] if k["kind"] == kind]
    doc = view["versions"][0]
    report = f"{path}/reports/{doc['report_uuid']}"
    await call(
        http,
        "PUT",
        report,
        template=f"{B}/reports/{{report_uuid}}",
        session=world.dpo,
        json={"sections": {s["key"]: "As the office wrote it" for s in doc["sections"]}},
    )
    return report


def _mailed(queued: Any, before: int) -> int:
    return sum(1 for n, _ in queued[before:] if n.endswith("send_breach_report"))


class TestWhoAReportGoesTo:
    async def test_the_sender_chooses_and_a_mandatory_entry_goes_with_it(
        self,
        http: httpx.AsyncClient,
        world: World,
        session_for: SessionFactory,
        queued: Any,
    ) -> None:
        path = await _incident(http, world, title="A spreadsheet mailed to the wrong list")
        await _yes(http, world, path)
        await on_the_board(http, world)
        address = fresh_email("member.")
        added = await call(
            http,
            "POST",
            "/breach-settings/board-recipients",
            session=world.dpo,
            json={"full_name": "A Member", "email": address},
        )
        [member] = [r for r in added.json()["board_recipients"] if plain(r["email"]) == address]
        entry = f"/breach-settings/board-recipients/{member['recipient_uuid']}"
        try:
            window = f"{B}/reports/recipients"

            offered = await call(
                http, "GET", f"{path}/reports/recipients", template=window, session=world.dpo
            )
            listed = offered.json()["recipients"]
            assert listed and all(str(r["email"]).startswith("SE::") for r in listed)
            assert all(
                set(r) == {"recipient_uuid", "full_name", "email", "mandatory"} for r in listed
            )
            legal = await session_for("legal")
            for who in (world.dco, world.admin, legal):
                await call(
                    http,
                    "GET",
                    f"{path}/reports/recipients",
                    template=window,
                    session=who,
                    expect=404,
                )

            report = await _written(http, world, path, "board_intimation")
            finalise = f"{B}/reports/{{report_uuid}}/finalise"
            await call(
                http, "POST", f"{report}/finalise", template=finalise, session=world.dpo, expect=422
            )
            await call(
                http,
                "PUT",
                f"{entry}/mandatory",
                template="/breach-settings/board-recipients/{recipient_uuid}/mandatory",
                session=world.admin,
                json={"mandatory": True},
            )
            others = [
                r["recipient_uuid"]
                for r in listed
                if r["recipient_uuid"] != member["recipient_uuid"]
            ]
            left_out = await call(
                http,
                "POST",
                f"{report}/finalise",
                template=finalise,
                session=world.dpo,
                json={"recipients": others},
                expect=409,
            )
            assert "recipient_mandatory" in left_out.text
            gone = await call(
                http,
                "POST",
                f"{report}/finalise",
                template=finalise,
                session=world.dpo,
                json={"recipients": [*others, member["recipient_uuid"], str(uuid4())]},
                expect=409,
            )
            assert "recipient_not_listed" in gone.text

            mandatory = [
                r["recipient_uuid"]
                for r in (
                    await call(
                        http,
                        "GET",
                        f"{path}/reports/recipients",
                        template=window,
                        session=world.dpo,
                    )
                ).json()["recipients"]
                if r["mandatory"]
            ]
            alone = fresh_email("auditor.")
            before = len(queued)
            sent = await call(
                http,
                "POST",
                f"{report}/finalise",
                template=finalise,
                session=world.dpo,
                json={
                    "recipients": mandatory,
                    "extra": [{"full_name": "An Auditor", "email": alone}],
                },
            )
            [view] = [k for k in sent.json()["kinds"] if k["kind"] == "board_intimation"]
            lines = {plain(r["email"]): r for r in view["versions"][0]["mail"]["recipients"]}
            assert set(lines) >= {address, alone} and len(lines) == len(mandatory) + 1
            assert (
                lines[alone]["added_for_this_send"] is True and lines[address]["mandatory"] is True
            )
            assert _mailed(queued, before) == len(lines)
            kept = await call(http, "GET", "/breach-settings", session=world.dpo)
            assert alone not in {plain(r["email"]) for r in kept.json()["board_recipients"]}
        finally:
            # A mandatory entry left behind would go with every report this
            # database's suites finalise, so it comes off whatever happened.
            await call(
                http,
                "PUT",
                f"{entry}/mandatory",
                template="/breach-settings/board-recipients/{recipient_uuid}/mandatory",
                session=world.admin,
                json={"mandatory": False},
            )
            await call(
                http,
                "DELETE",
                entry,
                template="/breach-settings/board-recipients/{recipient_uuid}",
                session=world.dpo,
            )


class TestACertInReportWaitsForAYes:
    async def test_finalised_before_validation_it_goes_at_the_first_yes(
        self, http: httpx.AsyncClient, world: World, queued: Any
    ) -> None:
        path = await _incident(
            http, world, title="A ransom note on the file server", cyber_attack="yes"
        )
        await on_the_board(http, world)
        report = await _written(http, world, path, "cert_in")
        before = len(queued)
        held = await call(
            http,
            "POST",
            f"{report}/finalise",
            template=f"{B}/reports/{{report_uuid}}/finalise",
            session=world.dpo,
            json=await everyone(http, world, path),
        )
        assert _mailed(queued, before) == 0, "nothing goes to the board before a yes"
        [view] = [k for k in held.json()["kinds"] if k["kind"] == "cert_in"]
        mail = view["versions"][0]["mail"]
        assert view["holds_mail"] is True and mail["held"] >= 1 and mail["retryable"] == 0
        waiting = await call(
            http,
            "POST",
            f"{report}/resend",
            template=f"{B}/reports/{{report_uuid}}/resend",
            session=world.dpo,
            expect=409,
        )
        assert "report_held" in waiting.text
        await _yes(http, world, path)
        assert _mailed(queued, before) == mail["held"]


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
