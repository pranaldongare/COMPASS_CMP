"""Withdrawing one purpose is not withdrawing the consent.

A withdrawal writes a new artefact marked `is_withdrawal` - that records the
act, and it is right. But every place that turned the record into a status read
the flag alone, so a person who withdrew one of two purposes was shown, counted
and exported as "withdrawn": the purpose she still agrees to vanished from the
agent's list, and her portal hid the control to withdraw it. Withdrawn means a
withdrawal left nothing granted; anything with some granted and some not is
partial, and the rest can still be withdrawn.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.pagination import PageRequest
from cmp.core.security import content_hash, new_token, token_fingerprint
from cmp.db.repositories import consent as consent_repo
from cmp.db.repositories import exchange as exchange_repo
from cmp.db.repositories import projects as project_repo
from cmp.domain.consent import service as consent_service
from cmp.domain.exchange import service as exchange_service

pytestmark = pytest.mark.integration


async def _two_purpose_consent(
    conn: Any, seeded: dict[str, Any]
) -> tuple[dict[str, Any], str, str]:
    """Her consent to both purposes of a notice. Returns it and the two purpose uuids."""
    dpo = seeded["users"]["dpo"]["id"]
    second = await (
        await conn.execute(
            """INSERT INTO purpose (purpose_code, name, description, uses, lawful_basis,
                                    data_categories, retention_period, retention_basis,
                                    erasure_trigger, status, created_by)
               VALUES ('P-TEST-2', 'Second purpose', 'd', 'u', 'consent_s6', ARRAY['name'],
                       interval '1 year', 'business_policy', 'withdrawal', 'active', %s)
               RETURNING purpose_id, purpose_uuid""",
            (dpo,),
        )
    ).fetchone()
    notice_id = (
        await (
            await conn.execute(
                """INSERT INTO notice (notice_code, project_id, version, withdraw_url,
                                       exercise_rights_url, board_complaint_url, dpo_contact)
                   VALUES ('N-TEST-TWO', %s, 1, 'https://x/w', 'https://x/r',
                           'https://dpb.gov.in', 'dpo@test.local')
                   RETURNING notice_id""",
                (seeded["project"]["project_id"],),
            )
        ).fetchone()
    )["notice_id"]
    text = "A notice with two purposes."
    await conn.execute(
        """INSERT INTO notice_language (notice_id, language_code, rendered_text,
                                        content_hash, created_by, approved_by, approved_at)
           VALUES (%s, 'english', %s, %s, %s, %s, now())""",
        (notice_id, text, content_hash(text), dpo, dpo),
    )
    for purpose_id in (seeded["purpose"]["purpose_id"], second["purpose_id"]):
        await conn.execute(
            "INSERT INTO notice_purpose (notice_id, purpose_id) VALUES (%s, %s)",
            (notice_id, purpose_id),
        )
    await conn.execute(
        """UPDATE notice SET status = 'published', recipients_text = 'Test Site',
                  approved_by = %s, published_at = now() WHERE notice_id = %s""",
        (dpo, notice_id),
    )
    raw = new_token()
    await conn.execute(
        """INSERT INTO consent_link (notice_id, site_id, token, expires_at, created_by)
           VALUES (%s, %s, %s, now() + interval '1 day', %s)""",
        (notice_id, seeded["site"]["site_id"], token_fingerprint(raw)[:64], dpo),
    )
    await consent_service.serve_notice(
        conn, token=raw, language_code="english", user_id=seeded["subject"]["id"]
    )
    first, other = str(seeded["purpose"]["purpose_uuid"]), str(second["purpose_uuid"])
    artefact = await consent_service.capture(
        conn,
        token=raw,
        user_id=seeded["subject"]["id"],
        language_code="english",
        grants={first: True, other: True},
        action_type="checkbox_click",
        ip_address="127.0.0.1",
    )
    return artefact, first, other


async def _withdraw(
    conn: Any, seeded: dict[str, Any], consent_uuid: str, purposes: list[str]
) -> Any:
    return await consent_service.withdraw(
        conn,
        consent_uuid=consent_uuid,
        user_id=seeded["subject"]["id"],
        purpose_uuids=purposes,
        withdraw_all=False,
        ip_address="127.0.0.1",
    )


async def _status_in_register(conn: Any, seeded: dict[str, Any], consent_uuid: str) -> str:
    rows, _, _ = await consent_repo.list_for_project(
        conn,
        PageRequest(limit=200, cursor=None, sort_field="created_at", descending=True),
        project_id=seeded["project"]["project_id"],
    )
    [row] = [r for r in rows if str(r["consent_uuid"]) == consent_uuid]
    return str(row["consent_status"])


async def test_withdrawing_one_of_two_purposes_leaves_the_consent_partial(
    conn: Any, seeded: dict[str, Any]
) -> None:
    artefact, first, _other = await _two_purpose_consent(conn, seeded)
    withdrawn = await _withdraw(conn, seeded, str(artefact["consent_uuid"]), [first])
    now_uuid = str(withdrawn["consent_uuid"])

    assert await _status_in_register(conn, seeded, now_uuid) == "partial"

    counts = await project_repo.consent_counts(conn, seeded["project"]["project_id"])
    assert counts["withdrawn"] == 0 and counts["partial"] >= 1

    rows = await exchange_repo.project_consents(
        conn,
        project_id=seeded["project"]["project_id"],
        role="dpo",
        user_id=seeded["users"]["dpo"]["id"],
    )
    [row] = [r for r in rows if str(r["consent_uuid"]) == now_uuid]
    assert exchange_service._consent_status(row) == "partial"


async def test_the_rest_can_be_withdrawn_afterwards_and_then_it_is_withdrawn(
    conn: Any, seeded: dict[str, Any]
) -> None:
    artefact, first, other = await _two_purpose_consent(conn, seeded)
    once = await _withdraw(conn, seeded, str(artefact["consent_uuid"]), [first])
    twice = await _withdraw(conn, seeded, str(once["consent_uuid"]), [other])

    assert await _status_in_register(conn, seeded, str(twice["consent_uuid"])) == "withdrawn"
    counts = await project_repo.consent_counts(conn, seeded["project"]["project_id"])
    assert counts["withdrawn"] >= 1
