"""`portal_address`: the one row holding the address portal links start with (0072)."""

from __future__ import annotations

from cmp.db.sql import Conn, Row, execute, fetch_one


async def current(conn: Conn) -> Row:
    row = await fetch_one(
        conn,
        """SELECT x.portal_url, x.updated_at, u.full_name AS updated_by_name
             FROM portal_address x
             LEFT JOIN auth_user u ON u.id = x.updated_by
            WHERE x.address_id = 1""",
    )
    assert row is not None, "portal_address has its one row from the migration"
    return row


async def set_address(conn: Conn, *, portal_url: str | None, actor_id: int) -> None:
    await execute(
        conn,
        """UPDATE portal_address
              SET portal_url = %s, updated_by = %s, updated_at = now()
            WHERE address_id = 1""",
        (portal_url, actor_id),
    )
