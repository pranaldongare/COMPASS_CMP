"""The response periods stay inside Rule 14's outer limit (2026-11-20).

A period of 91 days would be published to every requester and stamped on
every request as a promise the law does not allow; zero or less is no period
at all. A checkpoint has to fall inside the period it marks.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from cmp.core.config import Settings


def _settings(**kw: object) -> Settings:
    return Settings(_env_file=None, **kw)  # type: ignore[call-arg, arg-type]


@pytest.mark.parametrize("name", ["grievance_response_period_days", "rights_response_period_days"])
@pytest.mark.parametrize("days", [91, 0, -1])
def test_a_period_outside_one_to_ninety_days_is_refused(name: str, days: int) -> None:
    with pytest.raises(ValidationError):
        _settings(**{name: days})


@pytest.mark.parametrize("name", ["grievance_response_period_days", "rights_response_period_days"])
def test_ninety_days_is_accepted(name: str) -> None:
    assert getattr(_settings(**{name: 90}), name) == 90


def test_a_checkpoint_after_the_response_is_due_is_refused() -> None:
    with pytest.raises(ValidationError, match="RIGHTS_COLLATE_BEFORE_DAYS"):
        _settings(grievance_response_period_days=10, rights_collate_before_days=10)


def test_a_shorter_period_with_checkpoints_inside_it_is_accepted() -> None:
    s = _settings(grievance_response_period_days=30)
    assert s.grievance_response_period_days == 30


def test_the_due_date_follows_the_period_at_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    from cmp.domain.rights import clock

    received = datetime(2026, 11, 20, tzinfo=UTC)
    monkeypatch.setattr(clock, "settings", _settings(grievance_response_period_days=90))
    assert clock.due_for("grievance", received) == received + timedelta(days=90)
