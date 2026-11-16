"""The portal's address, as the administrator keeps it (0072).

See `cmp.core.portal_address` for what reads it. Here: what the console's
page shows, and the save - validated, recorded on the trail, and never
anything but an origin.
"""

from __future__ import annotations

from typing import Any

from cmp.core import portal_address as held
from cmp.core.errors import ValidationFailed
from cmp.db.repositories import portal_address as repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event

#: Shown under the field, and said when what was typed is not an address.
SHAPE = (
    "Enter the address as http:// or https:// and a host, with a port if it has "
    "one - for example http://10.20.30.40:3001 - and nothing after it."
)


async def overview(conn: Conn) -> dict[str, Any]:
    row = await repo.current(conn)
    return {
        #: What the administrator set; None while the configured one is used.
        "portal_url": row["portal_url"],
        #: The configured address, used while nothing is set.
        "configured_url": held.configured(),
        #: What links start with now.
        "in_use": row["portal_url"] or held.configured(),
        "updated_at": row["updated_at"] if row["updated_by_name"] is not None else None,
        "updated_by_name": row["updated_by_name"],
    }


async def save(conn: Conn, *, portal_url: str | None, actor_id: int) -> dict[str, Any]:
    """`portal_url` None or empty: back to the configured address."""
    before = (await repo.current(conn))["portal_url"]
    typed = (portal_url or "").strip()
    address = held.as_origin(typed) if typed else None
    if typed and address is None:
        raise ValidationFailed(SHAPE, field="portal_url")
    await repo.set_address(conn, portal_url=address, actor_id=actor_id)
    await audit.record(
        conn,
        event=Event.PORTAL_ADDRESS_CHANGED,
        entity_type="portal_address",
        entity_id=1,
        actor_user_id=actor_id,
        # An address names a machine, not a person: it is kept, so the trail
        # says where links pointed and when.
        detail={"address": address, "was": before, "changed": address != before},
    )
    return await overview(conn)
