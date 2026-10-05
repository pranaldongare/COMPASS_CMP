"""The body limit counts the bytes that arrive, not the bytes declared (review SEC-4).

The middleware read `Content-Length` and nothing else. A chunked request
carries none, so a streamed body of any size went straight through to the
route that parsed it - the denial of service the limit exists to prevent,
reproduced by the review with an isolated streamed request. The bytes are now
counted as the application reads them.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI, Request, UploadFile

from cmp.api import errors
from cmp.api.middleware.body_limit import BodyLimitMiddleware
from cmp.core.config import settings

LIMIT = 1024


def _app() -> FastAPI:
    app = FastAPI()
    errors.install(app)
    app.add_middleware(BodyLimitMiddleware)

    @app.post("/json")
    async def take_json(body: dict[str, Any]) -> dict[str, int]:
        return {"keys": len(body)}

    @app.post("/raw")
    async def take_raw(request: Request) -> dict[str, int]:
        return {"bytes": len(await request.body())}

    @app.post("/file")
    async def take_file(file: UploadFile) -> dict[str, int]:
        return {"bytes": len(await file.read())}

    return app


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[httpx.AsyncClient]:
    monkeypatch.setattr(settings, "max_upload_bytes", LIMIT)
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def _chunks(total: int, size: int = 256) -> AsyncIterator[bytes]:
    sent = 0
    while sent < total:
        piece = min(size, total - sent)
        yield b"x" * piece
        sent += piece


@pytest.mark.parametrize("path", ["/json", "/raw"])
async def test_a_streamed_body_over_the_limit_is_refused(
    client: httpx.AsyncClient, path: str
) -> None:
    response = await client.post(path, content=_chunks(LIMIT * 4))
    assert response.status_code == 413, response.text
    assert response.json()["error"]["code"] == "payload_too_large"


async def test_a_streamed_upload_over_the_limit_is_refused(client: httpx.AsyncClient) -> None:
    boundary = "cmpboundary"

    async def multipart() -> AsyncIterator[bytes]:
        yield (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="a.bin"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode()
        async for chunk in _chunks(LIMIT * 4):
            yield chunk
        yield f"\r\n--{boundary}--\r\n".encode()

    response = await client.post(
        "/file",
        content=multipart(),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    assert response.status_code == 413, response.text


async def test_a_declared_length_over_the_limit_is_refused_unread(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post("/raw", content=b"x" * (LIMIT + 1))
    assert response.status_code == 413


async def test_a_streamed_body_within_the_limit_passes(client: httpx.AsyncClient) -> None:
    response = await client.post("/raw", content=_chunks(LIMIT - 10))
    assert response.status_code == 200
    assert response.json() == {"bytes": LIMIT - 10}


async def test_a_body_that_understates_its_length_is_still_counted(
    client: httpx.AsyncClient,
) -> None:
    """A client can declare less than it sends; the server counts what came."""
    response = await client.post(
        "/raw", content=_chunks(LIMIT * 2), headers={"Content-Length": "10"}
    )
    assert response.status_code in (400, 413)
    assert response.status_code != 200
