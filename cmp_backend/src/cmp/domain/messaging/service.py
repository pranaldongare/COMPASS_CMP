"""Reading, replacing and resetting the words of a message.

The catalogue in `cmp.core.messages` says what exists and what is sent by
default; this decides what the console shows, checks what the office wants to
save, records who changed what, and tells the worker's mirror to forget.
"""

from __future__ import annotations

from typing import Any

from cmp.core.errors import NotFound, ValidationFailed
from cmp.core.logging import get_logger
from cmp.core.messages import (
    CATALOGUE,
    Channel,
    Junction,
    Message,
    check_template,
    render_text,
)
from cmp.db.redis import get_redis
from cmp.db.repositories import messages as repo
from cmp.db.sql import Conn, Row
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.infrastructure.messaging import MIRROR_KEY, common_variables

log = get_logger("cmp.messaging")


def _junction(key: str) -> Junction:
    try:
        return next(j for j in CATALOGUE if j.key.value == key)
    except StopIteration:
        raise NotFound("Message") from None


def _channel(junction: Junction, channel: str) -> Channel:
    try:
        ch = Channel(channel)
    except ValueError:
        raise NotFound("Channel") from None
    if ch not in junction.channels:
        raise NotFound("Channel")
    return ch


def _channel_view(junction: Junction, ch: Channel, stored: Row | None) -> dict[str, Any]:
    default_subject, default_body = junction.default(ch)
    return {
        "channel": ch.value,
        "default_subject": default_subject,
        "default_body": default_body,
        "subject": (stored["subject"] if stored and ch is Channel.EMAIL else default_subject),
        "body": stored["body"] if stored else default_body,
        "customised": stored is not None,
        "updated_at": stored["updated_at"] if stored else None,
        "updated_by_name": stored["updated_by_name"] if stored else None,
    }


def _view(junction: Junction, stored: dict[str, Row]) -> dict[str, Any]:
    return {
        "key": junction.key.value,
        "title": junction.title,
        "description": junction.description,
        "group": junction.group,
        "variables": [
            {"name": v.name, "description": v.description, "sample": v.sample}
            for v in junction.variables
        ],
        "channels": [_channel_view(junction, ch, stored.get(ch.value)) for ch in junction.channels],
    }


async def catalogue(conn: Conn) -> list[dict[str, Any]]:
    """Every junction, with the words in force and whether they are the default."""
    rows = await repo.list_all(conn)
    by_key: dict[str, dict[str, Row]] = {}
    for row in rows:
        by_key.setdefault(str(row["key"]), {})[str(row["channel"])] = row
    return [_view(j, by_key.get(j.key.value, {})) for j in CATALOGUE]


async def one(conn: Conn, key: str) -> dict[str, Any]:
    junction = _junction(key)
    rows = await repo.list_all(conn)
    stored = {str(r["channel"]): r for r in rows if str(r["key"]) == key}
    return _view(junction, stored)


def preview(key: str, channel: str, subject: str | None, body: str) -> dict[str, Any]:
    """Render the words with sample values, without saving anything."""
    junction = _junction(key)
    ch = _channel(junction, channel)
    problems = check_template(junction.key, ch, subject, body)
    if problems:
        raise ValidationFailed("; ".join(problems), field="body", details={"problems": problems})
    values = {**common_variables(), **junction.samples}
    return {
        "channel": ch.value,
        "subject": render_text(subject, values) if subject else None,
        "body": render_text(body, values),
    }


async def _forget_mirror() -> None:
    try:
        await get_redis().delete(MIRROR_KEY)
    except Exception as exc:  # the worker refreshes within MIRROR_TTL_S anyway
        log.warning("messages.mirror_not_cleared", error=str(exc))


async def save(
    conn: Conn, *, key: str, channel: str, subject: str | None, body: str, actor_id: int
) -> dict[str, Any]:
    junction = _junction(key)
    ch = _channel(junction, channel)
    problems = check_template(junction.key, ch, subject, body)
    if problems:
        raise ValidationFailed("; ".join(problems), field="body", details={"problems": problems})

    row = await repo.upsert(
        conn,
        key=junction.key.value,
        channel=ch.value,
        subject=subject if ch is Channel.EMAIL else None,
        body=body,
        updated_by=actor_id,
    )
    await audit.record(
        conn,
        event=Event.MESSAGE_TEMPLATE_UPDATED,
        entity_type="message_template",
        entity_id=int(row["template_id"]),
        actor_user_id=actor_id,
        detail={"message": junction.key.value, "channel": ch.value, "subject": subject},
    )
    await _forget_mirror()
    log.info("messages.template_saved", message=junction.key.value, channel=ch.value)
    return await one(conn, key)


async def reset(conn: Conn, *, key: str, channel: str, actor_id: int) -> dict[str, Any]:
    junction = _junction(key)
    ch = _channel(junction, channel)
    row = await repo.delete(conn, key=junction.key.value, channel=ch.value)
    if row:
        await audit.record(
            conn,
            event=Event.MESSAGE_TEMPLATE_RESET,
            entity_type="message_template",
            entity_id=int(row["template_id"]),
            actor_user_id=actor_id,
            detail={"message": junction.key.value, "channel": ch.value},
        )
        await _forget_mirror()
        log.info("messages.template_reset", message=junction.key.value, channel=ch.value)
    return await one(conn, key)


def keys() -> list[str]:
    return [m.value for m in Message]
