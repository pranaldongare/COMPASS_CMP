"""The dashboards' own queries.

Moved out of `api/routers/v1/dashboard.py` (review 2026-10-01, ARCH-5), where
they were written inline in the router. Each is the count or the short queue
one role's dashboard shows, copied unchanged; the router decides which role
sees which, and shapes the response.
"""

from __future__ import annotations

from cmp.core.permissions import Role
from cmp.db.repositories.projects import scope_predicate
from cmp.db.sql import Conn, Row, fetch_all, fetch_one


async def projects_in_scope(conn: Conn, role: Role, user_id: int) -> list[Row]:
    """The ids of the projects in this caller's *read* scope - the register's
    own predicate, imported rather than restated, so the feed and the project
    list cannot show different worlds."""
    pred, pred_params = scope_predicate(role, user_id)
    return await fetch_all(conn, f"SELECT p.project_id FROM project p WHERE {pred}", pred_params)


async def rnd_counts(conn: Conn, user_id: int) -> Row | None:
    return await fetch_one(
        conn,
        """SELECT
             count(*) AS total,
             count(*) FILTER (WHERE project_status IN ('in_draft', 'under_process'))
                                                                         AS in_draft,
             count(*) FILTER (WHERE project_status = 'pending_approval') AS pending_approval,
             count(*) FILTER (WHERE project_status = 'approved')         AS approved,
             count(*) FILTER (WHERE project_status = 'closed')           AS closed
           FROM project WHERE created_by = %s""",
        (user_id,),
    )


async def rnd_queue(conn: Conn, user_id: int) -> list[Row]:
    return await fetch_all(
        conn,
        """SELECT p.project_uuid, p.project_name, p.project_status, p.updated_at,
                  'Upload a security approval with its proof file' AS action
           FROM project p
           WHERE p.created_by = %s
             AND p.project_status IN ('in_draft', 'under_process')
             AND NOT EXISTS (
               SELECT 1 FROM project_approval a
               WHERE a.project_id = p.project_id
                 AND coalesce(length(trim(a.proof_file_ref)), 0) > 0)
           ORDER BY p.updated_at DESC LIMIT 25""",
        (user_id,),
    )


async def projects_created_by(conn: Conn, user_id: int) -> list[Row]:
    return await fetch_all(
        conn,
        "SELECT project_id FROM project WHERE created_by = %s",
        (user_id,),
    )


async def dpo_counts(conn: Conn) -> Row | None:
    """The DPO's figures, the four consent states among them.

    Each current record is in exactly one state, by what it grants now: every
    purpose (`consents_full`), some (`consents_partial`), none and never
    withdrawn from (`consents_declined`), or none after a withdrawal
    (`consents_withdrawn`). Before 2026-10-05 the dashboard showed total minus
    withdrawals as "still standing", counting declined and partial records as
    standing consent (UX review).
    """
    return await fetch_one(
        conn,
        """WITH states AS (
             SELECT vc.is_withdrawal,
                    count(g.*) FILTER (WHERE g.granted) AS granted,
                    count(g.*)                          AS asked
               FROM v_current_consent vc
               LEFT JOIN consent_purpose_grant g ON g.consent_id = vc.consent_id
              GROUP BY vc.consent_id, vc.is_withdrawal)
           SELECT
             (SELECT count(*) FILTER (WHERE granted > 0 AND granted = asked) FROM states)
               AS consents_full,
             (SELECT count(*) FILTER (WHERE granted > 0 AND granted < asked) FROM states)
               AS consents_partial,
             (SELECT count(*) FILTER (WHERE granted = 0 AND NOT is_withdrawal) FROM states)
               AS consents_declined,
             (SELECT count(*) FILTER (WHERE granted = 0 AND is_withdrawal) FROM states)
               AS consents_withdrawn,
             (SELECT count(*) FROM project WHERE project_status = 'in_draft')
               AS in_draft,
             (SELECT count(*) FROM project WHERE project_status = 'pending_approval')
               AS pending_approval,
             (SELECT count(*) FROM project WHERE project_status = 'approved')
               AS approved,
             (SELECT count(*) FROM notice WHERE status = 'draft')      AS draft_notices,
             (SELECT count(*) FROM purpose WHERE status = 'draft')     AS draft_purposes,
             (SELECT count(*) FROM v_current_consent)                  AS total_consents,
             (SELECT count(*) FROM v_current_consent vc
               WHERE vc.is_withdrawal AND NOT EXISTS (
                 SELECT 1 FROM consent_purpose_grant g
                  WHERE g.consent_id = vc.consent_id AND g.granted))
               AS withdrawals,
             (SELECT count(*) FROM notice_language WHERE approved_at IS NULL)
               AS unapproved_languages""",
    )


