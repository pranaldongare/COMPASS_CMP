"""DataVault: where it is, what it answered for a rights request, what it
was told to erase, and the consent changes it is told of (0070, 0071).

Tables of their own. Nothing here writes a rights or a consent table; what is
read of them is the request's and the holder's keys, which the caller has
already been let through to, and the consents themselves, which the worker
reads across both offices to work out what DataVault must hear.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from psycopg.types.json import Jsonb

from cmp.db.sql import Conn, fetch_all, fetch_one, fetch_val

Row = dict[str, Any]


# ------------------------------------------------------------- the connection
async def connection(conn: Conn) -> Row:
    row = await fetch_one(
        conn,
        """SELECT x.base_url, x.erasure_url, x.api_key_sealed, x.api_key_header, x.enabled,
                  x.id_format, x.consent_changes, x.consent_changes_after,
                  x.consent_changes_since, x.updated_at,
                  u.full_name AS updated_by_name
             FROM datavault_connection x
             LEFT JOIN auth_user u ON u.id = x.updated_by
            WHERE x.connection_id = 1""",
    )
    assert row is not None, "datavault_connection has its one row from the migration"
    return row


#: How long before consent changes are first switched on a consent is still
#: read: one being saved at that moment may commit after its number was
#: passed, and would otherwise never be read.
SETTLE = "1 minute"


async def highest_consent(conn: Conn) -> int:
    """Where consent changes start from: the newest consent given more than a
    minute ago, whichever office's - read by the caller across both. What was
    given in the last minute is read, so a consent still being saved as the
    administrator switches them on is not passed over."""
    return int(
        await fetch_val(
            conn,
            f"""SELECT coalesce(max(consent_id), 0) FROM consent_artefact
                 WHERE affirmative_action_at < now() - interval '{SETTLE}'""",
        )
    )


async def set_connection(
    conn: Conn,
    *,
    base_url: str | None,
    erasure_url: str | None,
    api_key_header: str,
    enabled: bool,
    id_format: str,
    consent_changes: bool,
    consent_changes_after: int | None,
    actor_id: int,
    api_key_sealed: bytes | None,
    keep_key: bool,
) -> None:
    """The row as the administrator saved it. `keep_key` leaves the key that
    is there: the page never has it to send back. `consent_changes_after`
    and the time beside it are written only while none is set: where consent
    changes start from is settled the first time they are switched on, and
    never moved."""
    await conn.execute(
        """UPDATE datavault_connection
              SET base_url = %(url)s, erasure_url = %(erasure)s, api_key_header = %(header)s,
                  enabled = %(enabled)s, id_format = %(ids)s, consent_changes = %(changes)s,
                  consent_changes_after = coalesce(consent_changes_after, %(after)s),
                  consent_changes_since = coalesce(
                    consent_changes_since, CASE WHEN %(after)s::int IS NOT NULL THEN now() END),
                  api_key_sealed = CASE WHEN %(keep)s THEN api_key_sealed ELSE %(key)s END,
                  updated_by = %(actor)s, updated_at = now()
            WHERE connection_id = 1""",
        {
            "url": base_url,
            "erasure": erasure_url,
            "header": api_key_header,
            "enabled": enabled,
            "ids": id_format,
            "changes": consent_changes,
            "after": consent_changes_after,
            "keep": keep_key,
            "key": api_key_sealed,
            "actor": actor_id,
        },
    )


# ------------------------------------------------------------------ the checks
_CHECK = """
  k.check_id, k.check_uuid, k.request_id, k.asked_at, k.outcome, k.failure, k.asset_count,
  (k.asked_by IS NULL) AS automatic, u.full_name AS asked_by_name
  FROM datavault_check k
  LEFT JOIN auth_user u ON u.id = k.asked_by
