"""The people a breach affected, found from the records and confirmed by the
office (S3-02).

Rule 7(1) asks for a notice to each affected principal "to the best of its
knowledge". A person running a breach knows what it reached, in the words of
the work, and the records answer in those words:

* **a project or activity** - everyone who ever gave consent in it, in a window
  if one is given (2026-11-06);
* **a vendor** (a processor) - everyone in files exported to it (`export_line`),
  and everyone standing in an HR activity whose category names it;
* **a data source** - everyone captured in its assets (`asset_consent`).

The last two are the same relation a rights request reads to find a person's
holders, read from the other end (`db/repositories/holdings.py`). The office
previews what the records show, confirms it - leaving out anyone the records
wrongly include, adding anyone they cannot show - and each confirmation is a
revision. A person is listed once and never removed; a later revision adds
only people not already listed, and each is notified in turn (S3-03).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from cmp.core.errors import NotFound, ValidationFailed
from cmp.db.repositories import breaches as repo
from cmp.db.repositories import holdings
from cmp.db.repositories import registry as registry_repo
from cmp.db.repositories import users as user_repo
from cmp.db.sql import Conn
from cmp.domain.audit.service import Event
from cmp.domain.breach import notices, service
from cmp.validation.choices import choice

Row = dict[str, Any]

#: How many listed people one page carries.
PAGE = 200


class ScopeKind(StrEnum):
    PROJECT = "project"
    PROCESSOR = "processor"
    DATA_SOURCE = "data_source"


def _merge(found: dict[int, tuple[str, dict[str, list[str]]]], pid: int, by: str, ev: Row) -> None:
    """Add what put a person on the list. The first scope to find them names how."""
    evidence = {k: sorted(set(v)) for k, v in ev.items() if v}
    if pid not in found:
        found[pid] = (by, evidence)
        return
    first, held = found[pid]
    for key, values in evidence.items():
        held[key] = sorted(set(held.get(key, [])) | set(values))
    found[pid] = (first, held)


async def _derive(
    conn: Conn, scopes: list[Row]
) -> tuple[list[Row], dict[int, tuple[str, dict[str, list[str]]]]]:
    """Every person the records place in these scopes, and the scopes as resolved."""
    found: dict[int, tuple[str, dict[str, list[str]]]] = {}
    resolved: list[Row] = []
    for i, scope in enumerate(scopes):
        kind = choice(ScopeKind, str(scope.get("kind") or ""), field=f"scopes[{i}].kind")
        if kind == ScopeKind.PROJECT:
            uuid = scope.get("project_uuid")
            project = uuid and await holdings.project_of_office(conn, str(uuid))
            if not project:
                raise NotFound("Project")
            since, until = scope.get("since"), scope.get("until")
            if since and until and since > until:
                raise ValidationFailed(
                    "The period ends before it starts", field=f"scopes[{i}].until"
                )
            rows = await holdings.people_in_project(
                conn, int(project["project_id"]), since=since, until=until
            )
            for r in rows:
                _merge(found, int(r["person_id"]), "project", {"projects": [str(uuid)]})
            resolved.append(
                {
                    "kind": kind.value,
                    "project_uuid": str(uuid),
                    "project_name": project["project_name"],
                    "since": since.isoformat() if since else None,
                    "until": until.isoformat() if until else None,
                    "found": len(rows),
                }
            )
        elif kind == ScopeKind.PROCESSOR:
            uuid = scope.get("processor_uuid")
            processor = uuid and await registry_repo.processor_by_uuid(conn, str(uuid))
            if not processor:
                raise NotFound("Processor")
            rows = await holdings.people_held_by(conn, processor_id=int(processor["processor_id"]))
            for r in rows:
                _merge(
                    found,
                    int(r["person_id"]),
                    "processor",
                    {"exports": r["exports"], "activities": r["activities"]},
                )
            resolved.append(
                {
                    "kind": kind.value,
                    "processor_uuid": str(uuid),
                    "processor_name": processor["legal_name"],
                    "found": len(rows),
                }
            )
        else:
            uuid = scope.get("source_uuid")
            source = uuid and await registry_repo.source_by_uuid(conn, str(uuid))
            if not source:
                raise NotFound("Data source")
            rows = await holdings.people_held_by(conn, source_id=int(source["source_id"]))
            for r in rows:
                _merge(found, int(r["person_id"]), "data_source", {"assets": r["assets"]})
            resolved.append(
                {
                    "kind": kind.value,
                    "source_uuid": str(uuid),
                    "source_name": source["name"],
                    "found": len(rows),
                }
            )
    return resolved, found


async def preview(conn: Conn, *, breach_uuid: str, scopes: list[Row]) -> Row:
    """What the records show for these scopes, before anyone confirms it."""
    breach = await service.require(conn, breach_uuid)
    if not scopes:
        raise ValidationFailed("Say where to look", field="scopes")
    resolved, found = await _derive(conn, scopes)
    listed = await repo.listed_person_ids(conn, int(breach["breach_id"]))
    new_ids = [pid for pid in found if pid not in listed]
    sample = await repo.people_by_ids(conn, sorted(found)[:PAGE])
    return {
        "scopes": resolved,
        "derived": len(found),
        "already_listed": len(found) - len(new_ids),
        "would_add": len(new_ids),
        "people": [
            {
                **p,
                "found_by": found[int(p["person_id"])][0],
                "evidence": found[int(p["person_id"])][1],
                "already_listed": int(p["person_id"]) in listed,
            }
            for p in sample
        ],
    }


async def confirm(
    conn: Conn,
    *,
    breach_uuid: str,
    scopes: list[Row],
    exclude: list[str],
    add: list[str],
    note: str | None,
    actor_id: int,
) -> Row:
    """Confirm the list as it now stands: a new revision.

    The records are derived again here, from the scopes, rather than taken
    from the caller: the revision is what the records showed when it was
    confirmed. Anyone already listed stays where they are.
    """
    breach = await service.locked_open(conn, breach_uuid)
    if not scopes and not add:
        raise ValidationFailed("Choose where to look, or add a person", field="scopes")
    resolved, found = await _derive(conn, scopes) if scopes else ([], {})

    excluded: set[int] = set()
    for uuid in exclude:
        person = await user_repo.by_uuid(conn, uuid)
        if person and int(person["id"]) in found:
            excluded.add(int(person["id"]))
    by_hand: list[int] = []
    for uuid in add:
        person = await user_repo.by_uuid(conn, uuid)
        if not person:
            raise NotFound("Person")
        by_hand.append(int(person["id"]))

    listed = await repo.listed_person_ids(conn, int(breach["breach_id"]))
    people: list[tuple[int, str, dict[str, Any]]] = [
        (pid, by, ev)
        for pid, (by, ev) in found.items()
        if pid not in excluded and pid not in listed
    ]
    taken = listed | {p[0] for p in people}
    for pid in dict.fromkeys(by_hand):
        if pid not in taken:
            people.append((pid, "dpo", {}))
            taken.add(pid)

    revision = await repo.add_affected_revision(
        conn,
        int(breach["breach_id"]),
        scopes=resolved,
        derived=len(found),
        added_by_hand=len(set(by_hand)),
        excluded=len(excluded),
        people=people,
        note=(note or "").strip() or None,
        confirmed_by=actor_id,
    )
    await service.record_event(
        conn,
        breach,
        Event.BREACH_AFFECTED_REVISED,
        actor_id=actor_id,
        detail={
            "revision": int(revision["revision"]),
            "derived": len(found),
            "added_by_hand": len(set(by_hand)),
            "excluded": len(excluded),
            "newly_listed": len(people),
        },
    )
    await notices.reopen_if_done(conn, breach, newly_listed=len(people), actor_id=actor_id)
    return await listing(conn, breach_uuid=breach_uuid, after=None)


async def listing(conn: Conn, *, breach_uuid: str, after: str | None) -> Row:
    """Every revision, and the listed people a page at a time."""
    breach = await service.require(conn, breach_uuid)
    breach_id = int(breach["breach_id"])
    after_id: int | None = None
    if after:
        after_id = await repo.affected_id_by_uuid(conn, breach_id, after)
        if after_id is None:
            raise ValidationFailed("Unknown cursor", field="cursor")
    page = await repo.affected_page(conn, breach_id, after=after_id, limit=PAGE + 1)
    more = len(page) > PAGE
    page = page[:PAGE]
    return {
        "total": await repo.count_affected(conn, breach_id),
        "revisions": await repo.affected_revisions(conn, breach_id),
        "people": page,
        "next_cursor": str(page[-1]["affected_uuid"]) if more else None,
    }


async def options(conn: Conn, *, breach_uuid: str) -> Row:
    """The projects and activities a person may choose from: the office's, and
    only those with people in them."""
    await service.require(conn, breach_uuid)
    return {"projects": await holdings.projects_with_people(conn)}
