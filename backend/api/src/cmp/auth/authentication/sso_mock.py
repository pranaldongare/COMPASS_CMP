"""The stand-in provider's sign-in page, for local development (`SSO_MOCK`).

The page a real provider would show, done the platform's way: any email
address, a code sent to it, and back to the callback with an assertion for
that address (`cmp.infrastructure.identity.mock`). From there the sign-in is
the real one (`cmp.auth.authentication.sso`).

Each step needs the sign-in `/c/{token}/sso/start` began, which it reads
and leaves for the callback; an unknown or expired one is `NotFound`, and
the person starts again from the link.
"""

from __future__ import annotations

from typing import Any

from cmp.auth.authentication import otp
from cmp.auth.rate_limit import service as ratelimit
from cmp.core.config import settings
from cmp.core.errors import NotFound
from cmp.db.sql import Conn
from cmp.domain.consent.service import resolve_link
from cmp.infrastructure.identity import mock
from cmp.infrastructure.identity import state as sso_state


async def _started(state: str) -> dict[str, Any]:
    started = await sso_state.peek(state)
    if not started:
        raise NotFound("Sign-in")
    return started


async def send_code(conn: Conn, *, state: str, email: str) -> None:
    """A code to whatever address was typed."""
    started = await _started(state)
    link = await resolve_link(conn, str(started["link_token"]))
    address = email.strip().lower()
    await ratelimit.enforce(
        "sso_mock",
        ratelimit.contact_key(address),
        limit=settings.otp_requests_per_contact_per_hour,
        window_s=3600,
        message="Too many code requests for this address.",
    )
    issued = await otp.issue(otp.Scope.SSO_MOCK, f"{state}:{address}")
    from cmp.tasks.authentication import send_consent_code
    from cmp.tasks.dispatch import dispatch_required

    dispatch_required(send_consent_code, address, issued.code, link["project_name"])


async def confirm(*, state: str, email: str, code: str) -> str:
    """The code came back: where to send the browser, the callback."""
    started = await _started(state)
    address = email.strip().lower()
    await otp.require(otp.Scope.SSO_MOCK, f"{state}:{address}", code)
    return await mock.signed_in(state=state, nonce=str(started["nonce"]), email=address)


async def cancel(*, state: str) -> str:
    await _started(state)
    return mock.cancelled(state=state)
