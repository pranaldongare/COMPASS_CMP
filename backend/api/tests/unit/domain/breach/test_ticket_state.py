"""A breach ticket's state, folded from its events (S3-08), and what it blocks."""

from __future__ import annotations

import pytest

from cmp.domain.breach import state_machine
from cmp.domain.breach.state_machine import BreachFacts
from cmp.domain.breach.ticket_state import OPEN, TicketState, fold, may_write, moves


def _events(*kinds: str) -> list[dict[str, str]]:
    return [{"kind": k} for k in kinds]


@pytest.mark.parametrize(
    ("kinds", "state"),
    [
        ((), TicketState.ISSUED),
        (("returned",), TicketState.RETURNED),
        (("returned", "sent_back"), TicketState.ISSUED),
        (("returned", "closed"), TicketState.CLOSED),
        (("withdrawn",), TicketState.WITHDRAWN),
        (("returned", "closed", "reopened"), TicketState.ISSUED),
        (("withdrawn", "reopened", "returned"), TicketState.RETURNED),
    ],
)
def test_the_state_is_where_the_events_leave_it(kinds: tuple[str, ...], state: TicketState) -> None:
    assert fold(_events(*kinds)) == state


def test_only_the_office_closes_and_only_a_returned_ticket() -> None:
    """BD-07: the holder has no close, withdraw or reopen at all."""
    office = {
        s: [m["move"] for m in moves(s, side="office", breach_open=True)] for s in TicketState
    }
    holder = {
        s: [m["move"] for m in moves(s, side="holder", breach_open=True)] for s in TicketState
    }
    assert office == {
        TicketState.ISSUED: ["withdraw"],
        TicketState.RETURNED: ["send_back", "close", "withdraw"],
        TicketState.CLOSED: ["reopen"],
        TicketState.WITHDRAWN: ["reopen"],
    }
    assert holder == {
        TicketState.ISSUED: ["return"],
        TicketState.RETURNED: [],
        TicketState.CLOSED: [],
        TicketState.WITHDRAWN: [],
    }
    assert all(
        m["reason_required"]
        for m in moves(TicketState.RETURNED, side="office", breach_open=True)
        if m["move"] != "close"
    )


def test_nothing_moves_on_a_closed_breach() -> None:
    for state in TicketState:
        assert moves(state, side="office", breach_open=False) == []
        assert moves(state, side="holder", breach_open=False) == []


def test_issued_and_returned_are_open_and_may_be_written_on() -> None:
    assert {TicketState.ISSUED, TicketState.RETURNED} == OPEN
    assert [s for s in TicketState if may_write(s)] == [TicketState.ISSUED, TicketState.RETURNED]


@pytest.mark.parametrize(
    ("n", "line"), [(1, "1 breach ticket is still open"), (2, "2 breach tickets are still open")]
)
def test_an_open_ticket_keeps_the_breach_open(n: int, line: str) -> None:
    facts = BreachFacts(determination="yes", outstanding=(), open_tickets=n)
    assert state_machine.blockers("open", "closed", facts) == [line]
    assert state_machine.blockers("open", "closed", BreachFacts(determination="yes")) == []
