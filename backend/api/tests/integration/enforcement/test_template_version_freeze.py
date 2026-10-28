"""What the database holds of the HR track's versions and activities (0053).

Raw SQL throughout, past the services, as the other enforcement tests are:
an approved template version never changes but to retire; an activity names
an approved version of a template in its own category, checked when it is
written and when its version changes and at no other update (open point
F-1); an R&D project names none of it; a purpose on an activity's notice is
on its version's list.
"""

from __future__ import annotations

from typing import Any

import psycopg
import pytest

from cmp.domain.notices import versions
from tests.integration.hr_world import approved_version, legal_office

pytestmark = pytest.mark.integration


@pytest.fixture
async def world(conn: Any, seeded: dict[str, Any], request_context: Any) -> dict[str, Any]:
    made = await legal_office(conn, seeded)
    made["version"] = await approved_version(conn, made)
    return made


async def _refused(conn: Any, sql: str, params: Any, error: type[Exception]) -> None:
    with pytest.raises(error):
        async with conn.transaction():
            await conn.execute(sql, params)


async def _activity(conn: Any, world: dict[str, Any], version_id: int) -> int:
    cur = await conn.execute(
        """INSERT INTO project (project_name, description, created_by, project_status,
                                office_id, category_id, template_version_id,
                                activity_description)
           VALUES ('Wellness week', 'd', %s, 'in_draft',
                   (SELECT office_id FROM office WHERE office_code = 'hr'), %s, %s,
                   'A week of sessions.')
           RETURNING project_id""",
        (world["poc"]["id"], world["category"]["category_id"], version_id),
    )
    return int((await cur.fetchone())["project_id"])


class TestAnApprovedVersionIsFrozen:
    @pytest.mark.parametrize(
        ("column", "value"),
        [
            ("slot_max_length", 500),
            ("reconsent_required", True),
            ("withdraw_url", "'https://elsewhere'"),
            ("applicable_to", "'employee'"),
        ],
    )
    async def test_its_fields_do_not_change(
        self, conn: Any, world: dict[str, Any], column: str, value: Any
    ) -> None:
        await _refused(
            conn,
            f"UPDATE template_version SET {column} = {value} WHERE version_id = %s",
            (world["version"]["version_id"],),
            psycopg.errors.InsufficientPrivilege,
        )

    async def test_it_does_not_go_back_to_draft(self, conn: Any, world: dict[str, Any]) -> None:
        await _refused(
            conn,
            """UPDATE template_version SET status = 'draft', approved_at = NULL,
                      approved_by = NULL WHERE version_id = %s""",
            (world["version"]["version_id"],),
            psycopg.errors.InsufficientPrivilege,
        )

    async def test_its_text_does_not_change(self, conn: Any, world: dict[str, Any]) -> None:
        await _refused(
            conn,
            "UPDATE template_version_language SET locked_text = 'x' WHERE version_id = %s",
            (world["version"]["version_id"],),
            psycopg.errors.InsufficientPrivilege,
        )
        await _refused(
            conn,
            "DELETE FROM template_version_language WHERE version_id = %s",
            (world["version"]["version_id"],),
            psycopg.errors.InsufficientPrivilege,
        )

    async def test_its_purposes_do_not_change(self, conn: Any, world: dict[str, Any]) -> None:
        await _refused(
            conn,
            """UPDATE template_version_purpose SET is_mandatory = NOT is_mandatory
                WHERE version_id = %s""",
            (world["version"]["version_id"],),
            psycopg.errors.InsufficientPrivilege,
        )
        await _refused(
            conn,
            """INSERT INTO template_version_purpose (version_id, purpose_id)
               VALUES (%s, %s)""",
            (world["version"]["version_id"], world["purposes"]["draft"]["purpose_id"]),
            psycopg.errors.InsufficientPrivilege,
        )

    async def test_retiring_is_the_one_move_left(self, conn: Any, world: dict[str, Any]) -> None:
        await conn.execute(
            """UPDATE template_version SET status = 'retired', retired_at = now(), retired_by = %s
                WHERE version_id = %s""",
            (world["legal"]["id"], world["version"]["version_id"]),
        )
        await _refused(
            conn,
            """UPDATE template_version SET status = 'approved', retired_at = NULL,
                      retired_by = NULL WHERE version_id = %s""",
            (world["version"]["version_id"],),
            psycopg.errors.InsufficientPrivilege,
        )


