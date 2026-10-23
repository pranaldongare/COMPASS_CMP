"""The request and the reply as they travel between the bridge and the collector.

Both are JSON, sealed before they touch AWS (`sealing`). The shape is the HTTP
exchange itself, filtered: the method, the path after `/api`, the query string,
an allow-listed set of headers, the client's address, and the body - inline
when it is small, otherwise the key of a sealed object in S3.

Two fields carry the relay's own rules:

* `deadline_ms` - wall-clock milliseconds, on the bridge's clock, after which
  the bridge has given up and the browser has seen an error. The collector
  never starts a request past its deadline, and never starts a write that
  could not finish before it. That is what stops a consent the person saw fail
  from being recorded later. The bridge runs on EC2, whose clock follows
  Amazon Time Sync, so the collector reads the deadline on AWS's clock, not its
  own: it passes its estimate of AWS's time to `time_left_s`.
* `reply_to` - the reply queue of the one bridge instance waiting. The collector
  only ever answers to a queue on its own configured list, so a forged request
  cannot point the reply somewhere else.

Headers travel as a list of pairs, not a mapping, because a response can carry
several `Set-Cookie` headers and every one of them must arrive.

`from_bytes` is strict: an unknown version, a missing field or a wrong type is
refused. These bytes come off a queue other software can write to.
"""

from __future__ import annotations

import base64
import binascii
import json
import time
from dataclasses import dataclass, field
from typing import Any, Literal

VERSION = 1

#: Bodies up to this size travel inside the message; larger ones go through S3.
#: An SQS message holds 1 MiB. A body is base64 inside the JSON (x4/3) and the
#: sealed JSON is base64 again in the message (x4/3), so 256 KiB lands near
#: 460 KiB with room to spare for headers.
INLINE_LIMIT = 256 * 1024

Kind = Literal["http", "ping"]


class EnvelopeError(ValueError):
    """Bytes that are not a well-formed envelope of this version."""


def now_ms() -> int:
    return int(time.time() * 1000)


@dataclass(frozen=True)
class Body:
    """A body: either inline bytes, or a sealed object in S3.

    For an S3 body, `size` and `sha256` describe the *sealed object* as stored,
    not the plaintext: the reader checks both before it opens anything."""

    inline: bytes | None = None
    s3_key: str | None = None
    size: int = 0
    sha256: str = ""

    def to_json(self) -> dict[str, Any]:
        if self.inline is not None:
            return {"inline": base64.b64encode(self.inline).decode()}
        return {"s3_key": self.s3_key, "size": self.size, "sha256": self.sha256}

    @classmethod
    def from_json(cls, data: Any) -> Body | None:
        if data is None:
            return None
        if not isinstance(data, dict):
            raise EnvelopeError("body must be an object")
        if "inline" in data:
            raw = data["inline"]
            if not isinstance(raw, str):
                raise EnvelopeError("body.inline must be a string")
            try:
                return cls(inline=base64.b64decode(raw, validate=True))
            except (binascii.Error, ValueError) as exc:
                raise EnvelopeError("body.inline is not base64") from exc
        key, size, digest = data.get("s3_key"), data.get("size"), data.get("sha256")
        if not isinstance(key, str) or not key:
            raise EnvelopeError("body.s3_key must be a non-empty string")
        if not isinstance(size, int) or size < 0:
            raise EnvelopeError("body.size must be a non-negative integer")
        if not isinstance(digest, str) or len(digest) != 64:
            raise EnvelopeError("body.sha256 must be a hex SHA-256")
        return cls(s3_key=key, size=size, sha256=digest)


def _pairs(data: Any, what: str) -> list[tuple[str, str]]:
    if not isinstance(data, list):
        raise EnvelopeError(f"{what} must be a list of pairs")
    out: list[tuple[str, str]] = []
    for item in data:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not all(isinstance(part, str) for part in item)
        ):
            raise EnvelopeError(f"{what} must be a list of [name, value] string pairs")
        out.append((item[0], item[1]))
    return out


