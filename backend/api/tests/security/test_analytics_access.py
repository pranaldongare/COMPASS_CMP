"""Who may reach the analytics, the reports and their settings (ADR 0045).

Negative assertions, against the matrix and the catalogue, as `test_bfla`
makes them: management writes nothing but its own reports and the tickets
addressed to it; the administrator reads no scorecard and sets the targets;
nobody but the administrator reads the platform's health; a data principal
reaches none of it.
"""

from __future__ import annotations

import pytest

from cmp.auth.authorization import resources
from cmp.auth.authorization.evaluator import can_read, can_write, writable_resources
from cmp.core import metrics as cat
from cmp.core.permissions import Role

PARTS = (
    resources.ANALYTICS,
    resources.AUDIT_REPORT,
    resources.HEALTH_REPORT,
    resources.ANALYTICS_SETTING,
    resources.REPORT,
)


def test_management_writes_nothing_but_its_reports_and_its_own_tickets() -> None:
    assert set(writable_resources(Role.MANAGEMENT)) <= {
        resources.REPORT,
        resources.TICKET,
        resources.BREACH_TICKET,
    }


def test_management_reads_no_record_register() -> None:
    for resource in (
        resources.USER,
        resources.CONSENT,
        resources.RIGHTS_REQUEST,
        resources.BREACH,
        resources.AUDIT,
        resources.PROJECT,
    ):
        assert not can_read(resource, Role.MANAGEMENT), resource


def test_the_administrator_reads_no_scorecard_and_alone_sets_targets() -> None:
    assert not can_read(resources.ANALYTICS, Role.ADMIN)
    assert can_write(resources.ANALYTICS_SETTING, Role.ADMIN)
    for role in Role:
        if role is not Role.ADMIN:
            assert not can_write(resources.ANALYTICS_SETTING, role), role


@pytest.mark.parametrize("role", [r for r in Role if r is not Role.ADMIN])
def test_only_the_administrator_reads_the_platforms_health(role: Role) -> None:
    assert not can_read(resources.HEALTH_REPORT, role)
    assert "health" not in cat.sections_for(role.value)


@pytest.mark.parametrize("role", [Role.DATA_SUBJECT, Role.BREACH_HOLDER])
def test_a_data_principal_and_a_temporary_holder_reach_none_of_it(role: Role) -> None:
    for resource in PARTS:
        assert not can_read(resource, role), resource
    assert cat.sections_for(role.value) == []


def test_breach_figures_reach_only_management_and_the_officers() -> None:
    for m in cat.CATALOGUE:
        if m.group == "Breaches":
            assert m.audience <= {"management", "dpo", "legal"}, m.key


def test_every_report_kind_reaches_only_roles_with_the_report_resource() -> None:
    for kind in cat.REPORTS.values():
        for role in kind.audience:
            assert can_read(resources.REPORT, role), (kind.key, role)
