"""Unknown choices are refused with the choices named, never crashed.

Request types, outcomes, scope decisions, target states and nominated rights
arrive as plain strings, so that a refusal can be a sentence rather than a
schema error. That puts their conversion to an enum inside the service - where,
until 2026-09-05, an unknown value raised ValueError and became a 500. The
console proxy then compounded it: the API dropped the connection, and the next
call through the proxy failed with a bare 500 before it reached the API at all.
The negative probes found it; this file keeps it found.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from cmp.core.errors import Conflict, ValidationFailed
from cmp.core.permissions import Role
from cmp.domain.rights import service
from tests.integration.test_rights_flows import _portal_request

pytestmark = pytest.mark.integration

DPO = Role.DPO
KINDS = "Choose access, correction, erasure or grievance"


class TestUnknownChoices:
    async def test_on_creation(self, conn: Any, seeded: dict[str, Any]) -> None:
        with pytest.raises(ValidationFailed) as refused:
            await _portal_request(conn, seeded, "bogus")
        assert refused.value.message == KINDS
        assert refused.value.field == "request_type"

    async def test_on_classification(self, conn: Any, seeded: dict[str, Any]) -> None:
        row = await _portal_request(conn, seeded, "access")
        with pytest.raises(ValidationFailed) as refused:
            await service.classify(
                conn,
                row,
                request_type="bogus",
                note=None,
                role=DPO,
                actor_id=seeded["users"]["dpo"]["id"],
            )
        assert refused.value.message == KINDS

    async def test_on_a_transition(self, conn: Any, seeded: dict[str, Any]) -> None:
        row = await _portal_request(conn, seeded, "access")
        with pytest.raises(ValidationFailed) as refused:
            await service.transition(
                conn, row, to="bogus", reason=None, role=DPO, actor_id=seeded["users"]["dpo"]["id"]
            )
        assert refused.value.field == "to"
        assert "in_progress" in refused.value.message

    async def test_on_a_response(self, conn: Any, seeded: dict[str, Any]) -> None:
        row = await _portal_request(conn, seeded, "access")
        with pytest.raises(ValidationFailed) as refused:
            await service.respond(
                conn,
                row,
                outcome="bogus",
                response_text="Nothing to say.",
                role=DPO,
                actor_id=seeded["users"]["dpo"]["id"],
            )
        assert refused.value.field == "outcome"

    async def test_on_a_scope_decision(self, conn: Any, seeded: dict[str, Any]) -> None:
        row = await _portal_request(conn, seeded, "erasure")
        with pytest.raises(ValidationFailed) as refused:
            await service.decide_item(
                conn,
                row,
                item_uuid=str(uuid4()),
                decision="bogus",
                basis="A basis.",
                retain_until=None,
                holder_uuid=None,
                role=DPO,
                actor_id=seeded["users"]["dpo"]["id"],
            )
        assert refused.value.field == "decision"

    async def test_on_a_nomination(self, conn: Any, seeded: dict[str, Any]) -> None:
        with pytest.raises(ValidationFailed) as refused:
            await service.nominate(
                conn,
                principal_user_id=seeded["subject"]["id"],
                nominee_name="Ravi Verma",
                nominee_mobile="+915550000077",
                nominee_email="ravi@example.org",
                rights=["access", "bogus"],
            )
        assert refused.value.field == "rights"
        assert refused.value.message == KINDS


class TestVerifiedRequests:
    async def test_a_verified_request_does_not_take_a_code(
        self, conn: Any, seeded: dict[str, Any]
    ) -> None:
        # From her dashboard: the session verified her, so there is no code to
        # enter, and entering one is a mistake to name rather than a code to check.
        row = await _portal_request(conn, seeded, "access")
        assert row["verification_status"] == "verified"
        with pytest.raises(Conflict) as refused:
            await service.confirm_verification_code(
                conn, row, code="000000", role=DPO, actor_id=seeded["users"]["dpo"]["id"]
            )
        assert refused.value.code == "already_verified"
