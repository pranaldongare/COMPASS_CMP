"""The Board and CERT-In (S3-04).

Both Board documents are drafted from the register at any point; the detailed
report carries all six items of Rule 7(2)(b), and says in words when no notice
has been sent. An extension moves the report's due time and not the
intimation's. The DPO's dashboard shows every open breach and each duty's
clock. Nothing in the code can reach a regulator.
"""

from __future__ import annotations

import ast
import pathlib
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

import cmp
from cmp.api.routers.v1 import dashboard
from cmp.domain.breach import board, notices, service
from tests.conftest import plain
from tests.integration.test_breach_affected import _breach, _person
from tests.integration.test_breach_notices import _approved, _determined, queued  # noqa: F401

pytestmark = pytest.mark.integration

HOUR = timedelta(hours=1)


async def test_both_documents_can_be_drafted_the_moment_an_incident_is_logged(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _breach(conn, seeded)
    intimation = await board.intimation(conn, breach_uuid=uuid)
    assert intimation["basis"] == "Rule 7(2)(a)" and intimation["determination"] == "pending"
    assert intimation["missing"] == [
        "Not yet recorded as a personal data breach",
        "The nature and extent of the breach",
        "Its timing",
        "Its likely impact",
    ]
    report = await board.report(conn, breach_uuid=uuid)
    assert report["notices"]["sent"] is False
    assert report["notices"]["statement"].startswith("No notice has yet been sent")
    assert [f["item"] for f in report["facts"]] == ["ii", "iii", "iv", "v"]
    assert report["missing"][:2] == [
        "Not yet recorded as a personal data breach",
        "(i) No assessment has been recorded",
    ]


async def test_the_detailed_report_carries_all_six_items_and_the_account_of_notices(
    conn: Any,
    seeded: dict[str, Any],
    queued: list[Any],  # noqa: F811
) -> None:
    a = await _person(conn, seeded, "a")
    uuid = await _determined(conn, seeded, [a[1]])
    dpo = int(seeded["users"]["dpo"]["id"])
    await service.assess(
        conn,
        breach_uuid=uuid,
        began_at=None,
        categories=[{"category": "Mobile", "sealed": True, "key_exposed": False}],
        text={
            "nature_extent": "One export file",
            "likely_impact": "Unwanted calls",
            "circumstances": "A share left public",
            "mitigation": "The share was closed",
            "caused_by_findings": "A contractor's sync client",
            "remedial_measures": "Shares are private by default",
        },
        actor_id=dpo,
    )
    before = await board.report(conn, breach_uuid=uuid)
    assert before["notices"]["sent"] is False, "said, not left out"
    assert before["notices"]["listed"] == 1

    await _approved(conn, seeded, uuid)
    await notices.send(conn, breach_uuid=uuid, actor_id=dpo)
    report = await board.report(conn, breach_uuid=uuid)
    assert report["missing"] == []
    facts = {f["item"]: plain(f["text"]) for f in report["facts"]}
    assert facts == {
        "ii": "A share left public",
        "iii": "The share was closed",
        "iv": "A contractor's sync client",
        "v": "Shares are private by default",
    }
    assert plain(report["assessment"]["nature_extent"]) == "One export file"
    account = report["notices"]
    assert account["sent"] is True and account["listed"] == 1 and account["notified"] == 0
    [version] = account["versions"]
    assert {c["channel"]: (c["delivered"], c["queued"]) for c in version["channels"]} == {
        "portal": (1, 0),
        "sms": (0, 1),
    }
    intimation = await board.intimation(conn, breach_uuid=uuid)
    assert intimation["missing"] == []
    assert plain(intimation["likely_impact"]) == "Unwanted calls"


async def test_an_extension_moves_the_report_and_not_the_intimation(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _breach(conn, seeded)
    dpo = int(seeded["users"]["dpo"]["id"])
    aware = datetime.now(UTC) - HOUR
    await service.determine(
        conn,
        breach_uuid=uuid,
        outcome="yes",
        reasoning="Yes",
        became_aware_at=aware,
        actor_id=dpo,
    )
    allowed = aware + timedelta(days=14)
    await service.extend_report(
        conn,
        breach_uuid=uuid,
        requested_at=datetime.now(UTC),
        allowed_until=allowed,
        reference="DPB/EXT/1",
        note=None,
        actor_id=dpo,
    )
    report = await board.report(conn, breach_uuid=uuid)
    intimation = await board.intimation(conn, breach_uuid=uuid)
    assert report["duty"]["due_at"] == allowed
    assert intimation["duty"]["due_at"] is None, "without delay, as before"

    await service.complete_duty(
        conn,
        breach_uuid=uuid,
        duty="board_intimation",
        occurred_at=datetime.now(UTC),
        reference="DPB/INT/9",
        note=None,
        actor_id=dpo,
    )
    intimation = await board.intimation(conn, breach_uuid=uuid)
    assert intimation["duty"]["state"] == "done" and intimation["duty"]["reference"] == "DPB/INT/9"


async def test_the_dashboard_shows_every_open_breach_and_each_duty(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    made = await service.record(
        conn,
        title="Noticed a week ago",
        detected_at=datetime.now(UTC) - 200 * HOUR,
        began_at=None,
        location_kind="platform",
        processor_uuid=None,
        source_uuid=None,
        location_detail=None,
        actor_id=dpo,
    )
    uuid = str(made["breach_uuid"])
    await service.mark_cert_in(conn, breach_uuid=uuid, actor_id=dpo)
    await service.determine(
        conn,
        breach_uuid=uuid,
        outcome="yes",
        reasoning="Yes",
        became_aware_at=datetime.now(UTC) - 100 * HOUR,
        actor_id=dpo,
    )
    data = await dashboard._dpo(conn)
    [mine] = [b for b in data["breaches"] if str(b["breach_uuid"]) == uuid]
    assert {d["duty"] for d in mine["obligations"]} == {
        "org_board",
        "cert_in",
        "board_intimation",
        "board_report",
        "principals",
    }
    assert data["counts"]["breach_duties_late"] >= 2, "CERT-In and the report are overdue"
    rows = {r["key"]: r for r in dashboard._attention("dpo", data["counts"], data["queues"])}
    assert rows["breach_duties_late"]["severity"] == "critical"
    assert rows["breach_duties_late"]["href"] == "/breaches"


def test_nothing_in_the_breach_code_can_reach_a_regulator() -> None:
    """The platform drafts and tracks; a person submits. So nothing that handles
    a breach may import a way to talk to the outside world, and the one task
    that sends anything sends the principals' notice and nothing else."""
    src = pathlib.Path(cmp.__file__).parent
    outward = {
        "httpx",
        "requests",
        "urllib",
        "aiohttp",
        "smtplib",
        "socket",
        "http",
        "cmp.infrastructure.email",
        "cmp.infrastructure.sms",
        "cmp.infrastructure.messaging",
    }
    files = [
        *sorted((src / "domain/breach").glob("*.py")),
        src / "api/routers/v1/breaches.py",
        src / "api/routers/v1/breach_tickets.py",
    ]
    found: list[str] = []
    for path in files:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = (
                [a.name for a in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else []
            )
            found += [
                f"{path.name}: {n}" for n in names if n.split(".")[0] in outward or n in outward
            ]
    assert found == [], found

    task = (src / "tasks/notifications/breach.py").read_text(encoding="utf-8")
    delivered = [
        ast.unparse(node.args[0])
        for node in ast.walk(ast.parse(task))
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "deliver"
    ]
    assert delivered == ["Message.BREACH_NOTICE"]

    # Breach tickets (S3-08) tell a member of staff a ticket is waiting, from
    # their own task, and nothing else.
    task = (src / "tasks/notifications/breach_tickets.py").read_text(encoding="utf-8")
    delivered = [
        ast.unparse(node.args[0])
        for node in ast.walk(ast.parse(task))
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "deliver"
    ]
    assert delivered == ["Message.BREACH_TICKET_WAITING"]
