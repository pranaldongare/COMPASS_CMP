"""Notice templates: the DPO's notices before there is a project (0044).

The Privacy Office writes a notice when it knows what a kind of study will
collect, which is usually before anybody has registered the study. A template
is that notice: the Rule 3 links and the DPO contact, who it addresses, the
purposes it carries and the text of each language, under a short ID
(`TPL-0007`) the DPO gives the study's R&D User.

It is never served and never consented to, so it is edited in place, needs no
approval, and is retired rather than deleted. It is only ever used by being
*copied*: `apply` makes a project's own draft notice from it, which is then
approved and published like any other notice - the legal sign-off is on what
the project serves, not on the template. Two projects using one template have
two notices, so "which text, for which project" keeps one answer.
"""

from __future__ import annotations

from typing import Any, Final

from cmp.core.enums import LanguageCode
from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.db.repositories import notice_templates as repo
from cmp.db.repositories import notices as notice_repo
from cmp.db.repositories import projects as project_repo
from cmp.db.repositories import registry as registry_repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.domain.notices import service as notices
from cmp.validation import choice

Row = dict[str, Any]

#: A purpose a template may carry: one the office uses or is still writing.
#: A draft purpose is fine on a template - the project's notice cannot be
#: published until the DPO activates it, which the notice checklist says.
ATTACHABLE: Final = ("active", "draft")

STATUSES: Final = ("active", "retired")


async def _record(conn: Conn, template: Row, event: str, **detail: Any) -> None:
    await audit.record(
        conn,
        event=event,
        entity_type="notice_template",
        entity_id=int(template["template_id"]),
        detail={"template": template["template_code"], **detail},
    )


async def require(conn: Conn, template_uuid: str) -> Row:
    found = await repo.by_uuid(conn, template_uuid)
    if not found:
        raise NotFound("Notice template")
    return found


async def detail(conn: Conn, template: Row) -> Row:
    """The template with its purposes, its languages and where it was used."""
    template_id = int(template["template_id"])
    fresh = await repo.by_id(conn, template_id) or template
    return {
        **fresh,
        "purposes": await repo.purposes_of(conn, template_id),
        "languages": await repo.languages_of(conn, template_id),
        "notices": await repo.notices_from(conn, template_id),
    }


async def create(
    conn: Conn,
    *,
    actor_id: int,
    title: str,
    withdraw_url: str,
    exercise_rights_url: str,
    board_complaint_url: str,
    dpo_contact: str,
    applicable_to: str | None = None,
    note: str | None = None,
    language_code: str | None = None,
    rendered_text: str | None = None,
) -> Row:
    """A new template, with its first text if the DPO has it to hand."""
    made = await repo.create(
        conn,
        title=title.strip(),
        withdraw_url=withdraw_url,
        exercise_rights_url=exercise_rights_url,
        board_complaint_url=board_complaint_url,
        dpo_contact=dpo_contact,
        applicable_to=applicable_to,
        note=note,
        created_by=actor_id,
    )
    await _record(conn, made, Event.NOTICE_TEMPLATE_CREATED)
    if rendered_text and rendered_text.strip():
        await set_language(
            conn,
            made,
            language_code=language_code or LanguageCode.ENGLISH.value,
            rendered_text=rendered_text,
            actor_id=actor_id,
        )
    return await detail(conn, made)


async def update(conn: Conn, template: Row, *, actor_id: int, **fields: Any) -> Row:
    """Edit the template's own fields. Notices already made from it keep what
    they were made with: they are copies, and theirs to change."""
    await repo.lock(conn, int(template["template_id"]))
    if "title" in fields and fields["title"] is not None:
        fields["title"] = str(fields["title"]).strip()
    await repo.update(conn, int(template["template_id"]), **fields)
    await _record(
        conn,
        template,
        Event.NOTICE_TEMPLATE_UPDATED,
        fields=sorted(k for k, v in fields.items() if v is not None),
    )
    return await detail(conn, template)


async def attach_purpose(
    conn: Conn,
    template: Row,
    *,
    purpose_uuid: str,
    display_order: int = 0,
    is_mandatory: bool = False,
) -> Row:
    purpose = await registry_repo.purpose_by_uuid(conn, purpose_uuid)
    if not purpose:
        raise NotFound("Purpose")
    if purpose["status"] not in ATTACHABLE:
        raise ValidationFailed(
            "A retired purpose cannot be put on a template",
            field="purpose_uuid",
            details={"status": purpose["status"]},
        )
    await repo.attach_purpose(
        conn,
        template_id=int(template["template_id"]),
        purpose_id=int(purpose["purpose_id"]),
        display_order=display_order,
        is_mandatory=is_mandatory,
    )
    await repo.touch(conn, int(template["template_id"]))
    await _record(
        conn,
        template,
        Event.NOTICE_TEMPLATE_PURPOSE_ATTACHED,
        purpose=purpose_uuid,
        is_mandatory=is_mandatory,
    )
    return await detail(conn, template)


