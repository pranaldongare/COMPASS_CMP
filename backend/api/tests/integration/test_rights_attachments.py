"""Documents a data principal sends with her request (2026-10-07).

A proof of who she is, a letter, a screenshot: kept as it came, with a sealed
name, its hash and size. Never replaced or removed - the database refuses
both. Only on her own request, only while it is open, and at most ten. The
trail says one was added and read, never its name.
"""

from __future__ import annotations

import json
from typing import Any

import psycopg
import pytest

from cmp.core.errors import Conflict, NotFound
from cmp.core.security import file_hash
from cmp.db.repositories import rights as repo
from cmp.db.sql import fetch_all, fetch_one
from cmp.domain.rights import service
from cmp.infrastructure.storage.service import storage
from tests.conftest import plain

pytestmark = pytest.mark.integration

LETTER = b"%PDF-1.4\n% A letter from Asha Rao asking for her records\n"


async def _request(conn: Any, seeded: dict[str, Any]) -> dict[str, Any]:
    return await service.create(
        conn,
        request_type="access",
        channel="portal",
        request_text="Everything you hold about me, please",
        submitted_contact="subject@test.local",
        submitted_name="Test Subject",
        subject_user_id=seeded["subject"]["id"],
        actor_id=seeded["subject"]["id"],
        verification_method="session",
    )


async def _attach(
    conn: Any, row: dict[str, Any], user_id: int, *, name: str = "Letter from Asha Rao.pdf"
) -> dict[str, Any]:
    return await service.add_attachment(
        conn,
        row,
        file_name=name,
        storage_ref=storage().save(LETTER, subdir="requests", suggested_name="attachment.pdf"),
        sha256=file_hash(LETTER),
        size_bytes=len(LETTER),
        content_type="application/pdf",
        actor_id=user_id,
    )


async def test_a_document_is_kept_sealed_hashed_and_readable_by_the_office(
    conn: Any, seeded: dict[str, Any]
) -> None:
    me = int(seeded["subject"]["id"])
    row = await _request(conn, seeded)
    made = await _attach(conn, row, me)
    [att] = await repo.attachments_of(conn, int(row["request_id"]))
    assert att["attachment_uuid"] == made["attachment_uuid"]
    assert (att["size_bytes"], att["sha256"], att["content_type"]) == (
        len(LETTER),
        file_hash(LETTER),
        "application/pdf",
    )
    assert att["file_name"].startswith("SE::")
    assert plain(att["file_name"]) == "Letter from Asha Rao.pdf"

    dpo = int(seeded["users"]["dpo"]["id"])
    payload, name, recorded = await service.read_attachment(
        conn, row, attachment_uuid=str(att["attachment_uuid"]), actor_id=dpo
    )
    assert (payload, name, recorded) == (LETTER, "Letter from Asha Rao.pdf", file_hash(LETTER))


async def test_the_trail_says_a_document_came_never_its_name(
    conn: Any, seeded: dict[str, Any]
) -> None:
    me = int(seeded["subject"]["id"])
    row = await _request(conn, seeded)
    made = await _attach(conn, row, me)
    await service.read_attachment(
        conn,
        row,
        attachment_uuid=str(made["attachment_uuid"]),
        actor_id=int(seeded["users"]["dpo"]["id"]),
    )
    rows = await fetch_all(
        conn,
        """SELECT event_type, subject_user_id, detail_json FROM audit_log
            WHERE event_type IN ('rights.attachment_added', 'rights.attachment_read')
              AND detail_json->>'attachment' = %s ORDER BY log_id""",
        (str(made["attachment_uuid"]),),
    )
    assert [r["event_type"] for r in rows] == ["rights.attachment_added", "rights.attachment_read"]
    assert {r["subject_user_id"] for r in rows} == {me}
    words = json.dumps([r["detail_json"] for r in rows])
    assert "Asha" not in words and ".pdf" not in words


async def test_only_her_own_open_request_takes_a_document(
    conn: Any, seeded: dict[str, Any]
) -> None:
    me = int(seeded["subject"]["id"])
    row = await _request(conn, seeded)
    with pytest.raises(NotFound):
        await _attach(conn, row, int(seeded["users"]["dpo"]["id"]))
    with pytest.raises(NotFound):
        service.may_attach(row, user_id=int(seeded["users"]["dpo"]["id"]))
    row = await service.refuse(
        conn,
        row,
        reason="Not a rights request",
        role="dpo",
        actor_id=int(seeded["users"]["dpo"]["id"]),
    )
    with pytest.raises(Conflict) as refused:
        await _attach(conn, row, me)
    assert refused.value.code == "request_closed"


async def test_at_most_ten_documents(conn: Any, seeded: dict[str, Any]) -> None:
    me = int(seeded["subject"]["id"])
    row = await _request(conn, seeded)
    for i in range(service.MAX_ATTACHMENTS):
        await _attach(conn, row, me, name=f"page-{i}.pdf")
    with pytest.raises(Conflict) as refused:
        await _attach(conn, row, me)
    assert refused.value.code == "too_many_attachments"


async def test_a_document_is_read_only_within_its_own_request(
    conn: Any, seeded: dict[str, Any]
) -> None:
    me = int(seeded["subject"]["id"])
    first = await _request(conn, seeded)
    second = await _request(conn, seeded)
    made = await _attach(conn, first, me)
    with pytest.raises(NotFound):
        await service.read_attachment(
            conn,
            second,
            attachment_uuid=str(made["attachment_uuid"]),
            actor_id=int(seeded["users"]["dpo"]["id"]),
        )


async def test_a_document_is_never_replaced_or_removed(conn: Any, seeded: dict[str, Any]) -> None:
    row = await _request(conn, seeded)
    await _attach(conn, row, int(seeded["subject"]["id"]))
    for sql in (
        "UPDATE rights_request_attachment SET content_type = 'text/plain'",
        "DELETE FROM rights_request_attachment",
    ):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            async with conn.transaction():
                await conn.execute(sql)
    stored = await fetch_one(
        conn,
        "SELECT count(*) AS n FROM rights_request_attachment WHERE request_id = %s",
        (int(row["request_id"]),),
    )
    assert stored is not None and stored["n"] == 1
