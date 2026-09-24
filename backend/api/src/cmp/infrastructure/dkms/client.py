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
from cmp.core.errors import CmpError, ServiceUnavailable
from cmp.core.logging import get_logger
from cmp.infrastructure.dkms.fields import PREFIX, DataType

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


class SealedValueUnreadable(CmpError):
    """A sealed value that no retry will open.

    Not a `DkmsUnavailable`, on purpose. That one means the service did not
    answer, which a retry a minute later may cure, and the message tasks
    retry on it. This one means the service answered and the value is the
    problem - truncated by a column that was too narrow, written under a key
    this service does not hold, glued to other text - and five retries
    spread over minutes change nothing but how long it takes to find out.
    Kept out of every task's `autoretry_for`, so it fails the first time,
    with its reason.
    """

    status_code = 500
    code = "sealed_value_unreadable"


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
        # Only values that need the work travel, and deciding that here is
        # what lets any key service holding to the contract stand behind
        # this client. `skip_encrypted` and `on_error` are this repository's
        # own service's extensions; a service without them would double-seal
        # a sealed value, or refuse a whole batch because one row was written
        # before sealing was switched on. Both are arranged on this side:
        #
        # * encrypting - a value already sealed is held back. Encrypting
        #   twice is not undone by decrypting once.
        # * decrypting - only sealed values are sent. A row still in the
        #   clear has nothing to open and is left exactly as it is, which is
        #   what `on_error="skip"` asked the service for.
        encrypting = path.endswith("encrypt")
        travelling = [
            {
                f: r[f]
                for f in key
                if isinstance(r.get(f), str) and r[f] and r[f].startswith(PREFIX) is not encrypting
            }
            for r in records
        ]

        out: list[Record] = []
        # Chunked here as well as inside the service: one enormous body is a
        # timeout waiting to happen, and the service refuses past its own limit.
        for start in range(0, len(records), self._batch_size):
            chunk = travelling[start : start + self._batch_size]
            # The contract and nothing beyond it. `on_error` and
            # `skip_encrypted` are this repository's own service's
            # extensions, and a key service holding to the contract as
            # written refuses a body carrying them - so the behaviour they
            # asked for is arranged on this side instead: values already
            # sealed are held back from an encrypt (below), and a decrypt
            # that comes back unchanged is judged against `on_error` when
            # the answer is read.
            body = {
                "data": chunk,
                "key": {field: t.value for field, t in key.items()},
                "method": method,
            }
            try:
                response = await self._client.post(path, json=body)
            except httpx.HTTPError as exc:
                log.error(
                    "dkms.unreachable",
                    url=f"{self._base_url}{path}",
                    records=len(chunk),
                    error=str(exc),
                )
                raise DkmsUnavailable(f"{self._base_url}{path}: {exc}") from exc

            if response.status_code == 422:
                # The service names the record and the field; it never quotes
                # the value, so this is safe to pass upward.
                detail = response.json().get("detail", {})
                log.error("dkms.refused", path=path, detail=detail)
                raise ValueError(f"DKMS refused the batch: {detail}")
            if response.status_code >= 400:
                log.error("dkms.error", url=f"{self._base_url}{path}", status=response.status_code)
                raise DkmsUnavailable(f"{self._base_url}{path} answered {response.status_code}")

            out.extend(response.json()["data"])

        answer = [{**original, **answered} for original, answered in zip(records, out, strict=True)]
        if on_error == "fail":
            # What "fail" meant when the service was asked to enforce it: a
            # value that travelled and came back as it went is work the
            # service did not do. Values held back above never travelled and
            # are not judged here.
            unchanged = [
                field
                for row, was, sent in zip(answer, records, travelling, strict=True)
                for field in sent
                if row.get(field) == was.get(field)
            ]
            if unchanged:
                raise DkmsUnavailable(
                    f"{self._base_url}{path} returned {len(unchanged)} value(s) unchanged: "
                    f"{sorted(set(unchanged))}. A key service that cannot do the work must "
                    "say so rather than answering with what it was given."
                )
        return answer

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

    sealed_at = [i for i, v in enumerate(values) if isinstance(v, str) and v.startswith(PREFIX)]

    if not settings.dkms_enabled:
        # Nothing to open *and* nothing sealed is the ordinary case - a
        # plaintext name, an address typed into a form - and it passes
        # through. A sealed value with the service switched off is not: it
        # would be returned as `SE::...` and used as if it were a name or an
        # address, which downstream becomes a nonsense error a long way from
        # the cause. This is that cause, said once.
        if sealed_at:
            # Not retried: the flag is read when the process starts, so the
            # same worker will answer the same way on every retry. The cure is
            # the setting and a restart, and saying so at once is kinder than
            # saying it five times over several minutes.
            raise SealedValueUnreadable(
                f"{len(sealed_at)} value(s) are sealed but DKMS_ENABLED is false, so "
                "nothing can open them. Set DKMS_ENABLED=true in the environment of "
                "every process that reads personal data - the API *and* the worker."
            )
        return list(values)

    # Two ways to open a value, chosen by what its envelope says.
    #
    # * The envelope names its type - this repository's service writes it in
    #   byte 3 - so it goes to `/bulk_decrypt` with that type, the contract
    #   every key service implements.
    # * It does not. Another key service writes its own format; the deployed
    #   one begins its envelope with two different bytes and carries no type
    #   at all. Those go to `/auto_decrypt`, where the service reads its own
    #   envelope. No vendor's bytes are hard-coded here: whether a value is
    #   readable is the service's question, and it answers it.
    typed: list[tuple[int, DataType]] = []
    records: list[Record] = []
    untyped: list[int] = []
    for i in sealed_at:
        t = type_of(values[i])
        if t is not None:
            typed.append((i, t))
            records.append({t.value: values[i]})
        else:
            untyped.append(i)
    if not sealed_at:
        return list(values)

    out = list(values)
    if typed:
        key = {t.value: t.value for _, t in typed}
        # The contract and nothing beyond it. `on_error` is this
        # repository's service's extension and a strict service refuses a
        # body carrying it; only sealed values are sent, so "fail" is what
        # any service does anyway.
        answer = _post_sync("/bulk_decrypt", {"data": records, "key": key, "method": "string"})
        for (i, t), record in zip(typed, answer["data"], strict=True):
            out[i] = record[t.value]
    if untyped:
        payload = {f"v{n}": values[i] for n, i in enumerate(untyped)}
        answer = _post_sync("/auto_decrypt", {"payload": payload}, auto=True)
        opened = answer.get("data") or {}
        for n, i in enumerate(untyped):
            out[i] = opened.get(f"v{n}", values[i])

    still = [i for i in sealed_at if isinstance(out[i], str) and out[i].startswith(PREFIX)]
    if still:
        # The service answered 200 and handed a value back as it went. That is
        # not an outage, and retrying will not change it.
        raise SealedValueUnreadable(
            f"{len(still)} value(s) came back from the key service still sealed: "
            "it could not open them and did not say so."
        )
    return out


