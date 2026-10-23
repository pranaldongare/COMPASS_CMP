"""The collector: the inside half of the relay.

It runs inside the organisation's network, which accepts no incoming
connection, and opens every connection itself: a long poll on the request queue
(outbound HTTPS to SQS), a read of a large body from S3, a call to the API on
the same host, and the sealed reply sent back to the asking bridge's queue.

Every message is untrusted input. Anyone allowed to send to the request queue
can seal a request to the collector's public key, so this side - not the
bridge - is where the relay's rules hold:

* **Only the public routes.** The route allow-list and the header and cookie
  filter are applied again here. A path that the URL library would rewrite
  (a `.` segment) is refused, so the API sees exactly the route that was
  allowed.
* **Only before the deadline.** A request whose deadline has passed is dropped
  without a reply: the bridge has already answered the browser. A write is
  started only with at least `RELAY_WRITE_BUDGET_S` left, so it can finish
  before the bridge gives up - what stops a consent the person saw fail from
  being recorded later. The time left is measured again after the write's
  message is deleted, and the API call is given only what is left then.
* **On AWS's clock.** The deadline is set on the bridge's clock (EC2, synced to
  Amazon Time Sync). This host's clock is compared with AWS's on every first
  receive (`ApproximateFirstReceiveTimestamp`), and the time left is measured
  on AWS's clock with the median of the last few offsets; an offset over a
  second is logged as `relay.clock_skew`. Both hosts must still run NTP.
* **At most once for writes.** The message of a POST, PUT, PATCH or DELETE is
  deleted before the API is called; a read's message after the reply is sent.
  A request id seen recently is dropped, so a message SQS delivers twice is
  executed once.
* **Replies only to a known bridge.** `reply_to` must be one of
  `RELAY_REPLY_QUEUE_URLS`, so a forged request cannot point the reply
  somewhere else.
* **No sealed values in.** A request carrying the sealed-value prefix in its
  query, a forwarded header or its body is refused, because the API opens
  sealed values in a relayed reply (`allowlist` says exactly what is searched;
  the API checks again with its own parser, ADR 0032).

On stop, a worker finishes the message in hand; a message it receives after
the stop is released back to the queue (visible again at once) for the next
collector, not handled.

The collector never talks to the key service. It presents a shared secret
(`X-CMP-Relay-Key`) and the API opens the sealed values in its reply.

What is logged: one `relay.handled` line per message - the request id, the
route template, the method, the status, the time taken, the outcome, the time
it spent queued and the clock offset in use (`offset_ms`, this host's clock
minus AWS's). Never the path, a header, a cookie, a body, a client address, or
an exception's message (an HTTP error's message carries the URL, and the URL a
token).
"""

from __future__ import annotations

import contextlib
import ipaddress
import logging
import re
import signal
import statistics
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from http.cookiejar import Cookie, CookieJar, CookiePolicy
from types import FrameType
from typing import Any

import httpx
from botocore.exceptions import BotoCoreError, ClientError

from cmp_relay import allowlist, logs, sealing, transport
from cmp_relay.config import CollectorSettings, ConfigError, collector_settings
from cmp_relay.envelope import (
    INLINE_LIMIT,
    Body,
    EnvelopeError,
    RelayRequest,
    RelayResponse,
    error_json,
    now_ms,
)

_log = logging.getLogger("cmp_relay.collector")

#: A request with this little time left is not started: the bridge gives up at
#: the deadline, and the reply has to travel back before then.
MIN_TIME_LEFT_S = 0.5
#: Request ids remembered to drop a message SQS delivers twice.
RECENT_IDS = 10_000
#: The largest sealed request body read from S3 (the bridge's default limit is
#: 26 MiB; sealing and the multipart framing add a little).
MAX_STORED_BODY = 27 * 1024 * 1024
#: Connecting to the API on the same host takes milliseconds; three seconds
#: means it is not there.
CONNECT_TIMEOUT_S = 3.0
#: How long a worker waits after an AWS error before it polls again.
ERROR_PAUSE_S = 1.0
#: Clock offsets kept: the estimate is their median.
OFFSET_SAMPLES = 20
#: An offset from AWS's clock larger than this is logged as `relay.clock_skew`...
SKEW_WARN_MS = 1000
#: ...at most this often.
SKEW_WARN_EVERY_S = 60.0

