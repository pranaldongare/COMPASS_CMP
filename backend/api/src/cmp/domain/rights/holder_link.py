"""An outside holder answers its ticket by a link on the portal (0049, 2026-10-08).

A vendor or third-party processor holding the person's data has no account
and should not need one. Its ticket comes as a link (`reach`); opening it shows
only the reference, the holder's name and where a code will go. The code goes
to the address the ticket was sent to - never one typed on the page - so
holding the link is not enough: the holder must also read that mailbox.

The code opens an hour on that ticket and nothing else: a random value in an
HttpOnly, SameSite=Strict cookie, its fingerprint in Redis naming the holder
and the link it came through. Every call names the link in its path too, and
both must agree, so the cookie alone opens nothing and a link sent to
somebody else since (a new one, after reassignment) shuts the old hour.

What the holder can then do is what a team does in the console: read what is
asked, the items, and what the platform holds about the person; write to the
office with a file; give its answer, which waits for the office's review.
Every act is on the trail with no actor - nobody with an account did it - and
the channel `link`.
"""

from __future__ import annotations

import json
from typing import Any

from cmp.auth.authentication import otp
from cmp.auth.rate_limit import service as ratelimit
from cmp.core.config import settings
from cmp.core.enums import RightsTicketStatus as Ticket
from cmp.core.errors import NotFound, Unauthenticated
from cmp.core.security import new_token, token_fingerprint
from cmp.db.redis import K_HOLDER_TICKET, get_redis
from cmp.db.redis import key as rkey
from cmp.db.repositories import rights as repo
from cmp.db.sql import Conn
from cmp.domain.rights import reach, service

Row = dict[str, Any]


class LinkInvalid(NotFound):
    """Every way a link can fail answers the same: no such ticket."""

    def __init__(self) -> None:
        super().__init__("This link does not open a ticket. Ask the Privacy Office for a new one.")


async def open_link(conn: Conn, raw: str) -> Row:
    """The ticket this link opens: issued, and the link still its current one."""
    ticket = await repo.ticket_by_link(conn, reach.fingerprint(raw))
    if not ticket or ticket["ticket_status"] == Ticket.PENDING:
        raise LinkInvalid
    return ticket


async def send_code(conn: Conn, raw: str) -> None:
    """A code to the address on the ticket. Rate-limited per ticket."""
    ticket = await open_link(conn, raw)
    await ratelimit.enforce(
        "holder_ticket_code",
        str(ticket["holder_uuid"]),
        limit=settings.otp_requests_per_contact_per_hour,
        window_s=3600,
        message="Too many codes for this ticket. Try again later.",
    )
    to = await reach.address(ticket)
    if not to:
        raise LinkInvalid
    issued = await otp.issue(otp.Scope.HOLDER_TICKET, str(ticket["holder_uuid"]))
    service._dispatch("send_holder_ticket_code", to, issued.code, str(ticket["reference"]))


async def verify(conn: Conn, raw: str, code: str) -> str:
    """The code proves the address: an hour on this ticket. Returns the
    cookie's value; only its fingerprint is kept."""
    ticket = await open_link(conn, raw)
    await otp.require(otp.Scope.HOLDER_TICKET, str(ticket["holder_uuid"]), code)
    value = new_token(32)
    await get_redis().set(
        rkey(K_HOLDER_TICKET, token_fingerprint(value)),
        json.dumps({"holder_id": int(ticket["holder_id"]), "link": reach.fingerprint(raw)}),
        ex=settings.holder_ticket_session_s,
    )
    return value


async def end(cookie: str | None) -> None:
    if cookie:
        await get_redis().delete(rkey(K_HOLDER_TICKET, token_fingerprint(cookie)))


async def holder_in(conn: Conn, raw: str, cookie: str | None) -> Row:
    """The ticket, for a holder who has entered the code for this link."""
    ticket = await open_link(conn, raw)
    if not await signed_in(ticket, raw, cookie):
        raise Unauthenticated("Enter the code sent to you to open this ticket", code="code_needed")
    return ticket


async def signed_in(ticket: Row, raw: str, cookie: str | None) -> bool:
    if not cookie:
        return False
    stored = await get_redis().get(rkey(K_HOLDER_TICKET, token_fingerprint(cookie)))
    if not stored:
        return False
    held = json.loads(stored)
    return bool(
        held.get("holder_id") == int(ticket["holder_id"])
        and held.get("link") == reach.fingerprint(raw)
    )


async def detail(conn: Conn, ticket: Row) -> dict[str, Any]:
    """The ticket as its holder reads it; reading marks the office's messages read."""
    holder_id = int(ticket["holder_id"])
    await repo.mark_thread_read(conn, holder_id, side="holder")
    fresh = await repo.ticket_by_holder_id(conn, holder_id)
    return {
        "ticket": fresh,
        "messages": await repo.messages_of(conn, holder_id),
        "items": await repo.items_for_holder(conn, holder_id),
    }


async def write(
    conn: Conn,
    ticket: Row,
    *,
    body: str,
    evidence_ref: str | None,
    evidence_hash: str | None,
    evidence_name: str | None,
) -> dict[str, Any]:
    await service.write_as_holder(
        conn,
        ticket,
        author_id=None,
        body=body,
        evidence_ref=evidence_ref,
        evidence_hash=evidence_hash,
        evidence_name=evidence_name,
    )
    return await detail(conn, ticket)


async def answer(
    conn: Conn,
    ticket: Row,
    *,
    summary: str,
    outcome: str,
    evidence_ref: str | None,
    evidence_hash: str | None,
    evidence_name: str | None,
) -> dict[str, Any]:
    await service.answer_as_holder(
        conn,
        ticket,
        author_id=None,
        summary=summary,
        outcome=outcome,
        evidence_ref=evidence_ref,
        evidence_hash=evidence_hash,
        evidence_name=evidence_name,
    )
    return await detail(conn, ticket)
