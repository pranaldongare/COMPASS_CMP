"""Where DataVault is, and the key it asks for (0070).

Kept by the administrator alone, on a page of its own. The address could not
be written into the code or its configuration, so it is a setting; and since
a setting somebody can change is a place the platform can be pointed at, the
change is on the trail - that the address or the key changed, never either
one. The key is encrypted with the application's own key and is never served
again: the page is told only that one is set.

Switched off, or with no address, the platform calls nothing and the request
page says DataVault is not set up.
"""

from __future__ import annotations

import re
from typing import Any

from cmp.core.errors import ValidationFailed
from cmp.core.security import seal_token, unseal_token
from cmp.db.repositories import datavault as repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.infrastructure.datavault import usable_base_url

Row = dict[str, Any]

DEFAULT_HEADER = "X-API-Key"
_HEADER = re.compile(r"^[A-Za-z0-9-]{1,64}$")
#: Headers the key may not be sent as: the call's own.
_RESERVED = frozenset({"host", "content-length", "content-type", "accept", "connection"})


def _view(row: Row) -> Row:
    return {
        "base_url": row["base_url"],
        "api_key_set": row["api_key_sealed"] is not None,
        "api_key_header": row["api_key_header"],
        "enabled": bool(row["enabled"]),
        "updated_at": row["updated_at"] if row["updated_by_name"] is not None else None,
        "updated_by_name": row["updated_by_name"],
    }


async def overview(conn: Conn) -> Row:
    return _view(await repo.connection(conn))


async def ready(conn: Conn) -> Row | None:
    """What a call needs - address, key, header - or None while DataVault is
    switched off or has no address."""
    row = await repo.connection(conn)
    if not row["enabled"] or not row["base_url"]:
        return None
    return {
        "base_url": str(row["base_url"]),
        "api_key": unseal_token(bytes(row["api_key_sealed"])) if row["api_key_sealed"] else None,
        "api_key_header": str(row["api_key_header"]),
    }


async def save(
    conn: Conn,
    *,
    base_url: str | None,
    api_key: str | None,
    clear_api_key: bool,
    api_key_header: str | None,
    enabled: bool,
    actor_id: int,
) -> Row:
    """`api_key` None keeps the key that is there; `clear_api_key` removes it."""
    before = await repo.connection(conn)
    address: str | None = None
    if base_url and base_url.strip():
        address = usable_base_url(base_url)
        if address is None:
            raise ValidationFailed(
                "Enter DataVault's address as http:// or https:// and a host, with no "
                "user name, question mark or # in it."
            )
    if enabled and address is None:
        raise ValidationFailed("Enter DataVault's address before switching it on.")
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
    await repo.set_connection(
        conn,
        base_url=address,
        api_key_header=header,
        enabled=enabled,
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
        # What changed, never the address or the key.
        detail={
            "address_changed": address != before["base_url"],
            "key_changed": not keep,
            "key_set": bool(key) or (keep and before["api_key_sealed"] is not None),
            "header_changed": header != before["api_key_header"],
            "enabled": enabled,
            "was_enabled": bool(before["enabled"]),
        },
    )
    return await overview(conn)
