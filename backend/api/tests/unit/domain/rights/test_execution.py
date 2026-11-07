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
    returned = [
        {
            "label": "Lab A",
            "ticket_status": "returned",
            "accepted_at": "2026-10-08",
            "return_outcome": "done",
        }
    ]
    assert execution.complete_blocked_by("correction", [], returned) is None
    # A return from before outcomes were asked (NULL) reads as done, as it did then.
    legacy = [
        {
            "label": "Lab A",
            "ticket_status": "returned",
            "accepted_at": "2026-10-08",
            "return_outcome": None,
        }
    ]
    assert execution.complete_blocked_by("correction", [], legacy) is None


@pytest.mark.parametrize("outcome", ["partial", "failed"])
def test_a_return_that_says_it_fell_short_blocks_complete(outcome: str) -> None:
    """DPDP-1: a ticket returned "unable to erase" is not the work done."""
    short = [
        {
            "label": "Lab A",
            "ticket_status": "returned",
            "accepted_at": "2026-10-08",
            "return_outcome": outcome,
        }
    ]
    reason = execution.complete_blocked_by("correction", [], short)
    assert reason is not None and "Lab A" in reason
    assert execution.account("correction", [], short)["holders_confirmed"] == []


def test_access_is_never_blocked_by_execution() -> None:
    assert execution.complete_blocked_by("access", [], []) is None
    assert execution.account("access", [], []) is None


# ------------------------------------------- reports from the public link (0065)
def _report(reference: str, *, erased: bool = False) -> dict[str, Any]:
    return {
        "reference": reference,
        "reporter_erased_at": "2026-11-07T10:00:00Z" if erased else None,
    }


def test_a_report_still_naming_her_blocks_complete() -> None:
    reason = execution.complete_blocked_by("erasure", [], [], reports=[_report("INC-2026-0001")])
    assert reason is not None and "still on 1 report(s)" in reason


def test_the_blocker_counts_reports_and_names_none() -> None:
    """An administrator may read it on a request about the office."""
    reports = [
        _report("INC-2026-0001"),
        _report("INC-2026-0002"),
        _report("INC-2026-0003", erased=True),
    ]
    reason = execution.complete_blocked_by("erasure", [_item("quarantine")], [], reports=reports)
    assert reason is not None and "2 report(s)" in reason
    assert "INC-" not in reason


def test_an_erased_report_is_something_done() -> None:
    """No item and no holder, and her name taken off one report: that is complete."""
    reports = [_report("INC-2026-0001", erased=True)]
    assert execution.complete_blocked_by("erasure", [], [], reports=reports) is None
    assert execution.complete_blocked_by("erasure", [], []) is not None


def test_reports_that_could_not_be_looked_for_block_complete() -> None:
    reason = execution.complete_blocked_by("erasure", [_item("quarantine")], [], reports=None)
    assert reason is not None and "could not be checked" in reason


def test_access_is_never_blocked_by_reports() -> None:
    for reports in ([_report("INC-2026-0001")], None):
        assert execution.complete_blocked_by("access", [], [], reports=reports) is None


def test_a_correction_is_not_reached_by_reports() -> None:
    """Only an erasure takes her off a report, so only an erasure waits for it."""
    returned = [
        {
            "label": "Lab A",
            "ticket_status": "returned",
            "accepted_at": "x",
            "return_outcome": "done",
        }
    ]
    reports = [_report("INC-2026-0001")]
    assert execution.complete_blocked_by("correction", [], returned, reports=reports) is None
    assert execution.complete_blocked_by("correction", [], [], reports=None) is not None
    assert execution.account("correction", [], [], reports)["public_reports"] == []


def test_the_account_lists_each_report_and_not_done_names_the_unerased() -> None:
    done = execution.account(
        "erasure",
        [_item("quarantine")],
        [],
        [_report("INC-2026-0001", erased=True), _report("INC-2026-0002")],
    )
    assert done is not None
    assert [(e["report"], e["done"]) for e in done["public_reports"]] == [
        ("INC-2026-0001", True),
        ("INC-2026-0002", False),
    ]
    assert "erased" in done["public_reports"][0]["outcome"]
    assert "Not yet erased" in done["public_reports"][1]["outcome"]
    assert done["not_done"] == ["INC-2026-0002"]
    assert done["kept_of_a_report"] == execution.KEPT_OF_A_REPORT
    assert execution.account("erasure", [], [])["kept_of_a_report"] is None


def test_the_administrator_is_not_sent_to_a_card_they_do_not_have() -> None:
    """On a request about the office the administrator is shown no reports
    and may not erase them: the sentence says who can, and still never a
    report's number."""
    reports = [_report("INC-2026-0001")]
    officer = execution.complete_blocked_by("erasure", [], [], reports=reports)
    assert officer is not None and "Erase them from the Holders tab" in officer
    other = execution.complete_blocked_by("erasure", [], [], reports=reports, officer=False)
    assert other is not None and "INC-2026-0001" not in other
    assert "Holders tab" not in other and "1 report(s)" in other
    assert "Only the DPO or the Legal office can take them off" in other
    assert "answer partial" in other
