"""Telling the people a breach touched (S3-03).

Rule 7(1): each affected principal is told, concisely, clearly and plainly and
without delay, five things - what happened, the consequences likely for her,
what has been and is being done, what she can do, and whom to ask - through
her user account and the contact she registered.

* **Nothing sends on its own.** The DPO drafts the words, approves them - and
  approval is refused while any of the five is empty - and presses Send.
* **Her account first.** Sending writes the notice to her account at once, in
  the same transaction: an audit row against her, which is how the portal's
  notifications are derived, and a delivery recorded `delivered`. Her email and
  her mobile are queued as deliveries, and the worker sends each after the
  commit (`dispatch_optional`) and records what happened.
* **A resend never duplicates.** Send writes only what is missing for the
  latest approved version: people newly listed, channels never tried, and a new
  attempt where the last one failed. A delivery still queued long after the
  worker would have finished with it (`STALE_AFTER`) was lost before the worker
  saw it, and is queued again - the same delivery, no new row.
  `breach_notice_delivery_once` holds it when two sends race.
* **The words are sealed**, like every narrative about a breach, and opened
  where they are read: the console, her portal, and `deliver()` in the worker.
* **An updated notice is a new version**, approved like the first and sent to
  everyone listed, the people already notified included.
* **The principals' duty completes by delivery**, never by hand: when every
  listed person has a version whose every channel reached an outcome -
  delivered, or failed after the worker's retries. People listed after that
  reopen it.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from cmp.core.errors import Conflict, NotFound, ValidationFailed
from cmp.db.repositories import breach_lists as list_repo
from cmp.db.repositories import breach_notices as repo
from cmp.db.repositories import breaches as breach_repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.domain.breach import clock, service
from cmp.domain.breach.clock import Duty, EventKind, State

Row = dict[str, Any]

CONTENTS = repo.CONTENTS

#: How long a delivery may sit queued before Send queues it again. The worker
#: retries a message for about two and a half minutes; one still queued long
#: after that was never picked up - the broker lost it after the commit
#: (ADR 0012) - and nothing else would ever send it.
STALE_AFTER = timedelta(minutes=15)

#: What each content is, as the DPO reads it and as a refusal names it.
LABELS: dict[str, str] = {
    "what_happened": "What happened - its nature, extent and timing (Rule 7(1)(a))",
    "consequences": "The consequences likely for her (Rule 7(1)(b))",
    "measures": "What has been done, and is being done, to limit them (Rule 7(1)(c))",
    "protective_steps": "What she can do to protect herself (Rule 7(1)(d))",
    "contact": "Who to contact with questions (Rule 7(1)(e))",
}


def _words(words: dict[str, str | None]) -> dict[str, str | None]:
    """Each content as written, or None where nothing is: a word not yet
    written is NULL, so completeness reads through the seal."""
    return {c: (words.get(c) or "").strip() or None for c in CONTENTS}


async def _notice(conn: Conn, breach: Row, notice_uuid: str) -> Row:
    notice = await repo.by_uuid(conn, int(breach["breach_id"]), notice_uuid)
    if not notice:
        raise NotFound("Notice")
    return notice


async def draft(
    conn: Conn, *, breach_uuid: str, words: dict[str, str | None], actor_id: int
) -> Row:
    """Start the next version. One draft at a time."""
    breach = await service.locked_open(conn, breach_uuid)
    if any(v["approved_at"] is None for v in await repo.versions(conn, int(breach["breach_id"]))):
        raise Conflict("A draft is already open; edit or approve it", code="notice_draft_open")
    made = await repo.create_draft(
        conn, int(breach["breach_id"]), words=_words(words), created_by=actor_id
    )
    notice = await _notice(conn, breach, str(made["notice_uuid"]))
    await service.record_event(
        conn,
        breach,
        Event.BREACH_NOTICE_DRAFTED,
        actor_id=actor_id,
        detail={"version": int(notice["version"])},
    )
    return await overview(conn, breach_uuid=breach_uuid)


async def edit(
    conn: Conn, *, breach_uuid: str, notice_uuid: str, words: dict[str, str | None], actor_id: int
) -> Row:
    breach = await service.locked_open(conn, breach_uuid)
    notice = await _notice(conn, breach, notice_uuid)
    if notice["approved_at"] is not None:
        raise Conflict(
            "An approved notice does not change; start a new version", code="notice_approved"
        )
    await repo.update_draft(conn, int(notice["notice_id"]), words=_words(words))
    await service.record_event(
        conn,
        breach,
        Event.BREACH_NOTICE_EDITED,
        actor_id=actor_id,
        detail={"version": int(notice["version"])},
    )
    return await overview(conn, breach_uuid=breach_uuid)


async def approve(conn: Conn, *, breach_uuid: str, notice_uuid: str, actor_id: int) -> Row:
    """Freeze the words. Refused while any of the five is empty."""
    breach = await service.locked_open(conn, breach_uuid)
    notice = await _notice(conn, breach, notice_uuid)
    if notice["approved_at"] is not None:
        raise Conflict("This notice is already approved", code="notice_approved")
    missing = [c for c in CONTENTS if notice[c] is None]
    if missing:
        raise ValidationFailed(
            "A notice says all five things Rule 7(1) requires. Missing: "
            + "; ".join(LABELS[c] for c in missing),
            field=missing[0],
            details={"missing": missing},
        )
    await repo.approve(conn, int(notice["notice_id"]), approved_by=actor_id)
    await service.record_event(
        conn,
        breach,
        Event.BREACH_NOTICE_APPROVED,
        actor_id=actor_id,
        detail={"version": int(notice["version"])},
    )
    return await overview(conn, breach_uuid=breach_uuid)


async def send(conn: Conn, *, breach_uuid: str, actor_id: int) -> Row:
    """Send the latest approved version to everyone listed who lacks it."""
    from cmp.tasks.dispatch import dispatch_optional
    from cmp.tasks.notifications.breach import send_breach_notice

    breach = await service.locked_open(conn, breach_uuid)
    # Drafting and approving may run during validation; telling anyone may not.
    service.require_recorded(breach, "anyone is notified")
    breach_id = int(breach["breach_id"])
    notice = await repo.latest_approved(conn, breach_id)
    if notice is None:
        raise Conflict("Approve a notice before anything is sent", code="no_approved_notice")
    people = await repo.recipients(conn, breach_id)
    if not people:
        raise Conflict(
            "Nobody is listed as touched yet. Confirm who it touched first", code="nobody_listed"
        )
    notice_id = int(notice["notice_id"])
    states = await repo.latest_states(conn, breach_id, notice_id)
    written = queued = retried = requeued = 0
    stale_before = datetime.now(UTC) - STALE_AFTER
    for person in people:
        to = repo.recipient_of(person)
        # A contact with no account (0045) has no account to write to: email
        # and SMS are how it hears.
        pid = to[1] if to[0] == "user" else None
        if (
            pid is not None
            and (to, "portal") not in states
            and await repo.add_delivery(
                conn, notice_id, to, channel="portal", attempt=1, status="delivered"
            )
        ):
            written += 1
            # Her account: the portal's notifications are her audit rows.
            await audit.record(
                conn,
                event=Event.BREACH_NOTICE_DELIVERED,
                entity_type="breach_notice",
                entity_id=notice_id,
                subject_user_id=pid,
                actor_user_id=actor_id,
                detail={"reference": breach["reference"], "version": int(notice["version"])},
            )
        for channel, reachable in (("email", person["has_email"]), ("sms", person["has_mobile"])):
            if not reachable:
                continue
            last = states.get((to, channel))
            if last is None:
                attempt = 1
            elif last["status"] == "failed":
                attempt = int(last["attempt"]) + 1
            elif last["status"] == "queued" and last["recorded_at"] <= stale_before:
                # Lost before the worker: queue the same delivery again. Its
                # task checks the attempt has no outcome yet before sending.
                again = await repo.queued_delivery(
                    conn, notice_id, to, channel=channel, attempt=int(last["attempt"])
                )
                if again:
                    requeued += 1
                    dispatch_optional(send_breach_notice, str(again["delivery_uuid"]))
                continue
            else:
                continue  # queued recently, or delivered: nothing to add
            row = await repo.add_delivery(
                conn, notice_id, to, channel=channel, attempt=attempt, status="queued"
            )
            if row:
                queued += 1
                retried += attempt > 1
                dispatch_optional(send_breach_notice, str(row["delivery_uuid"]))
    await service.record_event(
        conn,
        breach,
        Event.BREACH_NOTICE_SENT,
        actor_id=actor_id,
        detail={
            "version": int(notice["version"]),
            "accounts": written,
            "queued": queued,
            "retried": retried,
            "requeued": requeued,
        },
    )
    await settle(conn, breach, actor_id=actor_id)
    return await overview(conn, breach_uuid=breach_uuid)


async def listed_count(conn: Conn, breach_id: int) -> int:
    """Everyone the notice is owed to: accounts listed, and contacts with no
    account from an uploaded list (0045)."""
    return await breach_repo.count_affected(conn, breach_id) + await list_repo.count_contacts(
        conn, breach_id
    )


async def settle(conn: Conn, breach: Row, *, actor_id: int | None) -> bool:
    """Complete the principals' duty if every listed person has been notified.

    The caller holds the breach row. Returns whether it completed now.
    """
    breach_id = int(breach["breach_id"])
    found = (await service.duties_of(conn, breach_id)).get(Duty.PRINCIPALS)
    if not found or found[1]["state"] != State.OUTSTANDING:
        return False
    listed = await listed_count(conn, breach_id)
    if listed == 0 or await repo.unnotified(conn, breach_id) > 0:
        return False
    await breach_repo.add_obligation_event(
        conn,
        int(found[0]["obligation_id"]),
        kind=EventKind.COMPLETED,
        occurred_at=datetime.now(UTC),
        recorded_by=actor_id,
    )
    await service.record_event(
        conn,
        breach,
        Event.BREACH_OBLIGATION_COMPLETED,
        actor_id=actor_id,
        detail={"duty": Duty.PRINCIPALS.value, "notified": listed, "by": "delivery"},
    )
    return True


async def reopen_if_done(conn: Conn, breach: Row, *, newly_listed: int, actor_id: int) -> None:
    """People listed after the principals' duty completed are owed a notice too."""
    if newly_listed == 0:
        return
    found = (await service.duties_of(conn, int(breach["breach_id"]))).get(Duty.PRINCIPALS)
    if not found or found[1]["state"] != State.DONE:
        return
    await breach_repo.add_obligation_event(
        conn, int(found[0]["obligation_id"]), kind=EventKind.REOPENED, recorded_by=actor_id
    )
    await service.record_event(
        conn,
        breach,
        Event.BREACH_OBLIGATION_REOPENED,
        actor_id=actor_id,
        detail={"duty": Duty.PRINCIPALS.value, "newly_listed": newly_listed},
    )


