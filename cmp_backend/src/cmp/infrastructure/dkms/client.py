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

        out: list[Record] = []
        # Chunked here as well as inside the service: one enormous body is a
        # timeout waiting to happen, and the service refuses past its own limit.
        for start in range(0, len(records), self._batch_size):
            chunk = records[start : start + self._batch_size]
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
        return out

    async def encrypt_records(
        self,
        records: list[Record],
        key: dict[str, DataType],
        *,
        method: Method = "string",
    ) -> list[Record]:
        """Encrypt the named fields of every record, in order."""
        return await self._call("/encrypt/bulk", records, key, method=method, on_error="fail")

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
        return await self._call("/decrypt/bulk", records, key, method=method, on_error=on_error)


_client: DkmsClient | None = None


def get_dkms() -> DkmsClient:
    """The process's client, built on first use."""
    global _client
    if _client is None:
        _client = DkmsClient(
            settings.dkms_url,
            timeout_s=settings.dkms_timeout_s,
            batch_size=settings.dkms_batch_size,
        )
    return _client


async def close_dkms() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


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
