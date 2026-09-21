"""The clock on a rights request.

Every date in the flow is expressed relative to two fixed points: the moment
the request was received (D0) and the day the response is due (D). Everything
between is a checkpoint - acknowledge by D0+2, ticket the holders by D0+5, take
stock at halfway, stop collecting at D-5 so there is time to collate - and the
checkpoints are here so the console, the acknowledgement email and the
dashboard cannot disagree about when any of them falls.

Two decisions are worth stating because they are the ones people argue about:

**The clock starts on receipt, not on verification.** Verifying somebody can
take days if the code goes to a channel she no longer reads, and a clock that
waited for it would let a slow verification quietly eat the response window.
The statute counts from the request; so does this.

**`due_at` is stored, not computed.** The period is copied onto the request at
receipt and read back from the row. A period changed in configuration applies
to the next request, never to one already running - moving a deadline nobody
was told about is worse than either value of the setting.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from cmp.core.config import settings
from cmp.core.enums import RightsRequestType

_DAY = timedelta(days=1)


def response_period_days(request_type: RightsRequestType | str) -> int:
    """The published period for this kind of request, in days.

    A grievance may run on a different period from a request about data - Rule
    14(3) asks for each to be published - so the two are separate settings with
    the same default.
    """
    if request_type == RightsRequestType.GRIEVANCE:
        return settings.grievance_response_period_days
    return settings.rights_response_period_days


def due_for(request_type: RightsRequestType | str, received_at: datetime) -> datetime:
    """When a request received now is due. Called once, at receipt."""
    return received_at + timedelta(days=response_period_days(request_type))


@dataclass(frozen=True, slots=True)
class Checkpoint:
    """One named point on the clock, and whether it has passed."""

    key: str
    label: str
    at: datetime
    passed: bool


@dataclass(frozen=True, slots=True)
class Clock:
    received_at: datetime
    due_at: datetime
    acknowledge_by: datetime
    tickets_by: datetime
    halfway_at: datetime
    collate_by: datetime
    now: datetime
    closed: bool = False

    @property
    def days_remaining(self) -> int:
        """Whole days until D. Negative once overdue - the sign is the point."""
        remaining = self.due_at - self.now
        days = remaining / _DAY
        # Round away from zero so "due tomorrow at noon" reads as 1, not 0.
        return int(days) if days == int(days) else (int(days) + 1 if days > 0 else int(days) - 1)

    @property
    def overdue(self) -> bool:
        return not self.closed and self.now > self.due_at

    @property
    def at_risk(self) -> bool:
        """Past the collation checkpoint and still open: the window is closing."""
        return not self.closed and not self.overdue and self.now >= self.collate_by

    @property
    def progress(self) -> float:
        """How much of the period has elapsed, 0 to 1. Clamped, so overdue reads as 1."""
        total = (self.due_at - self.received_at) / _DAY
        if total <= 0:
            return 1.0
        elapsed = (self.now - self.received_at) / _DAY
        return max(0.0, min(1.0, elapsed / total))

    def checkpoints(self) -> list[Checkpoint]:
        """The path's clock column, in order, with what has passed."""
        points = [
            ("received", "Received", self.received_at),
            ("acknowledge", "Acknowledge", self.acknowledge_by),
            ("tickets", "Tickets issued", self.tickets_by),
            ("halfway", "Halfway", self.halfway_at),
            ("collate", "Collate", self.collate_by),
            ("due", "Respond", self.due_at),
        ]
        return [Checkpoint(k, label, at, self.now >= at) for k, label, at in points]

    @property
    def next_checkpoint(self) -> Checkpoint | None:
        """The first checkpoint still ahead, or none once D has passed."""
        for point in self.checkpoints():
            if not point.passed:
                return point
        return None

    def as_dict(self) -> dict[str, Any]:
        """The shape the API returns. Every instant is an ISO-8601 timestamp."""
        nxt = self.next_checkpoint
        return {
            "received_at": self.received_at,
            "due_at": self.due_at,
            "acknowledge_by": self.acknowledge_by,
            "tickets_by": self.tickets_by,
            "halfway_at": self.halfway_at,
            "collate_by": self.collate_by,
            "days_remaining": self.days_remaining,
            "overdue": self.overdue,
            "at_risk": self.at_risk,
            "progress": round(self.progress, 3),
            "checkpoints": [
                {"key": c.key, "label": c.label, "at": c.at, "passed": c.passed}
                for c in self.checkpoints()
            ],
            "next_checkpoint": nxt.key if nxt else None,
        }


def compute(
    received_at: datetime,
    due_at: datetime,
    *,
    now: datetime | None = None,
    closed: bool = False,
) -> Clock:
    """Lay the checkpoints between D0 and D.

    Halfway is half of *this request's* period, not half of the configured
    one, so a request received under an older period still has a halfway that
    means what it says.
    """
    moment = now or datetime.now(UTC)
    period = due_at - received_at
    return Clock(
        received_at=received_at,
        due_at=due_at,
        acknowledge_by=received_at + timedelta(days=settings.rights_acknowledge_within_days),
        tickets_by=received_at + timedelta(days=settings.rights_tickets_within_days),
        halfway_at=received_at + period / 2,
        collate_by=due_at - timedelta(days=settings.rights_collate_before_days),
        now=moment,
        closed=closed,
    )
