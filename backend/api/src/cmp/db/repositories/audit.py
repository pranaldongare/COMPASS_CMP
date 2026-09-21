"""Reading the audit trail.

Read-only by construction. There is no insert here - writes go through
`cmp.domain.audit.record` on the caller's transaction - and no update or delete
exists at any layer: the route is not registered, the grant is revoked from the
application role, and a database trigger refuses the statement.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from cmp.core.pagination import PageRequest, build_page
from cmp.db.sql import Conn, Row, fetch_all, fetch_one, keyset_clause

LIST_SORTS = ("occurred_at",)

#: The most rows one CSV export carries. Enough for a month of a busy
#: deployment; a question larger than that is a query, not a download.
EXPORT_LIMIT = 10_000

#: Events that are true, recorded, and not activity.
#:
#: Signing in is not something that happened *to the work*, and a feed that
#: leads with "you logged in" pushes out the notice somebody published. They
#: remain in the audit trail, where a DPO investigating access wants them and
#: knows to look; they are excluded from every activity feed.
#:
#: The same list the data-subject feed uses, for the same reason.
_NOT_ACTIVITY = (
    "auth.login_succeeded",
    "auth.login_failed",
    "auth.otp_requested",
    "auth.otp_verified",
    "auth.logout",
    "auth.mfa_verified",
)

#: What a data principal is told about. Her feed and her request trails are
#: the events that concern *her*: what she did, what was done with her data,
#: and how her request moved. The office's working on a request - deriving
#: holders, issuing and chasing tickets, classifying, deciding the scope - is
#: internal, and she has no page to see it on; naming it in her feed would
#: describe machinery she cannot open. The response, and the outcome, are hers.
SUBJECT_VISIBLE: frozenset[str] = frozenset(
    {
        "subject.registered",
        "user.person_type_changed",
        "user.deactivated",
        "user.reactivated",
        "consent.given",
        "consent.declined",
        "consent.withdrawn",
        "notice.served",
        "export.generated",
        "nomination.created",
        "nomination.accepted",
        "nomination.declined",
        "nomination.revoked",
        "nomination.invoked",
        "rights.request_received",
        "rights.acknowledged",
        "rights.verification_code_sent",
        "rights.verified",
        "rights.verification_failed",
        "rights.status_changed",
        "rights.responded",
        "rights.response_downloaded",
        "rights.grievance_decided",
        "rights.closed",
    }
)

_SELECT = """
  l.log_uuid, l.event_type, l.entity_type, l.entity_id, l.occurred_at,
  l.detail_json - '_hash' - '_prev' AS detail,
  actor.uuid   AS actor_uuid,   actor.full_name   AS actor_name,   actor.role AS actor_role,
  subject.uuid AS subject_uuid, subject.full_name AS subject_name
"""

_FROM = """
  FROM audit_log l
  LEFT JOIN auth_user actor   ON actor.id = l.actor_user_id
  LEFT JOIN auth_user subject ON subject.id = l.subject_user_id
