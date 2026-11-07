"""The reports a breach calls for (0059, ADR 0037).

Draft, finalise - which mails the organisation's board and nobody else - then,
for a regulator's report, file: both proofs, when, and the reference. Only then
is the duty done. The platform never sends to a regulator.
"""

from __future__ import annotations

import threading
import uuid as uuid_module
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
import pytest

from cmp.core.config import settings
from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.core.messages import Message
from cmp.db.repositories import breach_reports as repo
from cmp.db.repositories import breaches as breach_repo
from cmp.db.repositories import incident_reports as recipients_repo
from cmp.db.sql import execute, fetch_all
from cmp.domain.breach import reports, service
from cmp.domain.breach import settings as breach_settings
from cmp.domain.breach.clock import EventKind
from cmp.infrastructure import messaging
from cmp.infrastructure.dkms.client import DkmsUnavailable
from cmp.infrastructure.email import NullEmailTransport
from cmp.tasks.notifications import breach as claims
from cmp.tasks.notifications import breach_reports as mail_task
from tests.conftest import plain
from tests.integration.test_breach_by_office import _recorded as _recorded_in
from tests.integration.test_rights_by_office import _as_office, _legal_poc

pytestmark = pytest.mark.integration

HOUR = timedelta(hours=1)


def _dpo(seeded: dict[str, Any]) -> int:
    return int(seeded["users"]["dpo"]["id"])


@pytest.fixture(autouse=True)
async def _nobody_on_the_list(conn: Any, seeded: dict[str, Any]) -> None:
    """The board's list is the database's, not the test's, and one that has run
    `tests/http` holds that suite's addresses, a mandatory one among them. Each
    test starts with an empty list; the rollback puts the rest back. A mark
    moves only with its event, and a mandatory entry is never taken off, so
    each is made optional first, as the service would."""
    await execute(
        conn,
        """INSERT INTO breach_board_recipient_event (recipient_id, kind, recorded_by)
           SELECT recipient_id, 'optional', %s FROM breach_board_recipient
            WHERE removed_at IS NULL AND NOT one_off AND mandatory""",
        (_dpo(seeded),),
    )
    await execute(conn, "UPDATE breach_board_recipient SET mandatory = false WHERE mandatory")
    await execute(
        conn,
        """UPDATE breach_board_recipient SET removed_at = now(), removed_by = %s
            WHERE removed_at IS NULL AND NOT one_off""",
        (_dpo(seeded),),
    )


