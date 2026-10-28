"""Withdrawal on an HR activity reaches its respondents; holders come from its category.

A participant withdraws one purpose: the activity's HR PoC and the respondent
of each live category processor are emailed once each, queued after commit
and naming no participant; nobody on an R&D notice is; her own confirmation is
unchanged. A rights request about her derives the category's processors as
holders, `activity_processor`, answered by the account the category names or
the HR PoC (ADR 0033, open point F-15).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from cmp.core.permissions import Role
from cmp.db.repositories import holdings
from cmp.db.sql import fetch_all
from cmp.domain.consent import service as consent_service
from cmp.domain.hr import activities, categories
from tests.integration.hr_world import approved_version, legal_office, staff

pytestmark = pytest.mark.integration


@pytest.fixture
async def activity(conn: Any, seeded: dict[str, Any], request_context: Any) -> dict[str, Any]:
    world = await legal_office(conn, seeded)
    version = await approved_version(conn, world)
    # A second processor, a vendor, answered for by an account of its own.
    vendor_contact = await staff(
        conn, Role.HR_USER.value, f"vendor.{world['tag'].lower()}@test.local"
    )
    await categories.set_processors(
        conn,
        str(world["category"]["category_uuid"]),
        processors=[
            {
                "processor_uuid": str(seeded["processors"]["in_house"]["processor_uuid"]),
                "processor_role": "hrms",
            },
            {
                "processor_uuid": str(seeded["processors"]["external"]["processor_uuid"]),
                "processor_role": "vendor",
                "respondent_user_uuid": str(vendor_contact["uuid"]),
            },
        ],
        role=Role.LEGAL,
        actor_id=int(world["legal"]["id"]),
    )
    made = await activities.create(
        conn,
        actor_id=int(world["poc"]["id"]),
        role=Role.HR_USER,
        category_uuid=str(world["category"]["category_uuid"]),
        template_version_uuid=str(version["version_uuid"]),
        purpose_uuids=[
            str(world["purposes"]["sessions"]["purpose_uuid"]),
            str(world["purposes"]["survey"]["purpose_uuid"]),
        ],
        name=f"Wellness {world['tag']}",
        description="Four lunchtime sessions.",
        audience_mode="otp",
        link_expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    token = str(made["url_path"]).rsplit("/", 1)[-1]
    subject = seeded["subject"]["id"]
    served = await consent_service.serve_notice(
        conn, token=token, language_code="english", user_id=subject
    )
    given = await consent_service.capture(
        conn,
        token=token,
        user_id=subject,
        language_code="english",
        grants={str(p["purpose_uuid"]): True for p in served["purposes"]},
        action_type="checkbox_click",
        ip_address=None,
    )
    return {"world": world, "made": made, "consent": given, "vendor_contact": vendor_contact}


class TestTheRespondentsAreTold:
    async def test_one_email_per_respondent_naming_no_participant(
        self, conn: Any, activity: dict[str, Any], seeded: dict[str, Any], sent: Any
    ) -> None:
        world = activity["world"]
        await consent_service.withdraw(
            conn,
            consent_uuid=str(activity["consent"]["consent_uuid"]),
            user_id=seeded["subject"]["id"],
            purpose_uuids=[str(world["purposes"]["survey"]["purpose_uuid"])],
            withdraw_all=False,
            ip_address=None,
        )
        notices = [args for name, args in sent if name == "send_hr_withdrawal_notice"]
        # The HR PoC (the site's runner, and the HRMS's fallback) once, and the
        # vendor's named account once.
        assert len(notices) == 2
        for args in notices:
            assert "Test data_subject" not in str(args), "never her name"
            assert args[4] == ["Follow-up survey"]
            assert args[5] == ["Wellness sessions"]
        # Her own confirmation, unchanged.
        assert any(name == "send_withdrawal_confirmation" for name, _ in sent)

    async def test_an_r_and_d_withdrawal_tells_nobody_of_the_hr_track(
        self, conn: Any, seeded: dict[str, Any], sent: Any
    ) -> None:
        from cmp.core.security import new_token, token_fingerprint

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
        await consent_service.serve_notice(
            conn, token=raw, language_code="english", user_id=seeded["subject"]["id"]
        )
        given = await consent_service.capture(
            conn,
            token=raw,
            user_id=seeded["subject"]["id"],
            language_code="english",
            grants={str(seeded["purpose"]["purpose_uuid"]): True},
            action_type="checkbox_click",
            ip_address=None,
        )
        await consent_service.withdraw(
            conn,
            consent_uuid=str(given["consent_uuid"]),
            user_id=seeded["subject"]["id"],
            purpose_uuids=None,
            withdraw_all=True,
            ip_address=None,
        )
        assert not [n for n, _ in sent if n == "send_hr_withdrawal_notice"]


class TestHoldersFromTheCategory:
    async def test_her_holders_include_the_category_s_processors(
        self, conn: Any, activity: dict[str, Any], seeded: dict[str, Any]
    ) -> None:
        held = await holdings.holders_of_person(conn, seeded["subject"]["id"])
        names = {h["legal_name"] for h in held if h["activities"]}
        assert names == {"Test Internal Team", "Test Processor Ltd"}
        assert all(
            str(activity["made"]["activity_uuid"]) in h["activities"]
            for h in held
            if h["activities"]
        )

    async def test_a_derived_holder_is_an_activity_processor_with_its_respondent(
        self, conn: Any, activity: dict[str, Any], seeded: dict[str, Any]
    ) -> None:
        from cmp.domain.rights import service as rights

        request = await fetch_all(
            conn,
            """INSERT INTO rights_request (reference, request_type, channel, subject_user_id,
                                           status, due_at, submitted_contact,
                                           submitted_contact_hash, request_text, office_id)
               VALUES ('RR-HR-' || %s, 'access', 'portal', %s, 'in_progress',
                       now() + interval '30 days', 'SE::contact', 'h', 'SE::text',
                       (SELECT office_id FROM office WHERE office_code = 'hr'))
               RETURNING request_id, request_uuid""",
            (activity["world"]["tag"], seeded["subject"]["id"]),
        )
        from cmp.db.repositories import rights as rights_repo

        row = await rights_repo.by_id(conn, int(request[0]["request_id"]))
        holders = await rights.derive_holders(
            conn, row, role=Role.DPO, actor_id=int(seeded["users"]["dpo"]["id"])
        )
        by_name = {h["label"]: h for h in holders}
        vendor = by_name["Test Processor Ltd"]
        hrms = by_name["Test Internal Team"]
        assert vendor["derived_from"] == "activity_processor"
        assert hrms["derived_from"] == "activity_processor"
        assert vendor["responder_user_id"] == activity["vendor_contact"]["id"]
        assert hrms["responder_user_id"] == activity["world"]["poc"]["id"], "the HR PoC answers"
