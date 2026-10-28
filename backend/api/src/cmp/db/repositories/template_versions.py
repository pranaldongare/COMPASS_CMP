"""template_version and its text and purposes: what Legal approves (0053, ADR 0033).

A version is reached through its template, which the caller has already
found within its office; the lookups by uuid alone (an activity names its
version) carry the office themselves (`cmp_office_visible`, ADR 0032).
"""

from __future__ import annotations

from typing import Any

from cmp.db.sql import Conn, Row, execute, fetch_all, fetch_one

VERSION_COLUMNS = """
  v.version_id, v.version_uuid, v.template_id, v.version, v.status, v.reconsent_required,
  v.slot_guidance, v.slot_max_length, v.withdraw_url, v.exercise_rights_url,
  v.board_complaint_url, v.dpo_contact, v.applicable_to::text AS applicable_to,
  v.created_at, v.updated_at, v.approved_at, v.retired_at,
  cu.full_name AS created_by_name, au.full_name AS approved_by_name,
  t.template_uuid, t.template_code, t.title AS template_title, t.status AS template_status,
  t.category_id, c.category_uuid, c.category_code, c.name AS category_name,
  (SELECT o.office_code FROM office o WHERE o.office_id = t.office_id) AS office_code,
  (SELECT count(*) FROM template_version_language l WHERE l.version_id = v.version_id)
    AS language_count,
  (SELECT count(*) FROM template_version_purpose vp WHERE vp.version_id = v.version_id)
    AS purpose_count,
  (SELECT count(*) FROM project p WHERE p.template_version_id = v.version_id)
    AS activity_count
  FROM template_version v
  JOIN notice_template t ON t.template_id = v.template_id
  LEFT JOIN hr_category c ON c.category_id = t.category_id
  JOIN auth_user cu ON cu.id = v.created_by
  LEFT JOIN auth_user au ON au.id = v.approved_by
"""

#: Fields a draft may change, and their casts.
DRAFT_FIELDS = {
    "reconsent_required": "",
    "slot_guidance": "",
    "slot_max_length": "",
    "withdraw_url": "",
    "exercise_rights_url": "",
    "board_complaint_url": "",
    "dpo_contact": "",
    "applicable_to": "::notice_audience",
}


async def for_template(conn: Conn, template_id: int) -> list[Row]:
    """Every version of a template, newest first."""
    return await fetch_all(
        conn,
        f"SELECT {VERSION_COLUMNS} WHERE v.template_id = %s ORDER BY v.version DESC",
        (template_id,),
    )


async def by_number(conn: Conn, template_id: int, version: int) -> Row | None:
    return await fetch_one(
        conn,
        f"SELECT {VERSION_COLUMNS} WHERE v.template_id = %s AND v.version = %s",
        (template_id, version),
    )


async def by_id(conn: Conn, version_id: int) -> Row | None:
    return await fetch_one(conn, f"SELECT {VERSION_COLUMNS} WHERE v.version_id = %s", (version_id,))


async def by_uuid(conn: Conn, version_uuid: str) -> Row | None:
    """Within the caller's office: an activity names its version by uuid."""
    return await fetch_one(
        conn,
        f"""SELECT {VERSION_COLUMNS}
            WHERE v.version_uuid = %s AND cmp_office_visible(t.office_id)""",
        (version_uuid,),
    )


async def approved_for_category(conn: Conn, category_id: int) -> list[Row]:
    """The approved versions of a category's active templates: what an
    activity can be made from (ADR 0033)."""
    return await fetch_all(
        conn,
        f"""SELECT {VERSION_COLUMNS}
            WHERE t.category_id = %s AND t.status = 'active' AND v.status = 'approved'
            ORDER BY t.template_code, v.version DESC""",
        (category_id,),
    )


async def latest(conn: Conn, template_id: int) -> Row | None:
    return await fetch_one(
        conn,
        f"SELECT {VERSION_COLUMNS} WHERE v.template_id = %s ORDER BY v.version DESC LIMIT 1",
        (template_id,),
    )


async def lock_template(conn: Conn, template_id: int) -> None:
    """Serialise version numbering on one template."""
    await fetch_one(
        conn, "SELECT 1 FROM notice_template WHERE template_id = %s FOR UPDATE", (template_id,)
    )


