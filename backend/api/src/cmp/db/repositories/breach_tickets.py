"""Breach tickets (S3-08): the ticket, what happened to it, and its thread.

The ticket row changes only its two read markers, by trigger; its events and
its thread are append-only by trigger and grant. A ticket's state is read by
folding its events (`cmp.domain.breach.tickets.fold`), never stored.

Every word a person writes is sealed here, at the write. The holder's reads are
scoped OWN in the WHERE clause - `holder_user_id = %s` - so another person's
ticket is not found, and the router answers 404.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from cmp.db.sql import Conn, fetch_all, fetch_one
from cmp.infrastructure.dkms import seal

Row = dict[str, Any]

_COLUMNS = """
  t.ticket_id, t.ticket_uuid, t.breach_id, t.holder_user_id, t.parent_ticket_id,
  t.instruction, t.answer_by, t.created_at, t.office_read_at, t.holder_read_at,
  b.breach_uuid, b.status AS breach_status,
  coalesce(rec.reference, b.reference) AS breach_reference,
  hu.uuid AS holder_uuid, hu.full_name AS holder_name, hu.email AS holder_email,
  hu.role::text AS holder_role, hu.status::text AS holder_status,
  ab.full_name AS assigned_by_name,
  pt.ticket_uuid AS parent_ticket_uuid, pu.full_name AS added_by_name,
  (SELECT max(m.created_at) FROM breach_ticket_message m WHERE m.ticket_id = t.ticket_id)
    AS last_activity_at"""

_FROM = """
  FROM breach_ticket t
  JOIN breach b                  ON b.breach_id = t.breach_id
  LEFT JOIN breach_recording rec ON rec.breach_id = b.breach_id
  JOIN auth_user hu              ON hu.id = t.holder_user_id
  JOIN auth_user ab              ON ab.id = t.assigned_by
  LEFT JOIN breach_ticket pt     ON pt.ticket_id = t.parent_ticket_id
  LEFT JOIN auth_user pu         ON pu.id = pt.holder_user_id"""


def _select(side: str) -> str:
    """The ticket as one side reads it, with how many of the other side's
    messages that side has not read. Reads are stamped with clock_timestamp(),
    so a message written in the same transaction as a read is not unread
    forever."""
    marker = "office_read_at" if side == "office" else "holder_read_at"
    unread = f"""(SELECT count(*) FROM breach_ticket_message m
                   WHERE m.ticket_id = t.ticket_id AND m.author_side <> '{side}'
                     AND (t.{marker} IS NULL OR m.created_at > t.{marker})) AS unread"""
    return f"{_COLUMNS}, {unread} {_FROM}"


async def create(
    conn: Conn,
    *,
    breach_id: int,
    holder_user_id: int,
    assigned_by: int,
    instruction: str,
    answer_by: date | None,
    parent_ticket_id: int | None = None,
) -> Row | None:
    """The ticket, or None if this person already holds one on this breach.

    The caller holds the breach row, so the check before this sees a ticket a
    concurrent assignment wrote; `ON CONFLICT` is the second line.
    """
    sealed = await seal("breach_ticket", {"instruction": instruction})
    return await fetch_one(
        conn,
        """INSERT INTO breach_ticket
             (breach_id, holder_user_id, assigned_by, parent_ticket_id, instruction, answer_by)
           VALUES (%s, %s, %s, %s, %s, %s)
           ON CONFLICT (breach_id, holder_user_id) DO NOTHING
           RETURNING ticket_id, ticket_uuid""",
        (
            breach_id,
            holder_user_id,
            assigned_by,
            parent_ticket_id,
            sealed["instruction"],
            answer_by,
        ),
    )


async def held_by(conn: Conn, breach_id: int, user_id: int) -> Row | None:
    return await fetch_one(
        conn,
        "SELECT ticket_id FROM breach_ticket WHERE breach_id = %s AND holder_user_id = %s",
        (breach_id, user_id),
    )


async def for_breach(conn: Conn, breach_id: int) -> list[Row]:
    """Every ticket on a breach, as the office reads them, oldest first."""
    return await fetch_all(
        conn,
        f"SELECT {_select('office')} WHERE t.breach_id = %s ORDER BY t.ticket_id",
        (breach_id,),
    )


async def on_breach(conn: Conn, breach_id: int, ticket_uuid: str) -> Row | None:
    """One ticket, within this breach only."""
    return await fetch_one(
        conn,
        f"SELECT {_select('office')} WHERE t.breach_id = %s AND t.ticket_uuid = %s",
        (breach_id, ticket_uuid),
    )


async def for_holder(conn: Conn, user_id: int) -> list[Row]:
    """Every ticket addressed to this account: OWN, in the predicate."""
    return await fetch_all(
        conn,
        f"SELECT {_select('holder')} WHERE t.holder_user_id = %s ORDER BY t.ticket_id DESC",
        (user_id,),
    )


async def mine(conn: Conn, user_id: int, ticket_uuid: str) -> Row | None:
    """One ticket, if it is addressed to this account; otherwise nothing."""
    return await fetch_one(
        conn,
        f"SELECT {_select('holder')} WHERE t.holder_user_id = %s AND t.ticket_uuid = %s",
        (user_id, ticket_uuid),
    )


async def mark_read(conn: Conn, ticket_id: int, *, side: str) -> None:
    column = "office_read_at" if side == "office" else "holder_read_at"
    await conn.execute(
        f"UPDATE breach_ticket SET {column} = clock_timestamp() WHERE ticket_id = %s",
        (ticket_id,),
    )


# ---------------------------------------------------------------- events


async def add_event(
    conn: Conn,
    ticket_id: int,
    *,
    kind: str,
    actor_user_id: int,
    outcome: str | None = None,
    summary: str | None = None,
    reason: str | None = None,
) -> Row:
    sealed = await seal("breach_ticket_event", {"summary": summary, "reason": reason})
    row = await fetch_one(
        conn,
        """INSERT INTO breach_ticket_event
             (ticket_id, kind, outcome, summary, reason, actor_user_id)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING event_uuid""",
        (ticket_id, kind, outcome, sealed["summary"], sealed["reason"], actor_user_id),
    )
    assert row is not None
    return row


async def events_for(conn: Conn, ticket_ids: list[int]) -> list[Row]:
    """Every event on these tickets, in the order written."""
    return await fetch_all(
        conn,
        """SELECT e.ticket_id, e.event_uuid, e.kind, e.outcome, e.summary, e.reason,
                  e.occurred_at, u.full_name AS actor_name
             FROM breach_ticket_event e JOIN auth_user u ON u.id = e.actor_user_id
            WHERE e.ticket_id = ANY(%s) ORDER BY e.event_id""",
        (ticket_ids,),
    )


# ---------------------------------------------------------------- the thread

_MESSAGE = """
  m.message_id, m.message_uuid, m.ticket_id, m.author_user_id, m.author_side, m.kind,
  m.body, m.evidence_ref, m.evidence_hash, m.evidence_name, m.created_at,
  a.full_name AS author_name
  FROM breach_ticket_message m
  LEFT JOIN auth_user a ON a.id = m.author_user_id
