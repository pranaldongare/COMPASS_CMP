"""A contact is stamped proved when a code sent to it comes back, and only
that contact, in every flow that sends an account's contact a code
(2026-11-08).

`public_reports.email_proved` counts an account's email as the holder's only
once it is stamped. A flow that proves a mailbox without stamping it leaves the
holder without their own reports; one that stamps a contact the code never
went to makes an address somebody else typed count. So each place a code to an
account comes back is checked both ways: what it went to is stamped, and
nothing else is. The rights form's code is an exception, and stamps nothing:
it proves the requester holds the address, not that the account's holder does.
A nomination's code is the same on an account that was there already, and
stamps only an account made for whoever accepted.

Every person and address here is the test's own, with a uuid in it: these run
on a database the HTTP suite commits to.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from cmp.auth.authentication import otp
from cmp.auth.authentication import service as auth_service
from cmp.core.config import settings
from cmp.core.errors import BadRequest, RateLimited, ValidationFailed
from cmp.core.permissions import Role
from cmp.core.security import hash_password, new_token, token_fingerprint
from cmp.db.repositories import rights as rights_repo
from cmp.db.repositories import users as user_repo
from cmp.domain.consent import service as consent_service
from cmp.domain.rights import service as rights_service
from cmp.tasks import dispatch as dispatch_mod
from tests.conftest import office_of, plain
from tests.integration.test_contacts_mobile_first import _link
from tests.integration.test_rights_flows import _unthrottle
from tests.integration.test_staff_provisioning import NEW_PASSWORD, only, unthrottle

pytestmark = pytest.mark.integration

INVITATION = "cmp.notifications.send_staff_invitation"
RESET = "cmp.notifications.send_password_reset"
MFA = "cmp.notifications.send_mfa_code"
LOGIN = "cmp.notifications.send_login_code"
CONSENT = "cmp.notifications.send_consent_code"


@pytest.fixture
def queued(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, tuple[Any, ...]]]:
    """Every task the code under test queues, captured instead of sent."""
    kept: list[tuple[str, tuple[Any, ...]]] = []

    def capture(task: Any, *args: Any, **kwargs: Any) -> str:
        kept.append((task.name, args))
        return "queued-in-a-test"

    monkeypatch.setattr(dispatch_mod, "dispatch_optional", capture)
    monkeypatch.setattr(dispatch_mod, "dispatch_required", capture)
    return kept


def _email(tag: str = "proof") -> str:
    return f"{tag}.{uuid.uuid4().hex[:10]}@example.org"


def _mobile() -> str:
    return f"+9193{uuid.uuid4().int % 10**8:08d}"


async def _stamps(conn: Any, user_id: int) -> tuple[bool, bool, bool]:
    """(email, mobile, second email): which carry a stamp."""
    row = await user_repo.by_id(conn, user_id)
    assert row is not None
    return (
        row["email_verified_at"] is not None,
        row["mobile_verified_at"] is not None,
        row["secondary_email_verified_at"] is not None,
    )


async def _staff(conn: Any, *, status: str = "pending") -> dict[str, Any]:
    """A provisioned member of staff with an email and a mobile, neither stamped."""
    return await user_repo.create(
        conn,
        full_name="New Joiner",
        email=_email("staff"),
        mobile=_mobile(),
        role=Role.DCO.value,
        status=status,
        password_hash=hash_password(NEW_PASSWORD),
        office=office_of(Role.DCO.value),
    )


async def _principal(
    conn: Any, *, email: str | None = "", status: str = "active"
) -> dict[str, Any]:
    """A data principal with an email (unless None) and a mobile, neither stamped."""
    return await user_repo.create(
        conn,
        full_name="Asha Rao",
        email=_email("principal") if email == "" else email,
        mobile=_mobile(),
        role=Role.DATA_SUBJECT.value,
        person_type="external",
        status=status,
    )


async def _with_a_proved_second_email(conn: Any, person: dict[str, Any]) -> str:
    second = _email("second")
    await user_repo.set_secondary_email(conn, person["id"], second)
    await user_repo.mark_contact_verified(conn, person["id"], "secondary_email")
    return second


# ------------------------------------------------- a reset or an invitation
class TestAResetOrAnInvitation:
    async def test_the_invitation_s_code_stamps_the_email_and_not_the_mobile(
        self, conn: Any, request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        """The invitation's code goes to the account's email: setting the
        first password with it proves that mailbox, as a sign-in code would."""
        staff = await _staff(conn)
        await auth_service.invite_staff(conn, user=staff)
        _uuid, to, *_rest = only(queued, INVITATION)
        code = only(queued, INVITATION)[4]
        assert plain(to) == plain(staff["email"])
        assert await _stamps(conn, staff["id"]) == (False, False, False)

        await auth_service.confirm_password_reset(
            conn, email=plain(staff["email"]), code=code, new_password=NEW_PASSWORD
        )
        assert await _stamps(conn, staff["id"]) == (True, False, False)

    async def test_a_reset_s_code_stamps_the_email_and_not_the_mobile(
        self, conn: Any, request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        staff = await _staff(conn, status="active")
        email = plain(staff["email"])
        await unthrottle(redis_conn, email)
        await auth_service.request_password_reset(conn, email=email)
        _uuid, to, code = only(queued, RESET)
        assert plain(to) == email

        await auth_service.confirm_password_reset(
            conn, email=email, code=code, new_password=NEW_PASSWORD
        )
        assert await _stamps(conn, staff["id"]) == (True, False, False)

    async def test_a_wrong_code_stamps_nothing(
        self, conn: Any, request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        staff = await _staff(conn)
        await auth_service.invite_staff(conn, user=staff)
        code = only(queued, INVITATION)[4]
        with pytest.raises(BadRequest):
            await auth_service.confirm_password_reset(
                conn,
                email=plain(staff["email"]),
                code="000000" if code != "000000" else "111111",
                new_password=NEW_PASSWORD,
            )
        assert await _stamps(conn, staff["id"]) == (False, False, False)


# ------------------------------------------------------------ staff MFA
class TestTheSecondFactor:
    async def test_it_stamps_the_email_it_went_to_and_not_the_mobile(
        self, conn: Any, request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        staff = await _staff(conn, status="active")
        email = plain(staff["email"])
        await unthrottle(redis_conn, email)
        signed = await auth_service.authenticate(
            conn, login=email, password=NEW_PASSWORD, ip_address="127.0.0.1", user_agent="test"
        )
        assert signed["mfa_required"] is True
        _uuid, to, code = only(queued, MFA)
        assert plain(to) == email, "the second factor goes to the email alone"
        assert await _stamps(conn, staff["id"]) == (False, False, False)

        await auth_service.verify_mfa(
            conn, user_uuid=str(staff["uuid"]), code=code, token=signed["token"]
        )
        assert await _stamps(conn, staff["id"]) == (True, False, False)


# ------------------------------------------------------- sign-in by code
class TestSignInByCode:
    async def test_a_code_to_the_mobile_does_not_answer_for_the_email(
        self, conn: Any, request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        """Typed beside a code that went to the mobile, the account's email is
        refused, and so is not stamped: nothing went to it."""
        person = await _principal(conn)
        email, mobile = plain(person["email"]), plain(person["mobile"])
        await auth_service.request_subject_otp(conn, contact=mobile)
        _uuid, to, code = only(queued, LOGIN)
        assert to == mobile

        with pytest.raises(BadRequest) as refused:
            await auth_service.verify_subject_otp(
                conn, contact=email, code=code, ip_address="127.0.0.1", user_agent="test"
            )
        assert refused.value.code == "otp_invalid"
        assert await _stamps(conn, person["id"]) == (False, False, False)

        await auth_service.verify_subject_otp(
            conn, contact=mobile, code=code, ip_address="127.0.0.1", user_agent="test"
        )
        assert await _stamps(conn, person["id"]) == (False, True, False)

    async def test_a_code_to_the_email_stamps_the_email(
        self, conn: Any, request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        person = await _principal(conn)
        email = plain(person["email"])
        await auth_service.request_subject_otp(conn, contact=email)
        code = only(queued, LOGIN)[2]
        await auth_service.verify_subject_otp(
            conn, contact=email, code=code, ip_address="127.0.0.1", user_agent="test"
        )
        assert await _stamps(conn, person["id"]) == (True, False, False)

    async def test_a_second_email_signs_in_and_stamps_only_itself(
        self, conn: Any, request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        """The code went to the second address. The first, perhaps typed by
        somebody else, has answered nothing."""
        person = await _principal(conn)
        second = await _with_a_proved_second_email(conn, person)
        await auth_service.request_subject_otp(conn, contact=second)
        _uuid, to, code = only(queued, LOGIN)
        assert to == second
        await auth_service.verify_subject_otp(
            conn, contact=second, code=code, ip_address="127.0.0.1", user_agent="test"
        )
        assert await _stamps(conn, person["id"]) == (False, False, True)


# ---------------------------------------------------------- a consent link
class TestAConsentLink:
    async def test_a_second_email_answers_for_itself_and_not_the_first(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, queued: Any
    ) -> None:
        token = await _link(conn, seeded)
        person = await _principal(conn)
        second = await _with_a_proved_second_email(conn, person)
        await consent_service.send_contact_code(conn, token=token, contact=second)
        to, code, _project = only(queued, CONSENT)
        assert to == second
        await consent_service.verify_contact_code(conn, token=token, contact=second, code=code)
        assert await _stamps(conn, person["id"]) == (False, False, True)

    async def test_the_mobile_answers_for_the_mobile(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, queued: Any
    ) -> None:
        token = await _link(conn, seeded)
        person = await _principal(conn)
        mobile = plain(person["mobile"])
        await consent_service.send_contact_code(conn, token=token, contact=mobile)
        code = only(queued, CONSENT)[1]
        await consent_service.verify_contact_code(conn, token=token, contact=mobile, code=code)
        assert await _stamps(conn, person["id"]) == (False, True, False)


# ------------------------------------------------------ the public rights form
@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
    """What the rights service would have queued, kept here instead."""
    kept: list[tuple[Any, ...]] = []
    monkeypatch.setattr(rights_service, "_dispatch", lambda *a: kept.append(a))
    return kept


def _rights_code(sent: list[tuple[Any, ...]]) -> tuple[str, str]:
    """(where it went, the code) of the one rights verification code queued."""
    [(_task, to, code, _reference)] = [a for a in sent if a[0] == "send_rights_verification_code"]
    return plain(to), str(code)


async def _from_the_form(conn: Any, redis_conn: Any, contact: str) -> dict[str, Any]:
    await _unthrottle(redis_conn, contact)
    made = await rights_service.submit_public(
        conn,
        request_type="access",
        contact=contact,
        name="Asha Rao",
        request_text="What do you hold about me?",
        ip_address="127.0.0.1",
    )
    row = await rights_repo.by_reference(conn, made["reference"])
    assert row is not None
    return row


class TestTheRightsForm:
    async def test_a_code_to_the_account_s_email_verifies_the_request_and_stamps_nothing(
        self, conn: Any, request_context: Any, redis_conn: Any, sent: Any
    ) -> None:
        """Asked by the mobile, the code goes to the account's email. Its coming
        back proves the requester holds that address, not that the account's
        holder does: an account can carry an address somebody else typed, and a
        stamp would let its later requests find that address's reports."""
        person = await _principal(conn)
        row = await _from_the_form(conn, redis_conn, plain(person["mobile"]))
        assert row["subject_user_id"] == person["id"]
        to, code = _rights_code(sent)
        assert to == plain(person["email"])

        await rights_service.verify_public_code(conn, reference=row["reference"], code=code)
        assert (await rights_repo.by_reference(conn, row["reference"]))[
            "verification_status"
        ] == "verified"
        assert await _stamps(conn, person["id"]) == (False, False, False)

    async def test_with_no_email_the_mobile_s_code_stamps_nothing(
        self, conn: Any, request_context: Any, redis_conn: Any, sent: Any
    ) -> None:
        """The number can change after the code went out and the code does not
        say which it was, so nothing is stamped rather than a guess."""
        person = await _principal(conn, email=None)
        row = await _from_the_form(conn, redis_conn, plain(person["mobile"]))
        to, code = _rights_code(sent)
        assert to == plain(person["mobile"])
        await rights_service.verify_public_code(conn, reference=row["reference"], code=code)
        assert await _stamps(conn, person["id"]) == (False, False, False)

    async def test_a_data_principal_mid_sign_up_is_not_stamped(
        self, conn: Any, request_context: Any, redis_conn: Any, sent: Any
    ) -> None:
        """A sign-up asks a code of every medium it was given. A stamp from the
        rights form would let it finish on the mobile's code alone, with an
        email somebody else may have typed."""
        person = await _principal(conn, status="pending")
        row = await _from_the_form(conn, redis_conn, plain(person["email"]))
        _to, code = _rights_code(sent)
        await rights_service.verify_public_code(conn, reference=row["reference"], code=code)
        assert await _stamps(conn, person["id"]) == (False, False, False)
        with pytest.raises(ValidationFailed) as asked:
            await auth_service.confirm_registration(
                conn,
                mobile=plain(person["mobile"]),
                mobile_code="123456",
                email_code=None,
                ip_address=None,
                user_agent=None,
            )
        assert asked.value.field == "email_code", "the sign-up still wants the email's code"

    async def test_an_officer_confirming_a_code_read_back_stamps_nothing(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, sent: Any
    ) -> None:
        person = await _principal(conn)
        dpo = int(seeded["users"]["dpo"]["id"])
        row = await rights_service.create(
            conn,
            request_type="access",
            channel="staff_logged",
            request_text="Logged from a call",
            submitted_contact=plain(person["email"]),
            submitted_name="Asha Rao",
            subject_user_id=person["id"],
            actor_id=dpo,
            office="rnd",
        )
        row = await rights_service.send_verification_code(conn, row, role=Role.DPO, actor_id=dpo)
        to, code = _rights_code(sent)
        assert to == plain(person["email"])
        row = await rights_service.confirm_verification_code(
            conn, row, code=code, role=Role.DPO, actor_id=dpo
        )
        assert row["verification_status"] == "verified"
        assert await _stamps(conn, person["id"]) == (False, False, False)


