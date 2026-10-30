"""The bridge: the AWS side of the relay.

It listens on 127.0.0.1:8080 beside the public portal; the portal's `/api`
rewrite (`API_ORIGIN`) points here, so every call arrives with the `/api`
prefix already removed - `GET /c/{token}`, `POST /auth/otp/request`.

For each request it:

1. answers its own health probe, and only to a loopback caller that came
   straight in (no `X-Forwarded-For`): `GET /__relay/health`;
2. refuses anything not on the public allow-list (404), before it costs a queue
   round trip - the collector checks the same list again, and its check is the
   one that matters;
3. answers at once with 503 while the inside is known to be unreachable, so a
   visitor is not left waiting 25 seconds for a reply that cannot come;
4. reads the body with a hard cap, counting the bytes as they arrive rather
   than trusting `Content-Length` (413);
5. seals the request to the collector's public key, puts a large body in S3
   as a sealed object, sends the envelope to the request queue, and waits for
   the sealed reply on this instance's own reply queue until the deadline plus
   a short grace (504 after that);
6. opens the reply - fetching a large body from S3 - and answers the browser
   with its status, the reply headers that may cross (every `Set-Cookie`
   kept), and the body.

Replies are collected by a few threads long-polling the reply queue. Each
reply names its request id in a clear message attribute; the poller finds the
waiting request, opens the reply with that request's reply key and hands it to
the waiting coroutine. A reply for a request this bridge stopped waiting for
(it remembers about 10,000 of those for 5 minutes) is deleted as late. Any
other reply is not this bridge's: it is released back to the queue, visible at
once, and logged as `foreign_reply` - a sign that another bridge shares this
reply queue, which must never happen: each bridge needs its own, because on a
shared queue every reply is slowed and one can still be lost. A reply received
5 times without finding its bridge is deleted.

A pinger sends a `ping` envelope every `RELAY_PING_INTERVAL_S`; the collector
answers it by calling the API's `/health`. A failed ping marks the inside down
until a ping or any reply succeeds again. The bridge starts optimistic.

What is logged: one `relay.request` line per request with the request id, the
route *template*, the method, the status, the time taken, the sizes, and
whether a body went through S3. Never a path (it can carry a consent-link or
ticket token), a header value, a cookie, a body or a client address.
"""

from __future__ import annotations

import asyncio
import contextlib
import functools
import ipaddress
import logging
import threading
import time
import uuid
from collections import OrderedDict
from collections.abc import AsyncIterator, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

import uvicorn
from botocore.exceptions import BotoCoreError, ClientError
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import ClientDisconnect, Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

from cmp_relay import logs, sealing, transport
from cmp_relay.allowlist import RouteTable, request_headers, response_headers
from cmp_relay.config import BridgeSettings, ConfigError, bridge_settings
from cmp_relay.envelope import (
    INLINE_LIMIT,
    Body,
    EnvelopeError,
    RelayRequest,
    RelayResponse,
    error_json,
    now_ms,
)

log = logging.getLogger("cmp_relay.bridge")

#: The bridge's own probe. Answered only to a loopback caller with no
#: `X-Forwarded-For`; from anywhere else it is an ordinary path, which the
#: allow-list refuses.
HEALTH_PATH = "/__relay/health"

#: How long past a request's deadline the bridge still waits for its reply. The
#: collector never starts work past the deadline; this covers the reply's trip
#: back through the queue.
REPLY_GRACE_S = 2.0

#: The longest a ping waits for its answer (or the ping interval, if shorter).
PING_WAIT_S = 8.0

#: The largest sealed reply body the bridge will fetch from S3.
MAX_REPLY_BODY_BYTES = 100 * 1024 * 1024

#: Development only: the portal's dev-client header, allowed with the dev routes.
DEV_CLIENT_HEADER = "x-cmp-dev-client"

#: Threads for the blocking SQS and S3 calls made on a request's behalf.
AWS_WORKERS = 32

