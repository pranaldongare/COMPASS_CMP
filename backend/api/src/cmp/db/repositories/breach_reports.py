"""The reports written about a breach (0059).

A report is a version and its sections. A draft's words may be rewritten;
finalising freezes both, by trigger, and filing is written once after that.
Each version has its addressed set, written before it is frozen (0064): who
the sender chose to send it to. The deliveries are append-only, shaped like a
notice's, and each names one of its report's addressees. Every word is sealed
here, at the write, and the rows served carry ciphertext the console opens.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from psycopg.types.json import Jsonb

from cmp.db.sql import Conn, fetch_all, fetch_one
from cmp.infrastructure.dkms import seal_many

Row = dict[str, Any]

_REPORT = """
  r.report_id, r.report_uuid, r.breach_id, r.kind, r.version, r.created_at, r.updated_at,
  r.finalised_at, r.filed_at, r.filed_reference, r.filed_recorded_at, r.filed_by,
  cu.full_name AS created_by_name, fu.full_name AS finalised_by_name, fu.role AS finalised_by_role,
  su.full_name AS filed_by_name
  FROM breach_report r
  JOIN auth_user cu      ON cu.id = r.created_by
  LEFT JOIN auth_user fu ON fu.id = r.finalised_by
  LEFT JOIN auth_user su ON su.id = r.filed_by
"""


async def create(
    conn: Conn, breach_id: int, *, kind: str, sections: list[Row], created_by: int
) -> Row:
    """The next version, as a draft. The breach row is held by the caller, so
    the number cannot be drawn twice."""
    row = await fetch_one(
        conn,
        """INSERT INTO breach_report (breach_id, kind, version, created_by)
           VALUES (%s, %s,
                   (SELECT coalesce(max(version), 0) + 1 FROM breach_report
                     WHERE breach_id = %s AND kind = %s),
                   %s)
           RETURNING report_id, report_uuid, version""",
        (breach_id, kind, breach_id, kind, created_by),
    )
    assert row is not None
    sealed = await seal_many(
        "breach_report_section", [{"body": s.get("body") or None} for s in sections]
    )
    for ordinal, (section, closed) in enumerate(zip(sections, sealed, strict=True)):
        await conn.execute(
            """INSERT INTO breach_report_section (report_id, ordinal, section_key, body)
               VALUES (%s, %s, %s, %s)""",
            (int(row["report_id"]), ordinal, section["key"], closed["body"]),
        )
    return row


async def by_uuid(conn: Conn, breach_id: int, report_uuid: str) -> Row | None:
    """One report, within this breach only."""
    return await fetch_one(
        conn,
        f"SELECT {_REPORT} WHERE r.breach_id = %s AND r.report_uuid = %s",
        (breach_id, report_uuid),
    )


async def by_id(conn: Conn, report_id: int) -> Row | None:
    return await fetch_one(conn, f"SELECT {_REPORT} WHERE r.report_id = %s", (report_id,))


async def on_breach(conn: Conn, breach_id: int) -> list[Row]:
    """Every report on a breach, each kind's newest first."""
    return await fetch_all(
        conn,
        f"SELECT {_REPORT} WHERE r.breach_id = %s ORDER BY r.kind, r.version DESC",
        (breach_id,),
    )


async def sections_of(conn: Conn, report_ids: list[int]) -> list[Row]:
    return await fetch_all(
        conn,
        """SELECT s.report_id, s.section_key, s.body FROM breach_report_section s
            WHERE s.report_id = ANY(%s) ORDER BY s.report_id, s.ordinal""",
        (report_ids,),
    )


async def write_sections(conn: Conn, report_id: int, bodies: dict[str, str | None]) -> None:
    """A draft's words, section by section, and the moment they changed."""
    keys = list(bodies)
    sealed = await seal_many("breach_report_section", [{"body": bodies[k]} for k in keys])
    for key, closed in zip(keys, sealed, strict=True):
        await conn.execute(
            """UPDATE breach_report_section SET body = %s
                WHERE report_id = %s AND section_key = %s""",
            (closed["body"], report_id, key),
        )
    await conn.execute(
        "UPDATE breach_report SET updated_at = now() WHERE report_id = %s", (report_id,)
    )


