"""The consented list the Data Collection Tool loads (2026-11-11).

Its columns are the DCT's data contract, version 1, and the DCT refuses a file
that breaks it: so every rule here is one its validator or its loader checks,
or one that decides who an agent may tag - only people whose latest consent on
the project is fully in force, a child or an unknown age marked as a minor,
and nothing on the file an agent does not need.
"""

from __future__ import annotations

import csv
import io
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from cmp.core.errors import Conflict, ServiceUnavailable
from cmp.core.security import content_hash, new_token, token_fingerprint
from cmp.db.repositories import exchange as exchange_repo
from cmp.db.sql import fetch_all, fetch_one, fetch_val
from cmp.domain.consent import service as consent_service
from cmp.domain.exchange import dct
from cmp.domain.exchange import service as exchange_service
from cmp.infrastructure.dkms.blind import index_of
from cmp.infrastructure.storage import service as storage_service
from cmp.infrastructure.storage.local import LocalFileStorage

pytestmark = pytest.mark.integration

TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


@pytest.fixture
def tmp_storage(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> LocalFileStorage:
    store = LocalFileStorage(root=str(tmp_path))
    monkeypatch.setattr(storage_service, "storage", lambda: store)
    return store


async def _purpose(conn: Any, seeded: dict[str, Any], code: str, validity: str | None) -> Any:
    return await fetch_one(
        conn,
        """INSERT INTO purpose (purpose_code, name, description, uses, lawful_basis,
                                data_categories, retention_period, retention_basis,
                                erasure_trigger, status, created_by, office_id,
                                consent_validity_period)
           VALUES (%s, %s, 'd', 'u', 'consent_s6', ARRAY['name'], interval '1 year',
                   'business_policy', 'withdrawal', 'active', %s,
                   (SELECT office_id FROM office WHERE office_code = 'rnd'), %s::interval)
           RETURNING purpose_id, purpose_uuid""",
        (code, f"Purpose {code}", seeded["users"]["dpo"]["id"], validity),
    )


async def _notice(conn: Any, seeded: dict[str, Any], purposes: list[Any]) -> int:
    """The seeded project's next notice, with these purposes. The one before is
    superseded, as publishing a new version does; consents on it stand."""
    notice = await fetch_one(
        conn,
        """INSERT INTO notice (notice_code, project_id, version, withdraw_url,
                               exercise_rights_url, board_complaint_url, dpo_contact)
           VALUES (%s, %s, 1, 'https://x/w', 'https://x/r', 'https://dpb.gov.in',
                   'dpo@test.local')
           RETURNING notice_id""",
        (f"N-DCT-{secrets.token_hex(3)}", seeded["project"]["project_id"]),
    )
    assert notice is not None
    text = "A second notice."
    await conn.execute(
        """INSERT INTO notice_language (notice_id, language_code, rendered_text,
                                        content_hash, created_by, approved_by, approved_at)
           VALUES (%s, 'english', %s, %s, %s, %s, now())""",
        (
            notice["notice_id"],
            text,
            content_hash(text),
            seeded["users"]["dpo"]["id"],
            seeded["users"]["dpo"]["id"],
        ),
    )
    for p in purposes:
        await conn.execute(
            "INSERT INTO notice_purpose (notice_id, purpose_id) VALUES (%s, %s)",
            (notice["notice_id"], p["purpose_id"]),
        )
    await conn.execute(
        "UPDATE notice SET status = 'superseded' WHERE project_id = %s AND status = 'published'",
        (seeded["project"]["project_id"],),
    )
    await conn.execute(
        """UPDATE notice SET status = 'published', recipients_text = 'Test Site',
                  approved_by = %s, published_at = now()
            WHERE notice_id = %s""",
        (seeded["users"]["dpo"]["id"], notice["notice_id"]),
    )
    return int(notice["notice_id"])


async def _person(conn: Any, name: str, *, email: str | None = None) -> dict[str, Any]:
    mobile = f"+9177{secrets.randbelow(10**8):08d}"
    row = await fetch_one(
        conn,
        """INSERT INTO auth_user (full_name, email, email_hash, mobile, mobile_hash, role,
                                  status, minor_until)
           VALUES (%s, %s, %s, %s, %s, 'data_subject', 'active', DATE '2000-01-01')
           RETURNING id, uuid""",
        (
            name,
            email,
            index_of("email", email) if email else None,
            mobile,
            index_of("mobile", mobile),
        ),
    )
    assert row is not None
    return {"id": int(row["id"]), "uuid": str(row["uuid"]), "mobile": mobile}


async def _consent(
    conn: Any,
    seeded: dict[str, Any],
    person: dict[str, Any],
    grants: list[tuple[Any, bool]],
    notice_id: int | None = None,
) -> dict[str, Any]:
    raw = new_token()
    await conn.execute(
        """INSERT INTO consent_link (notice_id, site_id, token, expires_at, created_by)
           VALUES (%s, %s, %s, now() + interval '1 day', %s)""",
        (
            notice_id or seeded["notice"]["notice_id"],
            seeded["site"]["site_id"],
            token_fingerprint(raw)[:64],
            seeded["users"]["dco"]["id"],
        ),
    )
    await consent_service.serve_notice(
        conn, token=raw, language_code="english", user_id=person["id"]
    )
    return await consent_service.capture(
        conn,
        token=raw,
        user_id=person["id"],
        language_code="english",
        grants={str(p["purpose_uuid"]): g for p, g in grants},
        action_type="checkbox_click",
        ip_address="127.0.0.1",
    )


async def _generate(conn: Any, seeded: dict[str, Any], role: str = "dpo") -> dict[str, Any]:
    return await exchange_service.generate(
        conn,
        project_uuid=str(seeded["project"]["project_uuid"]),
        actor_id=seeded["users"][role]["id"],
        role=role,
        export_type="dct_consented_list",
    )


async def _file(conn: Any, seeded: dict[str, Any], export: dict[str, Any]) -> str:
    dpo = seeded["users"]["dpo"]["id"]
    _, payload, _, _ = await exchange_service.download(
        conn, str(export["export_uuid"]), role="dpo", user_id=dpo
    )
    return payload


def _rows(payload: str) -> tuple[list[str], list[dict[str, str]]]:
    reader = csv.DictReader(io.StringIO(payload))
    return list(reader.fieldnames or []), list(reader)


class TestTheFile:
    async def test_it_is_the_contract_s_ten_columns_one_row_each_in_name_order(
        self, conn: Any, seeded: dict[str, Any], tmp_storage: LocalFileStorage
    ) -> None:
        meera = await _person(conn, "meera Nair", email=f"meera.{secrets.token_hex(3)}@x.org")
        asha = await _person(conn, "Asha Rao")
        for p in (meera, asha):
            await _consent(conn, seeded, p, [(seeded["purpose"], True)])

        export = await _generate(conn, seeded)
        assert export["export_type"] == "dct_consented_list"
        assert export["row_count"] == 2 and export["line_count"] == 2
        payload = await _file(conn, seeded, export)

        assert payload.split("\n", 1)[0] == ",".join(dct.COLUMNS)
        assert not payload.startswith("﻿") and "\r\n" not in payload
        header, rows = _rows(payload)
        assert header == list(dct.COLUMNS)
        assert [r["display_name"] for r in rows] == ["Asha Rao", "meera Nair"]
        assert {r["person_id"] for r in rows} == {meera["uuid"], asha["uuid"]}
        for r in rows:
            assert r["project_id"] == str(seeded["project"]["project_uuid"])
            assert r["project_name"] == "Test Project"
            assert all(UUID.match(r[k]) for k in ("project_id", "person_id", "consent_id"))
            assert r["is_minor"] == "false" and r["consent_expires_at"] == ""
        assert rows[0]["contact_hint"] == f"…{asha['mobile'][-2:]}"

        # Nothing an agent does not need: no contact in full, no link, no notice.
        assert meera["mobile"] not in payload and "@x.org" not in payload
        assert "N-TEST" not in payload and "Test Site" not in payload

    async def test_every_time_is_utc_with_a_z_and_the_list_is_good_for_seven_days(
        self, conn: Any, seeded: dict[str, Any], tmp_storage: LocalFileStorage
    ) -> None:
        for name in ("A One", "B Two"):
            await _consent(conn, seeded, await _person(conn, name), [(seeded["purpose"], True)])
        export = await _generate(conn, seeded)
        _, rows = _rows(await _file(conn, seeded, export))

        assert len({r["list_generated_at"] for r in rows}) == 1
        assert len({r["list_valid_until"] for r in rows}) == 1
        made = rows[0]["list_generated_at"]
        assert TS.match(made) and TS.match(rows[0]["list_valid_until"])
        made_at = datetime.strptime(made, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
        until = datetime.strptime(rows[0]["list_valid_until"], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=UTC
        )
        assert until - made_at == timedelta(days=7)
        # The record's own time: the file's date and `exported_at` agree.
        assert made_at == export["exported_at"].replace(microsecond=0)
        assert dct.file_name(seeded["project"]["project_uuid"], export["exported_at"]) == (
            f"consented_list_{seeded['project']['project_uuid']}_{made_at:%Y%m%d}.csv"
        )


class TestWhoIsOnIt:
    async def test_withdrawn_and_partial_people_are_left_out_and_counted(
        self, conn: Any, seeded: dict[str, Any], tmp_storage: LocalFileStorage
    ) -> None:
        extra = await _purpose(conn, seeded, f"P-X{secrets.token_hex(2)}", None)
        notice = await _notice(conn, seeded, [seeded["purpose"], extra])
        whole = await _person(conn, "Whole Consent")
        await _consent(conn, seeded, whole, [(seeded["purpose"], True), (extra, True)], notice)
        partial = await _person(conn, "Partial Consent")
        await _consent(conn, seeded, partial, [(seeded["purpose"], True), (extra, False)], notice)
        gone = await _person(conn, "Withdrew Later")
        given = await _consent(
            conn, seeded, gone, [(seeded["purpose"], True), (extra, True)], notice
        )
        await consent_service.withdraw(
            conn,
            consent_uuid=str(given["consent_uuid"]),
            user_id=gone["id"],
            purpose_uuids=None,
            withdraw_all=True,
            ip_address=None,
        )

        export = await _generate(conn, seeded)
        _, rows = _rows(await _file(conn, seeded, export))
        assert [r["person_id"] for r in rows] == [whole["uuid"]]
        assert export["left_out"] == {"withdrawn": 1, "partial": 1, "lapsed": 0, "no_name": 0}

    async def test_a_person_with_two_consents_is_on_it_once_with_the_newer(
        self, conn: Any, seeded: dict[str, Any], tmp_storage: LocalFileStorage
    ) -> None:
        twice = await _person(conn, "Twice Over")
        await _consent(conn, seeded, twice, [(seeded["purpose"], True)])
        notice = await _notice(conn, seeded, [seeded["purpose"]])
        newer = await _consent(conn, seeded, twice, [(seeded["purpose"], True)], notice)

        _, rows = _rows(await _file(conn, seeded, await _generate(conn, seeded)))
        assert [(r["person_id"], r["consent_id"]) for r in rows] == [
            (twice["uuid"], str(newer["consent_uuid"]))
        ]

    async def test_a_newer_partial_consent_leaves_an_older_whole_one_out(
        self, conn: Any, seeded: dict[str, Any], tmp_storage: LocalFileStorage
    ) -> None:
        person = await _person(conn, "Changed Their Mind")
        await _consent(conn, seeded, person, [(seeded["purpose"], True)])
        keeper = await _person(conn, "Keeps Them On")
        await _consent(conn, seeded, keeper, [(seeded["purpose"], True)])
        extra = await _purpose(conn, seeded, f"P-Y{secrets.token_hex(2)}", None)
        notice = await _notice(conn, seeded, [seeded["purpose"], extra])
        await _consent(conn, seeded, person, [(seeded["purpose"], True), (extra, False)], notice)

        export = await _generate(conn, seeded)
        _, rows = _rows(await _file(conn, seeded, export))
        assert [r["person_id"] for r in rows] == [keeper["uuid"]]
        assert export["left_out"]["partial"] == 1

    async def test_the_consent_lapses_with_its_shortest_granted_purpose(
        self, conn: Any, seeded: dict[str, Any], tmp_storage: LocalFileStorage
    ) -> None:
        short = await _purpose(conn, seeded, f"P-S{secrets.token_hex(2)}", "30 days")
        long = await _purpose(conn, seeded, f"P-L{secrets.token_hex(2)}", "400 days")
        notice = await _notice(conn, seeded, [short, long])
        person = await _person(conn, "Lapses Soon")
        given = await _consent(conn, seeded, person, [(short, True), (long, True)], notice)
        at = await fetch_val(
            conn,
            "SELECT affirmative_action_at FROM consent_artefact WHERE consent_uuid = %s",
            (str(given["consent_uuid"]),),
        )

        _, rows = _rows(await _file(conn, seeded, await _generate(conn, seeded)))
        assert rows[0]["consent_expires_at"] == dct.utc_z(at + timedelta(days=30))
        assert TS.match(rows[0]["consent_expires_at"])

    async def test_a_child_and_an_unknown_age_are_marked_minors(
        self, conn: Any, seeded: dict[str, Any], tmp_storage: LocalFileStorage
    ) -> None:
        child = await _person(conn, "A Child")
        unknown = await _person(conn, "No Birthday")
        adult = await _person(conn, "An Adult")
        for p in (child, unknown, adult):
            await _consent(conn, seeded, p, [(seeded["purpose"], True)])
        # A consent is only ever taken from a known adult; a date corrected
        # afterwards, or one never asked for on an old account, is what the
        # list meets.
        await conn.execute(
            "UPDATE auth_user SET minor_until = current_date + 400 WHERE id = %s", (child["id"],)
        )
        await conn.execute(
            "UPDATE auth_user SET minor_until = NULL WHERE id = %s", (unknown["id"],)
        )

        _, rows = _rows(await _file(conn, seeded, await _generate(conn, seeded)))
        minor = {r["display_name"]: r["is_minor"] for r in rows}
        assert minor == {"A Child": "true", "No Birthday": "true", "An Adult": "false"}

    async def test_a_person_with_no_name_is_left_out(
        self, conn: Any, seeded: dict[str, Any], tmp_storage: LocalFileStorage
    ) -> None:
        await _consent(conn, seeded, await _person(conn, "  "), [(seeded["purpose"], True)])
        await _consent(conn, seeded, await _person(conn, "Has A Name"), [(seeded["purpose"], True)])
        export = await _generate(conn, seeded)
        _, rows = _rows(await _file(conn, seeded, export))
        assert [r["display_name"] for r in rows] == ["Has A Name"]
        assert export["left_out"]["no_name"] == 1

    async def test_nobody_in_force_is_refused_and_records_nothing(
        self, conn: Any, seeded: dict[str, Any], tmp_storage: LocalFileStorage
    ) -> None:
        before = await fetch_val(
            conn,
            "SELECT count(*) FROM export_log WHERE project_id = %s",
            (seeded["project"]["project_id"],),
        )
        with pytest.raises(Conflict) as refused:
            await _generate(conn, seeded)
        assert refused.value.code == "nobody_consented"
        after = await fetch_val(
            conn,
            "SELECT count(*) FROM export_log WHERE project_id = %s",
            (seeded["project"]["project_id"],),
        )
        assert after == before


class TestTheRecord:
    async def test_it_is_recorded_like_the_project_export_and_downloads_as_made(
        self, conn: Any, seeded: dict[str, Any], tmp_storage: LocalFileStorage
    ) -> None:
        person = await _person(conn, "Recorded Once")
        await _consent(conn, seeded, person, [(seeded["purpose"], True)])
        export = await _generate(conn, seeded)

        lines = await fetch_all(
            conn,
            """SELECT auth_user_id, destination_country FROM export_line l
                 JOIN export_log e USING (export_id) WHERE e.export_uuid = %s""",
            (str(export["export_uuid"]),),
        )
        assert [(r["auth_user_id"], r["destination_country"]) for r in lines] == [
            (person["id"], "IN")
        ]
        [event] = await fetch_all(
            conn,
            """SELECT detail_json FROM audit_log
                WHERE event_type = 'export.generated' AND entity_id = %s""",
            (export["export_id"],),
        )
        assert event["detail_json"]["type"] == "dct_consented_list"
        assert event["detail_json"]["left_out"]["withdrawn"] == 0
        assert "Recorded Once" not in str(event["detail_json"])

        first = await _file(conn, seeded, export)
        # The person renamed: a download is still the file as it was made.
        await conn.execute(
            "UPDATE auth_user SET full_name = 'Renamed' WHERE id = %s", (person["id"],)
        )
        assert await _file(conn, seeded, export) == first
        logs = await fetch_val(
            conn,
            "SELECT count(*) FROM export_log WHERE project_id = %s",
            (seeded["project"]["project_id"],),
        )
        assert logs == 1
        row = await exchange_repo.export_by_uuid(
            conn, str(export["export_uuid"]), role="dpo", user_id=seeded["users"]["dpo"]["id"]
        )
        assert row is not None and row["file_hash"] == export["file_hash"]

    async def test_a_formula_shaped_name_is_written_as_text(
        self, conn: Any, seeded: dict[str, Any], tmp_storage: LocalFileStorage
    ) -> None:
        await _consent(conn, seeded, await _person(conn, "=1+1"), [(seeded["purpose"], True)])
        _, rows = _rows(await _file(conn, seeded, await _generate(conn, seeded)))
        assert rows[0]["display_name"] == "'=1+1"

    async def test_a_list_storage_would_not_keep_is_not_recorded(
        self, conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        await _consent(conn, seeded, await _person(conn, "Not Kept"), [(seeded["purpose"], True)])
        monkeypatch.setattr(exchange_service, "_keep_export_file", lambda raw, digest: None)
        with pytest.raises(ServiceUnavailable):
            await _generate(conn, seeded)
