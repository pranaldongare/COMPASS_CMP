"""An incident reported through the public link (0058, ADR 0037).

Anybody may report, once they have proved their email. What arrives waits in
the shared intake with its INC number and starts nothing: both officers see it
until one claims it, which logs the incident under that number in that office,
or dismisses it with a reason.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
import pytest

from cmp.api.routers.v1 import dashboard
from cmp.auth.authentication import otp
from cmp.auth.rate_limit import service as ratelimit
from cmp.core.errors import (
    BadRequest,
    Conflict,
    NotFound,
    ServiceUnavailable,
    ValidationFailed,
)
from cmp.db.repositories import incident_reports as reports_repo
from cmp.db.sql import execute, fetch_one
from cmp.domain import alerts
from cmp.domain.breach import intake, service
from cmp.domain.breach import settings as breach_settings
from cmp.tasks import dispatch as dispatch_mod
from cmp.tasks.notifications.incident_reports import send_incident_report_code
from tests.conftest import plain
from tests.integration.hr_world import staff

pytestmark = pytest.mark.integration

EMAIL = "reporter@example.org"


def _dpo(seeded: dict[str, Any]) -> int:
    return int(seeded["users"]["dpo"]["id"])


async def _issued(email: str = EMAIL) -> Any:
    return await otp.issue(otp.Scope.INCIDENT_REPORT, ratelimit.contact_key(email))


async def _report(conn: Any, *, email: str = EMAIL, **over: Any) -> dict[str, Any]:
    issued = await _issued(email)
    fields: dict[str, Any] = {
        "reporter_name": "Asha Rao",
        "email": email,
        "code": issued.code,
        "title": "A laptop left on a train",
        "noticed_at": None,
        "told": {"incident_details": "It had the participant list on it"},
        "cyber_attack": None,
        "ip_address": None,
    }
    return await intake.submit(conn, **{**fields, **over})


async def _email_of(conn: Any, user_id: int) -> str:
    row = await fetch_one(conn, "SELECT email FROM auth_user WHERE id = %s", (user_id,))
    assert row is not None
    return str(plain(row["email"]))


async def _last_page(conn: Any) -> list[dict[str, Any]]:
    """Where a report just made sits, oldest first, whatever else this database
    has waiting."""
    total = await intake.waiting_count(conn)
    most = intake.WAITING_MOST
    page: list[dict[str, Any]] = (
        await intake.waiting(conn, limit=most, offset=max(0, total - most))
    )["items"]
    return page


async def _waiting(conn: Any, reference: str) -> dict[str, Any]:
    [found] = [r for r in await _last_page(conn) if r["reference"] == reference]
    return found


async def test_a_report_takes_its_number_and_waits_on_no_clock(
    conn: Any, request_context: Any
) -> None:
    made = await _report(conn)
    assert made["reference"].startswith("INC-")
    assert made["reference"] in made["message"]
    waiting = await _waiting(conn, made["reference"])
    assert plain(waiting["title"]) == "A laptop left on a train"
    assert plain(waiting["reporter_email"]) == EMAIL
    row = await fetch_one(
        conn,
        "SELECT reporter_email, title, incident_details FROM incident_report WHERE reference = %s",
        (made["reference"],),
    )
    assert row is not None and all(str(v).startswith("SE::") for v in row.values()), "sealed"


class TestTheListIsAPage:
    """A stranger can write eighty thousand characters twenty times an hour. The
    list has to stay small enough to read and to open while they do."""

    async def test_it_carries_who_and_what_and_none_of_the_long_text(
        self, conn: Any, request_context: Any
    ) -> None:
        made = await _report(conn)
        row = await _waiting(conn, made["reference"])
        assert set(row) == {
            "report_uuid",
            "reference",
            "reporter_name",
            "reporter_email",
            "title",
            "noticed_at",
            "received_at",
            "cyber_attack",
        }

    async def test_it_serves_a_page_and_says_how_many_there_are(
        self, conn: Any, request_context: Any
    ) -> None:
        before = await intake.waiting_count(conn)
        for n in range(3):
            await _report(conn, email=f"page.{n}@example.org")
        page = await intake.waiting(conn, limit=2, offset=before)
        assert page["total"] == before + 3
        assert (page["limit"], page["offset"]) == (2, before)
        assert len(page["items"]) == 2
        rest = await intake.waiting(conn, limit=2, offset=before + 2)
        assert len(rest["items"]) == 1

    async def test_a_page_is_fifty_unless_more_is_asked_for(self, conn: Any) -> None:
        assert (await intake.waiting(conn))["limit"] == intake.WAITING_SHOWN == 50
        assert intake.WAITING_MOST == 200

    async def test_the_oldest_comes_first(self, conn: Any, request_context: Any) -> None:
        before = await intake.waiting_count(conn)
        first = await _report(conn, email="first@example.org")
        second = await _report(conn, email="second@example.org")
        page = await intake.waiting(conn, limit=2, offset=before)
        assert [r["reference"] for r in page["items"]] == [first["reference"], second["reference"]]

    async def test_one_report_opens_in_full_and_sealed(
        self, conn: Any, request_context: Any
    ) -> None:
        made = await _report(conn)
        waiting = await _waiting(conn, made["reference"])
        full = await intake.read(conn, report_uuid=str(waiting["report_uuid"]))
        assert full["reference"] == made["reference"]
        told = full["logged"]["incident_details"]
        assert str(told).startswith("SE::")
        assert plain(told) == "It had the participant list on it"

    async def test_one_no_longer_waiting_answers_as_a_claim_does(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        claimed = await _report(conn)
        report = str((await _waiting(conn, claimed["reference"]))["report_uuid"])
        await intake.claim(conn, report_uuid=report, office="rnd", actor_id=_dpo(seeded))
        with pytest.raises(Conflict) as refused:
            await intake.read(conn, report_uuid=report)
        assert refused.value.code == "already_claimed"

        dismissed = await _report(conn, email="another@example.org")
        report = str((await _waiting(conn, dismissed["reference"]))["report_uuid"])
        await intake.dismiss(conn, report_uuid=report, reason="Not ours", actor_id=_dpo(seeded))
        with pytest.raises(Conflict) as refused:
            await intake.read(conn, report_uuid=report)
        assert refused.value.code == "already_dismissed"

    async def test_one_that_never_was_is_not_found(self, conn: Any) -> None:
        with pytest.raises(NotFound):
            await intake.read(conn, report_uuid="00000000-0000-4000-8000-000000000000")


async def test_no_report_without_the_code_to_the_address_given(
    conn: Any, request_context: Any
) -> None:
    with pytest.raises(BadRequest):
        await _report(conn, code="000000")
    issued = await _issued("someone.else@example.org")
    with pytest.raises(BadRequest):
        await _report(conn, code=issued.code)


async def test_a_code_works_once(conn: Any, request_context: Any) -> None:
    issued = await _issued()
    await _report_with(conn, issued.code)
    with pytest.raises(BadRequest):
        await _report_with(conn, issued.code)


async def _report_with(conn: Any, code: str, *, email: str = EMAIL) -> dict[str, Any]:
    return await intake.submit(
        conn,
        reporter_name="Asha Rao",
        email=email,
        code=code,
        title="Once",
        noticed_at=None,
        told={"incident_details": "Once"},
        cyber_attack=None,
        ip_address=None,
    )


@pytest.mark.parametrize(
    ("over", "field"),
    [
        ({"reporter_name": " "}, "name"),
        ({"title": " "}, "title"),
        ({"told": {"incident_details": " "}}, "incident_details"),
        ({"noticed_at": datetime.now(UTC) + timedelta(days=1)}, "noticed_at"),
    ],
)
async def test_a_report_says_who_and_what(
    conn: Any, request_context: Any, over: dict[str, Any], field: str
) -> None:
    with pytest.raises(ValidationFailed) as refused:
        await _report(conn, **over)
    assert refused.value.field == field


async def test_a_time_before_there_could_be_one_leaves_the_intake_readable(
    conn: Any, request_context: Any
) -> None:
    """Year 1 with a positive offset is before year 1 in UTC: stored, it stopped
    the intake opening for both offices, for good."""
    with pytest.raises(ValidationFailed) as refused:
        await _report(conn, noticed_at=datetime.fromisoformat("0001-01-01T00:00:00+14:00"))
    assert refused.value.field == "noticed_at"
    await reports_repo.waiting(conn, limit=intake.WAITING_MOST, offset=0)
    made = await _report(conn, noticed_at=datetime(1970, 1, 1, tzinfo=UTC))
    assert (await _waiting(conn, made["reference"]))["noticed_at"].year == 1970


@pytest.mark.parametrize(
    ("over", "field"),
    [
        ({"reporter_name": "SE::abcd"}, "name"),
        ({"title": "Words then SE::abcd"}, "title"),
        ({"told": {"incident_details": "SE::abcd"}}, "incident_details"),
        ({"told": {"incident_details": "It left", "third_parties": "SE::abcd"}}, "third_parties"),
    ],
)
async def test_a_sealed_value_is_refused_in_whatever_a_reporter_writes(
    conn: Any, request_context: Any, over: dict[str, Any], field: str
) -> None:
    """A message opens every sealed value it carries: a ciphertext typed as a
    name would be mailed back to whoever typed it, opened."""
    with pytest.raises(ValidationFailed) as refused:
        await _report(conn, **over)
    assert refused.value.field == field


async def test_a_code_that_cannot_be_queued_is_said_to_have_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def down(*args: Any, **kwargs: Any) -> None:
        raise ConnectionError("no broker")

    monkeypatch.setattr(send_incident_report_code, "apply_async", down)
    with pytest.raises(ServiceUnavailable):
        await intake.send_code(email=f"{uuid.uuid4().hex}@example.org", ip_address=None)


async def test_redis_keeps_the_code_under_no_address(
    conn: Any, request_context: Any, redis_conn: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[tuple[Any, ...]] = []

    def capture(task: Any, *args: Any) -> str:
        sent.append(args)
        return "queued-in-a-test"

    monkeypatch.setattr(dispatch_mod, "dispatch_required", capture)
    email = f"{uuid.uuid4().hex}@example.org"
    await intake.send_code(email=email, ip_address=None)
    keys = [str(k) async for k in redis_conn.scan_iter(match="*incident_report*")]
    assert keys and not any(email in k for k in keys)
    [(_, code)] = sent
    assert (await _report_with(conn, code, email=email))["reference"].startswith("INC-")


async def test_a_report_the_key_service_could_not_take_keeps_its_code(
    conn: Any, request_context: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    issued = await _issued()
    written = reports_repo.create

    async def down(*args: Any, **kwargs: Any) -> None:
        raise ServiceUnavailable("The key service is not answering")

    monkeypatch.setattr(reports_repo, "create", down)
    with pytest.raises(ServiceUnavailable):
        await _report_with(conn, issued.code)
    monkeypatch.setattr(reports_repo, "create", written)
    assert (await _report_with(conn, issued.code))["reference"].startswith("INC-")


async def test_of_two_reports_racing_with_one_code_the_later_is_refused(
    conn: Any, request_context: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both pass the first check, which spends nothing. The code is spent at
    the end, atomically, and refusing there rolls the second report back."""
    issued = await _issued()
    written = reports_repo.create

    async def beaten_to_it(*args: Any, **kwargs: Any) -> Any:
        made = await written(*args, **kwargs)
        key = ratelimit.contact_key(EMAIL)
        assert await otp.verify(otp.Scope.INCIDENT_REPORT, key, issued.code)
        return made

    monkeypatch.setattr(reports_repo, "create", beaten_to_it)
    with pytest.raises(BadRequest):
        await _report_with(conn, issued.code)


