"""Retention reviews (0076, ADR 0047): the sweep that finds who falls due, the
register the officers read, and the actions the people responsible answer.

When a consent ends, per purpose: if the person's latest decision still grants
the purpose, at that decision plus the purpose's validity (`validity`); if it
no longer does - withdrawn, in full or in part - at that decision
(`withdrawal`). Its data must go at the end plus the purpose's retention
period (the product owner, 2026-11-26: retention runs from the consent's end).

The sweep is set-based: one statement finds every candidate, one makes the
reviews, one adds the people. Run across both offices (the worker's session).
"""

from __future__ import annotations

from typing import Any

from cmp.db.sql import Conn, fetch_all, fetch_one, fetch_val
from cmp.infrastructure.dkms import seal

Row = dict[str, Any]

#: Every (consent chain, purpose ever granted in it): where it stands now.
_ENDS = """
WITH RECURSIVE chain AS (
  SELECT h.consent_id AS head_id, h.consent_id, h.supersedes_consent_id
    FROM v_current_consent h
  UNION ALL
  SELECT c.head_id, a.consent_id, a.supersedes_consent_id
    FROM chain c JOIN consent_artefact a ON a.consent_id = c.supersedes_consent_id
),
ever AS (
  SELECT DISTINCT c.head_id, g.purpose_id
    FROM chain c JOIN consent_purpose_grant g ON g.consent_id = c.consent_id AND g.granted
),
standing AS (
  SELECT h.consent_id, h.auth_user_id, pr.project_id, pr.office_id, pu.purpose_id,
         pu.consent_validity_period, pu.retention_period, h.affirmative_action_at,
         EXISTS (SELECT 1 FROM consent_purpose_grant g
                  WHERE g.consent_id = h.consent_id AND g.purpose_id = e.purpose_id
                    AND g.granted) AS in_force
    FROM ever e
    JOIN consent_artefact h ON h.consent_id = e.head_id
    JOIN notice n           ON n.notice_id = h.notice_id
    JOIN project pr         ON pr.project_id = n.project_id
    JOIN purpose pu         ON pu.purpose_id = e.purpose_id
),
ends AS (
  SELECT consent_id, auth_user_id, project_id, office_id, purpose_id, retention_period,
         CASE WHEN in_force THEN 'validity' ELSE 'withdrawal' END AS ended_by,
         CASE WHEN in_force THEN affirmative_action_at + consent_validity_period
              ELSE affirmative_action_at END AS ended_at
    FROM standing
   WHERE NOT in_force OR consent_validity_period IS NOT NULL
),
candidates AS (
  -- A validity running out within the horizon, or lately run out.
  SELECT 'validity' AS kind, consent_id, auth_user_id, project_id, office_id, purpose_id,
         ended_by, ended_at AS due_at
    FROM ends
   WHERE ended_by = 'validity'
     AND ended_at BETWEEN now() - make_interval(days => %(lookback)s)
                      AND now() + make_interval(days => %(horizon)s)
  UNION ALL
  -- Data that must go within the horizon, or should have gone already.
  SELECT 'retention', consent_id, auth_user_id, project_id, office_id, purpose_id,
         ended_by, ended_at + retention_period
    FROM ends
   WHERE retention_period IS NOT NULL
     AND ended_at + retention_period <= now() + make_interval(days => %(horizon)s)
)
"""


async def setting(conn: Conn) -> Row:
    row = await fetch_one(
        conn,
        """SELECT s.reminder_days, s.notice_hours, s.action_days, s.escalate_after_days,
                  s.updated_at, u.full_name AS updated_by_name
             FROM retention_setting s LEFT JOIN auth_user u ON u.id = s.updated_by
            WHERE s.setting_id = 1""",
    )
    assert row is not None, "retention_setting has its one row from the migration"
    return row


async def save_setting(conn: Conn, *, actor_id: int, **values: Any) -> None:
    await conn.execute(
        """UPDATE retention_setting
              SET reminder_days = %(reminder_days)s, notice_hours = %(notice_hours)s,
                  action_days = %(action_days)s, escalate_after_days = %(escalate_after_days)s,
                  updated_by = %(actor)s, updated_at = now()
            WHERE setting_id = 1""",
        {**values, "actor": actor_id},
    )


