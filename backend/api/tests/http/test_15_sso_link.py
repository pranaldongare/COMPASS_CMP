"""An employee link over HTTP, through a stub identity provider (ADR 0034).

A DCO mints an `sso` link for a site; `GET /c/{token}` says so; the start
answers with the provider's URL; the provider's return lands on
`/auth/sso/callback`, which sends the browser back to the link with
`?sso=mobile` and a pending cookie; the mobile is confirmed by code and the
person can read the notice. A code requested on the link sends nothing.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from cmp.core.config import settings
from cmp.infrastructure.identity import state as sso_state
from tests.http.conftest import SessionFactory, fresh_mobile
from tests.http.contract import call
from tests.http.world import World, build
from tests.support.oidc_stub import StubProvider, install


@pytest.fixture(scope="module")
def _world_box() -> dict[str, Any]:
    return {}


@pytest.fixture
async def world(
    http: httpx.AsyncClient, session_for: SessionFactory, queued: Any, _world_box: dict[str, Any]
) -> World:
    if "w" not in _world_box:
        _world_box["w"] = await build(http, session_for, queued)
    return _world_box["w"]


@pytest.fixture
def stub(monkeypatch: pytest.MonkeyPatch) -> Iterator[StubProvider]:
    with install(monkeypatch) as provider:
        yield provider


async def test_an_employee_signs_in_by_sso_and_reads_the_notice(
    http: httpx.AsyncClient, world: World, stub: StubProvider, queued: Any
) -> None:
    minted = await call(
        http,
        "POST",
        f"/sites/{world.site_uuid}/agent",
        template="/sites/{site_uuid}/agent",
        session=world.dco,
        expect=(200, 201),
        check_sealed=False,
        json={
            "expires_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
            "audience_mode": "sso",
        },
    )
    token = minted.json()["url_path"].rsplit("/", 1)[-1]
    opened = await call(http, "GET", f"/c/{token}", template="/c/{token}")
    assert opened.json()["audience_mode"] == "sso"

    # A code on an `sso` link: the usual sentence, and nothing sent.
    before = len(queued)
    await call(
        http,
        "POST",
        f"/c/{token}/otp",
        template="/c/{token}/otp",
        json={"contact": "+919800000000"},
    )
    assert len(queued) == before

    start = await call(http, "GET", f"/c/{token}/sso/start", template="/c/{token}/sso/start")
    query = parse_qs(urlparse(start.json()["redirect_url"]).query)
    employee = f"EMP-{fresh_mobile()[-6:]}"
    code = stub.code_for(stub.id_token(nonce=query["nonce"][0], employee_id=employee, email=None))

    back = await call(
        http,
        "GET",
        "/auth/sso/callback",
        params={"state": query["state"][0], "code": code},
        expect=303,
    )
    assert back.headers["location"].endswith(f"/c/{token}?sso=mobile")
    pending = back.cookies.get(sso_state.PENDING_COOKIE)
    assert pending

    mobile = fresh_mobile()
    await call(
        http,
        "POST",
        f"/c/{token}/sso/mobile",
        template="/c/{token}/sso/mobile",
        cookies={sso_state.PENDING_COOKIE: pending},
        json={"mobile": mobile},
    )
    sent = [args for name, args in queued if name.endswith("send_consent_code")]
    assert sent, "a code went to the mobile"
    confirmed = await call(
        http,
        "POST",
        f"/c/{token}/sso/mobile/verify",
        template="/c/{token}/sso/mobile/verify",
        cookies={sso_state.PENDING_COOKIE: pending},
        json={"mobile": mobile, "code": sent[-1][1]},
    )
    session_cookie = confirmed.cookies.get(settings.cookie_name)
    assert session_cookie

    # Her date of birth is asked next; the notice then serves as on any link.
    me = await call(
        http,
        "GET",
        "/auth/me",
        cookies={settings.cookie_name: session_cookie},
    )
    assert me.json()["role"] == "data_subject"
    assert me.json()["is_minor"] is None

    # An unknown state is a 404 that says nothing else.
    await call(
        http,
        "GET",
        "/auth/sso/callback",
        params={"state": "never-issued-state-0000", "code": "x"},
        expect=404,
    )
