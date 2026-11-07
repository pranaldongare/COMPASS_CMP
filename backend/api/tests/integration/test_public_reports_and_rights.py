"""A dismissed report from the public link, and the rights of the person who
sent it (the product owner's fifth answer of 2026-11-07, 0065).

An access or erasure request about everything held finds, once identity is
verified, the reports its subject sent that an office dismissed: by the blind
index of the addresses she has proved, or of the email a request with no
account gave. Only the officers are shown them. An erasure takes her name and
email off them, once, and keeps the number, her words, the reason and who
dismissed it; a legal hold on her stops it, and complete waits for it.

Every test makes its own person and addresses, with a uuid in them: these run
on a database the HTTP suite commits to, and a fixed address would meet its
rows. Reports are asserted by number, never by count of everything found.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from cmp.api.routers.v1 import rights as rights_router
from cmp.auth.authentication import otp
from cmp.auth.rate_limit import service as ratelimit
from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.core.permissions import Role
from cmp.db.repositories import audit as audit_repo
from cmp.db.sql import fetch_all, fetch_one
from cmp.domain.breach import intake
from cmp.domain.rights import execution, holds, package, public_reports, service
from cmp.infrastructure.dkms import DkmsUnavailable
from tests.conftest import hashed, plain
from tests.integration.test_rights_flows import _consent, _unthrottle

pytestmark = pytest.mark.integration

DPO = Role.DPO


def _dpo(seeded: dict[str, Any]) -> int:
    return int(seeded["users"]["dpo"]["id"])


def _address(tag: str = "reporter") -> str:
    return f"{tag}.{uuid.uuid4().hex[:10]}@example.org"


async def _person(
    conn: Any, *, email: str | None = None, secondary: str | None = None, proved: bool = False
) -> dict[str, Any]:
    """A data principal of her own, with a second email, proved or not."""
    email = email or _address("principal")
    mobile = f"+9196{uuid.uuid4().int % 10**8:08d}"
    row = await fetch_one(
        conn,
        """INSERT INTO auth_user (full_name, email, email_hash, mobile, mobile_hash, role,
                                  status, minor_until, secondary_email, secondary_email_hash,
                                  secondary_email_verified_at)
           VALUES ('Asha Rao', %s, %s, %s, %s, 'data_subject', 'active', DATE '2008-05-17',
                   %s, %s, %s)
           RETURNING id, uuid""",
        (
            email,
            hashed("email", email),
            mobile,
            hashed("mobile", mobile),
            secondary,
            hashed("email", secondary),
            datetime.now(UTC) if proved else None,
        ),
    )
    assert row is not None
    return {"id": int(row["id"]), "uuid": str(row["uuid"]), "email": email}


async def _reported(conn: Any, email: str, *, title: str = "A laptop left on a train") -> str:
    """A report through the public link, as the reporter makes it. Its number."""
    issued = await otp.issue(otp.Scope.INCIDENT_REPORT, ratelimit.contact_key(email))
    made = await intake.submit(
        conn,
        reporter_name="Asha Rao",
        email=email,
        code=issued.code,
        title=title,
        noticed_at=None,
        told={"incident_details": "It had the participant list on it"},
        cyber_attack=None,
        ip_address=None,
    )
    return str(made["reference"])


async def _uuid_of(conn: Any, reference: str) -> str:
    row = await fetch_one(
        conn, "SELECT report_uuid FROM incident_report WHERE reference = %s", (reference,)
    )
    assert row is not None
    return str(row["report_uuid"])


async def _dismissed(conn: Any, seeded: dict[str, Any], email: str, **kw: Any) -> str:
    reference = await _reported(conn, email, **kw)
    await intake.dismiss(
        conn,
        report_uuid=await _uuid_of(conn, reference),
        reason="Not a breach of ours",
        actor_id=_dpo(seeded),
    )
    return reference


async def _report_row(conn: Any, reference: str) -> dict[str, Any]:
    row = await fetch_one(
        conn, "SELECT to_jsonb(r) AS r FROM incident_report r WHERE reference = %s", (reference,)
    )
    assert row is not None
    return dict(row["r"])


async def _request(
    conn: Any,
    seeded: dict[str, Any],
    person: dict[str, Any],
    kind: str = "erasure",
    *,
    started: bool = True,
) -> dict[str, Any]:
    """Her request from the portal, verified by the session, in the DPO office."""
    row = await service.create(
        conn,
        request_type=kind,
        channel="portal",
        request_text=f"A {kind} request",
        submitted_contact=person["email"],
        submitted_name="Asha Rao",
        subject_user_id=person["id"],
        actor_id=person["id"],
        verification_method="session",
        office="rnd",
    )
    return await _start(conn, seeded, row) if started else row


async def _start(conn: Any, seeded: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    row = await service.classify(
        conn, row, request_type=row["request_type"], note=None, role=DPO, actor_id=_dpo(seeded)
    )
    if row["request_type"] == "erasure":
        row = await service.confirm_intent(conn, row, role=DPO, actor_id=_dpo(seeded))
    return await service.transition(
        conn, row, to="in_progress", reason=None, role=DPO, actor_id=_dpo(seeded)
    )


async def _from_the_form(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, contact: str
) -> dict[str, Any]:
    """An erasure request from the public form, as the office reads it."""
    await _unthrottle(redis_conn, contact)
    made = await service.submit_public(
        conn,
        request_type="erasure",
        contact=contact,
        name="Asha Rao",
        request_text="Take me off what I sent",
        ip_address="127.0.0.1",
    )
    return await service.require(
        conn, await _request_uuid(conn, made["reference"]), role=DPO, user_id=_dpo(seeded)
    )


async def _request_uuid(conn: Any, reference: str) -> str:
    row = await fetch_one(
        conn, "SELECT request_uuid FROM rights_request WHERE reference = %s", (reference,)
    )
    assert row is not None
    return str(row["request_uuid"])


async def _verified_by_hand(
    conn: Any, seeded: dict[str, Any], row: dict[str, Any]
) -> dict[str, Any]:
    row = await service.verify_manually(
        conn, row, note="Called her back", role=DPO, actor_id=_dpo(seeded)
    )
    return await service.claim(conn, row, role=DPO, office="rnd", actor_id=_dpo(seeded))


def _found(result: dict[str, Any]) -> set[str]:
    return {str(r["reference"]) for r in result["open"]}


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
    """What the rights service would have queued, kept here instead."""
    queued: list[tuple[Any, ...]] = []
    monkeypatch.setattr(service, "_dispatch", lambda *a: queued.append(a))
    return queued


# ------------------------------------------------------------------ finding
async def test_a_request_not_yet_verified_finds_nothing(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, sent: Any
) -> None:
    person = await _person(conn)
    mine = await _dismissed(conn, seeded, person["email"])
    row = await _from_the_form(conn, seeded, redis_conn, person["email"])
    assert row["subject_user_id"] == person["id"] and row["verification_status"] == "pending"
    found = await public_reports.found(conn, row)
    assert found["looked"] is False and found["open"] == []
    assert found["not_looked_because"] == public_reports.NOT_VERIFIED
    with pytest.raises(Conflict) as refused:
        await public_reports.erase(conn, row, role=DPO, actor_id=_dpo(seeded))
    assert refused.value.code == "request_not_started"
    assert (await _report_row(conn, mine))["reporter_email"] is not None


async def test_a_verified_request_finds_her_dismissed_reports_by_her_email(
    conn: Any, seeded: dict[str, Any]
) -> None:
    person = await _person(conn)
    first = await _dismissed(conn, seeded, person["email"].upper())
    second = await _dismissed(conn, seeded, person["email"], title="And another")
    waiting = await _reported(conn, person["email"])
    claimed = await _reported(conn, person["email"])
    await intake.claim(
        conn, report_uuid=await _uuid_of(conn, claimed), office="rnd", actor_id=_dpo(seeded)
    )
    someone_else = await _dismissed(conn, seeded, _address())

    row = await _request(conn, seeded, person, "access")
    found = await public_reports.found(conn, row)
    assert found["looked"] is True
    assert _found(found) == {first, second}
    assert not {waiting, claimed, someone_else} & _found(found)
    shown = await public_reports.view(conn, row, role=DPO)
    assert shown is not None
    assert [i["reference"] for i in shown["items"]] == [first, second], "oldest first"
    assert shown["total"] == 2 and shown["erased"] == 0
    assert all(str(i["reporter_email"]).startswith("SE::") for i in shown["items"])
    assert all(str(i["title"]).startswith("SE::") for i in shown["items"])
    assert "dismissal_reason" not in shown["items"][0]
    assert shown["may_erase"] is False and shown["erase_blocked_by"] == public_reports.NOT_ERASURE


async def test_a_verified_secondary_email_finds_and_an_unverified_one_does_not(
    conn: Any, seeded: dict[str, Any]
) -> None:
    proved, claimed = _address("second"), _address("second")
    on_proved = await _dismissed(conn, seeded, proved)
    on_claimed = await _dismissed(conn, seeded, claimed)
    a = await _person(conn, secondary=proved, proved=True)
    b = await _person(conn, secondary=claimed, proved=False)
    assert on_proved in _found(
        await public_reports.found(conn, await _request(conn, seeded, a, "access"))
    )
    assert on_claimed not in _found(
        await public_reports.found(conn, await _request(conn, seeded, b, "access"))
    )


async def test_a_grievance_finds_nothing(conn: Any, seeded: dict[str, Any]) -> None:
    person = await _person(conn)
    await _dismissed(conn, seeded, person["email"])
    row = await _request(conn, seeded, person, "grievance", started=False)
    found = await public_reports.found(conn, row)
    assert found["looked"] is False and found["open"] == []
    assert found["not_looked_because"] == public_reports.NOT_THIS_KIND


async def test_a_request_confined_to_a_consent_finds_nothing(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """A request from before 2026-10-07, confined to one consent: a report is under none."""
    person = await _person(conn)
    await _dismissed(conn, seeded, person["email"])
    consent = await _consent(conn, seeded)
    row = await _request(conn, seeded, person, "erasure")
    await conn.execute(
        "UPDATE rights_request SET consent_id = %s WHERE request_id = %s",
        (consent["consent_id"], int(row["request_id"])),
    )
    row = await service.reload(conn, row)
    found = await public_reports.found(conn, row)
    assert found["looked"] is False and found["not_looked_because"] == public_reports.CONFINED
    with pytest.raises(Conflict) as refused:
        await public_reports.erase(conn, row, role=DPO, actor_id=_dpo(seeded))
    assert refused.value.code == "not_erasure"


async def test_a_request_with_no_account_finds_by_the_email_it_gave_once_verified(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, sent: Any
) -> None:
    email = _address()
    mine = await _dismissed(conn, seeded, email)
    row = await _from_the_form(conn, seeded, redis_conn, f" {email.upper()} ")
    assert row["subject_user_id"] is None
    assert (await public_reports.found(conn, row))["looked"] is False
    row = await _verified_by_hand(conn, seeded, row)
    assert mine in _found(await public_reports.found(conn, row))


async def test_a_mobile_contact_finds_nothing(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, sent: Any
) -> None:
    row = await _from_the_form(conn, seeded, redis_conn, f"+9195{uuid.uuid4().int % 10**8:08d}")
    assert row["subject_user_id"] is None
    row = await _verified_by_hand(conn, seeded, row)
    found = await public_reports.found(conn, row)
    assert found["looked"] is True and found["open"] == []


async def test_the_key_service_down_leaves_the_page_and_holds_complete(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, sent: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    row = await _verified_by_hand(
        conn, seeded, await _from_the_form(conn, seeded, redis_conn, _address())
    )
    row = await _start(conn, seeded, row)

    async def down(*_: Any) -> Any:
        raise DkmsUnavailable("the key service is down")

    monkeypatch.setattr(public_reports, "unseal_value", down)
    found = await public_reports.found(conn, row)
    assert found["looked"] is False and found["unavailable"] is True
    detail = await rights_router._detail(conn, row, SimpleNamespace(role=DPO, user_id=_dpo(seeded)))
    assert detail["public_reports"]["looked"] is False
    assert detail["public_reports"]["not_looked_because"] == public_reports.UNAVAILABLE
    assert detail["public_reports"]["may_erase"] is False
    assert "could not be checked" in str(detail["complete_blocked_by"])
    with pytest.raises(DkmsUnavailable):
        await public_reports.erase(conn, row, role=DPO, actor_id=_dpo(seeded))


# ------------------------------------------------------------------- access
async def test_the_access_package_carries_her_words_and_not_the_office_s_reason(
    conn: Any, seeded: dict[str, Any]
) -> None:
    person = await _person(conn)
    mine = await _dismissed(conn, seeded, person["email"])
    row = await _request(conn, seeded, person, "access")
    built = await package.build_response(
        conn, row, holders=[], response_text="Our answer.", generated_at=datetime.now(UTC)
    )
    [entry] = [e for e in built["reports_from_the_public_link"] if e["reference"] == mine]
    assert entry["title"] == "A laptop left on a train"
    assert entry["reported_by"] == {"full_name": "Asha Rao", "email": person["email"]}
    assert entry["what_you_told_us"]["incident_details"] == "It had the participant list on it"
    assert entry["outcome"] == public_reports.NOT_TAKEN_UP
    assert entry["received_at"] and entry["dismissed_at"]
    assert built["summary"]["reports_from_the_public_link"] == 1
    assert "public link" in built["scope"]
    text = package.encode(built).decode()
    assert "dismissal_reason" not in text and "dismissed_by" not in text
    assert "Not a breach of ours" not in text, "the office's reason is its own note"
    digest = package.digest_text(built)
    assert "REPORTS YOU SENT THROUGH THE PUBLIC LINK" in digest and mine in digest
    assert person["email"] not in digest


# ------------------------------------------------------------------ erasure
async def test_erasure_blanks_her_name_and_email_and_keeps_the_number_the_words_the_reason_and_who(
    conn: Any, seeded: dict[str, Any]
) -> None:
    person = await _person(conn)
    mine = await _dismissed(conn, seeded, person["email"])
    before = await _report_row(conn, mine)
    row = await _request(conn, seeded, person)
    shown = await public_reports.view(conn, row, role=DPO)
    assert shown is not None and shown["may_erase"] is True and shown["erase_blocked_by"] is None

    shown = await public_reports.erase(conn, row, role=DPO, actor_id=_dpo(seeded))

    after = await _report_row(conn, mine)
    assert (after["reporter_name"], after["reporter_email"], after["reporter_email_hash"]) == (
        None,
        None,
        None,
    )
    assert after["reporter_erased_by"] == _dpo(seeded)
    assert after["reporter_erased_request_id"] == int(row["request_id"])
    assert after["reporter_erased_at"]
    for kept in ("reference", "title", "incident_details", "dismissed_by", "dismissed_at"):
        assert after[kept] == before[kept], kept
    assert plain(after["dismissal_reason"]) == "Not a breach of ours"
    [item] = [i for i in shown["items"] if i["reference"] == mine]
    assert item["reporter_name"] is None and item["reporter_email"] is None
    assert item["reporter_erased_at"] is not None and str(item["title"]).startswith("SE::")
    assert shown["total"] == 0 and shown["erased"] == 1
    assert shown["may_erase"] is False and shown["erase_blocked_by"] == public_reports.NOTHING_LEFT


async def test_an_erasure_of_one_person_s_reports_leaves_another_s_untouched(
    conn: Any, seeded: dict[str, Any]
) -> None:
    person = await _person(conn)
    await _dismissed(conn, seeded, person["email"])
    other = await _dismissed(conn, seeded, _address())
    before = await _report_row(conn, other)
    await public_reports.erase(
        conn, await _request(conn, seeded, person), role=DPO, actor_id=_dpo(seeded)
    )
    assert await _report_row(conn, other) == before


async def test_erasure_waits_for_the_request_to_start(conn: Any, seeded: dict[str, Any]) -> None:
    person = await _person(conn)
    mine = await _dismissed(conn, seeded, person["email"])
    row = await _request(conn, seeded, person, started=False)
    with pytest.raises(Conflict) as refused:
        await public_reports.erase(conn, row, role=DPO, actor_id=_dpo(seeded))
    assert refused.value.code == "request_not_started"
    shown = await public_reports.view(conn, row, role=DPO)
    assert shown is not None and mine in {i["reference"] for i in shown["items"]}
    assert shown["may_erase"] is False and shown["erase_blocked_by"] == public_reports.NOT_STARTED


async def test_an_access_request_cannot_erase(conn: Any, seeded: dict[str, Any]) -> None:
    person = await _person(conn)
    await _dismissed(conn, seeded, person["email"])
    row = await _request(conn, seeded, person, "access")
    with pytest.raises(Conflict) as refused:
        await public_reports.erase(conn, row, role=DPO, actor_id=_dpo(seeded))
    assert refused.value.code == "not_erasure"


async def test_a_closed_request_cannot_erase(conn: Any, seeded: dict[str, Any], sent: Any) -> None:
    person = await _person(conn)
    await _dismissed(conn, seeded, person["email"])
    row = await _request(conn, seeded, person)
    await conn.execute(
        "UPDATE rights_request SET status = 'closed', outcome = 'partial', closed_at = now()"
        " WHERE request_id = %s",
        (int(row["request_id"]),),
    )
    with pytest.raises(Conflict) as refused:
        await public_reports.erase(
            conn, await service.reload(conn, row), role=DPO, actor_id=_dpo(seeded)
        )
    assert refused.value.code == "request_closed"


async def test_a_hold_on_her_stops_it_and_its_release_lets_it_go(
    conn: Any, seeded: dict[str, Any]
) -> None:
    person = await _person(conn)
    mine = await _dismissed(conn, seeded, person["email"])
    row = await _request(conn, seeded, person)
    held = await holds.place(
        conn,
        asset_uuid=None,
        subject_uuid=person["uuid"],
        reason="Evidence in a live matter",
        actor_id=_dpo(seeded),
    )
    with pytest.raises(Conflict) as refused:
        await public_reports.erase(conn, row, role=DPO, actor_id=_dpo(seeded))
    assert refused.value.code == "legal_hold"
    shown = await public_reports.view(conn, row, role=DPO)
    assert shown is not None and shown["erase_blocked_by"] == public_reports.HELD
    assert (await _report_row(conn, mine))["reporter_email"] is not None

    await holds.release(conn, hold_uuid=str(held["hold_uuid"]), actor_id=_dpo(seeded))
    await public_reports.erase(conn, row, role=DPO, actor_id=_dpo(seeded))
    assert (await _report_row(conn, mine))["reporter_email"] is None


async def _erasures(conn: Any, reference: str) -> list[dict[str, Any]]:
    return await fetch_all(
        conn,
        """SELECT l.detail_json FROM audit_log l
            WHERE l.event_type = 'incident_report.reporter_erased'
              AND l.detail_json->>'incident_reference' = %s""",
        (reference,),
    )


async def test_erasing_twice_changes_nothing_and_records_once(
    conn: Any, seeded: dict[str, Any]
) -> None:
    person = await _person(conn)
    first = await _dismissed(conn, seeded, person["email"])
    second = await _dismissed(conn, seeded, person["email"])
    row = await _request(conn, seeded, person)
    await public_reports.erase(conn, row, role=DPO, actor_id=_dpo(seeded))
    after_once = (await _report_row(conn, first), await _report_row(conn, second))
    again = await public_reports.erase(conn, row, role=DPO, actor_id=_dpo(seeded))
    assert (await _report_row(conn, first), await _report_row(conn, second)) == after_once
    assert [len(await _erasures(conn, r)) for r in (first, second)] == [1, 1]
    assert again["erased"] == 2 and again["total"] == 0


async def test_the_trail_names_the_references_and_never_the_address(
    conn: Any, seeded: dict[str, Any]
) -> None:
    person = await _person(conn)
    mine = await _dismissed(conn, seeded, person["email"])
    row = await _request(conn, seeded, person)
    await public_reports.erase(conn, row, role=DPO, actor_id=_dpo(seeded))
    [logged] = await _erasures(conn, mine)
    detail = logged["detail_json"]
    # Beside what the audit adds to every row: its chain and the request's origin.
    said = {k: v for k, v in detail.items() if k not in {"_hash", "_prev", "ip", "request_id"}}
    assert said == {"reference": row["reference"], "incident_reference": mine}
    text = json.dumps(detail)
    assert "@" not in text and "Asha" not in text
    trail = await audit_repo.for_reference(conn, str(row["reference"]))
    erased = [e for e in trail if e["event_type"] == "incident_report.reporter_erased"]
    assert erased and erased[0]["entity_type"] == "incident_report"
    assert audit_repo.visible_to_subject(erased) == erased, "what was done with her name"
    feed = await audit_repo.for_subject(conn, person["id"])
    assert "incident_report.reporter_erased" in {e["event_type"] for e in feed}


async def test_complete_is_held_back_until_she_is_erased_and_allowed_after(
    conn: Any, seeded: dict[str, Any], sent: Any
) -> None:
    """An erasure with no asset and no holder: erasing her off a report is the
    one thing done, and it is enough."""
    person = await _person(conn)
    mine = await _dismissed(conn, seeded, person["email"])
    row = await _request(conn, seeded, person)
    row = await service.transition(
        conn, row, to="collating", reason=None, role=DPO, actor_id=_dpo(seeded)
    )
    with pytest.raises(ValidationFailed) as refused:
        await service.respond(
            conn, row, outcome="complete", response_text="Done.", role=DPO, actor_id=_dpo(seeded)
        )
    assert refused.value.code == "response_partial_required"
    assert "1 report(s)" in refused.value.message and mine not in refused.value.message

    await public_reports.erase(conn, row, role=DPO, actor_id=_dpo(seeded))
    closed = await service.respond(
        conn, row, outcome="complete", response_text="Done.", role=DPO, actor_id=_dpo(seeded)
    )
    assert closed["outcome"] == "complete"
    [mail] = [a for a in sent if a[0] == "send_rights_response"]
    digest = str(mail[5])
    assert mine in digest and "your name and email were erased" in digest
    payload, _, _ = await service.download(conn, closed, actor_id=_dpo(seeded), as_subject=False)
    record = json.loads(payload)
    [entry] = record["execution"]["public_reports"]
    assert entry == {
        "report": mine,
        "done": True,
        "outcome": "Your name and email were erased from it.",
    }
    assert record["execution"]["kept_of_a_report"]


async def test_a_report_dismissed_after_the_erasure_is_found_again(
    conn: Any, seeded: dict[str, Any]
) -> None:
    person = await _person(conn)
    first = await _dismissed(conn, seeded, person["email"])
    row = await _request(conn, seeded, person)
    await public_reports.erase(conn, row, role=DPO, actor_id=_dpo(seeded))
    later = await _dismissed(conn, seeded, person["email"])
    found = await public_reports.found(conn, row)
    assert _found(found) == {later}
    assert {str(r["reference"]) for r in found["erased"]} == {first}
    blocked = execution.complete_blocked_by(
        "erasure", [], [], reports=found["open"] + found["erased"]
    )
    assert blocked is not None and "1 report(s)" in blocked


async def test_an_erased_reporter_is_not_found_by_a_later_request(
    conn: Any, seeded: dict[str, Any]
) -> None:
    person = await _person(conn)
    mine = await _dismissed(conn, seeded, person["email"])
    await public_reports.erase(
        conn, await _request(conn, seeded, person), role=DPO, actor_id=_dpo(seeded)
    )
    later = await public_reports.found(conn, await _request(conn, seeded, person, "access"))
    assert mine not in _found(later) and later["erased"] == []


async def test_the_other_office_still_reads_the_row_without_the_name(
    conn: Any, seeded: dict[str, Any]
) -> None:
    person = await _person(conn)
    mine = await _dismissed(conn, seeded, person["email"])
    await public_reports.erase(
        conn, await _request(conn, seeded, person), role=DPO, actor_id=_dpo(seeded)
    )
    [listed] = [r for r in await intake.dismissed(conn) if r["reference"] == mine]
    assert listed["reporter_name"] is None and listed["reporter_email"] is None
    assert listed["reporter_erased_at"] is not None
    assert plain(listed["dismissal_reason"]) == "Not a breach of ours"
    assert plain(listed["dismissed_by_name"]) == "Test dpo"
    assert "reporter_erased_request_id" not in listed and "reporter_erased_by" not in listed


async def test_an_administrator_on_a_request_about_the_office_sees_none_and_cannot_erase(
    conn: Any, seeded: dict[str, Any]
) -> None:
    person = await _person(conn)
    mine = await _dismissed(conn, seeded, person["email"])
    row = await _request(conn, seeded, person)
    await conn.execute(
        "UPDATE rights_request SET about_dpo = true WHERE request_id = %s",
        (int(row["request_id"]),),
    )
    admin = int(seeded["users"]["admin"]["id"])
    row = await service.require(conn, str(row["request_uuid"]), role=Role.ADMIN, user_id=admin)
    assert await public_reports.view(conn, row, role=Role.ADMIN) is None
    detail = await rights_router._detail(conn, row, SimpleNamespace(role=Role.ADMIN, user_id=admin))
    assert detail["public_reports"] is None
    assert mine not in str(detail["complete_blocked_by"]), "a count, never a number"
    with pytest.raises(NotFound):
        await public_reports.erase(conn, row, role=Role.ADMIN, actor_id=admin)
    assert (await _report_row(conn, mine))["reporter_email"] is not None


async def test_a_request_with_no_account_is_answered_by_mail_with_its_reports(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, sent: Any
) -> None:
    """No account to download a file from, so the mail to the address the
    reports came from lists them, by number, dates and title."""
    email = _address()
    mine = await _dismissed(conn, seeded, email)
    row = await _from_the_form(conn, seeded, redis_conn, email)
    row = await _start(conn, seeded, await _verified_by_hand(conn, seeded, row))
    await public_reports.erase(conn, row, role=DPO, actor_id=_dpo(seeded))
    row = await service.transition(
        conn,
        await service.reload(conn, row),
        to="collating",
        reason=None,
        role=DPO,
        actor_id=_dpo(seeded),
    )
    await service.respond(
        conn, row, outcome="complete", response_text="Done.", role=DPO, actor_id=_dpo(seeded)
    )
    [mail] = [a for a in sent if a[0] == "send_rights_response"]
    assert plain(mail[1]) == email
    digest = str(mail[5])
    assert digest.startswith("REPORTS YOU SENT THROUGH THE PUBLIC LINK")
    assert mine in digest and "your name and email were erased" in digest
    assert "@" not in digest and "Asha" not in digest
    assert digest.endswith(execution.KEPT_OF_A_REPORT)
