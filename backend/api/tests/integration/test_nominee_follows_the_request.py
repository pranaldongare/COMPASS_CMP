"""A nominee can follow the request they raised, to the end.

Found on a running stack on 2026-09-17. A nominee had invoked a nomination on
a death trigger, raised an access request, and the office had answered and
closed it a week earlier with a full response and a released file. Signed in to
the portal, he saw an empty request list and no trace of any of it. The
acknowledgement he had been sent told him the response "will be available to
you signed in, from your own account" - a promise the platform could not keep,
because every route that returns a request filters on `subject_user_id`, and
the subject of his request is the principal, whom he is not.

Section 14 makes the nominee the person who exercises the right. A right to ask
without a right to be told the answer is not a right, so the request he raised
now reads to him exactly as it does to her: the state, the clock, the response
and the files released with it. He had been sent all of it by message already;
what was missing was anywhere to look.

Three rules hold the shape, and each has a test here:

* **Reading is not acting.** Being signed in is enough to read what became of
  the request he raised. Making another in her name still needs the nominee
  page and a code to a contact she recorded - and so does disputing, which
  makes a new request.
* **Revocation stops what comes next, and unasks nothing.** A nomination
  revoked after it was invoked keeps the request visible to him. One revoked
  without ever being acted on disappears, as before.
* **The link is a recorded account, not a string comparison.** Acceptance
  writes down which account accepted, so a nominee who later changes their
  mobile does not silently stop matching their own nomination.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.auth.authentication import otp
from cmp.core.security import new_token, token_fingerprint
from cmp.db.redis import K_CACHE, get_redis
from cmp.db.redis import key as rkey
from cmp.db.repositories import rights as repo
from cmp.db.repositories import users as user_repo
from cmp.domain.rights import service
from cmp.tasks import dispatch as dispatch_mod

pytestmark = pytest.mark.integration

ACKNOWLEDGEMENT = "cmp.notifications.send_rights_acknowledgement"

#: Inside a block nothing seeds and no manual probe reaches for. A contact a
#: live probe has already committed collides on the unique index, and the
#: failure reads as the feature rather than the fixture.
NOMINEE_MOBILE = "+919876511001"
NOMINEE_EMAIL = "nominee.follows@example.org"


@pytest.fixture
def queued(monkeypatch: Any) -> list[tuple[str, tuple[Any, ...]]]:
    sent: list[tuple[str, tuple[Any, ...]]] = []

    def capture(task: Any, *args: Any, **kwargs: Any) -> str:
        sent.append((task.name, args))
        return "queued-in-a-test"

    monkeypatch.setattr(dispatch_mod, "dispatch_required", capture)
    monkeypatch.setattr(dispatch_mod, "dispatch_optional", capture)
    return sent


async def nominate_and_accept(
    conn: Any,
    principal_user_id: int,
    *,
    mobile: str = NOMINEE_MOBILE,
    email: str | None = NOMINEE_EMAIL,
    rights: list[str] | None = None,
) -> dict[str, Any]:
    """The whole acceptance, as the link performs it: token, code, accept."""
    nomination = await service.nominate(
        conn,
        principal_user_id=principal_user_id,
        nominee_name="Nominee Who Follows",
        nominee_mobile=mobile,
        nominee_email=email,
        rights=rights or ["access", "grievance"],
    )
    raw = new_token()
    await conn.execute(
        "UPDATE nomination SET accept_token_hash = %s WHERE nomination_id = %s",
        (token_fingerprint(raw), nomination["nomination_id"]),
    )
    ref = str(nomination["nomination_uuid"])
    code = (await otp.issue(otp.Scope.NOMINATION_ACCEPT, ref)).code
    await get_redis().set(rkey(K_CACHE, "nomination_medium", ref), "mobile", ex=600)
    return dict(await service.accept_nomination(conn, raw, code=code))


async def raise_request(
    conn: Any, nomination: dict[str, Any], *, event: str = "death", kind: str = "access"
) -> dict[str, Any]:
    ref = str(nomination["nomination_uuid"])
    issued = await otp.issue(otp.Scope.NOMINEE_VERIFY, ref)
    return dict(
        await service.nominee_submit(
            conn,
            nomination_uuid=ref,
            code=issued.code,
            request_type=kind,
            request_text="Her records, please",
            trigger_event=event,
            evidence_ref=None,
            evidence_hash="ev1",
        )
    )


async def nominee_account(conn: Any) -> dict[str, Any]:
    found = await user_repo.by_contact(conn, NOMINEE_MOBILE)
    assert found is not None, "accepting should have made him an account"
    return dict(found)


class TestAcceptanceRecordsTheAccount:
    async def test_a_stranger_who_accepts_is_written_onto_the_nomination(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        """Without this the link is recomputed from contact strings every time,
        which already missed a second email and breaks the day he changes his
        number."""
        accepted = await nominate_and_accept(conn, seeded["subject"]["id"])
        him = await nominee_account(conn)

        fresh = await repo.nomination_by_uuid(conn, str(accepted["nomination_uuid"]))
        assert fresh is not None
        assert fresh["nominee_user_id"] == him["id"]

    async def test_an_existing_account_is_recorded_rather_than_duplicated(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        """A nominee who is already a data principal here keeps the one account
        he has, and the nomination points at it."""
        her = seeded["subject"]
        other = await user_repo.create(
            conn,
            full_name="Already Registered",
            email=None,
            mobile="+919876511002",
            role="data_subject",
            status="active",
        )
        accepted = await nominate_and_accept(conn, her["id"], mobile="+919876511002", email=None)

        fresh = await repo.nomination_by_uuid(conn, str(accepted["nomination_uuid"]))
        assert fresh is not None
        assert fresh["nominee_user_id"] == other["id"]

    async def test_he_is_matched_by_the_account_even_after_changing_his_mobile(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        """The contacts on the nomination are what she recorded and what a code
        goes to; they must not follow his later edits. The recorded account is
        what keeps his own nomination in front of him."""
        accepted = await nominate_and_accept(conn, seeded["subject"]["id"])
        him = await nominee_account(conn)
        await user_repo.update_profile(conn, int(him["id"]), mobile="+919876511009")
        moved = await user_repo.by_id(conn, int(him["id"]))
        assert moved is not None and moved["mobile"] == "+919876511009"

        listed = await repo.nominations_naming(
            conn, user_id=int(him["id"]), mobile=moved["mobile"], email=moved.get("email")
        )
        assert [str(r["nomination_uuid"]) for r in listed] == [str(accepted["nomination_uuid"])], (
            "his own nomination went missing when he changed his number"
        )


class TestWhatHeCanSee:
    async def test_the_list_carries_how_far_the_request_has_got(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        """A reference with no state beside it is how somebody comes to believe
        nothing has happened."""
        accepted = await nominate_and_accept(conn, seeded["subject"]["id"])
        him = await nominee_account(conn)
        row = await raise_request(conn, accepted)

        listed = await repo.nominations_naming(
            conn, user_id=int(him["id"]), mobile=him["mobile"], email=him.get("email")
        )
        assert len(listed) == 1
        one = listed[0]
        assert one["invoked_reference"] == row["reference"]
        assert one["invoked_request_uuid"] == row["request_uuid"]
        assert one["invoked_request_type"] == "access"
        assert one["invoked_status"] == "received"
        assert one["invoked_outcome"] is None
        assert one["invoked_due_at"] == row["due_at"]

    async def test_the_request_reads_to_him_as_it_does_to_her(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        accepted = await nominate_and_accept(conn, seeded["subject"]["id"])
        him = await nominee_account(conn)
        row = await raise_request(conn, accepted)

        his = await repo.request_as_nominee(
            conn,
            str(row["request_uuid"]),
            user_id=int(him["id"]),
            mobile=him["mobile"],
            email=him.get("email"),
        )
        hers = await repo.subject_request(conn, str(row["request_uuid"]), seeded["subject"]["id"])
        assert his is not None and hers is not None
        assert his["request_id"] == hers["request_id"]
        assert his["reference"] == row["reference"]
        assert his["subject_user_id"] == seeded["subject"]["id"], "it is still her request"

    async def test_a_stranger_signed_in_reaches_none_of_it(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        """The whole point of a second predicate rather than a looser one."""
        accepted = await nominate_and_accept(conn, seeded["subject"]["id"])
        row = await raise_request(conn, accepted)
        stranger = await user_repo.by_id(conn, seeded["users"]["dpo"]["id"])
        assert stranger is not None

        assert (
            await repo.request_as_nominee(
                conn,
                str(row["request_uuid"]),
                user_id=int(stranger["id"]),
                mobile=stranger.get("mobile"),
                email=stranger.get("email"),
            )
            is None
        )

    async def test_a_request_nobody_nominated_him_for_is_not_his_to_read(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        """He is a nominee, and that is not a key to every request there is."""
        accepted = await nominate_and_accept(conn, seeded["subject"]["id"])
        him = await nominee_account(conn)
        await raise_request(conn, accepted)
        hers = await service.create(
            conn,
            request_type="access",
            channel="portal",
            request_text="Mine, made myself",
            submitted_contact="subject@test.local",
            submitted_name="Test Subject",
            subject_user_id=seeded["subject"]["id"],
            actor_id=seeded["subject"]["id"],
            verification_method="session",
        )

        assert (
            await repo.request_as_nominee(
                conn,
                str(hers["request_uuid"]),
                user_id=int(him["id"]),
                mobile=him["mobile"],
                email=him.get("email"),
            )
            is None
        ), "a request she made herself is not his, whoever else he acts for"


class TestRevocation:
    async def test_a_nomination_revoked_after_he_acted_keeps_the_request_in_view(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        """Revocation stops what comes next. It does not unask the question he
        lawfully asked, or withdraw the answer he is owed."""
        principal = seeded["subject"]["id"]
        accepted = await nominate_and_accept(conn, principal)
        him = await nominee_account(conn)
        row = await raise_request(conn, accepted)
        await service.revoke_nomination(
            conn, nomination_uuid=str(accepted["nomination_uuid"]), principal_user_id=principal
        )

        listed = await repo.nominations_naming(
            conn, user_id=int(him["id"]), mobile=him["mobile"], email=him.get("email")
        )
        assert [r["invoked_reference"] for r in listed] == [row["reference"]]
        assert listed[0]["status"] == "revoked", "and it says plainly that it is over"
        assert (
            await repo.request_as_nominee(
                conn,
                str(row["request_uuid"]),
                user_id=int(him["id"]),
                mobile=him["mobile"],
                email=him.get("email"),
            )
            is not None
        )

    async def test_a_nomination_revoked_before_he_acted_disappears(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any
    ) -> None:
        principal = seeded["subject"]["id"]
        accepted = await nominate_and_accept(conn, principal)
        him = await nominee_account(conn)
        await service.revoke_nomination(
            conn, nomination_uuid=str(accepted["nomination_uuid"]), principal_user_id=principal
        )

        assert (
            await repo.nominations_naming(
                conn, user_id=int(him["id"]), mobile=him["mobile"], email=him.get("email")
            )
            == []
        )


class TestWhoIsTold:
    async def test_on_incapacity_she_is_acknowledged_as_well_as_him(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, queued: Any
    ) -> None:
        """Her account stays open and the request appears in her own list.
        Somebody exercising her rights in her name is a thing she should hear
        from us, not discover - and incapacity is the claim she might be in a
        position to dispute."""
        accepted = await nominate_and_accept(conn, seeded["subject"]["id"])
        row = await raise_request(conn, accepted, event="incapacity")

        told = [args[0] for name, args in queued if name == ACKNOWLEDGEMENT]
        assert NOMINEE_MOBILE in told, "the nominee is the requester and hears first"
        assert "subject@test.local" in told, "and she is told it was done in her name"
        assert row["trigger_event"] == "incapacity"

    async def test_on_death_only_he_is_written_to(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, queued: Any
    ) -> None:
        """There is nobody to write to, and writing anyway would be its own
        cruelty."""
        accepted = await nominate_and_accept(conn, seeded["subject"]["id"])
        await raise_request(conn, accepted, event="death")

        told = [args[0] for name, args in queued if name == ACKNOWLEDGEMENT]
        assert told == [NOMINEE_MOBILE]
