"""Who a message is copied to, as the office sets it (0046, 2026-10-08).

Only a message the catalogue lets be copied takes copies: never one with a
code, a link or a person's own record. Up to five addresses, sealed at rest,
listed once, replaced as a set, every change on the trail without an address.
A file the office puts on a ticket message is sent with the holder's email.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from cmp.core.errors import ValidationFailed
from cmp.db.sql import fetch_all
from cmp.domain.messaging import service
from cmp.infrastructure.storage.service import storage
from cmp.tasks.notifications.rights import _ticket_file
from tests.conftest import plain

pytestmark = pytest.mark.integration


async def test_copies_are_set_sealed_and_shown(conn: Any, seeded: dict[str, Any]) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    view = await service.set_copies(
        conn,
        key="project_submitted",
        addresses=["Approvals@Corp.example", "approvals@corp.example", "dpo-team@corp.example"],
        actor_id=dpo,
    )
    assert view["copyable"] is True
    shown = [plain(c["email"]) for c in view["copies"]]
    assert shown == ["approvals@corp.example", "dpo-team@corp.example"]
    rows = await fetch_all(conn, "SELECT address FROM message_copy WHERE key = 'project_submitted'")
    assert all(str(r["address"]).startswith("SE::") for r in rows)

    cleared = await service.set_copies(conn, key="project_submitted", addresses=[], actor_id=dpo)
    assert cleared["copies"] == []
    trail = await fetch_all(
        conn,
        """SELECT detail_json FROM audit_log WHERE event_type = 'message_template.copies_updated'
            AND detail_json->>'message' = 'project_submitted' ORDER BY log_id DESC LIMIT 2""",
    )
    assert [t["detail_json"]["copies"] for t in trail] == [0, 2]
    assert "corp.example" not in json.dumps([t["detail_json"] for t in trail])


async def test_a_message_with_a_code_or_her_record_takes_no_copy(
    conn: Any, seeded: dict[str, Any]
) -> None:
    dpo = int(seeded["users"]["dpo"]["id"])
    for key in ("mfa_code", "password_reset", "consent_receipt", "breach_notice"):
        with pytest.raises(ValidationFailed):
            await service.set_copies(conn, key=key, addresses=["a@corp.example"], actor_id=dpo)
    with pytest.raises(ValidationFailed):
        await service.set_copies(
            conn,
            key="ticket_message",
            addresses=[f"c{i}@corp.example" for i in range(6)],
            actor_id=dpo,
        )
    with pytest.raises(ValidationFailed):
        await service.set_copies(conn, key="ticket_message", addresses=["nobody"], actor_id=dpo)


def test_the_office_file_on_a_ticket_message_goes_with_the_email() -> None:
    ref = storage().save(b"%PDF-1.4 extract", subdir="rights", suggested_name="extract.pdf")
    [file] = _ticket_file(ref, "extract.pdf")
    assert (file.filename, file.content_type, file.data) == (
        "extract.pdf",
        "application/pdf",
        b"%PDF-1.4 extract",
    )
    assert _ticket_file(None, None) == []
