"""Rights requests by office over HTTP (0055).

The world's principal holds a consent on the DPO office's notice: her
offices are that one. Asked of both, she makes one request to each, received
together; the Legal PoC sees its own and the DPO is told the other is not
there. The DPO transfers its request to the Legal office with a reason - it
leaves the DPO's view, arrives sealed in Legal's, and the Legal office is
emailed. A stranger's request from the public form is in both queues until
the DPO claims it; then the Legal office is told it is not there.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.http.conftest import SessionFactory, fresh
from tests.http.contract import call
from tests.http.test_04_rights import _public_request
from tests.http.world import World, build

RIGHTS = "/requests/{request_uuid}"


@pytest.fixture(scope="module")
def _world_box() -> dict[str, Any]:
    return {}


@pytest.fixture
async def world(
    http: httpx.AsyncClient, session_for: SessionFactory, queued: Any, _world_box: dict[str, Any]
) -> World:
    if "w" not in _world_box:
        _world_box["w"] = await build(http, session_for, queued)
    return _world_box["w"]


async def test_her_offices_and_a_request_to_each(
    http: httpx.AsyncClient, world: World, queued: Any, session_for: SessionFactory
) -> None:
    legal = await session_for("legal")
    offices = await call(http, "GET", "/me/requests/offices", session=world.principal)
    assert [o["code"] for o in offices.json()["offices"]] == ["rnd"]

    made = await call(
        http,
        "POST",
        "/me/requests",
        session=world.principal,
        expect=201,
        json={
            "request_type": "access",
            "request_text": f"What does each office hold? {fresh()}",
            "office": "both",
        },
    )
    first = made.json()
    [second] = first["also"]
    assert first["reference"] != second["reference"]
    assert first["received_at"] == second["received_at"], "the same D0"

    # The DPO office's is the DPO's; the Legal office's is Legal's alone.
    dpo_view = await call(
        http,
        "GET",
        f"/requests/{first['request_uuid']}",
        template=RIGHTS,
        session=world.dpo,
    )
    assert dpo_view.json()["office"] == "rnd"
    await call(
        http,
        "GET",
        f"/requests/{second['request_uuid']}",
        template=RIGHTS,
        session=world.dpo,
        expect=404,
    )
    legal_view = await call(
        http,
        "GET",
        f"/requests/{second['request_uuid']}",
        template=RIGHTS,
        session=legal,
    )
    assert legal_view.json()["office"] == "hr"

    # The DPO sends its one across, with a reason; the clock stays.
    before = len(queued)
    moved = await call(
        http,
        "POST",
        f"/requests/{first['request_uuid']}/transfer",
        template=RIGHTS + "/transfer",
        session=world.dpo,
        json={"office": "hr", "reason": "Her question is about her employment."},
    )
    assert moved.json() == {
        "request_uuid": first["request_uuid"],
        "reference": first["reference"],
        "office": "hr",
    }
    assert any(name.endswith("send_rights_transfer_received") for name, _ in queued[before:])
    await call(
        http,
        "GET",
        f"/requests/{first['request_uuid']}",
        template=RIGHTS,
        session=world.dpo,
        expect=404,
    )
    arrived = await call(
        http,
        "GET",
        f"/requests/{first['request_uuid']}",
        template=RIGHTS,
        session=legal,
    )
    body = arrived.json()
    assert body["office"] == "hr" and body["transferred_from"] == "rnd"
    assert str(body["transfer_reason"]).startswith("SE::")
    assert body["due_at"] == dpo_view.json()["due_at"]


async def test_the_shared_intake_is_claimed_once(
    http: httpx.AsyncClient, world: World, queued: Any, session_for: SessionFactory
) -> None:
    legal = await session_for("legal")
    reference = await _public_request(http, queued, world.principal_email, f"Hello {fresh()}")
    listed = await call(http, "GET", "/requests", session=legal, params={"q": reference})
    row = next(r for r in listed.json()["items"] if r["reference"] == reference)
    assert row["office"] is None, "in the shared intake, Legal's queue shows it too"

    claimed = await call(
        http,
        "POST",
        f"/requests/{row['request_uuid']}/claim",
        template=RIGHTS + "/claim",
        session=world.dpo,
    )
    assert claimed.json()["office"] == "rnd"
    await call(
        http,
        "POST",
        f"/requests/{row['request_uuid']}/claim",
        template=RIGHTS + "/claim",
        session=legal,
        expect=404,
    )
