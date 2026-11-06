"""The reports a breach calls for (2026-11-06, ADR 0037).

Five kinds, one path:

| Kind | Goes to | When it may be written |
|---|---|---|
| `org_board` | the organisation's board, mailed by the platform | once recorded as a breach |
| `board_intimation` | the DPDP Board, Rule 7(2)(a) | once recorded |
| `cert_in` | CERT-In | once it is marked reportable, whatever validation says |
| `board_report` | the DPDP Board, Rule 7(2)(b): the 72-hour report | once recorded |
| `closure` | the DPDP Board. Optional: nothing waits for it | once recorded |

* **A draft starts from the register**, section by section, and is the office's
  to rewrite: what is drafted is what a person read and meant. It is never
  regenerated underneath them. A new version starts from the last one's words.
* **Finalising freezes it and mails the organisation's board.** For `org_board`
  that is the whole of it. Its duty completes when the mail has run its course
  and reached somebody, naming only those it reached: queued is not told, and
  if every address fails the duty stays outstanding and its overdue alert
  fires. Every other kind is told to the board for its information and goes no
  further here.
* **The platform never sends to a regulator** (ADR 0021). A person does, and
  files here: the proof of internal approval, the mail they sent, when, and the
  reference that came back. Only then is the regulator's duty done, so no duty
  completes without its proof.
* **A failed mail is on the record**, like a notice's: an address the report
  did not reach says so, and sending again tries only those, and any address
  added to the list since. One still queued long after the worker would have
  finished with it is queued again, as a new attempt: the account is only added
  to, and that row is what makes it read as moving. An address taken off the
  list is never mailed, whatever was waiting for it. One taken off and put back
  is the same address: what it was sent, it is not sent again.
* **One send at a time to one address.** However many tasks a delivery has, the
  worker claims the report and the address before it sends, and a task that
  loses stands down (`cmp.tasks.notifications.breach_reports`).
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Final

from cmp.core.config import settings
from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.db.pool import across_offices
from cmp.db.redis import K_LOCK
from cmp.db.redis import key as rkey
from cmp.db.repositories import breach_reports as repo
from cmp.db.repositories import breaches as breach_repo
from cmp.db.repositories import incident_reports as recipients_repo
from cmp.db.sql import Conn
from cmp.domain.audit.service import Event
from cmp.domain.breach import notices, service
from cmp.domain.breach.clock import Duty, EventKind, State
from cmp.domain.breach.state_machine import Status
from cmp.infrastructure.dkms import unseal_strings
from cmp.infrastructure.pdf import Document, Fields, Heading, Paragraph, render
from cmp.validation.choices import choice

Row = dict[str, Any]

#: Mailed for a report and still queued after this was lost before the worker
#: saw it, as a notice's is (`cmp.domain.breach.notices.STALE_AFTER`).
STALE_AFTER: Final = timedelta(minutes=15)

#: A clock on somebody's laptop may run a little ahead of ours.
_SKEW: Final = timedelta(minutes=5)

#: What a report says when there is nowhere to mail it.
_NOBODY: Final = (
    "Nobody is on the organisation's board list yet. Add their addresses under "
    "Breach settings first"
)


class Kind(StrEnum):
    ORG_BOARD = "org_board"
    BOARD_INTIMATION = "board_intimation"
    CERT_IN = "cert_in"
    BOARD_REPORT = "board_report"
    CLOSURE = "closure"


TITLES: Final[dict[Kind, str]] = {
    Kind.ORG_BOARD: "Report to the organisation's board",
    Kind.BOARD_INTIMATION: "Initial intimation to the DPDP Board",
    Kind.CERT_IN: "Report to CERT-In",
    Kind.BOARD_REPORT: "72-hour report to the DPDP Board",
    Kind.CLOSURE: "Closure report",
}

BASES: Final[dict[Kind, str]] = {
    Kind.ORG_BOARD: "Internal policy",
    Kind.BOARD_INTIMATION: "Rule 7(2)(a)",
    Kind.CERT_IN: "CERT-In Directions 2022 (IT Act s.70B)",
    Kind.BOARD_REPORT: "Rule 7(2)(b)",
    Kind.CLOSURE: "When the matter is concluded",
}

#: The duty a report discharges. A closure report discharges none.
DUTIES: Final[dict[Kind, Duty]] = {
    Kind.ORG_BOARD: Duty.ORG_BOARD,
    Kind.BOARD_INTIMATION: Duty.BOARD_INTIMATION,
    Kind.CERT_IN: Duty.CERT_IN,
    Kind.BOARD_REPORT: Duty.BOARD_REPORT,
}

#: What proves a report was approved, and that it was sent.
PROOFS: Final[dict[str, str]] = {
    "approval": "Proof of internal approval",
    "sent_mail": "The mail sent to the regulator",
}


@dataclass(frozen=True, slots=True)
class Section:
    key: str
    label: str
    #: Finalising is refused while a required section is empty.
    required: bool = True


SECTIONS: Final[dict[Kind, tuple[Section, ...]]] = {
    Kind.ORG_BOARD: (
        Section("what_happened", "What happened"),
        Section("timing", "When"),
        Section("location", "Where it occurred"),
        Section("people", "People affected"),
        Section("duties", "Where the duties stand"),
        Section("next_steps", "What happens next", required=False),
    ),
    Kind.BOARD_INTIMATION: (
        Section("nature_extent", "The nature and extent of the breach"),
        Section("timing", "Its timing"),
        Section("location", "Where it occurred"),
        Section("likely_impact", "Its likely impact"),
    ),
    Kind.CERT_IN: (
        Section("incident", "The incident"),
        Section("timing", "When it occurred and was noticed"),
        Section("affected_systems", "Systems affected"),
        Section("indicators", "What shows it: logs, addresses, files", required=False),
        Section("actions", "Action taken so far"),
    ),
    Kind.BOARD_REPORT: (
        Section("updated_information", "(i) Updated and detailed information"),
        Section("circumstances", "(ii) The events, circumstances and reasons"),
        Section("mitigation", "(iii) Measures implemented or proposed to mitigate the risk"),
        Section("findings", "(iv) Findings on the person who caused the breach"),
        Section("remedial_measures", "(v) Remedial measures to prevent recurrence"),
        Section("notices", "(vi) The account of notices to Data Principals"),
    ),
    Kind.CLOSURE: (
        Section("summary", "Summary of the incident"),
        Section("root_cause", "Root cause"),
        Section("measures", "Measures taken"),
        Section("prevention", "Measures to prevent recurrence"),
        Section("notices", "Data Principals notified"),
        Section("conclusion", "Conclusion"),
    ),
}


def _kind(value: str) -> Kind:
    return choice(Kind, value, field="kind")


def _label(kind: Kind, key: str) -> str:
    return next(s.label for s in SECTIONS[kind] if s.key == key)


def _when(value: datetime | None) -> str:
    from cmp.domain.alerts import moment

    return moment(value) if value else "Not known"


# ------------------------------------------------------------ what a draft says


async def _facts(conn: Conn, breach_uuid: str) -> Row:
    """What the register holds, opened: drafting is reading on the office's
    behalf, and what it writes is sealed again in the section."""
    detail = await service.detail(conn, breach_uuid)
    assessment = detail["assessment"] or {}
    logged = detail["logged"]
    opened = await unseal_strings(
        [
            detail["title"],
            detail["location"]["detail"],
            *assessment.values(),
            *logged.values(),
        ]
    )

    def read(value: Any) -> str:
        return str(opened.get(value, value)) if value else ""

    place = detail["location"]
    where = {
        "processor": f"Processor: {place['processor_name']}",
        "data_source": f"Data source: {place['source_name']}",
        "platform": "The platform's own database",
    }.get(str(place["kind"]), "")
    account = await notices.account_for_report(conn, breach_uuid=breach_uuid)
    duties = "\n".join(f"{d['label']}: {_standing(d)}" for d in detail["obligations"])
    return {
        "reference": detail["reference"],
        "title": read(detail["title"]),
        "timing": "\n".join(
            [
                f"First noticed: {_when(detail['detected_at'])}",
                f"Became aware: {_when(detail['became_aware_at'])}",
                f"Began: {_when(detail['began_at'])}",
            ]
        ),
        "location": "\n".join(x for x in (where, read(place["detail"])) if x),
        "assessment": {k: read(v) for k, v in assessment.items() if isinstance(v, str)},
        "logged": {k: read(v) for k, v in logged.items()},
        "statement": str(account["statement"]),
        "listed": int(account["listed"]),
        "notified": int(account["notified"]),
        "duties": duties,
    }


def _standing(duty: Row) -> str:
    if duty["state"] == State.DONE:
        return f"done {_when(duty['completed_at'])}"
    if duty["state"] == State.NOT_APPLICABLE:
        return "not applicable"
    return f"outstanding, due {_when(duty['due_at'])}" if duty["due_at"] else "due without delay"


def _either(*values: str) -> str:
    return next((v for v in values if v), "")


def _drafted(kind: Kind, facts: Row) -> dict[str, str]:
    """Each section's first words, from what the register holds. What it does
    not hold stays empty, and finalising says so."""
    a, told = facts["assessment"], facts["logged"]
    nature = _either(a.get("nature_extent", ""), told.get("incident_details", ""), facts["title"])
    if kind == Kind.ORG_BOARD:
        return {
            "what_happened": nature,
            "timing": facts["timing"],
            "location": facts["location"],
            "people": f"{facts['listed']} listed as affected; {facts['notified']} notified.",
            "duties": facts["duties"],
        }
    if kind == Kind.BOARD_INTIMATION:
        return {
            "nature_extent": nature,
            "timing": facts["timing"],
            "location": facts["location"],
            "likely_impact": a.get("likely_impact", ""),
        }
    if kind == Kind.CERT_IN:
        return {
            "incident": nature,
            "timing": facts["timing"],
            "affected_systems": told.get("affected_systems", ""),
            "actions": a.get("mitigation", ""),
        }
    if kind == Kind.BOARD_REPORT:
        return {
            "updated_information": "\n\n".join(
                x for x in (nature, a.get("likely_impact", ""), facts["timing"]) if x
            ),
            "circumstances": a.get("circumstances", ""),
            "mitigation": a.get("mitigation", ""),
            "findings": a.get("caused_by_findings", ""),
            "remedial_measures": a.get("remedial_measures", ""),
            "notices": facts["statement"],
        }
    return {
        "summary": nature,
        "root_cause": a.get("circumstances", ""),
        "measures": a.get("mitigation", ""),
        "prevention": a.get("remedial_measures", ""),
        "notices": facts["statement"],
    }


# -------------------------------------------------------------------- drafting


def _may_write(kind: Kind, breach: Row, duties: dict[str, Any]) -> str | None:
    """Why this report must wait, or None. Drafting a CERT-In report waits for
    the mark, not for validation: its clock does not wait for either. Once the
    mark is set aside there is no such report: a draft left open stays a draft,
    and nothing about it reaches the board unless it is marked again."""
    if kind == Kind.CERT_IN:
        found = duties.get(Duty.CERT_IN)
        if found is None:
            return "Mark it reportable to CERT-In first"
        if found[1]["state"] == State.NOT_APPLICABLE:
            return "CERT-In was set aside as not reportable. Mark it reportable again first"
        return None
    return service.not_recorded_reason(breach, "this report is written")


async def draft(conn: Conn, *, breach_uuid: str, kind: str, actor_id: int) -> Row:
    """Start the next version of this kind. One draft of a kind at a time."""
    chosen = _kind(kind)
    breach = await service.locked_open(conn, breach_uuid)
    breach_id = int(breach["breach_id"])
    duties = await service.duties_of(conn, breach_id)
    blocked = _may_write(chosen, breach, duties)
    if blocked:
        raise Conflict(blocked, code="breach_not_recorded")
    mine = [r for r in await repo.on_breach(conn, breach_id) if r["kind"] == chosen]
    if any(r["finalised_at"] is None for r in mine):
        raise Conflict("A draft is already open; edit or finalise it", code="report_draft_open")
    bodies: Row
    if mine:
        kept = await repo.sections_of(conn, [int(mine[0]["report_id"])])
        opened = await unseal_strings([s["body"] for s in kept])
        bodies = {str(s["section_key"]): opened.get(s["body"], s["body"]) for s in kept}
    else:
        bodies = _drafted(chosen, await _facts(conn, breach_uuid))
    made = await repo.create(
        conn,
        breach_id,
        kind=chosen.value,
        sections=[{"key": s.key, "body": bodies.get(s.key)} for s in SECTIONS[chosen]],
        created_by=actor_id,
    )
    await service.record_event(
        conn,
        breach,
        Event.BREACH_REPORT_DRAFTED,
        actor_id=actor_id,
        detail={"kind": chosen.value, "version": int(made["version"])},
    )
    return await overview(conn, breach_uuid=breach_uuid)


async def _report(conn: Conn, breach: Row, report_uuid: str) -> Row:
    report = await repo.by_uuid(conn, int(breach["breach_id"]), report_uuid)
    if report is None:
        raise NotFound("Report")
    return report


async def edit(
    conn: Conn, *, breach_uuid: str, report_uuid: str, bodies: dict[str, str | None], actor_id: int
) -> Row:
    breach = await service.locked_open(conn, breach_uuid)
    report = await _report(conn, breach, report_uuid)
    if report["finalised_at"] is not None:
        raise Conflict(
            "A finalised report does not change; start a new version", code="report_finalised"
        )
    kind = Kind(report["kind"])
    known = {s.key for s in SECTIONS[kind]}
    unknown = sorted(set(bodies) - known)
    if unknown:
        raise ValidationFailed(f"Not a section of this report: {', '.join(unknown)}")
    await repo.write_sections(
        conn,
        int(report["report_id"]),
        {k: (v or "").strip() or None for k, v in bodies.items()},
    )
    await service.record_event(
        conn,
        breach,
        Event.BREACH_REPORT_EDITED,
        actor_id=actor_id,
        detail={"kind": kind.value, "version": int(report["version"])},
    )
    return await overview(conn, breach_uuid=breach_uuid)


# ------------------------------------------------------------------ finalising


async def _board_list(conn: Conn) -> list[Row]:
    board = await recipients_repo.board_recipients(conn)
    if not board:
        raise Conflict(_NOBODY, code="no_board_recipients")
    return board


async def _whom(reached: list[Row]) -> str:
    """Who the board's duty says was told: names where there are names."""
    opened = await unseal_strings([r["full_name"] or r["email"] for r in reached])
    names = [str(opened.get(r["full_name"] or r["email"], "someone")) for r in reached]
    return "By email: " + ", ".join(names)


