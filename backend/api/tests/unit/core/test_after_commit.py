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


class TestUndoOnRollback:
    """Review ARCH-10: work outside the database that a rollback cannot reach."""

    def test_undo_runs_in_reverse_only_when_the_block_raises(self) -> None:
        ran: list[str] = []
        with pytest.raises(RuntimeError), after_commit.unit_of_work():
            after_commit.on_rollback(lambda: ran.append("first"))
            after_commit.on_rollback(lambda: ran.append("second"))
            raise RuntimeError("rolled back")
        assert ran == ["second", "first"]

    def test_undo_is_forgotten_when_the_block_commits(self) -> None:
        ran: list[str] = []
        with after_commit.unit_of_work():
            after_commit.on_rollback(lambda: ran.append("undo"))
        assert ran == []

    def test_outside_a_unit_on_rollback_declines(self) -> None:
        assert after_commit.on_rollback(lambda: None) is False


class TestAFileWrittenInARolledBackTransaction:
    def test_is_removed_and_one_committed_is_kept(self, tmp_path: object) -> None:
        from pathlib import Path

        from cmp.core.security import file_hash
        from cmp.infrastructure.storage.local import LocalFileStorage

        store = LocalFileStorage(str(tmp_path))
        with pytest.raises(RuntimeError), after_commit.unit_of_work():
            lost = store.save(b"response package", subdir="rights", suggested_name="r.zip")
            raise RuntimeError("the row naming it was not written")
        assert not (Path(str(tmp_path)) / lost).exists()

        with after_commit.unit_of_work():
            kept = store.save(b"response package", subdir="rights", suggested_name="r.zip")
        assert file_hash(store.read(kept)) == file_hash(b"response package")
