"""The Legal office's registry: categories, their processors, the HR PoCs (0052).

The Legal PoC keeps the categories of their office and names the processors
that hold each one's data; the administrator assigns HR PoCs to them; an HR
PoC reads only the categories assigned to them. Each office's purposes and
templates stay its own: a Legal office template names a category, a DPO
office template none.

The suite connects as a superuser, which no policy binds, so what keeps an
office's rows from the other office here is the query's own predicate
(`cmp_office_visible`) - the mechanism, with the policies as the backstop
(ADR 0032). Setting `app.office` on the test's connection is how an officer's
session reads.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.core.permissions import Role
from cmp.db.repositories import audit as audit_repo
from cmp.db.repositories import hr_categories as repo
from cmp.db.repositories import registry as registry_repo
from cmp.db.sql import fetch_all, fetch_one
from cmp.domain.hr import categories
from cmp.domain.notices import templates
from cmp.domain.registry import service as registry
from cmp.domain.users import service as users
from tests.conftest import hashed, office_of

pytestmark = pytest.mark.integration

PURPOSE = {
    "purpose_code": "P-HR-WELL",
    "name": "Wellness programme",
    "description": "Running the wellness programme.",
    "uses": "Scheduling sessions and measuring take-up.",
    "lawful_basis": "consent_s6",
    "s7_clause": None,
    "data_categories": ["name", "health_questionnaire"],
    "retention_period": "1 year",
    "retention_basis": "business_policy",
    "erasure_trigger": "withdrawal",
    "consent_validity_period": None,
    "cross_border_permitted": False,
    "permitted_for_minors": False,
    "lapse_behaviour": "erase",
}

TEMPLATE = {
    "title": "Wellness sessions",
    "withdraw_url": "https://example.org/withdraw",
    "exercise_rights_url": "https://example.org/rights",
    "board_complaint_url": "https://example.org/board",
    "dpo_contact": "legal@example.org",
}


async def _staff(conn: Any, role: str, email: str) -> dict[str, Any]:
    row = await fetch_one(
        conn,
        """INSERT INTO auth_user (full_name, email, email_hash, role, status, office_id)
           VALUES (%s, %s, %s, %s::user_role, 'active',
                   (SELECT office_id FROM office WHERE office_code = %s))
           RETURNING id, uuid""",
        (f"Test {role}", email, hashed("email", email), role, office_of(role)),
    )
    assert row is not None
    return row


async def _as(conn: Any, office: str) -> None:
    """Read as a session of this office reads."""
    await conn.execute("SELECT set_config('app.office', %s, true)", (office,))


@pytest.fixture
async def hr(conn: Any, seeded: dict[str, Any]) -> dict[str, Any]:
    """Codes of this test's own: the suite shares the development database,
    whose seed has its WELLNESS and CSR (and codes are unique)."""
    tag = uuid.uuid4().hex[:8].upper()
    legal = await _staff(conn, Role.LEGAL.value, "legal@test.local")
    poc = await _staff(conn, Role.HR_USER.value, "hrpoc@test.local")
    wellness = await categories.create(
        conn,
        category_code=f"WELLNESS_{tag}",
        name="Employee wellness",
        description=None,
        office="hr",
        actor_id=int(legal["id"]),
    )
    csr = await categories.create(
        conn,
        category_code=f"CSR_{tag}",
        name="Corporate social responsibility",
        description=None,
        office="hr",
        actor_id=int(legal["id"]),
    )
    return {"legal": legal, "poc": poc, "wellness": wellness, "csr": csr}


class TestTheLegalPocKeepsTheirRegistry:
    async def test_a_category_with_two_processors_and_an_active_purpose(
        self, conn: Any, seeded: dict[str, Any], hr: dict[str, Any], request_context: Any
    ) -> None:
        legal = int(hr["legal"]["id"])
        wellness = str(hr["wellness"]["category_uuid"])
        held = await categories.set_processors(
            conn,
            wellness,
            processors=[
                {
                    "processor_uuid": str(seeded["processors"]["in_house"]["processor_uuid"]),
                    "processor_role": "hrms",
                    "respondent_user_uuid": str(hr["legal"]["uuid"]),
                },
                {
                    "processor_uuid": str(seeded["processors"]["external"]["processor_uuid"]),
                    "processor_role": "vendor",
                },
            ],
            role=Role.LEGAL,
            actor_id=legal,
        )
        assert [p["processor_role"] for p in held] == ["hrms", "vendor"]
        assert held[0]["respondent_uuid"] == hr["legal"]["uuid"]
        assert held[1]["respondent_uuid"] is None, "with nobody named, the HR PoC answers"

        purpose = await registry.create_purpose(
            conn, fields=dict(PURPOSE), actor_id=legal, office="hr"
        )
        await registry.activate_purpose(conn, str(purpose["purpose_uuid"]))
        assert purpose["office_code"] == "hr"

        await _as(conn, "hr")
        assert await registry_repo.purpose_by_uuid(conn, str(purpose["purpose_uuid"]))
        found = await repo.by_uuid(conn, wellness, role=Role.LEGAL, user_id=legal)
        assert found and found["processor_count"] == 2

        # The DPO's session: neither is there, as a uuid that never existed.
        await _as(conn, "rnd")
        assert await registry_repo.purpose_by_uuid(conn, str(purpose["purpose_uuid"])) is None
        assert await repo.by_uuid(conn, wellness, role=Role.LEGAL, user_id=legal) is None

    async def test_a_dropped_processor_is_removed_by_date_not_deleted(
        self, conn: Any, seeded: dict[str, Any], hr: dict[str, Any], request_context: Any
    ) -> None:
        legal = int(hr["legal"]["id"])
        wellness = str(hr["wellness"]["category_uuid"])
        vendor = str(seeded["processors"]["external"]["processor_uuid"])
        await categories.set_processors(
            conn,
            wellness,
            processors=[{"processor_uuid": vendor, "processor_role": "vendor"}],
            role=Role.LEGAL,
            actor_id=legal,
        )
        assert (
            await categories.set_processors(
                conn, wellness, processors=[], role=Role.LEGAL, actor_id=legal
            )
            == []
        )
        rows = await fetch_all(
            conn,
            """SELECT removed_at, removed_by FROM category_processor
                WHERE category_id = %s""",
            (hr["wellness"]["category_id"],),
        )
        assert len(rows) == 1
        assert rows[0]["removed_at"] is not None and rows[0]["removed_by"] == legal

        # Named again, it is a new row: the old one keeps its dates.
        await categories.set_processors(
            conn,
            wellness,
            processors=[{"processor_uuid": vendor, "processor_role": "database"}],
            role=Role.LEGAL,
            actor_id=legal,
        )
        rows = await fetch_all(
            conn,
            "SELECT removed_at FROM category_processor WHERE category_id = %s",
            (hr["wellness"]["category_id"],),
        )
        assert len(rows) == 2

    async def test_a_respondent_works_in_the_category_s_office(
        self, conn: Any, seeded: dict[str, Any], hr: dict[str, Any], request_context: Any
    ) -> None:
        with pytest.raises(ValidationFailed) as refused:
            await categories.set_processors(
                conn,
                str(hr["wellness"]["category_uuid"]),
                processors=[
                    {
                        "processor_uuid": str(seeded["processors"]["external"]["processor_uuid"]),
                        "processor_role": "vendor",
                        "respondent_user_uuid": str(seeded["users"]["dco"]["uuid"]),
                    }
                ],
                role=Role.LEGAL,
                actor_id=int(hr["legal"]["id"]),
            )
        assert refused.value.field == "respondent_user_uuid"

    async def test_a_retired_category_keeps_its_processors(
        self, conn: Any, seeded: dict[str, Any], hr: dict[str, Any], request_context: Any
    ) -> None:
        legal = int(hr["legal"]["id"])
        wellness = str(hr["wellness"]["category_uuid"])
        retired = await categories.set_status(
            conn, wellness, status="retired", role=Role.LEGAL, user_id=legal
        )
        assert retired["status"] == "retired" and retired["retired_at"] is not None
        with pytest.raises(Conflict):
            await categories.set_processors(
                conn, wellness, processors=[], role=Role.LEGAL, actor_id=legal
            )
        with pytest.raises(Conflict):
            await categories.set_status(
                conn, wellness, status="retired", role=Role.LEGAL, user_id=legal
            )

    async def test_a_code_is_taken_once(
        self, conn: Any, hr: dict[str, Any], request_context: Any
    ) -> None:
        with pytest.raises(Conflict) as taken:
            await categories.create(
                conn,
                category_code=hr["csr"]["category_code"],
                name="Again",
                description=None,
                office="hr",
                actor_id=int(hr["legal"]["id"]),
            )
        assert taken.value.code == "category_code_taken"


class TestAnHrPocSeesTheirCategories:
    async def test_assigned_to_wellness_they_list_it_and_not_csr(
        self, conn: Any, seeded: dict[str, Any], hr: dict[str, Any], request_context: Any
    ) -> None:
        admin = int(seeded["users"]["admin"]["id"])
        poc = hr["poc"]
        assigned = await categories.set_user_categories(
            conn,
            str(poc["uuid"]),
            category_uuids=[str(hr["wellness"]["category_uuid"])],
            actor_id=admin,
            actor_role=Role.ADMIN.value,
        )
        assert [c["category_code"] for c in assigned] == [hr["wellness"]["category_code"]]

        await _as(conn, "hr")
        listed = await repo.list_categories(conn, role=Role.HR_USER, user_id=int(poc["id"]))
        assert [c["category_code"] for c in listed] == [hr["wellness"]["category_code"]]
        assert (
            await repo.by_uuid(
                conn, str(hr["csr"]["category_uuid"]), role=Role.HR_USER, user_id=int(poc["id"])
            )
            is None
        ), "a category not assigned is not there for them"

        # The Legal PoC reads both; the HR PoC appears on the category.
        everything = await repo.list_categories(
            conn, role=Role.LEGAL, user_id=int(hr["legal"]["id"])
        )
        assert {hr["wellness"]["category_code"], hr["csr"]["category_code"]} <= {
            c["category_code"] for c in everything
        }
        pocs = await repo.pocs_of(conn, int(hr["wellness"]["category_id"]))
        assert [p["uuid"] for p in pocs] == [poc["uuid"]]

    async def test_only_an_hr_poc_is_assigned(
        self, conn: Any, seeded: dict[str, Any], hr: dict[str, Any], request_context: Any
    ) -> None:
        with pytest.raises(ValidationFailed):
            await categories.set_user_categories(
                conn,
                str(seeded["users"]["dco"]["uuid"]),
                category_uuids=[str(hr["wellness"]["category_uuid"])],
                actor_id=int(seeded["users"]["admin"]["id"]),
                actor_role=Role.ADMIN.value,
            )

    async def test_a_role_change_ends_the_assignments(
        self, conn: Any, seeded: dict[str, Any], hr: dict[str, Any], request_context: Any, sent: Any
    ) -> None:
        admin = int(seeded["users"]["admin"]["id"])
        poc = hr["poc"]
        await categories.set_user_categories(
            conn,
            str(poc["uuid"]),
            category_uuids=[str(hr["wellness"]["category_uuid"])],
            actor_id=admin,
            actor_role=Role.ADMIN.value,
        )
        await users.change_role(
            conn, str(poc["uuid"]), role=Role.LEGAL.value, reason=None, actor_id=admin
        )
        assert await repo.categories_of_user(conn, int(poc["id"])) == []


class TestEachOfficeSTemplates:
    async def test_a_legal_template_names_its_category(
        self, conn: Any, hr: dict[str, Any], request_context: Any
    ) -> None:
        legal = int(hr["legal"]["id"])
        with pytest.raises(ValidationFailed) as refused:
            await templates.create(conn, actor_id=legal, office="hr", role="legal", **TEMPLATE)
        assert refused.value.field == "category_uuid"

        made = await templates.create(
            conn,
            actor_id=legal,
            office="hr",
            role="legal",
            category_uuid=str(hr["wellness"]["category_uuid"]),
            **TEMPLATE,
        )
        assert made["office_code"] == "hr"
        assert made["category_code"] == hr["wellness"]["category_code"]

    async def test_a_dpo_template_has_none(
        self, conn: Any, seeded: dict[str, Any], hr: dict[str, Any], request_context: Any
    ) -> None:
        with pytest.raises(ValidationFailed) as refused:
            await templates.create(
                conn,
                actor_id=int(seeded["users"]["dpo"]["id"]),
                office="rnd",
                role="dpo",
                category_uuid=str(hr["wellness"]["category_uuid"]),
                **TEMPLATE,
            )
        assert refused.value.field == "category_uuid"

    async def test_the_database_holds_the_same_rule(
        self, conn: Any, seeded: dict[str, Any], hr: dict[str, Any]
    ) -> None:
        import psycopg

        with pytest.raises(psycopg.errors.CheckViolation):
            async with conn.transaction():
                await conn.execute(
                    """INSERT INTO notice_template (title, withdraw_url, exercise_rights_url,
                                                    board_complaint_url, dpo_contact,
                                                    created_by, office_id, category_id)
                       VALUES ('x', 'https://x', 'https://x', 'https://x', 'dpo@x',
                               %s, (SELECT office_id FROM office WHERE office_code = 'rnd'), %s)""",
                    (seeded["users"]["dpo"]["id"], hr["wellness"]["category_id"]),
                )

    async def test_a_legal_template_is_never_copied_onto_a_project(
        self, conn: Any, seeded: dict[str, Any], hr: dict[str, Any], request_context: Any
    ) -> None:
        made = await templates.create(
            conn,
            actor_id=int(hr["legal"]["id"]),
            office="hr",
            role="legal",
            category_uuid=str(hr["wellness"]["category_uuid"]),
            **TEMPLATE,
        )
        with pytest.raises(NotFound):
            await templates.apply(
                conn,
                project_uuid=str(seeded["project"]["project_uuid"]),
                template_code=made["template_code"],
                actor_id=int(seeded["users"]["rnd_user"]["id"]),
                role=Role.RND_USER.value,
            )

    async def test_a_template_carries_its_own_office_s_purposes(
        self, conn: Any, seeded: dict[str, Any], hr: dict[str, Any], request_context: Any
    ) -> None:
        made = await templates.create(
            conn,
            actor_id=int(hr["legal"]["id"]),
            office="hr",
            role="legal",
            category_uuid=str(hr["wellness"]["category_uuid"]),
            **TEMPLATE,
        )
        with pytest.raises(NotFound):
            await templates.attach_purpose(
                conn, made, purpose_uuid=str(seeded["purpose"]["purpose_uuid"])
            )

    async def test_each_office_lists_its_own(
        self, conn: Any, seeded: dict[str, Any], hr: dict[str, Any], request_context: Any
    ) -> None:
        from cmp.db.repositories import notice_templates as template_repo

        await templates.create(
            conn,
            actor_id=int(hr["legal"]["id"]),
            office="hr",
            role="legal",
            category_uuid=str(hr["wellness"]["category_uuid"]),
            **TEMPLATE,
        )
        await templates.create(
            conn, actor_id=int(seeded["users"]["dpo"]["id"]), office="rnd", role="dpo", **TEMPLATE
        )
        await _as(conn, "hr")
        assert {t["office_code"] for t in await template_repo.list_all(conn)} == {"hr"}
        await _as(conn, "rnd")
        assert {t["office_code"] for t in await template_repo.list_all(conn)} == {"rnd"}


class TestTheTrailAndTheFeedKeepToTheOffice:
    async def test_a_category_s_events_are_on_legal_s_trail(
        self, conn: Any, hr: dict[str, Any], request_context: Any
    ) -> None:
        row = await fetch_one(
            conn,
            """SELECT log_uuid, detail_json->>'office' AS office FROM audit_log
                WHERE event_type = 'hr_category.created' AND entity_id = %s""",
            (hr["wellness"]["category_id"],),
        )
        assert row and row["office"] == "hr"
        assert await audit_repo.by_uuid(conn, str(row["log_uuid"]), office="hr")
        assert await audit_repo.by_uuid(conn, str(row["log_uuid"]), office="rnd") is None

    async def test_an_assignment_is_on_legal_s_trail(
        self, conn: Any, seeded: dict[str, Any], hr: dict[str, Any], request_context: Any
    ) -> None:
        await categories.set_user_categories(
            conn,
            str(hr["poc"]["uuid"]),
            category_uuids=[str(hr["wellness"]["category_uuid"])],
            actor_id=int(seeded["users"]["admin"]["id"]),
            actor_role=Role.ADMIN.value,
        )
        row = await fetch_one(
            conn,
            """SELECT detail_json FROM audit_log
                WHERE event_type = 'user.categories_set' AND entity_id = %s""",
            (hr["poc"]["id"],),
        )
        assert row and row["detail_json"]["office"] == "hr"
        assert row["detail_json"]["to"] == [hr["wellness"]["category_code"]]


class TestARoleWorksInItsTrack:
    """Open point F-20: a role of one track is held to that track's office."""

    async def test_a_legal_poc_is_refused_the_dpo_office(
        self, conn: Any, request_context: Any, sent: Any
    ) -> None:
        rnd = await fetch_one(conn, "SELECT office_uuid FROM office WHERE office_code = 'rnd'")
        assert rnd
        with pytest.raises(ValidationFailed) as refused:
            await users.create_staff(
                conn,
                full_name="Legal In Rnd",
                email="legal.rnd@test.local",
                role=Role.LEGAL.value,
                username=None,
                mobile=None,
                organization_id=None,
                person_type="employee",
                source_uuids=[],
                office_uuid=str(rnd["office_uuid"]),
            )
        assert refused.value.field == "office_uuid"

    async def test_a_move_across_tracks_names_the_new_office(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, sent: Any
    ) -> None:
        dco = seeded["users"]["dco"]
        with pytest.raises(ValidationFailed):
            # The account's office is the DPO's, which an HR PoC does not keep.
            await users.change_role(
                conn,
                str(dco["uuid"]),
                role=Role.HR_USER.value,
                reason=None,
                actor_id=int(seeded["users"]["admin"]["id"]),
            )