async def create(
    conn: Conn, *, template_id: int, version: int, created_by: int, fields: dict[str, Any]
) -> int:
    row = await fetch_one(
        conn,
        """INSERT INTO template_version
             (template_id, version, created_by, reconsent_required, slot_guidance,
              slot_max_length, withdraw_url, exercise_rights_url, board_complaint_url,
              dpo_contact, applicable_to)
           VALUES (%(template_id)s, %(version)s, %(created_by)s, %(reconsent_required)s,
                   %(slot_guidance)s, %(slot_max_length)s, %(withdraw_url)s,
                   %(exercise_rights_url)s, %(board_complaint_url)s, %(dpo_contact)s,
                   %(applicable_to)s::notice_audience)
           RETURNING version_id""",
        {**fields, "template_id": template_id, "version": version, "created_by": created_by},
    )
    assert row is not None
    return int(row["version_id"])


async def update(conn: Conn, version_id: int, fields: dict[str, Any]) -> None:
    """Set the draft fields given."""
    sets = {k: v for k, v in fields.items() if k in DRAFT_FIELDS}
    if not sets:
        return
    assignments = ", ".join(f"{k} = %s{DRAFT_FIELDS[k]}" for k in sets)
    await execute(
        conn,
        f"UPDATE template_version SET {assignments} WHERE version_id = %s",
        [*sets.values(), version_id],
    )


async def approve(conn: Conn, version_id: int, *, approved_by: int) -> None:
    await execute(
        conn,
        """UPDATE template_version SET status = 'approved', approved_by = %s, approved_at = now()
            WHERE version_id = %s AND status = 'draft'""",
        (approved_by, version_id),
    )


async def retire(conn: Conn, version_id: int, *, retired_by: int) -> None:
    await execute(
        conn,
        """UPDATE template_version SET status = 'retired', retired_by = %s, retired_at = now()
            WHERE version_id = %s AND status = 'approved'""",
        (retired_by, version_id),
    )


# ---------------------------------------------------------------- languages
async def languages_of(conn: Conn, version_id: int) -> list[Row]:
    return await fetch_all(
        conn,
        """SELECT l.language_code::text AS language_code, l.locked_text, l.content_hash,
                  l.updated_at, u.full_name AS updated_by_name
             FROM template_version_language l
             JOIN auth_user u ON u.id = l.updated_by
            WHERE l.version_id = %s
            ORDER BY (l.language_code = 'english') DESC, l.language_code""",
        (version_id,),
    )


async def set_language(
    conn: Conn, *, version_id: int, language_code: str, locked_text: str, updated_by: int
) -> None:
    """Add or replace one language's text; its hash is set again at approval."""
    await execute(
        conn,
        """INSERT INTO template_version_language (version_id, language_code, locked_text,
                                                  updated_by)
           VALUES (%s, %s::language_code, %s, %s)
           ON CONFLICT (version_id, language_code)
           DO UPDATE SET locked_text = EXCLUDED.locked_text, content_hash = NULL,
                         updated_by = EXCLUDED.updated_by, updated_at = now()""",
        (version_id, language_code, locked_text, updated_by),
    )


async def remove_language(conn: Conn, *, version_id: int, language_code: str) -> int:
    return await execute(
        conn,
        """DELETE FROM template_version_language
            WHERE version_id = %s AND language_code = %s::language_code""",
        (version_id, language_code),
    )


async def set_hash(conn: Conn, *, version_id: int, language_code: str, content_hash: str) -> None:
    await execute(
        conn,
        """UPDATE template_version_language SET content_hash = %s
            WHERE version_id = %s AND language_code = %s::language_code""",
        (content_hash, version_id, language_code),
    )


# ----------------------------------------------------------------- purposes
async def purposes_of(conn: Conn, version_id: int) -> list[Row]:
    """The purposes an activity may choose, in order, with what the composer
    renders of each."""
    return await fetch_all(
        conn,
        """SELECT p.purpose_id, p.purpose_uuid, p.purpose_code, p.name, p.status,
                  p.lawful_basis, p.uses, p.data_categories, vp.is_mandatory, vp.display_order
             FROM template_version_purpose vp
             JOIN purpose p ON p.purpose_id = vp.purpose_id
            WHERE vp.version_id = %s
            ORDER BY vp.display_order, p.name""",
        (version_id,),
    )


async def set_purposes(conn: Conn, version_id: int, purposes: list[dict[str, Any]]) -> None:
    """Exactly these, in this order."""
    await execute(conn, "DELETE FROM template_version_purpose WHERE version_id = %s", (version_id,))
    for p in purposes:
        await execute(
            conn,
            """INSERT INTO template_version_purpose
                 (version_id, purpose_id, is_mandatory, display_order)
               VALUES (%s, %s, %s, %s)""",
            (version_id, p["purpose_id"], p["is_mandatory"], p["display_order"]),
        )
