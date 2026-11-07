"""What was actually done, item by item - and what a response may claim (S2-02).

An erasure decision changes her disposition on the `asset_consent` row; until
the executor (S2-03) exists nothing is deleted anywhere. A request that closed
as `complete` still read to her as "erased". So `complete` is a claim this
module has to be able to back, for the two kinds of request that ask for a
change rather than a copy:

* **An item is done** only when it was applied *and* there is evidence it was
  carried out. A quarantine applied is its own evidence - the flag is the act,
  the platform's and nobody else's. An erase or a redaction needs the execution
  record S2-03 writes (`executed_at`); nothing here writes it, so today no
  erase or redaction counts as done, which is the truth. A retained item is not
  done: it was lawfully kept, not erased. An undecided one never reaches here -
  the state machine will not close a request holding one.
* **A correction is done** only by a holder that returned its ticket; the
  platform changes no record itself yet (S3-05).
* **Nothing done at all is not complete** - no item and no holder's return is a
  request nobody carried out, however it is worded. `no_records` is the honest
  answer when nothing is held.
* **A report she sent through the public link** that an office dismissed is
  done when her name and email are erased from it (0065). It is not an item,
  because items are her appearances in assets; an erasure that still leaves
  her on one is not complete, and one whose only act was erasing her from a
  report is.

Everything else closes `partial`, and the response says, item by item, what
happened, in words that never say "erased" for what was not.

This stays after S2-03: the executor writes the evidence; this decides what
the evidence allows the response to say.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from typing import Any

from cmp.core.enums import RightsItemState as ItemState
from cmp.core.enums import RightsRequestType as Kind
from cmp.core.enums import RightsScopeDecision as Decision
from cmp.core.enums import RightsTicketStatus as Ticket

Row = dict[str, Any]


KEPT_AS_EVIDENCE = (
    "Kept, because they are the record of what happened and are never rewritten: "
    "your consent records, the audit trail, the files of data sent to processors "
    "before your request, and earlier responses given to you."
)

KEPT_OF_A_REPORT = (
    "Of a report you sent through the public link that was not taken up, these are kept: "
    "its reference, what you wrote, why it was not taken up and who decided. They are the "
    "office's record of what it did with what it was told."
)


class ReturnOutcome(StrEnum):
    """What a holder says it did with its ticket (review 2026-10-01, DPDP-1).

    A return used to be taken as the work done, whatever it said - a ticket
    returned "unable to erase" let the request close complete. Only `done`
    counts as done now.
    """

    DONE = "done"
    PARTIAL = "partial"
    FAILED = "failed"


def returned_done(holder: Row) -> bool:
    """Returned, and saying it did all of it. NULL is a return from before the
    holder was asked (0037), read as done, which is how it was taken then.

    `holder["return_outcome"]`, not `.get()`: a query that forgot the column
    would otherwise read as NULL - as done - and a "failed" return would pass.
    """
    # Only an answer the office accepted counts (0048).
    return (
        holder.get("ticket_status") == Ticket.RETURNED
        and holder.get("accepted_at") is not None
        and holder["return_outcome"] in (None, ReturnOutcome.DONE)
    )


def returned_short(holder: Row) -> bool:
    """Returned, saying it did only part of it, or none."""
    return (
        holder.get("ticket_status") == Ticket.RETURNED
        and holder.get("accepted_at") is not None
        and holder["return_outcome"] in (ReturnOutcome.PARTIAL, ReturnOutcome.FAILED)
    )


def label(item: Row) -> str:
    """How an asset is named to the office and to her: its own reference."""
    return str(item.get("source_asset_ref") or item.get("asset_uuid"))


def is_done(item: Row) -> bool:
    if item.get("state") != ItemState.APPLIED:
        return False
    if item.get("decision") == Decision.QUARANTINE:
        return True
    return item.get("executed_at") is not None


def describe(item: Row) -> str:
    """What happened to one item, in words that claim nothing that did not."""
    decision = item.get("decision")
    done = is_done(item)
    if decision is None:
        return "Not yet decided."
    if decision == Decision.QUARANTINE:
        return (
            "Quarantined: kept out of any use or release. Not erased."
            if done
            else "Decided for quarantine; not yet carried out."
        )
    if decision == Decision.RETAIN:
        return (
            f"Retained until {item.get('retain_until')} under a legal obligation the "
            "Privacy Office has stated; not erased."
        )
    # Applying an erasure or redaction quarantines first (S2-03); the executor
    # moves it on only when every store that holds it is confirmed.
    held_back = " and kept out of use" if item.get("state") == ItemState.APPLIED else ""
    if decision == Decision.REDACT:
        return (
            "Redacted: your part removed; the material holds other people and was kept."
            if done
            else f"Decided for redaction{held_back}; not yet carried out."
        )
    return "Erased." if done else f"Decided for erasure{held_back}; not yet carried out."


def erased(report: Row) -> bool:
    """Her name and email are off this report."""
    return report.get("reporter_erased_at") is not None


def account(
    kind: str, items: list[Row], holders: list[Row], reports: Sequence[Row] = ()
) -> dict[str, Any] | None:
    """The record's account of what was done, for erasure and correction.

    `reports` are the dismissed reports from the public link found for her and
    those erased under this request; only an erasure reaches them.
    """
    if kind not in (Kind.ERASURE, Kind.CORRECTION):
        return None
    entries = [
        {
            "asset": label(i),
            "decision": i.get("decision"),
            "done": is_done(i),
            "outcome": describe(i),
        }
        for i in items
    ]
    reported = [
        {
            "report": str(r["reference"]),
            "done": erased(r),
            "outcome": (
                "Your name and email were erased from it."
                if erased(r)
                else "Not yet erased: it still carries your name and email."
            ),
        }
        for r in (reports if kind == Kind.ERASURE else ())
    ]
    return {
        "items": entries,
        "public_reports": reported,
        "not_done": [e["asset"] for e in entries if not e["done"]]
        + [e["report"] for e in reported if not e["done"]],
        # Decided with the user for S2-03: records of what happened are not
        # rewritten by an erasure, and the response says so rather than hiding it.
        "kept_as_evidence": KEPT_AS_EVIDENCE if kind == Kind.ERASURE else None,
        "kept_of_a_report": KEPT_OF_A_REPORT if reported else None,
        "holders_confirmed": [str(h["label"]) for h in holders if returned_done(h)],
        # Back, but saying they could not do all of it: named, never counted as done.
        "holders_short": [
            {"holder": str(h["label"]), "outcome": str(h["return_outcome"])}
            for h in holders
            if returned_short(h)
        ],
    }


def why_not_complete(
    kind: str, items: list[Row], holders: list[Row], reports: Sequence[Row] | None = ()
) -> str | None:
    """None when `complete` is earned; otherwise the sentence that says why not.

    `reports` is None when they could not be looked for. The sentence about them
    gives a count and never a report's number: an administrator may read it on
    a request about the office, and the reports are the officers' to see.
    """
    if kind not in (Kind.ERASURE, Kind.CORRECTION):
        return None
    returned = [h for h in holders if returned_done(h)]
    short = [str(h["label"]) for h in holders if returned_short(h)]
    if short:
        return (
            "Reported as not fully done by "
            + ", ".join(short)
            + ". The response can go out on time, but it is partial and says what remains;"
            " send the ticket back if the holder can still finish."
        )
    undone = [label(i) for i in items if not is_done(i)]
    if undone:
        return (
            "Not carried out yet: "
            + ", ".join(undone)
            + ". The response can go out on time, but it is partial and says what remains."
        )
    # Only an erasure reaches a report from the public link.
    if kind == Kind.ERASURE and reports is None:
        return (
            "Whether the requester sent a report through the public link could not be "
            "checked just now. Reload before answering complete."
        )
    reached = list(reports or ()) if kind == Kind.ERASURE else []
    naming = [r for r in reached if not erased(r)]
    if naming:
        return (
            f"The requester's name and email are still on {len(naming)} report(s) they sent "
            "through the public link. Erase them from the Holders tab, or answer partial."
        )
    if not items and not returned and not any(erased(r) for r in reached):
        what = "corrected" if kind == Kind.CORRECTION else "erased"
        return (
            f"Nothing in this request has been {what}: no item in scope has been carried "
            "out and no holder has returned its ticket. Answer it as partial, or as no "
            "records if nothing is held."
        )
    return None


def unreturned(holders: list[Row]) -> list[Row]:
    return [h for h in holders if h.get("ticket_status") in (Ticket.ISSUED, Ticket.ESCALATED)]


def unreturned_reason(holders: list[Row]) -> str | None:
    gap = unreturned(holders)
    if not gap:
        return None
    return (
        "A holder has not returned its ticket: "
        + ", ".join(str(h["label"]) for h in gap)
        + ". The response can go out on time, but it is partial and the gap is named."
    )


def complete_blocked_by(
    kind: str, items: list[Row], holders: list[Row], *, reports: Sequence[Row] | None = ()
) -> str | None:
    """Why this request may not close as `complete`, or None when it may.

    The one answer to the question, used by `respond` to refuse and served on
    the request so the console can say so before anybody presses the button -
    the console holds no copy of the rule.
    """
    return unreturned_reason(holders) or why_not_complete(kind, items, holders, reports)
