"""Files kept with an incident: the email, the proof, the chat (2026-10-06).

Evidence, kept as it came: a kind, a sealed name and note, the hash and size.
Never replaced or removed - the database refuses both - and refused on a
closed breach like every write. The trail says the kind, never the name.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
import pytest

from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.core.security import file_hash
from cmp.db.sql import fetch_all, fetch_one
from cmp.domain.breach import service
from cmp.infrastructure.storage.service import storage
from tests.conftest import plain

pytestmark = pytest.mark.integration

EMAIL = b"From: someone@example.org\r\nSubject: I received a list that is not mine\r\n\r\nHi.\r\n"


def _dpo(seeded: dict[str, Any]) -> int:
    return int(seeded["users"]["dpo"]["id"])


async def _incident(conn: Any, seeded: dict[str, Any]) -> str:
    made = await service.record(
        conn,
        title="A contact list sent to the wrong address",
        detected_at=datetime.now(UTC) - timedelta(minutes=20),
        began_at=None,
        location_kind="platform",
        processor_uuid=None,
        source_uuid=None,
        location_detail=None,
        actor_id=_dpo(seeded),
    )
    return str(made["breach_uuid"])


async def _attach(conn: Any, seeded: dict[str, Any], uuid: str, **kw: Any) -> dict[str, Any]:
    payload = kw.pop("payload", EMAIL)
    return await service.add_attachment(
        conn,
        breach_uuid=uuid,
        kind=kw.pop("kind", "email"),
        note=kw.pop("note", "The report from Asha Rao"),
        file_name=kw.pop("file_name", "Report from Asha Rao.eml"),
        storage_ref=storage().save(payload, subdir="breach", suggested_name="attachment.eml"),
        sha256=file_hash(payload),
        size_bytes=len(payload),
        content_type="message/rfc822",
        actor_id=_dpo(seeded),
    )


async def test_a_file_is_kept_with_the_incident_sealed_and_hashed(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _incident(conn, seeded)
    shown = await _attach(conn, seeded, uuid)
    [att] = shown["attachments"]
    assert (att["kind"], att["size_bytes"], att["sha256"]) == (
        "email",
        len(EMAIL),
        file_hash(EMAIL),
    )
    row = await fetch_one(
        conn,
        "SELECT file_name, note FROM breach_attachment WHERE attachment_uuid = %s",
        (att["attachment_uuid"],),
    )
    assert row is not None
    assert row["file_name"].startswith("SE::") and row["note"].startswith("SE::")
    assert plain(row["file_name"]) == "Report from Asha Rao.eml"

    payload, name, recorded = await service.read_attachment(
        conn, breach_uuid=uuid, attachment_uuid=str(att["attachment_uuid"]), actor_id=_dpo(seeded)
    )
    assert (payload, name, recorded) == (EMAIL, "Report from Asha Rao.eml", file_hash(EMAIL))


async def test_the_trail_says_the_kind_never_the_name(conn: Any, seeded: dict[str, Any]) -> None:
    uuid = await _incident(conn, seeded)
    shown = await _attach(conn, seeded, uuid)
    [att] = shown["attachments"]
    await service.read_attachment(
        conn, breach_uuid=uuid, attachment_uuid=str(att["attachment_uuid"]), actor_id=_dpo(seeded)
    )
    rows = await fetch_all(
        conn,
        """SELECT event_type, detail_json FROM audit_log
            WHERE event_type IN ('breach.attachment_added', 'breach.attachment_read')
              AND detail_json->>'attachment' = %s ORDER BY log_id""",
        (str(att["attachment_uuid"]),),
    )
    assert [r["event_type"] for r in rows] == ["breach.attachment_added", "breach.attachment_read"]
    assert rows[0]["detail_json"]["kind"] == "email"
    words = json.dumps([r["detail_json"] for r in rows])
    assert "Asha" not in words and ".eml" not in words


async def test_evidence_is_never_replaced_or_removed(conn: Any, seeded: dict[str, Any]) -> None:
    uuid = await _incident(conn, seeded)
    await _attach(conn, seeded, uuid)
    for sql in (
        "UPDATE breach_attachment SET kind = 'other'",
        "DELETE FROM breach_attachment",
    ):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            async with conn.transaction():
                await conn.execute(sql)


async def test_a_kind_it_does_not_know_and_a_closed_breach_are_refused(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _incident(conn, seeded)
    with pytest.raises(ValidationFailed):
        await _attach(conn, seeded, uuid, kind="video")
    await conn.execute("UPDATE breach SET status = 'closed' WHERE breach_uuid = %s", (uuid,))
    with pytest.raises(Conflict) as refused:
        await _attach(conn, seeded, uuid)
    assert refused.value.code == "breach_closed"
    with pytest.raises(Conflict):
        await service.require_open(conn, uuid)


async def test_a_file_is_read_only_within_its_own_breach(conn: Any, seeded: dict[str, Any]) -> None:
    first = await _incident(conn, seeded)
    second = await _incident(conn, seeded)
    [att] = (await _attach(conn, seeded, first))["attachments"]
    with pytest.raises(NotFound):
        await service.read_attachment(
            conn,
            breach_uuid=second,
            attachment_uuid=str(att["attachment_uuid"]),
            actor_id=_dpo(seeded),
        )
