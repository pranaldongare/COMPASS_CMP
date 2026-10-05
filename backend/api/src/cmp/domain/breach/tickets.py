"""Breach tickets: the DPO asks the people who must act, and they answer (S3-08).

The model is the rights request's ticket (ADR 0023, BD-03): the DPO assigns a
ticket to a person with an instruction, both sides write on its thread, the
holder returns it with what they did, and only the DPO closes it (BD-07).

Rules this module holds:

* **Only on a recorded breach.** A ticket reaches a person on the breach's
  account, so it waits for the first *yes* like the principals' notice
  (409 `breach_not_recorded`, BD-10).
* **Internal staff only** (BD-06, BD-12): every assignee's address must be on
  `BREACH_TICKET_EMAIL_DOMAINS`, checked here, on the server; a refusal names
  the rule and never echoes the address.
* **One ticket per person per breach** (BD-14): the breach row is held first, so
  two assignments of the same person act one after the other; the unique
  constraint is the second line.
* **The holder sees their ticket and nothing else** (BD-13): the breach
  reference, their instruction, the thread, the state, the answer-by date.
  Never the title, where, validation, assessment, who it touched, notices,
  duties or anybody else's ticket.
* **The trail says what happened, never the words** (ADR 0015): the ticket, an
  outcome, that a reason was given. The holder is the subject.
* **Every write takes the breach row first**, through `service.locked_open`,
  so a closed breach refuses every ticket write and two moves on one ticket
  act one after the other.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Any

from cmp.core.config import settings
from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.core.permissions import Role
from cmp.db.repositories import breach_tickets as repo
from cmp.db.repositories import users as user_repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.domain.breach import access, service
from cmp.domain.breach.ticket_state import (
    EVENT,
    REASON_REQUIRED,
    Move,
    Outcome,
    TicketState,
    fold,
    may_write,
    moves,
)
from cmp.infrastructure.dkms import unseal_value
from cmp.validation.choices import choice

Row = dict[str, Any]

#: The event written for each move, in the trail's words.
_TRAIL: dict[Move, str] = {
    Move.RETURN: Event.BREACH_TICKET_RETURNED,
    Move.SEND_BACK: Event.BREACH_TICKET_SENT_BACK,
    Move.CLOSE: Event.BREACH_TICKET_CLOSED,
    Move.WITHDRAW: Event.BREACH_TICKET_WITHDRAWN,
    Move.REOPEN: Event.BREACH_TICKET_REOPENED,
}

#: What the thread says when the office moves a ticket. The reason, where one
#: was given, follows it.
_STATUS_LINE: dict[Move, str] = {
    Move.SEND_BACK: "Sent back by the Privacy Office",
    Move.CLOSE: "Closed by the Privacy Office",
    Move.WITHDRAW: "Withdrawn by the Privacy Office",
    Move.REOPEN: "Reopened by the Privacy Office",
}

#: The moves after which the holder is emailed that a ticket is waiting.
_WAITING_AFTER: frozenset[Move] = frozenset({Move.SEND_BACK, Move.REOPEN})

#: Exactly what a holder is given (BD-13). A test holds the payload to it.
HOLDER_KEYS: frozenset[str] = frozenset(
    {
        "ticket_uuid",
        "breach_reference",
        "instruction",
        "state",
        "answer_by",
        "created_at",
        "unread",
        "last_activity_at",
        "moves",
        # Whether they may add a colleague now (S3-09): while it is open.
        "may_add_colleague",
    }
)


def _text(value: str | None) -> str:
    return (value or "").strip()


def _today() -> date:
    return datetime.now(UTC).date()


# ------------------------------------------------------------ who may hold one


async def _require_internal(user: Row) -> None:
    """BD-12: the opened address's domain is on the list. Said without the
    address: the DPO typed or picked it, and an error that repeats it is an
    error that may end up in a log."""
    email = await unseal_value("auth_user", "email", user.get("email"))
    domain = str(email).rsplit("@", 1)[-1].lower() if email and "@" in str(email) else ""
    allowed = {d.lower() for d in settings.breach_ticket_email_domains}
    if domain not in allowed:
        raise ValidationFailed(
            "Breach tickets go to internal staff only: this person's email address is not on "
            "one of the organisation's own domains",
            field="user_uuid",
        )


def _require_staff(user: Row) -> None:
    """BD-06: somebody who signs in to the console. A temporary login for a
    person without one is S3-09's."""
    if str(user.get("role")) == Role.DATA_SUBJECT.value or str(user.get("status")) != "active":
        raise ValidationFailed(
            "Assign a ticket to a member of staff with an active console account",
            field="user_uuid",
        )


