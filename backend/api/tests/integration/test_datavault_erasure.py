"""Erase in DataVault: the office's button on an erasure request (0071, 2026-11-13).

The assets the last check listed go to `POST {erasure address}/erasures` when
the DPO or the Legal PoC presses, on an erasure request that has been started,
with no legal hold on the person. Only what the request reaches goes: assets
matched to her records in the request's own office, and of a request about one
consent, that consent's. Each asset's answer is kept; "Check status" repeats
the same instruction; nothing runs by itself and nothing else about the
request changes. The trail keeps counts and codes, never an asset.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from cmp.core.errors import Conflict, Forbidden
from cmp.core.permissions import Role
from cmp.db.repositories import datavault as repo
from cmp.domain.datavault import checks, connection, erasures
from cmp.domain.rights import holds, service
from tests.integration.test_datavault_check import _answering, _check
from tests.integration.test_rights_by_office import _consent_with_legal_office
from tests.integration.test_rights_flows import (
    _consent,
    _portal_request,
    _second_notice_consent,
    _started,
)

pytestmark = pytest.mark.integration

DPO = Role.DPO
URL = "https://datavault.internal/api"
ERASE_URL = "https://datavault-erase.internal/api/v1"
KEY = "dv-key-0123456789"


# ------------------------------------------------------------------ the world
async def _on(conn: Any, seeded: dict[str, Any], **changes: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "base_url": URL,
        "erasure_url": ERASE_URL,
        "api_key": KEY,
        "clear_api_key": False,
        "api_key_header": None,
        "enabled": True,
        **changes,
    }
    return await connection.save(conn, actor_id=int(seeded["users"]["admin"]["id"]), **values)


async def _erasure(conn: Any, seeded: dict[str, Any], **kw: Any) -> dict[str, Any]:
    """An erasure request as the office has it once the work has started:
    identity verified, classified, and "she means erasure" confirmed."""
    dpo = seeded["users"]["dpo"]["id"]
    row = await _portal_request(conn, seeded, "erasure", **kw)
    row = await service.confirm_intent(conn, row, role=DPO, actor_id=dpo)
    return await _started(conn, seeded, row)


def _vault(
    seen: list[dict[str, Any]], words: dict[str, Any] | None = None, *, default: str = "pending"
) -> Any:
    """DataVault's side of `/erasures`: each asset answered as `words` says -
    a status, or a whole entry - and `default` for the rest."""

    def answer(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append({"_url": str(request.url), "_key": request.headers.get("X-API-Key"), **body})
        out = []
        for a in body["assets"]:
            word = (words or {}).get(a["asset_id"], default)
            said = word if isinstance(word, dict) else {"status": word}
            out.append({"asset_id": a["asset_id"], **said})
        return httpx.Response(200, json={"erasure_id": body["erasure_id"], "assets": out})

    return httpx.MockTransport(answer)


async def _press(
    conn: Any, row: dict[str, Any], transport: Any, *, actor: int, role: Role = DPO
) -> list[erasures.Send]:
    """A press of "Erase in DataVault", as the route does it."""
    sends = await erasures.start(conn, row, role=role, actor_id=actor)
    for send in sends:
        answer = await erasures.ask(send, transport=transport)
        await erasures.store(conn, send, answer, actor_id=actor)
    return sends


async def _status(
    conn: Any, row: dict[str, Any], transport: Any, *, actor: int, role: Role = DPO
) -> list[erasures.Send]:
    """A press of "Check status", as the route does it."""
    sends = await erasures.again(conn, row, role=role)
    for send in sends:
        answer = await erasures.ask(send, transport=transport)
        await erasures.store(conn, send, answer, actor_id=actor)
    return sends


async def _shown(conn: Any, row: dict[str, Any], role: Role = DPO) -> dict[str, Any]:
    return await checks.overview(conn, await service.reload(conn, row), role=role)


async def _trail(conn: Any, event: str, row: dict[str, Any]) -> list[dict[str, Any]]:
    rows = await (
        await conn.execute(
            """SELECT detail_json AS detail, detail_json::text AS said, actor_user_id,
                      subject_user_id
                 FROM audit_log
                WHERE event_type = %s AND entity_type = 'rights_request' AND entity_id = %s
                ORDER BY log_id""",
            (event, row["request_id"]),
        )
    ).fetchall()
    return [dict(r) for r in rows]


async def _consent_id_of(conn: Any, seeded: dict[str, Any]) -> int:
    """Her newest consent, by number: one an asset can be tagged with."""
    row = await (
        await conn.execute(
            "SELECT max(consent_id) AS n FROM consent_artefact WHERE auth_user_id = %s",
            (seeded["subject"]["id"],),
        )
    ).fetchone()
    return int(row["n"])


def _three(consent: dict[str, Any]) -> list[dict[str, Any]]:
    """What DataVault lists, all under her consent: named by number, by uuid,
    and by number again."""
    return [
        {"asset_id": "DV-IMG-000101", "consent_id": int(consent["consent_id"]), "mid": 4909},
        {"asset_id": "DV-VID-000102", "consent_id": str(consent["consent_uuid"])},
        {"asset_id": "DV-AUD-000103", "consent_id": int(consent["consent_id"])},
    ]


# ------------------------------------------------------- when it may be pressed
async def test_only_an_erasure_request_erases_anything(conn: Any, seeded: dict[str, Any]) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    consent = await _consent(conn, seeded)
    row = await _started(conn, seeded, await _portal_request(conn, seeded, "access"))
    await _check(conn, row, _answering(_three(consent)), dpo)
    shown = await _shown(conn, row)
    assert shown["erasure"] is None, "an access request has nothing to erase"
    assert all(a["erasure_status"] is None and a["in_scope"] is True for a in shown["assets"])
    with pytest.raises(Conflict) as refused:
        await erasures.start(conn, row, role=DPO, actor_id=dpo)
    assert refused.value.code == "datavault_not_an_erasure"
    with pytest.raises(Conflict):
        await erasures.again(conn, row, role=DPO)


async def test_it_waits_for_the_request_to_start_the_address_and_a_check(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded, erasure_url=None)
    consent = await _consent(conn, seeded)

    # Received, verified - and not started: she has not been asked what she means.
    row = await _portal_request(conn, seeded, "erasure")
    shown = await _shown(conn, row)
    assert shown["erasure"]["may_erase"] is False
    assert shown["erasure"]["why_not"].startswith("Start the request first")
    with pytest.raises(Conflict) as refused:
        await erasures.start(conn, row, role=DPO, actor_id=dpo)
    assert refused.value.code == "datavault_erasure_not_now"

    row = await service.confirm_intent(conn, row, role=DPO, actor_id=dpo)
    row = await _started(conn, seeded, row)
    shown = await _shown(conn, row)
    assert "erasure address is not set" in shown["erasure"]["why_not"]

    await _on(conn, seeded)
    shown = await _shown(conn, row)
    assert shown["erasure"]["why_not"].startswith("Check in DataVault first")
    assert shown["erasure"]["may_erase"] is False and shown["erasure"]["to_send"] == 0

    await _check(conn, row, _answering(_three(consent)), dpo)
    shown = await _shown(conn, row)
    assert shown["erasure"]["may_erase"] is True and shown["erasure"]["why_not"] is None
    assert (shown["erasure"]["to_send"], shown["erasure"]["left_out"]) == (3, 0)
    assert shown["erasure"]["may_check_status"] is False and shown["erasure"]["open"] == 0


async def test_a_check_that_listed_nothing_leaves_nothing_to_send(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    await _consent(conn, seeded)
    row = await _erasure(conn, seeded)
    await _check(conn, row, _answering([]), dpo)
    shown = await _shown(conn, row)
    assert shown["erasure"]["may_erase"] is False
    assert shown["erasure"]["why_not"] == "DataVault lists nothing this request reaches."
    with pytest.raises(Conflict) as refused:
        await erasures.start(conn, row, role=DPO, actor_id=dpo)
    assert refused.value.code == "datavault_nothing_to_erase"


async def test_who_may_press(conn: Any, seeded: dict[str, Any]) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    consent = await _consent(conn, seeded)
    row = await _erasure(conn, seeded)
    # Before a check the office is told why it cannot press yet; a reader who
    # may not act on the request is told nothing of the kind.
    assert (await _shown(conn, row))["erasure"]["why_not"].startswith("Check in DataVault")
    for role in (Role.DCO, Role.DCO_ADMIN, Role.ADMIN):
        assert (await _shown(conn, row, role))["erasure"]["why_not"] is None
    await _check(conn, row, _answering(_three(consent)), dpo)
    for role in (Role.DCO, Role.DCO_ADMIN, Role.ADMIN):
        with pytest.raises(Forbidden):
            await erasures.start(conn, row, role=role, actor_id=dpo)
        with pytest.raises(Forbidden):
            await erasures.again(conn, row, role=role)
        shown = await _shown(conn, row, role)
        assert shown["erasure"]["may_erase"] is False
        assert shown["erasure"]["may_check_status"] is False
        assert shown["erasure"]["why_not"] is None, "offered nothing, not even a reason"
    assert await repo.erasures_of(conn, int(row["request_id"])) == [], "nothing was written"


async def test_a_legal_hold_on_the_person_stops_it(conn: Any, seeded: dict[str, Any]) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    consent = await _consent(conn, seeded)
    row = await _erasure(conn, seeded)
    await _check(conn, row, _answering(_three(consent)), dpo)
    hold = await holds.place(
        conn,
        asset_uuid=None,
        subject_uuid=str(seeded["subject"]["uuid"]),
        reason="Evidence in a live matter",
        actor_id=dpo,
    )
    shown = await _shown(conn, row)
    assert shown["erasure"]["may_erase"] is False
    assert shown["erasure"]["why_not"].startswith("A legal hold stands on this person")
    seen: list[dict[str, Any]] = []
    with pytest.raises(Conflict) as refused:
        await _press(conn, row, _vault(seen), actor=dpo)
    assert refused.value.code == "datavault_erasure_not_now"
    assert seen == [] and await repo.erasures_of(conn, int(row["request_id"])) == []

    await holds.release(conn, hold_uuid=str(hold["hold_uuid"]), actor_id=dpo)
    assert (await _shown(conn, row))["erasure"]["may_erase"] is True
    await _press(conn, row, _vault(seen), actor=dpo)
    assert len(seen) == 1


async def test_a_hold_placed_after_the_press_withholds_what_had_not_gone(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """Review ARCH-8: the press commits its instructions, then sends them with
    no transaction open. A hold placed in between - before the last look each
    instruction gets - keeps it from DataVault; released, it goes from "Check
    status"; an instruction DataVault has already answered may always be asked
    about again."""
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    consent = await _consent(conn, seeded)
    row = await _erasure(conn, seeded)
    await _check(conn, row, _answering(_three(consent)), dpo)
    [ready] = await erasures.start(conn, row, role=DPO, actor_id=dpo)
    assert await erasures.gate(conn, ready) is None, "nothing stands in its way yet"

    hold = await holds.place(
        conn,
        asset_uuid=None,
        subject_uuid=str(seeded["subject"]["uuid"]),
        reason="Evidence in a live matter",
        actor_id=dpo,
    )
    assert await erasures.gate(conn, ready) == "a legal hold now stands on the person"

    await holds.release(conn, hold_uuid=str(hold["hold_uuid"]), actor_id=dpo)
    [again] = await erasures.again(conn, row, role=DPO)
    assert await erasures.gate(conn, again) is None
    seen: list[dict[str, Any]] = []
    await erasures.store(
        conn, again, await erasures.ask(again, transport=_vault(seen)), actor_id=dpo
    )
    assert len(seen) == 1, "sent once, when nothing stood in its way"

    await holds.place(
        conn,
        asset_uuid=None,
        subject_uuid=str(seeded["subject"]["uuid"]),
        reason="A second matter",
        actor_id=dpo,
    )
    [asked] = await erasures.again(conn, row, role=DPO)
    assert asked.answered and await erasures.gate(conn, asked) is None, (
        "DataVault has it: asking how far it has got starts nothing"
    )


# ------------------------------------------------------------ what is sent
async def test_the_assets_go_as_the_check_listed_them_and_each_answer_is_kept(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    consent = await _consent(conn, seeded)
    row = await _erasure(conn, seeded)
    await _check(conn, row, _answering(_three(consent)), dpo)

    seen: list[dict[str, Any]] = []
    vault = _vault(
        seen,
        {
            "DV-IMG-000101": {"status": "erased", "completed_at": "2026-11-13T09:30:12Z"},
            "DV-AUD-000103": {"status": "failed", "reason": "Held under a retention order"},
        },
    )
    [send] = await _press(conn, row, vault, actor=dpo)
    [sent] = seen
    assert sent.pop("_url") == ERASE_URL + "/erasures"
    assert sent.pop("_key") == KEY
    assert sent == {
        "erasure_id": send.erasure_uuid,
        # By number, as the administrator's switch starts: the request by its
        # reference, the person by her Person ID.
        "request_id": row["reference"],
        "person_id": int(row["subject_user_id"]),
        "assets": [
            # Each with the consent DataVault gave for it, as it gave it.
            {"asset_id": "DV-IMG-000101", "consent_id": int(consent["consent_id"])},
            {"asset_id": "DV-VID-000102", "consent_id": str(consent["consent_uuid"])},
            {"asset_id": "DV-AUD-000103", "consent_id": int(consent["consent_id"])},
        ],
    }
    assert type(sent["person_id"]) is int and type(sent["assets"][0]["consent_id"]) is int

    shown = await _shown(conn, row)
    by_ref = {a["asset_ref"]: a for a in shown["assets"]}
    assert by_ref["DV-IMG-000101"]["erasure_status"] == "erased"
    assert (
        by_ref["DV-IMG-000101"]["erasure_completed_at"]
        .isoformat()
        .startswith("2026-11-13T09:30:12")
    )
    assert by_ref["DV-VID-000102"]["erasure_status"] == "pending"
    assert by_ref["DV-AUD-000103"]["erasure_status"] == "failed"
    assert by_ref["DV-AUD-000103"]["erasure_reason"] == "Held under a retention order"
    assert all(a["erasure_status_at"] is not None and a["in_scope"] for a in shown["assets"])
    state = shown["erasure"]
    assert state["counts"] == {
        "unanswered": 0,
        "pending": 1,
        "erased": 1,
        "failed": 1,
        "not_held": 0,
    }
    assert (state["open"], state["may_check_status"]) == (1, True)
    assert (state["to_send"], state["may_erase"]) == (1, True), "what failed may be sent again"
    assert state["last_failure"] is None and state["last_asked_at"] is not None

    # The trail: that it went, and what came back, as counts.
    [went] = await _trail(conn, "datavault.erasure_sent", row)
    assert went["actor_user_id"] == dpo and went["subject_user_id"] == row["subject_user_id"]
    assert went["detail"]["reference"] == row["reference"]
    assert (went["detail"]["assets"], went["detail"]["instructions"]) == (3, 1)
    assert (went["detail"]["left_out"], went["detail"]["confined_to_consent"]) == (0, False)
    [came] = await _trail(conn, "datavault.erasure_checked", row)
    assert came["detail"]["outcome"] == "answered" and came["detail"]["again"] is False
    assert (came["detail"]["erased"], came["detail"]["pending"]) == (1, 1)
    assert (came["detail"]["failed"], came["detail"]["not_held"]) == (1, 0)
    for entry in (went, came):
        assert "DV-" not in entry["said"] and "retention order" not in entry["said"], (
            "never an asset or DataVault's reason"
        )

    # Nothing else about the request has moved.
    after = await service.reload(conn, row)
    assert after["status"] == row["status"]
    assert int(after["holders_confirmed"] or 0) == int(row["holders_confirmed"] or 0)


async def test_named_by_uuid_when_the_administrator_switches(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded, id_format="uuid")
    consent = await _consent(conn, seeded)
    row = await _erasure(conn, seeded)
    asked: list[httpx.Request] = []
    await _check(conn, row, _answering(_three(consent), asked), dpo)
    assert dict(asked[0].url.params) == {
        "request_id": str(row["request_uuid"]),
        "person_id": str(row["subject_uuid"]),
    }, "the lookup follows the same switch"

    seen: list[dict[str, Any]] = []
    await _press(conn, row, _vault(seen), actor=dpo)
    assert seen[0]["request_id"] == str(row["request_uuid"])
    assert seen[0]["person_id"] == str(row["subject_uuid"])
    # The consent goes back as DataVault gave it, whatever the switch says.
    assert seen[0]["assets"][0]["consent_id"] == int(consent["consent_id"])


async def test_a_request_about_one_consent_sends_only_that_consent_s_assets(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    first = await _consent(conn, seeded)
    other = await _second_notice_consent(conn, seeded)
    # She withdraws the first: the chain has two consents, and an asset may
    # carry either.
    from cmp.domain.consent import service as consent_service

    await consent_service.withdraw(
        conn,
        consent_uuid=str(first["consent_uuid"]),
        user_id=seeded["subject"]["id"],
        purpose_uuids=None,
        withdraw_all=True,
        ip_address="203.0.113.7",
    )
    later = await (
        await conn.execute(
            """SELECT consent_id FROM consent_artefact
                WHERE supersedes_consent_id = %s""",
            (first["consent_id"],),
        )
    ).fetchone()
    row = await _erasure(conn, seeded, consent_id=first["consent_id"])
    await _check(
        conn,
        row,
        _answering(
            [
                {"asset_id": "UNDER-IT", "consent_id": int(first["consent_id"])},
                {"asset_id": "UNDER-ITS-WITHDRAWAL", "consent_id": int(later["consent_id"])},
                {"asset_id": "UNDER-ANOTHER", "consent_id": int(other["consent_id"])},
                {"asset_id": "UNDER-NOBODY-S", "consent_id": "999999999"},
                {"asset_id": "UNDER-NONE"},
            ]
        ),
        dpo,
    )
    shown = await _shown(conn, row)
    assert {a["asset_ref"]: a["in_scope"] for a in shown["assets"]} == {
        "UNDER-IT": True,
        "UNDER-ITS-WITHDRAWAL": True,
        "UNDER-ANOTHER": False,
        "UNDER-NOBODY-S": False,
        "UNDER-NONE": False,
    }
    assert (shown["erasure"]["to_send"], shown["erasure"]["left_out"]) == (2, 3)

    seen: list[dict[str, Any]] = []
    await _press(conn, row, _vault(seen, default="erased"), actor=dpo)
    assert [a["asset_id"] for a in seen[0]["assets"]] == ["UNDER-IT", "UNDER-ITS-WITHDRAWAL"]
    shown = await _shown(conn, row)
    left = {a["asset_ref"]: a["erasure_status"] for a in shown["assets"] if not a["in_scope"]}
    assert set(left.values()) == {None}, "left out, and shown as not sent"
    assert (
        shown["erasure"]["why_not"] == "Everything this request reaches has been sent to DataVault."
    )
    [went] = await _trail(conn, "datavault.erasure_sent", row)
    assert (went["detail"]["assets"], went["detail"]["left_out"]) == (2, 3)
    assert went["detail"]["confined_to_consent"] is True


async def test_more_than_the_contract_s_limit_goes_as_several_instructions(
    conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    # The name the erasure module reads: the package's.
    monkeypatch.setattr(erasures.client, "MAX_ERASURE_ASSETS", 2)
    await _on(conn, seeded)
    await _consent(conn, seeded)
    row = await _erasure(conn, seeded)
    mine = await _consent_id_of(conn, seeded)
    await _check(
        conn, row, _answering([{"asset_id": f"A{i}", "consent_id": mine} for i in range(5)]), dpo
    )
    seen: list[dict[str, Any]] = []
    sends = await _press(conn, row, _vault(seen, default="erased"), actor=dpo)
    assert [len(s["assets"]) for s in seen] == [2, 2, 1]
    assert len({s["erasure_id"] for s in seen}) == 3 and len(sends) == 3
    assert [a["asset_id"] for s in seen for a in s["assets"]] == [f"A{i}" for i in range(5)]
    [went] = await _trail(conn, "datavault.erasure_sent", row)
    assert (went["detail"]["assets"], went["detail"]["instructions"]) == (5, 3)
    assert (await _shown(conn, row))["erasure"]["counts"]["erased"] == 5


# ------------------------------------------------------------- asking again
async def test_check_status_repeats_the_same_instruction(conn: Any, seeded: dict[str, Any]) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    consent = await _consent(conn, seeded)
    row = await _erasure(conn, seeded)
    await _check(conn, row, _answering(_three(consent)), dpo)
    seen: list[dict[str, Any]] = []
    await _press(conn, row, _vault(seen, {"DV-IMG-000101": "erased"}), actor=dpo)

    # DataVault has finished one more, and now says something else of the
    # one it had already erased: a final word stands.
    [again] = await _status(
        conn,
        row,
        _vault(seen, {"DV-IMG-000101": "pending", "DV-VID-000102": "not_held"}),
        actor=dpo,
    )
    first, second = seen
    assert again.again is True
    assert second["erasure_id"] == first["erasure_id"], "the same instruction: nothing new starts"
    assert second["assets"] == first["assets"], "and the same assets, in the same order"
    assert (second["request_id"], second["person_id"]) == (first["request_id"], first["person_id"])

    shown = await _shown(conn, row)
    by_ref = {a["asset_ref"]: a["erasure_status"] for a in shown["assets"]}
    assert by_ref == {
        "DV-IMG-000101": "erased",
        "DV-VID-000102": "not_held",
        "DV-AUD-000103": "pending",
    }
    [instruction] = await repo.erasures_of(conn, int(row["request_id"]))
    assert instruction["asks"] == 2 and instruction["open_assets"] == 1
    _, came = await _trail(conn, "datavault.erasure_checked", row)
    assert came["detail"]["again"] is True
    assert (came["detail"]["not_held"], came["detail"]["pending"]) == (1, 2)

    await _status(conn, row, _vault(seen, default="erased"), actor=dpo)
    shown = await _shown(conn, row)
    assert shown["erasure"]["open"] == 0 and shown["erasure"]["may_check_status"] is False
    with pytest.raises(Conflict) as refused:
        await erasures.again(conn, row, role=DPO)
    assert refused.value.code == "datavault_nothing_pending"


async def test_what_is_erased_pending_or_not_held_is_not_sent_again_and_what_failed_is(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    consent = await _consent(conn, seeded)
    row = await _erasure(conn, seeded)
    await _check(conn, row, _answering(_three(consent)), dpo)
    seen: list[dict[str, Any]] = []
    words = {
        "DV-IMG-000101": "erased",
        "DV-AUD-000103": {"status": "failed", "reason": "Storage offline"},
    }
    await _press(conn, row, _vault(seen, words), actor=dpo)

    await _press(conn, row, _vault(seen, default="erased"), actor=dpo)
    first, second = seen
    assert second["erasure_id"] != first["erasure_id"], "a new instruction"
    assert second["assets"] == [
        {"asset_id": "DV-AUD-000103", "consent_id": int(consent["consent_id"])}
    ], "only what failed"
    shown = await _shown(conn, row)
    by_ref = {a["asset_ref"]: a for a in shown["assets"]}
    assert by_ref["DV-AUD-000103"]["erasure_status"] == "erased", "the newest instruction's word"
    assert by_ref["DV-AUD-000103"]["erasure_reason"] is None
    assert shown["erasure"]["counts"] == {
        "unanswered": 0,
        "pending": 1,
        "erased": 2,
        "failed": 0,
        "not_held": 0,
    }

    # Nothing is left that a press would send.
    assert shown["erasure"]["may_erase"] is False and shown["erasure"]["to_send"] == 0
    with pytest.raises(Conflict) as refused:
        await erasures.start(conn, row, role=DPO, actor_id=dpo)
    assert refused.value.code == "datavault_nothing_to_erase"
    assert len(seen) == 2


async def test_a_fresh_check_that_lists_a_new_asset_leaves_it_to_be_sent(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    consent = await _consent(conn, seeded)
    row = await _erasure(conn, seeded)
    await _check(conn, row, _answering(_three(consent)), dpo)
    seen: list[dict[str, Any]] = []
    await _press(conn, row, _vault(seen, default="erased"), actor=dpo)
    # A lab delivered one more since; DataVault no longer lists what it erased.
    new = {"asset_id": "DV-NEW-000200", "consent_id": int(consent["consent_id"])}
    await _check(conn, row, _answering([new]), dpo)
    shown = await _shown(conn, row)
    assert [a["asset_ref"] for a in shown["assets"]] == ["DV-NEW-000200"]
    assert shown["erasure"]["counts"]["erased"] == 3, "what was erased still counts"
    assert (shown["erasure"]["to_send"], shown["erasure"]["may_erase"]) == (1, True)
    await _press(conn, row, _vault(seen, default="pending"), actor=dpo)
    assert seen[1]["assets"] == [new]


async def test_an_ask_that_is_not_answered_is_kept_and_asked_again(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    consent = await _consent(conn, seeded)
    row = await _erasure(conn, seeded)
    await _check(conn, row, _answering(_three(consent)), dpo)

    def slow(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    [send] = await _press(conn, row, httpx.MockTransport(slow), actor=dpo)
    shown = await _shown(conn, row)
    state = shown["erasure"]
    assert state["counts"]["unanswered"] == 3 and state["open"] == 3
    assert state["last_failure"] == "timeout"
    assert state["last_failure_said"] == "DataVault did not answer in time."
    assert state["may_check_status"] is True
    assert state["may_erase"] is False, "it is on record as sent: asked again, not sent anew"
    assert all(a["erasure_status"] == "unanswered" for a in shown["assets"])
    [came] = await _trail(conn, "datavault.erasure_checked", row)
    assert (came["detail"]["outcome"], came["detail"]["failure"]) == ("failed", "timeout")

    seen: list[dict[str, Any]] = []
    await _status(conn, row, _vault(seen, default="erased"), actor=dpo)
    assert seen[0]["erasure_id"] == send.erasure_uuid
    state = (await _shown(conn, row))["erasure"]
    assert state["counts"]["erased"] == 3 and state["last_failure"] is None


async def test_an_instruction_datavault_refuses_is_released_and_sent_again_anew(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """DataVault refuses the numbers outright: it has not taken the
    instruction. Its assets are marked not erased, with why, nothing waits on
    it, and once the administrator switches to uuids a press sends them again
    under a new erasure_id."""
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    consent = await _consent(conn, seeded)
    row = await _erasure(conn, seeded)
    await _check(conn, row, _answering(_three(consent)), dpo)

    refused: list[dict[str, Any]] = []

    def no(request: httpx.Request) -> httpx.Response:
        refused.append(json.loads(request.content))
        return httpx.Response(400, json={"error": "invalid_request"})

    [send] = await _press(conn, row, httpx.MockTransport(no), actor=dpo)
    assert refused[0]["person_id"] == int(row["subject_user_id"])
    shown = await _shown(conn, row)
    state = shown["erasure"]
    assert state["last_failure"] == "status_400"
    assert state["last_failure_said"] == "DataVault refused the instruction as badly formed."
    assert state["counts"]["failed"] == 3 and state["open"] == 0
    assert state["may_check_status"] is False, "nothing waits on it"
    assert (state["may_erase"], state["to_send"]) == (True, 3)
    assert {a["erasure_reason"] for a in shown["assets"]} == {
        "Not taken: DataVault refused the instruction as badly formed."
    }
    [came] = await _trail(conn, "datavault.erasure_checked", row)
    assert (came["detail"]["failure"], came["detail"]["released"]) == ("status_400", 3)

    await _on(conn, seeded, id_format="uuid", api_key=None)
    seen: list[dict[str, Any]] = []
    [anew] = await _press(conn, row, _vault(seen), actor=dpo)
    assert anew.erasure_uuid != send.erasure_uuid
    assert seen[0]["erasure_id"] == anew.erasure_uuid
    assert seen[0]["person_id"] == str(row["subject_uuid"])
    assert seen[0]["assets"] == refused[0]["assets"]


async def test_an_instruction_never_answered_is_named_as_the_switch_says_until_it_is(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """The first ask times out: DataVault may or may not have it. Check status
    sends the same instruction, named as the switch says then; once DataVault
    has answered it, a repeat names it the same whatever the switch says."""
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    consent = await _consent(conn, seeded)
    row = await _erasure(conn, seeded)
    await _check(conn, row, _answering(_three(consent)), dpo)

    def slow(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    [send] = await _press(conn, row, httpx.MockTransport(slow), actor=dpo)
    await _on(conn, seeded, id_format="uuid", api_key=None)
    seen: list[dict[str, Any]] = []
    await _status(conn, row, _vault(seen), actor=dpo)
    assert seen[0]["erasure_id"] == send.erasure_uuid, "the same instruction"
    assert seen[0]["person_id"] == str(row["subject_uuid"])
    assert seen[0]["request_id"] == str(row["request_uuid"])

    # Taken now. Whatever the switch says later, a repeat says the same.
    await _on(conn, seeded, id_format="numeric", api_key=None)
    await _status(conn, row, _vault(seen, default="erased"), actor=dpo)
    assert seen[1]["person_id"] == str(row["subject_uuid"])
    assert seen[1]["request_id"] == str(row["request_uuid"])


async def test_an_answer_about_an_asset_that_was_not_asked_about_is_not_kept(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    await _consent(conn, seeded)
    row = await _erasure(conn, seeded)
    mine = await _consent_id_of(conn, seeded)
    await _check(conn, row, _answering([{"asset_id": "MINE", "consent_id": mine}]), dpo)

    def answer(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "erasure_id": body["erasure_id"],
                "assets": [
                    {"asset_id": "SOMEBODY-ELSE-S", "status": "erased"},
                    {"asset_id": "MINE", "status": "pending"},
                ],
            },
        )

    await _press(conn, row, httpx.MockTransport(answer), actor=dpo)
    shown = await _shown(conn, row)
    assert [(a["asset_ref"], a["erasure_status"]) for a in shown["assets"]] == [("MINE", "pending")]
    [came] = await _trail(conn, "datavault.erasure_checked", row)
    assert (came["detail"]["erased"], came["detail"]["pending"]) == (0, 1)


async def test_status_can_still_be_checked_after_the_request_is_closed(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """Closing does not wait for DataVault; what was pending then can still be
    followed to its end. Nothing new is sent on a closed request."""
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    consent = await _consent(conn, seeded)
    row = await _erasure(conn, seeded)
    await _check(conn, row, _answering(_three(consent)), dpo)
    seen: list[dict[str, Any]] = []
    await _press(
        conn, row, _vault(seen, {"DV-AUD-000103": {"status": "failed", "reason": "x"}}), actor=dpo
    )
    await conn.execute(
        """UPDATE rights_request SET status = 'closed', closed_at = now(), outcome = 'complete'
            WHERE request_id = %s""",
        (row["request_id"],),
    )
    row = await service.reload(conn, row)
    state = (await _shown(conn, row))["erasure"]
    assert state["may_erase"] is False and state["why_not"] == f"{row['reference']} is closed."
    assert state["may_check_status"] is True and state["open"] == 2
    with pytest.raises(Conflict) as refused:
        await erasures.start(conn, row, role=DPO, actor_id=dpo)
    assert refused.value.code == "datavault_erasure_not_now"

    await _status(conn, row, _vault(seen, default="erased"), actor=dpo)
    assert seen[1]["erasure_id"] == seen[0]["erasure_id"]
    state = (await _shown(conn, row))["erasure"]
    assert state["counts"]["erased"] == 2 and state["open"] == 0


# ------------------------------------------------------------ how a consent goes back
@pytest.mark.parametrize(
    ("ref", "was_number", "goes"),
    [
        ("311", True, 311),
        ("311", False, "311"),
        ("9b2f4c1d-6e3a-4b7f-8d1c-2e5a9f0b3c71", False, "9b2f4c1d-6e3a-4b7f-8d1c-2e5a9f0b3c71"),
        (None, None, None),
        # A check from before the type was kept: by what the text looks like.
        ("311", None, 311),
        ("007", None, "007"),
        ("c-311", None, "c-311"),
        ("٣١١", None, "٣١١"),
    ],
)
def test_a_consent_goes_back_as_datavault_gave_it(
    ref: str | None, was_number: bool | None, goes: object
) -> None:
    sent = erasures._echo({"consent_ref": ref, "consent_ref_is_number": was_number})
    assert sent == goes and type(sent) is type(goes)


# ------------------------------------------------------------ what it reaches
async def test_a_request_reaches_only_its_own_office_s_assets(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """A request is one office's, and so is what it erases (the review of
    2026-11-13): an asset under her consent in the other office, one whose
    consent and project match nothing of hers, and one DataVault gave no
    consent for are all left out. One whose project is hers here goes,
    though DataVault's consent for it is not one the platform knows."""
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    mine = await _consent(conn, seeded)
    elsewhere = await _consent_with_legal_office(conn, seeded, int(seeded["subject"]["id"]))
    row = await _erasure(conn, seeded)
    project = int(seeded["project"]["project_id"])
    await _check(
        conn,
        row,
        _answering(
            [
                {"asset_id": "HERE", "consent_id": int(mine["consent_id"])},
                {"asset_id": "OTHER-OFFICE", "consent_id": elsewhere},
                {"asset_id": "NOBODY-S", "consent_id": "C-UNKNOWN", "project_id": "P-UNKNOWN"},
                {"asset_id": "HER-PROJECT", "consent_id": "C-UNKNOWN", "project_id": project},
                {"asset_id": "NO-CONSENT", "project_id": project},
            ]
        ),
        dpo,
    )
    shown = await _shown(conn, row)
    assert {a["asset_ref"]: a["in_scope"] for a in shown["assets"]} == {
        "HERE": True,
        "OTHER-OFFICE": False,
        "NOBODY-S": False,
        "HER-PROJECT": True,
        "NO-CONSENT": False,
    }
    assert (shown["erasure"]["to_send"], shown["erasure"]["left_out"]) == (2, 3)
    seen: list[dict[str, Any]] = []
    await _press(conn, row, _vault(seen, default="erased"), actor=dpo)
    assert [a["asset_id"] for a in seen[0]["assets"]] == ["HERE", "HER-PROJECT"]
    assert seen[0]["assets"][1] == {"asset_id": "HER-PROJECT", "consent_id": "C-UNKNOWN"}


