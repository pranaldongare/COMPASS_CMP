"""The wall between the offices (ADR 0032), proved in SQL.

Every query the application sends already carries its scope; these tests
skip the application and ask PostgreSQL directly, because the policies are
the backstop for the query that one day forgets. A connection set to one
office reads none of the other's rows and cannot write one; a connection that
says nothing reads nothing; `all` reads everything; the view and the shared
intake behave.

No policy binds a superuser, and the suite connects as one locally, so each
test acts as a role of its own - created inside the test's transaction and
rolled back with it - that holds the application's privileges and nothing
more. The rows the tests read are the test's own: one small world per office,
built as the owner before the role is assumed.
"""

from __future__ import annotations

import uuid
from typing import Any

import psycopg
import pytest

from cmp.core.security import content_hash

pytestmark = pytest.mark.integration

#: The key of each table the worlds below write a row into.
KEYS: dict[str, str] = {
    "project": "project_id",
    "project_site": "site_id",
    "purpose": "purpose_id",
    "notice_template": "template_id",
    "notice": "notice_id",
    "notice_language": "notice_language_id",
    "notice_purpose": "notice_purpose_id",
    "consent_link": "link_id",
    "consent_artefact": "consent_id",
    "consent_purpose_grant": "grant_id",
    "export_log": "export_id",
    "export_line": "line_id",
    "breach": "breach_id",
    "breach_status_history": "history_id",
    "rights_request": "request_id",
    # The Legal office's registry (0052): a category names its office; its
    # processors and HR PoCs are policed through it.
    "hr_category": "category_id",
    "category_processor": "category_processor_id",
    "hr_poc_category": "assignment_id",
}

#: The tables that carry the office themselves.
OWN = (
    "project",
    "purpose",
    "notice_template",
    "notice",
    "consent_link",
    "export_log",
    "breach",
    "rights_request",
    "hr_category",
)


async def _one(conn: Any, sql: str, params: Any = ()) -> dict[str, Any]:
    cur = await conn.execute(sql, params)
    row = await cur.fetchone()
    assert row is not None
    return dict(row)


