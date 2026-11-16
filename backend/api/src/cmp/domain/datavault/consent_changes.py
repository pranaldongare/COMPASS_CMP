"""Every consent change DataVault is told of (0071, ADR 0039).

**What is sent.** A change to a consent that already existed: a withdrawal, in
full or in part, a consent given again after one, and a lapse - a granted
purpose whose validity has run out, by the retention sweep's own test
(`affirmative_action_at` + `consent_validity_period`, where the purpose's
lapse does something). A first consent is not a change: DataVault holds
nothing under it until a lab is sent the data. Every consent counts, on a
project or an HR activity alike (the product owner, 2026-11-13); where
DataVault holds nothing it answers that no asset was affected.

**What it says.** The platform names the action, and it is never "delete":
- withdrawn, partly withdrawn, lapsed: `restrict`. The person is told that
  withdrawing "does not delete data already collected"; deletion only ever
  goes through an erasure request the office has decided (`erasures`).
- granted again: `lift_restriction`.
Every message carries the whole state - every purpose still granted - so the
latest is the truth and an earlier one still unsent is set aside.

**Nobody presses anything, and nothing in the consent flow depends on it.**
A withdrawal is saved as it always was. The worker then reads the consents it
has not read yet (`datavault_consent_noted`), chain by chain - a chain is one
person and one notice - and works out, from what DataVault was last told and
what the consents now say, the one message that brings it up to date. It runs
straight after a consent is saved (`nudge`) and every minute besides, so a
message is not lost when the broker is. Reading a chain takes the person's
capture lock without waiting: a capture or a withdrawal in progress is left
to finish, and the next run reads what it wrote. (A withdrawal does not take
that lock; it needs none: what it has not committed is not read, and only the
consents actually read are marked read.)

Because the message is worked out from saved consents and not from the act
itself, reading several changes at once gives the same answer as reading them
one by one: each is applied in order to what DataVault holds, and only where
the chain ends up is sent.

**Where it starts.** Nothing on record when the administrator first switched
consent changes on is ever read (`consent_changes_after`), and a validity that
had run out by then is never reported (`consent_changes_since`): switching on
tells DataVault nothing about the past. What happens afterwards is told
whatever the consent's age - a withdrawal of a consent given years before, a
validity that runs out next month - and told whole, the past included, since
each message carries the whole state. Switched off and on again, the changes
made meanwhile are read then: where it starts is settled once.

**One label for a mixed change.** Reading several unread consents at once can
both take a purpose away and give another back. The message then says
`partly_withdrawn` and `restrict`, with every purpose now granted in
`purposes_granted` - the state is the truth, and of the two labels the careful
one is used.

**Delivery.** Tried until DataVault answers `applied`, `duplicate` or `stale`
- each means it has the message - with a growing wait; a refusal is tried
hourly, because it does not mend until somebody fixes it, and is logged as an
error each time. A run stops at the first try DataVault does not answer - a
timeout, no connection, a 5xx - since every other would only wait for the same,
and the worker has other work (sign-in codes among it); and it stops once it
has taken `DELIVERY_BUDGET`, well inside its lock. What it did not try is due
at the next run. A message is on the trail when it is queued and when it is
delivered: on the consent, against the person, and read with the project's.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from cmp.core.logging import get_logger
from cmp.db.repositories import datavault as repo
from cmp.db.sql import Conn
from cmp.domain.audit import service as audit
from cmp.domain.audit.service import Event
from cmp.domain.datavault import ids
from cmp.domain.datavault.connection import Link
from cmp.infrastructure import datavault as client

log = get_logger("cmp.datavault")

Row = dict[str, Any]

#: How many chains one run reads, and how many queued messages it delivers.
SCAN = 200
BATCH = 100
#: How many lapsed consents the nightly run reads at a time; it reads on
#: until none is left, up to `LAPSE_PAGES` pages.
LAPSE_PAGE = 500
LAPSE_PAGES = 100
#: The longest wait between tries.
MAX_WAIT = timedelta(hours=1)
#: The longest one run spends delivering: well inside its five-minute lock.
DELIVERY_BUDGET = timedelta(seconds=90)
#: Failures that mend by themselves: the wait grows from minutes.
PASSING = ("timeout", "unreachable")


def passing(failure: str) -> bool:
    """DataVault not answering, as against refusing: it mends by itself."""
    return failure in PASSING or failure.startswith("status_5")


def nudge() -> None:
    """A consent was saved: have the worker look now, not at the next minute.
    Queued when the caller's transaction commits. It can fail nothing - the
    minute's run is the net under it - so nothing here may raise."""
    try:
        from cmp.tasks import datavault as tasks
        from cmp.tasks.dispatch import dispatch_optional

        dispatch_optional(tasks.deliver_consent_changes)
    except Exception as failed:
        log.warning("datavault.nudge_failed", error=type(failed).__name__)


