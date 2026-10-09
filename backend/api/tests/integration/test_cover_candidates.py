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


# ------------------------------------------------- every staff role (2026-10-09)
async def _grant(conn: Any, delegator: Any, delegate: Any, *, actor: Any, actor_role: str) -> Any:
    from cmp.domain.delegations import service

    return await service.grant(
        conn,
        delegator_uuid=str(delegator["uuid"]),
        delegate_uuid=str(delegate["uuid"]),
        reason=None,
        starts_at=None,
        ends_at=None,
        actor_id=int(actor["id"]),
        actor_role=actor_role,
    )


@pytest.mark.parametrize(
    ("role", "grants_access"),
    [("rco", True), ("dco_admin", False), ("admin", False)],
)
async def test_every_assigned_or_office_role_may_arrange_cover(
    conn: Any, seeded: dict[str, Any], request_context: Any, role: str, grants_access: bool
) -> None:
    """An RCO's rows are assigned, so cover reaches them; a DCO Admin's and an
    administrator's reach is not per assignment, so their cover is a record."""
    me = await _staff(conn, role, f"{role}-one@test.local")
    other = await _staff(conn, role, f"{role}-two@test.local")
    granted = await _grant(conn, me, other, actor=me, actor_role=role)
    assert granted["grants_access"] is grants_access


async def test_an_rnd_user_still_cannot(
    conn: Any, seeded: dict[str, Any], request_context: Any
) -> None:
    from cmp.core.errors import ValidationFailed

    me = await _staff(conn, "rnd_user", "rnd-one@test.local")
    other = await _staff(conn, "rnd_user", "rnd-two@test.local")
    with pytest.raises(ValidationFailed):
        await _grant(conn, me, other, actor=me, actor_role="rnd_user")


async def test_an_administrator_arranges_cover_for_somebody_else(
    conn: Any, seeded: dict[str, Any], request_context: Any
) -> None:
    from cmp.core.errors import Forbidden
    from cmp.domain.delegations import service

    admin = seeded["users"]["admin"]
    away = seeded["users"]["dco"]
    other = await _staff(conn, "dco", "dco-cover@test.local")
    offered = await service.cover_candidates(
        conn, role="admin", user_id=int(admin["id"]), for_user=str(away["uuid"])
    )
    uuids = {str(r["uuid"]) for r in offered}
    assert str(other["uuid"]) in uuids and str(away["uuid"]) not in uuids

    granted = await _grant(conn, away, other, actor=admin, actor_role="admin")
    assert granted["grants_access"] is True

    with pytest.raises(Forbidden):
        await service.cover_candidates(
            conn, role="dco", user_id=int(other["id"]), for_user=str(away["uuid"])
        )
