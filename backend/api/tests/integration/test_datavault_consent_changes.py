"""DataVault is told of every consent change, by itself (0071, 2026-11-13).

A withdrawal, in full or in part, a consent given again, and a validity that
has run out, each become one message to `POST {erasure address}/consent-changes`
- worked out by the worker from the consents as they were saved, queued before
it is sent, and tried until DataVault answers. Nothing on record before the
administrator switched it on is told; what happens afterwards is, whatever the
consent's age. It is on the trail against the consent, the person and the
project.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest

from cmp.core.errors import ValidationFailed
from cmp.core.security import content_hash, new_token, token_fingerprint
from cmp.db.repositories import datavault as repo
from cmp.domain.consent import service as consent_service
from cmp.domain.datavault import connection
from cmp.domain.datavault import consent_changes as changes

pytestmark = pytest.mark.integration

URL = "https://datavault.internal/api"
ERASE_URL = "https://datavault-erase.internal/api/v1"
KEY = "dv-key-0123456789"
IMG, VID = "DVT-IMG-01", "DVT-VID-02"


# ------------------------------------------------------------------ the world
async def _fresh(conn: Any) -> None:
    """The connection as a deployment that has never sent a consent change
    has it: the database these tests share may have had one switched on."""
    await conn.execute(
        """UPDATE datavault_connection
              SET consent_changes = false, consent_changes_after = NULL,
                  consent_changes_since = NULL
            WHERE connection_id = 1"""
    )


async def _on(conn: Any, seeded: dict[str, Any], **changes_: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "base_url": URL,
        "erasure_url": ERASE_URL,
        "api_key": KEY,
        "clear_api_key": False,
        "api_key_header": None,
        "enabled": True,
        "consent_changes": True,
        **changes_,
    }
    return await connection.save(conn, actor_id=int(seeded["users"]["admin"]["id"]), **values)


async def _notice(conn: Any, seeded: dict[str, Any], codes: tuple[str, ...] = (IMG, VID)) -> Any:
    """A published notice of the seeded project with these purposes: the
    seeded one has a single purpose, and a withdrawal in part needs two."""
    dpo = seeded["users"]["dpo"]["id"]
    purposes: dict[str, dict[str, Any]] = {}
    for code in codes:
        row = await (
            await conn.execute(
                """INSERT INTO purpose (purpose_code, name, description, uses, lawful_basis,
                                        data_categories, retention_period, retention_basis,
                                        erasure_trigger, status, created_by, office_id)
                   VALUES (%s, %s, 'd', 'u', 'consent_s6', ARRAY['name'], interval '1 year',
                           'business_policy', 'withdrawal', 'active', %s,
                           (SELECT office_id FROM office WHERE office_code = 'rnd'))
                   RETURNING purpose_id, purpose_uuid, purpose_code""",
                (code, f"Purpose {code}", dpo),
            )
        ).fetchone()
        purposes[code] = dict(row)
    notice_id = (
        await (
            await conn.execute(
                """INSERT INTO notice (notice_code, project_id, version, withdraw_url,
                                       exercise_rights_url, board_complaint_url, dpo_contact)
                   VALUES (%s, %s, 1, 'https://x/w', 'https://x/r',
                           'https://dpb.gov.in', 'dpo@test.local')
                   RETURNING notice_id""",
                (f"N-DV-{new_token()[:8]}", seeded["project"]["project_id"]),
            )
        ).fetchone()
    )["notice_id"]
    text = "The notice the DataVault tests are given."
    await conn.execute(
        """INSERT INTO notice_language (notice_id, language_code, rendered_text,
                                        content_hash, created_by, approved_by, approved_at)
           VALUES (%s, 'english', %s, %s, %s, %s, now())""",
        (notice_id, text, content_hash(text), dpo, dpo),
    )
    for p in purposes.values():
        await conn.execute(
            "INSERT INTO notice_purpose (notice_id, purpose_id) VALUES (%s, %s)",
            (notice_id, p["purpose_id"]),
        )
    await conn.execute(
        "UPDATE notice SET status = 'superseded' WHERE project_id = %s AND status = 'published'",
        (seeded["project"]["project_id"],),
    )
    await conn.execute(
        """UPDATE notice SET status = 'published', recipients_text = 'Test Site',
                  approved_by = %s, published_at = now()
            WHERE notice_id = %s""",
        (dpo, notice_id),
    )
    return {"notice_id": notice_id, "purposes": purposes}


async def _capture(
    conn: Any, seeded: dict[str, Any], notice: dict[str, Any], granted: tuple[str, ...]
) -> dict[str, Any]:
    raw = new_token()
    await conn.execute(
        """INSERT INTO consent_link (notice_id, site_id, token, expires_at, created_by)
           VALUES (%s, %s, %s, now() + interval '1 day', %s)""",
        (
            notice["notice_id"],
            seeded["site"]["site_id"],
            token_fingerprint(raw)[:64],
            seeded["users"]["dpo"]["id"],
        ),
    )
    await consent_service.serve_notice(
        conn, token=raw, language_code="english", user_id=seeded["subject"]["id"]
    )
    return await consent_service.capture(
        conn,
        token=raw,
        user_id=seeded["subject"]["id"],
        language_code="english",
        grants={str(p["purpose_uuid"]): code in granted for code, p in notice["purposes"].items()},
        action_type="checkbox_click",
        ip_address="203.0.113.7",
    )


async def _head(conn: Any, seeded: dict[str, Any], notice: dict[str, Any]) -> dict[str, Any]:
    row = await (
        await conn.execute(
            """SELECT consent_id, consent_uuid::text AS consent_uuid, affirmative_action_at
                 FROM consent_artefact WHERE auth_user_id = %s AND notice_id = %s
                ORDER BY consent_id DESC LIMIT 1""",
            (seeded["subject"]["id"], notice["notice_id"]),
        )
    ).fetchone()
    return dict(row)


async def _withdraw(
    conn: Any, seeded: dict[str, Any], notice: dict[str, Any], *codes: str
) -> dict[str, Any]:
    """Withdraw these purposes of the consent in force - all of them when none
    is named - and return the consent that replaces it."""
    head = await _head(conn, seeded, notice)
    await consent_service.withdraw(
        conn,
        consent_uuid=head["consent_uuid"],
        user_id=seeded["subject"]["id"],
        purpose_uuids=[str(notice["purposes"][c]["purpose_uuid"]) for c in codes] or None,
        withdraw_all=not codes,
        ip_address="203.0.113.7",
    )
    return await _head(conn, seeded, notice)


async def _read(conn: Any) -> int:
    """One run of the worker's first half: every unread chain, read."""
    link = await connection.for_consent_changes(conn)
    assert link is not None
    queued = 0
    for c in await changes.unread(conn, link):
        queued += await changes.note_chain(
            conn, link, user_id=int(c["auth_user_id"]), notice_id=int(c["notice_id"])
        )
    return queued


