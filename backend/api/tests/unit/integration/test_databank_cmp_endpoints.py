"""CMP's three endpoints (calls 1, 2 and 6): the verdicts, and the brief's
reliability rules - idempotent IDs, rising versions, IDs never reused."""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from cmp.integration.databank.contracts import Instruction
from cmp.integration.databank.store import IntegrationStore
from tests.unit.integration.conftest import (
    AUTH,
    CONSENT_A,
    CONSENT_B,
    CONSENT_W,
    CONSENT_W_OLD,
    PERSON_A,
    PERSON_B,
    PERSON_W,
    asset,
    event,
)

URL = "/integration/v1/asset-events"


async def register(cmp: httpx.AsyncClient, *assets: dict, **kw: object) -> list[dict]:
    response = await cmp.post(
        URL, json={"events": [event("registered", asset=a, **kw) for a in assets]}, headers=AUTH
    )
    assert response.status_code == 200, response.text
    return response.json()["results"]


# ----------------------------------------------------------------- access


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer wrong"}, {"Authorization": "Basic x"}],
)
async def test_a_call_without_the_service_token_is_refused(
    cmp: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    response = await cmp.get(f"/integration/v1/consents/{CONSENT_A}", headers=headers)
    assert response.status_code == 401


# ---------------------------------------------------------------- verdicts


async def test_the_briefs_asset_is_valid_for_its_purposes(cmp: httpx.AsyncClient) -> None:
    [result] = await register(cmp, asset())
    assert result["status"] == "accepted"
    assert result["verdict"] == "valid"
    assert result["subjects"] == [
        {
            "person_id": str(PERSON_A),
            "verdict": "valid",
            "purposes": ["research_dataset", "model_evaluation"],
        }
    ]


async def test_a_partly_withdrawn_consent_is_valid_for_what_is_left(
    cmp: httpx.AsyncClient,
) -> None:
    [result] = await register(cmp, asset(subjects=[(PERSON_A, CONSENT_A), (PERSON_B, CONSENT_B)]))
    assert result["verdict"] == "valid"
    assert result["subjects"][1]["purposes"] == ["research_dataset"]


@pytest.mark.parametrize(
    ("subjects", "captured_at", "verdict"),
    [
        # Withdrawn after capture: it was in force, it is not now.
        ([(PERSON_W, CONSENT_W)], "2026-10-05T10:00:00+05:30", "restricted"),
        # An older ID in the chain resolves to the current state.
        ([(PERSON_W, CONSENT_W_OLD)], "2026-10-05T10:00:00+05:30", "restricted"),
        # Captured after the withdrawal: nothing was in force.
        ([(PERSON_W, CONSENT_W)], "2026-10-07T10:00:00+05:30", "invalid"),
        # Captured before the consent was given.
        ([(PERSON_A, CONSENT_A)], "2026-09-01T10:00:00+05:30", "invalid"),
        # A person and a consent that do not belong together.
        ([(PERSON_B, CONSENT_A)], "2026-10-05T10:42:17+05:30", "invalid"),
        # A consent CMP has never heard of.
        ([(PERSON_A, uuid4())], "2026-10-05T10:42:17+05:30", "unknown"),
        # Two people: the asset takes the stricter verdict.
        ([(PERSON_A, CONSENT_A), (PERSON_W, CONSENT_W)], "2026-10-05T10:00:00+05:30", "restricted"),
    ],
)
async def test_the_verdict_follows_the_consent(
    cmp: httpx.AsyncClient, subjects: list, captured_at: str, verdict: str
) -> None:
    [result] = await register(cmp, asset(subjects=subjects, captured_at=captured_at))
    assert result["verdict"] == verdict


async def test_an_asset_from_another_site_is_invalid(cmp: httpx.AsyncClient) -> None:
    [result] = await register(cmp, asset(site=uuid4()))
    assert result["verdict"] == "invalid"


# ----------------------------------------------------------- reliability


async def test_the_same_event_twice_gets_the_first_answer(
    cmp: httpx.AsyncClient, store: IntegrationStore
) -> None:
    same = uuid4()
    [first] = await register(cmp, asset(), event_id=same)
    [again] = await register(cmp, asset(subjects=[(PERSON_A, uuid4())]), event_id=same)
    assert again == first
    assert store.assets["AST-000184213"].verdict == "valid"


async def test_an_older_version_is_ignored(cmp: httpx.AsyncClient) -> None:
    await register(cmp, asset(version=2))
    response = await cmp.post(
        URL, json={"events": [event("updated", asset=asset(version=2))]}, headers=AUTH
    )
    assert response.json()["results"][0]["status"] == "ignored_stale"
    response = await cmp.post(
        URL, json={"events": [event("updated", asset=asset(version=3))]}, headers=AUTH
    )
    assert response.json()["results"][0]["status"] == "accepted"


async def test_a_deleted_assets_id_is_never_reused(cmp: httpx.AsyncClient) -> None:
    await register(cmp, asset())
    deleted = event("deleted", asset_id="AST-000184213", reason="quality")
    response = await cmp.post(URL, json={"events": [deleted]}, headers=AUTH)
    assert response.json()["results"][0]["status"] == "accepted"
    [again] = await register(cmp, asset())
    assert again["status"] == "rejected"
    assert "never reused" in again["detail"]


async def test_a_release_is_recorded(cmp: httpx.AsyncClient, store: IntegrationStore) -> None:
    await register(cmp, asset())
    released = event(
        "released",
        asset_id="AST-000184213",
        release={"recipient": "Model team", "released_on": "2026-10-08"},
    )
    response = await cmp.post(URL, json={"events": [released]}, headers=AUTH)
    assert response.json()["results"][0]["status"] == "accepted"
    assert store.assets["AST-000184213"].releases[0].recipient == "Model team"


# --------------------------------------------------- call 2: consent lookup


async def test_any_id_in_the_chain_gives_the_current_record(cmp: httpx.AsyncClient) -> None:
    response = await cmp.get(f"/integration/v1/consents/{CONSENT_W_OLD}", headers=AUTH)
    assert response.status_code == 200
    record = response.json()
    assert record["current_consent_id"] == str(CONSENT_W)
    assert record["state"] == "withdrawn"
    # Where and when it was given stay in CMP.
    assert "site_id" not in record and "given_at" not in record


async def test_an_unknown_consent_is_not_found(cmp: httpx.AsyncClient) -> None:
    response = await cmp.get(f"/integration/v1/consents/{uuid4()}", headers=AUTH)
    assert response.status_code == 404


# ------------------------------------------------- call 6: instruction results


async def test_a_request_closes_only_when_every_item_is_done(
    cmp: httpx.AsyncClient, store: IntegrationStore
) -> None:
    instruction = Instruction.model_validate(
        {
            "instruction_id": str(uuid4()),
            "reason": "rights_request",
            "person_id": str(PERSON_A),
            "issued_at": "2026-10-07T11:00:00+05:30",
            "items": [
                {"asset_id": "AST-1", "action": "erase"},
                {"asset_id": "AST-2", "action": "erase"},
            ],
        }
    )
    store.remember_instruction(instruction)
    url = f"/integration/v1/instructions/{instruction.instruction_id}/results"

    def item(asset_id: str, outcome: str) -> dict[str, str]:
        return {"asset_id": asset_id, "action": "erase", "outcome": outcome}

    # An early partial result: one item done.
    part = {"instruction_id": str(instruction.instruction_id), "items": [item("AST-1", "done")]}
    status = (await cmp.post(url, json=part, headers=AUTH)).json()
    assert status == {
        "instruction_id": str(instruction.instruction_id),
        "items_reported": 1,
        "items_done": 1,
        "complete": False,
    }
    rest = {"instruction_id": str(instruction.instruction_id), "items": [item("AST-2", "done")]}
    assert (await cmp.post(url, json=rest, headers=AUTH)).json()["complete"] is True


async def test_the_path_and_the_body_must_name_one_instruction(cmp: httpx.AsyncClient) -> None:
    body = {
        "instruction_id": str(uuid4()),
        "items": [{"asset_id": "AST-1", "action": "erase", "outcome": "done"}],
    }
    response = await cmp.post(
        f"/integration/v1/instructions/{uuid4()}/results", json=body, headers=AUTH
    )
    assert response.status_code == 400
