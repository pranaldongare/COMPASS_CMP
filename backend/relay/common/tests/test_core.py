"""The relay's shared code (`common`): sealing, the envelope, the allow-list and
the settings both sides read. No network, no AWS: everything here is pure.
Each side's own settings and tools are tested with it."""

from __future__ import annotations

import base64
import json
import os
import re

import pytest
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from cmp_relay import allowlist, config, envelope, sealing
from cmp_relay.allowlist import (
    DEV_ROUTES,
    PUBLIC_ROUTES,
    RouteTable,
    carries_sealed_value,
    request_headers,
    response_headers,
)
from cmp_relay.envelope import Body, EnvelopeError, RelayRequest, RelayResponse
from cmp_relay.sealing import REPLY, REPLY_BODY, REQUEST, REQUEST_BODY, SealError

RID = "0d6f4c1e-8a7b-4c3d-9e2f-1a2b3c4d5e6f"


def _keypair() -> tuple[X25519PrivateKey, str]:
    private, public = sealing.generate_keypair()
    return sealing.load_private(private), public


# ===================================================================== sealing


class TestSealing:
    def test_request_round_trip_gives_both_sides_the_same_keys(self) -> None:
        private, public = _keypair()
        blob, bridge_keys = sealing.seal_request(sealing.load_public(public), b"hello", RID)
        plaintext, collector_keys = sealing.open_request([private], blob, RID)
        assert plaintext == b"hello"
        assert collector_keys.request_key == bridge_keys.request_key
        assert collector_keys.reply_key == bridge_keys.reply_key
        assert bridge_keys.request_key != bridge_keys.reply_key

    def test_reply_and_bodies_round_trip_under_their_keys(self) -> None:
        private, public = _keypair()
        header, bridge = sealing.begin_request(sealing.load_public(public))
        body = sealing.seal(bridge.request_key, REQUEST_BODY, b"x" * 300_000, RID)
        blob = sealing.finish_request(header, bridge, b"envelope", RID)
        _, collector = sealing.open_request([private], blob, RID)
        assert sealing.open_sealed(collector.request_key, REQUEST_BODY, body, RID) == b"x" * 300_000

        reply = sealing.seal(collector.reply_key, REPLY, b"answer", RID)
        reply_body = sealing.seal(collector.reply_key, REPLY_BODY, b"big answer", RID)
        assert sealing.open_sealed(bridge.reply_key, REPLY, reply, RID) == b"answer"
        assert sealing.open_sealed(bridge.reply_key, REPLY_BODY, reply_body, RID) == b"big answer"

    def test_ciphertext_does_not_contain_the_plaintext(self) -> None:
        _, public = _keypair()
        secret = b"+919876543210 consent for Asha"
        blob, keys_ = sealing.seal_request(sealing.load_public(public), secret, RID)
        assert secret not in blob
        assert secret not in sealing.seal(keys_.reply_key, REPLY, secret, RID)

    def test_every_request_gets_fresh_keys(self) -> None:
        _, public = _keypair()
        collector = sealing.load_public(public)
        first, k1 = sealing.seal_request(collector, b"same", RID)
        second, k2 = sealing.seal_request(collector, b"same", RID)
        assert first != second
        assert k1.request_key != k2.request_key
        assert k1.reply_key != k2.reply_key

    def test_a_request_is_bound_to_its_request_id(self) -> None:
        private, public = _keypair()
        blob, _ = sealing.seal_request(sealing.load_public(public), b"hello", RID)
        with pytest.raises(SealError):
            sealing.open_request([private], blob, "another-request")

    def test_replies_and_bodies_are_bound_to_their_request_id(self) -> None:
        key = os.urandom(32)
        for magic in (REPLY, REQUEST_BODY, REPLY_BODY):
            blob = sealing.seal(key, magic, b"data", RID)
            with pytest.raises(SealError):
                sealing.open_sealed(key, magic, blob, "another-request")

    def test_a_blob_of_one_kind_never_opens_as_another(self) -> None:
        key = os.urandom(32)
        reply = sealing.seal(key, REPLY, b"data", RID)
        with pytest.raises(SealError):
            sealing.open_sealed(key, REPLY_BODY, reply, RID)
        # Same bytes after the magic, relabelled: the magic is in the AAD too.
        relabelled = REPLY_BODY + reply[len(REPLY) :]
        with pytest.raises(SealError):
            sealing.open_sealed(key, REPLY_BODY, relabelled, RID)

    def test_a_request_body_does_not_open_under_the_reply_key(self) -> None:
        _, public = _keypair()
        _, k = sealing.begin_request(sealing.load_public(public))
        body = sealing.seal(k.request_key, REQUEST_BODY, b"data", RID)
        with pytest.raises(SealError):
            sealing.open_sealed(k.reply_key, REQUEST_BODY, body, RID)

    def test_a_request_sealed_to_another_collector_does_not_open(self) -> None:
        mine, _ = _keypair()
        _, theirs = _keypair()
        blob, _ = sealing.seal_request(sealing.load_public(theirs), b"hello", RID)
        with pytest.raises(SealError, match="does not hold"):
            sealing.open_request([mine], blob, RID)

    def test_a_reply_does_not_open_under_another_requests_key(self) -> None:
        _, public = _keypair()
        collector = sealing.load_public(public)
        _, k1 = sealing.seal_request(collector, b"a", RID)
        _, k2 = sealing.seal_request(collector, b"b", RID)
        reply = sealing.seal(k1.reply_key, REPLY, b"for request one", RID)
        with pytest.raises(SealError):
            sealing.open_sealed(k2.reply_key, REPLY, reply, RID)

    @pytest.mark.parametrize("where", ["ciphertext", "nonce", "ephemeral", "tag"])
    def test_a_tampered_request_does_not_open(self, where: str) -> None:
        private, public = _keypair()
        blob = bytearray(sealing.seal_request(sealing.load_public(public), b"hello", RID)[0])
        index = {
            "ephemeral": len(REQUEST) + 8 + 5,
            "nonce": len(REQUEST) + 8 + 32 + 3,
            "ciphertext": len(REQUEST) + 8 + 32 + 12 + 1,
            "tag": len(blob) - 1,
        }[where]
        blob[index] ^= 0x01
        with pytest.raises(SealError):
            sealing.open_request([private], bytes(blob), RID)

    def test_a_tampered_reply_does_not_open(self) -> None:
        key = os.urandom(32)
        blob = bytearray(sealing.seal(key, REPLY, b"answer", RID))
        blob[-3] ^= 0x80
        with pytest.raises(SealError):
            sealing.open_sealed(key, REPLY, bytes(blob), RID)

    def test_a_low_order_ephemeral_key_is_refused_not_crashed(self) -> None:
        private, public = _keypair()
        blob = bytearray(sealing.seal_request(sealing.load_public(public), b"hello", RID)[0])
        start = len(REQUEST) + 8
        blob[start : start + 32] = bytes(32)  # the all-zero point: shared secret all zeros
        with pytest.raises(SealError):
            sealing.open_request([private], bytes(blob), RID)

    @pytest.mark.parametrize(
        "blob", [b"", b"CR1Q", b"CR1Q" + bytes(52), b"XXXX" + bytes(100), b"CR1R" + bytes(100)]
    )
    def test_malformed_requests_are_refused(self, blob: bytes) -> None:
        private, _ = _keypair()
        with pytest.raises(SealError):
            sealing.open_request([private], blob, RID)

    @pytest.mark.parametrize("blob", [b"", b"CR1R", b"CR1R" + bytes(12), b"CR1Q" + bytes(40)])
    def test_malformed_sealed_blobs_are_refused(self, blob: bytes) -> None:
        with pytest.raises(SealError):
            sealing.open_sealed(os.urandom(32), REPLY, blob, RID)

    def test_rotation_opens_requests_sealed_to_either_key(self) -> None:
        current, current_public = _keypair()
        previous, previous_public = _keypair()
        _, retired_public = _keypair()
        held = [current, previous]
        for public in (current_public, previous_public):
            blob, sent = sealing.seal_request(sealing.load_public(public), b"hi", RID)
            plaintext, got = sealing.open_request(held, blob, RID)
            assert plaintext == b"hi"
            assert got.reply_key == sent.reply_key
        blob, _ = sealing.seal_request(sealing.load_public(retired_public), b"hi", RID)
        with pytest.raises(SealError):
            sealing.open_request(held, blob, RID)

    def test_key_id_names_the_public_key(self) -> None:
        private, public = _keypair()
        blob, _ = sealing.seal_request(sealing.load_public(public), b"x", RID)
        assert blob[len(REQUEST) : len(REQUEST) + 8] == sealing.key_id(private.public_key())

    def test_request_keys_never_print_their_material(self) -> None:
        _, public = _keypair()
        _, k = sealing.seal_request(sealing.load_public(public), b"x", RID)
        for text in (repr(k), str(k), f"{k!r}", repr([k])):
            assert "redacted" in text
            assert k.request_key.hex() not in text
            assert k.reply_key.hex() not in text
            assert repr(k.request_key) not in text

    def test_key_encoding_round_trip(self) -> None:
        private_b64, public_b64 = sealing.generate_keypair()
        private = sealing.load_private(private_b64)
        assert sealing.public_of(private) == public_b64
        assert sealing.load_private(f"  {private_b64}\n") is not None

    @pytest.mark.parametrize(
        "value", ["", "not base64!", base64.b64encode(bytes(31)).decode(), "AAAA"]
    )
    def test_bad_keys_are_refused(self, value: str) -> None:
        with pytest.raises(ValueError):
            sealing.load_public(value)
        with pytest.raises(ValueError):
            sealing.load_private(value)


