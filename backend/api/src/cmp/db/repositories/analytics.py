"""How each analytics figure is counted (ADR 0045).

One SQL source per metric of `cmp.core.metrics`, keyed the same; a test holds
the two together. Each source selects rows of one shape:

* `at` - when the row happened, the moment the period is tested against (now,
  for a figure as things stand);
* `office` - the office code the row belongs to, or NULL for a row of no
  office (an account, a sign-in, a request still in the shared intake);
* `v` - the value a median is taken of (days, hours); 1 otherwise;
* `d_<name>` - each breakdown the catalogue allows it.

`series()` puts the period, the office and the breakdown around it, so no
source repeats them. Row level security still applies underneath: an
officer's session reads only its office's rows of the policed tables, and the
office filter the service passes keeps the unpoliced ones (the trail) in step.
A source for "your work" names `{scope}`, the project register's own scope
predicate for the role, so these figures and the register cannot disagree.

Nothing here reads a sealed column: figures are counts, and a breakdown is by
something the platform owns.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Final

from cmp.db.sql import Conn, Row, fetch_all, fetch_one


def _office(alias: str) -> str:
    return f"(SELECT o.office_code FROM office o WHERE o.office_id = {alias}.office_id)"


_GRANTED = """EXISTS (SELECT 1 FROM consent_purpose_grant g
                       WHERE g.consent_id = {c}.consent_id AND g.granted)"""

_CONSENT = f"""SELECT c.affirmative_action_at AS at, {_office("n")} AS office,
       p.project_name AS d_project, hc.name AS d_category, 1 AS v
  FROM consent_artefact c
  JOIN notice n  ON n.notice_id = c.notice_id
  JOIN project p ON p.project_id = n.project_id
  LEFT JOIN hr_category hc ON hc.category_id = p.category_id"""

_RIGHTS = f"""SELECT {{at}} AS at, {_office("r")} AS office, r.request_type::text AS d_type,
       r.channel::text AS d_channel, r.outcome::text AS d_outcome, r.status::text AS d_status,
       {{v}} AS v
  FROM rights_request r"""


def _rights(at: str, where: str, v: str = "1") -> str:
    return _RIGHTS.format(at=at, v=v) + f" WHERE {where}"


def _days(later: str, earlier: str) -> str:
    return f"extract(epoch FROM ({later} - {earlier})) / 86400.0"


def _trail(events: str, *, dims: str = "") -> str:
    """Rows of the trail: its office as the row recorded it."""
    return (
        "SELECT l.occurred_at AS at, l.detail_json ->> 'office' AS office, 1 AS v"
        + (f", {dims}" if dims else "")
        + f" FROM audit_log l WHERE l.event_type IN ({events})"
    )


_DUTY_DUE = """coalesce(
       (SELECT x.due_at FROM breach_obligation_event x
         WHERE x.obligation_id = o.obligation_id AND x.kind = 'extended' AND x.due_at IS NOT NULL
         ORDER BY x.recorded_at DESC LIMIT 1),
       o.due_at, e.occurred_at)"""

_DUTY = f"""SELECT e.occurred_at AS at, {_office("b")} AS office, o.kind AS d_duty, 1 AS v
  FROM breach_obligation_event e
  JOIN breach_obligation o ON o.obligation_id = e.obligation_id
  JOIN breach b ON b.breach_id = o.breach_id
 WHERE e.kind = 'completed'"""

_ERASURE = f"""SELECT {{at}} AS at, {_office("r")} AS office, 1 AS v
  FROM datavault_erasure_asset a
  JOIN datavault_erasure e ON e.erasure_id = a.erasure_id
  JOIN rights_request r ON r.request_id = e.request_id"""

_HOLDER = f"""SELECT {{at}} AS at, {_office("r")} AS office, h.label AS d_holder, {{v}} AS v
  FROM rights_request_holder h JOIN rights_request r ON r.request_id = h.request_id"""

_NOTICE_DELIVERY = f"""SELECT d.recorded_at AS at, {_office("b")} AS office, d.channel AS d_channel,
       1 AS v
  FROM breach_notice_delivery d
  JOIN breach_notice n ON n.notice_id = d.notice_id
  JOIN breach b ON b.breach_id = n.breach_id
 WHERE d.channel IN ('email', 'sms')"""

_LINK_OPENED = f"""SELECT l.occurred_at AS at, {_office("cl")} AS office,
       p.project_name AS d_project, 1 AS v
  FROM audit_log l
  JOIN consent_link cl ON cl.link_id = l.entity_id
  JOIN notice n ON n.notice_id = cl.notice_id
  JOIN project p ON p.project_id = n.project_id
 WHERE l.event_type = 'link.opened' AND l.entity_type = 'consent_link'"""

_TRANSITION = f"""SELECT l.occurred_at AS at, {_office("p")} AS office, {{v}} AS v
  FROM audit_log l JOIN project p ON p.project_id = l.entity_id
 WHERE l.event_type = 'project.transitioned' AND l.entity_type = 'project'"""

_SCOPED_CONSENT = _CONSENT + " WHERE ({scope})"

#: Every metric's rows, keyed as the catalogue. Placeholders: `{scope}`, the
#: project scope predicate on `p`; `{user}`, the reader's account id.
SOURCES: Final[dict[str, str]] = {
    # ---------------------------------------------------------------- rights
    "rights.received": _rights("r.received_at", "TRUE"),
    "rights.closed": _rights("r.closed_at", "r.closed_at IS NOT NULL"),
    "rights.closed_on_time": _rights(
        "r.closed_at", "r.closed_at IS NOT NULL AND r.closed_at <= r.due_at"
    ),
    "rights.median_days_to_close": _rights(
        "r.closed_at", "r.closed_at IS NOT NULL", _days("r.closed_at", "r.received_at")
    ),
    "rights.open": _rights("now()", "r.status <> 'closed'"),
    "rights.overdue": _rights("now()", "r.status <> 'closed' AND r.due_at < now()"),
    "rights.grievances": _rights("r.received_at", "r.request_type = 'grievance'"),
    "rights.grievances_upheld": _rights(
        "r.closed_at", "r.request_type = 'grievance' AND r.outcome = 'upheld'"
    ),
    "rights.median_days_to_acknowledge": _rights(
        "r.acknowledged_at",
        "r.acknowledged_at IS NOT NULL",
        _days("r.acknowledged_at", "r.received_at"),
    ),
    "rights.median_days_to_verify": _rights(
        "r.verified_at", "r.verified_at IS NOT NULL", _days("r.verified_at", "r.received_at")
    ),
    "rights.median_days_to_respond": _rights(
        "r.responded_at", "r.responded_at IS NOT NULL", _days("r.responded_at", "r.received_at")
    ),
    # ---------------------------------------------------------------- breach
    "breach.incidents": f"""SELECT b.detected_at AS at, {_office("b")} AS office,
       b.location_kind AS d_location, 1 AS v FROM breach b""",
    "breach.confirmed": f"""SELECT rec.recorded_at AS at, {_office("b")} AS office,
       b.location_kind AS d_location, 1 AS v
  FROM breach_recording rec JOIN breach b ON b.breach_id = rec.breach_id""",
    "breach.open": f"""SELECT now() AS at, {_office("b")} AS office, 1 AS v
  FROM breach b WHERE b.status <> 'closed'""",
    "breach.duties_completed": _DUTY,
    "breach.duties_on_time": _DUTY + f" AND e.occurred_at <= {_DUTY_DUE}",
    "breach.public_reports": """SELECT ir.received_at AS at, NULL::text AS office, 1 AS v,
       CASE WHEN ir.breach_id IS NOT NULL OR ir.claimed_at IS NOT NULL THEN 'taken up'
            WHEN ir.dismissed_at IS NOT NULL THEN 'dismissed' ELSE 'waiting' END AS d_outcome
  FROM incident_report ir""",
    "breach.median_hours_to_confirm": f"""SELECT rec.recorded_at AS at, {_office("b")} AS office,
       extract(epoch FROM (rec.recorded_at - b.detected_at)) / 3600.0 AS v
  FROM breach_recording rec JOIN breach b ON b.breach_id = rec.breach_id""",
    # --------------------------------------------------------------- consent
    "consent.given": _CONSENT + f" WHERE NOT c.is_withdrawal AND {_GRANTED.format(c='c')}",
    "consent.withdrawn": _CONSENT + " WHERE c.is_withdrawal",
    "consent.active": f"""SELECT now() AS at, {_office("n")} AS office,
       p.project_name AS d_project, 1 AS v
  FROM v_current_consent c
  JOIN notice n  ON n.notice_id = c.notice_id
  JOIN project p ON p.project_id = n.project_id
 WHERE {_GRANTED.format(c="c")}""",
    "consent.expiring_90d": f"""SELECT now() AS at, {_office("n")} AS office, 1 AS v
  FROM v_current_consent c JOIN notice n ON n.notice_id = c.notice_id
 WHERE EXISTS (SELECT 1 FROM consent_purpose_grant g JOIN purpose pu ON pu.purpose_id = g.purpose_id
                WHERE g.consent_id = c.consent_id AND g.granted
                  AND pu.consent_validity_period IS NOT NULL
                  AND c.affirmative_action_at + pu.consent_validity_period
                      BETWEEN now() AND now() + interval '90 days')""",
    "funnel.links_opened": _LINK_OPENED,
    "funnel.notices_served": f"""SELECT l.occurred_at AS at, {_office("n")} AS office, 1 AS v
  FROM audit_log l JOIN notice n ON n.notice_id = l.entity_id
 WHERE l.event_type = 'notice.served' AND l.entity_type = 'notice'""",
    "funnel.declined": _CONSENT + f" WHERE NOT c.is_withdrawal AND NOT {_GRANTED.format(c='c')}",
    "hr.consents": _CONSENT
    + f" WHERE NOT c.is_withdrawal AND {_GRANTED.format(c='c')} AND p.category_id IS NOT NULL",
    "hr.withdrawals": _CONSENT + " WHERE c.is_withdrawal AND p.category_id IS NOT NULL",
    # -------------------------------------------------------------- projects
    "projects.approved": _TRANSITION.format(v="1") + " AND l.detail_json ->> 'to' = 'approved'",
    "projects.median_days_to_approve": _TRANSITION.format(v=_days("l.occurred_at", "p.created_at"))
    + " AND l.detail_json ->> 'to' = 'approved'",
    "projects.sent_back": _TRANSITION.format(v="1")
    + " AND l.detail_json ->> 'to' = 'in_draft' AND l.detail_json ->> 'from' <> 'in_draft'",
    "projects.active": f"""SELECT now() AS at, {_office("p")} AS office,
       p.project_status::text AS d_status, 1 AS v FROM project p""",
    # --------------------------------------------------------------- erasure
    "erasure.assets_sent": _ERASURE.format(at="e.sent_at"),
    "erasure.assets_erased": _ERASURE.format(at="a.completed_at")
    + " WHERE a.status = 'erased' AND a.completed_at IS NOT NULL",
    "erasure.assets_failed": _ERASURE.format(at="a.status_at")
    + " WHERE a.status = 'failed' AND a.status_at IS NOT NULL",
    # --------------------------------------------------------------- holders
    "holders.tickets_issued": _HOLDER.format(at="h.issued_at", v="1")
    + " WHERE h.issued_at IS NOT NULL",
    "holders.median_days_to_return": _HOLDER.format(
        at="h.returned_at", v=_days("h.returned_at", "h.issued_at")
    )
    + " WHERE h.returned_at IS NOT NULL AND h.issued_at IS NOT NULL",
    "holders.overdue": _HOLDER.format(at="now()", v="1")
    + " WHERE h.issued_at IS NOT NULL AND h.returned_at IS NULL AND h.due_at < now()"
    " AND r.status <> 'closed'",
    # -------------------------------------------------------------- delivery
    "delivery.notices_delivered": _NOTICE_DELIVERY + " AND d.status = 'delivered'",
    "delivery.notices_attempted": _NOTICE_DELIVERY + " AND d.status IN ('delivered', 'failed')",
    # ------------------------------------------------------------- your work
    "mine.projects": f"""SELECT now() AS at, {_office("p")} AS office,
       p.project_status::text AS d_status, p.project_name AS d_project, 1 AS v
  FROM project p WHERE ({{scope}})""",
    "mine.consents_given": _SCOPED_CONSENT
    + f" AND NOT c.is_withdrawal AND {_GRANTED.format(c='c')}",
    "mine.consents_withdrawn": _SCOPED_CONSENT + " AND c.is_withdrawal",
    "mine.links_opened": _LINK_OPENED + " AND ({scope})",
    "mine.links_active": f"""SELECT now() AS at, {_office("cl")} AS office,
       p.project_name AS d_project, 1 AS v
  FROM consent_link cl JOIN notice n ON n.notice_id = cl.notice_id
  JOIN project p ON p.project_id = n.project_id
 WHERE cl.status = 'active' AND (cl.expires_at IS NULL OR cl.expires_at > now()) AND ({{scope}})""",
    "mine.sites_active": f"""SELECT now() AS at, {_office("p")} AS office,
       p.project_name AS d_project, 1 AS v
  FROM project_site s JOIN project p ON p.project_id = s.project_id
 WHERE s.status = 'active' AND ({{scope}})""",
    "mine.tickets_returned": f"""SELECT h.returned_at AS at, {_office("r")} AS office, 1 AS v
  FROM rights_request_holder h JOIN rights_request r ON r.request_id = h.request_id
 WHERE h.returned_at IS NOT NULL AND h.responder_user_id = {{user}}""",
    # ---------------------------------------------------------------- health
    "health.otp_requested": _trail(
        "'auth.otp_requested'", dims="l.detail_json ->> 'flow' AS d_flow"
    ),
    "health.otp_verified": _trail("'auth.otp_verified'", dims="l.detail_json ->> 'flow' AS d_flow"),
    "health.sign_in_failures": _trail(
        "'auth.login_failed', 'auth.mfa_failed'", dims="l.event_type AS d_event"
    ),
    "health.lockouts": _trail("'auth.login_locked_out'"),
    "health.access_denied": _trail("'auth.access_denied'"),
    "health.audit_checks": _trail("'audit.verified'"),
    "health.audit_breaks": _trail("'audit.verified'") + " AND l.detail_json ->> 'intact' = 'false'",
    "health.breach_notice_failures": """SELECT d.recorded_at AS at, NULL::text AS office,
       d.channel AS d_channel, 1 AS v
  FROM breach_notice_delivery d WHERE d.status = 'failed' AND d.channel IN ('email', 'sms')""",
    "health.board_mail_failures": """SELECT d.recorded_at AS at, NULL::text AS office, 1 AS v
  FROM breach_report_delivery d WHERE d.status = 'failed'""",
    "health.datavault_pending": """SELECT now() AS at, NULL::text AS office, 1 AS v
  FROM datavault_consent_change c WHERE c.delivered_at IS NULL AND c.superseded_at IS NULL""",
    "health.datavault_failing": """SELECT now() AS at, NULL::text AS office, 1 AS v
  FROM datavault_consent_change c
 WHERE c.delivered_at IS NULL AND c.superseded_at IS NULL AND c.failure IS NOT NULL""",
    "health.reports_failed": f"""SELECT r.created_at AS at, {_office("r")} AS office, 1 AS v
  FROM report r WHERE r.status = 'failed'""",
    # ---------------------------------------------------------- data quality
    "quality.people_without_contact": """SELECT now() AS at, NULL::text AS office, 1 AS v
  FROM auth_user u
 WHERE u.role = 'data_subject' AND u.status = 'active'
   AND u.email_verified_at IS NULL AND u.mobile_verified_at IS NULL""",
    "quality.unmapped_assets": f"""SELECT now() AS at, {_office("p")} AS office, 1 AS v
  FROM data_asset da JOIN collection col ON col.collection_id = da.collection_id
  JOIN project p ON p.project_id = col.project_id WHERE da.has_unmapped_subjects""",
    "quality.processors_unconfirmed": """SELECT now() AS at, NULL::text AS office, 1 AS v
  FROM processor x WHERE x.status = 'active' AND x.security_confirmed_at IS NULL""",
    "quality.processors_no_country": """SELECT now() AS at, NULL::text AS office, 1 AS v
  FROM processor x WHERE x.status = 'active' AND x.location_country IS NULL""",
}

#: The grains a series may be bucketed by.
GRAINS: Final = ("day", "week", "month", "quarter", "year")


async def series(
    conn: Conn,
    key: str,
    *,
    start: datetime | None,
    end: datetime | None,
    office: str | None,
    dim: str | None,
    grain: str | None,
    median: bool,
    scope: tuple[str, list[Any]] | None = None,
    user_id: int | None = None,
) -> list[Row]:
    """The metric's rows for the period, as `(bucket, dim, value)`.

    `start`/`end` None: as things stand (a snapshot), no period applied. `dim`
    None: one figure. `grain` None: one bucket for the whole period. `office`
    None: every office; otherwise its rows and the rows of no office. A median
    is taken of `v`; anything else counts rows."""
    source = SOURCES[key]
    params: list[Any] = []
    if "{scope}" in source:
        if scope is None:
            raise ValueError(f"{key} needs a scope")
        pred, pred_params = scope
        source = source.replace("{scope}", pred.replace("%(u)s", "%s"))
        params.extend(pred_params)
    if "{user}" in source:
        source = source.replace("{user}", "%s")
        params.append(int(user_id or 0))
    where = ["TRUE"]
    if start is not None:
        where.append("s.at >= %s")
        params.append(start)
    if end is not None:
        where.append("s.at < %s")
        params.append(end)
    if office is not None:
        where.append("(s.office = %s OR s.office IS NULL)")
        params.append(office)
    if grain is not None:
        if grain not in GRAINS:
            raise ValueError(grain)
        bucket = f"date_trunc('{grain}', s.at AT TIME ZONE 'Asia/Kolkata')::date"
    else:
        bucket = "NULL::date"
    dim_sql = f"s.d_{dim}" if dim else "NULL::text"
    if dim == "office":
        dim_sql = "s.office"
    value = "percentile_cont(0.5) WITHIN GROUP (ORDER BY s.v)" if median else "count(*)::numeric"
    return await fetch_all(
        conn,
        f"""WITH s AS ({source})
            SELECT {bucket} AS bucket, {dim_sql} AS dim, {value} AS value
              FROM s WHERE {" AND ".join(where)}
             GROUP BY 1, 2 ORDER BY 1 NULLS FIRST, 2 NULLS FIRST""",
        params,
    )


# ------------------------------------------------------ targets, settings


async def targets(conn: Conn) -> dict[str, Row]:
    rows = await fetch_all(
        conn,
        """SELECT t.metric_key, t.target, t.amber, t.updated_at, u.full_name AS updated_by_name
             FROM analytics_target t LEFT JOIN auth_user u ON u.id = t.updated_by""",
    )
    return {str(r["metric_key"]): r for r in rows}


async def set_target(
    conn: Conn, key: str, *, target: float, amber: float | None, actor_id: int
) -> None:
    await conn.execute(
        """INSERT INTO analytics_target (metric_key, target, amber, updated_by)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT (metric_key) DO UPDATE
              SET target = EXCLUDED.target, amber = EXCLUDED.amber,
                  updated_by = EXCLUDED.updated_by, updated_at = now()""",
        (key, target, amber, actor_id),
    )


async def reset_target(conn: Conn, key: str) -> bool:
    cur = await conn.execute("DELETE FROM analytics_target WHERE metric_key = %s", (key,))
    return bool(cur.rowcount)


async def setting(conn: Conn) -> Row:
    row = await fetch_one(
        conn,
        """SELECT s.small_number_threshold, s.updated_at, u.full_name AS updated_by_name
             FROM analytics_setting s LEFT JOIN auth_user u ON u.id = s.updated_by
            WHERE s.setting_id = 1""",
    )
    return row or {"small_number_threshold": 1, "updated_at": None, "updated_by_name": None}


async def set_threshold(conn: Conn, threshold: int, *, actor_id: int) -> None:
    await conn.execute(
        """UPDATE analytics_setting SET small_number_threshold = %s, updated_by = %s,
                  updated_at = now() WHERE setting_id = 1""",
        (threshold, actor_id),
    )


# ----------------------------------------------------- the record of processing


async def inventory(conn: Conn, *, office: str | None) -> dict[str, list[Row]]:
    """Purposes, processors and sources: what the organisation processes, for
    what, on what basis, for how long, by whom and where."""
    clause, params = ("TRUE", []) if office is None else ("o.office_code = %s", [office])
    purposes = await fetch_all(
        conn,
        f"""SELECT pu.purpose_code, pu.name, pu.status::text AS status,
                   pu.lawful_basis::text AS lawful_basis, pu.data_categories,
                   pu.retention_period::text AS retention_period,
                   pu.retention_basis::text AS retention_basis,
                   pu.consent_validity_period::text AS consent_validity_period,
                   pu.cross_border_permitted, pu.permitted_for_minors, o.office_code AS office
              FROM purpose pu JOIN office o ON o.office_id = pu.office_id
             WHERE {clause} ORDER BY o.office_code, pu.purpose_code""",
        params,
    )
    processors = await fetch_all(
        conn,
        """SELECT x.legal_name, x.type::text AS type, x.status::text AS status, x.is_in_house,
                  x.location_country, x.security_confirmed_at, x.contract_ref
             FROM processor x ORDER BY x.legal_name""",
    )
    sources = await fetch_all(
        conn,
        """SELECT s.source_code, s.name, s.status::text AS status,
                  s.source_role::text AS source_role, s.exchange_mode::text AS exchange_mode,
                  x.legal_name AS processor
             FROM data_source s LEFT JOIN processor x ON x.processor_id = s.processor_id
            ORDER BY s.source_code""",
    )
    return {"purposes": purposes, "processors": processors, "sources": sources}


# -------------------------------------------------------------------- reports

_REPORT = """SELECT r.report_id, r.report_uuid::text AS report_uuid, r.kind, r.title, r.params,
       r.format, r.status, r.file_ref, r.file_sha256, r.file_bytes, r.error,
       r.requested_by, r.requested_role::text AS requested_role, r.created_at, r.ready_at,
       (SELECT o.office_code FROM office o WHERE o.office_id = r.office_id) AS office,
       u.full_name AS requested_by_name, s.schedule_uuid::text AS schedule_uuid
  FROM report r
  LEFT JOIN auth_user u ON u.id = r.requested_by
  LEFT JOIN report_schedule s ON s.schedule_id = r.schedule_id"""


async def add_report(
    conn: Conn,
    *,
    kind: str,
    title: str,
    params: dict[str, Any],
    office: str | None,
    fmt: str,
    requested_by: int | None,
    requested_role: str,
    schedule_id: int | None = None,
) -> Row:
    from psycopg.types.json import Jsonb

    row = await fetch_one(
        conn,
        """INSERT INTO report (kind, title, params, office_id, format, requested_by,
                               requested_role, schedule_id)
           VALUES (%s, %s, %s, (SELECT office_id FROM office WHERE office_code = %s), %s, %s,
                   %s::user_role, %s)
           RETURNING report_id, report_uuid::text AS report_uuid""",
        (kind, title, Jsonb(params), office, fmt, requested_by, requested_role, schedule_id),
    )
    assert row is not None
    return row


async def report_by_uuid(conn: Conn, report_uuid: str) -> Row | None:
    return await fetch_one(conn, _REPORT + " WHERE r.report_uuid = %s", (report_uuid,))


async def report_by_id(conn: Conn, report_id: int) -> Row | None:
    return await fetch_one(conn, _REPORT + " WHERE r.report_id = %s", (report_id,))


async def reports(
    conn: Conn,
    *,
    kinds: list[str],
    office: str | None,
    private_for: int | None,
    private_kinds: list[str],
    limit: int = 200,
) -> list[Row]:
    """The reports of these kinds the reader may see: of their office (an
    officer's), and of a private kind only their own."""
    if not kinds:
        return []
    where = ["r.kind = ANY(%s)"]
    params: list[Any] = [kinds]
    if office is not None:
        where.append("r.office_id = (SELECT office_id FROM office WHERE office_code = %s)")
        params.append(office)
    where.append("(NOT (r.kind = ANY(%s)) OR r.requested_by = %s)")
    params.extend([private_kinds, private_for or 0])
    return await fetch_all(
        conn,
        _REPORT + f" WHERE {' AND '.join(where)} ORDER BY r.created_at DESC LIMIT %s",
        [*params, limit],
    )


async def report_ready(
    conn: Conn, report_id: int, *, file_ref: str, sha256: str, size: int
) -> None:
    await conn.execute(
        """UPDATE report SET status = 'ready', file_ref = %s, file_sha256 = %s, file_bytes = %s,
                  ready_at = now(), error = NULL WHERE report_id = %s""",
        (file_ref, sha256, size, report_id),
    )


async def report_failed(conn: Conn, report_id: int, error: str) -> None:
    await conn.execute(
        "UPDATE report SET status = 'failed', error = %s WHERE report_id = %s",
        (error[:500], report_id),
    )


async def delete_report(conn: Conn, report_id: int) -> None:
    await conn.execute("DELETE FROM report WHERE report_id = %s", (report_id,))


# ------------------------------------------------------------------ schedules

_SCHEDULE = """SELECT s.schedule_id, s.schedule_uuid::text AS schedule_uuid, s.kind, s.title,
       s.params, s.format, s.cadence, s.recipient_roles, s.active, s.created_by,
       s.created_role::text AS created_role, s.created_at, s.last_run_at, s.next_run_at,
       (SELECT o.office_code FROM office o WHERE o.office_id = s.office_id) AS office,
       u.full_name AS created_by_name
  FROM report_schedule s LEFT JOIN auth_user u ON u.id = s.created_by"""


async def add_schedule(
    conn: Conn,
    *,
    kind: str,
    title: str,
    params: dict[str, Any],
    fmt: str,
    cadence: str,
    recipient_roles: list[str],
    office: str | None,
    created_by: int,
    created_role: str,
    next_run_at: datetime,
) -> Row:
    from psycopg.types.json import Jsonb

    row = await fetch_one(
        conn,
        """INSERT INTO report_schedule (kind, title, params, format, cadence, recipient_roles,
                                        office_id, created_by, created_role, next_run_at)
           VALUES (%s, %s, %s, %s, %s, %s,
                   (SELECT office_id FROM office WHERE office_code = %s), %s, %s::user_role, %s)
           RETURNING schedule_id, schedule_uuid::text AS schedule_uuid""",
        (
            kind,
            title,
            Jsonb(params),
            fmt,
            cadence,
            recipient_roles,
            office,
            created_by,
            created_role,
            next_run_at,
        ),
    )
    assert row is not None
    return row


async def schedule_by_uuid(conn: Conn, schedule_uuid: str) -> Row | None:
    return await fetch_one(conn, _SCHEDULE + " WHERE s.schedule_uuid = %s", (schedule_uuid,))


async def schedules(conn: Conn, *, kinds: list[str], office: str | None) -> list[Row]:
    if not kinds:
        return []
    where = ["s.kind = ANY(%s)"]
    params: list[Any] = [kinds]
    if office is not None:
        where.append("s.office_id = (SELECT office_id FROM office WHERE office_code = %s)")
        params.append(office)
    return await fetch_all(
        conn, _SCHEDULE + f" WHERE {' AND '.join(where)} ORDER BY s.created_at DESC", params
    )


async def due_schedules(conn: Conn, now: datetime) -> list[Row]:
    return await fetch_all(
        conn,
        _SCHEDULE + " WHERE s.active AND s.next_run_at <= %s ORDER BY s.next_run_at FOR UPDATE OF s"
        " SKIP LOCKED",
        (now,),
    )


async def set_schedule(conn: Conn, schedule_id: int, *, active: bool) -> None:
    await conn.execute(
        "UPDATE report_schedule SET active = %s WHERE schedule_id = %s", (active, schedule_id)
    )


async def schedule_ran(
    conn: Conn, schedule_id: int, *, ran_at: datetime, next_at: datetime
) -> None:
    await conn.execute(
        "UPDATE report_schedule SET last_run_at = %s, next_run_at = %s WHERE schedule_id = %s",
        (ran_at, next_at, schedule_id),
    )


async def delete_schedule(conn: Conn, schedule_id: int) -> None:
    await conn.execute("DELETE FROM report_schedule WHERE schedule_id = %s", (schedule_id,))


async def emails_for_roles(conn: Conn, roles: list[str], *, office: str | None) -> list[str]:
    """The active accounts of these roles, each once - of the office named for
    an office's own roles, of any for the rest."""
    if not roles:
        return []
    from cmp.core.permissions import OFFICE_ROLES

    rows = await fetch_all(
        conn,
        """SELECT DISTINCT u.email, u.id FROM auth_user u
             LEFT JOIN office o ON o.office_id = u.office_id
            WHERE u.status = 'active' AND u.role::text = ANY(%s) AND u.email IS NOT NULL
              AND (%s::text IS NULL OR NOT (u.role::text = ANY(%s)) OR o.office_code = %s)
            ORDER BY u.id""",
        (roles, office, list(OFFICE_ROLES), office),
    )
    return [str(r["email"]) for r in rows]


async def trail_for(conn: Conn, entity_type: str, entity_id: int) -> list[Row]:
    """Every row of the trail about one record and what belongs to it, oldest first."""
    from cmp.db.repositories.audit import AuditFilters, export_rows

    rows = await export_rows(
        conn, AuditFilters(entity_type=entity_type, entity_id=entity_id), limit=5000
    )
    return list(reversed(rows))


async def entity_id_of(conn: Conn, entity_type: str, entity_uuid: str) -> tuple[int, str] | None:
    """A rights request's or a breach's id and reference, by its uuid."""
    if entity_type == "rights_request":
        row = await fetch_one(
            conn,
            "SELECT request_id AS id, reference FROM rights_request WHERE request_uuid = %s",
            (entity_uuid,),
        )
    elif entity_type == "breach":
        row = await fetch_one(
            conn,
            """SELECT b.breach_id AS id, coalesce(rec.reference, b.reference) AS reference
                 FROM breach b LEFT JOIN breach_recording rec ON rec.breach_id = b.breach_id
                WHERE b.breach_uuid = %s""",
            (entity_uuid,),
        )
    else:
        return None
    return (int(row["id"]), str(row["reference"])) if row else None


async def breaches_in(
    conn: Conn, *, start: datetime, end: datetime, office: str | None
) -> list[Row]:
    """The breaches detected or confirmed in a period, with how their duties
    stand: for the board pack. References and counts only."""
    clause, params = ("TRUE", []) if office is None else ("o.office_code = %s", [office])
    return await fetch_all(
        conn,
        f"""SELECT coalesce(rec.reference, b.reference) AS reference, b.detected_at,
                   rec.recorded_at AS confirmed_at, b.status, b.location_kind, o.office_code,
                   (SELECT count(*) FROM breach_obligation bo WHERE bo.breach_id = b.breach_id)
                     AS duties,
                   (SELECT count(*) FROM breach_obligation bo
                      JOIN breach_obligation_event e ON e.obligation_id = bo.obligation_id
                     WHERE bo.breach_id = b.breach_id AND e.kind = 'completed') AS completed
              FROM breach b
              JOIN office o ON o.office_id = b.office_id
              LEFT JOIN breach_recording rec ON rec.breach_id = b.breach_id
             WHERE {clause}
               AND ((b.detected_at >= %s AND b.detected_at < %s)
                 OR (rec.recorded_at >= %s AND rec.recorded_at < %s))
             ORDER BY b.detected_at""",
        [*params, start, end, start, end],
    )


async def read_as(conn: Conn, office: str | None) -> None:
    """Have this connection read as an office reads - or both - for a report
    the worker makes on an officer's behalf: the same rows their session would."""
    await conn.execute("SELECT set_config('app.office', %s, false)", (office or "all",))
