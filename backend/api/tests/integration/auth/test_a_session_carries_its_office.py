"""The office a session reads in, from the account to the pool (ADR 0032).

A staff sign-in takes the office on the account; a data principal's session,
the administrator's and a breach-only login's take none and read across both.
A session minted before offices existed has no office field at all, and would
read as "none" - across both - so it is ended rather than trusted. And the
administrator's register holds each role to its office: a role that works in
one needs one, any other is refused one.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.auth.authentication import service as auth_service
from cmp.auth.sessions import service as sessions
from cmp.core.errors import ValidationFailed
from cmp.core.permissions import Role
from cmp.db.redis import get_redis
from cmp.db.repositories import offices as office_repo
from cmp.domain.users import service as users

pytestmark = pytest.mark.integration


async def _office_uuid(conn: Any, code: str) -> str:
    office = await office_repo.by_code(conn, code)
    assert office is not None
    return str(office["office_uuid"])


class TestTheSession:
    async def test_a_staff_session_holds_the_account_office(
        self, conn: Any, seeded: dict[str, Any], redis_conn: Any
    ) -> None:
        dpo = seeded["users"]["dpo"]
        raw, session = await sessions.create(
            user_id=dpo["id"],
            user_uuid=str(dpo["uuid"]),
            role=Role.DPO.value,
            ip_address="127.0.0.1",
            user_agent="test",
            mfa_verified=True,
            office="rnd",
        )
        try:
            loaded = await sessions.load(raw)
            assert loaded is not None and loaded.office == "rnd"
            me = await auth_service.me_payload(conn, user_id=dpo["id"], session=session)
            assert me["office"] == "rnd"
        finally:
            await sessions.destroy(raw)

    async def test_a_principal_session_holds_no_office(
        self, conn: Any, seeded: dict[str, Any], redis_conn: Any
    ) -> None:
        """Her records are hers on both tracks, bounded by the account."""
        raw, session = await auth_service.open_principal_session(
            user={
                "id": seeded["subject"]["id"],
                "uuid": seeded["subject"]["uuid"],
                "role": "data_subject",
            },
            ip_address="127.0.0.1",
            user_agent="test",
        )
        try:
            assert session.office is None
            loaded = await sessions.load(raw)
            assert loaded is not None and loaded.office is None
        finally:
            await sessions.destroy(raw)

    async def test_a_session_from_before_the_offices_is_ended(
        self, seeded: dict[str, Any], redis_conn: Any
    ) -> None:
        """Read as "no office" it would act across both: a DPO's old session
        would read the Legal office's registers."""
        dpo = seeded["users"]["dpo"]
        raw, _ = await sessions.create(
            user_id=dpo["id"],
            user_uuid=str(dpo["uuid"]),
            role=Role.DPO.value,
            ip_address="127.0.0.1",
            user_agent="test",
            mfa_verified=True,
            office="rnd",
        )
        from cmp.core.security import token_fingerprint

        await get_redis().hdel(sessions._skey(token_fingerprint(raw)), "office")
        assert await sessions.load(raw) is None
        assert not await get_redis().exists(sessions._skey(token_fingerprint(raw)))

    async def test_password_sign_in_carries_the_office(
        self, conn: Any, seeded: dict[str, Any], redis_conn: Any, monkeypatch: Any
    ) -> None:
        from cmp.tasks import dispatch as dispatch_mod

        monkeypatch.setattr(dispatch_mod, "dispatch_required", lambda *a, **k: "not-sent")
        result = await auth_service.authenticate(
            conn,
            login="dpo@test.local",
            password="TestPassw0rd!123",
            ip_address="127.0.0.1",
            user_agent="test",
        )
        try:
            assert result["session"].office == "rnd"
        finally:
            await sessions.destroy(result["token"])


class TestTheRegisterHoldsEachRoleToItsOffice:
    async def test_a_role_that_works_in_an_office_needs_one(
        self, conn: Any, request_context: Any, monkeypatch: Any
    ) -> None:
        with pytest.raises(ValidationFailed) as refused:
            await users.create_staff(
                conn,
                full_name="No Office",
                email="no.office@test.local",
                role=Role.DCO.value,
                username=None,
                mobile=None,
                organization_id=None,
                person_type="employee",
                source_uuids=[],
            )
        assert refused.value.field == "office_uuid"

    async def test_the_administrator_is_refused_one(self, conn: Any, request_context: Any) -> None:
        with pytest.raises(ValidationFailed) as refused:
            await users.create_staff(
                conn,
                full_name="Admin With Office",
                email="admin.office@test.local",
                role=Role.ADMIN.value,
                username=None,
                mobile=None,
                organization_id=None,
                person_type="employee",
                source_uuids=[],
                office_uuid=await _office_uuid(conn, "rnd"),
            )
        assert refused.value.field == "office_uuid"

    async def test_a_legal_poc_works_in_the_office_named(
        self, conn: Any, request_context: Any, sent: Any
    ) -> None:
        user, _ = await users.create_staff(
            conn,
            full_name="Legal PoC",
            email="legal.poc@test.local",
            role=Role.LEGAL.value,
            username=None,
            mobile=None,
            organization_id=None,
            person_type="employee",
            source_uuids=[],
            office_uuid=await _office_uuid(conn, "hr"),
        )
        assert user["office_code"] == "hr"

    async def test_a_role_change_keeps_the_office_or_clears_it(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, sent: Any
    ) -> None:
        dco = seeded["users"]["dco"]
        admin = seeded["users"]["admin"]["id"]
        await users.change_role(
            conn, str(dco["uuid"]), role=Role.RCO.value, reason=None, actor_id=admin
        )
        moved = await users.repo.require_by_uuid(conn, str(dco["uuid"]))
        assert moved["office_code"] == "rnd", "a role in the same office keeps it"

        await users.change_role(
            conn, str(dco["uuid"]), role=Role.ADMIN.value, reason=None, actor_id=admin
        )
        cleared = await users.repo.require_by_uuid(conn, str(dco["uuid"]))
        assert cleared["office_code"] is None, "a role across both offices holds none"

        with pytest.raises(ValidationFailed) as refused:
            await users.change_role(
                conn, str(dco["uuid"]), role=Role.DPO.value, reason=None, actor_id=admin
            )
        assert refused.value.field == "office_uuid", "and coming back needs one named"