# ------------------------------------------------------------------ the worker


async def job(conn: Conn, delivery_uuid: str) -> Row | None:
    """What the worker sends for one queued delivery, or None if there is
    nothing to do - an unknown uuid, or an attempt that already has an outcome."""
    row = await repo.job(conn, delivery_uuid)
    if not row or row["status"] != "queued" or row["settled"]:
        return None
    return row


async def record_result(
    conn: Conn, *, delivery_uuid: str, status: str, detail: dict[str, Any]
) -> None:
    """The worker's outcome for one attempt, then the duty re-read."""
    row = await repo.job(conn, delivery_uuid)
    if not row:
        return
    await breach_repo.lock(conn, int(row["breach_id"]))
    await repo.add_delivery(
        conn,
        int(row["notice_id"]),
        repo.recipient_of(row),
        channel=str(row["channel"]),
        attempt=int(row["attempt"]),
        status=status,
        detail=detail,
    )
    breach = await breach_repo.by_breach_id(conn, int(row["breach_id"]))
    assert breach is not None
    await settle(conn, breach, actor_id=None)


# -------------------------------------------------------------------- reading


async def overview(conn: Conn, *, breach_uuid: str) -> Row:
    """Every version, and the account of who received which, by channel."""
    breach = await service.require(conn, breach_uuid)
    breach_id = int(breach["breach_id"])
    versions = await repo.versions(conn, breach_id)
    return {
        "versions": [{**v, "state": "approved" if v["approved_at"] else "draft"} for v in versions],
        "account": await repo.account(conn, breach_id),
        "failures": await repo.failures(conn, breach_id),
        "listed": await listed_count(conn, breach_id),
        # Of them, contacts with no account (0045): email and SMS only.
        "contacts": await list_repo.count_contacts(conn, breach_id),
        "unnotified": await repo.unnotified(conn, breach_id),
        "contents": [{"key": c, "label": LABELS[c]} for c in CONTENTS],
        "duty": clock.LABELS[Duty.PRINCIPALS],
        # The server's word on why Send must wait, for the console to show.
        "send_blocked_by": service.not_recorded_reason(breach, "anyone is notified"),
    }


