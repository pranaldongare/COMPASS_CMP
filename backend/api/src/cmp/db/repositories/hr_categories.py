"""hr_category, category_processor, hr_poc_category: the Legal office's registry.

A category is a kind of HR activity the Legal office governs (ADR 0033): its
templates belong to it, the processors that hold its data are named on it, and
the HR PoCs who may run its activities are assigned to it.

Scope is two predicates, both in the WHERE: the office (`cmp_office_visible`,
the same test as the policy behind it, ADR 0032) and, for an HR PoC, the
categories assigned to them. The Legal PoC and the administrator read every
category the office lets them see.
"""

from __future__ import annotations

from typing import Any

from cmp.core.offices import OFFICE_ID
from cmp.core.permissions import Role, Scope, scope_of
from cmp.db.sql import Conn, Row, execute, fetch_all, fetch_one

_COLUMNS = """
  c.category_id, c.category_uuid, c.category_code, c.name, c.description, c.status,
  c.created_at, c.updated_at, c.retired_at,
  (SELECT o.office_code FROM office o WHERE o.office_id = c.office_id) AS office_code,
  (SELECT count(*) FROM category_processor cp
    WHERE cp.category_id = c.category_id AND cp.removed_at IS NULL) AS processor_count,
  (SELECT count(*) FROM hr_poc_category a WHERE a.category_id = c.category_id) AS poc_count,
  (SELECT count(*) FROM notice_template t WHERE t.category_id = c.category_id) AS template_count
"""

#: The order a category list reads in: active first, then by code.
_ORDER = "ORDER BY (c.status = 'retired'), c.category_code"


def scope_predicate(role: Role | str, user_id: int) -> tuple[str, list[Any]]:
    """The categories a role may read, as a WHERE fragment over alias `c`."""
    office = "cmp_office_visible(c.office_id)"
    match scope_of("hr_category", role):
        case Scope.ALL:
            return office, []
        case Scope.SCOPED:
            return (
                f"{office} AND EXISTS (SELECT 1 FROM hr_poc_category a"
                " WHERE a.category_id = c.category_id AND a.user_id = %s)",
                [user_id],
            )
        case _:
            return "FALSE", []


async def create(
    conn: Conn,
    *,
    category_code: str,
    name: str,
    description: str | None,
    office: str,
    created_by: int,
) -> Row:
    row = await fetch_one(
        conn,
        f"""INSERT INTO hr_category (category_code, name, description, office_id, created_by)
            VALUES (%s, %s, %s, {OFFICE_ID}, %s)
            RETURNING category_id""",
        (category_code, name, description, office, created_by),
    )
    assert row is not None
    made = await by_id(conn, int(row["category_id"]))
    assert made is not None
    return made


async def by_id(conn: Conn, category_id: int) -> Row | None:
    return await fetch_one(
        conn, f"SELECT {_COLUMNS} FROM hr_category c WHERE c.category_id = %s", (category_id,)
    )


async def by_uuid(conn: Conn, category_uuid: str, *, role: Role | str, user_id: int) -> Row | None:
    pred, params = scope_predicate(role, user_id)
    return await fetch_one(
        conn,
        f"SELECT {_COLUMNS} FROM hr_category c WHERE c.category_uuid = %s AND {pred}",
        (category_uuid, *params),
    )


async def list_categories(
    conn: Conn,
    *,
    role: Role | str,
    user_id: int,
    status: str | None = None,
    q: str | None = None,
) -> list[Row]:
    """A few dozen at most: one per kind of HR activity."""
    pred, params = scope_predicate(role, user_id)
    where = [pred]
    if status:
        where.append("c.status = %s")
        params.append(status)
    if q:
        where.append("(c.category_code ILIKE %s OR c.name ILIKE %s)")
        params += [f"%{q.strip()}%", f"%{q.strip()}%"]
    return await fetch_all(
        conn, f"SELECT {_COLUMNS} FROM hr_category c WHERE {' AND '.join(where)} {_ORDER}", params
    )


async def lock(conn: Conn, category_id: int) -> None:
    await fetch_one(
        conn, "SELECT 1 FROM hr_category WHERE category_id = %s FOR UPDATE", (category_id,)
    )


async def update(
    conn: Conn, category_id: int, *, name: str | None, description: str | None
) -> None:
    """The name and description; a code is stable once given."""
    await execute(
        conn,
        """UPDATE hr_category
              SET name = COALESCE(%s, name), description = COALESCE(%s, description)
            WHERE category_id = %s""",
        (name, description, category_id),
    )


async def set_status(conn: Conn, category_id: int, status: str) -> None:
    await execute(
        conn,
        """UPDATE hr_category
              SET status = %s,
                  retired_at = CASE WHEN %s = 'retired' THEN now() END
            WHERE category_id = %s""",
        (status, status, category_id),
    )


