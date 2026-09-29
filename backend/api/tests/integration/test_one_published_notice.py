"""A project collects under one notice at a time.

Publishing superseded only earlier versions of the same notice code, so a notice
that arrived under a code of its own - "New notice", "Use an existing notice",
an upload - could be published beside the one in force, and a project ended up
with two. Consent links kept serving whichever notice they were minted for.

Now publishing supersedes every other published notice on the project, the
replaced notice's live links move to the new one (consents already given keep
the notice they were given under), and the database refuses a second published
notice on a project whatever wrote it.
"""

from __future__ import annotations

from typing import Any

import psycopg
import pytest

from cmp.core.errors import Conflict
from cmp.core.permissions import Role
from cmp.core.security import content_hash, new_token, token_fingerprint
from cmp.db.sql import fetch_one
from cmp.domain.consent import service as consent_service
from cmp.domain.notices import service as notice_service

pytestmark = pytest.mark.integration


async def _draft(conn: Any, seeded: dict[str, Any], code: str) -> int:
    """A complete draft notice under its own code, ready to publish."""
    dpo = seeded["users"]["dpo"]["id"]
    row = await fetch_one(
        conn,
        """INSERT INTO notice (notice_code, project_id, version, withdraw_url,
                               exercise_rights_url, board_complaint_url, dpo_contact,
                               applicable_to)
           VALUES (%s, %s, 1, 'https://x/w', 'https://x/r', 'https://dpb.gov.in',
                   'dpo@test.local', 'data_subject')
           RETURNING notice_id""",
        (code, seeded["project"]["project_id"]),
    )
    assert row is not None
    text = f"The replacement notice {code}."
    await conn.execute(
        """INSERT INTO notice_language (notice_id, language_code, rendered_text,
                                        content_hash, created_by, approved_by, approved_at)
           VALUES (%s, 'english', %s, %s, %s, %s, now())""",
        (row["notice_id"], text, content_hash(text), dpo, dpo),
    )
    await conn.execute(
        "INSERT INTO notice_purpose (notice_id, purpose_id) VALUES (%s, %s)",
        (row["notice_id"], seeded["purpose"]["purpose_id"]),
    )
    return int(row["notice_id"])


async def _status(conn: Any, notice_id: int) -> str:
    row = await fetch_one(conn, "SELECT status FROM notice WHERE notice_id = %s", (notice_id,))
    assert row is not None
    return str(row["status"])


async def test_publishing_a_second_notice_supersedes_the_first_and_moves_its_links(
    conn: Any, seeded: dict[str, Any]
) -> None:
    old_notice = int(seeded["notice"]["notice_id"])
    # A person consents through the old notice's link first.
    raw = new_token()
    link = await fetch_one(
        conn,
        """INSERT INTO consent_link (notice_id, site_id, token, expires_at, created_by)
           VALUES (%s, %s, %s, now() + interval '1 day', %s) RETURNING link_id""",
        (
            old_notice,
            seeded["site"]["site_id"],
            token_fingerprint(raw)[:64],
            seeded["users"]["dpo"]["id"],
        ),
    )
    assert link is not None
    await consent_service.serve_notice(
        conn, token=raw, language_code="english", user_id=seeded["subject"]["id"]
    )
    artefact = await consent_service.capture(
        conn,
        token=raw,
        user_id=seeded["subject"]["id"],
        language_code="english",
        grants={str(seeded["purpose"]["purpose_uuid"]): True},
        action_type="checkbox_click",
        ip_address="127.0.0.1",
    )

    new_notice = await _draft(conn, seeded, "N-TEST-REPLACEMENT")
    await notice_service.publish(conn, notice_id=new_notice, actor_id=seeded["users"]["dpo"]["id"])

    assert await _status(conn, new_notice) == "published"
    assert await _status(conn, old_notice) == "superseded"
    project = await fetch_one(
        conn,
        "SELECT current_notice_id FROM project WHERE project_id = %s",
        (seeded["project"]["project_id"],),
    )
    assert project is not None and project["current_notice_id"] == new_notice

    # The link now serves the notice in force ...
    moved = await fetch_one(
        conn, "SELECT notice_id FROM consent_link WHERE link_id = %s", (link["link_id"],)
    )
    assert moved is not None and moved["notice_id"] == new_notice
    view = await consent_service.resolve_link(conn, raw)
    assert str(view["notice_id"]) == str(new_notice)
    # ... and the consent already given keeps the notice it was given under.
    kept = await fetch_one(
        conn,
        "SELECT notice_id FROM consent_artefact WHERE consent_uuid = %s",
        (artefact["consent_uuid"],),
    )
    assert kept is not None and kept["notice_id"] == old_notice


async def test_the_database_refuses_two_published_notices_on_one_project(
    conn: Any, seeded: dict[str, Any]
) -> None:
    second = await _draft(conn, seeded, "N-TEST-SECOND")
    async with conn.transaction():
        with pytest.raises(psycopg.errors.UniqueViolation):
            async with conn.transaction():
                await conn.execute(
                    """UPDATE notice SET status = 'published', recipients_text = 'Test Site',
                              published_at = now() WHERE notice_id = %s""",
                    (second,),
                )


async def test_another_projects_notice_code_is_refused(conn: Any, seeded: dict[str, Any]) -> None:
    other = await fetch_one(
        conn,
        """INSERT INTO project (project_name, description, created_by, project_status)
           VALUES ('Other Study', 'd', %s, 'in_draft') RETURNING project_uuid""",
        (seeded["users"]["dpo"]["id"],),
    )
    assert other is not None
    with pytest.raises(Conflict) as refused:
        await notice_service.create(
            conn,
            project_uuid=str(other["project_uuid"]),
            actor_id=seeded["users"]["dpo"]["id"],
            role=Role.DPO,
            withdraw_url="https://x/w",
            exercise_rights_url="https://x/r",
            board_complaint_url="https://dpb.gov.in",
            dpo_contact="dpo@test.local",
            notice_code="N-TEST",  # the seeded notice's code
        )
    assert refused.value.code == "notice_code_taken"


async def test_approval_publishes_the_newest_draft(conn: Any, seeded: dict[str, Any]) -> None:
    older = await _draft(conn, seeded, "N-TEST-OLDER")
    newer = await _draft(conn, seeded, "N-TEST-NEWER")
    # Both are version 1 under their own codes; only creation order tells them apart.
    await conn.execute(
        "UPDATE notice SET created_at = now() - interval '1 hour' WHERE notice_id = %s", (older,)
    )

    published = await notice_service.publish_current(
        conn, project_id=seeded["project"]["project_id"], actor_id=seeded["users"]["dpo"]["id"]
    )

    assert published is not None and int(published["notice_id"]) == newer
    assert await _status(conn, older) == "draft"
    assert await _status(conn, int(seeded["notice"]["notice_id"])) == "superseded"
