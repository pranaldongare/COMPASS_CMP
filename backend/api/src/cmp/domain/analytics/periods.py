"""Reporting periods, in India's time (ADR 0045).

A period is a half-open span `[start, end)` of instants, with a label a
person reads. The presets cover both calendars the product owner asked for:
the calendar's months, quarters and years, and the financial year that runs
from April to March (`FY 2026-27`). Its quarters share the calendar's
boundaries - April to June is the financial year's Q1 and the calendar's Q2 -
so a quarter is the same span, named either way.

Every period has a comparison: the one before it, of the same kind - the
previous month, quarter or year; for a span of days, the same number of days
just before it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Final
from zoneinfo import ZoneInfo

from cmp.core.errors import ValidationFailed

IST: Final = ZoneInfo("Asia/Kolkata")

PRESETS: Final[dict[str, str]] = {
    "last_7_days": "Last 7 days",
    "last_30_days": "Last 30 days",
    "this_month": "This month",
    "last_month": "Last month",
    "this_quarter": "This quarter",
    "last_quarter": "Last quarter",
    "this_year": "This calendar year",
    "last_year": "Last calendar year",
    "this_fy": "This financial year",
    "last_fy": "Last financial year",
    "custom": "Custom dates",
}

#: The longest span a custom period may cover.
MAX_DAYS: Final = 3 * 366


@dataclass(frozen=True, slots=True)
class Period:
    preset: str
    start: datetime
    end: datetime
    label: str

    @property
    def days(self) -> int:
        return max(1, round((self.end - self.start).total_seconds() / 86400))

    def as_dict(self) -> dict[str, object]:
        return {
            "preset": self.preset,
            "start": self.start,
            "end": self.end,
            "label": self.label,
            "start_date": self.start.astimezone(IST).date(),
            "end_date": (self.end.astimezone(IST) - timedelta(seconds=1)).date(),
        }


def _at(day: date) -> datetime:
    """Midnight in India, as an instant."""
    return datetime.combine(day, time.min, IST).astimezone(UTC)


def _month_start(day: date) -> date:
    return day.replace(day=1)


def _add_months(day: date, months: int) -> date:
    index = day.year * 12 + (day.month - 1) + months
    return date(index // 12, index % 12 + 1, 1)


def _quarter_start(day: date) -> date:
    return date(day.year, 3 * ((day.month - 1) // 3) + 1, 1)


def _fy_start(day: date) -> date:
    return date(day.year if day.month >= 4 else day.year - 1, 4, 1)


def _fy_label(start: date) -> str:
    return f"FY {start.year}-{str(start.year + 1)[2:]}"


def _quarter_label(start: date) -> str:
    q = (start.month - 1) // 3 + 1
    fy_q = (q + 2) % 4 + 1
    fy = _fy_start(start)
    return f"Q{q} {start.year} (Q{fy_q} {_fy_label(fy)})"


def _fmt(day: date) -> str:
    return f"{day.day} {day:%b %Y}"


def resolve(
    preset: str = "this_month",
    *,
    start: date | None = None,
    end: date | None = None,
    today: date | None = None,
) -> Period:
    """A preset, or custom dates (`start` to `end`, both included)."""
    now = today or datetime.now(IST).date()
    if preset not in PRESETS:
        raise ValidationFailed(
            f"Choose a period: {', '.join(PRESETS)}", field="period", details={"preset": preset}
        )
    if preset == "custom":
        if start is None or end is None:
            raise ValidationFailed("Give the first and the last day", field="start")
        if end < start:
            raise ValidationFailed("The last day is before the first", field="end")
        if (end - start).days > MAX_DAYS:
            raise ValidationFailed("A period may cover at most three years", field="end")
        return Period(
            preset, _at(start), _at(end + timedelta(days=1)), f"{_fmt(start)} - {_fmt(end)}"
        )
    if preset in ("last_7_days", "last_30_days"):
        n = 7 if preset == "last_7_days" else 30
        first = now - timedelta(days=n - 1)
        return Period(preset, _at(first), _at(now + timedelta(days=1)), PRESETS[preset])
    if preset in ("this_month", "last_month"):
        first = _month_start(now) if preset == "this_month" else _add_months(_month_start(now), -1)
        return Period(preset, _at(first), _at(_add_months(first, 1)), f"{first:%B %Y}")
    if preset in ("this_quarter", "last_quarter"):
        first = _quarter_start(now)
        if preset == "last_quarter":
            first = _add_months(first, -3)
        return Period(preset, _at(first), _at(_add_months(first, 3)), _quarter_label(first))
    if preset in ("this_year", "last_year"):
        year = now.year if preset == "this_year" else now.year - 1
        return Period(preset, _at(date(year, 1, 1)), _at(date(year + 1, 1, 1)), str(year))
    first = _fy_start(now)
    if preset == "last_fy":
        first = date(first.year - 1, 4, 1)
    return Period(preset, _at(first), _at(date(first.year + 1, 4, 1)), _fy_label(first))


def previous(period: Period) -> Period:
    """The period before, of the same kind."""
    start = period.start.astimezone(IST).date()
    if period.preset in ("this_month", "last_month"):
        first = _add_months(start, -1)
        return Period("custom", _at(first), _at(_add_months(first, 1)), f"{first:%B %Y}")
    if period.preset in ("this_quarter", "last_quarter"):
        first = _add_months(start, -3)
        return Period("custom", _at(first), _at(_add_months(first, 3)), _quarter_label(first))
    if period.preset in ("this_year", "last_year"):
        first = date(start.year - 1, 1, 1)
        return Period("custom", _at(first), _at(date(start.year, 1, 1)), str(first.year))
    if period.preset in ("this_fy", "last_fy"):
        first = date(start.year - 1, 4, 1)
        return Period("custom", _at(first), _at(date(start.year, 4, 1)), _fy_label(first))
    span = period.end - period.start
    begin = period.start - span
    first = begin.astimezone(IST).date()
    last = (period.start.astimezone(IST) - timedelta(seconds=1)).date()
    return Period("custom", begin, period.start, f"{_fmt(first)} - {_fmt(last)}")


def grain_for(period: Period) -> str:
    """The bucket a period's line is drawn in: days for a month or less."""
    if period.days <= 45:
        return "day"
    if period.days <= 190:
        return "week"
    return "month"


