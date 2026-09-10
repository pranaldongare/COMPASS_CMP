"""rights_request, rights_request_holder, rights_request_item, nomination.

SQL only. What a request *means* - who may move it, what a holder is asked to
do, whether an asset with three people in it may be deleted - is decided in
`cmp.domain.rights`. This module reads and writes rows.

Scope is compiled into the WHERE clause, as everywhere else. The DPO sees every
request. The administrator sees only grievances about the DPO, which are the
ones the DPO must not review. Nobody else sees any, and a data principal reaches
her own through the `for_subject` queries, which take her id and no other
identifier.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from psycopg.types.json import Jsonb

from cmp.core.pagination import PageRequest, build_page
from cmp.core.permissions import Role
from cmp.db.sql import Conn, Row, fetch_all, fetch_one, keyset_clause

LIST_SORTS = ("received_at", "due_at")

# ------------------------------------------------------------------ requests
_SELECT = """
  r.request_id, r.request_uuid, r.reference, r.request_type, r.original_type,
  r.status, r.outcome, r.channel, r.submitted_name, r.submitted_contact,
  r.request_text, r.received_at, r.due_at, r.acknowledged_at,
  r.verification_method, r.verification_status, r.verified_at, r.verification_note,
  r.classified_at, r.refusal_reason, r.intent_confirmed_at,
  r.linked_request_id, r.nomination_id, r.trigger_event, r.trigger_evidence_ref,
  r.trigger_evidence_hash, r.trigger_evidenced_at,
  r.about_dpo, r.reviewer_user_id, r.escalated_at, r.grievance_upheld, r.remedy_text,
  r.response_text, r.response_file_ref, r.response_file_hash, r.responded_at,
  r.download_expires_at, r.closed_at, r.created_at, r.updated_at,
  r.subject_user_id,
  s.uuid AS subject_uuid, s.full_name AS subject_name, s.email AS subject_email,
  s.mobile AS subject_mobile,
  lr.request_uuid AS linked_request_uuid, lr.reference AS linked_reference,
  lr.request_type AS linked_request_type,
  rv.uuid AS reviewer_uuid, rv.full_name AS reviewer_name,
  vb.full_name AS verified_by_name,
  n.nomination_uuid, n.nominee_name, coalesce(n.nominee_mobile, n.nominee_email) AS nominee_contact,
  n.nominee_mobile, n.nominee_email,
  (SELECT count(*) FROM rights_request_holder h WHERE h.request_id = r.request_id)
    AS holder_count,
  (SELECT count(*) FROM rights_request_holder h
    WHERE h.request_id = r.request_id AND h.confirmed_at IS NOT NULL) AS holders_confirmed,
  (SELECT count(*) FROM rights_request_holder h
    WHERE h.request_id = r.request_id AND h.ticket_status <> 'pending') AS tickets_issued,
  (SELECT count(*) FROM rights_request_holder h
    WHERE h.request_id = r.request_id AND h.ticket_status IN ('issued', 'escalated'))
    AS tickets_outstanding,
  (SELECT count(*) FROM rights_request_holder h
    WHERE h.request_id = r.request_id AND h.ticket_status = 'issued') AS tickets_unescalated,
  (SELECT count(*) FROM rights_request_holder h
    WHERE h.request_id = r.request_id AND h.ticket_status = 'returned') AS tickets_returned,
  (SELECT count(*) FROM rights_request_item i WHERE i.request_id = r.request_id) AS item_count,
  (SELECT count(*) FROM rights_request_item i
    WHERE i.request_id = r.request_id AND i.decision IS NULL) AS items_undecided
"""

_FROM = """
  FROM rights_request r
  LEFT JOIN auth_user s       ON s.id = r.subject_user_id
  LEFT JOIN rights_request lr ON lr.request_id = r.linked_request_id
  LEFT JOIN auth_user rv      ON rv.id = r.reviewer_user_id
  LEFT JOIN auth_user vb      ON vb.id = r.verified_by
  LEFT JOIN nomination n      ON n.nomination_id = r.nomination_id
