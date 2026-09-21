"""Provisioning a member of staff, from the administrator's form to a first sign-in.

An account an administrator creates is unusable until its owner sets a password,
and nothing checked that they could. Two faults made it impossible, and neither
was visible to a suite that exercised the reset flow only for accounts that were
already active:

* `request_password_reset` refused any account that was not `active`, and a
  provisioned account is `pending` — so the "Forgotten your password?" route the
  console pointed new joiners at answered them with silence;
* `confirm_password_reset` set the password and left the status alone, while
  `authenticate` refuses anything but an active account — so even a code that
  did arrive bought a password that did not work.

Each piece was correct on its own, which is why these tests walk the whole path
instead: provision, invite, set the password with the code that was sent, sign
in. Nothing here asserts that a message was *rendered* — that is the catalogue's
job — only that the right task was queued with the code the person needs.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.auth.authentication import otp
from cmp.auth.authentication import service as auth_service
from cmp.auth.rate_limit import service as ratelimit
from cmp.core.config import settings
from cmp.core.enums import UserStatus
from cmp.core.errors import Unauthenticated, ValidationFailed
from cmp.core.permissions import Role
from cmp.core.security import hash_password, new_token
from cmp.db.redis import K_LOCKOUT, K_LOGIN_FAILS, K_OTP, K_RATE
from cmp.db.redis import key as rkey
from cmp.db.repositories import users as user_repo
from cmp.db.sql import fetch_all
from cmp.domain.audit.service import Event
from cmp.tasks import dispatch as dispatch_mod
from tests.conftest import plain

pytestmark = pytest.mark.integration

#: Long enough for the password policy, and not a real one anywhere.
NEW_PASSWORD = "a-well-chosen-passphrase-2026"

INVITATION = "cmp.notifications.send_staff_invitation"
RESET = "cmp.notifications.send_password_reset"
ON_BEHALF = "cmp.notifications.send_contact_added_for_you"

#: As an administrator would type it; the row holds it in E.164. Inside the
#: 98765 0xxxx block, which nothing seeds and no manual test reaches for - a
#: number a person or a probe has already been given collides on the unique
#: index, and the failure looks like the feature rather than the fixture.
MOBILE = "+91 98765 00042"
MOBILE_E164 = "+919876500042"


@pytest.fixture
def queued(monkeypatch: Any) -> list[tuple[str, tuple[Any, ...]]]:
    """Every task the code under test queues, captured instead of sent.

    Both helpers are replaced, for different reasons. `dispatch_required` would
    reach for the broker. `dispatch_optional` would defer to after the commit —
    and the commit never comes, because every test here runs inside a
    transaction that is rolled back, so a real one would queue nothing and the
    assertion would pass for the wrong reason.
    """
    sent: list[tuple[str, tuple[Any, ...]]] = []

    def capture(task: Any, *args: Any, **kwargs: Any) -> str:
        sent.append((task.name, args))
        return "queued-in-a-test"

    monkeypatch.setattr(dispatch_mod, "dispatch_optional", capture)
    monkeypatch.setattr(dispatch_mod, "dispatch_required", capture)
    return sent


def only(sent: list[tuple[str, tuple[Any, ...]]], name: str) -> tuple[Any, ...]:
    """The arguments of the one task of this kind that was queued."""
    matching = [args for task_name, args in sent if task_name == name]
    assert len(matching) == 1, f"expected exactly one {name}, got {[n for n, _ in sent]}"
    return matching[0]


async def provision(
    conn: Any,
    *,
    email: str,
    role: str = Role.DCO.value,
    status: str = UserStatus.PENDING.value,
    mobile: str | None = None,
) -> dict[str, Any]:
    """What `POST /users` writes: a pending account holding an unusable password.

    Written with the repository rather than through the endpoint because the
    endpoint needs a request and an administrator's session, and what is under
    test here is what happens to the row afterwards.
    """
    return await user_repo.create(
        conn,
        full_name="New Joiner",
        email=email,
        role=role,
        status=status,
        mobile=mobile,
        password_hash=hash_password(new_token(32)),
    )


async def unthrottle(redis_conn: Any, email: str) -> None:
    """Forget everything Redis remembers about this address.

    Three counters outlive the test transaction, because none of them lives in
    Postgres: reset requests are capped at three an hour, failed sign-ins are
    counted per account, and five of those lock it. A test that deliberately
    signs in wrongly therefore poisons its own next run - the sixth attempt
    raises `RateLimited` where the test expects `Unauthenticated`, and the
    failure appears only in a full suite, hours from the change that caused it.
    """
    await redis_conn.delete(
        rkey(K_RATE, "pwreset", email.lower()),
        rkey(K_LOGIN_FAILS, email.lower()),
        rkey(K_LOCKOUT, email.lower()),
    )


async def events_for(conn: Any, user_id: int) -> list[str]:
    rows = await fetch_all(
        conn,
        "SELECT event_type FROM audit_log WHERE subject_user_id = %s ORDER BY log_id",
        (user_id,),
    )
    return [r["event_type"] for r in rows]


class TestTheInvitation:
    async def test_it_carries_a_code_that_sets_the_first_password(
        self, conn: Any, request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        """The whole point: the code in the message has to be one the reset page
        accepts. It is the reset flow's own code, deliberately — an invitation
        that expires is then replaced by "Forgotten your password?" rather than
        by a second mechanism nobody maintains."""
        user = await provision(conn, email="invited@test.local")
        await auth_service.invite_staff(conn, user=user)

        _uuid, email, full_name, role_title, code, reset_url, hours = only(queued, INVITATION)
        assert email == "invited@test.local"
        # Sealed on the row, and it travels sealed; delivery opens it.
        assert plain(full_name) == "New Joiner"
        # The role is named in words. "dco" is a column value, not a job title.
        assert role_title == "Data Collection Owner"
        assert len(code) == 6 and code.isdigit()
        assert reset_url.endswith("/sign-in/reset?email=invited%40test.local")
        assert hours >= 1

        await auth_service.confirm_password_reset(
            conn, email="invited@test.local", code=code, new_password=NEW_PASSWORD
        )

        after = await user_repo.by_id(conn, user["id"])
        assert after is not None
        assert after["status"] == UserStatus.ACTIVE.value

    async def test_the_account_is_pending_until_the_password_is_set(
        self, conn: Any, request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        """Provisioning alone must not let anybody in. The random password is
        unusable by construction, and the status is the second lock."""
        await unthrottle(redis_conn, "notyet@test.local")
        user = await provision(conn, email="notyet@test.local")
        await auth_service.invite_staff(conn, user=user)

        assert user["status"] == UserStatus.PENDING.value
        with pytest.raises(Unauthenticated):
            await auth_service.authenticate(
                conn,
                login="notyet@test.local",
                password=NEW_PASSWORD,
                ip_address="127.0.0.1",
                user_agent="test",
            )

    async def test_the_new_password_then_signs_in_and_still_wants_a_second_factor(
        self, conn: Any, request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        """Activation is not a way round MFA. A DCO steps up with a code like
        every other staff role, on the first sign-in as much as the hundredth."""
        await unthrottle(redis_conn, "firstsignin@test.local")
        user = await provision(conn, email="firstsignin@test.local")
        await auth_service.invite_staff(conn, user=user)
        code = only(queued, INVITATION)[4]
        await auth_service.confirm_password_reset(
            conn, email="firstsignin@test.local", code=code, new_password=NEW_PASSWORD
        )

        session = await auth_service.authenticate(
            conn,
            login="firstsignin@test.local",
            password=NEW_PASSWORD,
            ip_address="127.0.0.1",
            user_agent="test",
        )
        assert session["mfa_required"] is True
        assert only(queued, "cmp.notifications.send_mfa_code")[1] == "firstsignin@test.local"
        assert user["id"] is not None

    async def test_the_trail_shows_who_was_invited_and_when_they_activated(
        self, conn: Any, request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        """Provisioning is an administrator acting on somebody else's account,
        and activation is that person acting on their own. Both are evidence."""
        user = await provision(conn, email="audited@test.local")
        await auth_service.invite_staff(conn, user=user)
        code = only(queued, INVITATION)[4]
        await auth_service.confirm_password_reset(
            conn, email="audited@test.local", code=code, new_password=NEW_PASSWORD
        )

        events = await events_for(conn, user["id"])
        assert Event.USER_INVITED in events
        assert Event.USER_ACTIVATED in events
        assert Event.PASSWORD_RESET_COMPLETED in events

    async def test_a_data_principal_cannot_be_invited(
        self, conn: Any, request_context: Any, queued: Any
    ) -> None:
        """She has no password to set. Her sign-in is a code to a contact she
        chose, and an invitation would offer her a credential she should not
        have."""
        # The database insists a data principal has a mobile: her sign-in is a
        # code, and an account with nowhere to send one could not receive it.
        subject = await provision(
            conn,
            email="principal@test.local",
            role=Role.DATA_SUBJECT.value,
            mobile="+919000009999",
        )
        with pytest.raises(ValidationFailed):
            await auth_service.invite_staff(conn, user=subject)


class TestAskingForTheCodeAgain:
    async def test_a_pending_account_may_ask_for_its_own_code(
        self, conn: Any, request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        """The reported fault. An invitation that expired left no way back in:
        the console offers "Forgotten your password?", and for a pending account
        the server answered with the neutral reply and sent nothing."""
        user = await provision(conn, email="expired@test.local")
        await unthrottle(redis_conn, "expired@test.local")

        await auth_service.request_password_reset(conn, email="expired@test.local")

        assert only(queued, RESET)[1] == "expired@test.local"
        assert user["status"] == UserStatus.PENDING.value

    @pytest.mark.parametrize("status", [UserStatus.SUSPENDED.value, UserStatus.DEACTIVATED.value])
    async def test_a_suspended_or_deactivated_account_still_gets_nothing(
        self, conn: Any, request_context: Any, redis_conn: Any, queued: Any, status: str
    ) -> None:
        """The silence is the point for these two: an account somebody took away
        must not be recoverable by its former holder, and the neutral answer must
        not become an oracle for which accounts are switched off."""
        email = f"{status}@test.local"
        await provision(conn, email=email, status=status)
        await unthrottle(redis_conn, email)

        await auth_service.request_password_reset(conn, email=email)

        assert not [name for name, _ in queued if name == RESET]


async def unthrottle_mobile(redis_conn: Any) -> None:
    """The per-contact quota on confirmation codes lives in Redis and outlives
    the test transaction."""
    await redis_conn.delete(rkey(K_RATE, "contact_confirm", MOBILE_E164))


class TestAMobileGivenByTheAdministrator:
    """`POST /users` with a mobile, or `PATCH /users/{uuid}` changing one.

    The number is somebody else's phone, typed by an administrator: a claim,
    like any contact a person types for themselves, and no way in until a code
    sent to it comes back. What differs is that nobody is at a code box, so the
    code lasts as long as an invitation and the message is a courtesy that
    never fails the edit. The endpoints call the one service function tested
    here, after writing the row.
    """

    async def test_the_number_is_sent_a_code_that_lasts_hours_and_confirms_it(
        self, conn: Any, request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        await unthrottle_mobile(redis_conn)
        user = await provision(conn, email="with.mobile@test.local", mobile=MOBILE)
        row = await user_repo.by_id(conn, user["id"])
        assert row is not None and row["mobile_verified_at"] is None

        sent = await auth_service.request_contact_code_on_behalf(conn, user=row, contact=MOBILE)

        assert sent is True
        user_uuid, contact, code, hours = only(queued, ON_BEHALF)
        assert (user_uuid, contact, hours) == (
            str(user["uuid"]),
            MOBILE_E164,
            settings.staff_invite_ttl_h,
        )
        # Hours rather than minutes: the person is not waiting for it.
        ttl = await redis_conn.ttl(
            rkey(K_OTP, otp.Scope.CONTACT_VERIFY, f"{user['uuid']}:{MOBILE_E164}")
        )
        assert ttl > 3600, f"a code sent on somebody's behalf lasted {ttl}s"
        # And it is the code the account page's box accepts.
        confirmed = await auth_service.confirm_contact(conn, user=row, contact=MOBILE, code=code)
        assert confirmed["mobile_verified_at"] is not None
        assert Event.OTP_REQUESTED in await events_for(conn, user["id"])

    async def test_a_number_already_confirmed_is_left_alone(
        self, conn: Any, request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        user = await provision(conn, email="confirmed.mobile@test.local", mobile=MOBILE)
        await user_repo.mark_contact_verified(conn, user["id"], "mobile")
        row = await user_repo.by_id(conn, user["id"])
        assert row is not None

        assert (
            await auth_service.request_contact_code_on_behalf(conn, user=row, contact=MOBILE)
            is False
        )
        assert queued == []

    async def test_a_contact_not_on_the_account_gets_nothing(
        self, conn: Any, request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        """The endpoints only ever pass the row's own mobile, and this is what
        holds if one day something else does."""
        user = await provision(conn, email="no.such.mobile@test.local", mobile=MOBILE)
        assert (
            await auth_service.request_contact_code_on_behalf(
                conn, user=user, contact="+919000000009"
            )
            is False
        )
        assert queued == []

    async def test_a_spent_quota_withholds_the_code_without_failing_the_edit(
        self, conn: Any, request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        """Five codes an hour per contact, as for the person's own requests. The
        sixth is not sent - and the administrator's edit stands, because the
        alternative is a number that cannot be corrected for an hour."""
        await unthrottle_mobile(redis_conn)
        user = await provision(conn, email="throttled.mobile@test.local", mobile=MOBILE)
        for _ in range(settings.otp_requests_per_contact_per_hour):
            await ratelimit.check(
                "contact_confirm",
                MOBILE_E164,
                limit=settings.otp_requests_per_contact_per_hour,
                window_s=3600,
            )
        try:
            assert (
                await auth_service.request_contact_code_on_behalf(conn, user=user, contact=MOBILE)
                is False
            )
            assert queued == []
        finally:
            await unthrottle_mobile(redis_conn)
