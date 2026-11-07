"""An address for the organisation's board, and the name given with it (0064).

Both come from whoever keeps the list or sends a report, and both travel in the
officers' mail: the address is kept as its blind index finds it, and a name
that is somebody's ciphertext is refused, since a message opens every sealed
value it carries.
"""

from __future__ import annotations

import pytest

from cmp.core.errors import ValidationFailed
from cmp.domain.breach.reports import board_address, board_name


def test_an_address_is_kept_in_lower_case_however_it_was_typed() -> None:
    assert board_address("  Chair@Example.ORG ", field="email") == "chair@example.org"


@pytest.mark.parametrize("given", ["not an address", "", None, "a@b"])
def test_what_is_not_an_address_is_refused_on_its_field(given: str | None) -> None:
    with pytest.raises(ValidationFailed) as refused:
        board_address(given, field="extra.3.email")
    assert refused.value.field == "extra.3.email"
    assert refused.value.message == "That is not an email address"


@pytest.mark.parametrize("given", [None, "", "   "])
def test_no_name_is_none(given: str | None) -> None:
    assert board_name(given, field="full_name") is None


def test_a_name_is_kept_as_said() -> None:
    assert board_name("  The Chair ", field="full_name") == "The Chair"


@pytest.mark.parametrize("given", ["SE::v1:abc", "The Chair SE::v1:abc"])
def test_a_name_carrying_ciphertext_is_refused_on_its_field(given: str) -> None:
    with pytest.raises(ValidationFailed) as refused:
        board_name(given, field="extra.0.full_name")
    assert refused.value.field == "extra.0.full_name"
    assert "SE::" in refused.value.message
