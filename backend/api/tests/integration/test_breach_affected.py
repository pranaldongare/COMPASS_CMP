"""Who a breach touched - derived, confirmed and revised (S3-02).

A processor breach lists exactly the people in files sent to it; a source
breach exactly the people captured in its assets; a database breach the
people in the affected tables within the window. The DPO adds whom the
records cannot show and leaves out whom they wrongly include. A revision adds
rows and leaves the earlier list as it was.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
import pytest

from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.core.security import new_token, token_fingerprint
from cmp.db.repositories import breaches as breach_repo
from cmp.domain.breach import affected, service
from cmp.domain.consent import service as consent_service
from cmp.infrastructure.dkms.fields import ENCRYPTED_FIELDS
from tests.conftest import hashed
from tests.integration.test_rights_flows import _asset_with_her

pytestmark = pytest.mark.integration


async def _person(conn: Any, seeded: dict[str, Any], tag: str) -> tuple[int, str, int]:
    """A data principal with a real consent on the seeded notice.

    Returns her id, her uuid and her consent's id.
    """
    mobile = f"+9155501{secrets.randbelow(100000):05d}"
    row = await (
        await conn.execute(
            """INSERT INTO auth_user (full_name, mobile, mobile_hash, role, status, minor_until)
               VALUES (%s, %s, %s, 'data_subject', 'active', DATE '2000-01-01')
               RETURNING id, uuid""",
            (f"Affected {tag}", mobile, hashed("mobile", mobile)),
        )
    ).fetchone()
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
    await consent_service.serve_notice(conn, token=raw, language_code="english", user_id=row["id"])
    consent = await consent_service.capture(
        conn,
        token=raw,
        user_id=row["id"],
        language_code="english",
        grants={str(seeded["purpose"]["purpose_uuid"]): True},
        action_type="checkbox_click",
        ip_address="127.0.0.1",
    )
    return int(row["id"]), str(row["uuid"]), int(consent["consent_id"])


async def _export(
    conn: Any, seeded: dict[str, Any], processor: str, people: list[tuple[int, str, int]]
) -> None:
    """An export whose lines went to this processor."""
    processor_id = seeded["processors"][processor]["processor_id"]
    export_id = (
        await (
            await conn.execute(
                """INSERT INTO export_log
                     (project_id, export_type, exported_by, row_count, file_hash)
                   VALUES (%s, 'project_export', %s, %s, 'feed') RETURNING export_id""",
                (seeded["project"]["project_id"], seeded["users"]["dpo"]["id"], len(people)),
            )
        ).fetchone()
    )["export_id"]
    for pid, _, consent_id in people:
        await conn.execute(
            """INSERT INTO export_line (export_id, auth_user_id, consent_id,
                                        destination_processor_id, destination_country)
               VALUES (%s, %s, %s, %s, 'IN')""",
            (export_id, pid, consent_id, processor_id),
        )


async def _source_of(conn: Any, asset_consent_id: int) -> str:
    row = await (
        await conn.execute(
            """SELECT ds.source_uuid FROM asset_consent ac
                 JOIN data_asset da ON da.asset_id = ac.asset_id
                 JOIN data_source ds ON ds.source_id = da.source_id
                WHERE ac.asset_consent_id = %s""",
            (asset_consent_id,),
        )
    ).fetchone()
    return str(row["source_uuid"])


async def _breach(conn: Any, seeded: dict[str, Any]) -> str:
    made = await service.record(
        conn,
        title="A lab share left open",
        detected_at=datetime.now(UTC) - timedelta(hours=2),
        began_at=None,
        location_kind="platform",
        processor_uuid=None,
        source_uuid=None,
        location_detail=None,
        actor_id=int(seeded["users"]["dpo"]["id"]),
    )
    return str(made["breach_uuid"])


def _uuids(listing: dict[str, Any]) -> set[str]:
    return {str(p["person_uuid"]) for p in listing["people"]}


async def test_a_processor_breach_lists_exactly_the_people_sent_to_it(
    conn: Any, seeded: dict[str, Any]
) -> None:
    a, b, c = [await _person(conn, seeded, t) for t in "abc"]
    await _export(conn, seeded, "external", [a, b])
    await _export(conn, seeded, "in_house", [c])
    uuid = await _breach(conn, seeded)
    scope = {
        "kind": "processor",
        "processor_uuid": str(seeded["processors"]["external"]["processor_uuid"]),
    }

    shown = await affected.preview(conn, breach_uuid=uuid, scopes=[scope])
    assert shown["derived"] == 2 and shown["would_add"] == 2
    listing = await affected.confirm(
        conn,
        breach_uuid=uuid,
        scopes=[scope],
        exclude=[],
        add=[],
        note=None,
        actor_id=seeded["users"]["dpo"]["id"],
    )
    assert _uuids(listing) == {a[1], b[1]}
    assert all(p["found_by"] == "processor" and p["evidence"]["exports"] for p in listing["people"])


async def test_a_source_breach_lists_exactly_the_people_in_its_assets(
    conn: Any, seeded: dict[str, Any]
) -> None:
    a, _, c = [await _person(conn, seeded, t) for t in "abc"]
    held = await _asset_with_her(conn, seeded, a[2], bystanders=2, ref=f"S1{secrets.token_hex(3)}")
    await _asset_with_her(conn, seeded, c[2], bystanders=0, ref=f"S2{secrets.token_hex(3)}")
    uuid = await _breach(conn, seeded)
    listing = await affected.confirm(
        conn,
        breach_uuid=uuid,
        scopes=[{"kind": "data_source", "source_uuid": await _source_of(conn, held)}],
        exclude=[],
        add=[],
        note=None,
        actor_id=seeded["users"]["dpo"]["id"],
    )
    # The bystanders have no account to notify; they are in the asset, not on the list.
    assert _uuids(listing) == {a[1]}


async def test_a_database_breach_lists_the_people_in_the_tables_and_window(
    conn: Any, seeded: dict[str, Any]
) -> None:
    a, b, c = [await _person(conn, seeded, t) for t in "abc"]
    started = (await (await conn.execute("SELECT now() AS t")).fetchone())["t"]
    uuid = await _breach(conn, seeded)
    scope = {"kind": "platform", "tables": ["consent_artefact"], "since": started, "until": started}
    shown = await affected.preview(conn, breach_uuid=uuid, scopes=[scope])
    assert {str(p["person_uuid"]) for p in shown["people"]} == {a[1], b[1], c[1]}
    assert all(p["evidence"]["tables"] == ["consent_artefact"] for p in shown["people"])

    before = {**scope, "since": None, "until": started - timedelta(days=1)}
    earlier = await affected.preview(conn, breach_uuid=uuid, scopes=[before])
    assert not {a[1], b[1], c[1]} & {str(p["person_uuid"]) for p in earlier["people"]}

    with pytest.raises(ValidationFailed, match="Choose from"):
        await affected.preview(
            conn, breach_uuid=uuid, scopes=[{"kind": "platform", "tables": ["pg_authid"]}]
        )
    with pytest.raises(ValidationFailed):
        await affected.preview(conn, breach_uuid=uuid, scopes=[{"kind": "everywhere"}])


async def test_the_dpo_adds_and_leaves_out_and_a_revision_keeps_the_last_list(
    conn: Any, seeded: dict[str, Any]
) -> None:
    a, b, c = [await _person(conn, seeded, t) for t in "abc"]
    d = await _person(conn, seeded, "d")
    await _export(conn, seeded, "external", [a, b, c])
    uuid = await _breach(conn, seeded)
    dpo = seeded["users"]["dpo"]["id"]
    scope = {
        "kind": "processor",
        "processor_uuid": str(seeded["processors"]["external"]["processor_uuid"]),
    }

    first = await affected.confirm(
        conn,
        breach_uuid=uuid,
        scopes=[scope],
        exclude=[c[1]],
        add=[],
        note="c was test data",
        actor_id=dpo,
    )
    assert _uuids(first) == {a[1], b[1]}
    [rev1] = first["revisions"]
    assert (rev1["derived"], rev1["excluded"], rev1["newly_listed"]) == (3, 1, 2)
    assert str(rev1["note"]).startswith("SE::")
    before = await (
        await conn.execute("SELECT * FROM breach_affected ORDER BY affected_id")
    ).fetchall()

    # Knowledge grows: derive again and add one the records cannot show.
    second = await affected.confirm(
        conn,
        breach_uuid=uuid,
        scopes=[scope],
        exclude=[],
        add=[d[1], a[1]],
        note=None,
        actor_id=dpo,
    )
    assert second["total"] == 4, "c now, d by hand; a and b are not listed twice"
    assert _uuids(second) == {a[1], b[1], c[1], d[1]}
    by_person = {str(p["person_uuid"]): p for p in second["people"]}
    assert by_person[d[1]]["found_by"] == "dpo" and by_person[d[1]]["revision"] == 2
    assert by_person[a[1]]["revision"] == 1
    after = await (
        await conn.execute("SELECT * FROM breach_affected ORDER BY affected_id")
    ).fetchall()
    assert after[: len(before)] == before, "the earlier rows are byte-identical"
    assert [r["newly_listed"] for r in second["revisions"]] == [2, 2]

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        await conn.execute("DELETE FROM breach_affected")


async def test_nobody_is_added_from_nowhere(conn: Any, seeded: dict[str, Any]) -> None:
    uuid = await _breach(conn, seeded)
    dpo = seeded["users"]["dpo"]["id"]
    with pytest.raises(ValidationFailed):
        await affected.confirm(
            conn, breach_uuid=uuid, scopes=[], exclude=[], add=[], note=None, actor_id=dpo
        )
    with pytest.raises(NotFound):
        await affected.confirm(
            conn,
            breach_uuid=uuid,
            scopes=[],
            exclude=[],
            add=["00000000-0000-4000-8000-000000000000"],
            note=None,
            actor_id=dpo,
        )
    await service.determine(
        conn, breach_uuid=uuid, outcome="no", reasoning="Test", became_aware_at=None, actor_id=dpo
    )
    await service.transition(conn, breach_uuid=uuid, to="closed", reason=None, actor_id=dpo)
    with pytest.raises(Conflict):
        await affected.confirm(
            conn,
            breach_uuid=uuid,
            scopes=[],
            exclude=[],
            add=[str(seeded["subject"]["uuid"])],
            note=None,
            actor_id=dpo,
        )


async def test_the_trail_counts_and_names_nobody(conn: Any, seeded: dict[str, Any]) -> None:
    a = await _person(conn, seeded, "a")
    uuid = await _breach(conn, seeded)
    await affected.confirm(
        conn,
        breach_uuid=uuid,
        scopes=[],
        exclude=[],
        add=[a[1]],
        note=None,
        actor_id=seeded["users"]["dpo"]["id"],
    )
    row = await (
        await conn.execute(
            """SELECT subject_user_id, detail_json::text AS detail FROM audit_log
                WHERE event_type = 'breach.affected_revised' ORDER BY log_id DESC LIMIT 1"""
        )
    ).fetchone()
    assert row["subject_user_id"] is None
    assert a[1] not in row["detail"] and '"newly_listed": 1' in row["detail"]


def test_every_sealed_table_is_traced_to_a_principal_or_says_why_not() -> None:
    """A database breach finds people through `PLATFORM_TABLES`. A sealed table
    it does not know is one whose people it would silently miss."""
    known = set(breach_repo.PLATFORM_TABLES) | set(breach_repo.NOT_ABOUT_A_PRINCIPAL)
    missing = sorted(set(ENCRYPTED_FIELDS) - known)
    assert not missing, f"trace these to a person in PLATFORM_TABLES, or say why not: {missing}"
