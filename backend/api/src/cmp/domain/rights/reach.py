# ruff: noqa: E501 - the table in the docstring is read as a table; wrapped, it is not.
"""How a rights ticket's holder is reached, and answers (0049, 2026-10-08).

Decided with the product owner on 2026-10-08:

| The holder's responder | Reached | Answers |
|---|---|---|
| an account that signs in to the console | the ticket in My tasks, the email in full | in the console |
| an address on one of the organisation's own domains, with no console login | a temporary login, as a breach ticket's holder (S3-09), then as above | in the console |
| any other address - a vendor, a third-party processor | an email carrying a link and nothing of the request | on the portal, by the link, after a one-time code to the address on the ticket |

The internal domains are BREACH_TICKET_EMAIL_DOMAINS - one list of what the
organisation's own addresses are. The choice is made when the ticket is sent
(`place`), so the office may name and rename a responder freely until then.

An external holder's link is a token whose keyed fingerprint is on the holder
(`link_token`) and whose sealed copy (`link_token_sealed`) lets a reminder
carry the same link. A ticket sent to somebody else gets a new link; the old
stops working.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from cmp.core.config import settings
from cmp.core.errors import ValidationFailed
from cmp.core.security import new_token, seal_token, token_fingerprint, unseal_token
from cmp.db.repositories import rights as repo
from cmp.db.sql import Conn
from cmp.domain.breach import access
from cmp.infrastructure.dkms import unseal_value
from cmp.validation import mask_contact

Row = dict[str, Any]


def fingerprint(raw: str) -> str:
    return token_fingerprint(raw)[:64]


def external(holder: Row) -> bool:
    """Reached by a link on the portal: emails to it carry nothing of the request."""
    return holder.get("channel") != "portal" and bool(holder.get("link_token_sealed"))


def link_url(holder: Row) -> str | None:
    raw = unseal_token(holder.get("link_token_sealed"))
    return f"{settings.public_base_url.rstrip('/')}/ticket/{raw}" if raw else None


async def mint_link(conn: Conn, holder_id: int) -> None:
    """A new link for this holder; any earlier one stops working."""
    raw = new_token(32)
    await repo.update_holder(
        conn,
        holder_id,
        link_token=fingerprint(raw),
        link_token_sealed=seal_token(raw),
        link_issued_at=datetime.now(UTC),
    )


async def address(holder: Row) -> str | None:
    value = await unseal_value(
        "rights_request_holder", "responder_contact", holder.get("responder_contact")
    )
    return str(value).strip() or None if value else None


async def masked_address(holder: Row) -> str | None:
    to = await address(holder)
    return mask_contact(to) if to else None


async def place(conn: Conn, row: Row, holder: Row, *, actor_id: int) -> Row:
    """Decide, as the ticket goes, how this holder is reached; return it fresh.

    A holder already on an account is left as it is. Otherwise the address
    decides: an internal one is given a console login - a temporary one for
    somebody who does not sign in already - and an external one a link.
    """
    holder_id = int(holder["holder_id"])
    if holder.get("channel") == "portal":
        return holder
    to = await address(holder)
    if not to or "@" not in to:
        # Nobody to send to: the office reaches them itself and records it.
        return holder
    if access.internal(to):
        name = await unseal_value(
            "rights_request_holder", "responder_name", holder.get("responder_name")
        )
        try:
            user, created = await access.resolve(
                conn, full_name=str(name) if name else None, email=to, mobile=None
            )
        except ValidationFailed as refused:
            raise ValidationFailed(
                f"{holder['label']}: {refused.message}", field="responder_name"
            ) from refused
        temporary = access.needs_grant(user)
        await repo.update_holder(
            conn, holder_id, channel="portal", responder_user_id=int(user["id"])
        )
        if temporary:
            await access.grant_for_holder(
                conn,
                holder_id=holder_id,
                reference=str(row["reference"]),
                user=user,
                created=created,
                actor_id=actor_id,
            )
    elif not holder.get("link_token_sealed"):
        await mint_link(conn, holder_id)
    fresh = await repo.holder_by_uuid(conn, int(row["request_id"]), str(holder["holder_uuid"]))
    assert fresh is not None
    return fresh
