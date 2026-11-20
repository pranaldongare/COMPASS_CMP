"""Reading, replacing and resetting the words of a message.

The catalogue in `cmp.core.messages` says what exists and what is sent by
default; this decides what the console shows, checks what the office wants to
save, records who changed what, and tells the worker's mirror to forget.
"""

from __future__ import annotations

from typing import Any

from cmp.core.errors import Forbidden, NotFound, ValidationFailed
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
from cmp.infrastructure.email.transport import MAX_CC
from cmp.infrastructure.messaging import COPIES_KEY, MIRROR_KEY, common_variables

log = get_logger("cmp.messaging")


def _junction(key: str) -> Junction:
    try:
        return next(j for j in CATALOGUE if j.key.value == key)
    except StopIteration:
        raise NotFound("Message") from None


#: How a role is named where the console says who keeps a message.
_KEEPER_TITLES = {"admin": "Administrator", "dpo": "Data Protection Officer", "legal": "Legal PoC"}


def may_edit(junction: Junction, role: str | None) -> bool:
    """Whether this role may change the message's words and copies. `None` is
    the platform itself (a script, a test), which the routes never pass."""
    return role is None or str(role) in junction.editors


def _require_editor(junction: Junction, role: str | None) -> None:
    if not may_edit(junction, role):
        keepers = ", ".join(_KEEPER_TITLES[r] for r in sorted(junction.editors))
        raise Forbidden(f"'{junction.title}' is kept by: {keepers}")


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


def _view(
    junction: Junction,
    stored: dict[str, Row],
    copies: list[Row] | None = None,
    role: str | None = None,
) -> dict[str, Any]:
    return {
        "key": junction.key.value,
        # Who keeps its words (2026-11-20): the administrator and the DPO keep
        # every message; the Legal PoC also keeps those with legal weight.
        "editors": [_KEEPER_TITLES[r] for r in sorted(junction.editors)],
        "editable": may_edit(junction, role),
        "title": junction.title,
        "description": junction.description,
        "group": junction.group,
        # Who it may be copied to by email, and who it is (0046). Sealed; the
        # console opens each `email` like any other.
        "copyable": junction.copyable,
        "attachable": junction.attachable,
        "copies": [{"email": c["address"]} for c in (copies or [])] if junction.copyable else [],
        "variables": [
            {"name": v.name, "description": v.description, "sample": v.sample}
            for v in junction.variables
        ],
        "channels": [_channel_view(junction, ch, stored.get(ch.value)) for ch in junction.channels],
    }


async def catalogue(conn: Conn, *, role: str | None = None) -> list[dict[str, Any]]:
    """Every junction, with the words in force and whether they are the default."""
    rows = await repo.list_all(conn)
    by_key: dict[str, dict[str, Row]] = {}
    for row in rows:
        by_key.setdefault(str(row["key"]), {})[str(row["channel"])] = row
    copied: dict[str, list[Row]] = {}
    for c in await repo.copies(conn):
        copied.setdefault(str(c["key"]), []).append(c)
    return [_view(j, by_key.get(j.key.value, {}), copied.get(j.key.value), role) for j in CATALOGUE]


async def one(conn: Conn, key: str, *, role: str | None = None) -> dict[str, Any]:
    junction = _junction(key)
    rows = await repo.list_all(conn)
    stored = {str(r["channel"]): r for r in rows if str(r["key"]) == key}
    copied = [c for c in await repo.copies(conn) if str(c["key"]) == key]
    return _view(junction, stored, copied, role)


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


async def _told(conn: Conn, setting: str, actor_id: int) -> None:
    """A message's words or copies are what people are told; a change to them
    is told to everybody who answers for the platform (2026-11-20)."""
    from cmp.domain import alerts

    await alerts.setting_changed(conn, setting=setting, actor_id=actor_id)


async def _forget_mirror() -> None:
    try:
        await get_redis().delete(MIRROR_KEY, COPIES_KEY)
    except Exception as exc:  # the worker refreshes within MIRROR_TTL_S anyway
        log.warning("messages.mirror_not_cleared", error=str(exc))


async def save(
    conn: Conn,
    *,
    key: str,
    channel: str,
    subject: str | None,
    body: str,
    actor_id: int,
    role: str | None = None,
) -> dict[str, Any]:
    junction = _junction(key)
    _require_editor(junction, role)
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
    await _told(conn, f"the words of the message '{junction.title}' ({ch.value})", actor_id)
    return await one(conn, key, role=role)


async def reset(
    conn: Conn, *, key: str, channel: str, actor_id: int, role: str | None = None
) -> dict[str, Any]:
    junction = _junction(key)
    _require_editor(junction, role)
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
        await _told(
            conn,
            f"the words of the message '{junction.title}' ({ch.value}), back to the default",
            actor_id,
        )
    return await one(conn, key, role=role)


async def set_copies(
    conn: Conn, *, key: str, addresses: list[str], actor_id: int, role: str | None = None
) -> dict[str, Any]:
    """Who a message is copied to by email: up to five addresses, only on a
    message the catalogue lets be copied."""
    junction = _junction(key)
    _require_editor(junction, role)
    if not junction.copyable:
        raise ValidationFailed(
            "This message cannot be copied: it carries a code or a link, or a person's own "
            "record, and a copy would hand it to somebody else",
            field="addresses",
        )
    seen: list[str] = []
    for raw in addresses:
        address = raw.strip().lower()
        if not address:
            continue
        local, _, domain = address.partition("@")
        if not local or "." not in domain or len(address) > 255 or " " in address:
            raise ValidationFailed(f"Not an email address: {raw[:60]}", field="addresses")
        if address not in seen:
            seen.append(address)
    if len(seen) > MAX_CC:
        raise ValidationFailed(f"At most {MAX_CC} addresses", field="addresses")
    await repo.replace_copies(conn, key=junction.key.value, addresses=seen, added_by=actor_id)
    await audit.record(
        conn,
        event=Event.MESSAGE_COPIES_UPDATED,
        entity_type="message_template",
        entity_id=0,
        actor_user_id=actor_id,
        detail={"message": junction.key.value, "copies": len(seen)},
    )
    await _forget_mirror()
    log.info("messages.copies_saved", message=junction.key.value, copies=len(seen))
    await _told(conn, f"who the message '{junction.title}' is copied to", actor_id)
    return await one(conn, key, role=role)


def keys() -> list[str]:
    return [m.value for m in Message]