async def finalise(conn: Conn, report_id: int, *, finalised_by: int) -> None:
    await conn.execute(
        """UPDATE breach_report SET finalised_at = now(), finalised_by = %s, updated_at = now()
            WHERE report_id = %s""",
        (finalised_by, report_id),
    )


async def file(
    conn: Conn, report_id: int, *, filed_at: datetime, reference: str | None, filed_by: int
) -> None:
    await conn.execute(
        """UPDATE breach_report
              SET filed_at = %s, filed_reference = %s, filed_by = %s,
                  filed_recorded_at = now()
            WHERE report_id = %s""",
        (filed_at, reference, filed_by, report_id),
    )


# ------------------------------------------------------------------ deliveries


async def add_delivery(
    conn: Conn,
    report_id: int,
    recipient_id: int,
    *,
    attempt: int,
    status: str,
    detail: dict[str, Any] | None = None,
) -> Row | None:
    """One state of one attempt, or None if it is recorded already."""
    return await fetch_one(
        conn,
        """INSERT INTO breach_report_delivery (report_id, recipient_id, attempt, status, detail)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (report_id, recipient_id, attempt, status) DO NOTHING
           RETURNING delivery_uuid""",
        (report_id, recipient_id, attempt, status, Jsonb(detail or {})),
    )


async def address(conn: Conn, report_id: int, chosen: list[tuple[int, bool]]) -> None:
    """Who this version goes to: each entry or one-off address by its row, and
    whether it was mandatory as it was chosen. Before the version is frozen,
    which refuses any after it."""
    for recipient_id, mandatory in chosen:
        await conn.execute(
            """INSERT INTO breach_report_addressee (report_id, recipient_id, mandatory)
               VALUES (%s, %s, %s)""",
            (report_id, recipient_id, mandatory),
        )


async def latest_states(conn: Conn, report_ids: list[int]) -> list[Row]:
    """Each addressee of each report and its latest state: who it is, sealed,
    which attempt came last, whether it was mandatory when chosen and whether
    it was added for this report alone. An addressee never queued, a report to
    CERT-In waiting for a yes, carries a NULL status. Delivered outranks
    anything written after it. Recording takes no breach lock, so a re-queue or
    a removal can land just behind it, and neither unsends a mail that has
    gone."""
    return await fetch_all(
        conn,
        """SELECT a.report_id, a.recipient_id, a.mandatory, x.recipient_uuid, x.full_name,
                  x.email, x.email_hash, x.removed_at, x.one_off,
                  s.attempt, s.status, s.detail, s.recorded_at, s.last_attempt
             FROM breach_report_addressee a
             JOIN breach_board_recipient x ON x.recipient_id = a.recipient_id
             LEFT JOIN LATERAL (
                    SELECT d.attempt, d.status, d.detail, d.recorded_at,
                           max(d.attempt) OVER () AS last_attempt
                      FROM breach_report_delivery d
                     WHERE d.report_id = a.report_id AND d.recipient_id = a.recipient_id
                     ORDER BY (d.status = 'delivered') DESC, d.delivery_id DESC
                     LIMIT 1
                  ) s ON true
            WHERE a.report_id = ANY(%s)
            ORDER BY a.report_id, a.addressee_id""",
        (report_ids,),
    )


