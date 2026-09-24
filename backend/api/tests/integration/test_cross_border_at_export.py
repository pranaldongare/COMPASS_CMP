"""Cross-border control, enforced at export (S2-04).

An export row goes to the processor running the site its consent was given at.
Where that processor is decides the transfer: in India, domestic; anywhere
else, lawful under s.16 only if the country is not on the Government's
restricted list and every purpose the person granted permits it. A place the
platform cannot name is refused. The decision, and the ground it rested on, is
recorded on the export and on each line.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.errors import Conflict, ValidationFailed
from cmp.db.repositories import rights as rights_repo
from cmp.domain.exchange import service as exchange_service
from cmp.domain.exchange import transfer
from cmp.infrastructure.storage import service as storage_service
from cmp.infrastructure.storage.local import LocalFileStorage
from tests.integration.test_export_snapshot import _consent

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _tmp_storage(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    store = LocalFileStorage(root=str(tmp_path))
    monkeypatch.setattr(storage_service, "storage", lambda: store)


async def _locate(conn: Any, seeded: dict[str, Any], country: str | None) -> None:
    await conn.execute(
        "UPDATE processor SET location_country = %s WHERE processor_id = %s",
        (country, seeded["processors"]["external"]["processor_id"]),
    )


async def _cross_border(conn: Any, seeded: dict[str, Any], permitted: bool) -> None:
    await conn.execute(
        "UPDATE purpose SET cross_border_permitted = %s WHERE purpose_id = %s",
        (permitted, seeded["purpose"]["purpose_id"]),
    )


async def _export(conn: Any, seeded: dict[str, Any]) -> dict[str, Any]:
    return await exchange_service.generate(
        conn,
        project_uuid=str(seeded["project"]["project_uuid"]),
        actor_id=seeded["users"]["dpo"]["id"],
        role="dpo",
    )


async def _exports(conn: Any, seeded: dict[str, Any]) -> int:
    row = await (
        await conn.execute(
            "SELECT count(*) AS n FROM export_log WHERE project_id = %s",
            (seeded["project"]["project_id"],),
        )
    ).fetchone()
    return int(row["n"])


async def _refused(conn: Any, seeded: dict[str, Any]) -> ValidationFailed:
    before = await _exports(conn, seeded)
    with pytest.raises(ValidationFailed) as raised:
        await _export(conn, seeded)
    assert await _exports(conn, seeded) == before, "a refused export writes no disclosure"
    assert raised.value.code == "transfer_refused"
    return raised.value


async def test_a_destination_with_no_recorded_place_is_refused(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _consent(conn, seeded)
    await _locate(conn, seeded, None)
    refused = await _refused(conn, seeded)
    assert refused.details["refusals"][0]["cause"] == "location_unknown"
    assert "Test Processor Ltd" in refused.message


async def test_a_domestic_export_goes_and_says_so(conn: Any, seeded: dict[str, Any]) -> None:
    await _consent(conn, seeded)
    export = await _export(conn, seeded)

    [destination] = export["transfer_basis"]["destinations"]
    assert destination["country"] == "IN" and destination["basis"] == "domestic"
    line = await (
        await conn.execute(
            """SELECT destination_processor_id, destination_country
                 FROM export_line WHERE export_id = %s""",
            (export["export_id"],),
        )
    ).fetchone()
    assert line["destination_country"] == "IN"
    assert line["destination_processor_id"] == seeded["processors"]["external"]["processor_id"]


async def test_abroad_is_lawful_when_unrestricted_and_every_purpose_permits_it(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _consent(conn, seeded)
    await _locate(conn, seeded, "DE")
    await _cross_border(conn, seeded, True)
    export = await _export(conn, seeded)
    [destination] = export["transfer_basis"]["destinations"]
    assert destination["country"] == "DE" and destination["basis"] == "s.16"


async def test_abroad_is_refused_for_a_purpose_that_does_not_permit_it(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _consent(conn, seeded)
    await _locate(conn, seeded, "DE")
    await _cross_border(conn, seeded, False)
    refused = await _refused(conn, seeded)
    [why] = refused.details["refusals"]
    code = await (
        await conn.execute(
            "SELECT purpose_code FROM purpose WHERE purpose_id = %s",
            (seeded["purpose"]["purpose_id"],),
        )
    ).fetchone()
    assert why["cause"] == "purpose_not_cross_border"
    assert why["purposes"] == [code["purpose_code"]]


async def test_a_restricted_country_is_refused_until_the_restriction_is_lifted(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = seeded["users"]["dpo"]["id"]
    await _consent(conn, seeded)
    await _locate(conn, seeded, "XZ")
    await _cross_border(conn, seeded, True)
    listed = await transfer.restrict(
        conn, country_code="XZ", notification_ref="G.S.R. 000(E)", actor_id=dpo
    )

    refused = await _refused(conn, seeded)
    [why] = refused.details["refusals"]
    assert why["cause"] == "restricted_country" and why["notification"] == "G.S.R. 000(E)"

    await transfer.lift(conn, country_uuid=str(listed["country_uuid"]), actor_id=dpo)
    export = await _export(conn, seeded)
    assert export["transfer_basis"]["destinations"][0]["basis"] == "s.16"


async def test_a_country_is_listed_once_at_a_time_and_lifted_once(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = seeded["users"]["dpo"]["id"]
    listed = await transfer.restrict(conn, country_code="xz", notification_ref="N-1", actor_id=dpo)
    assert listed["country_code"] == "XZ"
    with pytest.raises(Conflict):
        await transfer.restrict(conn, country_code="XZ", notification_ref="N-2", actor_id=dpo)
    with pytest.raises(ValidationFailed):
        await transfer.restrict(conn, country_code="IN", notification_ref="N-3", actor_id=dpo)
    await transfer.lift(conn, country_uuid=str(listed["country_uuid"]), actor_id=dpo)
    with pytest.raises(Conflict):
        await transfer.lift(conn, country_uuid=str(listed["country_uuid"]), actor_id=dpo)


async def test_a_refusal_is_recorded_without_the_people_in_it(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """The route records it in its own transaction - the refusal rolls back
    the export's - so this calls the same function it does."""
    await _consent(conn, seeded)
    await _locate(conn, seeded, None)
    refused = await _refused(conn, seeded)
    assert isinstance(refused, transfer.TransferRefused)
    await transfer.record_refusal(
        conn,
        refused,
        project_id=seeded["project"]["project_id"],
        actor_id=seeded["users"]["dpo"]["id"],
    )
    row = await (
        await conn.execute(
            """SELECT detail_json FROM audit_log WHERE event_type = 'export.refused'
                ORDER BY log_id DESC LIMIT 1"""
        )
    ).fetchone()
    assert row is not None
    detail = row["detail_json"]
    assert detail["refusals"][0]["cause"] == "location_unknown"
    assert "subject" not in str(detail).lower() and "@" not in str(detail)


async def test_the_lines_name_the_holder_a_rights_request_is_ticketed_to(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """Exports stopped naming a site when they became one per project, and the
    holder derivation read the processor from that site. The line's own
    destination gives it back."""
    await _consent(conn, seeded)
    await _export(conn, seeded)
    candidates = await rights_repo.derive_holder_candidates(conn, seeded["subject"]["id"])
    assert "Test Processor Ltd" in [c["legal_name"] for c in candidates]
