"""The consent register, searched by the data subject (2026-11-12).

The register could be narrowed by project, site, status and date, and not by
whose consent it is - the first thing an officer with a person in front of
them asks. A name is sealed, so it is found the way the account register
finds one: by the hashed runs beside it, three letters or more; a contact by
its hash, whole. Scope is unchanged: the search narrows what the caller could
already list.
"""

from __future__ import annotations

from typing import Any

import pytest

from cmp.core.pagination import PageRequest
from cmp.core.permissions import Role
from cmp.db.repositories import consent as consent_repo
from cmp.infrastructure.dkms.blind import ngrams_of
from tests.integration.test_rights_flows import _consent
from tests.security.test_site_boundary import _owner

pytestmark = pytest.mark.integration

PAGE = PageRequest(limit=50, cursor=None, sort_field="created_at", descending=True)


async def _found(conn: Any, seeded: dict[str, Any], term: str | None, **who: Any) -> set[str]:
    who = who or {"role": Role.DPO, "user_id": int(seeded["users"]["dpo"]["id"])}
    rows, _, _ = await consent_repo.list_all_consents(conn, PAGE, person=term, **who)
    return {str(r["consent_uuid"]) for r in rows}


async def test_a_person_is_found_by_part_of_the_name_or_a_whole_contact(
    conn: Any, seeded: dict[str, Any]
) -> None:
    consent = await _consent(conn, seeded)
    hers = str(consent["consent_uuid"])
    # The fixture's subject is inserted raw; an account made through the
    # service has its runs written with its name.
    await conn.execute(
        "UPDATE auth_user SET full_name_ngrams = %s WHERE id = %s",
        (ngrams_of("Test Subject"), seeded["subject"]["id"]),
    )

    assert hers in await _found(conn, seeded, None)
    # Part of the name, in any case; the whole name too.
    assert hers in await _found(conn, seeded, "subj")
    assert hers in await _found(conn, seeded, "TEST SUB")
    # A whole contact, as it would be pasted.
    assert hers in await _found(conn, seeded, "subject@test.local")
    assert hers in await _found(conn, seeded, "+915550000001")
    # Somebody else, a fragment of a contact, and a name that is not hers.
    assert hers not in await _found(conn, seeded, "somebody.else@test.local")
    assert hers not in await _found(conn, seeded, "subject@test")
    assert hers not in await _found(conn, seeded, "Zzyzx Qwv")
    # Two letters cannot be searched for: no runs, so no name matches.
    assert hers not in await _found(conn, seeded, "su")


async def test_the_search_narrows_what_the_caller_may_see_and_nothing_more(
    conn: Any, seeded: dict[str, Any]
) -> None:
    consent = await _consent(conn, seeded)
    hers = str(consent["consent_uuid"])
    await conn.execute(
        "UPDATE auth_user SET full_name_ngrams = %s WHERE id = %s",
        (ngrams_of("Test Subject"), seeded["subject"]["id"]),
    )
    # A collection owner with no site on the project lists nothing, and
    # searching for her by name does not change that.
    rco = await _owner(conn, "rco", "search.other.owner@test.local")
    assert await _found(conn, seeded, None, role=Role.RCO, user_id=rco) == set()
    assert await _found(conn, seeded, "subj", role=Role.RCO, user_id=rco) == set()
    assert hers in await _found(conn, seeded, "subj")
