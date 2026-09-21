"""Mobile first: how a data principal and a nominee are reached, since 2026-09-06.

A data principal registers with a mobile and, if she likes, an email; every
medium she gave is authenticated before the account is hers, and later
sign-ins send a code to whichever of the two she chooses. A nominee is named
by mobile with an optional email, and the acceptance link alone no longer
accepts: the nominee proves a recorded contact first.
"""

from __future__ import annotations

from typing import Any

import psycopg
import pytest

from cmp.auth.authentication import otp
from cmp.auth.authentication import service as auth_service
from cmp.core.errors import BadRequest, NotFound, ValidationFailed
from cmp.core.security import new_token, token_fingerprint
from cmp.db.redis import K_RATE
from cmp.db.redis import key as rkey
from cmp.db.repositories import users as user_repo
from cmp.domain.consent import service as consent_service
from cmp.domain.rights import service as rights_service

pytestmark = pytest.mark.integration

MOBILE = "+91 55500 00901"  # typed with spaces; stored without
STORED = "+915550000901"
EMAIL = "priya.new@example.org"


@pytest.fixture(autouse=True)
async def _redis(redis_conn: Any) -> None:
    """Codes and rate limits live in Redis; every test here touches one or both."""


async def _unthrottle(redis_conn: Any, bucket: str, *identities: str) -> None:
    """Clear a per-contact bucket, so a run is not refused by the run before it."""
    for identity in identities:
        await redis_conn.delete(rkey(K_RATE, bucket, identity))


async def _register(
    conn: Any, redis_conn: Any, *, email: str | None = EMAIL, mobile: str = MOBILE
) -> dict[str, Any]:
    await _unthrottle(redis_conn, "subject_register", STORED, *(e for e in (email,) if e))
    await auth_service.register_data_subject(
        conn, full_name="Priya New", mobile=mobile, email=email, dob="1990-04-01"
    )
    user = await user_repo.by_contact(conn, mobile)
    assert user is not None
    return user


async def _link(conn: Any, seeded: dict[str, Any]) -> str:
    """A consent link with the raw token in hand: a stored link holds only a fingerprint."""
    raw = new_token()
    await conn.execute(
        """INSERT INTO consent_link (notice_id, site_id, token, expires_at, created_by)
           VALUES (%s, %s, %s, now() + interval '7 days', %s)""",
        (
            seeded["notice"]["notice_id"],
            seeded["site"]["site_id"],
            token_fingerprint(raw)[:64],
            seeded["users"]["dco"]["id"],
        ),
    )
    return raw


