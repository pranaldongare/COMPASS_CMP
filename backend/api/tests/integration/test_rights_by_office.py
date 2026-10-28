"""Rights requests by office: routed on receipt, claimed, transferred (0055).

The routing table of `hr-track.md` §5, row by row: consents on the Legal
office's notices only - its queue; on the DPO office's only - the DPO's; on
both, or none, or the public form - the shared intake, both queues, until one
office claims it. A request confined to a consent goes where the consent is;
a dispute where the request it disputes is. A claim is made once. A transfer
moves the office and nothing of the clock, writes who, when and why (sealed),
is audited, and tells the receiving office; it can be sent back the same way.
Each office's officer is told of its own requests and acts on them.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from cmp.core.errors import Conflict, ValidationFailed
from cmp.core.permissions import Role
from cmp.core.security import new_token, token_fingerprint
from cmp.db.repositories import audit as audit_repo
from cmp.db.repositories import rights as repo
from cmp.db.repositories import users as user_repo
from cmp.db.sql import fetch_one
from cmp.domain.consent import service as consent_service
from cmp.domain.hr import activities
from cmp.domain.rights import service
from tests.conftest import hashed
from tests.integration.hr_world import approved_version, legal_office, staff

pytestmark = pytest.mark.integration


async def _person(conn: Any) -> int:
    email = f"principal.{uuid.uuid4().hex[:10]}@test.local"
    mobile = f"+9197{uuid.uuid4().int % 10**8:08d}"
    row = await fetch_one(
        conn,
        # A known adult, as the seeded subject is: a consent waits for an age.
        """INSERT INTO auth_user (full_name, email, email_hash, mobile, mobile_hash, role,
                                  status, minor_until)
           VALUES ('Test principal', %s, %s, %s, %s, 'data_subject', 'active',
                   DATE '2008-05-17')
           RETURNING id""",
        (email, hashed("email", email), mobile, hashed("mobile", mobile)),
    )
    assert row is not None
    return int(row["id"])


async def _consent_with_dpo_office(conn: Any, seeded: dict[str, Any], person: int) -> int:
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
    await consent_service.serve_notice(conn, token=raw, language_code="english", user_id=person)
    given = await consent_service.capture(
        conn,
        token=raw,
        user_id=person,
        language_code="english",
        grants={str(seeded["purpose"]["purpose_uuid"]): True},
        action_type="checkbox_click",
        ip_address=None,
    )
    return int(given["consent_id"])


async def _consent_with_legal_office(conn: Any, seeded: dict[str, Any], person: int) -> int:
    world = await legal_office(conn, seeded)
    version = await approved_version(conn, world)
    made = await activities.create(
        conn,
        actor_id=int(world["poc"]["id"]),
        role=Role.HR_USER,
        category_uuid=str(world["category"]["category_uuid"]),
        template_version_uuid=str(version["version_uuid"]),
        purpose_uuids=[str(world["purposes"]["sessions"]["purpose_uuid"])],
        name=f"Wellness {world['tag']}",
        description="Four lunchtime sessions.",
        audience_mode="otp",
        link_expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    token = str(made["url_path"]).rsplit("/", 1)[-1]
    served = await consent_service.serve_notice(
        conn, token=token, language_code="english", user_id=person
    )
    given = await consent_service.capture(
        conn,
        token=token,
        user_id=person,
        language_code="english",
        grants={str(p["purpose_uuid"]): True for p in served["purposes"]},
        action_type="checkbox_click",
        ip_address=None,
    )
    return int(given["consent_id"])


async def _from_portal(conn: Any, person: int, **kw: Any) -> dict[str, Any]:
    return await service.create(
        conn,
        request_type="access",
        channel="portal",
        request_text="What do you hold about me?",
        submitted_contact="principal@test.local",
        subject_user_id=person,
        actor_id=person,
        verification_method="session",
        **kw,
    )


async def _legal_poc(conn: Any) -> int:
    row = await staff(conn, Role.LEGAL.value, f"legal.{uuid.uuid4().hex[:10]}@test.local")
    return int(row["id"])


async def _as_office(conn: Any, office: str) -> None:
    """From here, the connection reads as a session of `office` does."""
    await conn.execute("SELECT set_config('app.office', %s, false)", (office,))


class TestRoutingOnReceipt:
    async def test_consents_with_the_legal_office_only_go_to_its_queue(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        person = await _person(conn)
        await _consent_with_legal_office(conn, seeded, person)
        assert (await _from_portal(conn, person))["office_code"] == "hr"

    async def test_consents_with_the_dpo_office_only_go_to_its_queue(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        person = await _person(conn)
        await _consent_with_dpo_office(conn, seeded, person)
        assert (await _from_portal(conn, person))["office_code"] == "rnd"

    async def test_a_withdrawn_consent_still_places_her(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        """The office still holds what was collected before she withdrew."""
        person = await _person(conn)
        consent = await _consent_with_dpo_office(conn, seeded, person)
        row = await fetch_one(
            conn, "SELECT consent_uuid FROM consent_artefact WHERE consent_id = %s", (consent,)
        )
        assert row is not None
        await consent_service.withdraw(
            conn,
            consent_uuid=str(row["consent_uuid"]),
            user_id=person,
            purpose_uuids=None,
            withdraw_all=True,
            ip_address=None,
        )
        assert (await _from_portal(conn, person))["office_code"] == "rnd"

    async def test_both_and_none_go_to_the_shared_intake(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        nobody = await _person(conn)
        assert (await _from_portal(conn, nobody))["office_code"] is None
        both = await _person(conn)
        await _consent_with_dpo_office(conn, seeded, both)
        await _consent_with_legal_office(conn, seeded, both)
        assert await service.offices_of(conn, both) == ["hr", "rnd"]
        assert (await _from_portal(conn, both))["office_code"] is None

    async def test_asked_of_both_offices_she_makes_one_to_each_received_together(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        both = await _person(conn)
        to_dpo = await _from_portal(conn, both, office="rnd")
        to_legal = await _from_portal(conn, both, office="hr")
        assert (to_dpo["office_code"], to_legal["office_code"]) == ("rnd", "hr")
        assert to_dpo["reference"] != to_legal["reference"]
        assert to_dpo["received_at"] == to_legal["received_at"], "the same D0"

    async def test_the_public_form_goes_to_the_shared_intake(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        person = await _person(conn)
        await _consent_with_legal_office(conn, seeded, person)
        row = await service.create(
            conn,
            request_type="access",
            channel="public_form",
            request_text="Please tell me what you hold",
            submitted_contact="principal@test.local",
            subject_user_id=person,
        )
        assert row["office_code"] is None, "nobody is known until the code is confirmed"

    async def test_a_request_confined_to_a_consent_goes_where_the_consent_is(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        person = await _person(conn)
        await _consent_with_dpo_office(conn, seeded, person)
        hr_consent = await _consent_with_legal_office(conn, seeded, person)
        row = await _from_portal(conn, person, consent_id=hr_consent)
        assert row["office_code"] == "hr"

    async def test_a_dispute_goes_where_the_request_it_disputes_is(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        person = await _person(conn)
        original = await _from_portal(conn, person, office="hr")
        dispute = await _from_portal(conn, person, linked_request_id=int(original["request_id"]))
        assert dispute["office_code"] == "hr"


class TestTheIntake:
    async def test_both_offices_see_it_and_the_first_to_claim_keeps_it(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, sent: Any
    ) -> None:
        person = await _person(conn)
        row = await _from_portal(conn, person)
        uuid_ = str(row["request_uuid"])
        dpo = int(seeded["users"]["dpo"]["id"])
        # Arrived in the intake: both offices' officers are told.
        told = {args[0] for name, args in sent if name == "send_rights_request_received"}
        assert set(await user_repo.officer_emails(conn, None)) == told
        assert set(await user_repo.officer_emails(conn, "hr")) <= told

        await _as_office(conn, "hr")
        assert await repo.by_uuid(conn, uuid_, role=Role.LEGAL, user_id=dpo) is not None
        await _as_office(conn, "rnd")
        seen = await repo.by_uuid(conn, uuid_, role=Role.DPO, user_id=dpo)
        assert seen is not None
        # Work waits for a claim.
        with pytest.raises(Conflict):
            await service.transition(
                conn, seen, to="in_progress", reason=None, role=Role.DPO, actor_id=dpo
            )
        claimed = await service.claim(conn, seen, role=Role.DPO, office="rnd", actor_id=dpo)
        assert claimed["office_code"] == "rnd" and claimed["claimed_at"] is not None
        assert any(
            e["event_type"] == "rights.claimed"
            for e in await audit_repo.for_reference(conn, str(row["reference"]))
        )
        # Gone from the Legal office's queue; a second claim is refused.
        await _as_office(conn, "hr")
        assert await repo.by_uuid(conn, uuid_, role=Role.LEGAL, user_id=dpo) is None
        with pytest.raises(Conflict) as again:
            await service.claim(conn, claimed, role=Role.LEGAL, office="hr", actor_id=dpo)
        assert again.value.code == "already_claimed"


class TestTransfer:
    async def test_it_moves_the_office_and_nothing_of_the_clock(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, sent: Any
    ) -> None:
        person = await _person(conn)
        row = await _from_portal(conn, person, office="rnd")
        dpo = int(seeded["users"]["dpo"]["id"])
        legal = await _legal_poc(conn)
        moved = await service.transfer(
            conn,
            row,
            role=Role.DPO,
            to_office="hr",
            reason="Her consent is to a wellness activity.",
            actor_id=dpo,
        )
        assert moved["office_code"] == "hr"
        assert moved["transferred_from"] == "rnd"
        assert moved["transferred_at"] is not None
        assert (moved["received_at"], moved["due_at"]) == (row["received_at"], row["due_at"])
        stored = await fetch_one(
            conn,
            "SELECT transfer_reason, transferred_by FROM rights_request WHERE request_id = %s",
            (int(row["request_id"]),),
        )
        assert stored is not None and str(stored["transfer_reason"]).startswith("SE::")
        assert stored["transferred_by"] == dpo
        trail = await audit_repo.for_reference(conn, str(row["reference"]))
        moves = [e for e in trail if e["event_type"] == "rights.transferred"]
        assert moves and moves[-1]["detail"]["from"] == "rnd"
        assert "wellness" not in str(moves[-1]["detail"]), "never the reason"

        # The Legal office's officers hear, and only they; the reason travels sealed.
        told = [args for name, args in sent if name == "send_rights_transfer_received"]
        assert {a[0] for a in told} == set(await user_repo.officer_emails(conn, "hr"))
        assert all(str(a[6]).startswith("SE::") for a in told)

        # And back, by the Legal office, with a reason of its own.
        back = await service.transfer(
            conn, moved, role=Role.LEGAL, to_office="rnd", reason="Research data.", actor_id=legal
        )
        assert back["office_code"] == "rnd" and back["transferred_from"] == "hr"
        assert back["due_at"] == row["due_at"]

    async def test_what_a_transfer_refuses(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        person = await _person(conn)
        dpo = int(seeded["users"]["dpo"]["id"])
        held = await _from_portal(conn, person, office="rnd")
        with pytest.raises(ValidationFailed):
            await service.transfer(
                conn, held, role=Role.DPO, to_office="hr", reason="  ", actor_id=dpo
            )
        with pytest.raises(ValidationFailed):
            await service.transfer(
                conn, held, role=Role.DPO, to_office="rnd", reason="Same", actor_id=dpo
            )
        with pytest.raises(ValidationFailed):
            await service.transfer(
                conn, held, role=Role.DPO, to_office="legal", reason="No such", actor_id=dpo
            )
        intake = await _from_portal(conn, person)
        with pytest.raises(Conflict) as unclaimed:
            await service.transfer(
                conn, intake, role=Role.DPO, to_office="hr", reason="Theirs", actor_id=dpo
            )
        assert unclaimed.value.code == "unclaimed"


class TestTheLegalOfficeAnswersItsOwn:
    async def test_its_officer_is_told_and_starts_work(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, sent: Any
    ) -> None:
        person = await _person(conn)
        legal = await _legal_poc(conn)
        row = await _from_portal(conn, person, office="hr")
        told = {args[0] for name, args in sent if name == "send_rights_request_received"}
        assert told == set(await user_repo.officer_emails(conn, "hr"))
        assert "dpo@test.local" not in told

        await _as_office(conn, "hr")
        mine = await service.require(conn, str(row["request_uuid"]), role=Role.LEGAL, user_id=legal)
        mine = await service.classify(
            conn, mine, request_type="access", note=None, role=Role.LEGAL, actor_id=legal
        )
        started = await service.transition(
            conn, mine, to="in_progress", reason=None, role=Role.LEGAL, actor_id=legal
        )
        assert started["status"] == "in_progress"

        # The DPO office does not see it.
        await _as_office(conn, "rnd")
        assert (
            await repo.by_uuid(
                conn,
                str(row["request_uuid"]),
                role=Role.DPO,
                user_id=int(seeded["users"]["dpo"]["id"]),
            )
            is None
        )