def _load(data: bytes) -> dict[str, Any]:
    try:
        decoded = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EnvelopeError("not JSON") from exc
    if not isinstance(decoded, dict):
        raise EnvelopeError("not a JSON object")
    version = decoded.get("v")
    if type(version) is not int or version != VERSION:  # true and 1.0 are not 1
        raise EnvelopeError(f"unsupported envelope version {decoded.get('v')!r}")
    return decoded


def _get(data: dict[str, Any], name: str, kind: type) -> Any:
    value = data.get(name)
    if not isinstance(value, kind) or (isinstance(value, bool) and kind is int):
        raise EnvelopeError(f"{name} must be {kind.__name__}")
    return value


@dataclass(frozen=True)
class RelayRequest:
    id: str
    reply_to: str
    issued_ms: int
    deadline_ms: int
    method: str
    path: str
    query: str = ""
    headers: list[tuple[str, str]] = field(default_factory=list)
    client_ip: str | None = None
    body: Body | None = None
    kind: Kind = "http"

    def time_left_s(self, at_ms: int | None = None) -> float:
        """Seconds to the deadline from `at_ms` (default: this host's clock)."""
        return (self.deadline_ms - (now_ms() if at_ms is None else at_ms)) / 1000

    def to_bytes(self) -> bytes:
        return json.dumps(
            {
                "v": VERSION,
                "id": self.id,
                "kind": self.kind,
                "reply_to": self.reply_to,
                "issued_ms": self.issued_ms,
                "deadline_ms": self.deadline_ms,
                "method": self.method,
                "path": self.path,
                "query": self.query,
                "headers": [list(p) for p in self.headers],
                "client_ip": self.client_ip,
                "body": self.body.to_json() if self.body else None,
            },
            separators=(",", ":"),
        ).encode()

    @classmethod
    def from_bytes(cls, data: bytes) -> RelayRequest:
        d = _load(data)
        kind = d.get("kind")
        if kind not in ("http", "ping"):
            raise EnvelopeError("kind must be http or ping")
        client_ip = d.get("client_ip")
        if client_ip is not None and not isinstance(client_ip, str):
            raise EnvelopeError("client_ip must be a string or null")
        return cls(
            id=_get(d, "id", str),
            kind=kind,
            reply_to=_get(d, "reply_to", str),
            issued_ms=_get(d, "issued_ms", int),
            deadline_ms=_get(d, "deadline_ms", int),
            method=_get(d, "method", str),
            path=_get(d, "path", str),
            query=_get(d, "query", str),
            headers=_pairs(d.get("headers"), "headers"),
            client_ip=client_ip,
            body=Body.from_json(d.get("body")),
        )


@dataclass(frozen=True)
class RelayResponse:
    id: str
    status: int
    headers: list[tuple[str, str]] = field(default_factory=list)
    body: Body | None = None

    def to_bytes(self) -> bytes:
        return json.dumps(
            {
                "v": VERSION,
                "id": self.id,
                "status": self.status,
                "headers": [list(p) for p in self.headers],
                "body": self.body.to_json() if self.body else None,
            },
            separators=(",", ":"),
        ).encode()

    @classmethod
    def from_bytes(cls, data: bytes) -> RelayResponse:
        d = _load(data)
        status = _get(d, "status", int)
        if not 100 <= status <= 599:
            raise EnvelopeError("status out of range")
        return cls(
            id=_get(d, "id", str),
            status=status,
            headers=_pairs(d.get("headers"), "headers"),
            body=Body.from_json(d.get("body")),
        )


def error_json(code: str, message: str, request_id: str) -> bytes:
    """An error in the API's own shape, so the portal shows it like any other."""
    return json.dumps(
        {"error": {"code": code, "message": message, "request_id": request_id}},
        separators=(",", ":"),
    ).encode()
