"""The dashboard counts each consent state on its own (UX review 2026-10-05).

The DPO's dashboard showed "Still standing" as every current record minus the
complete withdrawals - so a person who declined every purpose, and one who
agreed to some of them, were both counted as consent still standing. Each
current record now falls in exactly one state:

* all agreed - every purpose on the notice granted;
* partly agreed - some granted, some not;
* declined - none granted, and never withdrawn from;
* withdrawn - none granted now, after a withdrawal.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.security import content_hash
from cmp.db.repositories import dashboard as dashboard_repo
from cmp.db.sql import fetch_one
from tests.conftest import hashed

pytestmark = pytest.mark.integration

STATES = ("consents_full", "consents_partial", "consents_declined", "consents_withdrawn")


async def _two_purpose_notice(conn: Any, seeded: dict[str, Any]) -> dict[str, Any]:
    dpo = seeded["users"]["dpo"]["id"]
    second = await fetch_one(
        conn,
        """INSERT INTO purpose (purpose_code, name, description, uses, lawful_basis,
                                data_categories, retention_period, retention_basis,
                                erasure_trigger, status, created_by)
           VALUES ('P-STATES', 'Second purpose', 'd', 'u', 'consent_s6', ARRAY['name'],
                   interval '1 year', 'business_policy', 'withdrawal', 'active', %s)
           RETURNING purpose_id""",
        (dpo,),
    )
    # A project of its own: a project has one published notice at a time.
    project = await fetch_one(
        conn,
        """INSERT INTO project (project_name, description, created_by, dco_user_id,
                                project_status)
           VALUES ('States Project', 'Two purposes', %s, %s, 'approved')
           RETURNING project_id""",
        (seeded["users"]["rnd_user"]["id"], seeded["users"]["dco"]["id"]),
    )
    site = await fetch_one(
        conn,
        """INSERT INTO project_site (project_id, site_label, location, processor_id)
           VALUES (%s, 'States Site', 'Pune', %s) RETURNING site_id""",
        (project["project_id"], seeded["processors"]["external"]["processor_id"]),
    )
    notice = await fetch_one(
        conn,
        """INSERT INTO notice (notice_code, project_id, version, withdraw_url,
                               exercise_rights_url, board_complaint_url, dpo_contact)
           VALUES ('N-STATES', %s, 1, 'https://x/w', 'https://x/r', 'https://dpb.gov.in',
                   'dpo@test.local')
           RETURNING notice_id""",
        (project["project_id"],),
    )
    text = "Two purposes, chosen apart."
    language = await fetch_one(
        conn,
        """INSERT INTO notice_language (notice_id, language_code, rendered_text,
                                        content_hash, created_by, approved_by, approved_at)
           VALUES (%s, 'english', %s, %s, %s, %s, now())
           RETURNING notice_language_id, content_hash""",
        (notice["notice_id"], text, content_hash(text), dpo, dpo),
    )
    purposes = [seeded["purpose"]["purpose_id"], second["purpose_id"]]
    for purpose_id in purposes:
        await conn.execute(
            "INSERT INTO notice_purpose (notice_id, purpose_id) VALUES (%s, %s)",
            (notice["notice_id"], purpose_id),
        )
    await conn.execute(
        """UPDATE notice SET status = 'published', recipients_text = 'Test Site',
                  approved_by = %s, published_at = now()
            WHERE notice_id = %s""",
        (dpo, notice["notice_id"]),
    )
    link = await fetch_one(
        conn,
        """INSERT INTO consent_link (notice_id, site_id, token, expires_at, created_by)
           VALUES (%s, %s, 'states-token-000000000000000000000', now() + interval '1 day', %s)
           RETURNING link_id""",
        (notice["notice_id"], site["site_id"], seeded["users"]["dco"]["id"]),
    )
    return {**notice, **language, **link, "purposes": purposes}


async def _choice(
    conn: Any, notice: dict[str, Any], who: str, grants: list[bool], *, withdrawal: bool
) -> None:
    mobile = "+9190" + f"{abs(hash(who)) % 100000000:08d}"
    person = await fetch_one(
        conn,
        """INSERT INTO auth_user (full_name, mobile, mobile_hash, role, status, minor_until)
           VALUES (%s, %s, %s, 'data_subject', 'active', '2000-01-01') RETURNING id""",
        (who, mobile, hashed("mobile", mobile)),
    )
    artefact = await fetch_one(
        conn,
        """INSERT INTO consent_artefact
                  (auth_user_id, notice_id, notice_language_id, notice_content_hash,
                   link_id, served_at, affirmative_action_at, action_type, is_withdrawal)
           VALUES (%s, %s, %s, %s, %s, now(), now(), 'checkbox_click', %s)
           RETURNING consent_id""",
        (
            person["id"],
            notice["notice_id"],
            notice["notice_language_id"],
            notice["content_hash"],
            notice["link_id"],
            withdrawal,
        ),
    )
    for purpose_id, granted in zip(notice["purposes"], grants, strict=True):
        await conn.execute(
            """INSERT INTO consent_purpose_grant (consent_id, purpose_id, granted)
               VALUES (%s, %s, %s)""",
            (artefact["consent_id"], purpose_id, granted),
        )


async def test_each_current_record_is_in_exactly_one_state(
    conn: Any, seeded: dict[str, Any]
) -> None:
    before = await dashboard_repo.dpo_counts(conn)
    assert before is not None
    notice = await _two_purpose_notice(conn, seeded)

    await _choice(conn, notice, "states-full", [True, True], withdrawal=False)
    await _choice(conn, notice, "states-partial", [True, False], withdrawal=False)
    await _choice(conn, notice, "states-declined", [False, False], withdrawal=False)
    await _choice(conn, notice, "states-withdrawn", [False, False], withdrawal=True)

    after = await dashboard_repo.dpo_counts(conn)
    assert after is not None
    added = {k: int(after[k]) - int(before[k]) for k in (*STATES, "total_consents")}
    assert added == {
        "consents_full": 1,
        "consents_partial": 1,
        "consents_declined": 1,
        "consents_withdrawn": 1,
        "total_consents": 4,
    }
    assert sum(int(after[k]) for k in STATES) == int(after["total_consents"])
