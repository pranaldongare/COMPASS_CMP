"""What the office is shown of a report's mail, address by address (0064).

One line per address a version was sent to, whichever row of the list it went
under. Taken off is by address, and an address added for that report alone is
never taken off. A line never queued reads held while the report waits for a
yes, and unsent once it no longer does.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from cmp.domain.breach.reports import _by_address, _counts, _mail, _owed

NOW = datetime.now(UTC)
STALE = NOW - timedelta(minutes=15)


def _state(
    email_hash: str,
    status: str | None,
    *,
    recipient_id: int = 1,
    one_off: bool = False,
    mandatory: bool = False,
    recorded_at: datetime | None = NOW,
    attempt: int | None = 1,
) -> dict[str, Any]:
    queued = status is not None
    return {
        "report_id": 7,
        "recipient_id": recipient_id,
        "recipient_uuid": f"uuid-{recipient_id}",
        "full_name": None,
        "email": f"SE::{email_hash}",
        "email_hash": email_hash,
        "removed_at": None,
        "one_off": one_off,
        "mandatory": mandatory,
        "status": status,
        "attempt": attempt if queued else None,
        "last_attempt": attempt if queued else None,
        "detail": {} if queued else None,
        "recorded_at": recorded_at if queued else None,
    }


class TestByAddress:
    def test_an_address_under_two_rows_is_one_line_and_delivered_outranks(self) -> None:
        lines = _by_address(
            [
                _state("a", "delivered", recipient_id=1, recorded_at=NOW - timedelta(hours=1)),
                _state("a", "failed", recipient_id=2),
            ],
            {"a"},
            held=False,
        )
        assert [(s["recipient_id"], s["status"]) for s in lines] == [(1, "delivered")]

    def test_otherwise_the_latest_speaks_for_it(self) -> None:
        lines = _by_address(
            [
                _state("a", "failed", recipient_id=1, recorded_at=NOW - timedelta(hours=1)),
                _state("a", "queued", recipient_id=2),
            ],
            {"a"},
            held=False,
        )
        assert [(s["recipient_id"], s["status"]) for s in lines] == [(2, "queued")]

    def test_taken_off_is_by_address_and_never_for_one_report_alone(self) -> None:
        lines = _by_address(
            [_state("a", "failed"), _state("b", "failed", recipient_id=2, one_off=True)],
            set(),
            held=False,
        )
        assert [s["removed"] for s in lines] == [True, False]

    def test_a_line_never_queued_reads_held_or_unsent(self) -> None:
        never = [_state("a", None)]
        [held] = _by_address(never, {"a"}, held=True)
        [unsent] = _by_address(never, {"a"}, held=False)
        assert (held["status"], held["attempt"], held["last_attempt"]) == ("held", 0, 0)
        assert (held["detail"], held["recorded_at"]) == ({}, None)
        assert unsent["status"] == "unsent"

    def test_a_line_queued_outranks_one_never_queued_under_the_same_address(self) -> None:
        lines = _by_address(
            [_state("a", None, recipient_id=1), _state("a", "queued", recipient_id=2)],
            {"a"},
            held=False,
        )
        assert [(s["recipient_id"], s["status"]) for s in lines] == [(2, "queued")]


class TestCounts:
    def test_taken_off_counts_only_if_it_got_there(self) -> None:
        lines = _by_address(
            [
                _state("a", "delivered", recipient_id=1),
                _state("b", "failed", recipient_id=2),
                _state("c", None, recipient_id=3),
            ],
            set(),
            held=False,
        )
        assert _counts(lines) == {"delivered": 1, "queued": 0, "failed": 0, "unsent": 0, "held": 0}

    def test_held_and_unsent_are_counted(self) -> None:
        never = [_state("a", None, recipient_id=1), _state("b", None, recipient_id=2)]
        assert _counts(_by_address(never, {"a", "b"}, held=True))["held"] == 2
        assert _counts(_by_address(never, {"a", "b"}, held=False))["unsent"] == 2


class TestOwed:
    def test_failed_unsent_and_lost_are_owed(self) -> None:
        lines = _by_address(
            [
                _state("a", "failed", recipient_id=1),
                _state("b", None, recipient_id=2),
                _state("c", "queued", recipient_id=3, recorded_at=STALE - timedelta(minutes=1)),
                _state("d", "queued", recipient_id=4),
                _state("e", "delivered", recipient_id=5),
            ],
            {"a", "b", "c", "d", "e"},
            held=False,
        )
        assert [_owed(s, STALE) for s in lines] == [True, True, True, False, False]

    def test_nothing_taken_off_is_owed(self) -> None:
        lines = _by_address(
            [
                _state("a", "failed", recipient_id=1),
                _state("b", None, recipient_id=2),
                _state("c", "queued", recipient_id=3, recorded_at=STALE - timedelta(minutes=1)),
            ],
            set(),
            held=False,
        )
        assert [_owed(s, STALE) for s in lines] == [False, False, False]

    def test_held_is_not_owed(self) -> None:
        [line] = _by_address([_state("a", None)], {"a"}, held=True)
        assert not _owed(line, STALE)


class TestMail:
    def test_retryable_is_none_when_the_press_would_be_refused(self) -> None:
        states = [_state("a", "failed"), _state("b", None, recipient_id=2)]
        assert _mail(states, {"a", "b"}, sendable=True, held=False)["retryable"] == 2
        assert _mail(states, {"a", "b"}, sendable=False, held=False)["retryable"] == 0

    def test_only_a_reason_the_yes_records_is_served(self) -> None:
        """Why the yes withheld a version, as the trail named it; anything
        else, and nothing, is served as no reason."""
        states = [_state("a", None)]
        for why in ("cert_in_set_aside", "nobody_on_the_list"):
            assert (
                _mail(states, {"a"}, sendable=False, held=False, withheld_because=why)[
                    "withheld_because"
                ]
                == why
            )
        for why in (None, "", "chair@example.org"):
            assert (
                _mail(states, {"a"}, sendable=False, held=False, withheld_because=why)[
                    "withheld_because"
                ]
                is None
            )

    def test_each_address_says_what_it_was_chosen_as(self) -> None:
        mail = _mail(
            [
                _state("a", None, mandatory=True),
                _state("b", None, recipient_id=2, one_off=True),
            ],
            {"a"},
            sendable=False,
            held=True,
        )
        assert set(mail) == {
            "delivered",
            "queued",
            "failed",
            "unsent",
            "held",
            "stale",
            "retryable",
            "withheld_because",
            "recipients",
        }
        assert mail["withheld_because"] is None
        [listed, alone] = mail["recipients"]
        assert set(listed) == {
            "recipient_uuid",
            "full_name",
            "email",
            "status",
            "attempt",
            "error",
            "recorded_at",
            "removed",
            "mandatory",
            "added_for_this_send",
        }
        assert (listed["mandatory"], listed["added_for_this_send"]) == (True, False)
        assert (alone["mandatory"], alone["added_for_this_send"]) == (False, True)
        assert (listed["status"], listed["attempt"], listed["recorded_at"]) == ("held", 0, None)
        assert mail["held"] == 2
