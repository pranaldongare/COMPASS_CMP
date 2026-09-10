"""message_template.

One row per (junction, channel) whose words the office replaced. Reads and
writes only; what a template may say is decided in `cmp.core.messages`, and
who may change one in the permission matrix.
"""

from __future__ import annotations

from cmp.db.sql import Conn, Row, fetch_all, fetch_one

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
