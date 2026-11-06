"""Who holds whose data: one relation, read from both ends.

The platform knows three ways a processor comes to hold a person's data. An
export carried her consent record to the processor running its site
(`export_line`); an asset a processor's data source captured has her in it
(`asset_consent`); and, on the HR track, she consents to an activity whose
category names the processors that hold its data - the HRMS, the HR
database, the vendors (`category_processor`, ADR 0033). `_HOLDINGS` is that
relation, one row per (person, processor, export, asset or activity), and
nothing else in the platform re-derives it.

It is read from two directions:

* **a person's holders** - a rights request asks every processor that holds her
  data (`holders_of_person`, S2 and before);
* **a holder's people** - a breach at a processor or a data source reaches
  everyone whose data it holds (`people_held_by`, S3-02).

Keeping one relation is the point: a correction to how holdings are derived -
0032's move from the export's site to the line's destination is the example -
reaches both answers at once.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from cmp.db.sql import Conn, fetch_all, fetch_one

Row = dict[str, Any]

_HOLDINGS = """
  SELECT el.auth_user_id AS person_id, pr.processor_id, pr.legal_name,
         'export' AS via, e.export_uuid::text AS export_uuid, NULL::text AS asset_uuid,
         NULL::int AS source_id, el.consent_id, 'active' AS disposition, e.office_id
    FROM export_line el
    JOIN export_log e     ON e.export_id = el.export_id
    -- Where the line went: recorded on the line since 0032. Before it, only a
    -- per-site export named its site; a project export (since 0010) named none.
    LEFT JOIN project_site s ON s.site_id = e.site_id
    JOIN processor pr     ON pr.processor_id = COALESCE(el.destination_processor_id, s.processor_id)
  UNION ALL
  SELECT ca.auth_user_id, pr.processor_id, pr.legal_name,
         'asset', NULL, da.asset_uuid::text, da.source_id, ac.consent_id,
         coalesce(ac.disposition::text, 'active'), p.office_id
    FROM asset_consent ac
    JOIN consent_artefact ca ON ca.consent_id = ac.consent_id
    JOIN data_asset da       ON da.asset_id = ac.asset_id
    JOIN data_source ds      ON ds.source_id = da.source_id
    JOIN processor pr        ON pr.processor_id = ds.processor_id
    -- Left: only to name the office. A person's holders read past it, and an
    -- inner join would lose her assets the session's policy hides.
    LEFT JOIN collection c   ON c.collection_id = da.collection_id
    LEFT JOIN project p      ON p.project_id = c.project_id
  UNION ALL
  -- An HR activity's participant: her current consent's activity, its
  -- category's live processors. While the consent stands, not after.
  SELECT v.auth_user_id, pr.processor_id, pr.legal_name,
         'activity', p.project_uuid::text, NULL, NULL::int, v.consent_id, 'active', p.office_id
    FROM v_current_consent v
    JOIN notice n             ON n.notice_id = v.notice_id
    JOIN project p            ON p.project_id = n.project_id
    JOIN category_processor cp ON cp.category_id = p.category_id AND cp.removed_at IS NULL
    JOIN processor pr         ON pr.processor_id = cp.processor_id
   WHERE NOT v.is_withdrawal
