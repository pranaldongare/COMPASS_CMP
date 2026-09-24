"""A link in someone's feed opens a page they can open.

The resolver picked one route per record type for all staff, so a DCO's bell
linked "Notice published" to a notice page - a section a DCO does not have - and
an R&D User's linked "Export generated" to the exports register. Both landed on
"Not part of your account". A link is now kept only when the reader's own menu
(`nav_for`, the server's list the console already guards with) has its section;
otherwise the entry reads the same, unlinked.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.permissions import Role
from cmp.db.repositories import entities as entity_repo

pytestmark = pytest.mark.integration


def _row(entity_type: str, entity_id: int) -> dict[str, Any]:
    return {"entity_type": entity_type, "entity_id": entity_id}


async def test_a_notice_link_is_kept_for_the_dpo_and_dropped_for_a_dco(
    conn: Any, seeded: dict[str, Any]
) -> None:
    notice_id = int(seeded["notice"]["notice_id"])
    [dpo] = await entity_repo.attach(conn, [_row("notice", notice_id)], reader_role=Role.DPO)
    [dco] = await entity_repo.attach(conn, [_row("notice", notice_id)], reader_role=Role.DCO)

    assert dpo["entity_href"] and dpo["entity_href"].startswith("/notices/")
    assert dco["entity_href"] is None, "a DCO has no Notices section"
    assert dco["entity_label"] == dpo["entity_label"], "what happened reads the same"


async def test_a_project_link_is_kept_for_every_role_with_projects(
    conn: Any, seeded: dict[str, Any]
) -> None:
    project_id = int(seeded["project"]["project_id"])
    for role in (Role.DPO, Role.DCO, Role.RND_USER, Role.RCO, Role.DCO_ADMIN):
        [row] = await entity_repo.attach(conn, [_row("project", project_id)], reader_role=role)
        assert row["entity_href"] and row["entity_href"].startswith("/projects/"), role
