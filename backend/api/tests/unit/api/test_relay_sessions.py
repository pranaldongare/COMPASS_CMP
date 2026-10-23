"""Through the public relay, only a data principal's session is honoured.

The portal and the console share the cookie name, and some routes the portal
needs (`/auth/me`, `/auth/sessions`, `/notifications`) accept any signed-in
caller. Without this a console session taken off a staff machine would open
the staff feed, with every name in it opened, to anyone on the internet who
holds it. `RelayOpenSealedMiddleware` marks the scope of a request whose
relay key matched; `session_from_request` refuses any session there whose
acting role is not `data_subject` (review 2026-10-23, finding 4).

The session store is the one thing stood in for: `sessions.load`, which
reads Redis. Everything between the cookie and the route is the real code.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Annotated, Any

import httpx
import pytest
from fastapi import Depends, FastAPI
from pydantic import SecretStr

from cmp.api import errors
from cmp.api.dependencies.authentication import current_principal
from cmp.api.dependencies.sessions import session_from_request
from cmp.api.errors import handlers
from cmp.api.middleware.relay_open_sealed import RelayOpenSealedMiddleware
from cmp.auth.identity import Principal
from cmp.auth.sessions import service as sessions
from cmp.auth.sessions.service import Session
from cmp.core.config import settings
from cmp.core.constants import BACKGROUND_HEADER

KEY = "k" * 40
CSRF = "csrf-token-of-this-session"


def _session(role: str, account_role: str | None = None, *, partial: bool = False) -> Session:
    now = time.time()
    return Session(
        sid=f"sid-{role}-{account_role}",
        user_id=7,
        user_uuid="7e57-u5er",
        role=role,
        account_role=account_role or role,
        created_at=now,
        last_seen_at=now,
        expires_at=now + 3600,
        ip_address=None,
        user_agent=None,
        mfa_verified=not partial,
        partial=partial,
        csrf_token=CSRF,
    )


#: Cookie token -> the session it resolves to.
SESSIONS = {
    "staff": _session("dpo"),
    "staff-partial": _session("admin", partial=True),
    "subject": _session("data_subject"),
    # A staff member signed in on the portal with a code: a data principal's
    # session on a staff account (staff-as-principal).
    "staff-as-principal": _session("data_subject", "dpo"),
}


class Store:
    """Stands in for `sessions.load`; records each call and whether it touched."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, bool]] = []

    async def load(self, token: str, *, touch: bool = True) -> Session | None:
        self.calls.append((token, touch))
        return SESSIONS.get(token)


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> Store:
    fake = Store()
    monkeypatch.setattr(sessions, "load", fake.load)
    monkeypatch.setattr(settings, "relay_ingress_key", SecretStr(KEY))

    # A refused CSRF check is audited on a connection of its own; no database here.
    async def not_recorded(request: Any, exc: Any) -> None:
        return None

    monkeypatch.setattr(handlers, "_record_denial", not_recorded)
    return fake


def _app() -> FastAPI:
    app = FastAPI()
    errors.install(app)

    @app.get("/auth/me")
    async def me(session: Annotated[Session, Depends(session_from_request)]) -> dict[str, Any]:
        return {"role": session.role}

    @app.get("/notifications")
    async def notifications(
        principal: Annotated[Principal, Depends(current_principal)],
    ) -> dict[str, Any]:
        return {"role": principal.role.value}

    @app.post("/auth/logout")
    async def logout(session: Annotated[Session, Depends(session_from_request)]) -> dict[str, Any]:
        return {"sid": session.sid}

    app.add_middleware(RelayOpenSealedMiddleware)
    return app


@pytest.fixture
async def http() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def _headers(token: str, *, relayed: bool, **extra: str) -> dict[str, str]:
    headers = {"Cookie": f"{settings.cookie_name}={token}", **extra}
    if relayed:
        headers["X-CMP-Relay-Key"] = KEY
    return headers


