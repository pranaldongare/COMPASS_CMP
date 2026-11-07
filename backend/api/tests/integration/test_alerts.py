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
    validated = await breach_service.determine(
        conn,
        breach_uuid=str(made["breach_uuid"]),
        outcome="yes",
        reasoning="Yes",
        became_aware_at=detected,
        actor_id=int(seeded["users"]["dpo"]["id"]),
    )
    # The organisation's board, by default: thirty minutes from the validation.
    [due] = [d["due_at"] for d in validated["obligations"] if d["duty"] == "org_board"]
    dpo = await _email(conn, int(seeded["users"]["dpo"]["id"]))

    # By the breach first: every open breach in the database is swept with this
    # one, and opening an address is a call to the key service.
    def mine() -> list[tuple[Any, ...]]:
        return [
            a
            for n, a in queued
            if n == "send_breach_duty_due"
            and a[5] == str(made["breach_uuid"])
            and plain(a[0]) == dpo
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


async def test_a_reinstated_duty_is_a_new_clock_and_says_so_again(
    conn: Any, seeded: dict[str, Any], queued: list[Any], redis_conn: Any
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    aware = datetime.now(UTC) - timedelta(minutes=10)
    made = await breach_service.record(
        conn,
        title="A list sent to the wrong address",
        detected_at=aware,
        began_at=None,
        location_kind="platform",
        processor_uuid=None,
        source_uuid=None,
        location_detail=None,
        actor_id=dpo,
    )
    uuid = str(made["breach_uuid"])

    async def determine(outcome: str) -> dict[str, Any]:
        return await breach_service.determine(
            conn,
            breach_uuid=uuid,
            outcome=outcome,
            reasoning=outcome,
            became_aware_at=aware if outcome == "yes" else None,
            actor_id=dpo,
        )

    [first] = [
        d["due_at"] for d in (await determine("yes"))["obligations"] if d["duty"] == "org_board"
    ]
    email = await _email(conn, dpo)

    def overdue() -> list[tuple[Any, ...]]:
        return [
            a
            for n, a in queued
            if n == "send_breach_duty_due"
            and a[5] == uuid
            and a[2] == "Organisation's board"
            and a[4].startswith("overdue")
            and plain(a[0]) == email
        ]

    await alerts.breach_duties(conn, now=first + timedelta(minutes=1))
    assert len(overdue()) == 1
    await determine("no")
    await determine("yes")
    detail = await breach_service.detail(conn, uuid)
    [second] = [d["due_at"] for d in detail["obligations"] if d["duty"] == "org_board"]
    assert second > first
    await alerts.breach_duties(conn, now=second + timedelta(minutes=1))
    await alerts.breach_duties(conn, now=second + timedelta(minutes=6))
    assert len(overdue()) == 2, "its own clock, said once"


async def test_a_reinstated_duty_is_warned_of_from_its_own_anchor(
    conn: Any, seeded: dict[str, Any], queued: list[Any], redis_conn: Any
) -> None:
    """Twelve of the report's seventy-two hours, from the moment it was
    reinstated: not a sixth of the time since the first awareness."""
    dpo = int(seeded["users"]["dpo"]["id"])
    now = datetime.now(UTC)
    made = await breach_service.record(
        conn,
        title="A list sent to the wrong address",
        detected_at=now - timedelta(hours=61),
        began_at=None,
        location_kind="platform",
        processor_uuid=None,
        source_uuid=None,
        location_detail=None,
        actor_id=dpo,
    )
    uuid = str(made["breach_uuid"])
    for outcome, aware in (
        ("yes", now - timedelta(hours=60)),
        ("no", None),
        ("yes", now),
    ):
        detail = await breach_service.determine(
            conn,
            breach_uuid=uuid,
            outcome=outcome,
            reasoning=outcome,
            became_aware_at=aware,
            actor_id=dpo,
        )
    [due] = [d["due_at"] for d in detail["obligations"] if d["duty"] == "board_report"]

    def said() -> list[tuple[Any, ...]]:
        return [
            a
            for n, a in queued
            if n == "send_breach_duty_due" and a[5] == uuid and a[2] == "Board - detailed report"
        ]

    await alerts.breach_duties(conn, now=due - timedelta(hours=20))
    assert said() == [], "twenty hours left is not the last sixth of this clock"
    await alerts.breach_duties(conn, now=due - timedelta(hours=11))
    assert said()


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
        """INSERT INTO auth_user (full_name, email, email_hash, role, status, office_id)
           VALUES ('Second DPO', 'dpo2@test.local', 'h-dpo2', 'dpo', 'active',
               (SELECT office_id FROM office WHERE office_code = 'rnd'))"""
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


# ------------------------------------------- the organisation's board list (0064)


async def _officers(conn: Any) -> list[str]:
    """Every active DPO and Legal account, as stored: whoever keeps a breach.
    Compared as stored, since this database holds hundreds from earlier runs."""
    from cmp.db.repositories import incident_reports

    return sorted(await incident_reports.active_emails(conn, ["dpo", "legal"]))


def _list_changed(queued: list[tuple[str, tuple[Any, ...]]]) -> list[tuple[Any, ...]]:
    return [args for name, args in queued if name == "send_breach_board_list_changed"]


async def test_a_change_to_the_board_list_reaches_both_offices_officers_naming_the_address(
    conn: Any, seeded: dict[str, Any], queued: list[Any]
) -> None:
    from uuid import uuid4

    from cmp.domain.breach import settings as breach_settings
    from tests.integration.test_rights_by_office import _legal_poc

    admin = int(seeded["users"]["admin"]["id"])
    dpo = int(seeded["users"]["dpo"]["id"])
    legal = await _legal_poc(conn)
    officers = await _officers(conn)
    address = f"chair.{uuid4().hex[:8]}@example.org"

    added = await breach_settings.add_board_recipient(
        conn, full_name="The Chair", email=address, actor_id=admin
    )
    [entry] = [r for r in added["board_recipients"] if plain(r["email"]) == address]
    recipient = str(entry["recipient_uuid"])
    steps = [
        ("Administrator", "added this address to"),
        ("Data Protection Officer", "made this address mandatory on"),
        ("Legal PoC", "made this address optional again on"),
        ("Data Protection Officer", "took this address off"),
    ]
    await breach_settings.set_board_recipient_mandatory(
        conn, recipient_uuid=recipient, mandatory=True, actor_id=dpo
    )
    await breach_settings.set_board_recipient_mandatory(
        conn, recipient_uuid=recipient, mandatory=False, actor_id=legal
    )
    await breach_settings.remove_board_recipient(conn, recipient_uuid=recipient, actor_id=dpo)

    told = _list_changed(queued)
    assert len(told) == len(steps) * len(officers), "each change, once to each officer"
    for i, (role, change) in enumerate(steps):
        batch = told[i * len(officers) : (i + 1) * len(officers)]
        assert sorted(str(args[0]) for args in batch) == officers
        assert {args[1:] for args in batch} == {batch[0][1:]}, "the same words to each"
        _, actor_name, actor_role, words, name, email, when = batch[0]
        assert (actor_role, words) == (role, change)
        assert str(name).startswith("SE::") and str(email).startswith("SE::"), "opened at send"
        assert (plain(name), plain(email)) == ("The Chair", address)
        assert plain(actor_name) and "UTC" in when
        assert not any(s in str(batch[0]) for s in ("BR-", "INC-", "/breaches/"))


async def test_with_no_officer_to_tell_it_says_so_at_error_and_the_change_stands(
    conn: Any, seeded: dict[str, Any], queued: list[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from cmp.db.repositories import incident_reports
    from cmp.domain.breach import settings as breach_settings

    logged: list[tuple[str, dict[str, Any]]] = []

    class Log:
        def error(self, event: str, **fields: Any) -> None:
            logged.append((event, fields))

    async def nobody(*_: Any) -> list[str]:
        return []

    monkeypatch.setattr(incident_reports, "active_emails", nobody)
    monkeypatch.setattr(alerts, "log", Log())
    added = await breach_settings.add_board_recipient(
        conn,
        full_name=None,
        email="nobody.told@example.org",
        actor_id=int(seeded["users"]["admin"]["id"]),
    )
    assert "nobody.told@example.org" in {plain(r["email"]) for r in added["board_recipients"]}
    assert _list_changed(queued) == []
    assert logged == [("breach_settings.nobody_to_tell", {"change": "added"})]


async def test_a_broker_that_cannot_be_reached_refuses_the_change(
    conn: Any, seeded: dict[str, Any], queued: list[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The officers' mail is the check on the list: a change nobody could be
    told of is not made."""
    from cmp.core.errors import ServiceUnavailable
    from cmp.domain.breach import settings as breach_settings

    dpo = int(seeded["users"]["dpo"]["id"])
    added = await breach_settings.add_board_recipient(
        conn, full_name=None, email="kept@example.org", actor_id=dpo
    )
    [entry] = [r for r in added["board_recipients"] if plain(r["email"]) == "kept@example.org"]
    recipient = str(entry["recipient_uuid"])
    trail = await conn.execute(
        "SELECT count(*) AS n FROM audit_log WHERE event_type = 'breach_settings.changed'"
    )
    before = (await trail.fetchone())["n"]
    queued.clear()

    def down() -> None:
        raise ConnectionRefusedError("the broker is down")

    monkeypatch.setattr(dispatch_mod, "_touch_broker", down)
    with pytest.raises(ServiceUnavailable):
        await breach_settings.add_board_recipient(
            conn, full_name=None, email="refused@example.org", actor_id=dpo
        )
    with pytest.raises(ServiceUnavailable):
        await breach_settings.set_board_recipient_mandatory(
            conn, recipient_uuid=recipient, mandatory=True, actor_id=dpo
        )
    with pytest.raises(ServiceUnavailable):
        await breach_settings.remove_board_recipient(conn, recipient_uuid=recipient, actor_id=dpo)
    kept = {
        plain(r["email"]): r for r in (await breach_settings.overview(conn))["board_recipients"]
    }
    assert "refused@example.org" not in kept
    assert kept["kept@example.org"]["mandatory"] is False
    trail = await conn.execute(
        "SELECT count(*) AS n FROM audit_log WHERE event_type = 'breach_settings.changed'"
    )
    assert (await trail.fetchone())["n"] == before and queued == []


async def test_a_mark_that_changes_nothing_tells_nobody(
    conn: Any, seeded: dict[str, Any], queued: list[Any]
) -> None:
    from cmp.domain.breach import settings as breach_settings

    dpo = int(seeded["users"]["dpo"]["id"])
    added = await breach_settings.add_board_recipient(
        conn, full_name=None, email="as.it.was@example.org", actor_id=dpo
    )
    [entry] = [r for r in added["board_recipients"] if plain(r["email"]) == "as.it.was@example.org"]
    queued.clear()
    await breach_settings.set_board_recipient_mandatory(
        conn, recipient_uuid=str(entry["recipient_uuid"]), mandatory=False, actor_id=dpo
    )
    assert queued == []
