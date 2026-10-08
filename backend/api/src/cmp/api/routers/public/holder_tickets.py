"""An outside holder's ticket, by its link (0049, 2026-10-08).

`/holder-tickets/{token}` is what the portal page `/ticket/{token}` calls. The
link alone shows the reference, the holder's name and where a code will go;
the code, sent to the address on the ticket, opens an hour on that ticket in
an HttpOnly, SameSite=Strict cookie. See `cmp.domain.rights.holder_link`.

As on every public route: rate limited per address, `Referrer-Policy:
no-referrer`, the token scrubbed from access logs, and every way a link can
fail answering the same 404.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, File, Form, Request, Response, UploadFile, status
from pydantic import Field

from cmp.api.routers.v1.rights import (
    TicketDetailOut,
    _attachment,
    _attachment_response,
)
from cmp.auth.rate_limit import service as ratelimit
from cmp.core.config import settings
from cmp.db.pool import transaction
from cmp.domain.rights import holder_link, reach, service, tickets
from cmp.schemas.common import Acknowledged, OtpCode, Out, Schema

router = APIRouter(prefix="/holder-tickets", tags=["holder tickets"])

TokenPath = Annotated[str, Field(min_length=20, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]


class HolderLinkOut(Out):
    """What the link alone shows: whose ticket, and where the code goes."""

    reference: str
    holder_label: str
    request_type: str
    #: The address the code goes to, masked.
    code_goes_to: str | None
    state: str
    state_label: str
    due_at: datetime | None
    #: True while this browser holds an hour on the ticket.
    signed_in: bool


class CodeIn(Schema):
    code: OtpCode


def _guard(response: Response) -> None:
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"


async def _per_address(request: Request, bucket: str, limit: int, window_s: int) -> None:
    await ratelimit.enforce(
        bucket,
        request.client.host if request.client else "unknown",
        limit=limit,
        window_s=window_s,
        fail_open=False,
    )


def _cookie(request: Request) -> str | None:
    return request.cookies.get(settings.holder_ticket_cookie)


@router.get(
    "/{token}", response_model=HolderLinkOut, summary="What the link opens, before the code"
)
async def open_link(token: TokenPath, request: Request, response: Response) -> dict[str, Any]:
    _guard(response)
    await _per_address(request, "holder_link_ip", settings.public_link_rate_per_minute, 60)
    async with transaction() as conn:
        ticket = await holder_link.open_link(conn, token)
        view = tickets.holder_view(ticket)
        return {
            "reference": ticket["reference"],
            "holder_label": ticket["label"],
            "request_type": ticket["request_type"],
            "code_goes_to": await reach.masked_address(ticket),
            "state": view["state"],
            "state_label": view["state_label"],
            "due_at": ticket["due_at"],
            "signed_in": await holder_link.signed_in(ticket, token, _cookie(request)),
        }


@router.post(
    "/{token}/code", response_model=Acknowledged, summary="Send a code to the ticket's address"
)
async def send_code(token: TokenPath, request: Request, response: Response) -> dict[str, Any]:
    _guard(response)
    await _per_address(request, "holder_link_act_ip", 20, 3600)
    async with transaction() as conn:
        await holder_link.send_code(conn, token)
    return {"ok": True, "message": "A code is on its way to the address on the ticket."}


@router.post("/{token}/verify", response_model=Acknowledged, summary="Enter the code")
async def verify(
    token: TokenPath, body: CodeIn, request: Request, response: Response
) -> dict[str, Any]:
    _guard(response)
    await _per_address(request, "holder_link_act_ip", 20, 3600)
    async with transaction() as conn:
        value = await holder_link.verify(conn, token, body.code)
    response.set_cookie(
        settings.holder_ticket_cookie,
        value,
        max_age=settings.holder_ticket_session_s,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        domain=settings.cookie_domain,
        path="/",
    )
    return {"ok": True, "message": "The ticket is open for the next hour."}


@router.post(
    "/{token}/sign-out", status_code=status.HTTP_204_NO_CONTENT, summary="Close the ticket here"
)
async def sign_out(token: TokenPath, request: Request, response: Response) -> None:
    _guard(response)
    await holder_link.end(_cookie(request))
    response.delete_cookie(settings.holder_ticket_cookie, domain=settings.cookie_domain, path="/")


@router.get("/{token}/ticket", response_model=TicketDetailOut, summary="The ticket, after the code")
async def read_ticket(token: TokenPath, request: Request, response: Response) -> dict[str, Any]:
    """What is asked, the items, what the platform holds about the person, and
    the messages. Reading marks the office's messages read."""
    _guard(response)
    async with transaction() as conn:
        ticket = await holder_link.holder_in(conn, token, _cookie(request))
        return await holder_link.detail(conn, ticket)


@router.post(
    "/{token}/messages",
    response_model=TicketDetailOut,
    summary="Write to the Privacy Office, with a file if it helps",
)
async def write(
    token: TokenPath,
    request: Request,
    response: Response,
    body: Annotated[str, Form(min_length=1, max_length=20_000)],
    evidence: Annotated[UploadFile | None, File(description="Optional file, max 25 MB")] = None,
) -> dict[str, Any]:
    _guard(response)
    async with transaction() as conn:
        await holder_link.holder_in(conn, token, _cookie(request))
    evidence_ref, evidence_hash, evidence_name = await _attachment(evidence)
    async with transaction() as conn:
        ticket = await holder_link.holder_in(conn, token, _cookie(request))
        return await holder_link.write(
            conn,
            ticket,
            body=body,
            evidence_ref=evidence_ref,
            evidence_hash=evidence_hash,
            evidence_name=evidence_name,
        )


@router.post(
    "/{token}/answer",
    response_model=TicketDetailOut,
    summary="Give the answer: what was done, what is held, and proof",
)
async def answer(
    token: TokenPath,
    request: Request,
    response: Response,
    summary: Annotated[str, Form(min_length=1, max_length=20_000)],
    outcome: Annotated[str, Form(description="done, partial or failed")],
    evidence: Annotated[UploadFile | None, File(description="Optional proof, max 25 MB")] = None,
) -> dict[str, Any]:
    """It waits for the Privacy Office to accept it, or send it back."""
    _guard(response)
    async with transaction() as conn:
        await holder_link.holder_in(conn, token, _cookie(request))
    evidence_ref, evidence_hash, evidence_name = await _attachment(evidence)
    async with transaction() as conn:
        ticket = await holder_link.holder_in(conn, token, _cookie(request))
        return await holder_link.answer(
            conn,
            ticket,
            summary=summary,
            outcome=outcome,
            evidence_ref=evidence_ref,
            evidence_hash=evidence_hash,
            evidence_name=evidence_name,
        )


@router.get(
    "/{token}/messages/{message_uuid}/evidence",
    summary="Download a file on the ticket's messages",
)
async def message_file(
    token: TokenPath, message_uuid: UUID, request: Request, response: Response
) -> Response:
    async with transaction() as conn:
        ticket = await holder_link.holder_in(conn, token, _cookie(request))
        payload, filename, recorded = await service.message_attachment(
            conn, holder=ticket, message_uuid=str(message_uuid), actor_id=None
        )
    out = _attachment_response(payload, filename, recorded)
    _guard(out)
    return out
