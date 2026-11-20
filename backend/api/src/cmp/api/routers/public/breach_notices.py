"""A breach notice by its link, for somebody with no account (2026-11-20).

`/breach-notices/{token}` is what the portal page `/breach-notice/{token}`
calls. The link alone shows the breach's reference and, masked, the mobile a
code will go to; the code, sent by text to the number on the breach's list,
opens the notice. See `cmp.domain.breach.notice_link`.

As on every public route: rate limited per address, `Referrer-Policy:
no-referrer`, the token scrubbed from access logs, and every way a link can
fail answering the same 404.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Request, Response
from pydantic import Field

from cmp.auth.rate_limit import service as ratelimit
from cmp.core.config import settings
from cmp.db.pool import transaction
from cmp.domain.breach import notice_link
from cmp.schemas.common import Acknowledged, OtpCode, Out, Schema

router = APIRouter(prefix="/breach-notices", tags=["breach notices"])

TokenPath = Annotated[str, Field(min_length=64, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]


class BreachNoticeLinkOut(Out):
    """What the link alone shows."""

    reference: str
    #: The mobile the code goes to, masked.
    code_goes_to: str


class BreachNoticeCodeIn(Schema):
    code: OtpCode


class BreachNoticeByLinkOut(Out):
    """The notice, in full: the five things Rule 7(1) requires."""

    reference: str
    version: int
    approved_at: datetime | None
    what_happened: str
    consequences: str
    measures: str
    protective_steps: str
    contact: str


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


@router.get(
    "/{token}", response_model=BreachNoticeLinkOut, summary="What the link opens, before the code"
)
async def open_link(token: TokenPath, request: Request, response: Response) -> dict[str, Any]:
    _guard(response)
    await _per_address(request, "breach_notice_link_ip", settings.public_link_rate_per_minute, 60)
    async with transaction() as conn:
        row = await notice_link.open_link(conn, token)
        return {"reference": row["reference"], "code_goes_to": await notice_link.masked_mobile(row)}


@router.post("/{token}/code", response_model=Acknowledged, summary="Send a code to the mobile")
async def send_code(token: TokenPath, request: Request, response: Response) -> dict[str, Any]:
    _guard(response)
    await _per_address(request, "breach_notice_act_ip", 20, 3600)
    async with transaction() as conn:
        await notice_link.send_code(conn, token)
    return {"ok": True, "message": "A code is on its way to the mobile the notice was sent to."}


@router.post(
    "/{token}/open", response_model=BreachNoticeByLinkOut, summary="Enter the code: the notice"
)
async def open_notice(
    token: TokenPath, body: BreachNoticeCodeIn, request: Request, response: Response
) -> dict[str, Any]:
    _guard(response)
    await _per_address(request, "breach_notice_act_ip", 20, 3600)
    async with transaction() as conn:
        return await notice_link.read(conn, token, body.code)
