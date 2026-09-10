"""The catalogue of messages is complete, consistent, and safe to render."""

from __future__ import annotations

import pytest

from cmp.core.messages import (
    CATALOGUE,
    JUNCTIONS,
    MAX_SMS_BODY_CHARS,
    MAX_SUBJECT_CHARS,
    Channel,
    Message,
    check_template,
    junction,
    placeholders,
    render_text,
)

#: Provided by the renderer for every message, not declared per junction.
COMMON = {"organisation", "portal_url", "console_url"}


class TestCatalogue:
    def test_every_message_key_has_a_junction_and_nothing_else_does(self) -> None:
        assert {m.value for m in Message} == set(JUNCTIONS)
        assert len(CATALOGUE) == len(JUNCTIONS), "a key is listed twice"

    @pytest.mark.parametrize("j", CATALOGUE, ids=lambda j: j.key.value)
    def test_each_channel_has_default_words(self, j) -> None:  # type: ignore[no-untyped-def]
        for ch in j.channels:
            subject, body = j.default(ch)
            assert body.strip()
            if ch is Channel.EMAIL:
                assert subject and subject.strip() and "\n" not in subject
                assert len(subject) <= MAX_SUBJECT_CHARS
            else:
                assert subject is None
                assert len(body) <= MAX_SMS_BODY_CHARS, f"{j.key.value} sms is {len(body)} chars"

    @pytest.mark.parametrize("j", CATALOGUE, ids=lambda j: j.key.value)
    def test_defaults_only_use_declared_variables(self, j) -> None:  # type: ignore[no-untyped-def]
        allowed = j.variable_names | COMMON
        for ch in j.channels:
            subject, body = j.default(ch)
            used = placeholders(body) | (placeholders(subject) if subject else set())
            assert used <= allowed, f"{j.key.value}/{ch.value} uses {used - allowed}"

    @pytest.mark.parametrize("j", CATALOGUE, ids=lambda j: j.key.value)
    def test_every_variable_has_a_sample_and_a_description(self, j) -> None:  # type: ignore[no-untyped-def]
        for v in j.variables:
            assert v.description.strip() and v.sample.strip(), f"{j.key.value}.{v.name}"
        assert len({v.name for v in j.variables}) == len(j.variables)

    def test_every_code_message_shows_the_code_and_its_life(self) -> None:
        for key in (
            Message.MFA_CODE,
            Message.LOGIN_CODE,
            Message.REGISTRATION_CODE,
            Message.CONSENT_CODE,
            Message.PASSWORD_RESET,
            Message.RIGHTS_VERIFICATION_CODE,
            Message.NOMINATION_CODE,
        ):
            j = junction(key)
            for ch in j.channels:
                _, body = j.default(ch)
                assert "{code}" in body and "{minutes}" in body, key


class TestRendering:
    def test_known_placeholders_are_filled(self) -> None:
        assert render_text("Code {code}, {minutes} min", {"code": "1234", "minutes": 5}) == (
            "Code 1234, 5 min"
        )

    def test_an_unknown_placeholder_is_left_as_written_not_a_crash(self) -> None:
        assert render_text("Hello {name}, code {code}", {"code": "1"}) == "Hello {name}, code 1"

    def test_none_renders_as_nothing(self) -> None:
        assert render_text("[{note}]", {"note": None}) == "[]"

    def test_a_malformed_template_is_returned_as_it_is(self) -> None:
        assert render_text("unbalanced {", {}) == "unbalanced {"

    def test_a_value_containing_braces_is_not_re_parsed(self) -> None:
        assert render_text("{body}", {"body": "see {code}"}) == "see {code}"


class TestCheckTemplate:
    def test_a_good_email_template_passes(self) -> None:
        assert (
            check_template(Message.MFA_CODE, "email", "Code {code}", "Use {code} in {minutes}")
            == []
        )

    def test_an_unknown_variable_is_named_with_the_allowed_ones(self) -> None:
        problems = check_template(Message.MFA_CODE, "email", "Hi", "Dear {full_name}, {code}")
        assert problems and "{full_name}" in problems[0] and "{code}" in problems[0]

    def test_a_format_spec_is_refused(self) -> None:
        problems = check_template(Message.MFA_CODE, "email", "Hi", "{code:>10}")
        assert problems and "malformed" in problems[0]

    def test_an_email_needs_a_one_line_subject(self) -> None:
        assert any("subject" in p for p in check_template(Message.MFA_CODE, "email", None, "x"))
        assert any("one line" in p for p in check_template(Message.MFA_CODE, "email", "a\nb", "x"))

    def test_an_sms_has_no_subject_and_a_length_cap(self) -> None:
        assert any("no subject" in p for p in check_template(Message.LOGIN_CODE, "sms", "Hi", "x"))
        long = "x" * (MAX_SMS_BODY_CHARS + 1)
        assert any("segments" in p for p in check_template(Message.LOGIN_CODE, "sms", None, long))

    def test_a_channel_the_message_does_not_use_is_refused(self) -> None:
        problems = check_template(Message.MFA_CODE, "sms", None, "code {code}")
        assert problems == ["'Staff sign-in code' is not sent by sms"]

    def test_the_body_cannot_be_blank(self) -> None:
        assert any("empty" in p for p in check_template(Message.MFA_CODE, "email", "Hi", "   "))