async def finalise(conn: Conn, *, breach_uuid: str, report_uuid: str, actor_id: int) -> Row:
    """Freeze the words and mail the organisation's board. Nothing here goes
    to a regulator."""
    from cmp.tasks.dispatch import dispatch_optional
    from cmp.tasks.notifications.breach_reports import send_breach_report

    breach = await service.locked_open(conn, breach_uuid)
    report = await _report(conn, breach, report_uuid)
    if report["finalised_at"] is not None:
        raise Conflict("This report is already finalised", code="report_finalised")
    kind = Kind(report["kind"])
    report_id = int(report["report_id"])
    duties = await service.duties_of(conn, int(breach["breach_id"]))
    blocked = _may_write(kind, breach, duties)
    if blocked:
        raise Conflict(blocked, code="breach_not_recorded")
    written = {str(s["section_key"]): s["body"] for s in await repo.sections_of(conn, [report_id])}
    missing = [s for s in SECTIONS[kind] if s.required and not written.get(s.key)]
    if missing:
        raise ValidationFailed(
            "A report says what it is for. Missing: " + "; ".join(s.label for s in missing),
            field=missing[0].key,
            details={"missing": [s.key for s in missing]},
        )
    board = await _board_list(conn)
    await repo.finalise(conn, report_id, finalised_by=actor_id)
    for person in board:
        row = await repo.add_delivery(
            conn, report_id, int(person["recipient_id"]), attempt=1, status="queued"
        )
        if row:
            dispatch_optional(send_breach_report, str(row["delivery_uuid"]))
    await service.record_event(
        conn,
        breach,
        Event.BREACH_REPORT_FINALISED,
        actor_id=actor_id,
        detail={"kind": kind.value, "version": int(report["version"]), "mailed": len(board)},
    )
    return await overview(conn, breach_uuid=breach_uuid)


