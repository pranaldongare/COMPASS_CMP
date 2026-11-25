"""The VerifyEmail connection, the organisation's email domains, and each
account's last answer (0075, ADR 0046)."""

from __future__ import annotations

from typing import Any

from cmp.db.sql import Conn, fetch_all, fetch_one

Row = dict[str, Any]


async def connection(conn: Conn) -> Row:
    row = await fetch_one(
        conn,
        """SELECT x.base_url, x.api_key_sealed, x.api_key_header, x.enabled,
                  x.allow_other_domains, x.updated_at, u.full_name AS updated_by_name
             FROM employee_check_connection x
             LEFT JOIN auth_user u ON u.id = x.updated_by
            WHERE x.connection_id = 1""",
    )
    assert row is not None, "employee_check_connection has its one row from the migration"
    return row


async def save_connection(
    conn: Conn,
    *,
    base_url: str | None,
    api_key_sealed: bytes | None,
    keep_key: bool,
    api_key_header: str,
    enabled: bool,
    allow_other_domains: bool,
    actor_id: int,
) -> None:
    await conn.execute(
        """UPDATE employee_check_connection
              SET base_url = %(base_url)s,
                  api_key_sealed = CASE WHEN %(keep)s THEN api_key_sealed ELSE %(key)s END,
                  api_key_header = %(header)s,
                  enabled = %(enabled)s,
                  allow_other_domains = %(other)s,
                  updated_by = %(actor)s,
                  updated_at = now()
            WHERE connection_id = 1""",
        {
            "base_url": base_url,
            "keep": keep_key,
            "key": api_key_sealed,
            "header": api_key_header,
            "enabled": enabled,
            "other": allow_other_domains,
            "actor": actor_id,
        },
    )


async def domains(conn: Conn) -> list[str]:
    rows = await fetch_all(conn, "SELECT domain FROM organisation_domain ORDER BY domain")
    return [str(r["domain"]) for r in rows]


async def domain_rows(conn: Conn) -> list[Row]:
    return await fetch_all(
        conn,
        """SELECT d.domain, d.added_at, u.full_name AS added_by_name
             FROM organisation_domain d LEFT JOIN auth_user u ON u.id = d.added_by
            ORDER BY d.domain""",
    )


async def add_domain(conn: Conn, domain: str, *, actor_id: int) -> bool:
    """True when it was not on the list already."""
    row = await fetch_one(
        conn,
        """INSERT INTO organisation_domain (domain, added_by) VALUES (%s, %s)
           ON CONFLICT (domain) DO NOTHING RETURNING domain""",
        (domain, actor_id),
    )
    return row is not None


async def remove_domain(conn: Conn, domain: str) -> bool:
    row = await fetch_one(
        conn, "DELETE FROM organisation_domain WHERE domain = %s RETURNING domain", (domain,)
    )
    return row is not None


async def record_employment(conn: Conn, user_id: int, status: str | None) -> None:
    """The last answer for the account: `active`, `inactive`, or None when the
    call failed - an answer that is not had does not stand for a stale one."""
    await conn.execute(
        """UPDATE auth_user SET employment_status = %s, employment_checked_at = now()
            WHERE id = %s""",
        (status, user_id),
    )


async def employment(conn: Conn, user_id: int) -> Row | None:
    return await fetch_one(
        conn,
        "SELECT employment_status, employment_checked_at FROM auth_user WHERE id = %s",
        (user_id,),
    )
