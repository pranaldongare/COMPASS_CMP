"""The breach register's only writer (S3-01).

Every change takes the breach row first (`repo.lock`), so two people acting on
one breach at once are made to act one after the other, and writes the audit
row in the same transaction. The trail says what was recorded - an outcome, a
duty, that a reason was given - and never the office's words, which are sealed
on their rows (ADR 0015).

Two rules this module exists to hold:

* **The platform records a determination; it never computes one.** Nothing
  here reads whether exposed data was sealed. A determination of *yes* creates
  the three DPDP duties with their clocks, whatever the assessment says about
  encryption.
* **Times are entered, never defaulted.** Detection, awareness and the moment
  a duty was done are what the DPO says they were. A breach recorded five hours
  after it was noticed shows one hour of CERT-In time left, not six.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from cmp.core.config import settings
from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.db.repositories import breaches as repo
from cmp.db.sql import Conn, fetch_one
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.domain.breach import clock, state_machine
from cmp.domain.breach.clock import DPDP_DUTIES, Duty, EventKind, State
from cmp.domain.breach.state_machine import BreachFacts, Status
from cmp.validation.choices import choice

Row = dict[str, Any]

#: A clock on somebody's laptop may run a little ahead of ours. A time "in the
#: future" by less than this is taken as now's; by more, it is a mistake.
_SKEW = timedelta(minutes=5)


class LocationKind(StrEnum):
    PLATFORM = "platform"
    PROCESSOR = "processor"
    DATA_SOURCE = "data_source"
    OTHER = "other"


class Outcome(StrEnum):
    PENDING = "pending"
    YES = "yes"
    NO = "no"


def _now() -> datetime:
    return datetime.now(UTC)


def _not_future(value: datetime, field: str) -> None:
    if value > _now() + _SKEW:
        raise ValidationFailed("This time is in the future", field=field)


def _text(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


async def require(conn: Conn, breach_uuid: str) -> Row:
    row = await repo.by_uuid(conn, breach_uuid)
    if not row:
        raise NotFound("Breach")
    return row


async def _locked_open(conn: Conn, breach_uuid: str) -> Row:
    row = await require(conn, breach_uuid)
    locked = await repo.lock(conn, int(row["breach_id"]))
    if locked["status"] != Status.OPEN:
        raise Conflict("This breach is closed; reopen it to record more", code="breach_closed")
    return row


async def _record(
    conn: Conn, breach: Row, event: str, *, actor_id: int, detail: dict[str, Any] | None = None
) -> None:
    await audit.record(
        conn,
        event=event,
        entity_type="breach",
        entity_id=int(breach["breach_id"]),
        actor_user_id=actor_id,
        detail={"reference": breach["reference"], **(detail or {})},
    )


# ---------------------------------------------------------------- recording


async def record(
    conn: Conn,
    *,
    title: str,
    detected_at: datetime,
    began_at: datetime | None,
    location_kind: str,
    processor_uuid: str | None,
    source_uuid: str | None,
    location_detail: str | None,
    actor_id: int,
) -> Row:
    """Open a breach. Nothing about it is known yet but that it was noticed."""
    kind = choice(LocationKind, location_kind, field="location_kind")
    title = (title or "").strip()
    if not title:
        raise ValidationFailed("Give the breach a short title", field="title")
    _not_future(detected_at, "detected_at")
    if began_at is not None:
        _not_future(began_at, "began_at")
        if began_at > detected_at:
            raise ValidationFailed(
                "It cannot have begun after it was first noticed", field="began_at"
            )
    processor_id = source_id = None
    if kind == LocationKind.PROCESSOR:
        if not processor_uuid:
            raise ValidationFailed("Name the processor", field="processor_uuid")
        found = await fetch_one(
            conn, "SELECT processor_id FROM processor WHERE processor_uuid = %s", (processor_uuid,)
        )
        if not found:
            raise NotFound("Processor")
        processor_id = int(found["processor_id"])
    elif processor_uuid:
        raise ValidationFailed(
            "A processor is named only for a processor breach", field="processor_uuid"
        )
    if kind == LocationKind.DATA_SOURCE:
        if not source_uuid:
            raise ValidationFailed("Name the data source", field="source_uuid")
        found = await fetch_one(
            conn, "SELECT source_id FROM data_source WHERE source_uuid = %s", (source_uuid,)
        )
        if not found:
            raise NotFound("Data source")
        source_id = int(found["source_id"])
    elif source_uuid:
        raise ValidationFailed(
            "A data source is named only for a source breach", field="source_uuid"
        )
    if kind == LocationKind.OTHER and not _text(location_detail):
        raise ValidationFailed("Say where it occurred", field="location_detail")

    created = await repo.create(
        conn,
        title=title,
        detected_at=detected_at,
        began_at=began_at,
        location_kind=kind.value,
        location_processor_id=processor_id,
        location_source_id=source_id,
        location_detail=_text(location_detail),
        recorded_by=actor_id,
    )
    await repo.add_status_history(
        conn,
        int(created["breach_id"]),
        from_status=None,
        to_status=Status.OPEN,
        reason=None,
        changed_by=actor_id,
    )
    breach = await require(conn, str(created["breach_uuid"]))
    await _record(
        conn, breach, Event.BREACH_RECORDED, actor_id=actor_id, detail={"location": kind.value}
    )
    return await detail(conn, str(created["breach_uuid"]))


# ------------------------------------------------------------- determination


async def determine(
    conn: Conn,
    *,
    breach_uuid: str,
    outcome: str,
    reasoning: str,
    became_aware_at: datetime | None,
    actor_id: int,
) -> Row:
    """Record whether this is a personal data breach under s.2(u).

    *Yes* creates the three DPDP duties, or reinstates any a previous *no* set
    aside, with clocks from `became_aware_at`. *No* sets aside those not yet
    done, citing this determination. *Pending* changes no duty. CERT-In stands
    on its own test and is untouched by all three.
    """
    breach = await _locked_open(conn, breach_uuid)
    decided = choice(Outcome, outcome, field="outcome")
    reasoning = (reasoning or "").strip()
    if not reasoning:
        raise ValidationFailed("Give the reasoning for this determination", field="reasoning")
    if decided == Outcome.YES:
        if became_aware_at is None:
            raise ValidationFailed(
                "Enter when the organisation became aware a personal data breach had occurred",
                field="became_aware_at",
            )
        _not_future(became_aware_at, "became_aware_at")
        if became_aware_at < breach["detected_at"]:
            raise ValidationFailed(
                "Awareness cannot come before the event was first noticed",
                field="became_aware_at",
            )
    elif became_aware_at is not None:
        raise ValidationFailed(
            "The time of awareness is recorded with a determination of yes",
            field="became_aware_at",
        )

    made = await repo.add_determination(
        conn,
        int(breach["breach_id"]),
        outcome=decided.value,
        reasoning=reasoning,
        became_aware_at=became_aware_at,
        determined_by=actor_id,
    )
    await _record(
        conn,
        breach,
        Event.BREACH_DETERMINED,
        actor_id=actor_id,
        detail={"outcome": decided.value, "reason_given": True},
    )
    determination_id = int(made["determination_id"])
    if decided == Outcome.YES:
        assert became_aware_at is not None
        await _apply_yes(conn, breach, determination_id, became_aware_at, actor_id=actor_id)
    elif decided == Outcome.NO:
        await _apply_no(conn, breach, determination_id, actor_id=actor_id)
    return await detail(conn, breach_uuid)


async def _duties(conn: Conn, breach_id: int) -> dict[str, tuple[Row, dict[str, Any]]]:
    """Each duty created on this breach, with its folded state."""
    rows = await repo.obligations(conn, [breach_id])
    events = await repo.obligation_events(conn, [int(r["obligation_id"]) for r in rows])
    by_obligation: dict[int, list[Row]] = defaultdict(list)
    for e in events:
        by_obligation[int(e["obligation_id"])].append(e)
    return {
        str(r["kind"]): (r, clock.fold(r, by_obligation[int(r["obligation_id"])])) for r in rows
    }


async def _apply_yes(
    conn: Conn, breach: Row, determination_id: int, aware: datetime, *, actor_id: int
) -> None:
    duties = await _duties(conn, int(breach["breach_id"]))
    for duty in DPDP_DUTIES:
        due = clock.due_for(duty, aware)
        if duty not in duties:
            await repo.create_obligation(
                conn,
                int(breach["breach_id"]),
                kind=duty.value,
                due_at=due,
                anchored_at=aware,
                determination_id=determination_id,
                created_by=actor_id,
            )
            await _record(
                conn,
                breach,
                Event.BREACH_OBLIGATION_CREATED,
                actor_id=actor_id,
                detail={"duty": duty.value, "due_at": due.isoformat() if due else None},
            )
            continue
        row, state = duties[duty]
        if state["state"] == State.NOT_APPLICABLE:
            await repo.add_obligation_event(
                conn,
                int(row["obligation_id"]),
                kind=EventKind.REINSTATED,
                due_at=due,
                anchored_at=aware,
                determination_id=determination_id,
                recorded_by=actor_id,
            )
            await _record(
                conn,
                breach,
                Event.BREACH_OBLIGATION_REINSTATED,
                actor_id=actor_id,
                detail={"duty": duty.value, "due_at": due.isoformat() if due else None},
            )
        # Outstanding or done: a later *yes* does not move a clock already
        # running. Its awareness time is on its own row, for the report.


async def _apply_no(conn: Conn, breach: Row, determination_id: int, *, actor_id: int) -> None:
    duties = await _duties(conn, int(breach["breach_id"]))
    for duty in DPDP_DUTIES:
        if duty in duties:
            row, state = duties[duty]
            if state["state"] != State.OUTSTANDING:
                # Done stays done: a report already filed was filed.
                continue
            obligation_id = int(row["obligation_id"])
        else:
            created = await repo.create_obligation(
                conn,
                int(breach["breach_id"]),
                kind=duty.value,
                due_at=None,
                anchored_at=None,
                determination_id=determination_id,
                created_by=actor_id,
            )
            obligation_id = int(created["obligation_id"])
        await repo.add_obligation_event(
            conn,
            obligation_id,
            kind=EventKind.NOT_APPLICABLE,
            determination_id=determination_id,
            recorded_by=actor_id,
        )
        await _record(
            conn,
            breach,
            Event.BREACH_OBLIGATION_NOT_APPLICABLE,
            actor_id=actor_id,
            detail={"duty": duty.value},
        )


# ---------------------------------------------------------------- assessment


async def assess(
    conn: Conn,
    *,
    breach_uuid: str,
    began_at: datetime | None,
    categories: list[dict[str, Any]],
    text: dict[str, str | None],
    actor_id: int,
) -> Row:
    """A new revision of what is known. The previous one stays as it was."""
    breach = await _locked_open(conn, breach_uuid)
    if began_at is not None:
        _not_future(began_at, "began_at")
        if began_at > breach["detected_at"]:
            raise ValidationFailed(
                "It cannot have begun after it was first noticed", field="began_at"
            )
    cleaned = {k: _text(text.get(k)) for k in repo.ASSESSMENT_TEXT}
    seen: set[str] = set()
    listed: list[dict[str, Any]] = []
    for c in categories:
        name = str(c["category"]).strip()
        if not name:
            raise ValidationFailed("Name each data category", field="categories")
        if name.lower() in seen:
            raise ValidationFailed(f"{name} is listed twice", field="categories")
        seen.add(name.lower())
        sealed = bool(c["sealed"])
        # A key cannot be exposed for data that was never under one.
        key_exposed = bool(c["key_exposed"]) if sealed else False
        listed.append({"category": name, "sealed": sealed, "key_exposed": key_exposed})
    if not listed and not any(cleaned.values()) and began_at is None:
        raise ValidationFailed("An assessment records at least one fact")
    made = await repo.add_assessment(
        conn,
        int(breach["breach_id"]),
        began_at=began_at,
        categories=listed,
        text=cleaned,
        revised_by=actor_id,
    )
    await _record(
        conn,
        breach,
        Event.BREACH_ASSESSED,
        actor_id=actor_id,
        detail={"revision": int(made["revision"]), "categories": len(listed)},
    )
    return await detail(conn, breach_uuid)


async def assessments(conn: Conn, *, breach_uuid: str) -> list[Row]:
    breach = await require(conn, breach_uuid)
    return await repo.assessments(conn, int(breach["breach_id"]))


# -------------------------------------------------------------------- duties


async def mark_cert_in(conn: Conn, *, breach_uuid: str, actor_id: int) -> Row:
    """A reportable cyber incident: CERT-In is due six hours from detection."""
    breach = await _locked_open(conn, breach_uuid)
    duties = await _duties(conn, int(breach["breach_id"]))
    if Duty.CERT_IN in duties:
        raise Conflict("Already marked as reportable to CERT-In", code="cert_in_marked")
    due = clock.due_for(Duty.CERT_IN, breach["detected_at"])
    await repo.create_obligation(
        conn,
        int(breach["breach_id"]),
        kind=Duty.CERT_IN.value,
        due_at=due,
        anchored_at=breach["detected_at"],
        determination_id=None,
        created_by=actor_id,
    )
    await _record(
        conn,
        breach,
        Event.BREACH_CERT_IN_MARKED,
        actor_id=actor_id,
        detail={"duty": Duty.CERT_IN.value, "due_at": due.isoformat() if due else None},
    )
    return await detail(conn, breach_uuid)


async def complete_duty(
    conn: Conn,
    *,
    breach_uuid: str,
    duty: str,
    occurred_at: datetime,
    reference: str,
    note: str | None,
    actor_id: int,
) -> Row:
    """Record that a submission was made, when, and what the regulator returned."""
    kind = choice(Duty, duty, field="duty")
    breach = await _locked_open(conn, breach_uuid)
    if kind == Duty.PRINCIPALS:
        raise Conflict(
            "Principals are notified by sending the approved notice; this duty completes "
            "when every affected principal's notice is delivered or its failure recorded",
            code="principals_complete_by_delivery",
        )
    row, state = await _outstanding(conn, breach, kind)
    reference = (reference or "").strip()
    if not reference:
        raise ValidationFailed("Enter the reference the regulator returned", field="reference")
    _not_future(occurred_at, "occurred_at")
    if state["anchored_at"] is not None and occurred_at < state["anchored_at"]:
        raise ValidationFailed(
            "A submission cannot come before its clock started", field="occurred_at"
        )
    await repo.add_obligation_event(
        conn,
        int(row["obligation_id"]),
        kind=EventKind.COMPLETED,
        occurred_at=occurred_at,
        reference=reference,
        note=_text(note),
        recorded_by=actor_id,
    )
    await _record(
        conn,
        breach,
        Event.BREACH_OBLIGATION_COMPLETED,
        actor_id=actor_id,
        detail={
            "duty": kind.value,
            "late": bool(state["due_at"] and occurred_at > state["due_at"]),
        },
    )
    return await detail(conn, breach_uuid)


async def extend_report(
    conn: Conn,
    *,
    breach_uuid: str,
    requested_at: datetime,
    allowed_until: datetime,
    reference: str | None,
    note: str | None,
    actor_id: int,
) -> Row:
    """Rule 7(2)(b): "or such longer period as the Board may allow". The detailed
    report's due time becomes the date allowed, as a new row; the initial
    intimation's clock is not touched."""
    breach = await _locked_open(conn, breach_uuid)
    row, state = await _outstanding(conn, breach, Duty.BOARD_REPORT)
    _not_future(requested_at, "requested_at")
    if state["anchored_at"] is not None and requested_at < state["anchored_at"]:
        raise ValidationFailed(
            "An extension cannot be asked for before awareness", field="requested_at"
        )
    if state["due_at"] is not None and allowed_until <= state["due_at"]:
        raise ValidationFailed(
            "The date allowed must be later than the report's current due time",
            field="allowed_until",
        )
    await repo.add_obligation_event(
        conn,
        int(row["obligation_id"]),
        kind=EventKind.EXTENDED,
        requested_at=requested_at,
        due_at=allowed_until,
        reference=_text(reference),
        note=_text(note),
        recorded_by=actor_id,
    )
    await _record(
        conn,
        breach,
        Event.BREACH_OBLIGATION_EXTENDED,
        actor_id=actor_id,
        detail={"duty": Duty.BOARD_REPORT.value, "due_at": allowed_until.isoformat()},
    )
    return await detail(conn, breach_uuid)


