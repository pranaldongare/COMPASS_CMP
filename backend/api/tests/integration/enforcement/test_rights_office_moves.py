"""A rights request changes office only by a claim or a transfer (0055).

`cmp_rights_request_office_moves()` in SQL, past the application: out of the
shared intake with who and when; from one office to the other with a new
stamp, who, why and where from; anything else refused - including a second
transfer that leans on the first one's columns (open point F-12). A legal
hold's office, like every other record's, never changes.
"""

from __future__ import annotations

from typing import Any

import psycopg
import pytest

pytestmark = pytest.mark.integration

_OFFICE = "(SELECT office_id FROM office WHERE office_code = %s)"


async def _request(conn: Any, seeded: dict[str, Any], office: str | None) -> int:
    cur = await conn.execute(
        f"""INSERT INTO rights_request (reference, request_type, channel, submitted_contact,
                                        submitted_contact_hash, request_text, due_at, office_id)
            VALUES ('RR-MOVE-' || substr(md5(random()::text), 1, 10), 'access', 'public_form',
                    'SE::contact', 'h', 'SE::text', now() + interval '30 days', {_OFFICE})
            RETURNING request_id""",
        (office,),
    )
    row = await cur.fetchone()
    return int(row["request_id"])


async def _refused(conn: Any, sql: str, params: tuple[Any, ...]) -> None:
    async with conn.transaction(force_rollback=True):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            await conn.execute(sql, params)


async def test_a_bare_update_of_the_office_is_refused(conn: Any, seeded: dict[str, Any]) -> None:
    held = await _request(conn, seeded, "rnd")
    await _refused(
        conn,
        f"UPDATE rights_request SET office_id = {_OFFICE} WHERE request_id = %s",
        ("hr", held),
    )
    intake = await _request(conn, seeded, None)
    await _refused(
        conn,
        f"UPDATE rights_request SET office_id = {_OFFICE} WHERE request_id = %s",
        ("hr", intake),
    )


async def test_a_claim_is_out_of_the_intake_with_who_and_when_once(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = seeded["users"]["dpo"]["id"]
    intake = await _request(conn, seeded, None)
    await conn.execute(
        f"""UPDATE rights_request SET office_id = {_OFFICE}, claimed_at = now(), claimed_by = %s
             WHERE request_id = %s""",
        ("rnd", dpo, intake),
    )
    # Claimed once: claiming it again into the other office is no claim.
    await _refused(
        conn,
        f"""UPDATE rights_request SET office_id = {_OFFICE}, claimed_at = now(), claimed_by = %s
             WHERE request_id = %s""",
        ("hr", dpo, intake),
    )


async def test_a_transfer_carries_its_four_columns_and_a_new_stamp(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = seeded["users"]["dpo"]["id"]
    held = await _request(conn, seeded, "rnd")
    move = f"""UPDATE rights_request
                  SET transferred_from_office_id = office_id, office_id = {_OFFICE},
                      transferred_at = clock_timestamp(), transferred_by = %s,
                      transfer_reason = 'SE::why'
                WHERE request_id = %s"""
    await conn.execute(move, ("hr", dpo, held))
    # Back again, by the same statement: a new stamp, so it is allowed.
    await conn.execute(move, ("rnd", dpo, held))
    # Back again with the old stamp and the old reason: the leftovers of the
    # last transfer are not a transfer.
    await _refused(
        conn,
        f"UPDATE rights_request SET office_id = {_OFFICE},"
        " transferred_from_office_id = office_id WHERE request_id = %s",
        ("hr", held),
    )
    # Without a reason: the trigger asks for it before the CHECK would.
    async with conn.transaction(force_rollback=True):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            await conn.execute(
                f"""UPDATE rights_request
                       SET transferred_from_office_id = office_id, office_id = {_OFFICE},
                           transferred_at = clock_timestamp(), transferred_by = %s,
                           transfer_reason = NULL
                     WHERE request_id = %s""",
                ("hr", dpo, held),
            )


async def test_a_legal_hold_keeps_its_office(conn: Any, seeded: dict[str, Any]) -> None:
    cur = await conn.execute(
        f"""INSERT INTO legal_hold (subject_user_id, reason, placed_by, office_id)
            VALUES (%s, 'SE::why', %s, {_OFFICE}) RETURNING hold_id""",
        (seeded["subject"]["id"], seeded["users"]["dpo"]["id"], "rnd"),
    )
    hold = (await cur.fetchone())["hold_id"]
    async with conn.transaction(force_rollback=True):
        with pytest.raises(psycopg.errors.RestrictViolation):
            await conn.execute(
                f"UPDATE legal_hold SET office_id = {_OFFICE} WHERE hold_id = %s", ("hr", hold)
            )
