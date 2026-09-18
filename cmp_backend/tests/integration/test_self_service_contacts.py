"""A person's own contacts, changed by the person.

A second email and a mobile added later, each confirmed by a code before it can
do anything. The second address exists for the person whose first one is not
theirs to keep: a member of staff is also a data principal, and the day they
leave, the corporate mailbox goes with them while their consents do not.

The rule that holds all of it: **a typed contact is a claim, and a claim is not
a way in.** Until the code comes back, the lookup that signs people in does not
see the address at all.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.auth.authentication import service as auth_service
from cmp.core.errors import Conflict, ValidationFailed
from cmp.core.permissions import Role
from cmp.db.redis import K_RATE
from cmp.db.redis import key as rkey
from cmp.db.repositories import users as user_repo
from cmp.tasks import dispatch as dispatch_mod

pytestmark = pytest.mark.integration

CONFIRMATION = "cmp.notifications.send_contact_confirmation"
LOGIN_CODE = "cmp.notifications.send_login_code"
SECOND = "Personal.Address@Example.org"


@pytest.fixture
def queued(monkeypatch: Any) -> list[tuple[str, tuple[Any, ...]]]:
    sent: list[tuple[str, tuple[Any, ...]]] = []

    def capture(task: Any, *args: Any, **kwargs: Any) -> str:
        sent.append((task.name, args))
        return "queued-in-a-test"

    monkeypatch.setattr(dispatch_mod, "dispatch_required", capture)
    monkeypatch.setattr(dispatch_mod, "dispatch_optional", capture)
    return sent


def last_code(queued: Any, task: str) -> str:
    return next(str(args[2]) for name, args in reversed(queued) if name == task)


async def unthrottle(redis_conn: Any, *contacts: str) -> None:
    for c in contacts:
        await redis_conn.delete(
            rkey(K_RATE, "contact_confirm", c.lower()), rkey(K_RATE, "subject_otp", c.lower())
        )


async def her_row(conn: Any, seeded: dict[str, Any]) -> dict[str, Any]:
    row = await user_repo.by_id(conn, seeded["subject"]["id"])
    assert row is not None
    return row


class TestASecondEmail:
    async def test_adding_one_stores_it_lower_cased_unconfirmed_and_sends_a_code(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        await unthrottle(redis_conn, SECOND)
        updated = await auth_service.add_secondary_email(
            conn, user=await her_row(conn, seeded), email=SECOND
        )

        assert updated["secondary_email"] == SECOND.lower()
        assert updated["secondary_email_verified_at"] is None
        assert [n for n, _ in queued] == [CONFIRMATION]
        assert queued[0][1][1] == SECOND.lower(), "the code goes to the new address"

    async def test_until_confirmed_it_signs_nobody_in(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        """The whole rule. A typed address that could sign somebody in would let
        anyone with a session claim a stranger's address as theirs."""
        await unthrottle(redis_conn, SECOND)
        await auth_service.add_secondary_email(conn, user=await her_row(conn, seeded), email=SECOND)

        assert await user_repo.by_contact(conn, SECOND) is None

    async def test_the_code_confirms_it_and_then_it_signs_her_in(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        await unthrottle(redis_conn, SECOND)
        await auth_service.add_secondary_email(conn, user=await her_row(conn, seeded), email=SECOND)
        code = last_code(queued, CONFIRMATION)

        confirmed = await auth_service.confirm_contact(
            conn, user=await her_row(conn, seeded), contact=SECOND, code=code
        )
        assert confirmed["secondary_email_verified_at"] is not None

        found = await user_repo.by_contact(conn, SECOND)
        assert found is not None and found["id"] == seeded["subject"]["id"]

        # And the portal's sign-in reaches her through it.
        await auth_service.request_subject_otp(conn, contact=SECOND)
        result = await auth_service.verify_subject_otp(
            conn,
            contact=SECOND,
            code=last_code(queued, LOGIN_CODE),
            ip_address="127.0.0.1",
            user_agent="test",
        )
        assert result["session"].role == Role.DATA_SUBJECT.value
        assert result["user"]["id"] == seeded["subject"]["id"]

    async def test_removing_it_clears_both_the_address_and_its_confirmation(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        await unthrottle(redis_conn, SECOND)
        await auth_service.add_secondary_email(conn, user=await her_row(conn, seeded), email=SECOND)
        await auth_service.confirm_contact(
            conn,
            user=await her_row(conn, seeded),
            contact=SECOND,
            code=last_code(queued, CONFIRMATION),
        )

        cleared = await auth_service.remove_secondary_email(conn, user=await her_row(conn, seeded))

        assert cleared["secondary_email"] is None
        assert cleared["secondary_email_verified_at"] is None
        assert await user_repo.by_contact(conn, SECOND) is None

    async def test_her_own_first_address_is_refused_as_a_second(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        with pytest.raises(ValidationFailed):
            await auth_service.add_secondary_email(
                conn, user=await her_row(conn, seeded), email="Subject@test.local"
            )

    async def test_somebody_elses_address_is_a_conflict_not_a_takeover(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        """The DPO's corporate address, claimed as a second by somebody else.
        The database refuses it, and the refusal is reported as the conflict it
        is rather than as a server error."""
        with pytest.raises(Conflict) as exc:
            await auth_service.add_secondary_email(
                conn, user=await her_row(conn, seeded), email="dpo@test.local"
            )
        assert exc.value.code == "contact_taken"


class TestGivingAContactThatIsAlreadyThere:
    """Re-saving a contact the account already carries.

    Reported from a running stack: a member of staff signed in to the portal as
    the data principal she also is, opened her account page, pressed save on
    the mobile already shown there, and no code ever arrived. The rule had been
    "a contact that *changed* is sent a code", and the commonest case is the
    one where nothing changes - an administrator had set the number on the
    register, so the edit box opens pre-filled with it, and the natural act of
    opening it and pressing save sent nothing at all while the screen said it
    had.

    The rule is now about the state she is left in rather than about the
    difference: a contact she gives that is still unconfirmed afterwards is
    sent a code. One that has already proved itself is left alone, because
    re-sending would take away a way of signing in to no purpose.
    """

    async def test_an_unconfirmed_mobile_resaved_unchanged_is_sent_a_code(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        her = await her_row(conn, seeded)
        assert her["mobile_verified_at"] is None, "the seeded principal has not confirmed hers"
        await unthrottle(redis_conn, str(her["mobile"]))

        same = str(her["mobile"])
        updated = await user_repo.update_profile(conn, her["id"], mobile=same)
        assert updated["mobile"] == same, "unchanged, and that is the point"
        assert updated["mobile_verified_at"] is None

        await auth_service.request_contact_code(conn, user=updated, contact=same)
        assert [n for n, _ in queued] == [CONFIRMATION]
        assert queued[0][1][1] == same

    async def test_a_confirmed_mobile_resaved_keeps_its_confirmation(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        """`update_profile` decides this, and the account page reads the answer
        off the row it gets back."""
        await user_repo.mark_contact_verified(conn, seeded["subject"]["id"], "mobile")
        her = await her_row(conn, seeded)
        assert her["mobile_verified_at"] is not None

        again = await user_repo.update_profile(conn, her["id"], mobile=str(her["mobile"]))
        assert again["mobile_verified_at"] is not None

    async def test_a_confirmed_second_address_resaved_keeps_its_confirmation_and_is_sent_nothing(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        """It had proved itself. Unconfirming it to send another code would
        cost her a way of signing in for no gain."""
        await unthrottle(redis_conn, SECOND)
        await auth_service.add_secondary_email(conn, user=await her_row(conn, seeded), email=SECOND)
        await auth_service.confirm_contact(
            conn,
            user=await her_row(conn, seeded),
            contact=SECOND,
            code=last_code(queued, CONFIRMATION),
        )
        queued.clear()

        again = await auth_service.add_secondary_email(
            conn, user=await her_row(conn, seeded), email=SECOND.upper()
        )

        assert again["secondary_email_verified_at"] is not None
        assert queued == [], "nothing to send: it is already confirmed"
        found = await user_repo.by_contact(conn, SECOND)
        assert found is not None, "and it still signs her in"

    async def test_an_unconfirmed_second_address_resaved_is_sent_another_code(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        await unthrottle(redis_conn, SECOND)
        await auth_service.add_secondary_email(conn, user=await her_row(conn, seeded), email=SECOND)
        queued.clear()

        again = await auth_service.add_secondary_email(
            conn, user=await her_row(conn, seeded), email=SECOND
        )

        assert again["secondary_email_verified_at"] is None
        assert [n for n, _ in queued] == [CONFIRMATION]


class TestCodesGoOnlyToHerOwnContacts:
    async def test_a_contact_not_on_her_account_gets_nothing(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        """Otherwise a signed-in person could aim confirmation codes at any
        address or number they liked."""
        with pytest.raises(ValidationFailed):
            await auth_service.request_contact_code(
                conn, user=await her_row(conn, seeded), contact="stranger@example.org"
            )
        assert queued == []

    async def test_a_contact_already_confirmed_is_not_sent_another(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        await user_repo.mark_contact_verified(conn, seeded["subject"]["id"], "mobile")
        with pytest.raises(ValidationFailed):
            await auth_service.request_contact_code(
                conn, user=await her_row(conn, seeded), contact="+915550000001"
            )
        assert queued == []


class TestAChangedMobile:
    async def test_is_unconfirmed_again(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        """The old confirmation was of the old number."""
        await user_repo.mark_contact_verified(conn, seeded["subject"]["id"], "mobile")
        before = await her_row(conn, seeded)
        assert before["mobile_verified_at"] is not None

        after = await user_repo.update_profile(
            conn, seeded["subject"]["id"], mobile="+915550000777"
        )
        assert after["mobile"] == "+915550000777"
        assert after["mobile_verified_at"] is None

    async def test_an_unchanged_mobile_keeps_its_confirmation(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        await user_repo.mark_contact_verified(conn, seeded["subject"]["id"], "mobile")
        after = await user_repo.update_profile(
            conn, seeded["subject"]["id"], full_name="Renamed Subject", mobile="+91 5550 000001"
        )
        assert after["mobile_verified_at"] is not None, "same number, spaced differently"