async def _outstanding(conn: Conn, breach: Row, duty: Duty) -> tuple[Row, dict[str, Any]]:
    duties = await _duties(conn, int(breach["breach_id"]))
    if duty not in duties:
        raise Conflict(f"{clock.LABELS[duty]} is not a duty on this breach", code="no_such_duty")
    row, state = duties[duty]
    if state["state"] != State.OUTSTANDING:
        raise Conflict(
            f"{clock.LABELS[duty]} is {state['state'].replace('_', ' ')}",
            code="duty_not_outstanding",
        )
    return row, state


# ------------------------------------------------------------- open, closed


async def _facts(conn: Conn, breach_id: int) -> BreachFacts:
    latest = await repo.latest_determinations(conn, [breach_id])
    duties = await _duties(conn, breach_id)
    return BreachFacts(
        determination=str(latest[breach_id]["outcome"]) if breach_id in latest else "pending",
        outstanding=tuple(
            clock.LABELS[kind] for kind, (_, s) in duties.items() if s["state"] == State.OUTSTANDING
        ),
    )


async def transitions_for(conn: Conn, *, breach_uuid: str) -> Row:
    breach = await require(conn, breach_uuid)
    facts = await _facts(conn, int(breach["breach_id"]))
    return {
        "current": breach["status"],
        "available": state_machine.available(str(breach["status"]), facts),
    }


