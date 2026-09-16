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

from cmp.auth.authentication import service as auth_service
from cmp.core.enums import UserStatus
from cmp.core.errors import Unauthenticated, ValidationFailed
from cmp.core.permissions import Role
from cmp.core.security import hash_password, new_token
from cmp.db.redis import K_LOCKOUT, K_LOGIN_FAILS, K_RATE
from cmp.db.redis import key as rkey
from cmp.db.repositories import users as user_repo
from cmp.db.sql import fetch_all
from cmp.domain.audit.service import Event
from cmp.tasks import dispatch as dispatch_mod

pytestmark = pytest.mark.integration

#: Long enough for the password policy, and not a real one anywhere.
NEW_PASSWORD = "a-well-chosen-passphrase-2026"

INVITATION = "cmp.notifications.send_staff_invitation"
RESET = "cmp.notifications.send_password_reset"


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
        assert full_name == "New Joiner"
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
