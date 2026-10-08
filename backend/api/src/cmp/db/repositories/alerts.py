"""What the office's and staff's emails are about (2026-10-08): the open
rights requests close to their date, and the open breaches with a dated duty."""

from __future__ import annotations

from cmp.db.sql import Conn, Row, fetch_all


async def rights_due_within(conn: Conn, days: int, *, limit: int = 50) -> list[Row]:
    """Open requests overdue or due within `days`, soonest first."""
    return await fetch_all(
        conn,
        """SELECT r.reference, r.request_type::text AS request_type, r.due_at
             FROM rights_request r
            WHERE r.status <> 'closed' AND r.due_at < now() + make_interval(days => %s)
            ORDER BY r.due_at LIMIT %s""",
        (days, limit),
    )


async def open_breaches_with_dated_duties(conn: Conn) -> list[Row]:
    return await fetch_all(
        conn,
        """SELECT DISTINCT b.breach_id, b.breach_uuid::text AS breach_uuid,
                  coalesce(rec.reference, b.reference) AS reference
             FROM breach b
             JOIN breach_obligation o ON o.breach_id = b.breach_id AND o.due_at IS NOT NULL
             LEFT JOIN breach_recording rec ON rec.breach_id = b.breach_id
            WHERE b.status = 'open'""",
    )
