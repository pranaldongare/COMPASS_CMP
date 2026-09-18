"""Asking the audit trail a question, the way the console now can.

By whom it concerns, by what it was about (named by its public uuid), by
the kind of thing that happened, by a term in the recorded detail; the
summary and the export over the same rows; and the pickers that turn a few
letters of a name into the record to filter on.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest

from cmp.core.pagination import Cursor, PageRequest
from cmp.db.repositories import audit as repo
from cmp.db.repositories import audit_lookup
from cmp.db.sql import fetch_one
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event

pytestmark = pytest.mark.integration


async def _name(conn: Any, user_id: int) -> str:
    row = await (
        await conn.execute("SELECT full_name FROM auth_user WHERE id = %s", (user_id,))
    ).fetchone()
    assert row is not None
    return str(row["full_name"])


def _page(limit: int = 50) -> PageRequest:
    return PageRequest(limit=limit, cursor=None, sort_field="occurred_at", descending=True)


async def _write_some(conn: Any, seeded: dict[str, Any]) -> None:
    """A handful of rows about the seeded world, so filters have something to divide."""
    subject = seeded["subject"]["id"]
    dpo = seeded["users"]["dpo"]["id"]
    project = seeded["project"]["project_id"]
    await audit.record(
        conn,
        event=Event.CONSENT_GIVEN,
        entity_type="consent_artefact",
        entity_id=999_999,
        subject_user_id=subject,
        actor_user_id=subject,
        detail={"notice": "n", "granted": ["gait"]},
    )
    await audit.record(
        conn,
        event=Event.PROJECT_UPDATED,
        entity_type="project",
        entity_id=project,
        actor_user_id=dpo,
        detail={"reason": "Renamed for the Pune campus"},
    )
    await audit.record(
        conn,
        event=Event.LOGIN_SUCCEEDED,
        entity_type="auth_user",
        entity_id=dpo,
        actor_user_id=dpo,
    )


class TestFilters:
    async def test_by_entity_uuid_resolves_to_the_trails_id(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        await _write_some(conn, seeded)
        project = seeded["project"]
        resolved = await audit_lookup.id_for_uuid(conn, "project", str(project["project_uuid"]))
        assert resolved == project["project_id"]

        items, _, total = await repo.search(
            conn, _page(), repo.AuditFilters(entity_type="project", entity_id=resolved)
        )
        assert total >= 1
        assert all(r["entity_type"] == "project" and r["entity_id"] == resolved for r in items)

    async def test_an_unknown_uuid_resolves_to_nothing(self, conn: Any) -> None:
        assert (
            await audit_lookup.id_for_uuid(conn, "project", "00000000-0000-4000-8000-000000000000")
            is None
        )
        assert await audit_lookup.id_for_uuid(conn, "no_such_table", "x") is None

    async def test_by_subject_and_by_actor_role(self, conn: Any, seeded: dict[str, Any]) -> None:
        await _write_some(conn, seeded)
        items, _, _ = await repo.search(
            conn, _page(), repo.AuditFilters(subject_uuid=str(seeded["subject"]["uuid"]))
        )
        assert items and all(
            str(r["subject_uuid"]) == str(seeded["subject"]["uuid"]) for r in items
        )

        items, _, _ = await repo.search(conn, _page(), repo.AuditFilters(actor_role="dpo"))
        assert items and all(r["actor_role"] == "dpo" for r in items)

    async def test_by_event_group(self, conn: Any, seeded: dict[str, Any]) -> None:
        await _write_some(conn, seeded)
        items, _, _ = await repo.search(conn, _page(), repo.AuditFilters(event_group="consent"))
        assert items and all(r["event_type"].startswith("consent.") for r in items)

    async def test_free_text_reaches_the_detail_and_the_names(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        await _write_some(conn, seeded)
        items, _, _ = await repo.search(conn, _page(), repo.AuditFilters(q="pune campus"))
        assert any(r["event_type"] == "project.updated" for r in items)
        # The subject's name, not only the detail.
        name = await _name(conn, seeded["subject"]["id"])
        items, _, _ = await repo.search(conn, _page(), repo.AuditFilters(q=name[:6]))
        assert items

    async def test_a_wildcard_in_the_term_is_literal(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        await _write_some(conn, seeded)
        items, _, total = await repo.search(conn, _page(), repo.AuditFilters(q="%"))
        assert total == 0 and items == []

    async def test_dates_bound_the_answer(self, conn: Any, seeded: dict[str, Any]) -> None:
        await _write_some(conn, seeded)
        tomorrow = datetime.now(UTC) + timedelta(days=1)
        _, _, total = await repo.search(conn, _page(), repo.AuditFilters(date_from=tomorrow))
        assert total == 0

    async def test_paging_keeps_the_filter(self, conn: Any, seeded: dict[str, Any]) -> None:
        await _write_some(conn, seeded)
        first, cursor, total = await repo.search(
            conn, _page(limit=1), repo.AuditFilters(actor_uuid=str(seeded["users"]["dpo"]["uuid"]))
        )
        assert len(first) == 1 and total >= 2 and cursor
        req = PageRequest(
            limit=1, cursor=Cursor.decode(cursor), sort_field="occurred_at", descending=True
        )
        second, _, _ = await repo.search(
            conn, req, repo.AuditFilters(actor_uuid=str(seeded["users"]["dpo"]["uuid"]))
        )
        assert second and second[0]["log_uuid"] != first[0]["log_uuid"]
        assert str(second[0]["actor_uuid"]) == str(seeded["users"]["dpo"]["uuid"])


class TestSummaryAndExport:
    async def test_summary_counts_the_same_rows_as_the_list(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        await _write_some(conn, seeded)
        filters = repo.AuditFilters(actor_uuid=str(seeded["users"]["dpo"]["uuid"]))
        _, _, total = await repo.search(conn, _page(), filters)
        s = await repo.summary(conn, filters, days=7)
        assert s["total"] == total
        assert sum(c["count"] for c in s["by_group"]) == total
        assert sum(c["count"] for c in s["by_actor_role"]) == total
        assert s["by_actor_role"][0]["key"] == "dpo"
        assert s["first_at"] is not None and s["last_at"] is not None
        assert s["by_day"] and s["by_day"][-1]["count"] >= 1

    async def test_export_rows_are_newest_first_and_bounded(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        await _write_some(conn, seeded)
        rows = await repo.export_rows(conn, repo.AuditFilters(), limit=2)
        assert len(rows) == 2
        assert rows[0]["occurred_at"] >= rows[1]["occurred_at"]


class TestLookup:
    async def test_a_data_principal_by_name(self, conn: Any, seeded: dict[str, Any]) -> None:
        """Searched on a name nothing else shares.

        The lookup returns ten rows ordered by name, so a term the seeded
        principal merely *contains* is not a test of anything: a database with
        eleven other people matching it sorts her off the end and the assertion
        fails for the size of the register rather than for the search. This
        makes its own principal, with a name no other row can hold.
        """
        unique = f"Zzq{uuid4().hex[:10]}"
        row = await fetch_one(
            conn,
            """INSERT INTO auth_user (full_name, email, mobile, role, status)
               VALUES (%s, %s, %s, 'data_subject', 'active')
               RETURNING uuid""",
            (
                f"{unique} Principal",
                f"{unique.lower()}@test.local",
                f"+9198765{uuid4().int % 100000:05d}",
            ),
        )

        hits = await audit_lookup.lookup(conn, "data_subject", unique)

        assert [h["uuid"] for h in hits] == [str(row["uuid"])]
        assert all(h["filter"] == "subject" and h["entity_type"] == "auth_user" for h in hits)

    async def test_staff_by_name_feed_the_actor_filter(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        hits = await audit_lookup.lookup(conn, "staff", "dpo@test")
        assert hits and hits[0]["filter"] == "actor"

    async def test_records_by_kind(self, conn: Any, seeded: dict[str, Any]) -> None:
        """Every kind the audit filter offers finds its own records.

        The seeded world carries a project, a notice, a processor and a site but
        no data source, so this used to pass only where one already existed -
        which is every developer's database and no clean one. It makes the
        missing row itself rather than hoping for it.
        """
        await conn.execute(
            """INSERT INTO data_source
                 (source_code, name, source_role, exchange_mode, processor_id, status)
               VALUES ('SRC-LOOKUP-1', 'Lookup Rig', 'collection', 'file_import', %s, 'active')""",
            (seeded["processors"]["external"]["processor_id"],),
        )

        for kind, expected_type in (
            ("project", "project"),
            ("notice", "notice"),
            ("processor", "processor"),
            ("data_source", "data_source"),
            ("site", "project_site"),
        ):
            hits = await audit_lookup.lookup(conn, kind, "")
            assert hits, kind
            assert all(h["entity_type"] == expected_type and h["filter"] == "entity" for h in hits)

    async def test_an_unknown_kind_finds_nothing(self, conn: Any) -> None:
        assert await audit_lookup.lookup(conn, "planet", "x") == []

    async def test_the_term_is_matched_literally(self, conn: Any, seeded: dict[str, Any]) -> None:
        assert await audit_lookup.lookup(conn, "project", "%%%zzz") == []