async def detach_purpose(conn: Conn, template: Row, *, purpose_uuid: str) -> Row:
    purpose = await registry_repo.purpose_by_uuid(conn, purpose_uuid)
    if not purpose:
        raise NotFound("Purpose")
    removed = await repo.detach_purpose(
        conn, template_id=int(template["template_id"]), purpose_id=int(purpose["purpose_id"])
    )
    if not removed:
        raise NotFound("Purpose on this template")
    await repo.touch(conn, int(template["template_id"]))
    await _record(conn, template, Event.NOTICE_TEMPLATE_PURPOSE_DETACHED, purpose=purpose_uuid)
    return await detail(conn, template)


async def set_language(
    conn: Conn, template: Row, *, language_code: str, rendered_text: str, actor_id: int
) -> Row:
    """The text in one language, added or replaced. No approval to clear:
    a template's text is approved on each project's notice made from it."""
    language = choice(LanguageCode, language_code, field="language_code")
    if not rendered_text.strip():
        raise ValidationFailed("The text cannot be empty", field="rendered_text")
    await repo.set_language(
        conn,
        template_id=int(template["template_id"]),
        language_code=language.value,
        rendered_text=rendered_text,
        updated_by=actor_id,
    )
    await repo.touch(conn, int(template["template_id"]))
    await _record(conn, template, Event.NOTICE_TEMPLATE_LANGUAGE_SET, language=language.value)
    return await detail(conn, template)


async def remove_language(conn: Conn, template: Row, *, language_code: str) -> Row:
    language = choice(LanguageCode, language_code, field="language_code")
    removed = await repo.remove_language(
        conn, template_id=int(template["template_id"]), language_code=language.value
    )
    if not removed:
        raise NotFound("Language on this template")
    await repo.touch(conn, int(template["template_id"]))
    await _record(conn, template, Event.NOTICE_TEMPLATE_LANGUAGE_REMOVED, language=language.value)
    return await detail(conn, template)


async def set_status(conn: Conn, template: Row, *, status: str) -> Row:
    """Retire a template so it can no longer be attached, or bring it back.
    Never deleted: the notices made from it name it."""
    if status not in STATUSES:
        raise ValidationFailed(f"status must be one of: {', '.join(STATUSES)}", field="status")
    await repo.lock(conn, int(template["template_id"]))
    template = await repo.by_id(conn, int(template["template_id"])) or template
    if template["status"] == status:
        return await detail(conn, template)
    await repo.set_status(conn, int(template["template_id"]), status)
    await _record(
        conn,
        template,
        Event.NOTICE_TEMPLATE_RETIRED if status == "retired" else Event.NOTICE_TEMPLATE_REACTIVATED,
    )
    return await detail(conn, template)


async def find(conn: Conn, template_code: str) -> Row:
    """A template by the ID the DPO gave out - for whoever is about to attach
    it. A retired one is found, and says so; `apply` refuses it."""
    found = await repo.by_code(conn, template_code)
    if not found:
        raise NotFound("Notice template")
    return await detail(conn, found)


async def apply(
    conn: Conn, *, project_uuid: str, template_code: str, actor_id: int, role: str
) -> Row:
    """Make this project's draft notice from a template.

    A copy: the links, the contact, the audience, the note, the purposes and
    the text of every language, under a code of the project's own. The notice
    remembers the template it came from; nothing after this connects them -
    changing the template changes no notice made from it. The notice then
    needs what every notice needs: each language approved, each purpose
    active, and publication.
    """
    project = await project_repo.require(conn, project_uuid, role=role, user_id=actor_id)
    template = await repo.by_code(conn, template_code)
    if not template:
        raise NotFound("Notice template")
    if template["status"] != "active":
        raise Conflict(
            f"{template['template_code']} has been retired by the Privacy Office. "
            "Ask them which template to use instead.",
            code="template_retired",
            field="template_code",
        )

    code = await notices.generate_code(conn, project_name=project["project_name"])
    notice = await notice_repo.create(
        conn,
        project_id=project["project_id"],
        notice_code=code,
        version=1,
        withdraw_url=template["withdraw_url"],
        exercise_rights_url=template["exercise_rights_url"],
        board_complaint_url=template["board_complaint_url"],
        dpo_contact=template["dpo_contact"],
        applicable_to=template["applicable_to"],
        note=template["note"],
        change_class=None,
        template_id=int(template["template_id"]),
    )

    template_id = int(template["template_id"])
    purposes = await repo.purposes_of(conn, template_id)
    for purpose in purposes:
        await notice_repo.attach_purpose(
            conn,
            notice_id=notice["notice_id"],
            purpose_id=purpose["purpose_id"],
            display_order=int(purpose.get("display_order") or 0),
            is_mandatory=bool(purpose.get("is_mandatory")),
        )
    languages = await repo.languages_of(conn, template_id)
    for language in languages:
        await notices.set_language(
            conn,
            notice_id=notice["notice_id"],
            language_code=language["language_code"],
            rendered_text=language["rendered_text"],
            actor_id=actor_id,
        )

    await audit.record(
        conn,
        event=Event.NOTICE_CREATED,
        entity_type="notice",
        entity_id=notice["notice_id"],
        detail={
            "project": project_uuid,
            "notice_code": code,
            "from_template": template["template_code"],
            "purposes": len(purposes),
            "languages": len(languages),
        },
    )
    made = await notice_repo.by_id(conn, notice["notice_id"])
    assert made is not None
    return made