class TestAnActivityNamesAnApprovedVersion:
    async def test_one_on_an_approved_version_is_written(
        self, conn: Any, world: dict[str, Any]
    ) -> None:
        assert await _activity(conn, world, int(world["version"]["version_id"]))

    async def test_one_on_a_draft_is_refused(self, conn: Any, world: dict[str, Any]) -> None:
        from cmp.domain.notices import templates

        template = await templates.require(conn, str(world["template"]["template_uuid"]))
        draft = await versions.open_version(conn, template, actor_id=int(world["legal"]["id"]))
        with pytest.raises(psycopg.errors.CheckViolation):
            async with conn.transaction():
                await _activity(conn, world, int(draft["version_id"]))

    async def test_one_without_a_version_is_refused(self, conn: Any, world: dict[str, Any]) -> None:
        await _refused(
            conn,
            """INSERT INTO project (project_name, description, created_by, project_status,
                                    office_id, category_id)
               VALUES ('No version', 'd', %s, 'in_draft',
                       (SELECT office_id FROM office WHERE office_code = 'hr'), %s)""",
            (world["poc"]["id"], world["category"]["category_id"]),
            psycopg.errors.CheckViolation,
        )

    async def test_one_in_another_category_is_refused(
        self, conn: Any, world: dict[str, Any]
    ) -> None:
        cur = await conn.execute(
            """INSERT INTO hr_category (category_code, name, office_id, created_by)
               VALUES ('OTHER_' || %s, 'Other',
                       (SELECT office_id FROM office WHERE office_code = 'hr'), %s)
               RETURNING category_id""",
            (world["tag"], world["legal"]["id"]),
        )
        other = (await cur.fetchone())["category_id"]
        await _refused(
            conn,
            """INSERT INTO project (project_name, description, created_by, project_status,
                                    office_id, category_id, template_version_id)
               VALUES ('Mismatch', 'd', %s, 'in_draft',
                       (SELECT office_id FROM office WHERE office_code = 'hr'), %s, %s)""",
            (world["poc"]["id"], other, world["version"]["version_id"]),
            psycopg.errors.CheckViolation,
        )

    async def test_a_retired_version_does_not_stop_its_activities_changing(
        self, conn: Any, world: dict[str, Any]
    ) -> None:
        """F-1: closing, renaming - any update that leaves the version alone."""
        project_id = await _activity(conn, world, int(world["version"]["version_id"]))
        await conn.execute(
            """UPDATE template_version SET status = 'retired', retired_at = now(), retired_by = %s
                WHERE version_id = %s""",
            (world["legal"]["id"], world["version"]["version_id"]),
        )
        await conn.execute(
            "UPDATE project SET project_name = 'Renamed' WHERE project_id = %s", (project_id,)
        )
        # Naming the same version again in the SET list is not a change either.
        await conn.execute(
            """UPDATE project SET template_version_id = template_version_id
                WHERE project_id = %s""",
            (project_id,),
        )

    async def test_an_r_and_d_project_names_none_of_it(
        self, conn: Any, world: dict[str, Any], seeded: dict[str, Any]
    ) -> None:
        await _refused(
            conn,
            """INSERT INTO project (project_name, description, created_by, project_status,
                                    office_id, activity_description)
               VALUES ('A study', 'd', %s, 'in_draft',
                       (SELECT office_id FROM office WHERE office_code = 'rnd'), 'x')""",
            (seeded["users"]["rnd_user"]["id"],),
            psycopg.errors.CheckViolation,
        )


class TestAnActivityNoticeCarriesItsVersionsPurposes:
    async def test_a_purpose_off_the_list_is_refused(
        self, conn: Any, world: dict[str, Any]
    ) -> None:
        project_id = await _activity(conn, world, int(world["version"]["version_id"]))
        cur = await conn.execute(
            """INSERT INTO notice (notice_code, project_id, version, withdraw_url,
                                   exercise_rights_url, board_complaint_url, dpo_contact,
                                   template_version_id)
               VALUES ('N-HR-' || %s, %s, 1, 'w', 'r', 'b', 'c', %s) RETURNING notice_id""",
            (world["tag"], project_id, world["version"]["version_id"]),
        )
        notice_id = (await cur.fetchone())["notice_id"]
        await conn.execute(
            "INSERT INTO notice_purpose (notice_id, purpose_id) VALUES (%s, %s)",
            (notice_id, world["purposes"]["sessions"]["purpose_id"]),
        )
        await _refused(
            conn,
            "INSERT INTO notice_purpose (notice_id, purpose_id) VALUES (%s, %s)",
            (notice_id, world["purposes"]["draft"]["purpose_id"]),
            psycopg.errors.CheckViolation,
        )