def _answer_by(value: date | None) -> date | None:
    if value is not None and value < _today():
        raise ValidationFailed("The answer-by date has already passed", field="answer_by")
    return value


async def _tell_holder(row: Row) -> None:
    """BD-18: the email names no breach. Sealed values go to the broker; the
    worker opens them at `deliver()`."""
    from cmp.tasks.dispatch import dispatch_optional
    from cmp.tasks.notifications.breach_tickets import send_breach_ticket_waiting

    if row.get("holder_email"):
        dispatch_optional(
            send_breach_ticket_waiting, str(row["holder_email"]), str(row["holder_name"] or "")
        )


async def _trail(
    conn: Conn, ticket: Row, event: str, *, actor_id: int, detail: dict[str, Any]
) -> None:
    await audit.record(
        conn,
        event=event,
        entity_type="breach_ticket",
        entity_id=int(ticket["ticket_id"]),
        actor_user_id=actor_id,
        subject_user_id=int(ticket["holder_user_id"]),
        detail={"ticket": str(ticket["ticket_uuid"]), **detail},
    )


# ---------------------------------------------------------------- assigning


async def assign(
    conn: Conn,
    *,
    breach_uuid: str,
    instruction: str,
    answer_by: date | None,
    actor_id: int,
    user_uuid: str | None = None,
    full_name: str | None = None,
    email: str | None = None,
    mobile: str | None = None,
) -> Row:
    """The DPO asks somebody to act on a recorded breach: a member of staff
    picked by `user_uuid`, or - S3-09 - anybody internal named by an email, who
    is given a breach-only login if they have no console account."""
    breach = await service.locked_open(conn, breach_uuid)
    service.require_recorded(breach, "a ticket is assigned")
    instruction = _text(instruction)
    if not instruction:
        raise ValidationFailed("Say what you are asking them to do", field="instruction")
    answer_by = _answer_by(answer_by)
    if user_uuid:
        user = await user_repo.by_uuid(conn, user_uuid)
        if not user:
            raise NotFound("Person")
        _require_staff(user)
        await _require_internal(user)
        made = await _open_ticket(
            conn,
            breach,
            holder_id=int(user["id"]),
            instruction=instruction,
            answer_by=answer_by,
            actor_id=actor_id,
        )
    else:
        made = await _ask_by_email(
            conn,
            breach,
            full_name=full_name,
            email=email,
            mobile=mobile,
            opening=instruction,
            answer_by=answer_by,
            actor_id=actor_id,
            cause="assigned",
        )
    return await office_detail(conn, breach_uuid=breach_uuid, ticket_uuid=str(made["ticket_uuid"]))


async def _ask_by_email(
    conn: Conn,
    breach: Row,
    *,
    full_name: str | None,
    email: str | None,
    mobile: str | None,
    opening: str,
    answer_by: date | None,
    actor_id: int,
    cause: str,
    parent_ticket_id: int | None = None,
) -> Row:
    """The three-way lookup (S3-09): staff get an ordinary ticket; anybody
    else internal gets a breach-only login with it. The caller holds the
    breach row."""
    address = (email or "").strip().lower()
    if not address or "@" not in address:
        raise ValidationFailed("Give their email address", field="email")
    if not access.internal(address):
        access.refuse_external()
    user, created = await access.resolve(conn, full_name=full_name, email=address, mobile=mobile)
    temporary = access.needs_grant(user)
    made = await _open_ticket(
        conn,
        breach,
        holder_id=int(user["id"]),
        instruction=opening,
        answer_by=answer_by,
        actor_id=actor_id,
        parent_ticket_id=parent_ticket_id,
        notify=not temporary,
    )
    if temporary:
        await access.grant(
            conn,
            breach=breach,
            user=user,
            ticket_id=int(made["ticket_id"]),
            created=created,
            actor_id=actor_id,
            cause=cause,
        )
    return made


