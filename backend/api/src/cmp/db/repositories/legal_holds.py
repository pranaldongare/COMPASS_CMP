"""Legal holds: what may not be erased, and until when (S2-03).

A hold covers one asset, or everything about one person. It is placed once and
released once - the table's trigger refuses any other change - and the reason
is sealed like every reason the office writes.

A hold is an office's (0055): each lists and releases its own. What it stops
is not: `active_covering` reads both offices' holds, so a hold on a person
stops the other office erasing her too.
"""

from __future__ import annotations

from typing import Any

from cmp.core.offices import OFFICE_ID
from cmp.db.pool import across_offices
from cmp.db.sql import Conn, fetch_all, fetch_one
from cmp.infrastructure.dkms import seal

Row = dict[str, Any]

_SELECT = """
  h.hold_id, h.hold_uuid, h.reason, h.placed_at, h.released_at,
  (SELECT o.office_code FROM office o WHERE o.office_id = h.office_id) AS office_code,
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
    office: str,
) -> Row:
    sealed = await seal("legal_hold", {"reason": reason})
    row = await fetch_one(
        conn,
        f"""INSERT INTO legal_hold (asset_id, subject_user_id, reason, placed_by, office_id)
            VALUES (%s, %s, %s, %s, {OFFICE_ID}) RETURNING hold_id, hold_uuid""",
        (asset_id, subject_user_id, sealed["reason"], placed_by, office),
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
    """A hold of the session's office; the other office's is not there."""
    return await fetch_one(
        conn,
        f"SELECT {_SELECT} WHERE h.hold_uuid = %s AND cmp_office_visible(h.office_id)",
        (hold_uuid,),
    )


async def list_holds(conn: Conn, *, active_only: bool) -> list[Row]:
    where = "WHERE cmp_office_visible(h.office_id)" + (
        " AND h.released_at IS NULL" if active_only else ""
    )
    return await fetch_all(conn, f"SELECT {_SELECT} {where} ORDER BY h.placed_at DESC LIMIT 500")


async def active_covering(
    conn: Conn, *, asset_id: int | None, subject_user_id: int | None
) -> Row | None:
    """The hold that stops erasing this asset or this person, if there is one -
    whichever office placed it."""
    async with across_offices(conn):
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


async def asset_by_uuid(conn: Conn, asset_uuid: str) -> Row | None:
    """An asset of the session's office, with that office: a hold on it is
    its project's office's."""
    return await fetch_one(
        conn,
        """SELECT da.asset_id, o.office_code
             FROM data_asset da
             JOIN collection c ON c.collection_id = da.collection_id
             JOIN project p    ON p.project_id = c.project_id
             JOIN office o     ON o.office_id = p.office_id
            WHERE da.asset_uuid = %s AND cmp_office_visible(p.office_id)""",
        (asset_uuid,),
    )


async def what_it_covers(conn: Conn, hold_id: int) -> Row | None:
    """The asset or the person a hold covers - the ids, which the public row hides."""
    return await fetch_one(
        conn,
        "SELECT asset_id, subject_user_id FROM legal_hold WHERE hold_id = %s",
        (hold_id,),
    )
