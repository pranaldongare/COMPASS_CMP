"""A one-time code buys a data principal's session, whoever owns the mailbox.

Found on 2026-09-17, on a running stack: the data-principal portal's sign-in
sent a code to the DPO's corporate address, accepted it with no password and no
second factor, and minted a session with role `dpo`, `mfa_verified: true`, the
DPO's whole navigation, and `/audit`, `/users` and `/requests` answering 200.
The portal *displayed* "this portal is for data principals"; the API session
behind the page had every power the role has. Anyone who could read a staff
mailbox could bypass the password and the second factor that ADR 0006 requires
for every staff role.

The fix is not to refuse staff on the portal - every person the register knows
is a data principal, the DPO's own consents included - but to make the session
carry what a code is worth: a data principal's powers and no others. The
permission matrix, navigation, writes and every `Require*` gate read
`session.role`, so this file asserts that field and what follows from it.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.auth.authentication import service as auth_service
from cmp.auth.identity.principal import Principal
from cmp.core.permissions import Role, nav_for, writes_for
from cmp.db.redis import K_RATE
from cmp.db.redis import key as rkey
from cmp.tasks import dispatch as dispatch_mod

pytestmark = pytest.mark.integration

LOGIN_CODE = "cmp.notifications.send_login_code"


@pytest.fixture
def queued(monkeypatch: Any) -> list[tuple[str, tuple[Any, ...]]]:
    sent: list[tuple[str, tuple[Any, ...]]] = []

    def capture(task: Any, *args: Any, **kwargs: Any) -> str:
        sent.append((task.name, args))
        return "queued-in-a-test"

    monkeypatch.setattr(dispatch_mod, "dispatch_required", capture)
    monkeypatch.setattr(dispatch_mod, "dispatch_optional", capture)
    return sent


async def sign_in_by_code(conn: Any, redis_conn: Any, queued: Any, contact: str) -> dict[str, Any]:
    """The portal's two calls, as the browser makes them."""
    await redis_conn.delete(rkey(K_RATE, "subject_otp", contact.lower()))
    await auth_service.request_subject_otp(conn, contact=contact)
    code = next(str(args[2]) for name, args in queued if name == LOGIN_CODE)
    return await auth_service.verify_subject_otp(
        conn, contact=contact, code=code, ip_address="127.0.0.1", user_agent="test"
    )


class TestWhatACodeIsWorth:
    async def test_a_staff_mailbox_earns_a_data_principals_session(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        """The regression. The DPO's row says `dpo`; the session says otherwise."""
        result = await sign_in_by_code(conn, redis_conn, queued, "dpo@test.local")
        session = result["session"]

        assert session.role == Role.DATA_SUBJECT.value
        assert session.account_role == Role.DPO.value
        assert result["user"]["role"] == Role.DPO.value, "the row itself is untouched"

    async def test_the_principal_built_from_it_is_not_staff(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        """`Principal` is what every endpoint dependency sees, and `is_staff` is
        what `RequireStaff` amounts to."""
        result = await sign_in_by_code(conn, redis_conn, queued, "dpo@test.local")
        session = result["session"]
        principal = Principal(
            user_id=session.user_id,
            uuid=session.user_uuid,
            role=Role(session.role),
            session=session,
        )

        assert principal.is_subject
        assert not principal.is_staff
        assert principal.scope_for("audit").value == "none"
        assert principal.scope_for("user").value == "none"

    async def test_who_am_i_describes_the_session_not_the_row(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        """First paint renders from this payload. A `nav` computed from the row
        would draw the DPO's console on the data-principal portal."""
        result = await sign_in_by_code(conn, redis_conn, queued, "dpo@test.local")
        me = await auth_service.me_payload(
            conn, user_id=result["user"]["id"], session=result["session"]
        )

        assert me["role"] == Role.DATA_SUBJECT.value
        assert me["account_role"] == Role.DPO.value
        assert me["nav"] == nav_for(Role.DATA_SUBJECT.value)
        assert me["writes"] == writes_for(Role.DATA_SUBJECT.value)
        assert "audit" not in me["nav"] and "users" not in me["nav"]

    async def test_the_console_sign_in_still_carries_the_real_role(
        self,
        conn: Any,
        seeded: dict[str, Any],
        request_context: Any,
        redis_conn: Any,
        queued: Any,
    ) -> None:
        """The other door. Password and second factor buy the staff role, and
        nothing here may have narrowed that by accident."""
        from cmp.auth.rate_limit import service as ratelimit
        from cmp.core.security import hash_password
        from cmp.db.repositories import users as user_repo

        await user_repo.set_password(
            conn, seeded["users"]["dpo"]["id"], hash_password("a-real-passphrase-2026")
        )
        # The lockout counts failures per account in Redis, which outlives the
        # test transaction; a clean slate so a re-run is not a sixth attempt.
        await ratelimit.clear_login_failures("dpo@test.local")
        result = await auth_service.authenticate(
            conn,
            login="dpo@test.local",
            password="a-real-passphrase-2026",
            ip_address="127.0.0.1",
            user_agent="test",
        )

        assert result["session"].role == Role.DPO.value
        assert result["session"].account_role == Role.DPO.value
        assert result["mfa_required"] is True

    async def test_a_data_principals_own_row_reads_the_same_both_ways(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        """Nothing changes for the person the portal was built for."""
        result = await sign_in_by_code(conn, redis_conn, queued, "subject@test.local")
        assert result["session"].role == Role.DATA_SUBJECT.value
        assert result["session"].account_role == Role.DATA_SUBJECT.value
