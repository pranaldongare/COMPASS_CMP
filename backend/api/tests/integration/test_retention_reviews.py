"""Retention reviews: acting when a consent ends and when its data must go
(0076, ADR 0047).

The night finds the cohorts: a consent whose validity is running out
(`validity`), and data whose retention has run out once the consent ended
(`retention`; the period runs from the consent's end). One review per project,
purpose and month, with the people counted - not a ticket each. Once due, the
ones responsible are asked: the project's DCO Admin (or HR PoC, or R&D User)
and every processor holding the data, in the console or by a link. Their
answers are accepted or sent back by the office's officer, and the review is
closed only when every one is settled. A legal hold keeps a person out; a
consent given again takes them out.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from cmp.auth.authentication import otp
from cmp.core.errors import Conflict, NotFound, Unauthenticated, ValidationFailed
from cmp.core.security import new_token, seal_token, token_fingerprint, unseal_token
from cmp.db.repositories import registry as registry_repo
from cmp.db.repositories import retention as repo
from cmp.domain.consent import service as consent_service
from cmp.domain.retention import actions, links, service
from cmp.infrastructure.dkms import unseal_value

pytestmark = pytest.mark.integration


# ------------------------------------------------------------------ the world
async def _purpose(conn: Any, *, validity: str | None, retention: str) -> None:
    await conn.execute(
        """UPDATE purpose SET consent_validity_period = %s::interval,
                              retention_period = %s::interval
            WHERE purpose_code = 'P-TEST'""",
        (validity, retention),
    )


async def _consent(conn: Any, seeded: dict[str, Any]) -> dict[str, Any]:
    raw = new_token()
    await conn.execute(
        """INSERT INTO consent_link (notice_id, site_id, token, token_sealed, expires_at,
                                     created_by)
           VALUES (%s, %s, %s, %s, now() + interval '30 days', %s)""",
        (
            seeded["notice"]["notice_id"],
            seeded["site"]["site_id"],
            token_fingerprint(raw)[:64],
            seal_token(raw),
            seeded["users"]["dpo"]["id"],
        ),
    )
    await consent_service.serve_notice(
        conn, token=raw, language_code="english", user_id=seeded["subject"]["id"]
    )
    await consent_service.capture(
        conn,
        token=raw,
        user_id=seeded["subject"]["id"],
        language_code="english",
        grants={str(seeded["purpose"]["purpose_uuid"]): True},
        action_type="checkbox_click",
        ip_address="203.0.113.7",
    )
    row = await (
        await conn.execute(
            """SELECT consent_id, consent_uuid::text AS consent_uuid FROM consent_artefact
                WHERE auth_user_id = %s ORDER BY consent_id DESC LIMIT 1""",
            (seeded["subject"]["id"],),
        )
    ).fetchone()
    return dict(row)


async def _withdraw(conn: Any, seeded: dict[str, Any], consent: dict[str, Any]) -> None:
    await consent_service.withdraw(
        conn,
        consent_uuid=consent["consent_uuid"],
        user_id=seeded["subject"]["id"],
        purpose_uuids=None,
        withdraw_all=True,
        ip_address="203.0.113.7",
    )


async def _asset(conn: Any, seeded: dict[str, Any], consent_id: int) -> None:
    """Footage of the person, captured by the external processor's rig."""
    ref = new_token()[:8]
    processor_id = seeded["processors"]["external"]["processor_id"]
    source_id = (
        await (
            await conn.execute(
                """INSERT INTO data_source (source_code, name, source_role, exchange_mode,
                                            processor_id)
                   VALUES (%s, 'Rig', 'collection', 'file_import', %s) RETURNING source_id""",
                (f"SRC-{ref}", processor_id),
            )
        ).fetchone()
    )["source_id"]
    batch_id = (
        await (
            await conn.execute(
                """INSERT INTO import_batch (source_id, project_id, file_name, file_hash,
                                             declared_rows, imported_by)
                   VALUES (%s, %s, 'm.csv', %s, 1, %s) RETURNING batch_id""",
                (
                    source_id,
                    seeded["project"]["project_id"],
                    f"hash-{ref}",
                    seeded["users"]["dco"]["id"],
                ),
            )
        ).fetchone()
    )["batch_id"]
    collection_id = (
        await (
            await conn.execute(
                """INSERT INTO collection (source_id, source_collection_ref, project_id, site_id,
                                           batch_id, collected_on, declared_asset_count)
                   VALUES (%s, %s, %s, %s, %s, current_date, 1) RETURNING collection_id""",
                (
                    source_id,
                    f"COL-{ref}",
                    seeded["project"]["project_id"],
                    seeded["site"]["site_id"],
                    batch_id,
                ),
            )
        ).fetchone()
    )["collection_id"]
    asset_id = (
        await (
            await conn.execute(
                """INSERT INTO data_asset (source_id, source_asset_ref, collection_id, asset_type)
                   VALUES (%s, %s, %s, 'video') RETURNING asset_id""",
                (source_id, f"ASSET-{ref}", collection_id),
            )
        ).fetchone()
    )["asset_id"]
    await conn.execute(
        """INSERT INTO asset_consent (asset_id, consent_id, subject_role, disposition)
           VALUES (%s, %s, 'consented', 'active')""",
        (asset_id, consent_id),
    )


