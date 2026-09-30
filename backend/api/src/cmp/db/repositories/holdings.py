"""Who holds whose data: one relation, read from both ends.

The platform knows two ways a processor comes to hold a person's data. An
export carried her consent record to the processor running its site
(`export_line`); and an asset a processor's data source captured has her in it
(`asset_consent`). `_HOLDINGS` is that relation, one row per (person, processor,
export or asset), and nothing else in the platform re-derives it.

It is read from two directions:

* **a person's holders** - a rights request asks every processor that holds her
  data (`holders_of_person`, S2 and before);
* **a holder's people** - a breach at a processor or a data source touches
  everyone whose data it holds (`people_held_by`, S3-02).

Keeping one relation is the point: a correction to how holdings are derived -
0032's move from the export's site to the line's destination is the example -
reaches both answers at once.
"""

from __future__ import annotations

from typing import Any

from cmp.db.sql import Conn, fetch_all

Row = dict[str, Any]

_HOLDINGS = """
  SELECT el.auth_user_id AS person_id, pr.processor_id, pr.legal_name,
         'export' AS via, e.export_uuid::text AS export_uuid, NULL::text AS asset_uuid,
         NULL::int AS source_id, el.consent_id, 'active' AS disposition
    FROM export_line el
    JOIN export_log e     ON e.export_id = el.export_id
    -- Where the line went: recorded on the line since 0032. Before it, only a
    -- per-site export named its site; a project export (since 0010) named none.
    LEFT JOIN project_site s ON s.site_id = e.site_id
    JOIN processor pr     ON pr.processor_id = COALESCE(el.destination_processor_id, s.processor_id)
  UNION ALL
  SELECT ca.auth_user_id, pr.processor_id, pr.legal_name,
         'asset', NULL, da.asset_uuid::text, da.source_id, ac.consent_id,
         coalesce(ac.disposition::text, 'active')
    FROM asset_consent ac
    JOIN consent_artefact ca ON ca.consent_id = ac.consent_id
    JOIN data_asset da       ON da.asset_id = ac.asset_id
    JOIN data_source ds      ON ds.source_id = da.source_id
    JOIN processor pr        ON pr.processor_id = ds.processor_id
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
                          FILTER (WHERE h.via = 'asset'), ARRAY[]::text[]) AS assets
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
    """Everyone whose data a processor was sent, or a data source captured.

    A processor holds what was exported to it; a source holds what it
    captured, in every asset not yet erased from it - a quarantined appearance
    is still there to be breached. Exactly one of the two is given.
    """
    assert (processor_id is None) != (source_id is None)
    if processor_id is not None:
        where, param = "h.via = 'export' AND h.processor_id = %(p)s", processor_id
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
                          FILTER (WHERE h.export_uuid IS NOT NULL), ARRAY[]::text[]) AS exports,
               coalesce(array_agg(DISTINCT h.asset_uuid)
                          FILTER (WHERE h.asset_uuid IS NOT NULL), ARRAY[]::text[]) AS assets
          FROM h
         WHERE {where}
         GROUP BY h.person_id
        """,
        {"p": param},
    )
