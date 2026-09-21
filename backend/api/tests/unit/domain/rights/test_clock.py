"""The clock on a request.

Two properties, both from the flow diagrams: the clock starts on receipt, and
every date is relative to the period the request was received under.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from cmp.core.config import settings
from cmp.domain.rights import clock

D0 = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)


def test_the_period_comes_from_the_published_setting() -> None:
    due = clock.due_for("access", D0)
    assert due == D0 + timedelta(days=settings.rights_response_period_days)
    assert clock.due_for("grievance", D0) == D0 + timedelta(
        days=settings.grievance_response_period_days
    )


def test_the_checkpoints_sit_where_the_diagram_puts_them() -> None:
    due = D0 + timedelta(days=90)
    c = clock.compute(D0, due, now=D0)
    assert c.acknowledge_by == D0 + timedelta(days=settings.rights_acknowledge_within_days)
    assert c.tickets_by == D0 + timedelta(days=settings.rights_tickets_within_days)
    assert c.halfway_at == D0 + timedelta(days=45)
    assert c.collate_by == due - timedelta(days=settings.rights_collate_before_days)
    assert [p.key for p in c.checkpoints()] == [
        "received",
        "acknowledge",
        "tickets",
        "halfway",
        "collate",
        "due",
    ]


def test_halfway_is_half_of_this_requests_period_not_the_settings() -> None:
    """A request received under an older, shorter period keeps its own halfway."""
    due = D0 + timedelta(days=30)
    c = clock.compute(D0, due, now=D0)
    assert c.halfway_at == D0 + timedelta(days=15)


def test_days_remaining_counts_down_and_goes_negative() -> None:
    due = D0 + timedelta(days=10)
    assert clock.compute(D0, due, now=D0).days_remaining == 10
    assert clock.compute(D0, due, now=D0 + timedelta(days=9, hours=12)).days_remaining == 1
    late = clock.compute(D0, due, now=due + timedelta(days=2))
    assert late.days_remaining == -2
    assert late.overdue is True


def test_a_closed_request_is_never_overdue_or_at_risk() -> None:
    due = D0 + timedelta(days=10)
    c = clock.compute(D0, due, now=due + timedelta(days=30), closed=True)
    assert c.overdue is False
    assert c.at_risk is False


def test_at_risk_is_the_window_between_collation_and_due() -> None:
    due = D0 + timedelta(days=90)
    before = clock.compute(D0, due, now=due - timedelta(days=10))
    inside = clock.compute(D0, due, now=due - timedelta(days=2))
    assert before.at_risk is False
    assert inside.at_risk is True
    assert inside.next_checkpoint is not None
    assert inside.next_checkpoint.key == "due"


def test_progress_is_clamped() -> None:
    due = D0 + timedelta(days=10)
    assert clock.compute(D0, due, now=D0 - timedelta(days=1)).progress == 0.0
    assert clock.compute(D0, due, now=D0 + timedelta(days=5)).progress == 0.5
    assert clock.compute(D0, due, now=due + timedelta(days=5)).progress == 1.0


def test_the_dict_shape_carries_everything_the_console_renders() -> None:
    due = D0 + timedelta(days=90)
    shape = clock.compute(D0, due, now=D0 + timedelta(days=3)).as_dict()
    assert shape["next_checkpoint"] == "tickets"
    assert shape["checkpoints"][1]["passed"] is True
    assert shape["overdue"] is False
    assert set(shape) >= {"due_at", "days_remaining", "progress", "checkpoints"}
