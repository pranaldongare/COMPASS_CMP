"""A caller's choice becomes an enum member, or a 422 that names the choices."""

from __future__ import annotations

import pytest

from cmp.core.enums import LanguageCode
from cmp.core.errors import ValidationFailed
from cmp.validation import choice, spell_choices


def test_a_member_comes_back_as_the_member() -> None:
    assert choice(LanguageCode, "hindi", field="language") is LanguageCode.HINDI


def test_anything_else_is_a_422_naming_the_members() -> None:
    with pytest.raises(ValidationFailed) as refused:
        choice(LanguageCode, "english_enin", field="language")
    assert refused.value.field == "language"
    assert refused.value.message == f"Choose {spell_choices(LanguageCode)}"
    assert refused.value.message.startswith("Choose english, hindi, ")
    assert refused.value.message.endswith(" or gujarati")