async def sweep(conn: Conn, *, horizon_days: int, lookback_days: int) -> dict[str, int]:
    """Find who falls due; make the reviews and add the people. Idempotent: a
    person is in one review of a kind per consent and purpose, ever."""
    params = {"horizon": horizon_days, "lookback": lookback_days}
    await conn.execute("DROP TABLE IF EXISTS retention_candidates")
    await conn.execute(
        f"CREATE TEMP TABLE retention_candidates ON COMMIT DROP AS {_ENDS} "
        "SELECT * FROM candidates",
        params,
    )
    made = await fetch_val(
        conn,
        """WITH made AS (
             INSERT INTO retention_review
                    (kind, office_id, project_id, purpose_id, cohort, reference)
             SELECT DISTINCT c.kind, c.office_id, c.project_id, c.purpose_id,
                    date_trunc('month', c.due_at)::date,
                    CASE c.kind WHEN 'validity' THEN 'VAL' ELSE 'RET' END
                      || '-' || to_char(date_trunc('month', c.due_at), 'YYYY-MM')
                      || '-' || lpad(c.project_id::text, 4, '0')
                      || '-' || lpad(c.purpose_id::text, 4, '0')
               FROM retention_candidates c
              WHERE NOT EXISTS (SELECT 1 FROM retention_review_person m
                                 WHERE m.kind = c.kind AND m.consent_id = c.consent_id
                                   AND m.purpose_id = c.purpose_id)
             ON CONFLICT (kind, project_id, purpose_id, cohort) DO NOTHING
             RETURNING 1)
           SELECT count(*) FROM made""",
    )
    added = await fetch_val(
        conn,
        """WITH added AS (
             INSERT INTO retention_review_person
                    (review_id, kind, consent_id, purpose_id, auth_user_id, due_at, ended_by,
                     office_id)
             SELECT r.review_id, c.kind, c.consent_id, c.purpose_id, c.auth_user_id, c.due_at,
                    c.ended_by, c.office_id
               FROM retention_candidates c
               JOIN retention_review r
                 ON r.kind = c.kind AND r.project_id = c.project_id
                AND r.purpose_id = c.purpose_id
                AND r.cohort = date_trunc('month', c.due_at)::date
             ON CONFLICT (kind, consent_id, purpose_id) DO NOTHING
             RETURNING 1)
           SELECT count(*) FROM added""",
    )
    # A legal hold keeps a person out of every action while it stands.
    held = await fetch_val(
        conn,
        """WITH changed AS (
             UPDATE retention_review_person m
                SET state = CASE WHEN EXISTS (
                                   SELECT 1 FROM legal_hold h
                                    WHERE h.subject_user_id = m.auth_user_id
                                      AND h.released_at IS NULL)
                                 THEN 'held' ELSE 'in' END
              WHERE m.state IN ('in', 'held')
                AND m.state <> CASE WHEN EXISTS (
                                   SELECT 1 FROM legal_hold h
                                    WHERE h.subject_user_id = m.auth_user_id
                                      AND h.released_at IS NULL)
                                 THEN 'held' ELSE 'in' END
             RETURNING 1)
           SELECT count(*) FROM changed""",
    )
    # A person who consented again to the purpose since is out of the review:
    # the consent no longer ends, and nothing of theirs is to go.
    renewed = await fetch_val(
        conn,
        """WITH changed AS (
             UPDATE retention_review_person m SET state = 'renewed'
              WHERE m.state <> 'renewed'
                AND EXISTS (
                  SELECT 1 FROM consent_artefact s
                    JOIN consent_purpose_grant g ON g.consent_id = s.consent_id
                   WHERE s.supersedes_consent_id = m.consent_id
                     AND g.purpose_id = m.purpose_id AND g.granted)
             RETURNING 1)
           SELECT count(*) FROM changed""",
    )
    due = await fetch_val(
        conn,
        """WITH changed AS (
             UPDATE retention_review r SET status = 'due', opened_at = now()
              WHERE r.status = 'upcoming'
                AND EXISTS (SELECT 1 FROM retention_review_person m
                             WHERE m.review_id = r.review_id AND m.state = 'in'
                               AND m.due_at <= now())
             RETURNING 1)
           SELECT count(*) FROM changed""",
    )
    return {
        "reviews_made": int(made or 0),
        "people_added": int(added or 0),
        "holds_changed": int(held or 0),
        "renewed": int(renewed or 0),
        "fell_due": int(due or 0),
    }