"""


async def add_check(
    conn: Conn,
    *,
    request_id: int,
    asked_by: int | None,
    outcome: str,
    failure: str | None,
    asset_count: int,
) -> Row:
    row = await fetch_one(
        conn,
        """INSERT INTO datavault_check (request_id, asked_by, outcome, failure, asset_count)
           VALUES (%s, %s, %s, %s, %s)
           RETURNING check_id, check_uuid""",
        (request_id, asked_by, outcome, failure, asset_count),
    )
    assert row is not None
    return row


async def add_assets(conn: Conn, check_id: int, assets: list[Row]) -> None:
    if not assets:
        return
    async with conn.cursor() as cur:
        await cur.executemany(
            """INSERT INTO datavault_check_asset
                 (check_id, position, asset_ref, consent_ref, consent_ref_is_number,
                  project_ref, consent_id, project_id, mid, datapath)
               VALUES (%(check_id)s, %(position)s, %(asset_ref)s, %(consent_ref)s,
                       %(consent_ref_is_number)s, %(project_ref)s, %(consent_id)s,
                       %(project_id)s, %(mid)s, %(datapath)s)""",
            [
                {"consent_ref_is_number": None, **a, "check_id": check_id, "position": i}
                for i, a in enumerate(assets)
            ],
        )


async def last_check(conn: Conn, request_id: int) -> Row | None:
    """The newest call, answered or not: what the page says happened last."""
    return await fetch_one(
        conn,
        f"SELECT {_CHECK} WHERE k.request_id = %s ORDER BY k.check_id DESC LIMIT 1",
        (request_id,),
    )


async def last_answer(conn: Conn, request_id: int) -> Row | None:
    """The newest call DataVault answered: a later one that failed does not
    unsay what an earlier one listed."""
    return await fetch_one(
        conn,
        f"""SELECT {_CHECK} WHERE k.request_id = %s AND k.outcome = 'answered'
            ORDER BY k.check_id DESC LIMIT 1""",
        (request_id,),
    )


_ASSET = """
  a.asset_ref, a.consent_ref, a.consent_ref_is_number, a.project_ref, a.mid, a.datapath,
  a.consent_id,
  c.consent_uuid, c.consent_id AS consent_no,
  p.project_uuid, p.project_id AS project_no, p.project_name
  FROM datavault_check_asset a
  LEFT JOIN consent_artefact c ON c.consent_id = a.consent_id
  LEFT JOIN project p ON p.project_id = a.project_id
"""


async def assets_of(conn: Conn, check_id: int, *, project_id: int | None = None) -> list[Row]:
    """What a check listed, in DataVault's order; of one project when asked."""
    only = "AND a.project_id = %(p)s" if project_id is not None else ""
    return await fetch_all(
        conn,
        f"SELECT {_ASSET} WHERE a.check_id = %(k)s {only} ORDER BY a.position",
        {"k": check_id, "p": project_id},
    )


# ------------------------------------------------ matching what DataVault named
async def consents_of_person(conn: Conn, user_id: int, *, office_id: int | None) -> list[Row]:
    """This person's consents with their projects, in the request's office:
    what DataVault's `consent_id` and `project_id` are matched against, and
    nothing wider. An identifier that is somebody else's consent stays
    unmatched, and so does her own consent in the other office's project - a
    request is one office's, and what it links to is that office's too.

    The office is named here and not left to the row policy, as
    `holdings.owners_of_person` names it: the platform's own check reads
    across both offices, where the policy would let every consent through.
    A request no office has claimed yet is matched within the caller's own."""
    office = "p.office_id = %(o)s" if office_id is not None else "cmp_office_visible(p.office_id)"
    return await fetch_all(
        conn,
        f"""SELECT ca.consent_id, ca.consent_uuid::text AS consent_uuid,
                   n.project_id, p.project_uuid::text AS project_uuid
              FROM consent_artefact ca
              JOIN notice n ON n.notice_id = ca.notice_id
              JOIN project p ON p.project_id = n.project_id
             WHERE ca.auth_user_id = %(u)s AND {office}""",
        {"u": user_id, "o": office_id},
    )


# -------------------------------------------------------------------- holders
async def dco_admin_holder(conn: Conn, holder_uuid: str, user_id: int) -> Row | None:
    """The holder behind a ticket, if it is a project's DCO Admin answering in
    the console and this account is the one it is addressed to (0069)."""
    return await fetch_one(
        conn,
        """SELECT h.request_id, h.project_id
             FROM rights_request_holder h
             JOIN project p ON p.project_id = h.project_id
            WHERE h.holder_uuid = %s AND h.responder_user_id = %s
              AND h.derived_from = 'project_owner' AND p.category_id IS NULL""",
        (holder_uuid, user_id),
    )