def _resend_refused(
    kind: Kind, report: Row, mine: list[Row], breach: Row, duties: dict[str, Any], board: list[Row]
) -> Conflict | None:
    """Why this report may not be sent again now, or None. `mine` is every
    version of its kind. What refuses the press also sets `mail.retryable`, so
    the figure and the button cannot disagree."""
    blocked = _may_write(kind, breach, duties)
    if blocked:
        return Conflict(blocked, code="breach_not_recorded")
    if any(r["finalised_at"] is not None and r["version"] > report["version"] for r in mine):
        return Conflict(
            "A later version of this report has been finalised, so this one is not sent again",
            code="report_superseded",
        )
    if not board:
        return Conflict(_NOBODY, code="no_board_recipients")
    return None


async def resend(conn: Conn, *, breach_uuid: str, report_uuid: str, actor_id: int) -> Row:
    """Try again for every address on the list the report has not reached: a
    new attempt after a failure, the first for an address added since, and
    another where one was lost. On the trail only if it queued anything. The
    answer says how many it queued.

    The board's duty is re-read first, whatever follows: a settling that failed
    after the mail was recorded is waiting on nobody but this."""
    from cmp.tasks.dispatch import dispatch_optional
    from cmp.tasks.notifications.breach_reports import send_breach_report

    breach = await service.locked_open(conn, breach_uuid)
    report = await _report(conn, breach, report_uuid)
    if report["finalised_at"] is None:
        raise Conflict("Finalise it first", code="report_not_finalised")
    kind = Kind(report["kind"])
    breach_id = int(breach["breach_id"])
    report_id = int(report["report_id"])
    completed = kind == Kind.ORG_BOARD and await _settle(conn, report_id, breach_id)
    board = await recipients_repo.board_recipients(conn)
    mine = [r for r in await repo.on_breach(conn, breach_id) if r["kind"] == kind]
    refused = _resend_refused(
        kind, report, mine, breach, await service.duties_of(conn, breach_id), board
    )
    if refused:
        if completed:
            return {**await overview(conn, breach_uuid=breach_uuid), "queued": 0}
        raise refused
    states = await repo.latest_states(conn, [report_id])
    lines = {s["email_hash"]: s for s in _by_address(states, board)}
    rows = {int(s["recipient_id"]): s for s in states}
    added = retried = requeued = 0
    stale_before = datetime.now(UTC) - STALE_AFTER
    # The list as it stands: an address taken off it is not tried again.
    for person in board:
        line = lines.get(person["email_hash"])
        if not _owed(line, stale_before):
            continue  # queued recently, or it has the report: nothing to add
        recipient_id = int(person["recipient_id"])
        own = rows.get(recipient_id)
        # A lost delivery takes a new attempt too. The account is only added to,
        # so this row is the one thing that can say it is moving again; the old
        # task, if it ever runs, finds the later attempt and stands down.
        attempt = int(own["last_attempt"]) + 1 if own else 1
        row = await repo.add_delivery(
            conn, report_id, recipient_id, attempt=attempt, status="queued"
        )
        if row:
            added += line is None
            retried += line is not None and line["status"] == "failed"
            requeued += line is not None and line["status"] == "queued"
            dispatch_optional(send_breach_report, str(row["delivery_uuid"]))
    queued = added + retried + requeued
    if queued:
        await service.record_event(
            conn,
            breach,
            Event.BREACH_REPORT_RESENT,
            actor_id=actor_id,
            detail={
                "kind": report["kind"],
                "version": int(report["version"]),
                "queued": queued,
                "added": added,
                "retried": retried,
                "requeued": requeued,
            },
        )
    return {**await overview(conn, breach_uuid=breach_uuid), "queued": queued}