#: Request ids remembered after the bridge stops waiting for them, and for how
#: long: a reply for one of them is late, and deleted.
GIVEN_UP_IDS = 10_000
GIVEN_UP_TTL_S = 300.0
#: A reply received this many times without finding its bridge is deleted.
MAX_REPLY_RECEIVES = 5
#: After releasing another bridge's reply, a poller waits this long before it
#: polls again, so that bridge's pollers get the next chance at it.
FOREIGN_PAUSE_S = 0.2

UNREACHABLE_MESSAGE = (
    "We can't reach our records right now. Nothing was saved; please try again shortly."
)
TIMEOUT_MESSAGE = (
    "This took too long to answer. If you were saving something, "
    "please check whether it went through before trying again."
)
RELAY_ERROR_MESSAGE = "We couldn't pass your request on. Please try again shortly."
BAD_REPLY_MESSAGE = "We couldn't read the answer to your request. Please try again shortly."

_JSON = "application/json"


class _NoReply(Exception):
    """No reply came before the request's deadline (plus grace)."""


@dataclass
class _Pending:
    """A request waiting for its reply."""

    keys: sealing.RequestKeys
    future: asyncio.Future[RelayResponse]
    kind: str


class _GivenUp:
    """Request ids this bridge has stopped waiting for: at most `capacity`, each
    for `ttl_s`. Not thread-safe; the bridge holds its lock."""

    def __init__(self, capacity: int = GIVEN_UP_IDS, ttl_s: float = GIVEN_UP_TTL_S) -> None:
        self._capacity = capacity
        self._ttl_s = ttl_s
        self._ids: OrderedDict[str, float] = OrderedDict()

    def add(self, rid: str, now: float) -> None:
        self._ids[rid] = now + self._ttl_s
        self._ids.move_to_end(rid)
        while len(self._ids) > self._capacity:
            self._ids.popitem(last=False)

    def has(self, rid: str, now: float) -> bool:
        # Oldest first, and all live as long: expired ids are at the front.
        while self._ids and next(iter(self._ids.values())) <= now:
            self._ids.popitem(last=False)
        return rid in self._ids

    def __len__(self) -> int:
        return len(self._ids)


def _resolve(future: asyncio.Future[RelayResponse], response: RelayResponse) -> None:
    if not future.done():
        future.set_result(response)


def _ip(value: str | None) -> str | None:
    """`value` as a canonical IP address, or None when it is not one."""
    if not value:
        return None
    try:
        address = ipaddress.ip_address(value.strip())
    except ValueError:
        return None
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return str(address.ipv4_mapped)
    return str(address)


def _safe_header(name: str, value: str) -> tuple[bytes, bytes] | None:
    """A reply header as raw bytes, or None when it could split the response."""
    if any(c in name or c in value for c in ("\r", "\n", "\0")):
        return None
    try:
        return name.encode("latin-1"), value.encode("latin-1")
    except UnicodeEncodeError:
        return None


