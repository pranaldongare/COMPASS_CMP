"""Breach-only logins, and colleagues who follow the same flow (S3-09, ADR 0023).

Somebody with no console login is given one for a breach: on their data
principal account if they have one, on a new account if not. It reaches their
ticket and nothing else. The grant ends when the breach closes or the ticket
is withdrawn, and the login stays so they can still read their ticket
(2026-10-06); an administrator's End temporary access is the one off switch.
Nobody is ever marked an ex-employee.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from cmp.core.config import settings
from cmp.core.errors import Conflict, ValidationFailed
from cmp.db.sql import fetch_all, fetch_one
from cmp.domain.breach import service, tickets
from cmp.domain.users import service as users
from cmp.tasks import dispatch as dispatch_mod
from tests.conftest import hashed
from tests.integration.test_breach_register import tell_org_board

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def internal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "breach_ticket_email_domains", ("test.local",))


@pytest.fixture
def mailed(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    sent: list[str] = []

    def capture(task: Any, *args: Any, **kwargs: Any) -> str:
        sent.append(task.name)
        return "queued"

    monkeypatch.setattr(dispatch_mod, "dispatch_optional", capture)
    return sent


def _dpo(seeded: dict[str, Any]) -> int:
    return int(seeded["users"]["dpo"]["id"])


async def _recorded(conn: Any, seeded: dict[str, Any]) -> str:
    made = await service.record(
        conn,
        title="A log server reachable from the guest network",
        detected_at=datetime.now(UTC) - timedelta(hours=1),
        began_at=None,
        location_kind="platform",
        processor_uuid=None,
        source_uuid=None,
        location_detail=None,
        actor_id=_dpo(seeded),
    )
    uuid = str(made["breach_uuid"])
    await service.determine(
        conn,
        breach_uuid=uuid,
        outcome="yes",
        reasoning="Contacts were in the logs",
        became_aware_at=datetime.now(UTC) - timedelta(minutes=30),
        actor_id=_dpo(seeded),
    )
    await tell_org_board(conn, seeded, uuid)
    return uuid


async def _by_email(conn: Any, seeded: dict[str, Any], uuid: str, email: str, **kw: Any) -> Any:
    return await tickets.assign(
        conn,
        breach_uuid=uuid,
        full_name=kw.get("full_name", "Ravi Engineer"),
        email=email,
        mobile=None,
        instruction="Pull the guest network's firewall log",
        answer_by=None,
        actor_id=_dpo(seeded),
    )


async def _account(conn: Any, email_hash_of: str) -> dict[str, Any]:
    row = await fetch_one(
        conn,
        """SELECT id, uuid, role::text AS role, status::text AS status, person_type::text
                  AS person_type, password_hash
             FROM auth_user WHERE email_hash = %s""",
        (hashed("email", email_hash_of),),
    )
    assert row is not None
    return row


async def _close_breach(conn: Any, seeded: dict[str, Any], uuid: str) -> None:
    """Close every ticket, set the duties aside, and close the breach."""
    for t in await tickets.for_breach(conn, breach_uuid=uuid):
        if t["state"] == "issued":
            await tickets.office_move(
                conn,
                breach_uuid=uuid,
                ticket_uuid=str(t["ticket_uuid"]),
                move="withdraw",
                reason="Not needed",
                actor_id=_dpo(seeded),
            )
        elif t["state"] == "returned":
            await tickets.office_move(
                conn,
                breach_uuid=uuid,
                ticket_uuid=str(t["ticket_uuid"]),
                move="close",
                reason=None,
                actor_id=_dpo(seeded),
            )
    await service.determine(
        conn,
        breach_uuid=uuid,
        outcome="no",
        reasoning="Contained before it reached anyone",
        became_aware_at=None,
        actor_id=_dpo(seeded),
    )
    await service.transition(
        conn, breach_uuid=uuid, to="closed", reason=None, actor_id=_dpo(seeded)
    )


async def test_a_principal_is_given_access_and_keeps_a_read_only_login(
    conn: Any, seeded: dict[str, Any], mailed: list[str]
) -> None:
    """Written first. The regression this guards: ending staff access marks a
    person an ex-employee, which a data principal asked about one breach is
    not. When the breach closes their login stays, to read the ticket
    (decided 2026-10-06); person_type is untouched throughout."""
    uuid = await _recorded(conn, seeded)
    before = await _account(conn, "subject@test.local")
    made = await _by_email(conn, seeded, uuid, "subject@test.local")
    during = await _account(conn, "subject@test.local")
    assert during["role"] == "breach_holder" and during["status"] == before["status"]
    assert made["ticket"]["temporary_access"] == "active"
    assert "cmp.notifications.send_breach_ticket_access" in mailed
    assert "cmp.notifications.send_breach_ticket_waiting" not in mailed, "the access email instead"

    t = str(made["ticket"]["ticket_uuid"])
    await tickets.return_ticket(
        conn, user_id=int(during["id"]), ticket_uuid=t, summary="Pulled", outcome="done"
    )
    await _close_breach(conn, seeded, uuid)

    after = await _account(conn, "subject@test.local")
    assert (after["role"], after["status"]) == ("breach_holder", before["status"])
    assert after["person_type"] == before["person_type"], "never ex_employee"
    [grant] = await fetch_all(
        conn,
        "SELECT end_cause, previous_role::text AS previous FROM breach_temporary_access"
        " WHERE user_id = %s",
        (int(during["id"]),),
    )
    assert grant == {"end_cause": "breach_closed", "previous": "data_subject"}

    # Read only: the ticket is still theirs to read, and nothing more.
    read = await tickets.my_detail(conn, user_id=int(during["id"]), ticket_uuid=t)
    assert read["ticket"]["moves"] == [] and read["ticket"]["may_add_colleague"] is False
    with pytest.raises(Conflict):
        await tickets.holder_message(
            conn, user_id=int(during["id"]), ticket_uuid=t, body="One more thing"
        )


async def test_an_account_made_for_the_breach_stays_after_the_end(
    conn: Any, seeded: dict[str, Any], mailed: list[str]
) -> None:
    uuid = await _recorded(conn, seeded)
    made = await _by_email(conn, seeded, uuid, "new.engineer@test.local")
    new = await _account(conn, "new.engineer@test.local")
    assert (new["role"], new["status"], new["person_type"]) == (
        "breach_holder",
        "pending",
        "employee",
    )
    assert made["ticket"]["temporary_access"] == "pending"
    with pytest.raises(ValidationFailed):
        await _by_email(conn, seeded, uuid, "nobody.named@test.local", full_name=" ")

    await _close_breach(conn, seeded, uuid)
    ended = await _account(conn, "new.engineer@test.local")
    assert (ended["role"], ended["status"], ended["person_type"]) == (
        "breach_holder",
        "pending",
        "employee",
    ), "left as it was: they can still set a password and read their ticket"


async def test_staff_named_by_email_get_an_ordinary_ticket(
    conn: Any, seeded: dict[str, Any], mailed: list[str]
) -> None:
    uuid = await _recorded(conn, seeded)
    made = await _by_email(conn, seeded, uuid, "dco@test.local")
    assert made["ticket"]["temporary_access"] is None
    assert mailed == ["cmp.notifications.send_breach_ticket_waiting"]
    assert (await _account(conn, "dco@test.local"))["role"] == "dco"


async def test_an_external_address_is_refused_before_anything_is_made(
    conn: Any, seeded: dict[str, Any]
) -> None:
    uuid = await _recorded(conn, seeded)
    with pytest.raises(ValidationFailed) as refused:
        await _by_email(conn, seeded, uuid, "someone@elsewhere.example")
    assert "elsewhere" not in refused.value.message
    row = await fetch_one(
        conn,
        "SELECT count(*) AS n FROM auth_user WHERE email_hash = %s",
        (hashed("email", "someone@elsewhere.example"),),
    )
    assert row is not None and row["n"] == 0


async def test_a_kept_login_asked_again_is_told_a_ticket_is_waiting(
    conn: Any, seeded: dict[str, Any], mailed: list[str]
) -> None:
    """A second breach for somebody who already signs in: no new password to
    set, so the waiting notice, and the first grant's previous role carried."""
    first = await _recorded(conn, seeded)
    second = await _recorded(conn, seeded)
    await _by_email(conn, seeded, first, "subject@test.local")
    await _close_breach(conn, seeded, first)
    mailed.clear()
    made = await _by_email(conn, seeded, second, "subject@test.local")
    assert made["ticket"]["temporary_access"] == "active"
    assert mailed == ["cmp.notifications.send_breach_ticket_waiting"]
    grants = await fetch_all(
        conn,
        """SELECT previous_role::text AS previous FROM breach_temporary_access a
             JOIN breach b USING (breach_id)
            WHERE b.breach_uuid = ANY(%s) ORDER BY access_id""",
        ([first, second],),
    )
    assert [g["previous"] for g in grants] == ["data_subject", "data_subject"]


