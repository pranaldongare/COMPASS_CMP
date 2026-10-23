"""The collector, against moto's SQS and S3 and a fake API.

The test plays the bridge: it seals requests to the collector's public key,
puts them on the request queue, lets the collector handle them, and opens the
replies off the reply queue with the keys it kept.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import boto3
import httpx
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from cmp_relay import collector as collector_module
from cmp_relay import envelope, sealing, transport
from cmp_relay.collector import Collector
from cmp_relay.config import CollectorSettings, collector_settings
from cmp_relay.envelope import (
    INLINE_LIMIT,
    Body,
    RelayRequest,
    RelayResponse,
    now_ms,
)

REGION = "ap-south-1"
BUCKET = "cmp-relay-test-bodies"
API = "http://api.inside:8000"
INGRESS_KEY = "k" * 48
CLIENT_IP = "203.0.113.9"
TOKEN = "tok-Secret-Consent-Link-123"


# ----------------------------------------------------------------- the fakes


@dataclass
class FakeAPI:
    """Records every request; answers with `respond` (a canned 200 by default)."""

    calls: list[httpx.Request] = field(default_factory=list)
    respond: Callable[[httpx.Request], httpx.Response] | None = None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        request.read()
        self.calls.append(request)
        if self.respond is not None:
            return self.respond(request)
        return httpx.Response(200, json={"ok": True})


@dataclass
class World:
    sqs: Any
    s3: Any
    request_q: str
    reply_q: str
    other_q: str
    public: Any
    settings: CollectorSettings
    api: FakeAPI
    collector: Collector

    def send(
        self,
        *,
        method: str = "GET",
        path: str = f"/c/{TOKEN}",
        query: str = "",
        headers: list[tuple[str, str]] | None = None,
        body: bytes | None = None,
        client_ip: str | None = CLIENT_IP,
        deadline_s: float = 25,
        kind: str = "http",
        rid: str | None = None,
        reply_to: str | None = None,
        envelope_id: str | None = None,
        s3_key: str | None = None,
    ) -> tuple[str, sealing.RequestKeys]:
        """Seal a request the way the bridge does and put it on the queue."""
        rid = rid or uuid.uuid4().hex
        header, keys = sealing.begin_request(self.public)
        wire_body: Body | None = None
        if body is not None and len(body) <= INLINE_LIMIT:
            wire_body = Body(inline=body)
        elif body is not None:
            key = s3_key or transport.body_key("req", rid)
            sealed = sealing.seal(keys.request_key, sealing.REQUEST_BODY, body, rid)
            digest = transport.put_blob(self.s3, BUCKET, key, sealed)
            wire_body = Body(s3_key=key, size=len(sealed), sha256=digest)
        issued = now_ms()
        request = RelayRequest(
            id=envelope_id or rid,
            reply_to=reply_to or self.reply_q,
            issued_ms=issued,
            deadline_ms=issued + int(deadline_s * 1000),
            method=method,
            path=path,
            query=query,
            headers=headers or [],
            client_ip=client_ip,
            body=wire_body,
            kind=kind,  # type: ignore[arg-type]
        )
        blob = sealing.finish_request(header, keys, request.to_bytes(), rid)
        transport.send(self.sqs, self.request_q, rid, "p" if kind == "ping" else "q", blob)
        return rid, keys

    def take(self, queue: str) -> list[tuple[transport.Received, dict[str, str]]]:
        """Everything on a queue now, without the 20-second long poll, with
        the SQS attributes the collector reads."""
        answer = self.sqs.receive_message(
            QueueUrl=queue,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=0,
            MessageAttributeNames=["All"],
            MessageSystemAttributeNames=list(transport.SYSTEM_ATTRIBUTES),
        )
        out = []
        for message in answer.get("Messages", []):
            attrs = {k: v["StringValue"] for k, v in message.get("MessageAttributes", {}).items()}
            system = message.get("Attributes", {})
            received = transport.Received(
                receipt=message["ReceiptHandle"],
                request_id=attrs.get("rid", ""),
                blob=base64.b64decode(message["Body"]),
                sent_ms=int(system["SentTimestamp"]),
                first_receive_ms=int(system["ApproximateFirstReceiveTimestamp"]),
                receive_count=int(system["ApproximateReceiveCount"]),
            )
            out.append((received, attrs))
        return out

    def pump(self, collector: Collector | None = None) -> int:
        """Let the collector (this world's, or another) handle whatever is on
        the request queue."""
        taken = self.take(self.request_q)
        for received, _ in taken:
            (collector or self.collector).handle(received)
        return len(taken)

    def replies(self, queue: str | None = None) -> list[tuple[transport.Received, dict[str, str]]]:
        return self.take(queue or self.reply_q)

    def reply(self, rid: str, keys: sealing.RequestKeys) -> RelayResponse:
        """The one reply on the reply queue, opened."""
        replies = self.replies()
        assert len(replies) == 1, f"expected one reply, found {len(replies)}"
        received, attrs = replies[0]
        assert attrs == {"rid": rid, "kind": "r"}
        plaintext = sealing.open_sealed(keys.reply_key, sealing.REPLY, received.blob, rid)
        response = RelayResponse.from_bytes(plaintext)
        assert response.id == rid
        return response

    def body_of(self, response: RelayResponse, keys: sealing.RequestKeys) -> bytes:
        if response.body is None:
            return b""
        if response.body.inline is not None:
            return response.body.inline
        assert response.body.s3_key == transport.body_key("res", response.id)
        blob = transport.take_blob(
            self.s3, BUCKET, response.body.s3_key, response.body.sha256, 64 * 1024 * 1024
        )
        return sealing.open_sealed(keys.reply_key, sealing.REPLY_BODY, blob, response.id)

    def depth(self, queue: str) -> int:
        """Messages on a queue, visible or in flight."""
        attrs = self.sqs.get_queue_attributes(
            QueueUrl=queue,
            AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
        )["Attributes"]
        return int(attrs["ApproximateNumberOfMessages"]) + int(
            attrs["ApproximateNumberOfMessagesNotVisible"]
        )

    def objects(self) -> list[str]:
        return [o["Key"] for o in self.s3.list_objects_v2(Bucket=BUCKET).get("Contents", [])]


def _settings(tmp_path: Path, world_env: dict[str, str], **extra: str) -> CollectorSettings:
    private, _ = sealing.generate_keypair()
    key_file = tmp_path / "collector.key"
    key_file.write_text(private)
    ingress_file = tmp_path / "ingress.key"
    ingress_file.write_text(INGRESS_KEY)
    env = {
        "RELAY_ENVIRONMENT": "test",
        "RELAY_REGION": REGION,
        "RELAY_COLLECTOR_PRIVATE_KEY_FILE": str(key_file),
        "RELAY_INGRESS_KEY_FILE": str(ingress_file),
        "RELAY_API_ORIGIN": API,
        "RELAY_WORKERS": "2",
        **world_env,
        **extra,
    }
    return collector_settings(env)


@pytest.fixture
def aws(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, Any]]:
    for name, value in {
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_SESSION_TOKEN": "testing",
        "AWS_DEFAULT_REGION": REGION,
    }.items():
        monkeypatch.setenv(name, value)
    with mock_aws():
        sqs = boto3.client("sqs", region_name=REGION)
        s3 = boto3.client("s3", region_name=REGION)
        queues = {
            name: sqs.create_queue(QueueName=f"cmp-relay-{name}")["QueueUrl"]
            for name in ("requests", "replies-a", "elsewhere")
        }
        s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION})
        yield {"sqs": sqs, "s3": s3, **queues}


def _world(aws: dict[str, Any], tmp_path: Path, **extra: str) -> World:
    settings = _settings(
        tmp_path,
        {
            "RELAY_REQUEST_QUEUE_URL": aws["requests"],
            "RELAY_BUCKET": BUCKET,
            "RELAY_REPLY_QUEUE_URLS": aws["replies-a"],
        },
        **extra,
    )
    api = FakeAPI()
    http = httpx.Client(transport=httpx.MockTransport(api))
    collector = Collector(settings, sqs=aws["sqs"], s3=aws["s3"], http=http)
    return World(
        sqs=aws["sqs"],
        s3=aws["s3"],
        request_q=aws["requests"],
        reply_q=aws["replies-a"],
        other_q=aws["elsewhere"],
        public=settings.private_keys[0].public_key(),
        settings=settings,
        api=api,
        collector=collector,
    )


@pytest.fixture
def world(aws: dict[str, Any], tmp_path: Path) -> World:
    return _world(aws, tmp_path)


def _error(response: RelayResponse, world: World, keys: sealing.RequestKeys) -> dict[str, str]:
    error: dict[str, str] = json.loads(world.body_of(response, keys))["error"]
    assert error["request_id"] == response.id
    return error


# ------------------------------------------------------------ a request runs


def test_get_executes_and_the_reply_opens(world: World) -> None:
    world.api.respond = lambda request: httpx.Response(
        200,
        headers=[
            ("content-type", "application/json"),
            ("set-cookie", "cmp_session=s1; HttpOnly; Path=/"),
            ("set-cookie", "cmp_csrf=c1; Path=/"),
            ("x-request-id", "api-req-1"),
            ("server", "uvicorn"),
            ("x-internal-host", "db01.inside"),
        ],
        content=b'{"notice":"hello"}',
    )
    rid, keys = world.send(path=f"/c/{TOKEN}", query="lang=en")
    assert world.pump() == 1

    [call] = world.api.calls
    assert call.method == "GET"
    assert str(call.url) == f"{API}/c/{TOKEN}?lang=en"

    response = world.reply(rid, keys)
    assert response.status == 200
    assert response.headers == [
        ("content-type", "application/json"),
        ("set-cookie", "cmp_session=s1; HttpOnly; Path=/"),
        ("set-cookie", "cmp_csrf=c1; Path=/"),
        ("x-request-id", "api-req-1"),
    ]
    assert world.body_of(response, keys) == b'{"notice":"hello"}'
    assert world.depth(world.request_q) == 0


def test_the_api_sees_only_what_may_cross_plus_the_relay_headers(world: World) -> None:
    _rid, _ = world.send(
        method="POST",
        path=f"/c/{TOKEN}/consent",
        headers=[
            ("Cookie", "cmp_session=abc; tracking=xyz; cmp_csrf=def"),
            ("X-CSRF-Token", "csrf-1"),
            ("Content-Type", "application/json"),
            ("Content-Type", "multipart/form-data; boundary=x"),
            ("User-Agent", "Mozilla/5.0"),
            ("Accept-Language", "hi-IN"),
            ("X-Forwarded-For", "10.0.0.1, 10.0.0.2"),
            ("X-CMP-Relay-Key", "forged"),
            ("X-CMP-Ingress", "staff"),
            ("Accept-Encoding", "gzip, br"),
            ("Authorization", "Bearer staff-token"),
            ("Host", "evil.example"),
            ("X-CMP-Dev-Client", "1"),
            ("X-Request-ID", "bad\r\nInjected: yes"),
        ],
        body=b'{"choices":[]}',
    )
    world.pump()

    [call] = world.api.calls
    h = call.headers
    assert h.get_list("x-forwarded-for") == [CLIENT_IP]
    assert h.get_list("x-cmp-relay-key") == [INGRESS_KEY]
    assert h.get_list("accept-encoding") == ["identity"]
    assert h.get_list("cookie") == ["cmp_session=abc; cmp_csrf=def"]
    assert h["x-csrf-token"] == "csrf-1"
    assert h.get_list("content-type") == ["application/json"]
    assert h["user-agent"] == "Mozilla/5.0"
    assert h["accept-language"] == "hi-IN"
    assert h["host"] == "api.inside:8000"
    # X-CMP-Ingress is not sent: nothing reads it, and the relay key is the only
    # signal the API trusts. The envelope's copy is dropped like any other.
    for refused in ("authorization", "x-cmp-dev-client", "x-request-id", "x-cmp-ingress"):
        assert refused not in h
    assert call.content == b'{"choices":[]}'


def test_the_api_never_sees_the_http_clients_own_defaults(world: World) -> None:
    world.send(headers=[])
    world.pump()
    [call] = world.api.calls
    assert "user-agent" not in call.headers
    assert "accept" not in call.headers


@pytest.mark.parametrize(
    ("client_ip", "forwarded"),
    [
        ("2001:db8::1", ["2001:db8::1"]),
        ("2001:0db8:0000::0001", ["2001:db8::1"]),
        ("not-an-address", []),
        ("203.0.113.9, 10.0.0.1", []),
        ("fe80::1%eth0", []),
        (None, []),
    ],
)
def test_x_forwarded_for_is_one_valid_address_or_absent(
    world: World, client_ip: str | None, forwarded: list[str]
) -> None:
    world.send(client_ip=client_ip)
    world.pump()
    [call] = world.api.calls
    assert call.headers.get_list("x-forwarded-for") == forwarded


def test_dev_header_and_routes_cross_only_when_allowed(aws: dict[str, Any], tmp_path: Path) -> None:
    world = _world(aws, tmp_path, RELAY_ALLOW_DEV_ROUTES="true")
    world.send(path="/dev/codes", headers=[("X-CMP-Dev-Client", "1")])
    world.pump()
    [call] = world.api.calls
    assert call.headers["x-cmp-dev-client"] == "1"


# --------------------------------------------------------------- refusals


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/admin/users"),
        ("POST", "/auth/login"),
        ("GET", "/metrics"),
        ("GET", "/dev/codes"),
        ("DELETE", f"/c/{TOKEN}"),
        ("GET", "/c/./notice"),
        ("GET", "/me/consents/./record"),
        ("GET", "/c/%2e%2e/admin"),
        ("GET", "/c/a/../../admin"),
        ("GET", "//evil.example/c/x"),
    ],
)
def test_a_route_off_the_list_is_404_and_never_reaches_the_api(
    world: World, method: str, path: str
) -> None:
    rid, keys = world.send(method=method, path=path)
    world.pump()
    assert world.api.calls == []
    response = world.reply(rid, keys)
    assert response.status == 404
    assert _error(response, world, keys)["code"] == "not_found"
    assert world.depth(world.request_q) == 0


@pytest.mark.parametrize(
    ("method", "path", "query", "content_type", "body"),
    [
        ("PATCH", "/me", "", "application/json", b'{"name":"SE::v1:abc"}'),
        ("GET", "/me/consents", "q=SE%3A%3Aabc", None, None),
        ("GET", "/me/consents", "q=SE::abc", None, None),
        (
            "POST",
            "/rights/requests",
            "",
            "application/x-www-form-urlencoded",
            b"name=SE%3A%3Aabc",
        ),
    ],
)
def test_a_sealed_value_is_422_and_never_reaches_the_api(
    world: World,
    method: str,
    path: str,
    query: str,
    content_type: str | None,
    body: bytes | None,
) -> None:
    headers = [("Content-Type", content_type)] if content_type else []
    rid, keys = world.send(method=method, path=path, query=query, headers=headers, body=body)
    world.pump()
    assert world.api.calls == []
    response = world.reply(rid, keys)
    assert response.status == 422
    assert _error(response, world, keys)["code"] == "sealed_value_refused"


@pytest.mark.parametrize(
    "header",
    [
        ("User-Agent", "Mozilla/5.0 SE::djEuMS5uYW1l"),
        ("Accept-Language", "SE::djEuMS5uYW1l"),
        ("Accept-Language", "hi, SE%3A%3AdjEuMS5uYW1l"),
        ("X-CSRF-Token", "SE%3a%3aabc"),
    ],
)
def test_a_sealed_value_in_a_header_is_422_and_never_reaches_the_api(
    world: World, header: tuple[str, str]
) -> None:
    # GET /auth/sessions returns the session's user agent; the API would open it.
    rid, keys = world.send(path="/auth/sessions", headers=[header])
    world.pump()
    assert world.api.calls == []
    response = world.reply(rid, keys)
    assert response.status == 422
    assert _error(response, world, keys)["code"] == "sealed_value_refused"
    assert world.depth(world.request_q) == 0


def test_the_cookie_and_the_collectors_own_headers_are_not_searched(world: World) -> None:
    # The cookie carries the visitor's session, never a value the API echoes.
    world.send(path="/auth/sessions", headers=[("Cookie", "cmp_session=SE::not-a-name")])
    world.pump()
    [call] = world.api.calls
    assert call.headers["cookie"] == "cmp_session=SE::not-a-name"


def _upload(*parts: tuple[bytes, bytes], boundary: str = "XyZ") -> bytes:
    out = b""
    for head, data in parts:
        out += f"--{boundary}\r\n".encode() + head + b"\r\n\r\n" + data + b"\r\n"
    return out + f"--{boundary}--\r\n".encode()


@pytest.mark.parametrize(
    ("content_type", "body"),
    [
        # The name of an uploaded file is stored and returned.
        (
            "multipart/form-data; boundary=XyZ",
            _upload(
                (b'Content-Disposition: form-data; name="file"; filename="SE::djEuMS5uYW1l"', b"x")
            ),
        ),
        # A text field the API reads as text, dressed so another parser would not.
        (
            "multipart/form-data; boundary=XyZ",
            _upload(
                (
                    b'Content-Disposition: form-data; name="body"\r\n'
                    b"Content-Transfer-Encoding: base64",
                    b"SE::djEuMS5uYW1l",
                )
            ),
        ),
        (
            "multipart/form-data; boundary=XyZ; charset=utf-16-le",
            _upload(
                (b'Content-Disposition: form-data; name="body"', "SE::abc".encode("utf-16-le"))
            ),
        ),
    ],
)
def test_a_sealed_value_in_an_upload_is_422_and_never_reaches_the_api(
    world: World, content_type: str, body: bytes
) -> None:
    rid, keys = world.send(
        method="POST",
        path="/me/requests/r1/attachments",
        headers=[("Content-Type", content_type)],
        body=body,
        deadline_s=50,
    )
    world.pump()
    assert world.api.calls == []
    response = world.reply(rid, keys)
    assert response.status == 422
    assert _error(response, world, keys)["code"] == "sealed_value_refused"


def test_a_json_body_too_deep_to_search_is_refused(world: World) -> None:
    # The prefix spelled with escapes, behind a nesting deeper than any
    # recursive search: found, or refused - never waved through.
    nested = b"[" * 2000 + b"]" * 2000
    body = b'{"x":' + nested + b',"SE\\u003a\\u003aabc":1,"contact":"a@b.co"}'
    rid, keys = world.send(
        method="POST",
        path="/auth/otp/request",
        headers=[("Content-Type", "application/json")],
        body=body,
    )
    world.pump()
    assert world.api.calls == []
    assert world.reply(rid, keys).status == 422


def test_an_expired_request_is_dropped_without_a_reply(world: World) -> None:
    world.send(deadline_s=-1)
    world.send(method="POST", path=f"/c/{TOKEN}/consent", deadline_s=0.3)
    assert world.pump() == 2
    assert world.api.calls == []
    assert world.replies() == []
    assert world.depth(world.request_q) == 0


def test_a_write_without_enough_time_left_is_503_and_never_starts(world: World) -> None:
    rid, keys = world.send(method="POST", path=f"/c/{TOKEN}/consent", body=b"{}", deadline_s=10)
    world.pump()
    assert world.api.calls == []
    response = world.reply(rid, keys)
    assert response.status == 503
    assert _error(response, world, keys)["code"] == "deadline_too_close"
    assert world.depth(world.request_q) == 0


def test_a_read_with_little_time_left_still_runs(world: World) -> None:
    rid, keys = world.send(deadline_s=3)
    world.pump()
    assert len(world.api.calls) == 1
    assert world.reply(rid, keys).status == 200


# ------------------------------------------------------------ AWS's clock


def _shift_clock(monkeypatch: pytest.MonkeyPatch, shift: dict[str, int]) -> None:
    """The collector's wall clock, `shift["ms"]` off AWS's (moto stamps
    messages with the real clock, as SQS stamps them with AWS's)."""
    monkeypatch.setattr(collector_module, "now_ms", lambda: envelope.now_ms() + shift["ms"])


def test_a_collector_clock_behind_aws_still_drops_an_expired_request(
    world: World, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="cmp_relay.collector")
    _shift_clock(monkeypatch, {"ms": -30_000})
    # By its own clock this has 29 s left; by AWS's it expired a second ago.
    world.send(deadline_s=-1)
    world.pump()
    assert world.api.calls == []
    assert world.replies() == []
    assert world.depth(world.request_q) == 0
    [handled] = [r for r in caplog.records if r.getMessage() == "relay.handled"]
    fields = handled.fields  # type: ignore[attr-defined]
    assert fields["outcome"] == "expired"
    assert -31_000 < fields["offset_ms"] < -29_000
    assert fields["queued_ms"] >= 0  # measured on AWS's clock
    [skew] = [r for r in caplog.records if r.getMessage() == "relay.clock_skew"]
    assert skew.levelno == logging.WARNING


def test_a_collector_clock_behind_aws_still_refuses_a_write_too_close_to_its_deadline(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    _shift_clock(monkeypatch, {"ms": -30_000})
    # 10 s left, under the 18 s write budget - 40 s by the collector's own clock.
    rid, keys = world.send(method="POST", path=f"/c/{TOKEN}/consent", body=b"{}", deadline_s=10)
    world.pump()
    assert world.api.calls == []
    response = world.reply(rid, keys)
    assert response.status == 503
    assert _error(response, world, keys)["code"] == "deadline_too_close"


def test_a_collector_clock_ahead_of_aws_still_runs_a_fresh_write(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    _shift_clock(monkeypatch, {"ms": 30_000})
    # By its own clock the deadline passed 5 s ago; by AWS's 25 s are left.
    rid, keys = world.send(method="POST", path=f"/c/{TOKEN}/consent", body=b"{}")
    world.pump()
    assert len(world.api.calls) == 1
    assert world.reply(rid, keys).status == 200
    timeout = world.api.calls[0].extensions["timeout"]
    assert 23.5 <= timeout["read"] <= 24.5


def test_the_clock_offset_is_the_median_of_recent_samples() -> None:
    clock = collector_module.ClockOffset(samples=3)
    assert clock.ms == 0
    assert clock.add(100) == 100
    assert clock.add(5_000) == 2_550
    assert clock.add(120) == 120
    assert clock.add(110) == 120  # 100 has aged out: median of 5000, 120, 110
    assert clock.add(130) == 120


def test_a_redelivered_message_gives_no_clock_sample(world: World) -> None:
    world.send()
    [(received, _)] = world.take(world.request_q)
    stale = replace(received, receive_count=2, first_receive_ms=received.first_receive_ms - 60_000)
    world.collector.handle(stale)
    assert world.collector._clock.ms == 0


def test_the_skew_warning_is_logged_at_most_once_a_minute(
    world: World, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="cmp_relay.collector")
    _shift_clock(monkeypatch, {"ms": 5_000})
    for _ in range(3):
        world.send()
    world.pump()
    assert len(world.api.calls) == 3
    assert len([r for r in caplog.records if r.getMessage() == "relay.clock_skew"]) == 1


# ------------------------------------------------- the delete, then the time


class _SlowDelete:
    """An SQS client whose DeleteMessage takes `delay_ms` on the collector's
    clock (the clock is moved on rather than slept on)."""

    def __init__(self, real: Any, shift: dict[str, int], delay_ms: int) -> None:
        self._real = real
        self._shift = shift
        self._delay_ms = delay_ms
        self.deletes = 0

    def delete_message(self, **kwargs: Any) -> Any:
        self.deletes += 1
        self._shift["ms"] += self._delay_ms
        return self._real.delete_message(**kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


def _slow_delete_collector(
    world: World, monkeypatch: pytest.MonkeyPatch, delay_ms: int
) -> tuple[Collector, _SlowDelete]:
    shift = {"ms": 0}
    _shift_clock(monkeypatch, shift)
    sqs = _SlowDelete(world.sqs, shift, delay_ms)
    http = httpx.Client(transport=httpx.MockTransport(world.api))
    return Collector(world.settings, sqs=sqs, s3=world.s3, http=http), sqs


def test_a_slow_delete_leaves_a_write_too_little_time_and_it_is_refused_unrun(
    world: World, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="cmp_relay.collector")
    collector, sqs = _slow_delete_collector(world, monkeypatch, delay_ms=10_000)
    # 25 s left when checked; 15 s once the delete is done - under the budget.
    rid, keys = world.send(method="POST", path=f"/c/{TOKEN}/consent", body=b"{}")
    world.pump(collector)
    assert world.api.calls == []
    response = world.reply(rid, keys)
    assert response.status == 503
    error = _error(response, world, keys)
    assert error["code"] == "deadline_too_close"
    assert "Nothing was saved" in error["message"]
    assert sqs.deletes == 1  # deleted once, before the write; not again
    assert world.depth(world.request_q) == 0
    [record] = [r for r in caplog.records if r.getMessage() == "relay.handled"]
    assert record.fields["outcome"] == "refused"  # type: ignore[attr-defined]


def test_a_delete_slower_than_the_deadline_drops_the_write_without_a_reply(
    world: World, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="cmp_relay.collector")
    collector, sqs = _slow_delete_collector(world, monkeypatch, delay_ms=30_000)
    world.send(method="POST", path=f"/c/{TOKEN}/consent", body=b"{}")
    world.pump(collector)
    assert world.api.calls == []
    assert world.replies() == []
    assert sqs.deletes == 1
    [record] = [r for r in caplog.records if r.getMessage() == "relay.handled"]
    assert record.fields["outcome"] == "expired"  # type: ignore[attr-defined]


def test_the_write_gets_the_time_left_after_the_delete(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    collector, _ = _slow_delete_collector(world, monkeypatch, delay_ms=5_000)
    rid, keys = world.send(method="POST", path=f"/c/{TOKEN}/consent", body=b"{}")
    world.pump(collector)
    assert world.reply(rid, keys).status == 200
    # 20 s left after the delete, less the half second for the way back.
    timeout = world.api.calls[0].extensions["timeout"]
    assert 18.5 <= timeout["read"] <= 19.5


# ------------------------------------------------------ at most once, once


def test_a_writes_message_is_deleted_before_the_api_is_called(world: World) -> None:
    depth_during_call: list[int] = []

    def respond(request: httpx.Request) -> httpx.Response:
        depth_during_call.append(world.depth(world.request_q))
        return httpx.Response(201, json={"id": "c1"})

    world.api.respond = respond
    rid, keys = world.send(method="POST", path=f"/c/{TOKEN}/consent", body=b"{}")
    world.pump()
    assert depth_during_call == [0]
    assert world.reply(rid, keys).status == 201


def test_a_reads_message_is_deleted_only_after_the_reply(world: World) -> None:
    during: list[tuple[int, int]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        during.append((world.depth(world.request_q), len(world.replies())))
        return httpx.Response(200, json={})

    world.api.respond = respond
    world.send()
    world.pump()
    assert during == [(1, 0)]
    assert world.depth(world.request_q) == 0


def test_a_duplicate_request_id_runs_once(world: World) -> None:
    rid, keys = world.send(method="POST", path=f"/c/{TOKEN}/consent", body=b"{}")
    world.send(method="POST", path=f"/c/{TOKEN}/consent", body=b"{}", rid=rid)
    assert world.pump() == 2
    assert len(world.api.calls) == 1
    assert world.reply(rid, keys).status == 200
    assert world.depth(world.request_q) == 0


def test_the_recent_ids_memory_is_bounded() -> None:
    recent = collector_module.RecentIds(capacity=3)
    assert all(recent.first_sight(i) for i in ("a", "b", "c"))
    assert not recent.first_sight("a")
    assert recent.first_sight("d")  # evicts b, the least recently seen
    assert recent.first_sight("b")
    assert not recent.first_sight("a")


# ------------------------------------------------ messages that are not ours


def test_a_reply_to_off_the_list_gets_no_reply(world: World) -> None:
    world.send(reply_to=world.other_q)
    world.pump()
    assert world.api.calls == []
    assert world.replies() == []
    assert world.replies(world.other_q) == []
    assert world.depth(world.request_q) == 0


def test_a_message_that_does_not_open_is_deleted(world: World) -> None:
    _other_private, other_public = sealing.generate_keypair()
    blob, _ = sealing.seal_request(sealing.load_public(other_public), b"{}", "rid-foreign-1")
    transport.send(world.sqs, world.request_q, "rid-foreign-1", "q", blob)
    world.pump()
    assert world.api.calls == []
    assert world.depth(world.request_q) == 0


def test_a_request_moved_onto_another_id_does_not_open(world: World) -> None:
    header, keys = sealing.begin_request(world.public)
    request = RelayRequest(
        id="rid-one",
        reply_to=world.reply_q,
        issued_ms=now_ms(),
        deadline_ms=now_ms() + 25_000,
        method="GET",
        path=f"/c/{TOKEN}",
    )
    blob = sealing.finish_request(header, keys, request.to_bytes(), "rid-one")
    transport.send(world.sqs, world.request_q, "rid-two", "q", blob)
    world.pump()
    assert world.api.calls == []
    assert world.replies() == []


def test_an_envelope_naming_another_id_is_dropped(world: World) -> None:
    world.send(rid="rid-outer", envelope_id="rid-inner")
    world.pump()
    assert world.api.calls == []
    assert world.replies() == []
    assert world.depth(world.request_q) == 0


def test_a_request_id_that_could_name_another_object_is_dropped(
    world: World, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="cmp_relay.collector")
    world.send(rid="x/../res/abc")
    world.pump()
    assert world.api.calls == []
    assert world.replies() == []
    [record] = [r for r in caplog.records if r.getMessage() == "relay.handled"]
    assert record.fields["rid"] == "-"  # type: ignore[attr-defined]
    assert record.fields["reason"] == "bad_request_id"  # type: ignore[attr-defined]


def test_a_malformed_envelope_is_dropped(world: World) -> None:
    blob, _ = sealing.seal_request(world.public, b'{"v":1,"kind":"http"}', "rid-bad")
    transport.send(world.sqs, world.request_q, "rid-bad", "q", blob)
    world.pump()
    assert world.api.calls == []
    assert world.depth(world.request_q) == 0


# ------------------------------------------------------------------- pings


@pytest.mark.parametrize(
    ("health", "status"),
    [(200, 200), (500, 503), ("refused", 503), ("timeout", 503)],
)
def test_a_ping_reports_whether_the_api_is_alive(
    world: World, health: int | str, status: int
) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        if health == "refused":
            raise httpx.ConnectError("refused", request=request)
        if health == "timeout":
            raise httpx.ReadTimeout("slow", request=request)
        assert isinstance(health, int)
        return httpx.Response(health, json={"status": "x"})

    world.api.respond = respond
    # The envelope's path is ignored: a ping only ever asks /health.
    rid, keys = world.send(kind="ping", path="/admin/users", deadline_s=8)
    world.pump()
    [call] = world.api.calls
    assert str(call.url) == f"{API}/health"
    assert "x-cmp-relay-key" not in call.headers
    response = world.reply(rid, keys)
    assert response.status == status
    if status == 503:
        assert _error(response, world, keys)["code"] == "api_unavailable"
    assert world.depth(world.request_q) == 0


# ---------------------------------------------------------- bodies in S3


def test_a_large_request_body_comes_through_s3_and_is_deleted(world: World) -> None:
    payload = json.dumps({"details": "x" * (INLINE_LIMIT + 50_000)}).encode()
    rid, keys = world.send(
        method="POST",
        path="/me/requests",
        headers=[("Content-Type", "application/json")],
        body=payload,
    )
    assert world.objects() == [f"req/{rid}"]
    world.pump()
    [call] = world.api.calls
    assert call.content == payload
    assert world.objects() == []
    assert world.reply(rid, keys).status == 200


def test_a_large_multipart_upload_is_checked_only_in_its_text_fields(world: World) -> None:
    document = b"%PDF-1.7 " + b"SE::not-a-field " * 20_000
    boundary = "b0undary"
    body = (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="note"\r\n\r\nmy letter\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="a.pdf"\r\n'
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode()
        + document
        + f"\r\n--{boundary}--\r\n".encode()
    )
    rid, keys = world.send(
        method="POST",
        path="/me/requests/r1/attachments",
        headers=[("Content-Type", f"multipart/form-data; boundary={boundary}")],
        body=body,
        deadline_s=150,
    )
    world.pump()
    [call] = world.api.calls
    assert call.content == body
    assert world.reply(rid, keys).status == 200


def test_a_request_body_stored_under_another_key_is_refused(world: World) -> None:
    world.s3.put_object(Bucket=BUCKET, Key="res/someone-elses-reply", Body=b"sealed")
    rid, keys = world.send(
        method="POST",
        path="/me/requests",
        body=b"y" * (INLINE_LIMIT + 1),
        s3_key="res/someone-elses-reply",
    )
    world.pump()
    assert world.api.calls == []
    response = world.reply(rid, keys)
    assert response.status == 400
    assert _error(response, world, keys)["code"] == "body_unreadable"
    assert "res/someone-elses-reply" in world.objects()


def test_a_tampered_request_body_is_refused(world: World) -> None:
    rid, keys = world.send(method="POST", path="/me/requests", body=b"z" * (INLINE_LIMIT + 1))
    key = transport.body_key("req", rid)
    world.s3.put_object(Bucket=BUCKET, Key=key, Body=b"CR1B" + b"\0" * 64)
    world.pump()
    assert world.api.calls == []
    response = world.reply(rid, keys)
    assert response.status == 400
    assert _error(response, world, keys)["code"] == "body_unreadable"


def test_a_large_reply_goes_through_s3_sealed(world: World) -> None:
    content = b"%PDF-1.7 personal record " + b"Asha Verma " * 40_000
    world.api.respond = lambda request: httpx.Response(
        200,
        headers={"content-type": "application/pdf", "content-disposition": "attachment"},
        content=content,
    )
    rid, keys = world.send(path="/me/consents/c1/record")
    world.pump()

    received, _ = world.replies()[0]
    response = RelayResponse.from_bytes(
        sealing.open_sealed(keys.reply_key, sealing.REPLY, received.blob, rid)
    )
    assert response.body is not None and response.body.inline is None
    key = transport.body_key("res", rid)
    assert response.body.s3_key == key
    raw = world.s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
    assert b"Asha Verma" not in raw
    assert raw.startswith(sealing.REPLY_BODY)
    assert response.body.size == len(raw)
    assert response.body.sha256 == hashlib.sha256(raw).hexdigest()
    assert world.body_of(response, keys) == content
    assert world.objects() == []


def test_a_reply_at_the_inline_limit_stays_inline(world: World) -> None:
    content = b"a" * INLINE_LIMIT
    world.api.respond = lambda request: httpx.Response(200, content=content)
    rid, keys = world.send()
    world.pump()
    response = world.reply(rid, keys)
    assert response.body is not None and response.body.inline == content
    assert world.objects() == []


# --------------------------------------------------------- the API failing


@pytest.mark.parametrize(
    ("failure", "status", "code"),
    [
        (httpx.ReadTimeout, 503, "api_timeout"),
        (httpx.ConnectError, 503, "api_unavailable"),
        (httpx.ConnectTimeout, 503, "api_unavailable"),
        (httpx.RemoteProtocolError, 502, "api_error"),
    ],
)
def test_the_api_failing_is_an_error_reply(
    world: World, failure: type[httpx.TransportError], status: int, code: str
) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        raise failure("no", request=request)

    world.api.respond = respond
    rid, keys = world.send(method="POST", path=f"/c/{TOKEN}/consent", body=b"{}")
    world.pump()
    response = world.reply(rid, keys)
    assert response.status == status
    error = _error(response, world, keys)
    assert error["code"] == code
    if code == "api_timeout":
        assert "may have been saved" in error["message"]


def test_the_api_call_has_the_deadlines_timeout(world: World) -> None:
    world.send(deadline_s=10)
    world.pump()
    [call] = world.api.calls
    timeout = call.extensions["timeout"]
    assert 8.5 <= timeout["read"] <= 9.5
    assert timeout["connect"] == 3.0


def test_a_redirect_is_returned_not_followed(world: World) -> None:
    world.api.respond = lambda request: httpx.Response(
        302, headers={"location": "http://api.inside:8000/elsewhere"}
    )
    rid, keys = world.send()
    world.pump()
    assert len(world.api.calls) == 1
    response = world.reply(rid, keys)
    assert response.status == 302
    assert response.headers == []


# ------------------------------------------------------------------ logging


def test_one_log_line_per_message_and_no_secrets_in_it(
    world: World, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="cmp_relay.collector")
    rid, _ = world.send(
        query="email=asha%40example.com",
        headers=[("Cookie", "cmp_session=very-secret-session")],
    )
    world.pump()
    handled = [r for r in caplog.records if r.getMessage() == "relay.handled"]
    assert len(handled) == 1
    fields = handled[0].fields  # type: ignore[attr-defined]
    assert fields["rid"] == rid
    assert fields["route"] == "/c/{token}"
    assert fields["method"] == "GET"
    assert fields["status"] == 200
    assert fields["outcome"] == "executed"
    assert isinstance(fields["ms"], int)
    text = json.dumps(fields)
    for secret in (TOKEN, "asha", "very-secret-session", CLIENT_IP, INGRESS_KEY):
        assert secret not in text


@pytest.mark.parametrize(
    ("send", "outcome"),
    [
        ({"deadline_s": -1}, "expired"),
        ({"reply_to": "other"}, "dropped"),
        ({"path": "/admin"}, "refused"),
    ],
)
def test_outcomes_are_logged(
    world: World, caplog: pytest.LogCaptureFixture, send: dict[str, Any], outcome: str
) -> None:
    caplog.set_level(logging.INFO, logger="cmp_relay.collector")
    if send.get("reply_to") == "other":
        send = {**send, "reply_to": world.other_q}
    world.send(**send)
    world.pump()
    [record] = [r for r in caplog.records if r.getMessage() == "relay.handled"]
    assert record.fields["outcome"] == outcome  # type: ignore[attr-defined]


# ------------------------------------------------------------- the workers


class _FlakySQS:
    """An SQS client whose first receive fails, as a proxy hiccup would."""

    def __init__(self, real: Any) -> None:
        self._real = real
        self.failures = 0

    def receive_message(self, **kwargs: Any) -> Any:
        if self.failures == 0:
            self.failures += 1
            raise ClientError({"Error": {"Code": "ServiceUnavailable"}}, "ReceiveMessage")
        return self._real.receive_message(**kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


class _StopOnReceive:
    """An SQS client that is told to stop while its long poll is out: the
    message arrives after the stop."""

    def __init__(self, real: Any, stop: threading.Event) -> None:
        self._real = real
        self._stop = stop

    def receive_message(self, **kwargs: Any) -> Any:
        answer = self._real.receive_message(**kwargs)
        if answer.get("Messages"):
            self._stop.set()
        return answer

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


def test_a_message_received_after_stop_is_released_not_handled(
    world: World, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="cmp_relay.collector")
    monkeypatch.setattr(transport, "LONG_POLL_S", 1)
    stop = threading.Event()
    collector = Collector(
        replace(world.settings, workers=1),
        sqs=_StopOnReceive(world.sqs, stop),
        s3=world.s3,
        http=httpx.Client(transport=httpx.MockTransport(world.api)),
    )
    rid, _keys = world.send(method="POST", path=f"/c/{TOKEN}/consent", body=b"{}")
    runner = threading.Thread(target=collector.run, args=(stop,))
    runner.start()
    runner.join(timeout=10)
    assert not runner.is_alive()
    assert world.api.calls == []
    assert world.replies() == []
    # Back on the queue, visible at once, for the next collector to run.
    [(again, _)] = world.take(world.request_q)
    assert again.request_id == rid
    assert again.receive_count == 2
    assert [r for r in caplog.records if r.getMessage() == "relay.handled"] == []
    assert [r.getMessage() for r in caplog.records].count("relay.released") == 1


def test_workers_survive_errors_and_stop_when_told(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(transport, "LONG_POLL_S", 1)
    monkeypatch.setattr(collector_module, "ERROR_PAUSE_S", 0.05)
    flaky = _FlakySQS(world.sqs)
    collector = Collector(
        replace(world.settings, workers=1),
        sqs=flaky,
        s3=world.s3,
        http=httpx.Client(transport=httpx.MockTransport(world.api)),
    )

    def explode(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/boom"):
            raise RuntimeError("a bug")
        return httpx.Response(200, json={})

    world.api.respond = explode
    # A bug in handling one message, then a good one: the worker carries on.
    world.send(path="/c/boom")
    rid, _keys = world.send()

    stop = threading.Event()
    runner = threading.Thread(target=collector.run, args=(stop,))
    runner.start()
    try:
        deadline = time.monotonic() + 10
        replies: list[Any] = []
        while time.monotonic() < deadline and not replies:
            replies = [r for r in world.replies() if r[1]["rid"] == rid]
            time.sleep(0.05)
    finally:
        stop.set()
        runner.join(timeout=10)
    assert not runner.is_alive()
    assert flaky.failures == 1
    assert len(replies) == 1
    assert len(world.api.calls) == 2


# --------------------------------------------------------------- transport


def test_receive_carries_what_sqs_says_about_the_message(world: World) -> None:
    before = now_ms()
    rid, _ = world.send()
    [received] = transport.receive(world.sqs, world.request_q, wait_s=0)
    assert received.request_id == rid
    assert received.receive_count == 1
    assert received.sent_ms is not None and before - 1000 <= received.sent_ms <= now_ms()
    assert received.first_receive_ms is not None and received.first_receive_ms >= received.sent_ms

    transport.release(world.sqs, world.request_q, received.receipt)
    [again] = transport.receive(world.sqs, world.request_q, wait_s=0)
    assert again.request_id == rid
    assert again.receive_count == 2
    assert again.first_receive_ms == received.first_receive_ms


def test_take_blob_refuses_a_stored_body_over_its_limit_and_deletes_it(world: World) -> None:
    blob = b"s" * 1000
    digest = transport.put_blob(world.s3, BUCKET, "req/big", blob)
    with pytest.raises(ValueError, match="larger"):
        transport.take_blob(world.s3, BUCKET, "req/big", digest, 999)
    assert world.objects() == []
    transport.put_blob(world.s3, BUCKET, "req/exact", blob)
    assert transport.take_blob(world.s3, BUCKET, "req/exact", digest, 1000, 1000) == blob
    transport.put_blob(world.s3, BUCKET, "req/other-size", blob)
    with pytest.raises(ValueError, match="size"):
        transport.take_blob(world.s3, BUCKET, "req/other-size", digest, 2000, expected_size=999)
    assert world.objects() == []


class _Stream:
    """An object body far larger than its listing said: replaced after a check."""

    def __init__(self, size: int) -> None:
        self.left = size
        self.read_bytes = 0
        self.closed = False

    def read(self, amount: int) -> bytes:
        chunk = min(amount, self.left)
        self.left -= chunk
        self.read_bytes += chunk
        return b"x" * chunk

    def close(self) -> None:
        self.closed = True


class _SwappedS3:
    def __init__(self, stream: _Stream) -> None:
        self.stream = stream
        self.deleted: list[str] = []

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        return {"ContentLength": 10, "Body": self.stream}

    def delete_object(self, **kwargs: Any) -> None:
        self.deleted.append(kwargs["Key"])


def test_take_blob_reads_no_more_than_its_limit_whatever_the_object_says() -> None:
    stream = _Stream(size=512 * 1024 * 1024)
    s3 = _SwappedS3(stream)
    with pytest.raises(ValueError, match="larger"):
        transport.take_blob(s3, BUCKET, "req/swapped", "0" * 64, 1024 * 1024)
    assert stream.read_bytes == 1024 * 1024 + 1
    assert stream.closed
    assert s3.deleted == ["req/swapped"]
