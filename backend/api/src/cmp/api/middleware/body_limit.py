"""Refuse an oversized body before anything parses it.

Checked against `Content-Length` first, which is free, and then against the
bytes actually read — because a client can lie about the former, and a chunked
request has none at all.

This sits above the route so an oversized payload never reaches a Pydantic model
or a file handler. Parsing a 2 GB body to discover it is too large is the
denial-of-service this prevents.

Until 2026-10-05 only the first half was true: the middleware read the header
and nothing else, so a streamed body of any size went through (review SEC-4).
It is a plain ASGI middleware now, because counting the bytes means wrapping
`receive`, and `BaseHTTPMiddleware` hides it.
"""

from __future__ import annotations

from typing import Any

from fastapi import status
from fastapi.responses import ORJSONResponse
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from cmp.core.config import settings
from cmp.core.context import current_context


class BodyTooLarge(HTTPException):
    """Raised from inside `receive` once the bytes read pass the limit.

    An `HTTPException` because FastAPI re-raises those from body parsing
    untouched, where any other exception becomes "There was an error parsing
    the body" - a 400 that would hide what happened. The API's handler for
    these answers 413 `payload_too_large`.
    """

    def __init__(self) -> None:
        super().__init__(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, _message())


class BodyLimitMiddleware:
    """Refuse oversized bodies before they are read into memory.

    Enforced here, in the application, and not left to whatever sits in front
    of it. A deployment may put a proxy with its own cap ahead of this; a limit
    that exists only in the proxy is a limit that disappears the moment someone
    bypasses the proxy, and in development nothing sits in front at all.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        limit = settings.max_upload_bytes
        declared = _header(scope, b"content-length")
        if declared is not None:
            try:
                if int(declared) > limit:
                    await _too_large()(scope, receive, send)
                    return
            except ValueError:
                await _malformed()(scope, receive, send)
                return

        received = 0

        async def counted() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise BodyTooLarge()
            return message

        started = False

        async def tracked(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, counted, tracked)
        except BodyTooLarge:
            # Normally answered by the API's handler before it gets here; this
            # is for a route outside it, or a body read after the reply began.
            if started:
                raise
            await _too_large()(scope, receive, send)


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            return bytes(value).decode("latin-1")
    return None


def _message() -> str:
    return f"Request body exceeds {settings.max_upload_bytes // (1024 * 1024)} MB"


def _too_large() -> ORJSONResponse:
    return _error(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "payload_too_large", _message())


def _malformed() -> ORJSONResponse:
    return _error(status.HTTP_400_BAD_REQUEST, "bad_request", "Malformed Content-Length")


def _error(status_code: int, code: str, message: str) -> ORJSONResponse:
    content: dict[str, Any] = {
        "error": {"code": code, "message": message, "request_id": current_context().request_id}
    }
    return ORJSONResponse(status_code=status_code, content=content)