async def _ours(conn: Any, seeded: dict[str, Any], kind: str) -> dict[str, Any]:
    rows = [
        r
        for r in await service.register(conn, kind=kind, status=None)
        if str(r["project_uuid"]) == str(seeded["project"]["project_uuid"])
    ]
    assert len(rows) == 1, rows
    return rows[0]


def _uid(seeded: dict[str, Any], role: str) -> int:
    return int(seeded["users"][role]["id"])


# ------------------------------------------------------------------ the sweep
async def test_a_validity_running_out_is_one_review_for_the_cohort_not_a_ticket(
    conn: Any, seeded: dict[str, Any], sent: list[Any]
) -> None:
    await _purpose(conn, validity="20 days", retention="10 years")
    consent = await _consent(conn, seeded)

    await service.daily(conn)
    review = await _ours(conn, seeded, "validity")
    # Not due for 20 days, but a validity is asked about at once: there is
    # time to invite the people again before it runs out.
    assert review["people"] == 1 and review["actions"] == 1
    assert review["reference"].startswith("VAL-")

    # The night again changes nothing: the same person is not added twice.
    await service.daily(conn)
    again = await _ours(conn, seeded, "validity")
    assert again["people"] == 1 and again["review_uuid"] == review["review_uuid"]

    detail = await service.detail(conn, str(review["review_uuid"]))
    assert [str(p["consent_uuid"]) for p in detail["people_list"]] == [consent["consent_uuid"]]
    assert detail["people_list"][0]["ended_by"] == "validity"


async def test_a_reminder_goes_to_the_owner_at_the_nearest_day_crossed(
    conn: Any, seeded: dict[str, Any], sent: list[Any]
) -> None:
    await _purpose(conn, validity="5 days", retention="10 years")
    await _consent(conn, seeded)
    await service.daily(conn)
    reminders = [s for s in sent if s[0] == "send_retention_review_reminder"]
    assert reminders, "7 days or fewer before: the 7-day reminder"
    sent.clear()
    await service.daily(conn)
    assert not [s for s in sent if s[0] == "send_retention_review_reminder"], "once per day"