class Bridge:
    """The bridge's state: the clients, the waiting requests, the inside's health."""

    def __init__(self, settings: BridgeSettings, sqs: Any, s3: Any) -> None:
        self.settings = settings
        self.sqs = sqs
        self.s3 = s3
        self.routes = RouteTable(allow_dev_routes=settings.common.allow_dev_routes)
        self._extra_headers = (
            frozenset({DEV_CLIENT_HEADER}) if settings.common.allow_dev_routes else frozenset()
        )
        self._pending: dict[str, _Pending] = {}
        self._given_up = _GivenUp()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._pinger: asyncio.Task[None] | None = None
        self._executor = ThreadPoolExecutor(max_workers=AWS_WORKERS, thread_name_prefix="relay-aws")
        self._inside_ok = True
        self._last_ping_ok: float | None = None

    async def _aws[**P, T](self, fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        """Run a blocking SQS or S3 call off the event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, functools.partial(fn, *args, **kwargs))

    # ------------------------------------------------------------ lifecycle

    async def start(self) -> None:
        """Start the reply pollers and the pinger."""
        self._stop.clear()
        for n in range(self.settings.reply_pollers):
            thread = threading.Thread(
                target=self._poll_replies, name=f"relay-reply-poller-{n}", daemon=True
            )
            thread.start()
            self._threads.append(thread)
        self._pinger = asyncio.create_task(self._ping_loop(), name="relay-pinger")
        logs.event(
            log,
            "relay.bridge_started",
            pollers=self.settings.reply_pollers,
            ping_interval_s=self.settings.ping_interval_s,
        )

    async def stop(self) -> None:
        """Stop the background work. The pollers finish their current long-poll."""
        self._stop.set()
        if self._pinger is not None:
            self._pinger.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._pinger
            self._pinger = None
        threads, self._threads = self._threads, []
        if threads:
            await asyncio.to_thread(self._join, threads, transport.LONG_POLL_S + 5)
        self._executor.shutdown(wait=False, cancel_futures=True)
        logs.event(log, "relay.bridge_stopped")

    @staticmethod
    def _join(threads: list[threading.Thread], timeout: float) -> None:
        end = time.monotonic() + timeout
        for thread in threads:
            thread.join(max(0.0, end - time.monotonic()))

    # --------------------------------------------------------------- health

    @property
    def inside_ok(self) -> bool:
        return self._inside_ok

    def _mark_up(self, source: str) -> None:
        with self._lock:
            changed = not self._inside_ok
            self._inside_ok = True
        if changed:
            logs.event(log, "relay.inside_up", source=source)

    def _mark_down(self, reason: str) -> None:
        with self._lock:
            changed = self._inside_ok
            self._inside_ok = False
        if changed:
            logs.event(log, "relay.inside_down", logging.WARNING, reason=reason)

    def health(self) -> dict[str, Any]:
        last = self._last_ping_ok
        with self._lock:
            pending = len(self._pending)
        return {
            "inside_ok": self._inside_ok,
            "last_ping_ok_age_s": None if last is None else round(time.monotonic() - last, 1),
            "pending": pending,
        }

    # ------------------------------------------------------- waiting requests

    def _register(self, rid: str, keys: sealing.RequestKeys, kind: str) -> _Pending:
        entry = _Pending(keys=keys, future=asyncio.get_running_loop().create_future(), kind=kind)
        with self._lock:
            self._pending[rid] = entry
        return entry

    def _forget(self, rid: str) -> None:
        """Stop waiting for `rid`, and remember it: a reply that comes later is
        this bridge's, and late."""
        with self._lock:
            self._pending.pop(rid, None)
            self._given_up.add(rid, time.monotonic())

    async def _exchange(
        self, request: RelayRequest, header: bytes, keys: sealing.RequestKeys, wait_s: float
    ) -> RelayResponse:
        """Send a sealed request and wait for its reply. Raises `_NoReply` when
        none comes in `wait_s`; AWS errors from the send propagate. The waiting
        entry is registered before the send, so even an instant reply finds it."""
        rid = request.id
        blob = sealing.finish_request(header, keys, request.to_bytes(), rid)
        entry = self._register(rid, keys, request.kind)
        try:
            await self._aws(
                transport.send,
                self.sqs,
                self.settings.common.request_queue_url,
                rid,
                "p" if request.kind == "ping" else "q",
                blob,
            )
            try:
                return await asyncio.wait_for(entry.future, timeout=max(0.0, wait_s))
            except TimeoutError as exc:
                raise _NoReply from exc
        finally:
            self._forget(rid)

    # ---------------------------------------------------------- reply pollers

    def _poll_replies(self) -> None:
        queue = self.settings.reply_queue_url
        while not self._stop.is_set():
            try:
                messages = transport.receive(self.sqs, queue, max_messages=10)
            except (BotoCoreError, ClientError) as exc:
                logs.event(
                    log, "relay.reply_poll_failed", logging.WARNING, error=type(exc).__name__
                )
                self._stop.wait(1.0)
                continue
            except Exception as exc:
                logs.event(log, "relay.reply_poll_failed", logging.ERROR, error=type(exc).__name__)
                self._stop.wait(1.0)
                continue
            released = False
            for message in messages:
                try:
                    released = self._deliver(message) or released
                except Exception as exc:
                    logs.event(
                        log,
                        "relay.reply_failed",
                        logging.ERROR,
                        rid=message.request_id,
                        error=type(exc).__name__,
                    )
            if released:
                self._stop.wait(FOREIGN_PAUSE_S)

    def _deliver(self, message: transport.Received) -> bool:
        """Hand a reply to its waiting request. True when the reply was not
        this bridge's and went back to the queue."""
        rid = message.request_id
        queue = self.settings.reply_queue_url
        with self._lock:
            entry = self._pending.get(rid)
            late = entry is None and self._given_up.has(rid, time.monotonic())
        if entry is None:
            receives = message.receive_count
            if late or receives is None or receives >= MAX_REPLY_RECEIVES:
                logs.event(log, "late_reply", rid=rid, receives=receives)
                transport.delete(self.sqs, queue, message.receipt)
                return False
            # Not a request of this bridge's: another bridge is polling this
            # queue. Put it back for that bridge rather than lose it.
            logs.event(log, "foreign_reply", logging.WARNING, rid=rid, receives=receives)
            try:
                transport.release(self.sqs, queue, message.receipt)
            except (BotoCoreError, ClientError) as exc:
                # Already deleted by its bridge (SQS can deliver a message
                # twice), or the receipt has expired: it is not lost here.
                logs.event(
                    log, "relay.release_failed", logging.WARNING, rid=rid, error=type(exc).__name__
                )
            return True
        try:
            plaintext = sealing.open_sealed(entry.keys.reply_key, sealing.REPLY, message.blob, rid)
            response = RelayResponse.from_bytes(plaintext)
        except (sealing.SealError, EnvelopeError) as exc:
            # Not from the collector, or damaged. Keep waiting for the real one.
            logs.event(log, "relay.reply_refused", logging.WARNING, rid=rid, reason=str(exc))
            transport.delete(self.sqs, queue, message.receipt)
            return False
        if response.id != rid:
            logs.event(log, "relay.reply_refused", logging.WARNING, rid=rid, reason="id mismatch")
            transport.delete(self.sqs, queue, message.receipt)
            return False
        entry.future.get_loop().call_soon_threadsafe(_resolve, entry.future, response)
        if entry.kind == "http":
            self._mark_up("reply")
        transport.delete(self.sqs, queue, message.receipt)
        return False

    # ----------------------------------------------------------------- pinger

    async def _ping_loop(self) -> None:
        interval = self.settings.ping_interval_s
        while not self._stop.is_set():
            started = time.monotonic()
            try:
                reason = await self._ping_once()
            except Exception as exc:
                logs.event(log, "relay.ping_failed", logging.ERROR, error=type(exc).__name__)
                reason = f"ping_failed:{type(exc).__name__}"
            if reason is None:
                self._last_ping_ok = time.monotonic()
                self._mark_up("ping")
            else:
                self._mark_down(reason)
            await asyncio.sleep(max(0.0, interval - (time.monotonic() - started)))

    async def _ping_once(self) -> str | None:
        """None when the inside answered healthy, else why not."""
        wait_s = min(PING_WAIT_S, self.settings.ping_interval_s)
        rid = uuid.uuid4().hex
        issued = now_ms()
        ping = RelayRequest(
            id=rid,
            reply_to=self.settings.reply_queue_url,
            issued_ms=issued,
            deadline_ms=issued + int(wait_s * 1000),
            method="GET",
            path="/health",
            kind="ping",
        )
        header, keys = sealing.begin_request(self.settings.collector_public)
        try:
            response = await self._exchange(ping, header, keys, wait_s)
        except _NoReply:
            return "ping_timeout"
        except (BotoCoreError, ClientError) as exc:
            return f"ping_send_failed:{type(exc).__name__}"
        if response.status != 200:
            return f"ping_status:{response.status}"
        return None

    # --------------------------------------------------------------- requests

    def _is_local_probe(self, request: Request) -> bool:
        if "x-forwarded-for" in request.headers:
            return False
        host = request.client.host if request.client else None
        try:
            return host is not None and ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    def _client_ip(self, request: Request) -> str | None:
        forwarded = ",".join(request.headers.getlist("x-forwarded-for"))
        entries = [e.strip() for e in forwarded.split(",") if e.strip()]
        hop = self.settings.client_ip_hop
        if len(entries) >= hop:
            chosen = _ip(entries[-hop])
            if chosen is not None:
                return chosen
        return _ip(request.client.host if request.client else None)

    async def _read_body(self, request: Request) -> bytes | None:
        """The body, or None when it is over the cap. Counts what arrives;
        `Content-Length` is only used to refuse early."""
        limit = self.settings.max_body_bytes
        declared = request.headers.get("content-length", "").strip()
        if declared.isdigit() and int(declared) > limit:
            return None
        chunks: list[bytes] = []
        size = 0
        async with contextlib.aclosing(request.stream()) as stream:
            async for chunk in stream:
                size += len(chunk)
                if size > limit:
                    return None
                chunks.append(chunk)
        return b"".join(chunks)

    def _store_request_body(self, rid: str, keys: sealing.RequestKeys, body: bytes) -> Body:
        sealed = sealing.seal(keys.request_key, sealing.REQUEST_BODY, body, rid)
        key = transport.body_key("req", rid)
        digest = transport.put_blob(self.s3, self.settings.common.bucket, key, sealed)
        return Body(s3_key=key, size=len(sealed), sha256=digest)

    def _drop_request_body(self, rid: str) -> None:
        try:
            self.s3.delete_object(
                Bucket=self.settings.common.bucket, Key=transport.body_key("req", rid)
            )
        except Exception as exc:
            logs.event(
                log, "relay.body_cleanup_failed", logging.WARNING, rid=rid, error=type(exc).__name__
            )

    def _load_reply_body(self, rid: str, keys: sealing.RequestKeys, body: Body) -> bytes:
        if body.s3_key != transport.body_key("res", rid):
            raise ValueError("reply body is not this request's")
        blob = transport.take_blob(
            self.s3,
            self.settings.common.bucket,
            body.s3_key,
            body.sha256,
            MAX_REPLY_BODY_BYTES,
            expected_size=body.size,
        )
        return sealing.open_sealed(keys.reply_key, sealing.REPLY_BODY, blob, rid)

    async def handle(self, request: Request) -> Response:
        scope = request.scope
        raw_path = scope.get("raw_path")
        path = (
            bytes(raw_path).decode("latin-1") if raw_path else str(scope.get("path", "/"))
        ).split("?", 1)[0]
        method = request.method.upper()

        if method == "GET" and path == HEALTH_PATH and self._is_local_probe(request):
            return JSONResponse(self.health(), headers={"cache-control": "no-store"})

        started = time.monotonic()
        rid = uuid.uuid4().hex
        template = self.routes.match(method, path)
        line: dict[str, Any] = {
            "rid": rid,
            "route": template,
            "method": method,
            "req_bytes": 0,
            "res_bytes": 0,
            "via": "inline",
        }

        def finish(response: Response) -> Response:
            line["status"] = response.status_code
            line["ms"] = int((time.monotonic() - started) * 1000)
            if not line["res_bytes"]:
                line["res_bytes"] = len(response.body)
            logs.event(log, "relay.request", **line)
            return response

        def error(status: int, code: str, message: str) -> Response:
            return finish(
                Response(error_json(code, message, rid), status_code=status, media_type=_JSON)
            )

        if template is None:
            return error(404, "not_found", "Not Found")
        if not self._inside_ok:
            return error(503, "inside_unreachable", UNREACHABLE_MESSAGE)

        try:
            body = await self._read_body(request)
        except ClientDisconnect:
            line["status"] = 499
            line["ms"] = int((time.monotonic() - started) * 1000)
            logs.event(log, "relay.request", **line)
            return Response(status_code=400)
        if body is None:
            mib = self.settings.max_body_bytes // (1024 * 1024)
            return error(413, "payload_too_large", f"Request body exceeds {mib} MB")
        line["req_bytes"] = len(body)

        common = self.settings.common
        headers = request_headers(
            [(k.decode("latin-1"), v.decode("latin-1")) for k, v in request.headers.raw],
            csrf_header=common.csrf_header,
            cookie_names=common.cookie_names,
            extra=self._extra_headers,
        )
        content_type = request.headers.get("content-type", "").lower()
        upload = content_type.startswith("multipart/form-data")
        deadline_s = self.settings.upload_deadline_s if upload else self.settings.deadline_s

        header, keys = sealing.begin_request(self.settings.collector_public)
        stored = False
        try:
            if len(body) > INLINE_LIMIT:
                body_ref: Body | None = await self._aws(self._store_request_body, rid, keys, body)
                stored = True
                line["via"] = "s3"
            else:
                body_ref = Body(inline=body) if body else None
            issued = now_ms()
            envelope = RelayRequest(
                id=rid,
                reply_to=self.settings.reply_queue_url,
                issued_ms=issued,
                deadline_ms=issued + int(deadline_s * 1000),
                method=method,
                path=path,
                query=bytes(scope.get("query_string", b"")).decode("latin-1"),
                headers=headers,
                client_ip=self._client_ip(request),
                body=body_ref,
                kind="http",
            )
            wait_s = (envelope.deadline_ms - now_ms()) / 1000 + REPLY_GRACE_S
            reply = await self._exchange(envelope, header, keys, wait_s)
        except _NoReply:
            if stored:
                await self._aws(self._drop_request_body, rid)
            return error(504, "inside_timeout", TIMEOUT_MESSAGE)
        except Exception as exc:
            logs.event(log, "relay.send_failed", logging.ERROR, rid=rid, error=type(exc).__name__)
            if stored:
                await self._aws(self._drop_request_body, rid)
            return error(502, "relay_error", RELAY_ERROR_MESSAGE)

        if reply.status < 200:
            return error(502, "bad_reply", BAD_REPLY_MESSAGE)
        try:
            if reply.body is None:
                content = b""
            elif reply.body.inline is not None:
                content = reply.body.inline
            else:
                content = await self._aws(self._load_reply_body, rid, keys, reply.body)
                line["via"] = "s3"
        except Exception as exc:
            logs.event(
                log, "relay.reply_body_failed", logging.ERROR, rid=rid, error=type(exc).__name__
            )
            return error(502, "bad_reply", BAD_REPLY_MESSAGE)

        if reply.status in (204, 304):
            content = b""
        response = Response(content=content, status_code=reply.status)
        for name, value in response_headers(reply.headers):
            raw = _safe_header(name, value)
            if raw is not None:
                response.raw_headers.append(raw)
        line["res_bytes"] = len(content)
        return finish(response)


class _Endpoint:
    """The catch-all: every method, every path, handed to the bridge."""

    def __init__(self, bridge: Bridge) -> None:
        self.bridge = bridge

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = await self.bridge.handle(Request(scope, receive))
        await response(scope, receive, send)


async def _not_found(request: Request, exc: Exception) -> Response:
    # Only a path the catch-all cannot match (one not starting with "/") gets here.
    return Response(
        error_json("not_found", "Not Found", uuid.uuid4().hex), status_code=404, media_type=_JSON
    )


def create_app(
    settings: BridgeSettings,
    *,
    sqs: Any = None,
    s3: Any = None,
    start_background: bool = True,
) -> Starlette:
    """The bridge as an ASGI app. The reply pollers and the pinger run for the
    app's lifespan when `start_background` is true."""
    if sqs is None or s3 is None:
        built_sqs, built_s3 = transport.build_clients(
            settings.common, pool=max(16, settings.reply_pollers + 32)
        )
        sqs = built_sqs if sqs is None else sqs
        s3 = built_s3 if s3 is None else s3
    bridge = Bridge(settings, sqs, s3)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        if start_background:
            await bridge.start()
        try:
            yield
        finally:
            if start_background:
                await bridge.stop()

    app = Starlette(
        routes=[Route("/{path:path}", endpoint=_Endpoint(bridge))],
        exception_handlers={HTTPException: _not_found},
        lifespan=lifespan,
    )
    app.state.bridge = bridge
    return app


def main() -> None:
    logs.setup()
    try:
        settings = bridge_settings()
    except ConfigError as exc:
        raise SystemExit(f"cmp-relay bridge: {exc}") from exc
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        proxy_headers=False,
        server_header=False,
        access_log=False,
        log_config=None,
    )


if __name__ == "__main__":
    main()
