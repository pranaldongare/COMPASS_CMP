"""Development seed: one administrator, and the configuration a platform starts from.

Creates exactly one account - the administrator - and the reference data
every other part of the platform is set up against:

* **processors** - who collects, and whether they are us or a third party;
* **data sources** - each processor's collection rigs and feeds;
* **purposes** - what data is collected for, on what lawful basis, for how long;
* **a notice** - published, in English and Hindi, naming those purposes, on a
  project that is approved and has a live consent link.

Every other account - the DPO, collection owners, R&D users, data principals -
is created by the administrator from the console (Users → Invite), which is
how a real deployment gets them. Until a DPO exists, nobody can open the
project or the notice: those are the DPO's, and the administrator's role
reads purposes, processors and sources but not projects.

Everything is data in the tables below: edit a table, re-run, and the
database comes back into line. Re-running never duplicates anything and
never touches an account other than the administrator's.

Refuses to run outside local/test. A seed that can run in production is a
production database with a known password in it.

    python scripts/seed.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, date, datetime, timedelta
from typing import Any

from cmp.core.config import settings
from cmp.core.context import RequestContext, use_context
from cmp.core.logging import configure_logging, get_logger
from cmp.core.security import content_hash, hash_password, new_token, token_fingerprint
from cmp.db.pool import close_pool, open_pool, transaction
from cmp.db.redis import close_redis, open_redis
from cmp.db.repositories import users as user_repo
from cmp.db.sql import fetch_one

log = get_logger("cmp.seed")

PASSWORD = "SeedPassw0rd!2026"  # noqa: S105 - development only, guarded below

# =============================================================================
#  The administrator - the only account the seed creates
# =============================================================================

ADMIN: dict[str, str] = {
    "full_name": "System Admin",
    "email": "admin@cmp.local",
    "username": "admin",
    "organization_id": "ORG-ADM-001",
    "person_type": "employee",
}

# =============================================================================
#  Processors and their data sources
# =============================================================================
#
# `is_in_house` is the one field routing reads. A third party's approved
# project goes to a DCO Admin, who picks its sources; an in-house one goes
# back to its R&D owner. No rule reads a name, so a new team is a row here.
#
# Field values must be the database's own:
#   type           lab | tool | other
#   source_role    identity | collection | both
#   exchange_mode  file_export | file_import | manual_upload | api
#   authoritative  data-category codes (see DATA CATEGORIES below)

PROCESSORS: list[dict[str, Any]] = [
    {
        "legal_name": "Pune Motion Lab Pvt Ltd",
        "type": "lab",
        "contract_ref": "CTR-2026-0091",
        "security_confirmed_at": date(2026, 1, 15),
        "is_in_house": False,
        "location_country": "IN",
        "sources": [
            {
                "source_code": "SRC-PUNE-01",
                "name": "Pune Motion Lab capture rig",
                "source_role": "collection",
                "exchange_mode": "file_import",
                "id_scheme": "lab-local",
                "authoritative": ["facial_image", "gait_video"],
            },
        ],
    },
    {
        "legal_name": "SEED",
        "type": "lab",
        "contract_ref": "CTR-2026-0114",
        "security_confirmed_at": date(2026, 1, 15),
        "is_in_house": False,
        "location_country": "IN",
        "sources": [
            {
                "source_code": "SRC-SEED-CIT",
                "name": "CIT",
                "source_role": "collection",
                "exchange_mode": "manual_upload",
                "id_scheme": "seed-campus",
                "authoritative": ["facial_image", "gait_video"],
            },
            {
                "source_code": "SRC-SEED-VIT",
                "name": "VIT",
                "source_role": "collection",
                "exchange_mode": "manual_upload",
                "id_scheme": "seed-campus",
                "authoritative": ["facial_image", "gait_video"],
            },
        ],
    },
    {
        "legal_name": "SRIB",
        "type": "other",
        # An in-house team has no contract with itself. The column is NOT NULL,
        # so it says why rather than sitting empty.
        "contract_ref": "in-house - no processor contract",
        "security_confirmed_at": date(2026, 1, 15),
        "is_in_house": True,
        "location_country": "IN",
        "sources": [
            {
                "source_code": "SRC-SRIB-SE",
                "name": "SE",
                "source_role": "collection",
                "exchange_mode": "manual_upload",
                "id_scheme": "srib-employee",
                "authoritative": ["facial_image", "gait_video"],
            },
            {
                "source_code": "SRC-SRIB-VOICE",
                "name": "Voice",
                "source_role": "collection",
                "exchange_mode": "manual_upload",
                "id_scheme": "srib-employee",
                "authoritative": ["voice_recording"],
            },
        ],
    },
]

# =============================================================================
#  Purposes
# =============================================================================
#
# Field values must be the database's own:
#   lawful_basis      consent_s6 | legitimate_use_s7
#   retention_basis   statutory | contractual | business_policy
#   erasure_trigger   withdrawal | purpose_served | period_elapsed | inactivity
#   lapse_behaviour   quarantine | erase | none
#   data_categories   name, email, mobile, postal_address, date_of_birth,
#                     gender, government_id, employee_id, facial_image,
#                     voice_recording, fingerprint, gait_video, health_data,
#                     location, device_identifier, ip_address,
#                     sensor_reading, usage_log

PURPOSES: list[dict[str, Any]] = [
    {
        "purpose_code": "PUR-GAIT-TRAIN",
        "name": "Gait model training",
        "description": "Building and evaluating gait-based identification models.",
        "uses": "Train, validate and benchmark models. No decisions are made about you.",
        "lawful_basis": "consent_s6",
        "data_categories": ["facial_image", "gait_video", "name", "mobile"],
        "retention_days": 1095,
        "retention_basis": "business_policy",
        "erasure_trigger": "withdrawal",
        "consent_validity_days": 730,
        "lapse_behaviour": "quarantine",
        "cross_border_permitted": False,
        "permitted_for_minors": False,
    },
    {
        "purpose_code": "PUR-QUALITY",
        "name": "Recording quality assurance",
        "description": "Checking that recordings are usable before they enter the dataset.",
        "uses": "Manual and automated review of recording quality.",
        "lawful_basis": "consent_s6",
        "data_categories": ["facial_image", "gait_video"],
        "retention_days": 365,
        "retention_basis": "business_policy",
        "erasure_trigger": "withdrawal",
        "consent_validity_days": 730,
        "lapse_behaviour": "quarantine",
        "cross_border_permitted": False,
        "permitted_for_minors": False,
    },
]

# =============================================================================
#  The notice, and the project it belongs to
# =============================================================================
#
# A notice cannot exist without a project (notice.project_id is NOT NULL), so
# the seed keeps one, approved, with a site per source it names and a live
# consent link on the first site. `applicable_to`: data_subject | employee |
# ex_employee | others.

PROJECT: dict[str, Any] = {
    "project_name": "Gait Identification Study 2026",
    "internal_project_name": "GAIT-2026",
    "description": "Collection of gait video and facial images for model training.",
    "requesting_team": "Computer Vision",
    # Where it is collected: (source_code, site location). The site takes the
    # source's name, as the console does when a site is added.
    "sites": [
        ("SRC-PUNE-01", "Pune, Maharashtra"),
        ("SRC-SEED-CIT", "CIT campus, Coimbatore"),
        ("SRC-SRIB-SE", "SRIB lab, Bengaluru"),
    ],
    "approval": {
        "approval_type": "security",
        "reference_no": "SEC-2026-0142",
        "approved_on": date(2026, 2, 10),
    },
    "consent_link_days": 60,
    "consent_link_max_uses": 500,
}

NOTICE: dict[str, Any] = {
    "notice_code": "NTC-GAIT-2026",
    "applicable_to": "data_subject",
    "withdraw_url": "https://cmp.local/withdraw",
    "exercise_rights_url": "https://cmp.local/rights",
    "board_complaint_url": "https://dpb.gov.in/complaint",
    "dpo_contact": "privacy@bharatresearch.example",
    "purposes": ["PUR-GAIT-TRAIN", "PUR-QUALITY"],
    "languages": {
        "english": """\
