"""Refusing a whole notice is always possible (review 2026-10-01, UX-1).

A mandatory purpose cannot be refused *on its own*: accepting the rest while
saying no to the purpose the project depends on is not a choice the notice
offers. But saying no to everything is - the portal tells her to "decline the
whole notice" when she does not agree to a mandatory purpose, and the server
used to refuse exactly that, because it read every No as refusing the
mandatory one. A whole refusal is a declined artefact like any other.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.errors import ValidationFailed
from cmp.core.security import content_hash, new_token, token_fingerprint
from cmp.domain.consent import service as consent_service

pytestmark = pytest.mark.integration


async def _mandatory_notice(conn: Any, seeded: dict[str, Any]) -> tuple[str, str, str]:
    """A published notice with one mandatory purpose and one optional one, and
    a live link to it. Returns the raw token and the two purpose uuids."""
    dpo = seeded["users"]["dpo"]["id"]
    optional = await (
        await conn.execute(
            """INSERT INTO purpose (purpose_code, name, description, uses, lawful_basis,
                                    data_categories, retention_period, retention_basis,
                                    erasure_trigger, status, created_by)
               VALUES ('P-OPT-UX1', 'Optional purpose', 'd', 'u', 'consent_s6', ARRAY['name'],
                       interval '1 year', 'business_policy', 'withdrawal', 'active', %s)
               RETURNING purpose_id, purpose_uuid""",
            (dpo,),
        )
    ).fetchone()
    notice = await (
        await conn.execute(
            """INSERT INTO notice (notice_code, project_id, version, withdraw_url,
                                   exercise_rights_url, board_complaint_url, dpo_contact)
               VALUES ('N-UX1', %s, 1, 'https://x/w', 'https://x/r', 'https://dpb.gov.in',
                       'dpo@test.local')
               RETURNING notice_id""",
            (seeded["project"]["project_id"],),
        )
    ).fetchone()
    text = "A notice with a purpose the project depends on."
    await conn.execute(
        """INSERT INTO notice_language (notice_id, language_code, rendered_text, content_hash,
                                        created_by, approved_by, approved_at)
           VALUES (%s, 'english', %s, %s, %s, %s, now())""",
        (notice["notice_id"], text, content_hash(text), dpo, dpo),
    )
    await conn.execute(
        """INSERT INTO notice_purpose (notice_id, purpose_id, display_order, is_mandatory)
           VALUES (%s, %s, 1, true), (%s, %s, 2, false)""",
        (
            notice["notice_id"],
            seeded["purpose"]["purpose_id"],
            notice["notice_id"],
            optional["purpose_id"],
        ),
    )
    # 0033: one published notice per project - the seeded one steps aside.
    await conn.execute(
        "UPDATE notice SET status = 'superseded' WHERE notice_id = %s",
        (seeded["notice"]["notice_id"],),
    )
    await conn.execute(
        """UPDATE notice SET status = 'published', recipients_text = 'Test Site',
                  approved_by = %s, published_at = now() WHERE notice_id = %s""",
        (dpo, notice["notice_id"]),
    )
    raw = new_token()
    await conn.execute(
        """INSERT INTO consent_link (notice_id, site_id, token, expires_at, created_by)
           VALUES (%s, %s, %s, now() + interval '1 day', %s)""",
        (
            notice["notice_id"],
            seeded["site"]["site_id"],
            token_fingerprint(raw)[:64],
            seeded["users"]["dco"]["id"],
        ),
    )
    return raw, str(seeded["purpose"]["purpose_uuid"]), str(optional["purpose_uuid"])


async def _answer(conn: Any, seeded: dict[str, Any], raw: str, grants: dict[str, bool]) -> Any:
    await consent_service.serve_notice(
        conn, token=raw, language_code="english", user_id=seeded["subject"]["id"]
    )
    return await consent_service.capture(
        conn,
        token=raw,
        user_id=seeded["subject"]["id"],
        language_code="english",
        grants=grants,
        action_type="checkbox_click",
        ip_address="127.0.0.1",
    )


async def test_refusing_everything_records_a_declined_consent(
    conn: Any, seeded: dict[str, Any]
) -> None:
    raw, mandatory, optional = await _mandatory_notice(conn, seeded)
    made = await _answer(conn, seeded, raw, {mandatory: False, optional: False})
    grants = await (
        await conn.execute(
            "SELECT granted FROM consent_purpose_grant WHERE consent_id = %s",
            (made["consent_id"],),
        )
    ).fetchall()
    assert [g["granted"] for g in grants] == [False, False], "a refusal on the record"


async def test_refusing_only_the_mandatory_purpose_is_still_refused(
    conn: Any, seeded: dict[str, Any]
) -> None:
    raw, mandatory, optional = await _mandatory_notice(conn, seeded)
    with pytest.raises(ValidationFailed, match="cannot be refused"):
        await _answer(conn, seeded, raw, {mandatory: False, optional: True})


async def test_accepting_everything_still_works(conn: Any, seeded: dict[str, Any]) -> None:
    raw, mandatory, optional = await _mandatory_notice(conn, seeded)
    made = await _answer(conn, seeded, raw, {mandatory: True, optional: False})
    assert made["consent_id"]
