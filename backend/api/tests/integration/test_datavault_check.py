"""Check in DataVault: what it holds of a rights request's person (0070, 2026-11-13).

The DPO or Legal asks from the request, or the platform asks by itself when
the holders it found include a project's DCO Admin. One call, kept whether or
not it is answered; the answer is matched to this person's own consents and
no wider; the DCO Admin sees their project's assets on their ticket; and
nothing else about the request changes.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from cmp.core.errors import Conflict, Forbidden, ValidationFailed
from cmp.core.permissions import Role
from cmp.db.repositories import datavault as repo
from cmp.domain.datavault import checks, connection
from cmp.domain.rights import service
from tests.integration.test_holders_by_owner import _only_dco_admin, _request
from tests.integration.test_rights_flows import _consent

pytestmark = pytest.mark.integration

DPO = Role.DPO
KEY = "dv-key-0123456789"
URL = "https://datavault.internal/api"


async def _on(conn: Any, seeded: dict[str, Any], **changes: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "base_url": URL,
        "api_key": KEY,
        "clear_api_key": False,
        "api_key_header": None,
        "enabled": True,
        **changes,
    }
    return await connection.save(conn, actor_id=int(seeded["users"]["admin"]["id"]), **values)


def _answering(assets: list[dict[str, Any]], seen: list[httpx.Request] | None = None) -> Any:
    def answer(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(200, json={"person_id": "x", "assets": assets})

    return httpx.MockTransport(answer)


def dv_held(consent_ref: str) -> Any:
    from cmp.infrastructure.datavault import Held

    return Held(asset_ref="A", consent_ref=consent_ref, project_ref=None, mid=None, datapath=None)


async def _check(conn: Any, row: dict[str, Any], transport: Any, actor: int | None) -> None:
    what = await checks.prepare(conn, row, role=DPO if actor else None)
    await checks.store(conn, what, await checks.ask(what, transport=transport), actor_id=actor)


# ------------------------------------------------------------- the connection
async def test_the_connection_is_saved_and_its_key_is_never_served(
    conn: Any, seeded: dict[str, Any]
) -> None:
    # The HTTP suite commits its own changes to this row's trail: count from here.
    start = await (
        await conn.execute("SELECT coalesce(max(log_id), 0) AS n FROM audit_log")
    ).fetchone()
    before = await connection.overview(conn)
    assert before["enabled"] is False and before["base_url"] is None
    assert await connection.ready(conn) is None, "nothing is called until it is set up"

    shown = await _on(conn, seeded, base_url=URL + "/")
    assert shown["base_url"] == URL and shown["enabled"] is True
    assert shown["api_key_set"] is True and shown["api_key_header"] == "X-API-Key"
    assert KEY not in repr(shown)
    stored = await repo.connection(conn)
    assert KEY.encode() not in bytes(stored["api_key_sealed"]), "encrypted where it is kept"
    assert await connection.ready(conn) == {
        "base_url": URL,
        "api_key": KEY,
        "api_key_header": "X-API-Key",
    }

    # Saved again without a key: the one that is there stays.
    await _on(conn, seeded, api_key=None, api_key_header="X-DV-Token")
    ready = await connection.ready(conn)
    assert ready is not None and ready["api_key"] == KEY
    assert ready["api_key_header"] == "X-DV-Token"
    # Removed on purpose.
    shown = await _on(conn, seeded, api_key=None, clear_api_key=True)
    assert shown["api_key_set"] is False
    # Switched off: the address stays, nothing is called.
    await _on(conn, seeded, enabled=False)
    assert await connection.ready(conn) is None

    trail = await (
        await conn.execute(
            """SELECT detail_json::text AS detail FROM audit_log
                WHERE event_type = 'datavault.connection_changed' AND log_id > %s
                ORDER BY log_id""",
            (start["n"],),
        )
    ).fetchall()
    assert len(trail) == 4
    assert all(URL not in t["detail"] and KEY not in t["detail"] for t in trail), (
        "the trail says that it changed, never the address or the key"
    )


@pytest.mark.parametrize(
    "bad",
    [
        {"base_url": "datavault.internal"},
        {"base_url": "https://u:p@datavault.internal"},
        {"base_url": None},
        {"api_key_header": "X Key"},
        {"api_key_header": "Host"},
        {"api_key": "line\nbreak"},
    ],
)
async def test_a_connection_that_could_not_be_called_is_refused(
    conn: Any, seeded: dict[str, Any], bad: dict[str, Any]
) -> None:
    with pytest.raises(ValidationFailed):
        await _on(conn, seeded, **bad)


# ------------------------------------------------------------------ the check
async def test_not_set_up_nothing_is_asked(conn: Any, seeded: dict[str, Any]) -> None:
    await _consent(conn, seeded)
    row = await _request(conn, seeded)
    with pytest.raises(Conflict) as refused:
        await checks.prepare(conn, row, role=DPO)
    assert refused.value.code == "datavault_not_configured"
    shown = await checks.overview(conn, row, role=DPO)
    assert shown["configured"] is False and shown["may_check"] is False
    assert shown["answer"] is None and shown["assets"] == []


async def test_the_office_checks_and_the_answer_is_matched_to_her_own_consents(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    consent = await _consent(conn, seeded)
    row = await _request(conn, seeded)
    project = seeded["project"]
    seen: list[httpx.Request] = []
    transport = _answering(
        [
            # By uuid, as the agreed sample has it.
            {
                "asset_id": "DV-IMG-000101",
                "consent_id": str(consent["consent_uuid"]),
                "project_id": str(project["project_uuid"]),
                "mid": 4909,
                "datapath": "/vault/img/000101",
            },
            # By number: the IDs the console shows.
            {
                "asset_id": "DV-VID-000102",
                "consent_id": int(consent["consent_id"]),
                "project_id": int(project["project_id"]),
                "mid": 4909,
                "datapath": "/vault/vid/000102",
            },
            # A consent that is nobody's here: kept as sent, matched to nothing.
            {
                "asset_id": "DV-AUD-000103",
                "consent_id": "00000000-0000-4000-8000-000000000000",
                "project_id": "999999999",
            },
        ],
        seen,
    )
    await _check(conn, row, transport, dpo)

    [request] = seen
    assert request.url.path == "/api/lookup"
    assert dict(request.url.params) == {
        "request_id": str(row["reference"]),
        "person_id": str(row["subject_user_id"]),
    }, "the request's reference and the numeric Person ID"
    assert request.headers["X-API-Key"] == KEY

    shown = await checks.overview(conn, row, role=DPO)
    assert shown["configured"] is True and shown["may_check"] is True
    assert shown["answer"]["outcome"] == "answered" and shown["answer"]["asset_count"] == 3
    assert shown["answer"]["automatic"] is False
    assert shown["last_failure"] is None
    first, second, third = shown["assets"]
    for mine in (first, second):
        assert str(mine["consent_uuid"]) == str(consent["consent_uuid"])
        assert str(mine["project_uuid"]) == str(project["project_uuid"])
        assert mine["consent_no"] == int(consent["consent_id"])
        assert mine["mid"] == "4909"
    assert first["datapath"] == "/vault/img/000101"
    assert third["consent_uuid"] is None and third["project_uuid"] is None
    assert third["consent_ref"] == "00000000-0000-4000-8000-000000000000"

    [trail] = await (
        await conn.execute(
            """SELECT detail_json AS detail, actor_user_id, subject_user_id FROM audit_log
                WHERE event_type = 'datavault.checked' AND entity_type = 'rights_request'
                  AND entity_id = %s""",
            (row["request_id"],),
        )
    ).fetchall()
    assert trail["actor_user_id"] == dpo
    assert trail["detail"]["reference"] == row["reference"]
    assert trail["detail"]["assets"] == 3 and trail["detail"]["unmatched"] == 1
    assert trail["detail"]["automatic"] is False
    assert "/vault" not in str(trail["detail"]) and "DV-IMG" not in str(trail["detail"])


async def test_another_person_s_consent_is_not_matched(conn: Any, seeded: dict[str, Any]) -> None:
    """DataVault names a consent that exists here but is somebody else's: the
    asset is kept as sent and linked to nothing of ours."""
    await _on(conn, seeded)
    mine = await _consent(conn, seeded)
    row = await _request(conn, seeded)
    other = await (
        await conn.execute(
            """SELECT consent_uuid::text AS u FROM consent_artefact
                WHERE auth_user_id <> %s LIMIT 1""",
            (row["subject_user_id"],),
        )
    ).fetchone()
    if other is None:
        pytest.skip("no other person's consent in this database")
    assert other["u"] != str(mine["consent_uuid"])
    await _check(
        conn,
        row,
        _answering([{"asset_id": "A", "consent_id": other["u"]}]),
        int(seeded["users"]["dpo"]["id"]),
    )
    [asset] = (await checks.overview(conn, row, role=DPO))["assets"]
    assert asset["consent_uuid"] is None and asset["consent_ref"] == other["u"]


async def test_her_consent_in_the_other_office_s_project_is_not_matched(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """A request is one office's, and what it links to is that office's too.
    The office is named in the matching itself: the platform's own check reads
    across both offices, where the row policy would let every consent through."""
    await _on(conn, seeded)
    consent = await _consent(conn, seeded)
    row = await _request(conn, seeded)
    assert row["office_id"] is not None
    other = await (
        await conn.execute(
            "SELECT office_id FROM office WHERE office_id <> %s ORDER BY office_id LIMIT 1",
            (row["office_id"],),
        )
    ).fetchone()
    assert other is not None, "two offices"

    here = await checks.prepare(conn, row, role=DPO)
    assert [c["consent_uuid"] for c in here.consents] == [str(consent["consent_uuid"])]
    # The same request, were it the other office's: her consent here is not
    # that office's to link, whoever reads.
    elsewhere = await checks.prepare(conn, {**row, "office_id": other["office_id"]}, role=DPO)
    assert elsewhere.consents == []
    # In the shared intake, with no office yet: within the reader's own.
    unclaimed = await checks.prepare(conn, {**row, "office_id": None}, role=DPO)
    assert [c["consent_uuid"] for c in unclaimed.consents] == [str(consent["consent_uuid"])]

    held = [dv_held(str(consent["consent_uuid"]))]
    await checks.store(conn, elsewhere, held, actor_id=None)
    [asset] = (await checks.overview(conn, row, role=DPO))["assets"]
    assert asset["consent_uuid"] is None and asset["project_uuid"] is None
    assert asset["consent_ref"] == str(consent["consent_uuid"]), "kept as sent, linked to nothing"


async def test_a_failed_check_is_kept_and_does_not_unsay_an_earlier_answer(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    await _consent(conn, seeded)
    row = await _request(conn, seeded)
    await _check(conn, row, _answering([{"asset_id": "A1"}]), dpo)
    await _check(conn, row, httpx.MockTransport(lambda _: httpx.Response(503, text="x")), dpo)

    shown = await checks.overview(conn, row, role=DPO)
    assert [a["asset_ref"] for a in shown["assets"]] == ["A1"]
    assert shown["answer"]["outcome"] == "answered"
    assert shown["last_failure"]["failure"] == "status_503"
    assert shown["last_failure"]["failure_said"] == "DataVault answered with an error (503)."

    # Answered again, with nothing: that is the answer now, and no failure stands.
    await _check(conn, row, _answering([]), dpo)
    shown = await checks.overview(conn, row, role=DPO)
    assert shown["assets"] == [] and shown["answer"]["asset_count"] == 0
    assert shown["last_failure"] is None


async def test_who_may_ask_and_about_what(conn: Any, seeded: dict[str, Any]) -> None:
    await _on(conn, seeded)
    await _consent(conn, seeded)
    row = await _request(conn, seeded)
    with pytest.raises(Forbidden):
        await checks.prepare(conn, row, role=Role.DCO)
    # No person behind the request: there is no Person ID to ask by.
    with pytest.raises(Conflict) as refused:
        await checks.prepare(conn, {**row, "subject_user_id": None}, role=DPO)
    assert refused.value.code == "datavault_not_askable"
    with pytest.raises(Conflict):
        await checks.prepare(conn, {**row, "status": "closed"}, role=DPO)
    shown = await checks.overview(conn, {**row, "status": "closed"}, role=DPO)
    assert shown["may_check"] is False and "closed" in shown["why_not"]


async def test_the_check_changes_nothing_else_on_the_request(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    await _only_dco_admin(conn, seeded)
    await _consent(conn, seeded)
    row = await _request(conn, seeded)
    holders = await service.derive_holders(conn, row, role=DPO, actor_id=dpo)
    before = await service.reload(conn, row)
    await _check(conn, row, _answering([{"asset_id": "A1"}, {"asset_id": "A2"}]), dpo)
    after = await service.reload(conn, row)
    assert {k: v for k, v in after.items() if k != "updated_at"} == {
        k: v for k, v in before.items() if k != "updated_at"
    }
    from cmp.db.repositories import rights as rights_repo

    assert [h["holder_uuid"] for h in await rights_repo.holders_of(conn, row["request_id"])] == [
        h["holder_uuid"] for h in holders
    ]


# ------------------------------------------------- by itself, and on the ticket
async def test_the_platform_asks_by_itself_when_a_dco_admin_is_among_the_holders(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    await _only_dco_admin(conn, seeded)
    await _consent(conn, seeded)
    row = await _request(conn, seeded)
    holders = await service.derive_holders(conn, row, role=DPO, actor_id=dpo)
    assert checks.names_a_dco_admin(holders)

    assert not await checks.wanted_automatically(conn, row, holders), "not set up: nothing asked"
    await _on(conn, seeded)
    assert await checks.wanted_automatically(conn, row, holders)
    assert not await checks.wanted_automatically(conn, row, []), "no DCO Admin among them"
    activity = [{**holders[0], "is_activity": True}]
    assert not await checks.wanted_automatically(conn, row, activity), "an HR owner is not one"

    await _check(conn, row, _answering([]), None)
    shown = await checks.overview(conn, row, role=DPO)
    assert shown["answer"]["automatic"] is True and shown["answer"]["asked_by_name"] is None
    assert not await checks.wanted_automatically(conn, row, holders), (
        "answered once: finding holders again does not ask again"
    )


async def test_a_dco_admin_sees_their_project_s_assets_on_their_ticket(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    dco_admin = await _only_dco_admin(conn, seeded)
    consent = await _consent(conn, seeded)
    row = await _request(conn, seeded)
    [holder] = await service.derive_holders(conn, row, role=DPO, actor_id=dpo)
    uuid = str(holder["holder_uuid"])
    assert await checks.for_ticket(conn, uuid, dco_admin) is None, "before DataVault answers"

    await _check(
        conn,
        row,
        _answering(
            [
                {"asset_id": "MINE", "consent_id": str(consent["consent_uuid"]), "datapath": "/p"},
                {"asset_id": "ELSEWHERE", "project_id": "not-a-project-here"},
            ]
        ),
        dpo,
    )
    shown = await checks.for_ticket(conn, uuid, dco_admin)
    assert shown is not None
    assert [a["asset_ref"] for a in shown["assets"]] == ["MINE"], (
        "the project they answer for, by the consent's project; nothing unmatched"
    )
    assert shown["assets"][0]["datapath"] == "/p"
    assert await checks.for_ticket(conn, uuid, dpo) is None, "addressed to nobody else"
