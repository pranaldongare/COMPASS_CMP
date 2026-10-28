"""The Legal office's world, for the HR track's tests (ADR 0033).

Built through the services, inside the test's transaction: a Legal PoC and
an HR PoC, a category the HR PoC is assigned to with an in-house processor
on it, three purposes (two active, one still a draft), a template under the
category and, when asked, an approved version of it. Codes carry a tag of
the test's own: the suite shares the development database, whose seed has
its own WELLNESS and its own purposes, and codes are unique.
"""

from __future__ import annotations

import uuid
from typing import Any

from cmp.core.permissions import Role
from cmp.db.sql import fetch_one
from cmp.domain.hr import categories
from cmp.domain.notices import templates, versions
from cmp.domain.registry import service as registry
from tests.conftest import hashed, office_of

LOCKED = (
    "The Legal office will use your data for:\n{{purposes}}\n\n"
    "About this activity: {{description}}\n\n"
    "You may withdraw at any time from your consents page."
)

TEMPLATE = {
    "title": "Wellness sessions",
    "withdraw_url": "https://example.org/withdraw",
    "exercise_rights_url": "https://example.org/rights",
    "board_complaint_url": "https://example.org/board",
    "dpo_contact": "legal@example.org",
    "applicable_to": "data_subject",
}


def _purpose(code: str, name: str) -> dict[str, Any]:
    return {
        "purpose_code": code,
        "name": name,
        "description": f"{name}.",
        "uses": f"Running the {name.lower()}.",
        "lawful_basis": "consent_s6",
        "s7_clause": None,
        "data_categories": ["name", "employee_id"],
        "retention_period": "1 year",
        "retention_basis": "business_policy",
        "erasure_trigger": "withdrawal",
        "consent_validity_period": None,
        "cross_border_permitted": False,
        "permitted_for_minors": False,
        "lapse_behaviour": "erase",
    }


async def staff(conn: Any, role: str, email: str) -> dict[str, Any]:
    row = await fetch_one(
        conn,
        """INSERT INTO auth_user (full_name, email, email_hash, role, status, office_id)
           VALUES (%s, %s, %s, %s::user_role, 'active',
                   (SELECT office_id FROM office WHERE office_code = %s))
           RETURNING id, uuid""",
        (f"Test {role}", email, hashed("email", email), role, office_of(role)),
    )
    assert row is not None
    return row


async def legal_office(conn: Any, seeded: dict[str, Any]) -> dict[str, Any]:
    tag = uuid.uuid4().hex[:8].upper()
    legal = await staff(conn, Role.LEGAL.value, f"legal.{tag.lower()}@test.local")
    poc = await staff(conn, Role.HR_USER.value, f"hrpoc.{tag.lower()}@test.local")
    category = await categories.create(
        conn,
        category_code=f"WELL_{tag}",
        name="Employee wellness",
        description=None,
        office="hr",
        actor_id=int(legal["id"]),
    )
    await categories.set_processors(
        conn,
        str(category["category_uuid"]),
        processors=[
            {
                "processor_uuid": str(seeded["processors"]["in_house"]["processor_uuid"]),
                "processor_role": "hrms",
            }
        ],
        role=Role.LEGAL,
        actor_id=int(legal["id"]),
    )
    await categories.set_user_categories(
        conn,
        str(poc["uuid"]),
        category_uuids=[str(category["category_uuid"])],
        actor_id=int(seeded["users"]["admin"]["id"]),
        actor_role=Role.ADMIN.value,
    )
    purposes = {}
    for key, name, active in [
        ("sessions", "Wellness sessions", True),
        ("survey", "Follow-up survey", True),
        ("draft", "Coaching pilot", False),
    ]:
        made = await registry.create_purpose(
            conn,
            fields=_purpose(f"P-HR-{key.upper()}-{tag}", name),
            actor_id=int(legal["id"]),
            office="hr",
        )
        if active:
            await registry.activate_purpose(conn, str(made["purpose_uuid"]))
        purposes[key] = made
    template = await templates.create(
        conn,
        actor_id=int(legal["id"]),
        office="hr",
        role="legal",
        category_uuid=str(category["category_uuid"]),
        **TEMPLATE,
    )
    return {
        "tag": tag,
        "legal": legal,
        "poc": poc,
        "category": category,
        "purposes": purposes,
        "template": template,
    }


async def approved_version(
    conn: Any,
    world: dict[str, Any],
    *,
    text: str = LOCKED,
    reconsent_required: bool = False,
) -> dict[str, Any]:
    """The template's next version: two purposes, the first mandatory; English
    text; approved."""
    legal = int(world["legal"]["id"])
    template = await templates.require(conn, str(world["template"]["template_uuid"]))
    draft = await versions.open_version(conn, template, actor_id=legal)
    if reconsent_required:
        draft = await versions.update(conn, draft, fields={"reconsent_required": True})
    draft = await versions.set_language(
        conn, draft, language_code="english", locked_text=text, actor_id=legal
    )
    draft = await versions.set_purposes(
        conn,
        draft,
        purposes=[
            {
                "purpose_uuid": str(world["purposes"]["sessions"]["purpose_uuid"]),
                "is_mandatory": True,
            },
            {"purpose_uuid": str(world["purposes"]["survey"]["purpose_uuid"])},
        ],
    )
    return await versions.approve(conn, template, draft, actor_id=legal)
