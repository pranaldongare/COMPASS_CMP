"""The consent record as a PDF, for audit (2026-10-15).

Her name and one masked contact, nothing else about her; the decision per
purpose and its history; the notice as shown, in the language shown; a copy
for staff in scope and for her, each one audited; and an archive of every
record in a range, with a manifest that names no one.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from typing import Any

import pytest

from cmp.core.errors import NotFound, ValidationFailed
from cmp.core.permissions import Role
from cmp.core.security import content_hash, new_token, token_fingerprint
from cmp.db.sql import fetch_all
from cmp.domain.consent import record
from cmp.domain.consent import service as consent_service
from tests.conftest import hashed

pytestmark = pytest.mark.integration

HINDI = "धारा 5, डिजिटल व्यक्तिगत डेटा संरक्षण अधिनियम 2023 के अंतर्गत सूचना"


async def _consent(
    conn: Any, seeded: dict[str, Any], *, language: str = "english", text: str = "A notice."
) -> dict[str, Any]:
    """Her consent, through a notice served in `language`."""
    dpo = seeded["users"]["dpo"]["id"]
    notice_id = (
        await (
            await conn.execute(
                """INSERT INTO notice (notice_code, project_id, version, withdraw_url,
                                       exercise_rights_url, board_complaint_url, dpo_contact)
                   VALUES (%s, %s, 1, 'https://x/w', 'https://x/r',
                           'https://dpb.gov.in', 'dpo@test.local')
                   RETURNING notice_id""",
                (f"N-REC-{new_token()[:8]}", seeded["project"]["project_id"]),
            )
        ).fetchone()
    )["notice_id"]
    await conn.execute(
        """INSERT INTO notice_language (notice_id, language_code, rendered_text,
                                        content_hash, created_by, approved_by, approved_at)
           VALUES (%s, %s::language_code, %s, %s, %s, %s, now())""",
        (notice_id, language, text, content_hash(text), dpo, dpo),
    )
    await conn.execute(
        "INSERT INTO notice_purpose (notice_id, purpose_id) VALUES (%s, %s)",
        (notice_id, seeded["purpose"]["purpose_id"]),
    )
    await conn.execute(
        """UPDATE notice SET status = 'superseded'
            WHERE project_id = %s AND status = 'published'""",
        (seeded["project"]["project_id"],),
    )
    await conn.execute(
        """UPDATE notice SET status = 'published', recipients_text = 'Test Site',
                  approved_by = %s, published_at = now()
            WHERE notice_id = %s""",
        (dpo, notice_id),
    )
    raw = new_token()
    await conn.execute(
        """INSERT INTO consent_link (notice_id, site_id, token, expires_at, created_by)
           VALUES (%s, %s, %s, now() + interval '1 day', %s)""",
        (notice_id, seeded["site"]["site_id"], token_fingerprint(raw)[:64], dpo),
    )
    await consent_service.serve_notice(
        conn, token=raw, language_code=language, user_id=seeded["subject"]["id"]
    )
    return await consent_service.capture(
        conn,
        token=raw,
        user_id=seeded["subject"]["id"],
        language_code=language,
        grants={str(seeded["purpose"]["purpose_uuid"]): True},
        action_type="checkbox_click",
        ip_address="203.0.113.7",
    )


async def _record(conn: Any, consent_uuid: str) -> dict[str, Any]:
    from cmp.db.repositories import consent as repo

    artefact = dict(await repo.artefact_by_uuid(conn, consent_uuid) or {})
    await record._open_people([artefact])
    return await record.gather(conn, artefact)


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, default=str)


async def test_the_record_names_her_and_masks_one_contact_and_says_nothing_else(
    conn: Any, seeded: dict[str, Any]
) -> None:
    consent = await _consent(conn, seeded)
    data = await _record(conn, str(consent["consent_uuid"]))

    person = data["data_principal"]
    assert person["name"] == "Test Subject"
    assert person["contact"] == {"kind": "Mobile (masked)", "value": "+91******0001"}
    assert person["principal_uuid"] == str(seeded["subject"]["uuid"])
    dumped = _json(data)
    # Not her email (she has a mobile), not the address, not her date of birth.
    for absent in ("subject@test.local", "203.0.113.7", "2008-05-17", "+915550000001"):
        assert absent not in dumped
    assert data["status"] == "consented" and data["in_force"] is True
    assert data["notice"]["hash_matches"] is True and data["notice"]["text"] == "A notice."


async def test_a_staff_copy_is_a_pdf_and_is_audited_without_her_name(
    conn: Any, seeded: dict[str, Any]
) -> None:
    consent = await _consent(conn, seeded)
    payload, name = await record.for_staff(
        conn, str(consent["consent_uuid"]), role=Role.DPO, user_id=seeded["users"]["dpo"]["id"]
    )
    assert payload.startswith(b"%PDF") and b"consent-record.json" in payload
    assert name == f"consent-{consent['consent_uuid']}.pdf"

    rows = await fetch_all(
        conn,
        """SELECT detail_json FROM audit_log
            WHERE event_type = 'consent.record_downloaded' AND entity_id = %s""",
        (consent["consent_id"],),
    )
    [detail] = [r["detail_json"] for r in rows]
    assert {k: detail[k] for k in ("format", "copy", "in_archive")} == {
        "format": "pdf",
        "copy": "staff",
        "in_archive": False,
    }
    # Nothing erasable in the trail: no name, no contact.
    assert "Test Subject" not in _json(detail) and "5550000001" not in _json(detail)


async def test_staff_outside_the_scope_find_nothing(conn: Any, seeded: dict[str, Any]) -> None:
    """A DCO with no site of this project's: the record is not found."""
    consent = await _consent(conn, seeded)
    stranger_id = await _bare_dco(conn)
    with pytest.raises(NotFound):
        await record.for_staff(
            conn, str(consent["consent_uuid"]), role=Role.DCO, user_id=stranger_id
        )


