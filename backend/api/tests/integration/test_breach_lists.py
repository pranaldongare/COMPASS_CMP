"""Who a breach touched, from a list somebody sends us (2026-10-07).

A breach whose people are not on the platform could never close: the notice
is owed to everyone listed, and nobody could be listed. Two lists now arrive:

* people by name, email and mobile - one already on the platform joins the
  list as themselves, anybody else is kept, sealed, as this breach's contact;
* asset IDs - the platform's or the capture tool's - and the people who
  consented in each.

Each contact is sent the notice by email and SMS (never to an account they do
not have), and the principals' duty completes when every one has an outcome -
so the breach can close.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from cmp.core.errors import Conflict, ValidationFailed
from cmp.db.sql import fetch_all, fetch_one
from cmp.domain.breach import lists, notices, service
from cmp.tasks import dispatch as dispatch_mod
from tests.conftest import plain
from tests.integration.test_breach_affected import _breach, _person
from tests.integration.test_breach_notices import WORDS, _duty, _sends
from tests.integration.test_rights_flows import _asset_with_her

pytestmark = pytest.mark.integration


@pytest.fixture
def queued(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, tuple[Any, ...]]]:
    sent: list[tuple[str, tuple[Any, ...]]] = []

    def capture(task: Any, *args: Any, **kwargs: Any) -> str:
        sent.append((task.name, args))
        return "queued-in-a-test"

    monkeypatch.setattr(dispatch_mod, "dispatch_optional", capture)
    return sent


def _csv(*rows: str) -> bytes:
    return ("\n".join(rows) + "\n").encode()


async def _recorded(conn: Any, seeded: dict[str, Any]) -> str:
    """A breach determined yes, with nobody listed."""
    uuid = await _breach(conn, seeded)
    await service.determine(
        conn,
        breach_uuid=uuid,
        outcome="yes",
        reasoning="A contact list left the building",
        became_aware_at=datetime.now(UTC) - timedelta(hours=1),
        actor_id=int(seeded["users"]["dpo"]["id"]),
    )
    return uuid


async def _take(conn: Any, seeded: dict[str, Any], uuid: str, kind: str, body: bytes) -> dict:
    return await lists.take(
        conn,
        breach_uuid=uuid,
        kind=kind,
        payload=body,
        file_name=f"{kind}.csv",
        actor_id=int(seeded["users"]["dpo"]["id"]),
    )


def test_the_templates_name_their_columns_and_say_how() -> None:
    people = lists.template("contacts").splitlines()
    assert people[0] == "name,email,mobile"
    assert any(line.startswith("#") for line in people)
    assets = lists.template("assets").splitlines()
    assert assets[0] == "asset_id,source_code"
    with pytest.raises(ValidationFailed):
        lists.template("everyone")


async def test_a_people_list_matches_accounts_and_keeps_the_rest_as_contacts(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _recorded(conn, seeded)
    on_platform = await _person(conn, seeded, "known")
    mobile = plain(
        (await fetch_one(conn, "SELECT mobile FROM auth_user WHERE id = %s", (on_platform[0],)))[
            "mobile"
        ]
    )
    body = _csv(
        "Name,Mail ID,Mobile No",
        "# a comment line is skipped",
        f"Known Person,,{mobile}",
        "Asha Rao,ASHA.rao@example.org,+91 98765 43210",
        "Ravi Kumar,,+91-90000-11111",
        "Asha again,asha.rao@example.org,",
        "Nobody,,",
        "Bad Mail,not-an-email,",
    )
    checked = await lists.check(conn, breach_uuid=uuid, kind="contacts", payload=body)
    assert (checked["matched_people"], checked["new_contacts"], checked["already_listed"]) == (
        1,
        2,
        1,
    )
    assert [e["row"] for e in checked["errors"]] == [7, 8]
    # A check writes nothing.
    assert (await lists.contacts(conn, breach_uuid=uuid, after=None))["total"] == 0

    taken = await _take(conn, seeded, uuid, "contacts", body)
    assert taken["new_contacts"] == 2 and taken["matched_people"] == 1
    shown = await lists.contacts(conn, breach_uuid=uuid, after=None)
    assert shown["total"] == 2
    row = shown["contacts"][0]
    assert row["email"].startswith("SE::") and plain(row["email"]) == "asha.rao@example.org"
    assert plain(row["mobile"]) == "+919876543210"
    [upload] = shown["uploads"]
    assert upload["file_name"].startswith("SE::") and upload["unreadable"] == 2

    [listed] = await fetch_all(
        conn,
        """SELECT a.found_by FROM breach_affected a JOIN breach b USING (breach_id)
            WHERE b.breach_uuid = %s""",
        (uuid,),
    )
    assert listed["found_by"] == "upload"

    # Sent again, the same file adds nothing.
    with pytest.raises(Conflict) as refused:
        await _take(conn, seeded, uuid, "contacts", body)
    assert refused.value.code == "nothing_new"


async def test_an_asset_list_lists_the_people_in_each_asset(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _recorded(conn, seeded)
    a = await _person(conn, seeded, "a")
    b = await _person(conn, seeded, "b")
    await _asset_with_her(conn, seeded, a[2], bystanders=2, ref="LST1")
    await _asset_with_her(conn, seeded, b[2], bystanders=0, ref="LST2")
    asset_b = await fetch_one(
        conn, "SELECT asset_uuid FROM data_asset WHERE source_asset_ref = 'ASSET-LST2'"
    )
    assert asset_b is not None
    body = _csv(
        "asset_id,source_code",
        "ASSET-LST1,",  # the capture tool's ID
        f"{asset_b['asset_uuid']},",  # the platform's ID
        "ASSET-NOPE,",
    )
    checked = await lists.check(conn, breach_uuid=uuid, kind="assets", payload=body)
    assert checked["matched_people"] == 2
    assert checked["untraceable"] == 2
    assert [e["row"] for e in checked["errors"]] == [4]
    taken = await _take(conn, seeded, uuid, "assets", body)
    assert taken["matched_people"] == 2
    people = await fetch_all(
        conn,
        """SELECT u.uuid::text AS uuid FROM breach_affected a
             JOIN breach b USING (breach_id) JOIN auth_user u ON u.id = a.auth_user_id
            WHERE b.breach_uuid = %s""",
        (uuid,),
    )
    assert {p["uuid"] for p in people} == {a[1], b[1]}


async def test_a_reference_two_sources_share_needs_the_source_code(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _recorded(conn, seeded)
    a = await _person(conn, seeded, "a")
    await _asset_with_her(conn, seeded, a[2], bystanders=0, ref="TWIN")
    # A second source with an asset of the same reference.
    await conn.execute(
        """INSERT INTO data_source (source_code, name, source_role, exchange_mode)
           VALUES ('SRC-OTHER', 'Other rig', 'collection', 'file_import')"""
    )
    await conn.execute(
        """INSERT INTO data_asset (source_id, source_asset_ref, collection_id, asset_type)
           SELECT (SELECT source_id FROM data_source WHERE source_code = 'SRC-OTHER'),
                  'ASSET-TWIN', collection_id, 'video'
             FROM data_asset WHERE source_asset_ref = 'ASSET-TWIN' LIMIT 1"""
    )
    ambiguous = await lists.check(
        conn, breach_uuid=uuid, kind="assets", payload=_csv("asset_id", "ASSET-TWIN")
    )
    assert "add source_code" in ambiguous["errors"][0]["message"]
    named = await lists.check(
        conn,
        breach_uuid=uuid,
        kind="assets",
        payload=_csv("asset_id,source_code", "ASSET-TWIN,src-twin"),
    )
    assert named["matched_people"] == 1 and not named["errors"]


async def test_a_file_that_is_not_a_csv_says_how_to_make_one(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _recorded(conn, seeded)
    with pytest.raises(ValidationFailed) as excel:
        await lists.check(conn, breach_uuid=uuid, kind="contacts", payload=b"PK\x03\x04rest")
    assert "Save it as CSV" in excel.value.message
    with pytest.raises(ValidationFailed) as headless:
        await lists.check(conn, breach_uuid=uuid, kind="contacts", payload=_csv("a,b", "1,2"))
    assert "Start from the template" in headless.value.message
    with pytest.raises(ValidationFailed):
        await _take(conn, seeded, uuid, "contacts", _csv("email", "not-an-email"))


async def test_contacts_are_written_to_by_email_and_sms_and_the_breach_can_close(
    conn: Any, seeded: dict[str, Any], queued: list[Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    uuid = await _recorded(conn, seeded)
    await _take(
        conn,
        seeded,
        uuid,
        "contacts",
        _csv("name,email,mobile", "Asha Rao,asha@example.org,+919876543210", "Ravi,,+919000011111"),
    )
    view = await notices.draft(conn, breach_uuid=uuid, words=WORDS, actor_id=dpo)
    await notices.approve(
        conn, breach_uuid=uuid, notice_uuid=str(view["versions"][-1]["notice_uuid"]), actor_id=dpo
    )
    sent = await notices.send(conn, breach_uuid=uuid, actor_id=dpo)
    assert sent["listed"] == 2 and sent["contacts"] == 2
    rows = await fetch_all(
        conn,
        """SELECT d.delivery_uuid, d.auth_user_id, d.contact_id, d.channel
             FROM breach_notice_delivery d JOIN breach_notice n USING (notice_id)
             JOIN breach b USING (breach_id) WHERE b.breach_uuid = %s ORDER BY d.delivery_id""",
        (uuid,),
    )
    # Asha by email and SMS, Ravi by SMS; nobody "in their account".
    assert sorted(r["channel"] for r in rows) == ["email", "sms", "sms"]
    assert all(r["auth_user_id"] is None and r["contact_id"] for r in rows)
    assert len(_sends(queued)) == 3

    job = await notices.job(conn, str(rows[0]["delivery_uuid"]))
    assert job is not None and job["contact_id"] and job["email"].startswith("SE::")

    # A second send adds nothing while they are queued.
    await notices.send(conn, breach_uuid=uuid, actor_id=dpo)
    assert len(_sends(queued)) == 3

    moves = (await service.transitions_for(conn, breach_uuid=uuid))["available"]
    assert "Principals notified is outstanding" in str(moves)
    for r in rows:
        await notices.record_result(
            conn, delivery_uuid=str(r["delivery_uuid"]), status="delivered", detail={}
        )
    duty = _duty(await service.detail(conn, uuid))
    assert duty["state"] == "done"
    report = await notices.account_for_report(conn, breach_uuid=uuid)
    assert report["notified"] == 2 and "no account" in report["statement"]
    moves = (await service.transitions_for(conn, breach_uuid=uuid))["available"]
    assert "Principals notified" not in str(moves)


async def test_a_contact_failure_is_an_outcome_and_names_the_contact(
    conn: Any, seeded: dict[str, Any], queued: list[Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    uuid = await _recorded(conn, seeded)
    await _take(conn, seeded, uuid, "contacts", _csv("name,mobile", "Ravi,+919000011111"))
    view = await notices.draft(conn, breach_uuid=uuid, words=WORDS, actor_id=dpo)
    await notices.approve(
        conn, breach_uuid=uuid, notice_uuid=str(view["versions"][-1]["notice_uuid"]), actor_id=dpo
    )
    await notices.send(conn, breach_uuid=uuid, actor_id=dpo)
    [row] = await fetch_all(
        conn,
        """SELECT d.delivery_uuid FROM breach_notice_delivery d JOIN breach_notice n USING
             (notice_id) JOIN breach b USING (breach_id) WHERE b.breach_uuid = %s""",
        (uuid,),
    )
    await notices.record_result(
        conn,
        delivery_uuid=str(row["delivery_uuid"]),
        status="failed",
        detail={"error": "ConnectionError", "attempts": 6},
    )
    view = await notices.overview(conn, breach_uuid=uuid)
    [failure] = view["failures"]
    assert failure["contact_uuid"] and failure["person_uuid"] is None
    assert plain(failure["full_name"]) == "Ravi"
    assert view["unnotified"] == 0
    # Sending again tries the failed SMS once more.
    await notices.send(conn, breach_uuid=uuid, actor_id=dpo)
    assert len(_sends(queued)) == 2


async def test_contacts_listed_after_the_duty_was_done_reopen_it(
    conn: Any, seeded: dict[str, Any], queued: list[Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    uuid = await _recorded(conn, seeded)
    await _take(conn, seeded, uuid, "contacts", _csv("mobile", "+919000011111"))
    view = await notices.draft(conn, breach_uuid=uuid, words=WORDS, actor_id=dpo)
    await notices.approve(
        conn, breach_uuid=uuid, notice_uuid=str(view["versions"][-1]["notice_uuid"]), actor_id=dpo
    )
    await notices.send(conn, breach_uuid=uuid, actor_id=dpo)
    [row] = await fetch_all(
        conn,
        """SELECT d.delivery_uuid FROM breach_notice_delivery d JOIN breach_notice n USING
             (notice_id) JOIN breach b USING (breach_id) WHERE b.breach_uuid = %s""",
        (uuid,),
    )
    await notices.record_result(
        conn, delivery_uuid=str(row["delivery_uuid"]), status="delivered", detail={}
    )
    await _take(conn, seeded, uuid, "contacts", _csv("mobile", "+919000022222"))
    duty = _duty(await service.detail(conn, uuid))
    assert duty["state"] == "outstanding"


async def test_the_trail_counts_and_never_names(conn: Any, seeded: dict[str, Any]) -> None:
    uuid = await _recorded(conn, seeded)
    await _take(conn, seeded, uuid, "contacts", _csv("name,email", "Asha Rao,asha@example.org"))
    [row] = await fetch_all(
        conn,
        """SELECT l.detail_json FROM audit_log l JOIN breach b ON b.breach_id = l.entity_id
            WHERE l.event_type = 'breach.affected_uploaded' AND b.breach_uuid = %s""",
        (uuid,),
    )
    assert row["detail_json"]["new_contacts"] == 1 and row["detail_json"]["kind"] == "contacts"
    assert "asha" not in str(row["detail_json"]).lower()