# ---------------------------------------------------------- reading the chains
async def unread(conn: Conn, link: Link) -> list[Row]:
    """The chains with a consent not read yet, oldest first."""
    return await repo.unnoted_chains(conn, after=link.consent_changes_after, limit=SCAN)


async def _queue(
    conn: Conn,
    *,
    user_id: int,
    consent_id: int,
    root_id: int,
    change: str,
    before: set[str],
    after: set[str],
    effective_at: datetime,
) -> None:
    removed = before - after
    made = await repo.queue_change(
        conn,
        consent_id=consent_id,
        chain_root_id=root_id,
        change=change,
        action="lift_restriction" if change == "granted_again" else "restrict",
        granted=sorted(after),
        removed=sorted(removed),
        effective_at=effective_at,
    )
    await audit.record(
        conn,
        event=Event.DATAVAULT_CONSENT_CHANGE_QUEUED,
        entity_type="consent_artefact",
        entity_id=consent_id,
        subject_user_id=user_id,
        actor_user_id=None,
        detail={
            "project": await repo.project_uuid_of_consent(conn, consent_id),
            "sequence": int(made["change_id"]),
            "change": change,
            "action": "lift_restriction" if change == "granted_again" else "restrict",
            "purposes_granted": sorted(after),
            "purposes_removed": sorted(removed),
        },
    )


async def note_chain(conn: Conn, link: Link, *, user_id: int, notice_id: int) -> bool:
    """Read one chain's unread consents and queue what DataVault must hear.
    In a transaction of the caller's, one chain to each. Returns whether a
    message was queued."""
    if not await repo.try_lock_capture(conn, user_id=user_id, notice_id=notice_id):
        return False  # a capture or a withdrawal is in progress: the next run reads it
    links = await repo.chain(
        conn, user_id=user_id, notice_id=notice_id, after=link.consent_changes_after
    )
    fresh = [c for c in links if not c["noted"]]
    if not fresh:
        return False
    root = links[0]
    at = links.index(fresh[0])
    told = await repo.last_told(conn, int(root["consent_id"]))
    if told is not None:
        before = set(told)
    else:
        # Nothing told yet: DataVault goes by the consent the labs' assets
        # were tagged with - the one before the first change read here, or
        # the chain's first, which is not a change.
        known = links[at - 1] if at > 0 else root
        before = set(await repo.granted_codes(conn, int(known["consent_id"])))
    # Each unread consent in turn, applied to what DataVault holds.
    state = set(before)
    for c in fresh:
        if c is root:
            continue  # the first consent: where the chain starts
        granted = set(await repo.granted_codes(conn, int(c["consent_id"])))
        if c["is_withdrawal"]:
            # A withdrawal grants nothing. It copies the other grants forward,
            # those whose validity had run out too, so such a purpose stays
            # out; and it never lifts a restriction - what DataVault was told
            # is gone stays gone until she grants it again.
            previous = links[links.index(c) - 1]
            granted -= set(
                await repo.run_out_on(
                    conn, int(previous["consent_id"]), at=c["affirmative_action_at"]
                )
            )
            granted &= state
        state = granted
    await repo.note(conn, [int(c["consent_id"]) for c in fresh])
    removed, added = before - state, state - before
    if not removed and not added:
        return False  # nothing DataVault does not hold already
    head = links[-1]
    if removed and not state:
        change = "withdrawn"
    elif removed:
        change = "partly_withdrawn"
    else:
        change = "granted_again"
    await _queue(
        conn,
        user_id=user_id,
        consent_id=int(head["consent_id"]),
        root_id=int(root["consent_id"]),
        change=change,
        before=before,
        after=state,
        effective_at=head["affirmative_action_at"],
    )
    return True


async def lapsed(conn: Conn, link: Link, *, after_id: int = 0) -> list[Row]:
    """A page of the consents in force with a purpose whose validity has run
    out since consent changes were switched on, which DataVault still takes as
    granted - those after `after_id`, oldest first."""
    if link.consent_changes_since is None:
        return []  # never switched on: nothing is told
    return await repo.lapsed_unreported(
        conn, since=link.consent_changes_since, after_id=after_id, limit=LAPSE_PAGE
    )


async def note_lapse(conn: Conn, link: Link, row: Row) -> bool:
    """Queue the lapse of one consent's purposes. In a transaction of the
    caller's. The consent is taken under the capture lock, without waiting
    for it, and checked to be still the one in force with nothing in its
    chain unread: a change committed since the list was read has its own
    message to come, and a lapse message worked out without it would say
    less than it. The next night finds what is still to tell."""
    consent_id = int(row["consent_id"])
    user_id, notice_id = int(row["auth_user_id"]), int(row["notice_id"])
    if not await repo.try_lock_capture(conn, user_id=user_id, notice_id=notice_id):
        return False
    if not await repo.is_current(conn, consent_id):
        return False
    links = await repo.chain(
        conn, user_id=user_id, notice_id=notice_id, after=link.consent_changes_after
    )
    if any(not c["noted"] for c in links):
        return False
    root_id = int(links[0]["consent_id"])
    told = await repo.last_told(conn, root_id)
    before = set(told) if told is not None else set(await repo.granted_codes(conn, consent_id))
    after = before - set(row["lapsed"])
    if after == before:
        return False
    await _queue(
        conn,
        user_id=user_id,
        consent_id=consent_id,
        root_id=root_id,
        change="expired",
        before=before,
        after=after,
        effective_at=datetime.now(UTC),
    )
    return True


