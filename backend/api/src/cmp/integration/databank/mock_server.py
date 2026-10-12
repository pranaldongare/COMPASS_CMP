"""A mock Databank, to build and test CMP against before the real one exists.

It plays Databank's half of the brief:

* hosts calls 3, 4 and 5 - inventory, consent changes, instructions;
* takes a lab delivery (`POST /mock/deliveries`, the brief's metadata schema),
  holds every asset in quarantine and registers it with CMP (call 1), then acts
  on the verdict;
* carries out instructions and reports each item's outcome to CMP (call 6),
  and tells CMP about an erasure with a `deleted` event.

Four asset states, only one of them usable: quarantined -> usable ->
restricted -> erased. An asset with several people is usable only while every
person in it is active. A legal hold blocks erasure until it is released.
Redaction fails with `redaction_not_supported` unless `--redaction` is on - the
brief's open question, answered both ways.

Run it next to the API (both need the same service token)::

    DATABANK_SERVICE_TOKEN=... python -m cmp.integration.databank.mock_server \\
        --port 8100 --cmp-url http://127.0.0.1:8000

In memory: a restart forgets everything, which for a mock is a feature.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import hmac
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query

from cmp.integration.databank.contracts import (
    PREFIX,
    Acknowledgement,
    Action,
    AssetEvent,
    AssetEventResults,
    AssetEvents,
    AssetId,
    AssetRecord,
    AssetState,
    ConsentEvents,
    ConsentRecord,
    ConsentState,
    DeleteReason,
    Delivery,
    ErasureEvidence,
    EventType,
    Instruction,
    InstructionAccepted,
    InstructionResult,
    Inventory,
    InventoryAsset,
    ItemResult,
    Outcome,
    Release,
    Verdict,
)

#: Derivatives the mock pretends to make per asset type (thumbnails,
#: transcodes, annotations), so an erasure has something to report.
_DERIVATIVES = {"image": 2, "video": 3, "audio": 1}


@dataclass
class MockAsset:
    record: AssetRecord
    state: AssetState = AssetState.QUARANTINED
    verdict: Verdict | None = None
    #: The verdict was valid once: the asset left quarantine.
    cleared: bool = False
    restricted_by_instruction: bool = False
    #: An update came back restricted after the asset had been cleared.
    restricted_by_verdict: bool = False
    hold: bool = False
    releases: list[Release] = field(default_factory=list)

    @property
    def derivatives(self) -> int:
        return 0 if self.state == AssetState.ERASED else _DERIVATIVES.get(self.record.asset_type, 0)


@dataclass
class MockDatabank:
    cmp_url: str
    token: str
    cmp_transport: httpx.AsyncBaseTransport | None = None
    redaction_supported: bool = False
    #: Seconds before an instruction's results are reported.
    result_delay: float = 0.0
    assets: dict[AssetId, MockAsset] = field(default_factory=dict)
    deleted_ids: set[AssetId] = field(default_factory=set)
    consents: dict[UUID, ConsentRecord] = field(default_factory=dict)
    consent_events: dict[UUID, bool] = field(default_factory=dict)
    instructions: dict[UUID, Instruction] = field(default_factory=dict)

    def cmp(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.cmp_url.rstrip("/") + PREFIX,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=httpx.Timeout(10.0),
            transport=self.cmp_transport,
        )

    async def send_events(self, events: list[AssetEvent]) -> AssetEventResults:
        body = AssetEvents(events=events).model_dump(mode="json")
        async with self.cmp() as http:
            response = await http.post("/asset-events", json=body)
            response.raise_for_status()
            return AssetEventResults.model_validate(response.json())

    # ---------------------------------------------------- consent and use

    def _subject_active(self, consent_id: UUID) -> bool:
        record = self.consents.get(consent_id)
        if record is None:
            return True  # nothing newer than the verdict
        if record.state in (ConsentState.WITHDRAWN, ConsentState.EXPIRED):
            return False
        return any(p.granted for p in record.purposes)

    def _settle(self, asset: MockAsset) -> None:
        """The state that follows from the verdict, the people and any instruction."""
        if asset.state == AssetState.ERASED:
            return
        if not asset.cleared:
            asset.state = AssetState.QUARANTINED
            return
        everyone_active = all(self._subject_active(s.consent_id) for s in asset.record.subjects)
        asset.state = (
            AssetState.USABLE
            if everyone_active
            and not asset.restricted_by_instruction
            and not asset.restricted_by_verdict
            else AssetState.RESTRICTED
        )

    def apply_verdict(self, asset: MockAsset, verdict: Verdict | None) -> None:
        """Valid clears quarantine. Restricted keeps a new asset in quarantine
        and restricts one already in use. Invalid or unknown quarantine it."""
        asset.verdict = verdict
        if verdict == Verdict.VALID:
            asset.cleared, asset.restricted_by_verdict = True, False
        elif verdict == Verdict.RESTRICTED and asset.cleared:
            asset.restricted_by_verdict = True
        else:
            asset.cleared = False
        self._settle(asset)

    # ------------------------------------------------------- instructions

    def _carry_out(self, instruction: Instruction) -> tuple[list[ItemResult], list[AssetEvent]]:
        results: list[ItemResult] = []
        events: list[AssetEvent] = []
        now = datetime.now(UTC)
        for item in instruction.items:
            asset = self.assets.get(item.asset_id)
            action = Action(item.action)

            def fail(reason: str, _item: Any = item) -> ItemResult:
                return ItemResult(
                    asset_id=_item.asset_id,
                    action=_item.action,
                    outcome=Outcome.FAILED,
                    reason=reason,
                )

            def done(evidence: ErasureEvidence | None = None, _item: Any = item) -> ItemResult:
                return ItemResult(
                    asset_id=_item.asset_id,
                    action=_item.action,
                    outcome=Outcome.DONE,
                    completed_at=now,
                    evidence=evidence,
                )

            if asset is None:
                results.append(fail("asset_not_found"))
            elif asset.state == AssetState.ERASED:
                results.append(done() if action == Action.ERASE else fail("asset_erased"))
            elif action == Action.RESTRICT:
                asset.restricted_by_instruction = True
                self._settle(asset)
                results.append(done())
            elif action == Action.LIFT_RESTRICTION:
                asset.restricted_by_instruction = False
                self._settle(asset)
                results.append(done())
            elif action == Action.HOLD:
                asset.hold = True
                results.append(done())
            elif action == Action.RELEASE_HOLD:
                asset.hold = False
                results.append(done())
            elif action == Action.ERASE:
                if asset.hold:
                    results.append(fail("legal_hold"))
                    continue
                derivatives = asset.derivatives
                asset.state = AssetState.ERASED
                self.deleted_ids.add(asset.record.asset_id)
                results.append(
                    done(
                        ErasureEvidence(
                            content_sha256=asset.record.content_sha256,
                            derivatives_deleted=derivatives,
                            backups_expire_on=datetime.now(UTC).date() + timedelta(days=30),
                        )
                    )
                )
                events.append(
                    AssetEvent(
                        event_id=uuid.uuid4(),
                        type=EventType.DELETED,
                        occurred_at=now,
                        asset_id=asset.record.asset_id,
                        reason=DeleteReason.INSTRUCTION,
                    )
                )
            elif action == Action.REDACT:
                others = [s for s in asset.record.subjects if s.person_id != instruction.person_id]
                if not self.redaction_supported:
                    results.append(fail("redaction_not_supported"))
                elif len(others) == len(asset.record.subjects):
                    results.append(fail("person_not_in_asset"))
                elif not others:
                    results.append(fail("only_person_in_asset_erase_instead"))
                else:
                    asset.record = asset.record.model_copy(
                        update={"subjects": others, "asset_version": asset.record.asset_version + 1}
                    )
                    self._settle(asset)
                    results.append(done())
                    events.append(
                        AssetEvent(
                            event_id=uuid.uuid4(),
                            type=EventType.UPDATED,
                            occurred_at=now,
                            asset=asset.record,
                        )
                    )
        return results, events

    async def report(self, instruction: Instruction) -> None:
        if self.result_delay:
            await asyncio.sleep(self.result_delay)
        results, events = self._carry_out(instruction)
        if events:
            outcome = await self.send_events(events)
            for result in outcome.results:
                if result.verdict is not None and result.asset_id in self.assets:
                    self.apply_verdict(self.assets[result.asset_id], result.verdict)
        body = InstructionResult(instruction_id=instruction.instruction_id, items=results)
        async with self.cmp() as http:
            response = await http.post(
                f"/instructions/{instruction.instruction_id}/results",
                json=body.model_dump(mode="json"),
            )
            response.raise_for_status()


def create_app(state: MockDatabank) -> FastAPI:
    app = FastAPI(
        title="Mock Databank",
        version="1",
        description="Databank's half of the COMPASS CMP integration, for development and tests.",
    )
    app.state.databank = state

    def require_cmp(authorization: Annotated[str | None, Header()] = None) -> None:
        scheme, _, presented = (authorization or "").partition(" ")
        if scheme.lower() != "bearer" or not hmac.compare_digest(
            presented.encode(), state.token.encode()
        ):
            raise HTTPException(status_code=401, detail="CMP service token required")

    guarded = [Depends(require_cmp)]

    # ------------------------------------------- calls 3, 4, 5 (hosted here)

    @app.get(
        f"{PREFIX}/persons/{{person_id}}/assets",
        response_model=Inventory,
        dependencies=guarded,
        summary="3 · Inventory",
        tags=["databank"],
    )
    async def inventory(
        person_id: UUID,
        project_id: Annotated[UUID | None, Query()] = None,
        consent_id: Annotated[UUID | None, Query()] = None,
    ) -> Inventory:
        found: list[InventoryAsset] = []
        for asset in state.assets.values():
            if asset.state == AssetState.ERASED:
                continue
            record = asset.record
            for subject in record.subjects:
                if subject.person_id != person_id:
                    continue
                if project_id and record.project_id != project_id:
                    continue
                if consent_id and subject.consent_id != consent_id:
                    continue
                found.append(
                    InventoryAsset(
                        asset_id=record.asset_id,
                        asset_version=record.asset_version,
                        asset_type=record.asset_type,
                        captured_at=record.captured_at,
                        project_id=record.project_id,
                        consent_id=subject.consent_id,
                        state=asset.state,
                        derivatives=asset.derivatives,
                        releases=asset.releases,
                    )
                )
        return Inventory(person_id=person_id, assets=found)

    @app.post(
        f"{PREFIX}/consent-events",
        response_model=Acknowledgement,
        dependencies=guarded,
        summary="4 · Consent changed",
        tags=["databank"],
    )
    async def consent_events(body: ConsentEvents) -> Acknowledgement:
        accepted: list[UUID] = []
        duplicates: list[UUID] = []
        for event in body.events:
            if event.event_id in state.consent_events:
                duplicates.append(event.event_id)
                continue
            state.consent_events[event.event_id] = True
            accepted.append(event.event_id)
            for consent_id in event.consent.consent_ids:
                state.consents[consent_id] = event.consent
            chain = set(event.consent.consent_ids)
            for asset in state.assets.values():
                if any(s.consent_id in chain for s in asset.record.subjects):
                    state._settle(asset)
        return Acknowledgement(accepted=accepted, duplicates=duplicates)

    @app.post(
        f"{PREFIX}/instructions",
        response_model=InstructionAccepted,
        status_code=202,
        dependencies=guarded,
        summary="5 · Instructions",
        tags=["databank"],
    )
    async def instructions(body: Instruction, tasks: BackgroundTasks) -> InstructionAccepted:
        if body.instruction_id in state.instructions:
            return InstructionAccepted(instruction_id=body.instruction_id, duplicate=True)
        state.instructions[body.instruction_id] = body
        tasks.add_task(state.report, body)
        return InstructionAccepted(instruction_id=body.instruction_id)

    # --------------------------------------- the mock's own controls (/mock)

    @app.post("/mock/deliveries", tags=["mock"], summary="A lab delivery arrives")
    async def delivery(body: Delivery) -> dict[str, Any]:
        """Quarantine every asset, register it with CMP, act on the verdict."""
        now = datetime.now(UTC)
        refused: dict[str, str] = {}
        events: list[AssetEvent] = []
        for item in body.assets:
            if item.asset_id in state.deleted_ids:
                refused[item.asset_id] = "belonged to a deleted asset"
                continue
            if item.asset_id in state.assets:
                refused[item.asset_id] = "already in use"
                continue
            record = AssetRecord(
                **item.model_dump(),
                asset_version=1,
                project_id=body.project_id,
                site_id=body.site_id,
                batch_ref=body.batch_ref,
                content_sha256=hashlib.sha256(item.asset_id.encode()).hexdigest(),
            )
            state.assets[item.asset_id] = MockAsset(record=record)
            events.append(
                AssetEvent(
                    event_id=uuid.uuid4(), type=EventType.REGISTERED, occurred_at=now, asset=record
                )
            )
        results = await state.send_events(events) if events else AssetEventResults(results=[])
        for result in results.results:
            state.apply_verdict(state.assets[result.asset_id], result.verdict)
        return {
            "batch_ref": body.batch_ref,
            "declared": body.declared_asset_count,
            "received": len(body.assets),
            "short_delivery": len(body.assets) < body.declared_asset_count,
            "refused": refused,
            "assets": {
                r.asset_id: {
                    "verdict": r.verdict,
                    "state": state.assets[r.asset_id].state,
                    "subjects": [s.model_dump(mode="json") for s in r.subjects],
                }
                for r in results.results
            },
        }

    @app.get("/mock/assets", tags=["mock"], summary="Everything the mock holds")
    async def assets() -> dict[str, Any]:
        return {
            a.record.asset_id: {
                "state": a.state,
                "verdict": a.verdict,
                "version": a.record.asset_version,
                "hold": a.hold,
                "subjects": [s.model_dump(mode="json") for s in a.record.subjects],
                "releases": [r.model_dump(mode="json") for r in a.releases],
            }
            for a in state.assets.values()
        }

    @app.post("/mock/assets/{asset_id}/release", tags=["mock"], summary="A copy leaves Databank")
    async def release(asset_id: str, recipient: str) -> dict[str, Any]:
        asset = state.assets.get(asset_id)
        if asset is None or asset.state != AssetState.USABLE:
            raise HTTPException(status_code=409, detail="only a usable asset can be released")
        entry = Release(recipient=recipient, released_on=datetime.now(UTC).date())
        asset.releases.append(entry)
        result = await state.send_events(
            [
                AssetEvent(
                    event_id=uuid.uuid4(),
                    type=EventType.RELEASED,
                    occurred_at=datetime.now(UTC),
                    asset_id=asset_id,
                    release=entry,
                )
            ]
        )
        return result.model_dump(mode="json")

    @app.post(
        "/mock/assets/{asset_id}/delete", tags=["mock"], summary="Databank deletes on its own"
    )
    async def delete(
        asset_id: str, reason: DeleteReason = DeleteReason.RETENTION
    ) -> dict[str, Any]:
        asset = state.assets.get(asset_id)
        if asset is None or asset.state == AssetState.ERASED:
            raise HTTPException(status_code=404, detail="no such asset")
        if asset.hold:
            raise HTTPException(status_code=409, detail="under a legal hold")
        asset.state = AssetState.ERASED
        state.deleted_ids.add(asset_id)
        result = await state.send_events(
            [
                AssetEvent(
                    event_id=uuid.uuid4(),
                    type=EventType.DELETED,
                    occurred_at=datetime.now(UTC),
                    asset_id=asset_id,
                    reason=reason,
                )
            ]
        )
        return result.model_dump(mode="json")

    return app


def main() -> None:  # pragma: no cover - a command line
    import uvicorn

    parser = argparse.ArgumentParser(description="Run the mock Databank.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8100)
    parser.add_argument("--cmp-url", default="http://127.0.0.1:8000")
    parser.add_argument("--redaction", action="store_true", help="support redaction")
    parser.add_argument("--result-delay", type=float, default=2.0, help="seconds")
    args = parser.parse_args()
    token = os.environ.get("DATABANK_SERVICE_TOKEN", "")
    if len(token) < 32:
        raise SystemExit("Set DATABANK_SERVICE_TOKEN (32+ characters), the same as the API's.")
    state = MockDatabank(
        cmp_url=args.cmp_url,
        token=token,
        redaction_supported=args.redaction,
        result_delay=args.result_delay,
    )
    uvicorn.run(create_app(state), host=args.host, port=args.port)


if __name__ == "__main__":  # pragma: no cover
    main()
