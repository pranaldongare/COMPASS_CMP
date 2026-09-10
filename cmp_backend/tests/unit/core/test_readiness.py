"""Readiness compares the deployed schema with the head this build ships.

A readiness check that accepted any `alembic_version` row put a replica into
rotation against a schema twenty migrations old (reproduced by the September
2026 review with revision 0001 against a head of 0022).
"""

from __future__ import annotations

import re
from pathlib import Path

from cmp.api.routers.v1.system import expected_schema_head, migrations_check


def _highest_revision_on_disk() -> str:
    versions = Path(__file__).resolve().parents[3] / "migrations" / "versions"
    names = [p.name for p in versions.glob("[0-9][0-9][0-9][0-9]_*.py")]
    assert names, "the migrations directory must be beside the tests"
    return max(m.group(1) for n in names if (m := re.match(r"^(\d{4})_", n)))


class TestExpectedHead:
    def test_the_head_is_the_newest_migration_on_disk(self) -> None:
        assert expected_schema_head() == _highest_revision_on_disk()


class TestMigrationsCheck:
    def test_no_row_is_not_ready(self) -> None:
        ok, detail = migrations_check(None, "0023")
        assert not ok
        assert detail and "alembic upgrade head" in detail

    def test_an_old_schema_is_not_ready_and_names_both_revisions(self) -> None:
        ok, detail = migrations_check("0001", "0023")
        assert not ok
        assert detail and "0001" in detail and "0023" in detail

    def test_the_expected_head_is_ready(self) -> None:
        assert migrations_check("0023", "0023") == (True, None)

    def test_an_unknown_head_is_ready_but_says_so(self) -> None:
        ok, detail = migrations_check("0023", None)
        assert ok
        assert detail and "unknown" in detail