async def test_a_promotion_meanwhile_is_left_alone_and_keeps_the_ticket(
    conn: Any, seeded: dict[str, Any], mailed: list[str]
) -> None:
    uuid = await _recorded(conn, seeded)
    made = await _by_email(conn, seeded, uuid, "subject@test.local")
    holder = await _account(conn, "subject@test.local")
    await users.change_role(
        conn,
        str(holder["uuid"]),
        role="dco",
        reason="Joined the team",
        actor_id=int(seeded["users"]["admin"]["id"]),
    )
    await _close_breach(conn, seeded, uuid)
    assert (await _account(conn, "subject@test.local"))["role"] == "dco"
    mine = await tickets.mine(conn, user_id=int(holder["id"]))
    assert [m["ticket_uuid"] for m in mine] == [made["ticket"]["ticket_uuid"]]


async def test_withdrawing_ends_the_grant_and_reopening_restores_it(
    conn: Any, seeded: dict[str, Any], mailed: list[str]
) -> None:
    uuid = await _recorded(conn, seeded)
    made = await _by_email(conn, seeded, uuid, "subject@test.local")
    t = str(made["ticket"]["ticket_uuid"])
    withdrawn = await tickets.office_move(
        conn,
        breach_uuid=uuid,
        ticket_uuid=t,
        move="withdraw",
        reason="Wrong person",
        actor_id=_dpo(seeded),
    )
    assert withdrawn["ticket"]["temporary_access"] == "ended"
    assert (await _account(conn, "subject@test.local"))["role"] == "breach_holder"

    mailed.clear()
    reopened = await tickets.office_move(
        conn,
        breach_uuid=uuid,
        ticket_uuid=t,
        move="reopen",
        reason="Right person after all",
        actor_id=_dpo(seeded),
    )
    assert reopened["ticket"]["temporary_access"] == "active"
    assert mailed == ["cmp.notifications.send_breach_ticket_waiting"], "they still sign in"
    rows = await fetch_all(
        conn,
        """SELECT end_cause FROM breach_temporary_access a JOIN breach b USING (breach_id)
            WHERE b.breach_uuid = %s ORDER BY access_id""",
        (uuid,),
    )
    assert [r["end_cause"] for r in rows] == ["ticket_withdrawn", None]


