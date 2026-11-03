"""The collector's settings (`collector_config`) and its key tool (`keys`). For
the settings: the defaults, what is required, key files and rotation, the API
origin, the ranges, and the shared rules as the collector applies them. For
`keys`: modes, refusing to overwrite or follow symlinks. The shared settings
themselves are tested in common/tests/test_core.py."""

from __future__ import annotations

import re
import stat
from pathlib import Path

import pytest

from cmp_relay import collector_config, config, keys, sealing


@pytest.fixture
def key_files(tmp_path: Path) -> dict[str, Path]:
    private, public = sealing.generate_keypair()
    previous, _ = sealing.generate_keypair()
    files = {
        "private": tmp_path / "collector.key",
        "previous": tmp_path / "previous.key",
        "ingress": tmp_path / "ingress.key",
        "public": tmp_path / "collector.pub",
    }
    files["private"].write_text(private + "\n")
    files["previous"].write_text(previous + "\n")
    files["ingress"].write_text("i" * 48 + "\n")
    files["public"].write_text(public)
    return files


def _collector_env(key_files: dict[str, Path], **extra: str) -> dict[str, str]:
    return {
        "RELAY_REQUEST_QUEUE_URL": "https://sqs.ap-south-1.amazonaws.com/1/requests",
        "RELAY_BUCKET": "bodies",
        "RELAY_COLLECTOR_PRIVATE_KEY_FILE": str(key_files["private"]),
        "RELAY_INGRESS_KEY_FILE": str(key_files["ingress"]),
        "RELAY_REPLY_QUEUE_URLS": "https://q/a, https://q/b ,",
        **extra,
    }


class TestCollectorConfig:
    def test_collector_defaults(self, key_files: dict[str, Path]) -> None:
        s = collector_config.collector_settings(_collector_env(key_files))
        assert s.api_origin == "http://127.0.0.1:8000"
        assert s.ingress_key == "i" * 48
        assert s.reply_queue_urls == frozenset({"https://q/a", "https://q/b"})
        assert (s.workers, s.write_budget_s) == (8, 18)
        assert len(s.private_keys) == 1
        assert sealing.public_of(s.private_keys[0]) == key_files["public"].read_text()

    @pytest.mark.parametrize(
        "missing",
        [
            "RELAY_REQUEST_QUEUE_URL",
            "RELAY_BUCKET",
            "RELAY_COLLECTOR_PRIVATE_KEY_FILE",
            "RELAY_INGRESS_KEY_FILE",
            "RELAY_REPLY_QUEUE_URLS",
        ],
    )
    def test_collector_required_settings(self, key_files: dict[str, Path], missing: str) -> None:
        env = _collector_env(key_files)
        env.pop(missing)
        with pytest.raises(config.ConfigError, match=missing):
            collector_config.collector_settings(env)

    @pytest.mark.parametrize("environment", ["production", "staging"])
    def test_local_only_settings_are_refused_outside_local(
        self, key_files: dict[str, Path], environment: str
    ) -> None:
        for extra in (
            {"RELAY_ENDPOINT_URL": "http://127.0.0.1:5000"},
            {"RELAY_ALLOW_DEV_ROUTES": "true"},
        ):
            env = _collector_env(key_files, RELAY_ENVIRONMENT=environment, **extra)
            with pytest.raises(config.ConfigError, match=next(iter(extra))):
                collector_config.collector_settings(env)

    def test_a_short_ingress_key_is_refused(
        self, key_files: dict[str, Path], tmp_path: Path
    ) -> None:
        short = tmp_path / "short.key"
        short.write_text("x" * 31)
        with pytest.raises(config.ConfigError, match="RELAY_INGRESS_KEY_FILE"):
            collector_config.collector_settings(
                _collector_env(key_files, RELAY_INGRESS_KEY_FILE=str(short))
            )
        short.write_text("x" * 32 + "\n")
        assert collector_config.collector_settings(
            _collector_env(key_files, RELAY_INGRESS_KEY_FILE=str(short))
        ).ingress_key == ("x" * 32)

    @pytest.mark.parametrize(
        "which", ["RELAY_COLLECTOR_PRIVATE_KEY_FILE", "RELAY_INGRESS_KEY_FILE"]
    )
    def test_key_files_must_exist_and_hold_something(
        self, key_files: dict[str, Path], tmp_path: Path, which: str
    ) -> None:
        with pytest.raises(config.ConfigError, match=which):
            collector_config.collector_settings(
                _collector_env(key_files, **{which: str(tmp_path / "nope")})
            )
        with pytest.raises(config.ConfigError, match=which):
            collector_config.collector_settings(_collector_env(key_files, **{which: str(tmp_path)}))
        empty = tmp_path / "empty"
        empty.write_text("\n")
        with pytest.raises(config.ConfigError, match=which):
            collector_config.collector_settings(_collector_env(key_files, **{which: str(empty)}))

    def test_a_private_key_file_that_is_not_a_key_is_refused(
        self, key_files: dict[str, Path]
    ) -> None:
        with pytest.raises(config.ConfigError, match="RELAY_COLLECTOR_PRIVATE_KEY_FILE"):
            collector_config.collector_settings(
                _collector_env(
                    key_files, RELAY_COLLECTOR_PRIVATE_KEY_FILE=str(key_files["ingress"])
                )
            )

    def test_the_previous_key_is_held_for_rotation(self, key_files: dict[str, Path]) -> None:
        s = collector_config.collector_settings(
            _collector_env(key_files, RELAY_COLLECTOR_PREVIOUS_KEY_FILE=str(key_files["previous"]))
        )
        assert len(s.private_keys) == 2
        assert sealing.public_of(s.private_keys[0]) == key_files["public"].read_text()

    def test_reply_queue_list_must_not_be_empty(self, key_files: dict[str, Path]) -> None:
        with pytest.raises(config.ConfigError, match="RELAY_REPLY_QUEUE_URLS"):
            collector_config.collector_settings(
                _collector_env(key_files, RELAY_REPLY_QUEUE_URLS=" , ")
            )

    @pytest.mark.parametrize("origin", ["127.0.0.1:8000", "ftp://api", "api.internal"])
    def test_the_api_origin_must_be_http(self, key_files: dict[str, Path], origin: str) -> None:
        with pytest.raises(config.ConfigError, match="RELAY_API_ORIGIN"):
            collector_config.collector_settings(_collector_env(key_files, RELAY_API_ORIGIN=origin))

    def test_the_api_origin_loses_a_trailing_slash(self, key_files: dict[str, Path]) -> None:
        s = collector_config.collector_settings(
            _collector_env(key_files, RELAY_API_ORIGIN="https://api.internal:8443/")
        )
        assert s.api_origin == "https://api.internal:8443"

    @pytest.mark.parametrize(
        ("name", "value"),
        [("RELAY_WORKERS", "0"), ("RELAY_WORKERS", "65"), ("RELAY_WRITE_BUDGET_S", "0")],
    )
    def test_collector_numbers_out_of_range_are_refused(
        self, key_files: dict[str, Path], name: str, value: str
    ) -> None:
        with pytest.raises(config.ConfigError, match=name):
            collector_config.collector_settings(_collector_env(key_files, **{name: value}))


