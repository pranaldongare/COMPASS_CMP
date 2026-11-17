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
    "smtp_host": "relay.organisation.example",
    "sms_transport": "http",
    "sms_http_url": "https://sms-gateway.example.org/send",
    "dkms_enabled": True,
    "blind_index_key": "a-real-blind-index-key-of-thirty-two-bytes",
    "breach_ticket_email_domains": ("organisation.example",),
    "notification_email_from": "privacy@organisation.example",
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

    def test_sns_boots_with_no_gateway_address(self) -> None:
        settings = _settings(sms_transport="sns", sms_http_url="")
        assert settings.sms_transport == "sns"
        assert settings.sms_sns_region == "ap-south-1"

    def test_null_sms_is_refused(self) -> None:
        with pytest.raises(ValueError, match="SMS_TRANSPORT"):
            _settings(sms_transport="null")

    def test_no_mail_server_is_refused(self) -> None:
        with pytest.raises(ValueError, match="SMTP_SERVER"):
            _settings(smtp_host="")

    def test_the_http_gateway_must_be_https(self) -> None:
        with pytest.raises(ValueError, match="https"):
            _settings(sms_http_url="http://sms-gateway.example.org/send")

    def test_production_will_not_boot_on_the_development_index_key(self) -> None:
        """A blind index under a key in the repository is a lookup table for
        anyone holding the repository."""
        with pytest.raises(ValueError, match="BLIND_INDEX_KEY"):
            _settings(blind_index_key="dev-only-blind-index-key-32-bytes-long!")

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


class TestBreachTicketDomainsInProduction:
    """ "Internal" is only as good as the list (BD-12, ADR 0023)."""

    def test_an_empty_list_is_refused(self) -> None:
        with pytest.raises(ValueError, match="BREACH_TICKET_EMAIL_DOMAINS"):
            _settings(breach_ticket_email_domains=())

    def test_the_development_domain_alone_is_refused(self) -> None:
        with pytest.raises(ValueError, match="BREACH_TICKET_EMAIL_DOMAINS"):
            _settings(breach_ticket_email_domains=("cmp.local",))

    def test_a_placeholder_sender_is_refused(self) -> None:
        with pytest.raises(ValueError, match="NOTIFICATION_EMAIL_FROM"):
            _settings(notification_email_from="privacy@example.org")

    def test_a_comma_separated_value_is_read_as_a_list(self) -> None:
        settings = _settings(breach_ticket_email_domains="organisation.example, lab.example")
        assert settings.breach_ticket_email_domains == ("organisation.example", "lab.example")


class TestSnsIsCheckedInAnyEnvironment:
    """Each of these is a text refused one at a time, while somebody waits for
    a code (ADR 0043)."""

    @staticmethod
    def _local(**overrides: Any) -> Settings:
        return Settings(
            **{
                "_env_file": None,
                "environment": "local",
                "secret_key": "dev-only-secret-key-for-local-use-only",
                "cookie_secure": False,
                "sms_transport": "sns",
                **overrides,
            }
        )

    def test_the_defaults_boot(self) -> None:
        settings = self._local()
        assert (settings.sms_sns_region, settings.sms_sns_sender_id) == ("ap-south-1", "")
        assert settings.sms_default_country_code == "91"

    @pytest.mark.parametrize("region", ["", "  ", "mumbai", "ap-south", "https://sns.aws"])
    def test_a_region_that_is_not_one_is_refused(self, region: str) -> None:
        with pytest.raises(ValueError, match="SMS_SNS_REGION"):
            self._local(sms_sns_region=region)

    @pytest.mark.parametrize("code", ["+91", "", "0", "091", "9191", "IN"])
    def test_a_country_code_that_is_not_digits_is_refused(self, code: str) -> None:
        with pytest.raises(ValueError, match="SMS_DEFAULT_COUNTRY_CODE"):
            self._local(sms_default_country_code=code)

    @pytest.mark.parametrize("sender", ["AB", "A B", "123456", "TWELVELETTER", "CMP_1"])
    def test_a_sender_id_sns_would_refuse_is_refused(self, sender: str) -> None:
        with pytest.raises(ValueError, match="SMS_SNS_SENDER_ID"):
            self._local(sms_sns_sender_id=sender)

    @pytest.mark.parametrize("sender", ["COMPASS", "CMP-1", "Compass2026"])
    def test_a_sender_id_sns_takes_boots(self, sender: str) -> None:
        assert self._local(sms_sns_sender_id=sender).sms_sns_sender_id == sender

    def test_none_of_it_is_looked_at_for_another_transport(self) -> None:
        settings = self._local(
            sms_transport="console", sms_sns_region="", sms_default_country_code="+91"
        )
        assert settings.sms_transport == "console"
