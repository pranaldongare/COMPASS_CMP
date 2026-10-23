"""The bridge, end to end against an in-process SQS and S3 (moto).

A small fake collector runs in a thread: it long-polls the request queue,
opens each request with the collector's private key, and answers - or does not -
as each test needs. Deadlines, ping intervals and the long-poll wait are
shortened so the suite stays quick.
"""

from __future__ import annotations

import contextlib
import dataclasses
import json
import logging
import os
import threading
import time
from collections.abc import Callable, Iterator
from typing import Any

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws
from starlette.testclient import TestClient

from cmp_relay import bridge as bridge_module
from cmp_relay import sealing, transport
from cmp_relay.bridge import Bridge, create_app
from cmp_relay.config import BridgeSettings, bridge_settings
from cmp_relay.envelope import INLINE_LIMIT, Body, RelayRequest, RelayResponse

REGION = "ap-south-1"
BUCKET = "cmp-relay-bodies-test"
LOOPBACK = ("127.0.0.1", 40000)

Answer = tuple[int, list[tuple[str, str]], bytes]
Handler = Callable[[RelayRequest, bytes | None], Answer | None]


# --------------------------------------------------------------------- world


@dataclasses.dataclass
class World:
    sqs: Any  # the test's (and the fake collector's) own clients
    s3: Any
    bridge_sqs: Any  # the bridge's clients, built the way production builds them
    bridge_s3: Any
    request_queue: str
    reply_queue: str
    private: Any
    settings: BridgeSettings

    def objects(self) -> list[str]:
        listed = self.s3.list_objects_v2(Bucket=BUCKET)
        return [item["Key"] for item in listed.get("Contents", [])]

    def queue_depth(self, url: str) -> int:
        attrs = self.sqs.get_queue_attributes(
            QueueUrl=url,
            AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
        )["Attributes"]
        return int(attrs["ApproximateNumberOfMessages"]) + int(
            attrs["ApproximateNumberOfMessagesNotVisible"]
        )


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch) -> Iterator[World]:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    # One-second long polls, a short grace: threads stop quickly, timeouts come fast.
    monkeypatch.setattr(transport, "LONG_POLL_S", 1)
    monkeypatch.setattr(bridge_module, "REPLY_GRACE_S", 0.3)
    with mock_aws():
        sqs = boto3.client("sqs", region_name=REGION)
        s3 = boto3.client("s3", region_name=REGION)
        request_queue = sqs.create_queue(QueueName="cmp-relay-requests")["QueueUrl"]
        reply_queue = sqs.create_queue(QueueName="cmp-relay-replies-bridge-a")["QueueUrl"]
        s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION})
        private_b64, public_b64 = sealing.generate_keypair()
        settings = bridge_settings(
            {
                "RELAY_ENVIRONMENT": "test",
                "RELAY_REGION": REGION,
                "RELAY_REQUEST_QUEUE_URL": request_queue,
                "RELAY_BUCKET": BUCKET,
                "RELAY_REPLY_QUEUE_URL": reply_queue,
                "RELAY_COLLECTOR_PUBLIC_KEY": public_b64,
                "RELAY_DEADLINE_S": "5",
                "RELAY_UPLOAD_DEADLINE_S": "30",
                "RELAY_REPLY_POLLERS": "1",
                "RELAY_PING_INTERVAL_S": "300",
            }
        )
        bridge_sqs, bridge_s3 = transport.build_clients(settings.common)
        yield World(
            sqs=sqs,
            s3=s3,
            bridge_sqs=bridge_sqs,
            bridge_s3=bridge_s3,
            request_queue=request_queue,
            reply_queue=reply_queue,
            private=sealing.load_private(private_b64),
            settings=settings,
        )


class RecordingSQS:
    """The bridge's SQS client, recording the kind of every message it sends.
    `fail_kinds` makes a send of those kinds fail as AWS would."""

    def __init__(self, inner: Any, fail_kinds: frozenset[str] = frozenset()) -> None:
        self.inner = inner
        self.fail_kinds = fail_kinds
        self.sent: list[str] = []

    def send_message(self, **kwargs: Any) -> Any:
        kind = kwargs["MessageAttributes"]["kind"]["StringValue"]
        self.sent.append(kind)
        if kind in self.fail_kinds:
            raise ClientError({"Error": {"Code": "InternalError", "Message": "x"}}, "SendMessage")
        return self.inner.send_message(**kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)


