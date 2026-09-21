"""Finding the thing an audit filter is about.

The trail records `(entity_type, entity_id)`, a table name and a surrogate
key, and nothing outside the process ever sees the key. A filter on the
console therefore arrives as a public uuid, and the first job here is to turn
it back into the id the trail indexes on. The second is the pickers: "the
consent record for Asha Rao on the gait study", typed as a few letters and
chosen from a short list, so that nobody has to know a uuid to ask what
happened to a record.

Read-only, and every query here is one the two supervising roles may run
over every row: the audit trail is theirs to read in full, so the pickers do
not scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from cmp.db.sql import Conn, fetch_all, fetch_one
from cmp.infrastructure.dkms.blind import index_of


@dataclass(frozen=True, slots=True)
class _Key:
    table: str
    id_column: str
    uuid_column: str


#: How each entity type's public uuid maps back to the id the trail stores.
#: A type absent here cannot be filtered by uuid; the console offers only the
#: ones that can.
_KEYS: Final[dict[str, _Key]] = {
    "auth_user": _Key("auth_user", "id", "uuid"),
    "purpose": _Key("purpose", "purpose_id", "purpose_uuid"),
    "processor": _Key("processor", "processor_id", "processor_uuid"),
    "data_source": _Key("data_source", "source_id", "source_uuid"),
    "project": _Key("project", "project_id", "project_uuid"),
    "project_site": _Key("project_site", "site_id", "site_uuid"),
    "project_approval": _Key("project_approval", "approval_id", "approval_uuid"),
    "notice": _Key("notice", "notice_id", "notice_uuid"),
    "consent_link": _Key("consent_link", "link_id", "link_uuid"),
    "consent_artefact": _Key("consent_artefact", "consent_id", "consent_uuid"),
    "import_batch": _Key("import_batch", "batch_id", "batch_uuid"),
    "collection": _Key("collection", "collection_id", "collection_uuid"),
    "export_log": _Key("export_log", "export_id", "export_uuid"),
    "delegation": _Key("delegation", "delegation_id", "delegation_uuid"),
    "rights_request": _Key("rights_request", "request_id", "request_uuid"),
    "nomination": _Key("nomination", "nomination_id", "nomination_uuid"),
}

FILTERABLE_BY_UUID: Final[frozenset[str]] = frozenset(_KEYS)


async def id_for_uuid(conn: Conn, entity_type: str, entity_uuid: str) -> int | None:
    """The trail's id for a public uuid, or None if the type or row is unknown."""
    key = _KEYS.get(entity_type)
    if key is None:
        return None
    # Identifiers come from the table above, never from the request.
    row = await fetch_one(
        conn,
        f"SELECT {key.id_column} AS id FROM {key.table} WHERE {key.uuid_column} = %s",
        (entity_uuid,),
    )
    return int(row["id"]) if row else None


# ------------------------------------------------------------------ pickers
#: What the console can search for by name, and how each answer is filtered:
#: a person is filtered as the subject or the actor of an event, everything
#: else as the entity an event was recorded against.
LOOKUP_KINDS: Final[dict[str, str]] = {
    "data_subject": "subject",
    "staff": "actor",
    "consent": "entity",
    "processor": "entity",
    "data_source": "entity",
    "project": "entity",
    "notice": "entity",
    "site": "entity",
    "rights_request": "entity",
}

