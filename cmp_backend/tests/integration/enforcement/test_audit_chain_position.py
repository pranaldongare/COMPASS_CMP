"""The audit chain draws a row's position inside the lock.

Migration 0002 serialised chain construction but let the column default draw
the row's id before the trigger waited for the lock. Two inserts granted the
lock in the other order from the one they formed their rows in then chained in
one order and carried ids in the other, and `cmp_audit_verify()`, which walks
by id, reported a break that was not tampering. Migration 0014 moves the draw
inside the lock.

This file pins the observable half of that. While one transaction holds the
lock, a second insert waiting for it has not moved the sequence; once it holds
the lock it takes the next position, and reads its predecessor only then.
Both transactions here are the test's own, and both end in a rollback.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import psycopg
import pytest
from psycopg.rows import dict_row

from cmp.core.config import settings

pytestmark = pytest.mark.integration

INSERT = """INSERT INTO audit_log (event_type, entity_type, entity_id)
            VALUES ('project.created', 'project', 1)
            RETURNING log_id, detail_json ->> '_prev' AS prev"""

LAST_COMMITTED_HASH = (
    "SELECT detail_json ->> '_hash' AS h FROM audit_log ORDER BY log_id DESC LIMIT 1"
)


def _connect() -> psycopg.Connection[Any]:
    # Not from the pool: the test needs one transaction that holds the lock and
    # one that waits for it, and it ends both itself. The lock timeout is a
    # safety net for a broken trigger, not part of what is being tested.
    return psycopg.connect(settings.dsn, row_factory=dict_row, options="-c lock_timeout=20000")


def _wait_until_blocked(conn: psycopg.Connection[Any], pid: int, *, seconds: float = 10.0) -> None:
    """Return once backend `pid` is waiting on an advisory lock."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        row = conn.execute(
            "SELECT wait_event_type, wait_event FROM pg_stat_activity WHERE pid = %s", (pid,)
        ).fetchone()
        if row and row["wait_event_type"] == "Lock" and row["wait_event"] == "advisory":
            return
        time.sleep(0.02)
    raise AssertionError("the second insert never waited for the chain lock")


class TestChainPosition:
    def test_the_column_has_no_default(self) -> None:
        with _connect() as conn:
            row = conn.execute(
                """SELECT column_default FROM information_schema.columns
                   WHERE table_name = 'audit_log' AND column_name = 'log_id'"""
            ).fetchone()
        assert row is not None
        assert row["column_default"] is None, "the position must come from the trigger, in the lock"

    def test_a_waiting_insert_takes_its_position_only_once_it_holds_the_lock(self) -> None:
        holder = _connect()
        waiter = _connect()
        got: dict[str, Any] = {}
        pid_known = threading.Event()
        inserted = threading.Event()
        release = threading.Event()

        def wait_then_insert() -> None:
            try:
                with waiter.transaction(force_rollback=True):
                    pid = waiter.execute("SELECT pg_backend_pid() AS pid").fetchone()
                    got["pid"] = pid["pid"] if pid else None
                    pid_known.set()
                    got["row"] = waiter.execute(INSERT).fetchone()  # blocks on the lock
                    inserted.set()
                    release.wait(timeout=20)
            except psycopg.Error as exc:
                got["error"] = exc
                pid_known.set()
                inserted.set()

        thread = threading.Thread(target=wait_then_insert, name="audit-chain-waiter")
        try:
            # The holder inserts and keeps its transaction open: it owns the lock.
            first = holder.execute(INSERT).fetchone()
            assert first is not None
            position = first["log_id"]

            thread.start()
            assert pid_known.wait(timeout=10), "the waiter never connected"
            assert "error" not in got, got.get("error")
            _wait_until_blocked(holder, got["pid"])

            # The waiter is blocked, and has drawn nothing: the sequence still
            # stands at the holder's row. Under 0002 it would already have moved.
            seq = holder.execute("SELECT last_value FROM audit_log_log_id_seq").fetchone()
            assert seq is not None
            assert seq["last_value"] == position, "a waiting insert drew a position before the lock"

            # The holder lets go - by rolling back, so its row never existed.
            holder.rollback()
            assert inserted.wait(timeout=20), "the waiter never got the lock"
            assert "error" not in got, got.get("error")
            second = got["row"]

            # Drawn once it held the lock: the next position after the one it
            # waited behind. And the predecessor was read then too - the row
            # that was rolled back is not it; the last committed row is.
            assert second["log_id"] == position + 1
            last = holder.execute(LAST_COMMITTED_HASH).fetchone()
            holder.rollback()
            assert second["prev"] == (last["h"] if last else None)
        finally:
            release.set()
            thread.join(timeout=20)
            holder.close()
            waiter.close()
        assert not thread.is_alive()
