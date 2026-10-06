"""The breach register (S3-01): the breach, its determinations, assessments and duties.

Everything below `breach` is append-only by trigger and grant, and `breach`
itself changes only its status, so this module has one UPDATE and it moves a
status. A revision is an INSERT and the latest row is current.

Every narrative field is sealed here, at the write, like every other reason the
office writes; the rows served carry ciphertext and the console opens it.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from psycopg.types.json import Jsonb

from cmp.db.sql import Conn, fetch_all, fetch_one
from cmp.infrastructure.dkms import seal

Row = dict[str, Any]

#: `reference` is what the record is quoted by: the breach reference once it is
#: recorded as a breach, the incident's until then. Both are carried apart.
_BREACH = """
  b.breach_id, b.breach_uuid, coalesce(rec.reference, b.reference) AS reference,
  b.reference AS incident_reference, rec.reference AS breach_reference,
  rec.recorded_at AS breach_recorded_at, rbb.full_name AS breach_recorded_by_name,
  b.title, b.detected_at, b.began_at,
  b.location_kind, b.location_detail, b.status, b.recorded_at,
  pr.processor_uuid AS location_processor_uuid, pr.legal_name AS location_processor_name,
  ds.source_uuid AS location_source_uuid, ds.name AS location_source_name,
  rb.full_name AS recorded_by_name
  FROM breach b
  LEFT JOIN breach_recording rec ON rec.breach_id = b.breach_id
  LEFT JOIN auth_user rbb        ON rbb.id = rec.recorded_by
  LEFT JOIN processor pr         ON pr.processor_id = b.location_processor_id
  LEFT JOIN data_source ds       ON ds.source_id = b.location_source_id
  JOIN auth_user rb              ON rb.id = b.recorded_by
