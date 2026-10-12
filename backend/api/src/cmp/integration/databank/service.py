"""CMP's side of the integration: what it does with each call it receives.

Kept apart from the router so the rules can be tested without HTTP, and so the
real implementation can replace the stub's pieces (`ConsentResolver`,
`IntegrationStore`) without touching the endpoints.
"""

from __future__ import annotations

from functools import lru_cache
from uuid import UUID

from cmp.core.config import settings
from cmp.core.logging import get_logger
from cmp.integration.databank.contracts import (
    AssetEvent,
    AssetEventResults,
    AssetEvents,
    ConsentRecord,
    EventResult,
    EventStatus,
    EventType,
    InstructionResult,
    InstructionStatus,
)
from cmp.integration.databank.store import HeldAsset, IntegrationStore
from cmp.integration.databank.verdicts import ConsentResolver, MockConsentResolver

# Identifiers and outcomes only - never a name, a contact or asset content.
log = get_logger("cmp.integration.databank")


@lru_cache(maxsize=1)
def get_resolver() -> ConsentResolver:
    return MockConsentResolver.from_file(settings.databank_stub_fixtures or None)


async def handle_asset_events(
    batch: AssetEvents, store: IntegrationStore, resolver: ConsentResolver
) -> AssetEventResults:
    """Call 1: each event in order, each answered on its own."""
    results: list[EventResult] = []
    async with store.lock:
        for event in batch.events:
            first = store.events.get(event.event_id)
            if first is not None:
                # The same ID twice: the first answer, and nothing changes.
                results.append(first)
                continue
            result = _apply(event, store, resolver)
            store.events[event.event_id] = result
            results.append(result)
            log.info(
                "databank.asset_event",
                event_id=str(event.event_id),
                type=event.type,
                asset_id=result.asset_id,
                status=result.status,
                verdict=result.verdict,
            )
    return AssetEventResults(results=results)


def _apply(event: AssetEvent, store: IntegrationStore, resolver: ConsentResolver) -> EventResult:
    asset_id = event.target
    held = store.assets.get(asset_id)

    def answer(status: EventStatus, detail: str | None = None) -> EventResult:
        return EventResult(event_id=event.event_id, status=status, asset_id=asset_id, detail=detail)

    if event.type in (EventType.REGISTERED, EventType.UPDATED):
        asset = event.asset
        assert asset is not None  # the contract requires it for these two
        if held is not None and held.deleted:
            return answer(
                EventStatus.REJECTED, "asset_id belonged to a deleted asset; IDs are never reused"
            )
        if held is not None and asset.asset_version <= held.version:
            if event.type == EventType.REGISTERED:
                return answer(EventStatus.REJECTED, "asset_id is already registered")
            return answer(
                EventStatus.IGNORED_STALE,
                f"version {asset.asset_version} is not newer than {held.version}",
            )
        verdict, subjects = resolver.judge(asset)
        store.assets[asset_id] = HeldAsset(
            asset_id=asset_id,
            version=asset.asset_version,
            verdict=verdict,
            releases=held.releases if held else [],
        )
        return EventResult(
            event_id=event.event_id,
            status=EventStatus.ACCEPTED,
            asset_id=asset_id,
            verdict=verdict,
            subjects=subjects,
        )

    if held is None:
        return answer(EventStatus.REJECTED, "asset_id is not registered with CMP")
    if event.type == EventType.DELETED:
        held.deleted = True
        return answer(EventStatus.ACCEPTED, f"deleted: {event.reason}")
    assert event.release is not None  # the contract requires it for released
    held.releases.append(event.release)
    return answer(EventStatus.ACCEPTED, "release recorded")


def lookup_consent(consent_id: UUID, resolver: ConsentResolver) -> ConsentRecord | None:
    """Call 2: the current state of the chain the ID belongs to."""
    record = resolver.lookup(consent_id)
    log.info("databank.consent_lookup", consent_id=str(consent_id), found=record is not None)
    return record


async def handle_results(
    instruction_id: UUID, result: InstructionResult, store: IntegrationStore
) -> InstructionStatus:
    """Call 6: keep each item's outcome; complete only when every item is done."""
    async with store.lock:
        reported, done, complete = store.record_results(instruction_id, result.items)
    log.info(
        "databank.instruction_result",
        instruction_id=str(instruction_id),
        items_reported=reported,
        items_done=done,
        complete=complete,
    )
    return InstructionStatus(
        instruction_id=instruction_id,
        items_reported=reported,
        items_done=done,
        complete=complete,
    )
