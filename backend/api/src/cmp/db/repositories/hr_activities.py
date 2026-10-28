"""HR activities: projects of the Legal office made from a template version (ADR 0033).

An activity is a `project` row, so its scope is the project predicate - an
HR PoC's categories, Legal's office, within the office (ADR 0032) - and
what this module adds is the activity's own view: its category, its
version, its live link and how many have consented.
"""

from __future__ import annotations

from cmp.core.permissions import Role
from cmp.db.repositories.projects import scope_predicate
from cmp.db.sql import Conn, Row, fetch_all, fetch_one

_COLUMNS = """
  p.project_id, p.project_uuid AS activity_uuid, p.project_name AS name,
  p.activity_description AS description, p.project_status AS status,
  p.created_at, p.updated_at,
  c.category_uuid, c.category_code, c.name AS category_name,
  v.version_uuid, v.version AS template_version, v.status AS version_status,
  v.reconsent_required, t.template_uuid, t.template_code, t.title AS template_title,
  creator.uuid AS created_by_uuid, creator.full_name AS created_by_name,
  n.notice_uuid, n.notice_code, n.version AS notice_version,
  (SELECT count(*) FROM v_current_consent vc
     JOIN notice cn ON cn.notice_id = vc.notice_id
    WHERE cn.project_id = p.project_id AND NOT vc.is_withdrawal) AS consent_count,
  (SELECT cl.status FROM consent_link cl
     JOIN notice ln ON ln.notice_id = cl.notice_id
    WHERE ln.project_id = p.project_id
    ORDER BY (cl.status = 'active') DESC, cl.created_at DESC LIMIT 1) AS link_status
  FROM project p
  JOIN hr_category c ON c.category_id = p.category_id
  JOIN template_version v ON v.version_id = p.template_version_id
  JOIN notice_template t ON t.template_id = v.template_id
  JOIN auth_user creator ON creator.id = p.created_by
  LEFT JOIN notice n ON n.notice_id = p.current_notice_id
"""


async def list_activities(
    conn: Conn,
    *,
    role: Role | str,
    user_id: int,
    status: str | None = None,
    category_uuid: str | None = None,
    q: str | None = None,
) -> list[Row]:
    """Newest first. An activity is short-lived and a category runs a few
    dozen a year, so the list is not paged."""
    pred, params = scope_predicate(role, user_id)
    where = [pred, "p.template_version_id IS NOT NULL"]
    if status:
        where.append("p.project_status = %s::project_status")
        params.append(status)
    if category_uuid:
        where.append("c.category_uuid = %s")
        params.append(category_uuid)
    if q:
        where.append("p.project_name ILIKE %s")
        params.append(f"%{q.strip()}%")
    return await fetch_all(
        conn,
        f"SELECT {_COLUMNS} WHERE {' AND '.join(where)} ORDER BY p.created_at DESC LIMIT 500",
        params,
    )


async def by_uuid(conn: Conn, activity_uuid: str, *, role: Role | str, user_id: int) -> Row | None:
    pred, params = scope_predicate(role, user_id)
    return await fetch_one(
        conn,
        f"""SELECT {_COLUMNS}
            WHERE p.project_uuid = %s AND p.template_version_id IS NOT NULL AND {pred}""",
        [activity_uuid, *params],
    )


async def participants(conn: Conn, project_id: int) -> list[Row]:
    """Everyone with a current consent on the activity, with the contacts a
    message to them is addressed by."""
    return await fetch_all(
        conn,
        """SELECT DISTINCT u.id, u.email, u.mobile, u.email_verified_at, u.mobile_verified_at
             FROM v_current_consent v
             JOIN notice n ON n.notice_id = v.notice_id
             JOIN auth_user u ON u.id = v.auth_user_id
            WHERE n.project_id = %s AND NOT v.is_withdrawal""",
        (project_id,),
    )


async def live_link(conn: Conn, project_id: int) -> Row | None:
    """The activity's open link: the active one, else the newest."""
    return await fetch_one(
        conn,
        """SELECT cl.link_uuid, cl.token_sealed, cl.status, cl.expires_at, cl.use_count,
                  cl.audience_mode, cl.created_at
             FROM consent_link cl JOIN notice n ON n.notice_id = cl.notice_id
            WHERE n.project_id = %s
            ORDER BY (cl.status = 'active') DESC, cl.created_at DESC
            LIMIT 1""",
        (project_id,),
    )