#: A request id names S3 objects (`req/<id>`) and appears in logs: nothing but
#: a token's characters.
_REQUEST_ID = re.compile(r"[A-Za-z0-9_.:-]{1,128}")
#: Methods a log line may name; anything else is logged as "other".
_KNOWN_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"})
#: Headers the collector sets itself. Whatever the envelope says about them is
#: discarded, so each is sent exactly once, with the collector's value.
_OWN_HEADERS = frozenset({"x-forwarded-for", "x-cmp-relay-key", "accept-encoding"})
#: Headers the HTTP client adds when the browser sent none. They are removed, so
#: the API never records the collector's client as the visitor's.
_CLIENT_DEFAULTS = ("user-agent", "accept")
#: Characters a header value may not carry.
_BAD_HEADER_CHARS = re.compile(r"[\r\n\x00]")

_ERROR_HEADERS = [("content-type", "application/json"), ("cache-control", "no-store")]
_HEALTHY = b'{"status":"ok"}'

_UNREACHABLE = "We can't reach our records right now. Nothing was saved; please try again shortly."
_TOO_LATE = "We couldn't get to this in time. Nothing was saved; please try again."
_UNREADABLE = "We couldn't read what you sent. Nothing was saved; please try again."
_REFUSED = "This request contains a value that can't be accepted."
_NOT_FOUND = "Not found."
_BAD_REQUEST = "This request can't be read."
_SLOW_READ = "Our records took too long to answer. Please try again shortly."
_SLOW_WRITE = (
    "Our records took too long to answer. Your change may have been saved; "
    "please check before trying again."
)
_FAILED_READ = "Something went wrong reaching our records. Please try again shortly."
_FAILED_WRITE = (
    "Something went wrong reaching our records. Your change may have been saved; "
    "please check before trying again."
)


class _BodyError(Exception):
    """A request body that cannot be read: missing, tampered with, or too large."""


@dataclass(frozen=True)
class _Answer:
    """What goes back to the bridge, before it is sealed."""

    status: int
    headers: list[tuple[str, str]]
    content: bytes
    reason: str | None = None


@dataclass
class _Note:
    """The one log line a message produces, filled in as it is handled."""

    rid: str
    route: str | None = None
    method: str | None = None
    status: int | None = None
    outcome: str = "failed"
    reason: str | None = None
    level: int = logging.INFO
    extra: dict[str, Any] = field(default_factory=dict)

    def fields(self, started: float) -> dict[str, Any]:
        out: dict[str, Any] = {
            "rid": self.rid[:128],
            "route": self.route,
            "method": self.method,
            "status": self.status,
            "ms": round((time.monotonic() - started) * 1000),
            "outcome": self.outcome,
        }
        if self.reason:
            out["reason"] = self.reason
        out.update(self.extra)
        return out


class RecentIds:
    """A bounded, thread-safe memory of request ids already taken."""

    def __init__(self, capacity: int = RECENT_IDS) -> None:
        self._capacity = capacity
        self._ids: OrderedDict[str, None] = OrderedDict()
        self._lock = threading.Lock()

    def first_sight(self, request_id: str) -> bool:
        """True the first time an id is offered; False while it is remembered."""
        with self._lock:
            if request_id in self._ids:
                self._ids.move_to_end(request_id)
                return False
            self._ids[request_id] = None
            if len(self._ids) > self._capacity:
                self._ids.popitem(last=False)
            return True


class ClockOffset:
    """How far this host's wall clock is ahead of AWS's, in milliseconds: the
    median of the last few samples, 0 until there is one. Thread-safe.

    A sample is this host's time at a receive minus SQS's
    `ApproximateFirstReceiveTimestamp`, taken only from a message received for
    the first time - for a redelivered one that timestamp is an older receive."""

    def __init__(self, samples: int = OFFSET_SAMPLES) -> None:
        self._samples: deque[int] = deque(maxlen=samples)
        self._ms = 0
        self._lock = threading.Lock()

    def add(self, sample_ms: int) -> int:
        """Add a sample; returns the new estimate."""
        with self._lock:
            self._samples.append(sample_ms)
            self._ms = int(statistics.median(self._samples))
            return self._ms

    @property
    def ms(self) -> int:
        with self._lock:
            return self._ms


