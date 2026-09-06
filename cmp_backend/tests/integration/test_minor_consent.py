"""Section 9 at the moment of capture.

The registry records whether a purpose is permitted for minors and the account
records a date of birth, and until this test existed nothing read the two
together. The obligation was stored and never applied: a fourteen-year-old with
a date of birth on file could grant a purpose marked not permitted for minors,
and the artefact would look like any other.

Three cases, and the middle one is the point. Unknown age is not treated as
adult - but it is not treated as a child either. Most accounts were registered
through a link that never asked, and refusing every one of them would stop the
platform for a gap it can only record, not resolve.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from cmp.core.errors import ConsentDefective
from cmp.core.security import new_token, token_fingerprint
from cmp.domain.consent import service as consent_service

pytestmark = pytest.mark.integration


async def _resolvable_link(conn: Any, seeded: dict[str, Any]) -> str:
    """A live link whose raw token the service can resolve.

    The seeded link stores a literal placeholder; resolution matches on the
    keyed fingerprint of the raw token, so a test that wants to walk the flow
    mints its own.
    """
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


async def _set_dob(conn: Any, user_id: int, years_ago: int | None) -> None:
    dob = (
        None
        if years_ago is None
        else datetime.now(UTC).date().replace(year=datetime.now(UTC).year - years_ago)
    )
    await conn.execute("UPDATE auth_user SET dob = %s WHERE id = %s", (dob, user_id))


async def _capture(conn: Any, seeded: dict[str, Any], token: str) -> dict[str, Any]:
    return await consent_service.capture(
        conn,
        token=token,
        user_id=seeded["subject"]["id"],
        language_code="english",
        served_at=datetime.now(UTC) - timedelta(minutes=1),
        grants={str(seeded["purpose"]["purpose_uuid"]): True},
        action_type="checkbox_click",
        ip_address="127.0.0.1",
    )


async def test_a_child_cannot_grant_a_purpose_not_permitted_for_minors(
    conn: Any, seeded: dict[str, Any]
) -> None:
    token = await _resolvable_link(conn, seeded)
    await _set_dob(conn, seeded["subject"]["id"], years_ago=14)
    await conn.execute(
        "UPDATE purpose SET permitted_for_minors = false WHERE purpose_id = %s",
        (seeded["purpose"]["purpose_id"],),
    )

    with pytest.raises(ConsentDefective) as raised:
        await _capture(conn, seeded, token)

    assert raised.value.code == "consent_minor_not_permitted"
    assert "Test purpose" in raised.value.details["blocked"]


async def test_a_child_may_grant_a_purpose_the_registry_permits(
    conn: Any, seeded: dict[str, Any]
) -> None:
    token = await _resolvable_link(conn, seeded)
    await _set_dob(conn, seeded["subject"]["id"], years_ago=14)
    await conn.execute(
        "UPDATE purpose SET permitted_for_minors = true WHERE purpose_id = %s",
        (seeded["purpose"]["purpose_id"],),
    )

    artefact = await _capture(conn, seeded, token)
    assert artefact["consent_id"]


async def test_an_unknown_age_is_recorded_not_refused(conn: Any, seeded: dict[str, Any]) -> None:
    """ "We did not ask" is neither "adult" nor "child"."""
    token = await _resolvable_link(conn, seeded)
    await _set_dob(conn, seeded["subject"]["id"], years_ago=None)
    await conn.execute(
        "UPDATE purpose SET permitted_for_minors = false WHERE purpose_id = %s",
        (seeded["purpose"]["purpose_id"],),
    )

    artefact = await _capture(conn, seeded, token)
    assert artefact["consent_id"]


async def test_an_adult_is_unaffected(conn: Any, seeded: dict[str, Any]) -> None:
    token = await _resolvable_link(conn, seeded)
    await _set_dob(conn, seeded["subject"]["id"], years_ago=30)
    await conn.execute(
        "UPDATE purpose SET permitted_for_minors = false WHERE purpose_id = %s",
        (seeded["purpose"]["purpose_id"],),
    )

    artefact = await _capture(conn, seeded, token)
    assert artefact["consent_id"]
