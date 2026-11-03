"""The local emulator's queues and bucket (`provision`): it refuses without an
emulator, makes everything twice to the same result, and writes env files that
each side accepts. It runs moto in-process."""

from __future__ import annotations

import socket
import stat
from collections.abc import Iterator
from pathlib import Path

import pytest

from cmp_relay import bridge_config, collector_config, keys, provision


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


@pytest.fixture
def emulator() -> Iterator[str]:
    from moto.server import ThreadedMotoServer

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = ThreadedMotoServer(ip_address="127.0.0.1", port=port, verbose=False)
    server.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.stop()


class TestProvisionTool:
    def test_refuses_without_an_emulator(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert provision.main([]) == 2
        assert "local emulator only" in capsys.readouterr().err
        with pytest.raises(provision.ProvisionError):
            provision.provision("", prefix="x", replies=1, region="ap-south-1")

    def test_makes_everything_idempotently_and_prints_settings(
        self, emulator: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        keys.main(["generate", "--out", str(tmp_path)])
        public = capsys.readouterr().out.strip()
        argv = ["--endpoint-url", emulator, "--prefix", "cmp-relay-test", "--keys-dir"]
        assert provision.main([*argv, str(tmp_path)]) == 0
        first = capsys.readouterr().out
        assert provision.main([*argv, str(tmp_path)]) == 0
        assert capsys.readouterr().out == first

        lines = dict(
            line.split("=", 1) for line in first.splitlines() if line and not line.startswith("#")
        )
        assert lines["RELAY_ENVIRONMENT"] == "local"
        assert lines["RELAY_ENDPOINT_URL"] == emulator
        assert lines["RELAY_BUCKET"] == "cmp-relay-test-bodies"
        assert lines["RELAY_REQUEST_QUEUE_URL"].endswith("/cmp-relay-test-requests")
        assert lines["RELAY_COLLECTOR_PUBLIC_KEY"] == public
        assert lines["RELAY_COLLECTOR_PRIVATE_KEY_FILE"] == str(
            (tmp_path / "collector.key").resolve()
        )
        assert first.count("RELAY_REPLY_QUEUE_URL=") == 2
        replies = lines["RELAY_REPLY_QUEUE_URLS"].split(",")
        assert [r.rsplit("/", 1)[1] for r in replies] == [
            "cmp-relay-test-replies-a",
            "cmp-relay-test-replies-b",
        ]

        import boto3

        session = boto3.session.Session(
            aws_access_key_id="testing", aws_secret_access_key="testing", region_name="ap-south-1"
        )
        sqs = session.client("sqs", endpoint_url=emulator)
        got = sqs.get_queue_attributes(
            QueueUrl=lines["RELAY_REQUEST_QUEUE_URL"], AttributeNames=["All"]
        )["Attributes"]
        for name, value in provision.REQUEST_QUEUE_ATTRIBUTES.items():
            assert got[name].lower() == value
        s3 = session.client("s3", endpoint_url=emulator)
        rules = s3.get_bucket_lifecycle_configuration(Bucket="cmp-relay-test-bodies")["Rules"]
        assert sorted(r["Filter"]["Prefix"] for r in rules) == ["req/", "res/"]
        assert all(r["Expiration"]["Days"] == 1 for r in rules)

    def test_the_env_files_it_writes_are_accepted(
        self, emulator: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        key_dir, env_dir = tmp_path / "keys", tmp_path / "var"
        keys.main(["generate", "--out", str(key_dir)])
        keys.main(["ingress-key", "--out", str(key_dir / "ingress.key")])
        capsys.readouterr()
        argv = ["--endpoint-url", emulator, "--prefix", "cmp-relay-ok", "--replies", "3"]
        assert provision.main([*argv, "--keys-dir", str(key_dir), "--env-dir", str(env_dir)]) == 0
        printed = capsys.readouterr().out

        def load(path: Path) -> dict[str, str]:
            assert _mode(path) == 0o600
            lines = path.read_text().splitlines()
            return dict(line.split("=", 1) for line in lines if line and not line.startswith("#"))

        names = sorted(p.name for p in env_dir.iterdir())
        assert names == ["bridge-a.env", "bridge-b.env", "bridge-c.env", "collector.env"]
        assert printed == "\n".join((env_dir / name).read_text() for name in names)
        bridges = [load(env_dir / f"bridge-{x}.env") for x in "abc"]
        assert [b["RELAY_BRIDGE_PORT"] for b in bridges] == ["8080", "8081", "8082"]
        for bridge in bridges:
            assert bridge_config.bridge_settings(bridge).common.is_local
        settings = collector_config.collector_settings(load(env_dir / "collector.env"))
        assert settings.reply_queue_urls == {b["RELAY_REPLY_QUEUE_URL"] for b in bridges}
        assert settings.common.allow_dev_routes

    def test_without_keys_the_public_key_line_is_a_comment(
        self, emulator: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        argv = ["--endpoint-url", emulator, "--prefix", "cmp-relay-nokey", "--replies", "1"]
        assert provision.main([*argv, "--keys-dir", str(tmp_path)]) == 0
        printed = capsys.readouterr().out
        assert "\n# RELAY_COLLECTOR_PUBLIC_KEY= missing" in printed
        assert "\nRELAY_COLLECTOR_PUBLIC_KEY=" not in printed