# ==================================================================== envelope


def _request(**overrides: object) -> RelayRequest:
    fields: dict[str, object] = {
        "id": RID,
        "reply_to": "https://sqs.ap-south-1.amazonaws.com/1/replies-a",
        "issued_ms": 1_792_000_000_000,
        "deadline_ms": 1_792_000_025_000,
        "method": "POST",
        "path": "/c/tok_123/consent",
        "query": "lang=hi",
        "headers": [("content-type", "application/json"), ("cookie", "cmp_session=s")],
        "client_ip": "203.0.113.7",
        "body": Body(inline=b'{"grants":[]}'),
    }
    fields.update(overrides)
    return RelayRequest(**fields)  # type: ignore[arg-type]


def _encode(request: RelayRequest, **changes: object) -> bytes:
    data = json.loads(request.to_bytes())
    for name, value in changes.items():
        if value is _DROP:
            data.pop(name, None)
        else:
            data[name] = value
    return json.dumps(data).encode()


_DROP = object()


class TestEnvelope:
    def test_request_round_trip(self) -> None:
        request = _request()
        assert RelayRequest.from_bytes(request.to_bytes()) == request

    def test_request_with_a_body_in_s3_round_trips(self) -> None:
        body = Body(s3_key=f"req/{RID}", size=1_000_000, sha256="ab" * 32)
        request = _request(body=body)
        back = RelayRequest.from_bytes(request.to_bytes())
        assert back.body == body
        assert back.body is not None and back.body.inline is None

    def test_request_without_a_body_or_address_round_trips(self) -> None:
        request = _request(method="GET", body=None, client_ip=None, query="", headers=[])
        assert RelayRequest.from_bytes(request.to_bytes()) == request

    def test_ping_round_trips(self) -> None:
        ping = _request(kind="ping", method="GET", path="/health", body=None, headers=[])
        back = RelayRequest.from_bytes(ping.to_bytes())
        assert back.kind == "ping"
        assert back == ping

    def test_an_empty_inline_body_is_kept_distinct_from_none(self) -> None:
        back = RelayRequest.from_bytes(_request(body=Body(inline=b"")).to_bytes())
        assert back.body == Body(inline=b"")

    def test_binary_bodies_survive(self) -> None:
        raw = bytes(range(256)) * 10
        assert RelayRequest.from_bytes(_request(body=Body(inline=raw)).to_bytes()).body == Body(
            inline=raw
        )

    def test_response_round_trip_keeps_every_set_cookie_in_order(self) -> None:
        response = RelayResponse(
            id=RID,
            status=200,
            headers=[
                ("content-type", "application/json"),
                ("set-cookie", "cmp_session=a; HttpOnly"),
                ("set-cookie", "cmp_csrf=b"),
            ],
            body=Body(inline=b"{}"),
        )
        back = RelayResponse.from_bytes(response.to_bytes())
        assert back == response
        assert [v for n, v in back.headers if n == "set-cookie"] == [
            "cmp_session=a; HttpOnly",
            "cmp_csrf=b",
        ]

    def test_response_with_a_body_in_s3_and_without_a_body(self) -> None:
        for body in (Body(s3_key=f"res/{RID}", size=5, sha256="0" * 64), None):
            response = RelayResponse(id=RID, status=204, body=body)
            assert RelayResponse.from_bytes(response.to_bytes()) == response

    def test_time_left(self) -> None:
        request = _request(deadline_ms=10_000)
        assert request.time_left_s(at_ms=4_000) == 6.0
        assert request.time_left_s(at_ms=12_500) == -2.5
        live = _request(deadline_ms=envelope.now_ms() + 25_000)
        assert 24 < live.time_left_s() <= 25

    def test_inline_limit(self) -> None:
        assert envelope.INLINE_LIMIT == 256 * 1024

    def test_error_json_is_the_apis_shape(self) -> None:
        data = json.loads(envelope.error_json("inside_timeout", "Try again.", RID))
        assert data == {
            "error": {"code": "inside_timeout", "message": "Try again.", "request_id": RID}
        }

    @pytest.mark.parametrize("raw", [b"", b"not json", b"\xff\xfe", b"[]", b"null", b'"v"'])
    def test_not_an_object_is_refused(self, raw: bytes) -> None:
        with pytest.raises(EnvelopeError):
            RelayRequest.from_bytes(raw)
        with pytest.raises(EnvelopeError):
            RelayResponse.from_bytes(raw)

    @pytest.mark.parametrize("version", [0, 2, "1", None, 1.5, _DROP])
    def test_another_version_is_refused(self, version: object) -> None:
        with pytest.raises(EnvelopeError):
            RelayRequest.from_bytes(_encode(_request(), v=version))

    @pytest.mark.parametrize("version", [True, 1.0])
    def test_a_version_of_the_wrong_type_is_refused(self, version: object) -> None:
        with pytest.raises(EnvelopeError):
            RelayRequest.from_bytes(_encode(_request(), v=version))

    @pytest.mark.parametrize(
        ("name", "value"),
        [
            ("id", 5),
            ("id", _DROP),
            ("reply_to", None),
            ("issued_ms", "1"),
            ("issued_ms", True),
            ("deadline_ms", 1.5),
            ("deadline_ms", False),
            ("method", ["GET"]),
            ("path", None),
            ("query", None),
            ("kind", "admin"),
            ("kind", _DROP),
            ("client_ip", 203),
            ("headers", {"accept": "x"}),
            ("headers", [["accept"]]),
            ("headers", [["accept", "x", "y"]]),
            ("headers", [["accept", 1]]),
            ("headers", ["accept: x"]),
            ("headers", _DROP),
            ("body", "inline"),
            ("body", {"inline": 5}),
            ("body", {"inline": "not base64!"}),
            ("body", {"s3_key": "", "size": 1, "sha256": "0" * 64}),
            ("body", {"s3_key": "req/x", "size": -1, "sha256": "0" * 64}),
            ("body", {"s3_key": "req/x", "size": "1", "sha256": "0" * 64}),
            ("body", {"s3_key": "req/x", "size": 1, "sha256": "short"}),
            ("body", {"s3_key": "req/x", "size": 1}),
            ("body", {}),
        ],
    )
    def test_a_wrong_request_field_is_refused(self, name: str, value: object) -> None:
        with pytest.raises(EnvelopeError):
            RelayRequest.from_bytes(_encode(_request(), **{name: value}))

    @pytest.mark.parametrize(
        ("name", "value"),
        [
            ("status", 99),
            ("status", 600),
            ("status", "200"),
            ("status", True),
            ("status", _DROP),
            ("id", None),
            ("headers", None),
        ],
    )
    def test_a_wrong_response_field_is_refused(self, name: str, value: object) -> None:
        raw = json.loads(RelayResponse(id=RID, status=200).to_bytes())
        if value is _DROP:
            raw.pop(name)
        else:
            raw[name] = value
        with pytest.raises(EnvelopeError):
            RelayResponse.from_bytes(json.dumps(raw).encode())

    def test_body_json_forms(self) -> None:
        assert Body(inline=b"ab").to_json() == {"inline": "YWI="}
        assert Body(s3_key="req/x", size=3, sha256="f" * 64).to_json() == {
            "s3_key": "req/x",
            "size": 3,
            "sha256": "f" * 64,
        }
        assert Body.from_json(None) is None