# --------------------------------------------------------------- processors
_PROCESSOR_COLUMNS = """
  cp.category_processor_id, cp.category_processor_uuid, cp.processor_id, cp.processor_role,
  cp.respondent_user_id, cp.added_at,
  p.processor_uuid, p.legal_name, p.is_in_house, p.status AS processor_status,
  r.uuid AS respondent_uuid, r.full_name AS respondent_name, r.email AS respondent_email
  FROM category_processor cp
  JOIN processor p ON p.processor_id = cp.processor_id
  LEFT JOIN auth_user r ON r.id = cp.respondent_user_id
"""


async def processors_of(conn: Conn, category_id: int) -> list[Row]:
    """The processors holding the category's data now, in the order named."""
    return await fetch_all(
        conn,
        f"""SELECT {_PROCESSOR_COLUMNS}
            WHERE cp.category_id = %s AND cp.removed_at IS NULL
            ORDER BY cp.category_processor_id""",
        (category_id,),
    )


async def add_processor(
    conn: Conn,
    *,
    category_id: int,
    processor_id: int,
    processor_role: str,
    respondent_user_id: int | None,
    added_by: int,
) -> None:
    await execute(
        conn,
        """INSERT INTO category_processor
             (category_id, processor_id, processor_role, respondent_user_id, added_by)
           VALUES (%s, %s, %s, %s, %s)""",
        (category_id, processor_id, processor_role, respondent_user_id, added_by),
    )


async def change_processor(
    conn: Conn, category_processor_id: int, *, processor_role: str, respondent_user_id: int | None
) -> None:
    await execute(
        conn,
        """UPDATE category_processor SET processor_role = %s, respondent_user_id = %s
            WHERE category_processor_id = %s""",
        (processor_role, respondent_user_id, category_processor_id),
    )


async def remove_processor(conn: Conn, category_processor_id: int, *, removed_by: int) -> None:
    await execute(
        conn,
        """UPDATE category_processor SET removed_at = now(), removed_by = %s
            WHERE category_processor_id = %s AND removed_at IS NULL""",
        (removed_by, category_processor_id),
    )


# ---------------------------------------------------------------- HR PoCs
async def pocs_of(conn: Conn, category_id: int) -> list[Row]:
    """The HR PoCs assigned to a category."""
    return await fetch_all(
        conn,
        """SELECT u.uuid, u.full_name, u.email, u.status, a.assigned_at
             FROM hr_poc_category a JOIN auth_user u ON u.id = a.user_id
            WHERE a.category_id = %s
            ORDER BY a.assignment_id""",
        (category_id,),
    )


async def categories_of_user(conn: Conn, user_id: int) -> list[Row]:
    """The categories an HR PoC is assigned to, within the caller's office."""
    return await fetch_all(
        conn,
        """SELECT c.category_id, c.category_uuid, c.category_code, c.name, c.status
             FROM hr_poc_category a JOIN hr_category c ON c.category_id = a.category_id
            WHERE a.user_id = %s AND cmp_office_visible(c.office_id)
            ORDER BY c.category_code""",
        (user_id,),
    )


async def set_user_categories(
    conn: Conn, user_id: int, category_ids: list[int], *, assigned_by: int
) -> None:
    """Exactly these: an assignment not named is ended. A working assignment,
    not evidence; the audit trail keeps who changed it."""
    await execute(
        conn,
        "DELETE FROM hr_poc_category WHERE user_id = %s AND NOT (category_id = ANY(%s))",
        (user_id, category_ids),
    )
    for category_id in category_ids:
        await execute(
            conn,
            """INSERT INTO hr_poc_category (user_id, category_id, assigned_by)
               VALUES (%s, %s, %s) ON CONFLICT (user_id, category_id) DO NOTHING""",
            (user_id, category_id, assigned_by),
        )


async def clear_user_categories(conn: Conn, user_id: int) -> int:
    """Every assignment of an account that no longer holds the HR PoC role."""
    return await execute(conn, "DELETE FROM hr_poc_category WHERE user_id = %s", (user_id,))


async def hr_pocs(conn: Conn, *, category_id: int | None = None) -> list[Row]:
    """Active HR PoCs, for a picker; `category_id` keeps those assigned to it."""
    where = "u.role = 'hr_user' AND u.status = 'active'"
    params: list[Any] = []
    if category_id is not None:
        where += (
            " AND EXISTS (SELECT 1 FROM hr_poc_category a"
            " WHERE a.user_id = u.id AND a.category_id = %s)"
        )
        params.append(category_id)
    return await fetch_all(
        conn,
        f"""SELECT u.uuid, u.full_name, u.email, u.role
              FROM auth_user u WHERE {where}
             ORDER BY u.id""",
        params,
    )
