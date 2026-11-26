"""An outside processor answers a retention action by its link (ADR 0047).

`/retention-links/{token}` is what the portal page `/retention/{token}`
calls. As a holder ticket's link (0049): the link alone shows the reference,
the processor and where a code will go; the code, sent to the respondent's
address, opens an hour on that one action in the same HttpOnly,
SameSite=Strict cookie. Rate limited per address, `Referrer-Policy:
no-referrer`, the token scrubbed from access logs, and every way a link can
fail answering the same 404. See `cmp.domain.retention.links`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Request, Response, status
from pydantic import Field

from cmp.api.routers.public.holder_tickets import CodeIn, _guard, _per_address
from cmp.api.routers.v1.retention import RetentionAnswerIn, RetentionHolderActionOut
from cmp.core.config import settings
from cmp.db.pool import across_offices, transaction
from cmp.domain.retention import actions, links
from cmp.schemas.common import Acknowledged, Out

router = APIRouter(prefix="/retention-links", tags=["retention links"])

TokenPath = Annotated[str, Field(min_length=20, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]


class RetentionLinkOut(Out):
    """What the link alone shows: which review, who is asked, where the code goes."""

    reference: str
    holder_label: str
    #: validity | retention
    kind: str
    #: The address the code goes to, masked.
    code_goes_to: str | None
    #: open | answered | accepted | sent_back | not_needed
    status: str
    due_at: datetime
    #: True while this browser holds an hour on the action.
    signed_in: bool


def _cookie(request: Request) -> str | None:
    return request.cookies.get(settings.holder_ticket_cookie)


@router.get("/{token}", response_model=RetentionLinkOut, summary="What the link opens")
async def open_link(token: TokenPath, request: Request, response: Response) -> dict[str, Any]:
    _guard(response)
    await _per_address(request, "retention_link_ip", settings.public_link_rate_per_minute, 60)
    async with transaction() as conn, across_offices(conn):
        action, review = await links.open_link(conn, token)
        return {
            "reference": review["reference"],
            "holder_label": action["label"],
            "kind": review["kind"],
            "code_goes_to": await links.masked_address(conn, action),
            "status": action["status"],
            "due_at": action["due_at"],
            "signed_in": await links.signed_in(action, token, _cookie(request)),
        }


@router.post("/{token}/code", response_model=Acknowledged, summary="Send a code")
async def send_code(token: TokenPath, request: Request, response: Response) -> dict[str, Any]:
    _guard(response)
    await _per_address(request, "retention_link_act_ip", 20, 3600)
    async with transaction() as conn, across_offices(conn):
        await links.send_code(conn, token)
    return {"ok": True, "message": "A code is on its way to the address the link was sent to."}


@router.post("/{token}/verify", response_model=Acknowledged, summary="Enter the code")
async def verify(
    token: TokenPath, body: CodeIn, request: Request, response: Response
) -> dict[str, Any]:
    _guard(response)
    await _per_address(request, "retention_link_act_ip", 20, 3600)
    async with transaction() as conn, across_offices(conn):
        value = await links.verify(conn, token, body.code)
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
    return {"ok": True, "message": "The review is open for the next hour."}


@router.post(
    "/{token}/sign-out", status_code=status.HTTP_204_NO_CONTENT, summary="Close the review here"
)
async def sign_out(token: TokenPath, request: Request, response: Response) -> None:
    _guard(response)
    await links.end(_cookie(request))
    response.delete_cookie(settings.holder_ticket_cookie, domain=settings.cookie_domain, path="/")


@router.get(
    "/{token}/action", response_model=RetentionHolderActionOut, summary="The action, after the code"
)
async def read_action(token: TokenPath, request: Request, response: Response) -> dict[str, Any]:
    _guard(response)
    async with transaction() as conn, across_offices(conn):
        action, _ = await links.holder_in(conn, token, _cookie(request))
        return await actions.detail_for_holder(conn, str(action["action_uuid"]), user_id=None)


@router.post("/{token}/answer", response_model=RetentionHolderActionOut, summary="Answer it")
async def answer(
    token: TokenPath, body: RetentionAnswerIn, request: Request, response: Response
) -> dict[str, Any]:
    """It waits for the Privacy Office to accept it, or send it back."""
    _guard(response)
    async with transaction() as conn, across_offices(conn):
        action, _ = await links.holder_in(conn, token, _cookie(request))
        await actions.answer(
            conn,
            str(action["action_uuid"]),
            user_id=None,
            outcome=body.outcome,
            reason=body.reason,
            keep_until=body.keep_until,
            reconsent=body.reconsent,
            by_link=True,
        )
        return await actions.detail_for_holder(conn, str(action["action_uuid"]), user_id=None)
