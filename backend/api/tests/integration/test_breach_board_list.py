"""The organisation's board list and its mandatory entries (0064, ADR 0037).

The list is what each report's window offers. An entry may be made mandatory:
every report then goes to it, and it is not taken off until somebody makes it
optional again. The mark moves only with the event that says who moved it and
when, and the database holds that as well as the service. An address added for
one report alone is no entry on the list, and nothing here reaches it.
"""

from __future__ import annotations

import uuid as uuid_module
from typing import Any

import psycopg
import pytest

from cmp.core.errors import Conflict, NotFound
from cmp.db.sql import execute, fetch_all
from cmp.domain.breach import reports
from cmp.domain.breach import settings as breach_settings
from tests.conftest import plain
from tests.integration.test_breach_reports import (
    _board,
    _breach,
    _cert_in_draft,
    _dpo,
    _draft,
    _entries,
    _finalise,
    _incident,
    _lines,
    _mark,
    _nobody_on_the_list,  # noqa: F401 - each test starts with an empty list
    _not_reached,
    _resend,
    _send,
    mailed,  # noqa: F401
)
from tests.integration.test_breach_tables_hold_to_their_word import M0064
from tests.integration.test_rights_by_office import _legal_poc

pytestmark = pytest.mark.integration


async def _events(conn: Any, recipient_uuid: str) -> list[dict[str, Any]]:
    return await fetch_all(
        conn,
        """SELECT e.kind, e.recorded_by, e.recorded_at FROM breach_board_recipient_event e
             JOIN breach_board_recipient x ON x.recipient_id = e.recipient_id
            WHERE x.recipient_uuid = %s ORDER BY e.event_id""",
        (recipient_uuid,),
    )


async def _changes(conn: Any, recipient_uuid: str) -> list[str]:
    """What the trail says was done to one entry, in order."""
    rows = await fetch_all(
        conn,
        """SELECT detail_json FROM audit_log
            WHERE entity_type = 'breach_settings' AND event_type = 'breach_settings.changed'
              AND detail_json->>'recipient' = %s
            ORDER BY log_id""",
        (recipient_uuid,),
    )
    return [str(r["detail_json"]["board_recipient"]) for r in rows]


async def _listed(conn: Any) -> dict[str, dict[str, Any]]:
    kept = await breach_settings.overview(conn)
    return {str(plain(r["email"])): r for r in kept["board_recipients"]}