async def dpo_draft_queue(conn: Conn) -> list[Row]:
    return await fetch_all(
        conn,
        """SELECT p.project_uuid, p.project_name, p.updated_at,
                  'Activate the purposes on its notice' AS action
           FROM project p
           WHERE p.project_status = 'in_draft'
             AND EXISTS (
                   SELECT 1
                     FROM notice n
                     JOIN notice_purpose np ON np.notice_id = n.notice_id
                     JOIN purpose pr        ON pr.purpose_id = np.purpose_id
                    WHERE n.project_id = p.project_id
                      AND n.status IN ('draft', 'approved')
                      AND pr.status <> 'active'
                 )
           ORDER BY p.updated_at DESC LIMIT 25""",
    )


async def dpo_approval_queue(conn: Conn) -> list[Row]:
    return await fetch_all(
        conn,
        """SELECT p.project_uuid, p.project_name, p.updated_at,
                  'Review the approval documents' AS action
           FROM project p WHERE p.project_status = 'pending_approval'
           ORDER BY p.updated_at DESC LIMIT 25""",
    )


async def dco_counts(conn: Conn, user_id: int) -> Row | None:
    return await fetch_one(
        conn,
        """SELECT
             (SELECT count(*) FROM project WHERE dco_user_id = %(u)s
                AND project_status = 'approved')                       AS approved_projects,
             (SELECT count(*) FROM consent_link cl
                JOIN notice n ON n.notice_id = cl.notice_id
                JOIN project p ON p.project_id = n.project_id
               WHERE p.dco_user_id = %(u)s AND cl.status = 'active')    AS active_links,
             (SELECT count(*) FROM v_current_consent vc
                JOIN notice n ON n.notice_id = vc.notice_id
                JOIN project p ON p.project_id = n.project_id
               WHERE p.dco_user_id = %(u)s)                            AS consents,
             (SELECT count(*) FROM export_log e
                JOIN project p ON p.project_id = e.project_id
               WHERE p.dco_user_id = %(u)s)                            AS exports,
             (SELECT count(*) FROM data_asset a
                JOIN collection c ON c.collection_id = a.collection_id
                JOIN project p ON p.project_id = c.project_id
               WHERE p.dco_user_id = %(u)s AND a.has_unmapped_subjects) AS flagged_assets""",
        {"u": user_id},
    )


async def dco_exceptions(conn: Conn, user_id: int) -> list[Row]:
    return await fetch_all(
        conn,
        """SELECT c.collection_uuid, c.source_collection_ref, c.collected_on,
                  c.declared_asset_count,
                  (SELECT count(*) FROM data_asset a
                    WHERE a.collection_id = c.collection_id) AS mapped_asset_count,
                  p.project_uuid, p.project_name
           FROM collection c JOIN project p ON p.project_id = c.project_id
           WHERE p.dco_user_id = %s
             AND c.declared_asset_count >
                 (SELECT count(*) FROM data_asset a WHERE a.collection_id = c.collection_id)
           ORDER BY c.collected_on DESC LIMIT 25""",
        (user_id,),
    )


async def dco_admin_counts(conn: Conn) -> Row | None:
    return await fetch_one(
        conn,
        """SELECT
             count(DISTINCT p.project_id)                                AS projects,
             count(DISTINCT p.project_id) FILTER (
               WHERE p.project_status = 'approved')                      AS approved_projects,
             count(DISTINCT ps.site_id) FILTER (
               WHERE ps.source_id IS NULL AND ps.status = 'active')      AS sites_awaiting_source,
             (SELECT count(*) FROM data_source d
                JOIN processor pr ON pr.processor_id = d.processor_id
               WHERE NOT pr.is_in_house
                 AND d.owner_user_id IS NULL
                 AND d.status = 'active')                                AS sources_without_owner
           FROM project p
           JOIN project_processor pp ON pp.project_id = p.project_id
           JOIN processor pr ON pr.processor_id = pp.processor_id
           LEFT JOIN project_site ps ON ps.project_id = p.project_id
          WHERE NOT pr.is_in_house""",
    )


async def dco_admin_awaiting(conn: Conn) -> list[Row]:
    return await fetch_all(
        conn,
        """SELECT DISTINCT p.project_uuid, p.project_name, p.project_status, p.updated_at,
                  ps.site_uuid, ps.site_label,
                  'Attach the data source that will collect here' AS action
           FROM project p
           JOIN project_processor pp ON pp.project_id = p.project_id
           JOIN processor pr ON pr.processor_id = pp.processor_id
           JOIN project_site ps ON ps.project_id = p.project_id
          WHERE NOT pr.is_in_house
            AND p.project_status = 'approved'
            AND ps.status = 'active'
            AND ps.source_id IS NULL
          ORDER BY p.updated_at DESC LIMIT 25""",
    )


