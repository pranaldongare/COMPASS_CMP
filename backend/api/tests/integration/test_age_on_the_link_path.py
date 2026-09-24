"""A consent link's registration asks for a date of birth, like sign-up does.

`POST /c/{token}/register` created every account without one, which is why most
accounts on the register have an unknown age. The portal no longer enrols
through the link - it sends a newcomer to sign-up - but the endpoint remains,
and a path that creates an account is a path that has to ask.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from cmp.core.errors import ValidationFailed
from cmp.core.security import new_token, token_fingerprint
from cmp.db.repositories import users as user_repo
from cmp.domain.consent import service as consent_service
from tests.conftest import plain

pytestmark = pytest.mark.integration


def _years_ago(n: int) -> str:
    today = datetime.now(UTC).date()
    return (today - timedelta(days=365 * n + n // 4)).isoformat()


async def _link(conn: Any, seeded: dict[str, Any]) -> str:
    raw = new_token()
    await conn.execute(
        """INSERT INTO consent_link (notice_id, site_id, token, expires_at, created_by)
           VALUES (%s, %s, %s, now() + interval '1 day', %s)""",
        (
            seeded["notice"]["notice_id"],
            seeded["site"]["site_id"],
            token_fingerprint(raw)[:64],
            seeded["users"]["dco"]["id"],
        ),
    )
    return raw


async def _uses(conn: Any, token: str) -> int:
    row = await (
        await conn.execute(
            "SELECT use_count FROM consent_link WHERE token = %s",
            (token_fingerprint(token)[:64],),
        )
    ).fetchone()
    return int(row["use_count"])


async def test_a_new_account_through_a_link_carries_its_age(
    conn: Any, seeded: dict[str, Any]
) -> None:
    token = await _link(conn, seeded)
    result = await consent_service.register_subject(
        conn,
        token=token,
        full_name="Ravi Link",
        mobile="+915550000071",
        email=None,
        organization_id=None,
        person_type=None,
        dob=_years_ago(30),
    )

    assert result["created"] is True
    user = await user_repo.by_contact(conn, "+915550000071")
    assert user["is_minor"] is False
    row = await (
        await conn.execute("SELECT dob, minor_until FROM auth_user WHERE id = %s", (user["id"],))
    ).fetchone()
    assert row["minor_until"] is not None
    assert str(row["dob"]).startswith("SE::"), "the date itself is sealed"
    assert plain(row["dob"]) == _years_ago(30)


async def test_a_minor_through_a_link_is_refused_and_uses_nothing(
    conn: Any, seeded: dict[str, Any]
) -> None:
    token = await _link(conn, seeded)
    used = await _uses(conn, token)

    with pytest.raises(ValidationFailed) as raised:
        await consent_service.register_subject(
            conn,
            token=token,
            full_name="Child Link",
            mobile="+915550000072",
            email=None,
            organization_id=None,
            person_type=None,
            dob=_years_ago(12),
        )

    assert raised.value.code == "minor_not_permitted"
    assert "guardian" not in raised.value.message.lower()
    assert await user_repo.by_contact(conn, "+915550000072") is None
    assert await _uses(conn, token) == used, "a refused registration spends no use"


async def test_an_existing_account_is_not_rewritten_by_an_unauthenticated_caller(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """Knowing somebody's number is not being them. The date given here is not
    written to an account that already exists; she is asked once signed in."""
    token = await _link(conn, seeded)
    result = await consent_service.register_subject(
        conn,
        token=token,
        full_name="Test Subject",
        mobile="+915550000001",  # the seeded subject
        email=None,
        organization_id=None,
        person_type=None,
        dob=_years_ago(40),
    )

    assert result["created"] is False
    row = await (
        await conn.execute(
            "SELECT dob, minor_until FROM auth_user WHERE id = %s", (seeded["subject"]["id"],)
        )
    ).fetchone()
    assert row["dob"] is None
