"""A nominee's code is refused for its shape as every other code is (2026-11-08).

`POST /rights/nominee/requests` took its code as a plain form field of four to
ten characters. A code that was not digits passed it, reached the service and
came back 400 otp_invalid, where every other route that takes a code refuses
it 422 by its schema (`OtpCode`). The form field now carries the same
constraint, so the contract is one: a code the schema refuses is 422 for every
caller alike, before anything is looked up.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from cmp.api import errors
from cmp.api.routers.public import rights as public


def _app() -> FastAPI:
    app = FastAPI()
    errors.install(app)
    app.include_router(public.router)
    return app


@pytest.fixture
def reached(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The codes that got as far as the service."""
    codes: list[str] = []

    async def enforce(*_args: Any, **_kwargs: Any) -> None:
        return None

    async def nominee_submit(_conn: Any, **kwargs: Any) -> dict[str, Any]:
        codes.append(kwargs["code"])
        return {"reference": "DSR-2026-0001"}

    @asynccontextmanager
    async def transaction() -> AsyncIterator[None]:
        yield None

    monkeypatch.setattr(public.ratelimit, "enforce", enforce)
    monkeypatch.setattr(public.rights_service, "nominee_submit", nominee_submit)
    monkeypatch.setattr(public, "transaction", transaction)
    return codes


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


def _form(code: str) -> dict[str, str]:
    return {
        "nomination_uuid": str(uuid.uuid4()),
        "code": code,
        "request_type": "access",
        "request_text": "The principal's records, please",
        "trigger_event": "death",
    }


@pytest.mark.parametrize("code", ["abcdef", "12 456", "12345a", "123", "12345678901"])
async def test_a_code_the_schema_refuses_is_422_before_the_service(
    client: httpx.AsyncClient, reached: list[str], code: str
) -> None:
    answer = await client.post("/rights/nominee/requests", data=_form(code))
    assert answer.status_code == 422, answer.text
    error = answer.json()["error"]
    assert (error["code"], error["field"]) == ("validation_failed", "code")
    assert reached == [], "a code the schema refuses never reaches the service"


async def test_a_code_of_digits_reaches_the_service(
    client: httpx.AsyncClient, reached: list[str]
) -> None:
    answer = await client.post("/rights/nominee/requests", data=_form("123456"))
    assert answer.status_code == 201, answer.text
    assert reached == ["123456"]


def test_the_published_contract_says_digits() -> None:
    """The OpenAPI document is what the clients are built from."""
    spec = _app().openapi()
    body = spec["paths"]["/rights/nominee/requests"]["post"]["requestBody"]
    ref = body["content"]["multipart/form-data"]["schema"]["$ref"].rsplit("/", 1)[-1]
    code = spec["components"]["schemas"][ref]["properties"]["code"]
    assert (code["pattern"], code["minLength"], code["maxLength"]) == ("^[0-9]+$", 4, 10)
