"""The five rights flows, walked through the service against a real database.

Each test follows one diagram from the Privacy Engineering deck and asserts the
decisions on it: the clock starts on receipt, identity gates everything, an
asset holding other people is redacted rather than erased, a holder that misses
its date is escalated once and the response goes out partial and on time, a
complaint about the DPO is decided by somebody else, and a nomination nobody
accepted is not usable.

Through the service rather than raw SQL, because what these flows get wrong is
never the SQL - it is a decision taken in the wrong order.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from cmp.auth.authentication import otp
from cmp.core.errors import BadRequest, Conflict, Forbidden, NotFound, ValidationFailed
from cmp.core.permissions import Role
from cmp.core.security import new_token, token_fingerprint
from cmp.db.redis import K_RATE
from cmp.db.redis import key as rkey
from cmp.db.repositories import audit as audit_repo
from cmp.db.repositories import rights as repo
from cmp.domain.consent import service as consent_service
from cmp.domain.rights import service

pytestmark = pytest.mark.integration


# ------------------------------------------------------------------ fixtures
async def _consent(conn: Any, seeded: dict[str, Any]) -> dict[str, Any]:
    """A real consent artefact for the seeded subject, through the service."""
    raw = new_token()
    await conn.execute(
        """INSERT INTO consent_link (notice_id, site_id, token, expires_at, created_by)
           VALUES (%s, %s, %s, now() + interval '1 day', %s)""",
        (
            seeded["notice"]["notice_id"],
            seeded["site"]["site_id"],
            token_fingerprint(raw)[:64],
            seeded["users"]["dco"]["id"],
        ),
    )
    return await consent_service.capture(
        conn,
        token=raw,
        user_id=seeded["subject"]["id"],
        language_code="english",
        served_at=datetime.now(UTC) - timedelta(minutes=1),
        grants={str(seeded["purpose"]["purpose_uuid"]): True},
        action_type="checkbox_click",
        ip_address="127.0.0.1",
    )


async def _export_with_her(conn: Any, seeded: dict[str, Any], consent_id: int) -> None:
    """An export that carried her record to the external processor's site."""
    await conn.execute(
        "UPDATE project_site SET processor_id = %s WHERE site_id = %s",
        (seeded["processors"]["external"]["processor_id"], seeded["site"]["site_id"]),
    )
    result = await conn.execute(
        """INSERT INTO export_log (project_id, site_id, export_type, exported_by, row_count,
                                   file_hash)
           VALUES (%s, %s, 'project_export', %s, 1, 'deadbeef') RETURNING export_id""",
        (seeded["project"]["project_id"], seeded["site"]["site_id"], seeded["users"]["dpo"]["id"]),
    )
    export_id = (await result.fetchone())["export_id"]
    await conn.execute(
        "INSERT INTO export_line (export_id, auth_user_id, consent_id) VALUES (%s, %s, %s)",
        (export_id, seeded["subject"]["id"], consent_id),
    )


async def _asset_with_her(
    conn: Any, seeded: dict[str, Any], consent_id: int, *, bystanders: int, ref: str
) -> int:
    """A collected asset she appears in, captured by the external processor's rig.

    Returns her asset_consent row id. `bystanders` adds incidental rows - people
    in frame who never consented - which is the redaction case.
    """
    processor_id = seeded["processors"]["external"]["processor_id"]
    source = await conn.execute(
        """INSERT INTO data_source (source_code, name, source_role, exchange_mode, processor_id)
           VALUES (%s, 'Test rig', 'collection', 'file_import', %s)
           ON CONFLICT (source_code) DO UPDATE SET name = EXCLUDED.name
           RETURNING source_id""",
        (f"SRC-{ref}", processor_id),
    )
    source_id = (await source.fetchone())["source_id"]
    batch = await conn.execute(
        """INSERT INTO import_batch (source_id, project_id, file_name, file_hash, declared_rows,
                                     imported_by)
           VALUES (%s, %s, 'm.csv', %s, 1, %s) RETURNING batch_id""",
        (source_id, seeded["project"]["project_id"], f"hash-{ref}", seeded["users"]["dco"]["id"]),
    )
    batch_id = (await batch.fetchone())["batch_id"]
    collection = await conn.execute(
        """INSERT INTO collection (source_id, source_collection_ref, project_id, site_id, batch_id,
                                   collected_on, declared_asset_count)
           VALUES (%s, %s, %s, %s, %s, current_date, 1) RETURNING collection_id""",
        (
            source_id,
            f"COL-{ref}",
            seeded["project"]["project_id"],
            seeded["site"]["site_id"],
            batch_id,
        ),
    )
    collection_id = (await collection.fetchone())["collection_id"]
    asset = await conn.execute(
        """INSERT INTO data_asset (source_id, source_asset_ref, collection_id, asset_type)
           VALUES (%s, %s, %s, 'video') RETURNING asset_id""",
        (source_id, f"ASSET-{ref}", collection_id),
    )
    asset_id = (await asset.fetchone())["asset_id"]
    hers = await conn.execute(
        """INSERT INTO asset_consent (asset_id, consent_id, subject_role, disposition)
           VALUES (%s, %s, 'consented', 'active') RETURNING asset_consent_id""",
        (asset_id, consent_id),
    )
    for _ in range(bystanders):
        await conn.execute(
            """INSERT INTO asset_consent (asset_id, consent_id, subject_role, disposition)
               VALUES (%s, NULL, 'incidental', 'active')""",
            (asset_id,),
        )
    return int((await hers.fetchone())["asset_consent_id"])