"""


async def add_message(
    conn: Conn,
    ticket_id: int,
    *,
    side: str,
    kind: str,
    body: str,
    author_user_id: int | None,
    evidence_ref: str | None = None,
    evidence_hash: str | None = None,
    evidence_name: str | None = None,
) -> Row:
    sealed = await seal("breach_ticket_message", {"body": body, "evidence_name": evidence_name})
    row = await fetch_one(
        conn,
        # clock_timestamp(), like the read markers: two messages and a read in
        # one transaction keep their order, so nothing is unread for ever.
        """INSERT INTO breach_ticket_message
             (ticket_id, author_user_id, author_side, kind, body,
              evidence_ref, evidence_hash, evidence_name, created_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, clock_timestamp())
           RETURNING message_uuid""",
        (
            ticket_id,
            author_user_id,
            side,
            kind,
            sealed["body"],
            evidence_ref,
            evidence_hash,
            sealed["evidence_name"],
        ),
    )
    assert row is not None
    return row


async def messages_of(conn: Conn, ticket_id: int) -> list[Row]:
    return await fetch_all(
        conn, f"SELECT {_MESSAGE} WHERE m.ticket_id = %s ORDER BY m.message_id", (ticket_id,)
    )


async def message_by_uuid(conn: Conn, ticket_id: int, message_uuid: str) -> Row | None:
    return await fetch_one(
        conn,
        f"SELECT {_MESSAGE} WHERE m.ticket_id = %s AND m.message_uuid = %s",
        (ticket_id, message_uuid),
    )


# ---------------------------------------------------------------- counts


async def ids_on(conn: Conn, breach_id: int) -> list[int]:
    rows = await fetch_all(
        conn, "SELECT ticket_id FROM breach_ticket WHERE breach_id = %s", (breach_id,)
    )
    return [int(r["ticket_id"]) for r in rows]


async def on_open_breaches(conn: Conn) -> list[Row]:
    """Every ticket on an open breach, with its events' kinds in order, for the
    DPO's dashboard counts."""
    return await fetch_all(
        conn,
        """SELECT t.ticket_id, t.answer_by,
                  coalesce(array_agg(e.kind ORDER BY e.event_id)
                           FILTER (WHERE e.event_id IS NOT NULL), '{}') AS kinds
             FROM breach_ticket t
             JOIN breach b ON b.breach_id = t.breach_id AND b.status = 'open'
             LEFT JOIN breach_ticket_event e ON e.ticket_id = t.ticket_id
            GROUP BY t.ticket_id, t.answer_by""",
    )


