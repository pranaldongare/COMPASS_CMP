"""A report nobody takes up is escalated; a breach moves to the other office
as it stands; the reporter is acknowledged, and told no more (0073, ADR 0042).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
import pytest

from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.db.repositories import breaches as breach_repo
from cmp.db.sql import fetch_all, fetch_one
from cmp.domain.breach import intake, service, settings
from cmp.tasks import dispatch as dispatch_mod
from tests.conftest import plain
from tests.integration.test_breach_by_office import _incident, _recorded
from tests.integration.test_incident_report import _dpo, _report, _waiting
from tests.integration.test_rights_by_office import _as_office, _legal_poc

pytestmark = pytest.mark.integration

LATER = timedelta(minutes=31)


async def _escalate_all(conn: Any, *, now: datetime) -> int:
    """Until nothing is left: this database may hold more waiting reports than
    one sweep takes."""
    total = 0
    for _ in range(200):
        done = await intake.escalate_waiting(conn, now=now)
        total += done
        if not done:
            break
    return total


async def _escalated(conn: Any, reference: str) -> dict[str, Any] | None:
    return await fetch_one(
        conn,
        """SELECT e.addresses, e.escalated_at FROM incident_report_escalation e
             JOIN incident_report r USING (report_id) WHERE r.reference = %s""",
        (reference,),
    )


class TestAReportNobodyTakesUpIsEscalated:
    async def test_management_is_mailed_once_after_half_an_hour(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, sent: Any
    ) -> None:
        await settings.add_escalation_recipient(
            conn, full_name="Meera Shah", email="coo@example.org", actor_id=_dpo(seeded)
        )
        made = await _report(conn)
        now = datetime.now(UTC)

        # Not yet: it has waited no time at all.
        await _escalate_all(conn, now=now + timedelta(minutes=29))
        assert await _escalated(conn, made["reference"]) is None

        del sent[:]
        assert await _escalate_all(conn, now=now + LATER) >= 1
        row = await _escalated(conn, made["reference"])
        assert row is not None and row["addresses"] == 1
        mine = [
            a
            for n, a in sent
            if n == "send_incident_report_escalated" and a[1] == made["reference"]
        ]
        assert len(mine) == 1
        assert plain(mine[0][0]) == "coo@example.org"
        # Nothing of what it says: an address, its number, when, how long.
        assert len(mine[0]) == 4 and "laptop" not in " ".join(map(str, mine[0]))

        # Once: a later sweep says nothing again.
        del sent[:]
        assert await _escalate_all(conn, now=now + timedelta(hours=3)) == 0
        assert sent == []
        waiting = await _waiting(conn, made["reference"])
        assert waiting["escalated_at"] is not None

    async def test_a_report_an_office_took_up_or_dismissed_is_not(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, sent: Any
    ) -> None:
        await settings.add_escalation_recipient(
            conn, full_name=None, email="coo@example.org", actor_id=_dpo(seeded)
        )
        claimed, dismissed = await _report(conn), await _report(conn)
        await intake.claim(
            conn,
            report_uuid=str((await _waiting(conn, claimed["reference"]))["report_uuid"]),
            office="rnd",
            actor_id=_dpo(seeded),
        )
        await intake.dismiss(
            conn,
            report_uuid=str((await _waiting(conn, dismissed["reference"]))["report_uuid"]),
            reason="A test",
            actor_id=_dpo(seeded),
        )
        await _escalate_all(conn, now=datetime.now(UTC) + LATER)
        assert await _escalated(conn, claimed["reference"]) is None
        assert await _escalated(conn, dismissed["reference"]) is None

    async def test_with_nobody_on_the_list_nothing_is_marked(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, sent: Any
    ) -> None:
        for row in (await settings.overview(conn))["escalation_recipients"]:
            await settings.remove_escalation_recipient(
                conn, recipient_uuid=str(row["recipient_uuid"]), actor_id=_dpo(seeded)
            )
        made = await _report(conn)
        later = datetime.now(UTC) + LATER
        assert await intake.escalate_waiting(conn, now=later) == 0
        assert await _escalated(conn, made["reference"]) is None
        # An address added afterwards hears of what is still waiting.
        await settings.add_escalation_recipient(
            conn, full_name=None, email="late@example.org", actor_id=_dpo(seeded)
        )
        await _escalate_all(conn, now=later)
        assert await _escalated(conn, made["reference"]) is not None

    async def test_the_list_keeps_an_address_once_and_is_its_own(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        before = (await settings.overview(conn))["board_recipients"]
        shown = await settings.add_escalation_recipient(
            conn, full_name="Meera Shah", email="COO@example.org ", actor_id=_dpo(seeded)
        )
        assert shown["escalate_after_minutes"] == 30
        [mine] = [
            r for r in shown["escalation_recipients"] if plain(r["email"]) == "coo@example.org"
        ]
        with pytest.raises(Conflict):
            await settings.add_escalation_recipient(
                conn, full_name=None, email="coo@example.org", actor_id=_dpo(seeded)
            )
        # The organisation's board is another list, and did not change.
        assert (await settings.overview(conn))["board_recipients"] == before
        gone = await settings.remove_escalation_recipient(
            conn, recipient_uuid=str(mine["recipient_uuid"]), actor_id=_dpo(seeded)
        )
        assert mine["recipient_uuid"] not in {
            r["recipient_uuid"] for r in gone["escalation_recipients"]
        }
        with pytest.raises(NotFound):
            await settings.remove_escalation_recipient(
                conn, recipient_uuid=str(mine["recipient_uuid"]), actor_id=_dpo(seeded)
            )


class TestABreachMovesToTheOtherOfficeAsItStands:
    async def test_it_leaves_one_register_for_the_other_and_nothing_else_moves(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, sent: Any
    ) -> None:
        dpo = _dpo(seeded)
        legal = await _legal_poc(conn)
        await _as_office(conn, "rnd")
        uuid = await _recorded(conn, actor_id=dpo, office="rnd")
        before = await service.detail(conn, uuid)
        assert before["office"] == "rnd" and before["transferred"] is None

        del sent[:]
        moved = await service.transfer(
            conn, breach_uuid=uuid, to_office="hr", reason="The data is HR's", actor_id=dpo
        )
        assert moved == {"reference": before["reference"], "office": "hr"}

        # Gone from the sender's register, as a wrong uuid is.
        with pytest.raises(NotFound):
            await service.require(conn, uuid)

        await _as_office(conn, "hr")
        after = await service.detail(conn, uuid)
        assert after["office"] == "hr"
        assert after["transferred"]["from_office"] == "rnd"
        assert plain(after["transferred"]["transfer_reason"]) == "The data is HR's"
        # As it stood: the number, the status, the validation, every duty and
        # every clock.
        for key in (
            "reference",
            "incident_reference",
            "breach_reference",
            "status",
            "determination",
            "detected_at",
            "became_aware_at",
            "recorded_at",
            "breach_recorded_at",
        ):
            assert after[key] == before[key], key
        assert [(d["duty"], d["state"], d["due_at"]) for d in after["obligations"]] == [
            (d["duty"], d["state"], d["due_at"]) for d in before["obligations"]
        ]
        assert len(after["determinations"]) == len(before["determinations"])
        assert len(after["status_history"]) == len(before["status_history"])

        # The receiving office's officers are mailed, the reason sealed.
        mails = [a for n, a in sent if n == "send_breach_transfer_received"]
        assert mails and all(a[1] == before["reference"] for a in mails)
        # To the office it went to, and to nobody of the office it left.
        told = {plain(a[0]) for a in mails}
        legal_emails = {
            plain(r["email"])
            for r in await fetch_all(
                conn, "SELECT email FROM auth_user WHERE role = 'legal' AND status = 'active'"
            )
        }
        assert told and told <= legal_emails
        assert all(plain(a[3]) == "The data is HR's" for a in mails)

        # And it is theirs to work on, and to send back.
        await service.transfer(
            conn, breach_uuid=uuid, to_office="rnd", reason="Not ours after all", actor_id=legal
        )
        await _as_office(conn, "rnd")
        assert (await service.detail(conn, uuid))["transferred"]["from_office"] == "hr"

    async def test_it_needs_a_reason_another_office_and_an_open_breach(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, sent: Any
    ) -> None:
        dpo = _dpo(seeded)
        await _as_office(conn, "rnd")
        uuid = await _incident(conn, actor_id=dpo, office="rnd")
        with pytest.raises(ValidationFailed):
            await service.transfer(
                conn, breach_uuid=uuid, to_office="hr", reason="  ", actor_id=dpo
            )
        with pytest.raises(ValidationFailed):
            await service.transfer(
                conn, breach_uuid=uuid, to_office="rnd", reason="Why", actor_id=dpo
            )
        with pytest.raises(ValidationFailed):
            await service.transfer(
                conn, breach_uuid=uuid, to_office="nowhere", reason="Why", actor_id=dpo
            )
        await service.determine(
            conn,
            breach_uuid=uuid,
            outcome="no",
            reasoning="Nothing personal in it",
            became_aware_at=None,
            actor_id=dpo,
        )
        await service.transition(
            conn, breach_uuid=uuid, to="closed", reason="Nothing in it", actor_id=dpo
        )
        with pytest.raises(Conflict):
            await service.transfer(
                conn, breach_uuid=uuid, to_office="hr", reason="Why", actor_id=dpo
            )
        # The other office cannot pull it over: it is not there for them.
        await _as_office(conn, "hr")
        with pytest.raises(NotFound):
            await service.transfer(
                conn, breach_uuid=uuid, to_office="hr", reason="Ours", actor_id=dpo
            )

    async def test_the_trail_says_from_where_to_where(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, sent: Any
    ) -> None:
        dpo = _dpo(seeded)
        await _as_office(conn, "rnd")
        uuid = await _incident(conn, actor_id=dpo, office="rnd")
        breach = await service.require(conn, uuid)
        await service.transfer(
            conn, breach_uuid=uuid, to_office="hr", reason="Theirs", actor_id=dpo
        )
        rows = await fetch_all(
            conn,
            """SELECT detail_json FROM audit_log
                WHERE event_type = 'breach.transferred' AND entity_id = %s""",
            (int(breach["breach_id"]),),
        )
        [row] = rows
        assert row["detail_json"]["from"] == "rnd" and row["detail_json"]["to"] == "hr"
        # On the receiving office's trail, and never the reason.
        assert row["detail_json"]["office"] == "hr"
        assert "Theirs" not in str(row["detail_json"])

    async def test_the_office_changes_no_other_way(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        await _as_office(conn, "rnd")
        uuid = await _incident(conn, actor_id=_dpo(seeded), office="rnd")
        breach = await breach_repo.by_uuid(conn, uuid)
        assert breach is not None
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            await conn.execute(
                """UPDATE breach SET office_id = (SELECT office_id FROM office
                                                   WHERE office_code = 'hr')
                    WHERE breach_id = %s""",
                (int(breach["breach_id"]),),
            )

    @pytest.mark.parametrize(
        "change",
        [
            # The stamp without the move.
            """transferred_from_office_id = office_id, transferred_at = clock_timestamp(),
               transferred_by = recorded_by, transfer_reason = 'x'""",
            # The move from an office it was not in.
            """office_id = (SELECT office_id FROM office WHERE office_code = 'hr'),
               transferred_from_office_id = (SELECT office_id FROM office WHERE office_code = 'hr'),
               transferred_at = clock_timestamp(), transferred_by = recorded_by,
               transfer_reason = 'x'""",
            # A true move, and something else with it.
            """office_id = (SELECT office_id FROM office WHERE office_code = 'hr'),
               transferred_from_office_id = office_id, transferred_at = clock_timestamp(),
               transferred_by = recorded_by, transfer_reason = 'x', title = 'y'""",
            """office_id = (SELECT office_id FROM office WHERE office_code = 'hr'),
               transferred_from_office_id = office_id, transferred_at = clock_timestamp(),
               transferred_by = recorded_by, transfer_reason = 'x', status = 'closed'""",
        ],
    )
    async def test_the_stamp_and_the_move_come_together_and_alone(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, change: str
    ) -> None:
        await _as_office(conn, "rnd")
        uuid = await _incident(conn, actor_id=_dpo(seeded), office="rnd")
        breach = await breach_repo.by_uuid(conn, uuid)
        assert breach is not None
        with pytest.raises(
            (psycopg.errors.InsufficientPrivilege, psycopg.errors.RestrictViolation)
        ):
            await conn.execute(
                f"UPDATE breach SET {change} WHERE breach_id = %s", (int(breach["breach_id"]),)
            )


class TestTheReporterIsAcknowledgedAndToldNoMore:
    @pytest.fixture(autouse=True)
    def _broker_up(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(dispatch_mod, "_touch_broker", lambda: None)

    async def test_an_officer_sends_it_and_each_time_is_kept(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, sent: Any
    ) -> None:
        dpo = _dpo(seeded)
        made = await _report(conn)
        await _as_office(conn, "rnd")
        detail = await intake.claim(
            conn,
            report_uuid=str((await _waiting(conn, made["reference"]))["report_uuid"]),
            office="rnd",
            actor_id=dpo,
        )
        uuid = str(detail["breach_uuid"])
        assert detail["reported"]["acknowledgements"] == 0
        assert detail["reported"]["acknowledged_at"] is None

        del sent[:]
        once = await intake.acknowledge_reporter(conn, breach_uuid=uuid, actor_id=dpo)
        assert once["reported"]["acknowledgements"] == 1
        assert once["reported"]["acknowledged_at"] is not None
        [mail] = [a for n, a in sent if n == "send_incident_report_acknowledged"]
        # Their address, their name and the number: nothing of the incident.
        assert plain(mail[0]) == "reporter@example.org"
        assert plain(mail[1]) == "Asha Rao"
        assert mail[2] == made["reference"] and len(mail) == 3

        twice = await intake.acknowledge_reporter(conn, breach_uuid=uuid, actor_id=dpo)
        assert twice["reported"]["acknowledgements"] == 2

    async def test_an_incident_the_office_logged_has_nobody_to_acknowledge(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, sent: Any
    ) -> None:
        await _as_office(conn, "rnd")
        uuid = await _incident(conn, actor_id=_dpo(seeded), office="rnd")
        with pytest.raises(Conflict):
            await intake.acknowledge_reporter(conn, breach_uuid=uuid, actor_id=_dpo(seeded))
        assert sent == []

    async def test_the_other_office_cannot_send_it(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, sent: Any
    ) -> None:
        dpo = _dpo(seeded)
        made = await _report(conn)
        await _as_office(conn, "rnd")
        detail = await intake.claim(
            conn,
            report_uuid=str((await _waiting(conn, made["reference"]))["report_uuid"]),
            office="rnd",
            actor_id=dpo,
        )
        await _as_office(conn, "hr")
        with pytest.raises(NotFound):
            await intake.acknowledge_reporter(
                conn, breach_uuid=str(detail["breach_uuid"]), actor_id=dpo
            )
