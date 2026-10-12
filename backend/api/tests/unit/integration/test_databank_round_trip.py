"""The two sides together: the mock Databank and CMP's endpoints, in process.

A lab delivery is quarantined and registered with CMP; the verdicts decide what
is usable; CMP asks for an inventory, tells Databank a consent changed, and
instructs an erasure and a redaction - and the outcomes come back to CMP.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from cmp.integration.databank.client import DatabankClient
from cmp.integration.databank.contracts import (
    Action,
    ConsentEvent,
    ConsentRecord,
    Instruction,
    InstructionItem,
    InstructionReason,
)
from cmp.integration.databank.mock_server import MockDatabank, create_app
from cmp.integration.databank.store import IntegrationStore
from tests.unit.integration.conftest import (
    CONSENT_B,
    CONSENT_W,
    PERSON_A,
    PERSON_B,
    PERSON_W,
    PROJECT,
    TOKEN,
)
from tests.unit.integration.test_databank_contracts import BRIEF_DELIVERY


@pytest.fixture
def databank(cmp_app: FastAPI) -> MockDatabank:
    return MockDatabank(
        cmp_url="http://cmp",
        token=TOKEN,
        cmp_transport=httpx.ASGITransport(app=cmp_app),
    )


@pytest.fixture
async def mock(databank: MockDatabank) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=create_app(databank))
    async with httpx.AsyncClient(transport=transport, base_url="http://databank") as http:
        yield http


@pytest.fixture
async def client(databank: MockDatabank, store: IntegrationStore) -> AsyncIterator[DatabankClient]:
    """CMP's client, pointed at the mock in process."""
    transport = httpx.ASGITransport(app=create_app(databank))
    async with DatabankClient(
        "http://databank", TOKEN, transport=transport, retries=0, store=store
    ) as databank_client:
        yield databank_client


async def deliver(mock: httpx.AsyncClient, body: dict | None = None) -> dict:
    response = await mock.post("/mock/deliveries", json=body or BRIEF_DELIVERY)
    assert response.status_code == 200, response.text
    return response.json()


async def test_a_delivery_is_registered_and_cleared_by_its_verdicts(
    mock: httpx.AsyncClient, store: IntegrationStore
) -> None:
    out = await deliver(mock)
    assert out["received"] == 2 and not out["short_delivery"]
    assert out["assets"]["AST-000184213"]["verdict"] == "valid"
    assert out["assets"]["AST-000184213"]["state"] == "usable"
    # Both people are active; the second is partly withdrawn but still grants research.
    assert out["assets"]["AST-000184377"]["state"] == "usable"
    # CMP has them both, with their verdicts.
    assert set(store.assets) == {"AST-000184213", "AST-000184377"}


async def test_an_asset_without_a_valid_verdict_stays_in_quarantine(
    mock: httpx.AsyncClient,
) -> None:
    body = {
        **BRIEF_DELIVERY,
        "batch_ref": "RUN-2026-002",
        "declared_asset_count": 2,
        "assets": [
            {
                "asset_id": "AST-900000001",
                "asset_type": "audio",
                "captured_at": "2026-10-05T10:00:00+05:30",
                "subjects": [{"person_id": str(PERSON_A), "consent_id": str(uuid4())}],
            }
        ],
    }
    out = await deliver(mock, body)
    assert out["assets"]["AST-900000001"] == {
        "verdict": "unknown",
        "state": "quarantined",
        "subjects": [{"person_id": str(PERSON_A), "verdict": "unknown", "purposes": []}],
    }
    # Two declared, one received: a short delivery is visible.
    assert out["short_delivery"] is True


async def test_an_id_in_use_is_refused(mock: httpx.AsyncClient) -> None:
    await deliver(mock)
    again = await deliver(mock)
    assert again["refused"] == {
        "AST-000184213": "already in use",
        "AST-000184377": "already in use",
    }


async def test_the_inventory_comes_from_databanks_own_index(
    mock: httpx.AsyncClient, client: DatabankClient
) -> None:
    await deliver(mock)
    inventory = await client.inventory(PERSON_A)
    assert {a.asset_id for a in inventory.assets} == {"AST-000184213", "AST-000184377"}
    assert {a.state for a in inventory.assets} == {"usable"}
    narrowed = await client.inventory(PERSON_B, consent_id=CONSENT_B)
    assert [a.asset_id for a in narrowed.assets] == ["AST-000184377"]


