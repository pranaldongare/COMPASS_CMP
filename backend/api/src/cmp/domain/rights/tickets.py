"""What a rights ticket is, in words, and what may be done with it next (2026-10-08).

The console drew a holder's buttons from its own copy of the rules - up to
seven of equal weight on a row, an "escalate" appearing at noon on the due day
because the browser and the server disagreed about what overdue meant. The
server now says, for each holder: its `state` in plain words, whether it is
`overdue`, and its `moves` - each with its label, whether it is the main one,
whether it needs a reason, whether it sends an email and so asks first. The
console renders that and holds no copy of the rules, as breach tickets do.

Overdue is one rule: the due moment has passed. The console sends the end of
the chosen day, so a ticket due today is overdue tomorrow.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Final

from cmp.core.enums import RightsRequestStatus as Status
from cmp.core.enums import RightsTicketStatus as Ticket

Row = dict[str, Any]

#: The states a holder is in, as the office reads them.
STATES: Final[dict[str, str]] = {
    "not_confirmed": "Not confirmed",
    "not_sent": "Not sent",
    "waiting": "Waiting",
    "sent_back": "Sent back",
    "overdue": "Overdue",
    "final_reminder": "Final reminder sent",
    "review": "Answered - review",
    "accepted": "Accepted",
    "withdrawn": "Withdrawn",
    "no_answer": "No answer",
}

OPEN: Final = (Ticket.ISSUED.value, Ticket.ESCALATED.value)

#: Request states in which tickets are still worked on.
WORKING: Final = (Status.IN_PROGRESS.value, Status.AWAITING_HOLDERS.value, Status.COLLATING.value)


def overdue(holder: Row, *, now: datetime | None = None) -> bool:
    due = holder.get("due_at")
    return (
        str(holder.get("ticket_status")) in OPEN
        and due is not None
        and (now or datetime.now(UTC)) > due
    )


def state(holder: Row, *, now: datetime | None = None) -> str:
    status = str(holder.get("ticket_status"))
    if status == Ticket.PENDING:
        return "not_confirmed" if holder.get("confirmed_at") is None else "not_sent"
    if status == Ticket.ESCALATED:
        return "final_reminder"
    if status == Ticket.ISSUED:
        if overdue(holder, now=now):
            return "overdue"
        return "sent_back" if holder.get("sent_back_at") else "waiting"
    if status == Ticket.RETURNED:
        return "accepted" if holder.get("accepted_at") else "review"
    if status == Ticket.WITHDRAWN:
        return "withdrawn"
    return "no_answer"


def _move(
    move: str,
    label: str,
    *,
    primary: bool = False,
    reason: bool = False,
    emails: bool = False,
    date: bool = False,
) -> Row:
    return {
        "move": move,
        "label": label,
        "primary": primary,
        "reason_required": reason,
        "sends_email": emails,
        "needs_date": date,
    }


def moves(holder: Row, *, request_status: str, now: datetime | None = None) -> list[Row]:
    """What the office may do with this holder now, the main move first."""
    if request_status not in WORKING:
        return []
    at = state(holder, now=now)
    console = holder.get("channel") == "portal"
    if at == "not_confirmed":
        return [
            _move("confirm", "Confirm who answers", primary=True),
            _move("remove", "Remove"),
        ]
    if at == "not_sent":
        return [_move("remove", "Remove")]
    if at in ("waiting", "sent_back", "overdue", "final_reminder"):
        out: list[Row] = []
        if at == "overdue":
            out.append(_move("final_reminder", "Send final reminder", primary=True, emails=True))
        out.append(
            _move(
                "record_answer",
                "Record their answer for them" if console else "Record their answer",
                primary=at != "overdue" and not console,
            )
        )
        out.append(_move("message", "Write to them", emails=True))
        out.append(_move("remind", "Send a reminder", emails=True))
        if not console:
            out.append(_move("log_contact", "Note a call or email"))
        out.append(_move("reassign", "Send to someone else", emails=True))
        out.append(_move("withdraw", "Withdraw", reason=True, emails=True))
        return out
    if at == "review":
        return [
            _move("accept", "Accept the answer", primary=True, emails=console),
            _move("send_back", "Send back", reason=True, emails=True, date=True),
            _move("message", "Write to them", emails=True),
        ]
    if at == "accepted":
        return [_move("send_back", "Send back", reason=True, emails=True, date=True)]
    if at == "withdrawn":
        return [_move("reopen", "Reopen", emails=True, date=True)]
    return []


#: The same states as the holder reads them, in My tasks.
HOLDER_STATES: Final[dict[str, str]] = {
    "not_confirmed": "Not sent yet",
    "not_sent": "Not sent yet",
    "waiting": "To answer",
    "sent_back": "Sent back to you",
    "overdue": "Overdue",
    "final_reminder": "Overdue - final reminder",
    "review": "Answered - with the Privacy Office",
    "accepted": "Accepted",
    "withdrawn": "Withdrawn",
    "no_answer": "Closed without your answer",
}


def holder_view(holder: Row, *, now: datetime | None = None) -> Row:
    at = state(holder, now=now)
    return {"state": at, "state_label": HOLDER_STATES[at], "overdue": overdue(holder, now=now)}


def view(holder: Row, *, request_status: str, now: datetime | None = None) -> Row:
    """The holder as the console shows it: state, overdue, moves."""
    at = state(holder, now=now)
    return {
        "state": at,
        "state_label": STATES[at],
        "overdue": overdue(holder, now=now),
        "moves": moves(holder, request_status=request_status, now=now),
    }