async def _open_ticket(
    conn: Conn,
    breach: Row,
    *,
    holder_id: int,
    instruction: str,
    answer_by: date | None,
    actor_id: int,
    parent_ticket_id: int | None = None,
    notify: bool = True,
) -> Row:
    """Write the ticket, its opening message and its trail, and tell the holder
    - unless they are being given a login, whose email says it instead. The
    caller holds the breach row."""
    if await repo.held_by(conn, int(breach["breach_id"]), holder_id):
        raise Conflict("This person already holds a ticket on this breach", code="ticket_exists")
    made = await repo.create(
        conn,
        breach_id=int(breach["breach_id"]),
        holder_user_id=holder_id,
        assigned_by=actor_id,
        instruction=instruction,
        answer_by=answer_by,
        parent_ticket_id=parent_ticket_id,
    )
    if made is None:
        raise Conflict("This person already holds a ticket on this breach", code="ticket_exists")
    await repo.add_message(
        conn,
        int(made["ticket_id"]),
        # A colleague's ticket opens with the adder's note: from neither the
        # office nor the colleague, so the platform's line, signed by the adder.
        side="office" if parent_ticket_id is None else "system",
        kind="instruction",
        body=instruction,
        author_user_id=actor_id,
    )
    ticket = await repo.on_breach(conn, int(breach["breach_id"]), str(made["ticket_uuid"]))
    assert ticket is not None
    await _trail(
        conn,
        ticket,
        Event.BREACH_TICKET_ASSIGNED,
        actor_id=actor_id,
        detail={"answer_by": answer_by.isoformat() if answer_by else None},
    )
    if notify:
        await _tell_holder(ticket)
    return ticket


# ---------------------------------------------------------------- reading


async def _events_by_ticket(conn: Conn, ticket_ids: list[int]) -> dict[int, list[Row]]:
    by: dict[int, list[Row]] = defaultdict(list)
    for e in await repo.events_for(conn, ticket_ids) if ticket_ids else []:
        by[int(e["ticket_id"])].append(e)
    return by


def _access_state(grant: Row | None) -> str | None:
    """A holder's breach-only login, as the office reads it: pending until
    they set a password, active, or ended. None for a member of staff."""
    if grant is None:
        return None
    if grant["ended_at"] is not None:
        return "ended"
    return "pending" if grant["user_status"] == "pending" else "active"


def _office_view(row: Row, events: list[Row], grant: Row | None = None) -> Row:
    state = fold(events)
    breach_open = row["breach_status"] == "open"
    return {
        "ticket_uuid": row["ticket_uuid"],
        "holder_uuid": row["holder_uuid"],
        "holder_name": row["holder_name"],
        "assigned_by_name": row["assigned_by_name"],
        "parent_ticket_uuid": row["parent_ticket_uuid"],
        "added_by_name": row["added_by_name"],
        "state": state.value,
        "answer_by": row["answer_by"],
        "overdue": bool(
            state == TicketState.ISSUED and row["answer_by"] and row["answer_by"] < _today()
        ),
        "created_at": row["created_at"],
        "unread": int(row["unread"] or 0),
        "last_activity_at": row["last_activity_at"],
        "events": events,
        "moves": moves(state, side="office", breach_open=breach_open),
        "may_write": breach_open and may_write(state),
        "temporary_access": _access_state(grant),
    }


def _holder_view(row: Row, events: list[Row]) -> Row:
    state = fold(events)
    view = {
        "ticket_uuid": row["ticket_uuid"],
        "breach_reference": row["breach_reference"],
        "instruction": row["instruction"],
        "state": state.value,
        "answer_by": row["answer_by"],
        "created_at": row["created_at"],
        "unread": int(row["unread"] or 0),
        "last_activity_at": row["last_activity_at"],
        "moves": moves(state, side="holder", breach_open=row["breach_status"] == "open"),
        "may_add_colleague": row["breach_status"] == "open" and may_write(state),
    }
    assert set(view) == HOLDER_KEYS
    return view


async def for_breach(conn: Conn, *, breach_uuid: str) -> list[Row]:
    """Every ticket on a breach, as the office reads them."""
    breach = await service.require(conn, breach_uuid)
    rows = await repo.for_breach(conn, int(breach["breach_id"]))
    ids = [int(r["ticket_id"]) for r in rows]
    events = await _events_by_ticket(conn, ids)
    grants = {int(g["ticket_id"]): g for g in await repo.access_by_ticket(conn, ids)} if ids else {}
    return [
        _office_view(r, events[int(r["ticket_id"])], grants.get(int(r["ticket_id"]))) for r in rows
    ]


async def _office_row(conn: Conn, breach: Row, ticket_uuid: str) -> Row:
    row = await repo.on_breach(conn, int(breach["breach_id"]), ticket_uuid)
    if not row:
        raise NotFound("Ticket")
    return row