# =================================================================== allowlist


def _sample(template: str) -> str:
    """A concrete path for a template: every `{x}` becomes a realistic segment."""
    samples = iter(["Ab3_x-Y.z~9", "3f2c9a1e-5b6d-4e7f-8a9b-0c1d2e3f4a5b", "tok%20en", "42", "q-1"])
    return re.sub(r"\{[a-z_]+\}", lambda _m: next(samples), template)


class TestAllowlist:
    @pytest.mark.parametrize(("method", "template"), PUBLIC_ROUTES)
    def test_every_public_route_matches_a_sample_path(self, method: str, template: str) -> None:
        assert RouteTable().match(method, _sample(template)) == template
        assert RouteTable().match(method.lower(), _sample(template)) == template

    @pytest.mark.parametrize(("method", "template"), PUBLIC_ROUTES)
    def test_a_public_route_is_refused_with_another_method(
        self, method: str, template: str
    ) -> None:
        allowed = {m for m, t in PUBLIC_ROUTES if t == template}
        for other in sorted({"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"} - allowed):
            assert RouteTable().match(other, _sample(template)) is None

    def test_the_table_has_no_duplicates(self) -> None:
        assert len(set(PUBLIC_ROUTES)) == len(PUBLIC_ROUTES)

    @pytest.mark.parametrize(
        ("method", "path"),
        [
            # Staff and sign-in with a password, MFA
            ("POST", "/auth/login"),
            ("POST", "/auth/mfa/verify"),
            ("POST", "/auth/password/reset"),
            ("GET", "/consents"),
            ("GET", "/consents/3f2c9a1e/record"),
            ("GET", "/consent-records"),
            ("POST", "/consent-records"),
            ("GET", "/users"),
            ("GET", "/principals"),
            ("GET", "/rights-requests"),
            ("GET", "/breaches"),
            ("GET", "/audit"),
            # Operations and documentation
            ("GET", "/metrics"),
            ("GET", "/docs"),
            ("GET", "/redoc"),
            ("GET", "/openapi.json"),
            ("GET", "/health"),
            ("GET", "/ready"),
            # Close to a public route but not one
            ("GET", "/me"),
            ("GET", "/me/"),
            ("GET", "/c/"),
            ("GET", "/c/tok/"),
            ("GET", "/c/tok/extra"),
            ("GET", "/c/tok/notice/x"),
            ("POST", "/me/consents/abc/withdraw/now"),
            ("GET", "/rights?x=1"),
            ("GET", ""),
            ("GET", "/"),
            ("GET", "c/tok"),
        ],
    )
    def test_everything_else_is_refused(self, method: str, path: str) -> None:
        assert RouteTable(allow_dev_routes=True).match(method, path) is None

    @pytest.mark.parametrize(
        "path",
        [
            "/c/tok/../../users",
            "/me/../consents",
            "/c/..",
            "/me/consents/..",
            "//me/consents",
            "/me//consents",
            "/c/a%2fb",
            "/c/a%2Fb/notice",
            "/c/%2e%2e",
            "/c/%2E%2E/notice",
            "/c/a%5cb",
            "/c/a%5Cb",
            "/c/a\\b",
            "/c/a/b",
            "/c/a?b",
            "/c/a#b",
            "/c/a b",
            "/c/a\nb",
        ],
    )
    def test_traversal_and_encoded_separators_are_refused(self, path: str) -> None:
        assert RouteTable().match("GET", path) is None

    def test_a_trailing_newline_is_refused(self) -> None:
        assert RouteTable().match("GET", "/c/tok\n") is None

    @pytest.mark.parametrize(("method", "path"), DEV_ROUTES)
    def test_dev_routes_only_when_enabled(self, method: str, path: str) -> None:
        assert RouteTable().match(method, path) is None
        assert RouteTable(allow_dev_routes=False).match(method, path) is None
        assert RouteTable(allow_dev_routes=True).match(method, path) == path

    def test_unsafe_methods(self) -> None:
        assert {"POST", "PUT", "PATCH", "DELETE"} == allowlist.UNSAFE_METHODS
        assert "GET" not in allowlist.UNSAFE_METHODS

    def test_request_headers_keep_only_what_the_api_reads(self) -> None:
        kept = request_headers(
            [
                ("Accept", "application/json"),
                ("Accept-Language", "hi"),
                ("Content-Type", "application/json"),
                ("User-Agent", "Firefox"),
                ("X-Request-ID", "abc"),
                ("x-csrf-token", "t"),
                ("X-Dev-Client", "portal"),
                ("Authorization", "Bearer x"),
                ("Host", "evil.example"),
                ("X-Forwarded-For", "1.2.3.4"),
                ("X-Real-IP", "1.2.3.4"),
                ("Forwarded", "for=1.2.3.4"),
                ("X-CMP-Relay-Key", "guess"),
                ("X-CMP-Ingress", "internal"),
                ("Origin", "https://evil.example"),
                ("Content-Length", "10"),
                ("Transfer-Encoding", "chunked"),
                ("Connection", "keep-alive"),
            ],
            csrf_header="X-CSRF-Token",
            cookie_names=frozenset({"cmp_session"}),
            extra=frozenset({"X-Dev-Client"}),
        )
        assert kept == [
            ("accept", "application/json"),
            ("accept-language", "hi"),
            ("content-type", "application/json"),
            ("user-agent", "Firefox"),
            ("x-request-id", "abc"),
            ("x-csrf-token", "t"),
            ("x-dev-client", "portal"),
        ]

    def test_cookies_are_filtered_to_the_named_ones(self) -> None:
        names = frozenset({"cmp_session", "cmp_csrf", "cmp_ticket"})
        kept = request_headers(
            [("Cookie", "_ga=1; cmp_session=abc; theme=dark; cmp_csrf=t=x; cmp_sessionX=no")],
            csrf_header="X-CSRF-Token",
            cookie_names=names,
        )
        assert kept == [("cookie", "cmp_session=abc; cmp_csrf=t=x")]

    def test_a_cookie_header_with_no_named_cookie_is_dropped(self) -> None:
        kept = request_headers(
            [("cookie", "_ga=1; theme=dark"), ("cookie", "junk")],
            csrf_header="X-CSRF-Token",
            cookie_names=frozenset({"cmp_session"}),
        )
        assert kept == []

    def test_response_headers_keep_what_the_browser_needs(self) -> None:
        kept = response_headers(
            [
                ("Content-Type", "application/pdf"),
                ("Content-Disposition", "attachment"),
                ("Set-Cookie", "cmp_session=a"),
                ("Set-Cookie", "cmp_csrf=b"),
                ("Cache-Control", "no-store"),
                ("Retry-After", "30"),
                ("X-Request-ID", "r"),
                ("X-Recorded-SHA256", "h"),
                ("Server", "uvicorn"),
                ("Content-Length", "10"),
                ("Transfer-Encoding", "chunked"),
                ("Content-Encoding", "gzip"),
                ("Access-Control-Allow-Origin", "*"),
                ("Location", "http://127.0.0.1:8000/inside"),
                ("X-Internal-Host", "api-1"),
            ]
        )
        assert kept == [
            ("content-type", "application/pdf"),
            ("content-disposition", "attachment"),
            ("set-cookie", "cmp_session=a"),
            ("set-cookie", "cmp_csrf=b"),
            ("cache-control", "no-store"),
            ("retry-after", "30"),
            ("x-request-id", "r"),
            ("x-recorded-sha256", "h"),
        ]

    def test_the_offices_question_is_its_own_row_not_a_request(self) -> None:
        assert RouteTable().match("GET", "/me/requests/offices") == "/me/requests/offices"
        assert RouteTable().match("GET", "/me/requests/abc") == "/me/requests/{request}"

    def test_the_sso_pending_cookie_crosses_with_the_default_names(self) -> None:
        names = config.common_settings(_common_env()).cookie_names
        kept = request_headers(
            [("Cookie", "cmp_session=s; cmp_csrf=c; cmp_sso_pending=P; _ga=1")],
            csrf_header="X-CSRF-Token",
            cookie_names=names,
        )
        assert kept == [("cookie", "cmp_session=s; cmp_csrf=c; cmp_sso_pending=P")]

    @pytest.mark.parametrize(
        ("location", "crosses_as"),
        [
            ("https://portal.example.in/c/Ab3_x-Y.z~9?sso=ok", "/c/Ab3_x-Y.z~9?sso=ok"),
            ("http://localhost:3001/c/tok?sso=mobile", "/c/tok?sso=mobile"),
            ("/c/tok?sso=cancelled", "/c/tok?sso=cancelled"),
            # Whatever host it names, the browser stays on the portal it came from.
            ("https://evil.example/c/tok?sso=ok", "/c/tok?sso=ok"),
            ("//evil.example/c/tok?sso=ok", "/c/tok?sso=ok"),
        ],
    )
    def test_the_sso_callbacks_redirect_crosses_as_the_links_path(
        self, location: str, crosses_as: str
    ) -> None:
        kept = response_headers(
            [
                ("Location", location),
                ("Set-Cookie", "cmp_sso_pending=P; Path=/; HttpOnly"),
                ("Referrer-Policy", "no-referrer"),
            ],
            route="/auth/sso/callback",
            status=303,
        )
        assert kept == [
            ("location", crosses_as),
            ("set-cookie", "cmp_sso_pending=P; Path=/; HttpOnly"),
        ]

    @pytest.mark.parametrize(
        "location",
        [
            "https://portal.example.in/me/consents",
            "https://portal.example.in/c/tok",
            "https://portal.example.in/c/tok/notice?sso=ok",
            "https://portal.example.in/c/tok?sso=ok&next=/users",
            "https://portal.example.in/c/tok?sso=OK",
            "https://portal.example.in/c/tok?sso=ok#x",
            "https://portal.example.in/c/a%2fb?sso=ok",
            "https://portal.example.in/c/..?sso=ok",
            "https://portal.example.in/c/.?sso=ok",
            "http://[::1/c/tok?sso=ok",
            "",
        ],
    )
    def test_the_callback_may_send_the_browser_only_to_a_link(self, location: str) -> None:
        kept = response_headers([("Location", location)], route="/auth/sso/callback", status=303)
        assert kept == []

    @pytest.mark.parametrize(
        ("route", "status"),
        [
            ("/auth/sso/callback", 200),
            ("/auth/sso/callback", None),
            ("/c/{token}", 303),
            ("/c/{token}/sso/start", 302),
            (None, 303),
        ],
    )
    def test_no_other_redirect_crosses(self, route: str | None, status: int | None) -> None:
        kept = response_headers(
            [("Location", "https://portal.example.in/c/tok?sso=ok")], route=route, status=status
        )
        assert kept == []

    # ------------------------------------------------------ carries_sealed_value

    @pytest.mark.parametrize(
        "query",
        [
            "name=SE::abc",
            "name=SE%3A%3Aabc",
            "name=SE%3a%3aabc",
            "a=1&b=SE::x",
            "SE::x",
            "name=SE:%3Aabc",
        ],
    )
    def test_a_sealed_value_in_the_query_is_caught(self, query: str) -> None:
        assert carries_sealed_value(query, None, None)

    @pytest.mark.parametrize("query", ["", "lang=hi", "name=SE:abc", "q=SEE&x=::"])
    def test_an_ordinary_query_passes(self, query: str) -> None:
        assert not carries_sealed_value(query, None, None)

    def test_a_sealed_value_in_a_json_body_is_caught(self) -> None:
        body = json.dumps({"full_name": "SE::djEuMS5uYW1l"}).encode()
        assert carries_sealed_value("", "application/json", body)
        assert carries_sealed_value("", "application/json; charset=utf-8", body)

    def test_a_json_body_without_one_passes(self) -> None:
        body = json.dumps({"full_name": "Asha SE", "note": "ratio 2::1"}).encode()
        assert not carries_sealed_value("", "application/json", body)

    def test_a_json_escaped_prefix_is_caught(self) -> None:
        body = b'{"full_name": "SE\\u003a\\u003adjEuMS5uYW1l"}'
        assert json.loads(body)["full_name"].startswith("SE::")
        assert carries_sealed_value("", "application/json", body)

    def test_a_sealed_value_in_a_form_body_is_caught(self) -> None:
        kind = "application/x-www-form-urlencoded"
        assert carries_sealed_value("", kind, b"name=SE%3A%3Aabc")
        assert carries_sealed_value("", kind, b"name=SE::abc")
        assert carries_sealed_value("", kind, b"x=1&name=SE%3a%3aabc")
        assert not carries_sealed_value("", kind, b"name=Asha&mobile=%2B91987")

    def test_a_body_without_a_content_type_is_searched_as_text(self) -> None:
        assert carries_sealed_value("", None, b"SE::abc")
        assert not carries_sealed_value("", None, b"plain")
        assert not carries_sealed_value("", "application/json", b"")
        assert not carries_sealed_value("", "application/json", None)

    @staticmethod
    def _multipart(*parts: tuple[str, str | None, bytes]) -> tuple[str, bytes]:
        boundary = "----cmpBoundary7MA4YWxkTrZu0gW"
        chunks: list[bytes] = []
        for name, filename, content in parts:
            disposition = f'form-data; name="{name}"'
            headers = ""
            if filename:
                disposition += f'; filename="{filename}"'
                headers = "Content-Type: application/octet-stream\r\n"
            chunks.append(
                f"--{boundary}\r\nContent-Disposition: {disposition}\r\n{headers}\r\n".encode()
                + content
                + b"\r\n"
            )
        chunks.append(f"--{boundary}--\r\n".encode())
        return f"multipart/form-data; boundary={boundary}", b"".join(chunks)

    def test_a_sealed_value_in_a_multipart_text_field_is_caught(self) -> None:
        kind, body = self._multipart(
            ("file", "proof.pdf", b"%PDF-1.7 harmless"),
            ("description", None, b"see SE::djEuMS5uYW1l"),
        )
        assert carries_sealed_value("", kind, body)

    def test_a_multipart_file_part_may_contain_anything(self) -> None:
        kind, body = self._multipart(
            ("description", None, b"my documents"),
            ("file", "notes.txt", b"my own notes mention SE::abc and SE%3A%3Aabc"),
        )
        assert not carries_sealed_value("", kind, body)

    def test_an_ordinary_multipart_upload_passes(self) -> None:
        kind, body = self._multipart(
            ("kind", None, b"identity"),
            ("file", "id.png", bytes(range(256))),
        )
        assert not carries_sealed_value("", kind, body)

    def test_a_multipart_body_that_does_not_parse_is_searched_whole(self) -> None:
        assert carries_sealed_value("", "multipart/form-data", b"no boundary SE::abc")
        assert not carries_sealed_value("", "multipart/form-data", b"no boundary at all")

    def test_the_query_is_checked_even_on_an_upload(self) -> None:
        kind, body = self._multipart(("kind", None, b"identity"))
        assert carries_sealed_value("x=SE::abc", kind, body)

    # ------------------------------------------------------------- headers

    @pytest.mark.parametrize(
        "header",
        [
            ("User-Agent", "Mozilla/5.0 SE::djEuMS5uYW1l"),
            ("accept-language", "SE::abc"),
            ("Accept-Language", "hi;q=0.9, SE%3A%3Aabc"),
            ("x-request-id", "SE%3a%3aabc"),
            ("X-CSRF-Token", "SE:%3Aabc"),
        ],
    )
    def test_a_sealed_value_in_a_header_is_caught(self, header: tuple[str, str]) -> None:
        assert carries_sealed_value("", None, None, [("accept", "application/json"), header])

    def test_ordinary_headers_and_the_cookie_pass(self) -> None:
        headers = [
            ("User-Agent", "Mozilla/5.0 (X11; Linux x86_64)"),
            ("Accept-Language", "hi-IN,hi;q=0.9"),
            ("Cookie", "cmp_session=SE::not-searched"),
            ("cookie", "cmp_csrf=SE%3A%3Ax"),
        ]
        assert not carries_sealed_value("", None, None, headers)

    # ---------------------------------------------------- deep JSON documents

    def test_a_deep_json_document_is_searched_all_the_way_down(self) -> None:
        nested = b"[" * 3000 + b'"SE\\u003a\\u003aabc"' + b"]" * 3000
        assert json.loads(nested) is not None  # the API's parser reads it
        assert carries_sealed_value("", "application/json", nested)
        assert not carries_sealed_value("", "application/json", b"[" * 3000 + b"]" * 3000)

    def test_a_json_document_too_deep_to_parse_is_refused(self) -> None:
        deep = b"[" * 100_000 + b"]" * 100_000
        with pytest.raises(RecursionError):
            json.loads(deep)
        assert carries_sealed_value("", "application/json", deep)

    # ------------------------------------------------- multipart, strictly

    BOUNDARY = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    KIND = f"multipart/form-data; boundary={BOUNDARY}"

    @classmethod
    def _raw(
        cls, *parts: tuple[bytes, bytes], preamble: bytes = b"", epilogue: bytes = b"\r\n"
    ) -> bytes:
        """A multipart body from raw (headers, bytes) parts."""
        out = preamble
        for head, data in parts:
            out += f"--{cls.BOUNDARY}\r\n".encode() + head + b"\r\n\r\n" + data + b"\r\n"
        return out + f"--{cls.BOUNDARY}--".encode() + epilogue

    FIELD = b'Content-Disposition: form-data; name="note"'
    FILE = b'Content-Disposition: form-data; name="file"; filename="id.pdf"'

    def test_what_a_browser_sends_passes(self) -> None:
        body = self._raw(
            (self.FIELD, b"my letter"),
            (self.FILE + b"\r\nContent-Type: application/pdf", b"%PDF SE::in-the-file"),
            (
                b'Content-Disposition: form-data; name="t"\r\n'
                b"Content-Type: text/plain; charset=utf-8",
                b"x",
            ),
        )
        assert not carries_sealed_value("", self.KIND, body)
        assert not carries_sealed_value("", self.KIND + "; charset=UTF-8", body)
        assert not carries_sealed_value("", self.KIND, self._raw(epilogue=b""))
        assert not carries_sealed_value(
            "", f'multipart/form-data; boundary="{self.BOUNDARY}"', body
        )

    def test_what_an_http_library_sends_passes(self) -> None:
        import httpx

        request = httpx.Request(
            "POST",
            "http://portal/api/me/requests/1/attachments",
            data={"note": "my letter"},
            files={"file": ("id.pdf", b"%PDF SE::in-the-file", "application/pdf")},
        )
        assert not carries_sealed_value("", request.headers["content-type"], request.read())

    @pytest.mark.parametrize(
        "content_type",
        [
            "{kind}; charset=utf-16-le",
            "{kind}; charset=latin-1",
            "{kind}; charset=no-such-charset",
            "{kind}; boundary=other",
            "{kind}; boundary*=utf-8''other",
            "{kind}; name=x",
            "{kind};",
            "multipart/form-data; boundary=bad\\boundary",
            "multipart/form-data; boundary=" + "b" * 71,
        ],
    )
    def test_a_content_type_a_browser_does_not_send_is_refused(self, content_type: str) -> None:
        body = self._raw((self.FIELD, b"harmless"))
        assert carries_sealed_value("", content_type.format(kind=self.KIND), body)

    @pytest.mark.parametrize(
        "parts",
        [
            # Content-Transfer-Encoding: another parser decodes it, the API does not.
            [(FIELD + b"\r\nContent-Transfer-Encoding: base64", b"U0U6OmFiYw==")],
            [(FIELD + b"\r\nContent-Transfer-Encoding: 8bit", b"harmless")],
            # Two Content-Dispositions: parsers disagree on which one counts.
            [(FILE + b"\r\n" + FIELD, b"harmless")],
            [(FIELD + b"\r\nContent-Type: text/plain\r\nContent-Type: text/html", b"x")],
            # A Content-Type parameter other than charset=utf-8 (name= made it a file).
            [(FIELD + b'\r\nContent-Type: text/plain; name="x.txt"', b"harmless")],
            [(FIELD + b"\r\nContent-Type: text/plain; charset=utf-16", b"harmless")],
            [(FIELD + b"\r\nContent-Type: text/plain; name*=utf-8''x.txt", b"harmless")],
            # Any other part header, a malformed or folded one, or none at all.
            [(FIELD + b"\r\nContent-Length: 8", b"harmless")],
            [(FIELD + b"\r\n X-Folded: yes", b"harmless")],
            [(FIELD + b"\r\nContent-Type : text/plain", b"harmless")],
            [(b"Content-Type: text/plain", b"harmless")],
            [(b"", b"harmless")],
        ],
    )
    def test_a_part_a_browser_does_not_send_is_refused(
        self, parts: list[tuple[bytes, bytes]]
    ) -> None:
        assert carries_sealed_value("", self.KIND, self._raw(*parts))

    @pytest.mark.parametrize(
        ("preamble", "epilogue"),
        [(b"\r\n", b"\r\n"), (b"hello\r\n", b""), (b"", b"\r\ntrailing"), (b"", b"--\r\n")],
    )
    def test_a_preamble_or_an_epilogue_is_refused(self, preamble: bytes, epilogue: bytes) -> None:
        body = self._raw((self.FIELD, b"harmless"), preamble=preamble, epilogue=epilogue)
        assert carries_sealed_value("", self.KIND, body)

    def test_a_boundary_inside_a_part_or_a_missing_end_is_refused(self) -> None:
        body = self._raw((self.FIELD, f"a\r\n--{self.BOUNDARY}X b".encode()))
        assert carries_sealed_value("", self.KIND, body)
        assert carries_sealed_value("", self.KIND, f"--{self.BOUNDARY}\r\n".encode() + self.FIELD)

    @pytest.mark.parametrize(
        "disposition",
        [
            b'form-data; name="file"; filename="SE::djEuMS5uYW1l"',
            b'form-data; name="file"; filename=SE::djEuMS5uYW1l',
            b"form-data; name=\"file\"; filename*=utf-8''SE%3A%3AdjEuMS5uYW1l",
            b"form-data; name=\"file\"; filename*=UTF-8''SE%3a%3adjEu",
            b'form-data; name="file"; filename*0="SE"; filename*1="::djEu"',
            b'form-data; name="SE::djEuMS5uYW1l"',
            b'form-data; name*0="SE"; name*1="::djEu"',
            b'form-data; name="file"; filename="SE%3A%3AdjEu"',
        ],
    )
    def test_a_sealed_value_in_a_part_name_or_filename_is_caught(self, disposition: bytes) -> None:
        body = self._raw(
            (b"Content-Disposition: " + disposition + b"\r\nContent-Type: text/plain", b"ok")
        )
        assert carries_sealed_value("", self.KIND, body)

    def test_a_sealed_value_in_a_part_content_type_is_caught(self) -> None:
        body = self._raw((self.FILE + b"\r\nContent-Type: SE::djEu/pdf", b"%PDF"))
        assert carries_sealed_value("", self.KIND, body)

    @pytest.mark.parametrize(
        "disposition",
        [
            # filename* alone: the API's parser ignores it and reads a text field.
            b"form-data; name=\"note\"; filename*=utf-8''letter.txt",
            # The `filename=` is inside the quoted name: there is no filename.
            b'form-data; name="note; filename=x.txt"',
            b'form-data; name="note\\"; filename=x.txt"',
        ],
    )
    def test_a_part_is_a_file_only_when_it_names_a_plain_filename(self, disposition: bytes) -> None:
        body = self._raw((b"Content-Disposition: " + disposition, b"SE::djEuMS5uYW1l"))
        assert carries_sealed_value("", self.KIND, body)
        named = b'form-data; name="note"; filename="letter.txt"'
        body = self._raw((b"Content-Disposition: " + named, b"SE::djEuMS5uYW1l"))
        assert not carries_sealed_value("", self.KIND, body)

    def test_an_empty_form_passes(self) -> None:
        assert not carries_sealed_value("", self.KIND, f"--{self.BOUNDARY}--\r\n".encode())

    def test_a_multipart_body_with_a_leading_space_in_its_type_is_still_read_strictly(
        self,
    ) -> None:
        # The API's parser strips the space and reads the parts.
        body = self._raw((b'Content-Disposition: form-data; name="SE::djEu"', b"x"))
        assert carries_sealed_value("", "  " + self.KIND, body)


