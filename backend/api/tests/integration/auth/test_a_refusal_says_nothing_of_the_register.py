"""A code's refusal is the same for a contact the register knows and for a
stranger, on every public route that takes one (2026-11-08).

Asking for a code answers everybody alike, and sends one only where the
register knows the contact. So the refusals had to be alike too, and two of
them were not:

* **A code of the wrong length.** `otp.require` checks the length, but only
  once the lookup has found somebody; a stranger was refused before it. "Invalid
  code" against "Invalid or expired code" told a registered contact apart
  without a message reaching anybody.
* **The fifth wrong code.** It ends in "too many" only where a code was sent,
  that is, only for a registered contact.

Both now answer as a wrong code does. The code is still discarded with its
budget, so guessing stays bounded; the limit per address is the 429 that
remains. The sign-in, the consent link, the password reset, the nominee's
request and the sign-up's confirmation are checked here.

The sign-up's confirmation also signed in, with no code at all, any data
principal whose contacts had all answered once: nothing was left to check,
and the loops that check codes checked none. It now refuses as it refuses an
unknown mobile.

And it still told a known mobile from a stranger, with no limit on asking
(fourth review, 2026-11-08): a code left out for a contact still waiting was a
422 "Enter the code we sent to your ...", before any code was checked, and a
refusal came on the field of the contact waiting - `email_code` when only the
email was. That named an unfinished sign-up, which `/auth/register` answers as
it answers a new one, and every account whose email had not answered. Every
refusal is now the unknown mobile's, on `mobile_code`, and failures count
against the address as at the code sign-in.

Every person and address here is the test's own, and each test fails from an
address of its own, so the budget per address is nobody else's.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

import pytest

from cmp.auth.authentication import otp
from cmp.auth.authentication import service as auth_service
from cmp.core.config import settings
from cmp.core.context import RequestContext, use_context
from cmp.core.errors import BadRequest, CmpError, RateLimited
from cmp.core.security import new_token, token_fingerprint
from cmp.db.repositories import users as user_repo
from cmp.domain.consent import service as consent_service
from cmp.domain.rights import service as rights_service
from cmp.tasks import dispatch as dispatch_mod
from tests.conftest import plain
from tests.integration.test_a_code_proves_where_it_went import (
    _email,
    _mobile,
    _principal,
    _staff,
    _stamps,
)
from tests.integration.test_contacts_mobile_first import _link

pytestmark = pytest.mark.integration

LOGIN = "cmp.notifications.send_login_code"
CONSENT = "cmp.notifications.send_consent_code"
RESET = "cmp.notifications.send_password_reset"

Answer = tuple[str, str | None, str, str | None]


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


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
    """What the rights service would have queued, kept here instead."""
    kept: list[tuple[Any, ...]] = []
    monkeypatch.setattr(rights_service, "_dispatch", lambda *a: kept.append(a))
    return kept


@pytest.fixture
def own_address() -> Iterator[str]:
    """An address nothing else fails from, for the length of the test."""
    address = f"10.77.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}"
    with use_context(RequestContext(request_id=f"refusal-{new_token(4)}", ip_address=address)):
        yield address


def _answer(exc: CmpError) -> Answer:
    return (type(exc).__name__, exc.code, exc.message, exc.field)


def _wrong(code: str | None) -> str:
    """A code of the right length that is not `code`."""
    return f"{(int(code or 0) + 1) % 10**settings.otp_length:0{settings.otp_length}d}"


async def _tries(attempt: Any, code: str | None) -> list[Answer]:
    """What `settings.otp_max_verify_attempts` wrong codes are answered."""
    answers = []
    for _ in range(settings.otp_max_verify_attempts):
        with pytest.raises((BadRequest, RateLimited)) as refused:
            await attempt(_wrong(code))
        answers.append(_answer(refused.value))
    return answers


async def _short(attempt: Any) -> Answer:
    """What a code one digit short is answered (the schema lets 4 to 10 in)."""
    with pytest.raises((BadRequest, RateLimited)) as refused:
        await attempt("1" * (settings.otp_length - 1))
    return _answer(refused.value)


REFUSED: Answer = ("BadRequest", "otp_invalid", "Invalid or expired code", "code")

#: The sign-up's confirmation answers every refusal as an unknown mobile is
#: answered, on the input every caller types.
ON_THE_MOBILE: Answer = ("BadRequest", "otp_invalid", "Invalid or expired code", "mobile_code")


# ------------------------------------------------------------ sign-in by code
class TestTheSignIn:
    @staticmethod
    def _verify(conn: Any, contact: str) -> Any:
        async def attempt(code: str) -> None:
            await auth_service.verify_subject_otp(
                conn, contact=contact, code=code, ip_address="127.0.0.1", user_agent="t"
            )

        return attempt

    async def test_a_code_of_the_wrong_length_answers_a_known_contact_as_a_stranger(
        self, conn: Any, own_address: str
    ) -> None:
        person = await _principal(conn)
        known = await _short(self._verify(conn, plain(person["mobile"])))
        stranger = await _short(self._verify(conn, _mobile()))
        assert known == stranger == REFUSED

    async def test_five_wrong_codes_answer_a_known_contact_as_a_stranger(
        self, conn: Any, own_address: str, queued: Any
    ) -> None:
        """And the code is spent with its budget: the right one is refused
        after, so guessing stays bounded."""
        person = await _principal(conn)
        mobile = plain(person["mobile"])
        await auth_service.request_subject_otp(conn, contact=mobile)
        [code] = [args[2] for name, args in queued if name == LOGIN]
        known = await _tries(self._verify(conn, mobile), code)

        stranger_contact = _mobile()
        await auth_service.request_subject_otp(conn, contact=stranger_contact)
        assert len([1 for name, _ in queued if name == LOGIN]) == 1, "nothing to a stranger"
        stranger = await _tries(self._verify(conn, stranger_contact), None)

        assert known == stranger == [REFUSED] * settings.otp_max_verify_attempts
        with pytest.raises(BadRequest) as spent:
            await self._verify(conn, mobile)(code)
        assert _answer(spent.value) == REFUSED

    async def test_the_limit_per_address_is_still_the_429(
        self, conn: Any, own_address: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "auth_failures_per_address", 2)
        person = await _principal(conn)
        for _ in range(2):
            with pytest.raises(BadRequest):
                await self._verify(conn, plain(person["mobile"]))("123456")
        with pytest.raises(RateLimited) as limited:
            await self._verify(conn, _mobile())("123456")
        assert limited.value.message == "Too many failed attempts. Try again later."


# ------------------------------------------------------------ a consent link
class TestTheConsentLink:
    async def test_five_wrong_codes_and_a_short_one_answer_a_known_contact_as_a_stranger(
        self, conn: Any, seeded: dict[str, Any], own_address: str, queued: Any
    ) -> None:
        token = await _link(conn, seeded)
        person = await _principal(conn)
        mobile = plain(person["mobile"])

        def attempt_for(contact: str) -> Any:
            async def attempt(code: str) -> None:
                await consent_service.verify_contact_code(
                    conn, token=token, contact=contact, code=code
                )

            return attempt

        await consent_service.send_contact_code(conn, token=token, contact=mobile)
        [(_to, code, _project)] = [args for name, args in queued if name == CONSENT]
        known = [await _short(attempt_for(mobile)), *await _tries(attempt_for(mobile), code)]

        stranger_contact = _mobile()
        await consent_service.send_contact_code(conn, token=token, contact=stranger_contact)
        stranger = [
            await _short(attempt_for(stranger_contact)),
            *await _tries(attempt_for(stranger_contact), None),
        ]
        assert known == stranger == [REFUSED] * (settings.otp_max_verify_attempts + 1)
        with pytest.raises(BadRequest):
            await attempt_for(mobile)(code)  # spent with its budget


# --------------------------------------------------------- a password reset
class TestThePasswordReset:
    async def test_five_wrong_codes_and_a_short_one_answer_an_account_as_a_stranger(
        self, conn: Any, own_address: str, queued: Any
    ) -> None:
        staff = await _staff(conn, status="active")
        email = plain(staff["email"])

        def attempt_for(address: str) -> Any:
            async def attempt(code: str) -> None:
                await auth_service.confirm_password_reset(
                    conn, email=address, code=code, new_password="a-fresh-passphrase-2026"
                )

            return attempt

        await auth_service.request_password_reset(conn, email=email)
        [(_uuid, _to, code)] = [args for name, args in queued if name == RESET]
        known = [await _short(attempt_for(email)), *await _tries(attempt_for(email), code)]
        nobody = _email("nobody")
        stranger = [await _short(attempt_for(nobody)), *await _tries(attempt_for(nobody), None)]
        assert known == stranger == [REFUSED] * (settings.otp_max_verify_attempts + 1)


# ---------------------------------------------------------- a nominee's request
class TestTheNomineesRequest:
    async def _active(
        self, conn: Any, seeded: dict[str, Any], sent: list[tuple[Any, ...]]
    ) -> dict[str, Any]:
        """A nomination accepted, as the link accepts one."""
        nomination = await rights_service.nominate(
            conn,
            principal_user_id=seeded["subject"]["id"],
            nominee_name="Ravi Verma",
            nominee_mobile=_mobile(),
            nominee_email=None,
            rights=["access"],
        )
        raw = new_token()
        await conn.execute(
            "UPDATE nomination SET accept_token_hash = %s WHERE nomination_id = %s",
            (token_fingerprint(raw), nomination["nomination_id"]),
        )
        sent.clear()
        await rights_service.send_nomination_code(conn, raw, medium="mobile")
        [code] = [a[2] for a in sent if a[0] == "send_nomination_code"]
        return dict(await rights_service.accept_nomination(conn, raw, code=str(code)))

    @staticmethod
    def _submit(conn: Any, nomination_uuid: str) -> Any:
        async def attempt(code: str) -> None:
            await rights_service.nominee_submit(
                conn,
                nomination_uuid=nomination_uuid,
                code=code,
                request_type="access",
                request_text="The principal's records, please",
                trigger_event="death",
                evidence_ref=None,
                evidence_hash=None,
            )

        return attempt

    async def test_whether_the_contact_matched_is_not_told_by_the_refusals(
        self, conn: Any, seeded: dict[str, Any], own_address: str, sent: Any
    ) -> None:
        """`nominee_start` sends a code only when the contact typed matches the
        one recorded, and says nothing either way. Five wrong codes after it,
        and a short one, are answered the same whether it matched."""
        principal = seeded["subject"]["id"]
        matched = await self._active(conn, seeded, sent)
        ref = str(matched["nomination_uuid"])
        sent.clear()
        await rights_service.nominee_start(
            conn, nomination_uuid=ref, contact=plain(matched["nominee_mobile"])
        )
        [code] = [str(a[2]) for a in sent if a[0] == "send_rights_verification_code"]
        known = [
            await _short(self._submit(conn, ref)),
            *await _tries(self._submit(conn, ref), code),
        ]
        await rights_service.revoke_nomination(
            conn, nomination_uuid=ref, principal_user_id=principal
        )

        unmatched = await self._active(conn, seeded, sent)
        other = str(unmatched["nomination_uuid"])
        sent.clear()
        await rights_service.nominee_start(conn, nomination_uuid=other, contact=_mobile())
        assert [a for a in sent if a[0] == "send_rights_verification_code"] == []
        stranger = [
            await _short(self._submit(conn, other)),
            *await _tries(self._submit(conn, other), None),
        ]
        assert known == stranger == [REFUSED] * (settings.otp_max_verify_attempts + 1)
        nobody = await _short(self._submit(conn, str(uuid.uuid4())))
        assert nobody == REFUSED


# ------------------------------------------------- the sign-up's confirmation
class TestTheSignUpsConfirmation:
    @staticmethod
    async def _confirm(conn: Any, mobile: str, *codes: str | None) -> Answer:
        mobile_code, email_code = (*codes, None, None)[:2]
        # Any refusal, so that a different kind - the 422 a code left out was -
        # is an answer that differs, not an error that escapes.
        with pytest.raises(CmpError) as refused:
            await auth_service.confirm_registration(
                conn,
                mobile=mobile,
                mobile_code=mobile_code,
                email_code=email_code,
                ip_address=None,
                user_agent=None,
            )
        return _answer(refused.value)

    @staticmethod
    async def _codes(person: dict[str, Any], *mediums: str) -> dict[str, str]:
        """The sign-up codes, as `/auth/register` sends them, one per medium."""
        return {
            medium: (await otp.issue(otp.Scope.SUBJECT_REGISTER, f"{person['uuid']}:{medium}")).code
            for medium in mediums
        }

    async def test_a_finished_sign_up_is_not_signed_in_by_its_mobile_alone(
        self, conn: Any, own_address: str
    ) -> None:
        """Every contact on the account has answered once, so nothing was left
        to check: the mobile alone, with no code, made a session. Now it is
        refused as an unknown mobile is, with codes or without."""
        both = await _principal(conn)
        for medium in ("mobile", "email"):
            await user_repo.mark_contact_verified(conn, both["id"], medium)
        mobile_only = await _principal(conn, email=None)
        await user_repo.mark_contact_verified(conn, mobile_only["id"], "mobile")
        unknown = await self._confirm(conn, _mobile())
        assert unknown == ON_THE_MOBILE
        for person in (both, mobile_only):
            mobile = plain(person["mobile"])
            assert await self._confirm(conn, mobile) == unknown
            assert await self._confirm(conn, mobile, "123456", "123456") == unknown
            still = await user_repo.by_id(conn, person["id"])
            assert still is not None and still["status"] == "active"

    async def test_a_wrong_code_a_short_one_and_a_spent_budget_are_one_sentence(
        self, conn: Any, own_address: str, redis_conn: Any
    ) -> None:
        pending = await _principal(conn, status="pending")
        mobile = plain(pending["mobile"])
        code = (await otp.issue(otp.Scope.SUBJECT_REGISTER, f"{pending['uuid']}:mobile")).code
        await otp.issue(otp.Scope.SUBJECT_REGISTER, f"{pending['uuid']}:email")
        stranger = _mobile()
        short = "1" * (settings.otp_length - 1)
        known = [await self._confirm(conn, mobile, short, short)]
        known += [
            await self._confirm(conn, mobile, _wrong(code), "000000")
            for _ in range(settings.otp_max_verify_attempts)
        ]
        theirs = [await self._confirm(conn, stranger, short, short)]
        theirs += [
            await self._confirm(conn, stranger, _wrong(code), "000000")
            for _ in range(settings.otp_max_verify_attempts)
        ]
        assert known == theirs == [ON_THE_MOBILE] * (settings.otp_max_verify_attempts + 1)

    async def test_an_account_with_only_its_email_waiting_answers_as_a_stranger(
        self, conn: Any, own_address: str, redis_conn: Any
    ) -> None:
        """The mobile has answered and the email has not: anybody who signs in
        by mobile, or a sign-up whose mobile a consent link proved. Every
        refusal came on `email_code`, where a stranger's is on `mobile_code`.
        A code of the wrong length, five wrong ones and the right one after
        them are the stranger's answer now, and the account is as it was."""
        active = await _principal(conn)
        await user_repo.mark_contact_verified(conn, active["id"], "mobile")
        pending = await _principal(conn, status="pending")
        await user_repo.mark_contact_verified(conn, pending["id"], "mobile")
        short = "1" * (settings.otp_length - 1)
        stranger = _mobile()
        theirs = [await self._confirm(conn, stranger, "000000", short)]
        theirs += [
            await self._confirm(conn, stranger, "000000", "000000")
            for _ in range(settings.otp_max_verify_attempts + 1)
        ]
        assert theirs == [ON_THE_MOBILE] * (settings.otp_max_verify_attempts + 2)
        for person in (active, pending):
            mobile = plain(person["mobile"])
            code = (await self._codes(person, "email"))["email"]
            known = [await self._confirm(conn, mobile, "000000", short)]
            known += [
                await self._confirm(conn, mobile, "000000", _wrong(code))
                for _ in range(settings.otp_max_verify_attempts)
            ]
            known += [await self._confirm(conn, mobile, "000000", code)]  # spent with its budget
            assert known == theirs
            assert await _stamps(conn, person["id"]) == (False, True, False)
            still = await user_repo.by_id(conn, person["id"])
            assert still is not None and still["status"] == person["status"]

    async def test_a_code_left_out_answers_as_a_stranger(
        self, conn: Any, own_address: str, redis_conn: Any
    ) -> None:
        """A code left out for a contact still waiting was a 422 "Enter the code
        we sent to your ...", answered before any code was checked: with no
        code at all, it named an unfinished sign-up. It is the stranger's
        refusal now, and spends nothing: the codes sent still finish it."""
        pending = await _principal(conn, status="pending")
        codes = await self._codes(pending, "mobile", "email")
        unanswered = await _principal(conn)  # active, and neither contact has answered
        mobile = plain(pending["mobile"])
        stranger = _mobile()
        unknown = await self._confirm(conn, stranger)
        assert unknown == ON_THE_MOBILE
        assert await self._confirm(conn, stranger, codes["mobile"]) == unknown
        assert await self._confirm(conn, mobile) == unknown
        assert await self._confirm(conn, mobile, codes["mobile"]) == unknown
        assert await self._confirm(conn, mobile, None, codes["email"]) == unknown
        assert await self._confirm(conn, plain(unanswered["mobile"])) == unknown
        assert await _stamps(conn, pending["id"]) == (False, False, False)

        result = await auth_service.confirm_registration(
            conn,
            mobile=mobile,
            mobile_code=codes["mobile"],
            email_code=codes["email"],
            ip_address=None,
            user_agent=None,
        )
        assert result["user"]["status"] == "active"

    async def test_a_wrong_email_code_does_not_burn_the_right_mobile_code(
        self, conn: Any, own_address: str, redis_conn: Any
    ) -> None:
        """Every code waiting is checked before any is spent, so the sign-up
        can be tried again; and the right pair still finishes it, with a
        session, and spends both."""
        pending = await _principal(conn, status="pending")
        codes = await self._codes(pending, "mobile", "email")
        mobile = plain(pending["mobile"])
        wrong_email = await self._confirm(conn, mobile, codes["mobile"], _wrong(codes["email"]))
        assert wrong_email == ON_THE_MOBILE
        assert await _stamps(conn, pending["id"]) == (False, False, False)

        result = await auth_service.confirm_registration(
            conn,
            mobile=mobile,
            mobile_code=codes["mobile"],
            email_code=codes["email"],
            ip_address="127.0.0.1",
            user_agent="t",
        )
        assert result["user"]["status"] == "active"
        assert result["token"] and result["session"].mfa_verified
        assert await _stamps(conn, pending["id"]) == (True, True, False)
        again = await self._confirm(conn, mobile, codes["mobile"], codes["email"])
        assert again == ON_THE_MOBILE, "both codes were spent with the sign-up"

    async def test_the_limit_per_address_is_the_only_429_and_is_everybody_s(
        self, conn: Any, own_address: str, redis_conn: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The route had no limit of any kind, so asking it was free. Failures
        now count against the address, a stranger's as a known mobile's, and
        a spent address is refused before anything is looked up: the right
        pair too, and nothing is finished."""
        monkeypatch.setattr(settings, "auth_failures_per_address", 2)
        pending = await _principal(conn, status="pending")
        codes = await self._codes(pending, "mobile", "email")
        mobile = plain(pending["mobile"])
        assert await self._confirm(conn, mobile, _wrong(codes["mobile"]), codes["email"]) == (
            ON_THE_MOBILE
        )
        assert await self._confirm(conn, _mobile(), "123456", "123456") == ON_THE_MOBILE
        spent = ("RateLimited", "rate_limited", "Too many failed attempts. Try again later.", None)
        assert await self._confirm(conn, _mobile(), "123456", "123456") == spent
        assert await self._confirm(conn, mobile, codes["mobile"], codes["email"]) == spent
        assert await _stamps(conn, pending["id"]) == (False, False, False)