async def test_once_due_the_dco_admin_is_asked_whether_to_invite_again(
    conn: Any, seeded: dict[str, Any], sent: list[Any]
) -> None:
    await _purpose(conn, validity="-1 day", retention="10 years")
    await _consent(conn, seeded)
    await service.daily(conn)

    review = await _ours(conn, seeded, "validity")
    assert review["status"] == "in_progress" and review["reconsent"] == "asked"
    detail = await service.detail(conn, str(review["review_uuid"]))
    (owner,) = detail["actions_list"]
    assert owner["kind"] == "owner" and owner["channel"] == "console"
    # A third party collects for the project: its office's DCO Admin answers.
    mine = await actions.mine(conn, _uid(seeded, "dco_admin"))
    assert [a["action_uuid"] for a in mine] == [owner["action_uuid"]]
    assert any(s[0] == "send_retention_action_asked" for s in sent)

    # Nobody else may answer it.
    with pytest.raises(NotFound):
        await actions.answer(
            conn,
            str(owner["action_uuid"]),
            user_id=_uid(seeded, "dco"),
            outcome=None,
            reason=None,
            keep_until=None,
            reconsent=False,
        )
    with pytest.raises(ValidationFailed):
        await actions.answer(
            conn,
            str(owner["action_uuid"]),
            user_id=_uid(seeded, "dco_admin"),
            outcome=None,
            reason=None,
            keep_until=None,
            reconsent=None,
        )

    # Yes, invite them: the project's live link goes to each person.
    answered = await actions.answer(
        conn,
        str(owner["action_uuid"]),
        user_id=_uid(seeded, "dco_admin"),
        outcome=None,
        reason=None,
        keep_until=None,
        reconsent=True,
    )
    assert answered["status"] == "answered" and answered["outcome"] == "reviewed"
    sent.clear()
    accepted = await actions.accept(
        conn,
        str(review["review_uuid"]),
        str(owner["action_uuid"]),
        actor_id=_uid(seeded, "dpo"),
    )
    assert accepted["status"] == "accepted"
    assert any(s[0] == "send_retention_reconsent_invite" for s in sent)
    review = await _ours(conn, seeded, "validity")
    assert review["reconsent"] == "sent"

    closed = await actions.close(
        conn, str(review["review_uuid"]), note="Invited.", actor_id=_uid(seeded, "dpo")
    )
    assert closed["status"] == "closed"


async def test_a_closed_project_is_not_asked_to_invite_again(
    conn: Any, seeded: dict[str, Any], sent: list[Any]
) -> None:
    await _purpose(conn, validity="-1 day", retention="10 years")
    await _consent(conn, seeded)
    await conn.execute(
        "UPDATE project SET project_status = 'closed' WHERE project_id = %s",
        (seeded["project"]["project_id"],),
    )
    await service.daily(conn)
    review = await _ours(conn, seeded, "validity")
    assert review["actions"] == 0 and review["reconsent"] is None


# ------------------------------------------------------- data that must go
async def test_after_withdrawal_and_the_retention_the_holders_are_asked(
    conn: Any, seeded: dict[str, Any], sent: list[Any]
) -> None:
    await _purpose(conn, validity=None, retention="-1 day")
    consent = await _consent(conn, seeded)
    await _asset(conn, seeded, int(consent["consent_id"]))
    await _withdraw(conn, seeded, consent)
    await registry_repo.add_respondent(
        conn,
        int(seeded["processors"]["external"]["processor_id"]),
        name="Priya at the processor",
        contact="privacy@processor.example",
        user_id=None,
    )

    await service.daily(conn)
    review = await _ours(conn, seeded, "retention")
    assert review["status"] == "in_progress" and review["reference"].startswith("RET-")
    detail = await service.detail(conn, str(review["review_uuid"]))
    by_kind = {a["kind"]: a for a in detail["actions_list"]}
    assert set(by_kind) == {"owner", "processor"}
    assert by_kind["processor"]["channel"] == "link", "no console login: by its link"
    assert any(s[0] == "send_retention_action_link" for s in sent)
    assert detail["people_list"][0]["ended_by"] == "withdrawal"

    owner = by_kind["owner"]
    base = {"user_id": _uid(seeded, "dco_admin"), "reconsent": None}
    with pytest.raises(ValidationFailed):
        await actions.answer(
            conn,
            str(owner["action_uuid"]),
            outcome="anonymised",
            reason=None,
            keep_until=None,
            **base,
        )
    with pytest.raises(ValidationFailed):
        await actions.answer(
            conn,
            str(owner["action_uuid"]),
            outcome="kept",
            reason="Audit",
            keep_until=datetime.now(UTC).date(),
            **base,
        )
    await actions.answer(
        conn,
        str(owner["action_uuid"]),
        outcome="anonymised",
        reason="Faces blurred; the frames feed the published benchmark.",
        keep_until=None,
        **base,
    )

    # Sent back: open again, with a new date, and the reason heard.
    back = await actions.send_back(
        conn,
        str(review["review_uuid"]),
        str(owner["action_uuid"]),
        reason="Say which frames.",
        actor_id=_uid(seeded, "dpo"),
    )
    assert back["status"] == "sent_back"
    assert await unseal_value("retention_action", "sent_back_reason", back["sent_back_reason"]) == (
        "Say which frames."
    ), "served sealed, opened in the browser"
    await actions.answer(
        conn,
        str(owner["action_uuid"]),
        outcome="erased",
        reason=None,
        keep_until=None,
        **base,
    )
    await actions.accept(
        conn, str(review["review_uuid"]), str(owner["action_uuid"]), actor_id=_uid(seeded, "dpo")
    )

    # Not closed while the processor has not answered.
    with pytest.raises(Conflict):
        await actions.close(conn, str(review["review_uuid"]), note=None, actor_id=1)

    # The processor, by its link: the link alone opens nothing.
    action = await repo.action_by_uuid(conn, str(by_kind["processor"]["action_uuid"]))
    assert action is not None and action["link_token_sealed"]
    raw = unseal_token(bytes(action["link_token_sealed"]))
    with pytest.raises(Unauthenticated):
        await links.holder_in(conn, raw, None)
    with pytest.raises(NotFound):
        await links.open_link(conn, new_token(32))
    assert await links.masked_address(conn, action) != "privacy@processor.example"

    issued = await otp.issue(otp.Scope.RETENTION_LINK, str(action["action_uuid"]))
    cookie = await links.verify(conn, raw, issued.code)
    held, _ = await links.holder_in(conn, raw, cookie)
    await actions.answer(
        conn,
        str(held["action_uuid"]),
        user_id=None,
        outcome="erased",
        reason=None,
        keep_until=None,
        reconsent=None,
        by_link=True,
    )
    await actions.accept(
        conn, str(review["review_uuid"]), str(held["action_uuid"]), actor_id=_uid(seeded, "dpo")
    )
    await links.end(cookie)
    assert not await links.signed_in(held, raw, cookie)

    closed = await actions.close(
        conn, str(review["review_uuid"]), note="Erased.", actor_id=_uid(seeded, "dpo")
    )
    assert closed["status"] == "closed"


