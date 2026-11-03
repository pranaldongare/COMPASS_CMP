"""The bridge's settings (AWS side), read once at start.

Its own, besides the shared ones in `config`:

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

`bridge/.env.example` lists them all.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey

from cmp_relay import sealing
from cmp_relay.config import (
    Common,
    ConfigError,
    common_settings,
    get_float,
    get_int,
    get_str,
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
    common = common_settings(env)
    try:
        public = sealing.load_public(get_str(env, "RELAY_COLLECTOR_PUBLIC_KEY"))
    except ValueError as exc:
        raise ConfigError(f"RELAY_COLLECTOR_PUBLIC_KEY: {exc}") from exc
    deadline = get_float(env, "RELAY_DEADLINE_S", 25, 2, 120)
    # Not past the front door's 60 s timeouts by default: an upload the browser
    # was told had failed must not be recorded afterwards.
    upload_deadline = get_float(env, "RELAY_UPLOAD_DEADLINE_S", max(50, deadline), deadline, 600)
    return BridgeSettings(
        common=common,
        host=get_str(env, "RELAY_BRIDGE_HOST", "127.0.0.1"),
        port=get_int(env, "RELAY_BRIDGE_PORT", 8080, 1, 65535),
        reply_queue_url=get_str(env, "RELAY_REPLY_QUEUE_URL"),
        collector_public=public,
        deadline_s=deadline,
        upload_deadline_s=upload_deadline,
        # Capped at 26 MiB: the collector reads a stored body of at most 27 MiB
        # (the sealed form is a few bytes longer), so a higher setting would
        # accept uploads the inside then refuses.
        max_body_bytes=get_int(
            env, "RELAY_MAX_BODY_BYTES", 26 * 1024 * 1024, 1024, 26 * 1024 * 1024
        ),
        reply_pollers=get_int(env, "RELAY_REPLY_POLLERS", 2, 1, 16),
        ping_interval_s=get_float(env, "RELAY_PING_INTERVAL_S", 10, 1, 300),
        client_ip_hop=get_int(env, "RELAY_CLIENT_IP_HOP", 1, 1, 5),
    )