def _client_ip(value: str | None) -> str | None:
    """The visitor's address, normalised, or None when it is not an address."""
    if not value or "%" in value:
        return None
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def _plain_path(path: str) -> bool:
    """No `.` or `..` segment, which an HTTP client would resolve away."""
    return all(segment not in (".", "..") for segment in path.split("/"))


def _budget(time_left_s: float) -> float:
    """How long the API call may take: up to half a second before the deadline."""
    return max(MIN_TIME_LEFT_S, time_left_s - MIN_TIME_LEFT_S)


def _http_timeout(time_left_s: float) -> httpx.Timeout:
    total = _budget(time_left_s)
    return httpx.Timeout(total, connect=min(CONNECT_TIMEOUT_S, total))


def _read_by(response: httpx.Response, give_up: float) -> bytes:
    """The whole body, or `httpx.ReadTimeout` once `give_up` (monotonic) passes.

    httpx's timeouts bound each read, not the call: an answer that arrives a
    little at a time would otherwise hold a worker, and its reply reach the
    bridge after it had given up."""
    chunks: list[bytes] = []
    for chunk in response.iter_bytes():
        chunks.append(chunk)
        if time.monotonic() > give_up:
            raise httpx.ReadTimeout("the answer did not finish in time", request=response.request)
    return b"".join(chunks)


class _RefuseEveryCookie(CookiePolicy):
    """Keeps no cookie and sends none, for any host - including a bare IP
    address, which `DefaultCookiePolicy(allowed_domains=[])` still stores for."""

    netscape = True
    rfc2965 = False
    hide_cookie2 = True

    def set_ok(self, cookie: Cookie, request: Any) -> bool:
        return False

    def return_ok(self, cookie: Cookie, request: Any) -> bool:
        return False

    def domain_return_ok(self, domain: str, request: Any) -> bool:
        return False

    def path_return_ok(self, path: str, request: Any) -> bool:
        return False


def no_cookie_jar() -> CookieJar:
    """A cookie jar that stores nothing and sends nothing.

    The collector forwards each visitor's own `Cookie` header and returns each
    `Set-Cookie` to that visitor; it must hold no cookie of its own between
    requests. Returned as the stdlib jar on purpose: `httpx.Client` copies an
    `httpx.Cookies` into a fresh jar, which would drop this policy."""
    return CookieJar(policy=_RefuseEveryCookie())


