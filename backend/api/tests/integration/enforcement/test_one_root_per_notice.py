"""One root consent artefact per person and notice, by the database's own word.

`uq_artefact_supersedes_once` stops a chain forking. Nothing stopped two
chains starting: two artefacts with no predecessor for the same pair, which
`v_current_consent` would both report as live. Migration 0023 adds the index;
this writes raw SQL to prove it holds without the service.
"""

from __future__ import annotations

from typing import Any

import psycopg
import pytest

pytestmark = pytest.mark.integration

INSERT_ROOT = """
INSERT INTO consent_artefact
    (auth_user_id, notice_id, notice_language_id, notice_content_hash,
     link_id, served_at, affirmative_action_at, action_type)
VALUES (%s, %s, %s, %s, %s, now() - interval '1 minute', now(), 'checkbox_click')
RETURNING consent_id
"""


async def _ids(conn: Any, seeded: dict[str, Any]) -> tuple[int, str, int]:
    lang = await (
        await conn.execute(
            "SELECT notice_language_id, content_hash FROM notice_language WHERE notice_id = %s",
            (seeded["notice"]["notice_id"],),
        )
    ).fetchone()
    link = await (
        await conn.execute(
            "SELECT link_id FROM consent_link WHERE notice_id = %s LIMIT 1",
            (seeded["notice"]["notice_id"],),
        )
    ).fetchone()
    assert lang and link
    return lang["notice_language_id"], lang["content_hash"], link["link_id"]


class TestOneRoot:
    async def test_a_second_root_for_the_same_pair_is_refused(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        language_id, digest, link_id = await _ids(conn, seeded)
        params = (
            seeded["subject"]["id"],
            seeded["notice"]["notice_id"],
            language_id,
            digest,
            link_id,
        )

        first = await (await conn.execute(INSERT_ROOT, params)).fetchone()
        assert first is not None

        with pytest.raises(psycopg.errors.UniqueViolation):
            await conn.execute(INSERT_ROOT, params)

    async def test_a_successor_is_still_allowed(self, conn: Any, seeded: dict[str, Any]) -> None:
        language_id, digest, link_id = await _ids(conn, seeded)
        params = (
            seeded["subject"]["id"],
            seeded["notice"]["notice_id"],
            language_id,
            digest,
            link_id,
        )
        first = await (await conn.execute(INSERT_ROOT, params)).fetchone()
        assert first is not None

        successor = await (
            await conn.execute(
                """INSERT INTO consent_artefact
                       (auth_user_id, notice_id, notice_language_id, notice_content_hash,
                        link_id, served_at, affirmative_action_at, action_type,
                        supersedes_consent_id, is_withdrawal)
                   VALUES (%s, %s, %s, %s, %s, now(), now(), 'button_press', %s, true)
                   RETURNING consent_id""",
                (*params, first["consent_id"]),
            )
        ).fetchone()
        assert successor is not None