NOTICE UNDER SECTION 5, DIGITAL PERSONAL DATA PROTECTION ACT 2023

Who is asking. Bharat Research Labs, acting as Data Fiduciary.

What we will collect. Your name, mobile number, and a facial image and short
gait video recorded at the collection site.

Why. To build and evaluate machine-learning models for gait-based
identification, and to verify the quality of the recordings we collect.

How long we keep it. Three years from the date of collection, after which the
recordings are erased.

Who else sees it. The recipients named at the end of this notice.

Your rights. You may ask for a summary of your data, ask us to correct or erase
it, nominate someone to act for you, and withdraw your consent. Withdrawing is
as easy as giving consent was. Withdrawal stops future processing; it does not
by itself delete recordings already made - ask for erasure if that is what you
want.

If you are not satisfied. Contact our Data Protection Officer first. You may
also complain to the Data Protection Board of India, independently of us.
""",
        "hindi": """\
धारा 5, डिजिटल व्यक्तिगत डेटा संरक्षण अधिनियम 2023 के अंतर्गत सूचना

कौन पूछ रहा है। भारत रिसर्च लैब्स, डेटा फ़िड्यूशियरी के रूप में।

हम क्या एकत्र करेंगे। आपका नाम, मोबाइल नंबर, तथा संग्रह स्थल पर रिकॉर्ड किया गया
चेहरे का चित्र और चाल का लघु वीडियो।