# ------------------------------------------------- breach-only logins (S3-09)


async def open_grant(conn: Conn, breach_id: int, user_id: int) -> Row | None:
    return await fetch_one(
        conn,
        """SELECT * FROM breach_temporary_access
            WHERE breach_id = %s AND user_id = %s AND ended_at IS NULL""",
        (breach_id, user_id),
    )


async def open_grants_for_user(conn: Conn, user_id: int) -> list[Row]:
    """Every grant this person still holds, on any breach, oldest first."""
    return await fetch_all(
        conn,
        """SELECT a.*, coalesce(rec.reference, b.reference) AS breach_reference
             FROM breach_temporary_access a
             JOIN breach b ON b.breach_id = a.breach_id
             LEFT JOIN breach_recording rec ON rec.breach_id = b.breach_id
            WHERE a.user_id = %s AND a.ended_at IS NULL ORDER BY a.access_id""",
        (user_id,),
    )


async def open_grants_on(conn: Conn, breach_id: int) -> list[Row]:
    return await fetch_all(
        conn,
        """SELECT * FROM breach_temporary_access
            WHERE breach_id = %s AND ended_at IS NULL ORDER BY access_id""",
        (breach_id,),
    )


async def first_grant_of(conn: Conn, user_id: int) -> Row | None:
    """This person's first grant on any breach: what the account was before."""
    return await fetch_one(
        conn,
        """SELECT * FROM breach_temporary_access
            WHERE user_id = %s ORDER BY access_id LIMIT 1""",
        (user_id,),
    )


async def latest_grant(conn: Conn, breach_id: int, user_id: int) -> Row | None:
    return await fetch_one(
        conn,
        """SELECT * FROM breach_temporary_access
            WHERE breach_id = %s AND user_id = %s ORDER BY access_id DESC LIMIT 1""",
        (breach_id, user_id),
    )


async def add_grant(
    conn: Conn,
    *,
    breach_id: int,
    user_id: int,
    ticket_id: int,
    account_created: bool,
    previous_role: str | None,
    granted_by: int,
) -> Row | None:
    """The grant, or None if one is already open for this person on this
    breach - the partial unique index, behind the breach row's lock."""
    return await fetch_one(
        conn,
        """INSERT INTO breach_temporary_access
             (breach_id, user_id, ticket_id, account_created, previous_role, granted_by)
           VALUES (%s, %s, %s, %s, %s::user_role, %s)
           ON CONFLICT (breach_id, user_id) WHERE ended_at IS NULL DO NOTHING
           RETURNING access_id, access_uuid""",
        (breach_id, user_id, ticket_id, account_created, previous_role, granted_by),
    )


async def end_grant(conn: Conn, access_id: int, *, cause: str, ended_by: int | None) -> None:
    await conn.execute(
        """UPDATE breach_temporary_access
              SET ended_at = now(), end_cause = %s, ended_by = %s
            WHERE access_id = %s AND ended_at IS NULL""",
        (cause, ended_by, access_id),
    )


async def access_by_ticket(conn: Conn, ticket_ids: list[int]) -> list[Row]:
    """Each ticket's latest grant, for the office's list: who has a temporary
    login, and whether it is pending, active or ended."""
    return await fetch_all(
        conn,
        """SELECT DISTINCT ON (a.ticket_id) a.ticket_id, a.account_created, a.ended_at,
                  a.end_cause, u.status::text AS user_status
             FROM breach_temporary_access a JOIN auth_user u ON u.id = a.user_id
            WHERE a.ticket_id = ANY(%s)
            ORDER BY a.ticket_id, a.access_id DESC""",
        (ticket_ids,),
    )
