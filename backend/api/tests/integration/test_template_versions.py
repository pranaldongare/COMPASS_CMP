"""Template versions: Legal approves the text once (0053, ADR 0033).

Version *n* opens as a draft carrying what version *n-1* said; approval is
refused while a purpose is not active or a language lacks a slot, and
otherwise hashes every language and freezes the version; a retired version
starts nothing new. A DPO office template is not versioned.
"""

from __future__ import annotations

from typing import Any

import psycopg
import pytest

from cmp.core.errors import Conflict, ValidationFailed
from cmp.core.security import content_hash
from cmp.db.repositories import template_versions as repo
from cmp.domain.notices import templates, versions
from tests.integration.hr_world import LOCKED, approved_version, legal_office

pytestmark = pytest.mark.integration


@pytest.fixture
async def world(conn: Any, seeded: dict[str, Any], request_context: Any) -> dict[str, Any]:
    return await legal_office(conn, seeded)


async def _template(conn: Any, world: dict[str, Any]) -> dict[str, Any]:
    return await templates.require(conn, str(world["template"]["template_uuid"]))


async def _draft(conn: Any, world: dict[str, Any], *, purposes: list[dict[str, Any]]) -> Any:
    legal = int(world["legal"]["id"])
    draft = await versions.open_version(conn, await _template(conn, world), actor_id=legal)
    draft = await versions.set_language(
        conn, draft, language_code="english", locked_text=LOCKED, actor_id=legal
    )
    return await versions.set_purposes(conn, draft, purposes=purposes)


class TestApproval:
    async def test_a_draft_purpose_is_refused_by_name(
        self, conn: Any, world: dict[str, Any]
    ) -> None:
        draft = await _draft(
            conn,
            world,
            purposes=[
                {
                    "purpose_uuid": str(world["purposes"]["sessions"]["purpose_uuid"]),
                    "is_mandatory": True,
                },
                {"purpose_uuid": str(world["purposes"]["draft"]["purpose_uuid"])},
            ],
        )
        with pytest.raises(Conflict) as refused:
            await versions.approve(
                conn, await _template(conn, world), draft, actor_id=int(world["legal"]["id"])
            )
        assert refused.value.code == "purpose_not_active"
        assert world["purposes"]["draft"]["purpose_code"] in str(refused.value)

    @pytest.mark.parametrize(
        ("text", "slot"),
        [
            ("Your data: {{purposes}}.", "{{description}}"),
            ("About: {{description}}.", "{{purposes}}"),
            ("{{purposes}} {{purposes}} {{description}}", "{{purposes}}"),
        ],
    )
    async def test_a_language_without_its_slots_is_refused(
        self, conn: Any, world: dict[str, Any], text: str, slot: str
    ) -> None:
        legal = int(world["legal"]["id"])
        draft = await _draft(
            conn,
            world,
            purposes=[{"purpose_uuid": str(world["purposes"]["sessions"]["purpose_uuid"])}],
        )
        draft = await versions.set_language(
            conn, draft, language_code="english", locked_text=text, actor_id=legal
        )
        with pytest.raises(ValidationFailed) as refused:
            await versions.approve(conn, await _template(conn, world), draft, actor_id=legal)
        assert refused.value.details == {"language": "english", "placeholder": slot}

    async def test_the_english_text_is_required(self, conn: Any, world: dict[str, Any]) -> None:
        legal = int(world["legal"]["id"])
        draft = await _draft(
            conn,
            world,
            purposes=[{"purpose_uuid": str(world["purposes"]["sessions"]["purpose_uuid"])}],
        )
        draft = await versions.set_language(
            conn, draft, language_code="hindi", locked_text=LOCKED, actor_id=legal
        )
        draft = await versions.remove_language(conn, draft, language_code="english")
        with pytest.raises(ValidationFailed) as refused:
            await versions.approve(conn, await _template(conn, world), draft, actor_id=legal)
        assert refused.value.field == "languages"

    async def test_approval_hashes_and_freezes(self, conn: Any, world: dict[str, Any]) -> None:
        approved = await approved_version(conn, world)
        assert approved["status"] == "approved"
        assert approved["approved_at"] is not None
        [english] = approved["languages"]
        assert english["content_hash"] == content_hash(LOCKED)

        with pytest.raises(Conflict) as frozen:
            await versions.set_language(
                conn,
                approved,
                language_code="english",
                locked_text=LOCKED + " Changed.",
                actor_id=int(world["legal"]["id"]),
            )
        assert frozen.value.code == "version_not_draft"

        # And under the service: a raw UPDATE of the text fails at the trigger.
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            async with conn.transaction():
                await conn.execute(
                    """UPDATE template_version_language SET locked_text = 'changed'
                        WHERE version_id = %s""",
                    (approved["version_id"],),
                )

    async def test_a_version_needs_its_audience(self, conn: Any, world: dict[str, Any]) -> None:
        legal = int(world["legal"]["id"])
        draft = await _draft(
            conn,
            world,
            purposes=[{"purpose_uuid": str(world["purposes"]["sessions"]["purpose_uuid"])}],
        )
        await conn.execute(
            "UPDATE template_version SET applicable_to = NULL WHERE version_id = %s",
            (draft["version_id"],),
        )
        draft = await repo.by_id(conn, int(draft["version_id"]))
        with pytest.raises(ValidationFailed) as refused:
            await versions.approve(conn, await _template(conn, world), draft, actor_id=legal)
        assert refused.value.field == "applicable_to"