क्यों। चाल-आधारित पहचान के लिए मशीन लर्निंग मॉडल बनाने और उनका मूल्यांकन करने हेतु।

हम इसे कितने समय तक रखेंगे। संग्रह की तिथि से तीन वर्ष।

आपके अधिकार। आप अपने डेटा का सारांश मांग सकते हैं, सुधार या मिटाने के लिए कह सकते
हैं, किसी को नामित कर सकते हैं, और अपनी सहमति वापस ले सकते हैं।
""",
    },
}


# =============================================================================
#  Seeding - each step brings the database into line with a table above
# =============================================================================


async def seed_admin(conn: Any) -> int:
    """The administrator, through the repository so the personal columns are
    sealed and indexed on the way in. Found by its index on a re-run and left
    as it is - including its password, if somebody changed it."""
    row = await user_repo.by_email(conn, ADMIN["email"])
    if row is None:
        row = await user_repo.create(
            conn,
            full_name=ADMIN["full_name"],
            email=ADMIN["email"],
            role="admin",
            username=ADMIN["username"],
            organization_id=ADMIN["organization_id"],
            person_type=ADMIN["person_type"],
            status="active",
            password_hash=hash_password(PASSWORD),
        )
    log.info("seed.admin", email=ADMIN["email"])
    return int(row["id"])


async def seed_processors(conn: Any) -> dict[str, dict[str, Any]]:
    """Every processor and source in PROCESSORS, created or brought into line.

    Returns the sources by code. Idempotent on `legal_name`, which carries no
    unique constraint - two organisations may genuinely share a name, and the
    seed should not be the thing that decides they cannot.
    """
    sources: dict[str, dict[str, Any]] = {}
    for p in PROCESSORS:
        proc = await fetch_one(
            conn,
            """WITH existing AS (
                 UPDATE processor
                    SET type = %(type)s::processor_type,
                        contract_ref = %(contract_ref)s,
                        security_confirmed_at = %(security_confirmed_at)s,
                        is_in_house = %(is_in_house)s,
                        location_country = %(location_country)s
                  WHERE legal_name = %(legal_name)s
                 RETURNING processor_id
               ), created AS (
                 INSERT INTO processor (legal_name, type, contract_ref,
                                        security_confirmed_at, is_in_house,
                                        location_country)
                 SELECT %(legal_name)s, %(type)s::processor_type, %(contract_ref)s,
                        %(security_confirmed_at)s, %(is_in_house)s, %(location_country)s
                  WHERE NOT EXISTS (SELECT 1 FROM existing)
                 RETURNING processor_id
               )
               SELECT processor_id FROM created UNION ALL SELECT processor_id FROM existing
               LIMIT 1""",
            p,
        )
        for s in p["sources"]:
            sources[s["source_code"]] = await fetch_one(
                conn,
                """INSERT INTO data_source (source_code, name, source_role, exchange_mode,
                                            id_scheme, processor_id, is_authoritative_for)
                   VALUES (%(source_code)s, %(name)s, %(source_role)s::source_role,
                           %(exchange_mode)s::exchange_mode, %(id_scheme)s,
                           %(processor_id)s, %(authoritative)s)
                   ON CONFLICT (source_code) DO UPDATE
                      SET name = EXCLUDED.name,
                          source_role = EXCLUDED.source_role,
                          exchange_mode = EXCLUDED.exchange_mode,
                          id_scheme = EXCLUDED.id_scheme,
                          processor_id = EXCLUDED.processor_id,
                          is_authoritative_for = EXCLUDED.is_authoritative_for
                   RETURNING source_id, source_uuid, processor_id, name""",
                {**s, "processor_id": proc["processor_id"]},
            )
        log.info(
            "seed.processor",
            name=p["legal_name"],
            in_house=p["is_in_house"],
            sources=len(p["sources"]),
        )
    return sources


async def seed_purposes(conn: Any, admin_id: int) -> dict[str, dict[str, Any]]:
    """Every purpose in PURPOSES, created or brought into line, by code."""
    purposes: dict[str, dict[str, Any]] = {}
    for p in PURPOSES:
        purposes[p["purpose_code"]] = await fetch_one(
            conn,
            """INSERT INTO purpose (purpose_code, name, description, uses, lawful_basis,
                                    data_categories, retention_period, retention_basis,
                                    erasure_trigger, consent_validity_period,
                                    lapse_behaviour, cross_border_permitted,
                                    permitted_for_minors, status, created_by)
               VALUES (%(purpose_code)s, %(name)s, %(description)s, %(uses)s,
                       %(lawful_basis)s::lawful_basis, %(data_categories)s,
                       %(retention)s, %(retention_basis)s::retention_basis,
                       %(erasure_trigger)s::erasure_trigger, %(validity)s,
                       %(lapse_behaviour)s::lapse_behaviour, %(cross_border_permitted)s,
                       %(permitted_for_minors)s, 'active', %(admin)s)
               ON CONFLICT (purpose_code) DO UPDATE
                  SET name = EXCLUDED.name,
                      description = EXCLUDED.description,
                      uses = EXCLUDED.uses,
                      data_categories = EXCLUDED.data_categories,
                      retention_period = EXCLUDED.retention_period,
                      retention_basis = EXCLUDED.retention_basis,
                      erasure_trigger = EXCLUDED.erasure_trigger,
                      consent_validity_period = EXCLUDED.consent_validity_period,
                      lapse_behaviour = EXCLUDED.lapse_behaviour,
                      cross_border_permitted = EXCLUDED.cross_border_permitted,
                      permitted_for_minors = EXCLUDED.permitted_for_minors
               RETURNING purpose_id, purpose_uuid, name""",
            {
                **p,
                "retention": timedelta(days=p["retention_days"]),
                "validity": timedelta(days=p["consent_validity_days"]),
                "admin": admin_id,
            },
        )
        log.info("seed.purpose", code=p["purpose_code"])
    return purposes


async def seed_notice(
    conn: Any,
    admin_id: int,
    sources: dict[str, dict[str, Any]],
    purposes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """The project, its sites, the published notice and a consent link.

    Created once. A second run finds the project and leaves it: re-running is
    how a developer repairs a database, and it should not leave them with a
    second study, a second published notice and a second live link.
    """
    existing = await fetch_one(
        conn,
        """SELECT p.project_uuid, n.notice_uuid, s.site_uuid
             FROM project p
             LEFT JOIN notice n       ON n.project_id = p.project_id
             LEFT JOIN project_site s ON s.project_id = p.project_id
            WHERE p.internal_project_name = %s
            ORDER BY n.notice_id, s.site_id
            LIMIT 1""",
        (PROJECT["internal_project_name"],),
    )
    if existing:
        log.info("seed.project.exists", internal_name=PROJECT["internal_project_name"])
        return {**existing, "raw_token": None}

    # ------------------------------------------------------------ project
    project = await fetch_one(
        conn,
        """INSERT INTO project (project_name, internal_project_name, description,
                                requesting_team, created_by, project_status)
           VALUES (%s, %s, %s, %s, %s, 'in_draft')
           RETURNING project_id, project_uuid""",
        (
            PROJECT["project_name"],
            PROJECT["internal_project_name"],
            PROJECT["description"],
            PROJECT["requesting_team"],
            admin_id,
        ),
    )
    await conn.execute(
        """INSERT INTO project_status_history (project_id, to_status, actor_user_id)
           VALUES (%s, 'in_draft', %s)""",
        (project["project_id"], admin_id),
    )

    # --------------------------------------------- processors and sites
    # Each site is a source standing somewhere: its label is the source's
    # name and its processor the source's, and that processor is named on
    # the project, approved - a site under a processor the project never
    # approved is a state the console refuses to create. The sources carry no
    # owner yet: owners are DCOs and RCOs, which the administrator invites.
    first_site = None
    for code, location in PROJECT["sites"]:
        src = sources[code]
        await conn.execute(
            """INSERT INTO project_processor (project_id, processor_id, added_by,
                                              decided_by, decided_at)
               SELECT %s, %s, %s, %s, now()
                WHERE NOT EXISTS (SELECT 1 FROM project_processor
                                   WHERE project_id = %s AND processor_id = %s)""",
            (
                project["project_id"],
                src["processor_id"],
                admin_id,
                admin_id,
                project["project_id"],
                src["processor_id"],
            ),
        )
        site = await fetch_one(
            conn,
            """INSERT INTO project_site (project_id, processor_id, source_id,
                                         site_label, location)
               VALUES (%s, %s, %s, %s, %s)
               RETURNING site_id, site_uuid, site_label""",
            (project["project_id"], src["processor_id"], src["source_id"], src["name"], location),
        )
        first_site = first_site or site

    # ------------------------------------------------------------- notice
    notice = await fetch_one(
        conn,
        """INSERT INTO notice (notice_code, project_id, version, withdraw_url,
                               exercise_rights_url, board_complaint_url, dpo_contact,
                               applicable_to)
           VALUES (%s, %s, 1, %s, %s, %s, %s, %s::notice_audience)
           RETURNING notice_id, notice_uuid""",
        (
            NOTICE["notice_code"],
            project["project_id"],
            NOTICE["withdraw_url"],
            NOTICE["exercise_rights_url"],
            NOTICE["board_complaint_url"],
            NOTICE["dpo_contact"],
            NOTICE["applicable_to"],
        ),
    )
    for order, code in enumerate(NOTICE["purposes"]):
        await conn.execute(
            """INSERT INTO notice_purpose (notice_id, purpose_id, display_order)
               VALUES (%s, %s, %s)""",
            (notice["notice_id"], purposes[code]["purpose_id"], order),
        )
    for lang, text in NOTICE["languages"].items():
        await conn.execute(
            """INSERT INTO notice_language (notice_id, language_code, rendered_text,
                                            content_hash, created_by, approved_by,
                                            approved_at)
               VALUES (%s, %s::language_code, %s, %s, %s, %s, now())""",
            (notice["notice_id"], lang, text, content_hash(text), admin_id, admin_id),
        )

    # Published last: the freeze triggers refuse purposes and languages on a
    # published notice.
    recipients = "; ".join(
        f"{sources[code]['name']} ({location})" for code, location in PROJECT["sites"]
    )
    await conn.execute(
        """UPDATE notice SET status = 'published', recipients_text = %s,
                  approved_by = %s, published_at = now() WHERE notice_id = %s""",
        (recipients, admin_id, notice["notice_id"]),
    )
    await conn.execute(
        "UPDATE project SET current_notice_id = %s WHERE project_id = %s",
        (notice["notice_id"], project["project_id"]),
    )

    # ---------------------------------------- approval, then to approved
    approval = PROJECT["approval"]
    await conn.execute(
        """INSERT INTO project_approval (project_id, approval_type, reference_no,
                                         approved_on, proof_file_ref, proof_file_hash,
                                         uploaded_by)
           VALUES (%s, %s, %s, %s, 'approvals/seed-proof.pdf', %s, %s)""",
        (
            project["project_id"],
            approval["approval_type"],
            approval["reference_no"],
            approval["approved_on"],
            content_hash("seed proof document"),
            admin_id,
        ),
    )
    for frm, to in (("in_draft", "pending_approval"), ("pending_approval", "approved")):
        await conn.execute(
            "UPDATE project SET project_status = %s::project_status WHERE project_id = %s",
            (to, project["project_id"]),
        )
        await conn.execute(
            """INSERT INTO project_status_history (project_id, from_status, to_status,
                                                   actor_user_id)
               VALUES (%s, %s::project_status, %s::project_status, %s)""",
            (project["project_id"], frm, to, admin_id),
        )

    # -------------------------------------------------------- consent link
    raw_token = new_token(32)
    await conn.execute(
        """INSERT INTO consent_link (notice_id, site_id, token, expires_at, max_uses,
                                     created_by)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (
            notice["notice_id"],
            first_site["site_id"],
            token_fingerprint(raw_token)[:64],
            datetime.now(UTC) + timedelta(days=PROJECT["consent_link_days"]),
            PROJECT["consent_link_max_uses"],
            admin_id,
        ),
    )
    await conn.execute(
        """INSERT INTO audit_log (event_type, actor_user_id, entity_type, entity_id,
                                  detail_json)
           VALUES ('project.created', %s, 'project', %s, '{"seed": true}'::jsonb)""",
        (admin_id, project["project_id"]),
    )
    return {
        "project_uuid": project["project_uuid"],
        "notice_uuid": notice["notice_uuid"],
        "site_uuid": first_site["site_uuid"],
        "raw_token": raw_token,
    }


