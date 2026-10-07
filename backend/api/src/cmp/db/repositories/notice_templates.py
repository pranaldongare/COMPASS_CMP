"""Notice templates (0044): the DPO's notices before there is a project.

Nothing here is scoped by project, because a template has none: every route
over these rows is the DPO's, except reading one by its code to attach it,
which is the caller's to guard. Never served and never evidence, so the rows
are edited in place; a template is retired, never deleted.
"""

from __future__ import annotations

from typing import Any

from cmp.db.sql import Conn, Row, execute, fetch_all, fetch_one

TEMPLATE_COLUMNS = """
  t.template_id, t.template_uuid, t.template_code, t.title, t.withdraw_url,
  t.exercise_rights_url, t.board_complaint_url, t.dpo_contact, t.applicable_to,
  t.note, t.status, t.created_at, t.updated_at, t.retired_at,
  u.full_name AS created_by_name,
  (SELECT count(*) FROM notice_template_purpose tp WHERE tp.template_id = t.template_id)
    AS purpose_count,
  (SELECT count(*) FROM notice_template_language tl WHERE tl.template_id = t.template_id)
    AS language_count,
  (SELECT count(*) FROM notice n WHERE n.template_id = t.template_id) AS used_count
  FROM notice_template t
  JOIN auth_user u ON u.id = t.created_by
"""


async def create(
    conn: Conn,
    *,
    title: str,
    withdraw_url: str,
    exercise_rights_url: str,
    board_complaint_url: str,
    dpo_contact: str,
    applicable_to: str | None,
    note: str | None,
    created_by: int,
) -> Row:
    row = await fetch_one(
        conn,
        """INSERT INTO notice_template (title, withdraw_url, exercise_rights_url,
                                        board_complaint_url, dpo_contact, applicable_to,
                                        note, created_by)
           VALUES (%s, %s, %s, %s, %s, %s::notice_audience, %s, %s)
           RETURNING template_id""",
        (
            title,
            withdraw_url,
            exercise_rights_url,
            board_complaint_url,
            dpo_contact,
            applicable_to,
            note,
            created_by,
        ),
    )
    assert row is not None
    made = await by_id(conn, int(row["template_id"]))
    assert made is not None
    return made


async def by_id(conn: Conn, template_id: int) -> Row | None:
    return await fetch_one(
        conn, f"SELECT {TEMPLATE_COLUMNS} WHERE t.template_id = %s", (template_id,)
    )


async def by_uuid(conn: Conn, template_uuid: str) -> Row | None:
    return await fetch_one(
        conn, f"SELECT {TEMPLATE_COLUMNS} WHERE t.template_uuid = %s", (template_uuid,)
    )


async def by_code(conn: Conn, template_code: str) -> Row | None:
    """By the ID the DPO hands out: case and spacing forgiven, as it is typed."""
    return await fetch_one(
        conn,
        f"SELECT {TEMPLATE_COLUMNS} WHERE t.template_code = upper(btrim(%s))",
        (template_code,),
    )


async def lock(conn: Conn, template_id: int) -> None:
    await fetch_one(
        conn, "SELECT 1 FROM notice_template WHERE template_id = %s FOR UPDATE", (template_id,)
    )


async def list_all(conn: Conn, *, status: str | None = None, q: str | None = None) -> list[Row]:
    """Every template, newest first. A few dozen at most: the Privacy Office's."""
    where: list[str] = []
    params: list[Any] = []
    if status:
        where.append("t.status = %s")
        params.append(status)
    if q:
        where.append("(t.template_code ILIKE %s OR t.title ILIKE %s)")
        params += [f"%{q.strip()}%", f"%{q.strip()}%"]
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    return await fetch_all(
        conn, f"SELECT {TEMPLATE_COLUMNS} {clause} ORDER BY t.template_id DESC", params
    )


