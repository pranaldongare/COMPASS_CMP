"""The platform finds who holds her data as work begins (the product owner, 2026-11-13).

"Find who holds the data" was a button the office pressed once a request was
in progress. The reading is the same every time and needs no judgement, so the
platform now does it as the request starts - the move from received to in
progress, which the state machine allows only for a request the office has
found valid. The route does it (`routers/v1/rights.py`, after the move has
committed; `tests/http/test_20_datavault.py` walks it); what is settled here
is when, and what the trail says.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.permissions import Role
from cmp.domain.rights import service
from tests.integration.test_holders_by_owner import _only_dco_admin, _request
from tests.integration.test_rights_flows import _consent

pytestmark = pytest.mark.integration

DPO = Role.DPO


def _row(**over: Any) -> dict[str, Any]:
    return {"status": "in_progress", "request_type": "access", "subject_user_id": 7, **over}


def test_it_reads_the_records_as_work_begins_and_only_then() -> None:
    assert service.finds_holders_at_start("received", _row())
    assert service.finds_holders_at_start("received", _row(request_type="erasure"))
    # Not for a grievance: it asks no holder anything.
    assert not service.finds_holders_at_start("received", _row(request_type="grievance"))
    # Not with no person behind the request: there are no records to read.
    assert not service.finds_holders_at_start("received", _row(subject_user_id=None))
    # Not on the way back from collating, nor on any other move.
    assert not service.finds_holders_at_start("collating", _row())
    assert not service.finds_holders_at_start("in_progress", _row(status="awaiting_holders"))
    assert not service.finds_holders_at_start("in_progress", _row(status="collating"))
    assert not service.finds_holders_at_start("received", _row(status="closed"))


async def _derived(conn: Any, request_id: int) -> list[dict[str, Any]]:
    cur = await conn.execute(
        """SELECT detail_json AS detail, actor_user_id FROM audit_log
            WHERE event_type = 'rights.holders_derived' AND entity_type = 'rights_request'
              AND entity_id = %s ORDER BY log_id""",
        (request_id,),
    )
    return list(await cur.fetchall())


async def test_the_trail_says_whether_the_platform_read_them_or_a_press_did(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    await _only_dco_admin(conn, seeded)
    await _consent(conn, seeded)
    row = await _request(conn, seeded)
    assert service.finds_holders_at_start("received", row), "a started access request, hers"

    found = await service.derive_holders(conn, row, role=DPO, actor_id=dpo, automatic=True)
    assert [h["derived_from"] for h in found] == ["project_owner"]
    row = await service.reload(conn, row)
    assert row["holders_derived_at"] is not None
    assert all(h["confirmed_at"] is None for h in found), "found is not confirmed: the office does"

    # The office's own press afterwards reads again and adds nobody twice.
    again = await service.derive_holders(conn, row, role=DPO, actor_id=dpo)
    assert [h["holder_uuid"] for h in again] == [h["holder_uuid"] for h in found]

    first, second = await _derived(conn, int(row["request_id"]))
    assert first["detail"]["automatic"] is True and first["detail"]["added"] == 1
    assert first["actor_user_id"] == dpo, "the officer who started the work"
    assert "automatic" not in second["detail"], "a press leaves the row as it always was"
    assert second["detail"]["added"] == 0