async def office_detail(conn: Conn, *, breach_uuid: str, ticket_uuid: str) -> Row:
    """One ticket and its thread, as the office reads it - which marks it read."""
    breach = await service.require(conn, breach_uuid)
    row = await _office_row(conn, breach, ticket_uuid)
    await repo.mark_read(conn, int(row["ticket_id"]), side="office")
    fresh = await _office_row(conn, breach, ticket_uuid)
    events = await _events_by_ticket(conn, [int(fresh["ticket_id"])])
    grants = await repo.access_by_ticket(conn, [int(fresh["ticket_id"])])
    return {
        "ticket": _office_view(
            fresh, events[int(fresh["ticket_id"])], grants[0] if grants else None
        ),
        "instruction": fresh["instruction"],
        "messages": await repo.messages_of(conn, int(fresh["ticket_id"])),
    }


async def mine(conn: Conn, *, user_id: int) -> list[Row]:
    """Every breach ticket addressed to this account."""
    rows = await repo.for_holder(conn, user_id)
    events = await _events_by_ticket(conn, [int(r["ticket_id"]) for r in rows])
    return [_holder_view(r, events[int(r["ticket_id"])]) for r in rows]


async def _holder_row(conn: Conn, user_id: int, ticket_uuid: str) -> Row:
    row = await repo.mine(conn, user_id, ticket_uuid)
    if not row:
        raise NotFound("Ticket")
    return row


async def my_detail(conn: Conn, *, user_id: int, ticket_uuid: str) -> Row:
    """One ticket addressed to me, with its thread - which marks it read."""
    row = await _holder_row(conn, user_id, ticket_uuid)
    await repo.mark_read(conn, int(row["ticket_id"]), side="holder")
    fresh = await _holder_row(conn, user_id, ticket_uuid)
    events = await _events_by_ticket(conn, [int(fresh["ticket_id"])])
    return {
        "ticket": _holder_view(fresh, events[int(fresh["ticket_id"])]),
        "messages": await repo.messages_of(conn, int(fresh["ticket_id"])),
    }


async def dashboard_counts(conn: Conn) -> dict[str, int]:
    """For the DPO's "Needs you today": tickets returned and waiting on the
    office, and tickets past their answer-by, on open breaches."""
    today = _today()
    returned = overdue = 0
    for r in await repo.on_open_breaches(conn):
        state = fold({"kind": k} for k in r["kinds"])
        if state == TicketState.RETURNED:
            returned += 1
        elif state == TicketState.ISSUED and r["answer_by"] and r["answer_by"] < today:
            overdue += 1
    return {"breach_tickets_returned": returned, "breach_tickets_overdue": overdue}


# ---------------------------------------------------------------- the thread


async def _write(
    conn: Conn,
    row: Row,
    events: list[Row],
    *,
    side: str,
    body: str,
    actor_id: int,
    evidence: tuple[str | None, str | None, str | None],
) -> None:
    if not may_write(fold(events)):
        raise Conflict("This ticket is no longer open", code="ticket_not_open")
    text = _text(body)
    if not text:
        raise ValidationFailed("Write something", field="body")
    ref, digest, name = evidence
    await repo.add_message(
        conn,
        int(row["ticket_id"]),
        side=side,
        kind="message",
        body=text,
        author_user_id=actor_id,
        evidence_ref=ref,
        evidence_hash=digest,
        evidence_name=name,
    )
    await repo.mark_read(conn, int(row["ticket_id"]), side=side)
    await _trail(
        conn,
        row,
        Event.BREACH_TICKET_MESSAGE,
        actor_id=actor_id,
        detail={"side": side, "file": digest is not None},
    )


async def office_message(
    conn: Conn,
    *,
    breach_uuid: str,
    ticket_uuid: str,
    body: str,
    actor_id: int,
    evidence: tuple[str | None, str | None, str | None] = (None, None, None),
) -> Row:
    breach = await service.locked_open(conn, breach_uuid)
    row = await _office_row(conn, breach, ticket_uuid)
    events = (await _events_by_ticket(conn, [int(row["ticket_id"])]))[int(row["ticket_id"])]
    await _write(conn, row, events, side="office", body=body, actor_id=actor_id, evidence=evidence)
    return await office_detail(conn, breach_uuid=breach_uuid, ticket_uuid=ticket_uuid)