@pytest.fixture
def mailed(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Each delivery queued, instead of a broker."""
    sent: list[str] = []
    import cmp.tasks.dispatch as dispatch

    def queue(task: Any, delivery_uuid: str, *_: Any) -> None:
        if task is mail_task.send_breach_report:
            sent.append(delivery_uuid)

    monkeypatch.setattr(dispatch, "dispatch_optional", queue)
    return sent


async def _board(conn: Any, seeded: dict[str, Any], *emails: str) -> None:
    for email in emails or ("chair@example.org", "member@example.org"):
        await breach_settings.add_board_recipient(
            conn, full_name=None, email=email, actor_id=_dpo(seeded)
        )


async def _incident(conn: Any, seeded: dict[str, Any]) -> str:
    made = await service.record(
        conn,
        title="A laptop left on a train",
        detected_at=datetime.now(UTC) - 2 * HOUR,
        began_at=None,
        location_kind="other",
        processor_uuid=None,
        source_uuid=None,
        location_detail="A train to Mysuru",
        actor_id=_dpo(seeded),
    )
    return str(made["breach_uuid"])


async def _breach(conn: Any, seeded: dict[str, Any]) -> str:
    uuid = await _incident(conn, seeded)
    await service.determine(
        conn,
        breach_uuid=uuid,
        outcome="yes",
        reasoning="Yes",
        became_aware_at=datetime.now(UTC) - HOUR,
        actor_id=_dpo(seeded),
    )
    await service.assess(
        conn,
        breach_uuid=uuid,
        began_at=None,
        categories=[],
        text={
            "nature_extent": "The participant list, unencrypted",
            "likely_impact": "Names and mobiles exposed",
            "circumstances": "It was left on a seat",
            "mitigation": "Passwords reset",
            "caused_by_findings": "A courier",
            "remedial_measures": "Disk encryption everywhere",
        },
        actor_id=_dpo(seeded),
    )
    return uuid


def _kind(overview: dict[str, Any], kind: str) -> dict[str, Any]:
    [found] = [k for k in overview["kinds"] if k["kind"] == kind]
    return found


def _latest(overview: dict[str, Any], kind: str) -> dict[str, Any]:
    return _kind(overview, kind)["versions"][0]


def _section(doc: dict[str, Any], key: str) -> Any:
    [found] = [s for s in doc["sections"] if s["key"] == key]
    return plain(found["body"])


async def _draft(conn: Any, seeded: dict[str, Any], uuid: str, kind: str) -> dict[str, Any]:
    return _latest(
        await reports.draft(conn, breach_uuid=uuid, kind=kind, actor_id=_dpo(seeded)), kind
    )


async def _finalise(conn: Any, seeded: dict[str, Any], uuid: str, kind: str) -> dict[str, Any]:
    doc = await _draft(conn, seeded, uuid, kind)
    return _latest(
        await reports.finalise(
            conn,
            breach_uuid=uuid,
            report_uuid=str(doc["report_uuid"]),
            recipients=None,
            actor_id=_dpo(seeded),
        ),
        kind,
    )


async def _proof(
    conn: Any, seeded: dict[str, Any], uuid: str, doc: dict[str, Any], kind: str
) -> Any:
    return await reports.add_proof(
        conn,
        breach_uuid=uuid,
        report_uuid=str(doc["report_uuid"]),
        kind=kind,
        note=None,
        file_name=f"{kind}.pdf",
        storage_ref=f"breach/{kind}.pdf",
        sha256="a" * 64,
        size_bytes=10,
        content_type="application/pdf",
        actor_id=_dpo(seeded),
    )


async def _file(
    conn: Any, seeded: dict[str, Any], uuid: str, doc: dict[str, Any], *, reference: Any = "DPB/1"
) -> dict[str, Any]:
    return await reports.file_report(
        conn,
        breach_uuid=uuid,
        report_uuid=str(doc["report_uuid"]),
        filed_at=datetime.now(UTC),
        reference=reference,
        actor_id=_dpo(seeded),
    )


def _duty(detail: dict[str, Any], duty: str) -> dict[str, Any]:
    [found] = [d for d in detail["obligations"] if d["duty"] == duty]
    return found


async def _delivery_rows(conn: Any, uuid: str, status: str) -> list[dict[str, Any]]:
    """The account of the mail on one breach, in the order it was written."""
    return await fetch_all(
        conn,
        """SELECT d.delivery_uuid, d.attempt, d.recorded_at FROM breach_report_delivery d
             JOIN breach_report r ON r.report_id = d.report_id
             JOIN breach b ON b.breach_id = r.breach_id
            WHERE b.breach_uuid = %s AND d.status = %s ORDER BY d.delivery_id""",
        (uuid, status),
    )


async def _queued(conn: Any, uuid: str) -> list[str]:
    return [str(r["delivery_uuid"]) for r in await _delivery_rows(conn, uuid, "queued")]


def _counts(doc: dict[str, Any]) -> dict[str, int]:
    return {k: doc["mail"][k] for k in ("delivered", "queued", "failed")}


async def _reached(conn: Any, *deliveries: str) -> None:
    for delivery in deliveries:
        await reports.record_result(conn, delivery_uuid=delivery, status="delivered", detail={})
        await reports.settle(conn, delivery_uuid=delivery)


async def _not_reached(conn: Any, *deliveries: str) -> None:
    for delivery in deliveries:
        await reports.record_result(
            conn,
            delivery_uuid=delivery,
            status="failed",
            detail={"error": "SMTPDataError", "attempts": 6},
        )
        await reports.settle(conn, delivery_uuid=delivery)


async def _long_queued(conn: Any) -> None:
    """Every delivery so far, as if the worker had not seen it in twenty minutes.
    `recorded_at` is the transaction's start, so nothing here ages by itself."""
    await conn.execute("ALTER TABLE breach_report_delivery DISABLE TRIGGER USER")
    await conn.execute(
        """UPDATE breach_report_delivery SET recorded_at = recorded_at - interval '20 minutes'
            WHERE status = 'queued'"""
    )
    await conn.execute("ALTER TABLE breach_report_delivery ENABLE TRIGGER USER")


async def _take_off(conn: Any, seeded: dict[str, Any], email: str) -> None:
    [mine] = [r for r in await recipients_repo.board_recipients(conn) if plain(r["email"]) == email]
    await breach_settings.remove_board_recipient(
        conn, recipient_uuid=str(mine["recipient_uuid"]), actor_id=_dpo(seeded)
    )


async def _resend(
    conn: Any, seeded: dict[str, Any], uuid: str, doc: dict[str, Any]
) -> dict[str, Any]:
    return _latest(
        await reports.resend(
            conn, breach_uuid=uuid, report_uuid=str(doc["report_uuid"]), actor_id=_dpo(seeded)
        ),
        str(doc["kind"]),
    )


async def _trail(conn: Any, uuid: str, event: str) -> list[dict[str, Any]]:
    return await fetch_all(
        conn,
        """SELECT l.actor_user_id, l.detail_json
             FROM audit_log l JOIN breach b ON b.breach_id = l.entity_id
            WHERE l.entity_type = 'breach' AND b.breach_uuid = %s AND l.event_type = %s
            ORDER BY l.log_id""",
        (uuid, event),
    )


async def _entries(conn: Any) -> dict[str, str]:
    """Each address on the list, opened, and the uuid of its entry."""
    return {
        str(plain(r["email"])): str(r["recipient_uuid"])
        for r in await recipients_repo.board_recipients(conn)
    }


async def _mark(conn: Any, seeded: dict[str, Any], email: str, *, mandatory: bool = True) -> None:
    await breach_settings.set_board_recipient_mandatory(
        conn,
        recipient_uuid=(await _entries(conn))[email],
        mandatory=mandatory,
        actor_id=_dpo(seeded),
    )


async def _send(
    conn: Any,
    seeded: dict[str, Any],
    uuid: str,
    doc: dict[str, Any],
    *,
    to: list[str] | None,
    extra: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Finalise a draft to the entries named by address, as the window would
    send them, and to the addresses for this report alone."""
    entries = await _entries(conn)
    return _latest(
        await reports.finalise(
            conn,
            breach_uuid=uuid,
            report_uuid=str(doc["report_uuid"]),
            recipients=None if to is None else [entries[e] for e in to],
            extra=extra or [],
            actor_id=_dpo(seeded),
        ),
        str(doc["kind"]),
    )


async def _addresses(conn: Any, deliveries: list[str]) -> list[str]:
    """Where the worker would mail each delivery, opened."""
    out = []
    for delivery in deliveries:
        job = await reports.job(conn, delivery)
        assert job is not None and job["removed"] is False
        out.append(str(plain(job["email"])))
    return sorted(out)


def _lines(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(plain(r["email"])): r for r in doc["mail"]["recipients"]}


async def _one_offs(conn: Any) -> int:
    [row] = await fetch_all(conn, "SELECT count(*) AS n FROM breach_board_recipient WHERE one_off")
    return int(row["n"])


async def _determine(conn: Any, seeded: dict[str, Any], uuid: str, outcome: str) -> None:
    await service.determine(
        conn,
        breach_uuid=uuid,
        outcome=outcome,
        reasoning="Read and decided",
        became_aware_at=datetime.now(UTC) - HOUR if outcome == "yes" else None,
        actor_id=_dpo(seeded),
    )


async def _cert_in_draft(conn: Any, seeded: dict[str, Any], uuid: str) -> dict[str, Any]:
    """Marked reportable, and a report to CERT-In with every section said."""
    await service.mark_cert_in(conn, breach_uuid=uuid, actor_id=_dpo(seeded))
    doc = await _draft(conn, seeded, uuid, "cert_in")
    await reports.edit(
        conn,
        breach_uuid=uuid,
        report_uuid=str(doc["report_uuid"]),
        bodies={s["key"]: "Said" for s in doc["sections"]},
        actor_id=_dpo(seeded),
    )
    return doc


async def _set_aside_after_a_no(conn: Any, seeded: dict[str, Any], uuid: str) -> None:
    await _determine(conn, seeded, uuid, "no")
    await service.set_aside_cert_in(
        conn, breach_uuid=uuid, reason="A false alarm", actor_id=_dpo(seeded)
    )


class TestADraft:
    async def test_it_starts_from_what_the_register_holds(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "board_intimation")
        assert doc["state"] == "draft" and doc["version"] == 1
        assert _section(doc, "nature_extent") == "The participant list, unencrypted"
        assert _section(doc, "likely_impact") == "Names and mobiles exposed"
        assert "A train to Mysuru" in _section(doc, "location")
        assert "First noticed" in _section(doc, "timing")

    async def test_the_72_hour_report_carries_all_six_items(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "board_report")
        assert len(doc["sections"]) == 6
        assert _section(doc, "findings") == "A courier"
        assert "No notice has yet been sent" in _section(doc, "notices")

    async def test_its_words_are_sealed(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _breach(conn, seeded)
        await _draft(conn, seeded, uuid, "closure")
        rows = await fetch_all(
            conn,
            """SELECT s.body FROM breach_report_section s
                 JOIN breach_report r USING (report_id) JOIN breach b USING (breach_id)
                WHERE b.breach_uuid = %s AND s.body IS NOT NULL""",
            (uuid,),
        )
        assert rows and all(str(r["body"]).startswith("SE::") for r in rows)

    async def test_one_draft_of_a_kind_at_a_time(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _breach(conn, seeded)
        await _draft(conn, seeded, uuid, "closure")
        with pytest.raises(Conflict) as refused:
            await _draft(conn, seeded, uuid, "closure")
        assert refused.value.code == "report_draft_open"
        await _draft(conn, seeded, uuid, "board_report")

    async def test_it_waits_for_the_recording_but_cert_in_only_for_the_mark(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _incident(conn, seeded)
        overview = await reports.overview(conn, breach_uuid=uuid)
        assert "Record the breach" in _kind(overview, "board_report")["blocked_by"]
        assert "Mark it reportable" in _kind(overview, "cert_in")["blocked_by"]
        for kind in ("org_board", "board_intimation", "board_report", "closure", "cert_in"):
            with pytest.raises(Conflict):
                await _draft(conn, seeded, uuid, kind)
        await service.mark_cert_in(conn, breach_uuid=uuid, actor_id=_dpo(seeded))
        assert (await _draft(conn, seeded, uuid, "cert_in"))["state"] == "draft"

    async def test_it_may_be_rewritten_section_by_section(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "board_intimation")
        edited = _latest(
            await reports.edit(
                conn,
                breach_uuid=uuid,
                report_uuid=str(doc["report_uuid"]),
                bodies={"likely_impact": "Worse than first thought"},
                actor_id=_dpo(seeded),
            ),
            "board_intimation",
        )
        assert _section(edited, "likely_impact") == "Worse than first thought"
        assert _section(edited, "nature_extent") == "The participant list, unencrypted"

    async def test_a_section_it_does_not_have_is_refused(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "closure")
        with pytest.raises(ValidationFailed):
            await reports.edit(
                conn,
                breach_uuid=uuid,
                report_uuid=str(doc["report_uuid"]),
                bodies={"nature_extent": "x"},
                actor_id=_dpo(seeded),
            )

    async def test_another_breachs_report_is_not_there(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "closure")
        other = await _breach(conn, seeded)
        with pytest.raises(NotFound):
            await reports.finalise(
                conn,
                breach_uuid=other,
                report_uuid=str(doc["report_uuid"]),
                recipients=None,
                actor_id=_dpo(seeded),
            )


class TestFinalising:
    async def test_it_mails_the_organisations_board_and_freezes_the_words(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        assert doc["state"] == "finalised"
        assert _counts(doc) == {"delivered": 0, "queued": 2, "failed": 0}
        assert len(mailed) == 2
        with pytest.raises(Conflict) as frozen:
            await reports.edit(
                conn,
                breach_uuid=uuid,
                report_uuid=str(doc["report_uuid"]),
                bodies={"likely_impact": "x"},
                actor_id=_dpo(seeded),
            )
        assert frozen.value.code == "report_finalised"

    async def test_it_leaves_the_regulators_duty_outstanding(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "board_intimation")
        detail = await service.detail(conn, uuid)
        assert _duty(detail, "board_intimation")["state"] == "outstanding"

    async def test_it_is_refused_with_nobody_on_the_list(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _breach(conn, seeded)
        with pytest.raises(Conflict) as refused:
            await _finalise(conn, seeded, uuid, "board_intimation")
        assert refused.value.code == "no_board_recipients"

    async def test_it_is_refused_while_a_required_section_is_empty(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "closure")
        with pytest.raises(ValidationFailed) as refused:
            await reports.finalise(
                conn,
                breach_uuid=uuid,
                report_uuid=str(doc["report_uuid"]),
                recipients=None,
                actor_id=_dpo(seeded),
            )
        assert refused.value.details["missing"] == ["conclusion"]

    async def test_a_new_version_starts_from_the_last_ones_words(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        first = await _draft(conn, seeded, uuid, "board_intimation")
        await reports.edit(
            conn,
            breach_uuid=uuid,
            report_uuid=str(first["report_uuid"]),
            bodies={"likely_impact": "As written the first time"},
            actor_id=_dpo(seeded),
        )
        await reports.finalise(
            conn,
            breach_uuid=uuid,
            report_uuid=str(first["report_uuid"]),
            recipients=None,
            actor_id=_dpo(seeded),
        )
        second = await _draft(conn, seeded, uuid, "board_intimation")
        assert second["version"] == 2
        assert _section(second, "likely_impact") == "As written the first time"


class TestNotifyingTheOrganisationsBoard:
    async def test_queued_is_not_told(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "org_board")
        assert doc["mail"]["queued"] == 2
        duty = _duty(await service.detail(conn, uuid), "org_board")
        assert duty["state"] == "outstanding" and duty["reported_to"] is None

    async def test_the_duty_waits_for_every_outcome_and_names_only_those_reached(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "org_board")
        [chair, member] = mailed
        await _reached(conn, chair)
        waiting = _duty(await service.detail(conn, uuid), "org_board")
        assert waiting["state"] == "outstanding", "one address is still to come"
        await _not_reached(conn, member)
        duty = _duty(await service.detail(conn, uuid), "org_board")
        assert duty["state"] == "done"
        assert plain(duty["reported_to"]) == "By email: chair@example.org"

    async def test_nobody_reached_leaves_it_outstanding_until_somebody_is(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "org_board")
        [first] = mailed
        await _not_reached(conn, first)
        assert _duty(await service.detail(conn, uuid), "org_board")["state"] == "outstanding"
        assert any(
            "Organisation's board" in b
            for b in (await service.detail(conn, uuid))["transitions"][0]["blockers"]
        ), "so the breach cannot close on it"
        await _resend(conn, seeded, uuid, doc)
        await _reached(conn, mailed[-1])
        duty = _duty(await service.detail(conn, uuid), "org_board")
        assert duty["state"] == "done"
        assert plain(duty["reported_to"]) == "By email: chair@example.org"

    async def test_it_completes_as_the_system_at_the_time_it_was_reached(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "org_board")
        await _reached(conn, *mailed)
        duty = _duty(await service.detail(conn, uuid), "org_board")
        [delivered] = await _delivery_rows(conn, uuid, "delivered")
        assert duty["completed_at"] == delivered["recorded_at"]
        [event] = await fetch_all(
            conn,
            """SELECT e.recorded_by FROM breach_obligation_event e
                 JOIN breach_obligation o ON o.obligation_id = e.obligation_id
                 JOIN breach b ON b.breach_id = o.breach_id
                WHERE b.breach_uuid = %s AND o.kind = 'org_board' AND e.kind = 'completed'""",
            (uuid,),
        )
        assert event["recorded_by"] is None, "nobody pressed anything"
        [trail] = await _trail(conn, uuid, "breach.obligation_completed")
        assert trail["actor_user_id"] is None
        assert trail["detail_json"]["duty"] == "org_board"
        assert trail["detail_json"]["by"] == "delivery"
        assert trail["detail_json"]["reached"] == 1
        assert trail["detail_json"]["late"] is False

    async def test_it_reads_the_time_the_board_was_first_told(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str], monkeypatch: Any
    ) -> None:
        """The duty completes when the mail has run its course, but it was met
        when somebody was told: a slow last address does not make it late."""
        monkeypatch.setattr(settings, "breach_org_board_minutes", -10)
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "org_board")
        [chair, member] = mailed
        due = _duty(await service.detail(conn, uuid), "org_board")["due_at"]
        reached_at = due - timedelta(minutes=5)
        await execute(
            conn,
            """INSERT INTO breach_report_delivery (report_id, recipient_id, attempt, status,
                                                   recorded_at)
               SELECT report_id, recipient_id, attempt, 'delivered', %s
                 FROM breach_report_delivery WHERE delivery_uuid = %s""",
            (reached_at, chair),
        )
        assert datetime.now(UTC) > due
        await _not_reached(conn, member)
        duty = _duty(await service.detail(conn, uuid), "org_board")
        assert duty["state"] == "done", "and only once the mail has run its course"
        assert duty["completed_at"] == reached_at
        [trail] = await _trail(conn, uuid, "breach.obligation_completed")
        assert trail["detail_json"]["late"] is False

    async def test_a_late_first_delivery_is_still_late(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str], monkeypatch: Any
    ) -> None:
        monkeypatch.setattr(settings, "breach_org_board_minutes", -10)
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "org_board")
        await _reached(conn, *mailed)
        [trail] = await _trail(conn, uuid, "breach.obligation_completed")
        assert trail["detail_json"]["late"] is True

    async def test_a_second_re_read_does_not_complete_it_twice(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "org_board")
        await _reached(conn, *mailed)
        await reports.settle(conn, delivery_uuid=mailed[0])
        assert len(await _trail(conn, uuid, "breach.obligation_completed")) == 1

    async def test_it_does_not_wait_for_an_address_taken_off_the_list(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "org_board")
        [chair, _] = mailed
        await _take_off(conn, seeded, "member@example.org")
        await _reached(conn, chair)
        duty = _duty(await service.detail(conn, uuid), "org_board")
        assert duty["state"] == "done"
        assert plain(duty["reported_to"]) == "By email: chair@example.org"

    async def test_a_report_of_another_kind_tells_this_duty_nothing(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "board_intimation")
        await _reached(conn, *mailed)
        assert _duty(await service.detail(conn, uuid), "org_board")["state"] == "outstanding"

    async def test_a_duty_set_aside_stays_aside(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "org_board")
        await service.determine(
            conn,
            breach_uuid=uuid,
            outcome="no",
            reasoning="It was never read",
            became_aware_at=None,
            actor_id=_dpo(seeded),
        )
        await _reached(conn, *mailed)
        assert _duty(await service.detail(conn, uuid), "org_board")["state"] == "not_applicable"

    async def test_its_draft_names_nobody_who_caused_it(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "org_board")
        assert not any("courier" in str(plain(s["body"])) for s in doc["sections"])

    async def test_it_may_be_sent_again_and_the_duty_stays_done(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "org_board")
        await _reached(conn, *mailed)
        first = _duty(await service.detail(conn, uuid), "org_board")
        await _board(conn, seeded, "member@example.org")
        again = await _finalise(conn, seeded, uuid, "org_board")
        assert again["version"] == 2 and len(mailed) == 3
        await _reached(conn, *mailed[1:])
        duty = _duty(await service.detail(conn, uuid), "org_board")
        assert duty["state"] == "done"
        assert duty["completed_at"] == first["completed_at"]
        assert plain(duty["reported_to"]) == "By email: chair@example.org"

    async def test_it_is_not_filed(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "org_board")
        with pytest.raises(Conflict) as refused:
            await _file(conn, seeded, uuid, doc)
        assert refused.value.code == "report_not_filed"
        with pytest.raises(Conflict):
            await _proof(conn, seeded, uuid, doc, "approval")


class TestTakingAnAddressOffTheList:
    """No further result would arrive for a mail that was lost, so taking the
    address off is itself the result the duty was waiting on."""

    @pytest.fixture
    def told(self, monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
        """The results left to the worker, each with its delivery."""
        out: list[tuple[Any, ...]] = []
        import cmp.tasks.dispatch as dispatch

        def queue(task: Any, *args: Any) -> None:
            if task is mail_task.record_breach_report_result:
                out.append(args)

        monkeypatch.setattr(dispatch, "dispatch_optional", queue)
        return out

    @staticmethod
    async def _as_the_worker(conn: Any, told: list[tuple[Any, ...]]) -> None:
        for delivery, status, detail in told:
            await reports.record_result(conn, delivery_uuid=delivery, status=status, detail=detail)
            await reports.settle(conn, delivery_uuid=delivery)

    async def test_the_duty_is_re_read_when_the_mail_to_it_was_lost(
        self, conn: Any, seeded: dict[str, Any], told: list[tuple[Any, ...]]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "org_board")
        [chair, _] = await _queued(conn, uuid)
        await _reached(conn, chair)
        assert _duty(await service.detail(conn, uuid), "org_board")["state"] == "outstanding"
        await _take_off(conn, seeded, "member@example.org")
        assert [t[1:] for t in told] == [("failed", {"error": "RecipientRemoved", "attempts": 1})]
        await self._as_the_worker(conn, told)
        duty = _duty(await service.detail(conn, uuid), "org_board")
        assert duty["state"] == "done"
        assert plain(duty["reported_to"]) == "By email: chair@example.org"
        doc = _latest(await reports.overview(conn, breach_uuid=uuid), "org_board")
        assert _counts(doc) == {"delivered": 1, "queued": 0, "failed": 0}
        assert doc["mail"]["recipients"][1]["error"] == "RecipientRemoved"

    async def test_nobody_reached_is_still_outstanding(
        self, conn: Any, seeded: dict[str, Any], told: list[tuple[Any, ...]]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "org_board")
        await _take_off(conn, seeded, "member@example.org")
        await self._as_the_worker(conn, told)
        assert _duty(await service.detail(conn, uuid), "org_board")["state"] == "outstanding"

    async def test_a_mail_already_running_its_course_is_left_alone(
        self, conn: Any, seeded: dict[str, Any], told: list[tuple[Any, ...]]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "org_board")
        [chair, member] = await _queued(conn, uuid)
        await _reached(conn, chair, member)
        await _take_off(conn, seeded, "member@example.org")
        assert told == [], "nothing was waiting on it"
        assert len(await _trail(conn, uuid, "breach.obligation_completed")) == 1

    async def test_the_task_and_the_removal_record_one_result(
        self, conn: Any, seeded: dict[str, Any], told: list[tuple[Any, ...]]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "org_board")
        await _take_off(conn, seeded, "chair@example.org")
        await self._as_the_worker(conn, told)
        await self._as_the_worker(conn, told)
        assert len(await _delivery_rows(conn, uuid, "failed")) == 1

    async def test_a_mail_that_got_there_first_is_not_written_over(
        self, conn: Any, seeded: dict[str, Any], told: list[tuple[Any, ...]]
    ) -> None:
        """The list was read, and the mail landed before the result was written."""
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "org_board")
        [chair] = await _queued(conn, uuid)
        await _take_off(conn, seeded, "chair@example.org")
        await _reached(conn, chair)
        await self._as_the_worker(conn, told)
        doc = _latest(await reports.overview(conn, breach_uuid=uuid), "org_board")
        assert _counts(doc) == {"delivered": 1, "queued": 0, "failed": 0}

    async def test_a_retry_under_the_row_it_was_sent_under_stops_when_the_address_goes(
        self, conn: Any, seeded: dict[str, Any], told: list[tuple[Any, ...]], monkeypatch: Any
    ) -> None:
        """Taken off and put back, an address is retried under the row its
        version was sent to. Taking the new row off stops that retry too: it
        is the same address."""
        sent: list[str] = []
        import cmp.tasks.dispatch as dispatch

        def queue(task: Any, *args: Any) -> None:
            if task is mail_task.send_breach_report:
                sent.append(args[0])
            elif task is mail_task.record_breach_report_result:
                told.append(args)

        monkeypatch.setattr(dispatch, "dispatch_optional", queue)
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "org_board")
        await _not_reached(conn, *sent)
        await _take_off(conn, seeded, "chair@example.org")
        await _board(conn, seeded, "chair@example.org")
        await _resend(conn, seeded, uuid, doc)
        retry = sent[-1]
        told.clear()
        await _take_off(conn, seeded, "chair@example.org")
        assert [t[0] for t in told] == [retry]
        assert await reports.job(conn, retry) == {"removed": True}

    async def test_it_reaches_both_offices_and_serves_neither(
        self, conn: Any, seeded: dict[str, Any], told: list[tuple[Any, ...]]
    ) -> None:
        """The list is shared. A DPO taking an address off finds the Legal
        office's report waiting on it, without being able to read that report."""
        legal = await _legal_poc(conn)
        await _board(conn, seeded, "chair@example.org")
        await _as_office(conn, "rnd")
        await _finalise(conn, seeded, await _breach(conn, seeded), "org_board")
        await _as_office(conn, "hr")
        mine = await _recorded_in(conn, actor_id=legal, office="hr")
        draft = await reports.draft(conn, breach_uuid=mine, kind="org_board", actor_id=legal)
        doc = _latest(draft, "org_board")
        await reports.edit(
            conn,
            breach_uuid=mine,
            report_uuid=str(doc["report_uuid"]),
            bodies={s["key"]: "Said" for s in doc["sections"]},
            actor_id=legal,
        )
        await reports.finalise(
            conn,
            breach_uuid=mine,
            report_uuid=str(doc["report_uuid"]),
            recipients=None,
            actor_id=legal,
        )
        await _as_office(conn, "rnd")
        await _take_off(conn, seeded, "chair@example.org")
        assert len({t[0] for t in told}) == 2
        with pytest.raises(NotFound):
            await service.require(conn, mine)
        office = await (
            await conn.execute("SELECT current_setting('app.office', true) AS office")
        ).fetchone()
        assert office["office"] == "rnd", "the wall is back up"

    async def test_the_look_across_is_needed_where_the_policies_bind(
        self, conn: Any, seeded: dict[str, Any], told: list[tuple[Any, ...]]
    ) -> None:
        """On a role the policies bind, as the API runs: the suite's own user
        is a superuser, for which the office setting does nothing."""
        await _board(conn, seeded, "chair@example.org")
        await _as_office(conn, "rnd")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "org_board")
        [recipient] = await recipients_repo.board_recipients(conn)
        probe = f"cmp_board_probe_{uuid_module.uuid4().hex[:12]}"
        await conn.execute(f"CREATE ROLE {probe} NOLOGIN NOSUPERUSER NOBYPASSRLS")
        await conn.execute(f"GRANT USAGE ON SCHEMA public TO {probe}")
        await conn.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {probe}")
        await conn.execute(f"SET LOCAL ROLE {probe}")
        await conn.execute("SELECT set_config('app.office', 'hr', false)")
        assert await repo.queued_to(conn, str(recipient["recipient_uuid"])) == []
        await reports.taken_off(conn, str(recipient["recipient_uuid"]))
        assert len(told) == 1
        await conn.execute("RESET ROLE")


class TestSendingAgain:
    async def test_an_address_taken_off_the_list_is_not_tried(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        [chair, member] = mailed
        await _reached(conn, chair)
        await _not_reached(conn, member)
        await _take_off(conn, seeded, "member@example.org")
        mailed.clear()
        again = await _resend(conn, seeded, uuid, doc)
        assert mailed == []
        assert _counts(again) == {"delivered": 1, "queued": 0, "failed": 0}
        assert await _trail(conn, uuid, "breach.report_resent") == []

    async def test_a_delivery_lost_to_an_address_taken_off_is_not_queued_again(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str], monkeypatch: Any
    ) -> None:
        monkeypatch.setattr(reports, "STALE_AFTER", timedelta(minutes=-1))
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        [chair, _] = mailed
        await _reached(conn, chair)
        # Lost: the worker never saw it, and nothing records it as anything.
        await _take_off(conn, seeded, "member@example.org")
        mailed.clear()
        again = await _resend(conn, seeded, uuid, doc)
        assert mailed == []
        assert again["mail"]["stale"] == 0, "sending again would not move it"

    async def test_the_worker_does_not_mail_an_address_taken_off_since_it_was_queued(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "board_intimation")
        [delivery] = mailed
        await _take_off(conn, seeded, "chair@example.org")
        assert await reports.job(conn, delivery) == {"removed": True}

    async def test_an_address_added_to_the_list_since_is_not_sent_a_version_it_was_not_addressed(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        """A wrong address is put right by a new version, sent to whoever is
        chosen for it: Try again sends what was frozen to whom it was frozen."""
        await _board(conn, seeded, "wrong@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        await _not_reached(conn, *mailed)
        await _take_off(conn, seeded, "wrong@example.org")
        await _board(conn, seeded, "right@example.org")
        mailed.clear()
        again = await _resend(conn, seeded, uuid, doc)
        assert mailed == []
        [line] = again["mail"]["recipients"]
        assert plain(line["email"]) == "wrong@example.org", "the new address has no line"
        assert (line["status"], line["removed"]) == ("failed", True)
        assert again["mail"]["retryable"] == 0
        assert await _trail(conn, uuid, "breach.report_resent") == []

    async def test_a_failure_is_a_new_attempt(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        await _not_reached(conn, *mailed)
        again = await _resend(conn, seeded, uuid, doc)
        [row] = again["mail"]["recipients"]
        assert (row["attempt"], row["status"], row["error"]) == (2, "queued", None)
        assert len(set(mailed)) == 2

    async def test_a_lost_delivery_is_queued_again_and_reads_as_moving(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        [lost] = mailed
        await _long_queued(conn)
        held_up = _latest(await reports.overview(conn, breach_uuid=uuid), "board_intimation")
        assert held_up["mail"]["stale"] == 1 and held_up["mail"]["retryable"] == 1
        mailed.clear()
        again = await _resend(conn, seeded, uuid, doc)
        [fresh] = mailed
        assert fresh != lost, "the account is only added to, so a row says it moved"
        assert _counts(again) == {"delivered": 0, "queued": 1, "failed": 0}
        assert again["mail"]["stale"] == 0, "and for as long as a new delivery would be"
        assert again["mail"]["retryable"] == 0, "so a second press queues nothing"
        assert again["mail"]["recipients"][0]["attempt"] == 2
        [trail] = await _trail(conn, uuid, "breach.report_resent")
        assert trail["detail_json"]["requeued"] == 1 and trail["detail_json"]["queued"] == 1
        mailed.clear()
        await _resend(conn, seeded, uuid, doc)
        assert mailed == []

    async def test_the_lost_task_stands_down_for_the_attempt_that_replaced_it(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        [lost] = mailed
        await _long_queued(conn)
        await _resend(conn, seeded, uuid, doc)
        fresh = mailed[-1]
        assert await reports.claim_key(conn, lost) is None
        assert await reports.job(conn, lost) is None
        assert await reports.claim_key(conn, fresh) is not None

    async def test_a_first_task_that_was_only_slow_stops_the_second(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        """Its outcome lands on the attempt it had, and nothing is sent after."""
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        [slow] = mailed
        await _long_queued(conn)
        await _resend(conn, seeded, uuid, doc)
        fresh = mailed[-1]
        await _reached(conn, slow)
        assert await reports.job(conn, fresh) is None
        assert await reports.claim_key(conn, fresh) is None
        latest = _latest(await reports.overview(conn, breach_uuid=uuid), "board_intimation")
        assert _counts(latest) == {"delivered": 1, "queued": 0, "failed": 0}

    async def test_a_failure_landing_after_a_new_attempt_still_leaves_a_next_one(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        [slow] = mailed
        await _long_queued(conn)
        await _resend(conn, seeded, uuid, doc)
        await _not_reached(conn, slow)
        mailed.clear()
        again = await _resend(conn, seeded, uuid, doc)
        assert len(mailed) == 1
        assert again["mail"]["recipients"][0]["attempt"] == 3

    async def test_the_same_address_and_report_claim_the_same_thing(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        """So a task queued again under a new uuid cannot get around it, nor can
        a row of the list put back after it was taken off."""
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        [first] = mailed
        key = await reports.claim_key(conn, first)
        await _long_queued(conn)
        await _resend(conn, seeded, uuid, doc)
        assert await reports.claim_key(conn, mailed[-1]) == key
        await _take_off(conn, seeded, "chair@example.org")
        await _board(conn, seeded, "chair@example.org")
        await _not_reached(conn, mailed[-1])
        await _resend(conn, seeded, uuid, doc)
        assert await reports.claim_key(conn, mailed[-1]) == key

    async def test_a_redis_claim_is_one_holder_for_longer_than_a_task(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        """On the real thing: `SET NX`, with a time to live."""
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "board_intimation")
        key = await reports.claim_key(conn, mailed[0])
        assert key is not None and key.startswith("mutex:breach_report:")
        redis = messaging._redis()
        try:
            assert claims.take_claim(key, "first-task") is True
            assert claims.take_claim(key, "second-task") is False
            assert claims.take_claim(key, "first-task") is True, "the same task, back"
            assert 600 < redis.ttl(key) <= claims.CLAIM_TTL_S
            claims.keep_claim(key, mail_task.CLAIM_KEPT_S)
            assert redis.ttl(key) > claims.CLAIM_TTL_S
            claims.drop_claim(key)
            assert claims.take_claim(key, "second-task") is True
        finally:
            redis.delete(key)

    async def test_it_says_how_many_it_queued(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        await _not_reached(conn, *mailed)
        resend = reports.resend(
            conn, breach_uuid=uuid, report_uuid=str(doc["report_uuid"]), actor_id=_dpo(seeded)
        )
        assert (await resend)["queued"] == 2
        again = await reports.resend(
            conn, breach_uuid=uuid, report_uuid=str(doc["report_uuid"]), actor_id=_dpo(seeded)
        )
        assert again["queued"] == 0
        assert "kinds" in again and "board_recipients" in again, "the rest is as it was"

    async def test_an_emptied_list_refuses_nothing_and_tries_nobody_taken_off(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        await _not_reached(conn, *mailed)
        await _take_off(conn, seeded, "chair@example.org")
        mailed.clear()
        again = await reports.resend(
            conn, breach_uuid=uuid, report_uuid=str(doc["report_uuid"]), actor_id=_dpo(seeded)
        )
        assert again["queued"] == 0 and mailed == []
        assert _latest(again, "board_intimation")["mail"]["retryable"] == 0

    async def test_a_version_a_later_one_replaced_is_not_sent_again(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        """Pressed on the old row it would mail the old words, after the new."""
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        first = await _finalise(conn, seeded, uuid, "board_intimation")
        await _not_reached(conn, *mailed)
        await _finalise(conn, seeded, uuid, "board_intimation")
        mailed.clear()
        with pytest.raises(Conflict) as refused:
            await _resend(conn, seeded, uuid, first)
        assert refused.value.code == "report_superseded"
        assert mailed == []

    async def test_a_draft_of_a_later_version_does_not_replace_it(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        first = await _finalise(conn, seeded, uuid, "board_intimation")
        await _not_reached(conn, *mailed)
        await _draft(conn, seeded, uuid, "board_intimation")
        mailed.clear()
        await reports.resend(
            conn, breach_uuid=uuid, report_uuid=str(first["report_uuid"]), actor_id=_dpo(seeded)
        )
        assert len(mailed) == 1

    async def test_an_address_taken_off_and_put_back_is_not_mailed_what_it_has(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        """The only way to correct a name, and a new row of the list."""
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        [chair, member] = mailed
        await _reached(conn, chair)
        await _not_reached(conn, member)
        await _take_off(conn, seeded, "chair@example.org")
        await breach_settings.add_board_recipient(
            conn, full_name="The Chair", email="chair@example.org", actor_id=_dpo(seeded)
        )
        mailed.clear()
        again = await _resend(conn, seeded, uuid, doc)
        [delivery] = mailed
        job = await reports.job(conn, delivery)
        assert job is not None and plain(job["email"]) == "member@example.org"
        [trail] = await _trail(conn, uuid, "breach.report_resent")
        assert trail["detail_json"]["queued"] == 1 and trail["detail_json"]["first"] == 0
        assert again["mail"]["delivered"] == 1
        assert len(again["mail"]["recipients"]) == 2, "one line for the chair, not two"
        [line] = [r for r in again["mail"]["recipients"] if r["status"] == "delivered"]
        assert plain(line["email"]) == "chair@example.org"
        assert line["removed"] is False, "it is back on the list"

    async def test_an_address_put_back_that_was_never_reached_is_tried(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        await _not_reached(conn, *mailed)
        await _take_off(conn, seeded, "chair@example.org")
        await _board(conn, seeded, "chair@example.org")
        mailed.clear()
        again = await _resend(conn, seeded, uuid, doc)
        [delivery] = mailed
        [line] = again["mail"]["recipients"]
        assert (line["status"], line["attempt"], line["removed"]) == ("queued", 2, False)
        job = await reports.job(conn, delivery)
        assert job is not None and job["removed"] is False, "under the row it was sent under"
        assert plain(job["email"]) == "chair@example.org"

    async def test_a_delivery_still_on_its_way_is_left_alone(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        mailed.clear()
        again = await _resend(conn, seeded, uuid, doc)
        assert mailed == [] and again["mail"]["stale"] == 0
        assert await _trail(conn, uuid, "breach.report_resent") == [], "nothing was queued"

    async def test_what_it_queued_is_on_the_trail_and_no_address_is(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        await _not_reached(conn, *mailed)
        await _board(conn, seeded, "member@example.org")
        await _resend(conn, seeded, uuid, doc)
        [trail] = await _trail(conn, uuid, "breach.report_resent")
        detail = trail["detail_json"]
        assert (detail["kind"], detail["version"]) == ("board_intimation", 1)
        assert (detail["queued"], detail["first"], detail["retried"]) == (1, 0, 1)
        assert "example.org" not in str(detail)


class TestWhatTheOfficeIsShownOfTheMail:
    async def test_each_address_says_where_it_stands_and_why(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await breach_settings.add_board_recipient(
            conn, full_name="The Chair", email="chair@example.org", actor_id=_dpo(seeded)
        )
        await _board(conn, seeded, "member@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "board_intimation")
        [chair, member] = mailed
        await _reached(conn, chair)
        await _not_reached(conn, member)
        await _take_off(conn, seeded, "member@example.org")
        doc = _latest(await reports.overview(conn, breach_uuid=uuid), "board_intimation")
        assert set(doc["mail"]) == {
            "delivered",
            "queued",
            "failed",
            "unsent",
            "held",
            "stale",
            "retryable",
            "recipients",
        }
        [first, second] = doc["mail"]["recipients"]
        assert set(first) == {
            "recipient_uuid",
            "full_name",
            "email",
            "status",
            "attempt",
            "error",
            "recorded_at",
            "removed",
            "mandatory",
            "added_for_this_send",
        }
        assert (first["mandatory"], first["added_for_this_send"]) == (False, False)
        assert str(first["email"]).startswith("SE::"), "sealed; the console opens it"
        assert str(first["full_name"]).startswith("SE::")
        assert plain(first["full_name"]) == "The Chair"
        assert (first["status"], first["error"], first["removed"]) == ("delivered", None, False)
        assert plain(second["email"]) == "member@example.org" and second["full_name"] is None
        assert (second["status"], second["error"]) == ("failed", "SMTPDataError")
        assert second["attempt"] == 1 and second["removed"] is True

    async def test_a_mail_long_queued_counts_as_stale(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str], monkeypatch: Any
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "board_intimation")
        fresh = _latest(await reports.overview(conn, breach_uuid=uuid), "board_intimation")
        assert fresh["mail"]["stale"] == 0
        monkeypatch.setattr(reports, "STALE_AFTER", timedelta(minutes=-1))
        stale = _latest(await reports.overview(conn, breach_uuid=uuid), "board_intimation")
        assert stale["mail"]["stale"] == 1

    async def test_a_failed_address_taken_off_is_listed_but_not_counted(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "board_intimation")
        [chair, member] = mailed
        await _reached(conn, chair)
        await _not_reached(conn, member)
        before = _latest(await reports.overview(conn, breach_uuid=uuid), "board_intimation")
        assert before["mail"]["failed"] == 1 and before["mail"]["retryable"] == 1
        await _take_off(conn, seeded, "member@example.org")
        mail = _latest(await reports.overview(conn, breach_uuid=uuid), "board_intimation")["mail"]
        assert (mail["failed"], mail["retryable"]) == (0, 0)
        assert [r["removed"] for r in mail["recipients"]] == [False, True]

    async def test_retryable_is_what_sending_again_would_queue(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        """Failed and lost. An address added to the list since was never this
        version's, so it is not counted."""
        await _board(conn, seeded, "failed@example.org", "lost@example.org", "fine@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        [failed, _, fine] = mailed
        await _long_queued(conn)
        await _not_reached(conn, failed)
        await _reached(conn, fine)
        await _board(conn, seeded, "added@example.org")
        read = _latest(await reports.overview(conn, breach_uuid=uuid), "board_intimation")
        assert read["mail"]["retryable"] == 2
        resent = await reports.resend(
            conn, breach_uuid=uuid, report_uuid=str(doc["report_uuid"]), actor_id=_dpo(seeded)
        )
        assert resent["queued"] == 2

    async def test_every_address_reached_leaves_nothing_to_send(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "board_intimation")
        await _reached(conn, *mailed)
        read = _latest(await reports.overview(conn, breach_uuid=uuid), "board_intimation")
        assert read["mail"]["retryable"] == 0

    async def test_a_draft_has_nothing_to_send(self, conn: Any, seeded: dict[str, Any]) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "board_intimation")
        assert doc["mail"]["retryable"] == 0

    async def test_a_version_a_later_one_replaced_has_nothing_to_send(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "board_intimation")
        await _not_reached(conn, *mailed)
        latest = await _finalise(conn, seeded, uuid, "board_intimation")
        await _not_reached(conn, mailed[-1])
        [newest, older] = _kind(await reports.overview(conn, breach_uuid=uuid), "board_intimation")[
            "versions"
        ]
        assert newest["report_uuid"] == latest["report_uuid"]
        assert newest["mail"]["retryable"] == 1
        assert older["mail"]["failed"] == 1, "it still says what happened"
        assert older["mail"]["retryable"] == 0

    async def test_a_closed_breach_has_nothing_to_send(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "board_intimation")
        await _not_reached(conn, *mailed)
        await execute(conn, "UPDATE breach SET status = 'closed' WHERE breach_uuid = %s", (uuid,))
        read = _latest(await reports.overview(conn, breach_uuid=uuid), "board_intimation")
        assert read["mail"]["failed"] == 1 and read["mail"]["retryable"] == 0


class TestAProofIsKept:
    """`check_proof` before the file is stored, and `add_proof` under the lock."""

    async def _both_refuse(
        self, conn: Any, seeded: dict[str, Any], uuid: str, doc: dict[str, Any], *, kind: str
    ) -> Any:
        with pytest.raises((Conflict, ValidationFailed)) as checked:
            await reports.check_proof(
                conn, breach_uuid=uuid, report_uuid=str(doc["report_uuid"]), kind=kind
            )
        with pytest.raises((Conflict, ValidationFailed)) as written:
            await _proof(conn, seeded, uuid, doc, kind)
        assert type(checked.value) is type(written.value)
        return checked.value

    async def test_not_on_a_draft(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "board_intimation")
        refused = await self._both_refuse(conn, seeded, uuid, doc, kind="approval")
        assert refused.code == "report_not_finalised"

    async def test_not_on_a_filed_report(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        for proof in ("approval", "sent_mail"):
            await _proof(conn, seeded, uuid, doc, proof)
        await _file(conn, seeded, uuid, doc)
        refused = await self._both_refuse(conn, seeded, uuid, doc, kind="approval")
        assert refused.code == "report_filed"

    async def test_not_on_the_report_to_the_organisations_board(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "org_board")
        refused = await self._both_refuse(conn, seeded, uuid, doc, kind="sent_mail")
        assert refused.code == "report_not_filed"

    async def test_only_the_two_kinds(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        refused = await self._both_refuse(conn, seeded, uuid, doc, kind="email")
        assert refused.field == "kind"

    async def test_a_kept_proof_passes_the_check_and_the_write(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        await reports.check_proof(
            conn, breach_uuid=uuid, report_uuid=str(doc["report_uuid"]), kind="approval"
        )
        kept = _latest(await _proof(conn, seeded, uuid, doc, "approval"), "board_intimation")
        assert [e["kind"] for e in kept["evidence"]] == ["approval"]

    async def test_not_on_another_breachs_report(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        mine = await _breach(conn, seeded)
        theirs = await _draft(conn, seeded, await _breach(conn, seeded), "board_intimation")
        with pytest.raises(NotFound):
            await reports.check_proof(
                conn, breach_uuid=mine, report_uuid=str(theirs["report_uuid"]), kind="approval"
            )


class TestWhatMustComeFirst:
    async def test_a_draft_is_neither_filed_nor_sent_again(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "board_intimation")
        with pytest.raises(Conflict) as unfiled:
            await _file(conn, seeded, uuid, doc)
        assert unfiled.value.code == "report_not_finalised"
        with pytest.raises(Conflict) as unsent:
            await _resend(conn, seeded, uuid, doc)
        assert unsent.value.code == "report_not_finalised"

    async def test_the_proof_of_one_version_does_not_file_the_next(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        first = await _finalise(conn, seeded, uuid, "board_intimation")
        for proof in ("approval", "sent_mail"):
            await _proof(conn, seeded, uuid, first, proof)
        second = await _finalise(conn, seeded, uuid, "board_intimation")
        with pytest.raises(Conflict) as lacking:
            await _file(conn, seeded, uuid, second)
        assert lacking.value.code == "report_proof_missing"


class TestFiling:
    async def test_it_needs_both_proofs_and_completes_the_duty(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        with pytest.raises(Conflict) as none:
            await _file(conn, seeded, uuid, doc)
        assert none.value.code == "report_proof_missing"
        await _proof(conn, seeded, uuid, doc, "approval")
        with pytest.raises(Conflict) as one:
            await _file(conn, seeded, uuid, doc)
        assert "The mail sent to the regulator" in str(one.value)
        await _proof(conn, seeded, uuid, doc, "sent_mail")
        filed = _latest(await _file(conn, seeded, uuid, doc), "board_intimation")
        assert filed["state"] == "filed" and filed["filed_reference"] == "DPB/1"
        assert {e["kind"] for e in filed["evidence"]} == {"approval", "sent_mail"}
        duty = _duty(await service.detail(conn, uuid), "board_intimation")
        assert duty["state"] == "done" and duty["reference"] == "DPB/1"

    async def test_a_regulators_report_needs_the_reference_and_a_closure_does_not(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        for proof in ("approval", "sent_mail"):
            await _proof(conn, seeded, uuid, doc, proof)
        with pytest.raises(ValidationFailed) as refused:
            await _file(conn, seeded, uuid, doc, reference=" ")
        assert refused.value.field == "reference"

        closure = await _draft(conn, seeded, uuid, "closure")
        await reports.edit(
            conn,
            breach_uuid=uuid,
            report_uuid=str(closure["report_uuid"]),
            bodies={
                "conclusion": "Concluded",
                "root_cause": "x",
                "measures": "x",
                "prevention": "x",
            },
            actor_id=_dpo(seeded),
        )
        done = _latest(
            await reports.finalise(
                conn,
                breach_uuid=uuid,
                report_uuid=str(closure["report_uuid"]),
                recipients=None,
                actor_id=_dpo(seeded),
            ),
            "closure",
        )
        for proof in ("approval", "sent_mail"):
            await _proof(conn, seeded, uuid, done, proof)
        filed = _latest(await _file(conn, seeded, uuid, done, reference=None), "closure")
        assert filed["state"] == "filed"

    async def test_a_person_may_have_sent_it_before_it_was_finalised_here(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        for proof in ("approval", "sent_mail"):
            await _proof(conn, seeded, uuid, doc, proof)
        sent = doc["finalised_at"] - timedelta(minutes=30)
        filed = _latest(
            await reports.file_report(
                conn,
                breach_uuid=uuid,
                report_uuid=str(doc["report_uuid"]),
                filed_at=sent,
                reference="DPB/1",
                actor_id=_dpo(seeded),
            ),
            "board_intimation",
        )
        assert filed["filed_at"] == sent
        assert _duty(await service.detail(conn, uuid), "board_intimation")["completed_at"] == sent

    @pytest.mark.parametrize(
        ("when", "field"),
        [(HOUR, "filed_at"), (-2 * HOUR, "occurred_at")],
        ids=["in the future", "before its clock started"],
    )
    async def test_the_time_may_not_be_impossible(
        self,
        conn: Any,
        seeded: dict[str, Any],
        mailed: list[str],
        when: timedelta,
        field: str,
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        for proof in ("approval", "sent_mail"):
            await _proof(conn, seeded, uuid, doc, proof)
        with pytest.raises(ValidationFailed) as refused:
            await reports.file_report(
                conn,
                breach_uuid=uuid,
                report_uuid=str(doc["report_uuid"]),
                filed_at=datetime.now(UTC) + when,
                reference="DPB/1",
                actor_id=_dpo(seeded),
            )
        assert refused.value.field == field

    async def test_it_is_filed_once(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        for proof in ("approval", "sent_mail"):
            await _proof(conn, seeded, uuid, doc, proof)
        await _file(conn, seeded, uuid, doc)
        with pytest.raises(Conflict) as again:
            await _file(conn, seeded, uuid, doc)
        assert again.value.code == "report_filed"

    async def test_the_cert_in_report_runs_before_validation(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _incident(conn, seeded)
        await service.mark_cert_in(conn, breach_uuid=uuid, actor_id=_dpo(seeded))
        doc = await _draft(conn, seeded, uuid, "cert_in")
        await reports.edit(
            conn,
            breach_uuid=uuid,
            report_uuid=str(doc["report_uuid"]),
            bodies={"affected_systems": "A laptop", "actions": "Passwords reset"},
            actor_id=_dpo(seeded),
        )
        done = _latest(
            await reports.finalise(
                conn,
                breach_uuid=uuid,
                report_uuid=str(doc["report_uuid"]),
                recipients=None,
                actor_id=_dpo(seeded),
            ),
            "cert_in",
        )
        assert mailed == [], "the board's mail waits for a yes"
        assert done["mail"]["held"] == 2
        for proof in ("approval", "sent_mail"):
            await _proof(conn, seeded, uuid, done, proof)
        await _file(conn, seeded, uuid, done, reference="CERT/1")
        assert _duty(await service.detail(conn, uuid), "cert_in")["state"] == "done"

    async def test_a_second_filing_leaves_the_duty_as_it_was(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        first = await _finalise(conn, seeded, uuid, "board_intimation")
        for proof in ("approval", "sent_mail"):
            await _proof(conn, seeded, uuid, first, proof)
        await _file(conn, seeded, uuid, first, reference="DPB/1")
        second = await _finalise(conn, seeded, uuid, "board_intimation")
        for proof in ("approval", "sent_mail"):
            await _proof(conn, seeded, uuid, second, proof)
        await _file(conn, seeded, uuid, second, reference="DPB/2")
        duty = _duty(await service.detail(conn, uuid), "board_intimation")
        assert duty["reference"] == "DPB/1", "the duty was done by the first"


async def test_a_closure_report_never_stands_in_the_way_of_closing(
    conn: Any, seeded: dict[str, Any], mailed: list[str]
) -> None:
    await _board(conn, seeded)
    uuid = await _breach(conn, seeded)
    # One finalised and never filed, and the next still a draft.
    doc = await _draft(conn, seeded, uuid, "closure")
    report = str(doc["report_uuid"])
    await reports.edit(
        conn,
        breach_uuid=uuid,
        report_uuid=report,
        bodies={"conclusion": "Nothing further was found"},
        actor_id=_dpo(seeded),
    )
    await reports.finalise(
        conn, breach_uuid=uuid, report_uuid=report, recipients=None, actor_id=_dpo(seeded)
    )
    await _draft(conn, seeded, uuid, "closure")
    breach = await service.require(conn, uuid)
    duties = await service.duties_of(conn, int(breach["breach_id"]))
    assert duties, "there were duties to discharge"
    for duty, (row, _) in duties.items():
        await breach_repo.add_obligation_event(
            conn,
            int(row["obligation_id"]),
            kind=EventKind.COMPLETED,
            occurred_at=datetime.now(UTC),
            reported_to="The chair" if duty == "org_board" else None,
            recorded_by=_dpo(seeded),
        )
    closed = await service.transition(
        conn, breach_uuid=uuid, to="closed", reason=None, actor_id=_dpo(seeded)
    )
    assert closed["status"] == "closed"


class TestTheAccountOfTheMailComesFirst:
    """Written and committed, and the duty after it by itself, so nothing the
    duty needs can undo the account of a mail that went."""

    @pytest.fixture
    def transactions(self, conn: Any, monkeypatch: pytest.MonkeyPatch) -> None:
        """Each of the task's transactions, as a savepoint of this test's."""

        @asynccontextmanager
        async def savepoint() -> AsyncIterator[Any]:
            async with conn.transaction():
                yield conn

        monkeypatch.setattr(mail_task, "transaction", savepoint)

    @staticmethod
    def _key_service_down(monkeypatch: pytest.MonkeyPatch) -> None:
        async def down(*_: Any, **__: Any) -> Any:
            raise DkmsUnavailable("key service down")

        monkeypatch.setattr(reports, "unseal_strings", down)

    async def test_a_key_service_error_leaves_the_mail_on_the_record(
        self,
        conn: Any,
        seeded: dict[str, Any],
        mailed: list[str],
        transactions: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "org_board")
        self._key_service_down(monkeypatch)
        with pytest.raises(DkmsUnavailable):
            await mail_task._recording(mailed[0], "delivered", {})
        assert len(await _delivery_rows(conn, uuid, "delivered")) == 1, "that stands"
        assert _duty(await service.detail(conn, uuid), "org_board")["state"] == "outstanding"

    async def test_recording_it_again_adds_nothing_and_still_reads_the_duty(
        self,
        conn: Any,
        seeded: dict[str, Any],
        mailed: list[str],
        transactions: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "org_board")
        with monkeypatch.context() as down:
            self._key_service_down(down)
            with pytest.raises(DkmsUnavailable):
                await mail_task._recording(mailed[0], "delivered", {})
        await mail_task._recording(mailed[0], "delivered", {})
        assert len(await _delivery_rows(conn, uuid, "delivered")) == 1
        assert _duty(await service.detail(conn, uuid), "org_board")["state"] == "done"

    async def test_recording_waits_for_no_breach_row(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An upload holds that row for as long as a list takes to seal."""
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "org_board")

        async def refuse(*_: Any, **__: Any) -> None:
            pytest.fail("the mail's account took the breach's row")

        monkeypatch.setattr(breach_repo, "lock", refuse)
        await reports.record_result(conn, delivery_uuid=mailed[0], status="delivered", detail={})
        assert len(await _delivery_rows(conn, uuid, "delivered")) == 1

    async def test_try_again_is_the_way_on_from_a_settling_that_failed(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "org_board")
        await reports.record_result(conn, delivery_uuid=mailed[0], status="delivered", detail={})
        assert _duty(await service.detail(conn, uuid), "org_board")["state"] == "outstanding"
        mailed.clear()
        again = await reports.resend(
            conn, breach_uuid=uuid, report_uuid=str(doc["report_uuid"]), actor_id=_dpo(seeded)
        )
        assert again["queued"] == 0 and mailed == []
        duty = _duty(await service.detail(conn, uuid), "org_board")
        assert duty["state"] == "done"
        assert plain(duty["reported_to"]) == "By email: chair@example.org"

    async def test_the_way_on_is_not_barred_by_an_empty_list(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "org_board")
        await reports.record_result(conn, delivery_uuid=mailed[0], status="delivered", detail={})
        await _take_off(conn, seeded, "chair@example.org")
        again = await reports.resend(
            conn, breach_uuid=uuid, report_uuid=str(doc["report_uuid"]), actor_id=_dpo(seeded)
        )
        assert again["queued"] == 0
        assert _duty(await service.detail(conn, uuid), "org_board")["state"] == "done"

    async def test_nor_by_a_later_version(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        first = await _finalise(conn, seeded, uuid, "org_board")
        await reports.record_result(conn, delivery_uuid=mailed[0], status="delivered", detail={})
        await _finalise(conn, seeded, uuid, "org_board")
        again = await reports.resend(
            conn, breach_uuid=uuid, report_uuid=str(first["report_uuid"]), actor_id=_dpo(seeded)
        )
        assert again["queued"] == 0
        assert _duty(await service.detail(conn, uuid), "org_board")["state"] == "done"

    async def test_a_regulators_report_settles_nothing(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        await reports.record_result(conn, delivery_uuid=mailed[0], status="delivered", detail={})
        await reports.resend(
            conn, breach_uuid=uuid, report_uuid=str(doc["report_uuid"]), actor_id=_dpo(seeded)
        )
        assert _duty(await service.detail(conn, uuid), "org_board")["state"] == "outstanding"


class TestACertInReportOnceTheDutyIsSetAside:
    @staticmethod
    async def _set_aside(conn: Any, seeded: dict[str, Any], uuid: str) -> None:
        await service.determine(
            conn,
            breach_uuid=uuid,
            outcome="no",
            reasoning="Not a breach",
            became_aware_at=None,
            actor_id=_dpo(seeded),
        )
        await service.set_aside_cert_in(
            conn, breach_uuid=uuid, reason="A false alarm", actor_id=_dpo(seeded)
        )

    async def test_an_open_draft_cannot_be_finalised_into_a_mail(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _incident(conn, seeded)
        await service.mark_cert_in(conn, breach_uuid=uuid, actor_id=_dpo(seeded))
        doc = await _draft(conn, seeded, uuid, "cert_in")
        await reports.edit(
            conn,
            breach_uuid=uuid,
            report_uuid=str(doc["report_uuid"]),
            bodies={s["key"]: "Said" for s in doc["sections"]},
            actor_id=_dpo(seeded),
        )
        await self._set_aside(conn, seeded, uuid)
        read = _kind(await reports.overview(conn, breach_uuid=uuid), "cert_in")
        assert "Mark it reportable again" in str(read["blocked_by"])
        with pytest.raises(Conflict) as refused:
            await reports.finalise(
                conn,
                breach_uuid=uuid,
                report_uuid=str(doc["report_uuid"]),
                recipients=None,
                actor_id=_dpo(seeded),
            )
        assert "Mark it reportable again" in refused.value.message
        assert mailed == []

    async def test_marked_again_it_may_be_finalised(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _incident(conn, seeded)
        await service.mark_cert_in(conn, breach_uuid=uuid, actor_id=_dpo(seeded))
        doc = await _draft(conn, seeded, uuid, "cert_in")
        await reports.edit(
            conn,
            breach_uuid=uuid,
            report_uuid=str(doc["report_uuid"]),
            bodies={s["key"]: "Said" for s in doc["sections"]},
            actor_id=_dpo(seeded),
        )
        await self._set_aside(conn, seeded, uuid)
        await service.mark_cert_in(conn, breach_uuid=uuid, actor_id=_dpo(seeded))
        done = await reports.finalise(
            conn,
            breach_uuid=uuid,
            report_uuid=str(doc["report_uuid"]),
            recipients=None,
            actor_id=_dpo(seeded),
        )
        assert mailed == [], "never validated yes, so its mail waits for one"
        read = _latest(done, "cert_in")
        assert read["state"] == "finalised" and read["mail"]["held"] == 1

    async def test_a_finalised_one_is_not_mailed_again(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        """Finalised on a recorded breach, so mailed at once; a No and the
        set-aside after it stop the next press, and leave what went."""
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await service.mark_cert_in(conn, breach_uuid=uuid, actor_id=_dpo(seeded))
        doc = await _draft(conn, seeded, uuid, "cert_in")
        await reports.edit(
            conn,
            breach_uuid=uuid,
            report_uuid=str(doc["report_uuid"]),
            bodies={s["key"]: "Said" for s in doc["sections"]},
            actor_id=_dpo(seeded),
        )
        await reports.finalise(
            conn,
            breach_uuid=uuid,
            report_uuid=str(doc["report_uuid"]),
            recipients=None,
            actor_id=_dpo(seeded),
        )
        [sent] = mailed
        await _not_reached(conn, sent)
        await self._set_aside(conn, seeded, uuid)
        read = _latest(await reports.overview(conn, breach_uuid=uuid), "cert_in")
        assert read["mail"]["failed"] == 1 and read["mail"]["retryable"] == 0
        mailed.clear()
        with pytest.raises(Conflict) as refused:
            await _resend(conn, seeded, uuid, doc)
        assert refused.value.code == "breach_not_recorded"
        assert mailed == []

    @staticmethod
    async def _finalised(conn: Any, seeded: dict[str, Any], uuid: str) -> dict[str, Any]:
        await service.mark_cert_in(conn, breach_uuid=uuid, actor_id=_dpo(seeded))
        doc = await _draft(conn, seeded, uuid, "cert_in")
        await reports.edit(
            conn,
            breach_uuid=uuid,
            report_uuid=str(doc["report_uuid"]),
            bodies={s["key"]: "Said" for s in doc["sections"]},
            actor_id=_dpo(seeded),
        )
        await reports.finalise(
            conn,
            breach_uuid=uuid,
            report_uuid=str(doc["report_uuid"]),
            recipients=None,
            actor_id=_dpo(seeded),
        )
        return doc

    async def test_it_takes_no_proof_and_is_not_filed(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        """Filed now it would complete nothing, and the mark made again would
        have no report left to complete it."""
        await _board(conn, seeded, "chair@example.org")
        uuid = await _incident(conn, seeded)
        doc = await self._finalised(conn, seeded, uuid)
        await _proof(conn, seeded, uuid, doc, "approval")
        await _proof(conn, seeded, uuid, doc, "sent_mail")
        await self._set_aside(conn, seeded, uuid)
        with pytest.raises(Conflict) as filing:
            await _file(conn, seeded, uuid, doc, reference="CERT/1")
        assert "Mark it reportable again" in filing.value.message
        with pytest.raises(Conflict) as keeping:
            await _proof(conn, seeded, uuid, doc, "approval")
        assert "Mark it reportable again" in keeping.value.message
        with pytest.raises(Conflict):
            await reports.check_proof(
                conn,
                breach_uuid=uuid,
                report_uuid=str(doc["report_uuid"]),
                kind="approval",
            )

    async def test_marked_again_the_same_report_completes_the_duty(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _incident(conn, seeded)
        doc = await self._finalised(conn, seeded, uuid)
        await _proof(conn, seeded, uuid, doc, "approval")
        await _proof(conn, seeded, uuid, doc, "sent_mail")
        await self._set_aside(conn, seeded, uuid)
        await service.mark_cert_in(conn, breach_uuid=uuid, actor_id=_dpo(seeded))
        await _file(conn, seeded, uuid, doc, reference="CERT/1")
        assert _duty(await service.detail(conn, uuid), "cert_in")["state"] == "done"


class TestAMailThatHasGoneStaysGone:
    """Recording takes no breach lock, so a re-queue or a removal can be written
    just behind a delivered row. Neither takes the mail back."""

    @staticmethod
    async def _reached_then(
        conn: Any, seeded: dict[str, Any], mailed: list[str], status: str
    ) -> tuple[str, dict[str, Any]]:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "org_board")
        await reports.record_result(conn, delivery_uuid=mailed[0], status="delivered", detail={})
        row = await fetch_all(
            conn,
            """SELECT d.report_id, d.recipient_id, d.attempt FROM breach_report_delivery d
                WHERE d.delivery_uuid = %s""",
            (mailed[0],),
        )
        await repo.add_delivery(
            conn,
            row[0]["report_id"],
            row[0]["recipient_id"],
            attempt=row[0]["attempt"] + 1,
            status=status,
            detail={"error": "RecipientRemoved"} if status == "failed" else None,
        )
        return uuid, doc

    @pytest.mark.parametrize("status", ["queued", "failed"])
    async def test_it_reads_delivered_and_nothing_is_owed(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str], status: str
    ) -> None:
        uuid, _ = await self._reached_then(conn, seeded, mailed, status)
        read = _latest(await reports.overview(conn, breach_uuid=uuid), "org_board")
        assert _counts(read) == {"delivered": 1, "queued": 0, "failed": 0}
        assert read["mail"]["retryable"] == 0
        assert [r["status"] for r in read["mail"]["recipients"]] == ["delivered"]

    @pytest.mark.parametrize("status", ["queued", "failed"])
    async def test_the_duty_completes_from_it(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str], status: str
    ) -> None:
        uuid, _ = await self._reached_then(conn, seeded, mailed, status)
        await reports.settle(conn, delivery_uuid=mailed[0])
        assert _duty(await service.detail(conn, uuid), "org_board")["state"] == "done"


class TestTheTaskMails:
    """The task itself, on a transport that keeps what it is handed. Only the
    pool it would open its own connection from is stood in for: `reports.job`
    and `record_result` run for real, in this test's transaction."""

    @pytest.fixture
    def transport(self, monkeypatch: pytest.MonkeyPatch) -> NullEmailTransport:
        null = NullEmailTransport()
        monkeypatch.setattr("cmp.infrastructure.email.build_email_transport", lambda: null)
        monkeypatch.setattr(messaging, "load_overrides", lambda: {})
        monkeypatch.setattr(messaging, "load_copies", lambda: {})
        return null

    @pytest.fixture
    def said(self, monkeypatch: pytest.MonkeyPatch) -> list[Message]:
        """Which words were chosen, on their way to the real `deliver`."""
        keys: list[Message] = []

        def spy(key: Message, **words: Any) -> dict[str, Any]:
            keys.append(key)
            return messaging.deliver(key, **words)

        monkeypatch.setattr(mail_task, "deliver", spy)
        return keys

    @staticmethod
    async def _work(
        conn: Any, monkeypatch: pytest.MonkeyPatch, delivery: str
    ) -> tuple[Any, list[tuple[str, dict[str, Any]]]]:
        """Run the task on what `reports.job` serves, keeping what it records."""
        job = await reports.job(conn, delivery)
        recorded: list[tuple[str, dict[str, Any]]] = []
        monkeypatch.setattr(mail_task, "_claim", lambda *_: "a claim")
        monkeypatch.setattr(mail_task, "drop_claim", lambda _: None)
        monkeypatch.setattr(mail_task, "_job", lambda _: job)
        monkeypatch.setattr(
            mail_task, "_record", lambda _, status, detail: recorded.append((status, detail))
        )
        mail_task.send_breach_report.push_request(retries=0)
        try:
            return mail_task.send_breach_report.run(delivery), recorded
        finally:
            mail_task.send_breach_report.pop_request()

    async def test_the_organisations_board_gets_its_report_as_the_sender_chose(
        self,
        conn: Any,
        seeded: dict[str, Any],
        mailed: list[str],
        transport: NullEmailTransport,
        said: list[Message],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "org_board")
        [delivery] = mailed
        result, recorded = await self._work(conn, monkeypatch, delivery)
        assert result == {"delivered": True} and recorded == [("delivered", {})]
        assert said == [Message.BREACH_BOARD_REPORT]
        [sent] = transport.sent
        assert sent["to"] == "chair@example.org" and sent["cc"] == []
        assert "Report to the organisation's board" in str(sent["subject"])
        assert "has not been sent to the regulator" not in str(sent["body"])
        [pdf] = sent["attachments"]  # type: ignore[misc]
        assert pdf.content_type == "application/pdf" and pdf.data.startswith(b"%PDF")
        assert pdf.filename.endswith("-org_board-v1.pdf")

    async def test_a_regulators_report_is_told_for_information_only(
        self,
        conn: Any,
        seeded: dict[str, Any],
        mailed: list[str],
        transport: NullEmailTransport,
        said: list[Message],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "board_report")
        [delivery] = mailed
        result, _ = await self._work(conn, monkeypatch, delivery)
        assert result == {"delivered": True}
        assert said == [Message.BREACH_REPORT_FINALISED]
        [sent] = transport.sent
        assert sent["to"] == "chair@example.org"
        assert str(sent["subject"]).endswith("72-hour report to the DPDP Board finalised")
        assert "has not been sent to the regulator" in str(sent["body"])
        [pdf] = sent["attachments"]  # type: ignore[misc]
        assert pdf.data.startswith(b"%PDF")

    async def test_a_transport_that_refuses_is_recorded_failed(
        self,
        conn: Any,
        seeded: dict[str, Any],
        mailed: list[str],
        transport: NullEmailTransport,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from cmp.infrastructure.email import EmailRejected

        def refuse(**_: Any) -> dict[str, Any]:
            raise EmailRejected("the mail server refused the message")

        monkeypatch.setattr(transport, "send", refuse)
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "org_board")
        [delivery] = mailed
        result, recorded = await self._work(conn, monkeypatch, delivery)
        assert result == {"failed": "EmailRejected"}
        assert recorded == [("failed", {"error": "EmailRejected", "attempts": 1})]

    async def test_an_address_taken_off_is_recorded_failed_and_not_mailed(
        self,
        conn: Any,
        seeded: dict[str, Any],
        mailed: list[str],
        transport: NullEmailTransport,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "org_board")
        [delivery] = mailed
        await _take_off(conn, seeded, "chair@example.org")
        result, recorded = await self._work(conn, monkeypatch, delivery)
        assert result == {"failed": "RecipientRemoved"}
        assert transport.sent == []
        [(status, detail)] = recorded
        await reports.record_result(conn, delivery_uuid=delivery, status=status, detail=detail)
        doc = _latest(await reports.overview(conn, breach_uuid=uuid), "org_board")
        [row] = doc["mail"]["recipients"]
        assert (row["status"], row["error"], row["removed"]) == (
            "failed",
            "RecipientRemoved",
            True,
        )


class TestTheWorker:
    async def test_a_delivery_is_mailed_once_with_its_pdf(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        await _finalise(conn, seeded, uuid, "board_intimation")
        [delivery] = mailed
        job = await reports.job(conn, delivery)
        assert job is not None
        assert job["report_title"] == "Initial intimation to the DPDP Board"
        assert "unencrypted" in job["report_text"]
        assert job["pdf"].startswith(b"%PDF")
        assert plain(job["email"]) == "chair@example.org"
        await reports.record_result(conn, delivery_uuid=delivery, status="delivered", detail={})
        assert await reports.job(conn, delivery) is None

    async def test_a_failure_is_on_the_record_and_resending_tries_only_it(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        [first, second] = mailed
        await reports.record_result(conn, delivery_uuid=first, status="delivered", detail={})
        await reports.record_result(
            conn, delivery_uuid=second, status="failed", detail={"error": "SMTPException"}
        )
        latest = _latest(await reports.overview(conn, breach_uuid=uuid), "board_intimation")
        assert _counts(latest) == {"delivered": 1, "queued": 0, "failed": 1}
        again = await _resend(conn, seeded, uuid, doc)
        assert len(mailed) == 3
        assert _counts(again) == {"delivered": 1, "queued": 1, "failed": 0}
        [trail] = await _trail(conn, uuid, "breach.report_resent")
        assert trail["detail_json"]["retried"] == 1 and trail["detail_json"]["queued"] == 1


async def test_a_pdf_is_a_pdf_and_its_reading_is_on_the_trail(
    conn: Any, seeded: dict[str, Any], mailed: list[str], request_context: Any
) -> None:
    uuid = await _breach(conn, seeded)
    doc = await _draft(conn, seeded, uuid, "board_report")
    payload, name = await reports.pdf(
        conn, breach_uuid=uuid, report_uuid=str(doc["report_uuid"]), actor_id=_dpo(seeded)
    )
    assert payload.startswith(b"%PDF") and name.endswith("-board_report-v1.pdf")
    assert len(await _trail(conn, uuid, "breach.report_read")) == 1


async def test_a_pdf_is_rendered_off_the_event_loop(
    conn: Any, seeded: dict[str, Any], mailed: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    uuid = await _breach(conn, seeded)
    doc = await _draft(conn, seeded, uuid, "board_report")
    real = reports.render
    threads: list[threading.Thread] = []

    def spy(document: Any) -> bytes:
        threads.append(threading.current_thread())
        return real(document)

    monkeypatch.setattr(reports, "render", spy)
    await reports.pdf(
        conn, breach_uuid=uuid, report_uuid=str(doc["report_uuid"]), actor_id=_dpo(seeded)
    )
    assert len(threads) == 1 and threads[0] is not threading.current_thread()


class TestWhoItGoesTo:
    """The sender chooses, in the window: the list less any left out, never a
    mandatory one, and any address for this report alone. What was chosen is
    frozen with the version (2026-11-07)."""

    async def test_the_picks_are_who_it_goes_to_and_one_left_out_gets_nothing(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org", "member@example.org", "spare@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "board_intimation")
        sent = await _send(conn, seeded, uuid, doc, to=["chair@example.org", "member@example.org"])
        assert await _addresses(conn, mailed) == ["chair@example.org", "member@example.org"]
        assert sorted(_lines(sent)) == ["chair@example.org", "member@example.org"]

    async def test_an_address_for_this_report_alone_is_mailed_sealed_and_kept_off_the_list(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "board_intimation")
        sent = await _send(
            conn,
            seeded,
            uuid,
            doc,
            to=["chair@example.org"],
            extra=[{"full_name": " The Auditor ", "email": " Auditor@Elsewhere.org "}],
        )
        assert await _addresses(conn, mailed) == ["auditor@elsewhere.org", "chair@example.org"]
        line = _lines(sent)["auditor@elsewhere.org"]
        assert (line["added_for_this_send"], line["mandatory"], line["removed"]) == (
            True,
            False,
            False,
        )
        assert str(line["email"]).startswith("SE::") and str(line["full_name"]).startswith("SE::")
        assert plain(line["full_name"]) == "The Auditor"
        assert list(await _entries(conn)) == ["chair@example.org"], "never on the list"
        kept = await breach_settings.overview(conn)
        assert [plain(r["email"]) for r in kept["board_recipients"]] == ["chair@example.org"]
        offered = await reports.board_list(conn, breach_uuid=uuid)
        assert [plain(r["email"]) for r in offered["recipients"]] == ["chair@example.org"]

    async def test_an_extra_already_on_the_list_is_that_entry(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org", "member@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "board_intimation")
        before = await _one_offs(conn)
        sent = await _send(
            conn,
            seeded,
            uuid,
            doc,
            to=["member@example.org"],
            extra=[{"email": "CHAIR@example.org"}],
        )
        assert await _one_offs(conn) == before, "no address for one report was made"
        assert len(mailed) == 2
        lines = _lines(sent)
        assert sorted(lines) == ["chair@example.org", "member@example.org"]
        assert not any(r["added_for_this_send"] for r in lines.values())
        entry = (await _entries(conn))["chair@example.org"]
        assert str(lines["chair@example.org"]["recipient_uuid"]) == entry

    async def test_two_extras_alike_are_one(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "board_intimation")
        before = await _one_offs(conn)
        sent = await _send(
            conn,
            seeded,
            uuid,
            doc,
            to=["chair@example.org"],
            extra=[{"email": "auditor@elsewhere.org"}, {"email": "Auditor@Elsewhere.org"}],
        )
        assert await _one_offs(conn) == before + 1
        assert len(mailed) == 2 and len(sent["mail"]["recipients"]) == 2

    async def test_a_mandatory_entry_left_out_is_refused_and_nothing_is_made(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org", "member@example.org")
        await _mark(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "board_intimation")
        before = await _one_offs(conn)
        with pytest.raises(Conflict) as refused:
            await _send(
                conn,
                seeded,
                uuid,
                doc,
                to=["member@example.org"],
                extra=[{"email": "auditor@elsewhere.org"}],
            )
        assert refused.value.code == "recipient_mandatory"
        assert refused.value.details["missing"] == [(await _entries(conn))["chair@example.org"]]
        assert await _one_offs(conn) == before and mailed == []
        still = _latest(await reports.overview(conn, breach_uuid=uuid), "board_intimation")
        assert still["state"] == "draft"
        sent = await _send(conn, seeded, uuid, doc, to=None)
        assert _lines(sent)["chair@example.org"]["mandatory"] is True

    async def test_an_entry_taken_off_since_the_window_opened_is_refused(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org", "member@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "board_intimation")
        offered = await _entries(conn)
        await _take_off(conn, seeded, "member@example.org")
        with pytest.raises(Conflict) as refused:
            await reports.finalise(
                conn,
                breach_uuid=uuid,
                report_uuid=str(doc["report_uuid"]),
                recipients=list(offered.values()),
                actor_id=_dpo(seeded),
            )
        assert refused.value.code == "recipient_not_listed"
        assert refused.value.details["gone"] == [offered["member@example.org"]]
        assert mailed == []

    async def test_nothing_chosen_is_refused_on_recipients(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "board_intimation")
        with pytest.raises(ValidationFailed) as refused:
            await _send(conn, seeded, uuid, doc, to=[])
        assert refused.value.field == "recipients"

    @pytest.mark.parametrize(
        ("extra", "field"),
        [
            ({"email": "not an address"}, "extra.0.email"),
            ({"full_name": "SE::v1:abc", "email": "auditor@elsewhere.org"}, "extra.0.full_name"),
        ],
        ids=["address", "sealed name"],
    )
    async def test_an_extra_is_an_address_and_its_name_carries_no_ciphertext(
        self,
        conn: Any,
        seeded: dict[str, Any],
        mailed: list[str],
        extra: dict[str, Any],
        field: str,
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "board_intimation")
        with pytest.raises(ValidationFailed) as refused:
            await _send(conn, seeded, uuid, doc, to=["chair@example.org"], extra=[extra])
        assert refused.value.field == field

    async def test_an_empty_list_takes_an_extra_and_without_one_says_where_to_add_one(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "board_intimation")
        with pytest.raises(Conflict) as refused:
            await _send(conn, seeded, uuid, doc, to=[])
        assert refused.value.code == "no_board_recipients"
        assert "Breach settings" in refused.value.message
        sent = await _send(conn, seeded, uuid, doc, to=[], extra=[{"email": "a@elsewhere.org"}])
        assert await _addresses(conn, mailed) == ["a@elsewhere.org"]
        assert sent["state"] == "finalised"

    async def test_the_trail_counts_what_was_chosen_and_names_nobody(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org", "member@example.org", "spare@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "board_intimation")
        await _send(
            conn,
            seeded,
            uuid,
            doc,
            to=["chair@example.org"],
            extra=[{"full_name": "The Auditor", "email": "auditor@elsewhere.org"}],
        )
        [trail] = await _trail(conn, uuid, "breach.report_finalised")
        detail = trail["detail_json"]
        assert {k: detail[k] for k in ("mailed", "held", "added", "left_out")} == {
            "mailed": 2,
            "held": False,
            "added": 1,
            "left_out": 2,
        }
        assert "example.org" not in str(detail) and "elsewhere" not in str(detail)
        assert "Auditor" not in str(detail)

    async def test_a_versions_lines_stay_as_they_were_when_the_list_changes(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org", "member@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "board_intimation")
        await _send(conn, seeded, uuid, doc, to=None)
        await _board(conn, seeded, "late@example.org")
        await _mark(conn, seeded, "chair@example.org")
        await _take_off(conn, seeded, "member@example.org")
        lines = _lines(_latest(await reports.overview(conn, breach_uuid=uuid), "board_intimation"))
        assert sorted(lines) == ["chair@example.org", "member@example.org"]
        assert lines["chair@example.org"]["mandatory"] is False, "as it was when it went"
        assert lines["member@example.org"]["removed"] is True


class TestTryAgainTriesTheReportsOwn:
    async def test_an_address_added_since_is_not_tried(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        await _not_reached(conn, *mailed)
        await _board(conn, seeded, "member@example.org")
        mailed.clear()
        again = await _resend(conn, seeded, uuid, doc)
        assert await _addresses(conn, mailed) == ["chair@example.org"]
        assert sorted(_lines(again)) == ["chair@example.org"]

    async def test_one_for_this_report_alone_is_tried_and_never_taken_off(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "board_intimation")
        await _send(conn, seeded, uuid, doc, to=[], extra=[{"email": "auditor@elsewhere.org"}])
        await _not_reached(conn, *mailed)
        mailed.clear()
        again = await _resend(conn, seeded, uuid, doc)
        assert await _addresses(conn, mailed) == ["auditor@elsewhere.org"]
        assert _lines(again)["auditor@elsewhere.org"]["attempt"] == 2

    async def test_a_version_withheld_at_the_yes_is_sent_once_marked_again(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _incident(conn, seeded)
        doc = await _cert_in_draft(conn, seeded, uuid)
        await _send(conn, seeded, uuid, doc, to=None)
        await _set_aside_after_a_no(conn, seeded, uuid)
        await _determine(conn, seeded, uuid, "yes")
        assert mailed == []
        withheld = _latest(await reports.overview(conn, breach_uuid=uuid), "cert_in")
        assert [r["status"] for r in withheld["mail"]["recipients"]] == ["unsent"]
        assert withheld["mail"]["retryable"] == 0, "not while it is set aside"
        await service.mark_cert_in(conn, breach_uuid=uuid, actor_id=_dpo(seeded))
        marked = _latest(await reports.overview(conn, breach_uuid=uuid), "cert_in")
        assert marked["mail"]["unsent"] == 1 and marked["mail"]["retryable"] == 1
        assert mailed == [], "marking it again sends nothing by itself"
        again = await _resend(conn, seeded, uuid, doc)
        assert await _addresses(conn, mailed) == ["chair@example.org"]
        assert _lines(again)["chair@example.org"]["attempt"] == 1
        [trail] = await _trail(conn, uuid, "breach.report_resent")
        assert (trail["detail_json"]["first"], trail["detail_json"]["queued"]) == (1, 1)


class TestACertInReportBeforeAYes:
    """Decision 6 of 2026-11-07: finalised before the incident is validated as a
    personal data breach, its mail to the board waits for the first yes, and
    goes then to whom it was chosen for. Never, if no yes comes."""

    async def test_finalised_before_validation_nothing_is_queued(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _incident(conn, seeded)
        doc = await _cert_in_draft(conn, seeded, uuid)
        assert _kind(await reports.overview(conn, breach_uuid=uuid), "cert_in")["holds_mail"]
        held = await _send(conn, seeded, uuid, doc, to=None)
        assert mailed == [] and await _queued(conn, uuid) == []
        mail = held["mail"]
        assert (mail["held"], mail["queued"], mail["retryable"]) == (2, 0, 0)
        assert {(r["status"], r["attempt"], r["recorded_at"]) for r in mail["recipients"]} == {
            ("held", 0, None)
        }
        with pytest.raises(Conflict) as refused:
            await _resend(conn, seeded, uuid, doc)
        assert refused.value.code == "report_held"
        [trail] = await _trail(conn, uuid, "breach.report_finalised")
        assert (trail["detail_json"]["held"], trail["detail_json"]["mailed"]) == (True, 0)

    async def test_the_first_yes_sends_it_to_whom_it_was_chosen_for(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org", "member@example.org", "spare@example.org")
        uuid = await _incident(conn, seeded)
        doc = await _cert_in_draft(conn, seeded, uuid)
        await _send(
            conn,
            seeded,
            uuid,
            doc,
            to=["chair@example.org", "member@example.org"],
            extra=[{"email": "auditor@elsewhere.org"}],
        )
        await _board(conn, seeded, "late@example.org")
        await _mark(conn, seeded, "spare@example.org")
        await _determine(conn, seeded, uuid, "yes")
        assert await _addresses(conn, mailed) == [
            "auditor@elsewhere.org",
            "chair@example.org",
            "member@example.org",
        ]
        [trail] = await _trail(conn, uuid, "breach.report_released")
        assert trail["actor_user_id"] == _dpo(seeded)
        detail = trail["detail_json"]
        assert {k: detail[k] for k in ("kind", "version", "queued", "left_out")} == {
            "kind": "cert_in",
            "version": 1,
            "queued": 3,
            "left_out": 0,
        }
        assert str(detail["reference"]).startswith("BR-")
        assert "example.org" not in str(detail) and "elsewhere" not in str(detail)
        view = _kind(await reports.overview(conn, breach_uuid=uuid), "cert_in")
        assert view["holds_mail"] is False
        assert {r["status"] for r in view["versions"][0]["mail"]["recipients"]} == {"queued"}

    async def test_an_older_held_version_never_goes_and_reads_superseded(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _incident(conn, seeded)
        first = await _cert_in_draft(conn, seeded, uuid)
        await _send(conn, seeded, uuid, first, to=None)
        second = await _draft(conn, seeded, uuid, "cert_in")
        await _send(conn, seeded, uuid, second, to=None)
        await _determine(conn, seeded, uuid, "yes")
        assert len(mailed) == 1
        job = await reports.job(conn, mailed[0])
        assert job is not None and job["file_name"].endswith("-cert_in-v2.pdf")
        [newest, older] = _kind(await reports.overview(conn, breach_uuid=uuid), "cert_in")[
            "versions"
        ]
        assert (newest["superseded"], older["superseded"]) == (False, True)
        assert [r["status"] for r in older["mail"]["recipients"]] == ["unsent"]
        assert older["mail"]["retryable"] == 0
        with pytest.raises(Conflict) as refused:
            await _resend(conn, seeded, uuid, first)
        assert refused.value.code == "report_superseded"

    async def test_a_no_keeps_it_held_and_a_later_yes_sends_it(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _incident(conn, seeded)
        doc = await _cert_in_draft(conn, seeded, uuid)
        await _send(conn, seeded, uuid, doc, to=None)
        await _determine(conn, seeded, uuid, "no")
        assert mailed == []
        read = _latest(await reports.overview(conn, breach_uuid=uuid), "cert_in")
        assert read["mail"]["held"] == 2, "a no issues no reference, so the yes is still to come"
        await _determine(conn, seeded, uuid, "yes")
        assert len(mailed) == 2
        assert len(await _trail(conn, uuid, "breach.report_released")) == 1

    async def test_set_aside_at_the_yes_it_is_withheld_and_says_so(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _incident(conn, seeded)
        doc = await _cert_in_draft(conn, seeded, uuid)
        await _send(conn, seeded, uuid, doc, to=None)
        await _set_aside_after_a_no(conn, seeded, uuid)
        await _determine(conn, seeded, uuid, "yes")
        assert mailed == []
        [trail] = await _trail(conn, uuid, "breach.report_withheld")
        assert trail["actor_user_id"] == _dpo(seeded)
        assert {k: trail["detail_json"][k] for k in ("kind", "version", "why")} == {
            "kind": "cert_in",
            "version": 1,
            "why": "cert_in_set_aside",
        }
        assert await _trail(conn, uuid, "breach.report_released") == []
        read = _latest(await reports.overview(conn, breach_uuid=uuid), "cert_in")
        assert read["mail"]["unsent"] == 2 and read["mail"]["held"] == 0
        with pytest.raises(Conflict) as refused:
            await _resend(conn, seeded, uuid, doc)
        assert refused.value.code == "breach_not_recorded"

    async def test_marked_again_after_the_yes_a_later_yes_does_not_send_it(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        """What the first yes withheld a person sends, with Try again: by then
        the office may be writing a new version, and two would reach the board."""
        await _board(conn, seeded)
        uuid = await _incident(conn, seeded)
        doc = await _cert_in_draft(conn, seeded, uuid)
        await _send(conn, seeded, uuid, doc, to=None)
        await _set_aside_after_a_no(conn, seeded, uuid)
        await _determine(conn, seeded, uuid, "yes")
        await service.mark_cert_in(conn, breach_uuid=uuid, actor_id=_dpo(seeded))
        await _determine(conn, seeded, uuid, "yes")
        assert mailed == []
        read = _latest(await reports.overview(conn, breach_uuid=uuid), "cert_in")
        assert read["mail"]["unsent"] == 2 and read["mail"]["retryable"] == 2

    async def test_set_aside_and_marked_again_before_the_yes_it_goes_at_the_yes(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _incident(conn, seeded)
        doc = await _cert_in_draft(conn, seeded, uuid)
        await _send(conn, seeded, uuid, doc, to=None)
        await _set_aside_after_a_no(conn, seeded, uuid)
        await service.mark_cert_in(conn, breach_uuid=uuid, actor_id=_dpo(seeded))
        assert mailed == []
        await _determine(conn, seeded, uuid, "yes")
        assert len(mailed) == 2

    async def test_a_held_report_may_be_filed_and_still_goes_at_the_yes(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _incident(conn, seeded)
        doc = await _cert_in_draft(conn, seeded, uuid)
        held = await _send(conn, seeded, uuid, doc, to=None)
        for proof in ("approval", "sent_mail"):
            await _proof(conn, seeded, uuid, held, proof)
        await _file(conn, seeded, uuid, held, reference="CERT/1")
        assert _duty(await service.detail(conn, uuid), "cert_in")["state"] == "done"
        assert mailed == []
        await _determine(conn, seeded, uuid, "yes")
        assert len(mailed) == 2

    async def test_an_address_taken_off_before_the_yes_is_left_out(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _incident(conn, seeded)
        doc = await _cert_in_draft(conn, seeded, uuid)
        await _send(conn, seeded, uuid, doc, to=None)
        await _take_off(conn, seeded, "member@example.org")
        await _determine(conn, seeded, uuid, "yes")
        assert await _addresses(conn, mailed) == ["chair@example.org"]
        [trail] = await _trail(conn, uuid, "breach.report_released")
        assert (trail["detail_json"]["queued"], trail["detail_json"]["left_out"]) == (1, 1)

    async def test_a_second_yes_releases_nothing_and_the_release_runs_once(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _incident(conn, seeded)
        doc = await _cert_in_draft(conn, seeded, uuid)
        await _send(conn, seeded, uuid, doc, to=None)
        await _determine(conn, seeded, uuid, "yes")
        await _not_reached(conn, *mailed)
        mailed.clear()
        await _determine(conn, seeded, uuid, "yes")
        breach = await service.require(conn, uuid)
        await reports.after_yes(conn, breach, first=True, actor_id=_dpo(seeded))
        assert mailed == []
        assert len(await _trail(conn, uuid, "breach.report_released")) == 1

    async def test_a_finalise_that_waited_behind_a_first_yes_mails_at_once(
        self,
        conn: Any,
        seeded: dict[str, Any],
        mailed: list[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Two people at once: the yes holds the breach's row, and the finalise
        read the breach before it waited for it. Read again once it holds the
        row, it finds the reference the yes issued. Read only before, it would
        hold a mail for a yes that had come and gone, and nothing would send it."""
        await _board(conn, seeded)
        uuid = await _incident(conn, seeded)
        doc = await _cert_in_draft(conn, seeded, uuid)
        lock = breach_repo.lock
        waited = False

        async def behind_a_yes(c: Any, breach_id: int) -> Any:
            nonlocal waited
            if not waited:
                waited = True
                await _determine(conn, seeded, uuid, "yes")
            return await lock(c, breach_id)

        monkeypatch.setattr(breach_repo, "lock", behind_a_yes)
        sent = await _send(conn, seeded, uuid, doc, to=None)
        assert waited and len(mailed) == 2
        assert sent["mail"]["queued"] == 2
        assert await _trail(conn, uuid, "breach.report_released") == [], "nothing was held"


class TestTheDatabaseHoldsTheRule:
    """Raw SQL, past the service."""

    async def test_a_finalised_reports_words_do_not_change(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        with pytest.raises(psycopg.errors.RestrictViolation):
            await conn.execute(
                """UPDATE breach_report_section SET body = 'x' WHERE report_id =
                   (SELECT report_id FROM breach_report WHERE report_uuid = %s)""",
                (str(doc["report_uuid"]),),
            )

    async def test_a_finalised_report_gains_no_section(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        with pytest.raises(psycopg.errors.RestrictViolation):
            await conn.execute(
                """INSERT INTO breach_report_section (report_id, ordinal, section_key, body)
                   SELECT report_id, 99, 'late_words', 'x' FROM breach_report
                    WHERE report_uuid = %s""",
                (str(doc["report_uuid"]),),
            )

    async def test_a_draft_still_takes_a_section(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "closure")
        await conn.execute(
            """INSERT INTO breach_report_section (report_id, ordinal, section_key, body)
               SELECT report_id, 99, 'late_words', 'x' FROM breach_report
                WHERE report_uuid = %s""",
            (str(doc["report_uuid"]),),
        )

    async def test_a_section_is_never_deleted(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "closure")
        with pytest.raises(psycopg.errors.RestrictViolation):
            await conn.execute(
                """DELETE FROM breach_report_section WHERE report_id =
                   (SELECT report_id FROM breach_report WHERE report_uuid = %s)""",
                (str(doc["report_uuid"]),),
            )

    async def test_a_report_is_never_deleted(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "closure")
        with pytest.raises(psycopg.errors.RestrictViolation):
            await conn.execute(
                "DELETE FROM breach_report WHERE report_uuid = %s", (str(doc["report_uuid"]),)
            )

    async def test_finalising_is_not_undone(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        with pytest.raises(psycopg.errors.RestrictViolation):
            await conn.execute(
                """UPDATE breach_report SET finalised_at = NULL, finalised_by = NULL
                    WHERE report_uuid = %s""",
                (str(doc["report_uuid"]),),
            )

    async def test_a_filed_report_does_not_change(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        for proof in ("approval", "sent_mail"):
            await _proof(conn, seeded, uuid, doc, proof)
        await _file(conn, seeded, uuid, doc)
        with pytest.raises(psycopg.errors.RestrictViolation):
            await conn.execute(
                "UPDATE breach_report SET filed_reference = 'DPB/2' WHERE report_uuid = %s",
                (str(doc["report_uuid"]),),
            )

    @pytest.mark.parametrize(
        "statement",
        [
            "UPDATE breach_report_delivery SET status = 'delivered' WHERE report_id = "
            "(SELECT report_id FROM breach_report WHERE report_uuid = %s)",
            "DELETE FROM breach_report_delivery WHERE report_id = "
            "(SELECT report_id FROM breach_report WHERE report_uuid = %s)",
        ],
        ids=["update", "delete"],
    )
    async def test_the_account_of_the_mail_is_only_added_to(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str], statement: str
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            await conn.execute(statement, (str(doc["report_uuid"]),))

    async def test_the_report_to_the_organisations_board_is_never_filed(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded)
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "org_board")
        with pytest.raises(psycopg.errors.CheckViolation):
            await conn.execute(
                """UPDATE breach_report
                      SET filed_at = now(), filed_by = %s, filed_recorded_at = now()
                    WHERE report_uuid = %s""",
                (_dpo(seeded), str(doc["report_uuid"])),
            )

    async def test_one_draft_of_a_kind(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _breach(conn, seeded)
        await _draft(conn, seeded, uuid, "closure")
        with pytest.raises(psycopg.errors.UniqueViolation):
            await conn.execute(
                """INSERT INTO breach_report (breach_id, kind, version, created_by)
                   SELECT breach_id, 'closure', 2, %s FROM breach WHERE breach_uuid = %s""",
                (_dpo(seeded), uuid),
            )

    async def test_only_a_proof_names_a_report(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "closure")
        with pytest.raises(psycopg.errors.CheckViolation):
            await conn.execute(
                """INSERT INTO breach_attachment (breach_id, kind, file_name, storage_ref, sha256,
                                                  size_bytes, content_type, added_by, report_id)
                   SELECT breach_id, 'email', 'x', 'x', %s, 1, 'x', %s,
                          (SELECT report_id FROM breach_report WHERE report_uuid = %s)
                     FROM breach WHERE breach_uuid = %s""",
                ("a" * 64, _dpo(seeded), str(doc["report_uuid"]), uuid),
            )

    async def test_a_proof_names_its_report(self, conn: Any, seeded: dict[str, Any]) -> None:
        uuid = await _breach(conn, seeded)
        with pytest.raises(psycopg.errors.CheckViolation):
            await conn.execute(
                """INSERT INTO breach_attachment (breach_id, kind, file_name, storage_ref, sha256,
                                                  size_bytes, content_type, added_by)
                   SELECT breach_id, 'approval', 'x', 'x', %s, 1, 'x', %s FROM breach
                    WHERE breach_uuid = %s""",
                ("a" * 64, _dpo(seeded), uuid),
            )

    async def test_a_finalised_report_takes_no_new_addressee(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        await _board(conn, seeded, "late@example.org")
        with pytest.raises(psycopg.errors.RestrictViolation):
            await conn.execute(
                """INSERT INTO breach_report_addressee (report_id, recipient_id)
                   SELECT r.report_id, x.recipient_id
                     FROM breach_report r, breach_board_recipient x
                    WHERE r.report_uuid = %s AND x.recipient_uuid = %s""",
                (str(doc["report_uuid"]), (await _entries(conn))["late@example.org"]),
            )

    @pytest.mark.parametrize(
        "statement",
        [
            "UPDATE breach_report_addressee SET mandatory = true WHERE report_id = "
            "(SELECT report_id FROM breach_report WHERE report_uuid = %s)",
            "DELETE FROM breach_report_addressee WHERE report_id = "
            "(SELECT report_id FROM breach_report WHERE report_uuid = %s)",
        ],
        ids=["update", "delete"],
    )
    async def test_who_a_version_went_to_is_only_added_to(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str], statement: str
    ) -> None:
        await _board(conn, seeded, "chair@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _finalise(conn, seeded, uuid, "board_intimation")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            await conn.execute(statement, (str(doc["report_uuid"]),))

    async def test_a_delivery_goes_only_to_an_address_the_report_went_to(
        self, conn: Any, seeded: dict[str, Any], mailed: list[str]
    ) -> None:
        await _board(conn, seeded, "chair@example.org", "spare@example.org")
        uuid = await _breach(conn, seeded)
        doc = await _draft(conn, seeded, uuid, "board_intimation")
        await _send(conn, seeded, uuid, doc, to=["chair@example.org"])
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            await conn.execute(
                """INSERT INTO breach_report_delivery (report_id, recipient_id, attempt, status)
                   SELECT r.report_id, x.recipient_id, 1, 'queued'
                     FROM breach_report r, breach_board_recipient x
                    WHERE r.report_uuid = %s AND x.recipient_uuid = %s""",
                (str(doc["report_uuid"]), (await _entries(conn))["spare@example.org"]),
            )
