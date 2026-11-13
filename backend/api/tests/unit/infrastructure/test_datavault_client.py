"""The call to DataVault reads its answer strictly and says little when it fails (0070)."""

from __future__ import annotations

import httpx
import pytest

from cmp.infrastructure.datavault import DataVaultFailed, lookup, usable_base_url
from cmp.infrastructure.datavault.client import MAX_ASSETS, read

SAMPLE = {
    "person_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "assets": [
        {
            "asset_id": "DV-IMG-000101",
            "consent_id": "9b2f4c1d-6e3a-4b7f-8d1c-2e5a9f0b3c71",
            "project_id": "0e8d6c4b-2a19-4f7e-b5d3-c1a9e7f50b22",
            "mid": 4909,
            "datapath": "/vault/a/000101",
        },
        {
            "asset_id": "DV-VID-000102",
            "consent_id": "9b2f4c1d-6e3a-4b7f-8d1c-2e5a9f0b3c71",
            "project_id": "0e8d6c4b-2a19-4f7e-b5d3-c1a9e7f50b22",
            "mid": 4909,
            "datapath": "/vault/a/000102",
        },
    ],
}


def test_the_agreed_answer_is_read_as_sent() -> None:
    first, second = read(SAMPLE)
    assert first.asset_ref == "DV-IMG-000101"
    assert first.consent_ref == "9b2f4c1d-6e3a-4b7f-8d1c-2e5a9f0b3c71"
    assert first.project_ref == "0e8d6c4b-2a19-4f7e-b5d3-c1a9e7f50b22"
    assert first.mid == "4909", "a number is kept as text: it is DataVault's, not ours to add up"
    assert first.datapath == "/vault/a/000101"
    assert second.asset_ref == "DV-VID-000102"


def test_nothing_held_is_an_answer() -> None:
    assert read({"person_id": "x", "assets": []}) == []


@pytest.mark.parametrize("body", [None, [], "ok", {}, {"assets": "none"}, {"assets": ["x"]}])
def test_anything_else_is_unreadable(body: object) -> None:
    with pytest.raises(DataVaultFailed) as failed:
        read(body)
    assert failed.value.code == "unreadable"


def test_an_asset_without_an_identifier_is_dropped_and_odd_values_are_not_kept() -> None:
    [only] = read(
        {
            "assets": [
                {"consent_id": "c"},
                {"asset_id": " A1 ", "consent_id": {"x": 1}, "mid": True, "datapath": "p" * 5000},
            ]
        }
    )
    assert only.asset_ref == "A1"
    assert only.consent_ref is None and only.mid is None
    assert only.datapath is not None and len(only.datapath) == 2000


def test_a_list_too_long_is_refused_whole() -> None:
    with pytest.raises(DataVaultFailed) as failed:
        read({"assets": [{"asset_id": str(i)} for i in range(MAX_ASSETS + 1)]})
    assert failed.value.code == "too_many"


@pytest.mark.parametrize(
    ("raw", "kept"),
    [
        ("https://datavault.internal/api/", "https://datavault.internal/api"),
        ("http://10.0.0.5:8090", "http://10.0.0.5:8090"),
        ("ftp://datavault.internal", None),
        ("datavault.internal", None),
        ("https://user:pw@datavault.internal", None),
        ("https://datavault.internal/api?x=1", None),
        ("https://datavault.internal/#a", None),
        ("https://data vault.internal", None),
        ("https://", None),
    ],
)
def test_an_address_is_one_the_call_can_be_seen_to_go_to(raw: str, kept: str | None) -> None:
    assert usable_base_url(raw) == kept


async def _ask(handler: httpx.MockTransport, key: str | None = "k-123") -> object:
    return await lookup(
        base_url="https://datavault.internal/api",
        api_key=key,
        api_key_header="X-API-Key",
        request_ref="RR-2026-0007",
        person_no=42,
        transport=handler,
    )


async def test_the_call_is_the_agreed_one() -> None:
    seen: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=SAMPLE)

    held = await _ask(httpx.MockTransport(answer))
    assert len(held) == 2  # type: ignore[arg-type]
    [request] = seen
    assert request.method == "GET"
    assert request.url.path == "/api/lookup"
    assert dict(request.url.params) == {"request_id": "RR-2026-0007", "person_id": "42"}
    assert request.headers["X-API-Key"] == "k-123"


async def test_without_a_key_no_key_header_is_sent() -> None:
    seen: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"assets": []})

    assert await _ask(httpx.MockTransport(answer), key=None) == []
    assert "x-api-key" not in seen[0].headers


@pytest.mark.parametrize(
    ("response", "code"),
    [
        (httpx.Response(503, text="secret upstream words"), "status_503"),
        (httpx.Response(401, json={"detail": "bad key k-123"}), "status_401"),
        (httpx.Response(302, headers={"Location": "http://169.254.169.254/"}), "status_302"),
        (httpx.Response(200, text="<html>"), "unreadable"),
    ],
)
async def test_a_failure_is_a_code_and_never_what_the_other_side_said(
    response: httpx.Response, code: str
) -> None:
    with pytest.raises(DataVaultFailed) as failed:
        await _ask(httpx.MockTransport(lambda _: response))
    assert failed.value.code == code
    assert str(failed.value) == code


async def test_no_answer_in_time_and_no_way_there() -> None:
    def slow(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    def gone(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    with pytest.raises(DataVaultFailed) as failed:
        await _ask(httpx.MockTransport(slow))
    assert failed.value.code == "timeout"
    with pytest.raises(DataVaultFailed) as failed:
        await _ask(httpx.MockTransport(gone))
    assert failed.value.code == "unreachable"