class TestTheNextVersion:
    async def test_version_two_copies_version_one_which_is_untouched(
        self, conn: Any, world: dict[str, Any]
    ) -> None:
        legal = int(world["legal"]["id"])
        one = await approved_version(conn, world)
        two = await versions.open_version(conn, await _template(conn, world), actor_id=legal)
        assert two["version"] == 2 and two["status"] == "draft"
        assert [lang["locked_text"] for lang in two["languages"]] == [LOCKED]
        assert [lang["content_hash"] for lang in two["languages"]] == [None]
        assert [(p["purpose_uuid"], p["is_mandatory"]) for p in two["purposes"]] == [
            (p["purpose_uuid"], p["is_mandatory"]) for p in one["purposes"]
        ]

        await versions.set_language(
            conn, two, language_code="english", locked_text=LOCKED + "\nNew.", actor_id=legal
        )
        again = await versions.detail(conn, one)
        assert again["status"] == "approved"
        assert again["languages"][0]["locked_text"] == LOCKED

    async def test_one_draft_at_a_time(self, conn: Any, world: dict[str, Any]) -> None:
        legal = int(world["legal"]["id"])
        await versions.open_version(conn, await _template(conn, world), actor_id=legal)
        with pytest.raises(Conflict) as refused:
            await versions.open_version(conn, await _template(conn, world), actor_id=legal)
        assert refused.value.code == "version_draft_open"

    async def test_the_first_version_takes_the_template_s_links(
        self, conn: Any, world: dict[str, Any]
    ) -> None:
        first = await versions.open_version(
            conn, await _template(conn, world), actor_id=int(world["legal"]["id"])
        )
        assert first["version"] == 1
        assert first["withdraw_url"] == world["template"]["withdraw_url"]
        assert first["dpo_contact"] == world["template"]["dpo_contact"]
        assert first["applicable_to"] == "data_subject"


class TestRetirement:
    async def test_only_an_approved_version_is_retired_and_then_stays_so(
        self, conn: Any, world: dict[str, Any]
    ) -> None:
        legal = int(world["legal"]["id"])
        approved = await approved_version(conn, world)
        retired = await versions.retire(conn, approved, actor_id=legal)
        assert retired["status"] == "retired" and retired["retired_at"] is not None
        assert retired["languages"][0]["content_hash"] == content_hash(LOCKED)
        with pytest.raises(Conflict):
            await versions.retire(conn, retired, actor_id=legal)


class TestThePreview:
    async def test_the_same_inputs_give_the_same_hash(
        self, conn: Any, world: dict[str, Any]
    ) -> None:
        approved = await approved_version(conn, world)
        first = await versions.preview(conn, approved, description="A week of sessions.")
        second = await versions.preview(conn, approved, description="A week of sessions.")
        assert first == second
        [english] = first
        assert "About this activity: A week of sessions." in english["text"]
        assert "Wellness sessions (required)" in english["text"]
        assert english["content_hash"] == content_hash(english["text"])

    async def test_a_description_with_a_link_is_refused(
        self, conn: Any, world: dict[str, Any]
    ) -> None:
        approved = await approved_version(conn, world)
        with pytest.raises(ValidationFailed):
            await versions.preview(conn, approved, description="See https://x.example")


class TestTheDpoOfficeTemplate:
    async def test_it_is_not_versioned(self, conn: Any, seeded: dict[str, Any]) -> None:
        mine = await templates.create(
            conn,
            actor_id=int(seeded["users"]["dpo"]["id"]),
            office="rnd",
            role="dpo",
            title="Gait studies",
            withdraw_url="https://x/w",
            exercise_rights_url="https://x/r",
            board_complaint_url="https://x/b",
            dpo_contact="dpo@test.local",
        )
        with pytest.raises(Conflict) as refused:
            await versions.open_version(conn, mine, actor_id=int(seeded["users"]["dpo"]["id"]))
        assert refused.value.code == "template_not_versioned"
        with pytest.raises(psycopg.errors.CheckViolation):
            async with conn.transaction():
                await conn.execute(
                    """INSERT INTO template_version (template_id, version, created_by, withdraw_url,
                                                     exercise_rights_url, board_complaint_url,
                                                     dpo_contact)
                       VALUES (%s, 1, %s, 'w', 'r', 'b', 'c')""",
                    (mine["template_id"], seeded["users"]["dpo"]["id"]),
                )


class TestTheAudit:
    async def test_approval_is_on_legal_s_trail_with_the_hashes(
        self, conn: Any, world: dict[str, Any]
    ) -> None:
        approved = await approved_version(conn, world)
        cur = await conn.execute(
            """SELECT detail_json FROM audit_log
                WHERE event_type = 'template_version.approved' AND entity_id = %s""",
            (approved["version_id"],),
        )
        row = await cur.fetchone()
        assert row["detail_json"]["office"] == "hr"
        assert row["detail_json"]["hashes"] == {"english": content_hash(LOCKED)}
