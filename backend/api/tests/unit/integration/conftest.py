"""Shared pieces for the Databank stub tests: a CMP app with only the
integration router, a fresh store per test, and the shared service token."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI
from pydantic import SecretStr

from cmp.api import errors
from cmp.api.routers.integration import databank_router
from cmp.core.config import settings
from cmp.integration.databank import service
from cmp.integration.databank.store import IntegrationStore, get_store
from cmp.integration.databank.verdicts import MockConsentResolver

TOKEN = "test-databank-service-token-0123456789abcdef"
AUTH = {"Authorization": f"Bearer {TOKEN}"}

# The brief's example IDs, and the fixtures' other people.
PROJECT = UUID("5d0c2c1e-8a41-4f1b-b6a0-3e9d7c2a1f54")
SITE = UUID("a8f3e6b2-1c7d-4e59-9b02-6d4f8a1c3e70")
PERSON_A, CONSENT_A = (
    UUID("1f6b9d3a-52c8-4a7e-8f10-c2e4b7a9d613"),
    UUID("c41e7a90-6b2f-4d83-a5c1-0e9f3b7d2a68"),
)  # in force
PERSON_B, CONSENT_B = (
    UUID("7a2d4c81-e3f5-4b96-8d07-5c1a9e6f4b32"),
    UUID("e95b1f04-2a6c-4c7d-b3e8-8f0d2a5c7e19"),
)  # partly withdrawn: research_dataset still granted
PERSON_W, CONSENT_W_OLD, CONSENT_W = (
    UUID("3c8e5a17-9d2b-4f60-8c41-a7e3d5b9f026"),
    UUID("0b6f2d18-7c3e-4a95-b1d4-9e2a6c8f5d70"),
    UUID("4d9c1e52-8b7a-4f36-a0e2-5c3b9d7f1a84"),
)  # withdrawn on 2026-10-06 08:00 +05:30


@pytest.fixture(autouse=True)
def _token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "databank_service_token", SecretStr(TOKEN))


@pytest.fixture
def store() -> IntegrationStore:
    return IntegrationStore()


@pytest.fixture
def cmp_app(store: IntegrationStore) -> Iterator[FastAPI]:
    app = FastAPI()
    errors.install(app)
    app.include_router(databank_router)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[service.get_resolver] = MockConsentResolver.from_file
    yield app


@pytest.fixture
async def cmp(cmp_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=cmp_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://cmp") as http:
        yield http


def asset(
    asset_id: str = "AST-000184213",
    *,
    subjects: list[tuple[UUID, UUID]] | None = None,
    captured_at: str = "2026-10-05T10:42:17+05:30",
    version: int = 1,
    project: UUID = PROJECT,
    site: UUID = SITE,
) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "asset_version": version,
        "project_id": str(project),
        "site_id": str(site),
        "batch_ref": "RUN-2026-001",
        "asset_type": "image",
        "captured_at": captured_at,
        "content_sha256": "9f2c41d7e41b",
        "subjects": [
            {"person_id": str(p), "consent_id": str(c)}
            for p, c in (subjects or [(PERSON_A, CONSENT_A)])
        ],
        "other_persons": "none",
    }


def event(kind: str = "registered", **fields: Any) -> dict[str, Any]:
    return {
        "event_id": str(fields.pop("event_id", uuid4())),
        "type": kind,
        "occurred_at": datetime.now().astimezone().isoformat(),
        **fields,
    }
