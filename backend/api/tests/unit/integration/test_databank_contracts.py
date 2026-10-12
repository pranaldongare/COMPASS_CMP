"""The contracts accept the brief's own examples, and refuse an event that
does not carry what its type needs."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from cmp.integration.databank.contracts import (
    AssetEvent,
    Delivery,
    Instruction,
    InstructionResult,
    Verdict,
    strictest,
)

BRIEF_DELIVERY = {
    "schema_version": "1.0",
    "project_id": "5d0c2c1e-8a41-4f1b-b6a0-3e9d7c2a1f54",
    "site_id": "a8f3e6b2-1c7d-4e59-9b02-6d4f8a1c3e70",
    "batch_ref": "RUN-2026-001",
    "declared_asset_count": 2,
    "assets": [
        {
            "asset_id": "AST-000184213",
            "asset_type": "image",
            "captured_at": "2026-10-05T10:42:17+05:30",
            "subjects": [
                {
                    "person_id": "1f6b9d3a-52c8-4a7e-8f10-c2e4b7a9d613",
                    "consent_id": "c41e7a90-6b2f-4d83-a5c1-0e9f3b7d2a68",
                }
            ],
            "other_persons": "none",
        },
        {
            "asset_id": "AST-000184377",
            "asset_type": "video",
            "captured_at": "2026-10-05T11:05:00+05:30",
            "subjects": [
                {
                    "person_id": "1f6b9d3a-52c8-4a7e-8f10-c2e4b7a9d613",
                    "consent_id": "c41e7a90-6b2f-4d83-a5c1-0e9f3b7d2a68",
                },
                {
                    "person_id": "7a2d4c81-e3f5-4b96-8d07-5c1a9e6f4b32",
                    "consent_id": "e95b1f04-2a6c-4c7d-b3e8-8f0d2a5c7e19",
                },
            ],
            "other_persons": "incidental",
        },
    ],
}

BRIEF_INSTRUCTION = {
    "instruction_id": "9e2a6c48-0f3b-4d75-a1c9-7b5e8d2f4a06",
    "reason": "rights_request",
    "reference": "RR-2026-000042",
    "person_id": "1f6b9d3a-52c8-4a7e-8f10-c2e4b7a9d613",
    "issued_at": "2026-10-07T11:00:00+05:30",
    "due_at": "2026-10-14T18:00:00+05:30",
    "items": [
        {"asset_id": "AST-000184213", "action": "erase"},
        {"asset_id": "AST-000184377", "action": "redact"},
    ],
}

BRIEF_RESULT = {
    "instruction_id": "9e2a6c48-0f3b-4d75-a1c9-7b5e8d2f4a06",
    "items": [
        {
            "asset_id": "AST-000184213",
            "action": "erase",
            "outcome": "done",
            "completed_at": "2026-10-09T16:20:00+05:30",
            "evidence": {
                "content_sha256": "9f2c41d7...e41b",
                "derivatives_deleted": 2,
                "backups_expire_on": "2026-11-08",
            },
        },
        {
            "asset_id": "AST-000184377",
            "action": "redact",
            "outcome": "failed",
            "reason": "redaction_not_supported",
        },
    ],
}


def test_the_briefs_examples_are_valid() -> None:
    delivery = Delivery.model_validate(BRIEF_DELIVERY)
    assert len(delivery.assets) == 2
    assert delivery.assets[1].other_persons == "incidental"
    assert len(Instruction.model_validate(BRIEF_INSTRUCTION).items) == 2
    assert InstructionResult.model_validate(BRIEF_RESULT).items[1].outcome == "failed"


def test_a_field_added_within_the_version_is_ignored() -> None:
    """Within a version a change only adds fields: the other side may be ahead."""
    delivery = Delivery.model_validate({**BRIEF_DELIVERY, "lab_note": "new in 1.1"})
    assert not hasattr(delivery, "lab_note")


def test_capture_time_needs_its_offset() -> None:
    naive = {**BRIEF_DELIVERY["assets"][0], "captured_at": "2026-10-05T10:42:17"}  # type: ignore[dict-item]
    with pytest.raises(ValidationError):
        Delivery.model_validate({**BRIEF_DELIVERY, "assets": [naive]})


def test_an_asset_names_at_least_one_subject() -> None:
    empty = {**BRIEF_DELIVERY["assets"][0], "subjects": []}  # type: ignore[dict-item]
    with pytest.raises(ValidationError):
        Delivery.model_validate({**BRIEF_DELIVERY, "assets": [empty]})


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"type": "registered"}, "full asset record"),
        ({"type": "deleted", "asset_id": "AST-1"}, "reason"),
        ({"type": "released", "asset_id": "AST-1"}, "recipient"),
        ({"type": "deleted", "reason": "quality"}, "asset_id"),
    ],
)
def test_an_event_carries_what_its_type_needs(body: dict[str, str], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        AssetEvent.model_validate(
            {
                "event_id": "3b8e5f27-9c14-4a60-8e2d-f1a7c3b5d908",
                "occurred_at": "2026-10-05T12:10:03+05:30",
                **body,
            }
        )


def test_the_asset_takes_the_strictest_verdict() -> None:
    assert strictest([Verdict.VALID, Verdict.RESTRICTED]) == Verdict.RESTRICTED
    assert strictest([Verdict.VALID, Verdict.UNKNOWN, Verdict.RESTRICTED]) == Verdict.UNKNOWN
    assert strictest([Verdict.UNKNOWN, Verdict.INVALID]) == Verdict.INVALID
    assert strictest([Verdict.VALID]) == Verdict.VALID
