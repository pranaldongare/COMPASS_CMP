"""What deactivating a member of staff does to the person.

It used to switch the row off: status `deactivated`, every session gone, and
with them the person's standing as a data principal - the consents they gave
and the rights they hold under the Act, which are theirs whether or not they
still work here. Now the staff role goes and the person stays.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.auth.authentication import service as auth_service
from cmp.core.errors import Unauthenticated, ValidationFailed
from cmp.core.permissions import Role
from cmp.core.security import hash_password
from cmp.db.redis import K_RATE
from cmp.db.redis import key as rkey
from cmp.db.repositories import users as user_repo
from cmp.db.sql import fetch_all, fetch_one
from cmp.domain.audit.service import Event
from cmp.tasks import dispatch as dispatch_mod

pytestmark = pytest.mark.integration


@pytest.fixture
def queued(monkeypatch: Any) -> list[tuple[str, tuple[Any, ...]]]:
    sent: list[tuple[str, tuple[Any, ...]]] = []

    def capture(task: Any, *args: Any, **kwargs: Any) -> str:
        sent.append((task.name, args))
        return "queued-in-a-test"

    monkeypatch.setattr(dispatch_mod, "dispatch_required", capture)
    monkeypatch.setattr(dispatch_mod, "dispatch_optional", capture)
    return sent


class TestEndingStaffAccess:
    async def test_the_role_goes_and_the_person_stays(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        dco = await user_repo.by_id(conn, seeded["users"]["dco"]["id"])
        assert dco is not None

        await auth_service.end_staff_access(
            conn, user=dco, actor_user_id=seeded["users"]["admin"]["id"]
        )

        after = await fetch_one(
            conn,
            """SELECT role::text, status::text, person_type::text, password_hash
                 FROM auth_user WHERE id = %s""",
            (dco["id"],),
        )
        assert after is not None
        assert after["role"] == Role.DATA_SUBJECT.value
        assert after["status"] == "active", "the person is not switched off"
        assert after["password_hash"] is None, "no credential the console could ever accept"
        assert after["person_type"] == "ex_employee"

    async def test_the_console_then_refuses_them_and_the_portal_still_admits_them(
        self, conn: Any, seeded: dict[str, Any], request_context: Any, redis_conn: Any, queued: Any
    ) -> None:
        dco = await user_repo.by_id(conn, seeded["users"]["dco"]["id"])
        assert dco is not None
        await user_repo.set_password(conn, dco["id"], hash_password("their-old-passphrase-2026"))
        await auth_service.end_staff_access(
            conn, user=dco, actor_user_id=seeded["users"]["admin"]["id"]
        )

        from cmp.auth.rate_limit import service as ratelimit

        await ratelimit.clear_login_failures("dco@test.local")
        with pytest.raises(Unauthenticated):
            await auth_service.authenticate(
                conn,
                login="dco@test.local",
                password="their-old-passphrase-2026",
                ip_address="127.0.0.1",
                user_agent="test",
            )

        await redis_conn.delete(rkey(K_RATE, "subject_otp", "dco@test.local"))
        await auth_service.request_subject_otp(conn, contact="dco@test.local")
        code = next(str(a[2]) for n, a in queued if n == "cmp.notifications.send_login_code")
        result = await auth_service.verify_subject_otp(
            conn, contact="dco@test.local", code=code, ip_address="127.0.0.1", user_agent="test"
        )
        assert result["session"].role == Role.DATA_SUBJECT.value
        assert result["session"].account_role == Role.DATA_SUBJECT.value

    async def test_the_trail_says_what_happened(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        dco = await user_repo.by_id(conn, seeded["users"]["dco"]["id"])
        assert dco is not None
        await auth_service.end_staff_access(
            conn, user=dco, actor_user_id=seeded["users"]["admin"]["id"]
        )

        rows = await fetch_all(
            conn,
            "SELECT event_type FROM audit_log WHERE subject_user_id = %s ORDER BY log_id",
            (dco["id"],),
        )
        events = [r["event_type"] for r in rows]
        assert Event.USER_ROLE_CHANGED in events
        assert Event.USER_STAFF_ACCESS_ENDED in events
        assert Event.USER_DEACTIVATED not in events, "nothing was deactivated"

        history = await fetch_all(
            conn,
            """SELECT from_type::text, to_type::text, changed_by
                 FROM person_type_history WHERE auth_user_id = %s""",
            (dco["id"],),
        )
        assert history and history[-1]["to_type"] == "ex_employee"
        assert history[-1]["changed_by"] == seeded["users"]["admin"]["id"]

    async def test_a_data_principal_has_no_staff_access_to_end(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        subject = await user_repo.by_id(conn, seeded["subject"]["id"])
        assert subject is not None
        with pytest.raises(ValidationFailed):
            await auth_service.end_staff_access(
                conn, user=subject, actor_user_id=seeded["users"]["admin"]["id"]
            )
