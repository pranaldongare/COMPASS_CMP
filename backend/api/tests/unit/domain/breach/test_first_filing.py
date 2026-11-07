"""Which filing a yes counts for a regulator's duty a no had set aside (ADR 0037).

The one that would have completed it had nothing set it aside: the first
recorded, the earlier version where two were recorded at once. A report that
is not filed, is of another kind or came back with no reference completes
nothing, as filing it would not have.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from cmp.domain.breach.reports import Kind, _first_filing

NOW = datetime.now(UTC)


def _report(
    version: int,
    *,
    kind: Kind = Kind.BOARD_INTIMATION,
    recorded: timedelta | None = timedelta(0),
    reference: str | None = "DPB/1",
) -> dict[str, Any]:
    filed = recorded is not None
    return {
        "kind": kind.value,
        "version": version,
        "filed_at": NOW - timedelta(hours=1) if filed else None,
        "filed_reference": reference if filed else None,
        "filed_recorded_at": NOW + recorded if recorded is not None else None,
    }


def test_the_first_recorded_counts_whatever_its_version() -> None:
    later = _report(1, recorded=timedelta(minutes=5), reference="DPB/1")
    first = _report(2, recorded=timedelta(0), reference="DPB/2")
    assert _first_filing([later, first], Kind.BOARD_INTIMATION) is first


def test_recorded_at_once_the_earlier_version_counts() -> None:
    newer, older = _report(2, reference="DPB/2"), _report(1, reference="DPB/1")
    assert _first_filing([newer, older], Kind.BOARD_INTIMATION) is older


def test_one_not_filed_is_passed_over() -> None:
    unfiled = _report(1, recorded=None)
    filed = _report(2, recorded=timedelta(minutes=5))
    assert _first_filing([unfiled, filed], Kind.BOARD_INTIMATION) is filed


def test_another_kinds_filing_is_not_this_ones() -> None:
    other = _report(1, kind=Kind.BOARD_REPORT, recorded=timedelta(0))
    mine = _report(1, recorded=timedelta(minutes=5))
    assert _first_filing([other, mine], Kind.BOARD_INTIMATION) is mine
    assert _first_filing([other], Kind.BOARD_INTIMATION) is None


def test_a_filing_with_no_reference_completes_nothing() -> None:
    bare = _report(1, recorded=timedelta(0), reference=None)
    blank = _report(2, recorded=timedelta(minutes=1), reference="")
    said = _report(3, recorded=timedelta(minutes=5))
    assert _first_filing([bare, blank, said], Kind.BOARD_INTIMATION) is said
    assert _first_filing([bare, blank], Kind.BOARD_INTIMATION) is None


def test_nothing_filed_is_none() -> None:
    assert _first_filing([], Kind.BOARD_REPORT) is None
