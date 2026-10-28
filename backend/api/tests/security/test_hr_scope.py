"""The Legal office's registry is the Legal office's (0052, ADR 0032, 0033).

Three walls, each tested on its own: the guard (the DPO holds no grant on a
category, and is told it is not there), the query (each read carries the
office, which is all that stands between offices where the policies do not
bind - local development, and this suite's superuser), and the policy (a
role the policies bind reads no other office's category, template, or a
category's processors).
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from cmp.api.dependencies.authorization import RequireResource
from cmp.core.errors import HiddenFromRole
from cmp.core.permissions import Role
from cmp.db.repositories import hr_categories as category_repo
from cmp.db.repositories import notice_templates as template_repo
from cmp.db.sql import fetch_one

pytestmark = pytest.mark.integration


class _Caller:
    def __init__(self, role: Role) -> None:
        self.role = role


async def _category(conn: Any, seeded: dict[str, Any]) -> dict[str, Any]:
    row = await fetch_one(
        conn,
        """INSERT INTO hr_category (category_code, name, office_id, created_by)
           VALUES ('SCOPE_TEST', 'Scope', (SELECT office_id FROM office WHERE office_code = 'hr'),
                   %s)
           RETURNING category_id, category_uuid""",
        (seeded["users"]["dpo"]["id"],),
    )
    assert row is not None
    await conn.execute(
        """INSERT INTO category_processor (category_id, processor_id, processor_role, added_by)
           VALUES (%s, %s, 'vendor', %s)""",
        (
            row["category_id"],
            seeded["processors"]["external"]["processor_id"],
            seeded["users"]["dpo"]["id"],
        ),
    )
    return row


async def _rnd_template(conn: Any, seeded: dict[str, Any]) -> str:
    row = await fetch_one(
        conn,
        """INSERT INTO notice_template (title, withdraw_url, exercise_rights_url,
                                        board_complaint_url, dpo_contact, created_by, office_id)
           VALUES ('DPO template', 'https://x/w', 'https://x/r', 'https://dpb.gov.in',
                   'dpo@test.local', %s, (SELECT office_id FROM office WHERE office_code = 'rnd'))
           RETURNING template_uuid""",
        (seeded["users"]["dpo"]["id"],),
    )
    assert row is not None
    return str(row["template_uuid"])


class TestTheGuard:
    @pytest.mark.parametrize("role", [Role.DPO, Role.DCO, Role.RND_USER, Role.DATA_SUBJECT])
    async def test_a_role_with_no_grant_is_told_there_is_nothing(self, role: Role) -> None:
        with pytest.raises(HiddenFromRole):
            await RequireResource("hr_category", hidden=True)(_Caller(role))  # type: ignore[arg-type]

    @pytest.mark.parametrize("role", [Role.LEGAL, Role.HR_USER, Role.ADMIN])
    async def test_the_roles_with_a_grant_pass(self, role: Role) -> None:
        caller = _Caller(role)
        assert await RequireResource("hr_category", hidden=True)(caller) is caller  # type: ignore[arg-type]


class TestTheQuery:
    """On the suite's own connection, which no policy binds."""

    async def test_the_dpo_office_reads_no_category(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        made = await _category(conn, seeded)
        await conn.execute("SELECT set_config('app.office', 'rnd', true)")
        # Even under a role whose grant is every row: ALL is the office's all.
        found = await category_repo.by_uuid(
            conn, str(made["category_uuid"]), role=Role.LEGAL, user_id=0
        )
        assert found is None
        listed = await category_repo.list_categories(conn, role=Role.ADMIN, user_id=0)
        assert {c["office_code"] for c in listed} <= {"rnd"}

    async def test_a_legal_session_reads_no_dpo_template(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        template_uuid = await _rnd_template(conn, seeded)
        await conn.execute("SELECT set_config('app.office', 'hr', true)")
        assert await template_repo.by_uuid(conn, template_uuid) is None
        assert template_uuid not in {
            str(t["template_uuid"]) for t in await template_repo.list_all(conn)
        }


class TestThePolicy:
    """As a role the policies bind, with no predicate in the query at all."""

    @pytest.fixture
    async def probe(self, conn: Any) -> str:
        name = f"cmp_hr_scope_{uuid.uuid4().hex[:12]}"
        await conn.execute(f"CREATE ROLE {name} NOLOGIN NOSUPERUSER NOBYPASSRLS")
        await conn.execute(f"GRANT USAGE ON SCHEMA public TO {name}")
        await conn.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {name}")
        return name

    async def _as(self, conn: Any, probe: str, office: str) -> None:
        await conn.execute(f"SET LOCAL ROLE {probe}")
        await conn.execute("SELECT set_config('app.office', %s, true)", (office,))

    async def test_a_category_and_its_processors_stay_in_the_legal_office(
        self, conn: Any, seeded: dict[str, Any], probe: str
    ) -> None:
        made = await _category(conn, seeded)
        await self._as(conn, probe, "rnd")
        assert (
            await fetch_one(
                conn, "SELECT 1 FROM hr_category WHERE category_id = %s", (made["category_id"],)
            )
            is None
        )
        assert (
            await fetch_one(
                conn,
                "SELECT 1 FROM category_processor WHERE category_id = %s",
                (made["category_id"],),
            )
            is None
        )
        await self._as(conn, probe, "hr")
        assert await fetch_one(
            conn, "SELECT 1 FROM hr_category WHERE category_id = %s", (made["category_id"],)
        )

    async def test_a_dpo_template_stays_in_the_dpo_office(
        self, conn: Any, seeded: dict[str, Any], probe: str
    ) -> None:
        template_uuid = await _rnd_template(conn, seeded)
        await self._as(conn, probe, "hr")
        assert (
            await fetch_one(
                conn, "SELECT 1 FROM notice_template WHERE template_uuid = %s", (template_uuid,)
            )
            is None
        )
