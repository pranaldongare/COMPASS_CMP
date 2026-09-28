"""An R&D User may start a notice from any approved one, whoever wrote it.

"Use an existing notice" offered an R&D User only notices on projects they had
created themselves - `GET /notices` is scoped to their own projects - so a
researcher's first study could never start from the text the Privacy Office had
already approved for a colleague's, and the copy route refused a colleague's
notice with 404 even when asked for it.

The picker now reads `copy_sources` - every approved or published notice - and
copying reaches past the caller's scope for exactly those. A draft stays its
project's own, and nothing else an R&D User reads widens.
"""

from __future__ import annotations

import secrets
from typing import Any

import pytest

from cmp.core.errors import NotFound
from cmp.core.pagination import PageRequest
from cmp.core.permissions import Role
from cmp.db.repositories import notices as notice_repo
from cmp.db.repositories import users as user_repo
from cmp.domain.notices import service as notice_service

pytestmark = pytest.mark.integration


async def _second_researcher(conn: Any) -> dict[str, Any]:
    """An R&D User who did not create the seeded project."""
    return dict(
        await user_repo.create(
            conn,
            full_name="Second Researcher",
            email=f"rnd2-{secrets.token_hex(4)}@test.local",
            role="rnd_user",
            person_type="employee",
            status="active",
            password_hash=None,
        )
    )


async def _own_draft_project(conn: Any, creator_id: int) -> str:
    row = await conn.execute(
        """INSERT INTO project (project_name, description, created_by, project_status)
           VALUES ('Second Study', 'd', %s, 'in_draft') RETURNING project_uuid""",
        (creator_id,),
    )
    return str((await row.fetchone())["project_uuid"])


async def test_the_picker_lists_every_approved_notice_whoever_wrote_it(
    conn: Any, seeded: dict[str, Any]
) -> None:
    other = await _second_researcher(conn)

    # What she may read in general is unchanged: the seeded notice is on a
    # project somebody else created.
    visible, _, _ = await notice_repo.list_all(
        conn,
        PageRequest(limit=200, cursor=None, sort_field="created_at", descending=True),
        role=Role.RND_USER,
        user_id=int(other["id"]),
    )
    assert seeded["notice"]["notice_uuid"] not in [n["notice_uuid"] for n in visible]

    # What she may start from is every approved or published notice.
    sources = await notice_repo.copy_sources(conn)
    listed = {str(n["notice_uuid"]): n for n in sources}
    assert str(seeded["notice"]["notice_uuid"]) in listed
    assert all(n["status"] in ("approved", "published") for n in sources)
    # Only what the picker shows travels.
    assert "withdraw_url" not in listed[str(seeded["notice"]["notice_uuid"])]


async def test_she_copies_a_colleagues_published_notice_into_her_own_project(
    conn: Any, seeded: dict[str, Any]
) -> None:
    other = await _second_researcher(conn)
    target = await _own_draft_project(conn, int(other["id"]))

    copied = await notice_service.copy_from(
        conn,
        project_uuid=target,
        source_notice_uuid=str(seeded["notice"]["notice_uuid"]),
        actor_id=int(other["id"]),
        role=Role.RND_USER,
    )

    assert copied["status"] == "draft"
    assert str(copied["project_uuid"]) == target
    languages = await notice_repo.languages_of(conn, copied["notice_id"], with_text=True)
    # The approval is the source project's, and does not come across.
    assert languages and all(x["approved_at"] is None for x in languages)


async def test_a_colleagues_draft_is_neither_listed_nor_copyable(
    conn: Any, seeded: dict[str, Any]
) -> None:
    draft = await (
        await conn.execute(
            """INSERT INTO notice (notice_code, project_id, version, withdraw_url,
                                   exercise_rights_url, board_complaint_url, dpo_contact)
               VALUES ('N-DRAFT-ONLY', %s, 2, 'https://x/w', 'https://x/r',
                       'https://dpb.gov.in', 'dpo@test.local')
               RETURNING notice_uuid""",
            (seeded["project"]["project_id"],),
        )
    ).fetchone()
    other = await _second_researcher(conn)
    target = await _own_draft_project(conn, int(other["id"]))

    assert str(draft["notice_uuid"]) not in [
        str(n["notice_uuid"]) for n in await notice_repo.copy_sources(conn)
    ]
    with pytest.raises(NotFound):
        await notice_service.copy_from(
            conn,
            project_uuid=target,
            source_notice_uuid=str(draft["notice_uuid"]),
            actor_id=int(other["id"]),
            role=Role.RND_USER,
        )
