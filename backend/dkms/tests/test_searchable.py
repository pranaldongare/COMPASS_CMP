"""Hashing and the two searches.

The properties that matter are not "it returns 64 characters". They are:
the same value always hashes the same way however it was typed, two
different values do not collide by design, a term's runs are a subset of the
runs of any value containing it - that is what makes substring search work -
and nothing here ever reveals what it was given.
"""

from __future__ import annotations

import pytest
from app.dkms.searchable import (
    DEFAULT_N,
    hash_of,
    ngrams_of,
    normalise,
    normalise_for_ngrams,
    search_ngrams,
)
from app.dkms.types import DataType

KEY = b"a-test-key-of-at-least-32-bytes-in-length"


class TestExactHash:
    @pytest.mark.parametrize(
        ("typed", "data_type"),
        [
            ("Amruta@Example.ORG", DataType.EMAIL),
            ("  amruta@example.org  ", DataType.EMAIL),
            ("AMRUTA@EXAMPLE.ORG", DataType.EMAIL),
        ],
    )
    def test_the_same_address_however_it_was_typed(self, typed: str, data_type: DataType) -> None:
        assert hash_of(KEY, data_type, typed) == hash_of(KEY, DataType.EMAIL, "amruta@example.org")

    @pytest.mark.parametrize(
        "typed",
        ["+91 98765 43210", "(+91) 98765-43210", "  +919876543210 "],
    )
    def test_the_same_number_however_it_was_written(self, typed: str) -> None:
        assert hash_of(KEY, DataType.MOBILE, typed) == hash_of(
            KEY, DataType.MOBILE, "+919876543210"
        )

    def test_one_box_that_takes_either_is_normalised_as_whichever_it_is(self) -> None:
        """An `@` decides which rule reduces it, the way the rest of the
        platform decides it - so a number typed with brackets into the public
        rights form matches the same number typed plainly."""
        assert hash_of(KEY, DataType.CONTACT, "(+91) 99999 11111") == hash_of(
            KEY, DataType.CONTACT, "+919999911111"
        )
        assert hash_of(KEY, DataType.CONTACT, "A@X.org") == hash_of(
            KEY, DataType.CONTACT, "a@x.org"
        )

    def test_each_type_is_its_own_namespace(self) -> None:
        """The label is part of the hashed message, so the same address filed
        as a CONTACT and as an EMAIL gives different hashes. That is what
        stops a lookup crossing from `submitted_contact_hash` into
        `email_hash`, where it would be answering a different question."""
        assert hash_of(KEY, DataType.CONTACT, "a@x.org") != hash_of(KEY, DataType.EMAIL, "a@x.org")

    def test_an_identifier_keeps_its_case(self) -> None:
        """An employee number is issued, not typed by its owner: `ORG-1` and
        `org-1` may be two people."""
        assert hash_of(KEY, DataType.ORG_ID, "ORG-1") != hash_of(KEY, DataType.ORG_ID, "org-1")

    def test_a_different_key_gives_a_different_hash(self) -> None:
        assert hash_of(KEY, DataType.EMAIL, "a@x.org") != hash_of(
            b"another-key-of-at-least-32-bytes-long!!", DataType.EMAIL, "a@x.org"
        )

    def test_empty_is_empty_rather_than_the_hash_of_nothing(self) -> None:
        """Otherwise every row with no secondary address would share one
        hash, and the unique index would refuse the second of them."""
        assert hash_of(KEY, DataType.EMAIL, "") == ""
        assert hash_of(KEY, DataType.EMAIL, "   ") == ""


class TestNgrams:
    def test_a_terms_runs_are_a_subset_of_any_value_containing_it(self) -> None:
        """The property the whole substring search rests on."""
        value = set(ngrams_of(KEY, DataType.NAME, "Amruta Shukla"))
        for term in ("amr", "shukla", "ta shu", "Amruta Shukla"):
            assert set(search_ngrams(KEY, DataType.NAME, term)) <= value, term

    def test_a_term_that_is_not_in_the_value_is_not_a_subset(self) -> None:
        value = set(ngrams_of(KEY, DataType.NAME, "Amruta Shukla"))
        assert not set(search_ngrams(KEY, DataType.NAME, "priya")) <= value

    def test_case_spacing_and_composition_do_not_matter(self) -> None:
        assert ngrams_of(KEY, DataType.NAME, "AMRUTA  SHUKLA") == ngrams_of(
            KEY, DataType.NAME, "amruta shukla"
        )

    def test_runs_are_deduplicated_and_ordered(self) -> None:
        """A repeated run says nothing more, and a stable order makes a
        stored column comparable in a diff."""
        runs = ngrams_of(KEY, DataType.NAME, "banana")
        assert len(runs) == len(set(runs))
        assert runs == ngrams_of(KEY, DataType.NAME, "banana")

    def test_a_value_shorter_than_the_run_is_still_findable(self) -> None:
        assert ngrams_of(KEY, DataType.NAME, "Li") == search_ngrams(KEY, DataType.NAME, "li")

    def test_the_run_length_changes_the_hashes(self) -> None:
        """So a column written with one `n` cannot be searched with another
        and silently return nothing."""
        assert ngrams_of(KEY, DataType.NAME, "amruta", n=3) != ngrams_of(
            KEY, DataType.NAME, "amruta", n=4
        )

    def test_the_count_is_what_the_arithmetic_says(self) -> None:
        text = normalise_for_ngrams("Amruta Shukla")
        assert len(set(ngrams_of(KEY, DataType.NAME, "Amruta Shukla"))) == len(
            {text[i : i + DEFAULT_N] for i in range(len(text) - DEFAULT_N + 1)}
        )


class TestNormalisation:
    def test_it_is_the_platforms_rule_not_this_services(self) -> None:
        """Pinned: the platform computes these hashes locally too, and a
        change here would make every stored hash unfindable."""
        assert normalise(DataType.EMAIL, " A@X.org ") == "a@x.org"
        assert normalise(DataType.MOBILE, "(+91) 98765 43210") == "+919876543210"
        assert normalise(DataType.MOBILE, "98765 43210") == "9876543210"
        assert normalise(DataType.ORG_ID, " ORG-1 ") == "ORG-1"
        assert normalise(DataType.NAME, " Priya ") == "priya"
