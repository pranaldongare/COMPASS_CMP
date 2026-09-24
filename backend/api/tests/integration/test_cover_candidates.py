"""Who a member of staff can hand their work to.

The cover form asked `GET /users` for colleagues in the caller's role, and only
the DPO and the administrator may read the users register - so a DCO, a DCO
Admin or an RCO was always told there was nobody to delegate to, whoever
existed. `GET /delegations/candidates` answers the one question the form has,
for whoever may arrange cover: the active accounts in my role, not me.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.db.repositories import delegations as repo
from tests.conftest import hashed

pytestmark = pytest.mark.integration


async def _staff(conn: Any, role: str, email: str, status: str = "active") -> Any:
    return await (
        await conn.execute(
            """INSERT INTO auth_user (full_name, email, email_hash, role, status)
               VALUES (%s, %s, %s, %s::user_role, %s::user_status) RETURNING id, uuid""",
            (f"Colleague {email}", email, hashed("email", email), role, status),
        )
    ).fetchone()


async def test_a_dco_is_offered_the_other_active_dcos_and_nobody_else(
    conn: Any, seeded: dict[str, Any]
) -> None:
    me = seeded["users"]["dco"]
    other = await _staff(conn, "dco", "dco-two@test.local")
    await _staff(conn, "dco", "dco-gone@test.local", status="suspended")
    await _staff(conn, "rco", "rco-two@test.local")

    offered = {
        str(r["uuid"]) for r in await repo.cover_candidates(conn, role="dco", user_id=me["id"])
    }

    assert str(other["uuid"]) in offered
    assert str(me["uuid"]) not in offered, "nobody covers for themselves"
    roles = {
        r["role"]
        for r in await (
            await conn.execute(
                "SELECT role::text AS role FROM auth_user WHERE uuid = ANY(%s::uuid[])",
                (list(offered),),
            )
        ).fetchall()
    }
    assert roles == {"dco"}, "same role only"
    statuses = {
        r["status"]
        for r in await (
            await conn.execute(
                "SELECT status::text AS status FROM auth_user WHERE uuid = ANY(%s::uuid[])",
                (list(offered),),
            )
        ).fetchall()
    }
    assert statuses == {"active"}
