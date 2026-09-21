"""Production refuses to boot with a transport that delivers nothing.

Before September 2026 a production process would accept `SMS_TRANSPORT=console`,
skip the outbox write, and report every code as delivered. Nobody could sign
in, and nothing said why.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.config import Settings

PRODUCTION: dict[str, Any] = {
    "_env_file": None,
    "environment": "production",
    "secret_key": "a-real-secret-key-of-at-least-thirty-two-bytes",
    "postgres_password": "not-a-default-password",
    "cookie_secure": True,
    "debug": False,
    "cors_origins": "https://console.example.org",
    "email_transport": "smtp",
    "sms_transport": "http",
    "sms_http_url": "https://sms-gateway.example.org/send",
    "dkms_enabled": True,
}


def _settings(**overrides: Any) -> Settings:
    return Settings(**{**PRODUCTION, **overrides})


class TestTransportsInProduction:
    def test_a_fully_configured_production_boots(self) -> None:
        settings = _settings()
        assert settings.is_production
        assert settings.sms_transport == "http"

    def test_console_sms_is_refused(self) -> None:
        with pytest.raises(ValueError, match="SMS_TRANSPORT"):
            _settings(sms_transport="console")

    def test_null_sms_is_refused(self) -> None:
        with pytest.raises(ValueError, match="SMS_TRANSPORT"):
            _settings(sms_transport="null")

    def test_console_email_is_refused(self) -> None:
        with pytest.raises(ValueError, match="EMAIL_TRANSPORT"):
            _settings(email_transport="console")

    def test_the_http_gateway_must_be_https(self) -> None:
        with pytest.raises(ValueError, match="https"):
            _settings(sms_http_url="http://sms-gateway.example.org/send")

    def test_production_will_not_boot_writing_personal_data_in_the_clear(self) -> None:
        """The same shape of failure as the transports above, and worse.

        `DKMS_ENABLED=false` is correct on a development database full of
        plaintext rows. In production it means every personal field is written
        in the clear, with nothing in the system ever reporting it - the API
        answers 200, the row is saved, and the only way to find out is to look
        in the table.
        """
        with pytest.raises(ValueError, match="DKMS_ENABLED"):
            _settings(dkms_enabled=False)


class TestOutsideProduction:
    def test_local_may_use_console(self) -> None:
        settings = Settings(
            _env_file=None,
            environment="local",
            secret_key="dev-only-secret-key-for-local-use-only",
            cookie_secure=False,
            sms_transport="console",
            email_transport="console",
        )
        assert settings.sms_transport == "console"
