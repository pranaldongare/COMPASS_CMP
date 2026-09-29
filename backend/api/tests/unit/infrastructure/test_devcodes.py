"""The development popup's codes: kept only when asked, only locally.

A code shown on the screen that asks for it proves nothing about who holds
the phone, so every one of these is about the switch staying off where it
must, as much as about it working where it may.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from cmp.infrastructure import devcodes


class _List:
    """Enough of a Redis pipeline for `record`."""

    def __init__(self) -> None:
        self.items: list[str] = []

    def pipeline(self) -> _List:
        return self

    def lpush(self, _key: str, value: str) -> None:
        self.items.insert(0, value)

    def ltrim(self, *_: Any) -> None: ...

    def expire(self, *_: Any) -> None: ...

    def execute(self) -> None: ...


@pytest.fixture
def kept(monkeypatch: Any) -> _List:
    store = _List()
    monkeypatch.setattr("cmp.core.config.settings.dev_show_codes", True)
    monkeypatch.setattr(devcodes, "_redis", lambda: store)
    return store


@pytest.mark.parametrize(
    ("channel", "text"),
    [
        ("email", "123456 is your COMPASS sign-in code\nYour sign-in code is:\n\n    123456\n"),
        ("sms", "COMPASS: 123456 confirms this mobile number. Enter it to finish signing up."),
        ("email", "Your verification code is 123456 for request RR-2026-000042."),
    ],
)
def test_the_code_is_kept_from_every_shape_the_templates_use(
    kept: _List, channel: str, text: str
) -> None:
    devcodes.record(channel=channel, to="priya@example.org", text=text)
    entry = json.loads(kept.items[0])
    assert entry["code"] == "123456"
    assert entry["to"] == "priya@example.org"


def test_a_message_with_no_code_keeps_nothing(kept: _List) -> None:
    devcodes.record(channel="email", to="a@x.org", text="Your request RR-2026-000042 is closed.")
    assert kept.items == []


def test_nothing_is_kept_unless_asked(monkeypatch: Any) -> None:
    monkeypatch.setattr("cmp.core.config.settings.dev_show_codes", False)
    monkeypatch.setattr(devcodes, "_redis", lambda: pytest.fail("touched Redis while off"))
    devcodes.record(channel="sms", to="+919876543210", text="COMPASS: 123456 confirms")


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_the_setting_is_refused_outside_local_development(environment: str) -> None:
    from cmp.core.config import Settings

    with pytest.raises(ValueError, match="DEV_SHOW_CODES"):
        Settings(
            ENVIRONMENT=environment,
            DEV_SHOW_CODES=True,
            SECRET_KEY="x" * 40,
            POSTGRES_PASSWORD="not-a-default-password",
            COOKIE_SECURE=True,
            EMAIL_TRANSPORT="smtp",
            SMS_TRANSPORT="http",
            SMS_HTTP_URL="https://sms.example.org",
            DKMS_ENABLED=True,
            BLIND_INDEX_KEY="y" * 40,
            CORS_ORIGINS="https://console.example.org",
        )


def test_the_route_exists_only_when_asked(monkeypatch: Any) -> None:
    from cmp.api.routers import _development_routers

    monkeypatch.setattr("cmp.core.config.settings.dev_show_codes", False)
    assert _development_routers() == ()
    monkeypatch.setattr("cmp.core.config.settings.dev_show_codes", True)
    assert [r.routes[0].path for r in _development_routers()] == ["/dev/codes"]


# ------------------------------------------------ only the tab that asked sees a code
#
# Every open portal and console polls `/dev/codes`, and a list shared by all of
# them showed each code in every window on every machine. The tab whose request
# caused a code is carried to the worker, kept with the code, and matched.

TAB = "tab-0123456789abcdef"


class _AsyncList:
    def __init__(self, items: list[str]) -> None:
        self.items = items

    async def lrange(self, _key: str, _start: int, _end: int) -> list[str]:
        return self.items


def _entry(code: str, client: str | None, at: float | None = None) -> str:
    import time

    return json.dumps(
        {
            "to": "a@x.org",
            "channel": "email",
            "code": code,
            "at": at or time.time(),
            "client": client,
        }
    )


def test_a_code_is_kept_with_the_tab_whose_request_caused_it(kept: _List) -> None:
    from cmp.core.context import RequestContext, use_context

    with use_context(RequestContext(request_id="r", extra={devcodes.CONTEXT_KEY: TAB})):
        devcodes.record(channel="sms", to="+919876543210", text="COMPASS: 123456 confirms")
    assert json.loads(kept.items[0])["client"] == TAB


async def test_a_tab_is_shown_its_own_codes_and_no_one_elses() -> None:
    store = _AsyncList(
        [_entry("111111", TAB), _entry("222222", "tab-somebody-else"), _entry("333333", None)]
    )

    mine = await devcodes.recent(store, client=TAB)
    assert [e["code"] for e in mine] == ["111111"]
    # The tab id is how codes are matched; it is not handed back.
    assert "client" not in mine[0]
    # A tab that says nothing about itself is shown nothing.
    assert await devcodes.recent(store, client=None) == []


def test_only_a_well_formed_tab_id_is_taken() -> None:
    assert devcodes.client_id(TAB) == TAB
    for bad in (None, "", "short", "has spaces in it!", "x" * 65, "evil\nX-Injected: 1"):
        assert devcodes.client_id(bad) is None


def test_the_tab_travels_with_the_task_to_the_worker() -> None:
    from types import SimpleNamespace

    from cmp.core.context import RequestContext, current_context, use_context
    from cmp.tasks.app import _bind_task_context
    from cmp.tasks.dispatch import _headers

    with use_context(RequestContext(request_id="r-1", extra={devcodes.CONTEXT_KEY: TAB})):
        headers = _headers()
    assert headers == {"request_id": "r-1", "dev_client": TAB}

    # The worker binds what the producer put in the headers.
    with use_context(RequestContext(request_id="-")):
        _bind_task_context(task_id="t", task=SimpleNamespace(request=SimpleNamespace(**headers)))
        assert current_context().extra.get(devcodes.CONTEXT_KEY) == TAB
        assert current_context().request_id == "r-1"


def test_the_request_carries_the_tab_id_only_while_the_popup_is_on(monkeypatch: Any) -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from cmp.api.middleware.request_context import RequestContextMiddleware
    from cmp.core.context import current_context

    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/probe")
    def probe() -> dict[str, Any]:
        return dict(current_context().extra)

    client = TestClient(app)
    monkeypatch.setattr("cmp.core.config.settings.dev_show_codes", True)
    assert client.get("/probe", headers={devcodes.CLIENT_HEADER: TAB}).json() == {"dev_client": TAB}
    monkeypatch.setattr("cmp.core.config.settings.dev_show_codes", False)
    assert client.get("/probe", headers={devcodes.CLIENT_HEADER: TAB}).json() == {}