# ------------------------------------------------------------------- erasures
_ERASURE = """
  e.erasure_id, e.erasure_uuid, e.request_id, e.check_id, e.id_format, e.sent_at, e.asks,
  e.last_asked_at, e.answered_at, e.failure, sb.full_name AS sent_by_name,
  (SELECT count(*) FROM datavault_erasure_asset ea
    WHERE ea.erasure_id = e.erasure_id AND ea.status IN ('unanswered', 'pending')) AS open_assets
  FROM datavault_erasure e
  LEFT JOIN auth_user sb ON sb.id = e.sent_by
"""


async def add_erasure(
    conn: Conn, *, request_id: int, check_id: int, id_format: str, sent_by: int, assets: list[Row]
) -> Row:
    """One instruction and the assets it names, before it is sent: a call that
    is never answered still leaves what was asked. `consent_sent` is the
    consent as it goes on the wire - a number or a text, as DataVault gave it."""
    row = await fetch_one(
        conn,
        """INSERT INTO datavault_erasure (request_id, check_id, id_format, sent_by)
           VALUES (%s, %s, %s, %s)
           RETURNING erasure_id, erasure_uuid""",
        (request_id, check_id, id_format, sent_by),
    )
    assert row is not None
    async with conn.cursor() as cur:
        await cur.executemany(
            """INSERT INTO datavault_erasure_asset (erasure_id, position, asset_ref, consent_sent)
               VALUES (%(erasure_id)s, %(position)s, %(asset_ref)s, %(consent_sent)s)""",
            [
                {
                    "erasure_id": row["erasure_id"],
                    "position": i,
                    "asset_ref": a["asset_ref"],
                    "consent_sent": (
                        Jsonb(a["consent_sent"]) if a["consent_sent"] is not None else None
                    ),
                }
                for i, a in enumerate(assets)
            ],
        )
    return row


async def lock_erasures(conn: Conn, request_id: int) -> None:
    """Presses of "Erase in DataVault" on one request, one at a time, until
    the caller's transaction ends. A key of its own (one 64-bit number), apart
    from the two-number keys the consent captures take."""
    await conn.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended('cmp.datavault.erasure', %s))",
        (request_id,),
    )


async def release_refused(conn: Conn, erasure_id: int, *, reason: str) -> int:
    """An instruction DataVault turned down without ever answering it: it has
    not taken it, so its assets are marked not erased, with why, and a later
    press sends them again. One it has answered before keeps its assets as
    they stand. Returns how many were released."""
    cur = await conn.execute(
        """UPDATE datavault_erasure_asset a
              SET status = 'failed', status_at = now(), reason = %s
            WHERE a.erasure_id = %s AND a.status = 'unanswered'
              AND EXISTS (SELECT 1 FROM datavault_erasure e
                           WHERE e.erasure_id = a.erasure_id AND e.answered_at IS NULL)""",
        (reason, erasure_id),
    )
    return int(cur.rowcount or 0)


async def erasure_by_id(conn: Conn, erasure_id: int) -> Row | None:
    return await fetch_one(conn, f"SELECT {_ERASURE} WHERE e.erasure_id = %s", (erasure_id,))


async def erasures_of(conn: Conn, request_id: int) -> list[Row]:
    """Every instruction sent for a request, newest first."""
    return await fetch_all(
        conn,
        f"SELECT {_ERASURE} WHERE e.request_id = %s ORDER BY e.erasure_id DESC",
        (request_id,),
    )


async def erasure_assets(conn: Conn, erasure_id: int) -> list[Row]:
    """What an instruction named, in the order it was sent in: a repeat sends
    the same assets, or DataVault refuses it."""
    return await fetch_all(
        conn,
        """SELECT asset_ref, consent_sent, status FROM datavault_erasure_asset
            WHERE erasure_id = %s ORDER BY position""",
        (erasure_id,),
    )


async def record_ask(
    conn: Conn, erasure_id: int, *, asked_by: int, failure: str | None, id_format: str
) -> None:
    """One more ask of an instruction, and how it went. An answer settles how
    the instruction names the person and the request: until DataVault has
    answered it, it has not taken it, and the next ask names them as the
    administrator's switch says then."""
    await conn.execute(
        """UPDATE datavault_erasure
              SET asks = asks + 1, last_asked_at = now(), last_asked_by = %(by)s,
                  failure = %(failure)s,
                  id_format = CASE WHEN %(failure)s::text IS NULL AND answered_at IS NULL
                                   THEN %(fmt)s ELSE id_format END,
                  answered_at = CASE WHEN %(failure)s::text IS NULL THEN now() ELSE answered_at END
            WHERE erasure_id = %(id)s""",
        {"id": erasure_id, "by": asked_by, "failure": failure, "fmt": id_format},
    )