# ====================================================================== config


def _common_env(**extra: str) -> dict[str, str]:
    return {
        "RELAY_REQUEST_QUEUE_URL": "https://sqs.ap-south-1.amazonaws.com/1/requests",
        "RELAY_BUCKET": "bodies",
        **extra,
    }


class TestConfig:
    """The settings both sides read. Each side's own, and these as it applies
    them, are tested with it (bridge/tests, collector/tests)."""

    @pytest.mark.parametrize("environment", ["production", "staging"])
    def test_local_only_settings_are_refused_outside_local(self, environment: str) -> None:
        for extra in (
            {"RELAY_ENDPOINT_URL": "http://127.0.0.1:5000"},
            {"RELAY_ALLOW_DEV_ROUTES": "true"},
        ):
            with pytest.raises(config.ConfigError, match=next(iter(extra))):
                config.common_settings(_common_env(RELAY_ENVIRONMENT=environment, **extra))

    @pytest.mark.parametrize("environment", ["local", "test", "LOCAL"])
    def test_local_only_settings_are_allowed_locally(self, environment: str) -> None:
        s = config.common_settings(
            _common_env(
                RELAY_ENVIRONMENT=environment,
                RELAY_ENDPOINT_URL="http://127.0.0.1:5000",
                RELAY_ALLOW_DEV_ROUTES="true",
            )
        )
        assert s.is_local
        assert s.endpoint_url == "http://127.0.0.1:5000"
        assert s.allow_dev_routes

    def test_an_unknown_environment_is_refused(self) -> None:
        with pytest.raises(config.ConfigError, match="RELAY_ENVIRONMENT"):
            config.common_settings(_common_env(RELAY_ENVIRONMENT="dev"))