async def test_a_legal_hold_keeps_a_person_out_and_its_release_puts_them_back(
    conn: Any, seeded: dict[str, Any], sent: list[Any]
) -> None:
    await _purpose(conn, validity=None, retention="5 days")
    consent = await _consent(conn, seeded)
    await _withdraw(conn, seeded, consent)
    hold = await (
        await conn.execute(
            """INSERT INTO legal_hold (subject_user_id, reason, placed_by, office_id)
               VALUES (%s, 'Litigation', %s,
                       (SELECT office_id FROM office WHERE office_code = 'rnd'))
               RETURNING hold_id""",
            (seeded["subject"]["id"], _uid(seeded, "dpo")),
        )
    ).fetchone()
    await service.daily(conn)
    review = await _ours(conn, seeded, "retention")
    assert review["held"] == 1 and review["people"] == 0

    await conn.execute(
        "UPDATE legal_hold SET released_at = now(), released_by = %s WHERE hold_id = %s",
        (_uid(seeded, "dpo"), hold["hold_id"]),
    )
    await service.daily(conn)
    review = await _ours(conn, seeded, "retention")
    assert review["held"] == 0 and review["people"] == 1


async def test_a_person_is_told_before_their_data_is_erased_unless_the_purpose_says_not(
    conn: Any, seeded: dict[str, Any], sent: list[Any]
) -> None:
    await _purpose(conn, validity=None, retention="1 day")
    consent = await _consent(conn, seeded)
    await _withdraw(conn, seeded, consent)
    await service.daily(conn)
    assert any(s[0] == "send_retention_erasure_notice" for s in sent), "within 48 hours"
    sent.clear()
    await service.daily(conn)
    assert not any(s[0] == "send_retention_erasure_notice" for s in sent), "told once"


async def test_no_notice_when_the_purpose_says_not(
    conn: Any, seeded: dict[str, Any], sent: list[Any]
) -> None:
    await _purpose(conn, validity=None, retention="1 day")
    await conn.execute(
        "UPDATE purpose SET notify_before_erasure = false WHERE purpose_code = 'P-TEST'"
    )
    consent = await _consent(conn, seeded)
    await _withdraw(conn, seeded, consent)
    await service.daily(conn)
    assert not any(s[0] == "send_retention_erasure_notice" for s in sent)


