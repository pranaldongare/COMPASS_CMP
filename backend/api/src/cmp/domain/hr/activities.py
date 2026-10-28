"""HR activities: an instance of a category, live as it is created (ADR 0033).

An activity is a project of the Legal office. The HR PoC creates it from an
approved template version of a category assigned to them - choosing the
purposes from the version's list, the mandatory ones always among them, and
writing the one description - and in the same transaction its notice is
composed from the version, the project goes `in_draft -> approved` by the
HR transition (which publishes the notice), its one implicit site is
registered under the category's HR system with the HR PoC running it, and
its open consent link is minted. Nothing waits on anybody: Legal's review
happened once, on the version.

Upgrading moves an activity to another approved version of its category
(or the same version with a new description): a new notice version composed
the same way and published, which moves the live link to it; consents
already given keep their text and hash. A version Legal flagged
`reconsent_required` asks every participant with a current consent to
decide again, after commit; their existing consent stands meanwhile
(open point OP-4).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from cmp.core import offices
from cmp.core.config import settings
from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.core.permissions import Role
from cmp.core.security import unseal_token
from cmp.db.repositories import consent as consent_repo
from cmp.db.repositories import hr_activities as activity_repo
from cmp.db.repositories import hr_categories as category_repo
from cmp.db.repositories import notices as notice_repo
from cmp.db.repositories import projects as project_repo
from cmp.db.repositories import template_versions as version_repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.domain.notices import composer, versions
from cmp.domain.notices import service as notice_service
from cmp.domain.projects import service as project_service
from cmp.domain.projects.state_machine import ProjectStatus

Row = dict[str, Any]

AUDIENCE_MODES = ("sso", "otp")


# ------------------------------------------------------------------ choices
async def options(conn: Conn, *, role: Role | str, user_id: int) -> list[Row]:
    """What the wizard offers: each active category the caller may run
    activities in, with the approved versions of its templates and each
    version's purposes and slot."""
    out = []
    for category in await category_repo.list_categories(
        conn, role=role, user_id=user_id, status="active"
    ):
        offered = []
        for version in await version_repo.approved_for_category(conn, int(category["category_id"])):
            offered.append(
                {
                    **version,
                    "purposes": await version_repo.purposes_of(conn, int(version["version_id"])),
                }
            )
        out.append({**category, "versions": offered})
    return out


async def _category(conn: Conn, category_uuid: str, *, role: Role | str, user_id: int) -> Row:
    category = await category_repo.by_uuid(conn, category_uuid, role=role, user_id=user_id)
    if not category:
        raise NotFound("Category")
    if category["status"] != "active":
        raise Conflict(f"{category['category_code']} is retired", code="category_retired")
    return category


async def _version(conn: Conn, version_uuid: str, *, category: Row) -> tuple[Row, list[Row]]:
    """An approved, untouched version of a template in the category, and its
    languages."""
    version = await version_repo.by_uuid(conn, version_uuid)
    if not version:
        raise NotFound("Template version")
    if version["category_id"] != category["category_id"]:
        raise ValidationFailed(
            "That template version belongs to another category", field="template_version_uuid"
        )
    if version["status"] != "approved" or version["template_status"] != "active":
        raise Conflict(
            f"{version['template_code']} v{version['version']} is "
            f"{version['status'] if version['status'] != 'approved' else 'on a retired template'}"
            "; choose an approved version",
            code="version_not_approved",
            field="template_version_uuid",
        )
    return version, await versions.verify_intact(conn, version)


async def _chosen(conn: Conn, version: Row, purpose_uuids: list[str]) -> list[Row]:
    """The chosen purposes in the version's order: within its list, every
    mandatory one among them."""
    offered = await version_repo.purposes_of(conn, int(version["version_id"]))
    by_uuid = {str(p["purpose_uuid"]): p for p in offered}
    wanted = set(purpose_uuids)
    outside = wanted - set(by_uuid)
    if outside:
        raise ValidationFailed(
            "A purpose is not on the template version's list",
            field="purpose_uuids",
            details={"not_offered": sorted(outside)},
        )
    missing = [p for p in offered if p["is_mandatory"] and str(p["purpose_uuid"]) not in wanted]
    if missing:
        raise ValidationFailed(
            "The template version makes "
            + ", ".join(str(p["name"]) for p in missing)
            + " mandatory",
            field="purpose_uuids",
            details={"mandatory": [str(p["purpose_uuid"]) for p in missing]},
        )
    return [p for p in offered if str(p["purpose_uuid"]) in wanted]


async def _hr_system(conn: Conn, category: Row) -> Row:
    """The processor the activity's one site stands under: the category's HR
    system, or failing that its first in-house processor."""
    held = await category_repo.processors_of(conn, int(category["category_id"]))
    for row in held:
        if row["processor_role"] == "hrms":
            return row
    for row in held:
        if row["is_in_house"]:
            return row
    raise ValidationFailed(
        f"{category['category_code']} names no HR system to hold the activity's data; "
        "ask the Legal PoC to add one",
        field="category_uuid",
    )


