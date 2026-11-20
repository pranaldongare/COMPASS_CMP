"""A breach notice to somebody with no account, by a link only their mobile
opens (the product owner, 2026-11-20).

The text carries a link, not the notice; the link shows the reference and,
masked, the mobile a code goes to; the code - sent to the number on the
breach's list, never one typed - opens the notice in full, on the trail.
A link for anybody else, or altered, opens nothing.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from cmp.db.sql import fetch_all
from cmp.domain.breach import notice_link, notices
from cmp.tasks import dispatch as dispatch_mod
from tests.conftest import plain
from tests.integration.test_breach_lists import WORDS, _csv, _recorded, _take

pytestmark = pytest.mark.integration

MOBILE = "+919000011114"


@pytest.fixture
def codes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, tuple[Any, ...]]]:
    sent: list[tuple[str, tuple[Any, ...]]] = []

    def capture(task: Any, *args: Any, **kwargs: Any) -> str:
        sent.append((task.name, args))
        return "queued-in-a-test"

    monkeypatch.setattr(dispatch_mod, "dispatch_required", capture)
    monkeypatch.setattr(dispatch_mod, "dispatch_optional", capture)
    return sent


async def _approved(conn: Any, seeded: dict[str, Any]) -> tuple[str, str, str]:
    """A breach with one contact, a mobile alone, and an approved notice."""
    dpo = int(seeded["users"]["dpo"]["id"])
    uuid = await _recorded(conn, seeded)
    await _take(conn, seeded, uuid, "contacts", _csv("name,mobile", f"Ravi,{MOBILE}"))
    view = await notices.draft(conn, breach_uuid=uuid, words=WORDS, actor_id=dpo)
    notice_uuid = str(view["versions"][-1]["notice_uuid"])
    await notices.approve(conn, breach_uuid=uuid, notice_uuid=notice_uuid, actor_id=dpo)
    [contact] = await fetch_all(
        conn,
        """SELECT c.contact_uuid::text AS contact_uuid FROM breach_contact c
             JOIN breach b USING (breach_id) WHERE b.breach_uuid = %s""",
        (uuid,),
    )
    return uuid, notice_uuid, str(contact["contact_uuid"])


async def test_the_link_opens_the_notice_only_with_the_code_sent_to_that_mobile(
    conn: Any, seeded: dict[str, Any], codes: list[Any], redis_conn: Any
) -> None:
    uuid, notice_uuid, contact_uuid = await _approved(conn, seeded)
    token = notice_link.token(notice_uuid, contact_uuid)
    assert len(token) == 64

    row = await notice_link.open_link(conn, token)
    masked = await notice_link.masked_mobile(row)
    assert masked.endswith("14") and "9000011" not in masked

    await notice_link.send_code(conn, token)
    [(name, args)] = codes
    assert name == "cmp.notifications.send_breach_notice_code"
    assert plain(args[0]) == MOBILE, "the number on the list, never one typed"
    code = str(args[1])

    from cmp.core.errors import BadRequest

    with pytest.raises(BadRequest):
        await notice_link.read(conn, token, "000000" if code != "000000" else "111111")
    notice = await notice_link.read(conn, token, code)
    # Opened for her: she has no session the portal could open them with.
    assert notice["what_happened"] == WORDS["what_happened"]
    assert not any(str(notice[f]).startswith("SE::") for f in WORDS)
    trail = await fetch_all(
        conn,
        """SELECT a.event_type FROM audit_log a JOIN breach b ON b.breach_id = a.entity_id
            WHERE a.entity_type = 'breach' AND b.breach_uuid = %s""",
        (uuid,),
    )
    assert "breach_notice.opened" in [t["event_type"] for t in trail]


@pytest.mark.parametrize("change", ["other_contact", "altered", "short", "unapproved"])
async def test_a_link_for_anybody_else_or_altered_opens_nothing(
    conn: Any, seeded: dict[str, Any], change: str
) -> None:
    _, notice_uuid, contact_uuid = await _approved(conn, seeded)
    token = notice_link.token(notice_uuid, contact_uuid)
    if change == "other_contact":
        token = notice_link.token(notice_uuid, str(uuid4()))
    elif change == "altered":
        token = token[:-2] + ("AA" if token[-2:] != "AA" else "BB")
    elif change == "short":
        token = token[:40]
    else:
        token = notice_link.token(str(uuid4()), contact_uuid)
    with pytest.raises(notice_link.LinkInvalid):
        await notice_link.open_link(conn, token)


async def test_the_text_carries_the_link_not_the_notice(
    conn: Any, seeded: dict[str, Any], codes: list[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The worker gives the text a link to the notice; the words stay off it."""
    from cmp.core.messages import Channel, Message
    from cmp.infrastructure import messaging

    _, notice_uuid, contact_uuid = await _approved(conn, seeded)
    monkeypatch.setattr(messaging, "load_overrides", lambda: {})
    _, body = messaging.render(
        Message.BREACH_NOTICE_DIRECT,
        Channel.SMS,
        {
            "breach_reference": "BR-1",
            "what_happened": "A very long account " * 200,
            "consequences": "c",
            "measures": "m",
            "protective_steps": "p",
            "contact": "q",
            "notice_url": notice_link.url(notice_uuid, contact_uuid),
        },
    )
    assert "/breach-notice/" + notice_link.token(notice_uuid, contact_uuid) in body
    assert "A very long account" not in body
    assert len(body) <= 320, "two text parts at most"