async def test_a_withdrawal_restricts_every_asset_with_that_person(
    mock: httpx.AsyncClient, client: DatabankClient
) -> None:
    await deliver(mock)
    withdrawn = ConsentRecord(
        consent_ids=[CONSENT_B],
        current_consent_id=CONSENT_B,
        person_id=PERSON_B,
        project_id=PROJECT,
        state="withdrawn",
        purposes=[{"code": "research_dataset", "granted": False}],
        changed_at=datetime.now(UTC),
    )
    sent = ConsentEvent(event_id=uuid4(), consent=withdrawn)
    ack = await client.consent_changed([sent])
    assert ack.accepted == [sent.event_id]
    # Again: acknowledged as a duplicate, nothing changes.
    assert (await client.consent_changed([sent])).duplicates == [sent.event_id]
    states = {a.asset_id: a.state for a in (await client.inventory(PERSON_A)).assets}
    # The video holds person B too: it is held back. The image is only A's.
    assert states == {"AST-000184213": "usable", "AST-000184377": "restricted"}


async def test_an_erasure_and_a_redaction_report_back_to_cmp(
    mock: httpx.AsyncClient, client: DatabankClient, store: IntegrationStore
) -> None:
    await deliver(mock)
    instruction = Instruction(
        instruction_id=uuid4(),
        reason=InstructionReason.RIGHTS_REQUEST,
        reference="RR-2026-000042",
        person_id=PERSON_A,
        issued_at=datetime.now(UTC),
        items=[
            InstructionItem(asset_id="AST-000184213", action=Action.ERASE),
            InstructionItem(asset_id="AST-000184377", action=Action.REDACT),
        ],
    )
    accepted = await client.instruct(instruction)
    assert accepted.status == "accepted" and not accepted.duplicate
    # Results arrived on call 6: the erasure done with evidence, the redaction refused.
    results = store.instructions[instruction.instruction_id].results
    assert results["AST-000184213"].outcome == "done"
    assert results["AST-000184213"].evidence is not None
    assert results["AST-000184213"].evidence.derivatives_deleted == 2
    assert results["AST-000184377"].outcome == "failed"
    assert results["AST-000184377"].reason == "redaction_not_supported"
    # Databank told CMP the asset is gone, and the ID can never come back.
    assert store.assets["AST-000184213"].deleted is True
    assert (await client.instruct(instruction)).duplicate is True
    inventory = await client.inventory(PERSON_A)
    assert [a.asset_id for a in inventory.assets] == ["AST-000184377"]


async def test_a_hold_blocks_erasure_until_it_is_released(
    mock: httpx.AsyncClient, client: DatabankClient, store: IntegrationStore
) -> None:
    await deliver(mock)

    async def instruct(*items: tuple[str, Action]) -> dict[str, str]:
        instruction = Instruction(
            instruction_id=uuid4(),
            reason=InstructionReason.LEGAL_HOLD,
            person_id=PERSON_A,
            issued_at=datetime.now(UTC),
            items=[InstructionItem(asset_id=a, action=act) for a, act in items],
        )
        await client.instruct(instruction)
        held = store.instructions[instruction.instruction_id].results
        return {a: r.reason or r.outcome for a, r in held.items()}

    assert await instruct(("AST-000184213", Action.HOLD)) == {"AST-000184213": "done"}
    assert await instruct(("AST-000184213", Action.ERASE)) == {"AST-000184213": "legal_hold"}
    await instruct(("AST-000184213", Action.RELEASE_HOLD))
    assert await instruct(("AST-000184213", Action.ERASE)) == {"AST-000184213": "done"}


async def test_redaction_when_databank_supports_it(
    databank: MockDatabank, mock: httpx.AsyncClient, client: DatabankClient, store: IntegrationStore
) -> None:
    databank.redaction_supported = True
    await deliver(mock)
    instruction = Instruction(
        instruction_id=uuid4(),
        reason=InstructionReason.CONSENT_WITHDRAWN,
        person_id=PERSON_B,
        issued_at=datetime.now(UTC),
        items=[InstructionItem(asset_id="AST-000184377", action=Action.REDACT)],
    )
    await client.instruct(instruction)
    assert store.instructions[instruction.instruction_id].results["AST-000184377"].outcome == "done"
    # The redacted asset came back as version 2, with person A alone.
    assert store.assets["AST-000184377"].version == 2
    assert [a.asset_id for a in (await client.inventory(PERSON_B)).assets] == []


async def test_a_withdrawn_persons_new_asset_is_quarantined(mock: httpx.AsyncClient) -> None:
    body = {
        **BRIEF_DELIVERY,
        "batch_ref": "RUN-2026-003",
        "declared_asset_count": 1,
        "assets": [
            {
                "asset_id": "AST-900000002",
                "asset_type": "image",
                "captured_at": "2026-10-05T10:00:00+05:30",
                "subjects": [{"person_id": str(PERSON_W), "consent_id": str(CONSENT_W)}],
            }
        ],
    }
    out = await deliver(mock, body)
    assert out["assets"]["AST-900000002"]["verdict"] == "restricted"
    assert out["assets"]["AST-900000002"]["state"] == "quarantined"