"""


@dataclass(frozen=True, slots=True)
class AuditFilters:
    """Every way the trail can be narrowed. One object, so the list, the
    summary and the export are guaranteed to answer the same question."""

    actor_uuid: str | None = None
    actor_role: str | None = None
    subject_uuid: str | None = None
    entity_type: str | None = None
    entity_id: int | None = None
    event_type: str | None = None
    #: The part of the event type before the dot: `consent`, `rights`, `auth`.
    event_group: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    #: Free text, matched against the event type, the recorded detail (a
    #: reference, a purpose name, a reason) and the names and addresses of
    #: the actor and the subject. Not indexed; narrow the dates first on a
    #: large trail.
    q: str | None = None


def _like(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _where(f: AuditFilters) -> tuple[str, list[Any]]:
    where: list[str] = ["1 = 1"]
    params: list[Any] = []
    if f.actor_uuid:
        where.append("actor.uuid = %s")
        params.append(f.actor_uuid)
    if f.actor_role:
        where.append("actor.role = %s")
        params.append(f.actor_role)
    if f.subject_uuid:
        where.append("subject.uuid = %s")
        params.append(f.subject_uuid)
    if f.entity_type:
        where.append("l.entity_type = %s")
        params.append(f.entity_type)
    if f.entity_id is not None:
        where.append("l.entity_id = %s")
        params.append(f.entity_id)
    if f.event_type:
        where.append("l.event_type = %s")
        params.append(f.event_type)
    if f.event_group:
        where.append("l.event_type LIKE %s")
        params.append(f"{f.event_group}.%")
    if f.date_from:
        where.append("l.occurred_at >= %s")
        params.append(f.date_from)
    if f.date_to:
        where.append("l.occurred_at <= %s")
        params.append(f.date_to)
    if f.q and f.q.strip():
        # The event type and the recorded details. Not the actor's or the
        # subject's name or address: those columns are sealed, so a pattern
        # matched against them finds nothing and costs a scan. A person is
        # found through the About picker, by the whole contact (audit_lookup).
        pattern = _like(f.q.strip())
        where.append(
            "(l.event_type ILIKE %s ESCAPE '\\'"
            " OR (l.detail_json - '_hash' - '_prev')::text ILIKE %s ESCAPE '\\')"
        )
        params.extend([pattern] * 2)
    return " AND ".join(where), params


async def search(
    conn: Conn, req: PageRequest, filters: AuditFilters | None = None
) -> tuple[list[Row], str | None, int]:
    clause, params = _where(filters or AuditFilters())
    keyset, kparams = keyset_clause(req, alias="l", id_column="log_id")
    rows = await fetch_all(
        conn,
        f"SELECT l.log_id AS _row_id, {_SELECT}{_FROM} WHERE {clause}{keyset}",
        [*params, *kparams],
    )
    total = await fetch_one(conn, f"SELECT count(*) AS n {_FROM} WHERE {clause}", params)
    items, cursor = build_page(rows, req)
    return items, cursor, int((total or {}).get("n", 0))


async def summary(conn: Conn, filters: AuditFilters, *, days: int = 30) -> dict[str, Any]:
    """Counts over the rows the filters select: the shape of the answer.

    By event, by group, by the actor's role, and by day for the last `days`;
    plus the span. The same WHERE as the list, so the numbers describe the
    rows on the page and not some other question.
    """
    clause, params = _where(filters)
    span = await fetch_one(
        conn,
        f"SELECT count(*) AS n, min(l.occurred_at) AS first_at, max(l.occurred_at) AS last_at"
        f" {_FROM} WHERE {clause}",
        params,
    ) or {"n": 0, "first_at": None, "last_at": None}
    by_event = await fetch_all(
        conn,
        f"SELECT l.event_type AS key, count(*) AS n {_FROM} WHERE {clause}"
        " GROUP BY l.event_type ORDER BY n DESC, l.event_type LIMIT 12",
        params,
    )
    by_group = await fetch_all(
        conn,
        f"SELECT split_part(l.event_type, '.', 1) AS key, count(*) AS n {_FROM} WHERE {clause}"
        " GROUP BY 1 ORDER BY n DESC, 1",
        params,
    )
    by_role = await fetch_all(
        conn,
        f"SELECT coalesce(actor.role::text, 'system') AS key, count(*) AS n {_FROM}"
        f" WHERE {clause} GROUP BY 1 ORDER BY n DESC, 1",
        params,
    )
    by_day = await fetch_all(
        conn,
        f"SELECT (l.occurred_at AT TIME ZONE 'UTC')::date AS day, count(*) AS n {_FROM}"
        f" WHERE {clause} AND l.occurred_at >= now() - make_interval(days => %s)"
        " GROUP BY 1 ORDER BY 1",
        [*params, days],
    )
    return {
        "total": int(span["n"] or 0),
        "first_at": span["first_at"],
        "last_at": span["last_at"],
        "by_event": [{"key": r["key"], "count": int(r["n"])} for r in by_event],
        "by_group": [{"key": r["key"], "count": int(r["n"])} for r in by_group],
        "by_actor_role": [{"key": r["key"], "count": int(r["n"])} for r in by_role],
        "by_day": [{"day": r["day"], "count": int(r["n"])} for r in by_day],
        "days": days,
    }


async def export_rows(conn: Conn, filters: AuditFilters, *, limit: int = EXPORT_LIMIT) -> list[Row]:
    """The rows the filters select, newest first, bounded for a download."""
    clause, params = _where(filters)
    return await fetch_all(
        conn,
        f"SELECT {_SELECT}{_FROM} WHERE {clause} ORDER BY l.occurred_at DESC, l.log_id DESC"
        " LIMIT %s",
        [*params, limit],
    )


async def by_uuid(conn: Conn, log_uuid: str) -> Row | None:
    return await fetch_one(conn, f"SELECT {_SELECT}{_FROM} WHERE l.log_uuid = %s", (log_uuid,))


async def for_subject(conn: Conn, subject_user_id: int, *, limit: int = 50) -> list[Row]:
    """ "What has happened to my data" - the DSAR query.

    Backed by idx_audit_subject. Only the events she is told about
    (`SUBJECT_VISIBLE`): what she did, what was done with her data, and how
    her request moved. The office's working is not hers to see.
    """
    return await fetch_all(
        conn,
        f"""
        SELECT {_SELECT}{_FROM}
        WHERE l.subject_user_id = %s
          AND l.event_type = ANY(%s)
        ORDER BY l.occurred_at DESC
        LIMIT %s
        """,
        (subject_user_id, sorted(SUBJECT_VISIBLE), limit),
    )


def visible_to_subject(rows: list[Row]) -> list[Row]:
    """The rows of a trail a data principal is shown: the same rule as her feed."""
    return [r for r in rows if str(r["event_type"]) in SUBJECT_VISIBLE]


async def for_reference(conn: Conn, reference: str, *, limit: int = 200) -> list[Row]:
    """Every row about one rights request, whichever table each names.

    A request's trail spans four tables - the request, its holders, its scope
    items, a nomination - so matching on the entity would need four branches
    and miss the next one. Every rights event carries the reference in its
    detail instead, and this reads that. Oldest first: a trail is a story.
    """
    return await fetch_all(
        conn,
        f"""
        SELECT {_SELECT}{_FROM}
        WHERE l.detail_json->>'reference' = %s
        ORDER BY l.occurred_at ASC, l.log_id ASC
        LIMIT %s
        """,
        (reference, limit),
    )


async def event_counts(conn: Conn, *, days: int = 7) -> list[Row]:
    return await fetch_all(
        conn,
        """
        SELECT event_type, count(*) AS n
        FROM audit_log
        WHERE occurred_at >= now() - make_interval(days => %s)
        GROUP BY event_type ORDER BY n DESC LIMIT 25
        """,
        (days,),
    )


async def denial_counts(conn: Conn, *, days: int = 7) -> int:
    row = await fetch_one(
        conn,
        """SELECT count(*) AS n FROM audit_log
           WHERE event_type = 'auth.access_denied'
             AND occurred_at >= now() - make_interval(days => %s)""",
        (days,),
    )
    return int((row or {}).get("n", 0))


# --------------------------------------------------------------- scoped feed
#
# Which audit rows belong to a project.
#
# The trail records what was touched as `(entity_type, entity_id)` — a table
# name and a surrogate key — because that is the only reference guaranteed to
# stay valid. Turning that back into "which project was this about" needs one
# join per table, and this is the map.
#
# Written as a UNION rather than a chain of ORs over LEFT JOINs so each branch
# uses its own index, and so a table added here cannot accidentally widen the
# others. A type absent from this map contributes no rows, which is the safe
# direction: a new entity type is invisible to the feed until somebody maps it,
# rather than leaking into everyone's.
_ENTITY_TO_PROJECT = """
  SELECT 'project'::text AS t, project_id AS id, project_id AS project_id FROM project
  UNION ALL SELECT 'notice', notice_id, project_id FROM notice
  UNION ALL SELECT 'project_site', site_id, project_id FROM project_site
  UNION ALL SELECT 'project_approval', approval_id, project_id FROM project_approval
  UNION ALL SELECT 'export_log', export_id, project_id FROM export_log
  UNION ALL SELECT 'collection', collection_id, project_id FROM collection
  UNION ALL SELECT 'consent_link', cl.link_id, n.project_id
              FROM consent_link cl JOIN notice n ON n.notice_id = cl.notice_id
  UNION ALL SELECT 'consent_artefact', ca.consent_id, n.project_id
              FROM consent_artefact ca JOIN notice n ON n.notice_id = ca.notice_id