# -------------------------------------------------------------------- filing


def _proof_kind(kind: str) -> None:
    if kind not in PROOFS:
        raise ValidationFailed(f"kind must be one of: {', '.join(PROOFS)}", field="kind")


def _takes_proof(report: Row) -> None:
    if report["kind"] == Kind.ORG_BOARD:
        raise Conflict("A report to the organisation's board is not filed", code="report_not_filed")
    if report["finalised_at"] is None:
        raise Conflict("Finalise the report first", code="report_not_finalised")
    if report["filed_at"] is not None:
        raise Conflict("This report is already filed", code="report_filed")


async def _may_file(conn: Conn, breach: Row, report: Row) -> None:
    """A report is filed on the same terms it is written. Filed with the CERT-In
    mark set aside it would complete nothing, and marking it again would then
    leave the duty with no report to complete it. So: mark it, then file it."""
    duties = await service.duties_of(conn, int(breach["breach_id"]))
    blocked = _may_write(Kind(report["kind"]), breach, duties)
    if blocked:
        raise Conflict(blocked, code="breach_not_recorded")


async def check_proof(conn: Conn, *, breach_uuid: str, report_uuid: str, kind: str) -> None:
    """Whether this proof may be kept, without taking the breach's row: a check
    made before the file is stored, so a refusal leaves nothing behind.
    `add_proof` still makes it under the lock."""
    _proof_kind(kind)
    breach = await service.require_open(conn, breach_uuid)
    report = await _report(conn, breach, report_uuid)
    _takes_proof(report)
    await _may_file(conn, breach, report)