async def for_subject(conn: Conn, *, user_id: int) -> list[Row]:
    """The notices written to her account."""
    return await repo.for_person(conn, user_id)


async def account_for_report(conn: Conn, *, breach_uuid: str) -> Row:
    """Rule 7(2)(b)(vi): the account of notices, for the Board's report.

    Always present, and in words: a report drafted before any notice went says
    so, rather than leaving the item out.
    """
    breach = await service.require(conn, breach_uuid)
    breach_id = int(breach["breach_id"])
    rows = await repo.account(conn, breach_id)
    approved = {
        int(v["version"]): v["approved_at"]
        for v in await repo.versions(conn, breach_id)
        if v["approved_at"] is not None
    }
    by_version: dict[int, dict[str, dict[str, int]]] = {}
    for r in rows:
        channels = by_version.setdefault(int(r["version"]), {})
        counts = channels.setdefault(str(r["channel"]), {"delivered": 0, "queued": 0, "failed": 0})
        counts[str(r["status"])] = int(r["people"])
    listed = await listed_count(conn, breach_id)
    contacts = await list_repo.count_contacts(conn, breach_id)
    notified = listed - await repo.unnotified(conn, breach_id)
    if not rows:
        statement = "No notice has yet been sent to the Data Principals affected. " + (
            f"{listed} are listed as affected." if listed else "Nobody is yet listed as affected."
        )
    else:
        statement = (
            f"{notified} of the {listed} Data Principals listed as affected have been notified: "
            "every email and SMS to them has an outcome, delivered or failed after retrying"
            + (
                f", and the notice is in the account of each of the {listed - contacts} "
                f"with one; the other {contacts} have no account and were written to by "
                "email and SMS."
                if contacts
                else ", and the notice is in each one's account."
            )
        )
    return {
        "sent": bool(rows),
        "statement": statement,
        "listed": listed,
        "notified": notified,
        "versions": [
            {
                "version": version,
                "approved_at": approved.get(version),
                "channels": [
                    {"channel": channel, **counts} for channel, counts in sorted(channels.items())
                ],
            }
            for version, channels in sorted(by_version.items())
        ],
    }
