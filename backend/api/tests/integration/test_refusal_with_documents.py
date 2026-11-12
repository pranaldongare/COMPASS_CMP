"""A refusal can carry documents (2026-11-12).

A response could release files with it; a refusal could not, though it is the
decision most likely to rest on one - the retention schedule, a court order,
the letter that says why. The office now sends them with the reason. They are
kept on the request like a response's files, named in the mail and on the
trail, and downloaded from her account on the same window. A request with no
account behind it has nowhere to download from, and its mail says how to get
them instead of promising a page.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from cmp.core.errors import Conflict
from cmp.core.permissions import Role
from cmp.core.security import file_hash
from cmp.db.repositories import audit as audit_repo
from cmp.db.repositories import rights as repo
from cmp.domain.rights import service
from cmp.infrastructure.storage.service import storage
from tests.conftest import plain
from tests.integration.test_rights_flows import _portal_request, _unthrottle

pytestmark = pytest.mark.integration

DPO = Role.DPO
SCHEDULE = b"%PDF-1.4 retention schedule, section 4"


def _stored(name: str = "retention-schedule.pdf") -> dict[str, Any]:
    return {
        "ref": storage().save(SCHEDULE, subdir="responses", suggested_name=name),
        "hash": file_hash(SCHEDULE),
        "name": name,
        "size": len(SCHEDULE),
        "content_type": "application/pdf",
    }


async def test_a_refusal_s_documents_reach_her_account_and_her_mail(
    conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[tuple[Any, ...]] = []
    monkeypatch.setattr(service, "_dispatch", lambda *a: sent.append(a))
    dpo = int(seeded["users"]["dpo"]["id"])
    me = int(seeded["subject"]["id"])
    row = await _portal_request(conn, seeded, "erasure")

    row = await service.refuse(
        conn,
        row,
        reason="The retention floor has not passed.",
        role=DPO,
        actor_id=dpo,
        files=[_stored()],
    )
    assert row["status"] == "closed" and row["outcome"] == "refused"
    assert row["download_expires_at"] > datetime.now(UTC) + timedelta(days=1)

    [released] = await repo.response_files_of(conn, int(row["request_id"]))
    assert plain(released["file_name"]) == "retention-schedule.pdf"
    assert released["file_hash"] == file_hash(SCHEDULE)

    # She downloads it while the window is open, and not after.
    got, found = await service.download_file(
        conn, row, file_uuid=str(released["file_uuid"]), actor_id=me, as_subject=True
    )
    assert got == SCHEDULE and found["content_type"] == "application/pdf"
    await repo.update(
        conn, int(row["request_id"]), download_expires_at=datetime.now(UTC) - timedelta(days=1)
    )
    with pytest.raises(Conflict):
        await service.download_file(
            conn,
            await service.reload(conn, row),
            file_uuid=str(released["file_uuid"]),
            actor_id=me,
            as_subject=True,
        )

    # The mail names it and says where it is; the trail names it too.
    [closed] = [a for a in sent if a[0] == "send_rights_closed"]
    assert closed[3] == "refused"
    assert closed[4].startswith("The retention floor has not passed.")
    assert "1 document goes with this decision:\n- retention-schedule.pdf" in closed[4]
    assert "Download from your account until" in closed[4] and "/my-requests" in closed[4]
    trail = await audit_repo.for_reference(conn, row["reference"], limit=20)
    [event] = [e for e in trail if e["event_type"] == "rights.closed"]
    [named] = event["detail"]["files_released"]
    assert named.startswith("SE::") and plain(named) == "retention-schedule.pdf"


async def test_a_refusal_without_documents_is_as_it_was(
    conn: Any, seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[tuple[Any, ...]] = []
    monkeypatch.setattr(service, "_dispatch", lambda *a: sent.append(a))
    row = await _portal_request(conn, seeded, "erasure")
    row = await service.refuse(
        conn,
        row,
        reason="Not a rights request",
        role=DPO,
        actor_id=int(seeded["users"]["dpo"]["id"]),
    )
    assert row["download_expires_at"] is None
    assert await repo.response_files_of(conn, int(row["request_id"])) == []
    [closed] = [a for a in sent if a[0] == "send_rights_closed"]
    assert closed[4] == "Not a rights request"


async def test_with_no_account_the_mail_says_how_to_get_them(
    conn: Any, seeded: dict[str, Any], redis_conn: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[tuple[Any, ...]] = []
    monkeypatch.setattr(service, "_dispatch", lambda *a: sent.append(a))
    await _unthrottle(redis_conn, "stranger@example.org")
    made = await service.submit_public(
        conn,
        request_type="access",
        contact="stranger@example.org",
        name=None,
        request_text="What do you hold?",
        ip_address="127.0.0.4",
    )
    row = await repo.by_reference(conn, made["reference"])
    assert row is not None and row["subject_user_id"] is None
    row = await service.refuse(
        conn,
        row,
        reason="We hold nothing under that address.",
        role=DPO,
        actor_id=int(seeded["users"]["dpo"]["id"]),
        files=[_stored("letter.pdf")],
    )
    assert row["download_expires_at"] is None, "nobody can sign in to download"
    [closed] = [a for a in sent if a[0] == "send_rights_closed"]
    assert "- letter.pdf" in closed[4]
    assert "Reply to this message" in closed[4] and "your account" not in closed[4]
