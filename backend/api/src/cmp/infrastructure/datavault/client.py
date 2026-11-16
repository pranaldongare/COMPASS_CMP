"""The calls to DataVault (0070, 0071).

What does it hold of this person?

    GET {base}/lookup?request_id=<the request>&person_id=<the person>

    200 {"person_id": ..., "assets": [
          {"asset_id": "DV-IMG-000101", "consent_id": ..., "project_id": ...,
           "mid": 4909, "datapath": "..."}, ...]}

Erase these assets, or say how far each has got (the same `erasure_id` again):

    POST {erasure address}/erasures
    {"erasure_id": ..., "request_id": ..., "person_id": ...,
     "assets": [{"asset_id": "DV-IMG-000101", "consent_id": ...}, ...]}

    200 {"erasure_id": ..., "assets": [{"asset_id": ..., "status": "erased"}, ...]}

A consent changed; act on the assets held under it:

    POST {erasure address}/consent-changes
    {"message_id": ..., "sequence": 1042, "person_id": ..., "project_id": ...,
     "consent_id": ..., "consent_ids": [...], "change": "partly_withdrawn",
     "action": "restrict", "purposes_granted": [...], "purposes_removed": [...],
     "effective_at": "..."}

    200 {"message_id": ..., "result": "applied", "assets_affected": 2}

How a person, a consent, a project and a request are named - by number or by
uuid - is the caller's to decide (`cmp.domain.datavault.ids`): this module
sends what it is given.

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
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

import httpx

from cmp.core.config import settings
from cmp.core.logging import get_logger

log = get_logger("cmp.infrastructure.datavault")

#: More than this in one answer is refused (`too_many`).
MAX_ASSETS = 5000
#: The most assets one erasure instruction may name: the contract's limit.
MAX_ERASURE_ASSETS = 1000
#: What DataVault may say of an asset it was told to erase. `pending` is the
#: only one that is not final.
ERASURE_STATUSES = ("erased", "pending", "failed", "not_held")
#: What DataVault may answer a consent change: each counts as delivered.
CHANGE_RESULTS = ("applied", "duplicate", "stale")
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
    #: DataVault gave the consent as a JSON number. An erasure sends it back
    #: as it came, a number as a number.
    consent_is_number: bool = False


@dataclass(frozen=True)
class Outcome:
    """What DataVault says of one asset it was told to erase."""

    asset_ref: str
    status: str
    completed_at: datetime | None
    reason: str | None


@dataclass(frozen=True)
class ChangeResult:
    """DataVault's answer to one consent change."""

    result: str
    assets_affected: int


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
        consent = entry.get("consent_id")
        out.append(
            Held(
                asset_ref=ref,
                consent_ref=_text(consent),
                project_ref=_text(entry.get("project_id")),
                mid=_text(entry.get("mid")),
                datapath=_text(entry.get("datapath"), _PATH),
                consent_is_number=isinstance(consent, int) and not isinstance(consent, bool),
            )
        )
    return out


async def _call(
    method: str,
    url: str,
    *,
    api_key: str | None,
    api_key_header: str,
    transport: httpx.AsyncBaseTransport | None,
    params: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> Any:
    """One request, and its answer as JSON - or `DataVaultFailed` with a code
    that says no more than how it went. No retry here: who retries, and when,
    is each caller's to say."""
    headers = {"Accept": "application/json"}
    if api_key:
        headers[api_key_header] = api_key
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.external_http_timeout_s),
            follow_redirects=False,
            transport=transport,
        ) as client:
            response = await client.request(method, url, params=params, json=body, headers=headers)
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
        return response.json()
    except ValueError as exc:
        log.warning("datavault.unreadable")
        raise DataVaultFailed("unreadable") from exc


async def lookup(
    *,
    base_url: str,
    api_key: str | None,
    api_key_header: str,
    request_id: str,
    person_id: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[Held]:
    """Ask once. No retry: the office can press again, and the automatic call
    is tried again by its task."""
    return read(
        await _call(
            "GET",
            f"{base_url.rstrip('/')}/lookup",
            api_key=api_key,
            api_key_header=api_key_header,
            transport=transport,
            params={"request_id": request_id, "person_id": person_id},
        )
    )


def _when(value: Any) -> datetime | None:
    """A time DataVault gave, or None: one it did not give, or not a time."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        at = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return at if at.tzinfo is not None else None


def read_outcomes(body: Any) -> list[Outcome]:
    """What an answer says of each asset, or `DataVaultFailed('unreadable')`.

    An entry with no identifier, or a status that is not one of the four, says
    nothing we can keep and is passed over: the asset stays as it stood, and
    is asked about again. An answer in which nothing can be read at all is
    unreadable."""
    if not isinstance(body, dict) or not isinstance(body.get("assets"), list):
        raise DataVaultFailed("unreadable")
    out: list[Outcome] = []
    for entry in body["assets"]:
        if not isinstance(entry, dict):
            raise DataVaultFailed("unreadable")
        ref = _text(entry.get("asset_id"))
        status = entry.get("status")
        if ref is None or status not in ERASURE_STATUSES:
            continue
        out.append(
            Outcome(
                asset_ref=ref,
                status=str(status),
                completed_at=_when(entry.get("completed_at")) if status == "erased" else None,
                reason=_text(entry.get("reason")) if status == "failed" else None,
            )
        )
    if body["assets"] and not out:
        raise DataVaultFailed("unreadable")
    return out


async def erase(
    *,
    erasure_url: str,
    api_key: str | None,
    api_key_header: str,
    erasure_id: str,
    request_id: Any,
    person_id: Any,
    assets: list[dict[str, Any]],
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[Outcome]:
    """Tell DataVault to erase these assets - or, with an `erasure_id` it has
    seen, ask how far each has got: a repeat starts nothing new."""
    return read_outcomes(
        await _call(
            "POST",
            f"{erasure_url.rstrip('/')}/erasures",
            api_key=api_key,
            api_key_header=api_key_header,
            transport=transport,
            body={
                "erasure_id": erasure_id,
                "request_id": request_id,
                "person_id": person_id,
                "assets": assets,
            },
        )
    )


def read_change_result(body: Any) -> ChangeResult:
    if not isinstance(body, dict) or body.get("result") not in CHANGE_RESULTS:
        raise DataVaultFailed("unreadable")
    affected = body.get("assets_affected")
    if not isinstance(affected, int) or isinstance(affected, bool) or affected < 0:
        affected = 0
    return ChangeResult(result=str(body["result"]), assets_affected=affected)


async def consent_change(
    *,
    erasure_url: str,
    api_key: str | None,
    api_key_header: str,
    message: dict[str, Any],
    transport: httpx.AsyncBaseTransport | None = None,
) -> ChangeResult:
    """Deliver one consent change. `applied`, `duplicate` and `stale` are all
    DataVault saying it has it."""
    return read_change_result(
        await _call(
            "POST",
            f"{erasure_url.rstrip('/')}/consent-changes",
            api_key=api_key,
            api_key_header=api_key_header,
            transport=transport,
            body=message,
        )
    )
