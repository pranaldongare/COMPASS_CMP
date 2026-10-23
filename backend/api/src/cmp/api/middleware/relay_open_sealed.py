"""Open the sealed values in a reply going back out through the public relay.

The public-ingress relay's side of ADR 0016, as amended by ADR 0032. The data
principal's portal runs on AWS; the API, the database and the key service stay
inside a network that accepts no inbound connection, and the two meet only
through Amazon SQS (`backend/relay`: a bridge beside the portal, a collector
inside). ADR 0016 has the portal's own server open every `SE::` value through
`DKMS_URL`, which a portal on AWS cannot reach - and must not, since the key
service authenticates nobody. So for this one path the API opens them itself,
and only for a response it is itself serving to a request that came through
the relay presenting `RELAY_INGRESS_KEY` in `X-CMP-Relay-Key`. Every other
reply - the console's, a direct caller's, one with a wrong key - is served as
stored, exactly as before.

Four things keep that narrow:

* **The collector never reaches the key service.** It holds the ingress key,
  not a key-service address: what it is given is one reply the API chose to
  open for the request it relayed, and nothing else.
* **No sealed value comes in.** `seal()` passes a value that is already sealed
  through untouched, and this opens every `SE::` string in the reply wherever
  it sits, so any input the API repeats back - a name, a file name, a
  User-Agent shown on the sessions page, a field named in a validation error -
  would come back opened: an oracle for every value in the database. So a
  vouched-for request is refused (422 `sealed_value_refused`) before any route
  runs if the prefix appears anywhere the routes read: the path, a query
  parameter's name or value, a header (the cookie aside), or the body - read
  here with the API's own parsers, Starlette's form parser for a form and
  `json.loads` for anything else, so what is checked is exactly what a route
  will be given. The bytes of an uploaded file are not searched; its name and
  its part's headers are.
  The collector refuses the same before it calls; this is the authority, and
  it does not depend on the two parsing a body alike.
* **Only a data principal's session is honoured.** The scope passed down is
  marked `state.relayed`, and `dependencies.sessions` refuses (401) any other
  session on such a request: a console session taken off a staff machine is
  no key to the inside from the internet.
* **The key never reaches the application.** `X-CMP-Relay-Key` is stripped from
  every request before the routes see it, whether it matched or not, so no
  handler, error report or log line below this can repeat it.

Only `application/json` is opened. A download - a PDF, a ZIP - streams through
as it comes, unbuffered: nothing in it is a JSON string to open. A JSON reply
is buffered, walked once, and every sealed string in it opened in one call to
the key service. If that call fails for any reason, the reply goes out as
stored and the page shows ciphertext - today's failure mode for a key service
that is down, not a new one.

The request body of a vouched-for request is buffered whole to be checked and
then handed to the app unchanged, as one message. `BodyLimit`, outside this,
bounds it; a request without the key is never buffered or checked.

Innermost of the five, and still outside GZip (registered earlier, in
`bootstrap.middleware`): a matching request has `Accept-Encoding` removed on
the way in, so what comes back up to here is JSON that can be read. The relay
asks for `identity` anyway; this makes it true whatever the caller sent.
"""

from __future__ import annotations

import hmac
import json
from typing import Any

from python_multipart.multipart import parse_options_header
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException
from starlette.formparsers import MultiPartException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from cmp.api.middleware.request_context import safe_path
from cmp.core.config import settings
from cmp.core.context import current_context
from cmp.core.logging import get_logger
from cmp.infrastructure.dkms.fields import PREFIX
from cmp.infrastructure.dkms.rows import unseal_strings

log = get_logger("cmp.api")

#: The header the collector presents. Lower-case: ASGI header names are.
RELAY_KEY_HEADER = b"x-cmp-relay-key"

#: The two bodies Starlette reads as a form, as `Request.form()` decides it.
_FORM_TYPES = (b"multipart/form-data", b"application/x-www-form-urlencoded")

#: Same words as the collector's refusal: the visitor sees one message.
_REFUSED = "This request contains a value that can't be accepted."