async def test_claiming_logs_the_incident_under_the_number_it_arrived_with(
    conn: Any, seeded: dict[str, Any], request_context: Any
) -> None:
    made = await _report(conn)
    waiting = await _waiting(conn, made["reference"])
    detail = await intake.claim(
        conn, report_uuid=str(waiting["report_uuid"]), office="rnd", actor_id=_dpo(seeded)
    )
    assert detail["incident_reference"] == made["reference"]
    assert detail["breach_reference"] is None
    assert plain(detail["title"]) == "A laptop left on a train"
    assert plain(detail["logged"]["incident_details"]) == "It had the participant list on it"
    assert plain(detail["reported"]["reporter_email"]) == EMAIL
    assert detail["obligations"] == [], "no clock until validation"
    assert made["reference"] not in {r["reference"] for r in await _last_page(conn)}


async def test_claiming_takes_the_time_it_arrived_as_first_noticed(
    conn: Any, seeded: dict[str, Any], request_context: Any
) -> None:
    long_ago = datetime.now(UTC) - timedelta(days=30)
    made = await _report(conn, noticed_at=long_ago)
    waiting = await _waiting(conn, made["reference"])
    detail = await intake.claim(
        conn, report_uuid=str(waiting["report_uuid"]), office="rnd", actor_id=_dpo(seeded)
    )
    assert detail["detected_at"] == waiting["received_at"]
    assert detail["reported"]["noticed_at"] == long_ago, "kept, and it anchors nothing"