# ------------------------------------------------------------ fake collector


class FakeCollector:
    """Just enough of the collector: open, answer, seal. `handler` returning
    None means no reply; `handler=None` ignores HTTP requests entirely (their
    bodies are left where they are)."""

    def __init__(
        self, world: World, handler: Handler | None = None, answer_pings: bool = True
    ) -> None:
        self.world = world
        self.handler = handler
        self.answer_pings = answer_pings
        self.seen: list[RelayRequest] = []
        self.bodies: dict[str, bytes | None] = {}
        self.stored: dict[str, bytes] = {}  # S3 request objects exactly as stored
        self.pings = 0
        self.errors: list[BaseException] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def signal_stop(self) -> None:
        self._stop.set()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(5)

    def _run(self) -> None:
        w = self.world
        while not self._stop.is_set():
            for message in transport.receive(w.sqs, w.request_queue, max_messages=10):
                try:
                    transport.delete(w.sqs, w.request_queue, message.receipt)
                    self._handle(message)
                except BaseException as exc:
                    self.errors.append(exc)

    def _handle(self, message: transport.Received) -> None:
        plaintext, keys = sealing.open_request(
            [self.world.private], message.blob, message.request_id
        )
        request = RelayRequest.from_bytes(plaintext)
        assert request.id == message.request_id
        if request.kind == "ping":
            self.pings += 1
            if self.answer_pings:
                self.reply(request, keys, (200, [], b'{"status":"ok"}'))
            return
        self.seen.append(request)
        if self.handler is None:
            return
        body = self._body(request, keys)
        self.bodies[request.id] = body
        answer = self.handler(request, body)
        if answer is not None:
            self.reply(request, keys, answer)

    def _body(self, request: RelayRequest, keys: sealing.RequestKeys) -> bytes | None:
        if request.body is None:
            return None
        if request.body.inline is not None:
            return request.body.inline
        w = self.world
        key = request.body.s3_key
        assert key is not None
        self.stored[key] = w.s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
        blob = transport.take_blob(w.s3, BUCKET, key, request.body.sha256, request.body.size)
        return sealing.open_sealed(keys.request_key, sealing.REQUEST_BODY, blob, request.id)

    def reply(self, request: RelayRequest, keys: sealing.RequestKeys, answer: Answer) -> None:
        status, headers, content = answer
        rid = request.id
        if len(content) > INLINE_LIMIT:
            sealed = sealing.seal(keys.reply_key, sealing.REPLY_BODY, content, rid)
            key = transport.body_key("res", rid)
            digest = transport.put_blob(self.world.s3, BUCKET, key, sealed)
            body: Body | None = Body(s3_key=key, size=len(sealed), sha256=digest)
        else:
            body = Body(inline=content) if content else None
        response = RelayResponse(id=rid, status=status, headers=headers, body=body)
        blob = sealing.seal(keys.reply_key, sealing.REPLY, response.to_bytes(), rid)
        transport.send(self.world.sqs, request.reply_to, rid, "r", blob)


def ok_json(payload: Any = None, *extra: tuple[str, str]) -> Answer:
    body = json.dumps({"ok": True} if payload is None else payload).encode()
    return 200, [("content-type", "application/json"), *extra], body


@contextlib.contextmanager
def running(
    world: World,
    collector: FakeCollector | None,
    *,
    client: tuple[str, int] = LOOPBACK,
    fail_kinds: frozenset[str] = frozenset(),
    start_background: bool = True,
    **changes: Any,
) -> Iterator[tuple[TestClient, Bridge, RecordingSQS]]:
    settings = dataclasses.replace(world.settings, **changes)
    sqs = RecordingSQS(world.bridge_sqs, fail_kinds)
    app = create_app(settings, sqs=sqs, s3=world.bridge_s3, start_background=start_background)
    if collector is not None:
        collector.start()
    try:
        with TestClient(app, client=client) as test_client:
            yield test_client, app.state.bridge, sqs
            if collector is not None:
                collector.signal_stop()  # let both sides finish their long poll together
    finally:
        if collector is not None:
            collector.stop()
            assert not collector.errors, collector.errors


