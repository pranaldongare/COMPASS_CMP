"""A proof refused at the last moment leaves no file behind (ADR 0037).

The check before the file is stored stops almost every refusal. What gets past
it is somebody moving in the gap, and then the file is stored and no row names
it, so nothing could ever serve it or clear it. A proof of approval is evidence,
though: anything less certain than a refusal leaves the file where it is, since
a row may name it.
"""

from __future__ import annotations

import io
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

import pytest
from fastapi import UploadFile

from cmp.api import uploads
from cmp.api.routers.v1 import breaches as route
from cmp.core.errors import Conflict

REF = "breach/0123456789abcdef-token.pdf"


@asynccontextmanager
async def _conn() -> AsyncIterator[None]:
    yield None


@pytest.fixture
def deleted(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    out: list[str] = []

    async def passes(*_: Any, **__: Any) -> None:
        return None

    async def stored(*_: Any, **__: Any) -> uploads.Kept:
        return uploads.Kept(REF, "a" * 64, 10, "application/pdf", "scan.pdf")

    monkeypatch.setattr(route, "connection", _conn)
    monkeypatch.setattr(route, "transaction", _conn)
    monkeypatch.setattr(route.reports, "check_proof", passes)
    monkeypatch.setattr(route.uploads, "kept", stored)
    monkeypatch.setattr(route, "delete_upload", out.append)
    return out


async def _post() -> Any:
    principal: Any = type("Principal", (), {"user_id": 1})()
    return await route.add_report_proof(
        uuid4(),
        uuid4(),
        principal,
        UploadFile(io.BytesIO(b"%PDF-"), filename="scan.pdf"),
        "approval",
    )


async def test_a_refusal_takes_the_file_back_out(
    monkeypatch: pytest.MonkeyPatch, deleted: list[str]
) -> None:
    async def refused(*_: Any, **__: Any) -> None:
        raise Conflict("This report is already filed", code="report_filed")

    monkeypatch.setattr(route.reports, "add_proof", refused)
    with pytest.raises(Conflict):
        await _post()
    assert deleted == [REF]


async def test_a_failure_it_cannot_be_sure_of_leaves_the_file_alone(
    monkeypatch: pytest.MonkeyPatch, deleted: list[str]
) -> None:
    async def unknown(*_: Any, **__: Any) -> None:
        raise ConnectionError("the commit may or may not have landed")

    monkeypatch.setattr(route.reports, "add_proof", unknown)
    with pytest.raises(ConnectionError):
        await _post()
    assert deleted == []


async def test_a_proof_kept_keeps_its_file(
    monkeypatch: pytest.MonkeyPatch, deleted: list[str]
) -> None:
    async def kept(*_: Any, **__: Any) -> dict[str, Any]:
        return {"kinds": []}

    monkeypatch.setattr(route.reports, "add_proof", kept)
    assert await _post() == {"kinds": []}
    assert deleted == []
