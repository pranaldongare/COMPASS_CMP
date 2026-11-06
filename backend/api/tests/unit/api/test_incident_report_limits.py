"""The public link's limits count the address the platform trusts.

Behind the relay's collector, or a proxy, every socket is the same one: counted
there, all reporters would share one bucket and twenty codes an hour between
them. `client_ip` is the one place that decides which address is the caller's.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import Response
from starlette.requests import Request

from cmp.api.middleware import request_context
from cmp.api.routers.public import incident_reports as public
from cmp.domain.breach import intake


def _request(forwarded: str | None = None) -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/incident-reports",
            "query_string": b"",
            "headers": headers,
            "client": ("10.0.0.9", 40000),
        }
    )


@pytest.fixture
def seen(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    out: dict[str, Any] = {}

    async def send_code(*, email: str, ip_address: str | None) -> str:
        out["code"] = ip_address
        return "On its way"

    async def submit(conn: Any, **kwargs: Any) -> dict[str, Any]:
        out["report"] = kwargs["ip_address"]
        return {"reference": "INC-2026-0001", "message": "Thank you"}

    @asynccontextmanager
    async def transaction() -> Any:
        yield None

    monkeypatch.setattr(intake, "send_code", send_code)
    monkeypatch.setattr(intake, "submit", submit)
    monkeypatch.setattr(public, "transaction", transaction)
    return out


async def _both(request: Request) -> None:
    await public.report_code(public.IncidentCodeIn(email="a@example.org"), request, Response())
    body = public.IncidentReportIn(
        name="Asha", email="a@example.org", code="123456", title="A", incident_details="B"
    )
    await public.report_incident(body, request, Response())


async def test_in_production_the_limits_count_the_caller_behind_the_collector(
    seen: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(request_context, "settings", SimpleNamespace(is_production=True))
    await _both(_request("203.0.113.7, 10.0.0.1"))
    assert seen == {"code": "203.0.113.7", "report": "203.0.113.7"}


async def test_elsewhere_a_header_cannot_choose_the_bucket(seen: dict[str, Any]) -> None:
    await _both(_request("203.0.113.7"))
    assert seen == {"code": "10.0.0.9", "report": "10.0.0.9"}
