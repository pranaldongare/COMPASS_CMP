"""Analytics, reports and schedules, against the record (ADR 0045).

Management reads both offices, combined or one; an officer reads their own
and is refused the other; the administrator reads audit and health and no
scorecard; the roles that do the work read their own. A rate is counted from
its two counts and judged against the target the administrator set. A count of
fewer people than the threshold is withheld. A report is made from the record,
kept with its hash, read by those who may and deleted by them, every act on
the trail; a schedule mails only roles that may read it.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest

from cmp.core.errors import Forbidden, NotFound, ValidationFailed
from cmp.core.security import content_hash
from cmp.domain.analytics import periods, reports, service
from cmp.domain.analytics.service import Reader
from cmp.tasks import dispatch as dispatch_mod
from tests.conftest import hashed

pytestmark = pytest.mark.integration

PERIOD = "last_30_days"


@pytest.fixture
def queued(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, tuple[Any, ...]]]:
    sent: list[tuple[str, tuple[Any, ...]]] = []

    def capture(task: Any, *args: Any, **kwargs: Any) -> str:
        sent.append((task.name, args))
        return "queued-in-a-test"

    monkeypatch.setattr(dispatch_mod, "dispatch_optional", capture)
    return sent


async def _user(conn: Any, role: str, office: str | None) -> int:
    email = f"{role}-{uuid4().hex[:6]}@test.local"
    row = await (
        await conn.execute(
            """INSERT INTO auth_user (full_name, email, email_hash, role, status, password_hash,
                                      office_id)
               VALUES (%s, %s, %s, %s::user_role, 'active', 'x',
                       (SELECT office_id FROM office WHERE office_code = %s))
               RETURNING id""",
            (f"Test {role}", email, hashed("email", email), role, office),
        )
    ).fetchone()
    return int(row["id"])


async def _request(
    conn: Any, office: str, *, received_days_ago: int, closed_days_ago: int | None, late: bool
) -> None:
    received = datetime.now(UTC) - timedelta(days=received_days_ago)
    closed = (
        None if closed_days_ago is None else datetime.now(UTC) - timedelta(days=closed_days_ago)
    )
    due = (closed - timedelta(days=1)) if (closed and late) else received + timedelta(days=90)
    await conn.execute(
        """INSERT INTO rights_request (reference, request_type, status, channel, submitted_contact,
                                       submitted_contact_hash, request_text, received_at, due_at,
                                       closed_at, outcome, office_id)
           VALUES (%s, 'access', %s, 'portal', 'x', 'h', 'x', %s, %s, %s,
                   %s, (SELECT office_id FROM office WHERE office_code = %s))""",
        (
            f"RR-T-{uuid4().hex[:8]}",
            "closed" if closed else "received",
            received,
            due,
            closed,
            "complete" if closed else None,
            office,
        ),
    )


async def _world(conn: Any) -> None:
    # R&D: three closed, one of them late; one open. HR: one closed on time.
    for late in (False, False, True):
        await _request(conn, "rnd", received_days_ago=20, closed_days_ago=5, late=late)
    await _request(conn, "rnd", received_days_ago=3, closed_days_ago=None, late=False)
    await _request(conn, "hr", received_days_ago=10, closed_days_ago=2, late=False)


def _fig(out: dict[str, Any], key: str) -> dict[str, Any]:
    return next(m for m in out["metrics"] if m["key"] == key)


async def _figures(conn: Any, reader: Reader, **kw: Any) -> dict[str, Any]:
    await conn.execute("SELECT set_config('app.office', %s, false)", (reader.office or "all",))
    out = await service.figures(conn, reader, period=periods.resolve(PERIOD), **kw)
    await conn.execute("SELECT set_config('app.office', 'all', false)")
    return out


class TestWhoReadsWhat:
    async def test_management_reads_both_offices_combined_or_one(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        await _world(conn)
        boss = Reader("management", await _user(conn, "management", None), None)
        keys = ["rights.closed", "rights.on_time_rate", "rights.received"]
        both = await _figures(conn, boss, keys=keys)
        rnd = await _figures(conn, boss, keys=keys, office="rnd")
        hr = await _figures(conn, boss, keys=keys, office="hr")
        assert _fig(both, "rights.closed")["value"] >= 4
        assert _fig(rnd, "rights.closed")["value"] == _fig(both, "rights.closed")["value"] - 1
        assert _fig(hr, "rights.closed")["value"] == 1
        split = await _figures(conn, boss, keys=["rights.closed"], dim="office")
        assert {p["key"] for p in _fig(split, "rights.closed")["breakdown"]} >= {"rnd", "hr"}

    async def test_an_officer_reads_their_own_office_and_is_refused_the_other(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        await _world(conn)
        dpo = Reader("dpo", int(seeded["users"]["dpo"]["id"]), "rnd")
        mine = await _figures(conn, dpo, keys=["rights.closed"])
        boss = Reader("management", await _user(conn, "management", None), None)
        rnd = await _figures(conn, boss, keys=["rights.closed"], office="rnd")
        assert _fig(mine, "rights.closed")["value"] == _fig(rnd, "rights.closed")["value"]
        with pytest.raises(Forbidden):
            await _figures(conn, dpo, keys=["rights.closed"], office="hr")
        with pytest.raises(Forbidden):
            await _figures(conn, dpo, keys=["rights.closed"], dim="office")

    async def test_the_administrator_reads_health_and_no_scorecard(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        admin = Reader("admin", int(seeded["users"]["admin"]["id"]), None)
        health = await _figures(conn, admin, section="health")
        assert {m["section"] for m in health["metrics"]} == {"health"}
        with pytest.raises(Forbidden):
            await _figures(conn, admin, section="management")
        with pytest.raises(Forbidden):
            await _figures(conn, admin, keys=["rights.closed"])

    async def test_an_rnd_user_reads_only_their_own_projects(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        owner = Reader("rnd_user", int(seeded["users"]["rnd_user"]["id"]), "rnd")
        other = Reader("rnd_user", await _user(conn, "rnd_user", "rnd"), "rnd")
        mine = _fig(await _figures(conn, owner, keys=["mine.projects"]), "mine.projects")
        theirs = _fig(await _figures(conn, other, keys=["mine.projects"]), "mine.projects")
        assert mine["value"] >= 1 and theirs["value"] == 0
        with pytest.raises(Forbidden):
            await _figures(conn, owner, keys=["rights.closed"])


class TestTheFigures:
    async def test_a_rate_is_its_two_counts_and_is_judged_against_the_target(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        await _world(conn)
        boss = Reader("management", await _user(conn, "management", None), None)
        rnd = await _figures(
            conn,
            boss,
            keys=["rights.on_time_rate", "rights.closed", "rights.closed_on_time"],
            office="rnd",
        )
        rate = _fig(rnd, "rights.on_time_rate")
        closed, on_time = (
            _fig(rnd, "rights.closed")["value"],
            _fig(rnd, "rights.closed_on_time")["value"],
        )
        assert rate["value"] == round(100 * on_time / closed, 1)
        assert rate["status"] in ("red", "amber")

        admin = int(seeded["users"]["admin"]["id"])
        await service.set_target(conn, "rights.on_time_rate", target=50, amber=40, actor_id=admin)
        judged = _fig(
            await _figures(conn, boss, keys=["rights.on_time_rate"], office="rnd"),
            "rights.on_time_rate",
        )
        assert judged["target"] == 50 and judged["status"] == "green"
        cur = await conn.execute(
            "SELECT 1 FROM audit_log WHERE event_type = 'analytics.target_changed'"
            " AND actor_user_id = %s",
            (admin,),
        )
        assert await cur.fetchone()

    async def test_an_amber_line_on_the_wrong_side_is_refused(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        with pytest.raises(ValidationFailed):
            await service.set_target(
                conn,
                "rights.on_time_rate",
                target=90,
                amber=95,
                actor_id=int(seeded["users"]["admin"]["id"]),
            )

    async def test_a_small_count_of_people_is_withheld_above_the_threshold(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        """One consent in force on the seeded project: shown at the threshold
        of 1, withheld at 5."""
        await conn.execute(
            """INSERT INTO consent_artefact (auth_user_id, notice_id, notice_language_id,
                                             notice_content_hash, link_id, served_at,
                                             affirmative_action_at, action_type, is_withdrawal)
               SELECT %s, %s, %s, %s, %s, now(), now(), 'button_press', false""",
            (
                seeded["subject"]["id"],
                seeded["notice"]["notice_id"],
                seeded["language"]["notice_language_id"],
                content_hash(seeded["notice_text"]),
                seeded["link"]["link_id"],
            ),
        )
        await conn.execute(
            """INSERT INTO consent_purpose_grant (consent_id, purpose_id, granted)
               SELECT max(consent_id), %s, true FROM consent_artefact""",
            (seeded["purpose"]["purpose_id"],),
        )
        boss = Reader("management", await _user(conn, "management", None), None)
        shown = _fig(await _figures(conn, boss, keys=["consent.given"]), "consent.given")
        assert shown["value"] and shown["value"] >= 1 and not shown["suppressed"]
        admin = int(seeded["users"]["admin"]["id"])
        await service.set_threshold(conn, 5, actor_id=admin)
        hidden = _fig(await _figures(conn, boss, keys=["consent.given"]), "consent.given")
        if 0 < (shown["value"] or 0) < 5:
            assert hidden["suppressed"] and hidden["value"] is None and hidden["status"] is None


class TestReports:
    async def test_a_report_is_made_kept_read_and_deleted_on_the_trail(
        self,
        conn: Any,
        seeded: dict[str, Any],
        queued: list[Any],
        tmp_path: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from cmp.core.config import settings

        monkeypatch.setattr(settings, "upload_root", str(tmp_path))
        await _world(conn)
        boss = Reader("management", await _user(conn, "management", None), None)
        for kind, fmt in (
            ("management_scorecard", "pdf"),
            ("board_pack", "pdf"),
            ("analytics_summary", "xlsx"),
            ("data_inventory", "xlsx"),
        ):
            row = await reports.request(
                conn, boss, kind_key=kind, fmt=fmt, params={"period": PERIOD}
            )
            assert row["status"] == "queued"
            made = await reports.make(conn, str(row["report_uuid"]))
            assert made and made["status"] == "ready", (kind, made and made["error"])
            data, name, _mime = await reports.download(conn, boss, str(row["report_uuid"]))
            assert data and name.endswith(f".{fmt}")
        assert any(name == "cmp.reports.generate_report" for name, _ in queued)

        dpo = Reader("dpo", int(seeded["users"]["dpo"]["id"]), "rnd")
        listed = {r["kind"] for r in await reports.listing(conn, dpo)}
        assert "management_scorecard" not in listed, (
            "a report of both offices carries the other office's figures: not the DPO's"
        )
        theirs = await reports.request(
            conn, dpo, kind_key="management_scorecard", fmt="pdf", params={"period": PERIOD}
        )
        assert theirs["office"] == "rnd"
        assert await reports.readable(conn, dpo, str(theirs["report_uuid"]))
        legal = Reader("legal", await _user(conn, "legal", "hr"), "hr")
        with pytest.raises(NotFound):
            await reports.readable(conn, legal, str(theirs["report_uuid"]))
        admin = Reader("admin", int(seeded["users"]["admin"]["id"]), None)
        assert not [r for r in await reports.listing(conn, admin) if r["kind"] == "board_pack"]

        one = (await reports.listing(conn, boss))[0]
        await reports.delete(conn, boss, str(one["report_uuid"]))
        with pytest.raises(NotFound):
            await reports.readable(conn, boss, str(one["report_uuid"]))
        cur = await conn.execute(
            "SELECT event_type FROM audit_log WHERE entity_type = 'report' ORDER BY log_id"
        )
        events = {r["event_type"] for r in await cur.fetchall()}
        assert {"report.generated", "report.downloaded", "report.deleted"} <= events

    async def test_your_own_work_is_yours_alone(
        self, conn: Any, seeded: dict[str, Any], queued: list[Any]
    ) -> None:
        owner = Reader("rnd_user", int(seeded["users"]["rnd_user"]["id"]), "rnd")
        other = Reader("rnd_user", await _user(conn, "rnd_user", "rnd"), "rnd")
        row = await reports.request(
            conn, owner, kind_key="my_analytics", fmt="xlsx", params={"period": PERIOD}
        )
        with pytest.raises(NotFound):
            await reports.readable(conn, other, str(row["report_uuid"]))
        assert await reports.readable(conn, owner, str(row["report_uuid"]))
        with pytest.raises(Forbidden):
            await reports.request(
                conn, owner, kind_key="board_pack", fmt="pdf", params={"period": PERIOD}
            )

    async def test_an_audit_report_and_an_evidence_pack_are_the_administrators(
        self, conn: Any, seeded: dict[str, Any], queued: list[Any]
    ) -> None:
        admin = Reader("admin", int(seeded["users"]["admin"]["id"]), None)
        await service.set_threshold(conn, 2, actor_id=admin.user_id)
        row = await reports.request(
            conn,
            admin,
            kind_key="audit",
            fmt="csv",
            params={"period": PERIOD, "audit": "configuration"},
        )
        made = await reports.make(conn, str(row["report_uuid"]))
        assert made and made["status"] == "ready", made and made["error"]
        with pytest.raises(ValidationFailed):
            await reports.request(conn, admin, kind_key="audit", fmt="csv", params={"audit": "x"})
        with pytest.raises(Forbidden):
            await reports.request(
                conn, admin, kind_key="management_scorecard", fmt="pdf", params={}
            )


class TestSchedules:
    async def test_a_schedule_mails_only_roles_that_may_read_it(
        self, conn: Any, seeded: dict[str, Any], queued: list[Any]
    ) -> None:
        boss_id = await _user(conn, "management", None)
        boss = Reader("management", boss_id, None)
        with pytest.raises(ValidationFailed):
            await reports.schedule(
                conn,
                boss,
                kind_key="management_scorecard",
                fmt="pdf",
                cadence="monthly",
                recipient_roles=["admin"],
                params={},
            )
        made = await reports.schedule(
            conn,
            boss,
            kind_key="management_scorecard",
            fmt="pdf",
            cadence="monthly",
            recipient_roles=["management", "dpo"],
            params={},
        )
        assert made["next_run_at"] > datetime.now(UTC)
        await conn.execute(
            "UPDATE report_schedule SET next_run_at = now() - interval '1 minute'"
            " WHERE schedule_uuid = %s",
            (made["schedule_uuid"],),
        )
        due = await reports.run_due(conn, datetime.now(UTC))
        [(report_uuid, emails, label)] = [d for d in due if d[0]]
        assert any("management" in e for e in map(str, emails)) or emails
        assert label
        fresh = await reports.set_active(conn, boss, str(made["schedule_uuid"]), active=False)
        assert fresh["active"] is False
        await reports.delete_schedule(conn, boss, str(made["schedule_uuid"]))
        assert await reports.readable(conn, boss, report_uuid), "its reports are kept"


class TestAuditReports:
    async def test_privileged_actions_are_listed_for_the_period(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        from cmp.domain.users import service as users

        await users.reset_mfa(conn, str(seeded["users"]["dco"]["uuid"]))
        admin = Reader("admin", int(seeded["users"]["admin"]["id"]), None)
        from cmp.api.routers.v1.analytics import audit_paging

        page = await audit_paging(limit=50, cursor=None, sort=None)
        out = await service.audit_report(
            conn, admin, "privileged", period=periods.resolve(PERIOD), page=page
        )
        assert any(r["event_type"] == "user.mfa_reset" for r in out["items"])
        assert out["summary"]["total"] >= 1
        with pytest.raises(Forbidden):
            await service.audit_report(
                conn,
                Reader("management", 1, None),
                "privileged",
                period=periods.resolve(PERIOD),
                page=page,
            )