def wait_until(condition: Callable[[], bool], timeout: float = 5.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if condition():
            return
        time.sleep(0.02)
    raise AssertionError("condition not met in time")


def error_code(response: Any) -> str:
    code: str = response.json()["error"]["code"]
    return code


# --------------------------------------------------------------------- tests


def test_get_round_trip_carries_status_headers_and_body(world: World) -> None:
    collector = FakeCollector(
        world,
        lambda req, body: ok_json(
            {"path_seen": req.path},
            ("x-request-id", "api-req-1"),
            ("server", "uvicorn"),
            ("content-length", "999"),
        ),
    )
    with running(world, collector) as (client, bridge, sqs):
        started = time.monotonic()
        response = client.get(
            "/c/tok_123-ABC?lang=hi&x=%20y", headers={"accept": "application/json"}
        )
        assert time.monotonic() - started < 3

        assert response.status_code == 200
        assert response.json() == {"path_seen": "/c/tok_123-ABC"}
        assert response.headers["content-type"] == "application/json"
        assert response.headers["x-request-id"] == "api-req-1"
        assert response.headers["content-length"] == str(len(response.content))
        assert "server" not in response.headers
        assert bridge.health()["pending"] == 0

    [request] = collector.seen
    assert request.kind == "http"
    assert request.method == "GET"
    assert request.path == "/c/tok_123-ABC"
    assert request.query == "lang=hi&x=%20y"
    assert request.reply_to == world.reply_queue
    assert request.deadline_ms - request.issued_ms == 5000
    assert request.client_ip == "127.0.0.1"
    assert request.body is None
    assert ("accept", "application/json") in request.headers
    assert "q" in sqs.sent


def test_post_body_travels_inline_with_the_reply_status(world: World) -> None:
    collector = FakeCollector(world, lambda req, body: (202, [], b""))
    with running(world, collector) as (client, _bridge, _sqs):
        response = client.post("/auth/otp/request", json={"contact": "a@example.com"})
        assert response.status_code == 202
        assert response.content == b""

    [request] = collector.seen
    assert request.method == "POST"
    assert request.body is not None and request.body.inline is not None
    assert json.loads(collector.bodies[request.id] or b"") == {"contact": "a@example.com"}
    assert world.objects() == []


def test_every_set_cookie_arrives_separately(world: World) -> None:
    cookies = [
        "cmp_session=s1; Path=/; HttpOnly; Secure; SameSite=Lax",
        "cmp_csrf=c1; Path=/; Secure; SameSite=Lax",
        "cmp_ticket=; Path=/; Max-Age=0",
    ]
    collector = FakeCollector(
        world, lambda req, body: ok_json(None, *(("set-cookie", c) for c in cookies))
    )
    with running(world, collector) as (client, _bridge, _sqs):
        response = client.post("/auth/otp/verify", json={"code": "123456"})
    assert response.status_code == 200
    assert response.headers.get_list("set-cookie") == cookies


REFUSED_ROUTES = [
    ("GET", "/admin/users"),
    ("POST", "/auth/login"),
    ("GET", "/metrics"),
    ("GET", "/docs"),
    ("GET", "/dev/codes"),  # dev routes are off
    ("DELETE", "/c/abc"),  # right path, wrong method
    ("GET", "/c/abc%2Fnotice"),  # encoded separator
    ("GET", "/c/abc/%2e%2e/notice"),  # encoded dot segment
    ("GET", "/me//consents"),
    ("OPTIONS", "/me"),
    ("GET", "/"),
]


def test_route_not_on_the_list_is_refused_before_sqs(world: World) -> None:
    collector = FakeCollector(world, lambda req, body: ok_json())
    with running(world, collector) as (client, _bridge, sqs):
        for method, path in REFUSED_ROUTES:
            response = client.request(method, path)
            assert response.status_code == 404, (method, path)
            assert error_code(response) == "not_found"
            assert len(response.json()["error"]["request_id"]) == 32
    assert "q" not in sqs.sent
    assert collector.seen == []


def test_body_over_the_cap_is_refused_whether_or_not_it_declares_its_length(
    world: World,
) -> None:
    collector = FakeCollector(world, lambda req, body: ok_json())
    with running(world, collector, max_body_bytes=2048) as (client, _bridge, sqs):
        declared = client.post("/auth/otp/request", content=b"x" * 4096)
        assert declared.status_code == 413
        assert error_code(declared) == "payload_too_large"

        # Chunked, no Content-Length: the bridge counts what arrives.
        streamed = client.post("/auth/otp/request", content=iter([b"x" * 1500, b"y" * 1500]))
        assert streamed.status_code == 413
        assert "content-length" not in {k.lower() for k in streamed.request.headers}

        assert "q" not in sqs.sent
        at_cap = client.post("/auth/otp/request", content=b"z" * 2048)
        assert at_cap.status_code == 200
    assert len(collector.seen) == 1


def test_large_request_body_goes_through_s3_sealed(world: World) -> None:
    marker = b"PERSONAL-DOCUMENT-CONTENT"
    document = marker * (INLINE_LIMIT // len(marker) + 100)
    collector = FakeCollector(world, lambda req, body: (201, [], b'{"id":"att-1"}'))
    with running(world, collector) as (client, _bridge, _sqs):
        response = client.post(
            "/me/requests/req-1/attachments",
            files={"file": ("id.pdf", document, "application/pdf")},
            data={"note": "my id"},
        )
        assert response.status_code == 201
        assert response.json() == {"id": "att-1"}

    [request] = collector.seen
    assert request.body is not None
    assert request.body.s3_key == f"req/{request.id}"
    stored = collector.stored[request.body.s3_key]
    assert stored.startswith(sealing.REQUEST_BODY)
    assert marker not in stored
    assert request.body.size == len(stored)
    assert marker in (collector.bodies[request.id] or b"")
    # A multipart upload gets the upload deadline.
    assert request.deadline_ms - request.issued_ms == 30_000
    # The reader deleted the object.
    assert world.objects() == []


def test_large_reply_body_comes_back_through_s3(world: World) -> None:
    payload = os.urandom(INLINE_LIMIT + 50_000)
    collector = FakeCollector(
        world,
        lambda req, body: (
            200,
            [("content-type", "application/zip"), ("content-disposition", "attachment")],
            payload,
        ),
    )
    with running(world, collector) as (client, _bridge, _sqs):
        response = client.get("/me/requests/req-1/download")
        assert response.status_code == 200
        assert response.content == payload
        assert response.headers["content-type"] == "application/zip"
        assert response.headers["content-length"] == str(len(payload))
    assert world.objects() == []


def test_no_reply_by_the_deadline_answers_504_and_drops_the_request_body(
    world: World,
) -> None:
    collector = FakeCollector(world, handler=None)  # never answers HTTP requests
    with running(world, collector, deadline_s=0.5) as (client, bridge, _sqs):
        started = time.monotonic()
        response = client.post(
            "/me/requests/req-1/attachments",
            content=b"a" * (INLINE_LIMIT + 1),
            headers={"content-type": "application/octet-stream"},
        )
        elapsed = time.monotonic() - started
        assert response.status_code == 504
        assert error_code(response) == "inside_timeout"
        assert 0.7 <= elapsed < 3
        assert bridge.health()["pending"] == 0
    assert len(collector.seen) == 1
    assert world.objects() == []


def test_late_reply_is_deleted_and_logged(world: World, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="cmp_relay.bridge")

    def slow(req: RelayRequest, body: bytes | None) -> Answer:
        time.sleep(1.2)
        return ok_json()

    collector = FakeCollector(world, slow)
    with running(world, collector, deadline_s=0.4) as (client, _bridge, _sqs):
        response = client.get("/me/consents")
        assert response.status_code == 504
        wait_until(lambda: any(r.getMessage() == "late_reply" for r in caplog.records))
        wait_until(lambda: world.queue_depth(world.reply_queue) == 0)


def test_the_ids_given_up_on_are_bounded_and_forgotten_in_time() -> None:
    given_up = bridge_module._GivenUp(capacity=3, ttl_s=10)
    for n, rid in enumerate(("a", "b", "c", "d")):
        given_up.add(rid, now=float(n))
    assert len(given_up) == 3
    assert not given_up.has("a", now=4)  # the oldest went when the fourth came
    assert given_up.has("b", now=4)
    assert not given_up.has("b", now=11)  # 10 s after it was added
    assert given_up.has("d", now=11)
    assert not given_up.has("d", now=13)
    assert len(given_up) == 0


def _wait_for_ping(bridge: Bridge) -> None:
    wait_until(lambda: bridge.health()["last_ping_ok_age_s"] is not None)


def test_two_bridges_on_one_reply_queue_both_get_every_reply(
    world: World, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A misconfiguration - each bridge needs its own reply queue - that must
    not lose replies: a bridge puts another bridge's reply back on the queue."""
    caplog.set_level(logging.INFO, logger="cmp_relay.bridge")
    # moto wakes a waiting long poll when a message is sent, not when one is
    # released; SQS hands a released message to a waiting poll at once.
    from moto.sqs import models as sqs_models

    wait_for_messages = sqs_models.Queue.wait_for_messages
    monkeypatch.setattr(
        sqs_models.Queue,
        "wait_for_messages",
        lambda queue, timeout: wait_for_messages(queue, 0.02),  # type: ignore[arg-type]
    )
    collector = FakeCollector(world, lambda req, body: ok_json({"path": req.path}))
    second = create_app(world.settings, sqs=world.bridge_sqs, s3=world.bridge_s3)
    with (
        running(world, collector) as (client_a, bridge_a, _sqs),
        TestClient(second, client=LOOPBACK) as client_b,
    ):
        bridge_b: Bridge = second.state.bridge
        _wait_for_ping(bridge_a)
        _wait_for_ping(bridge_b)
        for n in range(16):
            client = client_a if n % 2 == 0 else client_b
            response = client.get(f"/c/tok-{n}")
            assert response.status_code == 200, (n, response.text)
            assert response.json() == {"path": f"/c/tok-{n}"}
        assert bridge_a.inside_ok and bridge_b.inside_ok
    messages = [r.getMessage() for r in caplog.records]
    assert "foreign_reply" in messages
    assert "late_reply" not in messages
    foreign = next(r for r in caplog.records if r.getMessage() == "foreign_reply")
    assert foreign.levelno == logging.WARNING


def test_a_reply_no_bridge_takes_is_deleted_after_five_receives(
    world: World, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="cmp_relay.bridge")
    monkeypatch.setattr(bridge_module, "FOREIGN_PAUSE_S", 0.01)
    with running(world, None) as (_client, _bridge, _sqs):
        # A reply for a request this bridge never sent, as a bridge that shared
        # the queue and has since gone would leave behind.
        transport.send(world.sqs, world.reply_queue, "rid-nobodys", "r", b"sealed-reply")
        wait_until(lambda: world.queue_depth(world.reply_queue) == 0, timeout=10)
    events = [
        (r.getMessage(), getattr(r, "fields", {}).get("receives"))
        for r in caplog.records
        if getattr(r, "fields", {}).get("rid") == "rid-nobodys"
    ]
    assert events == [("foreign_reply", n) for n in range(1, 5)] + [("late_reply", 5)]


def test_reply_that_does_not_open_is_dropped_and_the_real_one_used(
    world: World, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="cmp_relay.bridge")

    def forge_first(req: RelayRequest, body: bytes | None) -> Answer:
        forged = RelayResponse(id=req.id, status=200, body=Body(inline=b'{"forged":true}'))
        blob = sealing.seal(os.urandom(32), sealing.REPLY, forged.to_bytes(), req.id)
        transport.send(world.sqs, req.reply_to, req.id, "r", blob)
        wait_until(lambda: any(r.getMessage() == "relay.reply_refused" for r in caplog.records))
        return ok_json({"genuine": True})

    collector = FakeCollector(world, forge_first)
    with running(world, collector) as (client, _bridge, _sqs):
        response = client.get("/me/consents")
    assert response.status_code == 200
    assert response.json() == {"genuine": True}


def test_failed_ping_answers_503_at_once_until_a_ping_succeeds(world: World) -> None:
    collector = FakeCollector(world, lambda req, body: ok_json(), answer_pings=False)
    with running(world, collector, ping_interval_s=0.3) as (client, bridge, sqs):
        wait_until(lambda: not bridge.inside_ok)

        started = time.monotonic()
        response = client.get("/c/tok")
        assert time.monotonic() - started < 0.5
        assert response.status_code == 503
        assert error_code(response) == "inside_unreachable"
        assert "Nothing was saved" in response.json()["error"]["message"]
        assert "q" not in sqs.sent
        assert collector.seen == []

        collector.answer_pings = True
        wait_until(lambda: bridge.inside_ok)
        assert bridge.health()["last_ping_ok_age_s"] is not None
        assert client.get("/c/tok").status_code == 200


def test_health_answers_only_a_loopback_caller_without_forwarding(world: World) -> None:
    collector = FakeCollector(world, lambda req, body: ok_json())
    with running(world, collector) as (client, _bridge, sqs):
        wait_until(lambda: collector.pings >= 1)
        response = client.get("/__relay/health")
        assert response.status_code == 200
        health = response.json()
        assert health["inside_ok"] is True
        assert health["pending"] == 0
        assert set(health) == {"inside_ok", "last_ping_ok_age_s", "pending"}

        forwarded = client.get("/__relay/health", headers={"x-forwarded-for": "127.0.0.1"})
        assert forwarded.status_code == 404
        assert client.post("/__relay/health").status_code == 404

    with running(world, None, client=("::1", 40000), start_background=False) as (client, _b, _s):
        assert client.get("/__relay/health").status_code == 200

    app = create_app(
        world.settings, sqs=world.bridge_sqs, s3=world.bridge_s3, start_background=False
    )
    with TestClient(app, client=("192.0.2.10", 40000)) as remote:
        refused = remote.get("/__relay/health")
        assert refused.status_code == 404
        assert error_code(refused) == "not_found"
    assert "q" not in sqs.sent


def test_client_ip_is_taken_from_the_right_of_x_forwarded_for(world: World) -> None:
    collector = FakeCollector(world, lambda req, body: ok_json())
    with running(world, collector, client=("10.0.0.5", 40000)) as (client, _bridge, _sqs):
        client.get("/me/consents", headers={"x-forwarded-for": "203.0.113.9, 198.51.100.7"})
        client.get(
            "/me/consents",
            headers=[("x-forwarded-for", "203.0.113.9"), ("x-forwarded-for", "198.51.100.8")],
        )
        client.get("/me/consents", headers={"x-forwarded-for": "198.51.100.7, not-an-ip"})
        client.get("/me/consents", headers={"x-forwarded-for": "::ffff:198.51.100.9"})
        client.get("/me/consents")
    assert [r.client_ip for r in collector.seen] == [
        "198.51.100.7",
        "198.51.100.8",
        "10.0.0.5",  # not an address: the socket peer
        "198.51.100.9",
        "10.0.0.5",
    ]
    # No forwarding header crosses as a header; the address travels in client_ip.
    assert all("x-forwarded-for" not in dict(r.headers) for r in collector.seen)

    collector = FakeCollector(world, lambda req, body: ok_json())
    with running(world, collector, client_ip_hop=2) as (client, _bridge, _sqs):
        client.get("/me/consents", headers={"x-forwarded-for": "203.0.113.9, 198.51.100.7"})
        client.get("/me/consents", headers={"x-forwarded-for": "198.51.100.7"})
    assert [r.client_ip for r in collector.seen] == ["203.0.113.9", "127.0.0.1"]


def test_only_allowed_headers_and_cookies_cross_either_way(world: World) -> None:
    collector = FakeCollector(
        world,
        lambda req, body: ok_json(
            None,
            ("server", "uvicorn"),
            ("x-powered-by", "fastapi"),
            ("access-control-allow-origin", "*"),
            ("x-request-id", "api-req-2"),
            ("cache-control", "no-store"),
        ),
    )
    with running(world, collector) as (client, _bridge, _sqs):
        response = client.patch(
            "/me",
            json={"name": "A"},
            headers={
                "cookie": "cmp_session=s1; _ga=tracker; cmp_csrf=c1; other=x",
                "authorization": "Bearer stolen",
                "x-csrf-token": "c1",
                "x-evil": "1",
                "accept-language": "hi-IN",
                "x-cmp-dev-client": "1",
                "x-cmp-relay-key": "guess",
                "x-cmp-ingress": "internal",
            },
        )
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "api-req-2"
    assert response.headers["cache-control"] == "no-store"
    for dropped in ("server", "x-powered-by", "access-control-allow-origin"):
        assert dropped not in response.headers

    [request] = collector.seen
    headers = dict(request.headers)
    assert headers["cookie"] == "cmp_session=s1; cmp_csrf=c1"
    assert headers["x-csrf-token"] == "c1"
    assert headers["accept-language"] == "hi-IN"
    assert headers["content-type"] == "application/json"
    for dropped in (
        "authorization",
        "x-evil",
        "x-cmp-dev-client",
        "x-cmp-relay-key",
        "x-cmp-ingress",
        "host",
        "content-length",
    ):
        assert dropped not in headers


def test_dev_routes_and_dev_header_cross_only_when_enabled(world: World) -> None:
    common = dataclasses.replace(world.settings.common, allow_dev_routes=True)
    collector = FakeCollector(world, lambda req, body: ok_json({"codes": []}))
    with running(world, collector, common=common) as (client, _bridge, _sqs):
        response = client.get("/dev/codes", headers={"x-cmp-dev-client": "portal"})
        assert response.status_code == 200
    [request] = collector.seen
    assert ("x-cmp-dev-client", "portal") in request.headers


def test_a_send_that_fails_answers_502(world: World) -> None:
    collector = FakeCollector(world, lambda req, body: ok_json())
    with running(world, collector, fail_kinds=frozenset({"q"})) as (client, bridge, _sqs):
        response = client.get("/me/consents")
        assert response.status_code == 502
        assert error_code(response) == "relay_error"
        assert bridge.health()["pending"] == 0


def test_request_log_line_names_the_route_never_the_path_or_contents(
    world: World, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="cmp_relay.bridge")
    collector = FakeCollector(world, lambda req, body: ok_json({"recorded": "Asha Rao"}))
    with running(world, collector) as (client, _bridge, _sqs):
        response = client.post(
            "/c/SECRET-TOKEN-123/consent?ref=QUERYSECRET",
            json={"name": "Asha Rao"},
            headers={
                "x-forwarded-for": "203.0.113.77",
                "cookie": "cmp_session=SESSIONVALUE",
                "x-csrf-token": "CSRFVALUE",
            },
        )
        assert response.status_code == 200

    lines = [r for r in caplog.records if r.getMessage() == "relay.request"]
    assert len(lines) == 1
    fields = getattr(lines[0], "fields", {})
    assert fields["route"] == "/c/{token}/consent"
    assert fields["method"] == "POST"
    assert fields["status"] == 200
    assert fields["via"] == "inline"
    assert fields["req_bytes"] == len(b'{"name":"Asha Rao"}')
    assert fields["res_bytes"] == len(response.content)
    assert isinstance(fields["ms"], int)
    assert len(fields["rid"]) == 32

    everything = " ".join(
        r.getMessage() + json.dumps(getattr(r, "fields", {}), default=str) for r in caplog.records
    )
    for secret in (
        "SECRET-TOKEN-123",
        "QUERYSECRET",
        "Asha",
        "203.0.113.77",
        "127.0.0.1",
        "SESSIONVALUE",
        "CSRFVALUE",
    ):
        assert secret not in everything