async def holder_message(
    conn: Conn,
    *,
    user_id: int,
    ticket_uuid: str,
    body: str,
    evidence: tuple[str | None, str | None, str | None] = (None, None, None),
) -> Row:
    row = await _holder_row(conn, user_id, ticket_uuid)
    await service.locked_open(conn, str(row["breach_uuid"]))
    events = (await _events_by_ticket(conn, [int(row["ticket_id"])]))[int(row["ticket_id"])]
    await _write(conn, row, events, side="holder", body=body, actor_id=user_id, evidence=evidence)
    return await my_detail(conn, user_id=user_id, ticket_uuid=ticket_uuid)


async def attachment(
    conn: Conn, row: Row, *, message_uuid: str, actor_id: int
) -> tuple[bytes, str, str]:
    """A file on the thread. Every read is audited."""
    from cmp.infrastructure.storage.service import storage

    message = await repo.message_by_uuid(conn, int(row["ticket_id"]), message_uuid)
    if not message or not message.get("evidence_ref"):
        raise NotFound("Attachment")
    payload = storage().read(str(message["evidence_ref"]))
    await _trail(
        conn,
        row,
        Event.BREACH_TICKET_FILE_READ,
        actor_id=actor_id,
        detail={"message": message_uuid},
    )
    name = await unseal_value("breach_ticket_message", "evidence_name", message["evidence_name"])
    return (
        payload,
        str(name or f"breach-ticket-{message_uuid}"),
        str(message["evidence_hash"] or ""),
    )


async def office_attachment(
    conn: Conn, *, breach_uuid: str, ticket_uuid: str, message_uuid: str, actor_id: int
) -> tuple[bytes, str, str]:
    breach = await service.require(conn, breach_uuid)
    row = await _office_row(conn, breach, ticket_uuid)
    return await attachment(conn, row, message_uuid=message_uuid, actor_id=actor_id)


async def holder_attachment(
    conn: Conn, *, user_id: int, ticket_uuid: str, message_uuid: str
) -> tuple[bytes, str, str]:
    row = await _holder_row(conn, user_id, ticket_uuid)
    return await attachment(conn, row, message_uuid=message_uuid, actor_id=user_id)


# ---------------------------------------------------------------- moves


def _require_move(state: TicketState, move: Move, *, side: str) -> None:
    allowed = {m["move"] for m in moves(state, side=side, breach_open=True)}
    if move.value not in allowed:
        raise Conflict(
            f"A ticket that is {state.value} cannot be {EVENT[move].replace('_', ' ')}",
            code="ticket_move_not_allowed",
        )


async def office_move(
    conn: Conn,
    *,
    breach_uuid: str,
    ticket_uuid: str,
    move: str,
    reason: str | None,
    actor_id: int,
) -> Row:
    """Send back, close, withdraw or reopen - the office's moves (BD-07)."""
    chosen = choice(Move, move, field="move")
    if chosen == Move.RETURN:
        raise Conflict("Only the holder returns a ticket", code="ticket_move_not_allowed")
    breach = await service.locked_open(conn, breach_uuid)
    row = await _office_row(conn, breach, ticket_uuid)
    events = (await _events_by_ticket(conn, [int(row["ticket_id"])]))[int(row["ticket_id"])]
    _require_move(fold(events), chosen, side="office")
    text = _text(reason)
    if chosen in REASON_REQUIRED and not text:
        raise ValidationFailed("Give the reason", field="reason")
    await repo.add_event(
        conn,
        int(row["ticket_id"]),
        kind=EVENT[chosen],
        actor_user_id=actor_id,
        reason=text or None,
    )
    await repo.add_message(
        conn,
        int(row["ticket_id"]),
        side="office",
        kind="status",
        body=_STATUS_LINE[chosen] + (f": {text}" if text else "."),
        author_user_id=actor_id,
    )
    await repo.mark_read(conn, int(row["ticket_id"]), side="office")
    await _trail(conn, row, _TRAIL[chosen], actor_id=actor_id, detail={"reason_given": bool(text)})
    regranted = False
    if chosen == Move.WITHDRAW:
        # BD-15: a withdrawn ticket takes its breach-only login with it.
        await access.end_for_ticket(
            conn, int(breach["breach_id"]), int(row["holder_user_id"]), actor_id=actor_id
        )
    elif chosen == Move.REOPEN:
        regranted = await _restore_access(conn, breach, row, actor_id=actor_id)
    if chosen in _WAITING_AFTER and not regranted:
        await _tell_holder(row)
    return await office_detail(conn, breach_uuid=breach_uuid, ticket_uuid=ticket_uuid)


