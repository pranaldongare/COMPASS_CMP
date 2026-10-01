"""Telling the people a breach touched (S3-03).

Nothing is sent before approval, and approval needs all five contents. A send
writes the notice to every listed person's account and queues her email and
SMS; a resend adds nothing; an updated version reaches everyone again. The
principals' duty completes when every channel has an outcome, and reopens
for people listed after that.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
import pytest

from cmp.core.errors import Conflict, ValidationFailed
from cmp.db.repositories import audit as audit_repo
from cmp.domain.breach import affected, notices, service
from cmp.tasks import dispatch as dispatch_mod
from tests.conftest import plain
from tests.integration.test_breach_affected import _breach, _person

pytestmark = pytest.mark.integration

WORDS = {
    "what_happened": "On 28 September a copy of a contact list went to the wrong address.",
    "consequences": "Someone outside the lab may have seen your name and mobile number.",
    "measures": "The recipient confirmed deletion; the list now travels encrypted.",
    "protective_steps": "Be wary of calls that mention the study and ask for anything.",
    "contact": "The Privacy Office, privacy@example.org",
}


@pytest.fixture
def queued(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, tuple[Any, ...]]]:
    sent: list[tuple[str, tuple[Any, ...]]] = []

    def capture(task: Any, *args: Any, **kwargs: Any) -> str:
        sent.append((task.name, args))
        return "queued-in-a-test"

    monkeypatch.setattr(dispatch_mod, "dispatch_optional", capture)
    return sent


def _sends(queued: list[tuple[str, tuple[Any, ...]]]) -> list[tuple[str, tuple[Any, ...]]]:
    """Breach notices only: a consent captured on the way queues its receipt."""
    return [q for q in queued if q[0] == "cmp.notifications.send_breach_notice"]


async def _determined(conn: Any, seeded: dict[str, Any], people: list[str]) -> str:
    """A breach determined yes, with these people listed as touched."""
    uuid = await _breach(conn, seeded)
    dpo = int(seeded["users"]["dpo"]["id"])
    await service.determine(
        conn,
        breach_uuid=uuid,
        outcome="yes",
        reasoning="Contacts left the building",
        became_aware_at=datetime.now(UTC) - timedelta(hours=1),
        actor_id=dpo,
    )
    await affected.confirm(
        conn, breach_uuid=uuid, scopes=[], exclude=[], add=people, note=None, actor_id=dpo
    )
    return uuid


async def _approved(conn: Any, seeded: dict[str, Any], uuid: str, **words: str) -> dict[str, Any]:
    dpo = int(seeded["users"]["dpo"]["id"])
    view = await notices.draft(conn, breach_uuid=uuid, words={**WORDS, **words}, actor_id=dpo)
    draft = view["versions"][-1]
    return await notices.approve(
        conn, breach_uuid=uuid, notice_uuid=str(draft["notice_uuid"]), actor_id=dpo
    )


async def _deliveries(conn: Any, uuid: str) -> list[dict[str, Any]]:
    return list(
        await (
            await conn.execute(
                """SELECT d.delivery_uuid, d.auth_user_id, d.channel, d.attempt, d.status,
                          n.version
                     FROM breach_notice_delivery d
                     JOIN breach_notice n ON n.notice_id = d.notice_id
                     JOIN breach b ON b.breach_id = n.breach_id
                    WHERE b.breach_uuid = %s ORDER BY d.delivery_id""",
                (uuid,),
            )
        ).fetchall()
    )


def _duty(conn_detail: dict[str, Any]) -> dict[str, Any]:
    [found] = [d for d in conn_detail["obligations"] if d["duty"] == "principals"]
    return found


async def test_nothing_is_sent_before_approval(
    conn: Any, seeded: dict[str, Any], queued: list[Any]
) -> None:
    a = await _person(conn, seeded, "a")
    uuid = await _determined(conn, seeded, [a[1]])
    dpo = int(seeded["users"]["dpo"]["id"])
    await notices.draft(conn, breach_uuid=uuid, words=WORDS, actor_id=dpo)
    with pytest.raises(Conflict, match="Approve a notice"):
        await notices.send(conn, breach_uuid=uuid, actor_id=dpo)
    assert await _deliveries(conn, uuid) == []
    assert _sends(queued) == []


async def test_a_missing_content_blocks_approval(conn: Any, seeded: dict[str, Any]) -> None:
    uuid = await _breach(conn, seeded)
    dpo = int(seeded["users"]["dpo"]["id"])
    view = await notices.draft(
        conn,
        breach_uuid=uuid,
        words={**WORDS, "protective_steps": "  ", "contact": None},
        actor_id=dpo,
    )
    draft = view["versions"][-1]
    with pytest.raises(ValidationFailed) as refused:
        await notices.approve(
            conn, breach_uuid=uuid, notice_uuid=str(draft["notice_uuid"]), actor_id=dpo
        )
    assert refused.value.details["missing"] == ["protective_steps", "contact"]
    assert "7(1)(d)" in refused.value.message and "7(1)(e)" in refused.value.message
    # And past the service, the database refuses it too.
    with pytest.raises(psycopg.errors.CheckViolation):
        await conn.execute(
            "UPDATE breach_notice SET approved_by = %s, approved_at = now() WHERE notice_uuid = %s",
            (dpo, str(draft["notice_uuid"])),
        )


async def test_a_send_reaches_every_account_and_every_registered_contact(
    conn: Any, seeded: dict[str, Any], queued: list[Any]
) -> None:
    a, b = await _person(conn, seeded, "a"), await _person(conn, seeded, "b")
    await conn.execute(
        "UPDATE auth_user SET email = 'x@y.z', email_hash = 'h-test-breach-b' WHERE id = %s",
        (b[0],),
    )
    uuid = await _determined(conn, seeded, [a[1], b[1]])
    await _approved(conn, seeded, uuid)
    view = await notices.send(conn, breach_uuid=uuid, actor_id=int(seeded["users"]["dpo"]["id"]))

    rows = await _deliveries(conn, uuid)
    by = {(r["auth_user_id"], r["channel"]): r["status"] for r in rows}
    assert by == {
        (a[0], "portal"): "delivered",
        (a[0], "sms"): "queued",
        (b[0], "portal"): "delivered",
        (b[0], "email"): "queued",
        (b[0], "sms"): "queued",
    }
    assert len(_sends(queued)) == 3
    assert view["unnotified"] == 2, "queued is not an outcome"

    # Her portal's bell: an audit row against each of them, linking to her page.
    for person_id, _, _ in (a, b):
        feed = await audit_repo.for_subject(conn, person_id, limit=10)
        assert any(e["event_type"] == "breach_notice.delivered" for e in feed)
        [mine] = await notices.for_subject(conn, user_id=person_id)
        assert plain(mine["what_happened"]) == WORDS["what_happened"] and mine["version"] == 1


async def test_a_resend_adds_nothing_and_an_update_reaches_everyone(
    conn: Any, seeded: dict[str, Any], queued: list[Any]
) -> None:
    a = await _person(conn, seeded, "a")
    uuid = await _determined(conn, seeded, [a[1]])
    dpo = int(seeded["users"]["dpo"]["id"])
    await _approved(conn, seeded, uuid)
    await notices.send(conn, breach_uuid=uuid, actor_id=dpo)
    first = await _deliveries(conn, uuid)
    await notices.send(conn, breach_uuid=uuid, actor_id=dpo)
    assert await _deliveries(conn, uuid) == first, "a resend duplicates nothing"
    assert len(_sends(queued)) == 1

    await _approved(conn, seeded, uuid, measures="The list is now encrypted and the share closed.")
    await notices.send(conn, breach_uuid=uuid, actor_id=dpo)
    rows = await _deliveries(conn, uuid)
    assert {(r["version"], r["channel"]) for r in rows} == {
        (1, "portal"),
        (1, "sms"),
        (2, "portal"),
        (2, "sms"),
    }
    assert [n["version"] for n in await notices.for_subject(conn, user_id=a[0])] == [2, 1]


async def test_an_approved_notice_does_not_change(conn: Any, seeded: dict[str, Any]) -> None:
    uuid = await _breach(conn, seeded)
    dpo = int(seeded["users"]["dpo"]["id"])
    view = await _approved(conn, seeded, uuid)
    approved = view["versions"][-1]
    with pytest.raises(Conflict):
        await notices.edit(
            conn,
            breach_uuid=uuid,
            notice_uuid=str(approved["notice_uuid"]),
            words=WORDS,
            actor_id=dpo,
        )
    with pytest.raises(psycopg.errors.RestrictViolation):
        async with conn.transaction():
            await conn.execute(
                "UPDATE breach_notice SET contact = 'someone else' WHERE notice_uuid = %s",
                (str(approved["notice_uuid"]),),
            )
    await notices.draft(conn, breach_uuid=uuid, words=WORDS, actor_id=dpo)
    with pytest.raises(Conflict, match="draft is already open"):
        await notices.draft(conn, breach_uuid=uuid, words=WORDS, actor_id=dpo)


async def test_the_duty_completes_by_delivery_and_reopens_for_people_listed_later(
    conn: Any, seeded: dict[str, Any], queued: list[Any]
) -> None:
    a = await _person(conn, seeded, "a")
    uuid = await _determined(conn, seeded, [a[1]])
    dpo = int(seeded["users"]["dpo"]["id"])
    await _approved(conn, seeded, uuid)
    await notices.send(conn, breach_uuid=uuid, actor_id=dpo)
    assert _duty(await service.detail(conn, uuid))["state"] == "outstanding"

    [sms] = [r for r in await _deliveries(conn, uuid) if r["channel"] == "sms"]
    # The worker spent its retries: a failure recorded is an outcome.
    await notices.record_result(
        conn,
        delivery_uuid=str(sms["delivery_uuid"]),
        status="failed",
        detail={"error": "ConnectionError", "attempts": 6},
    )
    duty = _duty(await service.detail(conn, uuid))
    assert duty["state"] == "done" and duty["events"][-1]["recorded_by_name"] is None
    # A worker recording the same outcome twice records it once.
    await notices.record_result(
        conn, delivery_uuid=str(sms["delivery_uuid"]), status="failed", detail={}
    )
    assert len([r for r in await _deliveries(conn, uuid) if r["status"] == "failed"]) == 1

    # A failed channel gets a new attempt on the next send, and only that.
    await notices.send(conn, breach_uuid=uuid, actor_id=dpo)
    assert [(r["channel"], r["attempt"], r["status"]) for r in await _deliveries(conn, uuid)][
        -1
    ] == ("sms", 2, "queued")

    b = await _person(conn, seeded, "b")
    await affected.confirm(
        conn, breach_uuid=uuid, scopes=[], exclude=[], add=[b[1]], note=None, actor_id=dpo
    )
    duty = _duty(await service.detail(conn, uuid))
    assert duty["state"] == "outstanding" and duty["events"][-1]["kind"] == "reopened"


async def test_the_principals_duty_cannot_be_completed_by_hand(
    conn: Any, seeded: dict[str, Any]
) -> None:
    a = await _person(conn, seeded, "a")
    uuid = await _determined(conn, seeded, [a[1]])
    with pytest.raises(Conflict):
        await service.complete_duty(
            conn,
            breach_uuid=uuid,
            duty="principals",
            occurred_at=datetime.now(UTC),
            reference="x",
            note=None,
            actor_id=int(seeded["users"]["dpo"]["id"]),
        )


async def test_nobody_listed_nothing_to_send(
    conn: Any, seeded: dict[str, Any], queued: list[Any]
) -> None:
    uuid = await _breach(conn, seeded)
    await _approved(conn, seeded, uuid)
    with pytest.raises(Conflict, match="Nobody is listed"):
        await notices.send(conn, breach_uuid=uuid, actor_id=int(seeded["users"]["dpo"]["id"]))


async def test_a_delivery_lost_before_the_worker_is_sent_again(
    conn: Any, seeded: dict[str, Any], queued: list[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A queued SMS whose task never ran - the broker dropped it - stayed queued
    for ever, and Send skipped anything queued, so the principals' duty could
    never complete. Send now queues a stale one again, on the same delivery,
    without a new row; a fresh one is left to the worker."""
    a = await _person(conn, seeded, "a")
    uuid = await _determined(conn, seeded, [a[1]])
    dpo = int(seeded["users"]["dpo"]["id"])
    await _approved(conn, seeded, uuid)
    await notices.send(conn, breach_uuid=uuid, actor_id=dpo)
    rows = await _deliveries(conn, uuid)
    [sms] = [r for r in rows if r["channel"] == "sms"]

    await notices.send(conn, breach_uuid=uuid, actor_id=dpo)
    assert len(_sends(queued)) == 1, "a delivery queued moments ago is the worker's"

    monkeypatch.setattr(notices, "STALE_AFTER", timedelta(0))
    view = await notices.send(conn, breach_uuid=uuid, actor_id=dpo)
    assert [args for _, args in _sends(queued)] == [(str(sms["delivery_uuid"]),)] * 2
    assert await _deliveries(conn, uuid) == rows, "the same delivery, no new row"
    assert view["unnotified"] == 1
