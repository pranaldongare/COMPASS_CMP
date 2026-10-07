"""Notice templates: the DPO's notices before there is a project (0044).

The DPO writes as many as they like, under IDs the database mints
(`TPL-0007`). An R&D User attaches one to their own project by that ID, which
copies it into the project's own draft notice - links, contact, audience,
purposes and text - with the template remembered. Nothing connects them after:
changing the template changes no notice. A retired template cannot be
attached; nobody attaches one to a project that is not theirs.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.core.permissions import Role
from cmp.db.repositories import notices as notice_repo
from cmp.db.sql import fetch_all
from cmp.domain.notices import templates

pytestmark = pytest.mark.integration

TEXT = "We collect your gait video to train walking-pattern models."


async def _template(conn: Any, seeded: dict[str, Any], **kw: Any) -> dict[str, Any]:
    return await templates.create(
        conn,
        actor_id=int(seeded["users"]["dpo"]["id"]),
        title=kw.pop("title", "Gait studies, adults"),
        withdraw_url="https://example.org/withdraw",
        exercise_rights_url="https://example.org/rights",
        board_complaint_url="https://example.org/board",
        dpo_contact="dpo@example.org",
        applicable_to="data_subject",
        note="Read it aloud to anyone who asks.",
        rendered_text=kw.pop("rendered_text", TEXT),
        **kw,
    )


async def _draft_project(conn: Any, creator_id: int, name: str = "Gait Study Two") -> str:
    cur = await conn.execute(
        """INSERT INTO project (project_name, description, created_by, project_status)
           VALUES (%s, 'd', %s, 'in_draft') RETURNING project_uuid""",
        (name, creator_id),
    )
    return str((await cur.fetchone())["project_uuid"])


async def test_the_dpo_writes_templates_without_a_project(
    conn: Any, seeded: dict[str, Any]
) -> None:
    first = await _template(conn, seeded)
    second = await _template(conn, seeded, title="Speech studies")
    assert first["template_code"].startswith("TPL-")
    assert first["template_code"] != second["template_code"]
    assert first["status"] == "active" and first["used_count"] == 0
    assert [lang["language_code"] for lang in first["languages"]] == ["english"]

    shown = await templates.attach_purpose(
        conn, first, purpose_uuid=str(seeded["purpose"]["purpose_uuid"]), is_mandatory=True
    )
    assert [(p["purpose_code"], p["is_mandatory"]) for p in shown["purposes"]] == [("P-TEST", True)]
    shown = await templates.set_language(
        conn, first, language_code="hindi", rendered_text="हिंदी पाठ", actor_id=1
    )
    assert {lang["language_code"] for lang in shown["languages"]} == {"english", "hindi"}
    shown = await templates.remove_language(conn, first, language_code="hindi")
    assert [lang["language_code"] for lang in shown["languages"]] == ["english"]
    shown = await templates.update(conn, first, actor_id=1, title="Gait, adults only")
    assert shown["title"] == "Gait, adults only"


async def test_an_rnd_user_attaches_one_by_its_id_as_a_copy(
    conn: Any, seeded: dict[str, Any]
) -> None:
    rnd = int(seeded["users"]["rnd_user"]["id"])
    made = await _template(conn, seeded)
    await templates.attach_purpose(
        conn, made, purpose_uuid=str(seeded["purpose"]["purpose_uuid"]), is_mandatory=True
    )
    project = await _draft_project(conn, rnd)

    # Typed as people type it: lower case, a space either side.
    notice = await templates.apply(
        conn,
        project_uuid=project,
        template_code=f"  {made['template_code'].lower()} ",
        actor_id=rnd,
        role=Role.RND_USER,
    )
    assert notice["status"] == "draft" and notice["version"] == 1
    assert notice["template_code"] == made["template_code"]
    assert notice["withdraw_url"] == "https://example.org/withdraw"
    assert notice["applicable_to"] == "data_subject"
    assert not notice["notice_code"].startswith("TPL-")
    purposes = await notice_repo.purposes_of(conn, notice["notice_id"])
    assert [(p["purpose_code"], p["is_mandatory"]) for p in purposes] == [("P-TEST", True)]
    [english] = await notice_repo.languages_of(conn, notice["notice_id"], with_text=True)
    assert english["rendered_text"] == TEXT and english["approved_at"] is None

    # A copy: the template changing changes nothing on the notice.
    await templates.set_language(
        conn, made, language_code="english", rendered_text="Something else.", actor_id=1
    )
    [still] = await notice_repo.languages_of(conn, notice["notice_id"], with_text=True)
    assert still["rendered_text"] == TEXT

    shown = await templates.detail(conn, made)
    assert shown["used_count"] == 1
    assert [n["notice_uuid"] for n in shown["notices"]] == [notice["notice_uuid"]]

    trail = await fetch_all(
        conn,
        "SELECT detail_json FROM audit_log WHERE event_type = 'notice.created' AND entity_id = %s",
        (notice["notice_id"],),
    )
    assert trail[0]["detail_json"]["from_template"] == made["template_code"]


async def test_a_template_is_attached_to_many_projects_each_with_its_own_notice(
    conn: Any, seeded: dict[str, Any]
) -> None:
    rnd = int(seeded["users"]["rnd_user"]["id"])
    made = await _template(conn, seeded)
    one = await templates.apply(
        conn,
        project_uuid=await _draft_project(conn, rnd, "Study One"),
        template_code=made["template_code"],
        actor_id=rnd,
        role=Role.RND_USER,
    )
    two = await templates.apply(
        conn,
        project_uuid=await _draft_project(conn, rnd, "Study Two"),
        template_code=made["template_code"],
        actor_id=rnd,
        role=Role.RND_USER,
    )
    assert one["notice_uuid"] != two["notice_uuid"]
    assert one["notice_code"] != two["notice_code"]
    assert (await templates.detail(conn, made))["used_count"] == 2


async def test_a_retired_template_or_an_unknown_id_is_refused(
    conn: Any, seeded: dict[str, Any]
) -> None:
    rnd = int(seeded["users"]["rnd_user"]["id"])
    made = await _template(conn, seeded)
    project = await _draft_project(conn, rnd)
    with pytest.raises(NotFound):
        await templates.apply(
            conn, project_uuid=project, template_code="TPL-9999", actor_id=rnd, role=Role.RND_USER
        )
    retired = await templates.set_status(conn, made, status="retired")
    assert retired["status"] == "retired" and retired["retired_at"] is not None
    with pytest.raises(Conflict) as refused:
        await templates.apply(
            conn,
            project_uuid=project,
            template_code=made["template_code"],
            actor_id=rnd,
            role=Role.RND_USER,
        )
    assert refused.value.code == "template_retired"
    # Found by its ID all the same, so the R&D User is told why.
    assert (await templates.find(conn, made["template_code"]))["status"] == "retired"
    back = await templates.set_status(conn, made, status="active")
    assert back["retired_at"] is None


async def test_nobody_attaches_one_to_a_project_that_is_not_theirs(
    conn: Any, seeded: dict[str, Any]
) -> None:
    made = await _template(conn, seeded)
    dpo = int(seeded["users"]["dpo"]["id"])
    someone_elses = await _draft_project(conn, dpo, "The DPO's own")
    with pytest.raises(NotFound):
        await templates.apply(
            conn,
            project_uuid=someone_elses,
            template_code=made["template_code"],
            actor_id=int(seeded["users"]["rnd_user"]["id"]),
            role=Role.RND_USER,
        )


async def test_what_a_template_will_not_take(conn: Any, seeded: dict[str, Any]) -> None:
    made = await _template(conn, seeded)
    with pytest.raises(ValidationFailed):
        await templates.set_language(
            conn, made, language_code="klingon", rendered_text="x", actor_id=1
        )
    with pytest.raises(ValidationFailed):
        await templates.set_language(
            conn, made, language_code="english", rendered_text=" ", actor_id=1
        )
    with pytest.raises(ValidationFailed):
        await templates.set_status(conn, made, status="deleted")
    await conn.execute(
        "UPDATE purpose SET status = 'retired' WHERE purpose_id = %s",
        (seeded["purpose"]["purpose_id"],),
    )
    with pytest.raises(ValidationFailed):
        await templates.attach_purpose(
            conn, made, purpose_uuid=str(seeded["purpose"]["purpose_uuid"])
        )


async def test_the_trail_names_the_template(conn: Any, seeded: dict[str, Any]) -> None:
    made = await _template(conn, seeded)
    await templates.set_status(conn, made, status="retired")
    rows = await fetch_all(
        conn,
        """SELECT event_type, entity_type, detail_json FROM audit_log
            WHERE entity_type = 'notice_template' AND entity_id = %s ORDER BY log_id""",
        (made["template_id"],),
    )
    assert [r["event_type"] for r in rows] == [
        "notice_template.created",
        "notice_template.language_set",
        "notice_template.retired",
    ]
    assert all(r["detail_json"]["template"] == made["template_code"] for r in rows)
    assert TEXT not in json.dumps([r["detail_json"] for r in rows])
