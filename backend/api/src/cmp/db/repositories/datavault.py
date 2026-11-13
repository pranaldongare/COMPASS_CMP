"""DataVault: where it is, and what it answered for a rights request (0070).

Three tables of their own. Nothing here reads or writes a rights table beyond
the request's and the holder's keys, which the caller has already been let
through to.
"""

from __future__ import annotations

from typing import Any

from cmp.db.sql import Conn, fetch_all, fetch_one

Row = dict[str, Any]


# ------------------------------------------------------------- the connection
async def connection(conn: Conn) -> Row:
    row = await fetch_one(
        conn,
        """SELECT x.base_url, x.api_key_sealed, x.api_key_header, x.enabled, x.updated_at,
                  u.full_name AS updated_by_name
             FROM datavault_connection x
             LEFT JOIN auth_user u ON u.id = x.updated_by
            WHERE x.connection_id = 1""",
    )
    assert row is not None, "datavault_connection has its one row from the migration"
    return row


async def set_connection(
    conn: Conn,
    *,
    base_url: str | None,
    api_key_header: str,
    enabled: bool,
    actor_id: int,
    api_key_sealed: bytes | None,
    keep_key: bool,
) -> None:
    """The row as the administrator saved it. `keep_key` leaves the key that
    is there: the page never has it to send back."""
    await conn.execute(
        """UPDATE datavault_connection
              SET base_url = %(url)s, api_key_header = %(header)s, enabled = %(enabled)s,
                  api_key_sealed = CASE WHEN %(keep)s THEN api_key_sealed ELSE %(key)s END,
                  updated_by = %(actor)s, updated_at = now()
            WHERE connection_id = 1""",
        {
            "url": base_url,
            "header": api_key_header,
            "enabled": enabled,
            "keep": keep_key,
            "key": api_key_sealed,
            "actor": actor_id,
        },
    )


# ------------------------------------------------------------------ the checks
_CHECK = """
  k.check_id, k.check_uuid, k.request_id, k.asked_at, k.outcome, k.failure, k.asset_count,
  (k.asked_by IS NULL) AS automatic, u.full_name AS asked_by_name
  FROM datavault_check k
  LEFT JOIN auth_user u ON u.id = k.asked_by
"""


async def add_check(
    conn: Conn,
    *,
    request_id: int,
    asked_by: int | None,
    outcome: str,
    failure: str | None,
    asset_count: int,
) -> Row:
    row = await fetch_one(
        conn,
        """INSERT INTO datavault_check (request_id, asked_by, outcome, failure, asset_count)
           VALUES (%s, %s, %s, %s, %s)
           RETURNING check_id, check_uuid""",
        (request_id, asked_by, outcome, failure, asset_count),
    )
    assert row is not None
    return row


async def add_assets(conn: Conn, check_id: int, assets: list[Row]) -> None:
    if not assets:
        return
    async with conn.cursor() as cur:
        await cur.executemany(
            """INSERT INTO datavault_check_asset
                 (check_id, position, asset_ref, consent_ref, project_ref,
                  consent_id, project_id, mid, datapath)
               VALUES (%(check_id)s, %(position)s, %(asset_ref)s, %(consent_ref)s,
                       %(project_ref)s, %(consent_id)s, %(project_id)s, %(mid)s, %(datapath)s)""",
            [{**a, "check_id": check_id, "position": i} for i, a in enumerate(assets)],
        )


async def last_check(conn: Conn, request_id: int) -> Row | None:
    """The newest call, answered or not: what the page says happened last."""
    return await fetch_one(
        conn,
        f"SELECT {_CHECK} WHERE k.request_id = %s ORDER BY k.check_id DESC LIMIT 1",
        (request_id,),
    )


async def last_answer(conn: Conn, request_id: int) -> Row | None:
    """The newest call DataVault answered: a later one that failed does not
    unsay what an earlier one listed."""
    return await fetch_one(
        conn,
        f"""SELECT {_CHECK} WHERE k.request_id = %s AND k.outcome = 'answered'
            ORDER BY k.check_id DESC LIMIT 1""",
        (request_id,),
    )


_ASSET = """
  a.asset_ref, a.consent_ref, a.project_ref, a.mid, a.datapath,
  c.consent_uuid, c.consent_id AS consent_no,
  p.project_uuid, p.project_id AS project_no, p.project_name
  FROM datavault_check_asset a
  LEFT JOIN consent_artefact c ON c.consent_id = a.consent_id
  LEFT JOIN project p ON p.project_id = a.project_id
"""


async def assets_of(conn: Conn, check_id: int, *, project_id: int | None = None) -> list[Row]:
    """What a check listed, in DataVault's order; of one project when asked."""
    only = "AND a.project_id = %(p)s" if project_id is not None else ""
    return await fetch_all(
        conn,
        f"SELECT {_ASSET} WHERE a.check_id = %(k)s {only} ORDER BY a.position",
        {"k": check_id, "p": project_id},
    )


# ------------------------------------------------ matching what DataVault named
async def consents_of_person(conn: Conn, user_id: int, *, office_id: int | None) -> list[Row]:
    """This person's consents with their projects, in the request's office:
    what DataVault's `consent_id` and `project_id` are matched against, and
    nothing wider. An identifier that is somebody else's consent stays
    unmatched, and so does her own consent in the other office's project - a
    request is one office's, and what it links to is that office's too.

    The office is named here and not left to the row policy, as
    `holdings.owners_of_person` names it: the platform's own check reads
    across both offices, where the policy would let every consent through.
    A request no office has claimed yet is matched within the caller's own."""
    office = "p.office_id = %(o)s" if office_id is not None else "cmp_office_visible(p.office_id)"
    return await fetch_all(
        conn,
        f"""SELECT ca.consent_id, ca.consent_uuid::text AS consent_uuid,
                   n.project_id, p.project_uuid::text AS project_uuid
              FROM consent_artefact ca
              JOIN notice n ON n.notice_id = ca.notice_id
              JOIN project p ON p.project_id = n.project_id
             WHERE ca.auth_user_id = %(u)s AND {office}""",
        {"u": user_id, "o": office_id},
    )


# -------------------------------------------------------------------- holders
async def dco_admin_holder(conn: Conn, holder_uuid: str, user_id: int) -> Row | None:
    """The holder behind a ticket, if it is a project's DCO Admin answering in
    the console and this account is the one it is addressed to (0069)."""
    return await fetch_one(
        conn,
        """SELECT h.request_id, h.project_id
             FROM rights_request_holder h
             JOIN project p ON p.project_id = h.project_id
            WHERE h.holder_uuid = %s AND h.responder_user_id = %s
              AND h.derived_from = 'project_owner' AND p.category_id IS NULL""",
        (holder_uuid, user_id),
    )
