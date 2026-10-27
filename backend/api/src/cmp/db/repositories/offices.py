"""office: the two governance offices (ADR 0032).

Not policed: every session reads the list, which is what the administrator's
picker and the request context are built from. What an office holds is the
policed part.
"""

from __future__ import annotations

from cmp.db.sql import Conn, Row, fetch_all, fetch_one

_COLUMNS = "office_id, office_uuid, office_code, name"


async def list_offices(conn: Conn) -> list[Row]:
    return await fetch_all(conn, f"SELECT {_COLUMNS} FROM office ORDER BY office_id")


async def by_uuid(conn: Conn, office_uuid: str) -> Row | None:
    return await fetch_one(
        conn, f"SELECT {_COLUMNS} FROM office WHERE office_uuid = %s", (office_uuid,)
    )


async def by_code(conn: Conn, office_code: str) -> Row | None:
    return await fetch_one(
        conn, f"SELECT {_COLUMNS} FROM office WHERE office_code = %s", (office_code,)
    )
