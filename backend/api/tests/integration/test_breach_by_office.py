"""Breaches and legal holds by office (0055).

A breach is logged into the register of the office that logs it: the Legal
PoC's incident is the Legal office's, its duties start as the DPO's do, and
the DPO is told it is not there. A legal hold is an office's to list and
release - but what it stops it stops for both: the DPO's erasure stops at a
hold the Legal office placed on the same person.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from cmp.core.config import settings
from cmp.core.errors import NotFound
from cmp.db.pool import across_offices
from cmp.db.repositories import breaches as breach_repo
from cmp.db.repositories import legal_holds as hold_repo
from cmp.db.repositories import users as user_repo
from cmp.domain.breach import intake, reports, service, tickets
from cmp.domain.rights import holds
from cmp.tasks import dispatch as dispatch_mod
from tests.conftest import plain
from tests.integration.test_incident_report import _report, _waiting
from tests.integration.test_rights_by_office import _as_office, _legal_poc

pytestmark = pytest.mark.integration


async def _incident(conn: Any, *, actor_id: int, office: str) -> str:
    made = await service.record(
        conn,
        title="A spreadsheet of survey answers sent to the wrong team",
        detected_at=datetime.now(UTC) - timedelta(minutes=30),
        began_at=None,
        location_kind="platform",
        processor_uuid=None,
        source_uuid=None,
        location_detail=None,
        actor_id=actor_id,
        office=office,
    )
    return str(made["breach_uuid"])


class TestTheRegisterIsTheOffices:
    async def test_the_legal_office_logs_its_own_and_the_dpo_is_told_it_is_not_there(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        legal = await _legal_poc(conn)
        await _as_office(conn, "hr")
        uuid = await _incident(conn, actor_id=legal, office="hr")
        mine = await service.require(conn, uuid)
        assert mine["office_code"] == "hr"
        assert await breach_repo.obligations(conn, [int(mine["breach_id"])]) == []
        assert uuid in {str(b["breach_uuid"]) for b in await service.register(conn, status=None)}

        await _as_office(conn, "rnd")
        with pytest.raises(NotFound):
            await service.require(conn, uuid)
        assert uuid not in {
            str(b["breach_uuid"]) for b in await service.register(conn, status=None)
        }

    async def test_the_dpo_s_incident_stays_the_dpo_s(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        await _as_office(conn, "rnd")
        uuid = await _incident(conn, actor_id=int(seeded["users"]["dpo"]["id"]), office="rnd")
        await _as_office(conn, "hr")
        with pytest.raises(NotFound):
            await service.require(conn, uuid)


async def _recorded(conn: Any, *, actor_id: int, office: str) -> str:
    uuid = await _incident(conn, actor_id=actor_id, office=office)
    await service.determine(
        conn,
        breach_uuid=uuid,
        outcome="yes",
        reasoning="It is one",
        became_aware_at=datetime.now(UTC) - timedelta(minutes=10),
        actor_id=actor_id,
    )
    return uuid


class TestACertInMarkIsTheOffices:
    async def test_the_other_office_cannot_set_it_aside(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        legal = await _legal_poc(conn)
        await _as_office(conn, "hr")
        uuid = await _incident(conn, actor_id=legal, office="hr")
        await service.mark_cert_in(conn, breach_uuid=uuid, actor_id=legal)
        await service.determine(
            conn,
            breach_uuid=uuid,
            outcome="no",
            reasoning="Nothing in it",
            became_aware_at=None,
            actor_id=legal,
        )
        await _as_office(conn, "rnd")
        with pytest.raises(NotFound):
            await service.set_aside_cert_in(
                conn,
                breach_uuid=uuid,
                reason="Not mine to say",
                actor_id=int(seeded["users"]["dpo"]["id"]),
            )
        await _as_office(conn, "hr")
        done = await service.set_aside_cert_in(
            conn, breach_uuid=uuid, reason="A false alarm", actor_id=legal
        )
        [duty] = [d for d in done["obligations"] if d["duty"] == "cert_in"]
        assert duty["state"] == "not_applicable"


class TestAPublicReportTakesTheOfficeThatClaimsIt:
    async def test_a_claim_by_legal_lands_in_its_register_and_not_the_dpos(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        legal = await _legal_poc(conn)
        made = await _report(conn)
        await _as_office(conn, "hr")
        waiting = await _waiting(conn, made["reference"])
        detail = await intake.claim(
            conn, report_uuid=str(waiting["report_uuid"]), office="hr", actor_id=legal
        )
        uuid = str(detail["breach_uuid"])
        assert (await service.require(conn, uuid))["office_code"] == "hr"

        await _as_office(conn, "rnd")
        with pytest.raises(NotFound):
            await service.require(conn, uuid)
        assert uuid not in {
            str(b["breach_uuid"]) for b in await service.register(conn, status=None)
        }


class TestTheReportsAreTheOffices:
    async def test_a_report_one_office_dismissed_is_read_by_the_other(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        made = await _report(conn)
        waiting = await _waiting(conn, made["reference"])
        await _as_office(conn, "rnd")
        await intake.dismiss(
            conn,
            report_uuid=str(waiting["report_uuid"]),
            reason="Reads like an HR matter to us",
            actor_id=int(seeded["users"]["dpo"]["id"]),
        )
        await _as_office(conn, "hr")
        [kept] = [r for r in await intake.dismissed(conn) if r["reference"] == made["reference"]]
        assert plain(kept["dismissal_reason"]) == "Reads like an HR matter to us"

    async def test_every_call_on_the_other_offices_breach_is_told_it_is_not_there(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        legal = await _legal_poc(conn)
        await _as_office(conn, "hr")
        uuid = await _recorded(conn, actor_id=legal, office="hr")
        drafted = await reports.draft(
            conn, breach_uuid=uuid, kind="board_intimation", actor_id=legal
        )
        [kind] = [k for k in drafted["kinds"] if k["kind"] == "board_intimation"]
        report = str(kind["versions"][0]["report_uuid"])

        await _as_office(conn, "rnd")
        dpo = int(seeded["users"]["dpo"]["id"])
        both = {"breach_uuid": uuid, "report_uuid": report}
        calls = {
            "overview": reports.overview(conn, breach_uuid=uuid),
            "draft": reports.draft(conn, breach_uuid=uuid, kind="closure", actor_id=dpo),
            "edit": reports.edit(conn, **both, bodies={"timing": "x"}, actor_id=dpo),
            "finalise": reports.finalise(conn, **both, actor_id=dpo),
            "resend": reports.resend(conn, **both, actor_id=dpo),
            "check_proof": reports.check_proof(conn, **both, kind="approval"),
            "add_proof": reports.add_proof(
                conn,
                **both,
                kind="approval",
                note=None,
                file_name="a.pdf",
                storage_ref="breach/a.pdf",
                sha256="a" * 64,
                size_bytes=1,
                content_type="application/pdf",
                actor_id=dpo,
            ),
            "file_report": reports.file_report(
                conn, **both, filed_at=datetime.now(UTC), reference="DPB/1", actor_id=dpo
            ),
            "pdf": reports.pdf(conn, **both, actor_id=dpo),
        }
        for name, call in calls.items():
            with pytest.raises(NotFound):
                await call
                pytest.fail(f"{name} reached the other office's report")


class TestAChangedDateReachesItsOwnOffice:
    async def test_a_holders_change_on_a_legal_breach_queues_only_the_legal_officers(
        self,
        conn: Any,
        seeded: dict[str, Any],
        request_context: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        sent: list[tuple[str, tuple[Any, ...]]] = []

        def capture(task: Any, *args: Any, **kwargs: Any) -> str:
            sent.append((task.name.rsplit(".", 1)[-1], args))
            return "queued-in-a-test"

        monkeypatch.setattr(dispatch_mod, "dispatch_optional", capture)
        monkeypatch.setattr(settings, "breach_ticket_email_domains", ("test.local",))
        legal = await _legal_poc(conn)
        holder = seeded["users"]["dco"]
        await _as_office(conn, "hr")
        uuid = await _recorded(conn, actor_id=legal, office="hr")
        made = await tickets.assign(
            conn,
            breach_uuid=uuid,
            user_uuid=str(holder["uuid"]),
            instruction="Keep the access log",
            answer_by=None,
            actor_id=legal,
        )
        sent.clear()
        async with across_offices(conn):
            await tickets.holder_change_date(
                conn,
                user_id=int(holder["id"]),
                ticket_uuid=str(made["ticket"]["ticket_uuid"]),
                answer_by=datetime.now(UTC).date() + timedelta(days=3),
                reason="The vendor answers on Monday",
            )
        told = [a[0] for name, a in sent if name == "send_breach_ticket_date_changed"]
        assert sorted(told) == sorted(await user_repo.officer_emails(conn, "hr"))
        addresses = {plain(sealed) for sealed in told}
        row = await (
            await conn.execute(
                "SELECT email FROM auth_user WHERE id = %s", (int(seeded["users"]["dpo"]["id"]),)
            )
        ).fetchone()
        assert plain(row["email"]) not in addresses, "the DPO's office hears nothing of it"


class TestLegalHolds:
    async def test_a_hold_is_its_office_s_to_list_and_both_offices_stop_at_it(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        legal = await _legal_poc(conn)
        person = seeded["subject"]
        await _as_office(conn, "hr")
        held = await holds.place(
            conn,
            asset_uuid=None,
            subject_uuid=str(person["uuid"]),
            reason="An employment tribunal claim",
            actor_id=legal,
            office="hr",
        )
        assert held["office_code"] == "hr"
        assert str(held["hold_uuid"]) in {
            str(h["hold_uuid"]) for h in await hold_repo.list_holds(conn, active_only=True)
        }

        await _as_office(conn, "rnd")
        assert str(held["hold_uuid"]) not in {
            str(h["hold_uuid"]) for h in await hold_repo.list_holds(conn, active_only=True)
        }
        with pytest.raises(NotFound):
            await holds.release(
                conn, hold_uuid=str(held["hold_uuid"]), actor_id=int(seeded["users"]["dpo"]["id"])
            )
        # What it stops, it stops for the DPO office too.
        covering = await hold_repo.active_covering(
            conn, asset_id=None, subject_user_id=int(person["id"])
        )
        assert covering is not None and str(covering["hold_uuid"]) == str(held["hold_uuid"])
        # And the connection reads as the DPO office again afterwards.
        setting = await (
            await conn.execute("SELECT current_setting('app.office', true) AS o")
        ).fetchone()
        assert setting["o"] == "rnd"
