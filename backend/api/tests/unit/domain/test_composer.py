"""Composing an HR activity's notice from its template version (ADR 0033).

The composed text is what a participant is served and what her consent
hashes, so the composer is held to four things: each slot is filled exactly
once, the description stays inside the slot's rules, nothing an HR PoC
writes can become a link or a slot, and the same inputs always give the same
text and the same hash.
"""

from __future__ import annotations

import pytest

from cmp.core.errors import ValidationFailed
from cmp.domain.notices import composer

LOCKED = (
    "The Legal office will process your data for:\n{{purposes}}\n\n"
    "About this activity: {{description}}\n\nWrite to legal@example.org to withdraw."
)
PURPOSES = [
    {
        "name": "Wellness sessions",
        "uses": "Scheduling the sessions you sign up for.",
        "data_categories": ["name", "employee_id"],
        "is_mandatory": True,
    },
    {
        "name": "Follow-up survey",
        "uses": "Asking how the sessions went.",
        "data_categories": ["email"],
        "is_mandatory": False,
    },
]


class TestTheSlots:
    def test_a_text_with_both_slots_once_has_no_problem(self) -> None:
        assert composer.placeholder_problems(LOCKED) == []

    @pytest.mark.parametrize(
        ("text", "problem"),
        [
            ("{{description}} only", "{{purposes}} is missing"),
            ("{{purposes}} only", "{{description}} is missing"),
            ("{{purposes}} {{purposes}} {{description}}", "{{purposes}} appears 2 times"),
            ("{{purposes}} {{description}} {{description}}", "{{description}} appears 2 times"),
        ],
    )
    def test_each_slot_must_appear_exactly_once(self, text: str, problem: str) -> None:
        assert problem in composer.placeholder_problems(text)

    def test_an_uncomposable_text_is_refused(self) -> None:
        with pytest.raises(ValidationFailed):
            composer.compose("{{purposes}} only", PURPOSES, "A week of sessions.", max_length=200)


class TestTheDescription:
    def test_it_is_trimmed_and_served(self) -> None:
        text = composer.compose(LOCKED, PURPOSES, "  A week of sessions.  ", max_length=200)
        assert "About this activity: A week of sessions.\n" in text

    def test_it_stays_within_the_slot_s_limit(self) -> None:
        with pytest.raises(ValidationFailed) as refused:
            composer.check_description("x" * 201, max_length=200)
        assert refused.value.field == "description"
        assert composer.check_description("x" * 200, max_length=200) == "x" * 200

    def test_it_is_required(self) -> None:
        with pytest.raises(ValidationFailed):
            composer.check_description("   ", max_length=200)

    @pytest.mark.parametrize("bad", ["Use {{purposes}} here", "an {{ open", "a }} close"])
    def test_it_holds_no_slot_of_its_own(self, bad: str) -> None:
        with pytest.raises(ValidationFailed):
            composer.check_description(bad, max_length=200)

    @pytest.mark.parametrize(
        "bad",
        [
            "Sign up at https://example.org/wellness",
            "See http://intranet/wellness",
            "Visit www.example.org",
            "Write to mailto:hr@example.org",
            "Open ftp://files.example.org",
        ],
    )
    def test_it_holds_no_link(self, bad: str) -> None:
        with pytest.raises(ValidationFailed):
            composer.check_description(bad, max_length=200)


class TestThePurposes:
    def test_each_chosen_purpose_is_listed_in_order_with_its_need(self) -> None:
        block = composer.render_purposes(PURPOSES)
        assert block.index("Wellness sessions (required)") < block.index(
            "Follow-up survey (optional)"
        )
        assert "Data: name, employee_id" in block

    def test_what_fills_one_slot_is_never_read_as_the_other(self) -> None:
        sly = [{**PURPOSES[0], "uses": "It says {{description}} here"}]
        text = composer.compose(LOCKED, sly, "A week of sessions.", max_length=200)
        assert "It says {{description}} here" in text
        assert text.count("A week of sessions.") == 1


class TestTheHash:
    def test_the_same_inputs_give_the_same_text_and_hash(self) -> None:
        a = composer.compose(LOCKED, PURPOSES, "A week of sessions.", max_length=200)
        b = composer.compose(LOCKED, list(PURPOSES), "A week of sessions.", max_length=200)
        assert a == b
        assert composer.hash_text(a) == composer.hash_text(b)

    def test_a_different_description_gives_a_different_hash(self) -> None:
        a = composer.compose(LOCKED, PURPOSES, "A week of sessions.", max_length=200)
        b = composer.compose(LOCKED, PURPOSES, "Two weeks of sessions.", max_length=200)
        assert composer.hash_text(a) != composer.hash_text(b)

    def test_the_hash_is_the_notice_s_own(self) -> None:
        from cmp.core.security import content_hash

        assert composer.hash_text("text") == content_hash("text")