"""


async def for_projects(conn: Conn, project_ids: Sequence[int], *, limit: int = 25) -> list[Row]:
    """Recent activity on a set of projects.

    This is what a dashboard's "recent activity" should be, and what it was not:
    the R&D User's showed rows from `project` ordered by `updated_at`, which
    says *that* something changed and never what or by whom. A person looking at
    it could see their project had moved and had to go elsewhere to find out who
    moved it.

    Same rows, same shape and same resolver as the DPO's audit trail — narrowed
    to projects the caller can reach. One feed, one renderer, and no second
    definition of what an activity entry is.

    An empty `project_ids` returns nothing rather than everything. That is worth
    stating: the natural SQL for "in this list" degenerates to a tautology on an
    empty list in some dialects, and the failure would be silent and total.
    """
    if not project_ids:
        return []

    return await fetch_all(
        conn,
        f"""
        SELECT {_SELECT}{_FROM}
        JOIN ({_ENTITY_TO_PROJECT}) m
          ON m.t = l.entity_type AND m.id = l.entity_id
        WHERE m.project_id = ANY(%s)
          AND l.event_type <> ALL(%s)
        ORDER BY l.occurred_at DESC
        LIMIT %s
        """,
        (list(project_ids), list(_NOT_ACTIVITY), limit),
    )


async def by_actor(conn: Conn, actor_user_id: int, *, limit: int = 25) -> list[Row]:
    """What this person did, most recent first.

    Complements `for_projects`: an R&D User's own actions are theirs to see even
    where the project has since moved to somebody else's scope.
    """
    return await fetch_all(
        conn,
        f"""
        SELECT {_SELECT}{_FROM}
        WHERE l.actor_user_id = %s
          AND l.event_type <> ALL(%s)
        ORDER BY l.occurred_at DESC
        LIMIT %s
        """,
        (actor_user_id, list(_NOT_ACTIVITY), limit),
    )


#: What the office does to a ticket, which its respondent should hear about.
_TO_HOLDER = (
    "rights.ticket_issued",
    "rights.ticket_withdrawn",
    "rights.ticket_reassigned",
    "rights.ticket_reminded",
    "rights.ticket_sent_back",
    "rights.ticket_escalated",
)


async def ticket_events_for_responder(
    conn: Conn, responder_user_id: int, *, limit: int = 50
) -> list[Row]:
    """What happened on the tickets addressed to this person, most recent
    first: issued, sent back, withdrawn, reassigned, reminded, and every
    message the office wrote. Carries the ticket's uuid so the feed can open
    the ticket itself rather than a request page the reader may not reach."""
    return await fetch_all(
        conn,
        f"""
        SELECT {_SELECT}, h.holder_uuid::text AS holder_uuid
        {_FROM}
        JOIN rights_request_holder h ON h.holder_id = l.entity_id
        WHERE l.entity_type = 'rights_request_holder'
          AND h.responder_user_id = %s
          AND (l.event_type = ANY(%s)
               OR (l.event_type = 'rights.ticket_message'
                   AND l.detail_json->>'side' = 'office'))
        ORDER BY l.occurred_at DESC
        LIMIT %s
        """,
        (responder_user_id, list(_TO_HOLDER), limit),
    )


async def ticket_events_for_office(conn: Conn, *, limit: int = 50) -> list[Row]:
    """What holders did on their tickets, for the office: every return and
    every message a holder wrote, most recent first."""
    return await fetch_all(
        conn,
        f"""
        SELECT {_SELECT}
        {_FROM}
        WHERE l.entity_type = 'rights_request_holder'
          AND (l.event_type = 'rights.ticket_returned'
               OR (l.event_type = 'rights.ticket_message'
                   AND l.detail_json->>'side' = 'holder'))
        ORDER BY l.occurred_at DESC
        LIMIT %s
        """,
        (limit,),
    )


async def for_consent(conn: Conn, consent_ids: Sequence[int], *, limit: int = 100) -> list[Row]:
    """Everything recorded about one consent, oldest first.

    Takes a *set* of ids because a consent is a chain: giving it writes one
    artefact, withdrawing writes another that supersedes it, and a partial
    change writes a third. Asking for the trail of "this consent" means the
    whole chain, or the answer stops at whichever link the person happened to
    open.

    Ordered oldest-first, unlike every other feed here. A trail is read as a
    story — served, agreed, disclosed, withdrawn — and a story told backwards
    from an arbitrary point is harder to follow than one that starts at the
    start. There are rarely more than a handful of entries.
    """
    if not consent_ids:
        return []

    return await fetch_all(
        conn,
        f"""
        SELECT {_SELECT}{_FROM}
        WHERE l.entity_type = 'consent_artefact' AND l.entity_id = ANY(%s)
        ORDER BY l.occurred_at ASC
        LIMIT %s
        """,
        (list(consent_ids), limit),
    )


async def recent(conn: Conn, *, limit: int = 15, event_type: str | None = None) -> list[Row]:
    """The latest entries across every project.

    Unscoped, so only for callers who already read every row — a DPO and an
    administrator. There is no `user_id` parameter, and there should not be one:
    a scoped feed is `for_projects`, and a function that could do either
    depending on an argument is a function somebody will call with the wrong
    argument.
    """
    clause = "WHERE l.event_type = %s" if event_type else ""
    params: list[Any] = [event_type] if event_type else []
    return await fetch_all(
        conn,
        f"SELECT {_SELECT}{_FROM} {clause} ORDER BY l.occurred_at DESC LIMIT %s",
        [*params, limit],
    )