async def set_outcome(
    conn: Conn,
    erasure_id: int,
    *,
    asset_ref: str,
    status: str,
    completed_at: datetime | None,
    reason: str | None,
) -> bool:
    """DataVault's word on one asset. A final word already recorded stands:
    only an asset not yet answered, or still pending, takes a new one."""
    cur = await conn.execute(
        """UPDATE datavault_erasure_asset
              SET status = %s, status_at = now(), completed_at = %s, reason = %s
            WHERE erasure_id = %s AND asset_ref = %s AND status IN ('unanswered', 'pending')""",
        (status, completed_at, reason, erasure_id, asset_ref),
    )
    return bool(cur.rowcount)


async def erasure_states(conn: Conn, request_id: int) -> dict[str, Row]:
    """Where each asset of a request stands in DataVault, by DataVault's own
    identifier: what the newest instruction that named it was last told."""
    rows = await fetch_all(
        conn,
        """SELECT DISTINCT ON (ea.asset_ref)
                  ea.asset_ref, ea.status, ea.status_at, ea.completed_at, ea.reason, e.sent_at
             FROM datavault_erasure_asset ea
             JOIN datavault_erasure e ON e.erasure_id = ea.erasure_id
            WHERE e.request_id = %s
            ORDER BY ea.asset_ref, e.erasure_id DESC""",
        (request_id,),
    )
    return {str(r["asset_ref"]): r for r in rows}


# ------------------------------------------------------------ consent changes
async def unnoted_chains(conn: Conn, *, after: int, limit: int) -> list[Row]:
    """The chains - one person, one notice - with a consent not yet read for
    DataVault, oldest unread first. Nothing up to `after` is ever read."""
    return await fetch_all(
        conn,
        """SELECT ca.auth_user_id, ca.notice_id, min(ca.consent_id) AS first_unread
             FROM consent_artefact ca
            WHERE ca.consent_id > %s
              AND NOT EXISTS (SELECT 1 FROM datavault_consent_noted n
                               WHERE n.consent_id = ca.consent_id)
            GROUP BY ca.auth_user_id, ca.notice_id
            ORDER BY min(ca.consent_id)
            LIMIT %s""",
        (after, limit),
    )


async def chain(conn: Conn, *, user_id: int, notice_id: int, after: int) -> list[Row]:
    """A chain's consents, oldest first, each with whether it has been read."""
    return await fetch_all(
        conn,
        """SELECT ca.consent_id, ca.is_withdrawal, ca.affirmative_action_at,
                  (ca.consent_id <= %(after)s
                   OR EXISTS (SELECT 1 FROM datavault_consent_noted n
                               WHERE n.consent_id = ca.consent_id)) AS noted
             FROM consent_artefact ca
            WHERE ca.auth_user_id = %(u)s AND ca.notice_id = %(n)s
            ORDER BY ca.consent_id""",
        {"u": user_id, "n": notice_id, "after": after},
    )


async def note(conn: Conn, consent_ids: list[int]) -> None:
    if not consent_ids:
        return
    await conn.execute(
        """INSERT INTO datavault_consent_noted (consent_id)
           SELECT unnest(%s::int[]) ON CONFLICT (consent_id) DO NOTHING""",
        (consent_ids,),
    )


async def try_lock_capture(conn: Conn, *, user_id: int, notice_id: int) -> bool:
    """The capture lock (`consent.lock_capture`), without waiting for it."""
    return bool(
        await fetch_val(conn, "SELECT pg_try_advisory_xact_lock(%s, %s)", (user_id, notice_id))
    )


async def project_uuid_of_consent(conn: Conn, consent_id: int) -> str:
    """The project a consent was given on: what its trail is read with."""
    value = await fetch_val(
        conn,
        """SELECT p.project_uuid::text
             FROM consent_artefact ca
             JOIN notice n ON n.notice_id = ca.notice_id
             JOIN project p ON p.project_id = n.project_id
            WHERE ca.consent_id = %s""",
        (consent_id,),
    )
    assert value is not None, "a consent is given on a notice of a project"
    return str(value)


