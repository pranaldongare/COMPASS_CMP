"""The server's word on a rights ticket (2026-10-08): its state in plain words,
whether it is overdue - one rule, the due moment has passed - and what may be
done next, the main move first. The console draws from this alone."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from cmp.domain.rights import tickets

NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)


def holder(**over: Any) -> dict[str, Any]:
    return {
        "ticket_status": "issued",
        "confirmed_at": NOW,
        "due_at": NOW + timedelta(days=3),
        "sent_back_at": None,
        "accepted_at": None,
        "channel": "email",
        **over,
    }


def moves(h: dict[str, Any], status: str = "awaiting_holders") -> list[str]:
    return [m["move"] for m in tickets.moves(h, request_status=status, now=NOW)]


def test_each_state_reads_in_plain_words() -> None:
    cases = {
        "not_confirmed": holder(ticket_status="pending", confirmed_at=None),
        "not_sent": holder(ticket_status="pending"),
        "waiting": holder(),
        "sent_back": holder(sent_back_at=NOW),
        "overdue": holder(due_at=NOW - timedelta(minutes=1)),
        "final_reminder": holder(ticket_status="escalated"),
        "review": holder(ticket_status="returned"),
        "accepted": holder(ticket_status="returned", accepted_at=NOW),
        "withdrawn": holder(ticket_status="withdrawn"),
        "no_answer": holder(ticket_status="unreturned"),
    }
    for expected, h in cases.items():
        assert tickets.state(h, now=NOW) == expected, expected
        assert tickets.STATES[expected]


def test_overdue_is_after_the_due_moment_and_only_while_open() -> None:
    assert not tickets.overdue(holder(due_at=NOW), now=NOW)
    assert tickets.overdue(holder(due_at=NOW - timedelta(seconds=1)), now=NOW)
    assert not tickets.overdue(
        holder(ticket_status="returned", due_at=NOW - timedelta(days=1)), now=NOW
    )


def test_a_final_reminder_only_once_overdue_and_then_it_leads() -> None:
    assert "final_reminder" not in moves(holder())
    late = tickets.moves(
        holder(due_at=NOW - timedelta(days=1)), request_status="awaiting_holders", now=NOW
    )
    assert late[0]["move"] == "final_reminder" and late[0]["primary"] and late[0]["sends_email"]
    assert "final_reminder" not in moves(holder(ticket_status="escalated"))


def test_an_answer_is_reviewed_accepted_or_sent_back() -> None:
    review = tickets.moves(
        holder(ticket_status="returned"), request_status="awaiting_holders", now=NOW
    )
    assert [m["move"] for m in review][:2] == ["accept", "send_back"]
    assert review[0]["primary"] and review[1]["reason_required"] and review[1]["needs_date"]
    assert moves(holder(ticket_status="returned", accepted_at=NOW)) == ["send_back"]


def test_the_rest_of_the_path() -> None:
    assert moves(holder(ticket_status="pending", confirmed_at=None)) == ["confirm", "remove"]
    assert moves(holder(ticket_status="pending")) == ["remove"]
    assert moves(holder(ticket_status="withdrawn")) == ["reopen"]
    assert moves(holder(ticket_status="unreturned")) == []
    # In the console, the team answers; there is no mail to note.
    console = moves(holder(channel="portal"))
    assert "log_contact" not in console and "record_answer" in console
    # A closed request takes no moves at all.
    assert moves(holder(), status="closed") == []