"""


def scope_predicate(role: Role | str, user_id: int) -> tuple[str, list[Any]]:
    """Which requests this caller may see, as SQL.

    The DPO: all. The administrator: only grievances about the DPO, where they
    stand in as the independent reviewer. Anyone else: none - and "none" is a
    predicate that selects nothing, not a check after the fact.
    """
    try:
        r = Role(role)
    except ValueError:
        return "FALSE", []
    if r is Role.DPO:
        return "TRUE", []
    if r is Role.ADMIN:
        return "r.about_dpo", []
    return "FALSE", []


async def create(
    conn: Conn,
    *,
    request_type: str,
    channel: str,
    subject_user_id: int | None,
    submitted_name: str | None,
    submitted_contact: str,
    request_text: str,
    due_at: datetime,
    created_by: int | None,
    verification_method: str | None = None,
    verification_status: str = "pending",
    verified_by: int | None = None,
    verification_note: str | None = None,
    linked_request_id: int | None = None,
    nomination_id: int | None = None,
    trigger_event: str | None = None,
    trigger_evidence_ref: str | None = None,
    trigger_evidence_hash: str | None = None,
    about_dpo: bool = False,
) -> Row:
    """Insert a request. The reference is minted here and never reused."""
    row = await fetch_one(
        conn,
        """
        INSERT INTO rights_request
          (reference, request_type, channel, subject_user_id, submitted_name,
           submitted_contact, request_text, due_at, created_by,
           verification_method, verification_status, verified_at, verified_by,
           verification_note, linked_request_id, nomination_id, trigger_event,
           trigger_evidence_ref, trigger_evidence_hash, about_dpo)
        VALUES
          ('RR-' || to_char(now(), 'YYYY') || '-'
             || lpad(nextval('rights_request_ref_seq')::text, 6, '0'),
           %(request_type)s::rights_request_type, %(channel)s::rights_request_channel,
           %(subject_user_id)s, %(submitted_name)s, %(submitted_contact)s,
           %(request_text)s, %(due_at)s, %(created_by)s,
           %(verification_method)s::rights_verification_method,
           %(verification_status)s::rights_verification_status,
           CASE WHEN %(verification_status)s = 'verified' THEN now() END,
           %(verified_by)s, %(verification_note)s, %(linked_request_id)s,
           %(nomination_id)s, %(trigger_event)s::rights_trigger_event,
           %(trigger_evidence_ref)s, %(trigger_evidence_hash)s, %(about_dpo)s)
        RETURNING request_id, request_uuid, reference, received_at, due_at
        """,
        {
            "request_type": request_type,
            "channel": channel,
            "subject_user_id": subject_user_id,
            "submitted_name": submitted_name,
            "submitted_contact": submitted_contact,
            "request_text": request_text,
            "due_at": due_at,
            "created_by": created_by,
            "verification_method": verification_method,
            "verification_status": verification_status,
            "verified_by": verified_by,
            "verification_note": verification_note,
            "linked_request_id": linked_request_id,
            "nomination_id": nomination_id,
            "trigger_event": trigger_event,
            "trigger_evidence_ref": trigger_evidence_ref,
            "trigger_evidence_hash": trigger_evidence_hash,
            "about_dpo": about_dpo,
        },
    )
    assert row is not None
    return row


#: Columns the service may set after creation. Anything else is a programming
#: error, and the check turns it into an exception rather than a SQL string
#: that quietly does nothing.
_MUTABLE = frozenset(
    {
        "request_type",
        "original_type",
        "status",
        "outcome",
        "subject_user_id",
        "acknowledged_at",
        "verification_method",
        "verification_status",
        "verified_at",
        "verified_by",
        "verification_note",
        "classified_at",
        "classified_by",
        "refusal_reason",
        "intent_confirmed_at",
        "trigger_evidenced_at",
        "reviewer_user_id",
        "escalated_at",
        "grievance_upheld",
        "remedy_text",
        "response_text",
        "response_file_ref",
        "response_file_hash",
        "responded_at",
        "responded_by",
        "download_expires_at",
        "closed_at",
    }
)

#: Columns whose values are PostgreSQL enums and need the cast.
_CASTS = {
    "request_type": "rights_request_type",
    "original_type": "rights_request_type",
    "status": "rights_request_status",
    "outcome": "rights_request_outcome",
    "verification_method": "rights_verification_method",
    "verification_status": "rights_verification_status",
}


async def update(conn: Conn, request_id: int, **cols: Any) -> None:
    unknown = set(cols) - _MUTABLE
    if unknown:
        raise ValueError(f"not a mutable rights_request column: {sorted(unknown)}")
    if not cols:
        return
    assignments = ", ".join(
        f"{name} = %({name})s::{_CASTS[name]}" if name in _CASTS else f"{name} = %({name})s"
        for name in cols
    )
    await conn.execute(
        f"UPDATE rights_request SET {assignments}, updated_at = now() "
        "WHERE request_id = %(request_id)s",
        {**cols, "request_id": request_id},
    )


async def by_uuid(conn: Conn, request_uuid: str, *, role: Role | str, user_id: int) -> Row | None:
    pred, params = scope_predicate(role, user_id)
    return await fetch_one(
        conn,
        f"SELECT {_SELECT}{_FROM} WHERE r.request_uuid = %s AND {pred}",
        [request_uuid, *params],
    )


async def by_id(conn: Conn, request_id: int) -> Row | None:
    return await fetch_one(conn, f"SELECT {_SELECT}{_FROM} WHERE r.request_id = %s", (request_id,))


async def by_reference(conn: Conn, reference: str) -> Row | None:
    """Unscoped: the public verification step identifies a request by the
    reference she was given, before there is anybody to scope to."""
    return await fetch_one(conn, f"SELECT {_SELECT}{_FROM} WHERE r.reference = %s", (reference,))


async def for_subject(conn: Conn, subject_user_id: int) -> list[Row]:
    """Her own requests. Takes her id and nothing else."""
    return await fetch_all(
        conn,
        f"SELECT {_SELECT}{_FROM} WHERE r.subject_user_id = %s ORDER BY r.received_at DESC",
        (subject_user_id,),
    )


async def subject_request(conn: Conn, request_uuid: str, subject_user_id: int) -> Row | None:
    return await fetch_one(
        conn,
        f"SELECT {_SELECT}{_FROM} WHERE r.request_uuid = %s AND r.subject_user_id = %s",
        (request_uuid, subject_user_id),
    )


async def list_requests(
    conn: Conn,
    req: PageRequest,
    *,
    role: Role | str,
    user_id: int,
    request_type: str | None = None,
    status: str | None = None,
    overdue: bool = False,
    q: str | None = None,
) -> tuple[list[Row], str | None, int]:
    pred, sparams = scope_predicate(role, user_id)
    where = [pred]
    params: list[Any] = [*sparams]

    if request_type:
        where.append("r.request_type = %s::rights_request_type")
        params.append(request_type)
    if status:
        where.append("r.status = %s::rights_request_status")
        params.append(status)
    if overdue:
        where.append("r.status <> 'closed' AND r.due_at < now()")
    if q:
        where.append(
            "(r.reference ILIKE %s OR s.full_name ILIKE %s OR s.email ILIKE %s "
            "OR r.submitted_contact ILIKE %s)"
        )
        needle = f"%{q}%"
        params.extend([needle, needle, needle, needle])

    clause = " AND ".join(where)
    keyset, kparams = keyset_clause(req, alias="r", id_column="request_id")
    rows = await fetch_all(
        conn,
        f"SELECT r.request_id AS _row_id, {_SELECT}{_FROM} WHERE {clause}{keyset}",
        [*params, *kparams],
    )
    total = await fetch_one(conn, f"SELECT count(*) AS n {_FROM} WHERE {clause}", params)
    items, cursor = build_page(rows, req)
    return items, cursor, int((total or {}).get("n", 0))


# ------------------------------------------------------------------- holders
_HOLDER_SELECT = """
  h.holder_id, h.holder_uuid, h.request_id, h.label, h.derived_from, h.evidence,
  h.confirmed_at, h.ticket_status, h.instruction, h.responder_name, h.responder_contact,
  h.issued_at, h.due_at, h.escalated_at, h.returned_at, h.return_summary,
  h.return_evidence_ref, h.return_evidence_hash, h.created_at,
  h.processor_id, pr.processor_uuid, pr.legal_name AS processor_name, pr.is_in_house,
  cb.full_name AS confirmed_by_name,
  h.respondent_id, rs.respondent_uuid, h.responder_user_id, h.channel, h.contact_log,
  ru.uuid AS responder_user_uuid, ru.full_name AS responder_user_name,
  ru.email AS responder_user_email,
  h.brief, h.office_read_at, h.holder_read_at,
  (SELECT count(*) FROM rights_ticket_message m WHERE m.holder_id = h.holder_id)
    AS message_count,
  (SELECT count(*) FROM rights_ticket_message m
    WHERE m.holder_id = h.holder_id AND m.author_side = 'holder'
      AND m.created_at > coalesce(h.office_read_at, 'epoch'::timestamptz))
    AS unread_for_office,
  (SELECT count(*) FROM rights_ticket_message m
    WHERE m.holder_id = h.holder_id AND m.author_side IN ('office', 'system')
      AND m.created_at > coalesce(h.holder_read_at, 'epoch'::timestamptz))
    AS unread_for_holder
  FROM rights_request_holder h
  LEFT JOIN processor pr ON pr.processor_id = h.processor_id
  LEFT JOIN auth_user cb ON cb.id = h.confirmed_by
  LEFT JOIN processor_respondent rs ON rs.respondent_id = h.respondent_id
  LEFT JOIN auth_user ru ON ru.id = h.responder_user_id
