"""A breach notice to somebody with no account, by a link only their mobile opens.

The product owner's decision (2026-11-20, review SCALE-7): a person a breach
affected who has no account and is reached by mobile is sent a short text with
a link, not the whole notice - the notice may be thousands of characters, and a
text takes 1,600 at most. The link opens a page on the portal that shows
nothing until a one-time code, sent by text to the number on the breach's list,
comes back. So holding the link is not enough: it must be read on that phone.

The link carries the notice and the contact and a keyed digest of the two
(HMAC under the application secret), so nothing is stored to open it and a
link cannot be made for anybody else. It opens one approved version of the
notice for one contact; the code is issued for that pair. Every way a link
can fail answers the same 404. Opening is on the breach's trail, with no actor.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Any
from uuid import UUID

from cmp.auth.authentication import otp
from cmp.auth.rate_limit import service as ratelimit
from cmp.core.config import settings
from cmp.core.errors import NotFound
from cmp.core.portal_address import portal_base
from cmp.db.repositories import breach_notices as repo
from cmp.db.sql import Conn
from cmp.domain.audit.service import Event
from cmp.domain.breach import service
from cmp.validation.contacts import indian_mobile, mask_contact

Row = dict[str, Any]

#: The page on the portal a link opens.
PORTAL_PATH = "/breach-notice"


class LinkInvalid(NotFound):
    """Every way a link can fail answers the same."""

    def __init__(self) -> None:
        super().__init__("This link does not open a notice. Contact the Privacy Office.")


def _key() -> bytes:
    secret = settings.secret_key.get_secret_value().encode("utf-8")
    return hmac.new(secret, b"cmp.breach-notice-link", hashlib.sha256).digest()


def _mac(notice: bytes, contact: bytes) -> bytes:
    return hmac.new(_key(), notice + contact, hashlib.sha256).digest()[:16]


def token(notice_uuid: str, contact_uuid: str) -> str:
    """The link's token: the notice, the contact and their digest, 64 characters."""
    notice, contact = UUID(str(notice_uuid)).bytes, UUID(str(contact_uuid)).bytes
    raw = notice + contact + _mac(notice, contact)
    return base64.urlsafe_b64encode(raw).decode("ascii")


def url(notice_uuid: str, contact_uuid: str) -> str:
    return f"{portal_base()}{PORTAL_PATH}/{token(notice_uuid, contact_uuid)}"


def _read(raw_token: str) -> tuple[str, str]:
    try:
        raw = base64.urlsafe_b64decode(raw_token.encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        raise LinkInvalid from None
    if len(raw) != 48:
        raise LinkInvalid
    notice, contact, mac = raw[:16], raw[16:32], raw[32:]
    if not hmac.compare_digest(mac, _mac(notice, contact)):
        raise LinkInvalid
    return str(UUID(bytes=notice)), str(UUID(bytes=contact))


async def open_link(conn: Conn, raw_token: str) -> Row:
    """The approved notice and the contact this link was made for, on one breach."""
    notice_uuid, contact_uuid = _read(raw_token)
    row = await repo.by_link(conn, notice_uuid=notice_uuid, contact_uuid=contact_uuid)
    if not row or not row.get("mobile"):
        raise LinkInvalid
    return row


async def _mobile(row: Row) -> str:
    from cmp.infrastructure.dkms import unseal_value

    opened = str(await unseal_value("breach_contact", "mobile", str(row["mobile"])))
    if indian_mobile(opened) is None:
        raise LinkInvalid
    return opened


async def masked_mobile(row: Row) -> str:
    return mask_contact(await _mobile(row))


def _identity(row: Row) -> str:
    return f"{row['notice_uuid']}:{row['contact_uuid']}"


async def send_code(conn: Conn, raw_token: str) -> None:
    """A code to the number on the breach's list - never one typed on the page."""
    row = await open_link(conn, raw_token)
    await ratelimit.enforce(
        "breach_notice_code",
        _identity(row),
        limit=settings.otp_requests_per_contact_per_hour,
        window_s=3600,
        message="Too many codes for this notice. Try again later.",
    )
    issued = await otp.issue(otp.Scope.BREACH_NOTICE, _identity(row))
    from cmp.tasks.authentication import send_breach_notice_code
    from cmp.tasks.dispatch import dispatch_required

    dispatch_required(send_breach_notice_code, str(row["mobile"]), issued.code, row["reference"])


async def read(conn: Conn, raw_token: str, code: str) -> Row:
    """The code proves the phone: the notice, in full. On the breach's trail."""
    row = await open_link(conn, raw_token)
    await otp.require(otp.Scope.BREACH_NOTICE, _identity(row), code)
    breach = {"breach_id": row["breach_id"], "reference": row["reference"]}
    await service.record_event(
        conn,
        breach,
        Event.BREACH_NOTICE_OPENED,
        actor_id=None,
        detail={"version": int(row["version"]), "contact": row["contact_uuid"]},
    )
    # Opened here, for this person alone, once the code has proved the phone:
    # somebody who came from a text has no session the portal could open
    # them with, and the relay's replies are opened by the API all the same.
    from cmp.infrastructure.dkms import unseal_value

    words = {
        field: str(await unseal_value("breach_notice", field, row[field]))
        for field in ("what_happened", "consequences", "measures", "protective_steps", "contact")
    }
    return {
        "reference": row["reference"],
        "version": int(row["version"]),
        "approved_at": row["approved_at"],
        **words,
    }
