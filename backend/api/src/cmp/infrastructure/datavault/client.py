"""The call to DataVault: what does it hold of this person? (0070)

    GET {base}/lookup?request_id=<the request's reference>&person_id=<Person ID>

    200 {"person_id": ..., "assets": [
          {"asset_id": "DV-IMG-000101", "consent_id": ..., "project_id": ...,
           "mid": 4909, "datapath": "..."}, ...]}

Where DataVault is, and the key it asks for, are the administrator's to set
(`datavault_connection`), so nothing here reads the environment but the
timeout every outbound call shares.

The rules of `cmp.infrastructure.external` hold: an explicit timeout, no
redirect followed (a redirect to another host is how a lookup becomes a
request somewhere it was never meant to go), and no credential, address or
body in a log line or an error. A failure is a short code - `timeout`,
`unreachable`, `status_503`, `unreadable` - which is all the office is told
and all the trail keeps; what DataVault said in an error body is not ours to
store.

The answer is read strictly and kept small: an asset without an identifier
is dropped, a text is cut to a length a column and a page can hold, and a
list longer than `MAX_ASSETS` is refused rather than stored in part, since a
part of a list reads as the whole of it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx

from cmp.core.config import settings
from cmp.core.logging import get_logger

log = get_logger("cmp.infrastructure.datavault")

#: More than this in one answer is refused (`too_many`).
MAX_ASSETS = 5000
_TEXT = 500
_PATH = 2000


class DataVaultFailed(Exception):
    """The call did not give an answer. `code` is safe to show and to keep."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Held:
    """One asset as DataVault listed it. Every value is its own, as sent."""

    asset_ref: str
    consent_ref: str | None
    project_ref: str | None
    mid: str | None
    datapath: str | None


def usable_base_url(raw: str) -> str | None:
    """The address as it will be called, or None if it cannot be one: http or
    https, a host, and nothing that hides where the call goes or carries a
    credential - no user, no query, no fragment."""
    address = raw.strip().rstrip("/")
    try:
        parts = urlsplit(address)
        host = parts.hostname
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not host:
        return None
    if parts.username or parts.password or parts.query or parts.fragment:
        return None
    if len(address) > 500 or any(c.isspace() for c in address):
        return None
    return address


def _text(value: Any, limit: int = _TEXT) -> str | None:
    """A string or a number as text; anything else is not a value we keep."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (str, int)):
        text = str(value).strip()
        return text[:limit] or None
    return None


def read(body: Any) -> list[Held]:
    """The assets out of an answer, or `DataVaultFailed('unreadable')`."""
    if not isinstance(body, dict) or not isinstance(body.get("assets"), list):
        raise DataVaultFailed("unreadable")
    listed = body["assets"]
    if len(listed) > MAX_ASSETS:
        raise DataVaultFailed("too_many")
    out: list[Held] = []
    for entry in listed:
        if not isinstance(entry, dict):
            raise DataVaultFailed("unreadable")
        ref = _text(entry.get("asset_id"))
        if ref is None:
            continue
        out.append(
            Held(
                asset_ref=ref,
                consent_ref=_text(entry.get("consent_id")),
                project_ref=_text(entry.get("project_id")),
                mid=_text(entry.get("mid")),
                datapath=_text(entry.get("datapath"), _PATH),
            )
        )
    return out


async def lookup(
    *,
    base_url: str,
    api_key: str | None,
    api_key_header: str,
    request_ref: str,
    person_no: int,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[Held]:
    """Ask once. No retry: the office can press again, and the automatic call
    is tried again by its task."""
    headers = {"Accept": "application/json"}
    if api_key:
        headers[api_key_header] = api_key
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.external_http_timeout_s),
            follow_redirects=False,
            transport=transport,
        ) as client:
            response = await client.get(
                f"{base_url.rstrip('/')}/lookup",
                params={"request_id": request_ref, "person_id": str(person_no)},
                headers=headers,
            )
    except httpx.TimeoutException as exc:
        log.warning("datavault.timeout")
        raise DataVaultFailed("timeout") from exc
    except httpx.HTTPError as exc:
        log.warning("datavault.unreachable", error=type(exc).__name__)
        raise DataVaultFailed("unreachable") from exc
    if response.status_code != 200:
        log.warning("datavault.status", status=response.status_code)
        raise DataVaultFailed(f"status_{response.status_code}")
    try:
        body = response.json()
    except ValueError as exc:
        log.warning("datavault.unreadable")
        raise DataVaultFailed("unreadable") from exc
    return read(body)
