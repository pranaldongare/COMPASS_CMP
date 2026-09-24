"""Section 9 at the moment of capture.

The registry records whether a purpose is permitted for minors and the account
records a date of birth. Until the guardian route exists (deferred, D-01 to
D-03) the platform has no lawful way to take a child's consent at all: s.9(1)
asks for a parent's or guardian's verifiable consent for *any* processing of a
child's data, and `permitted_for_minors` carries s.9(3) on top of that - it
never stood in for the guardian. So a child is refused whatever the purpose.

And an unknown age is not an adult. `cmp_is_minor()` answers NULL when it does
not know, and says callers must not treat that as adult; the gate used to test
`is True`, which let every account that was never asked straight through. It
is refused now until a date of birth is given - the portal asks at the next
sign-in, and on the consent page when it has to. Withdrawal is not a consent
and stays open to everybody.
"""

from __future__ import annotations

from datetime import UTC, datetime
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
    # The date itself is sealed and the s.9 test reads minor_until, so a fixture
    # that writes the date directly writes the date the test reads as well.
    await conn.execute(
        "UPDATE auth_user SET dob = %s, minor_until = %s::date + INTERVAL '18 years' WHERE id = %s",
        (dob.isoformat() if dob else None, dob, user_id),
    )


async def _capture(conn: Any, seeded: dict[str, Any], token: str) -> dict[str, Any]:
    # The notice must have been served to her, by the server, before a
    # decision can be recorded against it.
    await consent_service.serve_notice(
        conn, token=token, language_code="english", user_id=seeded["subject"]["id"]
    )
    return await consent_service.capture(
        conn,
        token=token,
        user_id=seeded["subject"]["id"],
        language_code="english",
        grants={str(seeded["purpose"]["purpose_uuid"]): True},
        action_type="checkbox_click",
        ip_address="127.0.0.1",
    )


async def _permit_minors(conn: Any, seeded: dict[str, Any], permitted: bool) -> None:
    await conn.execute(
        "UPDATE purpose SET permitted_for_minors = %s WHERE purpose_id = %s",
        (permitted, seeded["purpose"]["purpose_id"]),
    )


async def test_a_child_cannot_grant_a_purpose_not_permitted_for_minors(
    conn: Any, seeded: dict[str, Any]
) -> None:
    token = await _resolvable_link(conn, seeded)
    await _set_dob(conn, seeded["subject"]["id"], years_ago=14)
    await _permit_minors(conn, seeded, False)

    with pytest.raises(ConsentDefective) as raised:
        await _capture(conn, seeded, token)

    assert raised.value.code == "consent_minor_not_permitted"


async def test_a_child_is_refused_even_a_purpose_the_registry_permits(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """`permitted_for_minors` is s.9(3), and says nothing about s.9(1)."""
    token = await _resolvable_link(conn, seeded)
    await _set_dob(conn, seeded["subject"]["id"], years_ago=14)
    await _permit_minors(conn, seeded, True)

    with pytest.raises(ConsentDefective) as raised:
        await _capture(conn, seeded, token)

    assert raised.value.code == "consent_minor_not_permitted"


async def test_the_refusal_does_not_promise_a_guardian_route(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """There is no guardian route yet, so the message may not advertise one."""
    token = await _resolvable_link(conn, seeded)
    await _set_dob(conn, seeded["subject"]["id"], years_ago=14)

    with pytest.raises(ConsentDefective) as raised:
        await _capture(conn, seeded, token)

    said = raised.value.message.lower()
    assert "guardian" not in said
    assert "parent" not in said


async def test_an_unknown_age_is_refused_until_a_date_of_birth_is_given(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """ "We did not ask" is not "adult"."""
    token = await _resolvable_link(conn, seeded)
    await _set_dob(conn, seeded["subject"]["id"], years_ago=None)
    await _permit_minors(conn, seeded, True)

    with pytest.raises(ConsentDefective) as raised:
        await _capture(conn, seeded, token)

    assert raised.value.code == "age_required"
    count = await (
        await conn.execute(
            "SELECT count(*) AS n FROM consent_artefact WHERE auth_user_id = %s",
            (seeded["subject"]["id"],),
        )
    ).fetchone()
    assert count["n"] == 0, "nothing is recorded for a refused capture"


async def test_an_unknown_age_cannot_record_a_refusal_either(
    conn: Any, seeded: dict[str, Any]
) -> None:
    """A capture that grants nothing is still a new artefact about a person."""
    token = await _resolvable_link(conn, seeded)
    await _set_dob(conn, seeded["subject"]["id"], years_ago=None)
    await consent_service.serve_notice(
        conn, token=token, language_code="english", user_id=seeded["subject"]["id"]
    )

    with pytest.raises(ConsentDefective) as raised:
        await consent_service.capture(
            conn,
            token=token,
            user_id=seeded["subject"]["id"],
            language_code="english",
            grants={str(seeded["purpose"]["purpose_uuid"]): False},
            action_type="checkbox_click",
            ip_address="127.0.0.1",
        )

    assert raised.value.code == "age_required"


async def test_a_date_of_birth_given_later_lets_an_adult_through(
    conn: Any, seeded: dict[str, Any]
) -> None:
    token = await _resolvable_link(conn, seeded)
    await _set_dob(conn, seeded["subject"]["id"], years_ago=None)
    with pytest.raises(ConsentDefective):
        await _capture(conn, seeded, token)

    await _set_dob(conn, seeded["subject"]["id"], years_ago=30)
    artefact = await _capture(conn, seeded, token)
    assert artefact["consent_id"]


async def test_withdrawal_stays_open_to_an_unknown_age(conn: Any, seeded: dict[str, Any]) -> None:
    """Withdrawing is not consenting, and must be as easy as granting was."""
    token = await _resolvable_link(conn, seeded)
    await _set_dob(conn, seeded["subject"]["id"], years_ago=30)
    artefact = await _capture(conn, seeded, token)

    await _set_dob(conn, seeded["subject"]["id"], years_ago=None)
    withdrawn = await consent_service.withdraw(
        conn,
        consent_uuid=str(artefact["consent_uuid"]),
        user_id=seeded["subject"]["id"],
        purpose_uuids=None,
        withdraw_all=True,
        ip_address="127.0.0.1",
    )
    assert withdrawn


async def test_an_adult_is_unaffected(conn: Any, seeded: dict[str, Any]) -> None:
    token = await _resolvable_link(conn, seeded)
    await _set_dob(conn, seeded["subject"]["id"], years_ago=30)
    await _permit_minors(conn, seeded, False)

    artefact = await _capture(conn, seeded, token)
    assert artefact["consent_id"]
