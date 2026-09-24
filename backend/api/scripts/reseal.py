"""Seal what was written before sealing was on.

`seal()` runs on write, so a column is ciphertext only from the day the key
service was switched on. Everything before that is plaintext, and the read path
tolerates both - which is what made the switch safe to make and is also why
nothing forces this to run. It should run once after every column joins
ENCRYPTED_FIELDS, and it can run again at any time: a row already sealed is
skipped, so it is idempotent.

For each sealed column it walks the rows whose value is present and not yet
`SE::`, in batches, and writes the sealed value back. For a column with a blind
index beside it, the index is recomputed from the plaintext in the same
UPDATE, so a row is never left with a value nobody can find.

    python scripts/reseal.py            # do it
    python scripts/reseal.py --check    # report only; exit 1 if anything is unsealed
    python scripts/reseal.py --table auth_user

Refuses to run against the key service switched off: sealing needs it, and a
"reseal" that wrote plaintext back would be a no-op that reported success.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any

from cmp.core.config import settings
from cmp.core.logging import configure_logging, get_logger
from cmp.db.pool import close_pool, open_pool, transaction
from cmp.db.sql import fetch_all
from cmp.infrastructure.dkms import encrypt_records
from cmp.infrastructure.dkms.blind import index_of
from cmp.infrastructure.dkms.fields import BLIND_INDEXED, ENCRYPTED_FIELDS

log = get_logger("cmp.reseal")

PRIMARY_KEY = {
    "auth_user": "id",
    "nomination": "nomination_id",
    "rights_request": "request_id",
    "rights_request_holder": "holder_id",
    "rights_ticket_message": "message_id",
    "rights_response_file": "file_id",
    "consent_artefact": "consent_id",
    "processor_respondent": "respondent_id",
    "person_type_history": "history_id",
    "delegation": "delegation_id",
    "project_processor": "project_processor_id",
    "project_status_history": "history_id",
    "import_batch": "batch_id",
    "legal_hold": "hold_id",
}

#: What kind of blind index each indexed column takes.
INDEX_KIND = {
    "email": "email",
    "secondary_email": "email",
    "mobile": "mobile",
    "username": "username",
    "organization_id": "text",
    "nominee_email": "email",
    "nominee_mobile": "mobile",
    "submitted_contact": "contact",
}

BATCH = 200


async def unsealed_count(conn: Any, table: str, column: str) -> int:
    row = await fetch_all(
        conn,
        f"SELECT count(*) AS n FROM {table} "
        f"WHERE {column} IS NOT NULL AND {column} NOT LIKE 'SE::%%'",
    )
    return int(row[0]["n"])


#: Tables whose rows may never be edited, by trigger, and the trigger that says
#: so. Sealing changes how a value is stored and nothing about what it says, so
#: the operator running this may set the rule aside for the duration of the
#: transaction - and only then: DDL is transactional, and the trigger is back
#: before anyone else can see the table.
APPEND_ONLY = {
    "rights_ticket_message": "trg_ticket_message_append_only",
    "consent_artefact": "trg_consent_append_only",
    "project_status_history": "trg_project_history_append_only",
    "person_type_history": "trg_person_type_history_append_only",
    # Not append-only, but its reason is fixed once placed (0031); a value
    # written before sealing was on can only be sealed with the trigger off.
    "legal_hold": "trg_legal_hold_release_only",
}


async def reseal_column(conn: Any, table: str, column: str, *, check: bool) -> int:
    pk = PRIMARY_KEY[table]
    total = 0
    if not check and table in APPEND_ONLY:
        await conn.execute(f"ALTER TABLE {table} DISABLE TRIGGER {APPEND_ONLY[table]}")
    while True:
        rows = await fetch_all(
            conn,
            f"""SELECT {pk} AS pk, {column} AS value FROM {table}
                 WHERE {column} IS NOT NULL AND {column} NOT LIKE 'SE::%%'
                 ORDER BY {pk} LIMIT {BATCH}""",
        )
        if not rows:
            if table in APPEND_ONLY and not check:
                await conn.execute(f"ALTER TABLE {table} ENABLE TRIGGER {APPEND_ONLY[table]}")
            return total
        if check:
            return total + await unsealed_count(conn, table, column)

        sealed = await encrypt_records(
            [{column: str(r["value"])} for r in rows], {column: ENCRYPTED_FIELDS[table][column]}
        )
        idx_col = BLIND_INDEXED.get(table, {}).get(column)
        for row, out in zip(rows, sealed, strict=True):
            if idx_col:
                await conn.execute(
                    f"UPDATE {table} SET {column} = %s, {idx_col} = %s WHERE {pk} = %s",
                    (out[column], index_of(INDEX_KIND[column], str(row["value"])), row["pk"]),  # type: ignore[arg-type]
                )
            else:
                await conn.execute(
                    f"UPDATE {table} SET {column} = %s WHERE {pk} = %s",
                    (out[column], row["pk"]),
                )
        total += len(rows)
        log.info("reseal.batch", table=table, column=column, rows=len(rows))


async def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="report unsealed rows and change nothing"
    )
    parser.add_argument("--table", help="one table only")
    args = parser.parse_args(argv)

    if not settings.dkms_enabled:
        print("DKMS_ENABLED is false: nothing can be sealed. Refusing.", file=sys.stderr)
        return 2

    configure_logging()
    await open_pool()
    unsealed_total = 0
    try:
        for table, columns in ENCRYPTED_FIELDS.items():
            if args.table and table != args.table:
                continue
            for column in columns:
                async with transaction() as conn:
                    n = await reseal_column(conn, table, column, check=args.check)
                if n:
                    unsealed_total += n
                    verb = "unsealed" if args.check else "sealed"
                    print(f"{table}.{column:<24} {n:>6} rows {verb}")
    finally:
        await close_pool()

    if args.check:
        print(
            f"\n{unsealed_total} plaintext values in sealed columns"
            if unsealed_total
            else "\nevery sealed column is ciphertext"
        )
        return 1 if unsealed_total else 0
    print(f"\n{unsealed_total} values sealed")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv[1:])))
