"""The narrow lists the dashboard's attention rows open (UX review 2026-10-05).

"Rights requests due within 7 days" and "Notice text awaiting approval" each
counted a subset and linked to the whole register. The registers now take the
filter the count was made with, so the link can open exactly what it counted.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.pagination import PageRequest
from cmp.core.permissions import Role
from cmp.db.repositories import notices as notice_repo
from cmp.db.repositories import rights as rights_repo
from tests.integration.test_rights_flows import _portal_request

pytestmark = pytest.mark.integration


def _page() -> PageRequest:
    return PageRequest(limit=200, cursor=None, sort_field="created_at", descending=True)


async def test_due_soon_is_open_and_due_within_seven_days(
    conn: Any, seeded: dict[str, Any]
) -> None:
    soon = await _portal_request(conn, seeded, "access")
    later = await _portal_request(conn, seeded, "access")
    await conn.execute(
        "UPDATE rights_request SET due_at = now() + interval '3 days' WHERE request_id = %s",
        (soon["request_id"],),
    )
    await conn.execute(
        "UPDATE rights_request SET due_at = now() + interval '30 days' WHERE request_id = %s",
        (later["request_id"],),
    )
    rows, _, _ = await rights_repo.list_requests(
        conn, _page(), role=Role.DPO, user_id=seeded["users"]["dpo"]["id"], due_soon=True
    )
    found = {str(r["request_uuid"]) for r in rows}
    assert str(soon["request_uuid"]) in found
    assert str(later["request_uuid"]) not in found


async def test_unapproved_languages_lists_notices_with_text_awaiting_approval(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = seeded["users"]["dpo"]["id"]
    rows, _, _ = await notice_repo.list_all(
        conn, _page(), role=Role.DPO, user_id=dpo, unapproved_languages=True
    )
    assert str(seeded["notice"]["notice_uuid"]) not in {str(r["notice_uuid"]) for r in rows}

    await conn.execute(
        """INSERT INTO notice (notice_code, project_id, version, withdraw_url,
                               exercise_rights_url, board_complaint_url, dpo_contact)
           VALUES ('N-WAITING', %s, 2, 'https://x/w', 'https://x/r', 'https://dpb.gov.in',
                   'dpo@test.local')""",
        (seeded["project"]["project_id"],),
    )
    waiting = await (
        await conn.execute(
            "SELECT notice_id, notice_uuid FROM notice WHERE notice_code = 'N-WAITING'"
        )
    ).fetchone()
    await conn.execute(
        """INSERT INTO notice_language (notice_id, language_code, rendered_text,
                                        content_hash, created_by)
           VALUES (%s, 'hindi', 'पाठ', 'h', %s)""",
        (waiting["notice_id"], dpo),
    )
    rows, _, _ = await notice_repo.list_all(
        conn, _page(), role=Role.DPO, user_id=dpo, unapproved_languages=True
    )
    assert str(waiting["notice_uuid"]) in {str(r["notice_uuid"]) for r in rows}


async def test_one_person_by_uuid(conn: Any, seeded: dict[str, Any]) -> None:
    """A requester's name on a request opens that person, not the whole register."""
    from cmp.db.repositories import users as user_repo

    dco = seeded["users"]["dco"]
    rows, _, total = await user_repo.list_users(conn, _page(), person=str(dco["uuid"]))
    assert [str(r["uuid"]) for r in rows] == [str(dco["uuid"])]
    assert total == 1
