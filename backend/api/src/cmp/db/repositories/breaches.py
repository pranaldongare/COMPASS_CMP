"""The breach register (S3-01): the breach, its determinations, assessments and duties.

Everything below `breach` is append-only by trigger and grant, and `breach`
itself changes only its status, so this module has one UPDATE and it moves a
status. A revision is an INSERT and the latest row is current.

Every narrative field is sealed here, at the write, like every other reason the
office writes; the rows served carry ciphertext and the console opens it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from psycopg.types.json import Jsonb

from cmp.db.sql import Conn, fetch_all, fetch_one
from cmp.infrastructure.dkms import seal

Row = dict[str, Any]

_BREACH = """
  b.breach_id, b.breach_uuid, b.reference, b.title, b.detected_at, b.began_at,
  b.location_kind, b.location_detail, b.status, b.recorded_at,
  pr.processor_uuid AS location_processor_uuid, pr.legal_name AS location_processor_name,
  ds.source_uuid AS location_source_uuid, ds.name AS location_source_name,
  rb.full_name AS recorded_by_name
  FROM breach b
  LEFT JOIN processor pr  ON pr.processor_id = b.location_processor_id
  LEFT JOIN data_source ds ON ds.source_id = b.location_source_id
  JOIN auth_user rb       ON rb.id = b.recorded_by
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
        VALUES ('BR-' || to_char(now(), 'YYYY') || '-'
                  || lpad(nextval('breach_ref_seq')::text, 4, '0'),
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


async def by_uuid(conn: Conn, breach_uuid: str) -> Row | None:
    return await fetch_one(conn, f"SELECT {_BREACH} WHERE b.breach_uuid = %s", (breach_uuid,))


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
    due_at: datetime | None = None,
    anchored_at: datetime | None = None,
    requested_at: datetime | None = None,
    determination_id: int | None = None,
) -> Row:
    sealed = await seal("breach_obligation_event", {"note": note})
    row = await fetch_one(
        conn,
        """INSERT INTO breach_obligation_event
             (obligation_id, kind, occurred_at, reference, note, due_at, anchored_at,
              requested_at, determination_id, recorded_by)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           RETURNING event_id, event_uuid""",
        (
            obligation_id,
            kind,
            occurred_at,
            reference,
            sealed["note"],
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
                  e.due_at, e.anchored_at, e.requested_at, e.recorded_at,
                  d.determination_uuid, u.full_name AS recorded_by_name
             FROM breach_obligation_event e
             LEFT JOIN breach_determination d ON d.determination_id = e.determination_id
             LEFT JOIN auth_user u ON u.id = e.recorded_by
            WHERE e.obligation_id = ANY(%s) ORDER BY e.event_id""",
        (obligation_ids,),
    )