_REVIEW = """
SELECT r.review_id, r.review_uuid, r.reference, r.kind, r.status, r.cohort, r.reconsent,
       r.reminded_days, r.opened_at, r.closed_at, r.close_note, r.created_at, r.office_id,
       o.office_code AS office, p.project_id, p.project_uuid, p.project_name, p.project_status,
       p.category_id IS NOT NULL AS is_activity,
       pu.purpose_id, pu.purpose_code, pu.name AS purpose_name, pu.retention_period,
       pu.consent_validity_period, pu.lapse_behaviour, pu.notify_before_erasure,
       cb.full_name AS closed_by_name,
       (SELECT count(*) FROM retention_review_person m
         WHERE m.review_id = r.review_id AND m.state = 'in') AS people,
       (SELECT count(*) FROM retention_review_person m
         WHERE m.review_id = r.review_id AND m.state = 'held') AS held,
       (SELECT count(*) FROM retention_review_person m
         WHERE m.review_id = r.review_id AND m.state = 'renewed') AS renewed,
       (SELECT min(m.due_at) FROM retention_review_person m
         WHERE m.review_id = r.review_id AND m.state = 'in') AS first_due_at,
       (SELECT max(m.due_at) FROM retention_review_person m
         WHERE m.review_id = r.review_id AND m.state = 'in') AS last_due_at,
       (SELECT count(*) FROM retention_action a
         WHERE a.review_id = r.review_id) AS actions,
       (SELECT count(*) FROM retention_action a
         WHERE a.review_id = r.review_id AND a.status IN ('open', 'sent_back')) AS actions_open,
       (SELECT count(*) FROM retention_action a
         WHERE a.review_id = r.review_id AND a.status = 'answered') AS actions_to_review
  FROM retention_review r
  JOIN office o   ON o.office_id = r.office_id
  JOIN project p  ON p.project_id = r.project_id
  JOIN purpose pu ON pu.purpose_id = r.purpose_id
  LEFT JOIN auth_user cb ON cb.id = r.closed_by
"""


async def reviews(conn: Conn, *, kind: str | None, status: str | None) -> list[Row]:
    where, params = [], {}
    if kind:
        where.append("r.kind = %(kind)s")
        params["kind"] = kind
    if status:
        where.append("r.status = %(status)s")
        params["status"] = status
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    return await fetch_all(
        conn,
        f"""{_REVIEW} {clause}
            ORDER BY CASE r.status WHEN 'due' THEN 0 WHEN 'in_progress' THEN 1
                                   WHEN 'upcoming' THEN 2 ELSE 3 END, r.cohort, r.reference
            LIMIT 500""",
        params,
    )


async def review_by_uuid(conn: Conn, review_uuid: str) -> Row | None:
    return await fetch_one(conn, f"{_REVIEW} WHERE r.review_uuid = %s", (review_uuid,))


async def review_by_id(conn: Conn, review_id: int) -> Row | None:
    return await fetch_one(conn, f"{_REVIEW} WHERE r.review_id = %s", (review_id,))


async def people_of(conn: Conn, review_id: int, *, state: str | None = "in") -> list[Row]:
    clause = "AND m.state = %(state)s" if state else ""
    return await fetch_all(
        conn,
        f"""SELECT m.member_id, m.consent_id, ca.consent_uuid, m.auth_user_id, m.due_at,
                   m.ended_by, m.state, m.notified_at, m.invited_at
              FROM retention_review_person m
              JOIN consent_artefact ca ON ca.consent_id = m.consent_id
             WHERE m.review_id = %(r)s {clause}
             ORDER BY m.due_at, m.member_id""",
        {"r": review_id, "state": state},
    )


