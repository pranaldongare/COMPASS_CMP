"""VerifyEmail and the organisation's domains over HTTP (ADR 0046).

The administrator's alone: the settings (the key never served), the domains,
and asking about one address. Then a console sign-in by a leaver on a company
domain is refused before any code is sent.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from cmp.domain.employees import check
from tests.conftest import plain
from tests.http.conftest import SessionFactory
from tests.http.contract import call

PATH = "/employee-check"
KEY = "verify-http-key-0123456789"
PASSWORD = "HttpSuite!2026"


def stand_in(active: bool) -> httpx.MockTransport:
    def answer(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.headers.get("x-api-key") == KEY
        return httpx.Response(
            200, json={"MySingleID": body["MySingleID"], "IsActive": active, "Status": True}
        )

    return httpx.MockTransport(answer)


async def test_the_settings_are_the_administrators_and_a_leaver_cannot_sign_in(
    http: httpx.AsyncClient, session_for: SessionFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin = await session_for("admin")
    for role in ("dpo", "management"):
        who = await session_for(role)
        await call(http, "GET", PATH, session=who, expect=403)
        await call(http, "PUT", PATH, session=who, expect=403, json={"enabled": False})

    saved = await call(
        http,
        "PUT",
        PATH,
        session=admin,
        json={"base_url": "https://verify.test/api/", "api_key": KEY, "enabled": True},
    )
    assert saved.json()["base_url"] == "https://verify.test/api"
    assert saved.json()["api_key_set"] is True and KEY not in saved.text
    read = await call(http, "GET", PATH, session=admin)
    assert KEY not in read.text and "api_key_sealed" not in read.text
    await call(
        http,
        "PUT",
        PATH,
        session=admin,
        expect=422,
        json={"base_url": "https://verify.test/api/VerifyEmail", "enabled": True},
    )

    # The domains: the one list of who is inside the organisation.
    leaver = await session_for("dco")
    address = plain(leaver.user["email"])
    domain = address.rsplit("@", 1)[1]
    added = await call(
        http, "POST", f"{PATH}/domains", session=admin, expect=201, json={"domain": domain}
    )
    assert domain in [d["domain"] for d in added.json()]
    await call(http, "POST", f"{PATH}/domains", session=admin, expect=422, json={"domain": "a@b"})

    monkeypatch.setattr(check, "transport", stand_in(active=False))
    tested = await call(http, "POST", f"{PATH}/test", session=admin, json={"email": address})
    assert tested.json()["result"] == "inactive" and tested.json()["on_company_domain"]

    refused = await call(
        http,
        "POST",
        "/auth/login",
        expect=403,
        json={"login": address, "password": PASSWORD},
    )
    assert "active employee" in refused.json()["error"]["message"]

    monkeypatch.setattr(check, "transport", stand_in(active=True))
    first = await call(http, "POST", "/auth/login", json={"login": address, "password": PASSWORD})
    assert first.json()["mfa_required"] is True

    left: Any = await call(
        http,
        "DELETE",
        f"{PATH}/domains/{domain}",
        template=f"{PATH}/domains/{{domain}}",
        session=admin,
    )
    assert domain not in [d["domain"] for d in left.json()]
    await call(http, "PUT", PATH, session=admin, json={"base_url": None, "enabled": False})