async def granted_codes(conn: Conn, consent_id: int) -> list[str]:
    rows = await fetch_all(
        conn,
        """SELECT p.purpose_code FROM consent_purpose_grant g
             JOIN purpose p ON p.purpose_id = g.purpose_id
            WHERE g.consent_id = %s AND g.granted ORDER BY p.purpose_code""",
        (consent_id,),
    )
    return [str(r["purpose_code"]) for r in rows]


async def last_told(conn: Conn, chain_root_id: int) -> list[str] | None:
    """The purposes the newest message queued for this chain says the assets
    may be used for - what DataVault holds, or will once it is delivered -
    or None when nothing has been queued for the chain yet."""
    value = await fetch_one(
        conn,
        """SELECT purposes_granted FROM datavault_consent_change
            WHERE chain_root_id = %s ORDER BY change_id DESC LIMIT 1""",
        (chain_root_id,),
    )
    return list(value["purposes_granted"]) if value else None


async def run_out_on(conn: Conn, consent_id: int, *, at: datetime) -> list[str]:
    """The purposes granted on this consent whose validity had run out by its
    own clock at `at` - the moment of the withdrawal that replaced it - where
    the purpose's lapse does something (the retention sweep's test). A
    withdrawal copies such a grant forward, and DataVault is not to take that
    as a grant. Measured at the withdrawal and not at the reading, so a
    withdrawal reads the same however late the worker gets to it."""
    rows = await fetch_all(
        conn,
        """SELECT p.purpose_code
             FROM consent_artefact ca
             JOIN consent_purpose_grant g ON g.consent_id = ca.consent_id AND g.granted
             JOIN purpose p ON p.purpose_id = g.purpose_id
            WHERE ca.consent_id = %s
              AND p.consent_validity_period IS NOT NULL AND p.lapse_behaviour <> 'none'
              AND ca.affirmative_action_at + p.consent_validity_period < %s
            ORDER BY p.purpose_code""",
        (consent_id, at),
    )
    return [str(r["purpose_code"]) for r in rows]


async def queue_change(
    conn: Conn,
    *,
    consent_id: int,
    chain_root_id: int,
    change: str,
    action: str,
    granted: list[str],
    removed: list[str],
    effective_at: datetime,
) -> Row:
    """Queue one message, and set aside every earlier one for the same chain
    still undelivered: each carries the whole state, so the latest is enough."""
    await conn.execute(
        """UPDATE datavault_consent_change SET superseded_at = now()
            WHERE chain_root_id = %s AND delivered_at IS NULL AND superseded_at IS NULL""",
        (chain_root_id,),
    )
    row = await fetch_one(
        conn,
        """INSERT INTO datavault_consent_change
             (consent_id, chain_root_id, change, action, purposes_granted, purposes_removed,
              effective_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           RETURNING change_id, message_uuid""",
        (consent_id, chain_root_id, change, action, granted, removed, effective_at),
    )
    assert row is not None
    return row


_MESSAGE = """
  m.change_id, m.message_uuid, m.consent_id, m.change, m.action,
  m.purposes_granted, m.purposes_removed, m.effective_at, m.attempts,
  ca.consent_uuid, ca.auth_user_id, u.uuid AS person_uuid,
  p.project_id, p.project_uuid,
  (SELECT array_agg(x.consent_id ORDER BY x.consent_id)
     FROM consent_artefact x
    WHERE x.auth_user_id = ca.auth_user_id AND x.notice_id = ca.notice_id
      AND x.consent_id <= ca.consent_id) AS chain_ids,
  (SELECT array_agg(x.consent_uuid::text ORDER BY x.consent_id)
     FROM consent_artefact x
    WHERE x.auth_user_id = ca.auth_user_id AND x.notice_id = ca.notice_id
      AND x.consent_id <= ca.consent_id) AS chain_uuids
  FROM datavault_consent_change m
  JOIN consent_artefact ca ON ca.consent_id = m.consent_id
  JOIN auth_user u         ON u.id = ca.auth_user_id
  JOIN notice n            ON n.notice_id = ca.notice_id
  JOIN project p           ON p.project_id = n.project_id
"""


