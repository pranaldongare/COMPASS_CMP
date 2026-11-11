"""Who a breach affected, from a list somebody sends us (2026-10-07).

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

import io
import threading
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from openpyxl import Workbook, load_workbook

from cmp.core.errors import Conflict, ValidationFailed
from cmp.db.repositories import breach_lists as lists_repo
from cmp.db.sql import fetch_all, fetch_one
from cmp.domain.breach import affected, lists, notices, service
from cmp.tasks import dispatch as dispatch_mod
from tests.conftest import plain
from tests.integration.test_breach_affected import _breach, _person
from tests.integration.test_breach_notices import WORDS, _duty, _sends
from tests.integration.test_rights_by_office import _as_office
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


def _headers(payload: bytes) -> list[Any]:
    sheet = load_workbook(io.BytesIO(payload)).worksheets[0]
    return [c.value for c in next(sheet.iter_rows(min_row=1, max_row=1))]


def _workbook(*rows: tuple[Any, ...]) -> bytes:
    book = Workbook()
    for row in rows:
        book.active.append(row)
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


def test_the_templates_are_excel_files_that_name_their_columns() -> None:
    assert _headers(lists.template("contacts")) == ["Name", "Mail ID", "Mobile number"]
    assert _headers(lists.template("assets")) == ["Asset ID *", "Source code"]
    with pytest.raises(ValidationFailed):
        lists.template("everyone")


async def test_an_excel_list_is_read_like_a_csv(conn: Any, seeded: dict[str, Any]) -> None:
    uuid = await _recorded(conn, seeded)
    body = _workbook(
        ("Name", "Mail IDs", "Mobile Number"),
        ("Asha Rao", "asha.xlsx@example.org", "+91 98765 11111"),
        ("Vikram", None, 919876522222),
        ("Nobody", None, None),
        ("Broken", "not-an-address", None),
    )
    assert lists.read("contacts", body).rows[0] == (
        2,
        {"name": "Asha Rao", "email": "asha.xlsx@example.org", "mobile": "+91 98765 11111"},
    )
    report = await lists.check(conn, breach_uuid=uuid, kind="contacts", payload=body)
    assert report["new_contacts"] == 2 and report["unreadable"] == 2
    assert [e["row"] for e in report["errors"]] == [4, 5], "by the row Excel shows"
    assert report["errors"][1]["message"] == "Not an email address: not-an-address"
    taken = await _take(conn, seeded, uuid, "contacts", body)
    assert taken["new_contacts"] == 2


@pytest.mark.parametrize(
    ("mail", "mobile"),
    [
        ("Mail IDs", "Mobile number"),
        ("Mail ID", "Mobile numbers"),
        ("Email IDs", "Mobile No."),
        ("E-mail", "Phone number"),
        ("email_id", "mobile_no"),
    ],
)
def test_the_columns_people_write_are_read_from_either_kind_of_file(mail: str, mobile: str) -> None:
    expected = {"name": "Asha", "email": "asha@example.org", "mobile": "+919876511111"}
    excel = _workbook(("Name", mail, mobile), ("Asha", "asha@example.org", "+919876511111"))
    assert lists.read("contacts", excel).rows == [(2, expected)]
    csv = _csv(f"Name,{mail},{mobile}", "Asha,asha@example.org,+919876511111")
    assert lists.read("contacts", csv).rows == [(2, expected)]


@pytest.mark.parametrize(
    "heading", ["Alternate mail", "Email 2", "Secondary Mobile", "Telephone", "Mail ID"]
)
def test_a_contact_column_that_cannot_be_read_stops_the_file_by_name(heading: str) -> None:
    """Quietly left out, it is somebody who is never told. 'Mail ID' here is the
    column named a second time."""
    excel = _workbook(("Email", heading), ("asha@example.org", "x"))
    csv = _csv(f"Email,{heading}", "asha@example.org,x")
    for body in (excel, csv):
        with pytest.raises(ValidationFailed) as refused:
            lists.read("contacts", body)
        assert heading in refused.value.message and refused.value.field == "file"


def test_a_file_with_neither_contact_column_names_what_it_has() -> None:
    excel = _workbook(("Name", "Contact"), ("Asha", "asha@example.org"))
    csv = _csv("Name,Contact", "Asha,asha@example.org")
    for body in (excel, csv):
        with pytest.raises(ValidationFailed) as refused:
            lists.read("contacts", body)
        assert "'Contact'" in refused.value.message
        assert "Start from the template" in refused.value.message


def test_a_heading_that_only_sounds_like_a_contact_is_left_alone() -> None:
    body = _workbook(("Mailing address", "Email"), ("12 Hill Road", "asha@example.org"))
    assert lists.read("contacts", body).rows == [(2, {"email": "asha@example.org"})]


def test_a_mobile_excel_made_a_number_gets_its_plus_back() -> None:
    body = _workbook(
        ("Email", "Mobile number"),
        (None, 919876522222),  # as Excel keeps a typed +919876522222
        (None, 919876522222.0),
        (None, 9876522222),  # ten digits: no country code to be sure of
    )
    assert [r["mobile"] for _, r in lists.read("contacts", body).rows] == [
        "+919876522222",
        "+919876522222",
        "9876522222",
    ]


async def test_a_number_cell_finds_the_account_it_belongs_to(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _recorded(conn, seeded)
    a = await _person(conn, seeded, "by number")
    row = await fetch_one(conn, "SELECT mobile FROM auth_user WHERE id = %s", (a[0],))
    assert row is not None
    body = _workbook(("Mobile number",), (int(str(plain(row["mobile"])).lstrip("+")),))
    report = await lists.check(conn, breach_uuid=uuid, kind="contacts", payload=body)
    assert (report["matched_people"], report["new_contacts"]) == (1, 0)


def test_the_template_s_mobile_column_is_text() -> None:
    sheet = load_workbook(io.BytesIO(lists.template("contacts"))).worksheets[0]
    assert sheet.column_dimensions["C"].number_format == "@"


async def test_a_list_is_read_off_the_event_loop(
    conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    uuid = await _recorded(conn, seeded)
    read = lists.read
    ran_on: list[threading.Thread] = []

    def watched(kind: str, payload: bytes) -> lists.Reading:
        ran_on.append(threading.current_thread())
        return read(kind, payload)

    monkeypatch.setattr(lists, "read", watched)
    await lists.check(conn, breach_uuid=uuid, kind="contacts", payload=_csv("email", "a@b.org"))
    assert ran_on and ran_on[0] is not threading.current_thread()


def test_a_csv_is_read_as_one_text_and_rows_keep_their_lines() -> None:
    """A quoted field may hold a newline. A comment and a blank line are not
    rows, and the row number is the line the record starts on."""
    body = b'# from the vendor\nemail,name\n\n"a\nb@c.org",Asha\nd@e.org,Ravi\n'
    assert lists.read("contacts", body).rows == [
        (4, {"email": "a\nb@c.org", "name": "Asha"}),
        (6, {"email": "d@e.org", "name": "Ravi"}),
    ]


def test_a_csv_the_reader_refuses_is_a_plain_refusal() -> None:
    with pytest.raises(ValidationFailed) as refused:
        lists.read("contacts", b"email\n" + b"a" * 140_000 + b"\n")
    assert refused.value.field == "file"


async def test_an_asset_of_the_other_office_is_not_found_by_a_list(
    conn: Any, seeded: dict[str, Any]
) -> None:
    a = await _person(conn, seeded, "wall")
    await _asset_with_her(conn, seeded, a[2], bystanders=1, ref="WALL1")
    asset = await fetch_one(
        conn, "SELECT asset_id, asset_uuid FROM data_asset WHERE source_asset_ref = 'ASSET-WALL1'"
    )
    assert asset is not None
    asset_id, asset_uuid = int(asset["asset_id"]), str(asset["asset_uuid"])

    await _as_office(conn, "hr")
    assert await lists_repo.assets_by_uuid(conn, [asset_uuid]) == []
    assert await lists_repo.assets_by_ref(conn, ["ASSET-WALL1"]) == []
    assert await lists_repo.people_in_assets(conn, [asset_id]) == ([], 0)

    await _as_office(conn, "rnd")
    assert len(await lists_repo.assets_by_uuid(conn, [asset_uuid])) == 1
    assert len(await lists_repo.assets_by_ref(conn, ["ASSET-WALL1"])) == 1
    people, untraceable = await lists_repo.people_in_assets(conn, [asset_id])
    assert [p["person_id"] for p in people] == [a[0]] and untraceable == 1


async def test_the_template_as_downloaded_can_be_filled_in_and_sent(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _recorded(conn, seeded)
    book = load_workbook(io.BytesIO(lists.template("contacts")))
    book.worksheets[0].append(("Meena", "meena.template@example.org", None))
    out = io.BytesIO()
    book.save(out)
    report = await lists.check(conn, breach_uuid=uuid, kind="contacts", payload=out.getvalue())
    assert report["new_contacts"] == 1


async def test_an_excel_sheet_without_a_contact_column_says_so(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _recorded(conn, seeded)
    with pytest.raises(ValidationFailed) as refused:
        await lists.check(
            conn, breach_uuid=uuid, kind="contacts", payload=_workbook(("Name",), ("Asha",))
        )
    assert "Start from the template" in refused.value.message


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


async def test_a_file_that_cannot_be_read_says_what_to_do(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _recorded(conn, seeded)
    with pytest.raises(ValidationFailed) as old:
        await lists.check(
            conn, breach_uuid=uuid, kind="contacts", payload=b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
        )
    assert "Save it as .xlsx" in old.value.message
    with pytest.raises(ValidationFailed) as broken:
        await lists.check(conn, breach_uuid=uuid, kind="contacts", payload=b"PK\x03\x04rest")
    assert "xlsx" in broken.value.message
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


# ------------------------------------------------------- typed in (2026-11-11)


def test_typed_entries_split_as_outlook_copies_them() -> None:
    assert lists.split_entries(" a@x.org, b@x.org;c@x.org\n\nd@x.org ,") == [
        "a@x.org",
        "b@x.org",
        "c@x.org",
        "d@x.org",
    ]
    assert lists.split_entries('"Nair, Meera" <meera@x.org>; Ravi <ravi@x.org>') == [
        '"Nair, Meera" <meera@x.org>',
        "Ravi <ravi@x.org>",
    ]
    assert lists.split_entries("+91 98765 43210, +91-90000-11111") == [
        "+91 98765 43210",
        "+91-90000-11111",
    ]
    assert lists.split_entries(" , ;\n") == []


def test_each_mail_id_and_mobile_typed_is_one_person() -> None:
    reading = lists.read_typed(
        '"Nair, Meera" <Meera@X.org>, ravi@x.org', "+91 98765 43210, 98765 43211"
    )
    assert reading.rows == [
        (1, {"name": "Nair, Meera", "email": "Meera@X.org"}),
        (2, {"email": "ravi@x.org"}),
        (3, {"mobile": "+91 98765 43210"}),
    ]
    # No country code is assumed: the person typing it can add one.
    assert reading.errors == [
        {
            "row": 4,
            "message": "98765 43211: give the mobile number with its country code, "
            "as +91 98765 43210",
        }
    ]
    with pytest.raises(ValidationFailed):
        lists.read_typed(" , ", "")
    with pytest.raises(ValidationFailed):
        lists.read_typed(",".join(f"p{i}@x.org" for i in range(lists.MAX_TYPED + 1)), "")


async def test_typed_people_are_matched_or_kept_as_contacts_and_named_in_the_history(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _recorded(conn, seeded)
    dpo = int(seeded["users"]["dpo"]["id"])
    by_mobile = await _person(conn, seeded, "typed-mobile")
    by_name = await _person(conn, seeded, "typed-name")
    mobile = plain(
        (await fetch_one(conn, "SELECT mobile FROM auth_user WHERE id = %s", (by_mobile[0],)))[
            "mobile"
        ]
    )
    typed = {
        "mail_ids": 'Asha Rao <ASHA.typed@example.org>, "Kumar, Ravi" <ravi.typed@example.org>;'
        " asha.typed@example.org, not-an-email",
        "mobiles": f"{mobile}, +91 90000 22222, 90000 33333",
        "people": [by_name[1]],
    }
    checked = await lists.check_typed(conn, breach_uuid=uuid, **typed)
    assert checked["kind"] == "typed"
    assert (
        checked["rows_read"],
        checked["matched_people"],
        checked["new_contacts"],
        checked["already_listed"],
        checked["unreadable"],
    ) == (8, 2, 3, 1, 2)
    assert [e["message"] for e in checked["errors"]] == [
        "Not an email address: not-an-email",
        "90000 33333: give the mobile number with its country code, as +91 98765 43210",
    ]
    # A check writes nothing.
    assert (await lists.contacts(conn, breach_uuid=uuid, after=None))["total"] == 0

    taken = await lists.take_typed(
        conn, breach_uuid=uuid, note="From the vendor's email of 10 Nov", actor_id=dpo, **typed
    )
    assert (taken["matched_people"], taken["new_contacts"]) == (2, 3)
    shown = await lists.contacts(conn, breach_uuid=uuid, after=None)
    assert {
        (plain(c["full_name"]), plain(c["email"]), plain(c["mobile"]), c["upload_kind"])
        for c in shown["contacts"]
    } == {
        ("Asha Rao", "asha.typed@example.org", None, "typed"),
        ("Kumar, Ravi", "ravi.typed@example.org", None, "typed"),
        (None, None, "+919000022222", "typed"),
    }
    [upload] = shown["uploads"]
    assert upload["kind"] == "typed" and plain(upload["file_name"]) == lists.TYPED_NAME

    listed = await fetch_all(
        conn,
        """SELECT a.auth_user_id, a.found_by FROM breach_affected a JOIN breach b USING (breach_id)
            WHERE b.breach_uuid = %s ORDER BY a.auth_user_id""",
        (uuid,),
    )
    assert [(r["auth_user_id"], r["found_by"]) for r in listed] == sorted(
        [(by_mobile[0], "dpo"), (by_name[0], "dpo")]
    )
    [revision] = (await affected.listing(conn, breach_uuid=uuid, after=None))["revisions"]
    assert revision["scopes"][0]["file"] == "typed" and revision["added_by_hand"] == 2
    assert plain(revision["note"]) == "From the vendor's email of 10 Nov"

    # Typed again, it adds nothing.
    with pytest.raises(Conflict) as refused:
        await lists.take_typed(conn, breach_uuid=uuid, note=None, actor_id=dpo, **typed)
    assert refused.value.code == "nothing_new"


async def test_typed_entries_none_of_which_can_be_used_are_refused(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _recorded(conn, seeded)
    with pytest.raises(ValidationFailed):
        await lists.take_typed(
            conn,
            breach_uuid=uuid,
            mail_ids="nobody",
            mobiles="12345",
            people=[],
            note=None,
            actor_id=int(seeded["users"]["dpo"]["id"]),
        )


async def test_a_typed_list_on_the_trail_counts_and_never_names(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _recorded(conn, seeded)
    await lists.take_typed(
        conn,
        breach_uuid=uuid,
        mail_ids="Asha Rao <asha.trail@example.org>",
        mobiles="",
        people=[],
        note=None,
        actor_id=int(seeded["users"]["dpo"]["id"]),
    )
    [row] = await fetch_all(
        conn,
        """SELECT l.detail_json FROM audit_log l JOIN breach b ON b.breach_id = l.entity_id
            WHERE l.event_type = 'breach.affected_uploaded' AND b.breach_uuid = %s""",
        (uuid,),
    )
    assert row["detail_json"]["kind"] == "typed" and row["detail_json"]["new_contacts"] == 1
    assert "asha" not in str(row["detail_json"]).lower()
