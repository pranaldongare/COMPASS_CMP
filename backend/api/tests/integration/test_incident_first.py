"""An incident first; a breach is recorded on a yes (S3-06, ADR 0022).

Logging issues an incident reference and nothing else. The first
determination of *yes* records the breach and issues its breach reference, in
the same transaction as the duties it starts; nothing later withdraws it or
issues a second. Telling anyone waits for that recording, drafting does not.
"""

from __future__ import annotations

import importlib.util
import pathlib
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
import pytest

from cmp.core.errors import Conflict
from cmp.db.repositories import entities
from cmp.db.sql import fetch_all, fetch_one
from cmp.domain.breach import affected, board, notices, service
from tests.integration.test_breach_affected import _breach, _person
from tests.integration.test_breach_notices import WORDS, _sends, queued  # noqa: F401

pytestmark = pytest.mark.integration

HOUR = timedelta(hours=1)


def _dpo(seeded: dict[str, Any]) -> int:
    return int(seeded["users"]["dpo"]["id"])


async def _determine(
    conn: Any, seeded: dict[str, Any], uuid: str, outcome: str, *, aware_ago: timedelta = HOUR
) -> dict[str, Any]:
    return await service.determine(
        conn,
        breach_uuid=uuid,
        outcome=outcome,
        reasoning="As the team found it",
        became_aware_at=datetime.now(UTC) - aware_ago if outcome == "yes" else None,
        actor_id=_dpo(seeded),
    )


async def _events(conn: Any, uuid: str) -> list[dict[str, Any]]:
    return await fetch_all(
        conn,
        """SELECT l.event_type, l.detail_json FROM audit_log l
             JOIN breach b ON b.breach_id = l.entity_id
            WHERE l.entity_type = 'breach' AND b.breach_uuid = %s ORDER BY l.log_id""",
        (uuid,),
    )


async def _label(conn: Any, uuid: str) -> str:
    row = await fetch_one(conn, "SELECT breach_id FROM breach WHERE breach_uuid = %s", (uuid,))
    assert row is not None
    resolved = await entities.resolve(conn, [("breach", int(row["breach_id"]))])
    return str(resolved[("breach", int(row["breach_id"]))]["entity_label"])