async def _restore_access(conn: Conn, breach: Row, row: Row, *, actor_id: int) -> bool:
    """Reopening a ticket whose holder's breach-only login has ended grants it
    again: a new grant, and a new email. True if it did."""
    last = await repo.latest_grant(conn, int(breach["breach_id"]), int(row["holder_user_id"]))
    if last is None or last["ended_at"] is None:
        return False
    user = await user_repo.by_id(conn, int(row["holder_user_id"]))
    assert user is not None
    if not access.needs_grant(user):
        return False  # an administrator has since given them a real role
    await access.grant(
        conn,
        breach=breach,
        user=user,
        ticket_id=int(row["ticket_id"]),
        created=bool(last["account_created"]),
        actor_id=actor_id,
        cause="reopened",
    )
    return True


async def add_colleague(
    conn: Conn,
    *,
    user_id: int,
    ticket_uuid: str,
    full_name: str | None,
    email: str | None,
    mobile: str | None,
    note: str,
) -> Row:
    """A holder brings in a colleague, who follows the same flow (BD-05,
    BD-14): their own ticket on this breach, opening with this note - not the
    DPO's instruction - under the same domain check and the same lookup.

    The answer is the adder's own ticket whatever happened to the colleague's
    account, so nobody learns from it whether an address has one. Somebody who
    already holds a ticket here is a neutral 409.
    """
    row = await _holder_row(conn, user_id, ticket_uuid)
    breach = await service.locked_open(conn, str(row["breach_uuid"]))
    events = (await _events_by_ticket(conn, [int(row["ticket_id"])]))[int(row["ticket_id"])]
    if not may_write(fold(events)):
        raise Conflict("This ticket is no longer open", code="ticket_not_open")
    text = _text(note)
    if not text:
        raise ValidationFailed("Say what you are asking them to do", field="note")
    try:
        made = await _ask_by_email(
            conn,
            breach,
            full_name=full_name,
            email=email,
            mobile=mobile,
            opening=text,
            answer_by=row["answer_by"],
            actor_id=user_id,
            cause="colleague",
            parent_ticket_id=int(row["ticket_id"]),
        )
    except Conflict as exc:
        if exc.code in ("ticket_exists", "access_exists"):
            raise Conflict(
                "That person cannot be added to this ticket", code="colleague_not_added"
            ) from exc
        raise
    colleague = await repo.on_breach(conn, int(breach["breach_id"]), str(made["ticket_uuid"]))
    assert colleague is not None
    await _trail(
        conn,
        colleague,
        Event.BREACH_TICKET_COLLEAGUE_ADDED,
        actor_id=user_id,
        detail={"parent": str(row["ticket_uuid"])},
    )
    return await my_detail(conn, user_id=user_id, ticket_uuid=ticket_uuid)


async def return_ticket(
    conn: Conn,
    *,
    user_id: int,
    ticket_uuid: str,
    summary: str,
    outcome: str,
    evidence: tuple[str | None, str | None, str | None] = (None, None, None),
) -> Row:
    """The holder says what they did: done, partial or failed, with a summary
    and, if it helps, a file. It waits for the DPO to close or send back."""
    row = await _holder_row(conn, user_id, ticket_uuid)
    await service.locked_open(conn, str(row["breach_uuid"]))
    events = (await _events_by_ticket(conn, [int(row["ticket_id"])]))[int(row["ticket_id"])]
    _require_move(fold(events), Move.RETURN, side="holder")
    said = choice(Outcome, outcome, field="outcome")
    text = _text(summary)
    if not text:
        raise ValidationFailed("Say what was done", field="summary")
    await repo.add_event(
        conn,
        int(row["ticket_id"]),
        kind=EVENT[Move.RETURN],
        actor_user_id=user_id,
        outcome=said.value,
        summary=text,
    )
    ref, digest, name = evidence
    await repo.add_message(
        conn,
        int(row["ticket_id"]),
        side="holder",
        kind="return",
        body=text,
        author_user_id=user_id,
        evidence_ref=ref,
        evidence_hash=digest,
        evidence_name=name,
    )
    await repo.mark_read(conn, int(row["ticket_id"]), side="holder")
    await _trail(
        conn,
        row,
        Event.BREACH_TICKET_RETURNED,
        actor_id=user_id,
        detail={"outcome": said.value, "file": digest is not None},
    )
    return await my_detail(conn, user_id=user_id, ticket_uuid=ticket_uuid)
