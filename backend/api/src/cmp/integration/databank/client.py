"""CMP's side of calls 3, 4 and 5, which Databank hosts.

| # | Call            | Endpoint (on Databank)                              |
|---|-----------------|-----------------------------------------------------|
| 3 | Inventory       | GET  /integration/v1/persons/{person_id}/assets     |
| 4 | Consent changed | POST /integration/v1/consent-events                 |
| 5 | Instructions    | POST /integration/v1/instructions                   |

`DatabankClient` talks HTTP. Point it at the real Databank, at the mock
(`python -m cmp.integration.databank.mock_server`), or - in a test - at the
mock app in process through an ASGI transport.

The rules from `cmp.infrastructure.external` hold: an explicit timeout always,
bounded retries with jitter, no credential in a log line. Retrying is safe
because every event and instruction carries its own ID and the receiver answers
a repeat with its first answer.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any
from uuid import UUID

import httpx

from cmp.core.config import settings
from cmp.core.errors import UpstreamError
from cmp.core.logging import get_logger
from cmp.integration.databank.contracts import (
    PREFIX,
    Acknowledgement,
    ConsentEvent,
    ConsentEvents,
    Instruction,
    InstructionAccepted,
    Inventory,
)
from cmp.integration.databank.store import IntegrationStore, get_store

log = get_logger("cmp.integration.databank.client")

#: Worth retrying: the receiver did not get it, or could not take it yet.
_RETRYABLE = {408, 425, 429, 500, 502, 503, 504}


class DatabankClient:
    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        retries: int | None = None,
        store: IntegrationStore | None = None,
    ) -> None:
        secret = token or settings.databank_service_token.get_secret_value()
        self._http = httpx.AsyncClient(
            base_url=(base_url or settings.databank_base_url).rstrip("/") + PREFIX,
            headers={"Authorization": f"Bearer {secret}"},
            timeout=httpx.Timeout(settings.external_http_timeout_s),
            follow_redirects=False,  # a redirect to an internal host is an SSRF
            transport=transport,
        )
        self._retries = settings.external_http_retries if retries is None else retries
        self._store = store or get_store()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> DatabankClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    # ----------------------------------------------------------- the calls

    async def inventory(
        self,
        person_id: UUID,
        *,
        project_id: UUID | None = None,
        consent_id: UUID | None = None,
    ) -> Inventory:
        """Call 3: what Databank holds for one person, from its own index."""
        params = {
            k: str(v)
            for k, v in (("project_id", project_id), ("consent_id", consent_id))
            if v is not None
        }
        data = await self._send("GET", f"/persons/{person_id}/assets", params=params)
        return Inventory.model_validate(data)

    async def consent_changed(self, events: list[ConsentEvent]) -> Acknowledgement:
        """Call 4: tell Databank a consent's new state."""
        body = ConsentEvents(events=events).model_dump(mode="json")
        return Acknowledgement.model_validate(
            await self._send("POST", "/consent-events", json=body)
        )

    async def instruct(self, instruction: Instruction) -> InstructionAccepted:
        """Call 5: restrict, erase, redact or hold. Accepted now; the outcome
        arrives later on call 6, and is matched to this instruction."""
        self._store.remember_instruction(instruction)
        data = await self._send("POST", "/instructions", json=instruction.model_dump(mode="json"))
        return InstructionAccepted.model_validate(data)

    # ---------------------------------------------------------- transport

    async def _send(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        attempt = 0
        while True:
            try:
                response = await self._http.request(method, path, **kwargs)
            except httpx.TransportError as exc:
                if attempt >= self._retries:
                    log.warning("databank.unreachable", method=method, path=path)
                    raise UpstreamError(f"Databank {method} {path} failed") from exc
            else:
                if response.status_code < 400:
                    result: dict[str, Any] = response.json()
                    return result
                if response.status_code not in _RETRYABLE or attempt >= self._retries:
                    log.warning(
                        "databank.status", method=method, path=path, status=response.status_code
                    )
                    raise UpstreamError(f"Databank {method} {path} returned {response.status_code}")
            attempt += 1
            # Exponential backoff with full jitter, so retries do not arrive in step.
            await asyncio.sleep(random.uniform(0, min(8.0, 0.25 * 2**attempt)))  # noqa: S311
