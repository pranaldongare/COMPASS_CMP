"""Legal holds: what may not be erased, and until when (S2-03).

A hold covers one asset, or everything about one person. It is placed once and
released once - the table's trigger refuses any other change - and the reason
is sealed like every reason the office writes.
"""

from __future__ import annotations

from typing import Any

from cmp.db.sql import Conn, fetch_all, fetch_one
from cmp.infrastructure.dkms import seal

Row = dict[str, Any]

_SELECT = """
  h.hold_id, h.hold_uuid, h.reason, h.placed_at, h.released_at,
  da.asset_uuid, da.source_asset_ref,
  su.uuid AS subject_uuid, su.full_name AS subject_name,
  pb.full_name AS placed_by_name, rb.full_name AS released_by_name
  FROM legal_hold h
  LEFT JOIN data_asset da ON da.asset_id = h.asset_id
  LEFT JOIN auth_user su  ON su.id = h.subject_user_id
  JOIN auth_user pb       ON pb.id = h.placed_by
  LEFT JOIN auth_user rb  ON rb.id = h.released_by
"""


async def place(
    conn: Conn,
    *,
    asset_id: int | None,
    subject_user_id: int | None,
    reason: str,
    placed_by: int,
) -> Row:
    sealed = await seal("legal_hold", {"reason": reason})
    row = await fetch_one(
        conn,
        """INSERT INTO legal_hold (asset_id, subject_user_id, reason, placed_by)
           VALUES (%s, %s, %s, %s) RETURNING hold_id, hold_uuid""",
        (asset_id, subject_user_id, sealed["reason"], placed_by),
    )
    assert row is not None
    held = await by_uuid(conn, str(row["hold_uuid"]))
    assert held is not None
    return held


async def release(conn: Conn, hold_id: int, *, released_by: int) -> None:
    await conn.execute(
        """UPDATE legal_hold SET released_at = clock_timestamp(), released_by = %s
            WHERE hold_id = %s AND released_at IS NULL""",
        (released_by, hold_id),
    )


async def by_uuid(conn: Conn, hold_uuid: str) -> Row | None:
    return await fetch_one(conn, f"SELECT {_SELECT} WHERE h.hold_uuid = %s", (hold_uuid,))


async def list_holds(conn: Conn, *, active_only: bool) -> list[Row]:
    where = "WHERE h.released_at IS NULL" if active_only else ""
    return await fetch_all(conn, f"SELECT {_SELECT} {where} ORDER BY h.placed_at DESC LIMIT 500")


async def active_covering(
    conn: Conn, *, asset_id: int | None, subject_user_id: int | None
) -> Row | None:
    """The hold that stops erasing this asset or this person, if there is one."""
    return await fetch_one(
        conn,
        """SELECT hold_id, hold_uuid, asset_id, subject_user_id
             FROM legal_hold
            WHERE released_at IS NULL
              AND ((%s::int IS NOT NULL AND asset_id = %s)
                OR (%s::int IS NOT NULL AND subject_user_id = %s))
            ORDER BY placed_at LIMIT 1""",
        (asset_id, asset_id, subject_user_id, subject_user_id),
    )