class TestTheMark:
    async def test_marking_writes_an_event_and_the_trail_and_twice_is_once(
        self, conn: Any, seeded: dict[str, Any], sent: list[Any]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        entry = (await _entries(conn))["chair@example.org"]
        await _mark(conn, seeded, "chair@example.org")
        told = len(sent)
        await _mark(conn, seeded, "chair@example.org")
        assert len(sent) == told, "a mark that changes nothing tells nobody"
        assert [e["kind"] for e in await _events(conn, entry)] == ["mandatory"]
        assert await _changes(conn, entry) == ["added", "made_mandatory"]
        assert (await _listed(conn))["chair@example.org"]["mandatory"] is True
        await _mark(conn, seeded, "chair@example.org", mandatory=False)
        assert [e["kind"] for e in await _events(conn, entry)] == ["mandatory", "optional"]
        assert await _changes(conn, entry) == ["added", "made_mandatory", "made_optional"]

    async def test_a_mandatory_entry_is_not_taken_off_until_made_optional(
        self, conn: Any, seeded: dict[str, Any], sent: list[Any]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        entry = (await _entries(conn))["chair@example.org"]
        await _mark(conn, seeded, "chair@example.org")
        with pytest.raises(Conflict) as refused:
            await breach_settings.remove_board_recipient(
                conn, recipient_uuid=entry, actor_id=_dpo(seeded)
            )
        assert refused.value.code == "recipient_mandatory"
        assert "chair@example.org" in await _listed(conn)
        await _mark(conn, seeded, "chair@example.org", mandatory=False)
        await breach_settings.remove_board_recipient(
            conn, recipient_uuid=entry, actor_id=_dpo(seeded)
        )
        assert "chair@example.org" not in await _listed(conn)

    async def test_who_marked_it_and_when_is_the_latest_event(
        self, conn: Any, seeded: dict[str, Any], sent: list[Any]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        entry = (await _entries(conn))["chair@example.org"]
        before = (await _listed(conn))["chair@example.org"]
        assert (before["mandatory_changed_at"], before["mandatory_changed_by_name"]) == (None, None)
        await _mark(conn, seeded, "chair@example.org")
        legal = await _legal_poc(conn)
        await breach_settings.set_board_recipient_mandatory(
            conn, recipient_uuid=entry, mandatory=False, actor_id=legal
        )
        after = (await _listed(conn))["chair@example.org"]
        latest = (await _events(conn, entry))[-1]
        assert after["mandatory"] is False
        assert after["mandatory_changed_at"] == latest["recorded_at"]
        assert plain(after["mandatory_changed_by_name"]) == "Test legal"


class TestTheDatabaseHoldsTheRule:
    """Raw SQL, past the service."""

    @staticmethod
    async def _entry(conn: Any, seeded: dict[str, Any], *, mandatory: bool = False) -> str:
        await _board(conn, seeded, "chair@example.org")
        if mandatory:
            await _mark(conn, seeded, "chair@example.org")
        return (await _entries(conn))["chair@example.org"]

    async def test_a_mandatory_entry_is_not_taken_off(
        self, conn: Any, seeded: dict[str, Any], sent: list[Any]
    ) -> None:
        entry = await self._entry(conn, seeded, mandatory=True)
        with pytest.raises(psycopg.errors.CheckViolation):
            await conn.execute(
                """UPDATE breach_board_recipient SET removed_at = now(), removed_by = %s
                    WHERE recipient_uuid = %s""",
                (_dpo(seeded), entry),
            )

    async def test_a_mark_no_event_records_is_refused(
        self, conn: Any, seeded: dict[str, Any], sent: list[Any]
    ) -> None:
        entry = await self._entry(conn, seeded)
        with pytest.raises(psycopg.errors.RestrictViolation):
            await conn.execute(
                "UPDATE breach_board_recipient SET mandatory = true WHERE recipient_uuid = %s",
                (entry,),
            )

    @pytest.mark.parametrize(
        "statement",
        [
            "DELETE FROM breach_board_recipient WHERE recipient_uuid = %s",
            "UPDATE breach_board_recipient SET email = 'SE::v1:another' WHERE recipient_uuid = %s",
            "UPDATE breach_board_recipient SET full_name = NULL, email_hash = 'x' "
            "WHERE recipient_uuid = %s",
            "UPDATE breach_board_recipient SET one_off = true WHERE recipient_uuid = %s",
        ],
        ids=["delete", "address", "index", "one-off"],
    )
    async def test_an_entry_is_written_once(
        self, conn: Any, seeded: dict[str, Any], sent: list[Any], statement: str
    ) -> None:
        entry = await self._entry(conn, seeded)
        with pytest.raises(psycopg.errors.RestrictViolation):
            await conn.execute(statement, (entry,))

    async def test_an_entry_taken_off_stays_off(
        self, conn: Any, seeded: dict[str, Any], sent: list[Any]
    ) -> None:
        entry = await self._entry(conn, seeded)
        await breach_settings.remove_board_recipient(
            conn, recipient_uuid=entry, actor_id=_dpo(seeded)
        )
        with pytest.raises(psycopg.errors.RestrictViolation):
            await conn.execute(
                """UPDATE breach_board_recipient SET removed_at = NULL, removed_by = NULL
                    WHERE recipient_uuid = %s""",
                (entry,),
            )

    async def test_an_address_for_one_report_is_never_taken_off_or_marked(
        self,
        conn: Any,
        seeded: dict[str, Any],
        mailed: list[str],  # noqa: F811
    ) -> None:
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "board_intimation")
        sent = await _send(conn, seeded, uuid, doc, to=[], extra=[{"email": "a@elsewhere.org"}])
        [line] = sent["mail"]["recipients"]
        with pytest.raises(psycopg.errors.CheckViolation):
            async with conn.transaction():
                await conn.execute(
                    """UPDATE breach_board_recipient SET removed_at = now(), removed_by = %s
                        WHERE recipient_uuid = %s""",
                    (_dpo(seeded), str(line["recipient_uuid"])),
                )
        await execute(
            conn,
            """INSERT INTO breach_board_recipient_event (recipient_id, kind, recorded_by)
               SELECT recipient_id, 'mandatory', %s FROM breach_board_recipient
                WHERE recipient_uuid = %s""",
            (_dpo(seeded), str(line["recipient_uuid"])),
        )
        with pytest.raises(psycopg.errors.CheckViolation):
            await conn.execute(
                "UPDATE breach_board_recipient SET mandatory = true WHERE recipient_uuid = %s",
                (str(line["recipient_uuid"]),),
            )


class TestAnAddressForOneReport:
    async def test_it_is_never_listed_taken_off_or_marked(
        self,
        conn: Any,
        seeded: dict[str, Any],
        mailed: list[str],  # noqa: F811
    ) -> None:
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "board_intimation")
        sent = await _send(conn, seeded, uuid, doc, to=[], extra=[{"email": "a@elsewhere.org"}])
        one_off = str(_lines(sent)["a@elsewhere.org"]["recipient_uuid"])
        assert await _listed(conn) == {}
        with pytest.raises(NotFound):
            await breach_settings.remove_board_recipient(
                conn, recipient_uuid=one_off, actor_id=_dpo(seeded)
            )
        with pytest.raises(NotFound):
            await breach_settings.set_board_recipient_mandatory(
                conn, recipient_uuid=one_off, mandatory=True, actor_id=_dpo(seeded)
            )
        # The list's own uniqueness passes it by: the same address may be put
        # on the list, and is then an entry of its own.
        await _board(conn, seeded, "a@elsewhere.org")
        assert list(await _listed(conn)) == ["a@elsewhere.org"]
        assert (await _entries(conn))["a@elsewhere.org"] != one_off


class TestTheWayDown:
    """0064's GUARD: the older code would read an address for one report as on
    the list and mail it every report, and a mark or a held mail would be lost."""

    @staticmethod
    async def _refused(conn: Any) -> bool:
        try:
            async with conn.transaction():
                await conn.execute(M0064.GUARD)
        except psycopg.errors.RaiseException as raised:
            assert "choices were made about who reports go to" in str(raised)
            return True
        return False

    async def test_a_database_with_no_choice_made_may_go_down(
        self,
        conn: Any,
        seeded: dict[str, Any],
        mailed: list[str],  # noqa: F811
    ) -> None:
        if await self._refused(conn):
            pytest.skip("this database holds choices tests/http made; its way down is closed")
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "board_intimation")
        assert not await self._refused(conn), "a report sent to the list as it stood is none"

    @pytest.mark.parametrize("choice", ["one_off", "mark", "held", "left_out"])
    async def test_a_choice_refuses_it(
        self,
        conn: Any,
        seeded: dict[str, Any],
        mailed: list[str],  # noqa: F811
        choice: str,
    ) -> None:
        """Each choice alone closes the way down. On a database whose way down
        is closed already nothing here would show which clause did it, so it
        proves its clause only on one that still may go down."""
        if await self._refused(conn):
            pytest.skip("this database holds choices tests/http made; its way down is closed")
        await _board(conn, seeded, "chair@example.org", "member@example.org")
        assert not await self._refused(conn), "a list alone is no choice"
        if choice == "one_off":
            uuid = await _breach(conn, seeded)
            doc = await _draft(conn, seeded, uuid, "board_intimation")
            await _send(
                conn,
                seeded,
                uuid,
                doc,
                to=["chair@example.org", "member@example.org"],
                extra=[{"email": "a@elsewhere.org"}],
            )
        elif choice == "mark":
            await _mark(conn, seeded, "chair@example.org")
        elif choice == "held":
            uuid = await _incident(conn, seeded)
            doc = await _cert_in_draft(conn, seeded, uuid)
            await _send(conn, seeded, uuid, doc, to=None)
        else:
            # The member is implicated, so the sender leaves them out: the
            # older Try again would mail them the version all the same.
            uuid = await _breach(conn, seeded)
            doc = await _draft(conn, seeded, uuid, "board_intimation")
            await _send(conn, seeded, uuid, doc, to=["chair@example.org"])
        assert await self._refused(conn)


