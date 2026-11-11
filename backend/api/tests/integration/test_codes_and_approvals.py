"""Codes the platform gives, and approvals dated as given (2026-11-11).

A purpose and a data source used to need a code their creator invented, unique
across offices they cannot see; the platform now numbers them, `PUR-0001` and
`SRC-0001` (0068), and a code of that shape cannot be chosen by hand, or the
sequence would issue it twice. An approval is a thing that happened: Knox is one
of its types, and none can be dated in the future.
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from cmp.api.routers.v1.registry import PurposeIn, SourceIn, _purpose_fields
from cmp.core.errors import ValidationFailed
from cmp.db.sql import fetch_one
from cmp.domain.projects import service as project_service
from cmp.domain.registry import service as registry
from cmp.validation.common import latest_today

pytestmark = pytest.mark.integration

PURPOSE: dict[str, Any] = {
    "name": "Gait model training",
    "description": "Training the gait model.",
    "uses": "Model training.",
    "lawful_basis": "consent_s6",
    "data_categories": ["name"],
    "retention_days": 365,
    "retention_basis": "business_policy",
    "erasure_trigger": "withdrawal",
}


def _number(code: str, prefix: str) -> int:
    match = re.fullmatch(rf"{prefix}-(\d{{4,}})", code)
    assert match, code
    return int(match.group(1))


class TestPurposeCodes:
    async def test_a_purpose_with_no_code_is_numbered_in_turn(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        dpo = int(seeded["users"]["dpo"]["id"])
        first = await registry.create_purpose(
            conn, fields=_purpose_fields(PurposeIn(**PURPOSE)), actor_id=dpo
        )
        second = await registry.create_purpose(
            conn, fields=_purpose_fields(PurposeIn(**PURPOSE)), actor_id=dpo
        )
        assert _number(second["purpose_code"], "PUR") == _number(first["purpose_code"], "PUR") + 1

    async def test_a_code_sent_by_hand_is_still_kept(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        made = await registry.create_purpose(
            conn,
            fields=_purpose_fields(PurposeIn(**PURPOSE, purpose_code="PUR-GAIT-HAND")),
            actor_id=int(seeded["users"]["dpo"]["id"]),
        )
        assert made["purpose_code"] == "PUR-GAIT-HAND"

    @pytest.mark.parametrize("code", ["PUR-0001", "pur-12", "PUR-000123"])
    def test_the_numbered_shape_cannot_be_chosen(self, code: str) -> None:
        with pytest.raises(ValidationError, match="given by the platform"):
            PurposeIn(**PURPOSE, purpose_code=code)


class TestSourceCodes:
    async def test_a_source_with_no_code_is_numbered(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        made = await registry.create_source(
            conn,
            role="dpo",
            user_id=int(seeded["users"]["dpo"]["id"]),
            source_code=None,
            name="Gait rig, Pune",
            source_role="collection",
            exchange_mode="file_import",
            id_scheme=None,
            processor_uuid=str(seeded["processors"]["external"]["processor_uuid"]),
            site_uuid=None,
            is_authoritative_for=[],
        )
        _number(made["source_code"], "SRC")

    def test_the_numbered_shape_cannot_be_chosen(self) -> None:
        with pytest.raises(ValidationError, match="given by the platform"):
            SourceIn(
                source_code="SRC-0042",
                name="x",
                source_role="collection",
                exchange_mode="file_import",
            )


async def _draft_project(conn: Any, seeded: dict[str, Any]) -> str:
    row = await fetch_one(
        conn,
        """INSERT INTO project (project_name, description, created_by, dco_user_id,
                                project_status, office_id)
           VALUES ('Approval test', 'd', %s, %s, 'in_draft',
                   (SELECT office_id FROM office WHERE office_code = 'rnd'))
           RETURNING project_uuid""",
        (seeded["users"]["rnd_user"]["id"], seeded["users"]["dco"]["id"]),
    )
    assert row is not None
    return str(row["project_uuid"])


async def _approve(conn: Any, seeded: dict[str, Any], project: str, **over: Any) -> Any:
    return await project_service.add_approval(
        conn,
        project_uuid=project,
        actor_id=int(seeded["users"]["rnd_user"]["id"]),
        role="rnd_user",
        **{
            "approval_type": "security",
            "reference_no": "SEC-1",
            "approved_on": latest_today(),
            "proof_file_ref": "approvals/x.pdf",
            "proof_file_hash": "a" * 64,
            **over,
        },
    )


class TestApprovals:
    async def test_knox_is_an_approval_type(self, conn: Any, seeded: dict[str, Any]) -> None:
        project = await _draft_project(conn, seeded)
        made = await _approve(conn, seeded, project, approval_type="knox", reference_no="KNOX-7")
        assert made["approval_type"] == "knox"

    async def test_an_approval_cannot_be_dated_in_the_future(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        project = await _draft_project(conn, seeded)
        with pytest.raises(ValidationFailed, match="cannot be in the future"):
            await _approve(conn, seeded, project, approved_on=latest_today() + timedelta(days=1))
        # Today, wherever the person is, stands.
        await _approve(conn, seeded, project)
