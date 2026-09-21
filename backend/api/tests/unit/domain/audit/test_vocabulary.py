"""The filter vocabulary the console renders is the code's, complete."""

from __future__ import annotations

from cmp.db.repositories.audit_lookup import LOOKUP_KINDS
from cmp.domain.audit.service import ENTITY_TYPES, Event
from cmp.domain.audit.vocabulary import GROUP_LABELS, event_types, vocabulary


def _event_values() -> set[str]:
    return {v for k, v in vars(Event).items() if not k.startswith("_") and isinstance(v, str)}


def test_every_event_type_is_served_with_a_group_and_a_label() -> None:
    served = {e["value"] for e in event_types()}
    assert served == _event_values()
    for e in event_types():
        assert e["group"] == e["value"].split(".")[0]
        assert e["label"] and e["group_label"]


def test_every_group_the_code_uses_has_a_readable_name() -> None:
    groups = {v.split(".")[0] for v in _event_values()}
    unnamed = sorted(g for g in groups if g not in GROUP_LABELS)
    assert not unnamed, f"give these event groups a label in GROUP_LABELS: {unnamed}"


def test_every_entity_type_is_served_with_a_noun() -> None:
    v = vocabulary()
    assert {e["value"] for e in v["entity_types"]} == set(ENTITY_TYPES)
    for e in v["entity_types"]:
        # A readable noun, never the bare table name.
        assert e["label"]
        assert e["label"] != e["value"]


def test_the_pickers_are_the_lookup_kinds() -> None:
    v = vocabulary()
    assert {p["kind"] for p in v["lookups"]} == set(LOOKUP_KINDS)
    assert {p["filter"] for p in v["lookups"]} <= {"subject", "actor", "entity"}