async def add_proof(
    conn: Conn,
    *,
    breach_uuid: str,
    report_uuid: str,
    kind: str,
    note: str | None,
    file_name: str,
    storage_ref: str,
    sha256: str,
    size_bytes: int,
    content_type: str,
    actor_id: int,
) -> Row:
    """Keep the proof with the report, and with the breach's other evidence."""
    _proof_kind(kind)
    breach = await service.locked_open(conn, breach_uuid)
    report = await _report(conn, breach, report_uuid)
    _takes_proof(report)
    await _may_file(conn, breach, report)
    made = await breach_repo.add_attachment(
        conn,
        int(breach["breach_id"]),
        kind=kind,
        note=(note or "").strip() or None,
        file_name=file_name,
        storage_ref=storage_ref,
        sha256=sha256,
        size_bytes=size_bytes,
        content_type=content_type,
        added_by=actor_id,
        report_id=int(report["report_id"]),
    )
    await service.record_event(
        conn,
        breach,
        Event.BREACH_REPORT_PROOF_ADDED,
        actor_id=actor_id,
        detail={
            "kind": report["kind"],
            "version": int(report["version"]),
            "proof": kind,
            "attachment": str(made["attachment_uuid"]),
        },
    )
    return await overview(conn, breach_uuid=breach_uuid)


async def file_report(
    conn: Conn,
    *,
    breach_uuid: str,
    report_uuid: str,
    filed_at: datetime,
    reference: str | None,
    actor_id: int,
) -> Row:
    """Record that a person sent it. Refused without both proofs, and the duty
    completes with it: there is no other way to complete a regulator's duty."""
    breach = await service.locked_open(conn, breach_uuid)
    report = await _report(conn, breach, report_uuid)
    kind = Kind(report["kind"])
    if kind == Kind.ORG_BOARD:
        raise Conflict("A report to the organisation's board is not filed", code="report_not_filed")
    if report["finalised_at"] is None:
        raise Conflict("Finalise the report first", code="report_not_finalised")
    if report["filed_at"] is not None:
        raise Conflict("This report is already filed", code="report_filed")
    await _may_file(conn, breach, report)
    report_id = int(report["report_id"])
    held = {str(e["kind"]) for e in await repo.evidence_of(conn, [report_id])}
    lacking = [label for key, label in PROOFS.items() if key not in held]
    if lacking:
        raise Conflict("Attach the proof first: " + "; ".join(lacking), code="report_proof_missing")
    # It may be earlier than finalising here: a person may have sent it first.
    if filed_at > datetime.now(UTC) + _SKEW:
        raise ValidationFailed("This time is in the future", field="filed_at")
    reference = (reference or "").strip() or None
    duty = DUTIES.get(kind)
    if duty and not reference:
        raise ValidationFailed("Enter the reference the regulator returned", field="reference")
    await repo.file(conn, report_id, filed_at=filed_at, reference=reference, filed_by=actor_id)
    await service.record_event(
        conn,
        breach,
        Event.BREACH_REPORT_FILED,
        actor_id=actor_id,
        detail={"kind": kind.value, "version": int(report["version"])},
    )
    found = (await service.duties_of(conn, int(breach["breach_id"]))).get(duty) if duty else None
    if duty and found and found[1]["state"] == State.OUTSTANDING:
        await service.complete_duty(
            conn,
            breach_uuid=breach_uuid,
            duty=duty.value,
            occurred_at=filed_at,
            reference=reference,
            note=None,
            actor_id=actor_id,
        )
    return await overview(conn, breach_uuid=breach_uuid)


