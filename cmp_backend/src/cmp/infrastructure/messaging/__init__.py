"""Turning a junction into words and handing them to a transport.

The one way anything in this codebase sends a message is `deliver(Message.X,
to=..., **variables)`. It looks the junction up in the catalogue, applies the
office's replacement words if there are any, renders, picks the channel from
the shape of the contact, and hands the result to the email or SMS transport.
Free text never reaches a transport, which is what makes the console's list
of messages complete by construction.

Replacement words are read by a Celery worker, which is synchronous and has
no request. They come from a Redis mirror of the `message_template` table,
refreshed from the database when absent and cleared by the API on every
change; if neither is reachable the defaults are used and the failure is
logged, because a sign-in code must go out whatever else is wrong.
"""

from __future__ import annotations

import json
from typing import Any, Final

from cmp.core.config import settings
from cmp.core.logging import get_logger
from cmp.core.messages import Channel, Junction, Message, junction, render_text
from cmp.db.redis import K_CACHE
from cmp.db.redis import key as rkey

log = get_logger("cmp.messaging")

#: Where the worker reads the office's replacements from, and what the API
#: clears when one changes.
MIRROR_KEY: Final = rkey(K_CACHE, "message_templates")
MIRROR_TTL_S: Final = 300

Overrides = dict[str, dict[str, str | None]]

_redis_client: Any = None


def _redis() -> Any:
    global _redis_client
    if _redis_client is None:
        import redis

        _redis_client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
        )
    return _redis_client


def _read_overrides_from_db() -> Overrides:
    import psycopg

    try:
        with psycopg.connect(settings.dsn, connect_timeout=3) as conn:
            rows = conn.execute(
                "SELECT key, channel, subject, body FROM message_template"
            ).fetchall()
    except Exception as exc:
        log.error("messages.overrides_unavailable", error=str(exc))
        return {}
    return {f"{k}:{c}": {"subject": s, "body": b} for k, c, s, b in rows}


def load_overrides() -> Overrides:
    """The office's replacement words, from the mirror or the table."""
    try:
        raw = _redis().get(MIRROR_KEY)
        if raw is not None:
            return dict(json.loads(raw))
    except Exception as exc:
        log.warning("messages.mirror_unavailable", error=str(exc))
    overrides = _read_overrides_from_db()
    try:
        _redis().set(MIRROR_KEY, json.dumps(overrides), ex=MIRROR_TTL_S)
    except Exception as exc:
        log.warning("messages.mirror_not_written", error=str(exc))
    return overrides


def common_variables() -> dict[str, str]:
    """Available to every template, filled from configuration."""
    return {
        "organisation": settings.organisation_name,
        "portal_url": settings.public_base_url.rstrip("/"),
        "console_url": settings.console_base_url.rstrip("/"),
    }


def resolve(
    key: Message | str, channel: Channel | str, overrides: Overrides | None = None
) -> tuple[str | None, str]:
    """The template in force: the office's words if set, else the default."""
    j = junction(key)
    ch = Channel(channel)
    subject, body = j.default(ch)
    stored = (overrides if overrides is not None else load_overrides()).get(
        f"{j.key.value}:{ch.value}"
    )
    if stored and stored.get("body"):
        return (stored.get("subject") if ch is Channel.EMAIL else None), str(stored["body"])
    return subject, body


def render(
    key: Message | str,
    channel: Channel | str,
    variables: dict[str, Any],
    *,
    overrides: Overrides | None = None,
) -> tuple[str | None, str]:
    subject, body = resolve(key, channel, overrides)
    values = {**common_variables(), **variables}
    return (render_text(subject, values) if subject else None), render_text(body, values)


def channel_for(contact: str) -> Channel:
    return Channel.EMAIL if "@" in contact else Channel.SMS


def deliver(key: Message, *, to: str, **variables: Any) -> dict[str, Any]:
    """Render one junction for one contact and send it. Failure raises.

    A transport that swallowed an error and returned quietly would turn a
    retryable outage into silent loss, so nothing is caught here; the task's
    retry policy decides what happens next.
    """
    j: Junction = junction(key)
    ch = channel_for(to)
    if ch not in j.channels:
        raise ValueError(f"'{j.key.value}' is not sent by {ch.value}; contact is {to[:3]}…")

    subject, body = render(key, ch, variables)
    if ch is Channel.SMS:
        from cmp.infrastructure.sms import build_sms_transport

        result = dict(build_sms_transport().send(to=to, body=body))
    else:
        from cmp.infrastructure.email import build_email_transport

        assert subject is not None
        result = dict(build_email_transport().send(to=to, subject=subject, body=body))
    result["message"] = j.key.value
    return result


__all__ = [
    "MIRROR_KEY",
    "Overrides",
    "channel_for",
    "common_variables",
    "deliver",
    "load_overrides",
    "render",
    "resolve",
]
