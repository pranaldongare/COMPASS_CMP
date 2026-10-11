"""The dashboard's response keeps every part the page draws.

The response model drops a field it does not name: the week's trend lines
(2026-10-11) were computed and then silently thrown away on the way out.
"""

from __future__ import annotations

from cmp.api.routers.v1.dashboard import Dashboard


def test_the_trend_lines_reach_the_page() -> None:
    out = Dashboard(
        role="dpo",
        counts={"requests_open": 3},
        queues=[],
        recent=[],
        trends={"requests_open": [0, 1, 0, 2, 0, 0, 1]},
    ).model_dump()
    assert out["trends"] == {"requests_open": [0, 1, 0, 2, 0, 0, 1]}


def test_a_role_without_lines_gets_an_empty_map() -> None:
    assert Dashboard(role="admin", counts={}, queues=[], recent=[]).model_dump()["trends"] == {}
