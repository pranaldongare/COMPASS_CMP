"""Breaches and legal holds by office (0055).

A breach is logged into the register of the office that logs it: the Legal
PoC's incident is the Legal office's, its duties start as the DPO's do, and
the DPO is told it is not there. A legal hold is an office's to list and
release - but what it stops it stops for both: the DPO's erasure stops at a
hold the Legal office placed on the same person.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from cmp.core.errors import NotFound
from cmp.db.repositories import breaches as breach_repo
from cmp.db.repositories import legal_holds as hold_repo
from cmp.domain.breach import service
from cmp.domain.rights import holds
from tests.integration.test_rights_by_office import _as_office, _legal_poc

pytestmark = pytest.mark.integration


async def _incident(conn: Any, *, actor_id: int, office: str) -> str:
    made = await service.record(
        conn,
        title="A spreadsheet of survey answers sent to the wrong team",
        detected_at=datetime.now(UTC) - timedelta(minutes=30),
        began_at=None,
        location_kind="platform",
        processor_uuid=None,
        source_uuid=None,
        location_detail=None,
        actor_id=actor_id,
        office=office,
    )
    return str(made["breach_uuid"])


class TestTheRegisterIsTheOffices:
    async def test_the_legal_office_logs_its_own_and_the_dpo_is_told_it_is_not_there(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        legal = await _legal_poc(conn)
        await _as_office(conn, "hr")
        uuid = await _incident(conn, actor_id=legal, office="hr")
        mine = await service.require(conn, uuid)
        assert mine["office_code"] == "hr"
        # The organisation's board duty starts from first noticed, as on the
        # DPO office's register.
        duties = await breach_repo.obligations(conn, [int(mine["breach_id"])])
        assert [d["kind"] for d in duties] == ["org_board"]
        assert uuid in {str(b["breach_uuid"]) for b in await service.register(conn, status=None)}

        await _as_office(conn, "rnd")
        with pytest.raises(NotFound):
            await service.require(conn, uuid)
        assert uuid not in {
            str(b["breach_uuid"]) for b in await service.register(conn, status=None)
        }

    async def test_the_dpo_s_incident_stays_the_dpo_s(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        await _as_office(conn, "rnd")
        uuid = await _incident(conn, actor_id=int(seeded["users"]["dpo"]["id"]), office="rnd")
        await _as_office(conn, "hr")
        with pytest.raises(NotFound):
            await service.require(conn, uuid)


class TestLegalHolds:
    async def test_a_hold_is_its_office_s_to_list_and_both_offices_stop_at_it(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        legal = await _legal_poc(conn)
        person = seeded["subject"]
        await _as_office(conn, "hr")
        held = await holds.place(
            conn,
            asset_uuid=None,
            subject_uuid=str(person["uuid"]),
            reason="An employment tribunal claim",
            actor_id=legal,
            office="hr",
        )
        assert held["office_code"] == "hr"
        assert str(held["hold_uuid"]) in {
            str(h["hold_uuid"]) for h in await hold_repo.list_holds(conn, active_only=True)
        }

        await _as_office(conn, "rnd")
        assert str(held["hold_uuid"]) not in {
            str(h["hold_uuid"]) for h in await hold_repo.list_holds(conn, active_only=True)
        }
        with pytest.raises(NotFound):
            await holds.release(
                conn, hold_uuid=str(held["hold_uuid"]), actor_id=int(seeded["users"]["dpo"]["id"])
            )
        # What it stops, it stops for the DPO office too.
        covering = await hold_repo.active_covering(
            conn, asset_id=None, subject_user_id=int(person["id"])
        )
        assert covering is not None and str(covering["hold_uuid"]) == str(held["hold_uuid"])
        # And the connection reads as the DPO office again afterwards.
        setting = await (
            await conn.execute("SELECT current_setting('app.office', true) AS o")
        ).fetchone()
        assert setting["o"] == "rnd"