async def set_review(conn: Conn, review_id: int, **cols: Any) -> None:
    allowed = {"status", "reconsent", "reminded_days", "closed_at", "closed_by", "close_note"}
    unknown = set(cols) - allowed
    if unknown:
        raise ValueError(f"not a mutable review column: {sorted(unknown)}")
    cols = await seal("retention_review", cols)
    assignments = ", ".join(f"{k} = %({k})s" for k in cols)
    await conn.execute(
        f"UPDATE retention_review SET {assignments} WHERE review_id = %(id)s",
        {**cols, "id": review_id},
    )


# ------------------------------------------------------------------ actions
_ACTION = """
SELECT a.action_id, a.action_uuid, a.review_id, a.kind, a.processor_id, a.respondent_id,
       a.user_id, a.channel, a.label, a.status, a.outcome, a.reason, a.keep_until, a.reconsent,
       a.evidence_name, a.evidence_ref, a.evidence_hash, a.link_token, a.link_token_sealed,
       a.link_issued_at, a.due_at, a.answered_at, a.accepted_at, a.sent_back_reason,
       a.last_reminded_at, a.escalated_at, a.office_id, a.created_at,
       u.full_name AS user_name, u.email AS user_email,
       ab.full_name AS answered_by_name, cb.full_name AS accepted_by_name,
       r.review_uuid, r.reference, r.kind AS review_kind, r.status AS review_status
  FROM retention_action a
  JOIN retention_review r ON r.review_id = a.review_id
  LEFT JOIN auth_user u  ON u.id = a.user_id
  LEFT JOIN auth_user ab ON ab.id = a.answered_by
  LEFT JOIN auth_user cb ON cb.id = a.accepted_by
"""


async def actions_of(conn: Conn, review_id: int) -> list[Row]:
    return await fetch_all(
        conn,
        f"{_ACTION} WHERE a.review_id = %s ORDER BY a.kind DESC, a.label",
        (review_id,),
    )


async def action_by_uuid(conn: Conn, action_uuid: str) -> Row | None:
    return await fetch_one(conn, f"{_ACTION} WHERE a.action_uuid = %s", (action_uuid,))


async def action_by_link(conn: Conn, fingerprint: str) -> Row | None:
    return await fetch_one(conn, f"{_ACTION} WHERE a.link_token = %s", (fingerprint,))


async def actions_for_user(conn: Conn, user_id: int) -> list[Row]:
    return await fetch_all(
        conn,
        f"""{_ACTION} WHERE a.user_id = %s AND r.status <> 'closed'
            ORDER BY CASE a.status WHEN 'sent_back' THEN 0 WHEN 'open' THEN 1 ELSE 2 END,
                     a.due_at""",
        (user_id,),
    )


async def add_action(conn: Conn, **cols: Any) -> Row | None:
    """A new action, or None when the review has it already."""
    cols = await seal("retention_action", cols)
    names = ", ".join(cols)
    values = ", ".join(f"%({k})s" for k in cols)
    return await fetch_one(
        conn,
        f"""INSERT INTO retention_action ({names}) VALUES ({values})
            ON CONFLICT ON CONSTRAINT retention_action_one DO NOTHING
            RETURNING action_id""",
        cols,
    )


_ACTION_MUTABLE = frozenset(
    {
        "status",
        "outcome",
        "reason",
        "keep_until",
        "reconsent",
        "evidence_name",
        "evidence_ref",
        "evidence_hash",
        "answered_at",
        "answered_by",
        "accepted_at",
        "accepted_by",
        "sent_back_reason",
        "last_reminded_at",
        "escalated_at",
        "link_token",
        "link_token_sealed",
        "link_issued_at",
        "user_id",
        "respondent_id",
        "channel",
        "due_at",
    }
)


async def set_action(conn: Conn, action_id: int, **cols: Any) -> None:
    unknown = set(cols) - _ACTION_MUTABLE
    if unknown:
        raise ValueError(f"not a mutable action column: {sorted(unknown)}")
    cols = await seal("retention_action", cols)
    assignments = ", ".join(f"{k} = %({k})s" for k in cols)
    await conn.execute(
        f"UPDATE retention_action SET {assignments} WHERE action_id = %(id)s",
        {**cols, "id": action_id},
    )