"""


async def holders_of(conn: Conn, request_id: int) -> list[Row]:
    return await fetch_all(
        conn,
        f"SELECT {_HOLDER_SELECT} WHERE h.request_id = %s ORDER BY h.created_at, h.holder_id",
        (request_id,),
    )


async def holder_by_uuid(conn: Conn, request_id: int, holder_uuid: str) -> Row | None:
    return await fetch_one(
        conn,
        f"SELECT {_HOLDER_SELECT} WHERE h.request_id = %s AND h.holder_uuid = %s",
        (request_id, holder_uuid),
    )


async def derive_holder_candidates(conn: Conn, subject_user_id: int) -> list[Row]:
    """Who holds her data, from the records that say so.

    Two sources, joined: every export that carried one of her consent records
    went to the processor running the site it was for, and every collected
    asset she appears in was captured by a data source a processor runs. The
    DPO confirms the list and adds what the records miss - the records name
    what the platform knows, and the platform does not know everything.
    """
    return await fetch_all(
        conn,
        """
        WITH via_exports AS (
          SELECT pr.processor_id, pr.legal_name,
                 array_agg(DISTINCT e.export_uuid::text) AS exports
          FROM export_line el
          JOIN export_log e     ON e.export_id = el.export_id
          JOIN project_site s   ON s.site_id = e.site_id
          JOIN processor pr     ON pr.processor_id = s.processor_id
          WHERE el.auth_user_id = %(u)s
          GROUP BY pr.processor_id, pr.legal_name
        ),
        via_assets AS (
          SELECT pr.processor_id, pr.legal_name,
                 array_agg(DISTINCT da.asset_uuid::text) AS assets
          FROM asset_consent ac
          JOIN consent_artefact ca ON ca.consent_id = ac.consent_id
          JOIN data_asset da       ON da.asset_id = ac.asset_id
          JOIN data_source ds      ON ds.source_id = da.source_id
          JOIN processor pr        ON pr.processor_id = ds.processor_id
          WHERE ca.auth_user_id = %(u)s
            AND coalesce(ac.disposition, 'active') = 'active'
          GROUP BY pr.processor_id, pr.legal_name
        )
        SELECT coalesce(x.processor_id, a.processor_id) AS processor_id,
               coalesce(x.legal_name, a.legal_name)     AS legal_name,
               coalesce(x.exports, ARRAY[]::text[])     AS exports,
               coalesce(a.assets, ARRAY[]::text[])      AS assets
        FROM via_exports x
        FULL OUTER JOIN via_assets a ON a.processor_id = x.processor_id
        ORDER BY 2
        """,
        {"u": subject_user_id},
    )


async def add_holder(
    conn: Conn,
    request_id: int,
    *,
    processor_id: int | None,
    label: str,
    derived_from: str,
    evidence: dict[str, Any],
    responder_name: str | None = None,
    responder_contact: str | None = None,
    respondent_id: int | None = None,
    responder_user_id: int | None = None,
    channel: str = "email",
) -> Row:
    """One row per processor per request. Deriving twice refreshes the
    evidence rather than adding a second holder."""
    row = await fetch_one(
        conn,
        """
        INSERT INTO rights_request_holder
          (request_id, processor_id, label, derived_from, evidence,
           responder_name, responder_contact, respondent_id, responder_user_id, channel)
        VALUES (%s, %s, %s, %s::rights_holder_source, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (request_id, processor_id) WHERE processor_id IS NOT NULL
        DO UPDATE SET evidence = EXCLUDED.evidence
        RETURNING holder_id, holder_uuid, (xmax = 0) AS inserted
        """,
        (
            request_id,
            processor_id,
            label,
            derived_from,
            Jsonb(evidence),
            responder_name,
            responder_contact,
            respondent_id,
            responder_user_id,
            channel,
        ),
    )
    assert row is not None
    return row


_HOLDER_MUTABLE = frozenset(
    {
        "confirmed_at",
        "confirmed_by",
        "ticket_status",
        "instruction",
        "responder_name",
        "responder_contact",
        "issued_at",
        "due_at",
        "escalated_at",
        "returned_at",
        "return_summary",
        "return_evidence_ref",
        "return_evidence_hash",
        "respondent_id",
        "responder_user_id",
        "channel",
        "brief",
        "office_read_at",
        "holder_read_at",
    }
)


async def mark_thread_read(conn: Conn, holder_id: int, *, side: str) -> None:
    """One side has seen the thread up to now."""
    column = "office_read_at" if side == "office" else "holder_read_at"
    # clock_timestamp(), not now(): now() is frozen for the transaction, and a
    # read stamped in the same transaction as the message it follows would tie
    # with it and count it as unread forever - or read before it was written.
    await conn.execute(
        f"UPDATE rights_request_holder SET {column} = clock_timestamp() WHERE holder_id = %s",
        (holder_id,),
    )


# ------------------------------------------------------------ the thread

_MESSAGE_SELECT = """
  m.message_id, m.message_uuid, m.holder_id, m.author_user_id, m.author_side, m.kind,
  m.body, m.evidence_ref, m.evidence_hash, m.created_at,
  a.full_name AS author_name
  FROM rights_ticket_message m
  LEFT JOIN auth_user a ON a.id = m.author_user_id
"""


async def messages_of(conn: Conn, holder_id: int) -> list[Row]:
    return await fetch_all(
        conn,
        f"SELECT {_MESSAGE_SELECT} WHERE m.holder_id = %s ORDER BY m.message_id",
        (holder_id,),
    )


async def message_by_uuid(conn: Conn, holder_id: int, message_uuid: str) -> Row | None:
    return await fetch_one(
        conn,
        f"SELECT {_MESSAGE_SELECT} WHERE m.holder_id = %s AND m.message_uuid = %s",
        (holder_id, message_uuid),
    )


async def add_message(
    conn: Conn,
    holder_id: int,
    *,
    side: str,
    kind: str,
    body: str,
    author_user_id: int | None = None,
    evidence_ref: str | None = None,
    evidence_hash: str | None = None,
) -> Row:
    """One more message on the thread. Append-only at the trigger level."""
    row = await fetch_one(
        conn,
        """INSERT INTO rights_ticket_message
             (holder_id, author_user_id, author_side, kind, body, evidence_ref, evidence_hash,
              created_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, clock_timestamp())
           RETURNING message_id, message_uuid""",
        (holder_id, author_user_id, side, kind, body, evidence_ref, evidence_hash),
    )
    assert row is not None
    return row


async def holders_awaiting_office(conn: Conn, *, limit: int = 25) -> list[Row]:
    """Open holders whose team has written and the Privacy Office has not read it."""
    return await fetch_all(
        conn,
        """SELECT r.request_uuid, r.reference, r.due_at, s.full_name AS subject_name,
                  h.holder_uuid, h.label,
                  (SELECT count(*) FROM rights_ticket_message m
                    WHERE m.holder_id = h.holder_id AND m.author_side = 'holder'
                      AND m.created_at > coalesce(h.office_read_at, 'epoch'::timestamptz))
                    AS unread
           FROM rights_request_holder h
           JOIN rights_request r ON r.request_id = h.request_id
           LEFT JOIN auth_user s ON s.id = r.subject_user_id
           WHERE r.status <> 'closed'
             AND EXISTS (SELECT 1 FROM rights_ticket_message m
                          WHERE m.holder_id = h.holder_id AND m.author_side = 'holder'
                            AND m.created_at > coalesce(h.office_read_at, 'epoch'::timestamptz))
           ORDER BY r.due_at, h.holder_id
           LIMIT %s""",
        (limit,),
    )


# ------------------------------------------------------------- the brief


async def holder_brief(
    conn: Conn, *, subject_user_id: int, processor_id: int | None
) -> dict[str, Any]:
    """What the platform already knows, for the ticket to open with.

    The person, and every record on the platform that names this holder as
    holding something of hers: the consents given at its sites, the exports
    that carried her record to it, the assets it collected that she appears
    in. The ticket's question is then what the holder has *beyond* these -
    not who she is, which the platform knew all along.
    """
    subject = await fetch_one(
        conn,
        "SELECT uuid, full_name, email, mobile FROM auth_user WHERE id = %s",
        (subject_user_id,),
    )
    brief: dict[str, Any] = {
        "subject": {
            "uuid": str(subject["uuid"]) if subject else None,
            "full_name": subject["full_name"] if subject else None,
            "email": subject["email"] if subject else None,
            "mobile": subject["mobile"] if subject else None,
        },
        "consents": [],
        "exports": [],
        "assets": [],
    }
    if processor_id is None:
        return brief
    consents = await fetch_all(
        conn,
        """SELECT ca.consent_uuid, ca.affirmative_action_at, ca.is_withdrawal,
                  p.project_name, s.site_label,
                  array_remove(array_agg(pu.name ORDER BY pu.name)
                               FILTER (WHERE g.granted), NULL) AS granted,
                  array_remove(array_agg(pu.name ORDER BY pu.name)
                               FILTER (WHERE NOT g.granted), NULL) AS declined
           FROM consent_artefact ca
           JOIN consent_link cl ON cl.link_id = ca.link_id
           JOIN project_site s ON s.site_id = cl.site_id
           JOIN project p ON p.project_id = s.project_id
           LEFT JOIN consent_purpose_grant g ON g.consent_id = ca.consent_id
           LEFT JOIN purpose pu ON pu.purpose_id = g.purpose_id
           WHERE ca.auth_user_id = %(u)s AND s.processor_id = %(p)s
           GROUP BY ca.consent_id, ca.consent_uuid, ca.affirmative_action_at, ca.is_withdrawal,
                    p.project_name, s.site_label
           ORDER BY ca.affirmative_action_at""",
        {"u": subject_user_id, "p": processor_id},
    )
    exports = await fetch_all(
        conn,
        """SELECT e.export_uuid, e.exported_at, e.export_type, p.project_name
           FROM export_line el
           JOIN export_log e ON e.export_id = el.export_id
           JOIN project_site s ON s.site_id = e.site_id
           JOIN project p ON p.project_id = e.project_id
           WHERE el.auth_user_id = %(u)s AND s.processor_id = %(p)s
           ORDER BY e.exported_at""",
        {"u": subject_user_id, "p": processor_id},
    )
    assets = await fetch_all(
        conn,
        """SELECT da.asset_uuid, da.source_asset_ref, da.asset_type, ds.name AS source_name,
                  c.collected_on, ac.subject_role, ac.disposition
           FROM asset_consent ac
           JOIN consent_artefact ca ON ca.consent_id = ac.consent_id
           JOIN data_asset da ON da.asset_id = ac.asset_id
           JOIN data_source ds ON ds.source_id = da.source_id
           LEFT JOIN collection c ON c.collection_id = da.collection_id
           WHERE ca.auth_user_id = %(u)s AND ds.processor_id = %(p)s
           ORDER BY c.collected_on, da.asset_id""",
        {"u": subject_user_id, "p": processor_id},
    )
    brief["consents"] = [
        {
            "consent_uuid": str(c["consent_uuid"]),
            "at": c["affirmative_action_at"].isoformat() if c["affirmative_action_at"] else None,
            "withdrawal": bool(c["is_withdrawal"]),
            "project": c["project_name"],
            "site": c["site_label"],
            "granted": list(c["granted"] or []),
            "declined": list(c["declined"] or []),
        }
        for c in consents
    ]
    brief["exports"] = [
        {
            "export_uuid": str(e["export_uuid"]),
            "at": e["exported_at"].isoformat() if e["exported_at"] else None,
            "type": str(e["export_type"]),
            "project": e["project_name"],
        }
        for e in exports
    ]
    brief["assets"] = [
        {
            "asset_uuid": str(a["asset_uuid"]),
            "ref": a["source_asset_ref"],
            "type": str(a["asset_type"]) if a["asset_type"] else None,
            "source": a["source_name"],
            "collected_on": a["collected_on"].isoformat() if a["collected_on"] else None,
            "role": str(a["subject_role"]) if a["subject_role"] else None,
            "disposition": str(a["disposition"]) if a["disposition"] else None,
        }
        for a in assets
    ]
    return brief


async def append_contact(conn: Conn, holder_id: int, entry: dict[str, Any]) -> None:
    """One more line on the holder's contact log. Appended, never rewritten."""
    await conn.execute(
        """UPDATE rights_request_holder
              SET contact_log = contact_log || %s::jsonb
            WHERE holder_id = %s""",
        (Jsonb([entry]), holder_id),
    )


_TICKET_SELECT = f"""
  {_HOLDER_SELECT.split("FROM rights_request_holder h")[0]},
  r.request_uuid, r.reference, r.request_type, r.status AS request_status,
  r.due_at AS request_due_at, r.received_at, s.full_name AS subject_name
  FROM rights_request_holder h
  JOIN rights_request r ON r.request_id = h.request_id
  LEFT JOIN auth_user s ON s.id = r.subject_user_id
  LEFT JOIN processor pr ON pr.processor_id = h.processor_id
  LEFT JOIN auth_user cb ON cb.id = h.confirmed_by
  LEFT JOIN processor_respondent rs ON rs.respondent_id = h.respondent_id
  LEFT JOIN auth_user ru ON ru.id = h.responder_user_id
"""


async def tickets_for_user(conn: Conn, user_id: int, *, open_only: bool = False) -> list[Row]:
    """Tickets addressed to this member of staff: the portal channel's inbox.

    Scope OWN, realised here as the predicate: only holders whose responder is
    this account, and only ones that have actually been issued - a pending
    holder is the DPO's business, not yet the team's.
    """
    status = (
        "AND h.ticket_status IN ('issued', 'escalated')"
        if open_only
        else "AND h.ticket_status <> 'pending'"
    )
    return await fetch_all(
        conn,
        f"""SELECT {_TICKET_SELECT}
             WHERE h.responder_user_id = %s {status}
             ORDER BY (h.ticket_status IN ('issued', 'escalated')) DESC, h.due_at, h.holder_id""",
        (user_id,),
    )


async def ticket_for_user(conn: Conn, user_id: int, holder_uuid: str) -> Row | None:
    return await fetch_one(
        conn,
        f"SELECT {_TICKET_SELECT} WHERE h.responder_user_id = %s AND h.holder_uuid = %s",
        (user_id, holder_uuid),
    )


async def update_holder(conn: Conn, holder_id: int, **cols: Any) -> None:
    if "brief" in cols and cols["brief"] is not None and not isinstance(cols["brief"], Jsonb):
        cols["brief"] = Jsonb(cols["brief"])
    unknown = set(cols) - _HOLDER_MUTABLE
    if unknown:
        raise ValueError(f"not a mutable holder column: {sorted(unknown)}")
    if not cols:
        return
    assignments = ", ".join(
        f"{name} = %({name})s::rights_ticket_status"
        if name == "ticket_status"
        else f"{name} = %({name})s"
        for name in cols
    )
    await conn.execute(
        f"UPDATE rights_request_holder SET {assignments} WHERE holder_id = %(holder_id)s",
        {**cols, "holder_id": holder_id},
    )


async def mark_unreturned(conn: Conn, request_id: int) -> int:
    """Every ticket still open when the response goes out becomes the gap the
    response names. Returns how many."""
    cur = await conn.execute(
        """UPDATE rights_request_holder SET ticket_status = 'unreturned'
           WHERE request_id = %s AND ticket_status IN ('issued', 'escalated')""",
        (request_id,),
    )
    return cur.rowcount


# --------------------------------------------------------------------- items
_ITEM_SELECT = """
  i.item_id, i.item_uuid, i.request_id, i.asset_consent_id, i.holder_id, i.other_subjects,
  i.state, i.decision, i.basis, i.retain_until, i.floor_passed_at, i.decided_at,
  i.applied_at, i.created_at,
  ac.disposition, ac.disposition_at, ac.subject_role,
  da.asset_uuid, da.asset_type, da.source_asset_ref, da.storage_ref,
  ds.source_code, ds.name AS source_name,
  pr.legal_name AS processor_name,
  p.project_uuid, p.project_name, c.collected_on,
  h.holder_uuid, h.label AS holder_label, h.ticket_status AS holder_ticket_status,
  db.full_name AS decided_by_name
  FROM rights_request_item i
  JOIN asset_consent ac ON ac.asset_consent_id = i.asset_consent_id
  JOIN data_asset da    ON da.asset_id = ac.asset_id
  JOIN collection c     ON c.collection_id = da.collection_id
  JOIN data_source ds   ON ds.source_id = da.source_id
  LEFT JOIN processor pr ON pr.processor_id = ds.processor_id
  JOIN project p        ON p.project_id = c.project_id
  LEFT JOIN rights_request_holder h ON h.holder_id = i.holder_id
  LEFT JOIN auth_user db ON db.id = i.decided_by
"""


async def items_of(conn: Conn, request_id: int) -> list[Row]:
    return await fetch_all(
        conn,
        f"SELECT {_ITEM_SELECT} WHERE i.request_id = %s ORDER BY c.collected_on DESC, i.item_id",
        (request_id,),
    )


async def item_by_uuid(conn: Conn, request_id: int, item_uuid: str) -> Row | None:
    return await fetch_one(
        conn,
        f"SELECT {_ITEM_SELECT} WHERE i.request_id = %s AND i.item_uuid = %s",
        (request_id, item_uuid),
    )


async def derive_scope_candidates(conn: Conn, subject_user_id: int) -> list[Row]:
    """Every appearance of her in a collected asset that is still active.

    `other_subjects` counts the other people in the same asset - consented,
    incidental or unidentified - whose rows are still active. Zero is ordinary
    erasure; anything else is the redaction case, decided per item.
    """
    return await fetch_all(
        conn,
        """
        SELECT ac.asset_consent_id, da.asset_uuid, da.asset_type, ds.processor_id,
               pr.legal_name AS processor_name,
               (SELECT count(*) FROM asset_consent o
                 WHERE o.asset_id = ac.asset_id
                   AND o.asset_consent_id <> ac.asset_consent_id
                   AND coalesce(o.disposition, 'active') = 'active') AS other_subjects
        FROM asset_consent ac
        JOIN consent_artefact ca ON ca.consent_id = ac.consent_id
        JOIN data_asset da       ON da.asset_id = ac.asset_id
        JOIN data_source ds      ON ds.source_id = da.source_id
        LEFT JOIN processor pr   ON pr.processor_id = ds.processor_id
        WHERE ca.auth_user_id = %s
          AND coalesce(ac.disposition, 'active') = 'active'
        ORDER BY da.created_at DESC
        """,
        (subject_user_id,),
    )


async def add_item(
    conn: Conn,
    request_id: int,
    *,
    asset_consent_id: int,
    holder_id: int | None,
    other_subjects: int,
) -> Row | None:
    """Returns the new row, or None when the item was already in scope."""
    return await fetch_one(
        conn,
        """
        INSERT INTO rights_request_item (request_id, asset_consent_id, holder_id, other_subjects)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (request_id, asset_consent_id) DO NOTHING
        RETURNING item_id, item_uuid
        """,
        (request_id, asset_consent_id, holder_id, other_subjects),
    )


_ITEM_MUTABLE = frozenset(
    {
        "holder_id",
        "state",
        "decision",
        "basis",
        "retain_until",
        "floor_passed_at",
        "decided_at",
        "decided_by",
        "applied_at",
    }
)
_ITEM_CASTS = {"state": "rights_item_state", "decision": "rights_scope_decision"}


async def update_item(conn: Conn, item_id: int, **cols: Any) -> None:
    unknown = set(cols) - _ITEM_MUTABLE
    if unknown:
        raise ValueError(f"not a mutable item column: {sorted(unknown)}")
    if not cols:
        return
    assignments = ", ".join(
        f"{name} = %({name})s::{_ITEM_CASTS[name]}"
        if name in _ITEM_CASTS
        else f"{name} = %({name})s"
        for name in cols
    )
    await conn.execute(
        f"UPDATE rights_request_item SET {assignments} WHERE item_id = %(item_id)s",
        {**cols, "item_id": item_id},
    )


async def set_disposition(conn: Conn, asset_consent_id: int, disposition: str) -> Row | None:
    """The one write erasure makes to the collection model: her junction row.

    Never `data_asset`. See decision D-09 in the migration docstring.
    """
    return await fetch_one(
        conn,
        """UPDATE asset_consent
              SET disposition = %s::disposition, disposition_at = now()
            WHERE asset_consent_id = %s
            RETURNING asset_id, asset_consent_id""",
        (disposition, asset_consent_id),
    )


# -------------------------------------------------------------------- sweeps
async def unverified_public_older_than(conn: Conn, days: int) -> list[Row]:
    return await fetch_all(
        conn,
        f"""SELECT {_SELECT}{_FROM}
             WHERE r.status = 'received' AND r.channel = 'public_form'
               AND r.verification_status = 'pending'
               AND r.received_at < now() - make_interval(days => %s)""",
        (days,),
    )


async def retained_items_past_floor(conn: Conn, today: date) -> list[Row]:
    return await fetch_all(
        conn,
        f"""SELECT {_ITEM_SELECT}
             WHERE i.decision = 'retain' AND i.retain_until <= %s
               AND i.floor_passed_at IS NULL""",
        (today,),
    )


# ----------------------------------------------------------------- dashboard
async def counts(conn: Conn) -> Row:
    row = await fetch_one(
        conn,
        """SELECT
             count(*) FILTER (WHERE status <> 'closed') AS requests_open,
             count(*) FILTER (WHERE status <> 'closed' AND due_at < now())
               AS requests_overdue,
             count(*) FILTER (WHERE status <> 'closed'
                                AND due_at BETWEEN now() AND now() + interval '7 days')
               AS requests_due_7d,
             count(*) FILTER (WHERE status = 'received' AND verification_status = 'pending')
               AS requests_unverified,
             count(*) FILTER (WHERE status <> 'closed' AND about_dpo)
               AS grievances_about_dpo
           FROM rights_request""",
    )
    return row or {}


async def queue(conn: Conn, *, role: Role | str, user_id: int, limit: int = 25) -> list[Row]:
    """Open requests, soonest due first. The DPO's most time-bound work."""
    pred, params = scope_predicate(role, user_id)
    return await fetch_all(
        conn,
        f"""SELECT r.request_uuid, r.reference, r.request_type, r.status, r.due_at,
                   r.received_at, r.verification_status, r.about_dpo,
                   coalesce(s.full_name, r.submitted_name, r.submitted_contact) AS subject_name,
                   (r.due_at < now()) AS overdue,
                   CASE
                     WHEN r.verification_status = 'pending' THEN 'Verify identity'
                     WHEN r.status = 'received' THEN 'Classify and start'
                     WHEN r.status = 'in_progress' THEN 'Confirm holders and issue tickets'
                     WHEN r.status = 'awaiting_holders' THEN 'Chase the holders'
                     WHEN r.status = 'collating' THEN 'Collate, review and respond'
                   END AS action
            FROM rights_request r
            LEFT JOIN auth_user s ON s.id = r.subject_user_id
            WHERE r.status <> 'closed' AND {pred}
            ORDER BY r.due_at ASC
            LIMIT %s""",
        [*params, limit],
    )


async def floor_queue(conn: Conn, today: date, *, limit: int = 25) -> list[Row]:
    """Retained items whose floor has passed and that are not yet applied."""
    return await fetch_all(
        conn,
        """SELECT r.request_uuid, r.reference, i.item_uuid, i.retain_until,
                  coalesce(s.full_name, r.submitted_contact) AS subject_name,
                  'The retention floor has passed - apply the erasure' AS action
           FROM rights_request_item i
           JOIN rights_request r ON r.request_id = i.request_id
           LEFT JOIN auth_user s ON s.id = r.subject_user_id
           WHERE i.decision = 'retain' AND i.retain_until <= %s AND i.applied_at IS NULL
           ORDER BY i.retain_until
           LIMIT %s""",
        (today, limit),
    )


async def subject_counts(conn: Conn, subject_user_id: int) -> Row:
    row = await fetch_one(
        conn,
        """SELECT count(*) FILTER (WHERE status <> 'closed') AS requests_open,
                  count(*) FILTER (WHERE status = 'closed')  AS requests_closed
           FROM rights_request WHERE subject_user_id = %s""",
        (subject_user_id,),
    )
    return row or {}


# --------------------------------------------------------------- nominations
_NOMINATION_SELECT = """
  n.nomination_id, n.nomination_uuid, n.nominee_name, n.nominee_mobile, n.nominee_email,
  coalesce(n.nominee_mobile, n.nominee_email) AS nominee_contact,
  -- Cast: an enum array comes back unparsed unless its type is registered.
  n.rights::text[] AS rights,
  n.status, n.accept_expires_at, n.accepted_at, n.declined_at, n.revoked_at, n.created_at,
  n.principal_user_id, p.uuid AS principal_uuid, p.full_name AS principal_name,
  p.email AS principal_email
  FROM nomination n
  JOIN auth_user p ON p.id = n.principal_user_id
"""


async def create_nomination(
    conn: Conn,
    *,
    principal_user_id: int,
    nominee_name: str,
    nominee_mobile: str,
    nominee_email: str | None,
    rights: list[str],
    accept_token_hash: str,
    accept_expires_at: datetime,
) -> Row:
    row = await fetch_one(
        conn,
        """
        INSERT INTO nomination
          (principal_user_id, nominee_name, nominee_mobile, nominee_email, rights,
           accept_token_hash, accept_expires_at)
        VALUES (%s, %s, %s, %s, %s::rights_request_type[], %s, %s)
        RETURNING nomination_id, nomination_uuid
        """,
        (
            principal_user_id,
            nominee_name,
            nominee_mobile,
            nominee_email,
            rights,
            accept_token_hash,
            accept_expires_at,
        ),
    )
    assert row is not None
    return row


async def nominations_of(conn: Conn, principal_user_id: int) -> list[Row]:
    return await fetch_all(
        conn,
        f"SELECT {_NOMINATION_SELECT} WHERE n.principal_user_id = %s ORDER BY n.created_at DESC",
        (principal_user_id,),
    )


async def nominations_naming(conn: Conn, *, mobile: str | None, email: str | None) -> list[Row]:
    """Live nominations that name this person as nominee, by either contact.

    The other direction from `nominations_of`. A nominee is not a row in
    `auth_user` - she may be a stranger - so the match is on the contacts the
    principal recorded, compared the way they are stored: the mobile as
    digits, the email lower-cased. Only pending and active: a declined or
    revoked nomination is nothing she can act on and nothing she needs told.
    """
    return await fetch_all(
        conn,
        f"""SELECT {_NOMINATION_SELECT}
             WHERE n.status IN ('pending', 'active')
               AND ((%s::text IS NOT NULL AND n.nominee_mobile = %s)
                    OR (%s::text IS NOT NULL AND lower(n.nominee_email) = lower(%s)))
             ORDER BY n.created_at DESC""",
        (mobile, mobile, email, email),
    )


async def nomination_by_uuid(conn: Conn, nomination_uuid: str) -> Row | None:
    return await fetch_one(
        conn, f"SELECT {_NOMINATION_SELECT} WHERE n.nomination_uuid = %s", (nomination_uuid,)
    )


async def nomination_by_token_hash(conn: Conn, token_hash: str) -> Row | None:
    return await fetch_one(
        conn,
        f"SELECT {_NOMINATION_SELECT} WHERE n.accept_token_hash = %s",
        (token_hash,),
    )


async def live_nomination_of(conn: Conn, principal_user_id: int) -> Row | None:
    return await fetch_one(
        conn,
        f"""SELECT {_NOMINATION_SELECT}
             WHERE n.principal_user_id = %s AND n.status IN ('pending', 'active')""",
        (principal_user_id,),
    )


_NOMINATION_MUTABLE = frozenset(
    {"status", "accepted_at", "declined_at", "revoked_at", "accept_token_hash"}
)


async def update_nomination(conn: Conn, nomination_id: int, **cols: Any) -> None:
    unknown = set(cols) - _NOMINATION_MUTABLE
    if unknown:
        raise ValueError(f"not a mutable nomination column: {sorted(unknown)}")
    if not cols:
        return
    assignments = ", ".join(
        f"{name} = %({name})s::nomination_status" if name == "status" else f"{name} = %({name})s"
        for name in cols
    )
    await conn.execute(
        f"UPDATE nomination SET {assignments} WHERE nomination_id = %(nomination_id)s",
        {**cols, "nomination_id": nomination_id},
    )
