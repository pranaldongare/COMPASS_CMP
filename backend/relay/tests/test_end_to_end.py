"""The relay end to end: the real bridge and the real collector, joined by SQS.

Everything runs in this process:

* moto stands in for SQS and S3 - in memory, shared by every thread;
* the API is a small ASGI app served by uvicorn on a free loopback port, so the
  collector's HTTP client makes real HTTP calls to it;
* the bridge is driven through Starlette's TestClient, which runs its lifespan
  (the reply pollers and the pinger);
* the collector runs its own worker threads, exactly as `main()` runs them.

The only stand-ins are the clocks: a 3 s deadline (25 s in production), a 0.5 s
reply grace (2 s), a 1.5 s write budget (18 s), a 1 s long poll (20 s). Every
boto client is wrapped in a `Tap` that records the bytes handed to AWS - the
message bodies and the objects - so a test can check that AWS only ever holds
ciphertext.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import dataclasses
import hashlib
import json
import logging
import os
import socket
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import boto3
import pytest
import uvicorn
from moto import mock_aws
from starlette.testclient import TestClient

from cmp_relay import bridge as bridge_module
from cmp_relay import sealing, transport
from cmp_relay.bridge import Bridge, create_app
from cmp_relay.collector import Collector
from cmp_relay.config import (
    BridgeSettings,
    CollectorSettings,
    bridge_settings,
    collector_settings,
)
from cmp_relay.envelope import INLINE_LIMIT, RelayRequest

REGION = "ap-south-1"
BUCKET = "cmp-relay-e2e-bodies"
INGRESS_KEY = "e2e-ingress-key-" + "k" * 40
TOKEN = "tok-Consent-Link-Capability-4f9a"
LOOPBACK = ("127.0.0.1", 50123)

DEADLINE_S = 3.0
UPLOAD_DEADLINE_S = 30.0
GRACE_S = 0.5
WRITE_BUDGET_S = 1.5
#: When the bridge gives up on an ordinary request.
GIVE_UP_S = DEADLINE_S + GRACE_S

SET_COOKIES = [
    "cmp_session=s-9f2; Path=/; HttpOnly; Secure; SameSite=Lax",
    "cmp_csrf=c-77a; Path=/; Secure; SameSite=Lax",
    "cmp_ticket=; Path=/; Max-Age=0",
]


# ------------------------------------------------------------------ the API


@dataclasses.dataclass(frozen=True)
class Call:
    """One request as the API received it, off the wire."""

    method: str
    path: str
    query: str
    headers: list[tuple[str, str]]
    body: bytes

    def values(self, name: str) -> list[str]:
        return [v for n, v in self.headers if n == name]

    @property
    def names(self) -> set[str]:
        return {n for n, _ in self.headers}


class FakeAPI:
    """Just enough of the API, as raw ASGI so it sees the request as sent.

    `/health` answers the collector's pings. Every other call is recorded, then
    answered by route:

    * `GET /c/{token}` - echoes the token and the raw query, with an extra
      header that must not cross back;
    * `POST /c/{token}/otp` - three `Set-Cookie` headers;
    * `POST /auth/otp/verify` - a session cookie *without* `Secure`, as the
      local stack sets it, which an HTTP client's default jar would keep;
    * `POST /me/requests/{id}/attachments` - the size and hash of the body;
    * `GET /me/requests/{id}/download` - `self.download`, as a ZIP;
    * `GET /me/consents` - stalls `stall_s` before answering at all;
    * `GET /me/disclosures` - answers at once, then trickles the body for
      `trickle_s`;
    * anything else - `{"ok": true}`.
    """

    def __init__(self) -> None:
        self.origin = ""
        self.healthy = True
        self.stall_s = 0.0
        self.trickle_s = 0.0
        self.download = b""
        self.finished_slow = threading.Event()
        self.closing = False
        self._calls: list[Call] = []
        self._health: list[Call] = []
        self._lock = threading.Lock()

    @property
    def calls(self) -> list[Call]:
        with self._lock:
            return list(self._calls)

    @property
    def health_calls(self) -> list[Call]:
        with self._lock:
            return list(self._health)

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        assert scope["type"] == "http"
        chunks: list[bytes] = []
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunks.append(message.get("body", b""))
            if not message.get("more_body"):
                break
        call = Call(
            method=scope["method"],
            path=bytes(scope["raw_path"]).decode("latin-1"),
            query=bytes(scope["query_string"]).decode("latin-1"),
            headers=[(k.decode("latin-1"), v.decode("latin-1")) for k, v in scope["headers"]],
            body=b"".join(chunks),
        )
        if call.path == "/health":
            with self._lock:
                self._health.append(call)
            status = 200 if self.healthy else 503
            await _answer(send, status, b'{"status":"ok"}' if self.healthy else b"{}")
            return
        with self._lock:
            self._calls.append(call)
        await self._route(call, send)

    async def _route(self, call: Call, send: Any) -> None:
        parts = call.path.split("/")
        if call.method == "GET" and len(parts) == 3 and parts[1] == "c":
            payload = json.dumps({"token": parts[2], "query": call.query}).encode()
            await _answer(
                send, 200, payload, ("x-request-id", "api-req-1"), ("x-internal-note", "inside")
            )
        elif call.method == "POST" and call.path == "/auth/otp/verify":
            await _answer(
                send,
                200,
                b'{"ok":true}',
                ("set-cookie", "cmp_session=visitor-a; Path=/; HttpOnly; SameSite=lax"),
            )
        elif call.method == "POST" and call.path.endswith("/otp"):
            cookies = [("set-cookie", c) for c in SET_COOKIES]
            await _answer(send, 200, b'{"sent":true}', *cookies)
        elif call.method == "POST" and call.path.endswith("/attachments"):
            digest = hashlib.sha256(call.body).hexdigest()
            payload = json.dumps({"bytes": len(call.body), "sha256": digest}).encode()
            await _answer(send, 201, payload)
        elif call.method == "GET" and call.path.endswith("/download"):
            await _answer(
                send,
                200,
                self.download,
                ("content-disposition", 'attachment; filename="export.zip"'),
                content_type="application/zip",
            )
        elif call.path == "/me/consents":
            await asyncio.sleep(self.stall_s)
            self.finished_slow.set()
            await _answer(send, 200, b'{"late":true}')
        elif call.path == "/me/disclosures":
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            end = time.monotonic() + self.trickle_s
            while time.monotonic() < end and not self.closing:
                await send({"type": "http.response.body", "body": b" ", "more_body": True})
                await asyncio.sleep(0.2)
            self.finished_slow.set()
            await send({"type": "http.response.body", "body": b'{"late":true}'})
        else:
            await _answer(send, 200, b'{"ok":true}')


async def _answer(
    send: Any,
    status: int,
    body: bytes,
    *headers: tuple[str, str],
    content_type: str = "application/json",
) -> None:
    raw = [(b"content-type", content_type.encode())]
    raw += [(n.encode(), v.encode()) for n, v in headers]
    raw.append((b"content-length", str(len(body)).encode()))
    await send({"type": "http.response.start", "status": status, "headers": raw})
    await send({"type": "http.response.body", "body": body})


@pytest.fixture
def api() -> Iterator[FakeAPI]:
    fake = FakeAPI()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(
            fake,
            loop="asyncio",
            http="h11",
            lifespan="off",
            log_config=None,
            log_level="warning",
            access_log=False,
            proxy_headers=False,
            timeout_graceful_shutdown=1,
        )
    )
    thread = threading.Thread(
        target=server.run, kwargs={"sockets": [sock]}, name="e2e-api", daemon=True
    )
    thread.start()
    wait_until(lambda: server.started, timeout=10)
    fake.origin = f"http://127.0.0.1:{port}"
    try:
        yield fake
    finally:
        fake.closing = True
        server.should_exit = True
        thread.join(10)
        sock.close()


# ---------------------------------------------------------------- the wire


@dataclasses.dataclass(frozen=True)
class Message:
    side: str  # "bridge" or "collector"
    queue: str
    rid: str
    kind: str
    attributes: frozenset[str]
    body: str  # the SQS message body exactly as sent
    at: float

    @property
    def blob(self) -> bytes:
        return base64.b64decode(self.body)


@dataclasses.dataclass(frozen=True)
class Stored:
    side: str
    key: str
    body: bytes  # the S3 object exactly as stored


class Wire:
    """Everything the relay handed to AWS."""

    def __init__(self) -> None:
        self._messages: list[Message] = []
        self._objects: list[Stored] = []
        self._lock = threading.Lock()

    def add(self, item: Message | Stored) -> None:
        with self._lock:
            if isinstance(item, Message):
                self._messages.append(item)
            else:
                self._objects.append(item)

    @property
    def messages(self) -> list[Message]:
        with self._lock:
            return list(self._messages)

    @property
    def objects(self) -> list[Stored]:
        with self._lock:
            return list(self._objects)

    def sent(self, kind: str) -> list[Message]:
        return [m for m in self.messages if m.kind == kind]


class Tap:
    """A boto client as the relay uses it, recording what it hands to AWS.
    `reply_delay_s` holds back every reply (kind `r`) that long: a slow way back."""

    def __init__(self, inner: Any, side: str, wire: Wire) -> None:
        self._inner = inner
        self._side = side
        self._wire = wire
        self.reply_delay_s = 0.0

    def send_message(self, **kwargs: Any) -> Any:
        attributes = kwargs["MessageAttributes"]
        kind = attributes["kind"]["StringValue"]
        if kind == "r" and self.reply_delay_s:
            time.sleep(self.reply_delay_s)
        self._wire.add(
            Message(
                side=self._side,
                queue=kwargs["QueueUrl"],
                rid=attributes["rid"]["StringValue"],
                kind=kind,
                attributes=frozenset(attributes),
                body=kwargs["MessageBody"],
                at=time.monotonic(),
            )
        )
        return self._inner.send_message(**kwargs)

    def put_object(self, **kwargs: Any) -> Any:
        self._wire.add(Stored(side=self._side, key=kwargs["Key"], body=bytes(kwargs["Body"])))
        return self._inner.put_object(**kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


# --------------------------------------------------------------- the world


@dataclasses.dataclass
class World:
    api: FakeAPI
    sqs: Any  # the test's own clients, to look with
    s3: Any
    request_queue: str
    reply_queue: str
    bridge_settings: BridgeSettings
    collector_settings: CollectorSettings
    wire: Wire
    bridge_sqs: Tap
    bridge_s3: Tap
    collector_sqs: Tap
    collector_s3: Tap

    def objects(self) -> list[str]:
        listed = self.s3.list_objects_v2(Bucket=BUCKET)
        return [item["Key"] for item in listed.get("Contents", [])]

    def depth(self, queue: str) -> int:
        attrs = self.sqs.get_queue_attributes(
            QueueUrl=queue,
            AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
        )["Attributes"]
        return int(attrs["ApproximateNumberOfMessages"]) + int(
            attrs["ApproximateNumberOfMessagesNotVisible"]
        )

    def open_request(self, message: Message) -> RelayRequest:
        """A request message off the wire, opened with the collector's key."""
        plaintext, _ = sealing.open_request(
            list(self.collector_settings.private_keys), message.blob, message.rid
        )
        return RelayRequest.from_bytes(plaintext)


