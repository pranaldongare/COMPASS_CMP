"""Where DataVault is, the key it asks for, and what it is told by itself (0070, 0071).

Kept by the administrator alone, on a page of its own. The addresses could not
be written into the code or its configuration, so they are settings; and since
a setting somebody can change is a place the platform can be pointed at, every
change is on the trail - that an address or the key changed, never either one.
The key is encrypted with the application's own key and is never served again:
the page is told only that one is set.

Two addresses, because DataVault answers them in two places: the lookup's, and
the one erasures and consent changes go to. One key for both. One switch for
how a person, a consent and a project are named in every call (`ids`). And one
for whether DataVault is told of consent changes at all: nothing goes out by
itself until the administrator says so, and what was on record before that is
never read (`consent_changes_after`), nor a validity that had run out by then
reported (`consent_changes_since`), so switching it on tells DataVault nothing
about the past.

Switched off, or with no address, the platform calls nothing and the request
page says DataVault is not set up.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from cmp.core.errors import ValidationFailed
from cmp.core.security import seal_token, unseal_token
from cmp.db.pool import across_offices
from cmp.db.repositories import datavault as repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.domain.datavault import ids
from cmp.infrastructure.datavault import usable_base_url

Row = dict[str, Any]

DEFAULT_HEADER = "X-API-Key"
_HEADER = re.compile(r"^[A-Za-z0-9-]{1,64}$")
#: Headers the key may not be sent as: the call's own.
_RESERVED = frozenset({"host", "content-length", "content-type", "accept", "connection"})

#: Why a consent change was not delivered, in the administrator's words.
FAILURES: dict[str, str] = {
    "timeout": "DataVault did not answer in time.",
    "unreachable": "DataVault could not be reached.",
    "unreadable": "DataVault answered, but not in the agreed format.",
    "status_400": "DataVault refused the message as badly formed.",
    "status_401": "DataVault refused the key.",
    "status_403": "DataVault refused the key.",
    "status_404": "DataVault does not know this address.",
}


def failure_said(code: str) -> str:
    if code in FAILURES:
        return FAILURES[code]
    if code.startswith("status_"):
        return f"DataVault answered with an error ({code.removeprefix('status_')})."
    return "The message was not delivered."


@dataclass(frozen=True)
class Link:
    """The connection as a call needs it, while it is switched on."""

    base_url: str | None
    erasure_url: str | None
    api_key: str | None
    api_key_header: str
    id_format: str
    consent_changes: bool
    #: No consent up to this one is read for consent changes, and no validity
    #: that ran out before this time is reported: where they start (None:
    #: never switched on).
    consent_changes_after: int
    consent_changes_since: datetime | None


def _view(row: Row, health: Row) -> Row:
    failure = health["last_failure"]
    return {
        "base_url": row["base_url"],
        "erasure_url": row["erasure_url"],
        "api_key_set": row["api_key_sealed"] is not None,
        "api_key_header": row["api_key_header"],
        "enabled": bool(row["enabled"]),
        "id_format": row["id_format"],
        "consent_changes": bool(row["consent_changes"]),
        "consent_changes_waiting": int(health["waiting"] or 0),
        "consent_changes_last_delivered_at": health["last_delivered_at"],
        "consent_changes_last_failure": failure_said(str(failure)) if failure else None,
        "updated_at": row["updated_at"] if row["updated_by_name"] is not None else None,
        "updated_by_name": row["updated_by_name"],
    }


async def overview(conn: Conn) -> Row:
    """What the administrator's page shows. The queue's counts are read across
    both offices: how many messages wait says nothing of any consent."""
    row = await repo.connection(conn)
    async with across_offices(conn):
        health = await repo.queue_health(conn)
    return _view(row, health)


async def link(conn: Conn) -> Link | None:
    """The connection, or None while it is switched off."""
    row = await repo.connection(conn)
    if not row["enabled"]:
        return None
    return Link(
        base_url=str(row["base_url"]) if row["base_url"] else None,
        erasure_url=str(row["erasure_url"]) if row["erasure_url"] else None,
        api_key=unseal_token(bytes(row["api_key_sealed"])) if row["api_key_sealed"] else None,
        api_key_header=str(row["api_key_header"]),
        id_format=str(row["id_format"]),
        consent_changes=bool(row["consent_changes"]),
        consent_changes_after=int(row["consent_changes_after"] or 0),
        consent_changes_since=row["consent_changes_since"],
    )


async def ready(conn: Conn) -> Link | None:
    """What a lookup needs, or None while DataVault is switched off or the
    lookup has no address."""
    found = await link(conn)
    return found if found is not None and found.base_url else None


async def for_erasure(conn: Conn) -> Link | None:
    """What an erasure needs, or None while it has no address."""
    found = await link(conn)
    return found if found is not None and found.erasure_url else None


async def for_consent_changes(conn: Conn) -> Link | None:
    """What a consent change needs, or None while they are not sent."""
    found = await for_erasure(conn)
    return found if found is not None and found.consent_changes else None


def _address(raw: str | None, what: str) -> str | None:
    if not raw or not raw.strip():
        return None
    address = usable_base_url(raw)
    if address is None:
        raise ValidationFailed(
            f"Enter {what} as http:// or https:// and a host, with no user name, "
            "question mark or # in it."
        )
    return address


async def save(
    conn: Conn,
    *,
    base_url: str | None,
    api_key: str | None,
    clear_api_key: bool,
    api_key_header: str | None,
    enabled: bool,
    actor_id: int,
    erasure_url: str | None = None,
    id_format: str | None = None,
    consent_changes: bool = False,
) -> Row:
    """`api_key` None keeps the key that is there; `clear_api_key` removes it."""
    before = await repo.connection(conn)
    address = _address(base_url, "DataVault's address")
    erasure = _address(erasure_url, "the erasure address")
    if enabled and address is None:
        raise ValidationFailed("Enter DataVault's address before switching it on.")
    if consent_changes and erasure is None:
        raise ValidationFailed(
            "Enter the erasure address before switching consent changes on: they go there."
        )
    naming = id_format or str(before["id_format"])
    if naming not in ids.FORMATS:
        raise ValidationFailed("Choose numeric IDs or UUIDs.", field="id_format")
    header = (api_key_header or DEFAULT_HEADER).strip()
    if not _HEADER.match(header) or header.lower() in _RESERVED:
        raise ValidationFailed(
            "The header name may hold letters, digits and hyphens only, and cannot be "
            "one the call itself sets."
        )
    key = api_key.strip() if api_key else None
    if key is not None and (len(key) > 4000 or any(ord(c) < 32 or ord(c) > 126 for c in key)):
        raise ValidationFailed("The key may hold printable characters only.")
    keep = key is None and not clear_api_key
    # Where consent changes start from, settled the first time they are
    # switched on: the newest consent on record then, whichever office's.
    after: int | None = None
    if consent_changes and before["consent_changes_after"] is None:
        async with across_offices(conn):
            after = await repo.highest_consent(conn)
    await repo.set_connection(
        conn,
        base_url=address,
        erasure_url=erasure,
        api_key_header=header,
        enabled=enabled,
        id_format=naming,
        consent_changes=consent_changes,
        consent_changes_after=after,
        actor_id=actor_id,
        api_key_sealed=seal_token(key) if key else None,
        keep_key=keep,
    )
    await audit.record(
        conn,
        event=Event.DATAVAULT_CONNECTION_CHANGED,
        entity_type="datavault_connection",
        entity_id=1,
        actor_user_id=actor_id,
        # What changed, never an address or the key.
        detail={
            "address_changed": address != before["base_url"],
            "erasure_address_changed": erasure != before["erasure_url"],
            "key_changed": not keep,
            "key_set": bool(key) or (keep and before["api_key_sealed"] is not None),
            "header_changed": header != before["api_key_header"],
            "enabled": enabled,
            "was_enabled": bool(before["enabled"]),
            "id_format": naming,
            "id_format_was": str(before["id_format"]),
            "consent_changes": consent_changes,
            "consent_changes_were": bool(before["consent_changes"]),
        },
    )
    # Where erasures and consent changes go is a setting a stolen session would
    # want to change; everybody who answers for the platform hears (2026-11-20).
    from cmp.domain import alerts

    await alerts.setting_changed(conn, setting="the DataVault connection", actor_id=actor_id)
    return await overview(conn)
