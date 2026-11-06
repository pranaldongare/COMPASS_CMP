"""`scripts/reseal.py` walks every table in ENCRYPTED_FIELDS by its primary key.

A table added there and not here is a KeyError on the runbook's `--check`.
"""

from __future__ import annotations

import importlib.util
import pathlib
from typing import Any

from cmp.infrastructure.dkms.fields import ENCRYPTED_FIELDS


def _reseal() -> Any:
    path = pathlib.Path(__file__).parents[3] / "scripts/reseal.py"
    spec = importlib.util.spec_from_file_location("cmp_reseal_script", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_sealed_table_has_its_key() -> None:
    assert sorted(set(ENCRYPTED_FIELDS) - set(_reseal().PRIMARY_KEY)) == []


def test_every_guarded_table_it_names_is_a_sealed_table() -> None:
    assert sorted(set(_reseal().APPEND_ONLY) - set(ENCRYPTED_FIELDS)) == []