async def test_an_asset_listed_twice_is_sent_once(conn: Any, seeded: dict[str, Any]) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    consent = await _consent(conn, seeded)
    row = await _erasure(conn, seeded)
    twice = {"asset_id": "SAME", "consent_id": int(consent["consent_id"])}
    await _check(conn, row, _answering([twice, dict(twice)]), dpo)
    state = (await _shown(conn, row))["erasure"]
    assert (state["may_erase"], state["to_send"], state["left_out"]) == (True, 1, 0)
    seen: list[dict[str, Any]] = []
    await _press(conn, row, _vault(seen, default="erased"), actor=dpo)
    assert seen[0]["assets"] == [twice]


async def test_check_status_sends_nothing_new_past_a_legal_hold(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """The first ask never reached DataVault; then a hold is placed on the
    person. Sending that instruction now would start the erasure the hold
    stops, so Check status does not. One DataVault has answered may still be
    asked about: that only asks."""
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    consent = await _consent(conn, seeded)
    row = await _erasure(conn, seeded)
    await _check(conn, row, _answering(_three(consent)), dpo)

    def down(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    await _press(conn, row, httpx.MockTransport(down), actor=dpo)
    hold = await holds.place(
        conn,
        asset_uuid=None,
        subject_uuid=str(seeded["subject"]["uuid"]),
        reason="Evidence in a live matter",
        actor_id=dpo,
    )
    state = (await _shown(conn, row))["erasure"]
    assert state["open"] == 3 and state["may_check_status"] is False
    assert state["why_not"].startswith("A legal hold stands on this person")
    seen: list[dict[str, Any]] = []
    with pytest.raises(Conflict) as refused:
        await _status(conn, row, _vault(seen), actor=dpo)
    assert refused.value.code == "datavault_erasure_not_now" and seen == []

    # Released, it goes; DataVault answers it; a new hold then lets it be
    # asked about, since that starts nothing.
    await holds.release(conn, hold_uuid=str(hold["hold_uuid"]), actor_id=dpo)
    await _status(conn, row, _vault(seen), actor=dpo)
    await holds.place(
        conn,
        asset_uuid=None,
        subject_uuid=str(seeded["subject"]["uuid"]),
        reason="Another matter",
        actor_id=dpo,
    )
    assert (await _shown(conn, row))["erasure"]["may_check_status"] is True
    await _status(conn, row, _vault(seen, default="erased"), actor=dpo)
    assert len(seen) == 2 and seen[1]["erasure_id"] == seen[0]["erasure_id"]


async def test_presses_on_one_request_are_taken_one_at_a_time(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """A press holds the request's own lock to the end of its transaction, so
    a second press at the same moment waits and then finds the assets sent."""
    dpo = int(seeded["users"]["dpo"]["id"])
    await _on(conn, seeded)
    consent = await _consent(conn, seeded)
    row = await _erasure(conn, seeded)
    await _check(conn, row, _answering(_three(consent)), dpo)
    held = """SELECT count(*) AS n FROM pg_locks
               WHERE locktype = 'advisory' AND objsubid = 1 AND pid = pg_backend_pid()"""
    before = (await (await conn.execute(held)).fetchone())["n"]
    await erasures.start(conn, row, role=DPO, actor_id=dpo)
    after = (await (await conn.execute(held)).fetchone())["n"]
    assert after == before + 1, "one 64-bit advisory lock, held to the end of the transaction"
    with pytest.raises(Conflict) as again:
        await erasures.start(conn, row, role=DPO, actor_id=dpo)
    assert again.value.code == "datavault_nothing_to_erase"