# ------------------------------------------------------------------ settings
async def test_the_settings_are_checked_and_on_the_trail(conn: Any, seeded: dict[str, Any]) -> None:
    with pytest.raises(ValidationFailed):
        await service.save_settings(
            conn,
            reminder_days=[0],
            notice_hours=48,
            action_days=30,
            escalate_after_days=14,
            actor_id=_uid(seeded, "dpo"),
        )
    saved = await service.save_settings(
        conn,
        reminder_days=[60, 14],
        notice_hours=72,
        action_days=21,
        escalate_after_days=7,
        actor_id=_uid(seeded, "dpo"),
    )
    assert saved["reminder_days"] == [60, 14] and saved["notice_hours"] == 72
    trail = await (
        await conn.execute(
            "SELECT 1 FROM audit_log WHERE event_type = 'retention.settings_changed'"
        )
    ).fetchall()
    assert trail


async def test_an_action_past_its_date_is_chased_and_then_escalated(
    conn: Any, seeded: dict[str, Any], sent: list[Any]
) -> None:
    await _purpose(conn, validity=None, retention="-1 day")
    consent = await _consent(conn, seeded)
    await _withdraw(conn, seeded, consent)
    await service.daily(conn)
    review = await _ours(conn, seeded, "retention")
    await conn.execute(
        "UPDATE retention_action SET due_at = %s WHERE review_id = %s",
        (datetime.now(UTC) - timedelta(days=20), review_id := (await _review_id(conn, review))),
    )
    sent.clear()
    await service.daily(conn)
    names = {s[0] for s in sent}
    assert "send_retention_action_overdue" in names
    assert "send_retention_action_escalated" in names, "14 days past: the officers hear"
    assert review_id


async def _review_id(conn: Any, review: dict[str, Any]) -> int:
    row = await repo.review_by_uuid(conn, str(review["review_uuid"]))
    assert row is not None
    return int(row["review_id"])


async def test_the_figures_count_a_review_closed_on_time(
    conn: Any, seeded: dict[str, Any], sent: list[Any]
) -> None:
    from cmp.db.repositories import analytics as figures

    await _purpose(conn, validity="-1 day", retention="10 years")
    await _consent(conn, seeded)
    await service.daily(conn)
    review = await _ours(conn, seeded, "validity")
    (owner,) = (await service.detail(conn, str(review["review_uuid"])))["actions_list"]
    await actions.mark_not_needed(
        conn, str(review["review_uuid"]), str(owner["action_uuid"]), actor_id=_uid(seeded, "dpo")
    )
    await actions.close(conn, str(review["review_uuid"]), note=None, actor_id=_uid(seeded, "dpo"))

    window = {
        "start": datetime.now(UTC) - timedelta(days=1),
        "end": datetime.now(UTC) + timedelta(days=1),
        "office": None,
        "grain": None,
        "median": False,
    }
    for key in ("retention.reviews_opened", "retention.reviews_closed", "retention.closed_on_time"):
        rows = await figures.series(conn, key, dim="kind", **window)
        by_kind = {r["dim"]: r["value"] for r in rows}
        assert by_kind.get("validity", 0) >= 1, (key, rows)