# ------------------------------------------------------- a nomination accepted
class TestANominationAccepted:
    async def _nominated(
        self, conn: Any, seeded: dict[str, Any], *, mobile: str, email: str | None
    ) -> tuple[dict[str, Any], str]:
        """A nomination and the raw token its link carries."""
        nomination = await rights_service.nominate(
            conn,
            principal_user_id=seeded["subject"]["id"],
            nominee_name="Ravi Verma",
            nominee_mobile=mobile,
            nominee_email=email,
            rights=["access"],
        )
        raw = new_token()
        await conn.execute(
            "UPDATE nomination SET accept_token_hash = %s WHERE nomination_id = %s",
            (token_fingerprint(raw), nomination["nomination_id"]),
        )
        return nomination, raw

    async def _accept(
        self,
        conn: Any,
        seeded: dict[str, Any],
        sent: list[tuple[Any, ...]],
        *,
        mobile: str,
        email: str | None,
        medium: str,
    ) -> dict[str, Any]:
        """Nominate, send the code to `medium` the way the link's page does,
        and accept with it."""
        nomination, raw = await self._nominated(conn, seeded, mobile=mobile, email=email)
        await rights_service.send_nomination_code(conn, raw, medium=medium)
        [(_task, _to, code)] = [a for a in sent if a[0] == "send_nomination_code"]
        await rights_service.accept_nomination(conn, raw, code=str(code))
        return nomination

    @staticmethod
    async def _linked_to(conn: Any, nomination: dict[str, Any]) -> int | None:
        row = await rights_repo.nomination_by_uuid(conn, str(nomination["nomination_uuid"]))
        assert row is not None
        return row["nominee_user_id"]

    async def test_an_account_already_holding_the_proven_contact_is_linked_not_stamped(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, sent: Any
    ) -> None:
        """An account carries the recorded email, unproved, and the code went
        to that email and came back. That proves whoever accepted holds the
        address, not that the account `users.by_contact` found is theirs, so
        the account is linked and nothing on it is stamped."""
        person = await _principal(conn)
        nomination = await self._accept(
            conn, seeded, sent, mobile=_mobile(), email=plain(person["email"]), medium="email"
        )
        assert await self._linked_to(conn, nomination) == person["id"]
        assert await _stamps(conn, person["id"]) == (False, False, False)

    async def test_an_address_on_somebody_else_s_account_is_not_stamped_by_its_owner_accepting(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, sent: Any
    ) -> None:
        """A nominee's account: the email typed by a principal, its holder's
        mobile proved. The address's owner is nominated by somebody else and
        accepts with a code to it. The owner's proof is not the holder's."""
        owner = _email("owner")
        holder = await _principal(conn, email=owner)
        await user_repo.mark_contact_verified(conn, holder["id"], "mobile")
        await self._accept(conn, seeded, sent, mobile=_mobile(), email=owner, medium="email")
        assert await _stamps(conn, holder["id"]) == (False, True, False)

    async def test_an_account_found_by_the_proven_mobile_is_not_stamped_either(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, sent: Any
    ) -> None:
        """Nothing on an account that was there already, whichever contact
        found it: its holder proves its contacts by signing in."""
        person = await _principal(conn)
        nomination = await self._accept(
            conn, seeded, sent, mobile=plain(person["mobile"]), email=None, medium="mobile"
        )
        assert await self._linked_to(conn, nomination) == person["id"]
        assert await _stamps(conn, person["id"]) == (False, False, False)

    async def test_a_proven_contact_that_is_not_the_account_s_stamps_nothing_on_it(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, sent: Any
    ) -> None:
        """Linked by the recorded email, proved by the recorded mobile, which is
        not on that account: nothing of the account's answered."""
        person = await _principal(conn)
        await self._accept(
            conn, seeded, sent, mobile=_mobile(), email=plain(person["email"]), medium="mobile"
        )
        assert await _stamps(conn, person["id"]) == (False, False, False)

    async def test_a_second_email_is_not_confirmed_by_a_nomination(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, sent: Any
    ) -> None:
        """Found by its mobile, the account carries the recorded email as a
        second address nobody has confirmed. That is confirmed from the
        account, by its holder, and a nomination's code does not do it."""
        person = await _principal(conn)
        second = _email("second")
        await user_repo.set_secondary_email(conn, person["id"], second)
        await self._accept(
            conn, seeded, sent, mobile=plain(person["mobile"]), email=second, medium="email"
        )
        assert await _stamps(conn, person["id"]) == (False, False, False)

    async def test_an_account_made_for_whoever_accepted_carries_the_contact_proved(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, sent: Any
    ) -> None:
        """No account holds either recorded contact, so one is made for the
        person who answered, with the contact the code went to stamped, and
        the other, which nothing reached, not."""
        for medium, stamps in (("mobile", (False, True, False)), ("email", (True, False, False))):
            mobile = _mobile()
            sent.clear()
            await self._accept(conn, seeded, sent, mobile=mobile, email=_email(), medium=medium)
            made = await user_repo.by_contact(conn, mobile)
            assert made is not None
            assert await _stamps(conn, int(made["id"])) == stamps, medium
            await rights_service.revoke_nomination(
                conn,
                nomination_uuid=str(
                    (await rights_repo.live_nomination_of(conn, seeded["subject"]["id"]))[
                        "nomination_uuid"
                    ]
                ),
                principal_user_id=seeded["subject"]["id"],
            )

    async def test_a_code_proves_only_the_contact_it_was_sent_to(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, sent: Any
    ) -> None:
        """Asked for at the email, then at the mobile: the mobile's code is the
        live one, the email's is refused, and accepting stamps the mobile."""
        mobile, email = _mobile(), _email("nominee")
        _nomination, raw = await self._nominated(conn, seeded, mobile=mobile, email=email)
        await rights_service.send_nomination_code(conn, raw, medium="email")
        await rights_service.send_nomination_code(conn, raw, medium="mobile")
        codes = {plain(a[1]): str(a[2]) for a in sent if a[0] == "send_nomination_code"}
        with pytest.raises(BadRequest) as refused:
            await rights_service.accept_nomination(conn, raw, code=codes[email])
        assert (refused.value.code, refused.value.message) == (
            "otp_invalid",
            "Invalid or expired code",
        )
        await rights_service.accept_nomination(conn, raw, code=codes[mobile])
        made = await user_repo.by_contact(conn, mobile)
        assert made is not None
        assert await _stamps(conn, int(made["id"])) == (False, True, False)

    async def test_codes_asked_at_once_never_stamp_where_the_surviving_code_did_not_go(
        self,
        conn: Any,
        seeded: dict[str, Any],
        request_context: Any,
        redis_conn: Any,
        sent: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Two requests for a code at once, interleaved: the email's code is
        issued, a whole request for the mobile's runs, and only then does the
        email's request finish. The mobile's code is the live one. Recorded
        apart from the code, "email" was the last word on where it went, and
        accepting with the mobile's code stamped an email no code reached."""
        mobile, email = _mobile(), _email("nominee")
        _nomination, raw = await self._nominated(conn, seeded, mobile=mobile, email=email)
        real = otp.issue
        nested: list[bool] = []

        async def then_a_whole_request_for_the_mobile(*args: Any, **kw: Any) -> otp.Issued:
            issued = await real(*args, **kw)
            if not nested:
                nested.append(True)
                await rights_service.send_nomination_code(conn, raw, medium="mobile")
            return issued

        monkeypatch.setattr(otp, "issue", then_a_whole_request_for_the_mobile)
        await rights_service.send_nomination_code(conn, raw, medium="email")
        monkeypatch.setattr(otp, "issue", real)
        assert nested == [True]
        [code] = [a[2] for a in sent if a[0] == "send_nomination_code" and plain(a[1]) == mobile]
        await rights_service.accept_nomination(conn, raw, code=str(code))
        made = await user_repo.by_contact(conn, mobile)
        assert made is not None
        assert await _stamps(conn, int(made["id"])) == (False, True, False)

    async def test_a_wrong_code_costs_one_try_whichever_contact_it_went_to(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, sent: Any
    ) -> None:
        """One code is live, so five wrong ones spend its budget and no more,
        and the answers are the same whether it went to the mobile or the
        email."""
        seen: dict[str, list[tuple[str, str]]] = {}
        for medium in ("mobile", "email"):
            nomination, raw = await self._nominated(
                conn, seeded, mobile=_mobile(), email=_email("nominee")
            )
            sent.clear()
            await rights_service.send_nomination_code(conn, raw, medium=medium)
            [code] = [str(a[2]) for a in sent if a[0] == "send_nomination_code"]
            wrong = f"{(int(code) + 1) % 10**6:06d}"
            answers = []
            for _ in range(settings.otp_max_verify_attempts):
                with pytest.raises((BadRequest, RateLimited)) as refused:
                    await rights_service.accept_nomination(conn, raw, code=wrong)
                answers.append((type(refused.value).__name__, refused.value.code))
            seen[medium] = answers
            with pytest.raises(BadRequest):
                await rights_service.accept_nomination(conn, raw, code=code)  # discarded
            await rights_service.revoke_nomination(
                conn,
                nomination_uuid=str(nomination["nomination_uuid"]),
                principal_user_id=seeded["subject"]["id"],
            )
        assert seen["mobile"] == seen["email"]
        assert [a[0] for a in seen["mobile"]] == ["BadRequest"] * (
            settings.otp_max_verify_attempts - 1
        ) + ["RateLimited"]