# -------------------------------------------------------------------- reading


def _state(report: Row) -> str:
    if report["filed_at"] is not None:
        return "filed"
    return "finalised" if report["finalised_at"] is not None else "draft"


def _by_address(states: list[Row], board: list[Row]) -> list[Row]:
    """Where each address stands on a report, one line each. Taking an address
    off the list and putting it back makes a second row of the list, not a
    second person: delivered under either is delivered, and otherwise the row
    on the list now speaks for it. `removed` is whether it is off the list now,
    which the row it was mailed under cannot say."""

    def rank(state: Row) -> tuple[bool, bool, datetime]:
        return (
            state["status"] == "delivered",
            state["removed_at"] is None,
            state["recorded_at"],
        )

    listed = {r["email_hash"] for r in board}
    lines: dict[str, Row] = {}
    for s in states:
        held = lines.get(s["email_hash"])
        if held is None or rank(s) > rank(held):
            lines[s["email_hash"]] = s
    return [{**s, "removed": s["email_hash"] not in listed} for s in lines.values()]


def _counts(lines: Iterable[Row]) -> Row:
    """An address off the list is nobody's to act on, so it reads as neither on
    its way nor failed. It stays in the list of addresses, marked."""
    out = {"delivered": 0, "queued": 0, "failed": 0}
    for s in lines:
        if s["status"] == "delivered" or not s["removed"]:
            out[str(s["status"])] += 1
    return out


def _lost(line: Row, stale_before: datetime) -> bool:
    """Queued long after the worker would have finished with it, to an address
    still on the list: sending again is what would move it."""
    return (
        line["status"] == "queued" and line["recorded_at"] <= stale_before and not line["removed"]
    )


def _owed(line: Row | None, stale_before: datetime) -> bool:
    """Whether sending again would queue an address on the list: it was never
    mailed this report, or it failed, or it was lost."""
    return line is None or line["status"] == "failed" or _lost(line, stale_before)


def _mail(states: list[Row], board: list[Row], *, sendable: bool) -> Row:
    """What became of the mail, in all and address by address. The name and the
    address are served sealed. `retryable` is what sending again would queue
    now; none of this is what the board's duty reads (`_settle`)."""
    stale_before = datetime.now(UTC) - STALE_AFTER
    lines = _by_address(states, board)
    standing = {s["email_hash"]: s for s in lines}
    return {
        **_counts(lines),
        "stale": sum(_lost(s, stale_before) for s in lines),
        "retryable": (
            sum(_owed(standing.get(p["email_hash"]), stale_before) for p in board)
            if sendable
            else 0
        ),
        "recipients": [
            {
                "recipient_uuid": s["recipient_uuid"],
                "full_name": s["full_name"],
                "email": s["email"],
                "status": s["status"],
                "attempt": s["attempt"],
                "error": s["detail"].get("error"),
                "recorded_at": s["recorded_at"],
                "removed": s["removed"],
            }
            for s in lines
        ],
    }


def _view(
    report: Row,
    sections: list[Row],
    evidence: list[Row],
    states: list[Row],
    board: list[Row],
    *,
    sendable: bool,
) -> Row:
    kind = Kind(report["kind"])
    bodies = {str(s["section_key"]): s["body"] for s in sections}
    return {
        "report_uuid": report["report_uuid"],
        "kind": kind.value,
        "title": TITLES[kind],
        "version": report["version"],
        "state": _state(report),
        "sections": [
            {"key": s.key, "label": s.label, "required": s.required, "body": bodies.get(s.key)}
            for s in SECTIONS[kind]
        ],
        "created_at": report["created_at"],
        "created_by_name": report["created_by_name"],
        "updated_at": report["updated_at"],
        "finalised_at": report["finalised_at"],
        "finalised_by_name": report["finalised_by_name"],
        "filed_at": report["filed_at"],
        "filed_reference": report["filed_reference"],
        "filed_by_name": report["filed_by_name"],
        "evidence": evidence,
        "mail": _mail(states, board, sendable=sendable),
    }