class TestAStaffSessionThroughTheRelay:
    @pytest.mark.parametrize("path", ["/auth/me", "/notifications"])
    async def test_is_refused_as_unauthenticated(
        self, http: httpx.AsyncClient, store: Store, path: str
    ) -> None:
        response = await http.get(path, headers=_headers("staff", relayed=True))

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthenticated"
        # Nothing says why: to the caller it is a session that does not work.
        assert "staff" not in response.text.lower()

    async def test_a_write_is_refused_before_its_csrf_check(
        self, http: httpx.AsyncClient, store: Store
    ) -> None:
        response = await http.post(
            "/auth/logout", headers=_headers("staff", relayed=True, **{"X-CSRF-Token": CSRF})
        )

        assert response.status_code == 401

    async def test_a_partial_staff_session_is_refused_too(
        self, http: httpx.AsyncClient, store: Store
    ) -> None:
        response = await http.get("/auth/me", headers=_headers("staff-partial", relayed=True))

        assert response.status_code == 401

    async def test_is_not_kept_alive_by_being_refused(
        self, http: httpx.AsyncClient, store: Store
    ) -> None:
        """Read without sliding the idle window: polling a stolen session
        through the portal does not keep it from expiring."""
        await http.get("/auth/me", headers=_headers("staff", relayed=True))

        assert store.calls == [("staff", False)]


class TestTheSameStaffSessionInside:
    @pytest.mark.parametrize("path", ["/auth/me", "/notifications"])
    async def test_works_without_the_key(
        self, http: httpx.AsyncClient, store: Store, path: str
    ) -> None:
        response = await http.get(path, headers=_headers("staff", relayed=False))

        assert response.status_code == 200
        assert response.json() == {"role": "dpo"}
        assert store.calls == [("staff", True)]

    async def test_a_wrong_key_is_not_the_relay(
        self, http: httpx.AsyncClient, store: Store
    ) -> None:
        """Only a matching key marks a request relayed; anything else is a
        direct caller inside, as before."""
        headers = _headers("staff", relayed=False, **{"X-CMP-Relay-Key": "w" * 40})
        response = await http.get("/auth/me", headers=headers)

        assert response.status_code == 200


class TestADataPrincipalThroughTheRelay:
    @pytest.mark.parametrize("token", ["subject", "staff-as-principal"])
    @pytest.mark.parametrize("path", ["/auth/me", "/notifications"])
    async def test_is_served(
        self, http: httpx.AsyncClient, store: Store, token: str, path: str
    ) -> None:
        """The session's acting role decides, not the account's: a staff
        member's own code-signed-in principal session keeps working."""
        response = await http.get(path, headers=_headers(token, relayed=True))

        assert response.status_code == 200
        assert response.json() == {"role": "data_subject"}

    async def test_a_write_still_needs_its_csrf_token(
        self, http: httpx.AsyncClient, store: Store
    ) -> None:
        refused = await http.post("/auth/logout", headers=_headers("subject", relayed=True))
        served = await http.post(
            "/auth/logout", headers=_headers("subject", relayed=True, **{"X-CSRF-Token": CSRF})
        )

        assert refused.status_code == 403
        assert served.status_code == 200

    async def test_slides_its_idle_window_once_it_is_allowed(
        self, http: httpx.AsyncClient, store: Store
    ) -> None:
        await http.get("/auth/me", headers=_headers("subject", relayed=True))

        assert store.calls == [("subject", False), ("subject", True)]

    async def test_a_background_poll_does_not_slide_it(
        self, http: httpx.AsyncClient, store: Store
    ) -> None:
        await http.get(
            "/auth/me", headers=_headers("subject", relayed=True, **{BACKGROUND_HEADER: "1"})
        )

        assert store.calls == [("subject", False)]

    async def test_an_unknown_session_is_still_expired(
        self, http: httpx.AsyncClient, store: Store
    ) -> None:
        response = await http.get("/auth/me", headers=_headers("gone", relayed=True))

        assert response.status_code == 401
