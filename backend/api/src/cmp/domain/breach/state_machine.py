"""Open and closed, and what stands in the way of closing.

The duties run in parallel on their own clocks, so the state machine does not
walk a breach through them - `reported → assessed → notified` would have put
assessment in front of duties due without delay. It gates one thing: a breach
closes only when it has been determined one way or the other, every duty
that applies is done, and no breach ticket is still open (S3-08). Reopening is
always allowed, with a reason, and recorded.

Pure, like the project and rights machines: a status, and a snapshot of facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from cmp.core.errors import TransitionNotPermitted, ValidationFailed


class Status(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class BreachFacts:
    #: The latest determination's outcome: pending, yes or no.
    determination: str = "pending"
    #: Duties created and neither done nor not applicable, by label.
    outstanding: tuple[str, ...] = ()
    #: Breach tickets issued or returned: still owed something (S3-08, BD-17).
    open_tickets: int = 0


def blockers(current: str, target: str, facts: BreachFacts) -> list[str]:
    """Every reason this move cannot be made now, in the order to clear them."""
    if current == Status.OPEN and target == Status.CLOSED:
        out: list[str] = []
        if facts.determination == "pending":
            out.append("Record whether this is a personal data breach before closing it")
        out.extend(f"{label} is outstanding" for label in facts.outstanding)
        if facts.open_tickets:
            n = facts.open_tickets
            out.append(f"{n} breach ticket{'s are' if n != 1 else ' is'} still open")
        return out
    if current == Status.CLOSED and target == Status.OPEN:
        return []
    return [f"A breach cannot move from {current} to {target}"]


def available(current: str, facts: BreachFacts) -> list[dict[str, object]]:
    """The one move out of the current state, and what blocks it."""
    target = Status.CLOSED if current == Status.OPEN else Status.OPEN
    found = blockers(current, target, facts)
    return [
        {
            "to": target.value,
            "allowed": not found,
            "blocked_by": found[0] if found else None,
            "blockers": found,
            "reason_required": target == Status.OPEN,
        }
    ]


def validate(current: str, target: str, facts: BreachFacts, reason: str | None) -> None:
    try:
        Status(target)
    except ValueError:
        raise ValidationFailed("Choose open or closed", field="to") from None
    if current == target:
        raise TransitionNotPermitted(f"This breach is already {current}")
    found = blockers(current, target, facts)
    if found:
        raise TransitionNotPermitted(found[0], details={"blockers": found})
    if target == Status.OPEN and not (reason or "").strip():
        raise ValidationFailed("Say why the breach is being reopened", field="reason")
