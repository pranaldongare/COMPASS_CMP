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