async def _world(conn: Any, seeded: dict[str, Any], office: str) -> dict[str, int]:
    """A project with its notice, link, consent and export, a purpose, a
    template, a breach and a request, all of `office`. Written as the owner."""
    tag = f"{office}-{uuid.uuid4().hex[:8]}"
    users = seeded["users"]
    o = "(SELECT office_id FROM office WHERE office_code = %(office)s)"
    p = {"office": office, "tag": tag, "dpo": users["dpo"]["id"], "rnd": users["rnd_user"]["id"]}
    ids: dict[str, int] = {}

    # A Legal office project is an activity: an approved version of a
    # template in its category (0053). Written ahead, for the project only.
    p["activity_category"] = p["activity_version"] = None
    if office != "rnd":
        p["activity_category"] = (
            await _one(
                conn,
                f"""INSERT INTO hr_category (category_code, name, office_id, created_by)
                    VALUES (upper(replace('A_' || %(tag)s, '-', '_')), 'Activity', {o}, %(dpo)s)
                    RETURNING category_id""",
                p,
            )
        )["category_id"]
        activity_template = (
            await _one(
                conn,
                f"""INSERT INTO notice_template (title, withdraw_url, exercise_rights_url,
                                                 board_complaint_url, dpo_contact, created_by,
                                                 office_id, category_id)
                    VALUES ('Activity ' || %(tag)s, 'https://x/w', 'https://x/r',
                            'https://dpb.gov.in', 'office@test.local', %(dpo)s, {o},
                            %(activity_category)s)
                    RETURNING template_id""",
                p,
            )
        )["template_id"]
        p["activity_version"] = (
            await _one(
                conn,
                """INSERT INTO template_version (template_id, version, status, created_by,
                                                 withdraw_url, exercise_rights_url,
                                                 board_complaint_url, dpo_contact,
                                                 applicable_to, approved_by, approved_at)
                   VALUES (%(template)s, 1, 'approved', %(dpo)s, 'https://x/w', 'https://x/r',
                           'https://dpb.gov.in', 'office@test.local', 'data_subject',
                           %(dpo)s, now())
                   RETURNING version_id""",
                {**p, "template": activity_template},
            )
        )["version_id"]

    ids["project"] = (
        await _one(
            conn,
            f"""INSERT INTO project (project_name, description, created_by, project_status,
                                     office_id, category_id, template_version_id)
                VALUES ('Wall ' || %(tag)s, 'd', %(rnd)s, 'approved', {o},
                        %(activity_category)s, %(activity_version)s)
                RETURNING project_id""",
            p,
        )
    )["project_id"]
    p["project"] = ids["project"]
    p["processor"] = seeded["processors"]["external"]["processor_id"]
    ids["project_site"] = (
        await _one(
            conn,
            """INSERT INTO project_site (project_id, site_label, location, processor_id)
               VALUES (%(project)s, 'Site', 'Pune', %(processor)s) RETURNING site_id""",
            p,
        )
    )["site_id"]
    p["site"] = ids["project_site"]
    ids["purpose"] = (
        await _one(
            conn,
            f"""INSERT INTO purpose (purpose_code, name, description, uses, lawful_basis,
                                     data_categories, retention_period, retention_basis,
                                     erasure_trigger, status, created_by, office_id)
                VALUES ('P-' || %(tag)s, 'Purpose', 'd', 'u', 'consent_s6', ARRAY['name'],
                        interval '1 year', 'business_policy', 'withdrawal', 'active', %(dpo)s,
                        {o})
                RETURNING purpose_id""",
            p,
        )
    )["purpose_id"]
    p["purpose"] = ids["purpose"]
    # A category in each office: the schema allows one anywhere, and only a
    # template of the Legal office names one (0052).
    ids["hr_category"] = (
        await _one(
            conn,
            f"""INSERT INTO hr_category (category_code, name, office_id, created_by)
                VALUES (upper(replace('C_' || %(tag)s, '-', '_')), 'Category', {o}, %(dpo)s)
                RETURNING category_id""",
            p,
        )
    )["category_id"]
    p["category"] = ids["hr_category"]
    ids["category_processor"] = (
        await _one(
            conn,
            """INSERT INTO category_processor (category_id, processor_id, processor_role,
                                               added_by)
               VALUES (%(category)s, %(processor)s, 'vendor', %(dpo)s)
               RETURNING category_processor_id""",
            p,
        )
    )["category_processor_id"]
    ids["hr_poc_category"] = (
        await _one(
            conn,
            """INSERT INTO hr_poc_category (user_id, category_id, assigned_by)
               VALUES (%(rnd)s, %(category)s, %(dpo)s) RETURNING assignment_id""",
            p,
        )
    )["assignment_id"]
    p["template_category"] = None if office == "rnd" else ids["hr_category"]
    ids["notice_template"] = (
        await _one(
            conn,
            f"""INSERT INTO notice_template (title, withdraw_url, exercise_rights_url,
                                             board_complaint_url, dpo_contact, created_by,
                                             office_id, category_id)
                VALUES ('Template ' || %(tag)s, 'https://x/w', 'https://x/r',
                        'https://dpb.gov.in', 'office@test.local', %(dpo)s, {o},
                        %(template_category)s)
                RETURNING template_id""",
            p,
        )
    )["template_id"]
    # No office given: the trigger takes the project's.
    ids["notice"] = (
        await _one(
            conn,
            """INSERT INTO notice (notice_code, project_id, version, withdraw_url,
                                   exercise_rights_url, board_complaint_url, dpo_contact)
               VALUES ('N-' || %(tag)s, %(project)s, 1, 'https://x/w', 'https://x/r',
                       'https://dpb.gov.in', 'office@test.local')
               RETURNING notice_id""",
            p,
        )
    )["notice_id"]
    p["notice"] = ids["notice"]
    p["text"] = f"Notice text {tag}"
    p["hash"] = content_hash(p["text"])
    ids["notice_language"] = (
        await _one(
            conn,
            """INSERT INTO notice_language (notice_id, language_code, rendered_text,
                                            content_hash, created_by, approved_by, approved_at)
               VALUES (%(notice)s, 'english', %(text)s, %(hash)s, %(dpo)s, %(dpo)s, now())
               RETURNING notice_language_id""",
            p,
        )
    )["notice_language_id"]
    p["language"] = ids["notice_language"]
    ids["notice_purpose"] = (
        await _one(
            conn,
            """INSERT INTO notice_purpose (notice_id, purpose_id)
               VALUES (%(notice)s, %(purpose)s) RETURNING notice_purpose_id""",
            p,
        )
    )["notice_purpose_id"]
    await conn.execute(
        """UPDATE notice SET status = 'published', recipients_text = 'Site',
                  approved_by = %(dpo)s, published_at = now()
            WHERE notice_id = %(notice)s""",
        p,
    )
    ids["consent_link"] = (
        await _one(
            conn,
            """INSERT INTO consent_link (notice_id, site_id, token, expires_at, created_by)
               VALUES (%(notice)s, %(site)s, 'wall-' || %(tag)s, now() + interval '7 days',
                       %(dpo)s)
               RETURNING link_id""",
            p,
        )
    )["link_id"]
    p["link"] = ids["consent_link"]
    p["subject"] = seeded["subject"]["id"]
    ids["consent_artefact"] = (
        await _one(
            conn,
            """INSERT INTO consent_artefact
                 (auth_user_id, notice_id, notice_language_id, notice_content_hash,
                  link_id, served_at, affirmative_action_at, action_type)
               VALUES (%(subject)s, %(notice)s, %(language)s, %(hash)s, %(link)s,
                       now() - interval '1 minute', now(), 'checkbox_click')
               RETURNING consent_id""",
            p,
        )
    )["consent_id"]
    p["consent"] = ids["consent_artefact"]
    ids["consent_purpose_grant"] = (
        await _one(
            conn,
            """INSERT INTO consent_purpose_grant (consent_id, purpose_id, granted)
               VALUES (%(consent)s, %(purpose)s, true) RETURNING grant_id""",
            p,
        )
    )["grant_id"]
    ids["export_log"] = (
        await _one(
            conn,
            """INSERT INTO export_log (project_id, site_id, export_type, exported_by, row_count,
                                       file_hash)
               VALUES (%(project)s, %(site)s, 'project_export', %(dpo)s, 1, 'feed')
               RETURNING export_id""",
            p,
        )
    )["export_id"]
    p["export"] = ids["export_log"]
    ids["export_line"] = (
        await _one(
            conn,
            """INSERT INTO export_line (export_id, auth_user_id, consent_id)
               VALUES (%(export)s, %(subject)s, %(consent)s) RETURNING line_id""",
            p,
        )
    )["line_id"]
    ids["breach"] = (
        await _one(
            conn,
            f"""INSERT INTO breach (reference, title, detected_at, location_kind, recorded_by,
                                    office_id)
                VALUES ('INC-' || %(tag)s, 'SE::wall', now(), 'platform', %(dpo)s, {o})
                RETURNING breach_id""",
            p,
        )
    )["breach_id"]
    p["breach"] = ids["breach"]
    ids["breach_status_history"] = (
        await _one(
            conn,
            """INSERT INTO breach_status_history (breach_id, to_status, changed_by)
               VALUES (%(breach)s, 'open', %(dpo)s) RETURNING history_id""",
            p,
        )
    )["history_id"]
    ids["rights_request"] = await _request(conn, office=office, tag=tag)
    return ids


