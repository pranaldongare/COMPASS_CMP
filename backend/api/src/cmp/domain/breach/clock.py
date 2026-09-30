# ruff: noqa: E501 - the table of duties below is read as a table; wrapped, it is not.
"""The duties a breach starts, and the clock on each.

Four duties, running in parallel from two different moments:

| Duty | Created when | Due | Basis |
|---|---|---|---|
| Report to CERT-In | marked a reportable cyber incident | 6 hours from detection | CERT-In Directions 2022, IT Act s.70B |
| Board - initial intimation | determined a personal data breach | without delay | Rule 7(2)(a) |
| Board - detailed report | determined a personal data breach | 72 hours from awareness, or what the Board allows | Rule 7(2)(b) |
| Principals notified | determined a personal data breach | without delay | Rule 7(1) |

Three rules, each the opposite of something that looks simpler:

**A due time is stored when the duty is created and never recomputed** - the
rule `cmp.domain.rights.clock` follows. An extension or a reinstatement is a
new row carrying a new due time, and the state of a duty is read by folding its
events in order.

**"Without delay" has no statutory hours**, so it has no due time. The duty
shows the time elapsed since awareness and is flagged against the internal
target in `settings.breach_without_delay_target_hours` - and flagged against
nothing while that is unset. The number is Legal's to choose, not this file's.

**Nothing here reads encryption.** Whether exposed data was sealed bears on
whether an event *is* a breach under s.2(u), which is the determination a
person records. Once it is determined, every duty stands, sealed or not.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Final

from cmp.core.config import settings

#: CERT-In Directions of 28 April 2022, direction (ii): report within six
#: hours of noticing. Statute, not policy.
CERT_IN_HOURS: Final = 6
#: Rule 7(2)(b): the detailed report within seventy-two hours of becoming
#: aware, or such longer period as the Board may allow.
BOARD_REPORT_HOURS: Final = 72


class Duty(StrEnum):
    CERT_IN = "cert_in"
    BOARD_INTIMATION = "board_intimation"
    BOARD_REPORT = "board_report"
    PRINCIPALS = "principals"


#: The three duties a determination creates. CERT-In stands on its own test.
DPDP_DUTIES: Final[tuple[Duty, ...]] = (
    Duty.BOARD_INTIMATION,
    Duty.BOARD_REPORT,
    Duty.PRINCIPALS,
)

LABELS: Final[dict[str, str]] = {
    Duty.CERT_IN: "Report to CERT-In",
    Duty.BOARD_INTIMATION: "Board - initial intimation",
    Duty.BOARD_REPORT: "Board - detailed report",
    Duty.PRINCIPALS: "Principals notified",
}

BASIS: Final[dict[str, str]] = {
    Duty.CERT_IN: "CERT-In Directions 2022 (IT Act s.70B): within 6 hours of noticing",
    Duty.BOARD_INTIMATION: "Rule 7(2)(a): without delay",
    Duty.BOARD_REPORT: "Rule 7(2)(b): within 72 hours of becoming aware, or as the Board allows",
    Duty.PRINCIPALS: "Rule 7(1): without delay, to each affected Data Principal",
}


class State(StrEnum):
    OUTSTANDING = "outstanding"
    DONE = "done"
    NOT_APPLICABLE = "not_applicable"


class EventKind(StrEnum):
    COMPLETED = "completed"
    NOT_APPLICABLE = "not_applicable"
    REINSTATED = "reinstated"
    EXTENDED = "extended"
    REOPENED = "reopened"


def due_for(duty: Duty | str, anchor: datetime) -> datetime | None:
    """When a duty created now, anchored at `anchor`, falls due. None is "without
    delay". Called once, when the duty is created or reinstated."""
    if duty == Duty.CERT_IN:
        return anchor + timedelta(hours=CERT_IN_HOURS)
    if duty == Duty.BOARD_REPORT:
        return anchor + timedelta(hours=BOARD_REPORT_HOURS)
    return None


def fold(obligation: dict[str, Any], events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """A duty's current state, read from the row that created it and its events
    in the order they were written.

    Nothing is recomputed: every due time in the answer is one that was stored.
    """
    state = State.OUTSTANDING
    due_at: datetime | None = obligation["due_at"]
    anchored_at: datetime | None = obligation["anchored_at"]
    completed: dict[str, Any] | None = None
    extension: dict[str, Any] | None = None
    for event in events:
        kind = event["kind"]
        if kind == EventKind.COMPLETED:
            state = State.DONE
            completed = event
        elif kind == EventKind.NOT_APPLICABLE:
            state = State.NOT_APPLICABLE
        elif kind == EventKind.REINSTATED:
            state = State.OUTSTANDING
            due_at = event["due_at"]
            anchored_at = event["anchored_at"]
            completed = None
        elif kind == EventKind.EXTENDED:
            due_at = event["due_at"]
            extension = event
        elif kind == EventKind.REOPENED:
            state = State.OUTSTANDING
            completed = None
    return {
        "state": state,
        "due_at": due_at,
        "anchored_at": anchored_at,
        "completed_at": completed["occurred_at"] if completed else None,
        "reference": completed["reference"] if completed else None,
        "extended_until": extension["due_at"] if extension else None,
        "extension_requested_at": extension["requested_at"] if extension else None,
    }


def timing(
    state: str,
    due_at: datetime | None,
    anchored_at: datetime | None,
    *,
    now: datetime | None = None,
    target_hours: float | None = None,
) -> dict[str, Any]:
    """The clock a person reads: time left or overdue for a dated duty; time
    elapsed, against the internal target if one is set, for "without delay".

    `target_hours` defaults to the setting, read at the moment of asking: the
    target flags; it is not a due time, and nothing stores it.
    """
    moment = now or datetime.now(UTC)
    target = settings.breach_without_delay_target_hours if target_hours is None else target_hours
    live = state == State.OUTSTANDING
    out: dict[str, Any] = {
        "without_delay": due_at is None,
        "seconds_remaining": None,
        "overdue": False,
        "seconds_elapsed": None,
        "target_at": None,
        "past_target": False,
    }
    if anchored_at is not None:
        out["seconds_elapsed"] = int((moment - anchored_at).total_seconds())
    if due_at is not None:
        out["seconds_remaining"] = int((due_at - moment).total_seconds())
        out["overdue"] = live and moment > due_at
    elif anchored_at is not None and target:
        target_at = anchored_at + timedelta(hours=target)
        out["target_at"] = target_at
        out["past_target"] = live and moment > target_at
    return out
