"""What is known when an incident is logged (0047, 2026-10-08).

Every answer optional, free text, sealed, and fixed once logged - the trigger
now holds every column but the status, these included. A cyber attack is
reportable to CERT-In from the start; no and not known add nothing.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
import pytest

from cmp.core.errors import ValidationFailed
from cmp.db.repositories.breaches import LOGGED_TEXT
from cmp.db.sql import fetch_one
from cmp.domain.breach import service
from tests.conftest import plain

pytestmark = pytest.mark.integration

SAID = {
    "origin": "A vendor's file share",
    "discovery": "A participant emailed the lab",
    "affected_systems": "Lab NAS; the annotation tool",
    "incident_details": "A folder of gait videos was shared by public link.",
    "impact_scale": "About 1,200 videos, roughly 300 people",
    "countries_involved": "India, Singapore",
    "data_nature": "Video of faces and gait (identifying); names",
    "subject_types": "Study participants",
    "entities_involved": "The Bangalore research institute",
    "third_parties": "Singapore Annotation Partners",
}


async def _log(conn: Any, seeded: dict[str, Any], **kw: Any) -> dict[str, Any]:
    return await service.record(
        conn,
        title="A shared folder left open",
        detected_at=datetime.now(UTC) - timedelta(minutes=20),
        began_at=None,
        location_kind="platform",
        processor_uuid=None,
        source_uuid=None,
        location_detail=None,
        actor_id=int(seeded["users"]["dpo"]["id"]),
        **kw,
    )


def _duties(breach: dict[str, Any]) -> set[str]:
    return {d["duty"] for d in breach["obligations"]}


async def test_what_is_said_is_kept_sealed_and_shown(conn: Any, seeded: dict[str, Any]) -> None:
    made = await _log(conn, seeded, logged=SAID, cyber_attack="no")
    assert {k: plain(v) for k, v in made["logged"].items()} == SAID
    assert made["cyber_attack"] == "no"
    row = await fetch_one(
        conn,
        f"SELECT {', '.join(LOGGED_TEXT)} FROM breach WHERE breach_uuid = %s",
        (made["breach_uuid"],),
    )
    assert row is not None and all(str(row[c]).startswith("SE::") for c in LOGGED_TEXT)
    assert _duties(made) == {"org_board"}


async def test_nothing_is_required(conn: Any, seeded: dict[str, Any]) -> None:
    made = await _log(conn, seeded, logged={"origin": "  ", "impact_scale": None})
    assert all(v is None for v in made["logged"].values())
    assert made["cyber_attack"] is None


async def test_a_cyber_attack_is_reportable_to_cert_in_at_once(
    conn: Any, seeded: dict[str, Any]
) -> None:
    made = await _log(conn, seeded, cyber_attack="yes")
    assert _duties(made) == {"org_board", "cert_in"}
    unknown = await _log(conn, seeded, cyber_attack="unknown")
    assert _duties(unknown) == {"org_board"}
    with pytest.raises(ValidationFailed):
        await _log(conn, seeded, cyber_attack="maybe")


async def test_what_was_logged_never_changes(conn: Any, seeded: dict[str, Any]) -> None:
    made = await _log(conn, seeded, logged=SAID)
    with pytest.raises(psycopg.errors.RestrictViolation):
        async with conn.transaction():
            await conn.execute(
                "UPDATE breach SET third_parties = 'someone else' WHERE breach_uuid = %s",
                (made["breach_uuid"],),
            )
    # The status still moves.
    async with conn.transaction():
        await conn.execute(
            "UPDATE breach SET status = 'closed' WHERE breach_uuid = %s", (made["breach_uuid"],)
        )