# ---------------------------------------------------------------- schedules
CADENCES: Final[dict[str, str]] = {
    "weekly": "Every Monday, for the week before",
    "monthly": "On the 1st, for the month before",
    "quarterly": "On the 1st of a quarter, for the quarter before",
}

#: When a scheduled report is made, in India: early, before the working day.
RUN_AT: Final = time(6, 0)


def next_run(cadence: str, after: datetime) -> datetime:
    """The next run of a cadence strictly after `after`."""
    local = after.astimezone(IST)
    day = local.date()
    if cadence == "weekly":
        candidate = day + timedelta(days=(7 - day.weekday()) % 7)
    elif cadence == "monthly":
        candidate = day.replace(day=1)
    elif cadence == "quarterly":
        candidate = _quarter_start(day)
    else:
        raise ValidationFailed(f"Choose a cadence: {', '.join(CADENCES)}", field="cadence")
    while True:
        at = datetime.combine(candidate, RUN_AT, IST)
        if at > local:
            return at.astimezone(UTC)
        if cadence == "weekly":
            candidate += timedelta(days=7)
        elif cadence == "monthly":
            candidate = _add_months(candidate, 1)
        else:
            candidate = _add_months(candidate, 3)


def covered_by(cadence: str, run_at: datetime) -> Period:
    """What a scheduled run reports on: the complete period before it."""
    day = run_at.astimezone(IST).date()
    if cadence == "weekly":
        monday = day - timedelta(days=day.weekday())
        first = monday - timedelta(days=7)
        last = monday - timedelta(days=1)
        return Period("custom", _at(first), _at(monday), f"{_fmt(first)} - {_fmt(last)}")
    if cadence == "monthly":
        first = _add_months(_month_start(day), -1)
        return Period("custom", _at(first), _at(_add_months(first, 1)), f"{first:%B %Y}")
    first = _add_months(_quarter_start(day), -3)
    return Period("custom", _at(first), _at(_add_months(first, 3)), _quarter_label(first))