async def _bare_dco(conn: Any) -> int:
    row = await (
        await conn.execute(
            """INSERT INTO auth_user (full_name, email, email_hash, role, status)
               VALUES ('Far Away', 'far.away.dco@test.local', %s, 'dco', 'active')
               RETURNING id""",
            (hashed("email", "far.away.dco@test.local"),),
        )
    ).fetchone()
    return int(row["id"])


async def test_she_has_her_own_and_nobody_elses(conn: Any, seeded: dict[str, Any]) -> None:
    consent = await _consent(conn, seeded)
    payload, _ = await record.for_subject(
        conn, str(consent["consent_uuid"]), user_id=seeded["subject"]["id"]
    )
    assert payload.startswith(b"%PDF")
    with pytest.raises(NotFound):
        await record.for_subject(
            conn, str(consent["consent_uuid"]), user_id=seeded["users"]["dpo"]["id"]
        )


async def test_a_withdrawal_supersedes_and_each_record_says_so(
    conn: Any, seeded: dict[str, Any]
) -> None:
    consent = await _consent(conn, seeded)
    withdrawal = await consent_service.withdraw(
        conn,
        consent_uuid=str(consent["consent_uuid"]),
        user_id=seeded["subject"]["id"],
        purpose_uuids=[],
        withdraw_all=True,
        ip_address="203.0.113.7",
    )
    original = await _record(conn, str(consent["consent_uuid"]))
    after = await _record(conn, str(withdrawal["consent_uuid"]))

    assert original["in_force"] is False
    assert original["superseded_by"] == str(withdrawal["consent_uuid"])
    assert after["supersedes"] == str(consent["consent_uuid"])
    assert after["status"] == "withdrawn"
    assert [p["decision"] for p in after["purposes"]] == ["withdrawn"]
    assert [h["this_record"] for h in after["history"]] == [False, True]


async def test_a_notice_shown_in_hindi_is_recorded_in_hindi(
    conn: Any, seeded: dict[str, Any]
) -> None:
    consent = await _consent(conn, seeded, language="hindi", text=HINDI)
    data = await _record(conn, str(consent["consent_uuid"]))
    assert data["notice"]["language"] == "hindi" and data["notice"]["text"] == HINDI
    assert data["notice"]["content_sha256_at_capture"] == content_hash(HINDI)

    payload, _ = await record.for_staff(
        conn, str(consent["consent_uuid"]), role=Role.DPO, user_id=seeded["users"]["dpo"]["id"]
    )
    assert payload.startswith(b"%PDF")


