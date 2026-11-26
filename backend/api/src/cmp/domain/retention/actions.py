"""What the people responsible are asked to do in a retention review, and
what they answer (2026-11-26, ADR 0047).

Who is asked (the product owner's mapping):

* **owner** - who answers for the project: an HR activity's HR PoC; a
  project's DCO Admin where a third party collects for it, else its R&D User.
  On a *validity* review of an active project they confirm whether the people
  may be asked to consent again; on a *retention* review they confirm the
  project's own systems and sites hold nothing more.
* **processor** - each processor the records say holds the data (an export, an
  asset, an HR category). Its respondent answers: in the console when they
  have an account, otherwise by a link (as a rights holder does), and nobody
  until the processor has a respondent - the office is told.

An answer on a retention review is one of: **erased**; **anonymised**, with
the reason it could not be erased; **kept**, with the reason (a legal hold, a
statute) and the date it will be looked at again; **not held**. The officer
accepts it or sends it back; once every action is accepted the review closes.

The trail has each step against the review, never a person's name.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from cmp.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from cmp.core.logging import get_logger
from cmp.db.repositories import retention as repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event

log = get_logger("cmp.retention")

Row = dict[str, Any]

OUTCOMES = ("erased", "anonymised", "kept", "not_held")
_OPEN = ("open", "sent_back")
#: The fewest days anybody is given to answer.
_LEAST_DAYS = 7


async def action_view(a: Row) -> Row:
    """As served: `reason`, `sent_back_reason` and the names stay sealed - the
    console and the portal open them in the browser, as every sealed field."""
    return {
        "action_uuid": a["action_uuid"],
        "review_uuid": a["review_uuid"],
        "reference": a["reference"],
        "review_kind": a["review_kind"],
        "kind": a["kind"],
        "label": a["label"],
        "channel": a["channel"],
        "assignee_name": a.get("user_name"),
        "status": a["status"],
        "outcome": a["outcome"],
        "reason": a["reason"],
        "keep_until": a["keep_until"],
        "reconsent": a["reconsent"],
        "due_at": a["due_at"],
        "answered_at": a["answered_at"],
        "answered_by_name": a.get("answered_by_name"),
        "accepted_at": a["accepted_at"],
        "accepted_by_name": a.get("accepted_by_name"),
        "sent_back_reason": a["sent_back_reason"],
        #: Proof the one asked attached (sealed name; its SHA-256).
        "evidence_name": a.get("evidence_name"),
        "evidence_hash": a.get("evidence_hash"),
        "overdue": a["status"] in _OPEN and a["due_at"] < datetime.now(UTC),
    }


async def _record(
    conn: Conn, event: str, action: Row | None, review: Row, actor: int | None, **detail: Any
) -> None:
    await audit.record(
        conn,
        event=event,
        entity_type="retention_review",
        entity_id=int(review["review_id"]),
        actor_user_id=actor,
        detail={
            "reference": review["reference"],
            **({"action": str(action["action_uuid"]), "kind": action["kind"]} if action else {}),
            **detail,
        },
    )


# ------------------------------------------------------------------ making them
async def open_actions(conn: Conn, review: Row) -> int:
    """Ask the people responsible, once the review calls for it. Idempotent:
    an action the review has already is not made again."""
    from cmp.domain import alerts

    setting = await repo.setting(conn)
    due = datetime.now(UTC) + timedelta(days=int(setting["action_days"]))
    made: list[int] = []
    office_id = int(review["office_id"])
    owner = await repo.owner_of(conn, review)
    active = review["project_status"] == "approved"

    if review["kind"] == "validity":
        # Only a live project can ask its people again; anything else is for
        # the office to know, not for anybody to answer.
        if not active:
            return 0
        if owner is not None:
            row = await repo.add_action(
                conn,
                review_id=review["review_id"],
                kind="owner",
                user_id=owner["id"],
                channel="console",
                label=str(owner["full_name"]),
                # Before the consents run out where there is time; a week at
                # least where they ran out lately, so nobody is overdue on asking.
                due_at=max(
                    min(due, review["first_due_at"] or due),
                    datetime.now(UTC) + timedelta(days=_LEAST_DAYS),
                ),
                office_id=office_id,
            )
            if row:
                made.append(int(row["action_id"]))
                await repo.set_review(conn, int(review["review_id"]), reconsent="asked")
    else:
        if owner is not None:
            row = await repo.add_action(
                conn,
                review_id=review["review_id"],
                kind="owner",
                user_id=owner["id"],
                channel="console",
                label=str(owner["full_name"]),
                due_at=due,
                office_id=office_id,
            )
            if row:
                made.append(int(row["action_id"]))
        for p in await repo.processors_holding(conn, int(review["review_id"])):
            user_id = p["respondent_user_id"] or p["category_respondent_id"]
            channel = "console" if user_id else ("link" if p["respondent_id"] else "none")
            row = await repo.add_action(
                conn,
                review_id=review["review_id"],
                kind="processor",
                processor_id=p["processor_id"],
                respondent_id=p["respondent_id"],
                user_id=user_id,
                channel=channel,
                label=str(p["legal_name"]),
                due_at=due,
                office_id=office_id,
            )
            if row:
                made.append(int(row["action_id"]))
    if made:
        if review["status"] in ("upcoming", "due"):
            await repo.set_review(conn, int(review["review_id"]), status="in_progress")
        await _record(conn, Event.RETENTION_ACTIONS_OPENED, None, review, None, count=len(made))
        for action_id in made:
            action = await _action_by_id(conn, review, action_id)
            if action is not None:
                await alerts.retention_action_asked(conn, action=action, review=review)
    return len(made)


async def _action_by_id(conn: Conn, review: Row, action_id: int) -> Row | None:
    for a in await repo.actions_of(conn, int(review["review_id"])):
        if int(a["action_id"]) == action_id:
            return a
    return None


# --------------------------------------------------------------- answering
async def mine(conn: Conn, user_id: int) -> list[Row]:
    return [await action_view(a) for a in await repo.actions_for_user(conn, user_id)]


async def _loaded(conn: Conn, action_uuid: str) -> tuple[Row, Row]:
    action = await repo.action_by_uuid(conn, action_uuid)
    if action is None:
        raise NotFound("Retention action")
    review = await repo.review_by_id(conn, int(action["review_id"]))
    assert review is not None
    return action, review


async def detail_for_holder(conn: Conn, action_uuid: str, *, user_id: int | None) -> Row:
    """What the one asked reads: the review in brief - project, purpose, how
    many people, when it fell due - and their own action. No names."""
    from cmp.domain.retention.service import review_view

    action, review = await _loaded(conn, action_uuid)
    if user_id is not None and action["user_id"] != user_id:
        raise NotFound("Retention action")
    view = review_view(review)
    return {
        "action": await action_view(action),
        "review": {
            k: view[k]
            for k in (
                "reference",
                "kind",
                "project_name",
                "is_activity",
                "purpose_code",
                "purpose_name",
                "people",
                "first_due_at",
                "last_due_at",
                "retention_days",
                "validity_days",
                "status",
            )
        },
    }


async def answer(
    conn: Conn,
    action_uuid: str,
    *,
    user_id: int | None,
    outcome: str | None,
    reason: str | None,
    keep_until: date | None,
    reconsent: bool | None,
    by_link: bool = False,
) -> Row:
    """The one asked answers. `user_id` None: answered by a link."""
    action, review = await _loaded(conn, action_uuid)
    if not by_link and action["user_id"] != user_id:
        raise NotFound("Retention action")
    if action["status"] not in _OPEN:
        raise Conflict("This action has been answered already.", code="answered")
    if review["status"] == "closed":
        raise Conflict("This review is closed.", code="closed")
    note = (reason or "").strip() or None
    if review["kind"] == "validity":
        if reconsent is None:
            raise ValidationFailed(
                "Say whether these people should be asked to consent again.", field="reconsent"
            )
        if reconsent and await repo_live_link(conn, review) is None:
            raise ValidationFailed(
                "The project has no live consent link to send. Create one, then answer again.",
                field="reconsent",
            )
        cols: dict[str, Any] = {"outcome": "reviewed", "reconsent": reconsent, "reason": note}
    else:
        if outcome not in OUTCOMES:
            raise ValidationFailed("Choose what was done.", field="outcome")
        if outcome in ("anonymised", "kept") and not note:
            raise ValidationFailed(
                "Say why: anonymising instead of erasing, and keeping, each need a reason.",
                field="reason",
            )
        if outcome == "kept" and (keep_until is None or keep_until <= datetime.now(UTC).date()):
            raise ValidationFailed(
                "Give the date it will be looked at again, after today.", field="keep_until"
            )
        cols = {
            "outcome": outcome,
            "reason": note,
            "keep_until": keep_until if outcome == "kept" else None,
        }
    await repo.set_action(
        conn,
        int(action["action_id"]),
        status="answered",
        answered_at=datetime.now(UTC),
        answered_by=None if by_link else user_id,
        **cols,
    )
    await _record(
        conn,
        Event.RETENTION_ACTION_ANSWERED,
        action,
        review,
        None if by_link else user_id,
        outcome=cols["outcome"],
        channel="link" if by_link else "console",
        **({"reconsent": reconsent} if review["kind"] == "validity" else {}),
    )
    from cmp.domain import alerts

    await alerts.retention_action_answered(conn, review=review, label=str(action["label"]))
    fresh = await repo.action_by_uuid(conn, action_uuid)
    assert fresh is not None
    return await action_view(fresh)


async def repo_live_link(conn: Conn, review: Row) -> str | None:
    """The project's live consent link, as a person would open it - or None."""
    from cmp.core.portal_address import portal_base
    from cmp.core.security import unseal_token

    sealed = await repo.live_link_sealed(conn, int(review["project_id"]))
    if sealed is None:
        return None
    return f"{portal_base()}/c/{unseal_token(sealed)}"


