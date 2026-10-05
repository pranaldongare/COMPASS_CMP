"""Dashboards and notifications - 3 endpoints.

One `/dashboard` endpoint, role-aware, rather than five. The response shape
differs by role but the call does not, so the SPA has one loading path.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import Field

from cmp.api.dependencies import CurrentUser
from cmp.api.routers.v1.breaches import BreachSummaryOut
from cmp.core.errors import Forbidden, NotFound
from cmp.core.permissions import Role
from cmp.db.pool import connection, transaction
from cmp.db.repositories import audit as audit_repo
from cmp.db.repositories import dashboard as dashboard_repo
from cmp.db.repositories import entities as entity_repo
from cmp.db.repositories import projects as project_repo
from cmp.db.repositories import rights as rights_repo
from cmp.db.repositories import users as user_repo
from cmp.domain.breach import service as breach_service
from cmp.schemas.common import Acknowledged, Out

router = APIRouter(tags=["dashboard"])


class AttentionRow(Out):
    """One thing that needs this person today: a count, how urgent it is,
    and where to act on it. Rows with nothing to count are not sent."""

    key: str
    label: str
    count: int
    severity: str  # critical | warning | info
    href: str


class Dashboard(Out):
    role: str
    counts: dict[str, int]
    queues: list[dict[str, Any]]
    recent: list[dict[str, Any]]
    attention: list[AttentionRow] = Field(default_factory=list)
    #: The DPO's alone: every open breach, each duty's state and clock (S3-04).
    #: Empty for every other role, who cannot know a breach is open.
    breaches: list[BreachSummaryOut] = Field(default_factory=list)


def _slug(name: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")


#: Where a queue's "all N" goes, by queue name. Queues not named here link
#: to nothing beyond their own rows.
_QUEUE_HREF = {
    "Rights requests, soonest due first": "/requests",
    "Tickets past their date": "/requests?status=awaiting_holders",
    "Teams have written on their tickets": "/requests?unread=1",
    "Drafts whose purposes are not activated": "/projects?status=in_draft",
    "Pending Approval": "/projects?status=pending_approval",
    "Tickets addressed to you": "/tickets",
    "Needs your action": "/projects",
    "Grievances about the DPO - yours to review": "/requests?type=grievance",
    "Approved projects ready to collect": "/projects?status=approved",
    "Waiting for DPO review": "/projects?status=pending_approval",
    "Sites awaiting a data source": "/sites",
    "Processors with no collection set up": "/projects",
    "Import exceptions": "/collections",
}

#: What needs each role today, in priority order. Each row names where its
#: count comes from - a counts key or a queue - and where acting on it goes.
#: An anchor href points at the queue further down the same page.
#:
#: The rule for a row: the role can *do* something about it, today, from the
#: page the href opens. A count the role can only look at - lockouts that
#: clear on their own, a source somebody suspended on purpose, a draft that
#: is its author's to finish, refusals in the log - is information, and lives
#: in the queues and stats below, not here. A list of things you cannot act
#: on teaches people to stop reading the list.
_ATTENTION: dict[str, list[dict[str, Any]]] = {
    "dpo": [
        # A breach duty past its due time, or past the internal target for
        # "without delay" once one is set, is the most urgent thing there is.
        {
            "count": "breach_duties_late",
            "label": "Breach duties overdue",
            "severity": "critical",
            "href": "/breaches",
        },
        {
            "count": "breach_duties_outstanding",
            "label": "Breach duties outstanding",
            "severity": "warning",
            "href": "/breaches",
        },
        {
            "queue": "Tickets past their date",
            "label": "Tickets past their date",
            "severity": "critical",
        },
        {
            "count": "requests_overdue",
            "label": "Rights requests overdue",
            "severity": "critical",
            "href": "/requests?overdue=1",
        },
        {
            "count": "requests_due_7d",
            "label": "Rights requests due within 7 days",
            "severity": "warning",
            "href": "/requests?due_soon=1",
        },
        {
            "count": "requests_unverified",
            "label": "Requests awaiting verification",
            "severity": "warning",
            "href": "/requests?status=received",
        },
        {
            "queue": "Teams have written on their tickets",
            "label": "Teams have written on their tickets",
            "severity": "warning",
            "href": "/requests?unread=1",
        },
        {
            # Only the ones the DPO can still act on: escalating them to the
            # administrator. Once escalated, they are the administrator's.
            "count": "grievances_to_escalate",
            "label": "Grievances about the DPO to escalate",
            "severity": "warning",
            "href": "/requests?type=grievance",
        },
        {
            "queue": "Retention floors passed - erasure due",
            "label": "Retention floors passed, erasure due",
            "severity": "warning",
        },
        {
            "count": "tickets_for_me",
            "label": "Tickets addressed to you",
            "severity": "warning",
            "href": "/tickets",
        },
        {
            "count": "unapproved_languages",
            "label": "Notice text awaiting approval",
            "severity": "info",
            "href": "/notices?languages=unapproved",
        },
        {
            "count": "pending_approval",
            "label": "Projects pending approval",
            "severity": "info",
            "href": "/projects?status=pending_approval",
        },
        {
            "queue": "New collectors awaiting your decision",
            "label": "New collectors awaiting your decision",
            "severity": "info",
        },
    ],
    "admin": [
        {
            # Staff accounts whose owner has not yet accepted the invitation.
            # The administrator's move is to resend it; a data principal in
            # the same status is finishing her own sign-up, and is not counted.
            "count": "staff_invites_pending",
            "label": "Staff invitations not yet accepted",
            "severity": "warning",
            "href": "/users?status=pending",
        },
        {
            "count": "grievances_about_dpo",
            "label": "Grievances about the DPO to review",
            "severity": "warning",
            "href": "/requests?type=grievance",
        },
        {
            "count": "tickets_for_me",
            "label": "Tickets addressed to you",
            "severity": "warning",
            "href": "/tickets",
        },
    ],
    "dco": [
        {
            "overdue_tickets": True,
            "label": "Tickets past their date",
            "severity": "critical",
            "href": "/tickets",
        },
        {
            "count": "tickets_for_me",
            "label": "Tickets addressed to you",
            "severity": "warning",
            "href": "/tickets",
        },
        {
            "queue": "Import exceptions",
            "label": "Imports that did not reconcile",
            "severity": "warning",
        },
        {
            "count": "flagged_assets",
            "label": "Assets with unmapped subjects",
            "severity": "warning",
            "href": "/collections",
        },
    ],
    "dco_admin": [
        {
            "overdue_tickets": True,
            "label": "Tickets past their date",
            "severity": "critical",
            "href": "/tickets",
        },
        {
            "count": "sites_awaiting_source",
            "label": "Sites awaiting a data source",
            "severity": "warning",
        },
        {
            "count": "sources_without_owner",
            "label": "Sources with nobody accountable",
            "severity": "warning",
            "href": "/sources?unowned=1",
        },
        {
            "queue": "Processors with no collection set up",
            "label": "Processors with no collection set up",
            "severity": "info",
        },
        {
            "count": "tickets_for_me",
            "label": "Tickets addressed to you",
            "severity": "warning",
            "href": "/tickets",
        },
    ],
    "rnd_user": [
        {
            "queue": "Needs your action",
            "label": "Projects needing something from you",
            "severity": "warning",
        },
        {
            "count": "tickets_for_me",
            "label": "Tickets addressed to you",
            "severity": "warning",
            "href": "/tickets",
        },
    ],
}
_ATTENTION["rco"] = _ATTENTION["dco"]


def _attention(
    role: str, counts: dict[str, int], queues: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """The rows for this role with something to count, in priority order."""
    by_name = {q["name"]: q for q in queues}
    rows: list[dict[str, Any]] = []
    for spec in _ATTENTION.get(role, []):
        if "count" in spec:
            n = int(counts.get(spec["count"], 0) or 0)
            key = spec["count"]
        elif "queue" in spec:
            n = len(by_name.get(spec["queue"], {}).get("items", []))
            key = _slug(spec["queue"])
        else:
            tickets = by_name.get("Tickets addressed to you", {}).get("items", [])
            n = sum(1 for t in tickets if t.get("overdue"))
            key = "tickets_overdue"
        if n <= 0:
            continue
        href = spec.get("href") or (
            f"#q-{_slug(spec['queue'])}" if "queue" in spec else "/dashboard"
        )
        if "count" in spec and spec["count"] == "sites_awaiting_source":
            href = "#q-" + _slug("Sites awaiting a data source")
        rows.append(
            {
                "key": key,
                "label": spec["label"],
                "count": n,
                "severity": spec["severity"],
                "href": href,
            }
        )
    return rows


async def _tickets_for_me(conn: Any, user_id: int) -> tuple[int, list[dict[str, Any]]]:
    """Open tickets addressed to this account: a holder on somebody's rights
    request that is one of our own teams, answered on the portal."""
    rows = await rights_repo.tickets_for_user(conn, user_id, open_only=True)
    items = [
        {
            "holder_uuid": str(r["holder_uuid"]),
            "reference": r["reference"],
            "subject_name": r.get("subject_name"),
            "action": (
                f"Return the ticket for {r['label']}"
                + (
                    f" · {int(r.get('unread_for_holder') or 0)} new from the Privacy Office"
                    if int(r.get("unread_for_holder") or 0)
                    else ""
                )
            ),
            "due_at": r["due_at"].isoformat() if r.get("due_at") else None,
            "overdue": bool(r.get("due_at") and r["due_at"] < datetime.now(UTC)),
            "ticket": True,
        }
        for r in rows
    ]
    return len(items), items


@router.get("/dashboard", response_model=Dashboard, summary="Role-aware aggregate")
async def dashboard(principal: CurrentUser) -> dict[str, Any]:
    async with connection() as conn:
        data: dict[str, Any]
        match principal.role:
            case Role.RND_USER:
                data = await _rnd(conn, principal.user_id)
            case Role.DPO:
                data = await _dpo(conn)
            case Role.DCO | Role.RCO:
                # One dashboard. An RCO is accountable for collection the R&D
                # team does itself and a DCO for a third party's, but the work
                # in front of them - links, consents, import gaps - is the same
                # work, and two near-identical dashboards would drift.
                data = await _dco(conn, principal.user_id, role=principal.role)
            case Role.DCO_ADMIN:
                data = await _dco_admin(conn, principal.user_id)
            case Role.ADMIN:
                data = await _admin(conn)
            case Role.DATA_SUBJECT:
                return await _subject(conn, principal.user_id)
            case _:
                raise Forbidden("No dashboard for this role")
        # Every member of staff, whatever their role: a rights request's
        # holder that is one of our own teams is answered by whoever that team
        # named, and their ticket has to be in front of them.
        count, items = await _tickets_for_me(conn, principal.user_id)
        data["counts"]["tickets_for_me"] = count
        if items:
            data["queues"].append({"name": "Tickets addressed to you", "items": items})
        _finish_queues(data["queues"])
        data["attention"] = _attention(data["role"], data["counts"], data["queues"])
        return data


#: Every queue on the dashboard is cut at this many rows by its query.
QUEUE_LIMIT = 25

#: Where a row opens when it is about something other than its project. The
#: card's own rule picks the project first, which sent an import exception and a
#: site awaiting its source to the top of a project page (UX review 2026-10-05).
_ITEM_HREF: dict[str, Any] = {
    "Import exceptions": lambda r: f"/collections/{r['collection_uuid']}",
    "Sites awaiting a data source": lambda r: f"/projects/{r['project_uuid']}#sites",
    "Processors with no collection set up": lambda r: f"/projects/{r['project_uuid']}#sites",
}


def _finish_queues(queues: list[dict[str, Any]]) -> None:
    """Anchor, list link, row destinations, and whether the queue is complete.

    `capped` says the query stopped at its limit, so the count shown is a floor
    and not the whole list - "All 25" was claiming completeness it did not have.
    """
    for q in queues:
        q["slug"] = _slug(q["name"])
        q["href"] = _QUEUE_HREF.get(q["name"])
        q["capped"] = len(q["items"]) >= QUEUE_LIMIT
        destination = _ITEM_HREF.get(q["name"])
        if destination:
            q["items"] = [{**item, "href": destination(item)} for item in q["items"]]


async def _recent_activity(
    conn: Any, *, project_ids: list[int], actor_id: int, role: Role
) -> list[Any]:
    """Recent activity, in the shape the audit trail uses.

    This replaced two queries that read the wrong thing. The R&D User's read
    `project` ordered by `updated_at`, and the DCO's read `export_log`: both
    said *that* something happened, neither said what or who. Somebody seeing
    their project had moved had to go elsewhere to find out who moved it.

    Now the same rows, the same resolver and the same renderer as the DPO's
    audit trail, narrowed to what the caller can reach. Their own actions are
    merged in because a project can leave their scope after they acted on it,
    and their own history should not vanish with it.
    """
    on_projects = await audit_repo.for_projects(conn, project_ids, limit=25)
    mine = await audit_repo.by_actor(conn, actor_id, limit=25)

    # Merge and de-duplicate: an action on your own project appears in both.
    seen: set[str] = set()
    merged = []
    for row in sorted([*on_projects, *mine], key=lambda r: r["occurred_at"], reverse=True):
        key = str(row["log_uuid"])
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)

    # The same resolver the audit trail uses, so "Notice published" carries the
    # notice it was about rather than `notice#42`.
    return await entity_repo.attach(conn, merged[:15], reader_role=role)


async def _rnd(conn: Any, user_id: int) -> dict[str, Any]:
    """Own projects by status; what needs their action."""
    counts = await dashboard_repo.rnd_counts(conn, user_id)
    # A draft with no proof-bearing approval is precisely what they must act on:
    # it is the last requirement between them and submitting for review, and the
    # one most easily forgotten because the proof comes from somebody else.
    queue = await dashboard_repo.rnd_queue(conn, user_id)
    own_projects = await dashboard_repo.projects_created_by(conn, user_id)
    recent = await _recent_activity(
        conn,
        project_ids=[r["project_id"] for r in own_projects],
        actor_id=user_id,
        role=Role.RND_USER,
    )
    # Apart from what needs them: a project with the DPO is waiting, and
    # listing it as their action would be wrong (UX review 2026-10-05).
    waiting = await dashboard_repo.rnd_waiting_on_dpo(conn, user_id)
    return {
        "role": "rnd_user",
        "counts": _ints(counts),
        "queues": [
            {"name": "Needs your action", "items": queue},
            {"name": "Waiting for DPO review", "items": waiting},
        ],
        "recent": recent,
    }


async def _dpo(conn: Any) -> dict[str, Any]:
    counts = await dashboard_repo.dpo_counts(conn)
    # Drafts where the DPO has something to do, rather than every draft.
    #
    # It used to list them all, with the action "Review and publish the notice"
    # - and a DPO who followed that row arrived at a project whose transition
    # card reads "There is nothing for your role to do at this stage", because
    # the only move out of draft belongs to the author. The one thing that *is*
    # theirs on a draft is activating the purposes an imported document left.
    #
    # Nobody is held up by it: the author submits whenever they are ready, and
    # the activation gates the DPO's own approval. So this is work brought
    # forward rather than work owed, and the queue says so - it is not in
    # "Needs attention", and the name does not claim anyone is waiting.
    draft_queue = await dashboard_repo.dpo_draft_queue(conn)
    approval_queue = await dashboard_repo.dpo_approval_queue(conn)
    # Amendments to projects the DPO has already approved. Its own queue rather
    # than a row in the approval one: those are projects waiting to start, this
    # is a live project waiting to expand, and the second is easy to leave
    # sitting because nothing about it looks stalled.
    amendments = await project_repo.pending_processor_requests(conn)
    denials = await audit_repo.denial_counts(conn, days=7)
    # Rights requests run on a statutory clock, which is what makes them the
    # most time-bound work on this screen. Soonest due first, and the retained
    # erasures whose floor has passed - the ones nothing else would surface.
    rights_counts = await rights_repo.counts(conn)
    rights_queue = await rights_repo.queue(conn, role=Role.DPO, user_id=0)
    # Teams that have written on their tickets and not been read: the office's
    # side of the conversation, surfaced where the rest of its work is.
    overdue = [
        {
            "request_uuid": str(r["request_uuid"]),
            "reference": r["reference"],
            "subject_name": r.get("subject_name"),
            "action": (
                f"{r['label']} is past its date"
                + (" - escalated" if r.get("escalated_at") else " - not yet escalated")
                + (
                    f" · {int(r.get('reminders_sent') or 0)} reminder(s) sent"
                    if int(r.get("reminders_sent") or 0)
                    else ""
                )
            ),
            "due_at": r["due_at"].isoformat() if r.get("due_at") else None,
            "overdue": True,
        }
        for r in await rights_repo.holders_overdue(conn)
    ]
    replies = [
        {
            "request_uuid": str(r["request_uuid"]),
            "reference": r["reference"],
            "subject_name": r.get("subject_name"),
            "action": f"{r['label']} wrote on its ticket · {int(r['unread'])} unread",
            "due_at": r["due_at"].isoformat() if r.get("due_at") else None,
        }
        for r in await rights_repo.holders_awaiting_office(conn)
    ]
    floors = await rights_repo.floor_queue(conn, _today())
    # Full audit rows, resolved, so the dashboard panel and the audit page are
    # the same renderer over the same data. The partial projection this replaced
    # could not carry an entity reference, which is the half that says *what*
    # was published rather than only that something was.
    # Sign-ins are the administrator's business; on the DPO's page they bury
    # the events that mean something. Fetch wider, keep the first eight that
    # are not authentication.
    recent = await entity_repo.attach(
        conn,
        [
            e
            for e in await audit_repo.recent(conn, limit=60)
            if not str(e["event_type"]).startswith("auth.")
        ][:8],
        reader_role=Role.DPO,
    )
    breaches = await breach_service.register(conn, status="open")
    duties = [d for b in breaches for d in b["obligations"] if d["state"] == "outstanding"]
    return {
        "role": "dpo",
        "counts": {
            **_ints(counts),
            **_ints(rights_counts),
            "access_denials_7d": denials,
            "pending_processors": len(amendments),
            "open_breaches": len(breaches),
            "breach_duties_outstanding": len(duties),
            "breach_duties_late": sum(
                1 for d in duties if d["clock"]["overdue"] or d["clock"]["past_target"]
            ),
        },
        "breaches": breaches,
        # Most urgent first: work already late, then the statutory clock, then
        # what others are waiting on, then decisions, then work brought forward.
        # Overdue tickets used to sit below the whole rights queue (UX review).
        "queues": [
            {"name": "Tickets past their date", "items": overdue},
            {"name": "Rights requests, soonest due first", "items": rights_queue},
            {"name": "Teams have written on their tickets", "items": replies},
            {"name": "Retention floors passed - erasure due", "items": floors},
            {"name": "Pending Approval", "items": approval_queue},
            {"name": "New collectors awaiting your decision", "items": amendments},
            {"name": "Drafts whose purposes are not activated", "items": draft_queue},
        ],
        "recent": recent,
    }


async def _dco(conn: Any, user_id: int, *, role: Role = Role.DCO) -> dict[str, Any]:
    counts = await dashboard_repo.dco_counts(conn, user_id)
    # Declared-against-mapped gaps: the control that makes direct collection workable.
    exceptions = await dashboard_repo.dco_exceptions(conn, user_id)
    # Projects in this caller's *read* scope. The predicate is imported rather
    # than restated: it used to be copied here under a comment promising the
    # feed and the project list could not show different worlds, and a copy is
    # exactly how they come to.
    in_scope = await dashboard_repo.projects_in_scope(conn, role, user_id)
    recent = await _recent_activity(
        conn, project_ids=[r["project_id"] for r in in_scope], actor_id=user_id, role=role
    )
    # On a quiet day, the work they can start - not only a clear queue and an
    # activity log (UX review 2026-10-05).
    ready = await dashboard_repo.ready_to_collect(conn, role, user_id)
    return {
        "role": str(role),
        "counts": _ints(counts),
        "queues": [
            {"name": "Import exceptions", "items": exceptions},
            {"name": "Approved projects ready to collect", "items": ready},
        ],
        "recent": recent,
    }


async def _dco_admin(conn: Any, user_id: int) -> dict[str, Any]:
    """The routing queue.

    A DCO Admin's job has one shape: approved projects collected by a third party
    whose sites have no data source attached yet. Until one is, no consent link
    can be minted for that site and nobody is accountable for it - the project is
    approved and stalled, and nothing else in the system says so.
    """
    counts = await dashboard_repo.dco_admin_counts(conn)
    awaiting = await dashboard_repo.dco_admin_awaiting(conn)

    # A processor the DPO has just agreed to, with no collection set up under it
    # yet. The site queue above cannot show this - there are no sites to show -
    # so without it a newly approved partner is invisible to the person whose
    # job is to set it up.
    fresh = await dashboard_repo.dco_admin_fresh(conn)

    in_scope = await dashboard_repo.projects_in_scope(conn, Role.DCO_ADMIN, user_id)
    recent = await _recent_activity(
        conn,
        project_ids=[r["project_id"] for r in in_scope],
        actor_id=user_id,
        role=Role.DCO_ADMIN,
    )
    return {
        "role": "dco_admin",
        "counts": _ints(counts),
        "queues": [
            # The DCO Admin's core job first: sites waiting for their source.
            {"name": "Sites awaiting a data source", "items": awaiting},
            {"name": "Processors with no collection set up", "items": fresh},
        ],
        "recent": recent,
    }


async def _admin(conn: Any) -> dict[str, Any]:
    by_status = await user_repo.count_by_status(conn)
    by_role = await user_repo.count_by_role(conn)
    invites = await dashboard_repo.staff_invites_pending(conn)
    suspended = await dashboard_repo.inactive_registry_rows(conn)
    # An administrator's "recent" is refusals, not activity: they provision
    # accounts rather than run collections, and a denial is the signal they act
    # on. Same shape as every other role's, so one renderer serves all five.
    denials = await entity_repo.attach(
        conn,
        await audit_repo.recent(conn, limit=25, event_type="auth.access_denied"),
        reader_role=Role.ADMIN,
    )
    lockouts = await dashboard_repo.recent_lockouts(conn)
    # Grievances about the DPO: the one kind of rights request that reaches the
    # administrator, as the reviewer the DPO cannot be.
    escalated = await rights_repo.queue(conn, role=Role.ADMIN, user_id=0)
    return {
        "role": "admin",
        "counts": {
            **{f"users_{k}": v for k, v in by_status.items()},
            **{f"role_{k}": v for k, v in by_role.items()},
            "suspended_registry_rows": len(suspended),
            "staff_invites_pending": int((invites or {}).get("n", 0) or 0),
            "grievances_about_dpo": len(escalated),
        },
        "queues": [
            {"name": "Grievances about the DPO - yours to review", "items": escalated},
            {"name": "Lockouts (24h)", "items": lockouts},
            {"name": "Suspended sources and processors", "items": suspended},
        ],
        "recent": denials,
    }


async def _subject(conn: Any, user_id: int) -> dict[str, Any]:
    counts = await dashboard_repo.subject_counts(conn, user_id)
    recent = await audit_repo.for_subject(conn, user_id, limit=10)
    requests = await rights_repo.subject_counts(conn, user_id)
    return {
        "role": "data_subject",
        "counts": {**_ints(counts), **_ints(requests)},
        "queues": [],
        "recent": recent,
    }


def _today() -> Any:
    from datetime import UTC, datetime

    return datetime.now(UTC).date()


def _ints(row: dict[str, Any] | None) -> dict[str, int]:
    return {k: int(v or 0) for k, v in (row or {}).items()}


@router.get("/notifications")
async def notifications(
    principal: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict[str, Any]:
    """Derived from the audit trail rather than a separate table.

    There is no notifications table among the 22, and deriving the feed means it
    can never disagree with the record it is describing.
    """
    async with connection() as conn:
        if principal.role is Role.DATA_SUBJECT:
            rows = await audit_repo.for_subject(conn, principal.user_id, limit=limit)
        else:
            # Only what the reader can open. The feed used to be every event
            # on the platform for every member of staff, and for anyone whose
            # scope is narrower than the DPO's - an R&D user, a DCO - most of
            # its links led to a project or notice their role answers 404 for.
            # The same predicate the project register uses decides here: an
            # event about a project, or about a notice on one, is shown to the
            # people who could see that project in the register. Events with
            # no project - a lockout, a withdrawal - stay with the roles whose
            # section they belong to.
            rows = await dashboard_repo.staff_feed(
                conn, principal.role, principal.user_id, limit=limit
            )
            # What happened on the tickets addressed to this person, and -
            # for the office - what holders did on theirs. Without these the
            # bell said nothing about the one conversation staff are actually
            # in: a message from the Privacy Office on a ticket reached the
            # mail outbox and nowhere in the console.
            mine = await audit_repo.ticket_events_for_responder(
                conn, principal.user_id, limit=limit
            )
            office = (
                await audit_repo.ticket_events_for_office(conn, limit=limit)
                if principal.role is Role.DPO
                else []
            )
            seen: set[str] = set()
            merged: list[dict[str, Any]] = []
            for r in sorted([*rows, *mine, *office], key=lambda r: r["occurred_at"], reverse=True):
                if str(r["log_uuid"]) in seen:
                    continue
                seen.add(str(r["log_uuid"]))
                merged.append(r)
            rows = merged[:limit]
        # Same resolution the audit trail gets: a notification that says
        # "notice#42 published" tells the reader nothing they can act on.
        #
        # Resolved to the reader's own pages. A data principal's feed is all
        # events about herself, and every one of them used to link into a staff
        # console - `auth_user` to the administrator's account register, which
        # is where following her own registration notification took her.
        rows = await entity_repo.attach(
            conn,
            rows,
            for_subject=principal.role is Role.DATA_SUBJECT,
            reader_role=principal.role,
        )
        # A respondent opens the ticket, not the request page - which their
        # role may not reach. The DPO keeps the request page.
        if principal.role is not Role.DPO:
            for r in rows:
                if r.get("holder_uuid"):
                    r["entity_href"] = f"/tickets?ticket={r['holder_uuid']}"
    return {"items": rows, "next_cursor": None, "total": len(rows)}


@router.post("/notifications/{log_uuid}/resend", response_model=Acknowledged)
async def resend(log_uuid: UUID, principal: CurrentUser) -> dict[str, Any]:
    """Re-deliver a failed notification.

    Restricted to DPO and DCO: re-sending a consent receipt puts a message in
    somebody's inbox, and that is not an action a general user should be able to
    trigger for an arbitrary event.
    """
    if principal.role not in (Role.DPO, Role.DCO):
        raise Forbidden("Your role may not resend notifications")

    async with transaction() as conn:
        entry = await audit_repo.by_uuid(conn, str(log_uuid))
        if not entry:
            raise NotFound("Notification")

        if not entry.get("subject_uuid"):
            raise NotFound("Notification recipient")

        subject = await user_repo.by_uuid(conn, str(entry["subject_uuid"]))
        if not subject:
            raise NotFound("Notification recipient")

    from cmp.tasks.dispatch import dispatch_required
    from cmp.tasks.notifications import send_office_note

    dispatch_required(
        send_office_note,
        [subject["email"]],
        str(entry["event_type"]),
        f"{entry['occurred_at']:%d %B %Y}",
    )
    return {"ok": True, "message": "Queued for delivery."}
