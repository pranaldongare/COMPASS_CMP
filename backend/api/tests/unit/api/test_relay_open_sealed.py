"""The API opens sealed values only for a reply going back out through the relay.

The data principal's portal on AWS cannot reach the key service, so the
inside relay collector presents `RELAY_INGRESS_KEY` and the API opens the
`SE::` values in that one JSON reply (ADR 0016, relay amendment, ADR 0032).
These pin the narrowness of that: only with the right key, only JSON, never
the key itself to a route, and a key-service failure is today's failure
(ciphertext shown), not a broken reply.

And the other half: a vouched-for request that carries a sealed value in
anything a route reads is refused before any route runs, read with the API's
own parsers - otherwise whatever a route repeats back (a file name, a
User-Agent, a field named in a validation error) is opened on the way out, an
oracle for every value in the database.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated, Any

import httpx
import pytest
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import SecretStr

from cmp.api.middleware import relay_open_sealed
from cmp.api.middleware.relay_open_sealed import RelayOpenSealedMiddleware
from cmp.core.config import Settings, settings
from cmp.infrastructure.dkms.client import DkmsUnavailable

KEY = "k" * 40
NAME = "SE::name-envelope"
EMAIL = "SE::email-envelope"
OPENED = {NAME: "Asha Rao", EMAIL: "asha@example.org"}

#: Large enough that GZip (minimum_size=1024) compresses it when allowed to.
PADDING = "x" * 2048


def _app() -> FastAPI:
    app = FastAPI()
    seen: dict[str, Any] = {}
    app.state.seen = seen

    @app.get("/me")
    async def me(request: Request) -> dict[str, Any]:
        seen["headers"] = dict(request.headers)
        return {
            "name": NAME,
            "contacts": [{"email": EMAIL, "verified": True}, {"email": None}],
            "nested": {"deeper": [[NAME]], "count": 3, "plain": "SEnot-sealed"},
            "ünïcode": "महाराष्ट्र",
            "padding": PADDING,
        }

    @app.get("/plain")
    async def plain() -> dict[str, str]:
        return {"name": "nobody sealed"}

    @app.get("/pdf")
    async def pdf() -> StreamingResponse:
        async def chunks() -> AsyncIterator[bytes]:
            yield b"%PDF-1.7 " + NAME.encode()
            yield b" more"

        return StreamingResponse(chunks(), media_type="application/pdf")

    @app.get("/text")
    async def text() -> Response:
        return Response(f'{{"name":"{NAME}"}}', media_type="text/plain")

    @app.get("/streamed-json")
    async def streamed_json() -> StreamingResponse:
        async def chunks() -> AsyncIterator[bytes]:
            yield b'{"name":"'
            yield NAME.encode()
            yield b'"}'

        return StreamingResponse(chunks(), media_type="application/json")

    @app.get("/error")
    async def error() -> JSONResponse:
        return JSONResponse({"error": {"code": "x", "message": NAME}}, status_code=409)

    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(RelayOpenSealedMiddleware)
    return app


class Unseal:
    """Stands in for `unseal_strings`; records each call."""

    def __init__(self, fail: Exception | None = None) -> None:
        self.calls: list[list[str]] = []
        self.fail = fail

    async def __call__(self, values: list[Any]) -> dict[str, Any]:
        self.calls.append(list(values))
        if self.fail is not None:
            raise self.fail
        return {v: OPENED[v] for v in values if v in OPENED}


@pytest.fixture
def unseal(monkeypatch: pytest.MonkeyPatch) -> Unseal:
    fake = Unseal()
    monkeypatch.setattr(relay_open_sealed, "unseal_strings", fake)
    return fake


@pytest.fixture
def keyed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "relay_ingress_key", SecretStr(KEY))


@pytest.fixture
async def app_client() -> AsyncIterator[tuple[FastAPI, httpx.AsyncClient]]:
    app = _app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield app, http


RELAYED = {"X-CMP-Relay-Key": KEY, "Accept-Encoding": "gzip"}


@pytest.mark.usefixtures("keyed")
class TestWithTheKey:
    async def test_every_sealed_value_is_opened_at_any_depth_in_one_call(
        self, app_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal
    ) -> None:
        _, http = app_client
        response = await http.get("/me", headers=RELAYED)

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Asha Rao"
        assert body["contacts"] == [
            {"email": "asha@example.org", "verified": True},
            {"email": None},
        ]
        assert body["nested"] == {"deeper": [["Asha Rao"]], "count": 3, "plain": "SEnot-sealed"}
        assert body["ünïcode"] == "महाराष्ट्र"
        assert len(unseal.calls) == 1
        assert sorted(set(unseal.calls[0])) == sorted([NAME, EMAIL])

    async def test_content_length_is_the_opened_body_and_nothing_is_compressed(
        self, app_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal
    ) -> None:
        app, http = app_client
        response = await http.get("/me", headers=RELAYED)

        assert "content-encoding" not in response.headers
        assert int(response.headers["content-length"]) == len(response.content)
        # Re-serialised compactly, with the text as text, not \\u escapes.
        assert (
            response.content
            == json.dumps(response.json(), ensure_ascii=False, separators=(",", ":")).encode()
        )
        # The route was never told the caller accepts gzip, nor given the key.
        seen = app.state.seen["headers"]
        assert "accept-encoding" not in seen
        assert "x-cmp-relay-key" not in seen

    async def test_a_streamed_json_reply_is_gathered_and_opened(
        self, app_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal
    ) -> None:
        _, http = app_client
        response = await http.get("/streamed-json", headers=RELAYED)

        assert response.json() == {"name": "Asha Rao"}
        assert int(response.headers["content-length"]) == len(response.content)

    async def test_an_error_reply_is_opened_too_and_keeps_its_status(
        self, app_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal
    ) -> None:
        _, http = app_client
        response = await http.get("/error", headers=RELAYED)

        assert response.status_code == 409
        assert response.json()["error"]["message"] == "Asha Rao"

    async def test_json_with_nothing_sealed_is_sent_as_it_came(
        self, app_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal
    ) -> None:
        _, http = app_client
        response = await http.get("/plain", headers=RELAYED)

        assert response.content == b'{"name":"nobody sealed"}'
        assert int(response.headers["content-length"]) == len(response.content)
        assert unseal.calls == []

    @pytest.mark.parametrize("path", ["/pdf", "/text"])
    async def test_anything_but_json_is_not_opened(
        self, app_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal, path: str
    ) -> None:
        _, http = app_client
        response = await http.get(path, headers=RELAYED)

        assert NAME.encode() in response.content
        assert unseal.calls == []

    async def test_a_download_is_forwarded_as_it_streams_not_buffered(self, unseal: Unseal) -> None:
        """The first chunk reaches the server before the route sends the second.

        The route will not send its second chunk until the first has gone out;
        a middleware that buffered would hold the first, and the route would
        give up waiting.
        """
        first_out = asyncio.Event()
        app = FastAPI()

        @app.get("/pdf")
        async def pdf() -> StreamingResponse:
            async def chunks() -> AsyncIterator[bytes]:
                yield b"%PDF-1.7 " + NAME.encode()
                await asyncio.wait_for(first_out.wait(), timeout=2)
                yield b" more"

            return StreamingResponse(chunks(), media_type="application/pdf")

        app.add_middleware(RelayOpenSealedMiddleware)

        sent: list[dict[str, Any]] = []
        requested = False
        never = asyncio.Event()

        async def receive() -> dict[str, Any]:
            nonlocal requested
            if not requested:
                requested = True
                return {"type": "http.request", "body": b"", "more_body": False}
            await never.wait()  # no disconnect; cancelled when the reply ends
            return {"type": "http.disconnect"}

        async def send(message: Any) -> None:
            sent.append(dict(message))
            if message["type"] == "http.response.body" and message.get("body"):
                first_out.set()

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/pdf",
            "raw_path": b"/pdf",
            "root_path": "",
            "query_string": b"",
            "headers": [(b"host", b"test"), (b"x-cmp-relay-key", KEY.encode())],
            "client": ("127.0.0.1", 1),
            "server": ("test", 80),
        }
        await asyncio.wait_for(app(scope, receive, send), timeout=5)

        bodies = [m.get("body", b"") for m in sent if m["type"] == "http.response.body"]
        assert bodies[0] == b"%PDF-1.7 " + NAME.encode()
        assert b" more" in bodies
        assert unseal.calls == []

    async def test_when_the_key_service_fails_the_reply_goes_out_as_stored(
        self, app_client: tuple[FastAPI, httpx.AsyncClient], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        failing = Unseal(fail=DkmsUnavailable("down"))
        monkeypatch.setattr(relay_open_sealed, "unseal_strings", failing)
        _, http = app_client
        response = await http.get("/me", headers={"X-CMP-Relay-Key": KEY})

        assert response.status_code == 200
        assert response.json()["name"] == NAME
        assert int(response.headers["content-length"]) == len(response.content)
        assert len(failing.calls) == 1

    async def test_any_failure_at_all_is_the_same(
        self, app_client: tuple[FastAPI, httpx.AsyncClient], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(relay_open_sealed, "unseal_strings", Unseal(fail=RuntimeError("x")))
        _, http = app_client
        response = await http.get("/me", headers={"X-CMP-Relay-Key": KEY})

        assert response.json()["contacts"][0]["email"] == EMAIL


@pytest.mark.usefixtures("keyed")
class TestWithAWrongKey:
    async def test_nothing_is_opened_and_the_route_never_sees_the_header(
        self, app_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal
    ) -> None:
        app, http = app_client
        response = await http.get(
            "/me", headers={"X-CMP-Relay-Key": "w" * 40, "Accept-Encoding": "gzip"}
        )

        assert unseal.calls == []
        # Compressed as usual: Accept-Encoding is left alone without the key.
        assert response.headers.get("content-encoding") == "gzip"
        assert response.json()["name"] == NAME
        seen = app.state.seen["headers"]
        assert "x-cmp-relay-key" not in seen
        assert seen.get("accept-encoding") == "gzip"

    async def test_no_header_at_all_is_an_ordinary_request(
        self, app_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal
    ) -> None:
        app, http = app_client
        response = await http.get("/me", headers={"Accept-Encoding": "gzip"})

        assert response.json()["name"] == NAME
        assert response.headers.get("content-encoding") == "gzip"
        assert app.state.seen["headers"].get("accept-encoding") == "gzip"
        assert unseal.calls == []


class TestWithNoKeyConfigured:
    async def test_the_middleware_passes_everything_through(
        self,
        app_client: tuple[FastAPI, httpx.AsyncClient],
        unseal: Unseal,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(settings, "relay_ingress_key", SecretStr(""))
        app, http = app_client
        # Even a request presenting what would be the key gets nothing opened.
        response = await http.get("/me", headers={"X-CMP-Relay-Key": "", "Accept-Encoding": "gzip"})
        assert response.json()["name"] == NAME
        assert response.headers.get("content-encoding") == "gzip"

        response = await http.get("/me", headers={"X-CMP-Relay-Key": KEY})
        assert response.json()["name"] == NAME
        assert unseal.calls == []
        # The header is still kept from the route.
        assert "x-cmp-relay-key" not in app.state.seen["headers"]


# ------------------------------------------------------- no sealed value in

#: Someone else's ciphertext, as an attacker holding a leaked backup has it.
SEALED = "SE::REtBAQ-victim-ciphertext"
BOUNDARY = "relay-test-boundary"
MULTIPART = f"multipart/form-data; boundary={BOUNDARY}"
URLENCODED = "application/x-www-form-urlencoded"

Part = tuple[list[str], bytes]


def _multipart(*parts: Part) -> bytes:
    """A multipart body built by hand, so a test sends exactly the bytes it means."""
    out = b""
    for headers, content in parts:
        out += f"--{BOUNDARY}\r\n".encode()
        out += b"".join(h.encode("latin-1") + b"\r\n" for h in headers)
        out += b"\r\n" + content + b"\r\n"
    return out + f"--{BOUNDARY}--\r\n".encode()


def _field(name: str, value: bytes, *extra: str) -> Part:
    return [f'Content-Disposition: form-data; name="{name}"', *extra], value


def _file(disposition: str, content: bytes, content_type: str = "text/plain") -> Part:
    return [f"Content-Disposition: form-data; {disposition}", f"Content-Type: {content_type}"], (
        content
    )


def _utf16(text: str) -> str:
    """`text` as UTF-16-LE bytes, carried in a header that is sent as latin-1."""
    return text.encode("utf-16-le").decode("latin-1")


def _input_app() -> FastAPI:
    """Routes that read their input the ways the API's routes do, and record
    what they were given."""
    app = FastAPI()
    seen: dict[str, Any] = {}
    app.state.seen = seen

    @app.api_route("/echo", methods=["GET", "POST"])
    async def echo(request: Request) -> dict[str, Any]:
        seen["body"] = await request.body()
        seen["query"] = request.query_params.multi_items()
        seen["headers"] = dict(request.headers)
        seen["relayed"] = getattr(request.state, "relayed", False)
        items: list[Any] = []
        async with request.form() as form:
            for name, value in form.multi_items():
                if isinstance(value, str):
                    items.append((name, value))
                else:
                    items.append((name, value.filename, await value.read()))
        seen["form"] = items
        return {"ok": True}

    @app.post("/attachments")
    async def attach(
        file: Annotated[UploadFile, File()], note: Annotated[str, Form()] = ""
    ) -> dict[str, Any]:
        # As POST /me/requests/{request}/attachments does: the name comes back.
        seen["file"] = await file.read()
        return {"file_name": file.filename, "note": note}

    app.add_middleware(RelayOpenSealedMiddleware)
    return app


@pytest.fixture
async def input_client() -> AsyncIterator[tuple[FastAPI, httpx.AsyncClient]]:
    app = _input_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield app, http


def _refused(response: httpx.Response) -> bool:
    return (
        response.status_code == 422 and response.json()["error"]["code"] == "sealed_value_refused"
    )


@pytest.mark.usefixtures("keyed")
class TestASealedValueComingInIsRefused:
    """Wherever a route could read it, and before any route runs."""

    @pytest.mark.parametrize(
        "query",
        [
            f"q={SEALED}",
            "q=SE%3A%3AREtBAQ",  # percent-encoded: the route reads it decoded
            "q=x+SE::REtBAQ",  # anywhere in the value, not only at its start
            "SE%3A%3AREtBAQ=1",  # a parameter's name
            "a=1&b=2&c=" + SEALED,
        ],
    )
    async def test_in_the_query(
        self, input_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal, query: str
    ) -> None:
        app, http = input_client
        response = await http.get(f"/echo?{query}", headers={"X-CMP-Relay-Key": KEY})

        assert _refused(response)
        assert app.state.seen == {}  # no route ran
        assert unseal.calls == []

    @pytest.mark.parametrize(
        "header", ["User-Agent", "Accept-Language", "X-Request-ID", "X-CSRF-Token", "X-Anything"]
    )
    async def test_in_a_header(
        self, input_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal, header: str
    ) -> None:
        """The User-Agent is stored with a session and shown back by GET
        /auth/sessions; every other header is refused alike, for the route
        that reads one tomorrow."""
        app, http = input_client
        response = await http.get("/echo", headers={"X-CMP-Relay-Key": KEY, header: SEALED})

        assert _refused(response)
        assert app.state.seen == {}

    async def test_the_cookie_is_the_one_header_not_searched(
        self, input_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal
    ) -> None:
        app, http = input_client
        response = await http.get(
            "/echo", headers={"X-CMP-Relay-Key": KEY, "Cookie": f"other={SEALED}"}
        )

        assert response.status_code == 200
        assert app.state.seen["relayed"] is True

    async def test_in_the_path(
        self, input_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal
    ) -> None:
        _, http = input_client
        response = await http.get("/c/SE::REtBAQ/notice", headers={"X-CMP-Relay-Key": KEY})

        assert _refused(response)

    @pytest.mark.parametrize(
        "body",
        [
            json.dumps({"full_name": SEALED}),
            json.dumps({"nested": [{"deeper": ["ok", SEALED]}]}),
            json.dumps({SEALED: 1, "contact": "a@b.co"}),  # a key: named back in a 422
            # Escaped: no "SE::" in the bytes, one in what the route is given.
            '{"full_name": "\\u0053\\u0045\\u003a\\u003aREtBAQ"}',
            json.dumps(SEALED),
        ],
    )
    async def test_in_a_json_body(
        self, input_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal, body: str
    ) -> None:
        app, http = input_client
        response = await http.post(
            "/echo",
            content=body.encode(),
            headers={"X-CMP-Relay-Key": KEY, "Content-Type": "application/json"},
        )

        assert _refused(response)
        assert app.state.seen == {}

    async def test_json_nested_past_what_can_be_read_is_refused(
        self, input_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal
    ) -> None:
        """`json.loads` raises RecursionError on this. Not proven clean, so not let in."""
        app, http = input_client
        body = b"[" * 100_000 + b"]" * 100_000
        response = await http.post(
            "/echo",
            content=body,
            headers={"X-CMP-Relay-Key": KEY, "Content-Type": "application/json"},
        )

        assert _refused(response)
        assert app.state.seen == {}

    async def test_depth_is_no_way_past_the_walk(
        self, input_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal
    ) -> None:
        """Deeper than Python's recursion goes, yet parseable: the key is found."""
        _, http = input_client
        deep = "[" * 3000 + "]" * 3000
        body = '{"x":' + deep + ',"\\u0053E::REtBAQ":1}'
        assert "SE::REtBAQ" in json.loads(body)  # what a route would be given
        response = await http.post(
            "/echo",
            content=body.encode(),
            headers={"X-CMP-Relay-Key": KEY, "Content-Type": "application/json"},
        )

        assert _refused(response)

    @pytest.mark.parametrize("content_type", ["text/plain", None, "application/octet-stream"])
    async def test_in_any_other_body_as_text(
        self,
        input_client: tuple[FastAPI, httpx.AsyncClient],
        unseal: Unseal,
        content_type: str | None,
    ) -> None:
        _, http = input_client
        headers = {"X-CMP-Relay-Key": KEY}
        if content_type:
            headers["Content-Type"] = content_type
        response = await http.post(
            "/echo", content=b"not json: " + SEALED.encode() + b"\xff", headers=headers
        )

        assert _refused(response)

    @pytest.mark.parametrize(
        "body", ["note=SE%3A%3AREtBAQ", f"note={SEALED}", "SE%3A%3AREtBAQ=x", "a=1&note=x+SE::y"]
    )
    async def test_in_a_urlencoded_form(
        self, input_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal, body: str
    ) -> None:
        app, http = input_client
        response = await http.post(
            "/echo",
            content=body.encode(),
            headers={"X-CMP-Relay-Key": KEY, "Content-Type": URLENCODED},
        )

        assert _refused(response)
        assert app.state.seen == {}

    @pytest.mark.parametrize(
        ("parts", "content_type"),
        [
            pytest.param([_field("body", SEALED.encode())], MULTIPART, id="text field"),
            pytest.param([_field(SEALED, b"hello")], MULTIPART, id="field name"),
            pytest.param(
                [_file(f'name="file"; filename="{SEALED}"', b"%PDF-1.7")],
                MULTIPART,
                id="filename",
            ),
            pytest.param(
                [_file(f'name="file"; filename="a.pdf"; filename*=utf-8\'\'{SEALED}', b"x")],
                MULTIPART,
                id="filename and filename*",
            ),
            pytest.param(
                [_file('name="file"; filename="a.pdf"', b"x", f'application/pdf; x="{SEALED}"')],
                MULTIPART,
                id="a file's content type",
            ),
            # The email parser decodes this into nothing; Starlette ignores
            # Content-Transfer-Encoding and hands the route the raw value.
            pytest.param(
                [_field("body", SEALED.encode(), "Content-Transfer-Encoding: base64")],
                MULTIPART,
                id="content-transfer-encoding base64",
            ),
            # A part that names itself in its Content-Type looks like a file
            # to the email parser and is a text field to Starlette.
            pytest.param(
                [_field("body", SEALED.encode(), 'Content-Type: text/plain; name="x.txt"')],
                MULTIPART,
                id="content-type name",
            ),
            # Starlette decodes names, values and file names with the outer
            # charset: no "SE::" in the bytes, one in what the route is given.
            pytest.param(
                [_file(f'name="file"; filename="{_utf16(SEALED)}"', b"x")],
                MULTIPART + "; charset=utf-16-le",
                id="filename in the outer charset utf-16-le",
            ),
            pytest.param(
                [_field("body", SEALED.encode("utf-16-le"))],
                MULTIPART + "; charset=utf-16-le",
                id="outer charset utf-16-le",
            ),
            pytest.param(
                [
                    _field("ok", b"fine"),
                    _file('name="file"; filename="a.txt"', b"x"),
                    _field("late", SEALED.encode()),
                ],
                MULTIPART,
                id="the last of several parts",
            ),
        ],
    )
    async def test_in_a_multipart_form(
        self,
        input_client: tuple[FastAPI, httpx.AsyncClient],
        unseal: Unseal,
        parts: list[Part],
        content_type: str,
    ) -> None:
        app, http = input_client
        response = await http.post(
            "/echo",
            content=_multipart(*parts),
            headers={"X-CMP-Relay-Key": KEY, "Content-Type": content_type},
        )

        assert _refused(response)
        assert app.state.seen == {}

    async def test_a_filename_star_the_parser_ignores_never_reaches_a_route(
        self, input_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal
    ) -> None:
        """A part named only by `filename*`: python-multipart drops the
        extended form (RFC 7578 section 4.2), so the route gets a text field
        holding the content and never the name. Refused instead, should a
        later parser read it: the check reads with the routes' own parser."""
        app, http = input_client
        body = _multipart(_file(f"name=\"file\"; filename*=utf-8''{SEALED}", b"hello"))
        response = await http.post(
            "/echo", content=body, headers={"X-CMP-Relay-Key": KEY, "Content-Type": MULTIPART}
        )

        if response.status_code == 200:
            assert app.state.seen["form"] == [("file", "hello")]
        else:
            assert _refused(response)

    async def test_the_reflected_file_name_oracle_is_closed(
        self,
        input_client: tuple[FastAPI, httpx.AsyncClient],
        unseal: Unseal,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The attack itself: upload anything named with someone else's
        ciphertext and read the name back opened. Refused; nothing opened."""
        monkeypatch.setitem(OPENED, SEALED, "Victim Plaintext Name")
        app, http = input_client
        body = _multipart(_file(f'name="file"; filename="{SEALED}"', b"letter"))
        response = await http.post(
            "/attachments",
            content=body,
            headers={"X-CMP-Relay-Key": KEY, "Content-Type": MULTIPART},
        )

        assert _refused(response)
        assert "Victim" not in response.text
        assert unseal.calls == []
        assert "file" not in app.state.seen

    async def test_the_refusal_carries_the_request_id(self, unseal: Unseal) -> None:
        scope = _scope("GET", "/echo", query=b"q=" + SEALED.encode(), state={"request_id": "r-7"})
        sent = await _call(_input_app(), scope, [_whole(b"")])

        assert sent[0]["status"] == 422
        body = json.loads(b"".join(m.get("body", b"") for m in sent[1:]))
        assert body["error"] == {
            "code": "sealed_value_refused",
            "message": "This request contains a value that can't be accepted.",
            "request_id": "r-7",
        }


@pytest.mark.usefixtures("keyed")
class TestAnOrdinaryRequestThroughTheRelay:
    async def test_json_reaches_the_route_byte_for_byte(
        self, input_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal
    ) -> None:
        app, http = input_client
        body = '{"full_name": "Asha Rao", "lang": "महाराष्ट्र", "n": [1, 2.5, null]}'.encode()
        response = await http.post(
            "/echo?page=2",
            content=body,
            headers={"X-CMP-Relay-Key": KEY, "Content-Type": "application/json"},
        )

        assert response.status_code == 200
        assert app.state.seen["body"] == body
        assert app.state.seen["query"] == [("page", "2")]
        assert app.state.seen["relayed"] is True

    async def test_a_urlencoded_form_reaches_the_route_byte_for_byte(
        self, input_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal
    ) -> None:
        app, http = input_client
        body = b"name=Asha+Rao&city=Pune%2C+MH&empty="
        response = await http.post(
            "/echo", content=body, headers={"X-CMP-Relay-Key": KEY, "Content-Type": URLENCODED}
        )

        assert response.status_code == 200
        assert app.state.seen["body"] == body
        assert app.state.seen["form"] == [("name", "Asha Rao"), ("city", "Pune, MH"), ("empty", "")]

    async def test_a_file_whose_bytes_hold_the_prefix_is_let_in_whole(
        self, input_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal
    ) -> None:
        """Only names are searched: a scanned letter may hold the four
        characters, and no route reads a file's bytes as text."""
        app, http = input_client
        content = b"%PDF-1.7\n" + SEALED.encode() + bytes(range(256)) * 64
        body = _multipart(
            _field("note", "पत्र".encode()),
            _file('name="file"; filename="letter.pdf"', content, "application/pdf"),
        )
        response = await http.post(
            "/echo", content=body, headers={"X-CMP-Relay-Key": KEY, "Content-Type": MULTIPART}
        )

        assert response.status_code == 200
        assert app.state.seen["body"] == body
        assert app.state.seen["form"] == [("note", "पत्र"), ("file", "letter.pdf", content)]

    async def test_a_typed_upload_route_gets_its_file(
        self, input_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal
    ) -> None:
        app, http = input_client
        body = _multipart(
            _file('name="file"; filename="proof.pdf"', b"%PDF-1.7 SE::inside", "application/pdf"),
            _field("note", b"my letter"),
        )
        response = await http.post(
            "/attachments",
            content=body,
            headers={"X-CMP-Relay-Key": KEY, "Content-Type": MULTIPART},
        )

        assert response.json() == {"file_name": "proof.pdf", "note": "my letter"}
        assert app.state.seen["file"] == b"%PDF-1.7 SE::inside"

    async def test_a_form_that_does_not_parse_gets_the_routes_own_error(
        self, input_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal
    ) -> None:
        """No boundary: the check cannot read it, nor can the route, which
        answers as it always would. Nothing of the body was used."""
        app, http = input_client
        response = await http.post(
            "/attachments",
            content=b"--x\r\n" + SEALED.encode(),
            headers={"X-CMP-Relay-Key": KEY, "Content-Type": "multipart/form-data"},
        )

        assert response.status_code == 400
        assert "file" not in app.state.seen

    async def test_an_empty_get_is_untouched(
        self, input_client: tuple[FastAPI, httpx.AsyncClient], unseal: Unseal
    ) -> None:
        app, http = input_client
        response = await http.get("/echo", headers={"X-CMP-Relay-Key": KEY})

        assert response.status_code == 200
        assert app.state.seen["body"] == b""


class TestWithoutTheKeyNothingIsChecked:
    @pytest.mark.parametrize("key", [None, pytest.param("w" * 40, id="wrong key")])
    async def test_sealed_values_reach_the_route_as_sent(
        self,
        input_client: tuple[FastAPI, httpx.AsyncClient],
        unseal: Unseal,
        monkeypatch: pytest.MonkeyPatch,
        key: str | None,
    ) -> None:
        """The console and the inside's own callers send ciphertext routinely."""
        monkeypatch.setattr(settings, "relay_ingress_key", SecretStr(KEY))
        app, http = input_client
        headers = {"User-Agent": SEALED, "Content-Type": "application/json"}
        if key:
            headers["X-CMP-Relay-Key"] = key
        body = json.dumps({"full_name": SEALED}).encode()
        response = await http.post(f"/echo?q={SEALED}", content=body, headers=headers)

        assert response.status_code == 200
        assert app.state.seen["body"] == body
        assert app.state.seen["query"] == [("q", SEALED)]
        assert app.state.seen["headers"]["user-agent"] == SEALED
        assert app.state.seen["relayed"] is False

    async def test_with_no_key_configured_nothing_is_checked(
        self,
        input_client: tuple[FastAPI, httpx.AsyncClient],
        unseal: Unseal,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(settings, "relay_ingress_key", SecretStr(""))
        app, http = input_client
        response = await http.get(f"/echo?q={SEALED}", headers={"X-CMP-Relay-Key": KEY})

        assert response.status_code == 200
        assert app.state.seen["relayed"] is False

    @pytest.mark.usefixtures("keyed")
    async def test_the_body_is_buffered_only_with_the_key(self, unseal: Unseal) -> None:
        """Without the key the app reads the body as it streams in; with it,
        as one message, once it has been checked."""
        chunks = [_part(b'{"a":'), _part(b'"b"}', more=False)]

        plain, without = _recording_app()
        await _call(plain, _scope("POST", "/x", keyed=False), chunks)
        relayed, keyed = _recording_app()
        await _call(relayed, _scope("POST", "/x"), chunks)

        assert without == [*chunks, {"type": "http.disconnect"}]
        assert keyed == [_whole(b'{"a":"b"}'), {"type": "http.disconnect"}]


@pytest.mark.usefixtures("keyed")
class TestTheReplay:
    async def test_after_the_body_the_app_reads_the_original_receive(self, unseal: Unseal) -> None:
        """A disconnect after the body still reaches the app."""
        later = {"type": "http.disconnect", "from": "the original receive"}
        app, received = _recording_app()
        await _call(app, _scope("POST", "/x"), [_part(b"{"), _part(b"}", more=False), later])

        assert received == [_whole(b"{}"), later]

    async def test_a_client_gone_mid_body_is_the_apps_to_see(self, unseal: Unseal) -> None:
        gone = {"type": "http.disconnect"}
        app, received = _recording_app()
        await _call(app, _scope("POST", "/x"), [_part(b'{"a":'), gone])

        assert received == [gone]

    async def test_an_error_raised_while_reading_is_raised_to_the_app(self, unseal: Unseal) -> None:
        """As BodyLimit's 413 is: on the app's own first read, as before."""

        class TooLarge(Exception):
            pass

        raised: list[str] = []

        async def inner(scope: Any, receive: Any, send: Any) -> None:
            try:
                await receive()
            except TooLarge:
                raised.append("on the first read")
            await send({"type": "http.response.start", "status": 413, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        async def receive() -> dict[str, Any]:
            raise TooLarge

        sent: list[dict[str, Any]] = []

        async def send(message: Any) -> None:
            sent.append(dict(message))

        await RelayOpenSealedMiddleware(inner)(_scope("POST", "/x"), receive, send)

        assert raised == ["on the first read"]
        assert sent[0]["status"] == 413

    async def test_the_mark_and_the_stripping_stay_inside(self, unseal: Unseal) -> None:
        """The app is told the request was relayed; the scope the middleware
        outside holds is not changed."""
        outer = _scope("GET", "/x", state={"request_id": "r-1"})
        seen: dict[str, Any] = {}

        async def inner(scope: Any, receive: Any, send: Any) -> None:
            seen.update(scope)
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        await _call(RelayOpenSealedMiddleware(inner), outer, [_whole(b"")])

        assert seen["state"] == {"request_id": "r-1", "relayed": True}
        assert outer["state"] == {"request_id": "r-1"}
        assert (b"x-cmp-relay-key", KEY.encode()) in outer["headers"]
        assert all(name != b"x-cmp-relay-key" for name, _ in seen["headers"])


def _scope(
    method: str,
    path: str,
    *,
    keyed: bool = True,
    query: bytes = b"",
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers = [(b"host", b"test"), (b"content-type", b"application/json")]
    if keyed:
        headers.append((b"x-cmp-relay-key", KEY.encode()))
    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "root_path": "",
        "query_string": query,
        "headers": headers,
        "client": ("127.0.0.1", 1),
        "server": ("test", 80),
    }
    if state is not None:
        scope["state"] = state
    return scope


def _part(body: bytes, *, more: bool = True) -> dict[str, Any]:
    return {"type": "http.request", "body": body, "more_body": more}


def _whole(body: bytes) -> dict[str, Any]:
    return _part(body, more=False)


def _recording_app() -> tuple[RelayOpenSealedMiddleware, list[dict[str, Any]]]:
    """The middleware over a raw app that reads every message it is given,
    up to a disconnect; and the list of what that app received."""
    received: list[dict[str, Any]] = []

    async def inner(scope: Any, receive: Any, send: Any) -> None:
        while True:
            message = await receive()
            received.append(dict(message))
            if message["type"] == "http.disconnect":
                break
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    return RelayOpenSealedMiddleware(inner), received


async def _call(
    app: Any, scope: dict[str, Any], messages: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Run `app` over these request messages, then disconnects; what it sent."""
    queue = list(messages)
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return queue.pop(0) if queue else {"type": "http.disconnect"}

    async def send(message: Any) -> None:
        sent.append(dict(message))

    await asyncio.wait_for(app(scope, receive, send), timeout=5)
    return sent


#: Enough for production to boot, as in tests/unit/core/test_production_guards.py.
PRODUCTION: dict[str, Any] = {
    "_env_file": None,
    "environment": "production",
    "secret_key": "a-real-secret-key-of-at-least-thirty-two-bytes",
    "postgres_password": "not-a-default-password",
    "cookie_secure": True,
    "debug": False,
    "cors_origins": "https://console.example.org",
    "smtp_host": "relay.organisation.example",
    "sms_transport": "http",
    "sms_http_url": "https://sms-gateway.example.org/send",
    "dkms_enabled": True,
    "blind_index_key": "a-real-blind-index-key-of-thirty-two-bytes",
    "breach_ticket_email_domains": ("organisation.example",),
    "notification_email_from": "privacy@organisation.example",
}


class TestProductionGuard:
    def test_production_may_leave_it_off(self) -> None:
        assert Settings(**PRODUCTION).relay_ingress_key.get_secret_value() == ""

    def test_production_takes_a_long_key(self) -> None:
        loaded = Settings(**{**PRODUCTION, "relay_ingress_key": KEY})
        assert loaded.relay_ingress_key.get_secret_value() == KEY

    def test_production_refuses_a_short_key(self) -> None:
        with pytest.raises(ValueError, match="RELAY_INGRESS_KEY"):
            Settings(**{**PRODUCTION, "relay_ingress_key": "short-key"})

    def test_outside_production_a_short_key_is_allowed(self) -> None:
        local: dict[str, Any] = {
            "_env_file": None,
            "environment": "local",
            "relay_ingress_key": "short",
        }
        loaded = Settings(**local)
        assert loaded.relay_ingress_key.get_secret_value() == "short"