# ------------------------------------------------------------- the office
async def accept(conn: Conn, review_uuid: str, action_uuid: str, *, actor_id: int) -> Row:
    from cmp.domain import alerts

    action, review = await _loaded(conn, action_uuid)
    if str(review["review_uuid"]) != review_uuid:
        raise NotFound("Retention action")
    if action["status"] != "answered":
        raise Conflict("Only an answer can be accepted.", code="not_answered")
    await repo.set_action(
        conn,
        int(action["action_id"]),
        status="accepted",
        accepted_at=datetime.now(UTC),
        accepted_by=actor_id,
    )
    await _record(conn, Event.RETENTION_ACTION_ACCEPTED, action, review, actor_id)
    if review["kind"] == "validity" and action["kind"] == "owner":
        if action["reconsent"]:
            link = await repo_live_link(conn, review)
            if link is None:
                raise Conflict(
                    "The project has no live consent link any more. Create one, then accept.",
                    code="no_link",
                )
            invited = await alerts.retention_reconsent_invitations(conn, review=review, link=link)
            await repo.set_review(conn, int(review["review_id"]), reconsent="sent")
            await _record(
                conn, Event.RETENTION_RECONSENT_SENT, action, review, actor_id, people=invited
            )
        else:
            await repo.set_review(conn, int(review["review_id"]), reconsent="declined")
    fresh = await repo.action_by_uuid(conn, action_uuid)
    assert fresh is not None
    return await action_view(fresh)


