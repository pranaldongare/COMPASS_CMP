"""Breach tickets addressed to me (S3-08).

The holder's side: every member of staff may hold a breach ticket, and reads
and answers it here. Scope OWN, in the WHERE clause - a ticket addressed to
somebody else is 404 - and only what BD-13 allows: the breach reference, the
instruction, the thread, the state and the answer-by date. Nothing from the
register: the register itself answers this person 404.

A holder writes and returns; only the DPO closes, sends back, withdraws or
reopens, on `/breaches/{uuid}/tickets/*`, which answers everyone else 404.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, File, Form, Response, UploadFile
from pydantic import Field

from cmp.api import uploads
from cmp.api.dependencies import BreachTicketReader, BreachTicketWriter
from cmp.api.routers.v1.breaches import BreachTicketMessageOut, BreachTicketMoveOut
from cmp.db.pool import connection, transaction
from cmp.domain.breach import tickets
from cmp.schemas.common import Out, Schema

router = APIRouter(prefix="/breach-tickets", tags=["breach tickets"])


class MyBreachTicketOut(Out):
    """Exactly what a holder is given (BD-13), and nothing else."""

    ticket_uuid: UUID
    #: The breach reference: what they may quote, and all they learn of it.
    breach_reference: str
    #: What they were asked. Sealed; the console opens it.
    instruction: str
    #: issued, returned, closed or withdrawn.
    state: str
    answer_by: date | None
    created_at: datetime
    #: The Privacy Office's messages they have not read.
    unread: int
    last_activity_at: datetime | None
    #: What they may do now: return, while it is issued.
    moves: list[BreachTicketMoveOut]
    #: Whether they may bring in a colleague now (S3-09): while it is open.
    may_add_colleague: bool


class MyBreachTicketDetailOut(Out):
    ticket: MyBreachTicketOut
    messages: list[BreachTicketMessageOut]


@router.get("", response_model=list[MyBreachTicketOut], summary="Breach tickets addressed to me")
async def my_breach_tickets(principal: BreachTicketReader) -> list[dict[str, Any]]:
    async with connection() as conn:
        return await tickets.mine(conn, user_id=principal.user_id)


@router.get(
    "/{ticket_uuid}",
    response_model=MyBreachTicketDetailOut,
    summary="One breach ticket addressed to me, with its thread",
)
async def my_breach_ticket(ticket_uuid: UUID, principal: BreachTicketReader) -> dict[str, Any]:
    """Reading it marks the Privacy Office's messages read."""
    async with transaction() as conn:
        return await tickets.my_detail(
            conn, user_id=principal.user_id, ticket_uuid=str(ticket_uuid)
        )


@router.post(
    "/{ticket_uuid}/messages",
    response_model=MyBreachTicketDetailOut,
    summary="Write to the Privacy Office on my breach ticket, with a file if it helps",
)
async def message_office(
    ticket_uuid: UUID,
    principal: BreachTicketWriter,
    body: Annotated[str, Form(min_length=1, max_length=20_000)],
    evidence: Annotated[UploadFile | None, File(description="Optional file, max 25 MB")] = None,
) -> dict[str, Any]:
    stored = await uploads.stored(evidence, subdir="breach")
    async with transaction() as conn:
        return await tickets.holder_message(
            conn,
            user_id=principal.user_id,
            ticket_uuid=str(ticket_uuid),
            body=body,
            evidence=stored,
        )


@router.get(
    "/{ticket_uuid}/messages/{message_uuid}/evidence",
    summary="Download a file attached to a message on my breach ticket",
)
async def my_ticket_file(
    ticket_uuid: UUID, message_uuid: UUID, principal: BreachTicketReader
) -> Response:
    async with transaction() as conn:
        payload, name, recorded = await tickets.holder_attachment(
            conn,
            user_id=principal.user_id,
            ticket_uuid=str(ticket_uuid),
            message_uuid=str(message_uuid),
        )
    return uploads.download(payload, name, recorded)


class ColleagueIn(Schema):
    full_name: Annotated[str, Field(max_length=200)] | None = None
    email: Annotated[str, Field(min_length=3, max_length=320)]
    mobile: Annotated[str, Field(max_length=32)] | None = None
    #: What you are asking them; their ticket opens with it. Sealed.
    note: Annotated[str, Field(min_length=1, max_length=20_000)]


@router.post(
    "/{ticket_uuid}/colleagues",
    response_model=MyBreachTicketDetailOut,
    summary="Bring a colleague into my breach ticket: they get their own",
)
async def add_colleague(
    ticket_uuid: UUID, body: ColleagueIn, principal: BreachTicketWriter
) -> dict[str, Any]:
    """The answer is your own ticket whatever happened to theirs, so it says
    nothing about whether an address has an account."""
    async with transaction() as conn:
        return await tickets.add_colleague(
            conn,
            user_id=principal.user_id,
            ticket_uuid=str(ticket_uuid),
            full_name=body.full_name,
            email=body.email,
            mobile=body.mobile,
            note=body.note,
        )


@router.post(
    "/{ticket_uuid}/return",
    response_model=MyBreachTicketDetailOut,
    summary="Return my breach ticket: what was done, and how it went",
)
async def return_my_breach_ticket(
    ticket_uuid: UUID,
    principal: BreachTicketWriter,
    summary: Annotated[str, Form(min_length=1, max_length=20_000)],
    #: done, partial or failed. Only done counts as done.
    outcome: Annotated[str, Form(description="done, partial or failed")],
    evidence: Annotated[UploadFile | None, File(description="Optional evidence, max 25 MB")] = None,
) -> dict[str, Any]:
    stored = await uploads.stored(evidence, subdir="breach")
    async with transaction() as conn:
        return await tickets.return_ticket(
            conn,
            user_id=principal.user_id,
            ticket_uuid=str(ticket_uuid),
            summary=summary,
            outcome=outcome,
            evidence=stored,
        )
