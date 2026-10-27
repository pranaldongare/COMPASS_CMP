"""An officer's ALL is the office's all (ADR 0032).

The DPO's scope on a project, a notice, a link, a purpose, a request or a
breach is every row - every row *of the DPO office*. These tests take the
repositories' own scoped lookups, which compile the DPO's ALL into an
unfiltered WHERE, and run them on a connection set to the other office: the
row is not found, so the route that called them would answer 404, the same
answer as a uuid that never existed.

As in the enforcement tests, the connection acts as a role the policies bind;
the suite's own user is a superuser, which no policy binds.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from cmp.core.errors import NotFound
from cmp.core.permissions import Role
from cmp.db.repositories import breaches as breach_repo
from cmp.db.repositories import consent as consent_repo
from cmp.db.repositories import notices as notice_repo
from cmp.db.repositories import projects as project_repo
from cmp.db.repositories import registry as registry_repo

pytestmark = pytest.mark.integration


@pytest.fixture
async def as_office(conn: Any) -> Any:
    """Switch the test's connection to a policed role in an office."""
    name = f"cmp_office_scope_{uuid.uuid4().hex[:12]}"
    await conn.execute(f"CREATE ROLE {name} NOLOGIN NOSUPERUSER NOBYPASSRLS")
    await conn.execute(f"GRANT USAGE ON SCHEMA public TO {name}")
    await conn.execute(f"GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO {name}")

    async def switch(office: str) -> None:
        await conn.execute(f"SET LOCAL ROLE {name}")
        await conn.execute("SELECT set_config('app.office', %s, true)", (office,))

    return switch


async def _dpo_office_breach(conn: Any, seeded: dict[str, Any]) -> str:
    cur = await conn.execute(
        """INSERT INTO breach (reference, title, detected_at, location_kind, recorded_by,
                               office_id)
           VALUES ('INC-SCOPE', 'SE::scope', now(), 'platform', %s,
                   (SELECT office_id FROM office WHERE office_code = 'rnd'))
           RETURNING breach_uuid""",
        (seeded["users"]["dpo"]["id"],),
    )
    row = await cur.fetchone()
    assert row is not None
    return str(row["breach_uuid"])


class TestTheLegalOfficeCannotReachTheDpoOffice:
    async def test_a_project_is_not_found(
        self, conn: Any, seeded: dict[str, Any], as_office: Any
    ) -> None:
        await as_office("hr")
        with pytest.raises(NotFound):
            await project_repo.require(
                conn,
                str(seeded["project"]["project_uuid"]),
                role=Role.DPO,
                user_id=seeded["users"]["dpo"]["id"],
            )

    async def test_a_notice_is_not_found(
        self, conn: Any, seeded: dict[str, Any], as_office: Any
    ) -> None:
        await as_office("hr")
        found = await notice_repo.by_uuid(
            conn,
            str(seeded["notice"]["notice_uuid"]),
            role=Role.DPO,
            user_id=seeded["users"]["dpo"]["id"],
        )
        assert found is None

    async def test_a_link_is_not_found(
        self, conn: Any, seeded: dict[str, Any], as_office: Any
    ) -> None:
        await as_office("hr")
        found = await consent_repo.link_by_uuid(
            conn,
            str(seeded["link"]["link_uuid"]),
            role=Role.DPO,
            user_id=seeded["users"]["dpo"]["id"],
        )
        assert found is None

    async def test_a_purpose_is_not_found(
        self, conn: Any, seeded: dict[str, Any], as_office: Any
    ) -> None:
        await as_office("hr")
        assert (
            await registry_repo.purpose_by_uuid(conn, str(seeded["purpose"]["purpose_uuid"]))
            is None
        )

    async def test_a_breach_is_not_found(
        self, conn: Any, seeded: dict[str, Any], as_office: Any
    ) -> None:
        breach_uuid = await _dpo_office_breach(conn, seeded)
        await as_office("hr")
        assert await breach_repo.by_uuid(conn, breach_uuid) is None


class TestTheDpoOfficeStillReachesItsOwn:
    """The control has to permit the legitimate case, or it is only an outage."""

    async def test_its_project_is_found(
        self, conn: Any, seeded: dict[str, Any], as_office: Any
    ) -> None:
        await as_office("rnd")
        found = await project_repo.require(
            conn,
            str(seeded["project"]["project_uuid"]),
            role=Role.DPO,
            user_id=seeded["users"]["dpo"]["id"],
        )
        assert found["project_id"] == seeded["project"]["project_id"]

    async def test_its_breach_is_found(
        self, conn: Any, seeded: dict[str, Any], as_office: Any
    ) -> None:
        breach_uuid = await _dpo_office_breach(conn, seeded)
        await as_office("rnd")
        assert await breach_repo.by_uuid(conn, breach_uuid) is not None
