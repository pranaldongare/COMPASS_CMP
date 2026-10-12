"""What CMP remembers between calls, in memory (brief: "Security, reliability
and timing").

* **Idempotency.** Every event has an ID; receiving the same ID twice returns
  the first answer and changes nothing.
* **Ordering.** `asset_version` rises with every change; a version older than
  the one held is ignored.
* **Never reused.** An asset ID that belonged to a deleted asset is refused.

In memory and per process - a stub. The real store will be tables in CMP's
database with the same three rules, so a restart or a second replica does not
forget an event. Nothing here holds a name or a contact: identifiers, versions,
verdicts and outcomes only.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from uuid import UUID

from cmp.integration.databank.contracts import (
    Action,
    AssetId,
    EventResult,
    Instruction,
    ItemResult,
    Outcome,
    Release,
    Verdict,
)


@dataclass
class HeldAsset:
    asset_id: AssetId
    version: int
    verdict: Verdict | None
    deleted: bool = False
    releases: list[Release] = field(default_factory=list)


@dataclass
class SentInstruction:
    instruction: Instruction
    results: dict[AssetId, ItemResult] = field(default_factory=dict)

    @property
    def expected(self) -> set[tuple[AssetId, Action]]:
        return {(i.asset_id, Action(i.action)) for i in self.instruction.items}


class IntegrationStore:
    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.events: dict[UUID, EventResult] = {}
        self.assets: dict[AssetId, HeldAsset] = {}
        self.instructions: dict[UUID, SentInstruction] = {}
        #: Results for instructions this process did not send (another process
        #: did, or a test): kept, and judged on what was reported.
        self.orphan_results: dict[UUID, dict[AssetId, ItemResult]] = {}

    def remember_instruction(self, instruction: Instruction) -> None:
        self.instructions.setdefault(instruction.instruction_id, SentInstruction(instruction))

    def record_results(
        self, instruction_id: UUID, items: list[ItemResult]
    ) -> tuple[int, int, bool]:
        """Keep each item's latest outcome; (reported, done, complete)."""
        sent = self.instructions.get(instruction_id)
        held = sent.results if sent else self.orphan_results.setdefault(instruction_id, {})
        for item in items:
            held[item.asset_id] = item
        done = sum(1 for r in held.values() if r.outcome == Outcome.DONE)
        expected = len(sent.instruction.items) if sent else len(held)
        # CMP closes a request only when every item is done.
        return len(held), done, done == expected

    def snapshot(self) -> dict[str, object]:
        return {
            "assets": {
                a.asset_id: {
                    "version": a.version,
                    "verdict": a.verdict,
                    "deleted": a.deleted,
                    "releases": [r.model_dump(mode="json") for r in a.releases],
                }
                for a in self.assets.values()
            },
            "events_seen": len(self.events),
            "instructions": {
                str(k): {r.asset_id: r.outcome for r in v.results.values()}
                for k, v in self.instructions.items()
            },
            "orphan_results": {
                str(k): {a: r.outcome for a, r in v.items()} for k, v in self.orphan_results.items()
            },
        }


_store = IntegrationStore()


def get_store() -> IntegrationStore:
    return _store
