"""Every entity type the code writes is one the audit vocabulary accepts.

`audit.record()` refuses an `entity_type` outside `ENTITY_TYPES`, and it is
right to: a row that names a table the DSAR resolver does not know is a row the
data principal's own trail cannot render. The failure mode is that the refusal
happens at runtime, on the request that first exercises the path - which is how
granting cover raised a `ValueError` for months while every test passed, because
the only test that touched delegations inserted its rows with raw SQL.

So this reads the source. Every literal `entity_type="..."` in the package has
to be in the vocabulary, and every table in the vocabulary has to be a table the
resolver can label or a table nothing links to on purpose.
"""

from __future__ import annotations

import ast
import pathlib

import cmp
from cmp.domain.audit.service import ENTITY_TYPES

SRC = pathlib.Path(cmp.__file__).parent


def _entity_type_literals() -> dict[str, list[str]]:
    """Every `entity_type="..."` keyword argument in the package, by file."""
    found: dict[str, list[str]] = {}
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for keyword in node.keywords:
                if keyword.arg == "entity_type" and isinstance(keyword.value, ast.Constant):
                    value = keyword.value.value
                    if isinstance(value, str):
                        found.setdefault(str(path.relative_to(SRC)), []).append(value)
    return found


def test_every_recorded_entity_type_is_in_the_vocabulary() -> None:
    unknown = [
        f"{file}: {value!r}"
        for file, values in _entity_type_literals().items()
        for value in values
        if value not in ENTITY_TYPES
    ]
    assert not unknown, (
        "audit.record() would raise for these entity types at runtime: " + ", ".join(unknown)
    )


def test_the_vocabulary_is_made_of_table_names() -> None:
    """A vocabulary entry is a table name, never a concept.

    The resolver joins on it, so `"cover"` where the table is `delegation` would
    parse, pass the membership check, and resolve to nothing forever.
    """
    for name in ENTITY_TYPES:
        assert name == name.lower() and " " not in name and "." not in name, name