class RelayOpenSealedMiddleware:
    """Open `SE::` values in the JSON reply to a request the relay vouches for.

    Off when `RELAY_INGRESS_KEY` is empty. A plain ASGI middleware, because a
    download must pass through as a stream and `BaseHTTPMiddleware` would hand
    it over as one.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        expected = settings.relay_ingress_key.get_secret_value().encode()
        presented = _header(scope, RELAY_KEY_HEADER)
        if presented is not None:
            # Stripped whatever happens next: the routes never see the key.
            scope = _without(scope, {RELAY_KEY_HEADER})
        if not expected or presented is None:
            await self.app(scope, receive, send)
            return
        if not hmac.compare_digest(presented, expected):
            log.warning(
                "relay.key_refused",
                method=scope.get("method"),
                endpoint=safe_path(str(scope.get("path", ""))),
            )
            await self.app(scope, receive, send)
            return

        # The reply has to come back up as JSON this can read: GZip, below,
        # compresses only for a request that says it accepts it. And the
        # session check below needs to know where the request came from; the
        # state is copied, so nothing outside this sees the mark.
        scope = _without(scope, {b"accept-encoding"})
        scope = {**scope, "state": {**scope.get("state", {}), "relayed": True}}
        opener = _Opener(send).send

        first: Message | None = None
        where = _sealed_in_head(scope)
        if where is None:
            try:
                first = await _read_body(receive)
            except Exception as exc:
                # Raised by what sits outside - BodyLimit's 413 - while the body
                # came in. The app meets it on its own first read, as it would
                # have without this; none of the body reaches anything.
                await self.app(scope, _raising(exc, receive), opener)
                return
            if first["type"] == "http.request":
                try:
                    where = await _sealed_in_body(scope, first["body"])
                except RecursionError:
                    # Nested past what can be read: not proven clean, so not let in.
                    where = "body"
            # Anything else is the client gone mid-body: the app learns that
            # from its own first read, and nothing of the body is used.

        if where is not None:
            log.warning(
                "relay.sealed_value_refused",
                method=scope.get("method"),
                endpoint=safe_path(str(scope.get("path", ""))),
                where=where,
            )
            await _refusal(scope)(scope, receive, send)
            return
        assert first is not None  # read whenever nothing was found in the head
        await self.app(scope, _replaying(first, receive), opener)


class _Opener:
    """The `send` a vouched-for request's reply goes out through.

    Decides on `http.response.start`: anything but uncompressed JSON is
    forwarded message by message as it comes; JSON is held until its last
    body message, then opened and sent as one.
    """

    def __init__(self, send: Send) -> None:
        self._send = send
        self._start: Message | None = None
        self._chunks: list[bytes] = []
        self._buffering = False

    async def send(self, message: Message) -> None:
        kind = message["type"]
        if kind == "http.response.start":
            if _is_plain_json(message):
                self._start = message
                self._buffering = True
                return
            await self._send(message)
            return
        if kind != "http.response.body" or not self._buffering:
            await self._send(message)
            return

        self._chunks.append(message.get("body", b""))
        if message.get("more_body", False):
            return
        self._buffering = False
        start = self._start
        assert start is not None  # set with _buffering
        original = b"".join(self._chunks)
        self._chunks = []
        body = await _opened(original)
        if body is not original:
            start = {**start, "headers": _with_length(start.get("headers", []), len(body))}
        await self._send(start)
        await self._send({"type": "http.response.body", "body": body, "more_body": False})


async def _opened(body: bytes) -> bytes:
    """The body with every sealed string opened, or `body` itself if there is
    nothing to open or opening fails."""
    sealed: list[str] = []
    try:
        document = json.loads(body)
        _collect(document, sealed)
    except (ValueError, RecursionError):
        # Not JSON after all, a HEAD reply's empty body, or nested past what
        # can be walked: as it came.
        return body
    if not sealed:
        return body
    try:
        opened = await unseal_strings(sealed)
    except Exception as exc:
        # DkmsUnavailable, a refused batch, anything: the reply goes out as
        # stored and the page shows ciphertext. Neither the values nor the
        # error's text reach the log.
        log.warning("relay.open_failed", error=type(exc).__name__, values=len(sealed))
        return body
    if not opened:
        return body
    return json.dumps(
        _replace(document, opened), ensure_ascii=False, separators=(",", ":")
    ).encode()


def _collect(node: Any, into: list[str]) -> None:
    """Every sealed string in a decoded JSON document, at any depth."""
    if isinstance(node, str):
        if node.startswith(PREFIX):
            into.append(node)
    elif isinstance(node, dict):
        for value in node.values():
            _collect(value, into)
    elif isinstance(node, list):
        for item in node:
            _collect(item, into)


def _replace(node: Any, opened: dict[str, Any]) -> Any:
    """The document with each sealed string swapped for its opened value; a
    value the key service could not open stays as it was."""
    if isinstance(node, str):
        return opened.get(node, node) if node.startswith(PREFIX) else node
    if isinstance(node, dict):
        return {key: _replace(value, opened) for key, value in node.items()}
    if isinstance(node, list):
        return [_replace(item, opened) for item in node]
    return node


# ------------------------------------------------------------ what comes in


def _sealed_in_head(scope: Scope) -> str | None:
    """Where the prefix is in the path, the query or a header, if it is.

    The query as Starlette decodes it for a route. Every header but the
    cookie: a header a route never reads today (Accept-Language) is one a
    route may read tomorrow, and the User-Agent is already shown back.
    """
    if PREFIX in str(scope.get("path", "")):
        return "path"
    for name, value in Request(scope).query_params.multi_items():
        if PREFIX in name or PREFIX in value:
            return "query"
    for key, raw in scope.get("headers", []):
        if bytes(key).lower() == b"cookie":
            continue
        if PREFIX in bytes(raw).decode("latin-1"):
            return "header"
    return None


async def _sealed_in_body(scope: Scope, body: bytes) -> str | None:
    """Where the prefix is in the body, read the way a route will read it.

    A form through `Request.form()` - field names, text values, file names -
    with the limits FastAPI parses with; a form that does not parse is let
    through, and the route answers with the same parser's error. The bytes of
    a file are not searched: a scanned letter may well hold the four
    characters, and no route reads them as text. Any other body as JSON when
    it is JSON, every key and string, and as text when it is not. Raises
    `RecursionError` for JSON nested past what can be read.
    """
    if not body:
        return None
    content_type, _ = parse_options_header(Request(scope).headers.get("content-type"))
    if content_type in _FORM_TYPES:
        return "body" if await _form_carries(scope, body) else None
    try:
        document = json.loads(body)
    except ValueError:
        text = body.decode("utf-8", errors="replace"), body.decode("latin-1")
        return "body" if any(PREFIX in t for t in text) else None
    return "body" if _json_carries(document) else None


async def _form_carries(scope: Scope, body: bytes) -> bool:
    """Whether a field name, a text value or a file's name holds the prefix.

    For a file, every one of its part's headers too, as the parser hands them
    to a route: `UploadFile.content_type` is read from them and stored, and
    the raw Content-Disposition keeps a `filename*` the parser itself ignores.
    """
    request = Request(scope, _replaying(_whole(body), _gone))
    try:
        form = await request.form()
    except (MultiPartException, HTTPException, ValueError):
        # Malformed: the route's own `request.form()` raises the same over the
        # same bytes, so no value of it is ever read.
        return False
    try:
        for name, value in form.multi_items():
            if PREFIX in name:
                return True
            if isinstance(value, UploadFile):
                if value.filename is not None and PREFIX in value.filename:
                    return True
                if any(PREFIX in header for header in value.headers.values()):
                    return True
            elif PREFIX in value:
                return True
        return False
    finally:
        await form.close()


def _json_carries(document: Any) -> bool:
    """Whether any key or string in a decoded JSON document holds the prefix.

    Walked with a stack, not by recursion: depth is no way past it.
    """
    stack = [document]
    while stack:
        node = stack.pop()
        if isinstance(node, str):
            if PREFIX in node:
                return True
        elif isinstance(node, dict):
            for key, value in node.items():
                if PREFIX in key:
                    return True
                stack.append(value)
        elif isinstance(node, list):
            stack.extend(node)
    return False


async def _read_body(receive: Receive) -> Message:
    """The whole body as one `http.request` message, or the disconnect that
    cut it short."""
    chunks: list[bytes] = []
    while True:
        message = await receive()
        if message["type"] != "http.request":
            return message
        chunks.append(message.get("body", b""))
        if not message.get("more_body", False):
            return _whole(b"".join(chunks))


def _whole(body: bytes) -> Message:
    return {"type": "http.request", "body": body, "more_body": False}


def _replaying(first: Message, receive: Receive) -> Receive:
    """`first`, then whatever `receive` has next - a disconnect, normally."""
    pending: list[Message] = [first]

    async def replay() -> Message:
        if pending:
            return pending.pop()
        return await receive()

    return replay


def _raising(exc: Exception, receive: Receive) -> Receive:
    """A `receive` whose first call raises what reading the body raised."""
    raised = False

    async def replay() -> Message:
        nonlocal raised
        if not raised:
            raised = True
            raise exc
        return await receive()

    return replay


async def _gone() -> Message:
    """After the replayed body, for the check's own reading: nothing more."""
    return {"type": "http.disconnect"}