async def _compose_notice(
    conn: Conn,
    *,
    project_id: int,
    code: str,
    version: Row,
    languages: list[Row],
    purposes: list[Row],
    description: str,
    actor_id: int,
) -> Row:
    """The activity's notice, composed from the version: every language
    approved, because its legal text is the version Legal approved."""
    notice = await notice_repo.create(
        conn,
        project_id=project_id,
        notice_code=code,
        version=await notice_repo.max_version(conn, code) + 1,
        withdraw_url=version["withdraw_url"],
        exercise_rights_url=version["exercise_rights_url"],
        board_complaint_url=version["board_complaint_url"],
        dpo_contact=version["dpo_contact"],
        applicable_to=version["applicable_to"],
        template_version_id=int(version["version_id"]),
    )
    for order, p in enumerate(purposes):
        await notice_repo.attach_purpose(
            conn,
            notice_id=notice["notice_id"],
            purpose_id=p["purpose_id"],
            display_order=order,
            is_mandatory=bool(p["is_mandatory"]),
        )
    for lang in languages:
        text = composer.compose(
            lang["locked_text"],
            purposes,
            description,
            max_length=int(version["slot_max_length"]),
        )
        await notice_repo.upsert_language(
            conn,
            notice_id=notice["notice_id"],
            language_code=lang["language_code"],
            rendered_text=text,
            content_hash=composer.hash_text(text),
            created_by=actor_id,
        )
        await notice_repo.approve_language(
            conn,
            notice_id=notice["notice_id"],
            language_code=lang["language_code"],
            approved_by=actor_id,
        )
    await audit.record(
        conn,
        event=Event.NOTICE_CREATED,
        entity_type="notice",
        entity_id=notice["notice_id"],
        detail={
            "source": "template_version",
            "template": version["template_code"],
            "version": version["version"],
            "notice_code": code,
        },
    )
    return notice


def _expiry(link_expires_at: datetime) -> datetime:
    when = link_expires_at if link_expires_at.tzinfo else link_expires_at.replace(tzinfo=UTC)
    if when <= datetime.now(UTC):
        raise ValidationFailed("The link must expire in the future", field="link_expires_at")
    return when


# ------------------------------------------------------------------- create
async def create(
    conn: Conn,
    *,
    actor_id: int,
    role: Role | str,
    category_uuid: str,
    template_version_uuid: str,
    purpose_uuids: list[str],
    name: str,
    description: str,
    audience_mode: str,
    link_expires_at: datetime,
) -> Row:
    """The whole activity, in the caller's transaction: if any step refuses,
    nothing of it exists."""
    if audience_mode not in AUDIENCE_MODES:
        raise ValidationFailed("audience_mode is sso or otp", field="audience_mode")
    expires = _expiry(link_expires_at)
    if not name.strip():
        raise ValidationFailed("Name the activity", field="name")
    category = await _category(conn, category_uuid, role=role, user_id=actor_id)
    version, languages = await _version(conn, template_version_uuid, category=category)
    purposes = await _chosen(conn, version, purpose_uuids)
    served_description = composer.check_description(
        description, max_length=int(version["slot_max_length"])
    )
    hr_system = await _hr_system(conn, category)

    project = await project_repo.create(
        conn,
        project_name=name.strip(),
        description=served_description,
        internal_project_name=None,
        requesting_team=None,
        created_by=actor_id,
        dco_user_id=actor_id,
        office=offices.HR,
        category_id=int(category["category_id"]),
        template_version_id=int(version["version_id"]),
        activity_description=served_description,
    )
    project_id = int(project["project_id"])
    await project_repo.set_processors(
        conn, project_id, [hr_system["processor_id"]], actor_id=actor_id
    )
    await project_repo.record_transition(
        conn,
        project_id=project_id,
        from_status=None,
        to_status=ProjectStatus.IN_DRAFT.value,
        reason=None,
        actor_user_id=actor_id,
    )
    site = await project_repo.add_site(
        conn,
        project_id=project_id,
        site_label=str(project["project_name"]),
        location=None,
        processor_id=hr_system["processor_id"],
    )
    # The HR PoC runs it: the existing site-owner rules then hand the
    # activity's links and consents to them.
    await project_repo.set_site_owner_override(conn, site["site_id"], actor_id, actor_id=actor_id)

    code = await notice_service.generate_code(conn, project_name=name, prefix="HR")
    await _compose_notice(
        conn,
        project_id=project_id,
        code=code,
        version=version,
        languages=languages,
        purposes=purposes,
        description=served_description,
        actor_id=actor_id,
    )
    await audit.record(
        conn,
        event=Event.ACTIVITY_CREATED,
        entity_type="project",
        entity_id=project_id,
        detail={
            "category": category["category_code"],
            "template": version["template_code"],
            "version": version["version"],
            "purposes": [str(p["purpose_code"]) for p in purposes],
            "audience_mode": audience_mode,
        },
    )
    moved = await project_service.transition(
        conn,
        project_uuid=str(project["project_uuid"]),
        target=ProjectStatus.APPROVED.value,
        role=role,
        actor_id=actor_id,
    )
    from cmp.domain.consent import service as consent_service

    link = await consent_service.create_link(
        conn,
        site_uuid=str(site["site_uuid"]),
        expires_at=expires,
        max_uses=None,
        actor_id=actor_id,
        role=str(role),
        audience_mode=audience_mode,
    )
    return {
        "activity_uuid": project["project_uuid"],
        "notice_uuid": moved["published_notice_uuid"],
        "link_uuid": link["link_uuid"],
        "url_path": consent_service.link_path(link["token"]),
        "expires_at": link["expires_at"],
        "audience_mode": audience_mode,
    }