async def transition(
    conn: Conn, *, breach_uuid: str, to: str, reason: str | None, actor_id: int
) -> Row:
    breach = await require(conn, breach_uuid)
    locked = await repo.lock(conn, int(breach["breach_id"]))
    current = str(locked["status"])
    facts = await _facts(conn, int(breach["breach_id"]))
    state_machine.validate(current, to, facts, reason)
    await repo.set_status(conn, int(breach["breach_id"]), to=to)
    await repo.add_status_history(
        conn,
        int(breach["breach_id"]),
        from_status=current,
        to_status=to,
        reason=_text(reason),
        changed_by=actor_id,
    )
    await _record(
        conn,
        breach,
        Event.BREACH_CLOSED if to == Status.CLOSED else Event.BREACH_REOPENED,
        actor_id=actor_id,
        detail={"reason_given": bool(_text(reason))},
    )
    return await detail(conn, breach_uuid)


# -------------------------------------------------------------------- reading


def _duty_view(row: Row, state: dict[str, Any], events: list[Row], now: datetime) -> Row:
    return {
        "obligation_uuid": row["obligation_uuid"],
        "duty": row["kind"],
        "label": clock.LABELS[row["kind"]],
        "basis": clock.BASIS[row["kind"]],
        "created_at": row["created_at"],
        **state,
        "clock": clock.timing(state["state"], state["due_at"], state["anchored_at"], now=now),
        "events": events,
    }


