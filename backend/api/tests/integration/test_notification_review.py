"""The messages the notification review of 2026-11-20 added.

Each event the review found nobody was told of now reaches the people it
concerns, as one queued task per recipient: a password changed or a sign-in
step reset reaches its holder; a suspended processor, a deactivated site, a
collector asked for reach the project's people; a withdrawal on an R&D project
reaches its owner and collector by reference only; a broken audit chain and a
changed setting reach everybody who answers for the platform; notices that
fail are said once, not once per person. And the Legal PoC may change the
words of a message with legal weight, and no other.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest

from cmp.core.errors import Forbidden
from cmp.core.permissions import Role
from cmp.domain import alerts
from cmp.domain.messaging import service as messaging
from cmp.domain.projects import service as projects
from cmp.domain.registry import service as registry
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
    return sorted(str(plain(args[0])) for name, args in queued if name == task)


async def _add_legal(conn: Any) -> int:
    from tests.conftest import hashed

    email = f"legal-{uuid4().hex[:6]}@test.local"
    row = await (
        await conn.execute(
            """INSERT INTO auth_user (full_name, email, email_hash, role, status, password_hash,
                                      office_id)
               VALUES ('Test legal', %s, %s, 'legal'::user_role, 'active', 'x',
                       (SELECT office_id FROM office WHERE office_code = 'hr'))
               RETURNING id""",
            (email, hashed("email", email)),
        )
    ).fetchone()
    return int(row["id"])


class TestSecurity:
    async def test_a_password_changed_reaches_its_holder(
        self, conn: Any, seeded: dict[str, Any], queued: list[Any]
    ) -> None:
        from cmp.auth.authentication import service as auth

        dpo = int(seeded["users"]["dpo"]["id"])
        await auth.change_password(
            conn,
            user_id=dpo,
            current_password="TestPassw0rd!123",
            new_password="An0ther-Passw0rd!456",
        )
        assert _to(queued, "send_password_changed") == ["dpo@test.local"]

    async def test_a_sign_in_step_reset_reaches_its_holder(
        self, conn: Any, seeded: dict[str, Any], queued: list[Any]
    ) -> None:
        await users.reset_mfa(conn, str(seeded["users"]["dco"]["uuid"]))
        assert _to(queued, "send_mfa_reset") == ["dco@test.local"]

    async def test_a_contact_changed_reaches_the_contacts_already_there(
        self, queued: list[Any], conn: Any
    ) -> None:
        before = {
            "role": "data_subject",
            "email": "her@test.local",
            "email_verified_at": datetime.now(UTC),
            "mobile": "+915550000009",
            "mobile_verified_at": datetime.now(UTC),
            "secondary_email": None,
        }
        await alerts.contact_changed(
            conn, before=before, medium="mobile", action="set", by_admin=False
        )
        assert _to(queued, "send_contact_changed") == ["+915550000009", "her@test.local"]
        [(_, args)] = queued[:1]
        assert "mobile number" in args[1] and "+91" not in args[1], "the new contact is not named"


class TestProjects:
    async def test_a_suspended_processor_reaches_each_projects_owner_and_collector(
        self, conn: Any, seeded: dict[str, Any], queued: list[Any]
    ) -> None:
        await registry.suspend_processor(
            conn, str(seeded["processors"]["external"]["processor_uuid"])
        )
        assert _to(queued, "send_registry_suspended") == ["dco@test.local", "rnd@test.local"]

    async def test_a_collector_asked_for_on_an_approved_project_reaches_the_officers(
        self, conn: Any, seeded: dict[str, Any], queued: list[Any]
    ) -> None:
        await projects.request_processor(
            conn,
            project_uuid=str(seeded["project"]["project_uuid"]),
            processor_uuid=str(seeded["processors"]["in_house"]["processor_uuid"]),
            role=Role.RND_USER,
            actor_id=int(seeded["users"]["rnd_user"]["id"]),
        )
        assert "dpo@test.local" in _to(queued, "send_processor_requested")

    async def test_a_deactivated_site_reaches_the_projects_people(
        self, conn: Any, seeded: dict[str, Any], queued: list[Any]
    ) -> None:
        await projects.deactivate_site(
            conn,
            str(seeded["site"]["site_uuid"]),
            role=Role.DPO,
            actor_id=int(seeded["users"]["dpo"]["id"]),
        )
        assert _to(queued, "send_site_deactivated") == ["dco@test.local", "rnd@test.local"]

    async def test_a_withdrawal_on_an_rnd_project_names_her_by_reference_only(
        self, conn: Any, seeded: dict[str, Any], queued: list[Any]
    ) -> None:
        told = await alerts.rnd_withdrawal(
            conn,
            notice_id=int(seeded["notice"]["notice_id"]),
            user={"uuid": "7c3cbb28-0000-0000-0000-000000000000", "full_name": "Her Name"},
            consent_reference="ref",
            stopped=["Test purpose"],
            continuing=[],
        )
        assert told == 2
        assert _to(queued, "send_rnd_withdrawal_notice") == ["dco@test.local", "rnd@test.local"]
        assert all("Her Name" not in map(str, args) for _, args in queued)


class TestOversight:
    async def test_a_broken_audit_chain_reaches_administrators_and_officers(
        self, conn: Any, seeded: dict[str, Any], queued: list[Any]
    ) -> None:
        await alerts.audit_chain_broken(conn, position="entry 42 (hash mismatch)")
        told = _to(queued, "send_audit_chain_broken")
        assert "admin@test.local" in told and "dpo@test.local" in told

    async def test_the_overdue_word_goes_to_administrators_only_when_something_is_late(
        self, conn: Any, seeded: dict[str, Any], queued: list[Any]
    ) -> None:
        now = datetime.now(UTC)
        rows = [
            {"reference": "RR-1", "request_type": "access", "due_at": now + timedelta(days=2)},
        ]
        assert await alerts.rights_overdue(conn, rows, now) == 0
        rows.append(
            {
                "reference": "RR-2",
                "request_type": "erasure",
                "due_at": now - timedelta(days=3),
                "office_code": "rnd",
            }
        )
        assert await alerts.rights_overdue(conn, rows, now) == 1
        assert "admin@test.local" in _to(queued, "send_rights_overdue_escalation")
        [(_, args)] = [q for q in queued if q[0] == "send_rights_overdue_escalation"][:1]
        assert "RR-2" in args[2] and "RR-1" not in args[2]

    async def test_failed_breach_notices_are_said_once_not_once_per_person(
        self, conn: Any, seeded: dict[str, Any], queued: list[Any], redis_conn: Any
    ) -> None:
        breach = {"breach_uuid": str(uuid4()), "reference": "BR-T", "office_code": "rnd"}
        assert await alerts.breach_notices_undelivered(conn, breach=breach) is True
        assert await alerts.breach_notices_undelivered(conn, breach=breach) is False
        assert _to(queued, "send_breach_notices_undelivered") == ["dpo@test.local"]

    async def test_a_breach_ticket_message_to_its_holder_names_no_breach(
        self, conn: Any, queued: list[Any]
    ) -> None:
        await alerts.breach_ticket_office_wrote(
            conn,
            ticket={
                "holder_email": "holder@test.local",
                "holder_name": "Holder",
                "breach_reference": "BR-SECRET",
            },
        )
        [(name, args)] = queued
        assert name == "send_breach_ticket_message"
        assert "BR-SECRET" not in map(str, args)


class TestWhoKeepsTheWords:
    async def test_legal_may_change_a_message_with_legal_weight(
        self, conn: Any, seeded: dict[str, Any], queued: list[Any]
    ) -> None:
        legal = await _add_legal(conn)
        view = await messaging.save(
            conn,
            key="rights_closed",
            channel="sms",
            subject=None,
            body="Request {reference}: {headline}. {explanation} - {organisation}",
            actor_id=legal,
            role="legal",
        )
        assert view["editable"] is True
        assert "Legal PoC" in view["editors"]
        # The change is told to everybody who answers for the platform.
        assert "admin@test.local" in _to(queued, "send_settings_changed")

    async def test_legal_may_not_change_a_sign_in_code(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        legal = await _add_legal(conn)
        with pytest.raises(Forbidden):
            await messaging.save(
                conn,
                key="mfa_code",
                channel="email",
                subject="{code}",
                body="{code} {minutes}",
                actor_id=legal,
                role="legal",
            )
        rows = await messaging.catalogue(conn, role="legal")
        mine = {r["key"] for r in rows if r["editable"]}
        assert "rights_closed" in mine and "mfa_code" not in mine
        assert all(r["editable"] for r in await messaging.catalogue(conn, role="dpo"))
