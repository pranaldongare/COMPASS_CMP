"""The HTTP client for the DKMS service.

**Fail closed.** If the service cannot be reached, an encrypt raises and the
write fails. The alternative - falling back to storing plaintext - turns an
outage into a silent, permanent disclosure that nothing in the system would
ever report. A decrypt that cannot reach the service raises too, and a page
that cannot show a name is a page that says so.

**One call per batch.** The unit is a list of records, because the cost here is
the round trip. A route encrypting four fields of one row makes one call; the
same route over two hundred rows makes one call as well.

**Nothing is logged.** Not the values, not the ciphertext, not the key mapping.
The only things that reach the log are counts and the failure's own message,
which the service writes to be safe to repeat.
"""

from __future__ import annotations

import asyncio
from typing import Any, Literal

import httpx

from cmp.core.config import settings
from cmp.core.errors import ServiceUnavailable
from cmp.core.logging import get_logger
from cmp.infrastructure.dkms.fields import DataType

log = get_logger("cmp.dkms")

Method = Literal["string", "bytes"]
Record = dict[str, Any]


class DkmsUnavailable(ServiceUnavailable):
    """The key service did not answer, so the write did not happen.

    A 503 rather than a 500: the request was well formed and may well succeed
    on a retry, and the caller deserves to be told which of those it is.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(f"The encryption service is unavailable: {detail}")


class DkmsClient:
    """One client for the process, holding one connection pool."""

    def __init__(self, base_url: str, *, timeout_s: float, batch_size: int) -> None:
        self._base_url = base_url.rstrip("/")
        self._batch_size = batch_size
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(timeout_s),
            headers={"content-type": "application/json"},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def health(self) -> dict[str, Any]:
        response = await self._client.get("/health")
        response.raise_for_status()
        return dict(response.json())

    # ------------------------------------------------------------------ bulk
    async def _call(
        self,
        path: str,
        records: list[Record],
        key: dict[str, DataType],
        *,
        method: Method,
        on_error: Literal["fail", "skip"],
    ) -> list[Record]:
        if not records or not key:
            return [dict(r) for r in records]

        # Only the named fields travel. The rest of the row - ids, timestamps,
        # everything the key service has no business seeing - stays here, and
        # is put back around the answer. This is also what lets a row carry a
        # UUID or a datetime, which JSON would otherwise refuse to carry.
        travelling = [{f: r[f] for f in key if isinstance(r.get(f), str)} for r in records]

        out: list[Record] = []
        # Chunked here as well as inside the service: one enormous body is a
        # timeout waiting to happen, and the service refuses past its own limit.
        for start in range(0, len(records), self._batch_size):
            chunk = travelling[start : start + self._batch_size]
            body = {
                "data": chunk,
                "key": {field: t.value for field, t in key.items()},
                "method": method,
                "on_error": on_error,
            }
            try:
                response = await self._client.post(path, json=body)
            except httpx.HTTPError as exc:
                log.error("dkms.unreachable", path=path, records=len(chunk), error=str(exc))
                raise DkmsUnavailable(str(exc)) from exc

            if response.status_code == 422:
                # The service names the record and the field; it never quotes
                # the value, so this is safe to pass upward.
                detail = response.json().get("detail", {})
                log.error("dkms.refused", path=path, detail=detail)
                raise ValueError(f"DKMS refused the batch: {detail}")
            if response.status_code >= 400:
                log.error("dkms.error", path=path, status=response.status_code)
                raise DkmsUnavailable(f"answered {response.status_code}")

            out.extend(response.json()["data"])
        return [{**original, **answered} for original, answered in zip(records, out, strict=True)]

    async def encrypt_records(
        self,
        records: list[Record],
        key: dict[str, DataType],
        *,
        method: Method = "string",
    ) -> list[Record]:
        """Encrypt the named fields of every record, in order."""
        return await self._call("/bulk_encrypt", records, key, method=method, on_error="fail")

    async def decrypt_records(
        self,
        records: list[Record],
        key: dict[str, DataType],
        *,
        method: Method = "string",
        on_error: Literal["fail", "skip"] = "fail",
    ) -> list[Record]:
        """The inverse.

        `on_error="skip"` is for reading a table part-way through a migration,
        where some rows are ciphertext and some are still plaintext: those come
        back as they are rather than failing the page.
        """
        return await self._call("/bulk_decrypt", records, key, method=method, on_error=on_error)


_client: DkmsClient | None = None
_client_loop: asyncio.AbstractEventLoop | None = None


def get_dkms() -> DkmsClient:
    """The process's client, built on first use - and rebuilt for a new loop.

    An `httpx.AsyncClient` belongs to the event loop it was first used on. The
    API runs one loop for its lifetime, so one client serves it; the test suite
    runs a loop per test, and a client carried from one to the next fails with
    "Event loop is closed" on the first request. So the client is bound to the
    loop that built it and replaced when the loop changes.
    """
    global _client, _client_loop
    loop = asyncio.get_running_loop()
    if _client is None or _client_loop is not loop:
        _client = DkmsClient(
            settings.dkms_url,
            timeout_s=settings.dkms_timeout_s,
            batch_size=settings.dkms_batch_size,
        )
        _client_loop = loop
    return _client


async def close_dkms() -> None:
    global _client, _client_loop
    if _client is not None:
        await _client.aclose()
        _client = None
        _client_loop = None


# ------------------------------------------------------------------ shortcuts
async def encrypt_records(
    records: list[Record], key: dict[str, DataType], *, method: Method = "string"
) -> list[Record]:
    """Encrypt a batch, or return it untouched where DKMS is switched off.

    The switch exists for the development database and for the tests that are
    about something else. It is refused outside development by
    `settings.assert_production_ready()`, because a production deployment that
    silently stores plaintext is the failure this whole service exists to
    prevent.
    """
    if not settings.dkms_enabled:
        return [dict(r) for r in records]
    return await get_dkms().encrypt_records(records, key, method=method)


async def decrypt_records(
    records: list[Record],
    key: dict[str, DataType],
    *,
    method: Method = "string",
    on_error: Literal["fail", "skip"] = "skip",
) -> list[Record]:
    """Decrypt a batch. Tolerant by default: a row written before the rollout
    is plaintext already, and a page that refuses to render because of it helps
    nobody."""
    if not settings.dkms_enabled:
        return [dict(r) for r in records]
    return await get_dkms().decrypt_records(records, key, method=method, on_error=on_error)


# ------------------------------------------------------- the synchronous path
#
# Messages are rendered inside Celery tasks, which are synchronous, and the
# name in a greeting or the contact a ticket goes to may be sealed. This is the
# one place the service is called without an event loop.


def unseal_values_sync(values: list[str]) -> list[str]:
    """Decrypt a list of sealed strings, in one call, each under its own type.

    The type is read off each envelope, so the caller needs to know nothing
    but that it holds ciphertext. Values that are not sealed come back as they
    are, in their original positions. Fails closed like the async client: a
    key service that cannot be reached raises rather than sending a message
    with `SE::...` where a person's name should be.
    """
    from cmp.infrastructure.dkms.fields import type_of

    if not settings.dkms_enabled:
        return list(values)

    positions: list[tuple[int, DataType]] = []
    records: list[Record] = []
    for i, v in enumerate(values):
        t = type_of(v) if isinstance(v, str) else None
        if t is not None:
            positions.append((i, t))
            records.append({t.value: v})
    if not records:
        return list(values)

    key = {t.value: t.value for _, t in positions}
    body = {"data": records, "key": key, "method": "string", "on_error": "fail"}
    try:
        with httpx.Client(base_url=settings.dkms_url, timeout=settings.dkms_timeout_s) as client:
            response = client.post("/bulk_decrypt", json=body)
    except httpx.HTTPError as exc:
        log.error("dkms.unreachable", path="/bulk_decrypt", records=len(records), error=str(exc))
        raise DkmsUnavailable(str(exc)) from exc
    if response.status_code >= 400:
        log.error("dkms.error", path="/bulk_decrypt", status=response.status_code)
        raise DkmsUnavailable(f"answered {response.status_code}")

    out = list(values)
    for (i, t), record in zip(positions, response.json()["data"], strict=True):
        out[i] = record[t.value]
    return out


def unseal_variables_sync(variables: dict[str, Any]) -> dict[str, Any]:
    """The template variables of a message, with every sealed string opened."""
    keys = [k for k, v in variables.items() if isinstance(v, str) and v.startswith("SE::")]
    if not keys:
        return variables
    opened = unseal_values_sync([variables[k] for k in keys])
    return {**variables, **dict(zip(keys, opened, strict=True))}
