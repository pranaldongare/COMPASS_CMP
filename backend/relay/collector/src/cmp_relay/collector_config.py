"""The collector's settings (inside), read once at start.

Its own, besides the shared ones in `config`:

    RELAY_COLLECTOR_PRIVATE_KEY_FILE   file holding the private key, base64
    RELAY_COLLECTOR_PREVIOUS_KEY_FILE  optional: the key being rotated out
    RELAY_API_ORIGIN           the API (http://127.0.0.1:8000)
    RELAY_INGRESS_KEY_FILE     file holding the secret the API checks before it
                               opens sealed values in a relayed reply
    RELAY_REPLY_QUEUE_URLS     every reply queue a reply may be sent to
    RELAY_WORKERS              concurrent request handlers (8)
    RELAY_WRITE_BUDGET_S       a write is started only with this much time left (18)

`collector/.env.example` lists them all.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from cmp_relay import sealing
from cmp_relay.config import (
    Common,
    ConfigError,
    common_settings,
    get_float,
    get_int,
    get_list,
    get_str,
    read_secret_file,
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
    common = common_settings(env)
    keys: list[X25519PrivateKey] = []
    for name, required in (
        ("RELAY_COLLECTOR_PRIVATE_KEY_FILE", True),
        ("RELAY_COLLECTOR_PREVIOUS_KEY_FILE", False),
    ):
        value = read_secret_file(env, name, required)
        if value is None:
            continue
        try:
            keys.append(sealing.load_private(value))
        except ValueError as exc:
            raise ConfigError(f"{name}: {exc}") from exc
    ingress_key = read_secret_file(env, "RELAY_INGRESS_KEY_FILE") or ""
    if len(ingress_key) < 32:
        raise ConfigError("RELAY_INGRESS_KEY_FILE must hold a secret of at least 32 characters")
    replies = frozenset(get_list(env, "RELAY_REPLY_QUEUE_URLS"))
    if not replies:
        raise ConfigError("RELAY_REPLY_QUEUE_URLS must list every reply queue")
    api_origin = get_str(env, "RELAY_API_ORIGIN", "http://127.0.0.1:8000").rstrip("/")
    if not api_origin.startswith(("http://", "https://")):
        raise ConfigError("RELAY_API_ORIGIN must be an http:// or https:// URL")
    return CollectorSettings(
        common=common,
        private_keys=tuple(keys),
        api_origin=api_origin,
        ingress_key=ingress_key,
        reply_queue_urls=replies,
        workers=get_int(env, "RELAY_WORKERS", 8, 1, 64),
        write_budget_s=get_float(env, "RELAY_WRITE_BUDGET_S", 18, 1, 600),
    )
