"""The bulk operation itself, spread across a thread pool.

**Why threads help here.** `cryptography` calls into OpenSSL, which releases the
GIL for the duration, so AES on several threads is several cores of AES rather
than one core taking turns. The pool is built once at startup and shared; making
one per request would cost more than the work.

**How the work is divided.** Records are cut into chunks and each chunk is one
task. A chunk rather than a record because the hand-off to a worker costs more
than encrypting one short string, and a whole batch per worker because then one
long record decides how long everybody waits.

**Order is preserved.** Chunks come back in submission order and are
concatenated, so `data[3]` in the response is `data[3]` from the request. A
caller lining results up by position - which is what every caller does - is
never wrong.

**Records are not mutated.** Each is copied before its fields are replaced, so
a caller who still holds the objects it sent finds them as they were.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any

from app.dkms.base import DkmsError, DkmsProvider
from app.dkms.local import PREFIX
from app.dkms.types import DataType
from app.schemas import BulkRequest, BulkResponse, FieldError, Record


def _chunks(records: list[Record], size: int) -> Iterator[tuple[int, list[Record]]]:
    """Slices of `size`, each with the index its first record had."""
    for start in range(0, len(records), size):
        yield start, records[start : start + size]


class BulkEngine:
    """Owns the pool, and turns a request into a response."""

    def __init__(self, provider: DkmsProvider, *, workers: int, chunk_size: int) -> None:
        self._provider = provider
        self._workers = workers
        self._chunk_size = chunk_size
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="dkms")

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def workers(self) -> int:
        return self._workers

    def shutdown(self) -> None:
        self._pool.shutdown(wait=True, cancel_futures=True)

    # ----------------------------------------------------------- one value
    def _operation(
        self, request: BulkRequest, *, encrypting: bool
    ) -> Callable[[str, DataType], str]:
        if encrypting:
            return (
                self._provider.encrypt
                if request.method == "string"
                else self._provider.encrypt_bytes
            )
        return (
            self._provider.decrypt if request.method == "string" else self._provider.decrypt_bytes
        )

    @staticmethod
    def _already_done(value: str, method: str) -> bool:
        """Is this value DKMS ciphertext already?

        Only answerable for the string method, where the prefix says so. In the
        bytes form a base64 blob and a base64-looking plaintext are the same
        shape, and guessing would be worse than not trying.
        """
        return method == "string" and value.startswith(PREFIX)

    # ------------------------------------------------------------ one chunk
    def _do_chunk(
        self, offset: int, records: list[Record], request: BulkRequest, *, encrypting: bool
    ) -> tuple[list[Record], int, int, list[FieldError]]:
        operation = self._operation(request, encrypting=encrypting)
        out: list[Record] = []
        changed = skipped = 0
        errors: list[FieldError] = []

        for position, record in enumerate(records):
            copy = dict(record)
            for field, data_type in request.key.items():
                if field not in copy:
                    continue
                value = copy[field]
                # A null stays null: "we hold nothing here" is itself the fact,
                # and encrypting it would invent a value that means something.
                if value is None:
                    skipped += 1
                    continue
                if not isinstance(value, str):
                    skipped += 1
                    continue
                if (
                    encrypting
                    and request.skip_encrypted
                    and self._already_done(value, request.method)
                ):
                    skipped += 1
                    continue
                try:
                    copy[field] = operation(value, data_type)
                    changed += 1
                except DkmsError as exc:
                    errors.append(
                        FieldError(
                            index=offset + position,
                            field=field,
                            data_type=data_type,
                            message=exc.message,
                        )
                    )
                    if request.on_error == "fail":
                        return out, changed, skipped, errors
            out.append(copy)
        return out, changed, skipped, errors

    # ------------------------------------------------------------ the batch
    async def run(self, request: BulkRequest, *, encrypting: bool) -> BulkResponse:
        started = time.perf_counter()
        loop = asyncio.get_running_loop()

        # `partial`, because `run_in_executor` passes positionally and
        # `encrypting` is keyword-only on purpose: a boolean argument that can
        # be passed by position is a boolean that gets passed the wrong way
        # round eventually, and the wrong way round here means encrypting data
        # the caller asked to have decrypted.
        tasks = [
            loop.run_in_executor(
                self._pool,
                partial(self._do_chunk, offset, chunk, request, encrypting=encrypting),
            )
            for offset, chunk in _chunks(request.data, self._chunk_size)
        ]
        results: list[Any] = await asyncio.gather(*tasks)

        data: list[Record] = []
        changed = skipped = 0
        errors: list[FieldError] = []
        for chunk_records, chunk_changed, chunk_skipped, chunk_errors in results:
            data.extend(chunk_records)
            changed += chunk_changed
            skipped += chunk_skipped
            errors.extend(chunk_errors)

        if errors and request.on_error == "fail":
            # Raised rather than returned: a partial batch that looks like a
            # whole one is how half-encrypted tables happen.
            raise BulkFailed(errors)

        return BulkResponse(
            data=data,
            method=request.method,
            records=len(data),
            values=changed,
            skipped=skipped,
            errors=errors,
            took_ms=round((time.perf_counter() - started) * 1000, 3),
            provider=self.provider_name,
            workers=self._workers,
        )


class BulkFailed(Exception):
    """At least one value failed and the caller asked to be told, not patched."""

    def __init__(self, errors: list[FieldError]) -> None:
        super().__init__(f"{len(errors)} value(s) failed")
        self.errors = errors