async def overview(conn: Conn, *, breach_uuid: str) -> Row:
    """Every kind of report, where each stands, and what may be done with it."""
    breach = await service.require(conn, breach_uuid)
    breach_id = int(breach["breach_id"])
    reports = await repo.on_breach(conn, breach_id)
    ids = [int(r["report_id"]) for r in reports]
    sections: dict[int, list[Row]] = defaultdict(list)
    evidence: dict[int, list[Row]] = defaultdict(list)
    states: dict[int, list[Row]] = defaultdict(list)
    if ids:
        for s in await repo.sections_of(conn, ids):
            sections[int(s["report_id"])].append(s)
        for e in await repo.evidence_of(conn, ids):
            evidence[int(e["report_id"])].append(e)
        for d in await repo.latest_states(conn, ids):
            states[int(d["report_id"])].append(d)
    duties = await service.duties_of(conn, breach_id)
    board = await recipients_repo.board_recipients(conn)
    kinds = []
    for kind in Kind:
        mine = [r for r in reports if r["kind"] == kind]
        duty = DUTIES.get(kind)
        found = duties.get(duty) if duty else None
        kinds.append(
            {
                "kind": kind.value,
                "title": TITLES[kind],
                "basis": BASES[kind],
                "duty": duty.value if duty else None,
                "duty_state": found[1]["state"] if found else None,
                "blocked_by": _may_write(kind, breach, duties),
                "goes_to_regulator": kind != Kind.ORG_BOARD,
                "versions": [
                    _view(
                        r,
                        sections[int(r["report_id"])],
                        evidence[int(r["report_id"])],
                        states[int(r["report_id"])],
                        board,
                        sendable=(
                            r["finalised_at"] is not None
                            and breach["status"] == Status.OPEN
                            and _resend_refused(kind, r, mine, breach, duties, board) is None
                        ),
                    )
                    for r in mine
                ],
            }
        )
    return {
        "kinds": kinds,
        "board_recipients": len(board),
        "proofs": [{"kind": k, "label": v} for k, v in PROOFS.items()],
    }


# --------------------------------------------------------------- the document


async def _document(conn: Conn, report: Row, *, reference: str) -> tuple[Document, str, str]:
    """The report as a document: its PDF, its words for a mail body, its title."""
    kind = Kind(report["kind"])
    report_id = int(report["report_id"])
    sections = await repo.sections_of(conn, [report_id])
    opened = await unseal_strings([s["body"] for s in sections])
    bodies = {str(s["section_key"]): opened.get(s["body"], s["body"]) for s in sections}
    title = TITLES[kind]
    blocks: list[Any] = [
        Fields(
            rows=[
                ("Reference", reference),
                ("Organisation", settings.organisation_name),
                ("Basis", BASES[kind]),
                ("Version", str(report["version"])),
                (
                    "State",
                    "Finalised " + _when(report["finalised_at"])
                    if report["finalised_at"]
                    else "Draft, not finalised",
                ),
            ]
        )
    ]
    text: list[str] = []
    for section in SECTIONS[kind]:
        body = str(bodies.get(section.key) or "")
        if not body:
            continue
        blocks += [Heading(section.label), Paragraph(body)]
        text.append(f"{section.label}\n{body}")
    document = Document(
        title=title,
        subtitle=reference,
        blocks=blocks,
        created_at=report["finalised_at"] or report["updated_at"],
        footer=f"{reference} · version {report['version']}",
        subject=title,
    )
    return document, "\n\n".join(text), title


async def pdf(
    conn: Conn, *, breach_uuid: str, report_uuid: str, actor_id: int
) -> tuple[bytes, str]:
    """The report as a PDF, and a name for it. Every read is on the trail."""
    breach = await service.require(conn, breach_uuid)
    report = await _report(conn, breach, report_uuid)
    document, _, _ = await _document(conn, report, reference=str(breach["reference"]))
    await service.record_event(
        conn,
        breach,
        Event.BREACH_REPORT_READ,
        actor_id=actor_id,
        detail={"kind": report["kind"], "version": int(report["version"])},
    )
    # Off the event loop: the words may be a stranger's, and long.
    payload = await asyncio.to_thread(render, document)
    return payload, f"{breach['reference']}-{report['kind']}-v{report['version']}.pdf"


# ------------------------------------------------------------------ the worker


async def claim_key(conn: Conn, delivery_uuid: str) -> str | None:
    """What every task for this address on this report claims before it sends,
    or None if there is nothing to send. The report and the address, never the
    delivery: a lost one is queued again under a new uuid, and the same address
    may be on the list twice over."""
    row = await repo.job(conn, delivery_uuid)
    if not row or row["status"] != "queued" or row["settled"] or row["reached"]:
        return None
    return rkey(K_LOCK, "breach_report", row["report_id"], row["email_hash"])