async def seed() -> None:
    if settings.environment not in ("local", "test"):
        log.error("seed.refused", environment=settings.environment)
        sys.exit(f"Refusing to seed a {settings.environment} database.")

    await open_pool()
    await open_redis()

    with use_context(RequestContext(request_id="seed", ip_address="127.0.0.1")):
        async with transaction() as conn:
            admin_id = await seed_admin(conn)
            sources = await seed_processors(conn)
            purposes = await seed_purposes(conn, admin_id)
            demo = await seed_notice(conn, admin_id, sources, purposes)

    portal = settings.public_base_url.rstrip("/")
    print("\n" + "=" * 72)
    print("  SEED COMPLETE")
    print("=" * 72)
    print(f"  Administrator : {ADMIN['email']}   password {PASSWORD}")
    print("  (the only account; invite the DPO and the rest from Users in the console)")
    print()
    for p in PROCESSORS:
        whose = "in-house" if p["is_in_house"] else "third party"
        codes = ", ".join(s["source_code"] for s in p["sources"])
        print(f"  Processor     : {p['legal_name']:26} {whose:12} {codes}")
    for p in PURPOSES:
        print(f"  Purpose       : {p['purpose_code']:16} {p['name']}")
    print(f"  Project       : {PROJECT['project_name']}  ({demo['project_uuid']}, approved)")
    print(f"  Notice        : {NOTICE['notice_code']} v1, published  ({demo['notice_uuid']})")
    if demo["raw_token"]:
        print("\n  Consent link (the token is not recoverable from the database):")
        print(f"    {portal}/c/{demo['raw_token']}")
    else:
        print("\n  The project was already there, so no new consent link was minted;")
        print("  the stored token is a keyed digest and cannot be read back.")
    print("=" * 72 + "\n")

    await close_redis()
    await close_pool()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    configure_logging()
    asyncio.run(seed())
