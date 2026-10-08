"""The office's and staff's own emails about their work (2026-10-08).

Who is told, about what, and only after the act: a project closed reaches its
owner; a rights request from outside reaches every DPO, one the office logged
reaches nobody; a grievance about the DPO reaches the administrators; the
daily list names what is due; a breach duty about to fall due is said once,
and again once overdue; a role changed, access ended or cover arranged reaches
the people concerned. Each is a queued task - one per recipient - never a send
inside the transaction.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from cmp.core.permissions import Role
from cmp.domain import alerts
from cmp.domain.breach import service as breach_service
from cmp.domain.delegations import service as delegations
from cmp.domain.projects import service as projects
from cmp.domain.rights import service as rights
from cmp.domain.users import service as users
from cmp.tasks import dispatch as dispatch_mod
from tests.conftest import plain

pytestmark = pytest.mark.integration


@pytest.fixture
def queued(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, tuple[Any, ...]]]:
    sent: list[tuple[str, tuple[Any, ...]]] = []

    def capture(task: Any, *args: Any, **kwargs: Any) -> str:
        sent.append((task.name.rsplit(".", 1)[-1], args))
        return "queued-in-a-test"

    monkeypatch.setattr(dispatch_mod, "dispatch_optional", capture)
    return sent


def _to(queued: list[tuple[str, tuple[Any, ...]]], task: str) -> list[str]:
    return [str(plain(args[0])) for name, args in queued if name == task]


async def _email(conn: Any, user_id: int) -> str:
    row = await (
        await conn.execute("SELECT email FROM auth_user WHERE id = %s", (user_id,))
    ).fetchone()
    return str(plain(row["email"]))


async def test_a_project_closed_reaches_its_owner(
    conn: Any, seeded: dict[str, Any], queued: list[Any]
) -> None:
    await projects.close(
        conn,
        project_uuid=str(seeded["project"]["project_uuid"]),
        actor_id=int(seeded["users"]["dpo"]["id"]),
        role=Role.DPO,
        reason="The study has ended.",
    )
    owner = await _email(conn, int(seeded["users"]["rnd_user"]["id"]))
    assert _to(queued, "send_project_closed") == [owner]
    [(_, args)] = [q for q in queued if q[0] == "send_project_closed"]
    assert args[4] == "The study has ended."


async def test_a_submitted_project_reaches_every_dpo_and_the_rest_its_owner(
    conn: Any, seeded: dict[str, Any], queued: list[Any]
) -> None:
    project = {
        "project_name": "Gait Study",
        "project_uuid": str(seeded["project"]["project_uuid"]),
        "created_by": int(seeded["users"]["rnd_user"]["id"]),
    }
    rnd = int(seeded["users"]["rnd_user"]["id"])
    await alerts.project_moved(
        conn, project=project, to="pending_approval", reason=None, actor_id=rnd
    )
    dpo = await _email(conn, int(seeded["users"]["dpo"]["id"]))
    assert dpo in _to(queued, "send_project_submitted")
    for to, task in (
        ("approved", "send_project_approved"),
        ("in_draft", "send_project_sent_back"),
    ):
        await alerts.project_moved(conn, project=project, to=to, reason="Add Hindi", actor_id=1)
        assert _to(queued, task) == [await _email(conn, rnd)]


async def test_a_request_from_outside_reaches_every_dpo_never_with_her_words(
    conn: Any, seeded: dict[str, Any], queued: list[Any]
) -> None:
    made = await rights.create(
        conn,
        request_type="erasure",
        channel="portal",
        request_text="Please erase my gait videos",
        submitted_contact="subject@test.local",
        submitted_name="Test Subject",
        subject_user_id=seeded["subject"]["id"],
        actor_id=seeded["subject"]["id"],
        verification_method="session",
    )
    dpo = await _email(conn, int(seeded["users"]["dpo"]["id"]))
    assert dpo in _to(queued, "send_rights_request_received")
    [args] = [a for n, a in queued if n == "send_rights_request_received" and plain(a[0]) == dpo]
    assert args[1] == made["reference"] and args[2] == "erasure"
    assert "gait" not in " ".join(str(a) for a in args).lower()

    queued.clear()
    await rights.create(
        conn,
        request_type="access",
        channel="staff_logged",
        request_text="Logged from an email",
        submitted_contact="subject@test.local",
        actor_id=int(seeded["users"]["dpo"]["id"]),
    )
    assert _to(queued, "send_rights_request_received") == []


async def test_a_grievance_about_the_dpo_reaches_the_administrators(
    conn: Any, seeded: dict[str, Any], queued: list[Any]
) -> None:
    row = await rights.create(
        conn,
        request_type="grievance",
        channel="portal",
        request_text="The DPO ignored me",
        submitted_contact="subject@test.local",
        subject_user_id=seeded["subject"]["id"],
        actor_id=seeded["subject"]["id"],
        verification_method="session",
    )
    await rights.escalate(conn, row, role=Role.DPO, actor_id=int(seeded["users"]["dpo"]["id"]))
    admin = await _email(conn, int(seeded["users"]["admin"]["id"]))
    assert admin in _to(queued, "send_rights_grievance_about_dpo")


async def test_the_daily_list_names_what_is_due(
    conn: Any, seeded: dict[str, Any], queued: list[Any]
) -> None:
    row = await rights.create(
        conn,
        request_type="access",
        channel="portal",
        request_text="Everything",
        submitted_contact="subject@test.local",
        subject_user_id=seeded["subject"]["id"],
        actor_id=seeded["subject"]["id"],
        verification_method="session",
    )
    await conn.execute(
        """UPDATE rights_request SET received_at = now() - interval '40 days',
                  due_at = now() - interval '2 days' WHERE request_id = %s""",
        (int(row["request_id"]),),
    )
    listed = await alerts.rights_due(conn)
    assert listed >= 1
    dpo = await _email(conn, int(seeded["users"]["dpo"]["id"]))
    [args] = [a for n, a in queued if n == "send_rights_due_digest" and plain(a[0]) == dpo]
    assert f"{row['reference']} access" in args[2] and "overdue by 2 days" in args[2]


async def test_a_breach_duty_is_said_once_when_due_soon_and_once_when_overdue(
    conn: Any, seeded: dict[str, Any], queued: list[Any], redis_conn: Any
) -> None:
    detected = datetime.now(UTC) - timedelta(minutes=10)
    made = await breach_service.record(
        conn,
        title="A list sent to the wrong address",
        detected_at=detected,
        began_at=None,
        location_kind="platform",
        processor_uuid=None,
        source_uuid=None,
        location_detail=None,
        actor_id=int(seeded["users"]["dpo"]["id"]),
    )
    due = detected + timedelta(minutes=30)  # the organisation's board, by default
    dpo = await _email(conn, int(seeded["users"]["dpo"]["id"]))

    def mine() -> list[tuple[Any, ...]]:
        return [
            a
            for n, a in queued
            if n == "send_breach_duty_due"
            and plain(a[0]) == dpo
            and a[5] == str(made["breach_uuid"])
        ]

    await alerts.breach_duties(conn, now=due - timedelta(minutes=20))  # not yet
    assert mine() == []
    await alerts.breach_duties(conn, now=due - timedelta(minutes=4))
    await alerts.breach_duties(conn, now=due - timedelta(minutes=3))  # said once
    [soon] = mine()
    assert soon[2] == "Organisation's board" and soon[4].startswith("due in")
    await alerts.breach_duties(conn, now=due + timedelta(minutes=1))
    await alerts.breach_duties(conn, now=due + timedelta(minutes=6))
    assert [a[4].split(" ")[0] for a in mine()] == ["due", "overdue"]


async def test_role_access_and_cover_reach_the_people_concerned(
    conn: Any, seeded: dict[str, Any], queued: list[Any]
) -> None:
    admin = int(seeded["users"]["admin"]["id"])
    dco = seeded["users"]["dco"]
    await users.change_role(conn, str(dco["uuid"]), role="dco_admin", reason=None, actor_id=admin)
    dco_email = await _email(conn, int(dco["id"]))
    [(_, args)] = [q for q in queued if q[0] == "send_staff_role_changed"]
    assert plain(args[0]) == dco_email and args[2:] == ("Data Collection Owner", "DCO Admin")

    rco = seeded["users"]["rco"]
    await users.deactivate(conn, str(rco["uuid"]), actor_id=admin)
    assert _to(queued, "send_staff_access_ended") == [await _email(conn, int(rco["id"]))]

    await conn.execute(
        """INSERT INTO auth_user (full_name, email, email_hash, role, status)
           VALUES ('Second DPO', 'dpo2@test.local', 'h-dpo2', 'dpo', 'active')"""
    )
    second = await (
        await conn.execute("SELECT id, uuid FROM auth_user WHERE email = 'dpo2@test.local'")
    ).fetchone()
    await delegations.grant(
        conn,
        delegator_uuid=str(seeded["users"]["dpo"]["uuid"]),
        delegate_uuid=str(second["uuid"]),
        reason="Leave",
        starts_at=None,
        ends_at=datetime.now(UTC) + timedelta(days=7),
        actor_id=int(seeded["users"]["dpo"]["id"]),
        actor_role=Role.DPO,
    )
    assert sorted(_to(queued, "send_delegation_arranged")) == sorted(
        [await _email(conn, int(seeded["users"]["dpo"]["id"])), "dpo2@test.local"]
    )