# ------------------------------------------------------------------ upgrade
async def _activity(conn: Conn, activity_uuid: str, *, role: Role | str, user_id: int) -> Row:
    project = await project_repo.require(
        conn, activity_uuid, role=role, user_id=user_id, write=True
    )
    if project.get("office_code") == offices.RND or not project.get("template_version_id"):
        raise NotFound("Activity")
    return project


async def _live_link_url(conn: Conn, project_id: int) -> str | None:
    from cmp.domain.consent import service as consent_service

    for link in await consent_repo.links_for_project(conn, project_id):
        if link["status"] == "active":
            token = unseal_token(link.get("token_sealed"))
            if token:
                return settings.public_base_url.rstrip("/") + consent_service.link_path(token)
    return None


async def upgrade(
    conn: Conn,
    activity_uuid: str,
    *,
    actor_id: int,
    role: Role | str,
    template_version_uuid: str,
    purpose_uuids: list[str],
    description: str,
) -> Row:
    """Move a running activity to another approved version of its category -
    or the same one with a new description. A new notice version, published;
    the live link moves to it; consents already given keep theirs."""
    project = await _activity(conn, activity_uuid, role=role, user_id=actor_id)
    if project["project_status"] != ProjectStatus.APPROVED.value:
        raise Conflict("Only a running activity is upgraded", code="activity_not_running")
    project_id = int(project["project_id"])
    await project_repo.require_for_update(conn, project_id)
    category = await category_repo.by_id(conn, int(project["category_id"]))
    assert category is not None
    version, languages = await _version(conn, template_version_uuid, category=category)
    purposes = await _chosen(conn, version, purpose_uuids)
    served_description = composer.check_description(
        description, max_length=int(version["slot_max_length"])
    )
    previous = project["template_version_id"]
    await project_repo.set_activity_version(
        conn, project_id, version_id=int(version["version_id"]), description=served_description
    )
    current = [
        n
        for n in await notice_repo.list_for_project(conn, project_id)
        if n["status"] == "published"
    ]
    if not current:
        raise Conflict("The activity has no published notice", code="no_published_notice")
    notice = await _compose_notice(
        conn,
        project_id=project_id,
        code=str(current[0]["notice_code"]),
        version=version,
        languages=languages,
        purposes=purposes,
        description=served_description,
        actor_id=actor_id,
    )
    published = await notice_service.publish(
        conn, notice_id=int(notice["notice_id"]), actor_id=actor_id
    )

    asked = 0
    if version["reconsent_required"]:
        asked = await _ask_again(conn, project=project, version=version)
    await audit.record(
        conn,
        event=Event.ACTIVITY_UPGRADED,
        entity_type="project",
        entity_id=project_id,
        detail={
            "from_version_id": previous,
            "template": version["template_code"],
            "version": version["version"],
            "reconsent_requested": asked,
        },
    )
    return {
        "activity_uuid": project["project_uuid"],
        "notice_uuid": published["notice_uuid"],
        "version": version["version"],
        "reconsent_requested": asked,
    }


async def _ask_again(conn: Conn, *, project: Row, version: Row) -> int:
    """One re-consent request per participant with a current consent on the
    activity, queued to go after commit. Their consent stands meanwhile."""
    from cmp.domain.consent.service import receipt_contact
    from cmp.tasks.dispatch import dispatch_optional
    from cmp.tasks.notifications import send_reconsent_request

    url = await _live_link_url(conn, int(project["project_id"]))
    if not url:
        return 0
    people = await activity_repo.participants(conn, int(project["project_id"]))
    summary = f"{version['template_title']}, version {version['version']}"
    sent = 0
    for person in people:
        contact = receipt_contact(person)
        if contact:
            dispatch_optional(
                send_reconsent_request, contact, str(project["project_name"]), summary, url
            )
            sent += 1
    return sent


# -------------------------------------------------------------------- close
async def close(
    conn: Conn, activity_uuid: str, *, actor_id: int, role: Role | str, reason: str | None
) -> Row:
    """Closed by its HR PoC or by Legal; its link stops resolving."""
    await _activity(conn, activity_uuid, role=role, user_id=actor_id)
    return await project_service.close(
        conn, project_uuid=activity_uuid, actor_id=actor_id, role=role, reason=reason
    )