# ------------------------------------------------------------------ delivering
async def due(conn: Conn) -> list[Row]:
    return await repo.due_changes(conn, limit=BATCH)


def message_of(row: Row, fmt: str) -> dict[str, Any]:
    """A queued row as the contract's message, with the person, the project
    and the consents named as the administrator's switch says."""
    effective = row["effective_at"]
    chain = list(zip(row["chain_ids"], row["chain_uuids"], strict=True))
    return {
        "message_id": str(row["message_uuid"]),
        "sequence": int(row["change_id"]),
        "person_id": ids.of(fmt, no=row["auth_user_id"], uuid=row["person_uuid"]),
        "project_id": ids.of(fmt, no=row["project_id"], uuid=row["project_uuid"]),
        "consent_id": ids.of(fmt, no=row["consent_id"], uuid=row["consent_uuid"]),
        "consent_ids": [ids.of(fmt, no=no, uuid=uuid) for no, uuid in chain],
        "change": row["change"],
        "action": row["action"],
        "purposes_granted": list(row["purposes_granted"]),
        "purposes_removed": list(row["purposes_removed"]),
        "effective_at": effective.isoformat() if hasattr(effective, "isoformat") else effective,
    }


async def send(link: Link, row: Row, *, transport: Any = None) -> client.ChangeResult | str:
    """DataVault's answer to one message, or the failure's code."""
    assert link.erasure_url is not None
    try:
        return await client.consent_change(
            erasure_url=link.erasure_url,
            api_key=link.api_key,
            api_key_header=link.api_key_header,
            message=message_of(row, link.id_format),
            transport=transport,
        )
    except client.DataVaultFailed as failed:
        return failed.code


async def delivered(conn: Conn, row: Row, result: client.ChangeResult) -> None:
    first = await repo.record_delivery(
        conn, int(row["change_id"]), result=result.result, assets_affected=result.assets_affected
    )
    if not first:
        return  # recorded already: on the trail once
    await audit.record(
        conn,
        event=Event.DATAVAULT_CONSENT_CHANGE_DELIVERED,
        entity_type="consent_artefact",
        entity_id=int(row["consent_id"]),
        subject_user_id=int(row["auth_user_id"]),
        actor_user_id=None,
        detail={
            "project": str(row["project_uuid"]),
            "sequence": int(row["change_id"]),
            "change": row["change"],
            "action": row["action"],
            "result": result.result,
            "assets_affected": result.assets_affected,
        },
    )


Record = Callable[[Row, "client.ChangeResult | str"], Awaitable[None]]


async def deliver(
    link: Link,
    rows: list[Row],
    *,
    record: Record,
    transport: Any = None,
    budget: timedelta = DELIVERY_BUDGET,
) -> Row:
    """Send each due message, oldest first, with no transaction open; and have
    `record(row, answer)` write how it went, in a transaction of its own.

    Stops at the first try DataVault does not answer (`paused`): the others
    would only wait for the same. Stops once the run has taken `budget`. A
    message that cannot be worked at all is logged and passed over, so one
    bad row does not hold up the rest. Nothing is lost by stopping: what was
    not tried is due at the next run."""
    started = time.monotonic()
    sent = failed = broken = 0
    paused = False
    for row in rows:
        if time.monotonic() - started > budget.total_seconds():
            break
        try:
            answer = await send(link, row, transport=transport)
            await record(row, answer)
        except Exception as failed_on:
            broken += 1
            log.error(
                "datavault.consent_change_unsent",
                change=int(row["change_id"]),
                error=type(failed_on).__name__,
            )
            continue
        if isinstance(answer, str):
            failed += 1
            if passing(answer):
                paused = True
                break
        else:
            sent += 1
    return {"delivered": sent, "failed": failed, "broken": broken, "paused": paused}


async def undelivered(conn: Conn, row: Row, *, failure: str) -> None:
    mends = passing(failure)
    if mends:
        wait = min(MAX_WAIT, timedelta(minutes=2 ** min(int(row["attempts"]), 6)))
    else:
        wait = MAX_WAIT
    await repo.record_attempt(
        conn, int(row["change_id"]), failure=failure, next_attempt_at=datetime.now(UTC) + wait
    )
    said = {
        "change": int(row["change_id"]),
        "failure": failure,
        "attempts": int(row["attempts"]) + 1,
    }
    if mends:
        log.warning("datavault.consent_change_undelivered", **said)
    else:
        log.error("datavault.consent_change_undelivered", **said)
