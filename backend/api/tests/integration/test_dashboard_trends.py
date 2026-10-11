"""The line under each dashboard figure (2026-10-11).

Seven days of new records per day, oldest first, for each figure that has a
dated record behind it - and only within what the role may see. A series is
always seven long, so a quiet day draws as a zero rather than a gap.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.permissions import Role
from cmp.db.repositories import dashboard as dashboard_repo

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    ("role", "keys"),
    [
        (Role.DPO, {"requests_open", "open_breaches", "total_consents", "pending_approval"}),
        (Role.ADMIN, {"users_active", "users_pending", "grievances_about_dpo"}),
        (Role.DCO, {"active_links", "consents"}),
        (Role.RCO, {"active_links", "consents"}),
        (Role.DCO_ADMIN, {"projects"}),
        (Role.RND_USER, {"total"}),
    ],
)
async def test_each_figure_gets_seven_days(conn: Any, role: Role, keys: set[str]) -> None:
    series = await dashboard_repo.trends(conn, role, user_id=0)
    assert set(series) == keys
    for key, days in series.items():
        assert len(days) == dashboard_repo.TREND_DAYS, key
        assert all(isinstance(n, int) and n >= 0 for n in days), key


async def test_a_collector_sees_only_their_own_projects(conn: Any) -> None:
    # Nobody is accountable as user 0, so nothing is theirs.
    series = await dashboard_repo.trends(conn, Role.DCO, user_id=0)
    assert all(n == 0 for days in series.values() for n in days)


async def test_a_role_without_figures_gets_no_lines(conn: Any) -> None:
    assert await dashboard_repo.trends(conn, Role.DATA_SUBJECT, user_id=0) == {}
