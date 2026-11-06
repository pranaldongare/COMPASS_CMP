"""What 0058 to 0062 left open, closed by 0063, and 0061's way down.

The rules live in the migrations, so these read them from there: the grants
the application's role keeps, the section a finalised report cannot gain, the
board duties of the old rule, and a downgrade that would lose ticket dates.
`scripts/reseal.py` is checked here against the catalogue it runs on.
"""

from __future__ import annotations

import importlib.util
import pathlib
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import psycopg
import pytest

from cmp.core.config import settings
from cmp.db.repositories import breaches as breach_repo
from cmp.db.sql import fetch_all, fetch_one
from cmp.domain.breach import service, tickets
from cmp.domain.breach.clock import Duty, EventKind, State
from cmp.infrastructure.dkms.fields import ENCRYPTED_FIELDS
from tests.integration.test_breach_tickets import _assign, _today
from tests.integration.test_breach_tickets import _recorded as _ticketed

pytestmark = pytest.mark.integration

ROOT = pathlib.Path(__file__).parents[2]


def _load(path: str) -> Any:
    spec = importlib.util.spec_from_file_location(pathlib.Path(path).stem, ROOT / path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M0063 = _load("migrations/versions/0063_breach_tables_hold_to_their_word.py")
M0061 = _load("migrations/versions/0061_breach_ticket_resolve_by.py")
RESEAL = _load("scripts/reseal.py")
PROBE = "cmp_hardening_probe"
#: How the trigger that refuses an UPDATE of a sealed table is named.
GUARDS = ("append_only", "frozen", "outcome_once", "read_only", "status_only", "release_only")


REFUSED = {
    "breach_report_delivery": ("UPDATE", "DELETE", "TRUNCATE"),
    "incident_report": ("DELETE", "TRUNCATE"),
    "breach_report": ("DELETE", "TRUNCATE"),
    "breach_report_section": ("DELETE", "TRUNCATE"),
    "breach_board_recipient": ("DELETE", "TRUNCATE"),
    "breach_settings": ("INSERT", "DELETE", "TRUNCATE"),
}
KEPT = {
    "breach_report_delivery": ("SELECT", "INSERT"),
    "incident_report": ("SELECT", "INSERT", "UPDATE"),
    "breach_report": ("SELECT", "INSERT", "UPDATE"),
    "breach_report_section": ("SELECT", "INSERT", "UPDATE"),
    "breach_board_recipient": ("SELECT", "INSERT", "UPDATE"),
    "breach_settings": ("SELECT", "UPDATE"),
}


class TestGrants:
    async def _may(self, conn: Any, table: str, privilege: str) -> bool:
        row = await fetch_one(
            conn, "SELECT has_table_privilege(%s, %s, %s) AS may", (PROBE, table, privilege)
        )
        assert row is not None
        return bool(row["may"])

    async def test_the_role_loses_what_the_triggers_refuse_and_keeps_its_work(
        self, conn: Any
    ) -> None:
        await conn.execute(f"CREATE ROLE {PROBE}")
        for table in REFUSED:
            await conn.execute(f"GRANT ALL ON TABLE {table} TO {PROBE}")
        await conn.execute(M0063._harden(PROBE))
        for table, privileges in REFUSED.items():
            for privilege in privileges:
                assert not await self._may(conn, table, privilege), f"{table} {privilege}"
        for table, privileges in KEPT.items():
            for privilege in privileges:
                assert await self._may(conn, table, privilege), f"{table} {privilege}"

    async def test_no_such_role_is_passed_over_quietly(self, conn: Any) -> None:
        await conn.execute(M0063._harden("cmp_no_such_role"))


class TestTheBoardDutiesOfTheOldRule:
    """Until 0058 every logged incident took an `org_board` duty and a no left
    it alone. The incident's row is made here as it was then: the duty appears
    after the no, which under today's rule would have set it aside."""

    def _dpo(self, seeded: dict[str, Any]) -> int:
        return int(seeded["users"]["dpo"]["id"])

    async def _incident(self, conn: Any, seeded: dict[str, Any]) -> Any:
        made = await service.record(
            conn,
            title="A share left open",
            detected_at=datetime.now(UTC) - timedelta(hours=2),
            began_at=None,
            location_kind="platform",
            processor_uuid=None,
            source_uuid=None,
            location_detail=None,
            actor_id=self._dpo(seeded),
        )
        return await service.require(conn, str(made["breach_uuid"]))

    async def _determine(self, conn: Any, seeded: dict[str, Any], breach: Any, no: bool) -> None:
        await service.determine(
            conn,
            breach_uuid=str(breach["breach_uuid"]),
            outcome="no" if no else "yes",
            reasoning="Read and decided",
            became_aware_at=None if no else datetime.now(UTC) - timedelta(hours=1),
            actor_id=self._dpo(seeded),
        )

    async def _old_duty(self, conn: Any, seeded: dict[str, Any], breach: Any) -> int:
        row = await breach_repo.create_obligation(
            conn,
            int(breach["breach_id"]),
            kind=Duty.ORG_BOARD.value,
            due_at=datetime.now(UTC) + timedelta(hours=1),
            anchored_at=breach["detected_at"],
            determination_id=None,
            created_by=self._dpo(seeded),
        )
        return int(row["obligation_id"])

    async def _state(self, conn: Any, breach: Any) -> str:
        duties = await service.duties_of(conn, int(breach["breach_id"]))
        return str(duties[Duty.ORG_BOARD][1]["state"])

    async def _events(self, conn: Any, duty: int) -> list[dict[str, Any]]:
        return await fetch_all(
            conn,
            "SELECT kind, determination_id, recorded_by FROM breach_obligation_event "
            "WHERE obligation_id = %s ORDER BY event_id",
            (duty,),
        )

    async def test_one_validated_no_is_set_aside_citing_that_no_and_only_once(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        breach = await self._incident(conn, seeded)
        await self._determine(conn, seeded, breach, no=True)
        duty = await self._old_duty(conn, seeded, breach)
        assert await self._state(conn, breach) == State.OUTSTANDING

        await conn.execute(M0063.SET_ASIDE)
        await conn.execute(M0063.SET_ASIDE)

        no = await fetch_one(
            conn,
            "SELECT max(determination_id) AS id FROM breach_determination WHERE breach_id = %s",
            (breach["breach_id"],),
        )
        assert no is not None
        assert await self._events(conn, duty) == [
            {"kind": "not_applicable", "determination_id": no["id"], "recorded_by": None}
        ]
        assert await self._state(conn, breach) == State.NOT_APPLICABLE

    async def test_an_extended_duty_is_still_outstanding(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        breach = await self._incident(conn, seeded)
        await self._determine(conn, seeded, breach, no=True)
        duty = await self._old_duty(conn, seeded, breach)
        await breach_repo.add_obligation_event(
            conn,
            duty,
            kind=EventKind.EXTENDED,
            recorded_by=self._dpo(seeded),
            due_at=datetime.now(UTC) + timedelta(days=1),
            requested_at=datetime.now(UTC),
        )
        await conn.execute(M0063.SET_ASIDE)
        assert await self._state(conn, breach) == State.NOT_APPLICABLE

    async def test_a_duty_done_stays_done(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        breach = await self._incident(conn, seeded)
        await self._determine(conn, seeded, breach, no=True)
        duty = await self._old_duty(conn, seeded, breach)
        await breach_repo.add_obligation_event(
            conn,
            duty,
            kind=EventKind.COMPLETED,
            recorded_by=self._dpo(seeded),
            occurred_at=datetime.now(UTC),
            reported_to="The chair",
        )
        await conn.execute(M0063.SET_ASIDE)
        assert await self._state(conn, breach) == State.DONE

    async def test_a_yes_keeps_its_duty_and_an_incident_not_yet_validated_keeps_its_own(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        recorded = await self._incident(conn, seeded)
        await self._determine(conn, seeded, recorded, no=True)
        await self._determine(conn, seeded, recorded, no=False)
        pending = await self._incident(conn, seeded)
        await self._old_duty(conn, seeded, pending)

        await conn.execute(M0063.SET_ASIDE)

        assert await self._state(conn, recorded) == State.OUTSTANDING
        assert await self._state(conn, pending) == State.OUTSTANDING


class TestTheWayDownFrom0061:
    async def test_a_changed_date_refuses_the_downgrade_before_anything_goes(
        self,
        conn: Any,
        seeded: dict[str, Any],
        request_context: Any,
        sent: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(settings, "breach_ticket_email_domains", ("test.local",))
        said: list[str] = []
        monkeypatch.setattr(M0061, "op", SimpleNamespace(execute=said.append))
        M0061.downgrade()
        assert said.index(M0061.GUARD) < said.index(M0061.DOWNGRADE)

        uuid = await _ticketed(conn, seeded)
        made = await _assign(conn, seeded, uuid, answer_by=_today() + timedelta(days=2))
        await tickets.office_change_date(
            conn,
            breach_uuid=uuid,
            ticket_uuid=str(made["ticket"]["ticket_uuid"]),
            answer_by=_today() + timedelta(days=5),
            reason="More time agreed",
            actor_id=int(seeded["users"]["dpo"]["id"]),
        )
        with pytest.raises(psycopg.errors.RaiseException, match="dates were changed"):
            async with conn.transaction():
                await conn.execute(M0061.GUARD)


class TestResealReadsTheCatalogue:
    async def test_each_key_it_names_is_the_table_s_primary_key(self, conn: Any) -> None:
        rows = await fetch_all(
            conn,
            """SELECT t.relname AS table_name, a.attname AS key
                 FROM pg_index i
                 JOIN pg_class t ON t.oid = i.indrelid
                 JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(i.indkey)
                WHERE i.indisprimary AND t.relname = ANY(%s)""",
            (list(RESEAL.PRIMARY_KEY),),
        )
        assert {r["table_name"]: r["key"] for r in rows} == RESEAL.PRIMARY_KEY

    async def test_every_trigger_that_would_refuse_a_sealing_is_named(self, conn: Any) -> None:
        rows = await fetch_all(
            conn,
            """SELECT c.relname AS table_name, t.tgname AS trigger
                 FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
                WHERE NOT t.tgisinternal AND c.relname = ANY(%s)""",
            (list(ENCRYPTED_FIELDS),),
        )
        found = {(r["table_name"], r["trigger"]) for r in rows}
        assert set(RESEAL.APPEND_ONLY.items()) <= found, "a trigger that does not exist"
        guarding = {pair for pair in found if pair[1].endswith(GUARDS)}
        assert sorted(guarding - set(RESEAL.APPEND_ONLY.items())) == []