async def processors_holding(conn: Conn, review_id: int) -> list[Row]:
    """The processors that hold data of the review's people under its project:
    the exports that carried their consents, the assets a processor's source
    captured, and - for an HR activity - its category's processors, whether
    or not the consent still stands (it has ended: that is why we ask)."""
    return await fetch_all(
        conn,
        """
        WITH RECURSIVE people AS (
          -- The consent in force and every one it replaced: an asset or an
          -- export names the consent given then, not the withdrawal after it.
          SELECT m.consent_id FROM retention_review_person m
           WHERE m.review_id = %(r)s AND m.state = 'in'
          UNION
          SELECT a.supersedes_consent_id FROM people p
            JOIN consent_artefact a ON a.consent_id = p.consent_id
           WHERE a.supersedes_consent_id IS NOT NULL
        ), held AS (
          SELECT DISTINCT COALESCE(el.destination_processor_id, s.processor_id) AS processor_id
            FROM export_line el
            JOIN export_log e ON e.export_id = el.export_id
            LEFT JOIN project_site s ON s.site_id = e.site_id
           WHERE el.consent_id IN (SELECT consent_id FROM people)
          UNION
          SELECT DISTINCT ds.processor_id
            FROM asset_consent ac
            JOIN data_asset da  ON da.asset_id = ac.asset_id
            JOIN data_source ds ON ds.source_id = da.source_id
           WHERE ac.consent_id IN (SELECT consent_id FROM people)
             AND coalesce(ac.disposition::text, 'active') <> 'erased'
          UNION
          SELECT DISTINCT cp.processor_id
            FROM retention_review r
            JOIN project p ON p.project_id = r.project_id
            JOIN category_processor cp ON cp.category_id = p.category_id AND cp.removed_at IS NULL
           WHERE r.review_id = %(r)s
        )
        SELECT pr.processor_id, pr.legal_name,
               (SELECT pr2.respondent_id FROM processor_respondent pr2
                 WHERE pr2.processor_id = pr.processor_id AND pr2.removed_at IS NULL
                 ORDER BY pr2.respondent_id LIMIT 1) AS respondent_id,
               (SELECT pr2.user_id FROM processor_respondent pr2
                 WHERE pr2.processor_id = pr.processor_id AND pr2.removed_at IS NULL
                 ORDER BY pr2.respondent_id LIMIT 1) AS respondent_user_id,
               (SELECT cp.respondent_user_id FROM category_processor cp
                  JOIN retention_review r ON r.review_id = %(r)s
                  JOIN project p ON p.project_id = r.project_id
                 WHERE cp.category_id = p.category_id AND cp.processor_id = pr.processor_id
                   AND cp.removed_at IS NULL LIMIT 1) AS category_respondent_id
          FROM held h JOIN processor pr ON pr.processor_id = h.processor_id
         WHERE h.processor_id IS NOT NULL
         ORDER BY pr.legal_name
        """,
        {"r": review_id},
    )


async def owner_of(conn: Conn, review: Row) -> Row | None:
    """Who answers for the project: an HR activity's HR PoC (`dco_user_id`,
    ADR 0033); a project's DCO Admin of its office - the one that routes its
    collection - or, collected in-house, its R&D User."""
    if review["is_activity"]:
        return await fetch_one(
            conn,
            """SELECT u.id, u.full_name, u.role
                 FROM project p JOIN auth_user u ON u.id = p.dco_user_id
                WHERE p.project_id = %s AND u.status = 'active'""",
            (review["project_id"],),
        )
    third_party = await fetch_val(
        conn,
        """SELECT EXISTS (SELECT 1 FROM project_processor pp
                            JOIN processor pr ON pr.processor_id = pp.processor_id
                           WHERE pp.project_id = %s AND NOT pr.is_in_house)""",
        (review["project_id"],),
    )
    if third_party:
        return await fetch_one(
            conn,
            """SELECT u.id, u.full_name, u.role FROM auth_user u
                WHERE u.role = 'dco_admin' AND u.status = 'active' AND u.office_id = %s
                ORDER BY u.id LIMIT 1""",
            (review["office_id"],),
        )
    return await fetch_one(
        conn,
        """SELECT u.id, u.full_name, u.role FROM project p JOIN auth_user u ON u.id = p.created_by
            WHERE p.project_id = %s AND u.status = 'active'""",
        (review["project_id"],),
    )


