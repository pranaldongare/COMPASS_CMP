"""The address every link to the data principal's portal starts with.

`PUBLIC_BASE_URL` until the administrator sets another (0072, the console's
"Portal address" page). A deployment with no domain name yet is reached at an
IP that keeps changing; the setting follows it without a file edited or a
service restarted.

`portal_base()` is what builds a link, everywhere: a consent link shown to
staff, the public link for reporting a breach, a holder's ticket, and every
link in the platform's mail. It is called from plain functions as well as
coroutines, in the API and in the worker, so it is not a coroutine: the value
is kept in the process for `TTL_S` and read again, over a short connection of
its own, when that runs out. A changed address is therefore everywhere within
`TTL_S`, and at once in the process that saved it (`remember`). If the
database cannot be read, the last value known stands, or the configured one.
"""

from __future__ import annotations

import re
import time
from typing import Final
from urllib.parse import urlsplit

import psycopg

from cmp.core.config import settings
from cmp.core.logging import get_logger

log = get_logger("cmp.portal_address")

#: How long a process trusts what it last read.
TTL_S: Final = 15.0

_ORIGIN = re.compile(r"^https?://[^/?#@\s]+$")

#: (the address set, or None for "use the configured one"; when it was read).
_held: tuple[str | None, float] | None = None


def as_origin(raw: str | None) -> str | None:
    """`raw` as a scheme, a host and perhaps a port - or None if it is not
    one. No path, query, fragment or user: links are made by appending a path
    to it, and an address that carried one would send people somewhere else."""
    if raw is None:
        return None
    address = raw.strip().rstrip("/")
    if len(address) > 300 or not _ORIGIN.match(address):
        return None
    try:
        parts = urlsplit(address)
        port = parts.port
    except ValueError:
        return None
    if not parts.hostname or parts.path or (port is not None and not 0 < port < 65536):
        return None
    return address


def configured() -> str:
    """The address from configuration: what is used while none is set."""
    return settings.public_base_url.rstrip("/")


def _read() -> str | None:
    with psycopg.connect(settings.dsn, connect_timeout=2, autocommit=True) as conn:
        row = conn.execute("SELECT portal_url FROM portal_address WHERE address_id = 1").fetchone()
    return as_origin(row[0]) if row and row[0] else None


def remember(address: str | None) -> None:
    """What was just saved, for this process, without waiting for `TTL_S`."""
    global _held
    _held = (address, time.monotonic())


def forget() -> None:
    """Read again on the next call. For tests."""
    global _held
    _held = None


def portal_base() -> str:
    """The portal's address, with no trailing slash."""
    global _held
    now = time.monotonic()
    if _held is None or now - _held[1] > TTL_S:
        try:
            _held = (_read(), now)
        except Exception as exc:
            # The table is not there yet (a migration not run), or the database
            # is not answering: keep what is known, and ask again after TTL_S.
            log.warning("portal_address.not_read", error=type(exc).__name__)
            _held = (_held[0] if _held else None, now)
    return _held[0] or configured()
