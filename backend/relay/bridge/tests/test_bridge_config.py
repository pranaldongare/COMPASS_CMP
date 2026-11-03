"""The bridge's settings (`bridge_config`): the defaults, what is required, the
ranges, the collector's public key, and the shared rules as the bridge applies
them. The shared settings themselves are tested in common/tests/test_core.py."""

from __future__ import annotations

import base64

import pytest

from cmp_relay import bridge_config, config, sealing


@pytest.fixture
def public_key() -> str:
    return sealing.generate_keypair()[1]


def _bridge_env(public_key: str, **extra: str) -> dict[str, str]:
    return {
        "RELAY_REQUEST_QUEUE_URL": "https://sqs.ap-south-1.amazonaws.com/1/requests",
        "RELAY_BUCKET": "bodies",
        "RELAY_REPLY_QUEUE_URL": "https://sqs.ap-south-1.amazonaws.com/1/replies-a",
        "RELAY_COLLECTOR_PUBLIC_KEY": public_key,
        **extra,
    }


class TestBridgeConfig:
    def test_bridge_defaults(self, public_key: str) -> None:
        s = bridge_config.bridge_settings(_bridge_env(public_key))
        assert s.common.environment == "production"
        assert not s.common.is_local
        assert s.common.region == "ap-south-1"
        assert s.common.endpoint_url is None
        assert s.common.cookie_names == frozenset(
            {"cmp_session", "cmp_csrf", "cmp_ticket", "cmp_sso_pending"}
        )
        assert s.common.csrf_header == "X-CSRF-Token"
        assert not s.common.allow_dev_routes
        assert (s.host, s.port) == ("127.0.0.1", 8080)
        # 50 s plus the bridge's 2 s grace stays under the front door's 60 s.
        assert (s.deadline_s, s.upload_deadline_s) == (25, 50)
        assert s.max_body_bytes == 26 * 1024 * 1024
        assert (s.reply_pollers, s.ping_interval_s, s.client_ip_hop) == (2, 10, 1)
        expected = sealing.load_public(public_key)
        assert sealing.key_id(s.collector_public) == sealing.key_id(expected)

    def test_settings_come_from_os_environ_by_default(
        self, public_key: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for name, value in _bridge_env(public_key, RELAY_BRIDGE_PORT="8099").items():
            monkeypatch.setenv(name, value)
        assert bridge_config.bridge_settings().port == 8099

    @pytest.mark.parametrize(
        "missing",
        [
            "RELAY_REQUEST_QUEUE_URL",
            "RELAY_BUCKET",
            "RELAY_REPLY_QUEUE_URL",
            "RELAY_COLLECTOR_PUBLIC_KEY",
        ],
    )
    def test_bridge_required_settings(self, public_key: str, missing: str) -> None:
        env = _bridge_env(public_key)
        env.pop(missing)
        with pytest.raises(config.ConfigError, match=missing):
            bridge_config.bridge_settings(env)
        env[missing] = "   "
        with pytest.raises(config.ConfigError, match=missing):
            bridge_config.bridge_settings(env)

    @pytest.mark.parametrize("environment", ["production", "staging"])
    def test_local_only_settings_are_refused_outside_local(
        self, public_key: str, environment: str
    ) -> None:
        for extra in (
            {"RELAY_ENDPOINT_URL": "http://127.0.0.1:5000"},
            {"RELAY_ALLOW_DEV_ROUTES": "true"},
        ):
            env = _bridge_env(public_key, RELAY_ENVIRONMENT=environment, **extra)
            with pytest.raises(config.ConfigError, match=next(iter(extra))):
                bridge_config.bridge_settings(env)

    @pytest.mark.parametrize(
        ("name", "value"),
        [
            ("RELAY_DEADLINE_S", "1"),
            ("RELAY_DEADLINE_S", "121"),
            ("RELAY_DEADLINE_S", "soon"),
            ("RELAY_UPLOAD_DEADLINE_S", "10"),  # shorter than the ordinary deadline
            ("RELAY_UPLOAD_DEADLINE_S", "601"),
            ("RELAY_BRIDGE_PORT", "0"),
            ("RELAY_BRIDGE_PORT", "70000"),
            ("RELAY_MAX_BODY_BYTES", "10"),
            ("RELAY_REPLY_POLLERS", "0"),
            ("RELAY_PING_INTERVAL_S", "0"),
            ("RELAY_CLIENT_IP_HOP", "6"),
        ],
    )
    def test_bridge_numbers_out_of_range_are_refused(
        self, public_key: str, name: str, value: str
    ) -> None:
        with pytest.raises(config.ConfigError, match=name):
            bridge_config.bridge_settings(_bridge_env(public_key, **{name: value}))

    def test_the_upload_deadline_is_never_shorter_than_the_ordinary_one(
        self, public_key: str
    ) -> None:
        s = bridge_config.bridge_settings(_bridge_env(public_key, RELAY_DEADLINE_S="60"))
        assert (s.deadline_s, s.upload_deadline_s) == (60, 60)
        s = bridge_config.bridge_settings(_bridge_env(public_key, RELAY_UPLOAD_DEADLINE_S="150"))
        assert s.upload_deadline_s == 150  # allowed, with the front door's timeouts raised

    @pytest.mark.parametrize("value", ["", "not-a-key", base64.b64encode(bytes(16)).decode()])
    def test_a_bad_public_key_is_refused(self, public_key: str, value: str) -> None:
        with pytest.raises(config.ConfigError, match="RELAY_COLLECTOR_PUBLIC_KEY"):
            bridge_config.bridge_settings(_bridge_env(public_key, RELAY_COLLECTOR_PUBLIC_KEY=value))
