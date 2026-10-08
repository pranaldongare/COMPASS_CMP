"""message_template.

One row per (junction, channel) whose words the office replaced. Reads and
writes only; what a template may say is decided in `cmp.core.messages`, and
who may change one in the permission matrix.
"""

from __future__ import annotations

from cmp.db.sql import Conn, Row, execute, fetch_all, fetch_one
from cmp.infrastructure.dkms import seal_many
from cmp.infrastructure.dkms.blind import index_of

_SELECT = """
  t.template_id, t.key, t.channel, t.subject, t.body, t.updated_at,
  u.uuid AS updated_by_uuid, u.full_name AS updated_by_name
  FROM message_template t
  LEFT JOIN auth_user u ON u.id = t.updated_by
"""


async def list_all(conn: Conn) -> list[Row]:
    return await fetch_all(conn, f"SELECT {_SELECT} ORDER BY t.key, t.channel")


async def get(conn: Conn, *, key: str, channel: str) -> Row | None:
    return await fetch_one(
        conn, f"SELECT {_SELECT} WHERE t.key = %s AND t.channel = %s", (key, channel)
    )


async def upsert(
    conn: Conn, *, key: str, channel: str, subject: str | None, body: str, updated_by: int
) -> Row:
    row = await fetch_one(
        conn,
        """
        INSERT INTO message_template (key, channel, subject, body, updated_by)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (key, channel) DO UPDATE
          SET subject = EXCLUDED.subject, body = EXCLUDED.body,
              updated_by = EXCLUDED.updated_by, updated_at = now()
        RETURNING template_id
        """,
        (key, channel, subject, body, updated_by),
    )
    assert row is not None
    return row


async def delete(conn: Conn, *, key: str, channel: str) -> Row | None:
    return await fetch_one(
        conn,
        "DELETE FROM message_template WHERE key = %s AND channel = %s RETURNING template_id",
        (key, channel),
    )


# ------------------------------------------------- copies (0046, 2026-10-08)


async def copies(conn: Conn) -> list[Row]:
    """Every copy address, sealed, by message."""
    return await fetch_all(
        conn, "SELECT key, address, added_at FROM message_copy ORDER BY key, copy_id"
    )


async def replace_copies(conn: Conn, *, key: str, addresses: list[str], added_by: int) -> None:
    """The copy addresses of one message, as now set. Configuration: the old
    set is replaced."""
    await execute(conn, "DELETE FROM message_copy WHERE key = %s", (key,))
    if not addresses:
        return
    sealed = await seal_many("message_copy", [{"address": a} for a in addresses])
    for plain, closed in zip(addresses, sealed, strict=True):
        await execute(
            conn,
            """INSERT INTO message_copy (key, address, address_hash, added_by)
               VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING""",
            (key, closed["address"], index_of("email", plain), added_by),
        )