async def test_a_strangers_yes_starts_no_cert_in_duty(
    conn: Any, seeded: dict[str, Any], request_context: Any
) -> None:
    made = await _report(conn, cyber_attack="yes")
    waiting = await _waiting(conn, made["reference"])
    detail = await intake.claim(
        conn, report_uuid=str(waiting["report_uuid"]), office="rnd", actor_id=_dpo(seeded)
    )
    assert detail["obligations"] == []
    assert detail["reported"]["cyber_attack"] == "yes", "the officer reads it and decides"
    marked = await service.mark_cert_in(
        conn, breach_uuid=str(detail["breach_uuid"]), actor_id=_dpo(seeded)
    )
    assert [d["duty"] for d in marked["obligations"]] == ["cert_in"]


async def test_one_outcome_for_a_report(
    conn: Any, seeded: dict[str, Any], request_context: Any
) -> None:
    made = await _report(conn)
    report = str((await _waiting(conn, made["reference"]))["report_uuid"])
    await intake.dismiss(conn, report_uuid=report, reason="Not ours", actor_id=_dpo(seeded))
    with pytest.raises(Conflict) as again:
        await intake.claim(conn, report_uuid=report, office="rnd", actor_id=_dpo(seeded))
    assert again.value.code == "already_dismissed"

    made = await _report(conn)
    report = str((await _waiting(conn, made["reference"]))["report_uuid"])
    await intake.claim(conn, report_uuid=report, office="rnd", actor_id=_dpo(seeded))
    with pytest.raises(Conflict) as claimed:
        await intake.claim(conn, report_uuid=report, office="hr", actor_id=_dpo(seeded))
    assert claimed.value.code == "already_claimed"
    # It may have been a colleague in the same office: it does not say whose.
    assert claimed.value.message == "It has already been claimed"


