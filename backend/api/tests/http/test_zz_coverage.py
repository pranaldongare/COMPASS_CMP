"""Every documented personal-data endpoint was exercised by this run.

Named to sort last. `call()` records each (method, path template) it sends;
`docs/tools/personal-data-scan.py` is what `docs/domain/pii-fields-and-endpoints.md`
is generated from. The two are compared here, so an endpoint added to the API
and to the documentation, but not to this suite, fails the build - and an
endpoint the suite covers that the documentation forgot fails it too, from the
other side.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.db.sql import fetch_one
from cmp.infrastructure.dkms.fields import ENCRYPTED_FIELDS
from tests.http.contract import LEDGER, documented_pii_endpoints


def test_every_documented_pii_endpoint_was_exercised() -> None:
    documented = documented_pii_endpoints()
    missing = sorted(documented - LEDGER)
    assert not missing, (
        f"{len(missing)} of {len(documented)} documented personal-data endpoints were never "
        f"called by tests/http: {missing}"
    )


def test_nothing_in_the_suite_is_undocumented() -> None:
    """A path the suite calls and the documentation does not list.

    Not every endpoint carries personal data - a purpose's activation, a
    processor's decision - so this only asks about the ones that answered
    with a sealed field or a joined name, which `call()` checked. Those
    belong in the documentation, or the list the portals decrypt is short.
    """
    from tests.http.contract import TOUCHED_SEALED

    documented = documented_pii_endpoints()
    undocumented = sorted(TOUCHED_SEALED - documented)
    assert not undocumented, undocumented


# --------------------------------------------------------- the columns themselves
#
# The suite above wrote through every repository there is - accounts, consents,
# nominations, requests, holders, messages, respondents, imports. If any writer
# had let a plaintext value through, it is in the database now. One query per
# sealed column says whether it did. This is `scripts/reseal.py --check` as a
# test, run after the writes that would fail it.


@pytest.mark.parametrize(
    ("table", "column"),
    sorted((t, c) for t, cols in ENCRYPTED_FIELDS.items() for c in cols),
    ids=lambda v: v,
)
async def test_every_sealed_column_holds_only_ciphertext(
    db_pool: Any, table: str, column: str
) -> None:
    async with db_pool.connection() as conn:
        row = await fetch_one(
            conn,
            f"SELECT count(*) AS n FROM {table} "
            f"WHERE {column} IS NOT NULL AND {column} <> '' AND {column} NOT LIKE 'SE::%%'",
        )
    assert row is not None
    assert row["n"] == 0, f"{table}.{column}: {row['n']} plaintext row(s)"