def _vault(
    seen: list[dict[str, Any]], *, result: str = "applied", affected: int = 2, status: int = 200
) -> Any:
    def answer(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append({"url": str(request.url), "key": request.headers.get("X-API-Key"), **body})
        if status != 200:
            return httpx.Response(status, json={"error": "invalid_request"})
        return httpx.Response(
            200,
            json={"message_id": body["message_id"], "result": result, "assets_affected": affected},
        )

    return httpx.MockTransport(answer)


async def _deliver(conn: Any, transport: Any) -> int:
    """One run of the worker's second half: every message that is due, sent."""
    link = await connection.for_consent_changes(conn)
    assert link is not None
    rows = await changes.due(conn)
    for row in rows:
        answer = await changes.send(link, row, transport=transport)
        if isinstance(answer, str):
            await changes.undelivered(conn, row, failure=answer)
        else:
            await changes.delivered(conn, row, answer)
    return len(rows)


async def _messages(conn: Any, root: dict[str, Any]) -> list[dict[str, Any]]:
    rows = await (
        await conn.execute(
            """SELECT * FROM datavault_consent_change WHERE chain_root_id = %s
                ORDER BY change_id""",
            (root["consent_id"],),
        )
    ).fetchall()
    return [dict(r) for r in rows]


async def _trail(conn: Any, event: str, consent_id: int) -> list[dict[str, Any]]:
    rows = await (
        await conn.execute(
            """SELECT detail_json AS detail, actor_user_id, subject_user_id FROM audit_log
                WHERE event_type = %s AND entity_type = 'consent_artefact' AND entity_id = %s
                ORDER BY log_id""",
            (event, consent_id),
        )
    ).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------- the connection
async def test_consent_changes_are_off_until_the_administrator_says_so(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _fresh(conn)
    shown = await _on(conn, seeded, consent_changes=False)
    assert shown["consent_changes"] is False and shown["erasure_url"] == ERASE_URL
    assert shown["id_format"] == "numeric", "the numbers the console shows, to start with"
    assert await connection.for_consent_changes(conn) is None
    assert await connection.for_erasure(conn) is not None, "the erasure button has its address"

    shown = await _on(conn, seeded)
    assert shown["consent_changes"] is True and shown["consent_changes_waiting"] == 0
    link = await connection.for_consent_changes(conn)
    assert link is not None and link.erasure_url == ERASE_URL and link.api_key == KEY

    # The whole connection switched off: nothing goes out, and nothing is lost.
    await _on(conn, seeded, enabled=False)
    assert await connection.for_consent_changes(conn) is None
    assert await connection.for_erasure(conn) is None


async def test_consent_changes_need_the_address_they_go_to(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _fresh(conn)
    with pytest.raises(ValidationFailed) as refused:
        await _on(conn, seeded, erasure_url=None)
    assert "erasure address" in str(refused.value)
    with pytest.raises(ValidationFailed):
        await _on(conn, seeded, erasure_url="datavault-erase.internal")
    with pytest.raises(ValidationFailed):
        await _on(conn, seeded, id_format="names")
    # Without them the address may be left empty: the lookup works as it did.
    shown = await _on(conn, seeded, erasure_url=None, consent_changes=False)
    assert shown["erasure_url"] is None and shown["enabled"] is True


async def test_where_they_start_is_settled_the_first_time_and_never_moved(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _fresh(conn)
    notice = await _notice(conn, seeded)
    before = await _capture(conn, seeded, notice, (IMG, VID))
    await _on(conn, seeded)
    first = await repo.connection(conn)
    assert int(first["consent_changes_after"]) < int(before["consent_id"]), (
        "a consent given in the minute before is still read: it may have been saving"
    )
    assert first["consent_changes_since"] is not None

    # Switched off, a consent is saved, and switched on again: the start stays,
    # so what happened meanwhile is read when it is back on.
    await _on(conn, seeded, consent_changes=False)
    await _withdraw(conn, seeded, notice, VID)
    await _on(conn, seeded)
    again = await repo.connection(conn)
    assert again["consent_changes_after"] == first["consent_changes_after"]
    assert again["consent_changes_since"] == first["consent_changes_since"]
    assert await _read(conn) == 1, "the withdrawal made while it was off"


async def test_the_trail_says_what_changed_and_never_an_address(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _fresh(conn)
    start = await (
        await conn.execute("SELECT coalesce(max(log_id), 0) AS n FROM audit_log")
    ).fetchone()
    await _on(conn, seeded, consent_changes=False)
    await _on(conn, seeded, id_format="uuid")
    rows = await (
        await conn.execute(
            """SELECT detail_json AS detail, detail_json::text AS said FROM audit_log
                WHERE event_type = 'datavault.connection_changed' AND log_id > %s
                ORDER BY log_id""",
            (start["n"],),
        )
    ).fetchall()
    first, second = (r["detail"] for r in rows)
    assert first["erasure_address_changed"] is True and first["consent_changes"] is False
    assert second["erasure_address_changed"] is False
    assert (second["consent_changes"], second["consent_changes_were"]) == (True, False)
    assert (second["id_format"], second["id_format_was"]) == ("uuid", "numeric")
    assert all(ERASE_URL not in r["said"] and KEY not in r["said"] for r in rows)


# ------------------------------------------------------------ what is a change
async def test_a_first_consent_is_not_a_change(conn: Any, seeded: dict[str, Any]) -> None:
    await _fresh(conn)
    await _on(conn, seeded)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    assert await _read(conn) == 0
    assert await _messages(conn, first) == []
    link = await connection.for_consent_changes(conn)
    assert link is not None
    assert await changes.unread(conn, link) == [], "read once, and not again"


async def test_a_withdrawal_is_told_and_delivered(conn: Any, seeded: dict[str, Any]) -> None:
    await _fresh(conn)
    await _on(conn, seeded)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    assert await _read(conn) == 0
    gone = await _withdraw(conn, seeded, notice)
    assert await _read(conn) == 1

    [queued] = await _messages(conn, first)
    assert (queued["change"], queued["action"]) == ("withdrawn", "restrict")
    assert queued["delivered_at"] is None and queued["attempts"] == 0

    seen: list[dict[str, Any]] = []
    assert await _deliver(conn, _vault(seen)) >= 1
    [sent] = [m for m in seen if m["message_id"] == str(queued["message_uuid"])]
    assert sent.pop("url") == ERASE_URL + "/consent-changes"
    assert sent.pop("key") == KEY
    assert sent == {
        "message_id": str(queued["message_uuid"]),
        "sequence": queued["change_id"],
        # By number, as the administrator's switch starts: the IDs the console shows.
        "person_id": int(seeded["subject"]["id"]),
        "project_id": int(seeded["project"]["project_id"]),
        "consent_id": int(gone["consent_id"]),
        "consent_ids": [int(first["consent_id"]), int(gone["consent_id"])],
        "change": "withdrawn",
        "action": "restrict",
        "purposes_granted": [],
        "purposes_removed": [IMG, VID],
        "effective_at": gone["affirmative_action_at"].isoformat(),
    }
    assert all(type(sent[k]) is int for k in ("sequence", "person_id", "project_id", "consent_id"))

    [stored] = await _messages(conn, first)
    assert stored["delivered_at"] is not None and stored["failure"] is None
    assert (stored["result"], stored["assets_affected"], stored["attempts"]) == ("applied", 2, 1)
    link = await connection.for_consent_changes(conn)
    assert link is not None
    assert [m for m in await changes.due(conn) if m["change_id"] == queued["change_id"]] == []


async def test_it_is_on_the_trail_of_the_consent_the_person_and_the_project(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _fresh(conn)
    await _on(conn, seeded)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    await _read(conn)
    gone = await _withdraw(conn, seeded, notice, VID)
    await _read(conn)
    await _deliver(conn, _vault([], affected=3))

    [queued] = await _trail(conn, "datavault.consent_change_queued", int(gone["consent_id"]))
    [delivered] = await _trail(conn, "datavault.consent_change_delivered", int(gone["consent_id"]))
    [message] = await _messages(conn, first)
    for entry in (queued, delivered):
        assert entry["subject_user_id"] == seeded["subject"]["id"], "against the person"
        assert entry["actor_user_id"] is None, "nobody pressed anything"
        assert entry["detail"]["project"] == str(seeded["project"]["project_uuid"])
        assert entry["detail"]["sequence"] == message["change_id"]
        assert (entry["detail"]["change"], entry["detail"]["action"]) == (
            "partly_withdrawn",
            "restrict",
        )
    assert queued["detail"]["purposes_granted"] == [IMG]
    assert queued["detail"]["purposes_removed"] == [VID]
    assert (delivered["detail"]["result"], delivered["detail"]["assets_affected"]) == ("applied", 3)

    # The project's own trail reads them too - and of her consent nothing else.
    from cmp.core.pagination import PageRequest
    from cmp.db.repositories import audit as audit_repo

    of_project, _, _ = await audit_repo.search(
        conn,
        PageRequest(limit=200, cursor=None, sort_field="occurred_at", descending=True),
        audit_repo.AuditFilters(
            entity_type="project", entity_id=int(seeded["project"]["project_id"])
        ),
    )
    hers = [e["event_type"] for e in of_project if e["entity_type"] == "consent_artefact"]
    assert sorted(hers) == [
        "datavault.consent_change_delivered",
        "datavault.consent_change_queued",
    ]
    # And the person's: every event is written against her.
    of_person, _, _ = await audit_repo.search(
        conn,
        PageRequest(limit=200, cursor=None, sort_field="occurred_at", descending=True),
        audit_repo.AuditFilters(
            subject_uuid=str(seeded["subject"]["uuid"]), event_group="datavault"
        ),
    )
    assert {e["event_type"] for e in of_person} == {
        "datavault.consent_change_delivered",
        "datavault.consent_change_queued",
    }


async def test_a_withdrawal_in_part_says_what_is_left(conn: Any, seeded: dict[str, Any]) -> None:
    await _fresh(conn)
    await _on(conn, seeded)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    await _read(conn)
    await _withdraw(conn, seeded, notice, VID)
    assert await _read(conn) == 1
    [m] = await _messages(conn, first)
    assert (m["change"], m["action"]) == ("partly_withdrawn", "restrict")
    assert (m["purposes_granted"], m["purposes_removed"]) == ([IMG], [VID])


async def test_a_consent_given_again_lifts_the_restriction(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _fresh(conn)
    await _on(conn, seeded)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    await _read(conn)
    second = await _withdraw(conn, seeded, notice, VID)
    await _read(conn)
    await _deliver(conn, _vault([]))
    third = await _capture(conn, seeded, notice, (IMG, VID))
    assert await _read(conn) == 1

    seen: list[dict[str, Any]] = []
    await _deliver(conn, _vault(seen))
    [sent] = [m for m in seen if m["consent_id"] == int(third["consent_id"])]
    assert (sent["change"], sent["action"]) == ("granted_again", "lift_restriction")
    assert (sent["purposes_granted"], sent["purposes_removed"]) == ([IMG, VID], [])
    assert sent["consent_ids"] == [
        int(first["consent_id"]),
        int(second["consent_id"]),
        int(third["consent_id"]),
    ], "the whole chain, oldest first: an asset may carry any of them"
    one, two = await _messages(conn, first)
    assert two["change_id"] > one["change_id"], "the sequence grows with every message"


async def test_a_second_consent_that_declines_a_purpose_is_a_withdrawal_in_part(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _fresh(conn)
    await _on(conn, seeded)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    await _read(conn)
    await _capture(conn, seeded, notice, (IMG,))
    assert await _read(conn) == 1
    [m] = await _messages(conn, first)
    assert (m["change"], m["purposes_granted"], m["purposes_removed"]) == (
        "partly_withdrawn",
        [IMG],
        [VID],
    )


async def test_a_change_that_changes_nothing_datavault_holds_sends_nothing(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """She gives the same consent again: a new record, and nothing to tell."""
    await _fresh(conn)
    await _on(conn, seeded)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG,))
    await _capture(conn, seeded, notice, (IMG,))
    assert await _read(conn) == 0
    assert await _messages(conn, first) == []
    link = await connection.for_consent_changes(conn)
    assert link is not None
    assert await changes.unread(conn, link) == []


async def test_several_changes_read_at_once_are_one_message_for_where_it_ends(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _fresh(conn)
    await _on(conn, seeded)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    await _withdraw(conn, seeded, notice, VID)
    await _capture(conn, seeded, notice, (IMG, VID))
    last = await _withdraw(conn, seeded, notice, IMG)
    assert await _read(conn) == 1, "four consents, read in one go"
    [m] = await _messages(conn, first)
    assert m["consent_id"] == last["consent_id"]
    assert (m["change"], m["purposes_granted"], m["purposes_removed"]) == (
        "partly_withdrawn",
        [VID],
        [IMG],
    )
    assert m["effective_at"] == last["affirmative_action_at"]


async def test_taking_one_purpose_away_and_giving_another_back_is_told_as_a_restriction(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """One label has to do for both: the careful one, with the state whole."""
    await _fresh(conn)
    await _on(conn, seeded)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    await _read(conn)
    await _withdraw(conn, seeded, notice, VID)
    await _read(conn)  # DataVault is told: IMG only
    await _capture(conn, seeded, notice, (VID,))  # IMG declined, VID given again
    assert await _read(conn) == 1
    newest = (await _messages(conn, first))[-1]
    assert (newest["change"], newest["action"]) == ("partly_withdrawn", "restrict")
    assert (newest["purposes_granted"], newest["purposes_removed"]) == ([VID], [IMG])


async def test_an_earlier_message_still_unsent_is_set_aside(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _fresh(conn)
    await _on(conn, seeded)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    await _read(conn)
    await _withdraw(conn, seeded, notice, VID)
    await _read(conn)
    await _withdraw(conn, seeded, notice, IMG)
    await _read(conn)
    older, newer = await _messages(conn, first)
    assert older["superseded_at"] is not None and older["delivered_at"] is None
    assert newer["superseded_at"] is None
    # Worked out from what the older one said, which DataVault never heard:
    # the newer carries the whole state, so it is enough alone.
    assert (newer["change"], newer["purposes_granted"]) == ("withdrawn", [])

    seen: list[dict[str, Any]] = []
    await _deliver(conn, _vault(seen))
    mine = [m for m in seen if m["consent_ids"][0] == int(first["consent_id"])]
    assert [m["sequence"] for m in mine] == [newer["change_id"]]


# --------------------------------------------------------------- where it starts
async def _on_a_while_after(conn: Any, seeded: dict[str, Any]) -> None:
    """Switched on for the first time well after the consents so far: a test
    takes milliseconds, and the platform still reads what was given in the
    minute before the switch."""
    await _on(conn, seeded)
    await conn.execute(
        """UPDATE datavault_connection
              SET consent_changes_after = (SELECT max(consent_id) FROM consent_artefact)
            WHERE connection_id = 1"""
    )


async def test_nothing_on_record_before_it_was_switched_on_is_told(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _fresh(conn)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    await _withdraw(conn, seeded, notice, VID)
    await _on_a_while_after(conn, seeded)
    assert await _read(conn) == 0
    assert await _messages(conn, first) == []


async def test_a_change_saved_as_it_was_switched_on_is_not_passed_over(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """A withdrawal still saving as the administrator switches consent changes
    on takes its number before the switch and commits after it. The start is
    put a minute back, so it is read and told."""
    await _fresh(conn)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    await _withdraw(conn, seeded, notice, VID)
    await _on(conn, seeded)
    assert await _read(conn) == 1
    [m] = await _messages(conn, first)
    assert (m["change"], m["purposes_removed"]) == ("partly_withdrawn", [VID])


async def test_a_change_made_after_it_to_a_consent_given_before_it_is_told_whole(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _fresh(conn)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    second = await _withdraw(conn, seeded, notice, VID)
    await _on_a_while_after(conn, seeded)
    third = await _withdraw(conn, seeded, notice, IMG)
    assert await _read(conn) == 1

    seen: list[dict[str, Any]] = []
    await _deliver(conn, _vault(seen))
    [sent] = [m for m in seen if m["consent_id"] == int(third["consent_id"])]
    assert sent["change"] == "withdrawn"
    # From the consent in force when it was switched on: IMG was all it granted.
    assert (sent["purposes_granted"], sent["purposes_removed"]) == ([], [IMG])
    assert sent["consent_ids"] == [
        int(first["consent_id"]),
        int(second["consent_id"]),
        int(third["consent_id"]),
    ], "the chain whole, the consents from before included"


# ------------------------------------------------------------------- delivery
async def test_named_by_uuid_when_the_administrator_switches(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _fresh(conn)
    await _on(conn, seeded, id_format="uuid")
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    await _read(conn)
    gone = await _withdraw(conn, seeded, notice)
    await _read(conn)
    seen: list[dict[str, Any]] = []
    await _deliver(conn, _vault(seen))
    [sent] = [m for m in seen if m["consent_id"] == gone["consent_uuid"]]
    assert sent["person_id"] == str(seeded["subject"]["uuid"])
    assert sent["project_id"] == str(seeded["project"]["project_uuid"])
    assert sent["consent_ids"] == [str(first["consent_uuid"]), gone["consent_uuid"]]
    assert type(sent["sequence"]) is int, "the sequence is a number either way"


@pytest.mark.parametrize("result", ["duplicate", "stale"])
async def test_an_answer_that_means_datavault_has_it_ends_the_tries(
    conn: Any, seeded: dict[str, Any], result: str
) -> None:
    await _fresh(conn)
    await _on(conn, seeded)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    await _read(conn)
    await _withdraw(conn, seeded, notice)
    await _read(conn)
    await _deliver(conn, _vault([], result=result, affected=0))
    [m] = await _messages(conn, first)
    assert m["delivered_at"] is not None and (m["result"], m["assets_affected"]) == (result, 0)


async def test_a_message_not_delivered_is_kept_and_tried_again_later(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _fresh(conn)
    await _on(conn, seeded)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    await _read(conn)
    await _withdraw(conn, seeded, notice)
    await _read(conn)

    def gone(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    waits: list[timedelta] = []
    for _ in range(3):
        # Its time has come again, as far as the test is concerned.
        await conn.execute(
            """UPDATE datavault_consent_change SET next_attempt_at = now()
                WHERE chain_root_id = %s""",
            (first["consent_id"],),
        )
        await _deliver(conn, httpx.MockTransport(gone))
        [m] = await _messages(conn, first)
        assert m["delivered_at"] is None and m["failure"] == "unreachable"
        waits.append(m["next_attempt_at"] - datetime.now(UTC))
    assert m["attempts"] == 3
    assert waits[0] < waits[1] < waits[2], "the wait grows"
    assert waits[2] < timedelta(minutes=5)
    assert [x for x in await changes.due(conn) if x["change_id"] == m["change_id"]] == [], (
        "not tried again before its time"
    )
    shown = await connection.overview(conn)
    assert shown["consent_changes_waiting"] >= 1
    assert shown["consent_changes_last_failure"] == "DataVault could not be reached."

    # A refusal does not mend by itself: tried hourly.
    await conn.execute(
        "UPDATE datavault_consent_change SET next_attempt_at = now() WHERE chain_root_id = %s",
        (first["consent_id"],),
    )
    await _deliver(conn, _vault([], status=400))
    [m] = await _messages(conn, first)
    assert m["failure"] == "status_400" and m["attempts"] == 4
    assert m["next_attempt_at"] - datetime.now(UTC) > timedelta(minutes=55)

    # And when DataVault is back, it goes.
    await conn.execute(
        "UPDATE datavault_consent_change SET next_attempt_at = now() WHERE chain_root_id = %s",
        (first["consent_id"],),
    )
    await _deliver(conn, _vault([]))
    [m] = await _messages(conn, first)
    assert m["delivered_at"] is not None and m["failure"] is None and m["attempts"] == 5


async def test_a_delivery_recorded_twice_is_on_the_trail_once(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _fresh(conn)
    await _on(conn, seeded)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    await _read(conn)
    gone = await _withdraw(conn, seeded, notice)
    await _read(conn)
    [row] = [r for r in await changes.due(conn) if r["consent_id"] == gone["consent_id"]]
    from cmp.infrastructure.datavault import ChangeResult

    await changes.delivered(conn, row, ChangeResult(result="applied", assets_affected=1))
    await changes.delivered(conn, row, ChangeResult(result="duplicate", assets_affected=0))
    [m] = await _messages(conn, first)
    assert (m["result"], m["assets_affected"]) == ("applied", 1), "the first answer stands"
    assert (
        len(await _trail(conn, "datavault.consent_change_delivered", int(gone["consent_id"]))) == 1
    )


# --------------------------------------------------------------------- lapses
async def _runs_out(conn: Any, notice: dict[str, Any], code: str, *, behaviour: str) -> None:
    """The purpose's validity ended a day before her consent was given: run
    out by the retention sweep's own test, as soon as the consent exists."""
    await conn.execute(
        """UPDATE purpose SET consent_validity_period = interval '-1 day',
                              lapse_behaviour = %s::lapse_behaviour
            WHERE purpose_id = %s""",
        (behaviour, notice["purposes"][code]["purpose_id"]),
    )


async def _switched_on_a_month_ago(conn: Any) -> None:
    await conn.execute(
        """UPDATE datavault_connection SET consent_changes_since = now() - interval '30 days'
            WHERE connection_id = 1"""
    )


async def _night(conn: Any) -> int:
    link = await connection.for_consent_changes(conn)
    assert link is not None
    queued = 0
    for row in await changes.lapsed(conn, link):
        queued += await changes.note_lapse(conn, link, row)
    return queued


async def test_a_validity_that_runs_out_is_told_once(conn: Any, seeded: dict[str, Any]) -> None:
    await _fresh(conn)
    await _on(conn, seeded)
    await _switched_on_a_month_ago(conn)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    await _read(conn)
    assert await _night(conn) == 0, "nothing has run out"
    await _runs_out(conn, notice, VID, behaviour="quarantine")
    assert await _night(conn) == 1
    [m] = await _messages(conn, first)
    assert (m["change"], m["action"]) == ("expired", "restrict"), "a restriction, never a deletion"
    assert (m["purposes_granted"], m["purposes_removed"]) == ([IMG], [VID])
    assert m["consent_id"] == first["consent_id"]
    assert await _night(conn) == 0, "told once"
    [queued] = await _trail(conn, "datavault.consent_change_queued", int(first["consent_id"]))
    assert queued["detail"]["change"] == "expired"


async def test_a_purpose_whose_lapse_does_nothing_sends_nothing(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _fresh(conn)
    await _on(conn, seeded)
    await _switched_on_a_month_ago(conn)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    await _read(conn)
    await _runs_out(conn, notice, VID, behaviour="none")
    assert await _night(conn) == 0
    assert await _messages(conn, first) == []


async def test_a_validity_that_had_run_out_before_it_was_switched_on_is_not_told(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _fresh(conn)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    await _runs_out(conn, notice, VID, behaviour="quarantine")
    await _on_a_while_after(conn, seeded)  # switched on now: it ran out a day ago
    link = await connection.for_consent_changes(conn)
    assert link is not None
    assert [
        r for r in await changes.lapsed(conn, link) if r["consent_id"] == first["consent_id"]
    ] == []
    assert await _night(conn) == 0
    assert await _messages(conn, first) == []


async def test_a_consent_given_before_it_was_switched_on_is_told_when_its_validity_runs_out(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _fresh(conn)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    await _on_a_while_after(conn, seeded)
    await _switched_on_a_month_ago(conn)
    await _runs_out(conn, notice, VID, behaviour="erase")
    assert await _night(conn) == 1
    [m] = await _messages(conn, first)
    assert (m["change"], m["action"]) == ("expired", "restrict")
    assert (m["purposes_granted"], m["purposes_removed"]) == ([IMG], [VID])


async def test_a_withdrawal_does_not_bring_back_a_purpose_whose_validity_ran_out(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """A withdrawal copies every other grant forward, the run-out one too, and
    starts its clock again. DataVault is not to take that as a grant."""
    await _fresh(conn)
    await _on(conn, seeded)
    await _switched_on_a_month_ago(conn)
    third_code = "DVT-AUD-03"
    notice = await _notice(conn, seeded, (IMG, VID, third_code))
    first = await _capture(conn, seeded, notice, (IMG, VID, third_code))
    await _read(conn)
    await _runs_out(conn, notice, VID, behaviour="quarantine")
    assert await _night(conn) == 1
    await _withdraw(conn, seeded, notice, third_code)
    assert await _read(conn) == 1
    newest = (await _messages(conn, first))[-1]
    assert newest["change"] == "partly_withdrawn"
    assert newest["purposes_granted"] == [IMG], "VID stays out, though the withdrawal copied it"
    assert newest["purposes_removed"] == [third_code]
    assert await _night(conn) == 0, "and its lapse is not reported a second time"


async def test_a_run_out_purpose_not_yet_reported_goes_out_with_the_withdrawal(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _fresh(conn)
    await _on(conn, seeded)
    await _switched_on_a_month_ago(conn)
    third_code = "DVT-AUD-03"
    notice = await _notice(conn, seeded, (IMG, VID, third_code))
    first = await _capture(conn, seeded, notice, (IMG, VID, third_code))
    await _read(conn)
    await _runs_out(conn, notice, VID, behaviour="quarantine")
    await _withdraw(conn, seeded, notice, third_code)  # before any night's run
    assert await _read(conn) == 1
    [m] = await _messages(conn, first)
    assert m["purposes_granted"] == [IMG]
    assert m["purposes_removed"] == [third_code, VID] or m["purposes_removed"] == [
        VID,
        third_code,
    ]
    assert await _night(conn) == 0, "nothing is left for the night to tell"


async def test_a_lapse_waits_for_a_change_not_read_yet(conn: Any, seeded: dict[str, Any]) -> None:
    """A consent saved and not yet read has its own message to come; a lapse
    message worked out without it would say less than it."""
    await _fresh(conn)
    await _on(conn, seeded)
    await _switched_on_a_month_ago(conn)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    await _read(conn)
    await _capture(conn, seeded, notice, (IMG, VID))  # not read yet
    await _runs_out(conn, notice, VID, behaviour="quarantine")
    assert await _night(conn) == 0
    await _read(conn)
    assert await _night(conn) == 1
    [m] = await _messages(conn, first)
    assert (m["change"], m["purposes_removed"]) == ("expired", [VID])


async def test_granting_it_again_after_a_lapse_lifts_it_and_a_new_lapse_is_told(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _fresh(conn)
    await _on(conn, seeded)
    await _switched_on_a_month_ago(conn)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    await _read(conn)
    await _runs_out(conn, notice, VID, behaviour="quarantine")
    assert await _night(conn) == 1
    # The validity is made long again, and she gives the consent again.
    await conn.execute(
        "UPDATE purpose SET consent_validity_period = interval '1 year' WHERE purpose_id = %s",
        (notice["purposes"][VID]["purpose_id"],),
    )
    await _capture(conn, seeded, notice, (IMG, VID))
    assert await _read(conn) == 1
    newest = (await _messages(conn, first))[-1]
    assert (newest["change"], newest["action"]) == ("granted_again", "lift_restriction")
    assert newest["purposes_granted"] == [IMG, VID]
    # It runs out once more, on the new consent: told again.
    await _runs_out(conn, notice, VID, behaviour="quarantine")
    assert await _night(conn) == 1
    assert (await _messages(conn, first))[-1]["change"] == "expired"


async def test_a_withdrawal_never_gives_back_what_datavault_was_told_is_gone(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """DataVault was told VID lapsed. The DPO then makes VID's validity long
    again - which grants nothing - and she withdraws IMG. The withdrawal copies
    VID's grant forward, no longer run out by any clock; DataVault is still not
    to take it as granted: only she can give it again."""
    await _fresh(conn)
    await _on(conn, seeded)
    await _switched_on_a_month_ago(conn)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    await _read(conn)
    await _runs_out(conn, notice, VID, behaviour="quarantine")
    assert await _night(conn) == 1
    await conn.execute(
        "UPDATE purpose SET consent_validity_period = interval '1 year' WHERE purpose_id = %s",
        (notice["purposes"][VID]["purpose_id"],),
    )
    await _withdraw(conn, seeded, notice, IMG)
    assert await _read(conn) == 1
    newest = (await _messages(conn, first))[-1]
    assert (newest["change"], newest["action"]) == ("withdrawn", "restrict")
    assert (newest["purposes_granted"], newest["purposes_removed"]) == ([], [IMG])


async def test_a_withdrawal_is_read_as_of_its_own_moment(conn: Any, seeded: dict[str, Any]) -> None:
    """Whether a purpose had run out when she withdrew is measured at the
    withdrawal, not when the worker reads it: a worker that was down, or
    consent changes switched off for a while, read it the same."""
    await _fresh(conn)
    await _on(conn, seeded)
    notice = await _notice(conn, seeded)
    first = await _capture(conn, seeded, notice, (IMG, VID))
    await conn.execute(
        """UPDATE purpose SET consent_validity_period = interval '1 day',
                              lapse_behaviour = 'quarantine'
            WHERE purpose_id = %s""",
        (notice["purposes"][VID]["purpose_id"],),
    )
    given = first["affirmative_action_at"]
    assert await repo.run_out_on(conn, int(first["consent_id"]), at=given) == []
    later = given + timedelta(days=2)
    assert await repo.run_out_on(conn, int(first["consent_id"]), at=later) == [VID]


async def test_delivery_stops_at_the_first_try_datavault_does_not_answer(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """The rest would only wait for the same, on a worker that sends sign-in
    codes too: what was not tried is due at the next run."""
    await _fresh(conn)
    await _on(conn, seeded)
    notice = await _notice(conn, seeded)
    one = await _capture(conn, seeded, notice, (IMG, VID))
    other_notice = await _notice(conn, seeded, ("DVT-B-IMG", "DVT-B-VID"))
    two = await _capture(conn, seeded, other_notice, ("DVT-B-IMG", "DVT-B-VID"))
    await _read(conn)
    await _withdraw(conn, seeded, notice, VID)
    await _withdraw(conn, seeded, other_notice, "DVT-B-VID")
    assert await _read(conn) == 2

    tries: list[str] = []

    def gone(request: httpx.Request) -> httpx.Response:
        tries.append(json.loads(request.content)["message_id"])
        raise httpx.ConnectError("refused")

    async def record(row: dict[str, Any], answer: Any) -> None:
        if isinstance(answer, str):
            await changes.undelivered(conn, row, failure=answer)
        else:
            await changes.delivered(conn, row, answer)

    link = await connection.for_consent_changes(conn)
    assert link is not None
    mine = [
        r
        for r in await changes.due(conn)
        if r["consent_id"]
        in {m["consent_id"] for root in (one, two) for m in await _messages(conn, root)}
    ]
    assert len(mine) == 2
    outcome = await changes.deliver(link, mine, record=record, transport=httpx.MockTransport(gone))
    assert outcome == {"delivered": 0, "failed": 1, "broken": 0, "paused": True}
    assert len(tries) == 1, "the second was not tried"
    [first_m] = await _messages(conn, one)
    [second_m] = await _messages(conn, two)
    assert {first_m["attempts"], second_m["attempts"]} == {0, 1}

    # A refusal is not DataVault being away: the run goes on to the next.
    def no(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_request"})

    outcome = await changes.deliver(link, mine, record=record, transport=httpx.MockTransport(no))
    assert outcome == {"delivered": 0, "failed": 2, "broken": 0, "paused": False}

    # And a run that has used its time leaves the rest for the next.
    outcome = await changes.deliver(
        link, mine, record=record, transport=_vault([]), budget=timedelta(seconds=-1)
    )
    assert outcome["delivered"] == 0 and outcome["failed"] == 0


async def test_the_nightly_run_reads_lapses_a_page_at_a_time(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await _fresh(conn)
    await _on(conn, seeded)
    await _switched_on_a_month_ago(conn)
    notice = await _notice(conn, seeded)
    await _capture(conn, seeded, notice, (IMG, VID))
    other_notice = await _notice(conn, seeded, ("DVT-B-IMG", "DVT-B-VID"))
    await _capture(conn, seeded, other_notice, ("DVT-B-IMG", "DVT-B-VID"))
    await _read(conn)
    await _runs_out(conn, notice, VID, behaviour="quarantine")
    await _runs_out(conn, other_notice, "DVT-B-VID", behaviour="quarantine")
    link = await connection.for_consent_changes(conn)
    assert link is not None
    everything = await changes.lapsed(conn, link)
    mine = [
        r for r in everything if r["notice_id"] in (notice["notice_id"], other_notice["notice_id"])
    ]
    assert len(mine) == 2
    first, second = sorted(mine, key=lambda r: r["consent_id"])
    after_first = await changes.lapsed(conn, link, after_id=int(first["consent_id"]))
    assert int(second["consent_id"]) in {int(r["consent_id"]) for r in after_first}
    assert int(first["consent_id"]) not in {int(r["consent_id"]) for r in after_first}
