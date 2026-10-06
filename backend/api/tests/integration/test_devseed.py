"""The seed accounts the console's sign-in page lists, with the password.

Only a listed login, only while active, and only while its password is still
the seed password (2026-10-06): a changed password, a switched-off account and
an account that was never seeded are never shown.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.config import settings
from cmp.core.security import hash_password
from cmp.infrastructure import devseed

pytestmark = pytest.mark.integration

SEED = "TestPassw0rd!123"  # what the seeded fixture gives every account


@pytest.fixture(autouse=True)
def seed_logins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "dev_seed_password", SEED)
    monkeypatch.setattr(
        settings,
        "dev_seed_logins",
        ("dpo@test.local", "dco@test.local", "rco@test.local", "nobody@test.local"),
    )


async def test_only_listed_active_accounts_still_on_the_seed_password(
    conn: Any, seeded: dict[str, Any]
) -> None:
    await conn.execute(
        "UPDATE auth_user SET password_hash = %s WHERE id = %s",
        (hash_password("Changed-Passw0rd!9"), seeded["users"]["dco"]["id"]),
    )
    await conn.execute(
        "UPDATE auth_user SET status = 'deactivated' WHERE id = %s",
        (seeded["users"]["rco"]["id"],),
    )
    found = await devseed.accounts(conn)
    assert found == [
        {"login": "dpo@test.local", "role": "dpo", "role_title": "Data Protection Officer"}
    ]