#: Log events that mean something broke rather than something was refused.
_BROKEN = {
    "relay.handle_failed",
    "relay.reply_failed",
    "relay.reply_poll_failed",
    "relay.receive_failed",
    "relay.send_failed",
    "relay.reply_body_failed",
    "relay.ping_failed",
}


@pytest.fixture
def world(
    api: FakeAPI,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> Iterator[World]:
    for name, value in {
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_SESSION_TOKEN": "testing",
        "AWS_DEFAULT_REGION": REGION,
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(transport, "LONG_POLL_S", 1)
    monkeypatch.setattr(bridge_module, "REPLY_GRACE_S", GRACE_S)
    caplog.set_level(logging.INFO, logger="cmp_relay")

    with mock_aws():
        sqs = boto3.client("sqs", region_name=REGION)
        s3 = boto3.client("s3", region_name=REGION)
        # As deploy/cloudformation.yaml makes them.
        request_queue = sqs.create_queue(
            QueueName="cmp-relay-e2e-requests",
            Attributes={
                "VisibilityTimeout": "180",
                "MessageRetentionPeriod": "60",
                "MaximumMessageSize": "1048576",
            },
        )["QueueUrl"]
        reply_queue = sqs.create_queue(
            QueueName="cmp-relay-e2e-replies-a",
            Attributes={
                "VisibilityTimeout": "30",
                "MessageRetentionPeriod": "60",
                "MaximumMessageSize": "1048576",
            },
        )["QueueUrl"]
        s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION})

        private_b64, public_b64 = sealing.generate_keypair()
        (tmp_path / "collector.key").write_text(private_b64)
        (tmp_path / "ingress.key").write_text(INGRESS_KEY)
        common = {
            "RELAY_ENVIRONMENT": "test",
            "RELAY_REGION": REGION,
            "RELAY_REQUEST_QUEUE_URL": request_queue,
            "RELAY_BUCKET": BUCKET,
        }
        b_settings = bridge_settings(
            {
                **common,
                "RELAY_REPLY_QUEUE_URL": reply_queue,
                "RELAY_COLLECTOR_PUBLIC_KEY": public_b64,
                "RELAY_DEADLINE_S": str(DEADLINE_S),
                "RELAY_UPLOAD_DEADLINE_S": str(UPLOAD_DEADLINE_S),
                "RELAY_REPLY_POLLERS": "2",
                "RELAY_PING_INTERVAL_S": "300",
            }
        )
        c_settings = collector_settings(
            {
                **common,
                "RELAY_COLLECTOR_PRIVATE_KEY_FILE": str(tmp_path / "collector.key"),
                "RELAY_INGRESS_KEY_FILE": str(tmp_path / "ingress.key"),
                "RELAY_API_ORIGIN": api.origin,
                "RELAY_REPLY_QUEUE_URLS": reply_queue,
                "RELAY_WORKERS": "4",
                "RELAY_WRITE_BUDGET_S": str(WRITE_BUDGET_S),
            }
        )
        wire = Wire()
        # Each side's clients built the way production builds them.
        b_sqs, b_s3 = transport.build_clients(b_settings.common, pool=48)
        c_sqs, c_s3 = transport.build_clients(c_settings.common, pool=12)
        yield World(
            api=api,
            sqs=sqs,
            s3=s3,
            request_queue=request_queue,
            reply_queue=reply_queue,
            bridge_settings=b_settings,
            collector_settings=c_settings,
            wire=wire,
            bridge_sqs=Tap(b_sqs, "bridge", wire),
            bridge_s3=Tap(b_s3, "bridge", wire),
            collector_sqs=Tap(c_sqs, "collector", wire),
            collector_s3=Tap(c_s3, "collector", wire),
        )

    broken = [r for r in caplog.get_records("call") if r.getMessage() in _BROKEN]
    assert not broken, [(r.getMessage(), getattr(r, "fields", None)) for r in broken]