async def due_changes(conn: Conn, *, limit: int) -> list[Row]:
    """Undelivered messages whose time has come, oldest first, each with
    everything the message carries."""
    return await fetch_all(
        conn,
        f"""SELECT {_MESSAGE}
             WHERE m.delivered_at IS NULL AND m.superseded_at IS NULL
               AND m.next_attempt_at <= now()
             ORDER BY m.change_id LIMIT %s""",
        (limit,),
    )


async def record_delivery(conn: Conn, change_id: int, *, result: str, assets_affected: int) -> bool:
    """DataVault has it. False when it was recorded already - a second worker
    delivered the same message at once - so it is put on the trail once."""
    cur = await conn.execute(
        """UPDATE datavault_consent_change
              SET attempts = attempts + 1, last_attempt_at = now(), failure = NULL,
                  delivered_at = now(), result = %s, assets_affected = %s,
                  -- Set aside while its call was in flight: it was sent after all.
                  superseded_at = NULL
            WHERE change_id = %s AND delivered_at IS NULL""",
        (result, assets_affected, change_id),
    )
    return bool(cur.rowcount)


async def record_attempt(
    conn: Conn, change_id: int, *, failure: str, next_attempt_at: datetime
) -> None:
    await conn.execute(
        """UPDATE datavault_consent_change
              SET attempts = attempts + 1, last_attempt_at = now(), failure = %s,
                  next_attempt_at = %s
            WHERE change_id = %s AND delivered_at IS NULL""",
        (failure, next_attempt_at, change_id),
    )


async def lapsed_unreported(
    conn: Conn, *, since: datetime, after_id: int = 0, limit: int
) -> list[Row]:
    """Consents in force with a granted purpose whose validity has run out
    (the retention sweep's own test) and whose lapse does something, which
    DataVault still takes as granted.

    Only a validity that ran out after `since` - when consent changes were
    first switched on: what had lapsed by then is the past, and stays untold.
    And only a purpose DataVault has not been told is gone: the newest message
    queued for the chain says what it holds, and where none has been queued it
    holds what the consent grants. So a lapse is reported once, and one that a
    later withdrawal has already taken away is not reported at all. Read a
    page at a time, by consent, from after `after_id`."""
    return await fetch_all(
        conn,
        """SELECT vc.consent_id, vc.auth_user_id, vc.notice_id,
                  array_agg(DISTINCT p.purpose_code ORDER BY p.purpose_code) AS lapsed
             FROM v_current_consent vc
             JOIN consent_purpose_grant g ON g.consent_id = vc.consent_id AND g.granted
             JOIN purpose p ON p.purpose_id = g.purpose_id
            WHERE p.consent_validity_period IS NOT NULL
              AND p.lapse_behaviour <> 'none'
              AND vc.affirmative_action_at + p.consent_validity_period < now()
              AND vc.affirmative_action_at + p.consent_validity_period >= %(since)s
              AND vc.consent_id > %(after_id)s
              AND coalesce(
                    (SELECT p.purpose_code = ANY(t.purposes_granted)
                       FROM datavault_consent_change t
                       JOIN consent_artefact tc ON tc.consent_id = t.consent_id
                      WHERE tc.auth_user_id = vc.auth_user_id AND tc.notice_id = vc.notice_id
                      ORDER BY t.change_id DESC LIMIT 1),
                    true)
            GROUP BY vc.consent_id, vc.auth_user_id, vc.notice_id
            ORDER BY vc.consent_id LIMIT %(limit)s""",
        {"since": since, "after_id": after_id, "limit": limit},
    )


async def is_current(conn: Conn, consent_id: int) -> bool:
    return bool(
        await fetch_val(
            conn, "SELECT 1 FROM v_current_consent WHERE consent_id = %s", (consent_id,)
        )
    )


async def queue_health(conn: Conn) -> Row:
    """How the queue stands, as counts and times: nothing of any consent."""
    row = await fetch_one(
        conn,
        """SELECT count(*) FILTER (WHERE delivered_at IS NULL AND superseded_at IS NULL) AS waiting,
                  max(delivered_at) AS last_delivered_at,
                  (SELECT failure FROM datavault_consent_change
                    WHERE delivered_at IS NULL AND superseded_at IS NULL AND failure IS NOT NULL
                    ORDER BY last_attempt_at DESC NULLS LAST LIMIT 1) AS last_failure
             FROM datavault_consent_change""",
    )
    assert row is not None
    return row
