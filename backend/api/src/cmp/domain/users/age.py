"""Section 9, until the guardian route exists.

The DPDP Act asks for a parent's or lawful guardian's verifiable consent before
*any* processing of a child's personal data (s.9(1)), and this platform has no
way to take one yet - the guardian relationship and its consent are deferred.
So there is exactly one lawful answer to a child: no. No account is created for
one, and no consent is recorded from one. `permitted_for_minors` on a purpose is
s.9(3) - no tracking or targeting of children - and was never a stand-in for the
guardian, so it does not open the door either.

An unknown age is not an adult. `cmp_is_minor()` answers NULL when it does not
know, and its own comment says callers must not treat that as adult. Most
accounts were created through a consent link that never asked, so the answer to
an unknown age is to ask: a consent waits for a date of birth, and the portal
asks for one at the next sign-in. Withdrawing a consent and exercising a right
are not consents, and stay open to everybody whatever their age.

The age test is always the database's (`cmp_is_minor`, over `minor_until`),
never Python's, so the API, a report and a future sweep cannot disagree about
who is a child.

The wording refuses without advertising a route that does not exist. When the
guardian route returns (D-02), these are the two places that change.
"""

from __future__ import annotations

from typing import Final

from cmp.core.errors import ConsentDefective, ValidationFailed
from cmp.db.repositories import users as user_repo
from cmp.db.sql import Conn

MINOR_REFUSED: Final = (
    "We cannot register or record consent for a person under eighteen. "
    "If you think your date of birth is wrong, contact the Privacy Office."
)
AGE_REQUIRED: Final = "We need your date of birth before this consent can be recorded."


async def refuse_a_minor(conn: Conn, *, dob: str) -> None:
    """At registration: a date of birth under eighteen creates nothing."""
    if await user_repo.would_be_minor(conn, dob):
        raise ValidationFailed(MINOR_REFUSED, field="dob", code="minor_not_permitted")


async def require_an_adult(conn: Conn, *, user_id: int) -> None:
    """Before a consent is recorded: a known adult, or nothing is written."""
    is_minor = await user_repo.is_minor(conn, user_id)
    if is_minor is None:
        raise ConsentDefective(AGE_REQUIRED, field="dob", code="age_required")
    if is_minor:
        raise ConsentDefective(MINOR_REFUSED, code="consent_minor_not_permitted")