class Inside:
    """The collector, run as `main()` runs it, and stoppable mid-test."""

    def __init__(self, world: World, settings: CollectorSettings) -> None:
        self.collector = Collector(settings, sqs=world.collector_sqs, s3=world.collector_s3)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self.collector.run, args=(self._stop,), name="e2e-collector", daemon=True
        )
        self._thread.start()

    def signal_stop(self) -> None:
        self._stop.set()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(15)
            assert not self._thread.is_alive(), "the collector did not stop"
            self._thread = None


@dataclasses.dataclass
class Relay:
    client: TestClient
    bridge: Bridge
    inside: Inside


@contextlib.contextmanager
def running(
    world: World,
    *,
    collector_changes: dict[str, Any] | None = None,
    **bridge_changes: Any,
) -> Iterator[Relay]:
    """Both halves up: the collector first, then the bridge (whose first ping
    goes out as it starts)."""
    inside = Inside(
        world, dataclasses.replace(world.collector_settings, **(collector_changes or {}))
    )
    inside.start()
    try:
        app = create_app(
            dataclasses.replace(world.bridge_settings, **bridge_changes),
            sqs=world.bridge_sqs,
            s3=world.bridge_s3,
        )
        with TestClient(app, client=LOOPBACK) as client:
            yield Relay(client=client, bridge=app.state.bridge, inside=inside)
            inside.signal_stop()  # both sides finish their long poll together
    finally:
        inside.stop()
        inside.collector.close()