async def dco_admin_fresh(conn: Conn) -> list[Row]:
    return await fetch_all(
        conn,
        """SELECT p.project_uuid, p.project_name, p.project_status,
                  pr.legal_name, pp.decided_at,
                  'Register the collection sites for this new processor' AS action
           FROM project_processor pp
           JOIN project p    ON p.project_id = pp.project_id
           JOIN processor pr ON pr.processor_id = pp.processor_id
          WHERE pp.status = 'approved'
            AND NOT pr.is_in_house
            AND p.project_status = 'approved'
            AND NOT EXISTS (SELECT 1 FROM project_site ps
                             WHERE ps.project_id = pp.project_id
                               AND ps.processor_id = pp.processor_id
                               AND ps.status = 'active')
          ORDER BY pp.decided_at DESC NULLS LAST
          LIMIT 25""",
    )


async def staff_invites_pending(conn: Conn) -> Row | None:
    return await fetch_one(
        conn,
        "SELECT count(*) AS n FROM auth_user WHERE status = 'pending' AND role <> 'data_subject'",
    )


async def inactive_registry_rows(conn: Conn) -> list[Row]:
    return await fetch_all(
        conn,
        """SELECT source_uuid, source_code, name, status FROM data_source
           WHERE status <> 'active'
           UNION ALL
           SELECT processor_uuid, contract_ref, legal_name, status FROM processor
           WHERE status <> 'active'
           LIMIT 50""",
    )


async def recent_lockouts(conn: Conn) -> list[Row]:
    return await fetch_all(
        conn,
        """SELECT l.occurred_at, u.full_name, u.email
           FROM audit_log l JOIN auth_user u ON u.id = l.subject_user_id
           WHERE l.event_type = 'auth.login_locked_out'
             AND l.occurred_at > now() - interval '24 hours'
           ORDER BY l.occurred_at DESC LIMIT 25""",
    )


async def subject_counts(conn: Conn, user_id: int) -> Row | None:
    return await fetch_one(
        conn,
        """WITH mine AS (
             SELECT vc.consent_id, vc.is_withdrawal,
                    count(*) FILTER (WHERE g.granted) AS granted
             FROM v_current_consent vc
             LEFT JOIN consent_purpose_grant g ON g.consent_id = vc.consent_id
             WHERE vc.auth_user_id = %(u)s
             GROUP BY vc.consent_id, vc.is_withdrawal)
           SELECT count(*) AS total,
                  count(*) FILTER (WHERE granted > 0)                       AS active,
                  count(*) FILTER (WHERE is_withdrawal AND granted = 0)     AS withdrawn,
                  count(*) FILTER (WHERE NOT is_withdrawal AND granted = 0) AS declined,
                  (SELECT count(*) FROM export_line WHERE auth_user_id = %(u)s)
                    AS times_shared
           FROM mine""",
        {"u": user_id},
    )


async def staff_feed(conn: Conn, role: Role, user_id: int, *, limit: int) -> list[Row]:
    """The staff notification feed: platform events the reader could open.

    The same predicate the project register uses decides: an event about a
    project, or about a notice on one, is shown to the people who could see
    that project in the register. Events with no project - a lockout, a
    withdrawal - stay with the roles whose section they belong to.
    """
    scope, scope_params = scope_predicate(role, user_id)
    return await fetch_all(
        conn,
        f"""SELECT l.log_uuid, l.event_type, l.entity_type, l.entity_id,
                      l.occurred_at, l.detail_json - '_hash' - '_prev' AS detail,
                      a.full_name AS actor_name
               FROM audit_log l LEFT JOIN auth_user a ON a.id = l.actor_user_id
               WHERE l.event_type IN (
                 'project.transitioned','notice.published','import.rejected',
                 'export.generated','consent.withdrawn','auth.login_locked_out')
                 AND (
                   CASE l.entity_type
                     WHEN 'project' THEN EXISTS (
                       SELECT 1 FROM project p
                        WHERE p.project_id = l.entity_id AND {scope})
                     WHEN 'notice' THEN EXISTS (
                       SELECT 1 FROM notice n
                         JOIN project p ON p.project_id = n.project_id
                        WHERE n.notice_id = l.entity_id AND {scope})
                     WHEN 'import_batch' THEN EXISTS (
                       SELECT 1 FROM import_batch b
                         JOIN project p ON p.project_id = b.project_id
                        WHERE b.batch_id = l.entity_id AND {scope})
                     WHEN 'export_log' THEN EXISTS (
                       SELECT 1 FROM export_log e
                         JOIN project p ON p.project_id = e.project_id
                        WHERE e.export_id = l.entity_id AND {scope})
                     -- No project: a lockout is the administrator's and
                     -- the DPO's; a withdrawal opens a consent record,
                     -- which only the DPO's role reads.
                     ELSE (l.event_type <> 'consent.withdrawn' AND %s) OR %s
                   END)
               ORDER BY l.occurred_at DESC LIMIT %s""",
        (
            *scope_params,
            *scope_params,
            *scope_params,
            *scope_params,
            role in (Role.DPO, Role.ADMIN),
            role is Role.DPO,
            limit,
        ),
    )
