"""Deferred side effects run after the unit of work, and not after a failure."""

from __future__ import annotations

import pytest

from cmp.core import after_commit


class TestUnitOfWork:
    def test_hooks_run_after_the_block_in_order(self) -> None:
        ran: list[str] = []
        with after_commit.unit_of_work():
            assert after_commit.defer(lambda: ran.append("first"))
            assert after_commit.defer(lambda: ran.append("second"))
            assert ran == [], "nothing runs while the transaction is still open"
        assert ran == ["first", "second"]

    def test_hooks_are_dropped_when_the_block_raises(self) -> None:
        ran: list[str] = []
        with pytest.raises(RuntimeError), after_commit.unit_of_work():
            after_commit.defer(lambda: ran.append("never"))
            raise RuntimeError("rolled back")
        assert ran == []

    def test_a_nested_unit_waits_for_the_outer_commit(self) -> None:
        ran: list[str] = []
        with after_commit.unit_of_work():
            with after_commit.unit_of_work():
                after_commit.defer(lambda: ran.append("inner"))
            assert ran == [], "the inner block committed nothing on its own"
            after_commit.defer(lambda: ran.append("outer"))
        assert ran == ["inner", "outer"]

    def test_outside_a_unit_defer_declines(self) -> None:
        assert not after_commit.in_unit_of_work()
        assert after_commit.defer(lambda: None) is False

    def test_one_failing_hook_does_not_stop_the_rest(self) -> None:
        ran: list[str] = []

        def boom() -> None:
            raise ValueError("broker down")

        with after_commit.unit_of_work():
            after_commit.defer(boom)
            after_commit.defer(lambda: ran.append("still runs"))
        assert ran == ["still runs"]
