"""Finding a person by part of their name, when the name is ciphertext.

The exact hash answers "which row holds this address". It cannot answer
"which rows have `shu` in the name", and that is the search staff lost when
the names were sealed. The hashed runs bring it back: a row carries the runs
of its name, a term carries fewer, and `@>` asks whether the row's set
contains all of the term's.

What is worth pinning is the behaviour a person sees - a part of a name
finds them, a wrong name does not, case and spacing do not matter - and the
one property that makes it sound: the runs are of the *plaintext*, computed
on the way in, and the column they are compared against never holds a name.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from cmp.core.pagination import PageRequest
from cmp.db.repositories import audit_lookup
from cmp.db.repositories import users as user_repo
from cmp.db.sql import fetch_one

pytestmark = pytest.mark.anyio


def _page() -> PageRequest:
    return PageRequest(limit=20, cursor=None, sort_field="created_at", descending=True)


async def _person(conn: Any, name: str, **kw: Any) -> dict[str, Any]:
    return await user_repo.create(
        conn,
        full_name=name,
        email=f"{uuid4().hex[:10]}@search.test",
        mobile=f"+9198765{uuid4().int % 100000:05d}",
        role=kw.pop("role", "data_subject"),
        status="active",
        **kw,
    )


class TestPartOfAName:
    async def test_a_middle_fragment_finds_the_person(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        tag = uuid4().hex[:8]
        await _person(conn, f"Amruta {tag} Shukla")

        rows, _, _ = await user_repo.list_users(conn, _page(), q=tag[2:6])

        assert len(rows) == 1

    async def test_case_and_spacing_do_not_matter(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        tag = uuid4().hex[:8]
        await _person(conn, f"Priya  {tag}  Nair")

        for term in (tag.upper(), f" {tag} ", tag.lower()):
            rows, _, _ = await user_repo.list_users(conn, _page(), q=term)
            assert len(rows) == 1, term

    async def test_a_name_nobody_has_finds_nobody(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        await _person(conn, f"Findable {uuid4().hex[:8]}")

        rows, _, _ = await user_repo.list_users(conn, _page(), q="zzqqxx")

        assert rows == []

    async def test_a_term_shorter_than_a_run_does_not_match_everybody(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        """An empty set is contained in every set. If a two-character term
        produced no runs and the clause were still applied, the register
        would answer with every row it holds."""
        await _person(conn, f"Two {uuid4().hex[:8]}")

        rows, _, _ = await user_repo.list_users(conn, _page(), q="zz")

        assert rows == []

    async def test_the_column_holds_hashes_and_never_the_name(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        tag = uuid4().hex[:8]
        person = await _person(conn, f"Sealed {tag} Person")

        row = await fetch_one(
            conn,
            "SELECT full_name, full_name_ngrams FROM auth_user WHERE uuid = %s",
            (str(person["uuid"]),),
        )

        assert row is not None
        assert str(row["full_name"]).startswith("SE::")
        runs = list(row["full_name_ngrams"])
        assert runs, "the name was written without its runs"
        assert all(len(r) == 64 and tag not in r for r in runs)

    async def test_a_rename_is_findable_under_the_new_name(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        old, new = uuid4().hex[:8], uuid4().hex[:8]
        person = await _person(conn, f"Before {old}")

        await user_repo.update_profile(conn, int(person["id"]), full_name=f"After {new}")

        found, _, _ = await user_repo.list_users(conn, _page(), q=new)
        gone, _, _ = await user_repo.list_users(conn, _page(), q=old)
        assert len(found) == 1
        assert gone == []


class TestTheContactSearchStillWorks:
    async def test_a_whole_address_matches_exactly(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        address = f"{uuid4().hex[:10]}@search.test"
        await user_repo.create(
            conn,
            full_name="Contact Person",
            email=address,
            mobile=f"+9198765{uuid4().int % 100000:05d}",
            role="data_subject",
            status="active",
        )

        rows, _, _ = await user_repo.list_users(conn, _page(), q=address.upper())

        assert len(rows) == 1

    async def test_half_an_address_does_not(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        """A contact has no runs, deliberately: equality is all it leaks."""
        address = f"{uuid4().hex[:10]}@search.test"
        await user_repo.create(
            conn,
            full_name="Contact Person",
            email=address,
            mobile=f"+9198765{uuid4().int % 100000:05d}",
            role="data_subject",
            status="active",
        )

        rows, _, _ = await user_repo.list_users(conn, _page(), q=address.split("@")[0])

        assert rows == []


class TestTheAuditPicker:
    async def test_it_finds_a_person_by_part_of_a_name(
        self, conn: Any, seeded: dict[str, Any], request_context: Any
    ) -> None:
        tag = uuid4().hex[:8]
        await _person(conn, f"Audited {tag}")

        hits = await audit_lookup.lookup(conn, "data_subject", tag)

        assert len(hits) == 1
        assert hits[0]["filter"] == "subject"
