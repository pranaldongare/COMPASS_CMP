"""A world built through the API: the product's own flow, as the fixture.

Every row this suite reads back was written by an endpoint, so the writes are
exercised on the way to the reads - and every response on the way is checked
by `call()`. The world is one project brought from registration to a published
notice with a live consent link, one data principal who registered through that
link and consented, one export of her, and the office staff around them.

Built once per test module through `world`, because it is many requests and
nothing in it is mutated by the tests that read it; the tests that do mutate
build their own pieces.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from tests.http.conftest import Session, SessionFactory, fresh, fresh_email, fresh_mobile, last_code
from tests.http.contract import call

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
CONSENT_CODE = "cmp.notifications.send_consent_code"


@dataclass
class World:
    admin: Session
    dpo: Session
    rnd: Session
    dco: Session
    dco_admin: Session
    rco: Session
    purpose_uuid: str = ""
    processor_uuid: str = ""
    project_uuid: str = ""
    notice_uuid: str = ""
    source_uuid: str = ""
    site_uuid: str = ""
    link_uuid: str = ""
    link_path: str = ""
    link_token: str = ""
    principal: Session | None = None
    principal_mobile: str = ""
    principal_email: str = ""
    consent_uuid: str = ""
    export_uuid: str = ""
    batch_uuid: str = ""
    collection_uuid: str = ""
    #: When the build began, so a test can ask the trail for this world only.
    built_at: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


async def build(http: httpx.AsyncClient, session_for: SessionFactory, queued: list[Any]) -> World:
    w = World(
        admin=await session_for("admin"),
        dpo=await session_for("dpo"),
        rnd=await session_for("rnd_user"),
        dco=await session_for("dco"),
        dco_admin=await session_for("dco_admin"),
        rco=await session_for("rco"),
    )
    tag = fresh("W")
    w.built_at = datetime.now(UTC).isoformat()

    # ---- the register: a purpose and a third-party processor (DPO)
    purpose = await call(
        http,
        "POST",
        "/purposes",
        session=w.dpo,
        expect=201,
        check_sealed=False,
        json={
            "purpose_code": f"P-{tag}",
            "name": f"Gait research {tag}",
            "description": "Video of walking, for a gait-recognition model.",
            "uses": "Training and evaluating the model.",
            "lawful_basis": "consent_s6",
            "data_categories": ["video", "gait"],
            "retention_days": 365,
            "retention_basis": "business_policy",
            "erasure_trigger": "withdrawal",
        },
    )
    w.purpose_uuid = purpose.json()["purpose_uuid"]
    await call(
        http,
        "POST",
        f"/purposes/{w.purpose_uuid}/activate",
        session=w.dpo,
        expect=(200, 204),
        check_sealed=False,
    )

    processor = await call(
        http,
        "POST",
        "/processors",
        session=w.dpo,
        expect=201,
        check_sealed=False,
        json={
            "legal_name": f"Acme Labs {tag}",
            "type": "lab",
            "contract_ref": f"CTR-{tag}",
            "security_confirmed_at": datetime.now(UTC).date().isoformat(),
            "is_in_house": False,
        },
    )
    w.processor_uuid = processor.json()["processor_uuid"]

    # ---- the project (R&D), its notice (DPO writes; the author brings the doc)
    project = await call(
        http,
        "POST",
        "/projects",
        session=w.rnd,
        expect=201,
        json={
            "project_name": f"Walk Study {tag}",
            "description": "Gait video collection.",
            "processor_uuids": [w.processor_uuid],
            "requesting_team": "Computer Vision",
        },
    )
    w.project_uuid = project.json()["project_uuid"]

    notice = await call(
        http,
        "POST",
        f"/projects/{w.project_uuid}/notices",
        template="/projects/{project_uuid}/notices",
        session=w.dpo,
        expect=201,
        json={
            "withdraw_url": "https://example.org/withdraw",
            "exercise_rights_url": "https://example.org/rights",
            "board_complaint_url": "https://example.org/board",
            "dpo_contact": "dpo@example.org",
            "applicable_to": "data_subject",
            "note": "Ask for the campus card.",
            "rendered_text": (
                "We collect video of you walking, to train a model. You may withdraw at any time."
            ),
        },
    )
    w.notice_uuid = notice.json()["notice_uuid"]
    await call(
        http,
        "POST",
        f"/notices/{w.notice_uuid}/purposes",
        session=w.dpo,
        expect=(200, 201),
        check_sealed=False,
        json={"purpose_uuid": w.purpose_uuid, "display_order": 1, "is_mandatory": True},
    )
    await call(
        http,
        "POST",
        f"/notices/{w.notice_uuid}/languages/english/approve",
        session=w.dpo,
        expect=(200, 204),
        check_sealed=False,
    )

    # ---- the approval proof (R&D), and the submission
    proof = b"%PDF-1.4\n" + (FIXTURES / "notice_filled.docx").read_bytes()[:2000]
    await call(
        http,
        "POST",
        f"/projects/{w.project_uuid}/approvals",
        template="/projects/{project_uuid}/approvals",
        session=w.rnd,
        expect=201,
        data={
            "approval_type": "security",
            "reference_no": f"SEC-{tag}",
            "approved_on": datetime.now(UTC).date().isoformat(),
        },
        files={"proof": ("proof.pdf", proof, "application/pdf")},
    )
    await call(
        http,
        "POST",
        f"/projects/{w.project_uuid}/transition",
        template="/projects/{project_uuid}/transition",
        session=w.rnd,
        json={"to": "pending_approval"},
    )
    await call(
        http,
        "POST",
        f"/projects/{w.project_uuid}/transition",
        template="/projects/{project_uuid}/transition",
        session=w.dpo,
        json={"to": "approved"},
    )

    # ---- routing: a source under the processor, a site on it, the link (DCO)
    source = await call(
        http,
        "POST",
        "/sources",
        session=w.dco,
        expect=201,
        json={
            "source_code": f"SRC-{tag}",
            "name": f"Acme intake {tag}",
            "source_role": "both",
            "exchange_mode": "manual_upload",
            "processor_uuid": w.processor_uuid,
        },
    )
    w.source_uuid = source.json()["source_uuid"]
    await call(
        http,
        "PUT",
        f"/sources/{w.source_uuid}/owner",
        template="/sources/{source_uuid}/owner",
        session=w.dco_admin,
        expect=(200, 204),
        json={"owner_user_uuid": w.dco.uuid},
    )
    site = await call(
        http,
        "POST",
        f"/projects/{w.project_uuid}/sites",
        session=w.dco_admin,
        expect=201,
        check_sealed=False,
        json={"source_uuid": w.source_uuid, "location": "Pune"},
    )
    w.site_uuid = site.json()["site_uuid"]
    link = await call(
        http,
        "POST",
        f"/sites/{w.site_uuid}/agent",
        session=w.dco,
        expect=(200, 201),
        check_sealed=False,
        json={"expires_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(), "max_uses": 50},
    )
    body = link.json()
    w.link_uuid = body.get("link_uuid") or body.get("link", {}).get("link_uuid", "")
    w.link_path = body.get("url_path") or body.get("link", {}).get("url_path", "")
    w.link_token = w.link_path.rsplit("/", 1)[-1]

    # ---- a data principal arrives through the link and consents
    w.principal_mobile, w.principal_email = fresh_mobile(), fresh_email("principal")
    await call(http, "GET", f"/c/{w.link_token}", template="/c/{token}")
    await call(
        http,
        "GET",
        f"/c/{w.link_token}/notice",
        template="/c/{token}/notice",
        params={"language_code": "english"},
    )
    await call(
        http,
        "POST",
        f"/c/{w.link_token}/register",
        template="/c/{token}/register",
        expect=(200, 201),
        json={
            "full_name": f"Principal {tag}",
            "mobile": w.principal_mobile,
            "email": w.principal_email,
            "organization_id": f"STU-{tag}",
            "person_type": "external",
        },
    )
    # She registered with two contacts, so two codes: the second completes it
    # and opens her session.
    cookies: dict[str, str] = {}
    for contact in (w.principal_mobile, w.principal_email):
        await call(
            http,
            "POST",
            f"/c/{w.link_token}/otp",
            template="/c/{token}/otp",
            json={"contact": contact},
        )
        code = last_code(queued, CONSENT_CODE, position=1)
        verified = await call(
            http,
            "POST",
            f"/c/{w.link_token}/otp/verify",
            template="/c/{token}/otp/verify",
            json={"contact": contact, "code": code},
        )
        cookies.update(dict(verified.cookies))
    assert cookies, "the second code opened her session"
    # The notice has to have been shown to *her* - the serving record is per
    # person - so it is fetched again, signed in, before she decides.
    await call(
        http,
        "GET",
        f"/c/{w.link_token}/notice",
        template="/c/{token}/notice",
        params={"language_code": "english"},
        cookies=cookies,
    )
    consent = await call(
        http,
        "POST",
        f"/c/{w.link_token}/consent",
        template="/c/{token}/consent",
        expect=(200, 201),
        cookies=cookies,
        headers={"X-CSRF-Token": cookies.get("cmp_csrf", "")},
        json={
            "language_code": "english",
            "grants": {w.purpose_uuid: True},
            "action_type": "checkbox_click",
        },
    )
    w.consent_uuid = consent.json().get("consent_uuid", "")

    # her own session, for /me
    from cmp.db.pool import connection
    from cmp.db.repositories import users as user_repo

    async with connection() as conn:
        row = await user_repo.by_contact(conn, w.principal_mobile)
    assert row is not None
    w.principal = await session_for("data_subject", user=dict(row))

    # ---- an export of the people on the project (DCO)
    export = await call(
        http,
        "POST",
        f"/projects/{w.project_uuid}/exports",
        template="/projects/{project_uuid}/exports",
        session=w.dco,
        expect=(200, 201),
    )
    w.export_uuid = export.json().get("export_uuid", "")

    # ---- a manifest of what the site collected under her consent (DCO)
    manifest = (
        "source_collection_ref,source_asset_ref,asset_type,collected_on,subject_role,consent_uuid\n"
        f"run-{tag},clip-001.mp4,video,2026-09-01,consented,{w.consent_uuid}\n"
        f"run-{tag},clip-002.mp4,video,2026-09-01,incidental,\n"
    )
    await call(
        http,
        "POST",
        "/imports/validate",
        session=w.dco,
        data={"source": w.source_uuid, "project": w.project_uuid},
        files={"manifest": ("manifest.csv", manifest.encode(), "text/csv")},
    )
    imported = await call(
        http,
        "POST",
        "/imports",
        session=w.dco,
        expect=(200, 201),
        data={"source": w.source_uuid, "project": w.project_uuid},
        files={"manifest": ("manifest.csv", manifest.encode(), "text/csv")},
    )
    assert imported.json()["accepted_rows"] == 2, imported.json()
    w.batch_uuid = imported.json()["batch_uuid"]
    collections = await call(
        http,
        "GET",
        f"/projects/{w.project_uuid}/collections",
        template="/projects/{project_uuid}/collections",
        session=w.dco,
    )
    w.collection_uuid = collections.json()["items"][0]["collection_uuid"]
    return w