_LOOKUPS: Final[dict[str, tuple[str, str]]] = {
    # kind -> (entity_type, sql); every sql selects uuid, label, hint and takes
    # one ILIKE pattern `p`, bound as often as needed, and the blind indexes of
    # the term read as an email `e`, a mobile `m` and a username `u`.
    #
    # A person's name and contacts are sealed in the database, so no pattern
    # can be matched against them: a person is found by the exact contact or
    # username typed, through the index, and nothing else. The label and hint
    # that come back sealed are opened by the console, like every other
    # personal value it shows - which is why a label never concatenates a
    # sealed column with a plain one: the console could open neither half.
    "data_subject": (
        "auth_user",
        """SELECT uuid::text AS uuid, full_name AS label,
                  coalesce(email, mobile, '') AS hint
           FROM auth_user
           WHERE role = 'data_subject'
             AND (email_idx = %(e)s OR secondary_email_idx = %(e)s OR mobile_idx = %(m)s
                  OR uuid::text = %(t)s)
           ORDER BY created_at DESC LIMIT %(n)s""",
    ),
    "staff": (
        "auth_user",
        """SELECT uuid::text AS uuid, full_name AS label, role::text AS hint
           FROM auth_user
           WHERE role <> 'data_subject'
             AND (email_idx = %(e)s OR username_idx = %(u)s OR uuid::text = %(t)s)
           ORDER BY created_at DESC LIMIT %(n)s""",
    ),
    "consent": (
        "consent_artefact",
        """SELECT ca.consent_uuid::text AS uuid,
                  p.project_name || ' — ' || to_char(ca.affirmative_action_at, 'DD Mon YYYY')
                    || CASE WHEN ca.is_withdrawal THEN ' (withdrawal)' ELSE '' END AS label,
                  u.full_name AS hint
           FROM consent_artefact ca
           JOIN auth_user u ON u.id = ca.auth_user_id
           JOIN notice n    ON n.notice_id = ca.notice_id
           JOIN project p   ON p.project_id = n.project_id
           WHERE p.project_name ILIKE %(p)s OR ca.consent_uuid::text ILIKE %(p)s
              OR u.email_idx = %(e)s OR u.mobile_idx = %(m)s
           ORDER BY ca.affirmative_action_at DESC LIMIT %(n)s""",
    ),
    "processor": (
        "processor",
        """SELECT processor_uuid::text AS uuid, legal_name AS label,
                  CASE WHEN is_in_house THEN 'in-house' ELSE 'third party' END AS hint
           FROM processor WHERE legal_name ILIKE %(p)s
           ORDER BY legal_name LIMIT %(n)s""",
    ),
    "data_source": (
        "data_source",
        """SELECT s.source_uuid::text AS uuid, s.name || ' (' || s.source_code || ')' AS label,
                  pr.legal_name AS hint
           FROM data_source s JOIN processor pr ON pr.processor_id = s.processor_id
           WHERE s.name ILIKE %(p)s OR s.source_code ILIKE %(p)s
           ORDER BY s.name LIMIT %(n)s""",
    ),
    "project": (
        "project",
        """SELECT project_uuid::text AS uuid, project_name AS label,
                  project_status::text AS hint
           FROM project
           WHERE project_name ILIKE %(p)s OR internal_project_name ILIKE %(p)s
           ORDER BY project_name LIMIT %(n)s""",
    ),
    "notice": (
        "notice",
        """SELECT n.notice_uuid::text AS uuid,
                  n.notice_code || ' v' || n.version AS label, p.project_name AS hint
           FROM notice n JOIN project p ON p.project_id = n.project_id
           WHERE n.notice_code ILIKE %(p)s OR p.project_name ILIKE %(p)s
           ORDER BY n.notice_code, n.version DESC LIMIT %(n)s""",
    ),
    "site": (
        "project_site",
        """SELECT s.site_uuid::text AS uuid, s.site_label AS label, p.project_name AS hint
           FROM project_site s JOIN project p ON p.project_id = s.project_id
           WHERE s.site_label ILIKE %(p)s OR p.project_name ILIKE %(p)s
           ORDER BY s.site_label LIMIT %(n)s""",
    ),
    "rights_request": (
        "rights_request",
        """SELECT r.request_uuid::text AS uuid,
                  r.reference || ' — ' || r.request_type::text AS label,
                  coalesce(s.full_name, r.submitted_name, '') AS hint
           FROM rights_request r LEFT JOIN auth_user s ON s.id = r.subject_user_id
           WHERE r.reference ILIKE %(p)s OR r.submitted_contact_idx = %(c)s
              OR s.email_idx = %(e)s OR s.mobile_idx = %(m)s
           ORDER BY r.received_at DESC LIMIT %(n)s""",
    ),
}


def like_pattern(term: str) -> str:
    """A contains-match pattern with the user's wildcards neutralised."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


async def lookup(conn: Conn, kind: str, term: str, *, limit: int = 10) -> list[dict[str, Any]]:
    """Up to `limit` things of one kind whose name contains `term`."""
    if kind not in _LOOKUPS:
        return []
    entity_type, sql = _LOOKUPS[kind]
    t = term.strip()
    params = {
        "p": like_pattern(t),
        "n": limit,
        "t": t,
        "e": index_of("email", t),
        "m": index_of("mobile", t),
        "u": index_of("username", t),
        "c": index_of("contact", t),
    }
    rows = await fetch_all(conn, sql, params)
    return [
        {
            "kind": kind,
            "entity_type": entity_type,
            "filter": LOOKUP_KINDS[kind],
            "uuid": row["uuid"],
            "label": row["label"],
            "hint": row["hint"] or None,
        }
        for row in rows
    ]