async def test_logging_issues_an_incident_reference_and_no_breach_reference(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """Written first. A report is a suspicion until the team validates it: the
    BR numbers count breaches, and none is issued for a suspicion."""
    uuid = await _breach(conn, seeded)
    detail = await service.detail(conn, uuid)

    assert detail["incident_reference"].startswith("INC-")
    assert detail["breach_reference"] is None
    assert detail["reference"] == detail["incident_reference"]
    assert detail["breach_recorded_at"] is None
    [listed] = [
        b for b in await service.register(conn, status=None) if str(b["breach_uuid"]) == uuid
    ]
    assert listed["breach_reference"] is None and listed["reference"].startswith("INC-")
    assert await _label(conn, uuid) == f"Incident {detail['incident_reference']}"


async def test_the_first_yes_records_the_breach_once(conn: Any, seeded: dict[str, Any]) -> None:
    uuid = await _breach(conn, seeded)
    await _determine(conn, seeded, uuid, "pending")
    assert (await service.detail(conn, uuid))["breach_reference"] is None, "pending records nothing"

    recorded = await _determine(conn, seeded, uuid, "yes")
    reference = recorded["breach_reference"]
    assert reference and reference.startswith("BR-")
    assert recorded["reference"] == reference, "quoted by the breach reference from now on"
    assert recorded["incident_reference"].startswith("INC-"), "and the incident's is kept"
    assert recorded["breach_recorded_at"] is not None
    assert {o["duty"] for o in recorded["obligations"]} == {
        "org_board",
        "board_intimation",
        "board_report",
        "principals",
    }

    confirmed = [e for e in await _events(conn, uuid) if e["event_type"] == "breach.confirmed"]
    assert [e["detail_json"]["reference"] for e in confirmed] == [reference]
    assert await _label(conn, uuid) == f"Breach {reference} ({recorded['incident_reference']})"

    # A later no sets the duties aside and leaves the recording; a later yes
    # reinstates them and issues no second number.
    after_no = await _determine(conn, seeded, uuid, "no")
    assert after_no["breach_reference"] == reference
    dpdp = [o for o in after_no["obligations"] if o["duty"] != "org_board"]
    assert all(o["state"] == "not_applicable" for o in dpdp)
    after_yes = await _determine(conn, seeded, uuid, "yes")
    assert after_yes["breach_reference"] == reference
    assert all(o["state"] == "outstanding" for o in after_yes["obligations"]), (
        "the organisation's board is untouched by either"
    )
    assert len([e for e in await _events(conn, uuid) if e["event_type"] == "breach.confirmed"]) == 1
    rows = await fetch_all(
        conn,
        """SELECT r.reference FROM breach_recording r JOIN breach b USING (breach_id)
            WHERE b.breach_uuid = %s""",
        (uuid,),
    )
    assert [r["reference"] for r in rows] == [reference]


async def test_a_no_first_records_nothing(conn: Any, seeded: dict[str, Any]) -> None:
    uuid = await _breach(conn, seeded)
    detail = await _determine(conn, seeded, uuid, "no")
    assert detail["breach_reference"] is None
    assert not [e for e in await _events(conn, uuid) if e["event_type"] == "breach.confirmed"]


async def test_nobody_is_told_before_the_breach_is_recorded(
    conn: Any,
    seeded: dict[str, Any],
    queued: list[tuple[str, tuple[Any, ...]]],  # noqa: F811
) -> None:
    """Deriving, drafting and approving may run during validation; sending may
    not - a notice to principals about something that may not be a breach."""
    uuid = await _breach(conn, seeded)
    dpo = _dpo(seeded)
    person_id, person_uuid, _ = await _person(conn, seeded, "a")
    await affected.confirm(
        conn, breach_uuid=uuid, scopes=[], exclude=[], add=[person_uuid], note=None, actor_id=dpo
    )
    drafted = await notices.draft(conn, breach_uuid=uuid, words=WORDS, actor_id=dpo)
    version = drafted["versions"][-1]["notice_uuid"]
    await notices.approve(conn, breach_uuid=uuid, notice_uuid=str(version), actor_id=dpo)

    with pytest.raises(Conflict) as refused:
        await notices.send(conn, breach_uuid=uuid, actor_id=dpo)
    assert refused.value.code == "breach_not_recorded"
    assert not _sends(queued)
    waiting = await notices.overview(conn, breach_uuid=uuid)
    assert waiting["send_blocked_by"] == str(refused.value.message), "the console shows the same"

    recorded = await _determine(conn, seeded, uuid, "yes")
    assert (await notices.overview(conn, breach_uuid=uuid))["send_blocked_by"] is None
    await notices.send(conn, breach_uuid=uuid, actor_id=dpo)
    delivered = await fetch_all(
        conn,
        """SELECT l.detail_json FROM audit_log l
            WHERE l.event_type = 'breach_notice.delivered' AND l.subject_user_id = %s
            ORDER BY l.log_id DESC LIMIT 1""",
        (person_id,),
    )
    assert delivered[0]["detail_json"]["reference"] == recorded["breach_reference"], (
        "she is given the breach reference, never the incident's"
    )


async def test_the_board_documents_say_when_it_is_not_yet_a_breach(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _breach(conn, seeded)
    before = await board.intimation(conn, breach_uuid=uuid)
    report = await board.report(conn, breach_uuid=uuid)
    assert board.NOT_RECORDED in before["missing"] and board.NOT_RECORDED in report["missing"]
    assert before["breach_reference"] is None and before["reference"].startswith("INC-")

    await _determine(conn, seeded, uuid, "yes")
    after = await board.intimation(conn, breach_uuid=uuid)
    assert board.NOT_RECORDED not in after["missing"]
    assert after["reference"] == after["breach_reference"]
    assert after["reference"].startswith("BR-")


async def test_a_recording_is_written_once_and_never_changed(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """Raw SQL, past the service: one per breach, and never edited or removed."""
    uuid = await _breach(conn, seeded)
    await _determine(conn, seeded, uuid, "yes")
    where = "breach_id = (SELECT breach_id FROM breach WHERE breach_uuid = %s)"
    with pytest.raises(psycopg.errors.UniqueViolation):
        async with conn.transaction():
            await conn.execute(
                f"""INSERT INTO breach_recording
                      (breach_id, reference, determination_id, recorded_by)
                    SELECT breach_id, 'BR-TEST-0001', determination_id, recorded_by
                      FROM breach_recording WHERE {where}""",
                (uuid,),
            )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        async with conn.transaction():
            await conn.execute(
                f"UPDATE breach_recording SET reference = 'BR-TEST-0002' WHERE {where}", (uuid,)
            )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        async with conn.transaction():
            await conn.execute(f"DELETE FROM breach_recording WHERE {where}", (uuid,))


def _backfill_sql() -> str:
    path = pathlib.Path(__file__).parents[2] / "migrations/versions/0038_incident_first.py"
    spec = importlib.util.spec_from_file_location("m0038", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return str(module.UPGRADE).split("-- Rows logged before this revision")[1].split("\n", 1)[1]


async def test_a_breach_logged_before_the_order_keeps_its_number(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """The backfill: a row logged before 0038 has a BR string as its only
    reference. With a yes among its determinations, the recording carries that
    same string, the first yes, its author and its time; without one, none."""
    dpo = _dpo(seeded)
    made = []
    for ref in ("BR-1999-0001", "BR-1999-0002"):
        row = await fetch_one(
            conn,
            """INSERT INTO breach (reference, title, detected_at, location_kind, recorded_by)
               VALUES (%s, 'SE::legacy', now() - interval '3 days', 'platform', %s)
               RETURNING breach_id""",
            (ref, dpo),
        )
        assert row is not None
        made.append(int(row["breach_id"]))
    yes_at = datetime.now(UTC) - 2 * 24 * HOUR
    first_yes = await fetch_one(
        conn,
        """INSERT INTO breach_determination
             (breach_id, outcome, reasoning, became_aware_at, determined_by, determined_at)
           VALUES (%s, 'yes', 'SE::r', %s, %s, %s) RETURNING determination_id""",
        (made[0], yes_at, dpo, yes_at),
    )
    await conn.execute(
        """INSERT INTO breach_determination (breach_id, outcome, reasoning, became_aware_at,
                                             determined_by)
           VALUES (%s, 'yes', 'SE::later', now(), %s), (%s, 'no', 'SE::no', NULL, %s)""",
        (made[0], dpo, made[1], dpo),
    )

    # The migration's own statement, narrowed to these two rows.
    backfill = _backfill_sql().strip().rstrip(";")
    await conn.execute(f"{backfill} WHERE b.breach_id = ANY(%s)", (made,))

    rows = await fetch_all(
        conn,
        """SELECT breach_id, reference, determination_id, recorded_by, recorded_at
             FROM breach_recording WHERE breach_id = ANY(%s)""",
        (made,),
    )
    assert first_yes is not None
    assert [(r["breach_id"], r["reference"]) for r in rows] == [(made[0], "BR-1999-0001")]
    assert rows[0]["determination_id"] == first_yes["determination_id"]
    assert rows[0]["recorded_by"] == dpo and rows[0]["recorded_at"] == yes_at
    legacy = await fetch_one(
        conn, "SELECT breach_uuid FROM breach WHERE breach_id = %s", (made[0],)
    )
    assert legacy is not None
    assert await _label(conn, str(legacy["breach_uuid"])) == "Breach BR-1999-0001"
