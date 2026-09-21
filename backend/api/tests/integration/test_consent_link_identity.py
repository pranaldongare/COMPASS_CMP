"""Who a consent link will send a code to.

The link authenticates the person standing in front of it. It does not enrol
them, and this file is what holds that line, because the two failure modes pull
in opposite directions:

* **A code must not go to a contact nobody has registered.** It is a text
  message to a stranger, and no later step could have accepted it anyway -
  `verify_contact_code` has always refused a contact with no account behind it,
  so the code was never usable. Somebody could aim those messages at any number
  they liked, at the rate limiter's pace.

* **The refusal must not be visible.** The reply is the same sentence either
  way, so a visitor cannot use the form to ask whether a number is on the
  register. That is why the screen offers "create an account" to everybody
  rather than only to the people who turn out to need it.

Both are asserted here, because a change that fixes either one alone looks
correct in isolation and breaks the other.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.enums import UserStatus
from cmp.core.errors import LinkInvalid
from cmp.core.security import new_token, token_fingerprint
from cmp.db.redis import K_RATE
from cmp.db.redis import key as rkey
from cmp.db.repositories import users as user_repo
from cmp.domain.consent import service as consent_service
from cmp.tasks import dispatch as dispatch_mod

pytestmark = pytest.mark.integration

CONSENT_CODE = "cmp.notifications.send_consent_code"


@pytest.fixture
def queued(monkeypatch: Any) -> list[tuple[str, tuple[Any, ...]]]:
    """Codes the service tried to send, captured instead of queued."""
    sent: list[tuple[str, tuple[Any, ...]]] = []

    def capture(task: Any, *args: Any, **kwargs: Any) -> str:
        sent.append((task.name, args))
        return "queued-in-a-test"

    monkeypatch.setattr(dispatch_mod, "dispatch_required", capture)
    monkeypatch.setattr(dispatch_mod, "dispatch_optional", capture)
    return sent


async def a_link(conn: Any, seeded: dict[str, Any]) -> str:
    """A fresh link, and the raw token for it.

    Minted per test rather than shared: the stored token is a keyed digest, so
    the raw one cannot be read back out of the fixture's row.
    """
    raw = new_token()
    await conn.execute(
        """INSERT INTO consent_link (notice_id, site_id, token, expires_at, created_by)
           VALUES (%s, %s, %s, now() + interval '1 day', %s)""",
        (
            seeded["notice"]["notice_id"],
            seeded["site"]["site_id"],
            token_fingerprint(raw)[:64],
            seeded["users"]["dco"]["id"],
        ),
    )
    return raw


async def unthrottle(redis_conn: Any, contact: str) -> None:
    """Codes are capped per contact per hour, in Redis, which outlives the test
    transaction. Clear it so a re-run is not a sixth request."""
    await redis_conn.delete(rkey(K_RATE, "consent_otp_contact", contact.lower()))


class TestWhoGetsACode:
    async def test_a_registered_data_principal_is_sent_one(
        self, conn: Any, seeded: dict[str, Any], redis_conn: Any, queued: Any
    ) -> None:
        token = await a_link(conn, seeded)
        await unthrottle(redis_conn, "+915550000001")

        await consent_service.send_contact_code(conn, token=token, contact="+915550000001")

        assert [name for name, _ in queued] == [CONSENT_CODE]
        assert queued[0][1][0] == "+915550000001"

    async def test_her_email_works_as_well_as_her_mobile(
        self, conn: Any, seeded: dict[str, Any], redis_conn: Any, queued: Any
    ) -> None:
        """The form offers a choice, and the account carries both. A data
        principal who has only ever given a mobile is the reason the mobile is
        the default, not the reason the email is refused."""
        token = await a_link(conn, seeded)
        await unthrottle(redis_conn, "subject@test.local")

        await consent_service.send_contact_code(conn, token=token, contact="subject@test.local")

        assert [name for name, _ in queued] == [CONSENT_CODE]

    async def test_nothing_is_sent_to_a_contact_nobody_registered(
        self, conn: Any, seeded: dict[str, Any], redis_conn: Any, queued: Any
    ) -> None:
        """And it returns rather than raising, which is the neutrality: the
        endpoint above answers the same sentence in both cases."""
        token = await a_link(conn, seeded)
        await unthrottle(redis_conn, "+915559999999")

        await consent_service.send_contact_code(conn, token=token, contact="+915559999999")

        assert queued == []

    async def test_a_staff_contact_gets_one_too(
        self, conn: Any, seeded: dict[str, Any], redis_conn: Any, queued: Any
    ) -> None:
        """Every person the register knows can be a data principal, a member of
        staff included: the DPO's own consent is as much hers as anybody's. What
        keeps this safe is not refusing her here but what the code earns - a
        data principal's session and no more, decided in
        `open_principal_session` and asserted in the security suite."""
        token = await a_link(conn, seeded)
        await unthrottle(redis_conn, "dpo@test.local")

        await consent_service.send_contact_code(conn, token=token, contact="dpo@test.local")

        assert [name for name, _ in queued] == [CONSENT_CODE]

    async def test_an_invalid_link_is_refused_before_any_of_this(
        self, conn: Any, seeded: dict[str, Any], redis_conn: Any, queued: Any
    ) -> None:
        """The link is resolved first, so a bad token never reaches the rate
        limiter or the register."""
        with pytest.raises(LinkInvalid):
            await consent_service.send_contact_code(
                conn, token="not-a-real-token", contact="+915550000001"
            )
        assert queued == []


class TestWhatOneCodeProves:
    """How much a single confirmed contact is worth.

    The link used to wait for every medium on the account before it would hand
    out a session - including one the person gave long ago and never answered.
    That left a data principal standing at a counter, holding a code she had
    just proved, unable to consent and with nothing on the screen able to fix
    it. The portal's own sign-in never worked that way, and the difference was
    not a decision anybody took.
    """

    async def code_for(
        self, conn: Any, seeded: dict[str, Any], queued: Any, token: str, contact: str
    ) -> str:
        await consent_service.send_contact_code(conn, token=token, contact=contact)
        assert queued, f"no code was sent to {contact}"
        return str(queued[-1][1][1])

    async def test_an_active_account_is_signed_in_by_one_contact(
        self, conn: Any, seeded: dict[str, Any], redis_conn: Any, queued: Any
    ) -> None:
        """The fixture's data principal is active and has answered neither
        medium, which is the shape this used to fail on."""
        token = await a_link(conn, seeded)
        await unthrottle(redis_conn, "subject@test.local")
        code = await self.code_for(conn, seeded, queued, token, "subject@test.local")

        result = await consent_service.verify_contact_code(
            conn, token=token, contact="subject@test.local", code=code
        )

        assert result["complete"] is True
        assert result["remaining"] == []
        assert result["user"]["id"] == seeded["subject"]["id"]

    async def test_a_pending_account_still_answers_for_every_medium(
        self, conn: Any, seeded: dict[str, Any], redis_conn: Any, queued: Any
    ) -> None:
        """Enrolment is the other case, and the rule there has not moved: an
        account being created has to prove every contact it was created with,
        or one of them is a claim nobody checked."""
        pending = await user_repo.create(
            conn,
            full_name="Half Enrolled",
            email="halfway@test.local",
            mobile="+915550000077",
            role="data_subject",
            status=UserStatus.PENDING.value,
        )
        token = await a_link(conn, seeded)
        await unthrottle(redis_conn, "halfway@test.local")
        code = await self.code_for(conn, seeded, queued, token, "halfway@test.local")

        result = await consent_service.verify_contact_code(
            conn, token=token, contact="halfway@test.local", code=code
        )

        assert result["complete"] is False
        assert result["remaining"] == ["mobile"]
        assert pending["status"] == UserStatus.PENDING.value