class TestTheBackfill:
    async def test_it_names_each_deliverys_pair_once(
        self,
        conn: Any,
        seeded: dict[str, Any],
        mailed: list[str],  # noqa: F811
    ) -> None:
        """However many attempts and states a pair has, it went to that address
        once: one addressee each, as the version's own were written."""
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        [chair, _] = mailed
        await _not_reached(conn, chair)
        await _resend(conn, seeded, uuid, doc)
        pairs = M0064.BACKFILL[M0064.BACKFILL.index("SELECT") :].split(" ORDER BY")[0]
        found = await fetch_all(
            conn,
            f"""SELECT b.report_id, b.recipient_id FROM ({pairs}) b
                 JOIN breach_report r ON r.report_id = b.report_id
                WHERE r.report_uuid = %s ORDER BY b.recipient_id""",
            (str(doc["report_uuid"]),),
        )
        kept = await fetch_all(
            conn,
            """SELECT a.report_id, a.recipient_id FROM breach_report_addressee a
                 JOIN breach_report r ON r.report_id = a.report_id
                WHERE r.report_uuid = %s ORDER BY a.recipient_id""",
            (str(doc["report_uuid"]),),
        )
        assert len(found) == 2 and found == kept


class TestTheGrants:
    async def test_the_sequences_are_the_applications_and_a_missing_role_is_passed_over(
        self, conn: Any
    ) -> None:
        probe = f"cmp_board_list_probe_{uuid_module.uuid4().hex[:8]}"
        await conn.execute(f"CREATE ROLE {probe}")
        await conn.execute(M0064._grants(probe))
        for sequence in (
            "breach_report_addressee_addressee_id_seq",
            "breach_board_recipient_event_event_id_seq",
        ):
            [row] = await fetch_all(
                conn, "SELECT has_sequence_privilege(%s, %s, 'USAGE') AS may", (probe, sequence)
            )
            assert row["may"], sequence
        await conn.execute(M0064._grants("cmp_no_such_role"))


async def test_the_window_offers_the_list_and_says_which_are_mandatory(
    conn: Any,
    seeded: dict[str, Any],
    mailed: list[str],  # noqa: F811
) -> None:
    await _board(conn, seeded, "chair@example.org", "member@example.org")
    await _mark(conn, seeded, "member@example.org")
    uuid = await _breach(conn, seeded)
    offered = await reports.board_list(conn, breach_uuid=uuid)
    assert [(plain(r["email"]), r["mandatory"]) for r in offered["recipients"]] == [
        ("chair@example.org", False),
        ("member@example.org", True),
    ]
    assert all(str(r["email"]).startswith("SE::") for r in offered["recipients"])