async def _duty_views(conn: Conn, breach_ids: list[int]) -> dict[int, list[Row]]:
    rows = await repo.obligations(conn, breach_ids)
    events = await repo.obligation_events(conn, [int(r["obligation_id"]) for r in rows])
    by_obligation: dict[int, list[Row]] = defaultdict(list)
    for e in events:
        by_obligation[int(e["obligation_id"])].append(e)
    now = _now()
    out: dict[int, list[Row]] = defaultdict(list)
    for r in rows:
        mine = by_obligation[int(r["obligation_id"])]
        out[int(r["breach_id"])].append(_duty_view(r, clock.fold(r, mine), mine, now))
    return out


def _location(row: Row) -> Row:
    return {
        "kind": row["location_kind"],
        "processor_uuid": row["location_processor_uuid"],
        "processor_name": row["location_processor_name"],
        "source_uuid": row["location_source_uuid"],
        "source_name": row["location_source_name"],
        "detail": row["location_detail"],
    }


async def detail(conn: Conn, breach_uuid: str) -> Row:
    breach = await require(conn, breach_uuid)
    breach_id = int(breach["breach_id"])
    determinations = await repo.determinations(conn, breach_id)
    current = determinations[-1] if determinations else None
    aware = next(
        (d["became_aware_at"] for d in reversed(determinations) if d["outcome"] == Outcome.YES),
        None,
    )
    assessments = await repo.assessments(conn, breach_id)
    latest = assessments[0] if assessments else None
    duties = (await _duty_views(conn, [breach_id])).get(breach_id, [])
    facts = await _facts(conn, breach_id)
    return {
        "breach_uuid": breach["breach_uuid"],
        "reference": breach["reference"],
        "title": breach["title"],
        "status": breach["status"],
        "detected_at": breach["detected_at"],
        "became_aware_at": aware,
        # The latest revision's, where one says; otherwise as first recorded.
        "began_at": (latest["began_at"] if latest and latest["began_at"] else breach["began_at"]),
        "began_at_recorded": breach["began_at"],
        "location": _location(breach),
        "recorded_at": breach["recorded_at"],
        "recorded_by_name": breach["recorded_by_name"],
        "determination": current["outcome"] if current else Outcome.PENDING.value,
        "determinations": determinations,
        "assessment": latest,
        "assessment_revisions": len(assessments),
        "obligations": duties,
        "status_history": await repo.status_history(conn, breach_id),
        "transitions": state_machine.available(str(breach["status"]), facts),
        "without_delay_target_hours": settings.breach_without_delay_target_hours,
    }


async def register(conn: Conn, *, status: str | None) -> list[Row]:
    """Every breach, open first, each with its duties and their clocks."""
    if status is not None:
        status = choice(Status, status, field="status").value
    rows = await repo.list_breaches(conn, status=status)
    ids = [int(r["breach_id"]) for r in rows]
    latest = await repo.latest_determinations(conn, ids) if ids else {}
    duties = await _duty_views(conn, ids) if ids else {}
    out: list[Row] = []
    for r in rows:
        d = latest.get(int(r["breach_id"]))
        out.append(
            {
                "breach_uuid": r["breach_uuid"],
                "reference": r["reference"],
                "title": r["title"],
                "status": r["status"],
                "detected_at": r["detected_at"],
                "location": _location(r),
                "determination": d["outcome"] if d else Outcome.PENDING.value,
                "obligations": duties.get(int(r["breach_id"]), []),
            }
        )
    return out
