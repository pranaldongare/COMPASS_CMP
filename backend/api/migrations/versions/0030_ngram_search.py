"""Names become searchable again, by hashed runs of three characters.

Sealing the names took a search away. `WHERE full_name ILIKE '%shu%'` cannot
work on ciphertext, so the users list, the requests list and the audit
trail's "who was this about" picker were narrowed to whole contacts - and a
member of staff holding a piece of paper with a half-legible name had no way
to find the person on it.

This adds the second index that brings it back. Beside each searchable name
sits `<column>_ngrams`: a `text[]` of `HMAC-SHA256("ngram3:" || run)` for
every overlapping run of three characters in the normalised name. A search
hashes the runs of the term and asks for rows whose array contains all of
them - `@>`, answered by a GIN index. "shu" is one run; "amruta shu" is
eight; a row matches when it holds every one.

**Three columns, and that is deliberate.** A set of runs leaks more than a
single hash: anyone holding the column can count how often each run appears
and compare that against the letter statistics of a language, and with
enough rows common names come back without the key. So the runs exist only
where staff genuinely search by part of a value - a person's name - and
never for a contact, which is searched whole through the exact hash.
`NGRAM_INDEXED` in `cmp.infrastructure.dkms.fields` is the list, and the
reason is written beside it.

**The backfill decrypts.** The names are already sealed, so the runs cannot
be computed from what the column holds; each value is opened through the key
service, hashed, and the hashes written back. The plaintext is never stored
and never leaves this transaction. A key service that cannot be reached
fails the migration, which is right: a half-filled index is a search that
silently misses rows.

Revision ID: 0030
Revises: 0029
"""

from __future__ import annotations

import sys
from pathlib import Path

from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None

# The application's own hashing, so the migration and the code agree about
# every run they compute.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from cmp.infrastructure.dkms.blind import ngrams_of  # noqa: E402
from cmp.infrastructure.dkms.client import unseal_values_sync  # noqa: E402

#: (table, primary key, sealed name column, runs column)
NGRAMS: list[tuple[str, str, str, str]] = [
    ("auth_user", "id", "full_name", "full_name_ngrams"),
    ("rights_request", "request_id", "submitted_name", "submitted_name_ngrams"),
    ("nomination", "nomination_id", "nominee_name", "nominee_name_ngrams"),
]

ADD = "\n".join(
    f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {runs} text[];" for table, _, _, runs in NGRAMS
)

# GIN, because the question is "does this array contain all of these", and a
# btree cannot answer it. `gin__int_ops` is for integers; the default
# `array_ops` is what a text[] wants.
INDEX = "\n".join(
    f"CREATE INDEX IF NOT EXISTS idx_{table}_{column}_ngrams ON {table} USING gin ({runs});"
    for table, _, column, runs in NGRAMS
)

DROP = "\n".join(
    f"DROP INDEX IF EXISTS idx_{table}_{column}_ngrams;\n"
    f"ALTER TABLE {table} DROP COLUMN IF EXISTS {runs};"
    for table, _, column, runs in NGRAMS
)

#: How many rows are opened in one call to the key service. Large enough that
#: the round trip is not most of the cost, small enough that one failure does
#: not throw away a minute of work.
BATCH = 500


def _backfill() -> None:
    conn = op.get_bind()
    for table, pk, column, runs in NGRAMS:
        rows = conn.exec_driver_sql(
            f"SELECT {pk}, {column} FROM {table} WHERE {column} IS NOT NULL AND {column} <> ''"
        ).fetchall()
        for start in range(0, len(rows), BATCH):
            batch = rows[start : start + BATCH]
            values = [str(value) for _, value in batch]
            # Values sealed before this run are opened; anything still in the
            # clear - an old row, a test fixture - comes back unchanged.
            opened = unseal_values_sync(values)
            for (pk_value, _), plain in zip(batch, opened, strict=True):
                conn.exec_driver_sql(
                    f"UPDATE {table} SET {runs} = %s WHERE {pk} = %s",
                    (ngrams_of(plain), pk_value),
                )


def upgrade() -> None:
    op.execute(ADD)
    _backfill()
    op.execute(INDEX)


def downgrade() -> None:
    op.execute(DROP)