def _post_sync(path: str, body: dict[str, Any], *, auto: bool = False) -> dict[str, Any]:
    """One synchronous call, with its failure sorted into the right kind.

    An outage - no answer, a 5xx, a timeout - is a `DkmsUnavailable`, which
    the message tasks retry. An answer that refuses the values - a 4xx - is a
    `SealedValueUnreadable`, which they do not: the same values will be
    refused the same way however long they wait.
    """
    url = f"{settings.dkms_url.rstrip('/')}{path}"
    try:
        with httpx.Client(base_url=settings.dkms_url, timeout=settings.dkms_timeout_s) as client:
            response = client.post(path, json=body)
    except httpx.HTTPError as exc:
        log.error("dkms.unreachable", url=url, error=str(exc))
        raise DkmsUnavailable(f"{url}: {exc}") from exc
    if response.status_code >= 500:
        log.error("dkms.error", url=url, status=response.status_code)
        raise DkmsUnavailable(f"{url} answered {response.status_code}")
    if response.status_code >= 400:
        log.error("dkms.refused", url=url, status=response.status_code)
        if auto and response.status_code in (404, 405, 501):
            raise SealedValueUnreadable(
                f"{url} answered {response.status_code}: the value's envelope does not name "
                "its type, and this key service offers no /auto_decrypt to read it. Either "
                "the value was written by a different key service than DKMS_URL names, or "
                "that service needs /auto_decrypt."
            )
        raise SealedValueUnreadable(
            f"{url} answered {response.status_code}: the service could not open the value - "
            "truncated, written under a key it does not hold, or glued to other text."
        )
    return dict(response.json())


def unseal_variables_sync(variables: dict[str, Any]) -> dict[str, Any]:
    """The template variables of a message, with every sealed string opened."""
    keys = [k for k, v in variables.items() if isinstance(v, str) and v.startswith(PREFIX)]
    if not keys:
        return variables
    opened = unseal_values_sync([variables[k] for k in keys])
    return {**variables, **dict(zip(keys, opened, strict=True))}


async def healthcheck() -> tuple[bool, str | None]:
    """Can the key service be reached, and is it the one we are configured for?

    Personal data cannot be written or read without it: a sign-in code cannot
    be addressed, because the contact it goes to is sealed. So an API or a
    worker that cannot reach it is not ready, and saying so here is the
    difference between one curl and reading a worker traceback.

    Returns `(ok, detail)`; the detail names the URL, never a value.
    """
    if not settings.dkms_enabled:
        return True, "disabled"
    url = settings.dkms_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=settings.dkms_timeout_s) as client:
            response = await client.get(f"{url}/health")
    except httpx.HTTPError as exc:
        return False, f"{url} unreachable: {exc}"
    if response.status_code >= 400:
        return False, f"{url} answered {response.status_code}"
    return True, None
