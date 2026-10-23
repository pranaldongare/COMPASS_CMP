"""Turning a cookie into a session, and a session into cookies.

The session token lives in an **HttpOnly** cookie, which is the whole point:
JavaScript cannot read it, so an XSS bug in the console cannot exfiltrate it.
That also means the browser sends it automatically, which is what makes CSRF a
problem — see `csrf.py` for the other half.

`SameSite=Lax` plus a first-party proxy is what makes the cookie arrive at all.
A browser on `localhost:3000` talking to an API on `127.0.0.1:8000` is a
*cross-site* request as far as the cookie is concerned, and the cookie is
silently dropped — which presents as a login that returns 200 and then 401s on
the next call. The console proxies `/api/*` for exactly this reason.

A request that came in through the public relay (`state.relayed`, set by
`middleware.relay_open_sealed` once the relay's key matched) is honoured only
with a data principal's session: the portal is the only thing behind the
relay, and a staff session presented there is one that left the console.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request

from cmp.api.dependencies.csrf import verify_csrf
from cmp.auth.sessions import service as sessions
from cmp.auth.sessions.service import Session
from cmp.core.config import settings
from cmp.core.constants import BACKGROUND_HEADER
from cmp.core.errors import Unauthenticated
from cmp.core.logging import get_logger
from cmp.core.permissions import Role

log = get_logger("cmp.sessions")


async def session_from_request(request: Request) -> Session:
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise Unauthenticated("Sign in to continue")

    # A page's own background poll is authenticated but is not activity.
    background = request.headers.get(BACKGROUND_HEADER) == "1"
    relayed = bool(getattr(request.state, "relayed", False))
    # Through the relay the role is read before the idle window slides: a
    # session refused there must not be kept alive from outside either.
    session = await sessions.load(token, touch=not background and not relayed)
    if session is None:
        raise Unauthenticated("Your session has expired")
    if relayed:
        # The role the session acts with, not the account's: a staff member
        # signed in on the portal with a code holds a data principal's session.
        if session.role != Role.DATA_SUBJECT.value:
            log.warning(
                "relay.session_refused", sid=session.sid, user_id=session.user_id, role=session.role
            )
            raise Unauthenticated("Sign in to continue")
        if not background:
            session = await sessions.load(token)
            if session is None:
                raise Unauthenticated("Your session has expired")

    # Double-submit CSRF. Checked here rather than in middleware because it needs
    # the session's own token, and because safe methods must be exempt.
    verify_csrf(request, session.csrf_token)
    return session


def set_session_cookies(response: Any, token: str, csrf_token: str, *, max_age: int) -> None:
    """Two cookies, deliberately different.

    The session cookie is HttpOnly so script cannot read it. The CSRF cookie must
    be readable by script - that is the whole mechanism: the page reads it and
    echoes it in a header, which a cross-origin page cannot do.
    """
    response.set_cookie(
        settings.cookie_name,
        token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path="/",
    )


def clear_session_cookies(response: Any) -> None:
    for name in (settings.cookie_name, settings.csrf_cookie_name):
        response.delete_cookie(
            name,
            domain=settings.cookie_domain,
            path="/",
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
        )
