"""A consent is recorded against a serving the server itself witnessed.

The capture route used to accept `served_at` from the request body, checked
only that it was recent and not in the future. The September 2026 review
called capture with an invented timestamp and never rendered the notice; the
artefact looked like any other. The serving moment now comes from the
server's own record, written when the notice was rendered to this person
through this link in this language, and a capture with no such record is
refused.

Also here: two first captures for the same person and notice serialise on a
per-pair lock, so the second sees the first and supersedes it rather than
writing a second root.
"""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any

import psycopg
import pytest
from psycopg.rows import dict_row

from cmp.core.config import settings
from cmp.core.errors import ConsentDefective
from cmp.core.security import new_token, token_fingerprint
from cmp.domain.consent import service as consent_service

pytestmark = pytest.mark.integration


async def _link(conn: Any, seeded: dict[str, Any]) -> str:
    raw = new_token()
    await conn.execute(
        """INSERT INTO consent_link (notice_id, site_id, token, expires_at, created_by)
           VALUES (%s, %s, %s, now() + interval '1 day', %s)""",
        (
            seeded["notice"]["notice_id"],
            seeded["site"]["site_id"],
            token_fingerprint(raw)[:64],
            seeded["users"]["dco"]["id"],
        ),
    )
    return raw


async def _capture(conn: Any, seeded: dict[str, Any], token: str) -> dict[str, Any]:
    return await consent_service.capture(
        conn,
        token=token,
        user_id=seeded["subject"]["id"],
        language_code="english",
        grants={str(seeded["purpose"]["purpose_uuid"]): True},
        action_type="checkbox_click",
        ip_address="127.0.0.1",
    )


class TestServingIsTheServers:
    async def test_a_capture_with_no_serving_is_refused(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        token = await _link(conn, seeded)
        with pytest.raises(ConsentDefective) as exc:
            await _capture(conn, seeded, token)
        assert exc.value.code == "notice_not_served"

    async def test_the_artefact_carries_the_moment_the_server_served(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        token = await _link(conn, seeded)
        served = await consent_service.serve_notice(
            conn, token=token, language_code="english", user_id=seeded["subject"]["id"]
        )
        artefact = await _capture(conn, seeded, token)
        assert artefact["served_at"] == served["served_at"]
        assert artefact["served_at"] <= artefact["affirmative_action_at"]

    async def test_a_serving_to_somebody_else_does_not_count(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        token = await _link(conn, seeded)
        # Rendered to the DCO's account, not to the subject.
        await consent_service.serve_notice(
            conn, token=token, language_code="english", user_id=seeded["users"]["dco"]["id"]
        )
        with pytest.raises(ConsentDefective) as exc:
            await _capture(conn, seeded, token)
        assert exc.value.code == "notice_not_served"

    async def test_an_anonymous_render_does_not_count(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        token = await _link(conn, seeded)
        await consent_service.serve_notice(conn, token=token, language_code="english", user_id=None)
        with pytest.raises(ConsentDefective):
            await _capture(conn, seeded, token)


def _sync_connect() -> psycopg.Connection[Any]:
    return psycopg.connect(settings.dsn, row_factory=dict_row, options="-c lock_timeout=20000")


def _wait_until_blocked(
    holder: psycopg.Connection[Any], pid: int, *, seconds: float = 10.0
) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        row = holder.execute(
            "SELECT wait_event_type, wait_event FROM pg_stat_activity WHERE pid = %s", (pid,)
        ).fetchone()
        if row and row["wait_event_type"] == "Lock" and row["wait_event"] == "advisory":
            return
        time.sleep(0.02)
    raise AssertionError("capture never waited for the per-(person, notice) lock")


class TestFirstCapturesSerialise:
    async def test_capture_waits_for_the_pair_lock(self, conn: Any, seeded: dict[str, Any]) -> None:
        """Another transaction holds the (person, notice) lock; capture waits for it.

        Both transactions end in a rollback. The holder is a plain connection
        on its own thread, standing in for a concurrent first capture.
        """
        token = await _link(conn, seeded)
        await consent_service.serve_notice(
            conn, token=token, language_code="english", user_id=seeded["subject"]["id"]
        )
        pid_row = await (await conn.execute("SELECT pg_backend_pid() AS pid")).fetchone()
        assert pid_row is not None
        user_id, notice_id = seeded["subject"]["id"], seeded["notice"]["notice_id"]

        holder = _sync_connect()
        held = threading.Event()
        release = threading.Event()

        def hold() -> None:
            with holder.transaction(force_rollback=True):
                holder.execute("SELECT pg_advisory_xact_lock(%s, %s)", (user_id, notice_id))
                held.set()
                release.wait(timeout=20)

        thread = threading.Thread(target=hold, name="consent-lock-holder")
        thread.start()
        try:
            assert held.wait(timeout=10)
            task = asyncio.create_task(_capture(conn, seeded, token))
            await asyncio.sleep(0.2)  # let capture reach the lock
            assert not task.done(), "capture must block while another first capture is in flight"

            watcher = _sync_connect()
            try:
                await asyncio.to_thread(_wait_until_blocked, watcher, pid_row["pid"])
            finally:
                watcher.close()

            release.set()
            artefact = await task
            assert artefact["consent_uuid"]
        finally:
            release.set()
            thread.join(timeout=20)
            holder.close()


class TestSecondDecision:
    async def test_a_second_decision_supersedes_the_first(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        """Re-consenting on the same notice is a supersession, not a fork or a 500.

        Before September 2026 this path raised: the earlier artefact's uuid went
        into the audit detail as a UUID object, and nothing had ever recorded a
        second decision through the service to notice.
        """
        token = await _link(conn, seeded)
        await consent_service.serve_notice(
            conn, token=token, language_code="english", user_id=seeded["subject"]["id"]
        )
        first = await _capture(conn, seeded, token)
        second = await _capture(conn, seeded, token)
        assert second["consent_uuid"] != first["consent_uuid"]
        row = await (
            await conn.execute(
                "SELECT supersedes_consent_id FROM consent_artefact WHERE consent_id = %s",
                (second["consent_id"],),
            )
        ).fetchone()
        assert row is not None and row["supersedes_consent_id"] == first["consent_id"]
