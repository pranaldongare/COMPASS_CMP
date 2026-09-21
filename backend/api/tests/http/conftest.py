"""The HTTP harness: the application over ASGI, the real database, a session per role.

Every other suite in this repository calls the service layer. That is the right
altitude for most questions and the wrong one for this one: whether each
endpoint *serves* personal data sealed is a question about response bodies,
and only a request answers it.

**Committed, not rolled back.** The service tests wrap each test in a
transaction the fixture rolls back. That cannot work here: the application
takes its own connections from the pool, and would never see a fixture's
uncommitted rows. So this suite writes real rows, with identifiers no other
test or person would choose - a reserved mobile block, a reserved email domain
- and does not delete them. The browser suite already works this way, for the
same reason.

**Sessions are minted, not signed in.** Signing in through the API would spend a
one-time code per role per test and run into the lockout the API is right to
have. `session_for(role)` mints the session the way the API does after a
successful code, and hands back the two cookies.
"""

from __future__ import annotations

import secrets
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import httpx
import pytest

from cmp.core.config import settings

#: Every HTTP test's contacts come from here, so nothing collides with a real
#: probe on the unique indexes and nothing is mistaken for a person.
DOMAIN = "http-suite.test"
MOBILE_BLOCK = "+9198765"


def fresh(prefix: str = "t") -> str:
    """A token unique enough for an email, a name, a code, within this run."""
    return f"{prefix}{secrets.token_hex(4)}"


def fresh_email(prefix: str = "t") -> str:
    return f"{fresh(prefix)}@{DOMAIN}"


def fresh_mobile() -> str:
    return f"{MOBILE_BLOCK}{secrets.randbelow(100000):05d}"


#: The address the request context resolves for every request the in-process
#: transport carries.
TEST_CLIENT_HOST = "127.0.0.1"


@pytest.fixture
async def http(db_pool: Any, redis_conn: Any) -> AsyncIterator[httpx.AsyncClient]:
    """The application, in-process, with the pool and Redis the other fixtures opened.

    `ASGITransport` does not run the lifespan, and does not need to: the
    session-scoped fixtures already opened what the lifespan would.
    """
    from cmp.bootstrap.application import create_app
    from cmp.db.redis import K_RATE

    # Every request here arrives from the one loopback address, and the public
    # forms limit by address per hour. A second run of the suite within the
    # hour would be refused by the first run's counters, so the per-address
    # buckets for loopback are dropped - those only; a person's own buckets
    # are the behaviour under test.
    async for k in redis_conn.scan_iter(match=f"{K_RATE}:*_ip:{TEST_CLIENT_HOST}"):
        await redis_conn.delete(k)

    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=False
    ) as client:
        yield client


class Session:
    """A signed-in caller: cookies for every request, the CSRF header for writes."""

    def __init__(self, user: dict[str, Any], token: str, csrf: str) -> None:
        self.user = user
        self.cookies = {settings.cookie_name: token, settings.csrf_cookie_name: csrf}
        self.headers = {settings.csrf_header_name: csrf}

    @property
    def uuid(self) -> str:
        return str(self.user["uuid"])


SessionFactory = Callable[..., Awaitable[Session]]


@pytest.fixture
async def session_for(db_pool: Any, redis_conn: Any) -> SessionFactory:
    """Mint a session for a role, creating an account for it if none is given.

    dpo = await session_for("dpo")
    her = await session_for("data_subject", mobile="+919876500001")
    same = await session_for("dpo", user=existing_row)
    """
    from cmp.auth.sessions import service as sessions
    from cmp.core.security import hash_password
    from cmp.db.repositories import users as user_repo

    async def make(
        role: str,
        *,
        user: dict[str, Any] | None = None,
        email: str | None = None,
        mobile: str | None = None,
        full_name: str | None = None,
        organization_id: str | None = None,
        dob: str | None = None,
    ) -> Session:
        if user is None:
            async with db_pool.connection() as conn:
                await conn.set_autocommit(True)
                user = await user_repo.create(
                    conn,
                    full_name=full_name or f"Http {fresh('Person')}",
                    email=email if email is not None else fresh_email(role),
                    mobile=mobile
                    if mobile is not None
                    else (fresh_mobile() if role == "data_subject" else None),
                    role=role,
                    organization_id=organization_id,
                    person_type="external" if role == "data_subject" else "employee",
                    status="active",
                    password_hash=None
                    if role == "data_subject"
                    else hash_password("HttpSuite!2026"),
                    dob=dob,
                )
        token, session = await sessions.create(
            user_id=int(user["id"]),
            user_uuid=str(user["uuid"]),
            role=role,
            ip_address="127.0.0.1",
            user_agent="http-suite",
            mfa_verified=True,
        )
        return Session(dict(user), token, session.csrf_token)

    return make


@pytest.fixture
async def committed(db_pool: Any) -> AsyncIterator[Any]:
    """An autocommit connection, for a fixture that must be visible to the app."""
    async with db_pool.connection() as conn:
        await conn.set_autocommit(True)
        yield conn


# ------------------------------------------------------------- what was sent
#
# Codes and messages leave through Celery. In this suite they are captured
# instead of queued, so a test can read the code it needs off the task's
# arguments the way the person would read it off their phone.


@pytest.fixture
def queued(monkeypatch: Any) -> list[tuple[str, tuple[Any, ...]]]:
    from cmp.tasks import dispatch as dispatch_mod

    sent: list[tuple[str, tuple[Any, ...]]] = []

    def capture(task: Any, *args: Any, **kwargs: Any) -> str:
        sent.append((task.name, args))
        return "queued-in-a-test"

    monkeypatch.setattr(dispatch_mod, "dispatch_required", capture)
    monkeypatch.setattr(dispatch_mod, "dispatch_optional", capture)
    return sent


def last_code(queued: list[tuple[str, tuple[Any, ...]]], task: str, position: int = 2) -> str:
    """The code in the most recent message of this kind, where the person would read it.

    Every code task puts the code at one position in its arguments; the
    default is the second after the contact. Open the value if it travelled
    sealed - a contact does, a code never does.
    """
    from tests.conftest import plain

    for name, args in reversed(queued):
        if name == task:
            return str(plain(args[position]))
    raise AssertionError(f"no {task} was sent; sent: {[n for n, _ in queued]}")