async def _request(conn: Any, *, office: str | None, tag: str) -> int:
    row = await _one(
        conn,
        """INSERT INTO rights_request (reference, request_type, channel, submitted_contact,
                                       submitted_contact_hash, request_text, due_at, office_id)
           VALUES ('RR-' || %s, 'access', 'public_form', 'SE::contact', 'h-' || %s, 'SE::text',
                   now() + interval '30 days',
                   (SELECT office_id FROM office WHERE office_code = %s))
           RETURNING request_id""",
        (tag, tag, office),
    )
    return int(row["request_id"])


@pytest.fixture
async def worlds(conn: Any, seeded: dict[str, Any]) -> dict[str, dict[str, int]]:
    return {"rnd": await _world(conn, seeded, "rnd"), "hr": await _world(conn, seeded, "hr")}


@pytest.fixture
async def probe(conn: Any) -> str:
    """A role the policies bind: the application's privileges, no superuser,
    no BYPASSRLS. Gone with the test's transaction."""
    name = f"cmp_office_probe_{uuid.uuid4().hex[:12]}"
    await conn.execute(f"CREATE ROLE {name} NOLOGIN NOSUPERUSER NOBYPASSRLS")
    await conn.execute(f"GRANT USAGE ON SCHEMA public TO {name}")
    await conn.execute(f"GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO {name}")
    await conn.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {name}")
    return name


