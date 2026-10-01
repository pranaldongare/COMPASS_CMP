"""Notices to the people a breach touched, and the account of each (S3-03).

A notice is a version of five things Rule 7(1) requires; a delivery is one
state of one attempt on one channel for one person. Deliveries are
append-only, and a person's state on a channel is her latest attempt's
outcome - or `queued` while that attempt has none yet.
"""

from __future__ import annotations

from typing import Any

from psycopg.types.json import Jsonb

from cmp.db.sql import Conn, fetch_all, fetch_one
from cmp.infrastructure.dkms import seal

Row = dict[str, Any]

#: Rule 7(1)(a) to (e), in the order the Rule lists them.
CONTENTS: tuple[str, ...] = (
    "what_happened",
    "consequences",
    "measures",
    "protective_steps",
    "contact",
)

_NOTICE = f"""
  n.notice_id, n.notice_uuid, n.breach_id, n.version, {", ".join("n." + c for c in CONTENTS)},
  n.created_at, n.updated_at, n.approved_at,
  cb.full_name AS created_by_name, ab.full_name AS approved_by_name
  FROM breach_notice n
  JOIN auth_user cb      ON cb.id = n.created_by
  LEFT JOIN auth_user ab ON ab.id = n.approved_by
"""


async def create_draft(
    conn: Conn, breach_id: int, *, words: dict[str, str | None], created_by: int
) -> Row:
    words = await seal("breach_notice", words)
    row = await fetch_one(
        conn,
        f"""INSERT INTO breach_notice (breach_id, version, {", ".join(CONTENTS)}, created_by)
            VALUES (%s, (SELECT coalesce(max(version), 0) + 1 FROM breach_notice
                          WHERE breach_id = %s),
                    {", ".join(["%s"] * len(CONTENTS))}, %s)
            RETURNING notice_id, notice_uuid""",
        (breach_id, breach_id, *(words[c] for c in CONTENTS), created_by),
    )
    assert row is not None
    return row


async def update_draft(conn: Conn, notice_id: int, *, words: dict[str, str | None]) -> None:
    words = await seal("breach_notice", words)
    await conn.execute(
        f"""UPDATE breach_notice SET {", ".join(f"{c} = %s" for c in CONTENTS)}, updated_at = now()
             WHERE notice_id = %s AND approved_at IS NULL""",
        (*(words[c] for c in CONTENTS), notice_id),
    )


async def approve(conn: Conn, notice_id: int, *, approved_by: int) -> None:
    await conn.execute(
        """UPDATE breach_notice SET approved_by = %s, approved_at = clock_timestamp()
            WHERE notice_id = %s AND approved_at IS NULL""",
        (approved_by, notice_id),
    )


async def by_uuid(conn: Conn, breach_id: int, notice_uuid: str) -> Row | None:
    return await fetch_one(
        conn,
        f"SELECT {_NOTICE} WHERE n.breach_id = %s AND n.notice_uuid = %s",
        (breach_id, notice_uuid),
    )


async def versions(conn: Conn, breach_id: int) -> list[Row]:
    return await fetch_all(
        conn, f"SELECT {_NOTICE} WHERE n.breach_id = %s ORDER BY n.version", (breach_id,)
    )


async def latest_approved(conn: Conn, breach_id: int) -> Row | None:
    return await fetch_one(
        conn,
        f"""SELECT {_NOTICE} WHERE n.breach_id = %s AND n.approved_at IS NOT NULL
            ORDER BY n.version DESC LIMIT 1""",
        (breach_id,),
    )


async def recipients(conn: Conn, breach_id: int) -> list[Row]:
    """Everyone listed as touched, with whether each can be written to."""
    return await fetch_all(
        conn,
        """SELECT a.auth_user_id AS person_id,
                  (u.email IS NOT NULL) AS has_email, (u.mobile IS NOT NULL) AS has_mobile
             FROM breach_affected a JOIN auth_user u ON u.id = a.auth_user_id
            WHERE a.breach_id = %s ORDER BY a.affected_id""",
        (breach_id,),
    )


_LATEST = """
  SELECT DISTINCT ON (d.notice_id, d.auth_user_id, d.channel)
         d.notice_id, d.auth_user_id, d.channel, d.attempt, d.status, d.detail, d.recorded_at
    FROM breach_notice_delivery d
    JOIN breach_notice n ON n.notice_id = d.notice_id
   WHERE n.breach_id = %(b)s
   -- The latest attempt; within it, an outcome over the queueing that preceded it.
   ORDER BY d.notice_id, d.auth_user_id, d.channel, d.attempt DESC, (d.status = 'queued')
"""


async def latest_states(conn: Conn, breach_id: int, notice_id: int) -> dict[tuple[int, str], Row]:
    rows = await fetch_all(
        conn,
        f"SELECT * FROM ({_LATEST}) s WHERE s.notice_id = %(n)s",
        {"b": breach_id, "n": notice_id},
    )
    return {(int(r["auth_user_id"]), str(r["channel"])): r for r in rows}