async def test_a_closed_review_has_a_certificate_and_its_download_is_on_the_trail(
    conn: Any, seeded: dict[str, Any], sent: list[Any]
) -> None:
    from cmp.domain.retention import certificate

    await _purpose(conn, validity=None, retention="-1 day")
    consent = await _consent(conn, seeded)
    await _withdraw(conn, seeded, consent)
    await service.daily(conn)
    review = await _ours(conn, seeded, "retention")
    with pytest.raises(Conflict):
        await certificate.download(conn, str(review["review_uuid"]), "pdf", actor_id=1)
    (owner,) = (await service.detail(conn, str(review["review_uuid"])))["actions_list"]
    await actions.answer(
        conn,
        str(owner["action_uuid"]),
        user_id=_uid(seeded, "dco_admin"),
        outcome="anonymised",
        reason="Blurred for the benchmark.",
        keep_until=None,
        reconsent=None,
    )
    dpo = _uid(seeded, "dpo")
    await actions.accept(conn, str(review["review_uuid"]), str(owner["action_uuid"]), actor_id=dpo)
    await actions.close(conn, str(review["review_uuid"]), note="Done.", actor_id=dpo)

    pdf, name, mime = await certificate.download(
        conn, str(review["review_uuid"]), "pdf", actor_id=dpo
    )
    assert pdf.startswith(b"%PDF") and mime == "application/pdf"
    assert name == f"{review['reference']}-certificate.pdf"
    csv_bytes, _, _ = await certificate.download(
        conn, str(review["review_uuid"]), "csv", actor_id=dpo
    )
    text = csv_bytes.decode("utf-8-sig")
    assert "Blurred for the benchmark." in text, text
    assert "\nC-" in text, "the consents, by number"
    assert "Test subject" not in text, "no person is named"
    trail = await (
        await conn.execute(
            "SELECT count(*) AS n FROM audit_log WHERE event_type = %s",
            ("retention.certificate_downloaded",),
        )
    ).fetchone()
    assert trail["n"] >= 2


async def test_proof_is_attached_before_answering_and_kept_on_the_certificate(
    conn: Any, seeded: dict[str, Any], sent: list[Any]
) -> None:
    from cmp.core.security import file_hash
    from cmp.domain.retention import certificate
    from cmp.infrastructure.storage.service import storage

    await _purpose(conn, validity=None, retention="-1 day")
    consent = await _consent(conn, seeded)
    await _withdraw(conn, seeded, consent)
    await service.daily(conn)
    review = await _ours(conn, seeded, "retention")
    (owner,) = (await service.detail(conn, str(review["review_uuid"])))["actions_list"]
    uuid = str(owner["action_uuid"])
    admin, dpo = _uid(seeded, "dco_admin"), _uid(seeded, "dpo")

    payload = b"deleted 42 frames from rig-07\n"
    ref = storage().save(payload, subdir="retention", suggested_name="deletion-log.txt")
    with pytest.raises(NotFound):
        await actions.attach(
            conn, uuid, user_id=_uid(seeded, "dco"), ref=ref, digest="x", name="log.txt"
        )
    shown = await actions.attach(
        conn, uuid, user_id=admin, ref=ref, digest=file_hash(payload), name="deletion-log.txt"
    )
    assert shown["evidence_hash"] == file_hash(payload)
    assert str(shown["evidence_name"]).startswith("SE::"), "the name is served sealed"

    await actions.answer(
        conn, uuid, user_id=admin, outcome="erased", reason=None, keep_until=None, reconsent=None
    )
    with pytest.raises(Conflict):
        await actions.attach(
            conn, uuid, user_id=admin, ref=ref, digest=file_hash(payload), name="late.txt"
        )

    got, name, digest = await actions.evidence(
        conn, uuid, actor_id=dpo, review_uuid=str(review["review_uuid"])
    )
    assert got == payload and name == "deletion-log.txt" and digest == file_hash(payload)
    with pytest.raises(NotFound):
        await actions.evidence(conn, uuid, actor_id=dpo, owner_id=_uid(seeded, "dco"))

    await actions.accept(conn, str(review["review_uuid"]), uuid, actor_id=dpo)
    await actions.close(conn, str(review["review_uuid"]), note=None, actor_id=dpo)
    csv_bytes, _, _ = await certificate.download(
        conn, str(review["review_uuid"]), "csv", actor_id=dpo
    )
    text = csv_bytes.decode("utf-8-sig")
    assert "deletion-log.txt" in text and file_hash(payload) in text
    trail = await (
        await conn.execute(
            "SELECT event_type FROM audit_log WHERE event_type LIKE 'retention.evidence_%%'"
            " AND entity_id = %s",
            (int((await repo.review_by_uuid(conn, str(review["review_uuid"])))["review_id"]),),
        )
    ).fetchall()
    assert {r["event_type"] for r in trail} == {
        "retention.evidence_added",
        "retention.evidence_downloaded",
    }