# ======================================================================== keys


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


class TestKeysTool:
    def test_generate_writes_a_matching_pair(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        out = tmp_path / "keys"
        assert keys.main(["generate", "--out", str(out)]) == 0
        printed = capsys.readouterr().out.strip()
        private = (out / "collector.key").read_text().strip()
        assert sealing.public_of(sealing.load_private(private)) == printed
        assert (out / "collector.pub").read_text().strip() == printed
        assert _mode(out / "collector.key") == 0o600
        assert _mode(out) == 0o700

    def test_generate_refuses_to_overwrite_without_force(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert keys.main(["generate", "--out", str(tmp_path)]) == 0
        first = (tmp_path / "collector.key").read_text()
        assert keys.main(["generate", "--out", str(tmp_path)]) == 1
        assert "--force" in capsys.readouterr().err
        assert (tmp_path / "collector.key").read_text() == first
        assert keys.main(["generate", "--out", str(tmp_path), "--force"]) == 0
        assert (tmp_path / "collector.key").read_text() != first
        assert _mode(tmp_path / "collector.key") == 0o600

    def test_force_resets_a_loose_mode(self, tmp_path: Path) -> None:
        loose = tmp_path / "ingress.key"
        loose.write_text("old")
        loose.chmod(0o644)
        assert keys.main(["ingress-key", "--out", str(loose), "--force"]) == 0
        assert _mode(loose) == 0o600

    def test_keys_are_never_written_through_a_symlink(self, tmp_path: Path) -> None:
        target = tmp_path / "elsewhere"
        target.write_text("untouched")
        link = tmp_path / "ingress.key"
        link.symlink_to(target)
        assert keys.main(["ingress-key", "--out", str(link), "--force"]) != 0
        assert target.read_text() == "untouched"

    def test_public_prints_the_public_half(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        keys.main(["generate", "--out", str(tmp_path)])
        generated = capsys.readouterr().out.strip()
        assert keys.main(["public", "--key-file", str(tmp_path / "collector.key")]) == 0
        assert capsys.readouterr().out.strip() == generated

    def test_public_refuses_a_missing_or_bad_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert keys.main(["public", "--key-file", str(tmp_path / "nope")]) == 1
        bad = tmp_path / "bad.key"
        bad.write_text("not a key")
        assert keys.main(["public", "--key-file", str(bad)]) == 1
        assert "base64" in capsys.readouterr().err

    def test_ingress_key_is_48_url_safe_characters(self, tmp_path: Path) -> None:
        out = tmp_path / "ingress.key"
        assert keys.main(["ingress-key", "--out", str(out)]) == 0
        secret = out.read_text().strip()
        assert re.fullmatch(r"[A-Za-z0-9_-]{48}", secret)
        assert _mode(out) == 0o600
        assert keys.main(["ingress-key", "--out", str(out)]) == 1
        assert out.read_text().strip() == secret
        other = tmp_path / "other.key"
        keys.main(["ingress-key", "--out", str(other)])
        assert other.read_text() != out.read_text()

    def test_an_ingress_key_is_accepted_by_the_collector(
        self, tmp_path: Path, key_files: dict[str, Path]
    ) -> None:
        out = tmp_path / "fresh-ingress.key"
        keys.main(["ingress-key", "--out", str(out)])
        s = collector_config.collector_settings(
            _collector_env(key_files, RELAY_INGRESS_KEY_FILE=str(out))
        )
        assert len(s.ingress_key) == 48
