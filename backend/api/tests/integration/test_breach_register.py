"""The breach register and its obligations (S3-01).

A breach records three times kept apart, a determination a person makes, an
assessment revised by new rows, and one duty per statutory obligation, each
with a due time stored once. Encryption bears only on the determination: once
an event is determined a personal data breach, every duty stands.
"""

from __future__ import annotations

import ast
import pathlib
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
import pytest

from cmp.core.config import settings
from cmp.core.errors import Conflict, NotFound, TransitionNotPermitted, ValidationFailed
from cmp.db.sql import fetch_all
from cmp.domain.breach import board, clock, service
from tests.conftest import plain

pytestmark = pytest.mark.integration

HOUR = timedelta(hours=1)


def _dpo(seeded: dict[str, Any]) -> int:
    return int(seeded["users"]["dpo"]["id"])


async def _breach(
    conn: Any, seeded: dict[str, Any], *, detected_ago: timedelta = 5 * HOUR, **kw: Any
) -> dict[str, Any]:
    now = datetime.now(UTC)
    args: dict[str, Any] = {
        "title": "Lab laptop stolen",
        "detected_at": now - detected_ago,
        "began_at": None,
        "location_kind": "platform",
        "processor_uuid": None,
        "source_uuid": None,
        "location_detail": None,
    }
    args.update(kw)
    return await service.record(conn, actor_id=_dpo(seeded), **args)


async def _yes(
    conn: Any, seeded: dict[str, Any], breach: dict[str, Any], aware: datetime
) -> dict[str, Any]:
    return await service.determine(
        conn,
        breach_uuid=str(breach["breach_uuid"]),
        outcome="yes",
        reasoning="Contact details left the building",
        became_aware_at=aware,
        actor_id=_dpo(seeded),
    )


async def tell_org_board(conn: Any, seeded: dict[str, Any], uuid: str) -> dict[str, Any]:
    """A yes owes the organisation's board a report (ADR 0037); a test about
    something else records it so it does not stand in the way."""
    return await service.complete_duty(
        conn,
        breach_uuid=uuid,
        duty="org_board",
        occurred_at=datetime.now(UTC),
        reference=None,
        reported_to="The chair, by phone",
        note=None,
        actor_id=_dpo(seeded),
    )


def _duty(detail: dict[str, Any], duty: str) -> dict[str, Any]:
    [found] = [d for d in detail["obligations"] if d["duty"] == duty]
    return found


