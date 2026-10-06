"""Which development accounts still sign in with the seed password.

The console's sign-in page lists them, with the password, so a developer need
not ask for it (2026-10-06). Only the logins named in `DEV_SEED_LOGINS` are
looked at - the seed's own - each checked against the password it has *now*:
one whose password was changed, one that is not active, and any account that
was never seeded (a breach-only login, a test's leftovers) is never listed.

The same switch as the one-time-code popup, `DEV_SHOW_CODES`, which the
settings refuse outside local and test; without it the route does not exist.
"""

from __future__ import annotations

from typing import Any

from cmp.core.config import settings
from cmp.core.enums import UserStatus
from cmp.core.permissions import ROLE_TITLES, Role
from cmp.core.security import verify_password
from cmp.db.repositories import users as user_repo
from cmp.db.sql import Conn


async def accounts(conn: Conn) -> list[dict[str, Any]]:
    """The seed logins whose current password is still the seed password."""
    out: list[dict[str, Any]] = []
    for login in settings.dev_seed_logins:
        row = await user_repo.credentials_by_login(conn, login)
        if (
            row is None
            or str(row["status"]) != UserStatus.ACTIVE.value
            or str(row["role"]) == Role.DATA_SUBJECT.value
            or not row["password_hash"]
            or not verify_password(settings.dev_seed_password, row["password_hash"])
        ):
            continue
        role = str(row["role"])
        out.append({"login": login, "role": role, "role_title": ROLE_TITLES.get(role, role)})
    return out
