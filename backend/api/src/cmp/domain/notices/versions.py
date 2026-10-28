"""Template versions: what Legal approves once, for every activity made from it (ADR 0033).

A Legal office template is versioned. Version *n* opens as a draft carrying
what version *n-1* said (or, for the first, the template's links, contact
and audience); Legal edits it in place - the locked text per language with
its two slots, the purposes an activity may choose with the ones it must
carry, the description slot's guidance and limit, whether moving to it needs
consent again - and approves it. Approval is the legal sign-off: it checks
the version can be composed, hashes each language's text and freezes the
lot (`cmp_template_version_freeze`). A later change is version *n+1*.

A retired version starts no new activity; the activities already on it go
on. A DPO office template is not versioned (ADR 0028).
"""

from __future__ import annotations

from typing import Any, Final

from cmp.core.enums import LanguageCode
from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.db.repositories import registry as registry_repo
from cmp.db.repositories import template_versions as repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.domain.notices import composer
from cmp.validation import choice

Row = dict[str, Any]

#: What a draft may change, besides its text and its purposes.
DRAFT_FIELDS: Final = tuple(repo.DRAFT_FIELDS)

#: The sample a preview fills `{{description}}` with when none is given.
SAMPLE_DESCRIPTION: Final = "A short description of the activity, written by the HR PoC."


async def _record(conn: Conn, version: Row, event: str, **detail: Any) -> None:
    await audit.record(
        conn,
        event=event,
        entity_type="template_version",
        entity_id=int(version["version_id"]),
        detail={"template": version["template_code"], "version": version["version"], **detail},
    )


async def detail(conn: Conn, version: Row) -> Row:
    fresh = await repo.by_id(conn, int(version["version_id"])) or version
    return {
        **fresh,
        "languages": await repo.languages_of(conn, int(fresh["version_id"])),
        "purposes": await repo.purposes_of(conn, int(fresh["version_id"])),
    }


def _versioned(template: Row) -> None:
    if not template.get("category_id"):
        raise Conflict(
            "A DPO office template is not versioned; its text is approved on each "
            "project's notice (ADR 0028)",
            code="template_not_versioned",
        )


async def require(conn: Conn, template: Row, number: int) -> Row:
    _versioned(template)
    found = await repo.by_number(conn, int(template["template_id"]), number)
    if not found:
        raise NotFound("Template version")
    return found


def _draft(version: Row) -> None:
    if version["status"] != "draft":
        raise Conflict(
            f"Version {version['version']} is {version['status']} and cannot change; "
            "open the next version instead",
            code="version_not_draft",
            details={"status": version["status"]},
        )


async def list_versions(conn: Conn, template: Row) -> list[Row]:
    _versioned(template)
    return await repo.for_template(conn, int(template["template_id"]))


async def open_version(conn: Conn, template: Row, *, actor_id: int) -> Row:
    """The next version, as a draft carrying what the last one said."""
    _versioned(template)
    if template["status"] != "active":
        raise Conflict("A retired template takes no new version", code="template_retired")
    template_id = int(template["template_id"])
    await repo.lock_template(conn, template_id)
    last = await repo.latest(conn, template_id)
    if last and last["status"] == "draft":
        raise Conflict(
            f"Version {last['version']} is still a draft: approve it or edit it",
            code="version_draft_open",
            details={"version": last["version"]},
        )
    source = last or template
    fields = {
        "reconsent_required": False,
        "slot_guidance": last["slot_guidance"] if last else None,
        "slot_max_length": last["slot_max_length"] if last else 1200,
        "withdraw_url": source["withdraw_url"],
        "exercise_rights_url": source["exercise_rights_url"],
        "board_complaint_url": source["board_complaint_url"],
        "dpo_contact": source["dpo_contact"],
        "applicable_to": source["applicable_to"],
    }
    number = int(last["version"]) + 1 if last else 1
    version_id = await repo.create(
        conn, template_id=template_id, version=number, created_by=actor_id, fields=fields
    )
    if last:
        for language in await repo.languages_of(conn, int(last["version_id"])):
            await repo.set_language(
                conn,
                version_id=version_id,
                language_code=language["language_code"],
                locked_text=language["locked_text"],
                updated_by=actor_id,
            )
        await repo.set_purposes(
            conn,
            version_id,
            [dict(p) for p in await repo.purposes_of(conn, int(last["version_id"]))],
        )
    version = await repo.by_id(conn, version_id)
    assert version is not None
    await _record(
        conn,
        version,
        Event.TEMPLATE_VERSION_OPENED,
        copied_from=int(last["version"]) if last else None,
    )
    return await detail(conn, version)


async def update(conn: Conn, version: Row, *, fields: dict[str, Any]) -> Row:
    _draft(version)
    given = {k: v for k, v in fields.items() if k in DRAFT_FIELDS and v is not None}
    if "slot_guidance" in fields and fields["slot_guidance"] == "":
        given["slot_guidance"] = None
    await repo.update(conn, int(version["version_id"]), given)
    await _record(conn, version, Event.TEMPLATE_VERSION_UPDATED, fields=sorted(given))
    return await detail(conn, version)


async def set_language(
    conn: Conn, version: Row, *, language_code: str, locked_text: str, actor_id: int
) -> Row:
    """One language's locked text, added or replaced. The slots are checked at
    approval, so a draft can be written in any order."""
    _draft(version)
    language = choice(LanguageCode, language_code, field="language_code")
    if not locked_text.strip():
        raise ValidationFailed("The text cannot be empty", field="locked_text")
    await repo.set_language(
        conn,
        version_id=int(version["version_id"]),
        language_code=language.value,
        locked_text=locked_text,
        updated_by=actor_id,
    )
    await _record(conn, version, Event.TEMPLATE_VERSION_UPDATED, language=language.value)
    return await detail(conn, version)


