"""Walk the whole integration once against running servers.

Start the API with the stub on, and the mock Databank, with one token::

    export DATABANK_SERVICE_TOKEN=$(python -c "import secrets; print(secrets.token_hex(24))")
    DATABANK_STUB_ENABLED=true python -m cmp --port 8000
    python -m cmp.integration.databank.mock_server --port 8100 --cmp-url http://127.0.0.1:8000
    python -m cmp.integration.databank.demo --cmp-url http://127.0.0.1:8000 \\
        --databank-url http://127.0.0.1:8100

It delivers the brief's example batch, reads the inventory, withdraws the
second person's consent, then erases and redacts the first person's assets,
printing each answer. Nothing here is personal: the fixtures' IDs only.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx

from cmp.integration.databank.client import DatabankClient
from cmp.integration.databank.contracts import (
    PREFIX,
    Action,
    ConsentEvent,
    ConsentRecord,
    Instruction,
    InstructionItem,
    InstructionReason,
)

PROJECT = "5d0c2c1e-8a41-4f1b-b6a0-3e9d7c2a1f54"
SITE = "a8f3e6b2-1c7d-4e59-9b02-6d4f8a1c3e70"
PERSON_A, CONSENT_A = "1f6b9d3a-52c8-4a7e-8f10-c2e4b7a9d613", "c41e7a90-6b2f-4d83-a5c1-0e9f3b7d2a68"
PERSON_B, CONSENT_B = "7a2d4c81-e3f5-4b96-8d07-5c1a9e6f4b32", "e95b1f04-2a6c-4c7d-b3e8-8f0d2a5c7e19"


def show(title: str, body: Any) -> None:
    print(f"\n=== {title}\n{json.dumps(body, indent=2, default=str)}")  # noqa: T201 - a CLI


async def run(cmp_url: str, databank_url: str, token: str) -> None:
    suffix = uuid.uuid4().hex[:6].upper()  # asset IDs are never reused
    delivery = {
        "schema_version": "1.0",
        "project_id": PROJECT,
        "site_id": SITE,
        "batch_ref": f"RUN-DEMO-{suffix}",
        "declared_asset_count": 2,
        "assets": [
            {
                "asset_id": f"AST-{suffix}-1",
                "asset_type": "image",
                "captured_at": "2026-10-05T10:42:17+05:30",
                "subjects": [{"person_id": PERSON_A, "consent_id": CONSENT_A}],
                "other_persons": "none",
            },
            {
                "asset_id": f"AST-{suffix}-2",
                "asset_type": "video",
                "captured_at": "2026-10-05T11:05:00+05:30",
                "subjects": [
                    {"person_id": PERSON_A, "consent_id": CONSENT_A},
                    {"person_id": PERSON_B, "consent_id": CONSENT_B},
                ],
                "other_persons": "incidental",
            },
        ],
    }
    async with httpx.AsyncClient(base_url=databank_url, timeout=30) as mock:
        response = await mock.post("/mock/deliveries", json=delivery)
        response.raise_for_status()
        show("1. Lab delivery -> Databank registers each asset with CMP", response.json())

    async with DatabankClient(databank_url, token, retries=1) as databank:
        show(
            "3. CMP asks Databank what it holds for person A",
            (await databank.inventory(UUID(PERSON_A))).model_dump(mode="json"),
        )

        withdrawn = ConsentRecord(
            consent_ids=[UUID(CONSENT_B)],
            current_consent_id=UUID(CONSENT_B),
            person_id=UUID(PERSON_B),
            project_id=UUID(PROJECT),
            state="withdrawn",
            purposes=[{"code": "research_dataset", "granted": False}],
            changed_at=datetime.now(UTC),
        )
        ack = await databank.consent_changed(
            [ConsentEvent(event_id=uuid.uuid4(), consent=withdrawn)]
        )
        show("4. CMP tells Databank person B withdrew", ack.model_dump(mode="json"))

        instruction = Instruction(
            instruction_id=uuid.uuid4(),
            reason=InstructionReason.RIGHTS_REQUEST,
            reference="RR-DEMO",
            person_id=UUID(PERSON_A),
            issued_at=datetime.now(UTC),
            items=[
                InstructionItem(asset_id=f"AST-{suffix}-1", action=Action.ERASE),
                InstructionItem(asset_id=f"AST-{suffix}-2", action=Action.REDACT),
            ],
        )
        show(
            "5. CMP instructs an erasure and a redaction",
            (await databank.instruct(instruction)).model_dump(mode="json"),
        )

    print("\n... waiting for Databank to report back (call 6)")  # noqa: T201 - a CLI
    async with httpx.AsyncClient(
        base_url=cmp_url.rstrip("/") + PREFIX,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    ) as cmp:
        for _ in range(20):
            await asyncio.sleep(1)
            state = (await cmp.get("/stub/state")).json()
            reported = state["orphan_results"].get(str(instruction.instruction_id))
            if reported:
                show("6. Databank's results, as CMP received them", reported)
                break
        show(
            "CMP's view of the two assets",
            {k: v for k, v in state["assets"].items() if k.startswith(f"AST-{suffix}")},
        )


def main() -> None:  # pragma: no cover - a command line
    parser = argparse.ArgumentParser(description="Walk the Databank integration once.")
    parser.add_argument("--cmp-url", default="http://127.0.0.1:8000")
    parser.add_argument("--databank-url", default="http://127.0.0.1:8100")
    args = parser.parse_args()
    token = os.environ.get("DATABANK_SERVICE_TOKEN", "")
    if len(token) < 32:
        raise SystemExit("Set DATABANK_SERVICE_TOKEN, the same one the API and the mock use.")
    asyncio.run(run(args.cmp_url, args.databank_url, token))


if __name__ == "__main__":  # pragma: no cover
    main()
