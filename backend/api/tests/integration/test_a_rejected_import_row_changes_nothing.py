"""A rejected manifest row leaves no trace (review 2026-10-01, SCALE-3).

Each row was ingested by writing its collection first and checking its
consent reference after. A row whose consent did not exist was reported
rejected - and its collection stayed: a new one, or an existing one with its
declared count altered by a row the platform said it had refused. Each row now
runs in a savepoint and a rejected row is rolled back whole.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from cmp.domain.exchange import service

pytestmark = pytest.mark.integration


async def _source(conn: Any, seeded: dict[str, Any]) -> str:
    row = await (
        await conn.execute(
            """INSERT INTO data_source (source_code, name, source_role, exchange_mode, processor_id)
               VALUES ('SRC-SCALE3', 'Rig', 'collection', 'file_import', %s)
               RETURNING source_uuid""",
            (seeded["processors"]["external"]["processor_id"],),
        )
    ).fetchone()
    return str(row["source_uuid"])


def _manifest(*rows: tuple[str, str, str, str, str]) -> bytes:
    today = datetime.now(UTC).date().isoformat()
    lines = [
        "source_collection_ref,source_asset_ref,asset_type,collected_on,subject_role,"
        "consent_uuid,declared_asset_count"
    ]
    lines += [
        f"{c},{a},image,{today},{role},{consent},{count}" for c, a, role, consent, count in rows
    ]
    return ("\n".join(lines) + "\n").encode()


async def _collection(conn: Any, ref: str) -> dict[str, Any] | None:
    return await (
        await conn.execute(
            "SELECT declared_asset_count FROM collection WHERE source_collection_ref = %s", (ref,)
        )
    ).fetchone()


async def test_a_rejected_row_leaves_no_collection_and_alters_none(
    conn: Any, seeded: dict[str, Any]
) -> None:
    source = await _source(conn, seeded)
    nobody = str(uuid4())
    result = await service.import_manifest(
        conn,
        source_uuid=source,
        project_uuid=str(seeded["project"]["project_uuid"]),
        file_name="m.csv",
        raw=_manifest(
            ("RUN-OK-S3", "IMG_1", "incidental", "", "1"),
            # Refused: the consent does not exist. Its collection is new.
            ("RUN-BAD-S3", "IMG_2", "consented", nobody, "5"),
            # Refused too, on the collection the first row made: its count stays.
            ("RUN-OK-S3", "IMG_3", "consented", nobody, "99"),
        ),
        actor_id=int(seeded["users"]["dpo"]["id"]),
        role="dpo",
    )
    assert (result["accepted_rows"], result["rejected_rows"], result["status"]) == (1, 2, "partial")
    assert await _collection(conn, "RUN-BAD-S3") is None, "a refused row made a collection"
    kept = await _collection(conn, "RUN-OK-S3")
    assert kept is not None and kept["declared_asset_count"] == 1
    assets = await (
        await conn.execute(
            "SELECT source_asset_ref FROM data_asset WHERE source_asset_ref LIKE 'IMG_%%' "
            "AND collection_id IN (SELECT collection_id FROM collection "
            "WHERE source_collection_ref = 'RUN-OK-S3')"
        )
    ).fetchall()
    assert [a["source_asset_ref"] for a in assets] == ["IMG_1"]
