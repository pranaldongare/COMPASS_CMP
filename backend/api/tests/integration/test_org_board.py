"""The organisation's board within thirty minutes of a validation of yes.

An incident owes it nothing until it is validated (ADR 0037, which moved this
from first noticed): the first yes creates a duty anchored at that validation,
its due time stored then. A later no sets it aside with the DPDP duties and a
later yes brings it back. The platform drafts a brief that names nobody.
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


async def _validate(
    conn: Any, seeded: dict[str, Any], logged: dict[str, Any], outcome: str = "yes"
) -> dict[str, Any]:
    return await service.determine(
        conn,
        breach_uuid=str(logged["breach_uuid"]),
        outcome=outcome,
        reasoning="As found",
        became_aware_at=datetime.now(UTC) - MINUTE if outcome == "yes" else None,
        actor_id=_dpo(seeded),
    )


async def test_an_incident_owes_the_board_nothing_until_a_yes(
    conn: Any, seeded: dict[str, Any]
) -> None:
    logged = await _log(conn, seeded, noticed_ago=45 * MINUTE)
    assert logged["obligations"] == [], "logged an hour late or not, nothing is overdue"
    no = await _validate(conn, seeded, logged, "no")
    assert not [d for d in no["obligations"] if d["duty"] == "org_board"], "a no creates none"


async def test_a_yes_gives_the_board_thirty_minutes_from_the_validation(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """Not from first noticed: the incident here was noticed three hours ago,
    and the clock starts now."""
    logged = await _log(conn, seeded, noticed_ago=180 * MINUTE)
    before = datetime.now(UTC)
    duty = _org(await _validate(conn, seeded, logged))
    assert duty["state"] == "outstanding"
    assert before <= duty["anchored_at"] <= datetime.now(UTC)
    assert duty["due_at"] == duty["anchored_at"] + 30 * MINUTE
    assert duty["label"] == "Organisation's board"
    assert duty["basis"] == "Internal policy: within 30 minutes of a validation of yes"
    assert 29 * 60 < duty["clock"]["seconds_remaining"] <= 30 * 60
    assert duty["clock"]["overdue"] is False


async def test_a_later_no_sets_it_aside_and_a_later_yes_restarts_it(
    conn: Any, seeded: dict[str, Any]
) -> None:
    logged = await _log(conn, seeded)
    first = _org(await _validate(conn, seeded, logged))
    aside = _org(await _validate(conn, seeded, logged, "no"))
    assert aside["state"] == "not_applicable"
    back = _org(await _validate(conn, seeded, logged))
    assert back["state"] == "outstanding"
    assert back["anchored_at"] > first["anchored_at"], "thirty minutes from the new yes"


async def test_a_report_already_made_stays_made(conn: Any, seeded: dict[str, Any]) -> None:
    logged = await _log(conn, seeded)
    uuid = str(logged["breach_uuid"])
    await _validate(conn, seeded, logged)
    await tell_org_board(conn, seeded, uuid)
    assert _org(await _validate(conn, seeded, logged, "no"))["state"] == "done"


async def test_a_change_of_setting_moves_no_clock_already_running(
    conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _org(await _validate(conn, seeded, await _log(conn, seeded)))
    monkeypatch.setattr(settings, "breach_org_board_minutes", 60)
    logged = await _log(conn, seeded)
    second = _org(await _validate(conn, seeded, logged))

    reread = _org(await service.detail(conn, str(logged["breach_uuid"])))
    assert reread["due_at"] == second["anchored_at"] + 60 * MINUTE
    assert first["due_at"] == first["anchored_at"] + 30 * MINUTE, "stored, never recomputed"
    assert first["basis"] == "Internal policy: within 30 minutes of a validation of yes"
    assert second["basis"] == "Internal policy: within 60 minutes of a validation of yes"


async def test_recording_the_report_needs_whom_it_was_made_to(
    conn: Any, seeded: dict[str, Any]
) -> None:
    logged = await _log(conn, seeded)
    uuid = str(logged["breach_uuid"])
    await _validate(conn, seeded, logged)
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
            conn, **{**common, "occurred_at": logged["detected_at"] - 10 * MINUTE}, reported_to="x"
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
    await _validate(conn, seeded, logged)
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
    await _validate(conn, seeded, logged)
    with pytest.raises(TransitionNotPermitted) as refused:
        await service.transition(
            conn, breach_uuid=uuid, to="closed", reason=None, actor_id=_dpo(seeded)
        )
    assert "Organisation's board is outstanding" in refused.value.details["blockers"]


async def test_a_no_leaves_nothing_in_the_way_of_closing(conn: Any, seeded: dict[str, Any]) -> None:
    """Why the duty moved: an incident that turns out to be nothing, and every
    report from the public link that does, closes without telling the board."""
    logged = await _log(conn, seeded)
    await _validate(conn, seeded, logged, "no")
    closed = await service.transition(
        conn,
        breach_uuid=str(logged["breach_uuid"]),
        to="closed",
        reason=None,
        actor_id=_dpo(seeded),
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
    assert brief["affected"] == {"listed": 0, "notified": 0}
    assert brief["cert_in_reportable"] is False
    assert any("validation is still pending" in m for m in brief["missing"])
    assert "When it began" in brief["missing"]
    assert brief["duty"] is None, "no duty yet: it comes with a yes"
    text = json.dumps(brief, default=str)
    assert "caused_by" not in text and "Ravi" not in text
    sealed = (await service.detail(conn, uuid))["assessment"]["caused_by_findings"]
    assert sealed not in text, "not even sealed: the finding is not the board's"
    assert "_by_name" not in text and "reported_to" not in text, "nobody's name"


async def test_the_dashboard_counts_it(conn: Any, seeded: dict[str, Any]) -> None:
    """By the incident's own row. The dashboard reads the register, which holds
    500, so on a database with more open than that a new incident pushes an old
    one out, and the total does not move by what this one adds."""

    async def outstanding(incident: dict[str, Any]) -> int:
        page = await dashboard._dpo(conn)
        duties = [d for b in page["breaches"] for d in b["obligations"]]
        waiting = [d for d in duties if d["state"] == "outstanding"]
        assert page["counts"]["breach_duties_outstanding"] == len(waiting)
        [mine] = [b for b in page["breaches"] if b["breach_uuid"] == incident["breach_uuid"]]
        return sum(d["state"] == "outstanding" for d in mine["obligations"])

    assert await outstanding(await _log(conn, seeded, noticed_ago=45 * MINUTE)) == 0
    logged = await _log(conn, seeded)
    await _validate(conn, seeded, logged)
    assert await outstanding(logged) == 4