async def remove_language(conn: Conn, version: Row, *, language_code: str) -> Row:
    _draft(version)
    language = choice(LanguageCode, language_code, field="language_code")
    removed = await repo.remove_language(
        conn, version_id=int(version["version_id"]), language_code=language.value
    )
    if not removed:
        raise NotFound("Language on this version")
    await _record(conn, version, Event.TEMPLATE_VERSION_UPDATED, language_removed=language.value)
    return await detail(conn, version)


async def set_purposes(conn: Conn, version: Row, *, purposes: list[dict[str, Any]]) -> Row:
    """The purposes an activity may choose, exactly these, in this order. Each
    is the Legal office's own and not retired; a draft purpose is allowed here
    and refused at approval."""
    _draft(version)
    chosen: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, item in enumerate(purposes):
        uuid = str(item["purpose_uuid"])
        if uuid in seen:
            raise ValidationFailed("A purpose is listed twice", field="purposes")
        seen.add(uuid)
        purpose = await registry_repo.purpose_by_uuid(conn, uuid)
        if not purpose or purpose.get("office_code") != version["office_code"]:
            raise NotFound("Purpose")
        if purpose["status"] == "retired":
            raise ValidationFailed(
                f"{purpose['purpose_code']} is retired", field="purposes", details={"purpose": uuid}
            )
        chosen.append(
            {
                "purpose_id": purpose["purpose_id"],
                "is_mandatory": bool(item.get("is_mandatory")),
                "display_order": int(item.get("display_order", i)),
            }
        )
    await repo.set_purposes(conn, int(version["version_id"]), chosen)
    await _record(conn, version, Event.TEMPLATE_VERSION_UPDATED, purposes=len(chosen))
    return await detail(conn, version)


async def approve(conn: Conn, template: Row, version: Row, *, actor_id: int) -> Row:
    """Legal's sign-off: refused unless every activity made from it could be
    composed and published, then hashed and frozen."""
    _draft(version)
    if template["status"] != "active":
        raise Conflict("The template is retired", code="template_retired")
    purposes = await repo.purposes_of(conn, int(version["version_id"]))
    if not purposes:
        raise ValidationFailed("Give the version at least one purpose", field="purposes")
    for p in purposes:
        if p["status"] != "active":
            raise Conflict(
                f"{p['purpose_code']} ({p['name']}) is {p['status']}: activate it first",
                code="purpose_not_active",
                details={"purpose": str(p["purpose_uuid"]), "status": p["status"]},
            )
    languages = await repo.languages_of(conn, int(version["version_id"]))
    if not any(lang["language_code"] == LanguageCode.ENGLISH.value for lang in languages):
        raise ValidationFailed(
            "The version needs its English text", field="languages", details={"language": "english"}
        )
    for lang in languages:
        problems = composer.placeholder_problems(lang["locked_text"])
        if problems:
            slot = next(s for s in composer.PLACEHOLDERS if lang["locked_text"].count(s) != 1)
            raise ValidationFailed(
                f"The {lang['language_code']} text: {problems[0]}; each slot appears exactly once",
                field="languages",
                details={"language": lang["language_code"], "placeholder": slot},
            )
    if not version["applicable_to"]:
        raise ValidationFailed("Say who a notice made from it addresses", field="applicable_to")
    hashes = {}
    for lang in languages:
        digest = composer.hash_text(lang["locked_text"])
        await repo.set_hash(
            conn,
            version_id=int(version["version_id"]),
            language_code=lang["language_code"],
            content_hash=digest,
        )
        hashes[lang["language_code"]] = digest
    await repo.approve(conn, int(version["version_id"]), approved_by=actor_id)
    await _record(conn, version, Event.TEMPLATE_VERSION_APPROVED, hashes=hashes)
    return await detail(conn, version)


async def retire(conn: Conn, version: Row, *, actor_id: int) -> Row:
    """No new activity starts on it; those already on it go on."""
    if version["status"] != "approved":
        raise Conflict(
            f"Only an approved version is retired; version {version['version']} is "
            f"{version['status']}",
            code="version_not_approved",
        )
    await repo.retire(conn, int(version["version_id"]), retired_by=actor_id)
    await _record(conn, version, Event.TEMPLATE_VERSION_RETIRED)
    return await detail(conn, version)


async def preview(conn: Conn, version: Row, *, description: str | None) -> list[Row]:
    """What an activity made from it would serve, per language, with every
    purpose on its list and the description given (or a sample), and the
    hash that text would carry."""
    purposes = await repo.purposes_of(conn, int(version["version_id"]))
    out = []
    for lang in await repo.languages_of(conn, int(version["version_id"])):
        text = composer.compose(
            lang["locked_text"],
            purposes,
            description or SAMPLE_DESCRIPTION,
            max_length=int(version["slot_max_length"]),
        )
        out.append(
            {
                "language_code": lang["language_code"],
                "text": text,
                "content_hash": composer.hash_text(text),
            }
        )
    return out


async def verify_intact(conn: Conn, version: Row) -> list[Row]:
    """The version's languages, refused unless each still hashes to what was
    recorded at approval: a version changed in the database by hand is not
    the one Legal signed off."""
    languages = await repo.languages_of(conn, int(version["version_id"]))
    for lang in languages:
        if lang["content_hash"] != composer.hash_text(lang["locked_text"]):
            raise Conflict(
                f"Version {version['version']}'s {lang['language_code']} text no longer "
                "matches what Legal approved",
                code="version_tampered",
            )
    return languages