async def officers_of(conn: Conn, office_id: int) -> list[Row]:
    role = await fetch_val(
        conn,
        """SELECT CASE office_code WHEN 'hr' THEN 'legal' ELSE 'dpo' END
             FROM office WHERE office_id = %s""",
        (office_id,),
    )
    return await fetch_all(
        conn,
        """SELECT id, full_name, email FROM auth_user
            WHERE role = %s::user_role AND status = 'active' AND office_id = %s""",
        (role, office_id),
    )


# ------------------------------------------------------------ the daily run
async def reviews_to_open(conn: Conn) -> list[Row]:
    """Reviews that should ask somebody and have not: a validity review not
    closed (asked at once - there is time to renew), a retention review once
    it falls due."""
    return await fetch_all(
        conn,
        f"""{_REVIEW}
            WHERE r.status <> 'closed'
              AND NOT EXISTS (SELECT 1 FROM retention_action a WHERE a.review_id = r.review_id)
              AND (r.kind = 'validity' OR r.status = 'due')""",
    )


async def reviews_to_remind(conn: Conn) -> list[Row]:
    return await fetch_all(conn, f"{_REVIEW} WHERE r.status IN ('upcoming', 'due', 'in_progress')")


async def actions_past_due(conn: Conn) -> list[Row]:
    """Open actions past their date, not yet reminded since it passed."""
    return await fetch_all(
        conn,
        f"""{_ACTION}
            WHERE a.status IN ('open', 'sent_back') AND a.due_at < now()
              AND (a.last_reminded_at IS NULL OR a.last_reminded_at < a.due_at)""",
    )


async def actions_to_escalate(conn: Conn, days: int) -> list[Row]:
    return await fetch_all(
        conn,
        f"""{_ACTION}
            WHERE a.status IN ('open', 'sent_back') AND a.escalated_at IS NULL
              AND a.due_at + make_interval(days => %s) < now()""",
        (days,),
    )


async def people_to_notify(conn: Conn, notice_hours: int) -> list[Row]:
    """People to be told before their data is erased: in a retention review,
    the purpose asking for it, not told yet, within the notice."""
    return await fetch_all(
        conn,
        """SELECT m.member_id, m.auth_user_id, m.due_at, r.review_id, r.reference,
                  pu.name AS purpose_name, p.project_name
             FROM retention_review_person m
             JOIN retention_review r ON r.review_id = m.review_id
             JOIN purpose pu ON pu.purpose_id = r.purpose_id
             JOIN project p  ON p.project_id = r.project_id
            WHERE r.kind = 'retention' AND r.status <> 'closed' AND m.state = 'in'
              AND m.notified_at IS NULL AND pu.notify_before_erasure
              AND m.due_at - make_interval(hours => %s) <= now()
            LIMIT 5000""",
        (notice_hours,),
    )


async def mark_people(conn: Conn, member_ids: list[int], column: str) -> None:
    if column not in ("notified_at", "invited_at") or not member_ids:
        return
    await conn.execute(
        f"UPDATE retention_review_person SET {column} = now() WHERE member_id = ANY(%s)",
        (member_ids,),
    )


async def live_link_sealed(conn: Conn, project_id: int) -> bytes | None:
    """The project's newest live consent link that will stay live a week, sealed."""
    row = await fetch_one(
        conn,
        """SELECT l.token_sealed FROM consent_link l
             JOIN notice n ON n.notice_id = l.notice_id
            WHERE n.project_id = %s AND l.status = 'active' AND l.token_sealed IS NOT NULL
              AND (l.expires_at IS NULL OR l.expires_at > now() + interval '7 days')
              AND (l.max_uses IS NULL OR l.use_count < l.max_uses)
            ORDER BY l.created_at DESC LIMIT 1""",
        (project_id,),
    )
    return bytes(row["token_sealed"]) if row else None


async def respondent_contact(conn: Conn, respondent_id: int) -> Any:
    """A processor respondent's contact, sealed, while they are not removed."""
    row = await fetch_one(
        conn,
        "SELECT contact FROM processor_respondent WHERE respondent_id = %s AND removed_at IS NULL",
        (respondent_id,),
    )
    return row["contact"] if row else None