async def send_back(
    conn: Conn, review_uuid: str, action_uuid: str, *, reason: str, actor_id: int
) -> Row:
    from cmp.domain import alerts

    action, review = await _loaded(conn, action_uuid)
    if str(review["review_uuid"]) != review_uuid:
        raise NotFound("Retention action")
    if action["status"] != "answered":
        raise Conflict("Only an answer can be sent back.", code="not_answered")
    if not reason.strip():
        raise ValidationFailed("Say what is missing.", field="reason")
    setting = await repo.setting(conn)
    await repo.set_action(
        conn,
        int(action["action_id"]),
        status="sent_back",
        sent_back_reason=reason.strip(),
        due_at=datetime.now(UTC) + timedelta(days=int(setting["action_days"])),
        escalated_at=None,
    )
    await _record(conn, Event.RETENTION_ACTION_SENT_BACK, action, review, actor_id)
    fresh = await repo.action_by_uuid(conn, action_uuid)
    assert fresh is not None
    await alerts.retention_action_sent_back(conn, action=fresh, review=review)
    return await action_view(fresh)


async def mark_not_needed(conn: Conn, review_uuid: str, action_uuid: str, *, actor_id: int) -> Row:
    """An action the office decides nobody need answer: a processor found by
    the records that never had the data, or one with nobody to ask."""
    action, review = await _loaded(conn, action_uuid)
    if str(review["review_uuid"]) != review_uuid:
        raise NotFound("Retention action")
    if action["status"] not in _OPEN:
        raise Conflict("This action has been answered.", code="answered")
    await repo.set_action(conn, int(action["action_id"]), status="not_needed")
    await _record(conn, Event.RETENTION_ACTION_NOT_NEEDED, action, review, actor_id)
    fresh = await repo.action_by_uuid(conn, action_uuid)
    assert fresh is not None
    return await action_view(fresh)


