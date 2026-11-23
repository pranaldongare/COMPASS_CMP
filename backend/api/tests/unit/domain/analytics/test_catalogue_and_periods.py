"""The analytics catalogue holds together, and periods fall where India's
calendars put them (ADR 0045)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from cmp.core import metrics as cat
from cmp.core.permissions import Role
from cmp.db.repositories.analytics import SOURCES
from cmp.domain.analytics import periods
from cmp.domain.audit.service import Event


class TestCatalogue:
    def test_every_counted_metric_has_a_source_and_nothing_else_does(self) -> None:
        counted = {m.key for m in cat.CATALOGUE if m.kind not in (cat.RATIO, cat.LIVE)}
        assert counted == set(SOURCES)

    def test_a_rate_is_made_of_two_counts_of_the_same_audience(self) -> None:
        for m in cat.CATALOGUE:
            if m.kind == cat.RATIO:
                assert m.numerator in cat.METRICS and m.denominator in cat.METRICS, m.key
                for part in (cat.metric(m.numerator), cat.metric(m.denominator)):
                    assert part.kind == cat.COUNT, m.key
                    assert m.audience <= part.audience, m.key
                    assert set(m.dims) <= set(part.dims), m.key

    def test_audiences_and_sections_are_real(self) -> None:
        roles = {r.value for r in Role}
        for m in cat.CATALOGUE:
            assert m.audience <= roles, m.key
            assert m.section in cat.SECTIONS, m.key
            assert set(m.dims) <= set(cat.DIMENSIONS), m.key
            assert m.definition.endswith("."), m.key
        for r in cat.REPORTS.values():
            assert r.audience <= roles, r.key

    def test_the_administrator_reads_audit_and_health_only(self) -> None:
        sections = cat.sections_for(Role.ADMIN.value)
        assert "management" not in sections and "analytics" not in sections
        assert {"audit", "health"} <= set(sections)
        assert not any(m.section in ("management", "analytics") for m in cat.for_role("admin"))

    def test_management_reads_the_scorecard_and_no_audit_or_health(self) -> None:
        sections = cat.sections_for(Role.MANAGEMENT.value)
        assert "management" in sections and "audit" not in sections and "health" not in sections

    def test_the_workers_read_their_own_work_only(self) -> None:
        for role in cat.WORKERS:
            assert {m.section for m in cat.for_role(role)} == {"mine"}, role

    def test_every_audit_report_names_real_events(self) -> None:
        known = {v for k, v in vars(Event).items() if isinstance(v, str) and "." in v}
        for a in cat.AUDIT_REPORTS.values():
            assert set(a.events) <= known, a.key

    def test_targets_lie_on_the_right_side_of_the_amber_line(self) -> None:
        for m in cat.CATALOGUE:
            if m.target is not None and m.amber is not None:
                assert (m.amber <= m.target) if m.higher_is_better else (m.amber >= m.target), m.key


class TestPeriods:
    TODAY = date(2026, 11, 23)

    @pytest.mark.parametrize(
        ("preset", "first", "after", "label"),
        [
            ("this_month", date(2026, 11, 1), date(2026, 12, 1), "November 2026"),
            ("last_month", date(2026, 10, 1), date(2026, 11, 1), "October 2026"),
            ("this_quarter", date(2026, 10, 1), date(2027, 1, 1), "Q4 2026 (Q3 FY 2026-27)"),
            ("last_quarter", date(2026, 7, 1), date(2026, 10, 1), "Q3 2026 (Q2 FY 2026-27)"),
            ("this_year", date(2026, 1, 1), date(2027, 1, 1), "2026"),
            ("this_fy", date(2026, 4, 1), date(2027, 4, 1), "FY 2026-27"),
            ("last_fy", date(2025, 4, 1), date(2026, 4, 1), "FY 2025-26"),
        ],
    )
    def test_presets_fall_on_india_midnight(
        self, preset: str, first: date, after: date, label: str
    ) -> None:
        p = periods.resolve(preset, today=self.TODAY)
        assert p.start == periods._at(first) and p.end == periods._at(after)
        assert p.label == label
        assert p.start.astimezone(periods.IST).hour == 0

    def test_the_financial_year_starts_in_april_in_january_too(self) -> None:
        p = periods.resolve("this_fy", today=date(2027, 1, 15))
        assert p.label == "FY 2026-27"

    def test_the_previous_period_is_the_same_kind(self) -> None:
        q = periods.resolve("this_quarter", today=self.TODAY)
        assert periods.previous(q).label == "Q3 2026 (Q2 FY 2026-27)"
        fy = periods.resolve("this_fy", today=self.TODAY)
        assert periods.previous(fy).label == "FY 2025-26"
        week = periods.resolve("last_7_days", today=self.TODAY)
        before = periods.previous(week)
        assert before.end == week.start and (week.start - before.start).days == 7

    def test_custom_dates_include_the_last_day_and_are_bounded(self) -> None:
        p = periods.resolve("custom", start=date(2026, 11, 1), end=date(2026, 11, 3))
        assert p.days == 3
        from cmp.core.errors import ValidationFailed

        with pytest.raises(ValidationFailed):
            periods.resolve("custom", start=date(2026, 11, 3), end=date(2026, 11, 1))
        with pytest.raises(ValidationFailed):
            periods.resolve("custom", start=date(2020, 1, 1), end=date(2026, 1, 1))
        with pytest.raises(ValidationFailed):
            periods.resolve("fortnight")

    @pytest.mark.parametrize(
        ("cadence", "next_day", "covered"),
        [
            ("weekly", date(2026, 11, 30), "16 Nov 2026 - 22 Nov 2026"),
            ("monthly", date(2026, 12, 1), "October 2026"),
            ("quarterly", date(2027, 1, 1), "Q3 2026 (Q2 FY 2026-27)"),
        ],
    )
    def test_a_schedule_runs_at_six_in_the_morning_for_the_period_just_ended(
        self, cadence: str, next_day: date, covered: str
    ) -> None:
        now = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)
        run = periods.next_run(cadence, now)
        local = run.astimezone(periods.IST)
        assert local.date() == next_day and (local.hour, local.minute) == (6, 0)
        assert periods.covered_by(cadence, now).label == covered