async def add_delivery(
    conn: Conn,
    notice_id: int,
    person_id: int,
    *,
    channel: str,
    attempt: int,
    status: str,
    detail: dict[str, Any] | None = None,
) -> Row | None:
    """One state of one attempt. None when that state is already recorded -
    another send, or a worker recording the same outcome twice, got there first."""
    return await fetch_one(
        conn,
        """INSERT INTO breach_notice_delivery
             (notice_id, auth_user_id, channel, attempt, status, detail)
           VALUES (%s, %s, %s, %s, %s, %s)
           ON CONFLICT ON CONSTRAINT breach_notice_delivery_once DO NOTHING
           RETURNING delivery_id, delivery_uuid""",
        (notice_id, person_id, channel, attempt, status, Jsonb(detail or {})),
    )


async def queued_delivery(
    conn: Conn, notice_id: int, person_id: int, *, channel: str, attempt: int
) -> Row | None:
    """The queued row of one attempt, to queue its task again."""
    return await fetch_one(
        conn,
        """SELECT delivery_uuid FROM breach_notice_delivery
            WHERE notice_id = %s AND auth_user_id = %s AND channel = %s
              AND attempt = %s AND status = 'queued'""",
        (notice_id, person_id, channel, attempt),
    )


async def job(conn: Conn, delivery_uuid: str) -> Row | None:
    """Everything the worker needs to send one queued delivery, and whether its
    attempt already has an outcome."""
    return await fetch_one(
        conn,
        f"""SELECT d.delivery_uuid, d.notice_id, d.auth_user_id, d.channel, d.attempt, d.status,
                   n.breach_id, b.reference, {", ".join("n." + c for c in CONTENTS)},
                   u.email, u.mobile,
                   EXISTS (SELECT 1 FROM breach_notice_delivery o
                            WHERE o.notice_id = d.notice_id AND o.auth_user_id = d.auth_user_id
                              AND o.channel = d.channel AND o.attempt = d.attempt
                              AND o.status <> 'queued') AS settled
              FROM breach_notice_delivery d
              JOIN breach_notice n ON n.notice_id = d.notice_id
              JOIN breach b        ON b.breach_id = n.breach_id
              JOIN auth_user u     ON u.id = d.auth_user_id
             WHERE d.delivery_uuid = %s""",
        (delivery_uuid,),
    )


async def unnotified(conn: Conn, breach_id: int) -> int:
    """Listed people who have no notice yet whose every channel has an outcome.

    A person is notified when some approved version reached a final state -
    delivered or failed after retrying - on every channel it went to. Her
    account is always one of them, delivered at the send.
    """
    row = await fetch_one(
        conn,
        f"""WITH latest AS ({_LATEST}),
                 done AS (
                   SELECT auth_user_id FROM latest
                    GROUP BY notice_id, auth_user_id
                   HAVING bool_and(status <> 'queued')
                 )
            SELECT count(*) AS n FROM breach_affected a
             WHERE a.breach_id = %(b)s
               AND a.auth_user_id NOT IN (SELECT auth_user_id FROM done)""",
        {"b": breach_id},
    )
    return int(row["n"]) if row else 0


async def account(conn: Conn, breach_id: int) -> list[Row]:
    """Per version and channel, how many people are in each state."""
    return await fetch_all(
        conn,
        f"""SELECT n.notice_uuid, n.version, s.channel, s.status, count(*) AS people,
                   max(s.recorded_at) AS last_at
              FROM ({_LATEST}) s JOIN breach_notice n ON n.notice_id = s.notice_id
             GROUP BY n.notice_uuid, n.version, s.channel, s.status
             ORDER BY n.version, s.channel, s.status""",
        {"b": breach_id},
    )


async def failures(conn: Conn, breach_id: int, *, limit: int = 200) -> list[Row]:
    """Deliveries whose latest attempt failed, with who and why."""
    return await fetch_all(
        conn,
        f"""SELECT n.version, s.channel, s.attempt, s.detail, s.recorded_at,
                   u.uuid AS person_uuid, u.full_name
              FROM ({_LATEST}) s
              JOIN breach_notice n ON n.notice_id = s.notice_id
              JOIN auth_user u     ON u.id = s.auth_user_id
             WHERE s.status = 'failed'
             ORDER BY n.version, u.id LIMIT {int(limit)}""",
        {"b": breach_id},
    )


async def for_person(conn: Conn, person_id: int) -> list[Row]:
    """The notices written to her account, newest first."""
    return await fetch_all(
        conn,
        f"""SELECT n.notice_uuid, n.version, {", ".join("n." + c for c in CONTENTS)},
                   b.reference, d.recorded_at AS delivered_at
              FROM breach_notice_delivery d
              JOIN breach_notice n ON n.notice_id = d.notice_id
              JOIN breach b        ON b.breach_id = n.breach_id
             WHERE d.auth_user_id = %s AND d.channel = 'portal'
             ORDER BY d.recorded_at DESC, n.version DESC""",
        (person_id,),
    )
