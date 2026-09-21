"""What the trail can be filtered by, in words.

The console used to carry its own list of entity types - twenty-two table
names, typed by hand, and eight tables behind the truth by the time anyone
looked. This is the one place the vocabulary is spelled out: every entity
type the trail may name, with the noun a person reads; every event type,
grouped by the thing it concerns, with a label. The API serves it and the
console renders it, so a new event or table appears in the filters on the
day the code lands.
"""

from __future__ import annotations

from typing import Any, Final

from cmp.db.repositories.audit_lookup import FILTERABLE_BY_UUID, LOOKUP_KINDS
from cmp.db.repositories.entities import nouns
from cmp.domain.audit.service import ENTITY_TYPES, Event

#: The prefix of an event type, and what it concerns. A prefix not listed
#: here is still served, under its own name, so nothing is hidden.
GROUP_LABELS: Final[dict[str, str]] = {
    "auth": "Sign-in and access",
    "user": "Accounts",
    "purpose": "Purposes",
    "processor": "Processors",
    "source": "Data sources",
    "registry": "Registry",
    "project": "Projects",
    "approval": "Approvals",
    "site": "Collection sites",
    "link": "Consent links",
    "subject": "Data principals",
    "notice": "Notices",
    "consent": "Consent",
    "export": "Exports",
    "import": "Imports",
    "asset": "Assets",
    "delegation": "Delegation",
    "rights": "Rights requests",
    "nomination": "Nominations",
    "message_template": "Messages",
    "audit": "Audit trail",
}

#: Which pickers the console offers, and the plain name of each.
LOOKUP_LABELS: Final[dict[str, str]] = {
    "data_subject": "Data principal",
    "staff": "Member of staff",
    "consent": "Consent record",
    "processor": "Processor",
    "data_source": "Data source",
    "project": "Project",
    "notice": "Notice",
    "site": "Collection site",
    "rights_request": "Rights request",
}


def _label(part: str) -> str:
    return part.replace("_", " ").capitalize()


def event_types() -> list[dict[str, str]]:
    out = []
    for name, value in vars(Event).items():
        if name.startswith("_") or not isinstance(value, str) or "." not in value:
            continue
        group, _, rest = value.partition(".")
        out.append(
            {
                "value": value,
                "group": group,
                "group_label": GROUP_LABELS.get(group, _label(group)),
                "label": _label(rest),
            }
        )
    return sorted(out, key=lambda e: (e["group_label"], e["label"]))


def vocabulary() -> dict[str, Any]:
    events = event_types()
    groups_seen = {e["group"]: e["group_label"] for e in events}
    noun_of = nouns()
    return {
        "entity_types": sorted(
            (
                {
                    "value": t,
                    "label": noun_of.get(t) or _label(t),
                    "filterable_by_uuid": t in FILTERABLE_BY_UUID,
                }
                for t in ENTITY_TYPES
            ),
            key=lambda e: e["label"],
        ),
        "event_groups": sorted(
            ({"value": g, "label": label} for g, label in groups_seen.items()),
            key=lambda g: g["label"],
        ),
        "event_types": events,
        "lookups": [
            {"kind": kind, "label": LOOKUP_LABELS.get(kind, _label(kind)), "filter": filt}
            for kind, filt in LOOKUP_KINDS.items()
        ],
    }
