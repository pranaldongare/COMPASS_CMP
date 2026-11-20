"""What the office's and staff's emails are about (2026-10-08): the open
rights requests close to their date, and the open breaches with a dated duty."""

from __future__ import annotations

from cmp.db.sql import Conn, Row, fetch_all


async def rights_due_within(conn: Conn, days: int, *, limit: int = 50) -> list[Row]:
    """Open requests overdue or due within `days`, soonest first."""
    return await fetch_all(
        conn,
        """SELECT r.reference, r.request_type::text AS request_type, r.due_at,
                  (SELECT o.office_code FROM office o WHERE o.office_id = r.office_id)
                    AS office_code
             FROM rights_request r
            WHERE r.status <> 'closed' AND r.due_at < now() + make_interval(days => %s)
            ORDER BY r.due_at LIMIT %s""",
        (days, limit),
    )


async def open_breaches_with_dated_duties(conn: Conn) -> list[Row]:
    return await fetch_all(
        conn,
        """SELECT DISTINCT b.breach_id, b.breach_uuid::text AS breach_uuid,
                  coalesce(rec.reference, b.reference) AS reference,
                  (SELECT o.office_code FROM office o WHERE o.office_id = b.office_id)
                    AS office_code
             FROM breach b
             JOIN breach_obligation o ON o.breach_id = b.breach_id AND o.due_at IS NOT NULL
             LEFT JOIN breach_recording rec ON rec.breach_id = b.breach_id
            WHERE b.status = 'open'""",
    )


# ------------------------------------------------------- 2026-11-20 additions
#: A project's two people who answer for it: who made it, and who collects.
_PROJECT_PEOPLE = """SELECT DISTINCT p.project_id, p.project_uuid::text AS project_uuid,
                      p.project_name, p.created_by AS owner_id, p.dco_user_id AS dco_id,
                      (SELECT o.office_code FROM office o WHERE o.office_id = p.office_id)
                        AS office_code
                 FROM project p"""


async def projects_using_processor(conn: Conn, processor_id: int) -> list[Row]:
    """Every project not closed that names this processor, or has a site of it."""
    return await fetch_all(
        conn,
        _PROJECT_PEOPLE
        + """ WHERE p.project_status <> 'closed'
                AND (EXISTS (SELECT 1 FROM project_processor pp
                              WHERE pp.project_id = p.project_id AND pp.processor_id = %s
                                AND pp.status <> 'rejected')
                     OR EXISTS (SELECT 1 FROM project_site s
                                 WHERE s.project_id = p.project_id AND s.processor_id = %s
                                   AND s.status = 'active'))
              ORDER BY p.project_id""",
        (processor_id, processor_id),
    )


async def projects_using_source(conn: Conn, source_id: int) -> list[Row]:
    """Every project not closed with an active site collecting from this source."""
    return await fetch_all(
        conn,
        _PROJECT_PEOPLE
        + """ JOIN project_site s ON s.project_id = p.project_id
               WHERE p.project_status <> 'closed' AND s.source_id = %s AND s.status = 'active'
               ORDER BY p.project_id""",
        (source_id,),
    )


async def project_of_notice(conn: Conn, notice_id: int) -> Row | None:
    from cmp.db.sql import fetch_one

    return await fetch_one(
        conn,
        _PROJECT_PEOPLE + " JOIN notice n ON n.project_id = p.project_id WHERE n.notice_id = %s",
        (notice_id,),
    )


async def project_people(conn: Conn, project_id: int) -> Row | None:
    from cmp.db.sql import fetch_one

    return await fetch_one(conn, _PROJECT_PEOPLE + " WHERE p.project_id = %s", (project_id,))


async def hr_pocs_for_template(conn: Conn, template_id: int) -> list[int]:
    """The active HR PoCs assigned to the category a notice template serves."""
    rows = await fetch_all(
        conn,
        """SELECT DISTINCT a.user_id
             FROM notice_template t
             JOIN hr_poc_category a ON a.category_id = t.category_id
             JOIN auth_user u ON u.id = a.user_id AND u.status = 'active'
            WHERE t.template_id = %s
            ORDER BY a.user_id""",
        (template_id,),
    )
    return [int(r["user_id"]) for r in rows]


async def purposes_lapsed_offices(conn: Conn, purpose_codes: list[str]) -> list[Row]:
    """Which office each purpose is kept by."""
    if not purpose_codes:
        return []
    return await fetch_all(
        conn,
        """SELECT p.purpose_code, o.office_code
             FROM purpose p JOIN office o ON o.office_id = p.office_id
            WHERE p.purpose_code = ANY(%s)""",
        (purpose_codes,),
    )


async def template_title(conn: Conn, template_id: int) -> str | None:
    from cmp.db.sql import fetch_one

    row = await fetch_one(
        conn, "SELECT title FROM notice_template WHERE template_id = %s", (template_id,)
    )
    return str(row["title"]) if row and row.get("title") else None