async def job(conn: Conn, delivery_uuid: str) -> Row | None:
    """What the worker mails for one queued delivery, or None if there is
    nothing to do: an unknown uuid, an attempt that has its outcome or a later
    attempt in its place, or an address that has the report. An address taken
    off the list since comes back as that and nothing else: the report is not
    opened for it, and the task records why it was not mailed."""
    row = await repo.job(conn, delivery_uuid)
    if not row or row["status"] != "queued" or row["settled"] or row["reached"]:
        return None
    if row["removed_at"] is not None:
        return {"removed": True}
    report = await repo.by_id(conn, int(row["report_id"]))
    breach = await breach_repo.by_breach_id(conn, int(row["breach_id"]))
    assert report is not None and breach is not None
    document, text, title = await _document(conn, report, reference=str(breach["reference"]))
    return {
        "removed": False,
        "email": row["email"],
        "kind": report["kind"],
        "reference": breach["reference"],
        "report_title": title,
        "report_text": text,
        "pdf": render(document),
        "file_name": f"{breach['reference']}-{report['kind']}-v{report['version']}.pdf",
    }


async def _settle(conn: Conn, report_id: int, breach_id: int) -> bool:
    """Complete the organisation's board duty if this report has run its course
    and reached somebody. An address taken off the list is waited for no longer.
    The caller holds the breach row, so of two re-reads the second finds it
    done. Returns whether it completed now.

    Past `service.complete_duty`, as `notices.settle` is: this is the worker,
    with no office and no person, recording what happened."""
    found = (await service.duties_of(conn, breach_id)).get(Duty.ORG_BOARD)
    if not found or found[1]["state"] != State.OUTSTANDING:
        return False
    states = await repo.latest_states(conn, [report_id])
    lines = _by_address(states, await recipients_repo.board_recipients(conn))
    if any(s["status"] == "queued" and not s["removed"] for s in lines):
        return False
    reached = [s for s in lines if s["status"] == "delivered"]
    if not reached:
        return False
    # When the board was first told, which is what the clock asks. The duty is
    # recorded once the mail has run its course, and the last address may have
    # taken its retries well past that.
    occurred_at = min(s["recorded_at"] for s in states if s["status"] == "delivered")
    await breach_repo.add_obligation_event(
        conn,
        int(found[0]["obligation_id"]),
        kind=EventKind.COMPLETED,
        occurred_at=occurred_at,
        reported_to=await _whom(reached),
        recorded_by=None,
    )
    breach = await breach_repo.by_breach_id(conn, breach_id)
    assert breach is not None
    due = found[1]["due_at"]
    await service.record_event(
        conn,
        breach,
        Event.BREACH_OBLIGATION_COMPLETED,
        actor_id=None,
        detail={
            "duty": Duty.ORG_BOARD.value,
            "late": bool(due and occurred_at > due),
            "reached": len(reached),
            "by": "delivery",
        },
    )
    return True


async def record_result(
    conn: Conn, *, delivery_uuid: str, status: str, detail: dict[str, Any]
) -> None:
    """The worker's outcome for one attempt, and nothing else: the duty is
    `settle`'s, in a transaction of its own after this one, so that nothing it
    needs can undo the account of a mail that went. It takes no breach row
    either: a mail that has gone does not wait behind somebody's upload.

    Recorded twice, it is there once. No failure is written for an address the
    report has reached: one taken off while its mail was going still got it, and
    the account says so."""
    row = await repo.job(conn, delivery_uuid)
    if not row or (status == "failed" and row["reached"]):
        return
    await repo.add_delivery(
        conn,
        int(row["report_id"]),
        int(row["recipient_id"]),
        attempt=int(row["attempt"]),
        status=status,
        detail=detail,
    )


async def settle(conn: Conn, *, delivery_uuid: str) -> None:
    """The board's duty re-read after an outcome, under the breach's row."""
    row = await repo.job(conn, delivery_uuid)
    if not row:
        return
    report = await repo.by_id(conn, int(row["report_id"]))
    assert report is not None
    if report["kind"] == Kind.ORG_BOARD:
        await breach_repo.lock(conn, int(row["breach_id"]))
        await _settle(conn, int(row["report_id"]), int(row["breach_id"]))


async def taken_off(conn: Conn, recipient_uuid: str) -> None:
    """An address has left the list, so nothing waits on it: what was still
    queued to it is told to the worker as the result it would have recorded,
    and the board's duty is re-read as after any result. A task that does run
    finds the same thing and records the same thing.

    The list is shared and the reports are the offices'. This looks across both
    for that one statement, and what it finds goes to the worker and no
    further: the caller is served none of it."""
    from cmp.tasks.dispatch import dispatch_optional
    from cmp.tasks.notifications.breach_reports import record_breach_report_result

    async with across_offices(conn):
        waiting = await repo.queued_to(conn, recipient_uuid)
    for delivery in waiting:
        dispatch_optional(
            record_breach_report_result,
            delivery,
            "failed",
            {"error": "RecipientRemoved", "attempts": 1},
        )