async def withheld_at_the_yes(
    conn: Conn, breach_id: int, *, event: str, kind: str
) -> dict[int, str]:
    """Why the yes did not mail each version of `kind` it withheld, by
    version: the `why` its trail row recorded then (`reports._release_held`).
    The list may change after the yes, so nothing read from it now can say
    which it was. The earliest row for a version stands. No address is in it."""
    rows = await fetch_all(
        conn,
        """SELECT (detail_json->>'version')::int AS version, detail_json->>'why' AS why
             FROM audit_log
            WHERE entity_type = 'breach' AND entity_id = %s AND event_type = %s
              AND detail_json->>'kind' = %s AND detail_json ? 'version'
            ORDER BY log_id""",
        (breach_id, event, kind),
    )
    out: dict[int, str] = {}
    for r in rows:
        if r["why"] is not None:
            out.setdefault(int(r["version"]), str(r["why"]))
    return out


async def job(conn: Conn, delivery_uuid: str) -> Row | None:
    """One queued delivery, its address, whether that address has been taken
    off the list since, whether its attempt has an outcome or a later attempt
    took its place, and whether the address has this report already, under any
    row of the list. Taken off is by address, as the office is shown it: an
    address put back under a new row is on the list, and one added for this
    report alone is never taken off."""
    return await fetch_one(
        conn,
        """SELECT d.delivery_id, d.report_id, d.recipient_id, d.attempt, d.status,
                  x.email, x.email_hash, x.recipient_uuid, x.one_off, r.breach_id,
                  (NOT x.one_off AND NOT EXISTS (
                     SELECT 1 FROM breach_board_recipient c
                      WHERE c.email_hash = x.email_hash
                        AND c.removed_at IS NULL AND NOT c.one_off)) AS removed,
                  EXISTS (SELECT 1 FROM breach_report_delivery o
                           WHERE o.report_id = d.report_id
                             AND o.recipient_id = d.recipient_id
                             AND (o.attempt > d.attempt
                                  OR (o.attempt = d.attempt AND o.status <> 'queued'))) AS settled,
                  EXISTS (SELECT 1 FROM breach_report_delivery o
                            JOIN breach_board_recipient a ON a.recipient_id = o.recipient_id
                           WHERE o.report_id = d.report_id
                             AND a.email_hash = x.email_hash
                             AND o.status = 'delivered') AS reached
             FROM breach_report_delivery d
             JOIN breach_report r ON r.report_id = d.report_id
             JOIN breach_board_recipient x ON x.recipient_id = d.recipient_id
            WHERE d.delivery_uuid = %s""",
        (delivery_uuid,),
    )


async def queued_to(conn: Conn, recipient_uuid: str) -> list[str]:
    """The deliveries still waiting on an address, on every report: under this
    row of the list or an older one for the same address, which a retry for an
    address put back may still be queued under. Never one added for a report
    alone, which is no row of the list."""
    rows = await fetch_all(
        conn,
        """SELECT s.delivery_uuid FROM (
             SELECT DISTINCT ON (d.report_id, d.recipient_id) d.delivery_uuid, d.status
               FROM breach_report_delivery d
               JOIN breach_board_recipient x ON x.recipient_id = d.recipient_id
              WHERE x.email_hash = (SELECT email_hash FROM breach_board_recipient
                                     WHERE recipient_uuid = %s)
                AND NOT x.one_off
              ORDER BY d.report_id, d.recipient_id, d.delivery_id DESC
           ) s WHERE s.status = 'queued'""",
        (recipient_uuid,),
    )
    return [str(r["delivery_uuid"]) for r in rows]


# -------------------------------------------------------------------- evidence


async def evidence_of(conn: Conn, report_ids: list[int]) -> list[Row]:
    """The proof kept for these reports, oldest first."""
    return await fetch_all(
        conn,
        """SELECT a.report_id, a.attachment_uuid, a.kind, a.note, a.file_name, a.storage_ref,
                  a.sha256, a.size_bytes, a.content_type, a.added_at,
                  u.full_name AS added_by_name
             FROM breach_attachment a JOIN auth_user u ON u.id = a.added_by
            WHERE a.report_id = ANY(%s) ORDER BY a.attachment_id""",
        (report_ids,),
    )
