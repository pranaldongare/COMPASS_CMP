"""A DCO's or an RCO's own processors, and their data sources (2026-10-09, 0050).

The administrator says which processors a collection owner collects for - a
third party for a DCO, an in-house team for an RCO. The owner then sees the
data sources of those processors and no others, registers new ones only under
them, and is handed only those processors' sources. Cover lends the
delegator's processors, as it lends their projects.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.core.pagination import PageRequest
from cmp.core.permissions import Role
from cmp.db.repositories import registry as repo
from cmp.db.sql import fetch_one
from cmp.domain.registry import service as registry
from cmp.domain.users import service as users
from tests.conftest import hashed

pytestmark = pytest.mark.integration

PAGE = PageRequest(limit=100, cursor=None, sort_field="created_at", descending=True)


async def _processor(conn: Any, name: str, *, in_house: bool = False) -> dict[str, Any]:
    row = await fetch_one(
        conn,
        """INSERT INTO processor (legal_name, type, contract_ref, security_confirmed_at,
                                  is_in_house, location_country)
           VALUES (%s, 'lab', 'CTR-X', current_date, %s, 'IN')
           RETURNING processor_id, processor_uuid, legal_name""",
        (name, in_house),
    )
    assert row
    return row


async def _source(conn: Any, code: str, processor: dict[str, Any]) -> dict[str, Any]:
    row = await fetch_one(
        conn,
        """INSERT INTO data_source (source_code, name, source_role, exchange_mode,
                                    processor_id, is_authoritative_for)
           VALUES (%s, %s, 'collection', 'manual_upload', %s, '{}')
           RETURNING source_id, source_uuid""",
        (code, f"Source {code}", processor["processor_id"]),
    )
    assert row
    return row


async def _codes(conn: Any, role: Role, user_id: int) -> set[str]:
    items, _, _ = await repo.list_sources(
        conn, PAGE, collector_user_id=user_id if registry.is_collector(role) else None
    )
    return {i["source_code"] for i in items}


async def test_a_dco_sees_the_sources_of_their_own_processors_only(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dco = seeded["users"]["dco"]["id"]
    mine = seeded["processors"]["external"]
    other = await _processor(conn, "Somebody Else Ltd")
    await _source(conn, "SRC-MINE", mine)
    theirs = await _source(conn, "SRC-THEIRS", other)

    seen = await _codes(conn, Role.DCO, dco)
    assert "SRC-MINE" in seen and "SRC-THEIRS" not in seen
    # The DPO's register is unchanged.
    assert {"SRC-MINE", "SRC-THEIRS"} <= await _codes(conn, Role.DPO, seeded["users"]["dpo"]["id"])

    # One they cannot see is not there at all.
    source = await repo.source_by_uuid(conn, str(theirs["source_uuid"]))
    with pytest.raises(NotFound):
        await registry.require_in_reach(conn, source, role=Role.DCO, user_id=dco)
    await registry.require_in_reach(conn, source, role=Role.DPO, user_id=dco)


async def test_a_dco_registers_only_under_their_own_processors(
    conn: Any, seeded: dict[str, Any], request_context: Any
) -> None:
    dco = seeded["users"]["dco"]["id"]
    other = await _processor(conn, "Not Mine Ltd")
    fields = {
        "name": "Rig",
        "source_role": "collection",
        "exchange_mode": "manual_upload",
        "id_scheme": None,
        "site_uuid": None,
        "is_authoritative_for": [],
    }
    with pytest.raises(ValidationFailed) as refused:
        await registry.create_source(
            conn,
            role=Role.DCO,
            user_id=dco,
            source_code="SRC-NO",
            processor_uuid=str(other["processor_uuid"]),
            **fields,
        )
    assert refused.value.field == "processor_uuid"

    made = await registry.create_source(
        conn,
        role=Role.DCO,
        user_id=dco,
        source_code="SRC-YES",
        processor_uuid=str(seeded["processors"]["external"]["processor_uuid"]),
        **fields,
    )
    assert made["source_code"] == "SRC-YES"


async def test_the_administrator_sets_them_the_right_kind_and_the_trail_keeps_it(
    conn: Any, seeded: dict[str, Any], request_context: Any
) -> None:
    admin = seeded["users"]["admin"]["id"]
    dco = seeded["users"]["dco"]
    second = await _processor(conn, "Second Partner Ltd")

    # A DCO collects for third parties; an in-house team is refused.
    with pytest.raises(ValidationFailed):
        await users.set_processors(
            conn,
            str(dco["uuid"]),
            processor_uuids=[str(seeded["processors"]["in_house"]["processor_uuid"])],
            actor_id=admin,
        )
    # And a role that collects for nobody has none to set.
    with pytest.raises(ValidationFailed):
        await users.set_processors(
            conn, str(seeded["users"]["dpo"]["uuid"]), processor_uuids=[], actor_id=admin
        )

    now = await users.set_processors(
        conn,
        str(dco["uuid"]),
        processor_uuids=[
            str(seeded["processors"]["external"]["processor_uuid"]),
            str(second["processor_uuid"]),
        ],
        actor_id=admin,
    )
    assert {p["legal_name"] for p in now} == {"Test Processor Ltd", "Second Partner Ltd"}
    await _source(conn, "SRC-SECOND", second)
    assert "SRC-SECOND" in await _codes(conn, Role.DCO, dco["id"])

    trail = await fetch_one(
        conn,
        """SELECT detail_json FROM audit_log WHERE event_type = 'user.processors_set'
             AND entity_id = %s ORDER BY log_id DESC LIMIT 1""",
        (dco["id"],),
    )
    assert trail and len(trail["detail_json"]["to"]) == 2


async def test_a_processor_whose_source_they_hold_is_not_taken_away(
    conn: Any, seeded: dict[str, Any], request_context: Any
) -> None:
    admin = seeded["users"]["admin"]["id"]
    dco = seeded["users"]["dco"]
    held = await _source(conn, "SRC-HELD", seeded["processors"]["external"])
    await repo.set_source_owner(conn, held["source_id"], dco["id"])
    other = await _processor(conn, "Replacement Ltd")
    with pytest.raises(Conflict) as refused:
        await users.set_processors(
            conn, str(dco["uuid"]), processor_uuids=[str(other["processor_uuid"])], actor_id=admin
        )
    assert refused.value.code == "processor_still_held"


async def test_a_source_is_handed_only_to_somebody_who_collects_for_its_processor(
    conn: Any, seeded: dict[str, Any], request_context: Any
) -> None:
    other = await _processor(conn, "Unassigned Partner Ltd")
    source = await _source(conn, "SRC-HAND", other)
    with pytest.raises(ValidationFailed) as refused:
        await registry.assign_source_owner(
            conn, str(source["source_uuid"]), owner_user_uuid=str(seeded["users"]["dco"]["uuid"])
        )
    assert refused.value.field == "owner_user_uuid"

    mine = await _source(conn, "SRC-HAND-OK", seeded["processors"]["external"])
    done = await registry.assign_source_owner(
        conn, str(mine["source_uuid"]), owner_user_uuid=str(seeded["users"]["dco"]["uuid"])
    )
    assert done["has_owner"]


async def test_a_role_change_takes_the_processors_away(
    conn: Any, seeded: dict[str, Any], request_context: Any
) -> None:
    dco = seeded["users"]["dco"]
    await users.change_role(
        conn,
        str(dco["uuid"]),
        role="dco_admin",
        reason=None,
        actor_id=seeded["users"]["admin"]["id"],
    )
    assert await repo.processors_of_collector(conn, dco["id"]) == []


async def test_cover_lends_the_delegators_processors(conn: Any, seeded: dict[str, Any]) -> None:
    dco = seeded["users"]["dco"]["id"]
    other = await _processor(conn, "Colleague's Partner Ltd")
    await _source(conn, "SRC-COVER", other)
    colleague = await fetch_one(
        conn,
        """INSERT INTO auth_user (full_name, email, email_hash, role, status, password_hash)
           VALUES ('Colleague', 'colleague@test.local', %s, 'dco', 'active', 'x')
           RETURNING id""",
        (hashed("email", "colleague@test.local"),),
    )
    assert colleague
    await conn.execute(
        "INSERT INTO collection_owner_processor (user_id, processor_id) VALUES (%s, %s)",
        (colleague["id"], other["processor_id"]),
    )
    assert "SRC-COVER" not in await _codes(conn, Role.DCO, dco)
    await conn.execute(
        """INSERT INTO delegation (delegator_user_id, delegate_user_id, starts_at,
                                   reason, created_by)
           VALUES (%s, %s, now() - interval '1 minute', 'leave', %s)""",
        (colleague["id"], dco, colleague["id"]),
    )
    assert "SRC-COVER" in await _codes(conn, Role.DCO, dco)
