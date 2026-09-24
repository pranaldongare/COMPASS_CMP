"""What a response may claim, decided without a database (S2-02)."""

from __future__ import annotations

from typing import Any

import pytest

from cmp.domain.rights import execution


def _item(decision: str | None, state: str = "applied", **kw: Any) -> dict[str, Any]:
    return {"decision": decision, "state": state, "source_asset_ref": "A-1", **kw}


def test_a_quarantine_applied_is_done_and_says_it_was_not_erased() -> None:
    item = _item("quarantine")
    assert execution.is_done(item)
    assert "not erased" in execution.describe(item).lower()


@pytest.mark.parametrize("decision", ["erase", "redact"])
def test_applied_is_not_done_without_the_execution_record(decision: str) -> None:
    item = _item(decision)
    assert not execution.is_done(item)
    assert "not yet carried out" in execution.describe(item)
    assert execution.is_done({**item, "executed_at": "2026-10-01T00:00:00Z"})


@pytest.mark.parametrize("decision", ["erase", "redact", "retain", "quarantine", None])
def test_nothing_not_done_is_described_as_erased(decision: str | None) -> None:
    said = execution.describe(_item(decision, state="decided")).lower()
    assert not said.startswith("erased") and "been erased" not in said


def test_a_retained_item_is_never_done() -> None:
    assert not execution.is_done(_item("retain", retain_until="2027-01-01"))


def test_the_blocker_names_an_unreturned_holder_first() -> None:
    holders = [{"label": "Lab A", "ticket_status": "issued"}]
    said = execution.complete_blocked_by("erasure", [_item("quarantine")], holders)
    assert said is not None and "Lab A" in said


def test_nothing_done_blocks_but_a_returned_correction_does_not() -> None:
    assert execution.complete_blocked_by("correction", [], []) is not None
    returned = [{"label": "Lab A", "ticket_status": "returned"}]
    assert execution.complete_blocked_by("correction", [], returned) is None


def test_access_is_never_blocked_by_execution() -> None:
    assert execution.complete_blocked_by("access", [], []) is None
    assert execution.account("access", [], []) is None
