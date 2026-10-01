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

Everything else closes `partial`, and the response says, item by item, what
happened, in words that never say "erased" for what was not.

This stays after S2-03: the executor writes the evidence; this decides what
the evidence allows the response to say.
"""

from __future__ import annotations

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
    return holder.get("ticket_status") == Ticket.RETURNED and holder["return_outcome"] in (
        None,
        ReturnOutcome.DONE,
    )


def returned_short(holder: Row) -> bool:
    """Returned, saying it did only part of it, or none."""
    return holder.get("ticket_status") == Ticket.RETURNED and holder["return_outcome"] in (
        ReturnOutcome.PARTIAL,
        ReturnOutcome.FAILED,
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


def account(kind: str, items: list[Row], holders: list[Row]) -> dict[str, Any] | None:
    """The record's account of what was done, for erasure and correction."""
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
    return {
        "items": entries,
        "not_done": [e["asset"] for e in entries if not e["done"]],
        # Decided with the user for S2-03: records of what happened are not
        # rewritten by an erasure, and the response says so rather than hiding it.
        "kept_as_evidence": KEPT_AS_EVIDENCE if kind == Kind.ERASURE else None,
        "holders_confirmed": [str(h["label"]) for h in holders if returned_done(h)],
        # Back, but saying they could not do all of it: named, never counted as done.
        "holders_short": [
            {"holder": str(h["label"]), "outcome": str(h["return_outcome"])}
            for h in holders
            if returned_short(h)
        ],
    }


def why_not_complete(kind: str, items: list[Row], holders: list[Row]) -> str | None:
    """None when `complete` is earned; otherwise the sentence that says why not."""
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
    if not items and not returned:
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


def complete_blocked_by(kind: str, items: list[Row], holders: list[Row]) -> str | None:
    """Why this request may not close as `complete`, or None when it may.

    The one answer to the question, used by `respond` to refuse and served on
    the request so the console can say so before anybody presses the button -
    the console holds no copy of the rule.
    """
    return unreturned_reason(holders) or why_not_complete(kind, items, holders)
