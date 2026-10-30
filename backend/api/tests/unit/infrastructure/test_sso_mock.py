"""The stand-in provider for `sso` links (`SSO_MOCK`, 2026-10-30).

What it asserts is made from the address alone, so the same address is the
same employee every time; its routes exist only when asked for; and the
settings refuse it anywhere a real person signs in.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.infrastructure.identity import mock


def test_the_same_address_is_the_same_employee() -> None:
    one = mock.claims_for("Priya.Shah@Example.org")
    again = mock.claims_for("  priya.shah@example.org ")
    assert one == again
    assert one.employee_id.startswith("MOCK-") and len(one.employee_id) == 13
    assert one.email == "priya.shah@example.org"
    assert one.name == "Priya Shah"
    assert mock.claims_for("ravi@example.org").employee_id != one.employee_id


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_the_setting_is_refused_outside_local_development(environment: str) -> None:
    from cmp.core.config import Settings

    with pytest.raises(ValueError, match="SSO_MOCK"):
        Settings(
            ENVIRONMENT=environment,
            SSO_MOCK=True,
            DEV_SHOW_CODES=False,
            SECRET_KEY="x" * 40,
            POSTGRES_PASSWORD="not-a-default-password",
            COOKIE_SECURE=True,
            SMTP_SERVER="relay.organisation.example",
            SMS_TRANSPORT="http",
            SMS_HTTP_URL="https://sms.example.org",
            DKMS_ENABLED=True,
            BLIND_INDEX_KEY="y" * 40,
            CORS_ORIGINS="https://console.example.org",
            BREACH_TICKET_EMAIL_DOMAINS="organisation.example",
            NOTIFICATION_EMAIL_FROM="privacy@organisation.example",
        )


def test_the_routes_exist_only_when_asked(monkeypatch: Any) -> None:
    from cmp.api.routers import _development_routers

    monkeypatch.setattr("cmp.core.config.settings.dev_show_codes", False)
    monkeypatch.setattr("cmp.core.config.settings.sso_mock", False)
    assert _development_routers() == ()
    monkeypatch.setattr("cmp.core.config.settings.sso_mock", True)
    assert [route.path for r in _development_routers() for route in r.routes] == [  # type: ignore[attr-defined]
        "/dev/sso/code",
        "/dev/sso/confirm",
        "/dev/sso/cancel",
    ]