async def test_an_administrator_ending_it_puts_the_account_back(
    conn: Any, seeded: dict[str, Any], mailed: list[str]
) -> None:
    """The one off switch: an existing principal goes back to data_subject, an
    account made for a breach is switched off, and both lose the password."""
    admin = int(seeded["users"]["admin"]["id"])
    uuid = await _recorded(conn, seeded)
    await _by_email(conn, seeded, uuid, "subject@test.local")
    await _by_email(conn, seeded, uuid, "made.here@test.local")
    holder = await _account(conn, "subject@test.local")
    made = await _account(conn, "made.here@test.local")

    _, kept = await users.deactivate(conn, str(holder["uuid"]), actor_id=admin)
    after = await _account(conn, "subject@test.local")
    assert kept and after["role"] == "data_subject" and after["password_hash"] is None
    assert after["person_type"] == holder["person_type"]

    _, kept = await users.deactivate(conn, str(made["uuid"]), actor_id=admin)
    gone = await _account(conn, "made.here@test.local")
    assert not kept and gone["status"] == "deactivated" and gone["password_hash"] is None

    causes = await fetch_all(
        conn,
        "SELECT end_cause FROM breach_temporary_access WHERE user_id = ANY(%s)",
        ([holder["id"], made["id"]],),
    )
    assert {c["end_cause"] for c in causes} == {"account_deactivated"}

    # Asked again after that: a new password through the access email.
    mailed.clear()
    second = await _recorded(conn, seeded)
    await _by_email(conn, seeded, second, "made.here@test.local")
    assert (await _account(conn, "made.here@test.local"))["status"] == "pending"
    assert mailed == ["cmp.notifications.send_breach_ticket_access"]