async def _as(conn: Any, role: str, office: str | None) -> None:
    """From here to the next `_owner`, act as `role` in `office`; None resets
    the setting, as a connection that never set one."""
    await conn.execute(f"SET LOCAL ROLE {role}")
    if office is None:
        await conn.execute("RESET app.office")
    else:
        await conn.execute("SELECT set_config('app.office', %s, true)", (office,))


async def _owner(conn: Any) -> None:
    await conn.execute("RESET ROLE")
    await conn.execute("SELECT set_config('app.office', 'all', true)")


async def _visible(conn: Any, table: str) -> set[int]:
    key = KEYS[table]
    cur = await conn.execute(f"SELECT {key} AS k FROM {table}")
    return {int(r["k"]) for r in await cur.fetchall()}


class TestTheRoleIsOneThePoliciesBind:
    async def test_the_probe_is_neither_superuser_nor_bypasser(self, conn: Any, probe: str) -> None:
        """Every test below would pass vacuously for a role the policies skip."""
        await _as(conn, probe, "hr")
        row = await _one(
            conn,
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user",
        )
        assert row == {"rolsuper": False, "rolbypassrls": False}


class TestAnOfficeReadsItsOwnRows:
    @pytest.mark.parametrize("table", sorted(KEYS))
    @pytest.mark.parametrize(("mine", "theirs"), [("hr", "rnd"), ("rnd", "hr")])
    async def test_its_rows_and_none_of_the_other_office(
        self,
        conn: Any,
        worlds: dict[str, dict[str, int]],
        probe: str,
        table: str,
        mine: str,
        theirs: str,
    ) -> None:
        await _as(conn, probe, mine)
        seen = await _visible(conn, table)
        assert worlds[mine][table] in seen, f"{mine} cannot read its own {table}"
        assert worlds[theirs][table] not in seen, f"{mine} reads {theirs}'s {table}"

    @pytest.mark.parametrize("table", OWN)
    @pytest.mark.parametrize(("mine", "theirs"), [("hr", "rnd"), ("rnd", "hr")])
    async def test_no_row_of_the_other_office_anywhere(
        self,
        conn: Any,
        worlds: dict[str, dict[str, int]],
        probe: str,
        table: str,
        mine: str,
        theirs: str,
    ) -> None:
        """Across the whole database, not only this test's rows: the seeded
        development data is the DPO office's, and none of it reaches `hr`."""
        await _as(conn, probe, mine)
        row = await _one(
            conn,
            f"""SELECT count(*) AS n FROM {table}
                 WHERE office_id = (SELECT office_id FROM office WHERE office_code = %s)""",
            (theirs,),
        )
        assert row["n"] == 0

    @pytest.mark.parametrize("table", sorted(KEYS))
    async def test_all_reads_both(
        self, conn: Any, worlds: dict[str, dict[str, int]], probe: str, table: str
    ) -> None:
        await _as(conn, probe, "all")
        seen = await _visible(conn, table)
        assert {worlds["rnd"][table], worlds["hr"][table]} <= seen


class TestSayingNothingReadsNothing:
    @pytest.mark.parametrize("table", sorted(KEYS))
    @pytest.mark.parametrize("setting", [None, ""], ids=["unset", "empty"])
    async def test_no_office_reads_no_row(
        self,
        conn: Any,
        worlds: dict[str, dict[str, int]],
        probe: str,
        table: str,
        setting: str | None,
    ) -> None:
        """Deny by default: a connection that bypassed the pool, or a bug that
        cleared the setting, sees an empty register rather than both."""
        await _as(conn, probe, setting)
        assert await _visible(conn, table) == set()

    async def test_an_unknown_office_reads_no_row(
        self, conn: Any, worlds: dict[str, dict[str, int]], probe: str
    ) -> None:
        await _as(conn, probe, "nowhere")
        assert await _visible(conn, "project") == set()


