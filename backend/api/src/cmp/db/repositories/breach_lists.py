"""A breach's people from a list somebody sent us (0045).

Two lists arrive: people by name, email and mobile, and asset IDs. A person
the list names who has an account goes on the breach's ordinary list
(`breach_affected`, found by `upload`); one who has none is a contact of that
breach alone (`breach_contact`). Each file taken is a `breach_upload` row -
what it came to, never the file.
"""

from __future__ import annotations

from cmp.db.sql import Conn, Row, fetch_all, fetch_one, fetch_val
from cmp.infrastructure.dkms import seal, seal_many

# ----------------------------------------------------------------- matching


async def accounts_by_hashes(
    conn: Conn, *, email_hashes: list[str], mobile_hashes: list[str]
) -> list[Row]:
    """Accounts whose primary email or mobile is one of these, through the
    blind indexes - the sealed columns are never read."""
    if not email_hashes and not mobile_hashes:
        return []
    return await fetch_all(
        conn,
        """SELECT id AS person_id, email_hash, mobile_hash FROM auth_user
            WHERE email_hash = ANY(%s) OR mobile_hash = ANY(%s)""",
        (email_hashes, mobile_hashes),
    )


async def contact_hashes(conn: Conn, breach_id: int) -> tuple[set[str], set[str]]:
    """The email and mobile indexes of the contacts this breach already lists."""
    rows = await fetch_all(
        conn,
        "SELECT email_hash, mobile_hash FROM breach_contact WHERE breach_id = %s",
        (breach_id,),
    )
    return (
        {str(r["email_hash"]) for r in rows if r["email_hash"]},
        {str(r["mobile_hash"]) for r in rows if r["mobile_hash"]},
    )


async def assets_by_uuid(conn: Conn, uuids: list[str]) -> list[Row]:
    if not uuids:
        return []
    return await fetch_all(
        conn,
        """SELECT da.asset_id, da.asset_uuid::text AS asset_uuid, da.source_asset_ref,
                  ds.source_code
             FROM data_asset da JOIN data_source ds ON ds.source_id = da.source_id
            WHERE da.asset_uuid = ANY(%s::uuid[])""",
        (uuids,),
    )


async def assets_by_ref(conn: Conn, refs: list[str]) -> list[Row]:
    """Assets by the ID the capture tool gave them - one per source, so a
    reference can name an asset in more than one source."""
    if not refs:
        return []
    return await fetch_all(
        conn,
        """SELECT da.asset_id, da.asset_uuid::text AS asset_uuid, da.source_asset_ref,
                  ds.source_code
             FROM data_asset da JOIN data_source ds ON ds.source_id = da.source_id
            WHERE da.source_asset_ref = ANY(%s)""",
        (refs,),
    )


async def people_in_assets(conn: Conn, asset_ids: list[int]) -> tuple[list[Row], int]:
    """Who consented in these assets - each person, with the assets they are
    in - and how many appearances in them name nobody (incidental or
    unidentified subjects, who cannot be traced to anyone). An appearance
    already erased is gone, and not counted."""
    if not asset_ids:
        return [], 0
    people = await fetch_all(
        conn,
        """SELECT ca.auth_user_id AS person_id,
                  array_agg(DISTINCT da.asset_uuid::text) AS assets
             FROM asset_consent ac
             JOIN consent_artefact ca ON ca.consent_id = ac.consent_id
             JOIN data_asset da       ON da.asset_id = ac.asset_id
            WHERE ac.asset_id = ANY(%s)
              AND coalesce(ac.disposition::text, 'active') <> 'erased'
            GROUP BY ca.auth_user_id""",
        (asset_ids,),
    )
    untraceable = await fetch_val(
        conn,
        """SELECT count(*) FROM asset_consent
            WHERE asset_id = ANY(%s) AND consent_id IS NULL
              AND coalesce(disposition::text, 'active') <> 'erased'""",
        (asset_ids,),
    )
    return people, int(untraceable or 0)


# ------------------------------------------------------------------- writing


async def add_upload(
    conn: Conn,
    breach_id: int,
    *,
    kind: str,
    file_name: str,
    sha256: str,
    counts: dict[str, int],
    added_by: int,
) -> Row:
    sealed = await seal("breach_upload", {"file_name": file_name})
    row = await fetch_one(
        conn,
        """INSERT INTO breach_upload (breach_id, kind, file_name, sha256, rows_read,
                                      matched_people, new_contacts, already_listed,
                                      unreadable, untraceable, added_by)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           RETURNING upload_id, upload_uuid""",
        (
            breach_id,
            kind,
            sealed["file_name"],
            sha256,
            counts["rows_read"],
            counts["matched_people"],
            counts["new_contacts"],
            counts["already_listed"],
            counts["unreadable"],
            counts.get("untraceable", 0),
            added_by,
        ),
    )
    assert row is not None
    return row


async def add_contacts(conn: Conn, breach_id: int, upload_id: int, contacts: list[Row]) -> int:
    """Contacts with no account, sealed in one call. One already listed on the
    breach - by email or by mobile - is skipped. Returns how many were added."""
    if not contacts:
        return 0
    sealed = await seal_many(
        "breach_contact",
        [
            {"full_name": c.get("full_name"), "email": c.get("email"), "mobile": c.get("mobile")}
            for c in contacts
        ],
    )
    added = 0
    for plain, closed in zip(contacts, sealed, strict=True):
        row = await fetch_one(
            conn,
            """INSERT INTO breach_contact (breach_id, upload_id, full_name, email, mobile,
                                           email_hash, mobile_hash)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT DO NOTHING
               RETURNING contact_id""",
            (
                breach_id,
                upload_id,
                closed["full_name"],
                closed["email"],
                closed["mobile"],
                plain.get("email_hash"),
                plain.get("mobile_hash"),
            ),
        )
        added += row is not None
    return added


# ------------------------------------------------------------------- reading


async def count_contacts(conn: Conn, breach_id: int) -> int:
    n = await fetch_val(
        conn, "SELECT count(*) FROM breach_contact WHERE breach_id = %s", (breach_id,)
    )
    return int(n or 0)


async def contact_id_by_uuid(conn: Conn, breach_id: int, contact_uuid: str) -> int | None:
    n = await fetch_val(
        conn,
        "SELECT contact_id FROM breach_contact WHERE breach_id = %s AND contact_uuid = %s",
        (breach_id, contact_uuid),
    )
    return int(n) if n is not None else None


async def contacts_page(conn: Conn, breach_id: int, *, after: int | None, limit: int) -> list[Row]:
    """The contacts with no account, oldest first, sealed as stored."""
    return await fetch_all(
        conn,
        """SELECT c.contact_uuid, c.full_name, c.email, c.mobile, c.added_at,
                  u.upload_uuid, u.kind AS upload_kind
             FROM breach_contact c JOIN breach_upload u ON u.upload_id = c.upload_id
            WHERE c.breach_id = %s AND (%s::int IS NULL OR c.contact_id > %s)
            ORDER BY c.contact_id LIMIT %s""",
        (breach_id, after, after, limit),
    )


async def uploads(conn: Conn, breach_id: int) -> list[Row]:
    return await fetch_all(
        conn,
        """SELECT u.upload_uuid, u.kind, u.file_name, u.sha256, u.rows_read, u.matched_people,
                  u.new_contacts, u.already_listed, u.unreadable, u.untraceable, u.added_at,
                  a.full_name AS added_by_name
             FROM breach_upload u JOIN auth_user a ON a.id = u.added_by
            WHERE u.breach_id = %s ORDER BY u.upload_id""",
        (breach_id,),
    )