async def _portal_request(
    conn: Any, seeded: dict[str, Any], kind: str, **kw: Any
) -> dict[str, Any]:
    return await service.create(
        conn,
        request_type=kind,
        channel="portal",
        request_text=f"A {kind} request from the seeded subject",
        submitted_contact="subject@test.local",
        submitted_name="Test Subject",
        subject_user_id=seeded["subject"]["id"],
        actor_id=seeded["subject"]["id"],
        verification_method="session",
        **kw,
    )


DPO = Role.DPO


async def _started(conn: Any, seeded: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    dpo = seeded["users"]["dpo"]["id"]
    row = await service.classify(
        conn, row, request_type=row["request_type"], note=None, role=DPO, actor_id=dpo
    )
    return await service.transition(
        conn, row, to="in_progress", reason=None, role=DPO, actor_id=dpo
    )


async def _unthrottle(redis_conn: Any, contact: str) -> None:
    """The public form is rate limited per contact in Redis, which outlives the
    test transaction. Clear the bucket so a re-run is not a sixth attempt."""
    await redis_conn.delete(
        rkey(K_RATE, "rights_public_contact", contact.lower()),
        rkey(K_RATE, "rights_public_ip", "127.0.0.1"),
        rkey(K_RATE, "rights_public_ip", "127.0.0.2"),
    )


# ------------------------------------------------------------------- access
class TestAccessRequest:
    async def test_the_clock_starts_on_receipt_and_the_session_verifies(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        row = await _portal_request(conn, seeded, "access")
        assert row["reference"].startswith("RR-")
        assert row["verification_status"] == "verified"
        assert row["verification_method"] == "session"
        assert row["acknowledged_at"] is not None, "a verified request is acknowledged at once"
        assert row["due_at"] > row["received_at"]
        assert service.clock_of(row)["next_checkpoint"] == "acknowledge"

    async def test_it_cannot_start_until_classified(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        row = await _portal_request(conn, seeded, "access")
        with pytest.raises(Conflict) as raised:
            await service.transition(
                conn,
                row,
                to="in_progress",
                reason=None,
                role=DPO,
                actor_id=seeded["users"]["dpo"]["id"],
            )
        assert raised.value.code == "transition_blocked"

    async def test_the_full_path_to_a_complete_response(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        """Steps 1 to 10: received, verified, holders derived from the records,
        tickets issued and returned, collated, released as a file she can fetch."""
        dpo = seeded["users"]["dpo"]["id"]
        consent = await _consent(conn, seeded)
        await _export_with_her(conn, seeded, consent["consent_id"])
        await _asset_with_her(conn, seeded, consent["consent_id"], bystanders=0, ref="A1")

        row = await _started(conn, seeded, await _portal_request(conn, seeded, "access"))
        assert row["status"] == "in_progress"

        holders = await service.derive_holders(conn, row, role=DPO, actor_id=dpo)
        assert [h["label"] for h in holders] == ["Test Processor Ltd"]
        assert holders[0]["evidence"]["exports"] and holders[0]["evidence"]["assets"]
        assert holders[0]["confirmed_at"] is None, "derived is not confirmed - the DPO does that"

        holder = await service.confirm_holder(
            conn,
            row,
            holder_uuid=str(holders[0]["holder_uuid"]),
            responder_name="Lab manager",
            responder_contact="lab@example.org",
            role=DPO,
            actor_id=dpo,
        )
        assert holder["confirmed_at"] is not None

        issued = await service.issue_tickets(
            conn, row, instruction=None, due_at=None, role=DPO, actor_id=dpo
        )
        assert issued[0]["ticket_status"] == "issued"
        assert issued[0]["instruction"] and row["reference"] in issued[0]["instruction"]
        clock = service.clock_of(row)
        assert issued[0]["due_at"] == clock["halfway_at"], "tickets fall due at halfway by default"

        row = await service.reload(conn, row)
        assert row["status"] == "awaiting_holders"

        with pytest.raises(Conflict):
            # Nothing has come back: collation is blocked until it does or is escalated.
            await service.transition(conn, row, to="collating", reason=None, role=DPO, actor_id=dpo)

        await service.return_ticket(
            conn,
            row,
            holder_uuid=str(holder["holder_uuid"]),
            summary="Two video files, one form; nothing shared onward.",
            evidence_ref=None,
            evidence_hash=None,
            role=DPO,
            actor_id=dpo,
        )
        row = await service.transition(
            conn,
            await service.reload(conn, row),
            to="collating",
            reason=None,
            role=DPO,
            actor_id=dpo,
        )
        row = await service.respond(
            conn,
            row,
            outcome="complete",
            response_text="Everything we hold is in the file.",
            role=DPO,
            actor_id=dpo,
        )
        assert row["status"] == "closed" and row["outcome"] == "complete"
        assert row["response_file_hash"] and row["download_expires_at"] is not None

        payload, filename, _recorded = await service.download(
            conn, row, actor_id=seeded["subject"]["id"], as_subject=True
        )
        assert filename == f"{row['reference']}.json"
        assert b'"holders"' in payload and b"Test Processor Ltd" in payload
        assert b"Lab manager" not in payload, "the responder's name is ours, not hers"

        events = [e["event_type"] for e in await audit_repo.for_reference(conn, row["reference"])]
        assert events[0] == "rights.request_received"
        assert "rights.ticket_returned" in events and events[-1] == "rights.response_downloaded"

    async def test_a_holder_that_misses_its_date_is_escalated_once_then_named(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        """Respond partial and on time. The clock does not pause for a busy lab."""
        dpo = seeded["users"]["dpo"]["id"]
        consent = await _consent(conn, seeded)
        await _export_with_her(conn, seeded, consent["consent_id"])
        row = await _started(conn, seeded, await _portal_request(conn, seeded, "access"))
        [holder] = await service.derive_holders(conn, row, role=DPO, actor_id=dpo)
        await service.confirm_holder(
            conn,
            row,
            holder_uuid=str(holder["holder_uuid"]),
            responder_name=None,
            responder_contact=None,
            role=DPO,
            actor_id=dpo,
        )
        await service.issue_tickets(
            conn, row, instruction=None, due_at=None, role=DPO, actor_id=dpo
        )
        row = await service.reload(conn, row)

        escalated = await service.escalate_ticket(
            conn, row, holder_uuid=str(holder["holder_uuid"]), role=DPO, actor_id=dpo
        )
        assert escalated["ticket_status"] == "escalated"
        with pytest.raises(Conflict):
            await service.escalate_ticket(
                conn, row, holder_uuid=str(holder["holder_uuid"]), role=DPO, actor_id=dpo
            )

        row = await service.transition(
            conn,
            await service.reload(conn, row),
            to="collating",
            reason=None,
            role=DPO,
            actor_id=dpo,
        )
        with pytest.raises(ValidationFailed) as refused:
            await service.respond(
                conn, row, outcome="complete", response_text="All done.", role=DPO, actor_id=dpo
            )
        assert refused.value.code == "response_partial_required"

        row = await service.respond(
            conn,
            row,
            outcome="partial",
            response_text="The lab has not returned.",
            role=DPO,
            actor_id=dpo,
        )
        assert row["outcome"] == "partial"
        [holder] = await repo.holders_of(conn, int(row["request_id"]))
        assert holder["ticket_status"] == "unreturned"
        payload, _, _ = await service.download(conn, row, actor_id=dpo, as_subject=False)
        assert b'"gaps": [\n    "Test Processor Ltd"' in payload

    async def test_no_records_held_anywhere_is_a_complete_short_response(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        dpo = seeded["users"]["dpo"]["id"]
        row = await _started(conn, seeded, await _portal_request(conn, seeded, "access"))
        assert await service.derive_holders(conn, row, role=DPO, actor_id=dpo) == []
        row = await service.transition(
            conn,
            await service.reload(conn, row),
            to="collating",
            reason=None,
            role=DPO,
            actor_id=dpo,
        )
        # She has a consent on the platform. "No records held anywhere" is an
        # answer about the holders; the platform's own record still goes back
        # to her, attached and spelled out - that record is the answer.
        await _consent(conn, seeded)
        row = await service.respond(
            conn,
            row,
            outcome="no_records",
            response_text="We hold nothing beyond your consent record.",
            role=DPO,
            actor_id=dpo,
        )
        assert row["outcome"] == "no_records"
        assert row["response_file_hash"] and row["download_expires_at"] is not None
        payload, _, _ = await service.download(conn, row, actor_id=dpo, as_subject=False)
        import json

        from cmp.domain.rights import package

        record = json.loads(payload)
        assert record["outcome"] == "no_records"
        assert record["summary"]["consents"] == 1 and record["summary"]["holders"] == 0
        assert record["consents"][0]["purposes"], "the purposes she answered are listed"
        digest = package.digest_text(record)
        assert "YOUR CONSENTS ON RECORD" in digest and "Consent on" in digest
        assert "No party beyond the platform itself was asked" in digest


# ------------------------------------------------------------------- erasure
class TestErasureRequest:
    async def test_she_meant_withdrawal(self, conn: Any, seeded: dict[str, Any]) -> None:
        dpo = seeded["users"]["dpo"]["id"]
        row = await _portal_request(conn, seeded, "erasure")
        row = await service.reclassify_as_withdrawal(
            conn, row, note="Confirmed on the phone", role=DPO, actor_id=dpo
        )
        assert row["status"] == "closed" and row["outcome"] == "reclassified_withdrawal"
        assert "does not delete" in str(row["response_text"])

    async def test_an_asset_holding_others_is_redacted_never_erased(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        """Decision D-09, end to end. One video, three people; she asks for erasure."""
        dpo = seeded["users"]["dpo"]["id"]
        consent = await _consent(conn, seeded)
        shared = await _asset_with_her(conn, seeded, consent["consent_id"], bystanders=2, ref="E1")
        alone = await _asset_with_her(conn, seeded, consent["consent_id"], bystanders=0, ref="E2")

        row = await _portal_request(conn, seeded, "erasure")
        row = await service.classify(
            conn, row, request_type="erasure", note=None, role=DPO, actor_id=dpo
        )
        with pytest.raises(Conflict):
            await service.transition(
                conn, row, to="in_progress", reason=None, role=DPO, actor_id=dpo
            )
        row = await service.confirm_intent(conn, row, role=DPO, actor_id=dpo)
        row = await service.transition(
            conn, row, to="in_progress", reason=None, role=DPO, actor_id=dpo
        )

        [holder] = await service.derive_holders(conn, row, role=DPO, actor_id=dpo)
        items = await service.derive_scope(conn, row, role=DPO, actor_id=dpo)
        by_ac = {int(i["asset_consent_id"]): i for i in items}
        assert by_ac[shared]["other_subjects"] == 2 and by_ac[alone]["other_subjects"] == 0
        assert by_ac[shared]["holder_label"] == "Test Processor Ltd", (
            "linked to the holder by processor"
        )

        with pytest.raises(ValidationFailed) as refused:
            await service.decide_item(
                conn,
                row,
                item_uuid=str(by_ac[shared]["item_uuid"]),
                decision="erase",
                basis="She asked",
                retain_until=None,
                holder_uuid=None,
                role=DPO,
                actor_id=dpo,
            )
        assert refused.value.code == "asset_holds_others"

        await service.decide_item(
            conn,
            row,
            item_uuid=str(by_ac[shared]["item_uuid"]),
            decision="redact",
            basis="Two other people consented to this recording",
            retain_until=None,
            holder_uuid=None,
            role=DPO,
            actor_id=dpo,
        )
        await service.decide_item(
            conn,
            row,
            item_uuid=str(by_ac[alone]["item_uuid"]),
            decision="erase",
            basis="Only she appears",
            retain_until=None,
            holder_uuid=None,
            role=DPO,
            actor_id=dpo,
        )

        # The platform records erasure; the lab performs it. Nothing applies
        # until the holder has confirmed what was removed.
        with pytest.raises(Conflict) as early:
            await service.apply_item(
                conn, row, item_uuid=str(by_ac[shared]["item_uuid"]), role=DPO, actor_id=dpo
            )
        assert early.value.code == "holder_not_confirmed"

        await service.confirm_holder(
            conn,
            row,
            holder_uuid=str(holder["holder_uuid"]),
            responder_name=None,
            responder_contact=None,
            role=DPO,
            actor_id=dpo,
        )
        await service.issue_tickets(
            conn, row, instruction=None, due_at=None, role=DPO, actor_id=dpo
        )
        row = await service.reload(conn, row)
        await service.return_ticket(
            conn,
            row,
            holder_uuid=str(holder["holder_uuid"]),
            summary="Face and voice removed from E1; E2 deleted in full.",
            evidence_ref=None,
            evidence_hash="abc",
            role=DPO,
            actor_id=dpo,
        )

        redacted = await service.apply_item(
            conn, row, item_uuid=str(by_ac[shared]["item_uuid"]), role=DPO, actor_id=dpo
        )
        erased = await service.apply_item(
            conn, row, item_uuid=str(by_ac[alone]["item_uuid"]), role=DPO, actor_id=dpo
        )
        assert redacted["disposition"] == "redacted" and erased["disposition"] == "erased"

        others = await conn.execute(
            """SELECT disposition FROM asset_consent
               WHERE asset_id = (SELECT asset_id FROM asset_consent WHERE asset_consent_id = %s)
                 AND asset_consent_id <> %s""",
            (shared, shared),
        )
        assert {r["disposition"] for r in await others.fetchall()} == {"active"}, (
            "the other two are untouched"
        )

        artefacts = await conn.execute(
            "SELECT count(*) AS n FROM consent_artefact WHERE auth_user_id = %s",
            (seeded["subject"]["id"],),
        )
        assert (await artefacts.fetchone())["n"] == 1, "consent artefacts are never erased"

    async def test_the_retention_floor_binds_even_against_her_request(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        dpo = seeded["users"]["dpo"]["id"]
        consent = await _consent(conn, seeded)
        ac = await _asset_with_her(conn, seeded, consent["consent_id"], bystanders=0, ref="F1")
        row = await _portal_request(conn, seeded, "erasure")
        row = await service.classify(
            conn, row, request_type="erasure", note=None, role=DPO, actor_id=dpo
        )
        row = await service.confirm_intent(conn, row, role=DPO, actor_id=dpo)
        row = await service.transition(
            conn, row, to="in_progress", reason=None, role=DPO, actor_id=dpo
        )
        [item] = await service.derive_scope(conn, row, role=DPO, actor_id=dpo)
        assert int(item["asset_consent_id"]) == ac

        floor = datetime.now(UTC).date() + timedelta(days=200)
        decided = await service.decide_item(
            conn,
            row,
            item_uuid=str(item["item_uuid"]),
            decision="retain",
            basis="Rule 8(3): one-year floor from collection",
            retain_until=floor,
            holder_uuid=None,
            role=DPO,
            actor_id=dpo,
        )
        assert decided["retain_until"] == floor
        with pytest.raises(Conflict) as held:
            await service.apply_item(
                conn, row, item_uuid=str(item["item_uuid"]), role=DPO, actor_id=dpo
            )
        assert held.value.code == "retention_floor"

        # The floor passes; the sweep notes it; applying now erases.
        await conn.execute(
            "UPDATE rights_request_item SET retain_until = current_date - 1 WHERE item_uuid = %s",
            (str(item["item_uuid"]),),
        )
        swept = await service.sweep(conn)
        assert swept["floors_passed"] == 1
        applied = await service.apply_item(
            conn, row, item_uuid=str(item["item_uuid"]), role=DPO, actor_id=None
        )
        assert applied["disposition"] == "erased"


# ------------------------------------------------------------------- grievance
class TestGrievance:
    async def test_a_complaint_about_the_dpo_is_decided_by_somebody_else(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        dpo = seeded["users"]["dpo"]["id"]
        admin = seeded["users"]["admin"]
        original = await _started(conn, seeded, await _portal_request(conn, seeded, "access"))
        original = await service.transition(
            conn,
            await service.reload(conn, original),
            to="collating",
            reason=None,
            role=DPO,
            actor_id=dpo,
        )
        original = await service.respond(
            conn,
            original,
            outcome="no_records",
            response_text="Nothing held.",
            role=DPO,
            actor_id=dpo,
        )

        grievance = await service.dispute(
            conn,
            original,
            subject_user_id=seeded["subject"]["id"],
            text="The DPO closed my request without looking.",
            about_dpo=True,
        )
        assert (
            grievance["request_type"] == "grievance"
            and grievance["linked_reference"] == original["reference"]
        )

        # In the administrator's scope, not only the DPO's.
        assert await repo.by_uuid(
            conn, str(grievance["request_uuid"]), role=Role.ADMIN, user_id=admin["id"]
        )
        assert (
            await repo.by_uuid(
                conn, str(original["request_uuid"]), role=Role.ADMIN, user_id=admin["id"]
            )
            is None
        )

        grievance = await service.classify(
            conn, grievance, request_type="grievance", note=None, role=DPO, actor_id=dpo
        )
        with pytest.raises(Conflict):
            await service.transition(
                conn,
                grievance,
                to="in_progress",
                reason=None,
                role=Role.ADMIN,
                actor_id=admin["id"],
            )
        grievance = await service.assign_reviewer(
            conn, grievance, reviewer_uuid=str(admin["uuid"]), role=Role.ADMIN, actor_id=admin["id"]
        )
        grievance = await service.transition(
            conn, grievance, to="in_progress", reason=None, role=Role.ADMIN, actor_id=admin["id"]
        )

        with pytest.raises(Forbidden):
            await service.decide_grievance(
                conn,
                grievance,
                upheld=True,
                remedy_text="Re-run",
                response_text="Upheld.",
                rerun=True,
                role=DPO,
                actor_id=dpo,
            )
        result = await service.decide_grievance(
            conn,
            grievance,
            upheld=True,
            remedy_text="The request is re-run at no cost.",
            response_text="The handling was incomplete.",
            rerun=True,
            role=Role.ADMIN,
            actor_id=admin["id"],
        )
        assert result["request"]["outcome"] == "upheld"
        rerun = result["rerun"]
        assert rerun is not None and rerun["request_type"] == "access"
        assert rerun["linked_reference"] == result["request"]["reference"]
        assert rerun["verification_status"] == "verified" and rerun["classified_at"] is not None

    async def test_not_upheld_is_reasoned_and_carries_the_board_route(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        dpo = seeded["users"]["dpo"]["id"]
        row = await _started(conn, seeded, await _portal_request(conn, seeded, "grievance"))
        result = await service.decide_grievance(
            conn,
            row,
            upheld=False,
            remedy_text=None,
            response_text="Handled within the period.",
            rerun=False,
            role=DPO,
            actor_id=dpo,
        )
        assert result["request"]["outcome"] == "not_upheld" and result["rerun"] is None


# ------------------------------------------------------------------ nomination
class TestNomination:
    async def test_a_nomination_naming_a_registered_person_is_listed_for_her(
        self, conn: Any, seeded: dict[str, Any], redis_conn: Any
    ) -> None:
        """The nominee's side. A nominee may be a data principal here herself,
        and her account then has to say who named her: matched on the contacts
        the principal recorded, live ones only, by either contact."""
        principal = seeded["subject"]["id"]
        nomination = await service.nominate(
            conn,
            principal_user_id=principal,
            nominee_name="Meera Nominee",
            nominee_mobile="+91 555 000 0091",  # stored as digits
            nominee_email="Meera.Nominee@Example.org",  # stored as typed, matched case-blind
            rights=["access"],
        )
        ref = str(nomination["nomination_uuid"])

        by_mobile = await repo.nominations_naming(conn, mobile="+915550000091", email=None)
        assert [str(r["nomination_uuid"]) for r in by_mobile] == [ref]
        assert by_mobile[0]["status"] == "pending"
        assert by_mobile[0]["principal_name"] == "Test Subject"  # the seeded principal

        by_email = await repo.nominations_naming(
            conn, mobile=None, email="meera.nominee@example.org"
        )
        assert [str(r["nomination_uuid"]) for r in by_email] == [ref]

        nobody = await repo.nominations_naming(
            conn, mobile="+915559999999", email="nobody@example.org"
        )
        assert nobody == []

        # Revoked is not something she can act on, so it is not listed.
        await service.revoke_nomination(conn, nomination_uuid=ref, principal_user_id=principal)
        assert await repo.nominations_naming(conn, mobile="+915550000091", email=None) == []

    async def test_accepting_makes_the_nominee_an_account_he_can_sign_in_with(
        self, conn: Any, seeded: dict[str, Any], redis_conn: Any
    ) -> None:
        """Accepting proved a contact - the same proof registration needs.

        A stranger who accepts gets a data principal's account, active, with
        the contact the code went to marked verified, so the sign-in code he
        asks for next actually arrives. A nominee who already has an account
        under a recorded contact keeps that one; nothing is created."""
        from cmp.db.redis import K_CACHE, get_redis
        from cmp.db.redis import key as rkey
        from cmp.db.repositories import users as user_repo

        principal = seeded["subject"]["id"]

        async def accept(mobile: str, email: str | None, *, proven: str) -> dict[str, Any]:
            nomination = await service.nominate(
                conn,
                principal_user_id=principal,
                nominee_name="Nominee Who Accepts",
                nominee_mobile=mobile,
                nominee_email=email,
                rights=["access"],
            )
            raw = new_token()
            await conn.execute(
                "UPDATE nomination SET accept_token_hash = %s WHERE nomination_id = %s",
                (token_fingerprint(raw), nomination["nomination_id"]),
            )
            ref = str(nomination["nomination_uuid"])
            code = (await otp.issue(otp.Scope.NOMINATION_ACCEPT, ref)).code
            # What `send_nomination_code` records: where the code went.
            await get_redis().set(rkey(K_CACHE, "nomination_medium", ref), proven, ex=600)
            accepted = await service.accept_nomination(conn, raw, code=code)
            await service.revoke_nomination(conn, nomination_uuid=ref, principal_user_id=principal)
            return dict(accepted)

        # A stranger: no account under either contact.
        assert await user_repo.by_contact(conn, "+915550000201") is None
        await accept("+915550000201", "stranger.nominee@example.org", proven="mobile")
        made = await user_repo.by_contact(conn, "+915550000201")
        assert made is not None
        assert made["role"] == "data_subject" and made["status"] == "active"
        assert made["full_name"] == "Nominee Who Accepts"
        assert made["email"] == "stranger.nominee@example.org"
        assert made["mobile_verified_at"] is not None and made["email_verified_at"] is None

        # Somebody with an account already: the same person, named again on a
        # later nomination. The account is his; nothing new is made.
        before = await conn.execute("SELECT count(*) AS n FROM auth_user")
        n_before = (await before.fetchone())["n"]
        await accept("+915550000201", None, proven="mobile")
        after = await conn.execute("SELECT count(*) AS n FROM auth_user")
        assert (await after.fetchone())["n"] == n_before

    async def test_pending_until_accepted_then_usable(
        self, conn: Any, seeded: dict[str, Any], redis_conn: Any
    ) -> None:
        principal = seeded["subject"]["id"]
        nomination = await service.nominate(
            conn,
            principal_user_id=principal,
            nominee_name="Ravi Verma",
            nominee_mobile="+915550000077",
            nominee_email="ravi@example.org",
            rights=["access", "erasure"],
        )
        assert nomination["status"] == "pending"
        with pytest.raises(Conflict):
            await service.nominate(
                conn,
                principal_user_id=principal,
                nominee_name="Someone Else",
                nominee_mobile="+915550000078",
                nominee_email="x@example.org",
                rights=["access"],
            )

        # A nomination he has not accepted cannot be acted on: no code is issued.
        start = await service.nominee_start(
            conn, nomination_uuid=str(nomination["nomination_uuid"]), contact="ravi@example.org"
        )
        assert "If that nomination" in start["message"]
        issued = await otp.issue(otp.Scope.NOMINEE_VERIFY, str(nomination["nomination_uuid"]))
        with pytest.raises(BadRequest):
            await service.nominee_submit(
                conn,
                nomination_uuid=str(nomination["nomination_uuid"]),
                code=issued.code,
                request_type="access",
                request_text="On her behalf",
                trigger_event="death",
                evidence_ref=None,
                evidence_hash=None,
            )

        token_row = await conn.execute(
            "SELECT accept_token_hash FROM nomination WHERE nomination_id = %s",
            (nomination["nomination_id"],),
        )
        assert (await token_row.fetchone())["accept_token_hash"], "only the digest is stored"

    async def test_the_nominee_acts_and_the_dpo_gates_on_the_event(
        self, conn: Any, seeded: dict[str, Any], redis_conn: Any
    ) -> None:
        principal = seeded["subject"]["id"]
        dpo = seeded["users"]["dpo"]["id"]
        nomination = await service.nominate(
            conn,
            principal_user_id=principal,
            nominee_name="Ravi Verma",
            nominee_mobile="+915550000077",
            nominee_email="ravi@example.org",
            rights=["access"],
        )
        # Accept through the token, the way the link does.
        raw = new_token()
        await conn.execute(
            "UPDATE nomination SET accept_token_hash = %s WHERE nomination_id = %s",
            (token_fingerprint(raw), nomination["nomination_id"]),
        )
        code = (
            await otp.issue(otp.Scope.NOMINATION_ACCEPT, str(nomination["nomination_uuid"]))
        ).code
        accepted = await service.accept_nomination(conn, raw, code=code)
        assert accepted["status"] == "active"
        with pytest.raises(NotFound):
            await service.accept_nomination(conn, raw, code="000000")  # single use

        issued = await otp.issue(otp.Scope.NOMINEE_VERIFY, str(nomination["nomination_uuid"]))
        with pytest.raises(ValidationFailed):
            await service.nominee_submit(
                conn,
                nomination_uuid=str(nomination["nomination_uuid"]),
                code=issued.code,
                request_type="erasure",
                request_text="Not granted",
                trigger_event="death",
                evidence_ref=None,
                evidence_hash=None,
            )
        issued = await otp.issue(otp.Scope.NOMINEE_VERIFY, str(nomination["nomination_uuid"]))
        row = await service.nominee_submit(
            conn,
            nomination_uuid=str(nomination["nomination_uuid"]),
            code=issued.code,
            request_type="access",
            request_text="Her records, please",
            trigger_event="death",
            evidence_ref=None,
            evidence_hash="ev1",
        )
        assert row["channel"] == "nominee" and row["subject_user_id"] == principal
        assert row["verification_status"] == "verified"
        assert service.contact_for(row) == "+915550000077", "the nominee is written to, not her"

        row = await service.classify(
            conn, row, request_type="access", note=None, role=DPO, actor_id=dpo
        )
        with pytest.raises(Conflict):
            await service.transition(
                conn, row, to="in_progress", reason=None, role=DPO, actor_id=dpo
            )
        row = await service.record_event_evidence(
            conn, row, evidenced=True, note="Death certificate seen", role=DPO, actor_id=dpo
        )
        row = await service.transition(
            conn, row, to="in_progress", reason=None, role=DPO, actor_id=dpo
        )
        assert row["status"] == "in_progress"

    async def test_an_unevidenced_event_is_refused_to_the_nominee(
        self, conn: Any, seeded: dict[str, Any], redis_conn: Any
    ) -> None:
        principal = seeded["subject"]["id"]
        dpo = seeded["users"]["dpo"]["id"]
        nomination = await service.nominate(
            conn,
            principal_user_id=principal,
            nominee_name="Ravi Verma",
            nominee_mobile="+915550000077",
            nominee_email="ravi@example.org",
            rights=["access"],
        )
        await conn.execute(
            "UPDATE nomination SET status = 'active', accepted_at = now() WHERE nomination_id = %s",
            (nomination["nomination_id"],),
        )
        issued = await otp.issue(otp.Scope.NOMINEE_VERIFY, str(nomination["nomination_uuid"]))
        row = await service.nominee_submit(
            conn,
            nomination_uuid=str(nomination["nomination_uuid"]),
            code=issued.code,
            request_type="access",
            request_text="x",
            trigger_event="incapacity",
            evidence_ref=None,
            evidence_hash=None,
        )
        row = await service.record_event_evidence(
            conn, row, evidenced=False, note="No medical evidence supplied", role=DPO, actor_id=dpo
        )
        assert row["status"] == "closed" and row["outcome"] == "refused"
        assert "not evidenced" in str(row["refusal_reason"])

        revoked = await service.revoke_nomination(
            conn, nomination_uuid=str(nomination["nomination_uuid"]), principal_user_id=principal
        )
        assert revoked["status"] == "revoked"


# ---------------------------------------------------------------- public form
class TestPublicForm:
    async def test_a_known_contact_gets_a_code_to_the_stored_channel(
        self, conn: Any, seeded: dict[str, Any], redis_conn: Any
    ) -> None:
        await _unthrottle(redis_conn, "subject@test.local")
        result = await service.submit_public(
            conn,
            request_type="access",
            contact="subject@test.local",
            name="Test Subject",
            request_text="What do you hold?",
            ip_address="127.0.0.1",
        )
        assert result["message"] == service.NEUTRAL_MESSAGE
        row = await repo.by_reference(conn, result["reference"])
        assert row is not None and row["subject_user_id"] == seeded["subject"]["id"]
        assert row["verification_status"] == "pending" and row["acknowledged_at"] is None

        issued = await otp.issue(otp.Scope.RIGHTS_VERIFY, row["reference"])
        verified = await service.verify_public_code(
            conn, reference=row["reference"], code=issued.code
        )
        assert verified["ok"] is True
        row = await repo.by_reference(conn, row["reference"])
        assert row is not None
        assert row["verification_status"] == "verified" and row["verification_method"] == "code"
        assert row["acknowledged_at"] is not None

    async def test_an_unknown_contact_is_recorded_and_told_the_same_thing(
        self, conn: Any, seeded: dict[str, Any], redis_conn: Any
    ) -> None:
        await _unthrottle(redis_conn, "nobody@example.org")
        result = await service.submit_public(
            conn,
            request_type="erasure",
            contact="nobody@example.org",
            name=None,
            request_text="Erase me",
            ip_address="127.0.0.1",
        )
        assert result["message"] == service.NEUTRAL_MESSAGE
        row = await repo.by_reference(conn, result["reference"])
        assert row is not None and row["subject_user_id"] is None
        with pytest.raises(BadRequest) as raised:
            await service.verify_public_code(conn, reference=row["reference"], code="123456")
        assert "Invalid or expired code" in str(raised.value)

    async def test_the_sweep_closes_what_never_verified(
        self, conn: Any, seeded: dict[str, Any], redis_conn: Any
    ) -> None:
        await _unthrottle(redis_conn, "nobody@example.org")
        result = await service.submit_public(
            conn,
            request_type="access",
            contact="nobody@example.org",
            name=None,
            request_text="x",
            ip_address="127.0.0.2",
        )
        await conn.execute(
            "UPDATE rights_request SET received_at = now() - interval '30 days'"
            " WHERE reference = %s",
            (result["reference"],),
        )
        swept = await service.sweep(conn)
        assert swept["closed_unverified"] == 1
        row = await repo.by_reference(conn, result["reference"])
        assert row is not None and row["outcome"] == "not_verified"


# ----------------------------------------------------------------- the register
class TestTheRegister:
    async def test_only_the_dpo_and_the_reviewer_see_anything(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        row = await _portal_request(conn, seeded, "access")
        for role in (
            Role.DCO,
            Role.DCO_ADMIN,
            Role.RCO,
            Role.RND_USER,
            Role.DATA_SUBJECT,
            Role.ADMIN,
        ):
            assert (
                await repo.by_uuid(
                    conn, str(row["request_uuid"]), role=role, user_id=seeded["users"]["dpo"]["id"]
                )
                is None
            )
        assert await repo.by_uuid(conn, str(row["request_uuid"]), role=Role.DPO, user_id=0)

    async def test_her_own_requests_are_hers_alone(self, conn: Any, seeded: dict[str, Any]) -> None:
        row = await _portal_request(conn, seeded, "access")
        assert [r["reference"] for r in await repo.for_subject(conn, seeded["subject"]["id"])] == [
            row["reference"]
        ]
        assert (
            await repo.subject_request(conn, str(row["request_uuid"]), seeded["users"]["dpo"]["id"])
            is None
        )
