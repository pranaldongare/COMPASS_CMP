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
    assert moves(holder(ticket_status="pending")) == ["edit_responder", "remove"]
    assert moves(holder(ticket_status="withdrawn")) == ["reopen"]
    assert moves(holder(ticket_status="unreturned")) == []
    # In the console, the team answers; there is no mail to note.
    console = moves(holder(channel="portal"))
    assert "log_contact" not in console and "record_answer" in console
    # A closed request takes no moves at all.
    assert moves(holder(), status="closed") == []


def test_a_holder_answering_by_its_link_answers_itself() -> None:
    """Outside holders answer on the portal (0049): recording their answer for
    them stays possible, but it is not the main move, as it is for one the
    office reaches only by email."""
    by_email = tickets.moves(holder(), request_status="awaiting_holders", now=NOW)
    by_link = tickets.moves(holder(link_issued_at=NOW), request_status="awaiting_holders", now=NOW)
    assert [m["move"] for m in by_email if m["primary"]] == ["record_answer"]
    assert [m["move"] for m in by_link if m["primary"]] == []
    [record] = [m for m in by_link if m["move"] == "record_answer"]
    assert record["label"] == "Record their answer for them"


def test_a_mistyped_address_can_be_corrected_on_an_open_ticket() -> None:
    """2026-10-08: by email or on a temporary login, never a member of staff."""
    assert "correct_contact" in moves(holder())
    assert "correct_contact" in moves(holder(channel="portal", temporary_access="pending"))
    assert "correct_contact" not in moves(holder(channel="portal"))
    assert "correct_contact" not in moves(holder(ticket_status="returned"))


def test_a_holder_with_nobody_to_send_to_says_so() -> None:
    def has(**over: Any) -> bool:
        return bool(tickets.view(holder(**over), request_status="in_progress")["has_address"])

    assert not has(responder_contact=None, responder_user_id=None)
    assert has(responder_contact="SE::sealed")
    assert has(responder_user_id=7)


def test_the_date_can_be_changed_while_a_ticket_is_open_and_not_after() -> None:
    # 2026-11-12: as a breach ticket's can. It takes a date and a reason, and
    # the holder is written to, so it asks first.
    for open_ticket in (holder(), holder(ticket_status="escalated")):
        offered = tickets.moves(open_ticket, request_status="awaiting_holders", now=NOW)
        [move] = [m for m in offered if m["move"] == "change_date"]
        assert move["label"] == "Change the date" and not move["primary"]
        assert move["reason_required"] and move["needs_date"] and move["sends_email"]
    assert "change_date" not in moves(holder(ticket_status="returned"))
    assert "change_date" not in moves(holder(ticket_status="withdrawn"))
    assert "change_date" not in moves(holder(ticket_status="not_issued"))

    # The holder's side: only while it waits on them, on a request being worked on.
    waiting = holder(request_status="awaiting_holders")
    assert tickets.holder_view(waiting, now=NOW)["may_change_date"] is True
    answered = holder(ticket_status="returned", request_status="awaiting_holders")
    assert tickets.holder_view(answered, now=NOW)["may_change_date"] is False
    closed = holder(request_status="closed")
    assert tickets.holder_view(closed, now=NOW)["may_change_date"] is False


def test_the_sentence_a_date_change_leaves_and_the_reason_read_back_out_of_it() -> None:
    said = tickets.date_change_said("20 November 2026", "27 November 2026", "Audit: until Friday")
    assert said == (
        "Answer by changed from 20 November 2026 to 27 November 2026: Audit: until Friday"
    )
    # The reason is everything after the first colon - one of its own stays in it.
    assert tickets.date_change_reason(said) == "Audit: until Friday"
    assert tickets.date_change_reason("no date to 3 December 2026") == "no date to 3 December 2026"