"""


async def holders_of_person(
    conn: Conn, subject_user_id: int, *, consent_ids: list[int] | None = None
) -> list[Row]:
    """Who holds her data, from the records that say so. The DPO confirms.

    An asset counts while her appearance in it is active: one already
    quarantined or erased is being dealt with by the erasure executor, not by a
    new request. `consent_ids` confines the answer to records under those
    consents: a request about one consent names only the holders of data
    under it.
    """
    confined = "AND h.consent_id = ANY(%(c)s)" if consent_ids is not None else ""
    return await fetch_all(
        conn,
        f"""
        WITH h AS ({_HOLDINGS})
        SELECT h.processor_id, h.legal_name,
               coalesce(array_agg(DISTINCT h.export_uuid)
                          FILTER (WHERE h.via = 'export'), ARRAY[]::text[]) AS exports,
               coalesce(array_agg(DISTINCT h.asset_uuid)
                          FILTER (WHERE h.via = 'asset'), ARRAY[]::text[]) AS assets,
               -- The activity's uuid travels in the export column's place.
               coalesce(array_agg(DISTINCT h.export_uuid)
                          FILTER (WHERE h.via = 'activity'), ARRAY[]::text[]) AS activities
          FROM h
         WHERE h.person_id = %(u)s {confined}
           AND (h.via = 'export' OR h.disposition = 'active')
         GROUP BY h.processor_id, h.legal_name
         ORDER BY 2
        """,
        {"u": subject_user_id, "c": consent_ids},
    )


async def people_held_by(
    conn: Conn, *, processor_id: int | None = None, source_id: int | None = None
) -> list[Row]:
    """Everyone whose data a processor holds, or a data source captured, as far
    as the session's office can see: a breach is an office's, and the shared
    registry names vendors both offices use.

    A processor holds what was exported to it, and what an HR activity's
    participants consented to while its category names that processor; a
    source holds what it captured, in every asset not yet erased from it - a
    quarantined appearance is still there to be breached. Exactly one of the
    two is given.
    """
    assert (processor_id is None) != (source_id is None)
    if processor_id is not None:
        where, param = "h.via IN ('export', 'activity') AND h.processor_id = %(p)s", processor_id
    else:
        assert source_id is not None
        where = "h.via = 'asset' AND h.source_id = %(p)s AND h.disposition <> 'erased'"
        param = source_id
    return await fetch_all(
        conn,
        f"""
        WITH h AS ({_HOLDINGS})
        SELECT h.person_id,
               coalesce(array_agg(DISTINCT h.export_uuid)
                          FILTER (WHERE h.via = 'export'), ARRAY[]::text[]) AS exports,
               coalesce(array_agg(DISTINCT h.asset_uuid)
                          FILTER (WHERE h.via = 'asset'), ARRAY[]::text[]) AS assets,
               -- The activity's uuid travels in the export column's place.
               coalesce(array_agg(DISTINCT h.export_uuid)
                          FILTER (WHERE h.via = 'activity'), ARRAY[]::text[]) AS activities
          FROM h
         WHERE {where} AND cmp_office_visible(h.office_id)
         GROUP BY h.person_id
        """,
        {"p": param},
    )


async def people_in_project(
    conn: Conn, project_id: int, *, since: datetime | None, until: datetime | None
) -> list[Row]:
    """Everyone who ever gave consent in a project or activity, in the window
    if one is given. A consent later withdrawn counts: their data was held, and
    listing too many is the safe side of Rule 7. Somebody who declined every
    purpose has an artefact and gave nothing, so a person needs a grant among
    their artefacts here; the one in the window may be the withdrawal after it."""
    return await fetch_all(
        conn,
        """SELECT ca.auth_user_id AS person_id,
                  array_agg(DISTINCT ca.consent_uuid::text) AS consents
             FROM consent_artefact ca
             JOIN notice n ON n.notice_id = ca.notice_id
            WHERE n.project_id = %(p)s
              AND (%(since)s::timestamptz IS NULL OR ca.affirmative_action_at >= %(since)s)
              AND (%(until)s::timestamptz IS NULL OR ca.affirmative_action_at <= %(until)s)
              AND EXISTS (
                    SELECT 1 FROM consent_artefact held
                      JOIN notice hn ON hn.notice_id = held.notice_id
                      JOIN consent_purpose_grant g ON g.consent_id = held.consent_id
                     WHERE held.auth_user_id = ca.auth_user_id
                       AND hn.project_id = n.project_id AND g.granted)
            GROUP BY ca.auth_user_id""",
        {"p": project_id, "since": since, "until": until},
    )


async def project_of_office(conn: Conn, project_uuid: str) -> Row | None:
    """A project or activity by its uuid, if it is the session's office's."""
    return await fetch_one(
        conn,
        """SELECT p.project_id, p.project_uuid, p.project_name FROM project p
            WHERE p.project_uuid = %s AND cmp_office_visible(p.office_id)""",
        (project_uuid,),
    )


async def projects_with_people(conn: Conn) -> list[Row]:
    """The session's office's projects and activities in which somebody gave
    consent, each with how many people: what a person chooses from when a
    breach reaches one. Counted as `people_in_project` lists them."""
    return await fetch_all(
        conn,
        """SELECT p.project_uuid, p.project_name, (p.category_id IS NOT NULL) AS is_activity,
                  count(DISTINCT ca.auth_user_id)::int AS people
             FROM project p
             JOIN notice n ON n.project_id = p.project_id
             JOIN consent_artefact ca ON ca.notice_id = n.notice_id
             JOIN consent_purpose_grant g ON g.consent_id = ca.consent_id AND g.granted
            WHERE cmp_office_visible(p.office_id)
            GROUP BY p.project_id
            ORDER BY p.project_name""",
    )
