"""The stand-in provider's sign-in, for the portal's `/sso-mock` page.

Mounted only when `SSO_MOCK` is on, which the settings refuse outside
`local` and `test`. See `cmp.infrastructure.identity.mock` for what it
stands in for, and `cmp.auth.authentication.sso_mock` for the steps.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Request, Response
from pydantic import StringConstraints

from cmp.auth.authentication import sso_mock
from cmp.auth.rate_limit import service as ratelimit
from cmp.core.config import settings
from cmp.db.pool import transaction
from cmp.schemas.common import Acknowledged, OtpCode, Out, Schema
from cmp.validation import Email

router = APIRouter(tags=["development"], include_in_schema=False)

State = Annotated[str, StringConstraints(min_length=16, max_length=128)]


class MockState(Schema):
    state: State


class MockCode(MockState):
    email: Email


class MockConfirm(MockCode):
    code: OtpCode


class Redirect(Out):
    redirect_url: str


def _private(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"


@router.post("/dev/sso/code", response_model=Acknowledged)
async def mock_code(body: MockCode, request: Request, response: Response) -> dict[str, Any]:
    """A code to the address typed, whatever it is."""
    _private(response)
    await ratelimit.enforce(
        "public_link",
        request.client.host if request.client else "unknown",
        limit=settings.public_link_rate_per_minute,
        window_s=60,
        fail_open=False,
    )
    async with transaction() as conn:
        await sso_mock.send_code(conn, state=body.state, email=str(body.email))
    return {"ok": True, "message": "We have sent a code to that address."}


@router.post("/dev/sso/confirm", response_model=Redirect)
async def mock_confirm(body: MockConfirm, response: Response) -> dict[str, Any]:
    """The code back: where to send the browser - the callback."""
    _private(response)
    url = await sso_mock.confirm(state=body.state, email=str(body.email), code=body.code)
    return {"redirect_url": url}


@router.post("/dev/sso/cancel", response_model=Redirect)
async def mock_cancel(body: MockState, response: Response) -> dict[str, Any]:
    _private(response)
    return {"redirect_url": await sso_mock.cancel(state=body.state)}