def _refusal(scope: Scope) -> JSONResponse:
    request_id = scope.get("state", {}).get("request_id") or current_context().request_id
    content: dict[str, Any] = {
        "error": {"code": "sealed_value_refused", "message": _REFUSED, "request_id": request_id}
    }
    return JSONResponse(content, status_code=422)


# ----------------------------------------------------------------- helpers


def _is_plain_json(start: Message) -> bool:
    """`application/json`, with no content coding applied."""
    content_type = b""
    encoding = b""
    for key, value in start.get("headers", []):
        name = bytes(key).lower()
        if name == b"content-type":
            content_type = bytes(value)
        elif name == b"content-encoding":
            encoding = bytes(value)
    media_type = content_type.split(b";", 1)[0].strip().lower()
    return media_type == b"application/json" and encoding.strip().lower() in (b"", b"identity")


def _header(scope: Scope, name: bytes) -> bytes | None:
    for key, value in scope.get("headers", []):
        if bytes(key).lower() == name:
            return bytes(value)
    return None


def _without(scope: Scope, names: set[bytes]) -> Scope:
    """A copy of the scope with these request headers removed. A copy, so the
    middleware outside this one keeps seeing the request it was given."""
    headers = [(k, v) for k, v in scope.get("headers", []) if bytes(k).lower() not in names]
    return {**scope, "headers": headers}


def _with_length(headers: Any, length: int) -> list[tuple[bytes, bytes]]:
    kept = [(bytes(k), bytes(v)) for k, v in headers if bytes(k).lower() != b"content-length"]
    kept.append((b"content-length", str(length).encode("latin-1")))
    return kept