# ----------------------------------------------------------------- helpers


def wait_until(condition: Callable[[], bool], timeout: float = 5.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if condition():
            return
        time.sleep(0.02)
    raise AssertionError("condition not met in time")


def error_of(response: Any) -> dict[str, str]:
    error: dict[str, str] = response.json()["error"]
    return error


def multipart(boundary: str, *parts: tuple[str, str | None, str | None, bytes]) -> bytes:
    """A multipart/form-data body, built by hand so the test knows every byte.
    Each part is (name, filename, content type, content)."""
    out = b""
    for name, filename, content_type, content in parts:
        disposition = f'form-data; name="{name}"'
        if filename:
            disposition += f'; filename="{filename}"'
        out += f"--{boundary}\r\nContent-Disposition: {disposition}\r\n".encode()
        if content_type:
            out += f"Content-Type: {content_type}\r\n".encode()
        out += b"\r\n" + content + b"\r\n"
    return out + f"--{boundary}--\r\n".encode()


def spellings(secret: bytes) -> list[bytes]:
    """The secret, and the runs of base64 it shows up as inside any base64
    text, whatever its offset - an inline body travels base64 in the envelope."""
    out = [secret]
    for offset in range(3):
        encoded = base64.b64encode(b"\0" * offset + secret)
        out.append(encoded[4 if offset else 0 : -4])
    return out


def assert_not_on_the_wire(world: World, secrets: list[bytes]) -> None:
    for message in world.wire.messages:
        assert message.attributes == {"rid", "kind"}
        blob = message.blob
        assert blob[:4] in (sealing.REQUEST, sealing.REPLY), message.kind
        for secret in secrets:
            for spelling in spellings(secret):
                assert spelling not in message.body.encode(), (message.kind, secret)
                assert spelling not in blob, (message.kind, secret)
    for stored in world.wire.objects:
        assert stored.body[:4] in (sealing.REQUEST_BODY, sealing.REPLY_BODY), stored.key
        for secret in secrets:
            for spelling in spellings(secret):
                assert spelling not in stored.body, (stored.key, secret)


def asgi_get(client: TestClient, raw_path: bytes) -> tuple[int, dict[str, Any]]:
    """GET a raw path straight into the bridge's ASGI app, on the TestClient's
    event loop. An HTTP client would resolve a `.` segment before sending it;
    a browser or a proxy might not."""
    portal = client.portal
    assert portal is not None
    sent: list[Any] = []

    async def receive() -> Any:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Any) -> None:
        sent.append(message)

    scope: Any = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": raw_path.decode(),
        "raw_path": raw_path,
        "root_path": "",
        "query_string": b"",
        "headers": [(b"host", b"testserver"), (b"x-forwarded-for", b"203.0.113.5")],
        "client": LOOPBACK,
        "server": ("testserver", 80),
        "state": {},
    }

    async def call() -> None:
        await client.app(scope, receive, send)

    portal.call(call)
    status: int = next(m["status"] for m in sent if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return status, json.loads(body)


# ------------------------------------------------------------------- tests


def test_a_get_goes_round_trip(world: World) -> None:
    with running(world) as relay:
        response = relay.client.get(
            f"/c/{TOKEN}?lang=hi&x=%20y",
            headers={"accept": "application/json", "x-forwarded-for": "203.0.113.20"},
        )
        assert response.status_code == 200
        assert response.json() == {"token": TOKEN, "query": "lang=hi&x=%20y"}
        assert response.headers["content-type"] == "application/json"
        assert response.headers["x-request-id"] == "api-req-1"
        assert response.headers["content-length"] == str(len(response.content))
        assert "x-internal-note" not in response.headers
        assert "server" not in response.headers
        assert relay.bridge.health()["pending"] == 0
        wait_until(lambda: relay.bridge.health()["last_ping_ok_age_s"] is not None)

    [call] = world.api.calls
    assert (call.method, call.path, call.query) == ("GET", f"/c/{TOKEN}", "lang=hi&x=%20y")
    assert call.values("accept") == ["application/json"]
    # The ping went to the API's health check, without the relay's key.
    assert world.api.health_calls
    assert all("x-cmp-relay-key" not in c.names for c in world.api.health_calls)
    assert world.depth(world.request_queue) == 0
    assert world.depth(world.reply_queue) == 0


def test_a_post_reaches_the_api_with_only_what_may_cross(world: World) -> None:
    with running(world) as relay:
        response = relay.client.post(
            f"/c/{TOKEN}/otp?lang=hi",
            content=b'{"channel":"email"}',
            headers=[
                ("content-type", "application/json"),
                ("x-csrf-token", "csrf-5e1"),
                ("cookie", "cmp_session=s-1; _ga=GA1.2.3; cmp_csrf=c-1; tracker=t-9"),
                ("x-forwarded-for", "198.51.100.1, 192.0.2.10"),
                ("x-forwarded-for", "203.0.113.77"),
                ("authorization", "Bearer someone-elses"),
                ("x-cmp-relay-key", "forged"),
                ("x-cmp-ingress", "private"),
                ("x-unlisted", "1"),
                ("accept-encoding", "gzip, br"),
            ],
        )
        assert response.status_code == 200
        assert response.json() == {"sent": True}

    [call] = world.api.calls
    assert (call.method, call.path, call.query) == ("POST", f"/c/{TOKEN}/otp", "lang=hi")
    assert call.body == b'{"channel":"email"}'
    # Exactly one X-Forwarded-For: the right-most entry the bridge received.
    assert call.values("x-forwarded-for") == ["203.0.113.77"]
    assert call.values("cookie") == ["cmp_session=s-1; cmp_csrf=c-1"]
    assert call.values("x-csrf-token") == ["csrf-5e1"]
    assert call.values("content-type") == ["application/json"]
    assert call.values("x-cmp-relay-key") == [INGRESS_KEY]
    # No X-CMP-Ingress: nothing reads it; the relay key is the only signal.
    assert call.values("x-cmp-ingress") == []
    assert call.values("accept-encoding") == ["identity"]
    assert call.names <= {
        "host",
        "accept",
        "accept-encoding",
        "connection",
        "content-length",
        "content-type",
        "cookie",
        "user-agent",
        "x-csrf-token",
        "x-forwarded-for",
        "x-cmp-relay-key",
    }


def test_every_set_cookie_comes_back_to_the_browser(world: World) -> None:
    with running(world) as relay:
        response = relay.client.post(f"/c/{TOKEN}/otp", json={"channel": "sms"})
        assert response.status_code == 200
        assert response.headers.get_list("set-cookie") == SET_COOKIES


def test_one_visitors_session_never_rides_on_the_next_visitors_request(world: World) -> None:
    """The collector serves every visitor through one HTTP client, so that
    client must keep no cookie. With httpx's default jar it kept visitor A's
    session and sent it on visitor B's anonymous request: B was signed in as A
    (found in the end-to-end run on the local stack, 2026-10-23)."""
    with running(world) as relay:
        signed_in = relay.client.post("/auth/otp/verify", json={"code": "123456"})
        assert signed_in.status_code == 200
        assert signed_in.headers.get_list("set-cookie") == [
            "cmp_session=visitor-a; Path=/; HttpOnly; SameSite=lax"
        ]
        relay.client.cookies.clear()  # visitor B: a different browser
        assert relay.client.get("/auth/me").status_code == 200

    verify, me = world.api.calls
    assert verify.path == "/auth/otp/verify"
    assert me.path == "/auth/me"
    assert me.values("cookie") == [], "visitor B arrived carrying visitor A's cookie"


def test_concurrent_requests_each_get_their_own_answer(world: World) -> None:
    tokens = [f"tok-{n:02d}-{uuid.uuid4().hex[:8]}" for n in range(12)]
    with running(world) as relay, ThreadPoolExecutor(max_workers=12) as pool:
        responses = list(pool.map(lambda t: relay.client.get(f"/c/{t}"), tokens))
        assert relay.bridge.health()["pending"] == 0
    assert [r.status_code for r in responses] == [200] * len(tokens)
    assert [r.json()["token"] for r in responses] == tokens
    assert sorted(c.path for c in world.api.calls) == sorted(f"/c/{t}" for t in tokens)


def test_a_20_mb_upload_arrives_byte_identical_through_s3(world: World) -> None:
    marker = b"E2E-UPLOAD-PLAINTEXT-MARKER-6c1d5e"
    block = marker + os.urandom(64 * 1024)
    document = block * (20 * 1024 * 1024 // len(block))
    boundary = "e2e-boundary-q7MA4YWxkTrZu0gW"
    body = multipart(
        boundary,
        ("note", None, None, b"my identity document"),
        ("file", "id.pdf", "application/pdf", document),
    )
    content_type = f"multipart/form-data; boundary={boundary}"
    assert len(body) > 20 * 1000 * 1000

    with running(world) as relay:
        response = relay.client.post(
            "/me/requests/9b2e/attachments",
            content=body,
            headers={"content-type": content_type, "x-csrf-token": "c"},
        )
        assert response.status_code == 201, response.text
        assert response.json() == {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}

    [call] = world.api.calls
    assert call.body == body
    assert call.values("content-type") == [content_type]

    # The body travelled as one sealed object, under the upload deadline.
    [request_message] = world.wire.sent("q")
    request = world.open_request(request_message)
    assert request.deadline_ms - request.issued_ms == int(UPLOAD_DEADLINE_S * 1000)
    assert request.body is not None
    assert request.body.s3_key == transport.body_key("req", request.id)
    [stored] = world.wire.objects
    assert (stored.side, stored.key) == ("bridge", request.body.s3_key)
    assert request.body.size == len(stored.body)  # the sealed object's size
    assert stored.body.startswith(sealing.REQUEST_BODY)
    assert marker not in stored.body
    assert world.objects() == []  # the collector deleted it once read


def test_a_2_mb_answer_comes_back_through_s3(world: World) -> None:
    marker = b"E2E-DOWNLOAD-PLAINTEXT-MARKER-0a93"
    world.api.download = (marker + os.urandom(4096)) * (2 * 1024 * 1024 // (len(marker) + 4096))
    assert len(world.api.download) > 2 * 1000 * 1000

    with running(world) as relay:
        response = relay.client.get("/me/requests/9b2e/download")
        assert response.status_code == 200
        assert response.content == world.api.download
        assert response.headers["content-type"] == "application/zip"
        assert response.headers["content-disposition"] == 'attachment; filename="export.zip"'

    [stored] = world.wire.objects
    assert stored.side == "collector"
    assert stored.key.startswith("res/")
    assert stored.body.startswith(sealing.REPLY_BODY)
    assert marker not in stored.body
    assert world.objects() == []  # the bridge deleted it once read


def test_bodies_at_the_inline_limit_fit_in_one_message(world: World) -> None:
    # 256 KiB, base64 inside the envelope and base64 again on the queue, must
    # stay under SQS's 1 MiB - moto refuses a larger message as SQS does.
    padding = b"a" * (INLINE_LIMIT - len(b'{"pad":""}'))
    body = b'{"pad":"' + padding + b'"}'
    assert len(body) == INLINE_LIMIT
    world.api.download = b"z" * INLINE_LIMIT
    with running(world) as relay:
        posted = relay.client.post(
            f"/c/{TOKEN}/otp", content=body, headers={"content-type": "application/json"}
        )
        assert posted.status_code == 200
        fetched = relay.client.get("/me/requests/1/download")
        assert fetched.status_code == 200
        assert fetched.content == world.api.download
    assert world.api.calls[0].body == body
    assert world.wire.objects == []  # both travelled inside their message
    largest = max(len(m.body) for m in world.wire.messages)
    assert INLINE_LIMIT * 16 // 9 < largest < 1024 * 1024  # base64 twice: x16/9


def test_aws_only_ever_holds_ciphertext(world: World, caplog: pytest.LogCaptureFixture) -> None:
    session, csrf, client_ip = b"cmp-session-value-8e4c1", b"csrf-value-71bd0", "203.0.113.199"
    small = b"E2E-INLINE-BODY-MARKER-d41f"
    upload = b"E2E-S3-UPLOAD-MARKER-5b27c"
    answer = b"E2E-S3-ANSWER-MARKER-90e1f"
    world.api.download = answer * (INLINE_LIMIT // len(answer) + 1000)
    headers = {
        "cookie": f"cmp_session={session.decode()}",
        "x-csrf-token": csrf.decode(),
        "x-forwarded-for": client_ip,
    }
    with running(world) as relay:
        client = relay.client
        assert client.get(f"/c/{TOKEN}", headers=headers).status_code == 200
        posted = client.post(
            f"/c/{TOKEN}/otp", content=b'{"note":"' + small + b'"}', headers=headers
        )
        assert posted.status_code == 200
        boundary = "e2e-b-1"
        body = multipart(
            boundary, ("file", "a.bin", None, upload * (INLINE_LIMIT // len(upload) + 1000))
        )
        uploaded = client.post(
            "/me/requests/1/attachments",
            content=body,
            headers={**headers, "content-type": f"multipart/form-data; boundary={boundary}"},
        )
        assert uploaded.status_code == 201
        assert client.get("/me/requests/1/download", headers=headers).content == world.api.download

    kinds = {m.kind for m in world.wire.messages}
    assert kinds == {"q", "p", "r"}
    assert {o.key.split("/")[0] for o in world.wire.objects} == {"req", "res"}
    secrets = [TOKEN.encode(), session, csrf, client_ip.encode(), small, upload, answer]
    assert_not_on_the_wire(world, secrets)

    # Nor in the logs, on either side.
    logged = [
        r.getMessage() + json.dumps(getattr(r, "fields", {}), default=str)
        for r in caplog.get_records("call")
        if r.name.startswith("cmp_relay")
    ]
    assert any("relay.request" in line for line in logged)
    assert any("relay.handled" in line for line in logged)
    for secret in secrets:
        assert not [line for line in logged if secret.decode() in line], secret


def test_a_route_off_the_list_never_reaches_the_api(world: World) -> None:
    refused = [
        ("GET", "/admin/users"),
        ("POST", "/auth/login"),
        ("POST", "/auth/mfa/verify"),
        ("GET", "/metrics"),
        ("GET", "/docs"),
        ("GET", "/me"),
        ("PUT", "/me"),
        ("GET", f"/c/{TOKEN}/notice/extra"),
        ("GET", "/me/consents/abc%2F..%2F..%2Fadmin/record"),
        ("DELETE", f"/c/{TOKEN}"),
    ]
    with running(world) as relay:
        for method, path in refused:
            response = relay.client.request(method, path)
            assert response.status_code == 404, (method, path)
            assert error_of(response)["code"] == "not_found"
        assert world.wire.sent("q") == []  # refused at the bridge, before any queue

        # A `.` segment, sent raw: the API must never see the path it resolves to.
        # Today the bridge's allow-list lets `/c/./notice` through to the queue
        # (a gap in allowlist.RouteTable, reported) and the collector refuses
        # it; either side refusing is a pass here.
        for raw in (b"/c/./notice", b"/me/consents/./record", b"/c/../me/consents"):
            status, payload = asgi_get(relay.client, raw)
            assert status == 404, raw
            assert payload["error"]["code"] == "not_found"
    assert world.api.calls == []


def test_a_sealed_value_sent_in_is_refused_before_the_api(world: World) -> None:
    boundary = "e2e-b-2"
    with running(world) as relay:
        client = relay.client
        in_json = client.post("/auth/otp/request", json={"contact": "SE::v1:k7:Zm9vYmFy"})
        in_query = client.get(f"/c/{TOKEN}", params={"name": "SE::v1:k7:Zm9v"})
        in_field = client.post(
            "/me/requests/1/attachments",
            content=multipart(boundary, ("note", None, None, b"SE::v1:k7:YmFy")),
            headers={"content-type": f"multipart/form-data; boundary={boundary}"},
        )
        # A file's name is stored and returned, so it is searched too.
        in_filename = client.post(
            "/me/requests/1/attachments",
            content=multipart(boundary, ("file", "SE::v1:k7:YmF6", "text/plain", b"notes")),
            headers={"content-type": f"multipart/form-data; boundary={boundary}"},
        )
        # So is every header that crosses: GET /auth/sessions returns the agent.
        in_header = client.get("/auth/sessions", headers={"user-agent": "SE::v1:k7:cXV4"})
        for response in (in_json, in_query, in_field, in_filename, in_header):
            assert response.status_code == 422
            assert error_of(response)["code"] == "sealed_value_refused"
        assert world.api.calls == []

        # A file's bytes are the person's own document, and may hold anything.
        in_file = client.post(
            "/me/requests/1/attachments",
            content=multipart(boundary, ("file", "notes.txt", "text/plain", b"SE::v1:abc")),
            headers={"content-type": f"multipart/form-data; boundary={boundary}"},
        )
        assert in_file.status_code == 201
    assert [c.path for c in world.api.calls] == ["/me/requests/1/attachments"]


def test_a_write_too_close_to_its_deadline_is_never_started(world: World) -> None:
    # A write budget longer than the whole deadline: no write can ever start.
    with running(world, collector_changes={"write_budget_s": DEADLINE_S + 1}) as relay:
        write = relay.client.post(f"/c/{TOKEN}/otp", json={"channel": "email"})
        assert write.status_code == 503
        assert error_of(write)["code"] == "deadline_too_close"
        assert relay.client.get(f"/c/{TOKEN}").status_code == 200  # reads still run
    assert [c.method for c in world.api.calls] == ["GET"]


def test_with_the_collector_stopped_the_bridge_answers_503_at_once(world: World) -> None:
    with running(world, ping_interval_s=1.0) as relay:
        bridge, client = relay.bridge, relay.client
        wait_until(lambda: bridge.health()["last_ping_ok_age_s"] is not None)
        assert client.get(f"/c/{TOKEN}").status_code == 200

        relay.inside.stop()
        wait_until(lambda: not bridge.inside_ok, timeout=5)
        queued = len(world.wire.sent("q"))
        started = time.monotonic()
        response = client.get(f"/c/{TOKEN}")
        elapsed = time.monotonic() - started
        assert response.status_code == 503
        assert error_of(response)["code"] == "inside_unreachable"
        assert elapsed < 0.5  # not the deadline: at once
        assert len(world.wire.sent("q")) == queued  # nothing was sent

        # Back up: the next ping finds it, and requests flow again. The pings
        # left on the queue meanwhile have expired and are dropped unanswered.
        relay.inside.start()
        wait_until(lambda: bridge.inside_ok, timeout=5)
        assert client.get(f"/c/{TOKEN}").status_code == 200
    assert [c.path for c in world.api.calls] == [f"/c/{TOKEN}", f"/c/{TOKEN}"]


def test_with_the_api_down_the_bridge_answers_503_at_once(world: World) -> None:
    # The collector is up but the API is not: its pings answer 503, and the
    # bridge stops sending work it knows cannot be done.
    closed = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    closed.bind(("127.0.0.1", 0))
    nowhere = f"http://127.0.0.1:{closed.getsockname()[1]}"
    closed.close()
    with running(world, ping_interval_s=1.0, collector_changes={"api_origin": nowhere}) as relay:
        wait_until(lambda: not relay.bridge.inside_ok, timeout=5)
        started = time.monotonic()
        response = relay.client.post(f"/c/{TOKEN}/otp", json={"channel": "email"})
        assert response.status_code == 503
        assert error_of(response)["code"] == "inside_unreachable"
        assert time.monotonic() - started < 0.5
    assert world.wire.sent("q") == []


def test_an_api_slower_than_the_deadline_is_cut_off_by_the_collector(world: World) -> None:
    # The API stalls past the bridge's deadline. The collector's call to it is
    # bounded by the deadline, so the collector answers 503 api_timeout itself,
    # before the bridge would give up - and has nothing more to send after.
    world.api.stall_s = GIVE_UP_S + 0.5
    with running(world) as relay:
        started = time.monotonic()
        response = relay.client.get("/me/consents")
        elapsed = time.monotonic() - started
        assert response.status_code == 503
        assert error_of(response)["code"] == "api_timeout"
        assert DEADLINE_S - 1.5 < elapsed < GIVE_UP_S
        rid = error_of(response)["request_id"]

        assert world.api.finished_slow.wait(5)  # the API's own answer, at last
        time.sleep(0.5)
        assert [m.rid for m in world.wire.sent("r") if m.rid == rid] == [rid]  # one reply only
        assert relay.client.get(f"/c/{TOKEN}").status_code == 200


def test_an_api_answer_trickling_past_the_deadline_is_cut_off_too(world: World) -> None:
    # Headers at once, then a byte at a time: each read is quick, the whole is
    # not. The collector still stops at the deadline.
    world.api.trickle_s = GIVE_UP_S + 1.5
    with running(world) as relay:
        started = time.monotonic()
        response = relay.client.get("/me/disclosures")
        elapsed = time.monotonic() - started
        assert response.status_code == 503
        assert error_of(response)["code"] == "api_timeout"
        assert elapsed < GIVE_UP_S


def test_a_reply_after_the_deadline_gets_504_and_is_thrown_away(
    world: World, caplog: pytest.LogCaptureFixture
) -> None:
    # The API answers, but the reply's way back is slower than the deadline.
    with running(world) as relay:
        bridge, client = relay.bridge, relay.client
        wait_until(lambda: bridge.health()["last_ping_ok_age_s"] is not None)
        world.collector_sqs.reply_delay_s = GIVE_UP_S + 0.5
        started = time.monotonic()
        response = client.get(f"/c/{TOKEN}")
        elapsed = time.monotonic() - started
        world.collector_sqs.reply_delay_s = 0.0
        assert response.status_code == 504
        assert error_of(response)["code"] == "inside_timeout"
        assert GIVE_UP_S - 0.2 < elapsed < GIVE_UP_S + 1.0
        rid = error_of(response)["request_id"]
        assert len(world.api.calls) == 1  # the API did answer

        # The late reply arrives, is recognised as nobody's, and is deleted.
        def late_reply_seen() -> bool:
            return any(
                r.getMessage() == "late_reply" and getattr(r, "fields", {}).get("rid") == rid
                for r in caplog.get_records("call")
            )

        wait_until(late_reply_seen, timeout=5)
        wait_until(lambda: world.depth(world.reply_queue) == 0)

        # The bridge is none the worse: the next request gets its own answer.
        follow_up = client.get("/c/tok-next")
        assert follow_up.status_code == 200
        assert follow_up.json()["token"] == "tok-next"
        assert bridge.inside_ok
