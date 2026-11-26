"""Retention reviews (2026-11-26, ADR 0047): who falls due, and the register.

Two clocks per purpose, two kinds of review:

* **validity** - a consent's validity is running out. The people responsible
  are warned ahead; at the end the night's quarantine stands as before
  (`apply_retention_lapse`, the product owner: kept as the first step); and,
  where the project is still active, its owner may confirm that the people be
  asked to consent again.
* **retention** - the data must go: the consent's end (its withdrawal, or its
  validity) plus the purpose's retention period. Everyone holding the data is
  asked to erase it - or anonymise it, or keep it, each with its reason.

A review is one project or HR activity, one purpose and one month: a cohort,
not a person. Its own register for the office's officer - never a rights or a
breach ticket.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from cmp.core.errors import NotFound, ValidationFailed
from cmp.core.logging import get_logger
from cmp.db.repositories import retention as repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event

log = get_logger("cmp.retention")

Row = dict[str, Any]

KINDS = ("validity", "retention")
STATUSES = ("upcoming", "due", "in_progress", "closed")
#: A validity that ran out longer ago than this is past asking anybody about:
#: the night's quarantine has acted on it, and there is nobody to renew.
VALIDITY_LOOKBACK_DAYS = 30


# ---------------------------------------------------------------- settings
def _setting_view(row: Row) -> Row:
    return {
        "reminder_days": sorted((int(d) for d in row["reminder_days"]), reverse=True),
        "notice_hours": int(row["notice_hours"]),
        "action_days": int(row["action_days"]),
        "escalate_after_days": int(row["escalate_after_days"]),
        "updated_at": row["updated_at"] if row["updated_by_name"] is not None else None,
        "updated_by_name": row["updated_by_name"],
    }


async def settings_view(conn: Conn) -> Row:
    return _setting_view(await repo.setting(conn))


async def save_settings(
    conn: Conn,
    *,
    reminder_days: list[int],
    notice_hours: int,
    action_days: int,
    escalate_after_days: int,
    actor_id: int,
) -> Row:
    days = sorted(set(reminder_days), reverse=True)
    if not days or len(days) > 5 or any(d < 1 or d > 365 for d in days):
        raise ValidationFailed(
            "Give one to five reminder days, each from 1 to 365.", field="reminder_days"
        )
    if not 0 <= notice_hours <= 720:
        raise ValidationFailed("The notice is given 0 to 720 hours ahead.", field="notice_hours")
    if not 1 <= action_days <= 365 or not 1 <= escalate_after_days <= 365:
        raise ValidationFailed("Give a number of days from 1 to 365.", field="action_days")
    await repo.save_setting(
        conn,
        actor_id=actor_id,
        reminder_days=days,
        notice_hours=notice_hours,
        action_days=action_days,
        escalate_after_days=escalate_after_days,
    )
    await audit.record(
        conn,
        event=Event.RETENTION_SETTINGS_CHANGED,
        entity_type="retention_setting",
        entity_id=1,
        actor_user_id=actor_id,
        detail={
            "reminder_days": days,
            "notice_hours": notice_hours,
            "action_days": action_days,
            "escalate_after_days": escalate_after_days,
        },
    )
    return await settings_view(conn)


# ------------------------------------------------------------------- sweep
async def sweep(conn: Conn) -> dict[str, int]:
    """Find who falls due, as far ahead as the earliest reminder; make the
    reviews and add the people. Run across both offices."""
    setting = await repo.setting(conn)
    horizon = max(int(d) for d in setting["reminder_days"])
    counts = await repo.sweep(conn, horizon_days=horizon, lookback_days=VALIDITY_LOOKBACK_DAYS)
    log.info("retention.swept", **counts)
    return counts


# ---------------------------------------------------------------- the views
def _interval_days(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, timedelta):
        return value.days
    return None


def review_view(row: Row) -> Row:
    return {
        "review_uuid": row["review_uuid"],
        "reference": row["reference"],
        "kind": row["kind"],
        "status": row["status"],
        "office": row["office"],
        "cohort": row["cohort"],
        "project_uuid": row["project_uuid"],
        "project_name": row["project_name"],
        "project_status": row["project_status"],
        "is_activity": bool(row["is_activity"]),
        "purpose_code": row["purpose_code"],
        "purpose_name": row["purpose_name"],
        "retention_days": _interval_days(row["retention_period"]),
        "validity_days": _interval_days(row["consent_validity_period"]),
        "lapse_behaviour": row["lapse_behaviour"],
        "notify_before_erasure": bool(row["notify_before_erasure"]),
        "people": int(row["people"]),
        "held": int(row["held"]),
        "renewed": int(row["renewed"]),
        "first_due_at": row["first_due_at"],
        "last_due_at": row["last_due_at"],
        "actions": int(row["actions"]),
        "actions_open": int(row["actions_open"]),
        "actions_to_review": int(row["actions_to_review"]),
        "reconsent": row["reconsent"],
        "opened_at": row["opened_at"],
        "closed_at": row["closed_at"],
        "closed_by_name": row["closed_by_name"],
        "close_note": row["close_note"],
    }


async def register(conn: Conn, *, kind: str | None, status: str | None) -> list[Row]:
    if kind and kind not in KINDS:
        raise ValidationFailed("Choose validity or retention.", field="kind")
    if status and status not in STATUSES:
        raise ValidationFailed("Not a status a review has.", field="status")
    return [review_view(r) for r in await repo.reviews(conn, kind=kind, status=status)]


async def review(conn: Conn, review_uuid: str) -> Row:
    row = await repo.review_by_uuid(conn, review_uuid)
    if row is None:
        raise NotFound("Retention review")
    return row


async def detail(conn: Conn, review_uuid: str) -> Row:
    """A review with its people's dates and its actions. People are counted
    and their consents listed by number: names stay where they are kept."""
    from cmp.domain.retention import actions as acts

    row = await review(conn, review_uuid)
    people = await repo.people_of(conn, int(row["review_id"]), state=None)
    return {
        **review_view(row),
        "people_list": [
            {
                "consent_uuid": p["consent_uuid"],
                "consent_no": p["consent_id"],
                "person_no": p["auth_user_id"],
                "due_at": p["due_at"],
                "ended_by": p["ended_by"],
                "state": p["state"],
                "notified_at": p["notified_at"],
                "invited_at": p["invited_at"],
            }
            for p in people[:500]
        ],
        "actions_list": [
            await acts.action_view(a) for a in await repo.actions_of(conn, int(row["review_id"]))
        ],
    }


# --------------------------------------------------------------- the day
async def daily(conn: Conn) -> dict[str, int]:
    """The night's work, across both offices: who falls due; ask the people
    responsible; remind ahead at the days set; remind a holder when their date
    passes; tell the office when an action is long overdue; and tell each
    person, where the purpose asks for it, before their data is erased."""
    from datetime import UTC, datetime

    from cmp.domain import alerts
    from cmp.domain.retention import actions as acts

    counts = await sweep(conn)
    setting = await repo.setting(conn)
    opened = 0
    for row in await repo.reviews_to_open(conn):
        opened += await acts.open_actions(conn, row)

    reminded = 0
    days = sorted((int(d) for d in setting["reminder_days"]), reverse=True)
    now = datetime.now(UTC)
    for row in await repo.reviews_to_remind(conn):
        first = row["first_due_at"]
        if first is None:
            continue
        left = (first - now).days
        crossed = [d for d in days if left <= d]
        if not crossed:
            continue
        nearest = min(crossed)
        if nearest in (row["reminded_days"] or []):
            continue
        await alerts.retention_review_reminder(conn, review=row, days_left=max(left, 0))
        await repo.set_review(
            conn,
            int(row["review_id"]),
            reminded_days=sorted(set(crossed) | set(row["reminded_days"] or [])),
        )
        reminded += 1

    chased = 0
    for a in await repo.actions_past_due(conn):
        review = await repo.review_by_id(conn, int(a["review_id"]))
        if review is not None:
            await alerts.retention_action_overdue_holder(conn, action=a, review=review)
        await repo.set_action(conn, int(a["action_id"]), last_reminded_at=now)
        chased += 1

    escalated = 0
    for a in await repo.actions_to_escalate(conn, int(setting["escalate_after_days"])):
        review = await repo.review_by_id(conn, int(a["review_id"]))
        if review is not None:
            await alerts.retention_action_escalated(conn, action=a, review=review)
        await repo.set_action(conn, int(a["action_id"]), escalated_at=now)
        escalated += 1

    told = await alerts.retention_erasure_notices(
        conn, people=await repo.people_to_notify(conn, int(setting["notice_hours"]))
    )
    return {
        **counts,
        "actions_opened": opened,
        "reminders": reminded,
        "chased": chased,
        "escalated": escalated,
        "people_told": told,
    }