"""

ASSESSMENT_TEXT = (
    "nature_extent",
    "likely_impact",
    "consequences",
    "circumstances",
    "mitigation",
    "protective_steps",
    "caused_by_findings",
    "remedial_measures",
    "contact_point",
)


async def create(
    conn: Conn,
    *,
    title: str,
    detected_at: datetime,
    began_at: datetime | None,
    location_kind: str,
    location_processor_id: int | None,
    location_source_id: int | None,
    location_detail: str | None,
    recorded_by: int,
) -> Row:
    sealed = await seal("breach", {"title": title, "location_detail": location_detail})
    row = await fetch_one(
        conn,
        """
        INSERT INTO breach (reference, title, detected_at, began_at, location_kind,
                            location_processor_id, location_source_id, location_detail,
                            recorded_by)
        VALUES ('INC-' || to_char(now(), 'YYYY') || '-'
                  || lpad(nextval('breach_incident_ref_seq')::text, 4, '0'),
                %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING breach_id, breach_uuid
        """,
        (
            sealed["title"],
            detected_at,
            began_at,
            location_kind,
            location_processor_id,
            location_source_id,
            sealed["location_detail"],
            recorded_by,
        ),
    )
    assert row is not None
    return row


async def record_as_breach(
    conn: Conn, breach_id: int, *, determination_id: int, recorded_by: int
) -> Row | None:
    """Issue the breach reference, once. The caller holds the breach row, so a
    second *yes* sees the first one's recording; `ON CONFLICT` is the second
    line, and a number drawn by a losing insert is simply never used."""
    return await fetch_one(
        conn,
        """INSERT INTO breach_recording (breach_id, reference, determination_id, recorded_by)
           VALUES (%s, 'BR-' || to_char(now(), 'YYYY') || '-'
                         || lpad(nextval('breach_ref_seq')::text, 4, '0'),
                   %s, %s)
           ON CONFLICT (breach_id) DO NOTHING
           RETURNING recording_uuid, reference""",
        (breach_id, determination_id, recorded_by),
    )


async def by_uuid(conn: Conn, breach_uuid: str) -> Row | None:
    return await fetch_one(conn, f"SELECT {_BREACH} WHERE b.breach_uuid = %s", (breach_uuid,))


async def by_breach_id(conn: Conn, breach_id: int) -> Row | None:
    return await fetch_one(conn, f"SELECT {_BREACH} WHERE b.breach_id = %s", (breach_id,))


async def lock(conn: Conn, breach_id: int) -> Row:
    """Take the breach row for the rest of the transaction.

    Every write to a breach goes through this first, so two determinations or
    two completions of the same duty are made one after the other and the
    second sees what the first did.
    """
    row = await fetch_one(
        conn, "SELECT breach_id, status FROM breach WHERE breach_id = %s FOR UPDATE", (breach_id,)
    )
    assert row is not None
    return row


async def list_breaches(conn: Conn, *, status: str | None) -> list[Row]:
    where = "WHERE b.status = %s" if status else ""
    params: tuple[Any, ...] = (status,) if status else ()
    return await fetch_all(
        conn,
        f"""SELECT {_BREACH} {where}
            ORDER BY (b.status = 'open') DESC, b.detected_at DESC LIMIT 500""",
        params,
    )


async def set_status(conn: Conn, breach_id: int, *, to: str) -> None:
    await conn.execute("UPDATE breach SET status = %s WHERE breach_id = %s", (to, breach_id))


async def add_status_history(
    conn: Conn,
    breach_id: int,
    *,
    from_status: str | None,
    to_status: str,
    reason: str | None,
    changed_by: int,
) -> None:
    sealed = await seal("breach_status_history", {"reason": reason})
    await conn.execute(
        """INSERT INTO breach_status_history (breach_id, from_status, to_status, reason, changed_by)
           VALUES (%s, %s, %s, %s, %s)""",
        (breach_id, from_status, to_status, sealed["reason"], changed_by),
    )


async def status_history(conn: Conn, breach_id: int) -> list[Row]:
    return await fetch_all(
        conn,
        """SELECT h.from_status, h.to_status, h.reason, h.changed_at, u.full_name AS changed_by_name
             FROM breach_status_history h JOIN auth_user u ON u.id = h.changed_by
            WHERE h.breach_id = %s ORDER BY h.history_id""",
        (breach_id,),
    )


# ------------------------------------------------------------- determinations


async def add_determination(
    conn: Conn,
    breach_id: int,
    *,
    outcome: str,
    reasoning: str,
    became_aware_at: datetime | None,
    determined_by: int,
) -> Row:
    sealed = await seal("breach_determination", {"reasoning": reasoning})
    row = await fetch_one(
        conn,
        """INSERT INTO breach_determination
             (breach_id, outcome, reasoning, became_aware_at, determined_by)
           VALUES (%s, %s, %s, %s, %s)
           RETURNING determination_id, determination_uuid""",
        (breach_id, outcome, sealed["reasoning"], became_aware_at, determined_by),
    )
    assert row is not None
    return row


async def determinations(conn: Conn, breach_id: int) -> list[Row]:
    """Every determination, oldest first. The last is current."""
    return await fetch_all(
        conn,
        """SELECT d.determination_id, d.determination_uuid, d.outcome, d.reasoning,
                  d.became_aware_at, d.determined_at, u.full_name AS determined_by_name
             FROM breach_determination d JOIN auth_user u ON u.id = d.determined_by
            WHERE d.breach_id = %s ORDER BY d.determination_id""",
        (breach_id,),
    )


async def last_activity(conn: Conn, breach_ids: list[int]) -> dict[int, Any]:
    """When anything last happened to each breach: the newest audit row about
    it, its notices or its tickets. The trail records every write, so it is
    the one place that knows."""
    rows = await fetch_all(
        conn,
        """SELECT x.breach_id, max(a.occurred_at) AS at
             FROM (SELECT breach_id, 'breach' AS entity_type, breach_id AS entity_id
                     FROM breach WHERE breach_id = ANY(%(ids)s)
                   UNION ALL
                   SELECT breach_id, 'breach_notice', notice_id
                     FROM breach_notice WHERE breach_id = ANY(%(ids)s)
                   UNION ALL
                   SELECT breach_id, 'breach_ticket', ticket_id
                     FROM breach_ticket WHERE breach_id = ANY(%(ids)s)) x
             JOIN audit_log a ON a.entity_type = x.entity_type AND a.entity_id = x.entity_id
            GROUP BY x.breach_id""",
        {"ids": breach_ids},
    )
    return {int(r["breach_id"]): r["at"] for r in rows}


async def latest_determinations(conn: Conn, breach_ids: list[int]) -> dict[int, Row]:
    rows = await fetch_all(
        conn,
        """SELECT DISTINCT ON (breach_id) breach_id, outcome, became_aware_at, determined_at
             FROM breach_determination WHERE breach_id = ANY(%s)
            ORDER BY breach_id, determination_id DESC""",
        (breach_ids,),
    )
    return {int(r["breach_id"]): r for r in rows}


# ---------------------------------------------------------------- assessments


async def add_assessment(
    conn: Conn,
    breach_id: int,
    *,
    began_at: datetime | None,
    categories: list[dict[str, Any]],
    text: dict[str, str | None],
    revised_by: int,
) -> Row:
    """The next revision. The breach row is locked by the caller, so the
    revision number cannot be drawn twice."""
    sealed = await seal("breach_assessment", {k: text.get(k) for k in ASSESSMENT_TEXT})
    columns = ", ".join(ASSESSMENT_TEXT)
    placeholders = ", ".join(["%s"] * len(ASSESSMENT_TEXT))
    row = await fetch_one(
        conn,
        f"""INSERT INTO breach_assessment
              (breach_id, revision, began_at, categories, {columns}, revised_by)
            VALUES (%s,
                    (SELECT coalesce(max(revision), 0) + 1 FROM breach_assessment
                      WHERE breach_id = %s),
                    %s, %s, {placeholders}, %s)
            RETURNING assessment_id, assessment_uuid, revision""",
        (
            breach_id,
            breach_id,
            began_at,
            Jsonb(categories),
            *(sealed[k] for k in ASSESSMENT_TEXT),
            revised_by,
        ),
    )
    assert row is not None
    return row


async def assessments(conn: Conn, breach_id: int) -> list[Row]:
    """Every revision, newest first."""
    return await fetch_all(
        conn,
        f"""SELECT a.assessment_uuid, a.revision, a.began_at, a.categories,
                   {", ".join("a." + c for c in ASSESSMENT_TEXT)},
                   a.revised_at, u.full_name AS revised_by_name
              FROM breach_assessment a JOIN auth_user u ON u.id = a.revised_by
             WHERE a.breach_id = %s ORDER BY a.revision DESC""",
        (breach_id,),
    )


# ------------------------------------------------------------------ obligations


async def create_obligation(
    conn: Conn,
    breach_id: int,
    *,
    kind: str,
    due_at: datetime | None,
    anchored_at: datetime | None,
    determination_id: int | None,
    created_by: int,
) -> Row:
    row = await fetch_one(
        conn,
        """INSERT INTO breach_obligation
             (breach_id, kind, due_at, anchored_at, determination_id, created_by)
           VALUES (%s, %s, %s, %s, %s, %s)
           RETURNING obligation_id, obligation_uuid""",
        (breach_id, kind, due_at, anchored_at, determination_id, created_by),
    )
    assert row is not None
    return row


async def obligations(conn: Conn, breach_ids: list[int]) -> list[Row]:
    return await fetch_all(
        conn,
        """SELECT o.obligation_id, o.obligation_uuid, o.breach_id, o.kind, o.due_at,
                  o.anchored_at, o.created_at
             FROM breach_obligation o WHERE o.breach_id = ANY(%s)
            ORDER BY o.breach_id, o.obligation_id""",
        (breach_ids,),
    )


async def add_obligation_event(
    conn: Conn,
    obligation_id: int,
    *,
    kind: str,
    recorded_by: int | None,
    occurred_at: datetime | None = None,
    reference: str | None = None,
    note: str | None = None,
    reported_to: str | None = None,
    due_at: datetime | None = None,
    anchored_at: datetime | None = None,
    requested_at: datetime | None = None,
    determination_id: int | None = None,
) -> Row:
    sealed = await seal("breach_obligation_event", {"note": note, "reported_to": reported_to})
    row = await fetch_one(
        conn,
        """INSERT INTO breach_obligation_event
             (obligation_id, kind, occurred_at, reference, note, reported_to, due_at,
              anchored_at, requested_at, determination_id, recorded_by)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           RETURNING event_id, event_uuid""",
        (
            obligation_id,
            kind,
            occurred_at,
            reference,
            sealed["note"],
            sealed["reported_to"],
            due_at,
            anchored_at,
            requested_at,
            determination_id,
            recorded_by,
        ),
    )
    assert row is not None
    return row


async def obligation_events(conn: Conn, obligation_ids: list[int]) -> list[Row]:
    """Every event on these duties, in the order written."""
    return await fetch_all(
        conn,
        """SELECT e.event_uuid, e.obligation_id, e.kind, e.occurred_at, e.reference, e.note,
                  e.reported_to, e.due_at, e.anchored_at, e.requested_at, e.recorded_at,
                  d.determination_uuid, u.full_name AS recorded_by_name
             FROM breach_obligation_event e
             LEFT JOIN breach_determination d ON d.determination_id = e.determination_id
             LEFT JOIN auth_user u ON u.id = e.recorded_by
            WHERE e.obligation_id = ANY(%s) ORDER BY e.event_id""",
        (obligation_ids,),
    )


# ------------------------------------------------------------- who it touched

#: The tables of the platform's own database that hold something about a data
#: principal, each as (the person it is about, when the row was written).
#: A database breach names tables and a window; everyone with a row in one of
#: them written in that window is touched. Hand-kept, like every inventory of
#: personal data here: `tests/integration/test_breach_affected.py` fails when a
#: sealed table is neither listed nor named in `NOT_ABOUT_A_PRINCIPAL`.
PLATFORM_TABLES: dict[str, str] = {
    # Her account: name, contacts, date of birth.
    "auth_user": "SELECT id AS person_id, created_at AS at FROM auth_user",
    "consent_artefact": "SELECT auth_user_id, created_at FROM consent_artefact",
    "asset_consent": """SELECT ca.auth_user_id, ac.created_at FROM asset_consent ac
                        JOIN consent_artefact ca ON ca.consent_id = ac.consent_id""",
    "export_line": """SELECT el.auth_user_id, e.exported_at FROM export_line el
                      JOIN export_log e ON e.export_id = el.export_id""",
    "rights_request": """SELECT subject_user_id, received_at FROM rights_request
                         WHERE subject_user_id IS NOT NULL""",
    # The holder's brief and thread carry her name, contacts and words.
    "rights_request_holder": """SELECT r.subject_user_id, h.created_at
                                FROM rights_request_holder h
                                JOIN rights_request r ON r.request_id = h.request_id
                                WHERE r.subject_user_id IS NOT NULL""",
    "rights_ticket_message": """SELECT r.subject_user_id, m.created_at
                                FROM rights_ticket_message m
                                JOIN rights_request_holder h ON h.holder_id = m.holder_id
                                JOIN rights_request r ON r.request_id = h.request_id
                                WHERE r.subject_user_id IS NOT NULL""",
    "rights_response_file": """SELECT r.subject_user_id, f.created_at FROM rights_response_file f
                               JOIN rights_request r ON r.request_id = f.request_id
                               WHERE r.subject_user_id IS NOT NULL""",
    # Both people in a nomination: the principal, and a nominee with an account.
    "nomination": """SELECT principal_user_id, created_at FROM nomination
                     UNION ALL
                     SELECT nominee_user_id, created_at FROM nomination
                     WHERE nominee_user_id IS NOT NULL""",
    "person_type_history": "SELECT auth_user_id, changed_at FROM person_type_history",
    "legal_hold": """SELECT subject_user_id, placed_at FROM legal_hold
                     WHERE subject_user_id IS NOT NULL""",
    # Staff are data principals too (ADR 0013): a cover arrangement's reason.
    "delegation": """SELECT delegator_user_id, created_at FROM delegation
                     UNION ALL
                     SELECT delegate_user_id, created_at FROM delegation""",
    "audit_log": """SELECT subject_user_id, occurred_at FROM audit_log
                    WHERE subject_user_id IS NOT NULL""",
    # Breach tickets (S3-08): the holder - a member of staff, and staff are
    # data principals too - and what they and the office wrote to each other.
    "breach_ticket": "SELECT holder_user_id, created_at FROM breach_ticket",
    "breach_ticket_event": """SELECT t.holder_user_id, e.occurred_at FROM breach_ticket_event e
                              JOIN breach_ticket t ON t.ticket_id = e.ticket_id""",
    "breach_ticket_message": """SELECT t.holder_user_id, m.created_at
                                FROM breach_ticket_message m
                                JOIN breach_ticket t ON t.ticket_id = m.ticket_id""",
}

#: Sealed tables a database breach cannot trace to a data principal's account,
#: and why. Whoever they concern is added to the list by hand.
NOT_ABOUT_A_PRINCIPAL: dict[str, str] = {
    "processor_respondent": "a contact at a processor, not an account the platform can notify",
    "project_processor": "the office's reason for a processor decision",
    "project_status_history": "the office's reason for a project's move",
    "import_batch": "the name of a manifest file",
    "breach": "the office's account of an incident",
    "breach_status_history": "the office's reason for reopening a breach",
    "breach_determination": "the office's reasoning",
    "breach_assessment": "the office's account; a person named in it is added by hand",
    "breach_obligation_event": "a note on a submission",
    "breach_affected_revision": "a note on a revision of this list",
    "breach_notice": "what everyone a breach touched is told; it names nobody",
}


async def people_in_tables(
    conn: Conn, tables: list[str], *, since: datetime | None, until: datetime | None
) -> list[Row]:
    """Everyone with a row in these tables written in the window, and which tables."""
    arms = " UNION ALL ".join(
        f"SELECT person_id, at, '{t}' AS tbl FROM ({PLATFORM_TABLES[t]}) AS x(person_id, at)"
        for t in tables
    )
    return await fetch_all(
        conn,
        f"""SELECT person_id, array_agg(DISTINCT tbl ORDER BY tbl) AS tables
              FROM ({arms}) AS rows
             WHERE (%(since)s::timestamptz IS NULL OR at >= %(since)s)
               AND (%(until)s::timestamptz IS NULL OR at <= %(until)s)
             GROUP BY person_id""",
        {"since": since, "until": until},
    )


async def listed_person_ids(conn: Conn, breach_id: int) -> set[int]:
    rows = await fetch_all(
        conn, "SELECT auth_user_id FROM breach_affected WHERE breach_id = %s", (breach_id,)
    )
    return {int(r["auth_user_id"]) for r in rows}


async def add_affected_revision(
    conn: Conn,
    breach_id: int,
    *,
    scopes: list[dict[str, Any]],
    derived: int,
    added_by_hand: int,
    excluded: int,
    people: list[tuple[int, str, dict[str, Any]]],
    note: str | None,
    confirmed_by: int,
) -> Row:
    """The next revision, and a row for each person it lists for the first time.

    The breach row is locked by the caller. `ON CONFLICT DO NOTHING` is the
    second line: a person already listed stays on the revision that first
    listed them.
    """
    sealed = await seal("breach_affected_revision", {"note": note})
    revision = await fetch_one(
        conn,
        """INSERT INTO breach_affected_revision
             (breach_id, revision, scopes, derived, added_by_hand, excluded, newly_listed,
              note, confirmed_by)
           VALUES (%s, (SELECT coalesce(max(revision), 0) + 1 FROM breach_affected_revision
                         WHERE breach_id = %s),
                   %s, %s, %s, %s, %s, %s, %s)
           RETURNING revision_id, revision_uuid, revision""",
        (
            breach_id,
            breach_id,
            Jsonb(scopes),
            derived,
            added_by_hand,
            excluded,
            len(people),
            sealed["note"],
            confirmed_by,
        ),
    )
    assert revision is not None
    if people:
        await conn.execute(
            """INSERT INTO breach_affected
                 (breach_id, revision_id, auth_user_id, found_by, evidence)
               SELECT %s, %s, p.person_id, p.found_by, p.evidence::jsonb
                 FROM unnest(%s::int[], %s::text[], %s::text[]) AS p(person_id, found_by, evidence)
               ON CONFLICT (breach_id, auth_user_id) DO NOTHING""",
            (
                breach_id,
                int(revision["revision_id"]),
                [p[0] for p in people],
                [p[1] for p in people],
                [json.dumps(p[2]) for p in people],
            ),
        )
    return revision


async def affected_revisions(conn: Conn, breach_id: int) -> list[Row]:
    return await fetch_all(
        conn,
        """SELECT r.revision_uuid, r.revision, r.scopes, r.derived, r.added_by_hand, r.excluded,
                  r.newly_listed, r.note, r.confirmed_at, u.full_name AS confirmed_by_name
             FROM breach_affected_revision r JOIN auth_user u ON u.id = r.confirmed_by
            WHERE r.breach_id = %s ORDER BY r.revision""",
        (breach_id,),
    )


_PERSON = """
  u.uuid AS person_uuid, u.full_name, u.role::text AS role,
  (u.email IS NOT NULL) AS has_email, (u.mobile IS NOT NULL) AS has_mobile
"""


async def affected_page(conn: Conn, breach_id: int, *, after: int | None, limit: int) -> list[Row]:
    """The listed people, in the order they were listed, a page at a time."""
    return await fetch_all(
        conn,
        f"""SELECT a.affected_id, a.affected_uuid, a.found_by, a.evidence, r.revision, {_PERSON}
              FROM breach_affected a
              JOIN breach_affected_revision r ON r.revision_id = a.revision_id
              JOIN auth_user u ON u.id = a.auth_user_id
             WHERE a.breach_id = %s AND (%s::int IS NULL OR a.affected_id > %s)
             ORDER BY a.affected_id LIMIT %s""",
        (breach_id, after, after, limit),
    )


async def people_by_ids(conn: Conn, ids: list[int]) -> list[Row]:
    return await fetch_all(
        conn, f"SELECT u.id AS person_id, {_PERSON} FROM auth_user u WHERE u.id = ANY(%s)", (ids,)
    )


async def count_affected(conn: Conn, breach_id: int) -> int:
    row = await fetch_one(
        conn, "SELECT count(*) AS n FROM breach_affected WHERE breach_id = %s", (breach_id,)
    )
    return int(row["n"]) if row else 0


async def affected_id_by_uuid(conn: Conn, breach_id: int, affected_uuid: str) -> int | None:
    """The row a page cursor names, within this breach only."""
    row = await fetch_one(
        conn,
        "SELECT affected_id FROM breach_affected WHERE affected_uuid = %s AND breach_id = %s",
        (affected_uuid, breach_id),
    )
    return int(row["affected_id"]) if row else None
