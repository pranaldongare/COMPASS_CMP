"""The organisation's board within thirty minutes of first noticed (S3-07).

Every incident owes it, from the moment it is logged: a duty anchored at first
noticed, its due time stored then. Validation never touches it. A person
reports; the DPO records when and to whom, and the platform drafts a brief that
names nobody.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
import pytest

from cmp.api.routers.v1 import dashboard
from cmp.core.config import settings
from cmp.core.errors import TransitionNotPermitted, ValidationFailed
from cmp.db.sql import fetch_one
from cmp.domain.breach import board, service
from tests.conftest import plain
from tests.integration.test_breach_register import tell_org_board

pytestmark = pytest.mark.integration

MINUTE = timedelta(minutes=1)


def _dpo(seeded: dict[str, Any]) -> int:
    return int(seeded["users"]["dpo"]["id"])


async def _log(
    conn: Any, seeded: dict[str, Any], *, noticed_ago: timedelta = 5 * MINUTE
) -> dict[str, Any]:
    return await service.record(
        conn,
        title="Badge reader logs copied to a USB stick",
        detected_at=datetime.now(UTC) - noticed_ago,
        began_at=None,
        location_kind="platform",
        processor_uuid=None,
        source_uuid=None,
        location_detail=None,
        actor_id=_dpo(seeded),
    )


def _org(detail: dict[str, Any]) -> dict[str, Any]:
    [duty] = [d for d in detail["obligations"] if d["duty"] == "org_board"]
    return duty


async def test_every_incident_owes_the_board_thirty_minutes_from_first_noticed(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """Written first. No mark and no validation: logging is the trigger, and the
    clock runs from when it was noticed, not from when it was typed in."""
    logged = await _log(conn, seeded, noticed_ago=10 * MINUTE)
    duty = _org(logged)
    assert duty["state"] == "outstanding"
    assert duty["anchored_at"] == logged["detected_at"]
    assert duty["due_at"] == logged["detected_at"] + 30 * MINUTE
    assert duty["label"] == "Organisation's board"
    assert duty["basis"] == "Internal policy: within 30 minutes of first noticed"
    assert 0 < duty["clock"]["seconds_remaining"] <= 20 * 60


async def test_an_incident_logged_late_starts_overdue(conn: Any, seeded: dict[str, Any]) -> None:
    duty = _org(await _log(conn, seeded, noticed_ago=45 * MINUTE))
    assert duty["clock"]["overdue"] is True
    assert duty["clock"]["seconds_remaining"] < 0


async def test_validation_never_touches_it(conn: Any, seeded: dict[str, Any]) -> None:
    logged = await _log(conn, seeded)
    uuid = str(logged["breach_uuid"])
    before = _org(logged)
    for outcome, aware in (("no", None), ("yes", datetime.now(UTC)), ("no", None)):
        detail = await service.determine(
            conn,
            breach_uuid=uuid,
            outcome=outcome,
            reasoning="As found",
            became_aware_at=aware,
            actor_id=_dpo(seeded),
        )
        after = _org(detail)
        assert after["state"] == "outstanding" and after["due_at"] == before["due_at"]
        assert after["events"] == []


async def test_a_change_of_setting_moves_no_clock_already_running(
    conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    first = await _log(conn, seeded)
    monkeypatch.setattr(settings, "breach_org_board_minutes", 60)
    second = await _log(conn, seeded)

    reread = _org(await service.detail(conn, str(first["breach_uuid"])))
    assert reread["due_at"] == first["detected_at"] + 30 * MINUTE, "stored, never recomputed"
    assert reread["basis"] == "Internal policy: within 30 minutes of first noticed"
    assert _org(second)["due_at"] == second["detected_at"] + 60 * MINUTE
    assert _org(second)["basis"] == "Internal policy: within 60 minutes of first noticed"


async def test_recording_the_report_needs_whom_it_was_made_to(
    conn: Any, seeded: dict[str, Any]
) -> None:
    logged = await _log(conn, seeded)
    uuid = str(logged["breach_uuid"])
    common: dict[str, Any] = {
        "breach_uuid": uuid,
        "duty": "org_board",
        "occurred_at": datetime.now(UTC),
        "reference": None,
        "note": None,
        "actor_id": _dpo(seeded),
    }
    with pytest.raises(ValidationFailed) as refused:
        await service.complete_duty(conn, **common, reported_to="  ")
    assert refused.value.field == "reported_to"
    with pytest.raises(ValidationFailed):
        await service.complete_duty(
            conn, **{**common, "occurred_at": logged["detected_at"] - MINUTE}, reported_to="x"
        )
    with pytest.raises(ValidationFailed):
        await service.complete_duty(
            conn,
            **{**common, "occurred_at": datetime.now(UTC) + timedelta(hours=1)},
            reported_to="x",
        )

    done = _org(await service.complete_duty(conn, **common, reported_to="Board secretary, by call"))
    assert done["state"] == "done" and done["reference"] is None, "a reference is optional here"
    assert str(done["reported_to"]).startswith("SE::"), "sealed; the console opens it"
    assert plain(done["reported_to"]) == "Board secretary, by call"
    row = await fetch_one(
        conn,
        """SELECT e.reported_to FROM breach_obligation_event e
             JOIN breach_obligation o USING (obligation_id)
             JOIN breach b USING (breach_id)
            WHERE b.breach_uuid = %s AND o.kind = 'org_board'""",
        (uuid,),
    )
    assert row is not None and str(row["reported_to"]).startswith("SE::"), "sealed at rest"


async def test_only_the_board_takes_whom_and_only_it_does_without_a_reference(
    conn: Any, seeded: dict[str, Any]
) -> None:
    logged = await _log(conn, seeded)
    uuid = str(logged["breach_uuid"])
    await service.mark_cert_in(conn, breach_uuid=uuid, actor_id=_dpo(seeded))
    base: dict[str, Any] = {
        "breach_uuid": uuid,
        "duty": "cert_in",
        "occurred_at": datetime.now(UTC),
        "note": None,
        "actor_id": _dpo(seeded),
    }
    with pytest.raises(ValidationFailed) as no_reference:
        await service.complete_duty(conn, **base, reference=None)
    assert no_reference.value.field == "reference"
    with pytest.raises(ValidationFailed) as no_whom:
        await service.complete_duty(conn, **base, reference="CERT/1", reported_to="Someone")
    assert no_whom.value.field == "reported_to"


async def test_the_database_holds_the_rule_too(conn: Any, seeded: dict[str, Any]) -> None:
    """Past the service: a completion of this duty without whom is refused."""
    logged = await _log(conn, seeded)
    with pytest.raises(psycopg.errors.CheckViolation):
        await conn.execute(
            """INSERT INTO breach_obligation_event (obligation_id, kind, occurred_at, recorded_by)
               SELECT o.obligation_id, 'completed', now(), %s
                 FROM breach_obligation o JOIN breach b USING (breach_id)
                WHERE b.breach_uuid = %s AND o.kind = 'org_board'""",
            (_dpo(seeded), str(logged["breach_uuid"])),
        )


async def test_closing_waits_for_the_report(conn: Any, seeded: dict[str, Any]) -> None:
    logged = await _log(conn, seeded)
    uuid = str(logged["breach_uuid"])
    await service.determine(
        conn,
        breach_uuid=uuid,
        outcome="no",
        reasoning="Not personal data",
        became_aware_at=None,
        actor_id=_dpo(seeded),
    )
    with pytest.raises(TransitionNotPermitted) as refused:
        await service.transition(
            conn, breach_uuid=uuid, to="closed", reason=None, actor_id=_dpo(seeded)
        )
    assert refused.value.details["blockers"] == ["Organisation's board is outstanding"]
    await tell_org_board(conn, seeded, uuid)
    closed = await service.transition(
        conn, breach_uuid=uuid, to="closed", reason=None, actor_id=_dpo(seeded)
    )
    assert closed["status"] == "closed"


async def test_the_brief_names_what_is_missing_and_nobody(
    conn: Any, seeded: dict[str, Any]
) -> None:
    logged = await _log(conn, seeded)
    uuid = str(logged["breach_uuid"])
    await service.assess(
        conn,
        breach_uuid=uuid,
        began_at=None,
        categories=[],
        text={"caused_by_findings": "Ravi Kumar copied the logs"},
        actor_id=_dpo(seeded),
    )
    brief = await board.org_board_brief(conn, breach_uuid=uuid)

    assert brief["reference"].startswith("INC-") and brief["validation"] == "pending"
    assert brief["touched"] == {"listed": 0, "notified": 0}
    assert brief["cert_in_reportable"] is False
    assert any("validation is still pending" in m for m in brief["missing"])
    assert "When it began" in brief["missing"]
    assert brief["duty"] is not None and brief["duty"]["duty"] == "org_board"
    text = json.dumps(brief, default=str)
    assert "caused_by" not in text and "Ravi" not in text
    sealed = (await service.detail(conn, uuid))["assessment"]["caused_by_findings"]
    assert sealed not in text, "not even sealed: the finding is not the board's"
    assert "_by_name" not in text and "reported_to" not in text, "nobody's name"


async def test_the_dashboard_counts_it(conn: Any, seeded: dict[str, Any]) -> None:
    before = (await dashboard._dpo(conn))["counts"]
    await _log(conn, seeded, noticed_ago=45 * MINUTE)
    after = (await dashboard._dpo(conn))["counts"]
    assert after["breach_duties_late"] == before["breach_duties_late"] + 1
    assert after["breach_duties_outstanding"] == before["breach_duties_outstanding"] + 1