class TestSelfRegistration:
    async def test_the_mobile_is_stored_normalised_and_found_however_typed(
        self, conn: Any, redis_conn: Any
    ) -> None:
        user = await _register(conn, redis_conn)
        assert user["mobile"] == STORED
        assert user["email"] == EMAIL
        assert user["status"] == "pending"
        assert await user_repo.by_contact(conn, "+91-55500-00901") is not None

    async def test_email_is_optional(self, conn: Any, redis_conn: Any) -> None:
        user = await _register(conn, redis_conn, email=None)
        assert user["email"] is None and user["mobile"] == STORED

    async def test_both_mediums_are_authenticated_before_she_is_signed_in(
        self, conn: Any, redis_conn: Any
    ) -> None:
        user = await _register(conn, redis_conn)
        uuid = str(user["uuid"])
        mobile_code = (await otp.issue(otp.Scope.SUBJECT_REGISTER, f"{uuid}:mobile")).code
        email_code = (await otp.issue(otp.Scope.SUBJECT_REGISTER, f"{uuid}:email")).code

        # The mobile alone is not enough while an email is on the account.
        with pytest.raises(ValidationFailed) as refused:
            await auth_service.confirm_registration(
                conn,
                mobile=MOBILE,
                mobile_code=mobile_code,
                email_code=None,
                ip_address=None,
                user_agent=None,
            )
        assert refused.value.field == "email_code"
        still = await user_repo.by_contact(conn, MOBILE)
        assert still is not None and still["status"] == "pending"

        # Nothing was spent: the same mobile code, with the email code, finishes it.
        result = await auth_service.confirm_registration(
            conn,
            mobile=MOBILE,
            mobile_code=mobile_code,
            email_code=email_code,
            ip_address=None,
            user_agent=None,
        )
        assert result["user"]["status"] == "active"
        assert result["user"]["email_verified_at"] is not None
        assert result["token"] and result["session"].mfa_verified

    async def test_a_wrong_code_is_refused_neutrally(self, conn: Any, redis_conn: Any) -> None:
        await _register(conn, redis_conn)
        with pytest.raises(BadRequest) as refused:
            await auth_service.confirm_registration(
                conn,
                mobile=MOBILE,
                mobile_code="000000",
                email_code="000000",
                ip_address=None,
                user_agent=None,
            )
        assert refused.value.code == "otp_invalid"

    async def test_an_unknown_mobile_is_refused_the_same_way(self, conn: Any) -> None:
        with pytest.raises(BadRequest) as refused:
            await auth_service.confirm_registration(
                conn,
                mobile="+915550009999",
                mobile_code="000000",
                email_code=None,
                ip_address=None,
                user_agent=None,
            )
        assert refused.value.code == "otp_invalid"

    async def test_a_sign_in_code_does_not_finish_an_unfinished_registration(
        self, conn: Any, redis_conn: Any
    ) -> None:
        user = await _register(conn, redis_conn)
        code = (await otp.issue(otp.Scope.SUBJECT_LOGIN, str(user["uuid"]))).code
        with pytest.raises(BadRequest) as refused:
            await auth_service.verify_subject_otp(
                conn, contact=MOBILE, code=code, ip_address=None, user_agent=None
            )
        assert refused.value.code == "registration_incomplete"
        still = await user_repo.by_contact(conn, MOBILE)
        assert still is not None and still["status"] == "pending"

    async def test_a_sign_in_code_goes_to_the_medium_chosen(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        # The seeded principal has both. Whichever she types is where the code goes,
        # and both resolve to her account.
        subject = await user_repo.by_id(conn, seeded["subject"]["id"])
        assert subject is not None
        for contact in (subject["email"], subject["mobile"]):
            code = (await otp.issue(otp.Scope.SUBJECT_LOGIN, str(subject["uuid"]))).code
            result = await auth_service.verify_subject_otp(
                conn, contact=contact, code=code, ip_address=None, user_agent=None
            )
            assert result["user"]["id"] == subject["id"]


class TestConsentLinkRegistration:
    async def test_mobile_required_email_optional_and_each_medium_verified(
        self, conn: Any, seeded: dict[str, Any], redis_conn: Any
    ) -> None:
        token = await _link(conn, seeded)
        await _unthrottle(redis_conn, "consent_otp_contact", STORED, EMAIL)
        result = await consent_service.register_subject(
            conn,
            token=token,
            full_name="Link Registrant",
            mobile=MOBILE,
            email=EMAIL,
            organization_id=None,
            person_type=None,
        )
        assert result["created"] and result["user"]["mobile"] == STORED

        link_uuid = str(result["link"]["link_uuid"])
        mobile_code = (await otp.issue(otp.Scope.CONSENT_LINK, f"{link_uuid}:{STORED}")).code
        first = await consent_service.verify_contact_code(
            conn, token=token, contact=MOBILE, code=mobile_code
        )
        assert first["complete"] is False and first["remaining"] == ["email"]
        assert first["user"]["status"] == "pending"

        email_code = (await otp.issue(otp.Scope.CONSENT_LINK, f"{link_uuid}:{EMAIL}")).code
        second = await consent_service.verify_contact_code(
            conn, token=token, contact=EMAIL, code=email_code
        )
        assert second["complete"] is True and second["remaining"] == []
        assert second["user"]["status"] == "active"

    async def test_mobile_only_completes_in_one_step(
        self, conn: Any, seeded: dict[str, Any], redis_conn: Any
    ) -> None:
        token = await _link(conn, seeded)
        await _unthrottle(redis_conn, "consent_otp_contact", "+915550000902")
        result = await consent_service.register_subject(
            conn,
            token=token,
            full_name="Mobile Only",
            mobile="+915550000902",
            email=None,
            organization_id=None,
            person_type=None,
        )
        link_uuid = str(result["link"]["link_uuid"])
        code = (await otp.issue(otp.Scope.CONSENT_LINK, f"{link_uuid}:+915550000902")).code
        done = await consent_service.verify_contact_code(
            conn, token=token, contact="+91 55500 00902", code=code
        )
        assert done["complete"] is True and done["user"]["status"] == "active"


class TestNomination:
    async def _nominate(self, conn: Any, seeded: dict[str, Any], **kw: Any) -> dict[str, Any]:
        args: dict[str, Any] = {
            "principal_user_id": seeded["subject"]["id"],
            "nominee_name": "Ravi Verma",
            "nominee_mobile": "+91 55500 00777",
            "nominee_email": "ravi@example.org",
            "rights": ["access"],
        }
        args.update(kw)
        return await rights_service.nominate(conn, **args)

    async def test_the_nominee_is_named_by_mobile_with_an_optional_email(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        row = await self._nominate(conn, seeded)
        assert row["nominee_mobile"] == "+915550000777"
        assert row["nominee_email"] == "ravi@example.org"

    async def test_without_a_mobile_there_is_no_nomination(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        with pytest.raises(ValidationFailed) as refused:
            await self._nominate(conn, seeded, nominee_mobile="  ")
        assert refused.value.field == "nominee_mobile"

    async def test_the_view_offers_the_recorded_contacts_masked(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        row = await self._nominate(conn, seeded)
        raw = new_token()
        await conn.execute(
            "UPDATE nomination SET accept_token_hash = %s WHERE nomination_id = %s",
            (token_fingerprint(raw), row["nomination_id"]),
        )
        view = await rights_service.nomination_from_token(conn, raw)
        mediums = rights_service.nomination_mediums(view)
        assert [m["kind"] for m in mediums] == ["mobile", "email"]
        assert mediums[0]["masked"] == "+91" + "•" * 8 + "77"
        assert "ravi" not in mediums[1]["masked"] and mediums[1]["masked"].endswith("@example.org")

    async def test_the_link_alone_neither_accepts_nor_declines(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        row = await self._nominate(conn, seeded)
        raw = new_token()
        await conn.execute(
            "UPDATE nomination SET accept_token_hash = %s WHERE nomination_id = %s",
            (token_fingerprint(raw), row["nomination_id"]),
        )
        with pytest.raises(BadRequest) as refused:
            await rights_service.accept_nomination(conn, raw, code="000000")
        assert refused.value.code == "otp_invalid"
        with pytest.raises(BadRequest):
            await rights_service.decline_nomination(conn, raw, code="000000")
        untouched = await rights_service.nomination_from_token(conn, raw)
        assert untouched["status"] == "pending", "a wrong code changes nothing"

    async def test_a_code_to_a_chosen_recorded_contact_accepts(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        row = await self._nominate(conn, seeded)
        raw = new_token()
        await conn.execute(
            "UPDATE nomination SET accept_token_hash = %s WHERE nomination_id = %s",
            (token_fingerprint(raw), row["nomination_id"]),
        )
        sent = await rights_service.send_nomination_code(conn, raw, medium="email")
        assert sent["to"] == "ravi@example.org"
        with pytest.raises(ValidationFailed):
            await rights_service.send_nomination_code(conn, raw, medium="fax")

        code = (await otp.issue(otp.Scope.NOMINATION_ACCEPT, str(row["nomination_uuid"]))).code
        accepted = await rights_service.accept_nomination(conn, raw, code=code)
        assert accepted["status"] == "active"
        with pytest.raises(NotFound):
            await rights_service.nomination_from_token(conn, raw)  # single use

    async def test_a_code_to_a_contact_not_on_the_nomination_is_refused(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        row = await self._nominate(conn, seeded, nominee_email=None)
        raw = new_token()
        await conn.execute(
            "UPDATE nomination SET accept_token_hash = %s WHERE nomination_id = %s",
            (token_fingerprint(raw), row["nomination_id"]),
        )
        with pytest.raises(ValidationFailed) as refused:
            await rights_service.send_nomination_code(conn, raw, medium="email")
        assert refused.value.field == "medium"

    async def test_the_nominee_starts_from_either_recorded_contact(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        row = await self._nominate(conn, seeded)
        await conn.execute(
            "UPDATE nomination SET status = 'active', accepted_at = now(),"
            " accept_token_hash = NULL WHERE nomination_id = %s",
            (row["nomination_id"],),
        )
        uuid = str(row["nomination_uuid"])
        for typed in ("+91-55500-00777", "RAVI@example.org"):
            reply = await rights_service.nominee_start(conn, nomination_uuid=uuid, contact=typed)
            assert "If that nomination" in reply["message"]
            assert reply["sent_to"] in ("+915550000777", "ravi@example.org")
        stranger = await rights_service.nominee_start(
            conn, nomination_uuid=uuid, contact="+915550000000"
        )
        assert stranger["sent_to"] is None, "nothing is sent, and the reply does not say so"


class TestTheSchemaHoldsTheRule:
    async def test_a_new_data_principal_needs_a_mobile(self, conn: Any) -> None:
        with pytest.raises(psycopg.errors.CheckViolation):
            await conn.execute(
                """INSERT INTO auth_user (full_name, email, role, status)
                   VALUES ('No Mobile', 'nomobile@example.org', 'data_subject', 'pending')"""
            )

    async def test_staff_still_need_an_email(self, conn: Any) -> None:
        with pytest.raises(psycopg.errors.CheckViolation):
            await conn.execute(
                """INSERT INTO auth_user (full_name, mobile, role, status)
                   VALUES ('No Email', '+915550000903', 'dco', 'active')"""
            )

    async def test_a_nomination_from_before_the_rule_can_still_be_revoked(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        """Held on insert, not on update: the first attempt held it as a NOT VALID
        check, and revoking a nomination made under the old rule was a 500."""
        await conn.execute("ALTER TABLE nomination DISABLE TRIGGER trg_nominee_needs_mobile")
        legacy = await conn.execute(
            """INSERT INTO nomination (principal_user_id, nominee_name, nominee_email, rights,
                                       status, accepted_at)
               VALUES (%s, 'Old Nominee', 'old@example.org',
                       ARRAY['access']::rights_request_type[], 'active', now())
               RETURNING nomination_uuid""",
            (seeded["subject"]["id"],),
        )
        await conn.execute("ALTER TABLE nomination ENABLE TRIGGER trg_nominee_needs_mobile")
        uuid = str((await legacy.fetchone())["nomination_uuid"])
        row = await rights_service.revoke_nomination(
            conn, nomination_uuid=uuid, principal_user_id=seeded["subject"]["id"]
        )
        assert row["status"] == "revoked"

    async def test_a_new_nomination_needs_a_mobile(self, conn: Any, seeded: dict[str, Any]) -> None:
        with pytest.raises(psycopg.errors.CheckViolation):
            await conn.execute(
                """INSERT INTO nomination (principal_user_id, nominee_name, nominee_email, rights)
                   VALUES (%s, 'Email Only', 'only@example.org',
                           ARRAY['access']::rights_request_type[])""",
                (seeded["subject"]["id"],),
            )