class TestWritingIntoTheOtherOffice:
    async def test_a_record_of_the_other_office_is_refused(
        self, conn: Any, seeded: dict[str, Any], probe: str
    ) -> None:
        await _as(conn, probe, "hr")
        with pytest.raises(psycopg.errors.InsufficientPrivilege) as refused:
            await conn.execute(
                """INSERT INTO project (project_name, description, created_by, office_id)
                   VALUES ('Smuggled', 'd', %s,
                           (SELECT office_id FROM office WHERE office_code = 'rnd'))""",
                (seeded["users"]["rnd_user"]["id"],),
            )
        assert "row-level security" in str(refused.value)

    async def test_the_reverse_is_refused_too(
        self, conn: Any, seeded: dict[str, Any], probe: str
    ) -> None:
        await _as(conn, probe, "rnd")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            await conn.execute(
                """INSERT INTO breach (reference, title, detected_at, location_kind, recorded_by,
                                       office_id)
                   VALUES ('INC-SMUGGLED', 'SE::x', now(), 'platform', %s,
                           (SELECT office_id FROM office WHERE office_code = 'hr'))""",
                (seeded["users"]["dpo"]["id"],),
            )

    async def test_a_child_cannot_be_hung_on_a_parent_it_cannot_see(
        self, conn: Any, worlds: dict[str, dict[str, int]], seeded: dict[str, Any], probe: str
    ) -> None:
        await _as(conn, probe, "hr")
        with pytest.raises(psycopg.errors.InsufficientPrivilege) as refused:
            await conn.execute(
                "INSERT INTO export_line (export_id, auth_user_id, consent_id) VALUES (%s, %s, %s)",
                (
                    worlds["rnd"]["export_log"],
                    seeded["subject"]["id"],
                    worlds["hr"]["consent_artefact"],
                ),
            )
        assert "row-level security" in str(refused.value)

    async def test_an_update_reaches_no_row_of_the_other_office(
        self, conn: Any, worlds: dict[str, dict[str, int]], probe: str
    ) -> None:
        await _as(conn, probe, "hr")
        cur = await conn.execute(
            "UPDATE project SET description = 'reached' WHERE project_id = %s",
            (worlds["rnd"]["project"],),
        )
        assert cur.rowcount == 0

    async def test_a_record_cannot_be_moved_to_the_other_office(
        self, conn: Any, worlds: dict[str, dict[str, int]], probe: str
    ) -> None:
        """Even by a connection that reads both: a record's office is fixed."""
        await _as(conn, probe, "all")
        with pytest.raises(psycopg.errors.RestrictViolation):
            await conn.execute(
                """UPDATE project SET office_id = (SELECT office_id FROM office
                                                    WHERE office_code = 'hr')
                    WHERE project_id = %s""",
                (worlds["rnd"]["project"],),
            )


class TestTheOfficeComesFromTheParent:
    async def test_a_link_takes_its_notice_office(
        self, conn: Any, worlds: dict[str, dict[str, int]]
    ) -> None:
        row = await _one(
            conn,
            """SELECT o.office_code FROM consent_link l JOIN office o USING (office_id)
                WHERE l.link_id = %s""",
            (worlds["hr"]["consent_link"],),
        )
        assert row["office_code"] == "hr"

    async def test_an_office_that_disagrees_with_the_parent_is_refused(
        self, conn: Any, worlds: dict[str, dict[str, int]], seeded: dict[str, Any]
    ) -> None:
        with pytest.raises(psycopg.errors.CheckViolation):
            await conn.execute(
                """INSERT INTO export_log (project_id, export_type, exported_by, row_count,
                                           file_hash, office_id)
                   VALUES (%s, 'project_export', %s, 0, 'feed',
                           (SELECT office_id FROM office WHERE office_code = 'rnd'))""",
                (worlds["hr"]["project"], seeded["users"]["dpo"]["id"]),
            )


