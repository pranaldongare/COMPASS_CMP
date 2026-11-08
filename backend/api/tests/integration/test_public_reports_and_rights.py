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
from cmp.core.config import settings
from cmp.core.errors import BadRequest, CmpError, Conflict, NotFound, ValidationFailed
from cmp.core.pagination import PageRequest
from cmp.core.permissions import Role
from cmp.core.security import new_token, token_fingerprint
from cmp.db.repositories import audit as audit_repo
from cmp.db.repositories import rights as rights_repo
from cmp.db.repositories import users as user_repo
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
    conn: Any,
    *,
    email: str | None = None,
    secondary: str | None = None,
    proved: bool = False,
    email_proved: bool = True,
    mobile_proved: bool = False,
) -> dict[str, Any]:
    """A data principal of the test's own whose email a code came back from,
    with a second email, proved or not. `email_proved=False` leaves the email
    as somebody typed it: with `mobile_proved`, the shape of a nominee's
    account; without, of a changed number or an older account."""
    email = email or _address("principal")
    mobile = f"+9196{uuid.uuid4().int % 10**8:08d}"
    now = datetime.now(UTC)
    row = await fetch_one(
        conn,
        """INSERT INTO auth_user (full_name, email, email_hash, mobile, mobile_hash, role,
                                  status, minor_until, secondary_email, secondary_email_hash,
                                  secondary_email_verified_at, email_verified_at,
                                  mobile_verified_at)
           VALUES ('Asha Rao', %s, %s, %s, %s, 'data_subject', 'active', DATE '2008-05-17',
                   %s, %s, %s, %s, %s)
           RETURNING id, uuid""",
        (
            email,
            hashed("email", email),
            mobile,
            hashed("mobile", mobile),
            secondary,
            hashed("email", secondary),
            now if proved else None,
            now if email_proved else None,
            now if mobile_proved else None,
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


async def test_an_email_only_the_mobile_s_proof_stands_behind_finds_nothing(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """A nominee's account carries the email the principal typed and proves the
    mobile alone, so its email may be a stranger's who sent a report. That
    report is not this account's to read or to erase."""
    stranger = _address("stranger")
    theirs = await _dismissed(conn, seeded, stranger)
    before = await _report_row(conn, theirs)
    person = await _person(conn, email=stranger, email_proved=False, mobile_proved=True)

    access = await _request(conn, seeded, person, "access")
    assert await public_reports.address_hashes(conn, access) == []
    assert theirs not in _found(await public_reports.found(conn, access))
    built = await package.build_response(
        conn, access, holders=[], response_text="Our answer.", generated_at=datetime.now(UTC)
    )
    assert built["reports_from_the_public_link"] == []
    assert built["summary"]["reports_from_the_public_link"] == 0

    erasure = await _request(conn, seeded, person)
    with pytest.raises(Conflict) as refused:
        await public_reports.erase(conn, erasure, role=DPO, actor_id=_dpo(seeded))
    assert refused.value.code == "no_proved_email"
    assert await _report_row(conn, theirs) == before, "nothing blanked"


async def test_neither_medium_stamped_finds_nothing_by_the_email(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """No stamp on either medium is not read as an account older than the
    stamps: the email has never answered a code, so it is nobody's yet. An
    older account counts from the next code to it."""
    person = await _person(conn, email_proved=False, mobile_proved=False)
    mine = await _dismissed(conn, seeded, person["email"])
    access = await _request(conn, seeded, person, "access")
    assert await public_reports.address_hashes(conn, access) == []
    assert mine not in _found(await public_reports.found(conn, access))


async def test_a_number_changed_and_not_yet_confirmed_does_not_make_the_email_count(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """A nominee's account (the email typed by the principal, the mobile
    proved) whose holder changes the number: the new one is unconfirmed, so
    neither medium is stamped, and that must not bring the email back."""
    stranger = _address("stranger")
    theirs = await _dismissed(conn, seeded, stranger)
    person = await _person(conn, email=stranger, email_proved=False, mobile_proved=True)
    # What PATCH /me {mobile} does: the new number is unconfirmed.
    after = await user_repo.update_profile(
        conn, person["id"], mobile=f"+9197{uuid.uuid4().int % 10**8:08d}"
    )
    assert after["mobile_verified_at"] is None and after["email_verified_at"] is None
    access = await _request(conn, seeded, person, "access")
    assert await public_reports.address_hashes(conn, access) == []
    assert theirs not in _found(await public_reports.found(conn, access))
    erasure = await _request(conn, seeded, person)
    before = await _report_row(conn, theirs)
    with pytest.raises(Conflict):
        await public_reports.erase(conn, erasure, role=DPO, actor_id=_dpo(seeded))
    assert await _report_row(conn, theirs) == before, "nothing blanked"


async def test_a_member_of_staff_signed_in_by_mobile_still_finds_their_own_report(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A provisioned account: the invitation's code to the work email set the
    first password, which proves that mailbox. Signed in to the portal by a
    code to the mobile, as ADR 0013 lets a member of staff act as a data
    principal, the email still finds the report they sent from it."""
    from cmp.auth.authentication import service as auth_service
    from cmp.core.security import hash_password, new_token
    from cmp.tasks import dispatch as dispatch_mod

    queued: list[tuple[str, tuple[Any, ...]]] = []

    def capture(task: Any, *args: Any, **kwargs: Any) -> str:
        queued.append((task.name, args))
        return "queued-in-a-test"

    monkeypatch.setattr(dispatch_mod, "dispatch_optional", capture)
    monkeypatch.setattr(dispatch_mod, "dispatch_required", capture)
    email, mobile = _address("staff"), f"+9197{uuid.uuid4().int % 10**8:08d}"
    staff = await user_repo.create(
        conn,
        full_name="Ravi Iyer",
        email=email,
        role=Role.RND_USER.value,
        status="pending",
        password_hash=hash_password(new_token(32)),
        office="rnd",
    )
    await auth_service.invite_staff(conn, user=staff)
    [invitation] = [a for n, a in queued if n == "cmp.notifications.send_staff_invitation"]
    await auth_service.confirm_password_reset(
        conn, email=email, code=invitation[4], new_password="a-well-chosen-passphrase-2026"
    )
    mine = await _dismissed(conn, seeded, email)

    await user_repo.update_profile(conn, int(staff["id"]), mobile=mobile)
    await auth_service.request_subject_otp(conn, contact=mobile)
    [login] = [a for n, a in queued if n == "cmp.notifications.send_login_code"]
    await auth_service.verify_subject_otp(
        conn, contact=mobile, code=login[2], ip_address="127.0.0.1", user_agent="test"
    )
    after = await user_repo.by_id(conn, int(staff["id"]))
    assert after is not None and after["mobile_verified_at"] is not None

    row = await _request(conn, seeded, {"id": int(staff["id"]), "email": email}, "access")
    assert mine in _found(await public_reports.found(conn, row))


async def test_a_pending_account_carrying_somebody_s_address_finds_none_of_their_reports(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, sent: Any
) -> None:
    """A sign-up started with one's own mobile and a stranger's address, and
    never finished: neither medium stamped. A request attached to it by the
    mobile, verified by hand, is not the stranger's to read or erase."""
    stranger = _address("stranger")
    theirs = await _dismissed(conn, seeded, stranger)
    before = await _report_row(conn, theirs)
    mobile = f"+9197{uuid.uuid4().int % 10**8:08d}"
    pending = await user_repo.create(
        conn,
        full_name="Mallory",
        email=stranger,
        mobile=mobile,
        role="data_subject",
        person_type="external",
        status="pending",
    )
    row = await _from_the_form(conn, seeded, redis_conn, mobile)
    assert row["subject_user_id"] == pending["id"]
    row = await _start(conn, seeded, await _verified_by_hand(conn, seeded, row))
    assert await public_reports.address_hashes(conn, row) == []
    shown = await public_reports.view(conn, row, role=DPO)
    assert shown is not None and shown["items"] == []
    assert shown["not_looked_because"] == public_reports.NO_PROVED_EMAIL
    with pytest.raises(Conflict) as refused:
        await public_reports.erase(conn, row, role=DPO, actor_id=_dpo(seeded))
    assert refused.value.code == "no_proved_email"
    assert await _report_row(conn, theirs) == before, "nothing blanked"


async def test_the_owner_s_own_coded_request_through_that_account_finds_nothing_either(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, sent: Any
) -> None:
    """The owner of the address asks from the form. `users.by_contact` attaches
    the request to the pending account and the code goes to the owner, who
    answers it. That proves the request, and stamps nothing on an account
    whose sign-up is unfinished, so the account's email still counts for
    nobody and the reports stay with the owner."""
    owner = _address("owner")
    theirs = await _dismissed(conn, seeded, owner)
    pending = await user_repo.create(
        conn,
        full_name="Mallory",
        email=owner,
        mobile=f"+9197{uuid.uuid4().int % 10**8:08d}",
        role="data_subject",
        person_type="external",
        status="pending",
    )
    await _unthrottle(redis_conn, owner)
    made = await service.submit_public(
        conn,
        request_type="access",
        contact=owner,
        name=None,
        request_text="What do you hold about me?",
        ip_address="127.0.0.1",
    )
    [code] = [a[2] for a in sent if a[0] == "send_rights_verification_code"]
    await service.verify_public_code(conn, reference=made["reference"], code=code)
    row = await service.require(
        conn, await _request_uuid(conn, made["reference"]), role=DPO, user_id=_dpo(seeded)
    )
    assert row["subject_user_id"] == pending["id"] and row["verification_status"] == "verified"
    still = await user_repo.by_id(conn, int(pending["id"]))
    assert still is not None and still["email_verified_at"] is None
    found = await public_reports.found(conn, row)
    assert theirs not in _found(found)
    assert found["not_looked_because"] == public_reports.NO_PROVED_EMAIL


async def test_the_owner_s_answered_code_does_not_hand_their_reports_to_the_account(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, sent: Any
) -> None:
    """An active account carries the owner's address as somebody else typed it
    (a nominee's: the mobile proved, the email not). The owner asks from the
    form, `users.by_contact` attaches the request to that account, and the
    owner answers the code. That verifies the owner's request and stamps
    nothing, so the account holder's own request afterwards still finds none
    of the owner's reports."""
    owner = _address("owner")
    theirs = await _dismissed(conn, seeded, owner)
    holder = await _person(conn, email=owner, email_proved=False, mobile_proved=True)
    await _unthrottle(redis_conn, owner)
    made = await service.submit_public(
        conn,
        request_type="access",
        contact=owner,
        name=None,
        request_text="What do you hold about me?",
        ip_address="127.0.0.1",
    )
    [code] = [a[2] for a in sent if a[0] == "send_rights_verification_code"]
    await service.verify_public_code(conn, reference=made["reference"], code=code)
    asked = await service.require(
        conn, await _request_uuid(conn, made["reference"]), role=DPO, user_id=_dpo(seeded)
    )
    assert asked["subject_user_id"] == holder["id"] and asked["verification_status"] == "verified"
    still = await user_repo.by_id(conn, int(holder["id"]))
    assert still is not None and still["email_verified_at"] is None

    theirs_now = await _request(conn, seeded, holder, "access")
    assert await public_reports.address_hashes(conn, theirs_now) == []
    assert theirs not in _found(await public_reports.found(conn, theirs_now))


async def test_the_owner_s_accepted_nomination_does_not_hand_their_reports_to_the_account(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, sent: Any
) -> None:
    """The same account, carrying the owner's address unproved. Somebody else
    nominates the owner by that address and a mobile no account holds, and
    the owner accepts with a code to the address. `users.by_contact` finds
    the account by the address and the nomination is linked to it; nothing is
    stamped, so the account's own request still finds none of the owner's
    reports."""
    owner = _address("owner")
    theirs = await _dismissed(conn, seeded, owner)
    holder = await _person(conn, email=owner, email_proved=False, mobile_proved=True)
    nomination = await service.nominate(
        conn,
        principal_user_id=seeded["subject"]["id"],
        nominee_name="The Owner",
        nominee_mobile=f"+9197{uuid.uuid4().int % 10**8:08d}",
        nominee_email=owner,
        rights=["access"],
    )
    raw = new_token()
    await conn.execute(
        "UPDATE nomination SET accept_token_hash = %s WHERE nomination_id = %s",
        (token_fingerprint(raw), nomination["nomination_id"]),
    )
    await service.send_nomination_code(conn, raw, medium="email")
    [(_task, to, code)] = [a for a in sent if a[0] == "send_nomination_code"]
    assert to == owner
    await service.accept_nomination(conn, raw, code=str(code))
    linked = await rights_repo.nomination_by_uuid(conn, str(nomination["nomination_uuid"]))
    assert linked is not None and linked["nominee_user_id"] == holder["id"]
    still = await user_repo.by_id(conn, int(holder["id"]))
    assert still is not None and still["email_verified_at"] is None

    mine = await _request(conn, seeded, holder, "access")
    assert await public_reports.address_hashes(conn, mine) == []
    assert theirs not in _found(await public_reports.found(conn, mine))


async def test_a_request_with_no_proved_email_is_told_nothing_was_looked_for(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """The card would otherwise say no report carries the requester's email,
    when no email was searched for. Nothing is held back for it: complete is
    not blocked by reports nobody looked for, and the answer names none."""
    person = await _person(conn, email_proved=False, mobile_proved=True)
    await _dismissed(conn, seeded, person["email"])
    for kind in ("access", "erasure"):
        row = await _request(conn, seeded, person, kind)
        found = await public_reports.found(conn, row)
        assert found["looked"] is False and found["unavailable"] is False
        assert found["not_looked_because"] == public_reports.NO_PROVED_EMAIL
        shown = await public_reports.view(conn, row, role=DPO)
        assert shown is not None
        assert (shown["looked"], shown["items"], shown["may_erase"]) == (False, [], False)
        assert shown["erase_blocked_by"] == public_reports.NO_PROVED_EMAIL
        detail = await rights_router._detail(
            conn, row, SimpleNamespace(role=DPO, user_id=_dpo(seeded))
        )
        assert detail["public_reports"]["not_looked_because"] == public_reports.NO_PROVED_EMAIL
        blocked = str(detail["complete_blocked_by"] or "")
        assert "public link" not in blocked and "could not be checked" not in blocked
        built = await package.build_response(
            conn, row, holders=[], response_text="Our answer.", generated_at=datetime.now(UTC)
        )
        assert built["reports_from_the_public_link"] == []
        assert "REPORTS YOU SENT" not in package.digest_text(built)
    with pytest.raises(Conflict) as refused:
        await public_reports.erase(conn, row, role=DPO, actor_id=_dpo(seeded))
    assert refused.value.code == "no_proved_email"
    assert refused.value.message == public_reports.NO_PROVED_EMAIL


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


async def test_the_neutral_reply_says_the_code_goes_to_the_contact_held(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, sent: Any
) -> None:
    """Asked by an account's mobile, the code goes to its email: the reply says
    it goes to the contact held for them, which is true for everybody, and is
    the same for somebody nobody holds."""
    person = await _person(conn, mobile_proved=True)
    mobile = plain(
        (await fetch_one(conn, "SELECT mobile FROM auth_user WHERE id = %s", (person["id"],)))[
            "mobile"
        ]
    )
    replies = []
    for contact in (mobile, _address("stranger")):
        await _unthrottle(redis_conn, contact)
        made = await service.submit_public(
            conn,
            request_type="access",
            contact=contact,
            name=None,
            request_text="What do you hold about me?",
            ip_address="127.0.0.1",
        )
        replies.append(made["message"])
    assert replies[0] == replies[1] == service.NEUTRAL_MESSAGE
    assert "a verification code has been sent to the contact we hold for you" in replies[0]
    [code] = [a for a in sent if a[0] == "send_rights_verification_code"]
    assert plain(code[1]) == person["email"], "not to the mobile typed"


async def test_a_dismissed_reporter_and_a_stranger_fail_verification_alike(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, sent: Any
) -> None:
    """Five wrong codes, and a sixth, answer the same for a contact a code was
    sent to and for one nobody holds: otherwise the tries would say that an
    address sent a report an office dismissed. The code is spent with its
    budget, so guessing stays bounded."""
    email = _address()
    await _dismissed(conn, seeded, email)
    reporter = await _from_the_form(conn, seeded, redis_conn, email)
    [code] = [a[2] for a in sent if a[0] == "send_rights_verification_code"]
    stranger = await _from_the_form(conn, seeded, redis_conn, _address("stranger"))
    wrong = "111111" if code == "000000" else "000000"
    seen = []
    for row in (reporter, stranger):
        out = []
        for attempt in ("12345", *[wrong] * (settings.otp_max_verify_attempts + 1)):
            try:
                await service.verify_public_code(conn, reference=row["reference"], code=attempt)
            except CmpError as refused:
                out.append(
                    (type(refused).__name__, refused.status_code, refused.code, refused.message)
                )
        seen.append(out)
    assert seen[0] == seen[1]
    assert set(seen[0]) == {("BadRequest", 400, "otp_invalid", "Invalid or expired code")}
    with pytest.raises(BadRequest):
        await service.verify_public_code(conn, reference=reporter["reference"], code=code)


async def test_a_mobile_contact_finds_nothing_and_says_nothing_was_looked_for(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, sent: Any
) -> None:
    row = await _from_the_form(conn, seeded, redis_conn, f"+9195{uuid.uuid4().int % 10**8:08d}")
    assert row["subject_user_id"] is None
    row = await _verified_by_hand(conn, seeded, row)
    found = await public_reports.found(conn, row)
    assert found["looked"] is False and found["open"] == []
    assert found["not_looked_because"] == public_reports.NO_PROVED_EMAIL
    assert found["unavailable"] is False


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


# ------------------------------------------------------- a code's channel
async def _channel(conn: Any, seeded: dict[str, Any], row: dict[str, Any], role: Role = DPO) -> Any:
    who = seeded["users"]["admin" if role is Role.ADMIN else "dpo"]["id"]
    detail = await rights_router._detail(conn, row, SimpleNamespace(role=role, user_id=who))
    return detail["code_channel"]


async def test_the_page_says_whether_a_code_has_somewhere_to_go(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, sent: Any
) -> None:
    """The console offers Send a code on it: an account's channel, the address
    a dismissed report came from, or nothing held at all."""
    person = await _person(conn)
    theirs = await _from_the_form(conn, seeded, redis_conn, person["email"])
    assert theirs["subject_user_id"] is not None
    assert await _channel(conn, seeded, theirs) is True

    reporter = _address()
    await _dismissed(conn, seeded, reporter)
    from_a_report = await _from_the_form(conn, seeded, redis_conn, reporter)
    assert from_a_report["subject_user_id"] is None
    assert await _channel(conn, seeded, from_a_report) is True

    nobody = await _from_the_form(conn, seeded, redis_conn, _address("stranger"))
    assert await _channel(conn, seeded, nobody) is False

    detail = await rights_router._detail(
        conn, from_a_report, SimpleNamespace(role=DPO, user_id=_dpo(seeded))
    )
    assert reporter not in json.dumps(detail, default=str), "never the address"


async def test_the_channel_is_asked_only_while_identity_waits_and_only_by_an_officer(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, sent: Any
) -> None:
    reporter = _address()
    await _dismissed(conn, seeded, reporter)
    row = await _from_the_form(conn, seeded, redis_conn, reporter)
    await conn.execute(
        "UPDATE rights_request SET about_dpo = true WHERE request_id = %s",
        (int(row["request_id"]),),
    )
    row = await service.reload(conn, row)
    assert await _channel(conn, seeded, row, Role.ADMIN) is None, "the register is the officers'"
    assert await _channel(conn, seeded, row) is True
    other = await _from_the_form(conn, seeded, redis_conn, reporter)
    verified = await _verified_by_hand(conn, seeded, other)
    assert await _channel(conn, seeded, verified) is None, "nothing waits for a code"


async def test_the_administrator_learns_nothing_of_the_register_from_send_a_code(
    conn: Any, seeded: dict[str, Any], sent: Any
) -> None:
    """On a request about the office with no account, the administrator is
    refused alike whether the contact sent a dismissed report or not, and no
    code goes to the reporter: code_channel is null for them for that reason."""
    admin = int(seeded["users"]["admin"]["id"])
    reporter = _address()
    await _dismissed(conn, seeded, reporter)
    outcomes = []
    for contact in (reporter, _address("stranger")):
        row = await service.create(
            conn,
            request_type="access",
            channel="staff_logged",
            request_text="Logged from an email",
            submitted_contact=contact,
            submitted_name=None,
            subject_user_id=None,
            actor_id=admin,
            about_dpo=True,
        )
        try:
            await service.send_verification_code(conn, row, role=Role.ADMIN, actor_id=admin)
            outcomes.append(("sent",))
        except CmpError as refused:
            outcomes.append(
                (type(refused).__name__, refused.status_code, refused.code, refused.message)
            )
    assert outcomes[0] == outcomes[1]
    assert outcomes[0] == ("Forbidden", 403, "officers_only", service.OFFICERS_ONLY)
    assert not [a for a in sent if a[0] == "send_rights_verification_code"]


async def test_nor_from_confirm_and_the_reporter_s_code_survives_their_tries(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, sent: Any
) -> None:
    """Five wrong codes would spend a reporter's code and say so, where a
    stranger's request has none to spend. The administrator is refused before
    any code is checked, so the reporter's still verifies."""
    admin = int(seeded["users"]["admin"]["id"])
    reporter = _address()
    await _dismissed(conn, seeded, reporter)
    from_a_report = await _from_the_form(conn, seeded, redis_conn, reporter)
    [code] = [a[2] for a in sent if a[0] == "send_rights_verification_code"]
    nobody = await _from_the_form(conn, seeded, redis_conn, _address("stranger"))
    wrong = "111111" if code == "000000" else "000000"
    seen = []
    for row in (from_a_report, nobody):
        await conn.execute(
            "UPDATE rights_request SET about_dpo = true WHERE request_id = %s",
            (int(row["request_id"]),),
        )
        row = await service.reload(conn, row)
        out = []
        for _ in range(settings.otp_max_verify_attempts + 1):
            try:
                await service.confirm_verification_code(
                    conn, row, code=wrong, role=Role.ADMIN, actor_id=admin
                )
            except CmpError as refused:
                out.append((type(refused).__name__, refused.code))
        seen.append(out)
    assert seen[0] == seen[1] == [("Forbidden", "officers_only")] * len(seen[0])
    row = await service.reload(conn, from_a_report)
    row = await service.confirm_verification_code(
        conn, row, code=code, role=DPO, actor_id=_dpo(seeded)
    )
    assert row["verification_status"] == "verified"


async def test_an_officer_still_sends_the_reporter_a_code_and_is_told_of_a_stranger(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, sent: Any
) -> None:
    reporter = _address()
    await _dismissed(conn, seeded, reporter)
    from_a_report = await _from_the_form(conn, seeded, redis_conn, reporter)
    nobody = await _from_the_form(conn, seeded, redis_conn, _address("stranger"))
    sent.clear()
    for role in (DPO, Role.LEGAL):
        await service.send_verification_code(conn, from_a_report, role=role, actor_id=_dpo(seeded))
        [code] = [a for a in sent if a[0] == "send_rights_verification_code"]
        assert plain(code[1]) == reporter
        sent.clear()
    with pytest.raises(ValidationFailed) as refused:
        await service.send_verification_code(conn, nobody, role=DPO, actor_id=_dpo(seeded))
    assert "matches nobody" in refused.value.message


async def test_a_key_service_down_leaves_the_channel_unknown_and_the_page_open(
    conn: Any,
    seeded: dict[str, Any],
    redis_conn: Any,
    sent: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reporter = _address()
    await _dismissed(conn, seeded, reporter)
    row = await _from_the_form(conn, seeded, redis_conn, reporter)

    async def down(*_: Any) -> Any:
        raise DkmsUnavailable("the key service is down")

    logged: list[tuple[str, dict[str, Any]]] = []

    class Log:
        def warning(self, event: str, **fields: Any) -> None:
            logged.append((event, fields))

    monkeypatch.setattr(public_reports, "unseal_value", down)
    monkeypatch.setattr(service, "log", Log())
    assert await _channel(conn, seeded, row) is None
    assert logged == [("rights.code_channel_unknown", {"reference": row["reference"]})]


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


async def _held_without_an_account(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, email: str, person_uuid: str
) -> None:
    """A report from this address, a hold on the account it is on, and an
    erasure from the public form, which opens it with no account: the hold
    stops it all the same."""
    mine = await _dismissed(conn, seeded, email)
    await holds.place(
        conn,
        asset_uuid=None,
        subject_uuid=person_uuid,
        reason="Evidence in a live matter",
        actor_id=_dpo(seeded),
    )
    row = await _from_the_form(conn, seeded, redis_conn, email)
    assert row["subject_user_id"] is None, "the form gives this request no account"
    row = await _start(conn, seeded, await _verified_by_hand(conn, seeded, row))
    shown = await public_reports.view(conn, row, role=DPO)
    assert shown is not None and mine in {i["reference"] for i in shown["items"]}
    assert shown["may_erase"] is False and shown["erase_blocked_by"] == public_reports.HELD
    with pytest.raises(Conflict) as refused:
        await public_reports.erase(conn, row, role=DPO, actor_id=_dpo(seeded))
    assert refused.value.code == "legal_hold"
    assert (await _report_row(conn, mine))["reporter_email"] is not None


async def test_a_hold_on_the_staff_account_a_contact_is_stops_a_form_erasure(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, sent: Any
) -> None:
    staff = seeded["users"]["dco"]
    await _held_without_an_account(conn, seeded, redis_conn, "dco@test.local", str(staff["uuid"]))


async def test_a_hold_on_whoever_typed_the_address_as_a_second_email_stops_it_too(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, sent: Any
) -> None:
    """An unproved second email signs nobody in, so the form takes it as no
    account; a hold on the account that claims it is still reason to stop."""
    second = _address("second")
    person = await _person(conn, secondary=second, proved=False)
    await _held_without_an_account(conn, seeded, redis_conn, second, person["uuid"])


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
    # Beside what the audit adds to every row: its chain, the request's origin,
    # and the office whose record it is - the rights request's.
    added = {"_hash", "_prev", "ip", "request_id", "office"}
    said = {k: v for k, v in detail.items() if k not in added}
    assert said == {"reference": row["reference"], "incident_reference": mine}
    assert detail["office"] == "rnd"
    text = json.dumps(detail)
    assert "@" not in text and "Asha" not in text
    trail = await audit_repo.for_reference(conn, str(row["reference"]))
    erased = [e for e in trail if e["event_type"] == "incident_report.reporter_erased"]
    assert erased and erased[0]["entity_type"] == "incident_report"
    assert audit_repo.visible_to_subject(erased) == erased, "what was done with her name"
    feed = await audit_repo.for_subject(conn, person["id"])
    assert "incident_report.reporter_erased" in {e["event_type"] for e in feed}


async def test_the_erasure_is_on_its_own_office_s_trail_and_not_the_other_s(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """The row names the request and who acted under it, and the request is
    one office's: the other office's trail must not carry it."""
    person = await _person(conn)
    mine = await _dismissed(conn, seeded, person["email"])
    row = await _request(conn, seeded, person)  # in the DPO's office
    await public_reports.erase(conn, row, role=DPO, actor_id=_dpo(seeded))

    async def read_by(office: str) -> list[dict[str, Any]]:
        items, _, _ = await audit_repo.search(
            conn,
            PageRequest(limit=50, cursor=None, sort_field="occurred_at", descending=True),
            audit_repo.AuditFilters(
                office=office, event_type="incident_report.reporter_erased", q=mine
            ),
        )
        return [i for i in items if (i.get("detail") or {}).get("incident_reference") == mine]

    assert await read_by("hr") == [], "the Legal office's trail does not carry it"
    [own] = await read_by("rnd")
    assert own["detail"].get("office") == "rnd"


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
    said = str(detail["complete_blocked_by"])
    assert mine not in said, "a count, never a number"
    assert "Holders tab" not in said, "no card of theirs to erase from"
    assert "Only the DPO or the Legal office can take them off" in said and "partial" in said
    officer = await rights_router._detail(
        conn, row, SimpleNamespace(role=DPO, user_id=_dpo(seeded))
    )
    assert "Erase them from the Holders tab" in str(officer["complete_blocked_by"])
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


def _rendered(mail: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """The response the task would send for these queued arguments, as each
    channel's default words render it."""
    from cmp.core.messages import Message
    from cmp.infrastructure import messaging
    from cmp.tasks.notifications import rights as rights_tasks

    given: dict[str, Any] = {}

    def deliver(key: Any, *, to: str, **variables: Any) -> dict[str, Any]:
        given.update(variables)
        return {}

    monkeypatch.setattr(rights_tasks, "deliver", deliver)
    rights_tasks.send_rights_response.run(*mail[1:])
    return {
        channel: messaging.render(Message.RIGHTS_RESPONSE, channel, given, overrides={})[1]
        for channel in ("email", "sms")
    }


async def test_a_request_with_no_account_is_pointed_at_no_account(
    conn: Any,
    seeded: dict[str, Any],
    redis_conn: Any,
    sent: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """There is none to sign in to, and the portal's list of requests would
    never show it: the message says it is the answer, by mail and by text."""
    email = _address()
    await _dismissed(conn, seeded, email)
    row = await _from_the_form(conn, seeded, redis_conn, email)
    row = await _start(conn, seeded, await _verified_by_hand(conn, seeded, row))
    row = await service.transition(
        conn, row, to="collating", reason=None, role=DPO, actor_id=_dpo(seeded)
    )
    await service.respond(
        conn, row, outcome="partial", response_text="Partly.", role=DPO, actor_id=_dpo(seeded)
    )
    [mail] = [a for a in sent if a[0] == "send_rights_response"]
    assert mail[7] is None, "no account to point at"
    for channel, body in _rendered(mail, monkeypatch).items():
        assert "your account" not in body and "my-requests" not in body, channel
        assert "Sign in" not in body, channel
        assert "this message is our answer" in body, channel


async def test_a_request_with_an_account_is_still_pointed_at_it(
    conn: Any, seeded: dict[str, Any], sent: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    person = await _person(conn)
    row = await _request(conn, seeded, person, "access")
    row = await service.transition(
        conn, row, to="collating", reason=None, role=DPO, actor_id=_dpo(seeded)
    )
    await service.respond(
        conn, row, outcome="complete", response_text="Here.", role=DPO, actor_id=_dpo(seeded)
    )
    [mail] = [a for a in sent if a[0] == "send_rights_response"]
    assert str(mail[7]).endswith("/my-requests")
    for channel, body in _rendered(mail, monkeypatch).items():
        assert "from your account until" in body and "/my-requests" in body, channel


async def test_a_no_account_erasure_answered_partial_says_the_name_is_still_there(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, sent: Any
) -> None:
    """Answered before anybody erased: the mail must not read as though the
    name and email were gone."""
    email = _address()
    mine = await _dismissed(conn, seeded, email)
    row = await _from_the_form(conn, seeded, redis_conn, email)
    row = await _start(conn, seeded, await _verified_by_hand(conn, seeded, row))
    row = await service.transition(
        conn, row, to="collating", reason=None, role=DPO, actor_id=_dpo(seeded)
    )
    await service.respond(
        conn, row, outcome="partial", response_text="Partly.", role=DPO, actor_id=_dpo(seeded)
    )
    [mail] = [a for a in sent if a[0] == "send_rights_response"]
    digest = str(mail[5])
    [line] = [x for x in digest.splitlines() if mine in x]
    assert "not yet erased: it still carries your name and email" in line
    assert "were erased" not in digest
    assert execution.KEPT_OF_A_REPORT not in digest