async def update(conn: Conn, template_id: int, **fields: Any) -> None:
    """Set the fields given; `None` leaves one as it is."""
    sets = {k: v for k, v in fields.items() if v is not None}
    if not sets:
        return
    assignments = ", ".join(
        f"{k} = %s::notice_audience" if k == "applicable_to" else f"{k} = %s" for k in sets
    )
    await execute(
        conn,
        f"UPDATE notice_template SET {assignments}, updated_at = now() WHERE template_id = %s",
        [*sets.values(), template_id],
    )


async def set_status(conn: Conn, template_id: int, status: str) -> None:
    await execute(
        conn,
        """UPDATE notice_template
              SET status = %s,
                  retired_at = CASE WHEN %s = 'retired' THEN now() END,
                  updated_at = now()
            WHERE template_id = %s""",
        (status, status, template_id),
    )


async def touch(conn: Conn, template_id: int) -> None:
    await execute(
        conn, "UPDATE notice_template SET updated_at = now() WHERE template_id = %s", (template_id,)
    )


# ----------------------------------------------------------------- purposes


async def purposes_of(conn: Conn, template_id: int) -> list[Row]:
    return await fetch_all(
        conn,
        """SELECT p.purpose_id, p.purpose_uuid, p.purpose_code, p.name, p.status,
                  p.lawful_basis, p.data_categories, tp.display_order, tp.is_mandatory
             FROM notice_template_purpose tp
             JOIN purpose p ON p.purpose_id = tp.purpose_id
            WHERE tp.template_id = %s
            ORDER BY tp.display_order, p.name""",
        (template_id,),
    )


async def attach_purpose(
    conn: Conn, *, template_id: int, purpose_id: int, display_order: int, is_mandatory: bool
) -> None:
    await execute(
        conn,
        """INSERT INTO notice_template_purpose
             (template_id, purpose_id, display_order, is_mandatory)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT (template_id, purpose_id)
           DO UPDATE SET display_order = EXCLUDED.display_order,
                         is_mandatory = EXCLUDED.is_mandatory""",
        (template_id, purpose_id, display_order, is_mandatory),
    )


async def detach_purpose(conn: Conn, *, template_id: int, purpose_id: int) -> int:
    return await execute(
        conn,
        "DELETE FROM notice_template_purpose WHERE template_id = %s AND purpose_id = %s",
        (template_id, purpose_id),
    )


# ---------------------------------------------------------------- languages


async def languages_of(conn: Conn, template_id: int) -> list[Row]:
    return await fetch_all(
        conn,
        """SELECT tl.language_code::text AS language_code, tl.rendered_text, tl.updated_at,
                  u.full_name AS updated_by_name
             FROM notice_template_language tl
             JOIN auth_user u ON u.id = tl.updated_by
            WHERE tl.template_id = %s
            ORDER BY (tl.language_code = 'english') DESC, tl.language_code""",
        (template_id,),
    )


async def set_language(
    conn: Conn, *, template_id: int, language_code: str, rendered_text: str, updated_by: int
) -> None:
    await execute(
        conn,
        """INSERT INTO notice_template_language (template_id, language_code, rendered_text,
                                                 updated_by)
           VALUES (%s, %s::language_code, %s, %s)
           ON CONFLICT (template_id, language_code)
           DO UPDATE SET rendered_text = EXCLUDED.rendered_text,
                         updated_by = EXCLUDED.updated_by,
                         updated_at = now()""",
        (template_id, language_code, rendered_text, updated_by),
    )


async def remove_language(conn: Conn, *, template_id: int, language_code: str) -> int:
    return await execute(
        conn,
        """DELETE FROM notice_template_language
            WHERE template_id = %s AND language_code = %s::language_code""",
        (template_id, language_code),
    )


# ---------------------------------------------------------------- where used


async def notices_from(conn: Conn, template_id: int) -> list[Row]:
    """The project notices made from this template, newest first."""
    return await fetch_all(
        conn,
        """SELECT n.notice_uuid, n.notice_code, n.version, n.status, n.created_at,
                  p.project_uuid, p.project_name
             FROM notice n
             JOIN project p ON p.project_id = n.project_id
            WHERE n.template_id = %s
            ORDER BY n.notice_id DESC""",
        (template_id,),
    )