async def test_resending_a_pending_holders_invitation_sends_the_access_email(
    conn: Any, seeded: dict[str, Any], mailed: list[str]
) -> None:
    """Not the staff invitation, which would welcome them to a role they do not have."""
    uuid = await _recorded(conn, seeded)
    await _by_email(conn, seeded, uuid, "late.reader@test.local")
    holder = await _account(conn, "late.reader@test.local")
    mailed.clear()
    await users.resend_invitation(conn, str(holder["uuid"]))
    assert mailed == ["cmp.notifications.send_breach_ticket_access"]


async def test_the_role_is_never_granted_by_hand(conn: Any, seeded: dict[str, Any]) -> None:
    admin = int(seeded["users"]["admin"]["id"])
    with pytest.raises(ValidationFailed):
        await users.create_staff(
            conn,
            full_name="X",
            email="x@test.local",
            role="breach_holder",
            username=None,
            mobile=None,
            organization_id=None,
            person_type=None,
            source_uuids=[],
        )
    with pytest.raises(ValidationFailed):
        await users.change_role(
            conn,
            str(seeded["users"]["dco"]["uuid"]),
            role="breach_holder",
            reason=None,
            actor_id=admin,
        )


class TestColleagues:
    async def test_a_chain_two_deep_each_with_only_the_adders_note(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _recorded(conn, seeded)
        first = await tickets.assign(
            conn,
            breach_uuid=uuid,
            user_uuid=str(seeded["users"]["dco"]["uuid"]),
            instruction="The DPO's instruction, for the DCO only",
            answer_by=None,
            actor_id=_dpo(seeded),
        )
        mine = str(first["ticket"]["ticket_uuid"])
        await tickets.add_colleague(
            conn,
            user_id=int(seeded["users"]["dco"]["id"]),
            ticket_uuid=mine,
            full_name="Colleague One",
            email="one@test.local",
            mobile=None,
            note="Please check the switch config",
        )
        one = await _account(conn, "one@test.local")
        [theirs] = await tickets.mine(conn, user_id=int(one["id"]))
        detail = await tickets.my_detail(
            conn, user_id=int(one["id"]), ticket_uuid=str(theirs["ticket_uuid"])
        )
        from tests.conftest import plain

        assert plain(detail["ticket"]["instruction"]) == "Please check the switch config"
        assert "The DPO's instruction" not in str(detail)
        await tickets.add_colleague(
            conn,
            user_id=int(one["id"]),
            ticket_uuid=str(theirs["ticket_uuid"]),
            full_name="Colleague Two",
            email="two@test.local",
            mobile=None,
            note="And the access points",
        )
        rows = await tickets.for_breach(conn, breach_uuid=uuid)
        by_parent = {str(r["ticket_uuid"]): r["parent_ticket_uuid"] for r in rows}
        assert len(rows) == 3
        chain = [r for r in rows if r["parent_ticket_uuid"]]
        assert len(chain) == 2 and all(str(p) in by_parent for p in by_parent.values() if p)
        events = await fetch_all(
            conn,
            "SELECT count(*) AS n FROM audit_log WHERE event_type = 'breach_ticket.colleague_added'"
            " AND entity_id IN (SELECT ticket_id FROM breach_ticket WHERE breach_id ="
            " (SELECT breach_id FROM breach WHERE breach_uuid = %s))",
            (uuid,),
        )
        assert events[0]["n"] == 2

    async def test_the_adders_answer_is_the_same_whatever_the_colleague_had(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _recorded(conn, seeded)
        first = await tickets.assign(
            conn,
            breach_uuid=uuid,
            user_uuid=str(seeded["users"]["dco"]["uuid"]),
            instruction="Look",
            answer_by=None,
            actor_id=_dpo(seeded),
        )
        mine = str(first["ticket"]["ticket_uuid"])
        answers = []
        for email in ("rco@test.local", "subject@test.local", "brand.new@test.local"):
            answer = await tickets.add_colleague(
                conn,
                user_id=int(seeded["users"]["dco"]["id"]),
                ticket_uuid=mine,
                full_name="Someone",
                email=email,
                mobile=None,
                note="Help, please",
            )
            answers.append(
                {
                    k: v
                    for k, v in answer["ticket"].items()
                    if k not in ("unread", "last_activity_at")
                }
            )
        assert answers[0] == answers[1] == answers[2]

    async def test_the_domain_check_and_one_ticket_each_apply_to_colleagues(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _recorded(conn, seeded)
        first = await tickets.assign(
            conn,
            breach_uuid=uuid,
            user_uuid=str(seeded["users"]["dco"]["uuid"]),
            instruction="Look",
            answer_by=None,
            actor_id=_dpo(seeded),
        )
        mine = str(first["ticket"]["ticket_uuid"])
        with pytest.raises(ValidationFailed):
            await tickets.add_colleague(
                conn,
                user_id=int(seeded["users"]["dco"]["id"]),
                ticket_uuid=mine,
                full_name="Out",
                email="out@elsewhere.example",
                mobile=None,
                note="x",
            )
        await tickets.add_colleague(
            conn,
            user_id=int(seeded["users"]["dco"]["id"]),
            ticket_uuid=mine,
            full_name="In",
            email="rco@test.local",
            mobile=None,
            note="x",
        )
        with pytest.raises(Conflict) as again:
            await tickets.add_colleague(
                conn,
                user_id=int(seeded["users"]["dco"]["id"]),
                ticket_uuid=mine,
                full_name="In",
                email="rco@test.local",
                mobile=None,
                note="x",
            )
        assert again.value.code == "colleague_not_added"


async def test_a_grant_is_ended_once_and_never_deleted(
    conn: Any, seeded: dict[str, Any], mailed: list[str]
) -> None:
    import psycopg

    uuid = await _recorded(conn, seeded)
    await _by_email(conn, seeded, uuid, "subject@test.local")
    await _close_breach(conn, seeded, uuid)
    with pytest.raises(psycopg.errors.RestrictViolation):
        async with conn.transaction():
            await conn.execute(
                """UPDATE breach_temporary_access SET end_cause = 'ticket_withdrawn'
                    WHERE breach_id = (SELECT breach_id FROM breach WHERE breach_uuid = %s)""",
                (uuid,),
            )
    with pytest.raises(psycopg.errors.RestrictViolation):
        async with conn.transaction():
            await conn.execute(
                """DELETE FROM breach_temporary_access
                    WHERE breach_id = (SELECT breach_id FROM breach WHERE breach_uuid = %s)""",
                (uuid,),
            )
