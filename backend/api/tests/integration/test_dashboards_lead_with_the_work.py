"""Each dashboard leads with the work its role can do (UX review 2026-10-05).

* The DPO's queues ran rights requests first and the tickets already past
  their date below them; the overdue work now leads.
* A DCO or RCO with nothing failing saw a clear queue and an activity log,
  and nothing to start: approved projects ready to collect are now listed.
* An R&D user's projects waiting on the DPO were nowhere on the page; they
  are listed apart from the ones that need the user.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.api.routers.v1 import dashboard
from cmp.core.permissions import Role
from cmp.db.sql import fetch_one

pytestmark = pytest.mark.integration


async def test_the_dpo_sees_overdue_work_before_the_rest(conn: Any, seeded: dict[str, Any]) -> None:
    data = await dashboard._dpo(conn)
    names = [q["name"] for q in data["queues"]]
    assert names[0] == "Tickets past their date"
    assert names.index("Rights requests, soonest due first") == 1
    assert names[-1] == "Drafts whose purposes are not activated"


@pytest.mark.parametrize("role", [Role.DCO, Role.RCO])
async def test_a_collector_on_a_quiet_day_sees_what_they_can_start(
    conn: Any, seeded: dict[str, Any], role: Role
) -> None:
    owner = seeded["users"]["dco" if role is Role.DCO else "rco"]["id"]
    if role is Role.RCO:
        await conn.execute(
            "UPDATE project SET dco_user_id = %s WHERE project_id = %s",
            (owner, seeded["project"]["project_id"]),
        )
    data = await dashboard._dco(conn, owner, role=role)
    ready = next(q for q in data["queues"] if q["name"] == "Approved projects ready to collect")
    assert str(seeded["project"]["project_uuid"]) in {
        str(i["project_uuid"]) for i in ready["items"]
    }


async def test_r_and_d_sees_what_is_waiting_on_the_dpo_apart(
    conn: Any, seeded: dict[str, Any]
) -> None:
    rnd = seeded["users"]["rnd_user"]["id"]
    waiting = await fetch_one(
        conn,
        """INSERT INTO project (project_name, description, created_by, project_status)
           VALUES ('Waiting on review', 'd', %s, 'pending_approval') RETURNING project_uuid""",
        (rnd,),
    )
    data = await dashboard._rnd(conn, rnd)
    queues = {q["name"]: q["items"] for q in data["queues"]}
    assert str(waiting["project_uuid"]) in {
        str(i["project_uuid"]) for i in queues["Waiting for DPO review"]
    }
    assert str(waiting["project_uuid"]) not in {
        str(i["project_uuid"]) for i in queues["Needs your action"]
    }