async def test_the_archive_holds_every_record_and_a_manifest_naming_no_one(
    conn: Any, seeded: dict[str, Any]
) -> None:
    consent = await _consent(conn, seeded)
    withdrawal = await consent_service.withdraw(
        conn,
        consent_uuid=str(consent["consent_uuid"]),
        user_id=seeded["subject"]["id"],
        purpose_uuids=[],
        withdraw_all=True,
        ip_address="203.0.113.7",
    )
    zipped, name, count = await record.archive(
        conn,
        role=Role.DPO,
        user_id=seeded["users"]["dpo"]["id"],
        project_uuid=str(seeded["project"]["project_uuid"]),
        date_from=consent["affirmative_action_at"],
    )
    assert name.startswith("consent-records-") and name.endswith(".zip")

    with zipfile.ZipFile(io.BytesIO(zipped)) as zf:
        manifest = list(csv.DictReader(io.StringIO(zf.read("manifest.csv").decode())))
        wanted = {str(consent["consent_uuid"]), str(withdrawal["consent_uuid"])}
        # The superseded decision is in the archive as well as the withdrawal.
        assert wanted <= {m["consent_uuid"] for m in manifest}
        assert count == len(manifest)
        for row in manifest:
            assert hashlib.sha256(zf.read(row["file"])).hexdigest() == row["sha256"]
        manifest_text = zf.read("manifest.csv").decode()
    assert "Test Subject" not in manifest_text and "5550000001" not in manifest_text


async def test_an_archive_too_large_is_refused_with_the_count(
    conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    await _consent(conn, seeded)
    await _consent(conn, seeded)
    monkeypatch.setattr(record, "ARCHIVE_LIMIT", 1)
    with pytest.raises(ValidationFailed) as caught:
        await record.archive(conn, role=Role.DPO, user_id=seeded["users"]["dpo"]["id"])
    assert caught.value.code == "archive_too_large"
    assert caught.value.details["matched"] >= 2


async def test_a_list_of_ids_gives_exactly_those_records_once_each(
    conn: Any, seeded: dict[str, Any]
) -> None:
    first = await _consent(conn, seeded)
    second = await _consent(conn, seeded)
    ids = [str(second["consent_uuid"]), str(first["consent_uuid"]), str(second["consent_uuid"])]
    zipped, _, count = await record.archive_of_ids(
        conn, ids, role=Role.DPO, user_id=seeded["users"]["dpo"]["id"]
    )
    assert count == 2
    with zipfile.ZipFile(io.BytesIO(zipped)) as zf:
        manifest = list(csv.DictReader(io.StringIO(zf.read("manifest.csv").decode())))
    # The order given, the repeat counted once.
    assert [m["consent_uuid"] for m in manifest] == ids[:2]

    rows = await fetch_all(
        conn,
        """SELECT detail_json->>'selection' AS selection FROM audit_log
            WHERE event_type = 'consent.record_downloaded' AND entity_id = %s""",
        (first["consent_id"],),
    )
    assert [r["selection"] for r in rows] == ["ids"]


async def test_an_id_not_found_or_out_of_scope_refuses_the_list_and_names_it(
    conn: Any, seeded: dict[str, Any]
) -> None:
    consent = await _consent(conn, seeded)
    unknown = "00000000-0000-4000-8000-000000000000"
    with pytest.raises(ValidationFailed) as caught:
        await record.archive_of_ids(
            conn,
            [str(consent["consent_uuid"]), unknown],
            role=Role.DPO,
            user_id=seeded["users"]["dpo"]["id"],
        )
    assert caught.value.code == "consent_records_not_found"
    assert caught.value.details["not_found"] == [unknown]

    # Somebody else's consent reads the same as one that does not exist.
    stranger = await _bare_dco(conn)
    with pytest.raises(ValidationFailed) as caught:
        await record.archive_of_ids(
            conn, [str(consent["consent_uuid"])], role=Role.DCO, user_id=stranger
        )
    assert caught.value.details["not_found"] == [str(consent["consent_uuid"])]
