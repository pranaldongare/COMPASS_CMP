"""An address identifies exactly one person, whichever column holds it.

Two rows that would both answer the same sign-in is the failure these guard
against. The unique index covers one column; the trigger covers the diagonal -
a second address that is somebody else's first, and the reverse - and raises
with the unique-violation code so the application reports a conflict rather
than a server error.

Raw SQL, bypassing the service layer, because the rule has to hold against a
writer that forgot it. One violation per test: an aborted transaction accepts
nothing further, and the fixture's rollback is what cleans up.
"""

from __future__ import annotations

from typing import Any

import psycopg
import pytest

pytestmark = pytest.mark.integration


async def test_a_second_address_may_not_be_somebody_elses_first(
    conn: Any, seeded: dict[str, Any]
) -> None:
    with pytest.raises(psycopg.errors.UniqueViolation):
        await conn.execute(
            "UPDATE auth_user SET secondary_email = 'DPO@test.local' WHERE id = %s",
            (seeded["subject"]["id"],),
        )


async def test_a_first_address_may_not_be_somebody_elses_second(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await conn.execute(
        "UPDATE auth_user SET secondary_email = 'kept@example.org' WHERE id = %s",
        (seeded["subject"]["id"],),
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        await conn.execute(
            "UPDATE auth_user SET email = 'Kept@example.org' WHERE id = %s",
            (seeded["users"]["dco"]["id"],),
        )


async def test_two_people_may_not_share_a_second_address(conn: Any, seeded: dict[str, Any]) -> None:
    await conn.execute(
        "UPDATE auth_user SET secondary_email = 'Shared@example.org' WHERE id = %s",
        (seeded["subject"]["id"],),
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        await conn.execute(
            "UPDATE auth_user SET secondary_email = 'shared@example.org' WHERE id = %s",
            (seeded["users"]["dco"]["id"],),
        )


async def test_the_same_address_twice_on_one_row_is_refused(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """It would say nothing, and would let an unconfirmed copy sit beside a
    confirmed one."""
    with pytest.raises(psycopg.errors.CheckViolation):
        await conn.execute(
            "UPDATE auth_user SET secondary_email = 'SUBJECT@test.local' WHERE id = %s",
            (seeded["subject"]["id"],),
        )