async def close(conn: Conn, review_uuid: str, *, note: str | None, actor_id: int) -> Row:
    from cmp.domain.retention.service import review as load

    review = await load(conn, review_uuid)
    if review["status"] == "closed":
        raise Conflict("This review is closed already.", code="closed")
    actions = await repo.actions_of(conn, int(review["review_id"]))
    waiting = [a for a in actions if a["status"] not in ("accepted", "not_needed")]
    if waiting:
        raise Conflict(
            f"{len(waiting)} action(s) are still to be answered or accepted.",
            code="actions_open",
        )
    if review["kind"] == "retention" and review["status"] == "upcoming":
        raise Conflict("A review that has not fallen due cannot be closed.", code="not_due")
    await repo.set_review(
        conn,
        int(review["review_id"]),
        status="closed",
        closed_at=datetime.now(UTC),
        closed_by=actor_id,
        close_note=(note or "").strip() or None,
    )
    await _record(
        conn,
        Event.RETENTION_REVIEW_CLOSED,
        None,
        review,
        actor_id,
        outcomes=sorted({str(a["outcome"]) for a in actions if a["outcome"]}),
    )
    return await load(conn, review_uuid)


def may_answer(action: Row, user_id: int) -> None:
    if action["user_id"] != user_id:
        raise Forbidden("This action is not yours to answer")


# ------------------------------------------------------------- the proof
async def attach(
    conn: Conn,
    action_uuid: str,
    *,
    user_id: int | None,
    ref: str,
    digest: str,
    name: str | None,
    by_link: bool = False,
) -> Row:
    """The one asked attaches proof - a deletion log, a screenshot, a letter -
    before they answer, or with a new answer after a send-back. One file per
    action: a new one replaces the last. Never once the answer is in."""
    action, review = await _loaded(conn, action_uuid)
    if not by_link and action["user_id"] != user_id:
        raise NotFound("Retention action")
    if action["status"] not in _OPEN or review["status"] == "closed":
        raise Conflict("Proof is added before the answer is sent.", code="answered")
    await repo.set_action(
        conn,
        int(action["action_id"]),
        evidence_ref=ref,
        evidence_hash=digest,
        evidence_name=name or "proof",
    )
    await _record(
        conn,
        Event.RETENTION_EVIDENCE_ADDED,
        action,
        review,
        None if by_link else user_id,
        channel="link" if by_link else "console",
        sha256=digest,
    )
    fresh = await repo.action_by_uuid(conn, action_uuid)
    assert fresh is not None
    return await action_view(fresh)


async def evidence(
    conn: Conn,
    action_uuid: str,
    *,
    actor_id: int,
    review_uuid: str | None = None,
    owner_id: int | None = None,
) -> tuple[bytes, str, str]:
    """The proof on an action: for the review's officer (`review_uuid`), or the
    one who was asked (`owner_id`). Every read on the trail."""
    from cmp.infrastructure.dkms import unseal_value
    from cmp.infrastructure.storage.service import storage

    action, review = await _loaded(conn, action_uuid)
    if review_uuid is not None and str(review["review_uuid"]) != review_uuid:
        raise NotFound("Retention action")
    if owner_id is not None and action["user_id"] != owner_id:
        raise NotFound("Retention action")
    if not action.get("evidence_ref"):
        raise NotFound("Proof")
    payload = storage().read(str(action["evidence_ref"]))
    await _record(conn, Event.RETENTION_EVIDENCE_DOWNLOADED, action, review, actor_id)
    name = await unseal_value("retention_action", "evidence_name", action.get("evidence_name"))
    return payload, str(name or f"{review['reference']}-proof"), str(action["evidence_hash"] or "")
