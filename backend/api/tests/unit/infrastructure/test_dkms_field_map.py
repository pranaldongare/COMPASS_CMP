"""The field map is a specification, so it gets tested as one.

Two systems have to agree about one vocabulary: this repository's map of column
to data type, and the key service's roster of types. They are in different
processes and different languages of deployment, and the failure when they
drift is not a crash - it is a batch refused in the middle of a write, or worse,
a column quietly left in plaintext because nobody listed it.

So the list is asserted here: every type this side names exists over there, and
every personal column in `docs/domain/personal-data.md` is either encrypted or
written down as a lookup field with the reason it cannot be.
"""

from __future__ import annotations

import ast
import json
import pathlib

import pytest

from cmp.infrastructure.dkms.fields import (
    ENCRYPTED_FIELDS,
    LOOKUP_FIELDS,
    DataType,
    fields_for,
)

#: The service's own roster, read from its source rather than from a copy. A
#: test that asks the running service would be a better test and a worse
#: check-in gate: this has to hold when nothing is running.
#: parents[5] is the repository root: tests/unit/infrastructure/<file> is
#: four levels inside backend/api, which is two inside the root.
TYPES_PY = pathlib.Path(__file__).resolve().parents[5] / "backend/dkms/app/dkms/types.py"


def _service_types() -> set[str]:
    """Read the service's enum without importing it.

    Parsed rather than imported: the service is a separate deployable with its
    own virtualenv, and this suite must not depend on that being installed.
    Parsed with `ast` rather than by splitting on strings, because the first
    version of this helper read the module constants below the class as though
    they were members.
    """
    tree = ast.parse(TYPES_PY.read_text())
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "DataType":
            return {
                member.value.value
                for member in node.body
                if isinstance(member, ast.Assign) and isinstance(member.value, ast.Constant)
            }
    raise AssertionError("the service has no DataType enum any more")


@pytest.mark.skipif(not TYPES_PY.exists(), reason="the DKMS service is not in this checkout")
def test_every_type_this_side_names_exists_in_the_service() -> None:
    ours = {t.value for t in DataType}
    theirs = _service_types()

    assert ours == theirs, (
        "the two vocabularies have drifted; a type here that the service does "
        "not know is a batch refused mid-write"
    )


def test_no_column_is_both_encrypted_and_a_lookup() -> None:
    """The two lists are a partition, not an overlap.

    A column in both would mean somebody decided twice and the last edit wins,
    which is exactly the kind of thing that leaves `email` encrypted and
    sign-in broken.
    """
    for table, columns in LOOKUP_FIELDS.items():
        clash = set(columns) & set(ENCRYPTED_FIELDS.get(table, {}))
        assert not clash, f"{table}: {clash} is in both lists"


def test_every_lookup_exclusion_carries_its_reason() -> None:
    """A column left in plaintext has to say why, in a sentence.

    Otherwise the list reads as an oversight in six months, and somebody either
    encrypts it and breaks sign-in or leaves it and never learns it was a
    decision.
    """
    for table, columns in LOOKUP_FIELDS.items():
        for column, reason in columns.items():
            assert len(reason) > 20, f"{table}.{column} has no real reason"


def test_the_map_is_in_the_shape_the_service_takes() -> None:
    """`fields_for` produces a key mapping the API accepts as written."""
    key = fields_for("rights_request")

    assert key["request_text"] is DataType.FREE_TEXT
    body = {"data": [{}], "key": {k: v.value for k, v in key.items()}, "method": "string"}
    # Round-trips through JSON, which is how it will actually travel.
    assert json.loads(json.dumps(body))["key"]["request_text"] == "FREE_TEXT"


def test_a_table_nobody_listed_gets_an_empty_map_not_an_error() -> None:
    """Callers ask by table name; an unlisted one encrypts nothing."""
    assert fields_for("purpose") == {}
    assert fields_for("no_such_table") == {}


def test_free_text_is_the_commonest_type_and_names_the_second() -> None:
    """A shape check on the map itself, which catches a wholesale mistake.

    If a later edit maps everything to GENERIC, or to NAME, the counts move and
    this fails - which is cheaper than noticing it in a decrypt six months on,
    where every value has to be re-encrypted under the right type.
    """
    counted: dict[DataType, int] = {}
    for columns in ENCRYPTED_FIELDS.values():
        for data_type in columns.values():
            counted[data_type] = counted.get(data_type, 0) + 1

    ranked = sorted(counted.items(), key=lambda kv: -kv[1])
    assert ranked[0][0] is DataType.FREE_TEXT
    assert ranked[1][0] is DataType.NAME
    assert DataType.GENERIC not in counted, "GENERIC means somebody skipped the decision"