async def test_every_category_sealed_and_the_key_safe_still_creates_all_three_duties(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """Written first. DPDP has no encryption exemption and no severity
    threshold: encryption bears on whether an event *is* a breach, and that is
    the determination a person records. Once it is *yes*, every duty stands."""
    breach = await _breach(conn, seeded)
    await service.assess(
        conn,
        breach_uuid=str(breach["breach_uuid"]),
        began_at=None,
        categories=[
            {"category": "Contact details", "sealed": True, "key_exposed": False},
            {"category": "Date of birth", "sealed": True, "key_exposed": False},
        ],
        text={"nature_extent": "A copy of the database left on a laptop"},
        actor_id=_dpo(seeded),
    )
    aware = datetime.now(UTC) - 2 * HOUR
    detail = await _yes(conn, seeded, breach, aware)

    duties = {d["duty"]: d for d in detail["obligations"] if d["duty"] != "org_board"}
    assert set(duties) == {"board_intimation", "board_report", "principals"}
    assert all(d["state"] == "outstanding" for d in duties.values())
    assert duties["board_report"]["due_at"] == aware + timedelta(hours=72)
    assert duties["board_intimation"]["due_at"] is None, "without delay has no statutory hours"
    assert duties["principals"]["due_at"] is None
    assert all(d["anchored_at"] == aware for d in duties.values())


async def test_the_three_times_are_kept_apart_and_as_entered(
    conn: Any, seeded: dict[str, Any]
) -> None:
    now = datetime.now(UTC)
    detected = now - 5 * HOUR
    began = now - 30 * HOUR
    breach = await _breach(conn, seeded, detected_at=detected, began_at=began)
    assert breach["detected_at"] == detected, "entered, never the moment of saving"
    assert breach["began_at"] == began
    assert breach["became_aware_at"] is None, "awareness comes with a determination"

    aware = now - 3 * HOUR
    detail = await _yes(conn, seeded, breach, aware)
    assert detail["became_aware_at"] == aware
    assert detail["detected_at"] == detected


async def test_a_breach_recorded_late_shows_the_cert_in_time_actually_left(
    conn: Any, seeded: dict[str, Any]
) -> None:
    detected = datetime.now(UTC) - 5 * HOUR
    breach = await _breach(conn, seeded, detected_at=detected)
    detail = await service.mark_cert_in(
        conn, breach_uuid=str(breach["breach_uuid"]), actor_id=_dpo(seeded)
    )
    cert_in = _duty(detail, "cert_in")
    assert cert_in["due_at"] == detected + timedelta(hours=6)
    assert cert_in["anchored_at"] == detected
    remaining = cert_in["clock"]["seconds_remaining"]
    assert 0 < remaining <= 3600, "five hours after noticing, one hour is left - not six"

    with pytest.raises(Conflict):
        await service.mark_cert_in(
            conn, breach_uuid=str(breach["breach_uuid"]), actor_id=_dpo(seeded)
        )


class TestACertInMarkMadeInError:
    """A false alarm validated No has nothing to report and nobody to report it
    to, and must be able to close without saying otherwise."""

    @staticmethod
    async def _marked(conn: Any, seeded: dict[str, Any], *outcomes: str) -> str:
        uuid = str((await _breach(conn, seeded))["breach_uuid"])
        await service.mark_cert_in(conn, breach_uuid=uuid, actor_id=_dpo(seeded))
        for outcome in outcomes:
            await TestACertInMarkMadeInError._determine(conn, seeded, uuid, outcome)
        return uuid

    @staticmethod
    async def _determine(conn: Any, seeded: dict[str, Any], uuid: str, outcome: str) -> None:
        await service.determine(
            conn,
            breach_uuid=uuid,
            outcome=outcome,
            reasoning="As far as is known",
            became_aware_at=datetime.now(UTC) - HOUR if outcome == "yes" else None,
            actor_id=_dpo(seeded),
        )

    @staticmethod
    async def _set_aside(
        conn: Any, seeded: dict[str, Any], uuid: str, reason: str = "It was a false alarm"
    ) -> dict[str, Any]:
        return await service.set_aside_cert_in(
            conn, breach_uuid=uuid, reason=reason, actor_id=_dpo(seeded)
        )

    async def test_after_a_no_it_is_set_aside_and_the_incident_closes(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        uuid = await self._marked(conn, seeded, "no")
        before = await service.detail(conn, uuid)
        assert "Report to CERT-In is outstanding" in before["transitions"][0]["blockers"]
        after = await self._set_aside(conn, seeded, uuid)
        assert _duty(after, "cert_in")["state"] == "not_applicable"
        assert after["transitions"][0]["allowed"] is True
        closed = await service.transition(
            conn, breach_uuid=uuid, to="closed", reason=None, actor_id=_dpo(seeded)
        )
        assert closed["status"] == "closed"

    async def test_it_cites_the_no_and_seals_the_reason(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        uuid = await self._marked(conn, seeded, "no")
        detail = await self._set_aside(conn, seeded, uuid)
        [event] = _duty(detail, "cert_in")["events"]
        assert event["determination_uuid"] == detail["determinations"][-1]["determination_uuid"]
        assert str(event["note"]).startswith("SE::")
        assert plain(event["note"]) == "It was a false alarm"

    async def test_the_trail_says_a_reason_was_given_and_not_what_it_said(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        uuid = await self._marked(conn, seeded, "no")
        await self._set_aside(conn, seeded, uuid)
        [row] = await fetch_all(
            conn,
            """SELECT l.actor_user_id, l.detail_json FROM audit_log l
                 JOIN breach b ON b.breach_id = l.entity_id
                WHERE l.entity_type = 'breach' AND b.breach_uuid = %s
                  AND l.event_type = 'breach.cert_in_set_aside'""",
            (uuid,),
        )
        assert row["actor_user_id"] == _dpo(seeded)
        assert row["detail_json"]["duty"] == "cert_in"
        assert row["detail_json"]["reason_given"] is True
        assert "false alarm" not in str(row["detail_json"])

    @pytest.mark.parametrize("reason", ["", "   "])
    async def test_it_needs_a_reason(self, conn: Any, seeded: dict[str, Any], reason: str) -> None:
        uuid = await self._marked(conn, seeded, "no")
        with pytest.raises(ValidationFailed) as refused:
            await self._set_aside(conn, seeded, uuid, reason)
        assert refused.value.field == "reason"

    @pytest.mark.parametrize("outcomes", [(), ("pending",), ("no", "pending"), ("no", "yes")])
    async def test_it_waits_for_the_latest_determination_to_be_no(
        self, conn: Any, seeded: dict[str, Any], outcomes: tuple[str, ...]
    ) -> None:
        uuid = await self._marked(conn, seeded, *outcomes)
        with pytest.raises(Conflict) as refused:
            await self._set_aside(conn, seeded, uuid)
        assert refused.value.code == "cert_in_not_validated_no"
        assert "validated as No" in refused.value.message
        assert _duty(await service.detail(conn, uuid), "cert_in")["state"] == "outstanding"

    async def test_there_must_be_such_a_duty(self, conn: Any, seeded: dict[str, Any]) -> None:
        uuid = str((await _breach(conn, seeded))["breach_uuid"])
        await self._determine(conn, seeded, uuid, "no")
        with pytest.raises(Conflict) as refused:
            await self._set_aside(conn, seeded, uuid)
        assert refused.value.code == "no_such_duty"

    async def test_a_duty_done_stands(self, conn: Any, seeded: dict[str, Any]) -> None:
        uuid = await self._marked(conn, seeded, "no")
        await service.complete_duty(
            conn,
            breach_uuid=uuid,
            duty="cert_in",
            occurred_at=datetime.now(UTC),
            reference="CERT/1",
            note=None,
            actor_id=_dpo(seeded),
        )
        with pytest.raises(Conflict) as refused:
            await self._set_aside(conn, seeded, uuid)
        assert refused.value.code == "duty_not_outstanding"

    async def test_set_aside_twice_is_refused(self, conn: Any, seeded: dict[str, Any]) -> None:
        uuid = await self._marked(conn, seeded, "no")
        await self._set_aside(conn, seeded, uuid)
        with pytest.raises(Conflict) as refused:
            await self._set_aside(conn, seeded, uuid)
        assert refused.value.code == "duty_not_outstanding"

    async def test_a_report_filed_stands(self, conn: Any, seeded: dict[str, Any]) -> None:
        """Filed while the duty was aside, then marked again: the duty is out
        again, and something was still reported."""
        uuid = await self._marked(conn, seeded, "no")
        breach = await service.require(conn, uuid)
        cur = await conn.execute(
            """INSERT INTO breach_report (breach_id, kind, version, created_by, finalised_by,
                                          finalised_at, filed_at, filed_reference, filed_by,
                                          filed_recorded_at)
               VALUES (%s, 'cert_in', 1, %s, %s, now(), now(), 'CERT/1', %s, now())
               RETURNING report_id""",
            (breach["breach_id"], _dpo(seeded), _dpo(seeded), _dpo(seeded)),
        )
        assert await cur.fetchone()
        with pytest.raises(Conflict) as refused:
            await self._set_aside(conn, seeded, uuid)
        assert refused.value.code == "report_filed"

    async def test_it_tells_nobody_and_leaves_the_board_alone(
        self, conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        uuid = await self._marked(conn, seeded, "yes", "no")
        board = _duty(await service.detail(conn, uuid), "org_board")

        def told(*_: Any, **__: Any) -> None:
            pytest.fail("somebody was told")

        import cmp.tasks.dispatch as dispatch

        monkeypatch.setattr(dispatch, "dispatch_optional", told)
        monkeypatch.setattr(dispatch, "dispatch_required", told)
        after = await self._set_aside(conn, seeded, uuid)
        assert _duty(after, "org_board")["events"] == board["events"]

    async def test_marking_again_brings_the_duty_back_with_its_own_clock(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        uuid = await self._marked(conn, seeded, "no")
        first = _duty(await service.detail(conn, uuid), "cert_in")
        await self._set_aside(conn, seeded, uuid)
        detail = await service.mark_cert_in(conn, breach_uuid=uuid, actor_id=_dpo(seeded))
        duty = _duty(detail, "cert_in")
        assert duty["state"] == "outstanding"
        assert duty["due_at"] == first["due_at"], "six hours from detection, as it was"
        assert duty["obligation_uuid"] == first["obligation_uuid"], "the same duty"
        assert [e["kind"] for e in duty["events"]] == ["not_applicable", "reinstated"]
        with pytest.raises(Conflict) as refused:
            await service.mark_cert_in(conn, breach_uuid=uuid, actor_id=_dpo(seeded))
        assert refused.value.code == "cert_in_marked"

    async def test_a_later_yes_does_not_bring_it_back_and_marking_does(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        """CERT-In stands on its own test. Were a yes to bring it back, a real
        breach that was never a cyber incident could not close, since a mark
        can be set aside only after a No."""
        uuid = await self._marked(conn, seeded, "no")
        await self._set_aside(conn, seeded, uuid)
        await self._determine(conn, seeded, uuid, "yes")
        assert _duty(await service.detail(conn, uuid), "cert_in")["state"] == "not_applicable"
        detail = await service.mark_cert_in(conn, breach_uuid=uuid, actor_id=_dpo(seeded))
        assert _duty(detail, "cert_in")["state"] == "outstanding"

    async def test_the_board_is_no_longer_told_it_is_reportable(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        uuid = await self._marked(conn, seeded, "no")
        assert (await board.org_board_brief(conn, breach_uuid=uuid))["cert_in_reportable"] is True
        await self._set_aside(conn, seeded, uuid)
        assert (await board.org_board_brief(conn, breach_uuid=uuid))["cert_in_reportable"] is False


async def test_cert_in_stands_on_its_own_test(conn: Any, seeded: dict[str, Any]) -> None:
    breach = await _breach(conn, seeded)
    await service.mark_cert_in(conn, breach_uuid=str(breach["breach_uuid"]), actor_id=_dpo(seeded))
    detail = await service.determine(
        conn,
        breach_uuid=str(breach["breach_uuid"]),
        outcome="no",
        reasoning="Only a system log left; no personal data",
        became_aware_at=None,
        actor_id=_dpo(seeded),
    )
    assert _duty(detail, "cert_in")["state"] == "outstanding"
    for duty in clock.DPDP_DUTIES:
        found = _duty(detail, duty)
        assert found["state"] == "not_applicable"
        [event] = found["events"]
        assert event["determination_uuid"] == detail["determinations"][-1]["determination_uuid"]


async def test_a_later_yes_reinstates_what_a_no_set_aside(
    conn: Any, seeded: dict[str, Any]
) -> None:
    breach = await _breach(conn, seeded)
    await service.determine(
        conn,
        breach_uuid=str(breach["breach_uuid"]),
        outcome="no",
        reasoning="Looked like no personal data",
        became_aware_at=None,
        actor_id=_dpo(seeded),
    )
    aware = datetime.now(UTC) - HOUR
    detail = await _yes(conn, seeded, breach, aware)
    report = _duty(detail, "board_report")
    assert report["state"] == "outstanding"
    assert report["due_at"] == aware + timedelta(hours=72)
    assert [e["kind"] for e in report["events"]] == ["not_applicable", "reinstated"]


async def test_closing_is_refused_while_a_duty_is_outstanding(
    conn: Any, seeded: dict[str, Any]
) -> None:
    breach = await _breach(conn, seeded)
    uuid = str(breach["breach_uuid"])
    with pytest.raises(TransitionNotPermitted, match="before closing"):
        await service.transition(
            conn, breach_uuid=uuid, to="closed", reason=None, actor_id=_dpo(seeded)
        )

    aware = datetime.now(UTC) - HOUR
    await _yes(conn, seeded, breach, aware)
    await tell_org_board(conn, seeded, uuid)
    for duty in ("board_intimation", "board_report"):
        await service.complete_duty(
            conn,
            breach_uuid=uuid,
            duty=duty,
            occurred_at=datetime.now(UTC),
            reference=f"DPB/{duty}/1",
            note=None,
            actor_id=_dpo(seeded),
        )
    with pytest.raises(TransitionNotPermitted) as refused:
        await service.transition(
            conn, breach_uuid=uuid, to="closed", reason=None, actor_id=_dpo(seeded)
        )
    assert refused.value.details["blockers"] == ["Principals notified is outstanding"]
    transitions = await service.transitions_for(conn, breach_uuid=uuid)
    assert transitions["available"][0]["allowed"] is False


async def test_a_breach_determined_no_closes_and_reopens_with_a_reason(
    conn: Any, seeded: dict[str, Any]
) -> None:
    breach = await _breach(conn, seeded)
    uuid = str(breach["breach_uuid"])
    await service.determine(
        conn,
        breach_uuid=uuid,
        outcome="no",
        reasoning="No personal data",
        became_aware_at=None,
        actor_id=_dpo(seeded),
    )
    closed = await service.transition(
        conn, breach_uuid=uuid, to="closed", reason=None, actor_id=_dpo(seeded)
    )
    assert closed["status"] == "closed"
    with pytest.raises(Conflict):
        await service.assess(
            conn,
            breach_uuid=uuid,
            began_at=None,
            categories=[],
            text={"mitigation": "x"},
            actor_id=_dpo(seeded),
        )
    with pytest.raises(ValidationFailed):
        await service.transition(
            conn, breach_uuid=uuid, to="open", reason=" ", actor_id=_dpo(seeded)
        )
    reopened = await service.transition(
        conn, breach_uuid=uuid, to="open", reason="A second copy was found", actor_id=_dpo(seeded)
    )
    assert [h["to_status"] for h in reopened["status_history"]] == ["open", "closed", "open"]
    assert str(reopened["status_history"][-1]["reason"]).startswith("SE::")


async def test_a_stored_due_time_does_not_move_when_configuration_does(
    conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    breach = await _breach(conn, seeded)
    aware = datetime.now(UTC) - 2 * HOUR
    await _yes(conn, seeded, breach, aware)

    # The target is configuration; the 72 hours are statute. Change both and
    # read the duties again: the target flags, and nothing stored moves.
    monkeypatch.setattr(settings, "breach_without_delay_target_hours", 1.0)
    monkeypatch.setattr(clock, "BOARD_REPORT_HOURS", 1)
    detail = await service.detail(conn, str(breach["breach_uuid"]))
    assert _duty(detail, "board_report")["due_at"] == aware + timedelta(hours=72)
    intimation = _duty(detail, "board_intimation")
    assert intimation["due_at"] is None
    assert intimation["clock"]["target_at"] == aware + HOUR
    assert intimation["clock"]["past_target"] is True


async def test_without_a_target_nothing_is_flagged(conn: Any, seeded: dict[str, Any]) -> None:
    breach = await _breach(conn, seeded, detected_ago=100 * HOUR)
    detail = await _yes(conn, seeded, breach, datetime.now(UTC) - 90 * HOUR)
    intimation = _duty(detail, "board_intimation")["clock"]
    assert intimation["without_delay"] is True
    assert intimation["target_at"] is None and intimation["past_target"] is False
    assert intimation["seconds_elapsed"] >= 90 * 3600
    assert _duty(detail, "board_report")["clock"]["overdue"] is True


async def test_an_extension_moves_the_report_and_leaves_the_intimation_alone(
    conn: Any, seeded: dict[str, Any]
) -> None:
    breach = await _breach(conn, seeded)
    aware = datetime.now(UTC) - HOUR
    await _yes(conn, seeded, breach, aware)
    allowed = aware + timedelta(days=10)
    detail = await service.extend_report(
        conn,
        breach_uuid=str(breach["breach_uuid"]),
        requested_at=datetime.now(UTC),
        allowed_until=allowed,
        reference="DPB/EXT/7",
        note=None,
        actor_id=_dpo(seeded),
    )
    report = _duty(detail, "board_report")
    assert report["due_at"] == allowed and report["extended_until"] == allowed
    assert _duty(detail, "board_intimation")["due_at"] is None
    raw = await (
        await conn.execute(
            "SELECT due_at FROM breach_obligation WHERE obligation_uuid = %s",
            (report["obligation_uuid"],),
        )
    ).fetchone()
    assert raw["due_at"] == aware + timedelta(hours=72), "the original due time stays on its row"


async def test_completing_a_duty_needs_the_regulators_reference(
    conn: Any, seeded: dict[str, Any]
) -> None:
    breach = await _breach(conn, seeded)
    uuid = str(breach["breach_uuid"])
    await _yes(conn, seeded, breach, datetime.now(UTC) - HOUR)
    with pytest.raises(ValidationFailed):
        await service.complete_duty(
            conn,
            breach_uuid=uuid,
            duty="board_intimation",
            occurred_at=datetime.now(UTC),
            reference="  ",
            note=None,
            actor_id=_dpo(seeded),
        )
    with pytest.raises(Conflict):
        await service.complete_duty(
            conn,
            breach_uuid=uuid,
            duty="principals",
            occurred_at=datetime.now(UTC),
            reference="x",
            note=None,
            actor_id=_dpo(seeded),
        )
    with pytest.raises(ValidationFailed):
        await service.complete_duty(
            conn,
            breach_uuid=uuid,
            duty="nonsense",
            occurred_at=datetime.now(UTC),
            reference="x",
            note=None,
            actor_id=_dpo(seeded),
        )
    done = await service.complete_duty(
        conn,
        breach_uuid=uuid,
        duty="board_intimation",
        occurred_at=datetime.now(UTC) - HOUR / 2,
        reference="DPB/INT/42",
        note="Filed on the portal",
        actor_id=_dpo(seeded),
    )
    intimation = _duty(done, "board_intimation")
    assert intimation["state"] == "done" and intimation["reference"] == "DPB/INT/42"
    with pytest.raises(Conflict):
        await service.complete_duty(
            conn,
            breach_uuid=uuid,
            duty="board_intimation",
            occurred_at=datetime.now(UTC),
            reference="again",
            note=None,
            actor_id=_dpo(seeded),
        )


async def test_times_are_checked_against_each_other(conn: Any, seeded: dict[str, Any]) -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValidationFailed):
        await _breach(conn, seeded, detected_at=now + 2 * HOUR)
    with pytest.raises(ValidationFailed):
        await _breach(conn, seeded, detected_at=now - HOUR, began_at=now - HOUR / 2)
    breach = await _breach(conn, seeded, detected_at=now - HOUR)
    with pytest.raises(ValidationFailed):
        await _yes(conn, seeded, breach, now - 2 * HOUR)
    with pytest.raises(ValidationFailed):
        await service.determine(
            conn,
            breach_uuid=str(breach["breach_uuid"]),
            outcome="no",
            reasoning="r",
            became_aware_at=now,
            actor_id=_dpo(seeded),
        )


async def test_a_location_names_what_its_kind_says(conn: Any, seeded: dict[str, Any]) -> None:
    processor = str(seeded["processors"]["external"]["processor_uuid"])
    with pytest.raises(ValidationFailed):
        await _breach(conn, seeded, location_kind="processor")
    with pytest.raises(ValidationFailed):
        await _breach(conn, seeded, location_kind="platform", processor_uuid=processor)
    with pytest.raises(ValidationFailed):
        await _breach(conn, seeded, location_kind="elsewhere")
    with pytest.raises(NotFound):
        await _breach(
            conn,
            seeded,
            location_kind="processor",
            processor_uuid="00000000-0000-0000-0000-000000000000",
        )
    at_processor = await _breach(conn, seeded, location_kind="processor", processor_uuid=processor)
    assert at_processor["location"]["processor_name"] == "Test Processor Ltd"


async def test_revisions_are_new_rows_and_leave_the_last_intact(
    conn: Any, seeded: dict[str, Any]
) -> None:
    breach = await _breach(conn, seeded)
    uuid = str(breach["breach_uuid"])
    await service.assess(
        conn,
        breach_uuid=uuid,
        began_at=None,
        categories=[{"category": "Name", "sealed": True, "key_exposed": False}],
        text={"nature_extent": "First account"},
        actor_id=_dpo(seeded),
    )
    before = await (
        await conn.execute(
            "SELECT * FROM breach_assessment WHERE breach_id = "
            "(SELECT breach_id FROM breach WHERE breach_uuid = %s)",
            (uuid,),
        )
    ).fetchall()
    detail = await service.assess(
        conn,
        breach_uuid=uuid,
        began_at=None,
        categories=[{"category": "Name", "sealed": True, "key_exposed": True}],
        text={"nature_extent": "Fuller account", "caused_by_findings": "An engineer's laptop"},
        actor_id=_dpo(seeded),
    )
    assert detail["assessment"]["revision"] == 2
    assert detail["assessment_revisions"] == 2
    after = await (
        await conn.execute(
            "SELECT * FROM breach_assessment WHERE breach_id = "
            "(SELECT breach_id FROM breach WHERE breach_uuid = %s) ORDER BY revision",
            (uuid,),
        )
    ).fetchall()
    assert after[0] == before[0], "the first revision is byte-identical"
    assert after[1]["categories"] == [{"category": "Name", "sealed": True, "key_exposed": True}]

    await _yes(conn, seeded, breach, datetime.now(UTC) - HOUR)
    await service.determine(
        conn,
        breach_uuid=uuid,
        outcome="yes",
        reasoning="Confirmed, wider than thought",
        became_aware_at=datetime.now(UTC) - HOUR / 2,
        actor_id=_dpo(seeded),
    )
    history = (await service.detail(conn, uuid))["determinations"]
    assert len(history) == 2 and history[0]["reasoning"] != history[1]["reasoning"]


async def test_a_key_cannot_be_exposed_for_data_that_was_not_sealed(
    conn: Any, seeded: dict[str, Any]
) -> None:
    breach = await _breach(conn, seeded)
    detail = await service.assess(
        conn,
        breach_uuid=str(breach["breach_uuid"]),
        began_at=None,
        categories=[{"category": "Consent relationships", "sealed": False, "key_exposed": True}],
        text={},
        actor_id=_dpo(seeded),
    )
    assert detail["assessment"]["categories"] == [
        {"category": "Consent relationships", "sealed": False, "key_exposed": False}
    ]


async def test_the_finding_on_who_caused_it_is_sealed(conn: Any, seeded: dict[str, Any]) -> None:
    breach = await _breach(conn, seeded)
    await service.assess(
        conn,
        breach_uuid=str(breach["breach_uuid"]),
        began_at=None,
        categories=[],
        text={"caused_by_findings": "Ravi in the lab team copied it"},
        actor_id=_dpo(seeded),
    )
    raw = await (
        await conn.execute(
            "SELECT a.caused_by_findings, b.title FROM breach_assessment a "
            "JOIN breach b ON b.breach_id = a.breach_id WHERE b.breach_uuid = %s",
            (str(breach["breach_uuid"]),),
        )
    ).fetchone()
    assert str(raw["caused_by_findings"]).startswith("SE::")
    assert str(raw["title"]).startswith("SE::")


async def test_the_trail_records_what_happened_and_none_of_the_words(
    conn: Any, seeded: dict[str, Any]
) -> None:
    breach = await _breach(conn, seeded)
    await _yes(conn, seeded, breach, datetime.now(UTC) - HOUR)
    rows = await (
        await conn.execute(
            "SELECT event_type, detail_json::text AS detail FROM audit_log "
            "WHERE entity_type = 'breach' AND entity_id = "
            "(SELECT breach_id FROM breach WHERE breach_uuid = %s) ORDER BY log_id",
            (str(breach["breach_uuid"]),),
        )
    ).fetchall()
    events = [r["event_type"] for r in rows]
    # Logged, then validated, and the yes creates all four duties.
    assert events[:2] == ["breach.recorded", "breach.determined"]
    assert events.count("breach.obligation_created") == 4
    assert not any(
        "laptop" in r["detail"].lower() or "contact details" in r["detail"].lower() for r in rows
    )


class TestTheRecordCannotBeEdited:
    """Raw SQL, past the service: the database holds the rule."""

    async def test_a_determination_is_never_updated(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        breach = await _breach(conn, seeded)
        await _yes(conn, seeded, breach, datetime.now(UTC) - HOUR)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            await conn.execute("UPDATE breach_determination SET outcome = 'no'")

    async def test_a_duty_is_never_updated(self, conn: Any, seeded: dict[str, Any]) -> None:
        breach = await _breach(conn, seeded)
        await _yes(conn, seeded, breach, datetime.now(UTC) - HOUR)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            await conn.execute("UPDATE breach_obligation SET due_at = now() + interval '1 year'")

    async def test_only_the_status_of_a_breach_moves(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        breach = await _breach(conn, seeded)
        with pytest.raises(psycopg.errors.RestrictViolation):
            await conn.execute(
                "UPDATE breach SET detected_at = now() WHERE breach_uuid = %s",
                (str(breach["breach_uuid"]),),
            )


def test_nothing_reads_encryption_to_decide_a_duty() -> None:
    """Whether data was sealed is recorded, and read by nobody who decides a
    duty: only `assess`, which stores it, may name it."""
    root = pathlib.Path(service.__file__).parent
    readers: dict[str, set[str]] = {}
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for node in ast.walk(fn):
                if isinstance(node, ast.Constant) and node.value in ("key_exposed", "sealed"):
                    readers.setdefault(path.name, set()).add(fn.name)
    assert readers == {"service.py": {"assess"}}, readers
