"""HR activities: live as they are created, from an approved version (ADR 0033).

The HR PoC creates an activity in one transaction - project, site, notice
composed from the version and published, link - with no approval step; a
refusal anywhere leaves nothing behind. The activity keeps its version until
upgraded; an upgrade to a version flagged for re-consent asks each
participant again, after commit. Legal sees every activity; the DPO none.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.core.permissions import Role
from cmp.core.security import content_hash
from cmp.db.repositories import hr_activities as repo
from cmp.db.sql import fetch_all, fetch_one
from cmp.domain.consent import service as consent_service
from cmp.domain.hr import activities
from cmp.domain.notices import templates, versions
from cmp.domain.projects import service as project_service
from tests.integration.hr_world import approved_version, legal_office

pytestmark = pytest.mark.integration

DESCRIPTION = "Four lunchtime sessions on sleep and stress, in the Pune office in November."


@pytest.fixture
async def world(conn: Any, seeded: dict[str, Any], request_context: Any) -> dict[str, Any]:
    made = await legal_office(conn, seeded)
    made["version"] = await approved_version(conn, made)
    return made


def _in_a_week() -> datetime:
    return datetime.now(UTC) + timedelta(days=7)


async def _create(conn: Any, world: dict[str, Any], **over: Any) -> dict[str, Any]:
    args: dict[str, Any] = {
        "actor_id": int(world["poc"]["id"]),
        "role": Role.HR_USER,
        "category_uuid": str(world["category"]["category_uuid"]),
        "template_version_uuid": str(world["version"]["version_uuid"]),
        "purpose_uuids": [
            str(world["purposes"]["sessions"]["purpose_uuid"]),
            str(world["purposes"]["survey"]["purpose_uuid"]),
        ],
        "name": f"Wellness week {world['tag']}",
        "description": DESCRIPTION,
        "audience_mode": "otp",
        "link_expires_at": _in_a_week(),
    }
    args.update(over)
    return await activities.create(conn, **args)


async def _count(conn: Any, name: str) -> int:
    row = await fetch_one(
        conn, "SELECT count(*) AS n FROM project WHERE project_name = %s", (name,)
    )
    return int(row["n"]) if row else 0


class TestCreating:
    async def test_one_request_makes_the_whole_activity(
        self, conn: Any, world: dict[str, Any]
    ) -> None:
        made = await _create(conn, world, audience_mode="sso")
        assert made["url_path"].startswith("/c/")
        row = await fetch_one(
            conn,
            """SELECT p.project_id, p.project_status, p.dco_user_id, p.template_version_id,
                      (SELECT o.office_code FROM office o WHERE o.office_id = p.office_id) AS office
                 FROM project p WHERE p.project_uuid = %s""",
            (made["activity_uuid"],),
        )
        assert row["project_status"] == "approved" and row["office"] == "hr"
        assert row["dco_user_id"] == world["poc"]["id"]
        notices = await fetch_all(
            conn,
            "SELECT status, template_version_id, notice_code FROM notice WHERE project_id = %s",
            (row["project_id"],),
        )
        assert [(n["status"], n["template_version_id"]) for n in notices] == [
            ("published", world["version"]["version_id"])
        ]
        assert notices[0]["notice_code"].startswith("HR-"), "HR codes have their own namespace"
        sites = await fetch_all(
            conn,
            "SELECT dco_override_user_id FROM project_site WHERE project_id = %s",
            (row["project_id"],),
        )
        assert [s["dco_override_user_id"] for s in sites] == [world["poc"]["id"]]
        links = await fetch_all(
            conn,
            """SELECT cl.audience_mode FROM consent_link cl JOIN notice n USING (notice_id)
                WHERE n.project_id = %s""",
            (row["project_id"],),
        )
        assert [link["audience_mode"] for link in links] == ["sso"]
        events = await fetch_all(
            conn,
            """SELECT DISTINCT event_type FROM audit_log
                WHERE (entity_type = 'project' AND entity_id = %(p)s)
                   OR (entity_type = 'notice' AND entity_id IN
                         (SELECT notice_id FROM notice WHERE project_id = %(p)s))
                   OR (entity_type = 'consent_link' AND entity_id IN
                         (SELECT link_id FROM consent_link cl JOIN notice n USING (notice_id)
                           WHERE n.project_id = %(p)s))""",
            {"p": row["project_id"]},
        )
        assert {e["event_type"] for e in events} >= {
            "activity.created",
            "notice.published",
            "project.transitioned",
            "link.created",
        }

    async def test_the_notice_is_the_version_composed(
        self, conn: Any, world: dict[str, Any]
    ) -> None:
        made = await _create(conn, world)
        [lang] = await fetch_all(
            conn,
            """SELECT nl.rendered_text, nl.content_hash, nl.approved_at FROM notice_language nl
                JOIN notice n USING (notice_id) WHERE n.notice_uuid = %s""",
            (made["notice_uuid"],),
        )
        assert DESCRIPTION in lang["rendered_text"]
        assert "Wellness sessions (required)" in lang["rendered_text"]
        assert lang["content_hash"] == content_hash(lang["rendered_text"])
        assert lang["approved_at"] is not None
        preview = await versions.preview(conn, world["version"], description=DESCRIPTION)
        assert preview[0]["text"] == lang["rendered_text"], "what Legal previewed is served"

    async def test_the_mandatory_purpose_alone_is_enough(
        self, conn: Any, world: dict[str, Any]
    ) -> None:
        made = await _create(
            conn,
            world,
            purpose_uuids=[str(world["purposes"]["sessions"]["purpose_uuid"])],
        )
        rows = await fetch_all(
            conn,
            """SELECT np.is_mandatory FROM notice_purpose np JOIN notice n USING (notice_id)
                WHERE n.notice_uuid = %s""",
            (made["notice_uuid"],),
        )
        assert [r["is_mandatory"] for r in rows] == [True]


class TestRefusals:
    """Each refused before anything is written, so nothing of it exists."""

    @pytest.mark.parametrize(
        ("over", "field"),
        [
            ({"purpose_uuids": "outside"}, "purpose_uuids"),
            ({"purpose_uuids": "no-mandatory"}, "purpose_uuids"),
            ({"description": "Bring a {{mat}} along."}, "description"),
            ({"description": "Sign up at https://example.org/x"}, "description"),
            ({"description": "x" * 5000}, "description"),
        ],
    )
    async def test_a_bad_request_writes_nothing(
        self, conn: Any, world: dict[str, Any], over: dict[str, Any], field: str
    ) -> None:
        if over.get("purpose_uuids") == "outside":
            over = {
                "purpose_uuids": [
                    str(world["purposes"]["sessions"]["purpose_uuid"]),
                    str(world["purposes"]["draft"]["purpose_uuid"]),
                ]
            }
        elif over.get("purpose_uuids") == "no-mandatory":
            over = {"purpose_uuids": [str(world["purposes"]["survey"]["purpose_uuid"])]}
        name = f"Refused {world['tag']}"
        with pytest.raises(ValidationFailed) as refused:
            async with conn.transaction():
                await _create(conn, world, name=name, **over)
        assert refused.value.field == field
        assert await _count(conn, name) == 0

    async def test_a_retired_version_is_refused(self, conn: Any, world: dict[str, Any]) -> None:
        await versions.retire(conn, world["version"], actor_id=int(world["legal"]["id"]))
        with pytest.raises(Conflict) as refused:
            await _create(conn, world)
        assert refused.value.code == "version_not_approved"

    async def test_a_version_edited_by_hand_is_refused(
        self, conn: Any, world: dict[str, Any]
    ) -> None:
        # Past the freeze, as only a superuser could: the hash no longer matches.
        await conn.execute("ALTER TABLE template_version_language DISABLE TRIGGER USER")
        await conn.execute(
            "UPDATE template_version_language SET locked_text = locked_text || ' x' "
            "WHERE version_id = %s",
            (world["version"]["version_id"],),
        )
        await conn.execute("ALTER TABLE template_version_language ENABLE TRIGGER USER")
        with pytest.raises(Conflict) as refused:
            await _create(conn, world)
        assert refused.value.code == "version_tampered"

    async def test_a_category_not_assigned_is_not_there(
        self, conn: Any, world: dict[str, Any]
    ) -> None:
        await conn.execute("DELETE FROM hr_poc_category WHERE user_id = %s", (world["poc"]["id"],))
        with pytest.raises(NotFound):
            await _create(conn, world)

    async def test_the_link_expires_in_the_future(self, conn: Any, world: dict[str, Any]) -> None:
        with pytest.raises(ValidationFailed) as refused:
            await _create(conn, world, link_expires_at=datetime.now(UTC) - timedelta(days=1))
        assert refused.value.field == "link_expires_at"


class TestTheTransition:
    async def test_the_hr_poc_is_offered_approved_on_an_activity_and_nothing_else(
        self, conn: Any, world: dict[str, Any]
    ) -> None:
        made = await _create(conn, world)
        moves = await project_service.transitions_for(
            conn,
            project_uuid=str(made["activity_uuid"]),
            role=Role.HR_USER,
            user_id=int(world["poc"]["id"]),
        )
        assert moves["current"] == "approved"
        assert [m["to"] for m in moves["available"]] == ["closed"]


class TestUpgrading:
    async def _participant(self, conn: Any, seeded: dict[str, Any], made: dict[str, Any]) -> None:
        token = made["url_path"].rsplit("/", 1)[-1]
        await consent_service.serve_notice(
            conn, token=token, language_code="english", user_id=seeded["subject"]["id"]
        )
        purposes = await fetch_all(
            conn,
            """SELECT p.purpose_uuid FROM notice_purpose np JOIN notice n USING (notice_id)
                 JOIN purpose p USING (purpose_id) WHERE n.notice_uuid = %s""",
            (made["notice_uuid"],),
        )
        await consent_service.capture(
            conn,
            token=token,
            user_id=seeded["subject"]["id"],
            language_code="english",
            grants={str(p["purpose_uuid"]): True for p in purposes},
            action_type="checkbox_click",
            ip_address="203.0.113.7",
        )

    async def test_a_flagged_version_moves_the_link_and_asks_again(
        self, conn: Any, world: dict[str, Any], seeded: dict[str, Any], sent: Any
    ) -> None:
        made = await _create(conn, world)
        await self._participant(conn, seeded, made)
        old_hash = (
            await fetch_one(
                conn,
                """SELECT ca.notice_content_hash FROM consent_artefact ca
                     JOIN notice n USING (notice_id) WHERE n.notice_uuid = %s""",
                (made["notice_uuid"],),
            )
        )["notice_content_hash"]

        two = await approved_version(conn, world, reconsent_required=True)
        upgraded = await activities.upgrade(
            conn,
            str(made["activity_uuid"]),
            actor_id=int(world["poc"]["id"]),
            role=Role.HR_USER,
            template_version_uuid=str(two["version_uuid"]),
            purpose_uuids=[str(world["purposes"]["sessions"]["purpose_uuid"])],
            description=DESCRIPTION + " Now with a follow-up call.",
        )
        assert upgraded["version"] == 2
        assert upgraded["reconsent_requested"] == 1
        assert [args for name, args in sent if name.endswith("send_reconsent_request")]

        link = await fetch_one(
            conn,
            """SELECT n.notice_uuid FROM consent_link cl JOIN notice n USING (notice_id)
                WHERE cl.status = 'active' AND n.project_id =
                      (SELECT project_id FROM project WHERE project_uuid = %s)""",
            (made["activity_uuid"],),
        )
        assert str(link["notice_uuid"]) == str(upgraded["notice_uuid"]), "the link moved"
        still = await fetch_one(
            conn,
            """SELECT ca.notice_content_hash FROM consent_artefact ca
                 JOIN notice n USING (notice_id) WHERE n.notice_uuid = %s""",
            (made["notice_uuid"],),
        )
        assert still["notice_content_hash"] == old_hash, "version 1's consents keep their text"

    async def test_an_unflagged_version_asks_nobody(
        self, conn: Any, world: dict[str, Any], seeded: dict[str, Any], sent: Any
    ) -> None:
        made = await _create(conn, world)
        await self._participant(conn, seeded, made)
        two = await approved_version(conn, world)
        upgraded = await activities.upgrade(
            conn,
            str(made["activity_uuid"]),
            actor_id=int(world["poc"]["id"]),
            role=Role.HR_USER,
            template_version_uuid=str(two["version_uuid"]),
            purpose_uuids=[str(world["purposes"]["sessions"]["purpose_uuid"])],
            description=DESCRIPTION,
        )
        assert upgraded["reconsent_requested"] == 0


class TestWhoSeesIt:
    async def test_legal_sees_it_and_the_dpo_does_not(
        self, conn: Any, world: dict[str, Any], seeded: dict[str, Any]
    ) -> None:
        made = await _create(conn, world)
        await conn.execute("SELECT set_config('app.office', 'hr', true)")
        assert await repo.by_uuid(
            conn, str(made["activity_uuid"]), role=Role.LEGAL, user_id=int(world["legal"]["id"])
        )
        assert await repo.by_uuid(
            conn, str(made["activity_uuid"]), role=Role.HR_USER, user_id=int(world["poc"]["id"])
        )
        await conn.execute("SELECT set_config('app.office', 'rnd', true)")
        assert (
            await repo.by_uuid(
                conn,
                str(made["activity_uuid"]),
                role=Role.DPO,
                user_id=int(seeded["users"]["dpo"]["id"]),
            )
            is None
        )

    async def test_an_hr_poc_of_another_category_does_not_see_it(
        self, conn: Any, world: dict[str, Any], seeded: dict[str, Any]
    ) -> None:
        made = await _create(conn, world)
        other = await legal_office(conn, seeded)
        assert (
            await repo.by_uuid(
                conn,
                str(made["activity_uuid"]),
                role=Role.HR_USER,
                user_id=int(other["poc"]["id"]),
            )
            is None
        )


class TestClosing:
    async def test_the_hr_poc_closes_it_and_its_link_stops(
        self, conn: Any, world: dict[str, Any]
    ) -> None:
        made = await _create(conn, world)
        closed = await activities.close(
            conn,
            str(made["activity_uuid"]),
            actor_id=int(world["poc"]["id"]),
            role=Role.HR_USER,
            reason="The week is over.",
        )
        assert closed["to"] == "closed" and closed["links_revoked"] == 1

    async def test_a_retired_version_does_not_stop_closing(
        self, conn: Any, world: dict[str, Any]
    ) -> None:
        made = await _create(conn, world)
        await versions.retire(conn, world["version"], actor_id=int(world["legal"]["id"]))
        closed = await activities.close(
            conn,
            str(made["activity_uuid"]),
            actor_id=int(world["legal"]["id"]),
            role=Role.LEGAL,
            reason=None,
        )
        assert closed["to"] == "closed"


class TestTheOptions:
    async def test_the_wizard_offers_the_approved_versions_of_my_categories(
        self, conn: Any, world: dict[str, Any]
    ) -> None:
        offered = await activities.options(conn, role=Role.HR_USER, user_id=int(world["poc"]["id"]))
        mine = [c for c in offered if c["category_uuid"] == world["category"]["category_uuid"]]
        assert len(mine) == 1
        [version] = mine[0]["versions"]
        assert version["version_uuid"] == world["version"]["version_uuid"]
        assert [p["is_mandatory"] for p in version["purposes"]] == [True, False]
        template = await templates.require(conn, str(world["template"]["template_uuid"]))
        await versions.open_version(conn, template, actor_id=int(world["legal"]["id"]))
        again = await activities.options(conn, role=Role.HR_USER, user_id=int(world["poc"]["id"]))
        mine = [c for c in again if c["category_uuid"] == world["category"]["category_uuid"]]
        assert len(mine[0]["versions"]) == 1, "a draft is not offered"
