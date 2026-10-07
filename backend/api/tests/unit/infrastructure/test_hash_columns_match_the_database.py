"""The `*_hash` columns the code names are the ones the schema has.

`BLIND_INDEXED` is the map every lookup is written against: a contact column,
and the column beside it holding `HMAC-SHA256(normalised value)`. If the two
drift - a migration renames one, the map keeps the old name - every lookup
through it fails at runtime with an undefined-column error, on sign-in, which
is the worst possible place to find out.

Static: the names in the map are checked against the migration that created
them, so this runs without a database.
"""

from __future__ import annotations

import re
from pathlib import Path

from cmp.infrastructure.dkms.fields import BLIND_INDEXED

MIGRATIONS = Path(__file__).resolve().parents[3] / "migrations" / "versions"


def test_every_hash_column_is_named_hash() -> None:
    """The suffix is `_hash`, since 0029. `_idx` was what an index is built
    on; `_hash` is what the column holds."""
    for table, columns in BLIND_INDEXED.items():
        for source, hashed in columns.items():
            assert hashed == f"{source}_hash", f"{table}.{source} maps to {hashed}"


#: Tables whose hash columns were created with them, after 0029 renamed the
#: rest - and the migration that created each.
BORN_HASHED = {"breach_contact": "0045_breach_contact_upload.py"}


def test_the_rename_migration_covers_exactly_these_columns() -> None:
    text = (MIGRATIONS / "0029_hash_columns.py").read_text()
    renamed = {
        (table, old, new) for table, old, new in re.findall(r'\("(\w+)", "(\w+)", "(\w+)"\)', text)
    }
    expected = {
        (table, f"{source}_idx", hashed)
        for table, columns in BLIND_INDEXED.items()
        if table not in BORN_HASHED
        for source, hashed in columns.items()
    }
    assert renamed == expected


def test_a_table_born_with_hash_columns_creates_them() -> None:
    for table, migration in BORN_HASHED.items():
        text = (MIGRATIONS / migration).read_text()
        for hashed in BLIND_INDEXED[table].values():
            assert f"{hashed} " in text, f"{migration} does not create {table}.{hashed}"
