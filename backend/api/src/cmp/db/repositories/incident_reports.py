"""Incidents reported through the public link, and how the office is set up to
hear of them (0058).

A report is written once and its outcome once, by trigger, and a dismissed
report's reporter may be erased once more, under a rights request (0065). It
belongs to no office, so every reader here is one the caller's role has already
been let through to: the two officers, on the shared intake or on a request.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from cmp.db.repositories.breaches import LOGGED_TEXT
from cmp.db.sql import Conn, fetch_all, fetch_one
from cmp.infrastructure.dkms import seal
from cmp.infrastructure.dkms.blind import index_of

Row = dict[str, Any]

_COLUMNS = f"""
  r.report_id, r.report_uuid, r.reference, r.reporter_name, r.reporter_email, r.title,
  r.noticed_at, {", ".join("r." + c for c in LOGGED_TEXT)}, r.cyber_attack, r.received_at,
  r.breach_id, r.claimed_at, r.dismissed_at, r.reporter_erased_at
"""


async def create(
    conn: Conn,
    *,
    reporter_name: str,
    reporter_email: str,
    title: str,
    noticed_at: datetime | None,
    told: dict[str, str | None],
    cyber_attack: str | None,
) -> Row:
    """The report, with its INC number: the same sequence the console's
    incidents draw on, so no two share one. The address's blind index is
    computed from the plaintext in the same statement, so a rights request can
    find the report without opening it (0065)."""
    sealed = await seal(
        "incident_report",
        {
            "reporter_name": reporter_name,
            "reporter_email": reporter_email,
            "title": title,
            **{c: told.get(c) for c in LOGGED_TEXT},
        },
    )
    columns = ", ".join(LOGGED_TEXT)
    marks = ", ".join(["%s"] * len(LOGGED_TEXT))
    row = await fetch_one(
        conn,
        f"""INSERT INTO incident_report
              (reference, reporter_name, reporter_email, reporter_email_hash, title, noticed_at,
               {columns}, cyber_attack)
            VALUES ('INC-' || to_char(now(), 'YYYY') || '-'
                      || cmp_next_number('breach_incident_ref_seq'),
                    %s, %s, %s, %s, %s, {marks}, %s)
            RETURNING report_id, report_uuid, reference, reporter_name, reporter_email,
                      received_at""",
        (
            sealed["reporter_name"],
            sealed["reporter_email"],
            index_of("email", reporter_email),
            sealed["title"],
            noticed_at,
            *(sealed[c] for c in LOGGED_TEXT),
            cyber_attack,
        ),
    )
    assert row is not None
    return row


async def waiting(conn: Conn, *, limit: int, offset: int) -> list[Row]:
    """A page of the reports no office has taken up, oldest first: the oldest
    has waited longest. Who sent each and its title, and none of the long text,
    which is read a report at a time: a stranger can write as much as they like,
    and this is read by both offices every minute."""
    return await fetch_all(
        conn,
        """SELECT r.report_uuid, r.reference, r.reporter_name, r.reporter_email, r.title,
                  r.noticed_at, r.received_at, r.cyber_attack
             FROM incident_report r
            WHERE r.claimed_at IS NULL AND r.dismissed_at IS NULL
            ORDER BY r.received_at, r.report_id
            LIMIT %s OFFSET %s""",
        (limit, offset),
    )


async def count_waiting(conn: Conn) -> int:
    row = await fetch_one(
        conn,
        """SELECT count(*) AS n FROM incident_report
            WHERE claimed_at IS NULL AND dismissed_at IS NULL""",
    )
    return int(row["n"]) if row else 0


async def dismissed(conn: Conn, *, limit: int) -> list[Row]:
    """The reports an office dismissed, latest first, with who did it and why,
    and when their reporter was erased. Not under which request, or by whom:
    the request is an office's, and this list is both offices'."""
    return await fetch_all(
        conn,
        """SELECT r.reference, r.reporter_name, r.reporter_email, r.title, r.received_at,
                  r.dismissed_at, r.dismissal_reason, u.full_name AS dismissed_by_name,
                  r.reporter_erased_at
             FROM incident_report r JOIN auth_user u ON u.id = r.dismissed_by
            WHERE r.dismissed_at IS NOT NULL
            ORDER BY r.dismissed_at DESC, r.report_id DESC
            LIMIT %s""",
        (limit,),
    )


async def by_uuid(conn: Conn, report_uuid: str) -> Row | None:
    return await fetch_one(
        conn,
        f"SELECT {_COLUMNS} FROM incident_report r WHERE r.report_uuid = %s",
        (report_uuid,),
    )


async def locked(conn: Conn, report_uuid: str) -> Row | None:
    """A report, held for the rest of the transaction: two officers acting on
    one at once act one after the other, and the second sees the first."""
    return await fetch_one(
        conn,
        f"SELECT {_COLUMNS} FROM incident_report r WHERE r.report_uuid = %s FOR UPDATE",
        (report_uuid,),
    )


async def for_breach(conn: Conn, breach_id: int) -> Row | None:
    """The report an incident came from, if it came from one."""
    return await fetch_one(
        conn,
        f"SELECT {_COLUMNS} FROM incident_report r WHERE r.breach_id = %s",
        (breach_id,),
    )


async def set_claimed(conn: Conn, report_id: int, *, breach_id: int, claimed_by: int) -> None:
    await conn.execute(
        """UPDATE incident_report SET breach_id = %s, claimed_by = %s, claimed_at = now()
            WHERE report_id = %s""",
        (breach_id, claimed_by, report_id),
    )


async def set_dismissed(conn: Conn, report_id: int, *, reason: str, dismissed_by: int) -> None:
    sealed = await seal("incident_report", {"dismissal_reason": reason})
    await conn.execute(
        """UPDATE incident_report
              SET dismissal_reason = %s, dismissed_by = %s, dismissed_at = now()
            WHERE report_id = %s""",
        (sealed["dismissal_reason"], dismissed_by, report_id),
    )


# ------------------------------------------------------- a reporter's rights
#
# A dismissed report is found by the blind index of the address it came from,
# never by the address: nothing here compares or opens a sealed value.

#: Dismissed, and its reporter not erased: the reports a rights request reaches.
_REACHED = "r.dismissed_at IS NOT NULL AND r.reporter_erased_at IS NULL"


async def found_for(conn: Conn, email_hashes: list[str], *, limit: int | None) -> list[Row]:
    """The dismissed reports still naming whoever holds one of these
    addresses, oldest first. A waiting or claimed report is never among them."""
    return await fetch_all(
        conn,
        f"""SELECT {_COLUMNS} FROM incident_report r
             WHERE {_REACHED} AND r.reporter_email_hash = ANY(%s)
             ORDER BY r.received_at, r.report_id"""
        + (" LIMIT %s" if limit is not None else ""),
        (email_hashes, limit) if limit is not None else (email_hashes,),
    )


async def erased_under(conn: Conn, request_id: int) -> list[Row]:
    """The reports whose reporter was erased under this request, oldest first:
    how a request still shows what it erased once the index has gone. Their
    name and email come back NULL."""
    return await fetch_all(
        conn,
        """SELECT r.report_id, r.report_uuid, r.reference, r.title, r.received_at,
                  r.dismissed_at, r.reporter_erased_at, r.reporter_name, r.reporter_email
             FROM incident_report r
            WHERE r.reporter_erased_request_id = %s
            ORDER BY r.received_at, r.report_id""",
        (request_id,),
    )


async def erase_reporters(
    conn: Conn, email_hashes: list[str], *, request_id: int, erased_by: int
) -> list[Row]:
    """Blank the name, the address and its index on every dismissed report
    still naming these addresses, in one statement: of two officers erasing at
    once, the second waits on the rows, finds them erased, and blanks none. The
    trigger allows this write once and nothing else with it."""
    return await fetch_all(
        conn,
        f"""UPDATE incident_report r
               SET reporter_name = NULL, reporter_email = NULL, reporter_email_hash = NULL,
                   reporter_erased_at = now(), reporter_erased_by = %s,
                   reporter_erased_request_id = %s
             WHERE {_REACHED} AND r.reporter_email_hash = ANY(%s)
         RETURNING r.report_id, r.reference""",
        (erased_by, request_id, email_hashes),
    )


async def reporter_address(conn: Conn, email_hash: str) -> str | None:
    """The address a dismissed report came from, sealed, for a code to a
    reporter with no account: the stored one, never the one typed. The latest
    report's, which is as proved as any."""
    row = await fetch_one(
        conn,
        f"""SELECT r.reporter_email FROM incident_report r
             WHERE {_REACHED} AND r.reporter_email_hash = %s
             ORDER BY r.report_id DESC LIMIT 1""",
        (email_hash,),
    )
    return str(row["reporter_email"]) if row else None


