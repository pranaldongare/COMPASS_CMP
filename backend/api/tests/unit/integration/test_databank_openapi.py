"""The draft specification covers the six calls, each on its own side, and the
copy in docs/ is the one the models produce."""

from __future__ import annotations

import json
from pathlib import Path

from cmp.integration.databank.openapi import build

DOC = Path(__file__).resolve().parents[5] / "docs" / "integration" / "databank" / "openapi.json"


def test_six_calls_three_each_side() -> None:
    spec = build()
    calls = [
        (m.upper(), p, o["tags"][0]) for p, ops in spec["paths"].items() for m, o in ops.items()
    ]
    assert calls == [
        ("POST", "/integration/v1/asset-events", "hosted by CMP"),
        ("GET", "/integration/v1/consents/{consent_id}", "hosted by CMP"),
        ("GET", "/integration/v1/persons/{person_id}/assets", "hosted by Databank"),
        ("POST", "/integration/v1/consent-events", "hosted by Databank"),
        ("POST", "/integration/v1/instructions", "hosted by Databank"),
        ("POST", "/integration/v1/instructions/{instruction_id}/results", "hosted by CMP"),
    ]


def test_the_published_copy_is_current() -> None:
    """Regenerate with: python -m cmp.integration.databank.openapi > docs/.../openapi.json"""
    assert json.loads(DOC.read_text()) == build()
