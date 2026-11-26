"""An outside holder answers a retention action by a link (ADR 0047).

A processor whose respondent has no console login is asked by email, with a
link to the portal (`/retention/{token}`), as a rights holder is (0049).
Opening the link shows only the review's reference, the processor and where
a code will go; the code goes to the address the link was sent to - never one
typed on the page - so holding the link is not enough.

The code opens an hour on that one action: a random value in the same
HttpOnly, SameSite=Strict cookie a holder ticket uses (the relay already lets
it cross), its fingerprint in Redis under a key of its own naming the action
and the link - so a ticket's hour never opens an action, nor an action's a
ticket. Every request through the portal reaches the API by the bridge, SQS
and the collector (ADR 0035); the routes are on the relay's allow-list.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from cmp.auth.authentication import otp
from cmp.auth.rate_limit import service as ratelimit
from cmp.core.config import settings
from cmp.core.errors import NotFound, Unauthenticated
from cmp.core.portal_address import portal_base
from cmp.core.security import new_token, seal_token, token_fingerprint, unseal_token
from cmp.db.redis import K_RETENTION_LINK, get_redis
from cmp.db.redis import key as rkey
from cmp.db.repositories import retention as repo
from cmp.db.sql import Conn
from cmp.infrastructure.dkms import unseal_value
from cmp.validation import mask_contact

Row = dict[str, Any]


class LinkInvalid(NotFound):
    """Every way a link can fail answers the same."""

    def __init__(self) -> None:
        super().__init__(
            "This link does not open a retention review. Ask the Privacy Office for a new one."
        )


def fingerprint(raw: str) -> str:
    return token_fingerprint(raw)


async def _address(conn: Conn, action: Row) -> str | None:
    if not action.get("respondent_id"):
        return None
    sealed = await repo.respondent_contact(conn, int(action["respondent_id"]))
    if sealed is None:
        return None
    value = await unseal_value("processor_respondent", "contact", sealed)
    text = str(value or "").strip()
    return text if "@" in text else None


async def _url(conn: Conn, action: Row) -> str:
    """The action's link, minted the first time it is needed."""
    if action.get("link_token_sealed"):
        raw = unseal_token(bytes(action["link_token_sealed"]))
    else:
        raw = new_token(32)
        await repo.set_action(
            conn,
            int(action["action_id"]),
            link_token=fingerprint(raw),
            link_token_sealed=seal_token(raw),
            link_issued_at=datetime.now(UTC),
        )
    return f"{portal_base()}/retention/{raw}"


async def send(
    conn: Conn, *, action: Row, review: Row, again: str | None = None, overdue: bool = False
) -> None:
    """Email the link to the respondent's address - first, again after a
    send-back, or once overdue."""
    from cmp.domain.alerts import _queue, day
    from cmp.tasks.notifications import updates as tasks

    to = await _address(conn, action)
    if to is None:
        return
    note = (
        f"Your earlier answer was sent back: {again}\n\n"
        if again
        else "This was due and has not been answered yet.\n\n"
        if overdue
        else ""
    )
    _queue(
        tasks.send_retention_action_link,
        to,
        str(action["label"]),
        str(review["reference"]),
        str(review["project_name"]),
        str(review["purpose_name"]),
        int(review["people"]),
        day(action["due_at"]),
        note,
        await _url(conn, action),
    )


async def open_link(conn: Conn, raw: str) -> tuple[Row, Row]:
    action = await repo.action_by_link(conn, fingerprint(raw))
    if action is None or action["channel"] != "link":
        raise LinkInvalid
    review = await repo.review_by_id(conn, int(action["review_id"]))
    if review is None:
        raise LinkInvalid
    return action, review


async def masked_address(conn: Conn, action: Row) -> str | None:
    to = await _address(conn, action)
    return mask_contact(to) if to else None


async def send_code(conn: Conn, raw: str) -> None:
    from cmp.domain.alerts import _queue
    from cmp.tasks.notifications import updates as tasks

    action, review = await open_link(conn, raw)
    await ratelimit.enforce(
        "retention_link_code",
        str(action["action_uuid"]),
        limit=settings.otp_requests_per_contact_per_hour,
        window_s=3600,
        message="Too many codes for this review. Try again later.",
    )
    to = await _address(conn, action)
    if not to:
        raise LinkInvalid
    issued = await otp.issue(otp.Scope.RETENTION_LINK, str(action["action_uuid"]))
    _queue(tasks.send_retention_link_code, to, issued.code, str(review["reference"]))


async def verify(conn: Conn, raw: str, code: str) -> str:
    action, review = await open_link(conn, raw)
    await otp.require(otp.Scope.RETENTION_LINK, str(action["action_uuid"]), code)
    value = new_token(32)
    await get_redis().set(
        rkey(K_RETENTION_LINK, token_fingerprint(value)),
        json.dumps({"action_id": int(action["action_id"]), "link": fingerprint(raw)}),
        ex=settings.holder_ticket_session_s,
    )
    from cmp.domain.audit import service as audit
    from cmp.domain.audit.service import Event

    await audit.record(
        conn,
        event=Event.RETENTION_LINK_OPENED,
        entity_type="retention_review",
        entity_id=int(review["review_id"]),
        actor_user_id=None,
        detail={"reference": review["reference"], "action": str(action["action_uuid"])},
    )
    return value


async def signed_in(action: Row, raw: str, cookie: str | None) -> bool:
    if not cookie:
        return False
    stored = await get_redis().get(rkey(K_RETENTION_LINK, token_fingerprint(cookie)))
    if not stored:
        return False
    held = json.loads(stored)
    return bool(
        held.get("action_id") == int(action["action_id"]) and held.get("link") == fingerprint(raw)
    )


async def holder_in(conn: Conn, raw: str, cookie: str | None) -> tuple[Row, Row]:
    action, review = await open_link(conn, raw)
    if not await signed_in(action, raw, cookie):
        raise Unauthenticated("Enter the code sent to you to open this review", code="code_needed")
    return action, review


async def end(cookie: str | None) -> None:
    if cookie:
        await get_redis().delete(rkey(K_RETENTION_LINK, token_fingerprint(cookie)))