async def test_a_dismissal_says_why_and_keeps_the_report(
    conn: Any, seeded: dict[str, Any], request_context: Any
) -> None:
    made = await _report(conn)
    report = str((await _waiting(conn, made["reference"]))["report_uuid"])
    with pytest.raises(ValidationFailed):
        await intake.dismiss(conn, report_uuid=report, reason=" ", actor_id=_dpo(seeded))
    await intake.dismiss(conn, report_uuid=report, reason="A test", actor_id=_dpo(seeded))
    row = await fetch_one(
        conn, "SELECT dismissal_reason FROM incident_report WHERE report_uuid = %s", (report,)
    )
    assert row is not None and str(row["dismissal_reason"]).startswith("SE::")
    assert report not in {str(r["report_uuid"]) for r in await _last_page(conn)}


async def test_what_was_dismissed_can_be_read_with_who_did_it_and_why(
    conn: Any, seeded: dict[str, Any], request_context: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = await _report(conn)
    second = await _report(conn, title="Junk")
    for made, reason in ((first, "Not ours"), (second, "A test")):
        report = str((await _waiting(conn, made["reference"]))["report_uuid"])
        await intake.dismiss(conn, report_uuid=report, reason=reason, actor_id=_dpo(seeded))
    still = await _report(conn)

    rows = await intake.dismissed(conn)
    assert [r["reference"] for r in rows[:2]] == [second["reference"], first["reference"]]
    assert still["reference"] not in {r["reference"] for r in rows}
    newest = rows[0]
    assert str(newest["dismissal_reason"]).startswith("SE::"), "sealed"
    assert plain(newest["dismissal_reason"]) == "A test"
    assert plain(newest["title"]) == "Junk"
    assert plain(newest["reporter_name"]) == "Asha Rao"
    assert plain(newest["reporter_email"]) == EMAIL
    assert plain(newest["dismissed_by_name"])
    assert newest["received_at"] and newest["dismissed_at"]

    monkeypatch.setattr(intake, "DISMISSED_SHOWN", 1)
    assert [r["reference"] for r in await intake.dismissed(conn)] == [second["reference"]]


async def test_an_unknown_report_is_not_there(conn: Any, seeded: dict[str, Any]) -> None:
    with pytest.raises(NotFound):
        await intake.claim(
            conn,
            report_uuid="00000000-0000-4000-8000-000000000000",
            office="rnd",
            actor_id=_dpo(seeded),
        )


@pytest.mark.parametrize(
    ("role", "read"),
    [("dpo", dashboard._dpo), ("legal", dashboard._legal)],
    ids=["dpo", "legal"],
)
async def test_a_waiting_report_is_on_both_officers_dashboards(
    conn: Any, seeded: dict[str, Any], request_context: Any, role: str, read: Any
) -> None:
    before = (await read(conn))["counts"]["incident_reports_waiting"]
    made = await _report(conn)
    after = await read(conn)
    assert after["counts"]["incident_reports_waiting"] == before + 1
    rows = {r["key"] for r in dashboard._attention(role, after["counts"], after["queues"])}
    assert "incident_reports_waiting" in rows
    report = str((await _waiting(conn, made["reference"]))["report_uuid"])
    await intake.dismiss(conn, report_uuid=report, reason="A test", actor_id=_dpo(seeded))
    assert (await read(conn))["counts"]["incident_reports_waiting"] == before


class TestWhatWasReportedStaysAsItWasSaid:
    """Raw SQL, past the service."""

    async def test_the_words_never_change(self, conn: Any, request_context: Any) -> None:
        made = await _report(conn)
        with pytest.raises(psycopg.errors.RestrictViolation):
            await conn.execute(
                "UPDATE incident_report SET title = 'x' WHERE reference = %s",
                (made["reference"],),
            )

    async def test_a_report_is_never_deleted(self, conn: Any, request_context: Any) -> None:
        made = await _report(conn)
        with pytest.raises(psycopg.errors.RestrictViolation):
            await conn.execute(
                "DELETE FROM incident_report WHERE reference = %s", (made["reference"],)
            )

    async def test_it_has_one_outcome(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        made = await _report(conn)
        report = str((await _waiting(conn, made["reference"]))["report_uuid"])
        await intake.dismiss(conn, report_uuid=report, reason="Not ours", actor_id=_dpo(seeded))
        with pytest.raises(psycopg.errors.RestrictViolation):
            await conn.execute(
                "UPDATE incident_report SET dismissal_reason = 'x' WHERE reference = %s",
                (made["reference"],),
            )


class TestWhoIsTold:
    @pytest.fixture
    def queued(self, monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, tuple[Any, ...]]]:
        sent: list[tuple[str, tuple[Any, ...]]] = []

        def capture(task: Any, *args: Any, **kwargs: Any) -> str:
            sent.append((task.name.rsplit(".", 1)[-1], args))
            return "queued-in-a-test"

        monkeypatch.setattr(dispatch_mod, "dispatch_optional", capture)
        return sent

    async def test_the_roles_named_are_told_its_number_and_its_time_and_nothing_else(
        self,
        conn: Any,
        seeded: dict[str, Any],
        request_context: Any,
        queued: list[tuple[str, tuple[Any, ...]]],
    ) -> None:
        await breach_settings.set_intake_roles(conn, roles=["hr_user"], actor_id=_dpo(seeded))
        await staff(conn, "hr_user", "active.hr@test.local")
        suspended = await staff(conn, "hr_user", "suspended.hr@test.local")
        await execute(
            conn,
            "UPDATE auth_user SET status = 'suspended' WHERE id = %s",
            (int(suspended["id"]),),
        )
        made = await _report(conn)
        queued_report = await _waiting(conn, made["reference"])
        officers = [a for name, a in queued if name == "send_incident_reported"]
        # The roles are honoured, and the words are exactly these three: the
        # address, the number and the time. Nothing of what it says.
        assert all(len(a) == 3 for a in officers)
        assert {a[1:] for a in officers} == {
            (made["reference"], alerts.moment(queued_report["received_at"]))
        }
        told = {plain(a[0]) for a in officers}
        assert "active.hr@test.local" in told and "suspended.hr@test.local" not in told
        assert await _email_of(conn, _dpo(seeded)) in told, "the officers, always"
        admin = int(seeded["users"]["admin"]["id"])
        assert await _email_of(conn, admin) not in told, "a role not named"

        [reporter] = [a for name, a in queued if name == "send_incident_report_received"]
        assert len(reporter) == 3 and reporter[2] == made["reference"]
        assert plain(reporter[0]) == EMAIL and plain(reporter[1]) == "Asha Rao"

    async def test_with_nobody_to_tell_it_says_so_at_error_and_the_reporter_still_hears(
        self,
        conn: Any,
        seeded: dict[str, Any],
        request_context: Any,
        queued: list[tuple[str, tuple[Any, ...]]],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        logged: list[tuple[str, dict[str, Any]]] = []

        class Log:
            def error(self, event: str, **fields: Any) -> None:
                logged.append((event, fields))

        async def nobody(*_: Any) -> list[str]:
            return []

        monkeypatch.setattr(reports_repo, "active_emails", nobody)
        monkeypatch.setattr(alerts, "log", Log())
        made = await _report(conn)
        assert [name for name, _ in queued] == ["send_incident_report_received"]
        [(event, fields)] = logged
        assert event == "incident_report.nobody_to_tell"
        assert fields["reference"] == made["reference"]

    async def test_the_reporter_is_not_told_the_office_has_been_told(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        made = await _report(conn)
        assert "it has reached the Privacy Office" in made["message"]
        assert "has been told" not in made["message"]

    async def test_the_officers_are_told_and_cannot_be_taken_off(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        told = await breach_settings.set_intake_roles(conn, roles=[], actor_id=_dpo(seeded))
        assert told["intake_roles"] == ["dpo", "legal"]
        more = await breach_settings.set_intake_roles(
            conn, roles=["hr_user"], actor_id=_dpo(seeded)
        )
        assert more["intake_roles"] == ["dpo", "hr_user", "legal"]

    async def test_only_a_role_that_signs_in_may_be_named(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        for role in ("data_subject", "breach_holder", "nobody"):
            with pytest.raises(ValidationFailed):
                await breach_settings.set_intake_roles(conn, roles=[role], actor_id=_dpo(seeded))


class TestTheOrganisationsBoard:
    async def test_an_address_is_listed_once_and_sealed(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        added = await breach_settings.add_board_recipient(
            conn, full_name="The Chair", email="Chair@Example.org", actor_id=_dpo(seeded)
        )
        [mine] = [r for r in added["board_recipients"] if plain(r["email"]) == "chair@example.org"]
        assert str(mine["email"]).startswith("SE::") and plain(mine["full_name"]) == "The Chair"
        with pytest.raises(Conflict):
            await breach_settings.add_board_recipient(
                conn, full_name=None, email="chair@example.org", actor_id=_dpo(seeded)
            )

    async def test_a_bad_address_is_refused(self, conn: Any, seeded: dict[str, Any]) -> None:
        with pytest.raises(ValidationFailed):
            await breach_settings.add_board_recipient(
                conn, full_name=None, email="not an address", actor_id=_dpo(seeded)
            )

    async def test_an_address_taken_off_may_come_back(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        added = await breach_settings.add_board_recipient(
            conn, full_name=None, email="member@example.org", actor_id=_dpo(seeded)
        )
        [mine] = [r for r in added["board_recipients"] if plain(r["email"]) == "member@example.org"]
        gone = await breach_settings.remove_board_recipient(
            conn, recipient_uuid=str(mine["recipient_uuid"]), actor_id=_dpo(seeded)
        )
        assert "member@example.org" not in {plain(r["email"]) for r in gone["board_recipients"]}
        with pytest.raises(NotFound):
            await breach_settings.remove_board_recipient(
                conn, recipient_uuid=str(mine["recipient_uuid"]), actor_id=_dpo(seeded)
            )
        await breach_settings.add_board_recipient(
            conn, full_name=None, email="member@example.org", actor_id=_dpo(seeded)
        )