class Collector:
    """Takes requests off the queue, runs them against the API, sends the replies.

    `handle` processes one message synchronously; `run` keeps `workers` threads
    doing that until told to stop."""

    def __init__(
        self,
        settings: CollectorSettings,
        *,
        sqs: Any = None,
        s3: Any = None,
        http: httpx.Client | None = None,
    ) -> None:
        self._settings = settings
        common = settings.common
        if sqs is None or s3 is None:
            built_sqs, built_s3 = transport.build_clients(common, pool=settings.workers * 2 + 4)
            sqs = built_sqs if sqs is None else sqs
            s3 = built_s3 if s3 is None else s3
        self._sqs = sqs
        self._s3 = s3
        self._owns_http = http is None
        # trust_env=False: the host's HTTPS_PROXY is for the way out to AWS; the
        # API is on this side and must never be reached through the proxy.
        # cookies=no_cookie_jar(): one client serves every visitor, so it must
        # never keep a cookie. httpx's default jar stores each Set-Cookie and
        # adds it to the next request that carries none - which signed every
        # anonymous visitor in as whoever had signed in last (found in the
        # end-to-end run, 2026-10-23).
        self._http = http or httpx.Client(
            follow_redirects=False,
            trust_env=False,
            cookies=no_cookie_jar(),
            limits=httpx.Limits(
                max_connections=settings.workers + 2,
                max_keepalive_connections=settings.workers,
            ),
        )
        self._routes = allowlist.RouteTable(allow_dev_routes=common.allow_dev_routes)
        self._extra_headers = (
            frozenset({"x-cmp-dev-client"}) if common.allow_dev_routes else frozenset()
        )
        self._private_keys = list(settings.private_keys)
        self._recent = RecentIds()
        self._clock = ClockOffset()
        self._skew_lock = threading.Lock()
        self._skew_logged_at: float | None = None

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    # ------------------------------------------------------------------ running

    def run(self, stop: threading.Event) -> None:
        """Run `workers` threads until `stop` is set, then wait for them to
        finish the message in hand: at most the long poll under way (20 s),
        whose message is released rather than handled, or one request already
        started (up to its deadline, 50 s for an upload)."""
        threads = [
            threading.Thread(target=self._work, args=(stop,), name=f"collector-{n}", daemon=True)
            for n in range(self._settings.workers)
        ]
        for thread in threads:
            thread.start()
        logs.event(_log, "relay.collector_started", workers=len(threads))
        while not stop.wait(0.5):
            pass
        for thread in threads:
            thread.join()
        logs.event(_log, "relay.collector_stopped")

    def _work(self, stop: threading.Event) -> None:
        queue = self._settings.common.request_queue_url
        while not stop.is_set():
            try:
                batch = transport.receive(self._sqs, queue, max_messages=1)
            except Exception as exc:  # AWS, the network, the proxy: wait, then poll again
                logs.event(_log, "relay.receive_failed", logging.WARNING, error=type(exc).__name__)
                stop.wait(ERROR_PAUSE_S)
                continue
            if stop.is_set():
                # Stopping: what this poll brought back goes back to the queue,
                # visible at once to the next collector, and nothing more is taken.
                self._release(batch)
                return
            for received in batch:
                try:
                    self.handle(received)
                except Exception as exc:  # one bad message never stops a worker
                    logs.event(
                        _log,
                        "relay.handle_failed",
                        logging.ERROR,
                        rid=received.request_id[:128],
                        error=type(exc).__name__,
                    )

    def _release(self, batch: list[transport.Received]) -> None:
        queue = self._settings.common.request_queue_url
        for received in batch:
            rid = received.request_id[:128] if _REQUEST_ID.fullmatch(received.request_id) else "-"
            try:
                transport.release(self._sqs, queue, received.receipt)
            except Exception as exc:  # best effort: it comes back after its visibility timeout
                logs.event(
                    _log, "relay.release_failed", logging.WARNING, rid=rid, error=type(exc).__name__
                )
            else:
                logs.event(_log, "relay.released", rid=rid)

    # -------------------------------------------------------------------- clock

    def _observe_clock(self, received: transport.Received) -> None:
        """Take a clock sample from a first receive, and say when the offset is
        large (at most once a minute)."""
        if received.receive_count != 1 or received.first_receive_ms is None:
            return
        offset = self._clock.add(now_ms() - received.first_receive_ms)
        if abs(offset) <= SKEW_WARN_MS:
            return
        with self._skew_lock:
            now = time.monotonic()
            if self._skew_logged_at is not None and now - self._skew_logged_at < SKEW_WARN_EVERY_S:
                return
            self._skew_logged_at = now
        logs.event(_log, "relay.clock_skew", logging.WARNING, offset_ms=offset)

    def _aws_now_ms(self) -> int:
        """Now on AWS's clock, as far as this host can tell."""
        return now_ms() - self._clock.ms

    def _time_left_s(self, request: RelayRequest) -> float:
        return request.time_left_s(self._aws_now_ms())

    # ----------------------------------------------------------------- handling

    def handle(self, received: transport.Received) -> None:
        """Process one message: open, check, execute, reply. Logs one line.

        Bad input never raises: it is dropped or refused. What raises is AWS
        failing (sending the reply, deleting the message) or a bug; the worker
        loop logs it and carries on."""
        started = time.monotonic()
        note = _Note(rid=received.request_id)
        self._observe_clock(received)
        note.extra["offset_ms"] = self._clock.ms
        try:
            self._handle(received, note)
        except BaseException:
            note.outcome, note.level = "failed", logging.ERROR
            raise
        finally:
            logs.event(_log, "relay.handled", note.level, **note.fields(started))

    def _handle(self, received: transport.Received, note: _Note) -> None:
        rid = received.request_id
        if not _REQUEST_ID.fullmatch(rid):
            note.rid = "-"  # not echoed into the log: it could be anything
            self._drop(received, note, "bad_request_id")
            return
        try:
            plaintext, keys = sealing.open_request(self._private_keys, received.blob, rid)
        except sealing.SealError:
            self._drop(received, note, "unsealable")
            return
        try:
            request = RelayRequest.from_bytes(plaintext)
        except EnvelopeError:
            self._drop(received, note, "malformed")
            return
        if request.id != rid:
            self._drop(received, note, "id_mismatch")
            return
        method = request.method.upper()
        note.method = method if method in _KNOWN_METHODS else "other"
        # Not clamped: a negative figure is a clock out of step, worth seeing.
        note.extra["queued_ms"] = self._aws_now_ms() - request.issued_ms
        if request.reply_to not in self._settings.reply_queue_urls:
            self._drop(received, note, "reply_to_not_allowed")
            return
        if not self._recent.first_sight(rid):
            # Delete with this, the newest, receipt: an older one may no longer work.
            self._delete(received)
            note.outcome = "duplicate"
            return
        if self._time_left_s(request) <= MIN_TIME_LEFT_S:
            self._expire(received, request, note)
            return
        if request.kind == "ping":
            self._ping(received, request, keys, note)
            return
        self._http_request(received, request, keys, note)

    def _http_request(
        self,
        received: transport.Received,
        request: RelayRequest,
        keys: sealing.RequestKeys,
        note: _Note,
    ) -> None:
        method = request.method.upper()
        route = self._routes.match(method, request.path)
        if route is None or not _plain_path(request.path):
            self._refuse(received, request, keys, note, 404, "not_found", _NOT_FOUND)
            return
        note.route = route
        url = self._url(request)
        if url is None:
            self._refuse(received, request, keys, note, 400, "bad_request", _BAD_REQUEST)
            return

        try:
            body = self._request_body(request, keys)
        except _BodyError:
            self._refuse(received, request, keys, note, 400, "body_unreadable", _UNREADABLE)
            return
        headers = self._forward_headers(request)
        content_type = next((v for n, v in headers if n == "content-type"), None)
        visitors = [(n, v) for n, v in headers if n not in _OWN_HEADERS]
        if allowlist.carries_sealed_value(request.query, content_type, body, visitors):
            self._refuse(received, request, keys, note, 422, "sealed_value_refused", _REFUSED)
            return

        time_left = self._time_left_s(request)
        if time_left <= MIN_TIME_LEFT_S:
            self._expire(received, request, note)
            return
        unsafe = method in allowlist.UNSAFE_METHODS
        if unsafe:
            budget = self._settings.write_budget_s
            if time_left < budget:
                self._refuse(received, request, keys, note, 503, "deadline_too_close", _TOO_LATE)
                return
            # At most once: the message goes before the write starts. If the
            # collector dies now the write is lost, never repeated.
            self._delete(received)
            # The delete is a call through the proxy and can be slow: measure
            # again. The message is gone, so neither answer below deletes it.
            time_left = self._time_left_s(request)
            if time_left <= MIN_TIME_LEFT_S:
                note.outcome, note.reason = "expired", "after_delete"
                self._discard_body(request)
                return
            if time_left < budget:
                note.status, note.reason, note.outcome = 503, "deadline_too_close", "refused"
                answer = _error_answer(503, "deadline_too_close", _TOO_LATE, request.id)
                self._reply(request, keys, answer, False)
                self._discard_body(request)
                return

        answer = self._call(request, method, url, headers, body, unsafe)
        note.status, note.reason = answer.status, answer.reason
        note.outcome = "executed"
        self._reply(request, keys, answer, unsafe)
        if not unsafe:
            self._delete(received)

    # ------------------------------------------------------------ the request

    def _url(self, request: RelayRequest) -> httpx.URL | None:
        """The API URL, or None when the URL library would not send the path
        exactly as it was matched against the allow-list."""
        raw = self._settings.api_origin + request.path
        if request.query:
            raw += "?" + request.query
        try:
            url = httpx.URL(raw)
        except httpx.InvalidURL:
            return None
        if url.raw_path.split(b"?", 1)[0] != request.path.encode("ascii"):
            return None
        return url

    def _request_body(self, request: RelayRequest, keys: sealing.RequestKeys) -> bytes | None:
        body = request.body
        if body is None:
            return None
        if body.inline is not None:
            return body.inline
        expected = transport.body_key("req", request.id)
        if body.s3_key != expected or body.size > MAX_STORED_BODY:
            raise _BodyError("the body is not where this request's body belongs")
        try:
            blob = transport.take_blob(
                self._s3,
                self._settings.common.bucket,
                expected,
                body.sha256,
                MAX_STORED_BODY,
                expected_size=body.size,
            )
            return sealing.open_sealed(keys.request_key, sealing.REQUEST_BODY, blob, request.id)
        except (ValueError, sealing.SealError, ClientError, BotoCoreError) as exc:
            raise _BodyError(type(exc).__name__) from exc

    def _forward_headers(self, request: RelayRequest) -> list[tuple[str, str]]:
        """The allow-listed headers, re-filtered here, plus the collector's own."""
        common = self._settings.common
        kept = allowlist.request_headers(
            request.headers,
            csrf_header=common.csrf_header,
            cookie_names=common.cookie_names,
            extra=self._extra_headers,
        )
        out: list[tuple[str, str]] = []
        has_content_type = False
        for name, value in kept:
            if name in _OWN_HEADERS or _BAD_HEADER_CHARS.search(value):
                continue
            try:
                value.encode("latin-1")
            except UnicodeEncodeError:
                continue
            if name == "content-type":
                # One content type: the one the sealed-value check looks at is
                # the one the API reads.
                if has_content_type:
                    continue
                has_content_type = True
            out.append((name, value))
        client_ip = _client_ip(request.client_ip)
        if client_ip:
            out.append(("x-forwarded-for", client_ip))
        out.append(("x-cmp-relay-key", self._settings.ingress_key))
        out.append(("accept-encoding", "identity"))
        return out

    def _call(
        self,
        request: RelayRequest,
        method: str,
        url: httpx.URL,
        headers: list[tuple[str, str]],
        body: bytes | None,
        unsafe: bool,
    ) -> _Answer:
        rid = request.id
        sent = {name for name, _ in headers}
        # The time left now, as the call starts: not as it was before the body
        # was fetched or the message deleted.
        time_left = self._time_left_s(request)
        give_up = time.monotonic() + _budget(time_left)
        try:
            outgoing = self._http.build_request(
                method,
                url,
                headers=[(n.encode("ascii"), v.encode("latin-1")) for n, v in headers],
                content=body or None,
                timeout=_http_timeout(time_left),
            )
            for default in _CLIENT_DEFAULTS:
                if default not in sent and default in outgoing.headers:
                    del outgoing.headers[default]
            response = self._http.send(outgoing, follow_redirects=False, stream=True)
            try:
                content = _read_by(response, give_up)
            finally:
                response.close()
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
            return _error_answer(503, "api_unavailable", _UNREACHABLE, rid)
        except httpx.TimeoutException:
            return _error_answer(503, "api_timeout", _SLOW_WRITE if unsafe else _SLOW_READ, rid)
        except httpx.HTTPError:
            return _error_answer(502, "api_error", _FAILED_WRITE if unsafe else _FAILED_READ, rid)
        return _Answer(
            status=response.status_code,
            headers=allowlist.response_headers(response.headers.multi_items()),
            content=content,
        )

    # ---------------------------------------------------------------- pings

    def _ping(
        self,
        received: transport.Received,
        request: RelayRequest,
        keys: sealing.RequestKeys,
        note: _Note,
    ) -> None:
        """A ping asks whether the inside is there. The envelope's path is not
        used: a ping only ever calls the API's liveness check."""
        note.route = "ping"
        try:
            response = self._http.get(
                self._settings.api_origin + "/health",
                headers={"accept-encoding": "identity"},
                timeout=_http_timeout(self._time_left_s(request)),
                follow_redirects=False,
            )
            healthy = response.status_code == 200
        except httpx.HTTPError:
            healthy = False
        if healthy:
            answer = _Answer(200, [("content-type", "application/json")], _HEALTHY)
        else:
            answer = _error_answer(503, "api_unavailable", _UNREACHABLE, request.id)
        note.status, note.reason, note.outcome = answer.status, answer.reason, "executed"
        self._reply(request, keys, answer, unsafe=False)
        self._delete(received)

    # -------------------------------------------------------------- replies

    def _reply(
        self,
        request: RelayRequest,
        keys: sealing.RequestKeys,
        answer: _Answer,
        unsafe: bool,
    ) -> None:
        content = answer.content
        body: Body | None = None
        if content and len(content) <= INLINE_LIMIT:
            body = Body(inline=content)
        elif content:
            key = transport.body_key("res", request.id)
            sealed = sealing.seal(keys.reply_key, sealing.REPLY_BODY, content, request.id)
            try:
                digest = transport.put_blob(self._s3, self._settings.common.bucket, key, sealed)
            except (ClientError, BotoCoreError):
                answer = _error_answer(
                    502, "relay_error", _FAILED_WRITE if unsafe else _FAILED_READ, request.id
                )
                self._send(
                    request, keys, answer.status, answer.headers, Body(inline=answer.content)
                )
                return
            body = Body(s3_key=key, size=len(sealed), sha256=digest)
        self._send(request, keys, answer.status, answer.headers, body)

    def _send(
        self,
        request: RelayRequest,
        keys: sealing.RequestKeys,
        status: int,
        headers: list[tuple[str, str]],
        body: Body | None,
    ) -> None:
        reply = RelayResponse(id=request.id, status=status, headers=headers, body=body)
        blob = sealing.seal(keys.reply_key, sealing.REPLY, reply.to_bytes(), request.id)
        transport.send(self._sqs, request.reply_to, request.id, "r", blob)

    # ------------------------------------------------- refusals and drops

    def _refuse(
        self,
        received: transport.Received,
        request: RelayRequest,
        keys: sealing.RequestKeys,
        note: _Note,
        status: int,
        code: str,
        message: str,
    ) -> None:
        """Answer without calling the API, then let the message go."""
        note.status, note.reason, note.outcome = status, code, "refused"
        self._reply(request, keys, _error_answer(status, code, message, request.id), False)
        self._delete(received)
        self._discard_body(request)

    def _expire(self, received: transport.Received, request: RelayRequest, note: _Note) -> None:
        """Too late: the bridge has answered already. No reply, no call."""
        note.outcome = "expired"
        self._delete(received)
        self._discard_body(request)

    def _drop(self, received: transport.Received, note: _Note, reason: str) -> None:
        """A message that is not a request this collector will answer."""
        note.outcome, note.reason, note.level = "dropped", reason, logging.WARNING
        self._delete(received)

    def _delete(self, received: transport.Received) -> None:
        transport.delete(self._sqs, self._settings.common.request_queue_url, received.receipt)

    def _discard_body(self, request: RelayRequest) -> None:
        """Remove the stored body of a request that will not run. Best effort:
        the bucket's lifecycle rule catches whatever this misses."""
        body = request.body
        expected = transport.body_key("req", request.id)
        if body is None or body.s3_key != expected:
            return
        with contextlib.suppress(ClientError, BotoCoreError):
            self._s3.delete_object(Bucket=self._settings.common.bucket, Key=expected)


def _error_answer(status: int, code: str, message: str, request_id: str) -> _Answer:
    return _Answer(status, list(_ERROR_HEADERS), error_json(code, message, request_id), code)


# ------------------------------------------------------------------- process


def main() -> None:
    logs.setup()
    try:
        settings = collector_settings()
    except ConfigError as exc:
        raise SystemExit(f"collector: {exc}") from exc
    sqs, s3 = transport.build_clients(settings.common, pool=settings.workers * 2 + 4)
    collector = Collector(settings, sqs=sqs, s3=s3)
    stop = threading.Event()

    def _stop(signum: int, frame: FrameType | None) -> None:
        logs.event(_log, "relay.collector_stopping", signal=signal.Signals(signum).name)
        stop.set()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    try:
        collector.run(stop)
    finally:
        collector.close()


if __name__ == "__main__":
    main()