class TestTheViewAndTheIntake:
    @pytest.mark.parametrize(("mine", "theirs"), [("hr", "rnd"), ("rnd", "hr")])
    async def test_the_current_consent_view_honours_the_setting(
        self, conn: Any, worlds: dict[str, dict[str, int]], probe: str, mine: str, theirs: str
    ) -> None:
        """Without `security_invoker` the view would read as its owner, and
        through the wall."""
        await _as(conn, probe, mine)
        cur = await conn.execute("SELECT consent_id FROM v_current_consent")
        seen = {int(r["consent_id"]) for r in await cur.fetchall()}
        assert worlds[mine]["consent_artefact"] in seen
        assert worlds[theirs]["consent_artefact"] not in seen

    @pytest.mark.parametrize("office", ["hr", "rnd"])
    async def test_the_shared_intake_is_visible_to_both_offices(
        self, conn: Any, worlds: dict[str, dict[str, int]], probe: str, office: str
    ) -> None:
        unrouted = await _request(conn, office=None, tag=f"intake-{uuid.uuid4().hex[:8]}")
        await _as(conn, probe, office)
        assert unrouted in await _visible(conn, "rights_request")

    @pytest.mark.parametrize("setting", [None, "", "nowhere"], ids=["unset", "empty", "unknown"])
    async def test_the_shared_intake_is_not_visible_to_no_office(
        self, conn: Any, worlds: dict[str, dict[str, int]], probe: str, setting: str | None
    ) -> None:
        """An office's session sees the intake; a connection that names none
        sees nothing, the intake included (0056)."""
        unrouted = await _request(conn, office=None, tag=f"intake-{uuid.uuid4().hex[:8]}")
        await _as(conn, probe, setting)
        assert unrouted not in await _visible(conn, "rights_request")


class TestThePoolSetsTheOffice:
    """The application's half: the setting the policies read is the one the
    request context names, and it goes with the connection's return."""

    async def test_a_connection_reads_in_the_context_office(self, db_pool: Any) -> None:
        from cmp.core.context import RequestContext, use_context
        from cmp.db.pool import connection, transaction

        with use_context(RequestContext(request_id="t", office="hr")):
            async with connection() as c:
                cur = await c.execute("SELECT current_setting('app.office', true) AS o")
                assert (await cur.fetchone())["o"] == "hr"
            async with transaction() as c:
                cur = await c.execute("SELECT current_setting('app.office', true) AS o")
                assert (await cur.fetchone())["o"] == "hr"

    async def test_no_office_in_the_context_reads_across_both(self, db_pool: Any) -> None:
        from cmp.core.context import RequestContext, use_context
        from cmp.db.pool import connection

        with use_context(RequestContext(request_id="t")):
            async with connection() as c:
                cur = await c.execute("SELECT current_setting('app.office', true) AS o")
                assert (await cur.fetchone())["o"] == "all"

    async def test_forgetting_the_office_clears_it(self, db_pool: Any) -> None:
        from cmp.db.pool import _forget_office

        async with db_pool.connection() as c:
            await c.set_autocommit(True)
            await c.execute("SELECT set_config('app.office', 'hr', false)")
            await _forget_office(c)
            cur = await c.execute("SELECT current_setting('app.office', true) AS o")
            assert (await cur.fetchone())["o"] in ("", None)

    @pytest.mark.parametrize("unit", ["connection", "transaction"])
    @pytest.mark.parametrize("fails", [False, True], ids=["clean", "raising"])
    async def test_every_connection_forgets_its_office_on_the_way_back(
        self, db_pool: Any, monkeypatch: Any, unit: str, fails: bool
    ) -> None:
        """Whether the body finished or raised: a connection that went back
        holding `hr` would be read by the next request as the Legal office's."""
        from cmp.core.context import RequestContext, use_context
        from cmp.db import pool

        forgotten: list[Any] = []
        real = pool._forget_office

        async def spy(c: Any) -> None:
            forgotten.append(c)
            await real(c)

        monkeypatch.setattr(pool, "_forget_office", spy)
        used: list[Any] = []
        with use_context(RequestContext(request_id="t", office="hr")):
            try:
                async with getattr(pool, unit)() as c:
                    used.append(c)
                    if fails:
                        raise RuntimeError("the body failed")
            except RuntimeError:
                assert fails
        assert forgotten == used