# ------------------------------------------------------------------- settings


async def settings(conn: Conn) -> Row:
    row = await fetch_one(
        conn, "SELECT intake_roles, updated_at FROM breach_settings WHERE settings_id = 1"
    )
    assert row is not None
    return row


async def set_intake_roles(conn: Conn, roles: list[str], *, updated_by: int) -> None:
    await conn.execute(
        """UPDATE breach_settings SET intake_roles = %s, updated_by = %s, updated_at = now()
            WHERE settings_id = 1""",
        (roles, updated_by),
    )


async def active_emails(conn: Conn, roles: list[str]) -> list[str]:
    """Where to tell these roles something, each address once. Sealed."""
    rows = await fetch_all(
        conn,
        """SELECT DISTINCT ON (u.email_hash) u.email FROM auth_user u
            WHERE u.role::text = ANY(%s) AND u.status = 'active' AND u.email IS NOT NULL
            ORDER BY u.email_hash""",
        (roles,),
    )
    return [str(r["email"]) for r in rows]


_RECIPIENT = """
  x.recipient_id, x.recipient_uuid, x.full_name, x.email, x.email_hash, x.added_at,
  x.mandatory, x.one_off, u.full_name AS added_by_name,
  m.recorded_at AS mandatory_changed_at, mu.full_name AS mandatory_changed_by_name
  FROM breach_board_recipient x JOIN auth_user u ON u.id = x.added_by
  LEFT JOIN LATERAL (
         SELECT e.recorded_at, e.recorded_by FROM breach_board_recipient_event e
          WHERE e.recipient_id = x.recipient_id
          ORDER BY e.event_id DESC LIMIT 1
       ) m ON true
  LEFT JOIN auth_user mu ON mu.id = m.recorded_by
"""

