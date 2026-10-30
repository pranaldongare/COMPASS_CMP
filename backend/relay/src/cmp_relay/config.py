"""Every setting, read from the environment, checked once at start.

A setting that is missing or malformed stops the process with a sentence saying
which, rather than failing on the first request. `.env.example` lists them all.

Shared by both sides:

    RELAY_ENVIRONMENT          local | staging | production (default production)
    RELAY_REGION               AWS region (default ap-south-1)
    RELAY_ENDPOINT_URL         local emulator only (moto, LocalStack); unset on AWS
    RELAY_REQUEST_QUEUE_URL    the request queue
    RELAY_BUCKET               the bucket for bodies too large for a message
    RELAY_COOKIE_NAMES         cookies that may cross (cmp_session,cmp_csrf,cmp_ticket)
    RELAY_CSRF_HEADER          the CSRF header's name (X-CSRF-Token)
    RELAY_ALLOW_DEV_ROUTES     true only with RELAY_ENVIRONMENT=local: /dev/codes

The bridge (AWS side):

    RELAY_BRIDGE_HOST / _PORT  where it listens (127.0.0.1:8080); the portal's
                               API_ORIGIN points here
    RELAY_REPLY_QUEUE_URL      this instance's own reply queue
    RELAY_COLLECTOR_PUBLIC_KEY the collector's public key, base64
    RELAY_DEADLINE_S           time budget for one request (25)
    RELAY_UPLOAD_DEADLINE_S    time budget for a multipart upload (50, or the
                               ordinary deadline if that is longer). The
                               bridge waits this plus 2 s, which must stay
                               under the front door's 60 s (ALB idle timeout,
                               CloudFront origin response timeout); raise it
                               only with those, which must exceed it by 5 s
    RELAY_MAX_BODY_BYTES       largest request body accepted (26 MiB)
    RELAY_REPLY_POLLERS        threads long-polling the reply queue (2)
    RELAY_PING_INTERVAL_S      how often the inside is checked (10)
    RELAY_CLIENT_IP_HOP        which X-Forwarded-For entry, from the right, is
                               the visitor: 1 behind an ALB alone (the ALB
                               appends the visitor's address); 2 behind
                               CloudFront -> ALB (the ALB appends CloudFront's)

The collector (inside):

    RELAY_COLLECTOR_PRIVATE_KEY_FILE   file holding the private key, base64
    RELAY_COLLECTOR_PREVIOUS_KEY_FILE  optional: the key being rotated out
    RELAY_API_ORIGIN           the API (http://127.0.0.1:8000)
    RELAY_INGRESS_KEY_FILE     file holding the secret the API checks before it
                               opens sealed values in a relayed reply
    RELAY_REPLY_QUEUE_URLS     every reply queue a reply may be sent to
    RELAY_WORKERS              concurrent request handlers (8)
    RELAY_WRITE_BUDGET_S       a write is started only with this much time left (18)

AWS credentials come from the standard chain: an instance profile for the
bridge on EC2; IAM Roles Anywhere (`credential_process`) for the collector;
any dummy pair against the local emulator.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)

from cmp_relay import sealing

ENVIRONMENTS = ("local", "test", "staging", "production")


class ConfigError(ValueError):
    """A setting that is missing or wrong. The message names it."""


def _str(env: Mapping[str, str], name: str, default: str | None = None) -> str:
    value = env.get(name, default)
    if value is None or not str(value).strip():
        raise ConfigError(f"{name} is required")
    return str(value).strip()


def _opt(env: Mapping[str, str], name: str) -> str | None:
    value = env.get(name)
    return value.strip() if value and value.strip() else None


def _float(env: Mapping[str, str], name: str, default: float, low: float, high: float) -> float:
    raw = env.get(name)
    try:
        value = float(raw) if raw not in (None, "") else default
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number") from exc
    if not low <= value <= high:
        raise ConfigError(f"{name} must be between {low} and {high}")
    return value


def _int(env: Mapping[str, str], name: str, default: int, low: int, high: int) -> int:
    return int(_float(env, name, default, low, high))


def _bool(env: Mapping[str, str], name: str) -> bool:
    return env.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _list(env: Mapping[str, str], name: str, default: str = "") -> tuple[str, ...]:
    raw = env.get(name, default)
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _read_secret_file(env: Mapping[str, str], name: str, required: bool = True) -> str | None:
    path = _opt(env, name)
    if path is None:
        if required:
            raise ConfigError(f"{name} is required")
        return None
    file = Path(path)
    if not file.is_file():
        raise ConfigError(f"{name} names {path}, which is not a readable file")
    value = file.read_text().strip()
    if not value:
        raise ConfigError(f"{name} names an empty file")
    return value


@dataclass(frozen=True)
class Common:
    environment: str
    region: str
    endpoint_url: str | None
    request_queue_url: str
    bucket: str
    cookie_names: frozenset[str]
    csrf_header: str
    allow_dev_routes: bool

    @property
    def is_local(self) -> bool:
        return self.environment in ("local", "test")


def _common(env: Mapping[str, str]) -> Common:
    environment = _str(env, "RELAY_ENVIRONMENT", "production").lower()
    if environment not in ENVIRONMENTS:
        raise ConfigError(f"RELAY_ENVIRONMENT must be one of {', '.join(ENVIRONMENTS)}")
    endpoint_url = _opt(env, "RELAY_ENDPOINT_URL")
    if endpoint_url and environment not in ("local", "test"):
        raise ConfigError("RELAY_ENDPOINT_URL is for a local emulator only")
    allow_dev = _bool(env, "RELAY_ALLOW_DEV_ROUTES")
    if allow_dev and environment not in ("local", "test"):
        raise ConfigError("RELAY_ALLOW_DEV_ROUTES is for local development only")
    return Common(
        environment=environment,
        region=_str(env, "RELAY_REGION", "ap-south-1"),
        endpoint_url=endpoint_url,
        request_queue_url=_str(env, "RELAY_REQUEST_QUEUE_URL"),
        bucket=_str(env, "RELAY_BUCKET"),
        cookie_names=frozenset(_list(env, "RELAY_COOKIE_NAMES", "cmp_session,cmp_csrf,cmp_ticket")),
        csrf_header=_str(env, "RELAY_CSRF_HEADER", "X-CSRF-Token"),
        allow_dev_routes=allow_dev,
    )


@dataclass(frozen=True)
class BridgeSettings:
    common: Common
    host: str
    port: int
    reply_queue_url: str
    collector_public: X25519PublicKey
    deadline_s: float
    upload_deadline_s: float
    max_body_bytes: int
    reply_pollers: int
    ping_interval_s: float
    client_ip_hop: int


def bridge_settings(env: Mapping[str, str] | None = None) -> BridgeSettings:
    env = os.environ if env is None else env
    common = _common(env)
    try:
        public = sealing.load_public(_str(env, "RELAY_COLLECTOR_PUBLIC_KEY"))
    except ValueError as exc:
        raise ConfigError(f"RELAY_COLLECTOR_PUBLIC_KEY: {exc}") from exc
    deadline = _float(env, "RELAY_DEADLINE_S", 25, 2, 120)
    # Not past the front door's 60 s timeouts by default: an upload the browser
    # was told had failed must not be recorded afterwards.
    upload_deadline = _float(env, "RELAY_UPLOAD_DEADLINE_S", max(50, deadline), deadline, 600)
    return BridgeSettings(
        common=common,
        host=_str(env, "RELAY_BRIDGE_HOST", "127.0.0.1"),
        port=_int(env, "RELAY_BRIDGE_PORT", 8080, 1, 65535),
        reply_queue_url=_str(env, "RELAY_REPLY_QUEUE_URL"),
        collector_public=public,
        deadline_s=deadline,
        upload_deadline_s=upload_deadline,
        # Capped at 26 MiB: the collector reads a stored body of at most 27 MiB
        # (the sealed form is a few bytes longer), so a higher setting would
        # accept uploads the inside then refuses.
        max_body_bytes=_int(env, "RELAY_MAX_BODY_BYTES", 26 * 1024 * 1024, 1024, 26 * 1024 * 1024),
        reply_pollers=_int(env, "RELAY_REPLY_POLLERS", 2, 1, 16),
        ping_interval_s=_float(env, "RELAY_PING_INTERVAL_S", 10, 1, 300),
        client_ip_hop=_int(env, "RELAY_CLIENT_IP_HOP", 1, 1, 5),
    )


@dataclass(frozen=True)
class CollectorSettings:
    common: Common
    private_keys: tuple[X25519PrivateKey, ...]
    api_origin: str
    ingress_key: str
    reply_queue_urls: frozenset[str]
    workers: int
    write_budget_s: float


def collector_settings(env: Mapping[str, str] | None = None) -> CollectorSettings:
    env = os.environ if env is None else env
    common = _common(env)
    keys: list[X25519PrivateKey] = []
    for name, required in (
        ("RELAY_COLLECTOR_PRIVATE_KEY_FILE", True),
        ("RELAY_COLLECTOR_PREVIOUS_KEY_FILE", False),
    ):
        value = _read_secret_file(env, name, required)
        if value is None:
            continue
        try:
            keys.append(sealing.load_private(value))
        except ValueError as exc:
            raise ConfigError(f"{name}: {exc}") from exc
    ingress_key = _read_secret_file(env, "RELAY_INGRESS_KEY_FILE") or ""
    if len(ingress_key) < 32:
        raise ConfigError("RELAY_INGRESS_KEY_FILE must hold a secret of at least 32 characters")
    replies = frozenset(_list(env, "RELAY_REPLY_QUEUE_URLS"))
    if not replies:
        raise ConfigError("RELAY_REPLY_QUEUE_URLS must list every reply queue")
    api_origin = _str(env, "RELAY_API_ORIGIN", "http://127.0.0.1:8000").rstrip("/")
    if not api_origin.startswith(("http://", "https://")):
        raise ConfigError("RELAY_API_ORIGIN must be an http:// or https:// URL")
    return CollectorSettings(
        common=common,
        private_keys=tuple(keys),
        api_origin=api_origin,
        ingress_key=ingress_key,
        reply_queue_urls=replies,
        workers=_int(env, "RELAY_WORKERS", 8, 1, 64),
        write_budget_s=_float(env, "RELAY_WRITE_BUDGET_S", 18, 1, 600),
    )
