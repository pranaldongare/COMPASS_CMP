"""Every office-bearing table has its policy, and nothing else hides one.

A table that arrives later holding an office's rows - a column of its own, or
a key to a table that has one - must arrive with its `office_isolation`
policy, or the wall has a door nobody drew. The policies are a list in
migration 0051; this test reads PostgreSQL's catalogue rather than that list,
so a policy dropped by hand fails it too (ADR 0032,
`docs/architecture/offices-and-tenancy.md`).

The assertion runs both ways, as the enum parity test does: a policed table
the page does not name is a wall nobody knows is there.
"""

from __future__ import annotations

from typing import Any

import pytest

pytestmark = pytest.mark.integration

#: The tables that name their office (`office_id`), as the architecture page
#: lists them. `auth_user` names the office an account works in and is not
#: policed: one person, both tracks.
OWN = {
    "project",
    "purpose",
    "notice_template",
    "notice",
    "consent_link",
    "export_log",
    "breach",
    "rights_request",
    "hr_category",
}

#: The children, policed through their parent.
CHILDREN = {
    "consent_artefact",
    "consent_purpose_grant",
    "export_line",
    "notice_language",
    "notice_purpose",
    "notice_template_language",
    "notice_template_purpose",
    "project_site",
    "project_processor",
    "project_approval",
    "project_status_history",
    "import_batch",
    "collection",
    "data_asset",
    "asset_consent",
    "rights_request_holder",
    "rights_request_item",
    "rights_item_execution",
    "rights_ticket_message",
    "rights_response_file",
    "rights_request_attachment",
    "breach_affected",
    "breach_affected_revision",
    "breach_assessment",
    "breach_attachment",
    "breach_contact",
    "breach_determination",
    "breach_notice",
    "breach_notice_delivery",
    "breach_obligation",
    "breach_obligation_event",
    "breach_recording",
    "breach_status_history",
    "breach_ticket",
    "breach_ticket_event",
    "breach_ticket_message",
    "breach_upload",
    "category_processor",
    "hr_poc_category",
    "template_version",
    "template_version_language",
    "template_version_purpose",
}

#: Tables with a key to a policed table that are deliberately not policed,
#: each with its reason. A new one goes here only with a reason.
NOT_POLICED = {
    # One person, both tracks: an account is nobody's office's.
    "auth_user": "registered_via_link_id names the link a sign-up came from; the account is hers",
    # Scoped through its request or asset in the query; a hold on a person is
    # no office's.
    "legal_hold": "asset_id; a hold on a person belongs to no office",
    # A breach-only login is the account's, ended by the administrator.
    "breach_temporary_access": "the grant of a login, read by the account and the administrator",
    # The registry is shared (offices-and-tenancy.md): a source belongs to a
    # processor; `site_id` is the site it was first registered for.
    "data_source": "site_id; the registry of sources is shared by both offices",
    # A nomination is the principal's, on both tracks; `invoked_request_id` is
    # the request that used it.
    "nomination": "invoked_request_id; a nominee acts for the person, not for an office",
}


async def _policed(conn: Any) -> set[str]:
    cur = await conn.execute(
        """SELECT tablename FROM pg_policies
            WHERE schemaname = 'public' AND policyname = 'office_isolation'"""
    )
    return {r["tablename"] for r in await cur.fetchall()}


async def test_the_policed_tables_are_exactly_the_listed_ones(conn: Any) -> None:
    policed = await _policed(conn)
    expected = OWN | CHILDREN
    assert not expected - policed, f"tables without their policy: {sorted(expected - policed)}"
    assert not policed - expected, (
        f"policed but not listed here or on the page: {sorted(policed - expected)}"
    )


async def test_every_policed_table_forces_its_policy(conn: Any) -> None:
    """Without FORCE the table owner - which the migrations and the seed run
    as - would read through the wall."""
    cur = await conn.execute(
        """SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r'
              AND c.relname = ANY(%s)
              AND NOT (c.relrowsecurity AND c.relforcerowsecurity)""",
        (sorted(OWN | CHILDREN),),
    )
    loose = [r["relname"] for r in await cur.fetchall()]
    assert not loose, f"policy not enabled and forced on: {loose}"


async def test_every_table_with_an_office_is_policed(conn: Any) -> None:
    cur = await conn.execute(
        """SELECT table_name FROM information_schema.columns
            WHERE table_schema = 'public' AND column_name = 'office_id'
              AND table_name NOT IN ('office', 'auth_user')"""
    )
    with_office = {r["table_name"] for r in await cur.fetchall()}
    assert with_office == OWN, f"office-bearing but not listed: {sorted(with_office - OWN)}"


async def test_every_table_keyed_to_a_policed_one_is_policed_or_says_why(conn: Any) -> None:
    """A row hanging off a policed row is that office's too. A new table that
    references one must be policed through it, or be named above with why not."""
    cur = await conn.execute(
        """SELECT DISTINCT child.relname AS child, parent.relname AS parent
             FROM pg_constraint con
             JOIN pg_class child ON child.oid = con.conrelid
             JOIN pg_class parent ON parent.oid = con.confrelid
             JOIN pg_namespace n ON n.oid = child.relnamespace
            WHERE con.contype = 'f' AND n.nspname = 'public'"""
    )
    policed = OWN | CHILDREN
    loose = sorted(
        f"{r['child']} -> {r['parent']}"
        for r in await cur.fetchall()
        if r["parent"] in policed and r["child"] not in policed and r["child"] not in NOT_POLICED
    )
    assert not loose, f"references a policed table but is not policed: {loose}"


async def test_the_current_consent_view_reads_as_its_caller(conn: Any) -> None:
    cur = await conn.execute("SELECT reloptions FROM pg_class WHERE relname = 'v_current_consent'")
    row = await cur.fetchone()
    assert row is not None
    assert "security_invoker=true" in (row["reloptions"] or [])