#: On the list: not taken off, and not an address added for one report alone.
_LISTED = "x.removed_at IS NULL AND NOT x.one_off"


async def board_recipients(conn: Conn, *, lock: bool = False) -> list[Row]:
    """The organisation's board as it stands, in the order they were added, and
    who last marked each mandatory or optional, and when. `lock` holds the rows
    for a finalise: a mark or a removal waits for it, so a report is judged
    against the list it read. The lock is on the list's rows, never on the
    side of a join that may be empty."""
    return await fetch_all(
        conn,
        f"SELECT {_RECIPIENT} WHERE {_LISTED} ORDER BY x.recipient_id"
        + (" FOR SHARE OF x" if lock else ""),
    )


async def board_recipient(conn: Conn, recipient_uuid: str, *, lock: bool) -> Row | None:
    """One entry on the list, or None: one taken off, or one added for one
    report alone, is not on it. Held for the change the caller makes."""
    return await fetch_one(
        conn,
        f"SELECT {_RECIPIENT} WHERE x.recipient_uuid = %s AND {_LISTED}"
        + (" FOR UPDATE OF x" if lock else ""),
        (recipient_uuid,),
    )


async def add_board_recipient(
    conn: Conn, *, full_name: str | None, email: str, added_by: int
) -> Row | None:
    """The new entry, or None if the address is on the list already. The
    conflict's predicate is the index's, or the insert raises instead."""
    sealed = await seal("breach_board_recipient", {"full_name": full_name, "email": email})
    return await fetch_one(
        conn,
        """INSERT INTO breach_board_recipient (full_name, email, email_hash, added_by)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT (email_hash) WHERE removed_at IS NULL AND NOT one_off DO NOTHING
           RETURNING recipient_id, recipient_uuid, full_name, email""",
        (sealed["full_name"], sealed["email"], index_of("email", email), added_by),
    )


async def add_one_off_recipient(
    conn: Conn, *, full_name: str | None, email: str, added_by: int
) -> Row:
    """An address added by the sender for one report alone: sealed as an entry
    on the list is, and never on it."""
    sealed = await seal("breach_board_recipient", {"full_name": full_name, "email": email})
    row = await fetch_one(
        conn,
        """INSERT INTO breach_board_recipient (full_name, email, email_hash, added_by, one_off)
           VALUES (%s, %s, %s, %s, true)
           RETURNING recipient_id, recipient_uuid, full_name, email, email_hash, mandatory,
                     one_off""",
        (sealed["full_name"], sealed["email"], index_of("email", email), added_by),
    )
    assert row is not None
    return row


async def remove_board_recipient(conn: Conn, recipient_uuid: str, *, removed_by: int) -> Row | None:
    return await fetch_one(
        conn,
        """UPDATE breach_board_recipient SET removed_by = %s, removed_at = now()
            WHERE recipient_uuid = %s AND removed_at IS NULL AND NOT one_off AND NOT mandatory
            RETURNING recipient_uuid""",
        (removed_by, recipient_uuid),
    )


async def mark_board_recipient(
    conn: Conn, recipient_id: int, *, mandatory: bool, recorded_by: int
) -> None:
    """The event first, then the mark: the row refuses a mark no event records."""
    await conn.execute(
        """INSERT INTO breach_board_recipient_event (recipient_id, kind, recorded_by)
           VALUES (%s, %s, %s)""",
        (recipient_id, "mandatory" if mandatory else "optional", recorded_by),
    )
    await conn.execute(
        "UPDATE breach_board_recipient SET mandatory = %s WHERE recipient_id = %s",
        (mandatory, recipient_id),
    )
