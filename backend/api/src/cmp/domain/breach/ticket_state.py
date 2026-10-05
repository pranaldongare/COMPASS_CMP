"""A breach ticket's state, read from what happened to it (S3-08).

Pure, like the breach's own state machine: no database, no clock. A ticket is
*issued* when it is assigned; what happens afterwards is an append-only list of
events, and the state is where they leave it.

| From | Event | To | Who |
|---|---|---|---|
| (assignment) | | issued | DPO |
| issued | returned | returned | the holder |
| returned | sent back | issued | DPO |
| returned | closed | closed | the DPO only (BD-07) |
| issued, returned | withdrawn | withdrawn | DPO |
| closed, withdrawn | reopened | issued | DPO |

The moves a side may make are served with every ticket, so neither console
holds a copy of this table.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Any, Final


class TicketState(StrEnum):
    ISSUED = "issued"
    RETURNED = "returned"
    CLOSED = "closed"
    WITHDRAWN = "withdrawn"


class Move(StrEnum):
    RETURN = "return"
    SEND_BACK = "send_back"
    CLOSE = "close"
    WITHDRAW = "withdraw"
    REOPEN = "reopen"


class Outcome(StrEnum):
    """What the holder says it did. Only *done* is done."""

    DONE = "done"
    PARTIAL = "partial"
    FAILED = "failed"


#: Issued or returned: a ticket still owed something, which keeps its breach
#: from closing (BD-17) and may still be written on.
OPEN: Final[frozenset[TicketState]] = frozenset({TicketState.ISSUED, TicketState.RETURNED})

#: Where each event leaves a ticket, whatever it was before - the moves below
#: decide which events may be written in the first place.
_AFTER: Final[dict[str, TicketState]] = {
    "returned": TicketState.RETURNED,
    "sent_back": TicketState.ISSUED,
    "closed": TicketState.CLOSED,
    "withdrawn": TicketState.WITHDRAWN,
    "reopened": TicketState.ISSUED,
}

#: The event each move writes.
EVENT: Final[dict[Move, str]] = {
    Move.RETURN: "returned",
    Move.SEND_BACK: "sent_back",
    Move.CLOSE: "closed",
    Move.WITHDRAW: "withdrawn",
    Move.REOPEN: "reopened",
}

#: The office's moves, by state. The holder has none of these: no route to
#: close, withdraw or reopen exists for them at all.
OFFICE: Final[dict[TicketState, tuple[Move, ...]]] = {
    TicketState.ISSUED: (Move.WITHDRAW,),
    TicketState.RETURNED: (Move.SEND_BACK, Move.CLOSE, Move.WITHDRAW),
    TicketState.CLOSED: (Move.REOPEN,),
    TicketState.WITHDRAWN: (Move.REOPEN,),
}

#: The holder's one move.
HOLDER: Final[dict[TicketState, tuple[Move, ...]]] = {
    TicketState.ISSUED: (Move.RETURN,),
    TicketState.RETURNED: (),
    TicketState.CLOSED: (),
    TicketState.WITHDRAWN: (),
}

#: A move whose reason is required and sealed.
REASON_REQUIRED: Final[frozenset[Move]] = frozenset({Move.SEND_BACK, Move.WITHDRAW, Move.REOPEN})


def fold(events: Iterable[dict[str, Any]]) -> TicketState:
    """The state the events, in the order written, leave a ticket in."""
    state = TicketState.ISSUED
    for event in events:
        state = _AFTER[str(event["kind"])]
    return state


def moves(state: TicketState, *, side: str, breach_open: bool) -> list[dict[str, Any]]:
    """The moves this side may make now. None on a closed breach: nothing about
    a closed breach is recorded until it is reopened."""
    if not breach_open:
        return []
    table = OFFICE if side == "office" else HOLDER
    return [{"move": m.value, "reason_required": m in REASON_REQUIRED} for m in table[state]]


def may_write(state: TicketState) -> bool:
    """Either side may write on the thread while the ticket is open."""
    return state in OPEN
