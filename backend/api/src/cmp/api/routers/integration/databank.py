"""CMP's three Databank endpoints: calls 1, 2 and 6 of the integration brief.

A stub (2026-10-12): verdicts come from the mock consent register and the
store is in memory - see `cmp.integration.databank`. Mounted only when
`DATABANK_STUB_ENABLED` is on, which the settings refuse in production.

| # | Call                | Endpoint                                              |
|---|---------------------|-------------------------------------------------------|
| 1 | Asset events        | POST /integration/v1/asset-events                     |
| 2 | Consent lookup      | GET  /integration/v1/consents/{consent_id}            |
| 6 | Instruction results | POST /integration/v1/instructions/{instruction_id}/results |

Databank's identity may send asset events, look up consent by ID and post
results - nothing else. It cannot list people or read names, and nothing here
returns either.
"""

from __future__ import annotations

import hmac
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header

from cmp.core.config import settings
from cmp.core.errors import BadRequest, NotFound, Unauthenticated
from cmp.integration.databank import service
from cmp.integration.databank.contracts import (
    PREFIX,
    AssetEventResults,
    AssetEvents,
    ConsentRecord,
    InstructionResult,
    InstructionStatus,
)
from cmp.integration.databank.store import IntegrationStore, get_store
from cmp.integration.databank.verdicts import ConsentResolver


def require_databank(authorization: Annotated[str | None, Header()] = None) -> None:
    """Databank's service identity: a bearer token, compared in constant time.

    A stand-in for mutual TLS or signed tokens - whichever the organisation
    already runs. No token configured means no caller is accepted.
    """
    expected = settings.databank_service_token.get_secret_value()
    scheme, _, presented = (authorization or "").partition(" ")
    if (
        not expected
        or scheme.lower() != "bearer"
        or not hmac.compare_digest(presented.encode(), expected.encode())
    ):
        raise Unauthenticated("A Databank service token is required")


router = APIRouter(
    prefix=PREFIX,
    tags=["integration: databank"],
    dependencies=[Depends(require_databank)],
)

Store = Annotated[IntegrationStore, Depends(get_store)]
Resolver = Annotated[ConsentResolver, Depends(service.get_resolver)]


@router.post(
    "/asset-events",
    response_model=AssetEventResults,
    summary="1 · Asset events: registered, updated, deleted, released",
)
async def asset_events(body: AssetEvents, store: Store, resolver: Resolver) -> AssetEventResults:
    """Databank tells CMP about its assets; a registration or update is answered
    with a verdict per person and one for the asset (the strictest)."""
    return await service.handle_asset_events(body, store, resolver)


@router.get(
    "/consents/{consent_id}",
    response_model=ConsentRecord,
    summary="2 · Consent lookup",
)
async def consent_lookup(consent_id: UUID, resolver: Resolver) -> ConsentRecord:
    """The current state of the chain any consent ID belongs to. Databank's
    fallback: it stores what consent events tell it and asks only when unsure."""
    record = service.lookup_consent(consent_id, resolver)
    if record is None:
        raise NotFound("Consent")
    return record


@router.post(
    "/instructions/{instruction_id}/results",
    response_model=InstructionStatus,
    summary="6 · Instruction results",
)
async def instruction_results(
    instruction_id: UUID, body: InstructionResult, store: Store
) -> InstructionStatus:
    """Databank reports each item's outcome, in parts as items finish. CMP
    closes the request only when every item is done."""
    if body.instruction_id != instruction_id:
        raise BadRequest("instruction_id in the path and the body differ")
    return await service.handle_results(instruction_id, body, store)


@router.get("/stub/state", include_in_schema=False)
async def stub_state(store: Store) -> dict[str, Any]:
    """The stub's memory, for whoever is testing against it. Not one of the
    six calls, and gone with the stub."""
    return store.snapshot()
