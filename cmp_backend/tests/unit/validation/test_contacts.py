"""A contact as typed, as stored, and as shown back to a stranger."""

from __future__ import annotations

import pytest

from cmp.validation import is_mobile, mask_contact, normalise_contact, normalise_mobile


@pytest.mark.parametrize(
    ("typed", "stored"),
    [
        ("+91 90000 00001", "+919000000001"),
        ("+91-90000-00001", "+919000000001"),
        ("(+91) 90000 00001", "+919000000001"),
        ("9000000001", "9000000001"),
        ("  +919000000001  ", "+919000000001"),
    ],
)
def test_a_mobile_is_stored_as_digits_with_its_plus(typed: str, stored: str) -> None:
    assert normalise_mobile(typed) == stored


def test_a_contact_is_normalised_by_its_shape() -> None:
    assert normalise_contact("  Anjali@Example.ORG ") == "anjali@example.org"
    assert normalise_contact("+91 90000 00001") == "+919000000001"
    assert is_mobile("+919000000001") and not is_mobile("anjali@example.org")


def test_masking_leaves_enough_to_recognise_and_nothing_to_use() -> None:
    assert mask_contact("+919000000001") == "+91••••••••01"
    assert mask_contact("anjali@example.org") == "a•••••@example.org"
    assert mask_contact("ab@x.in") == "a•@x.in"


# ------------------------------------------------------------ email domains


@pytest.mark.parametrize(
    "address",
    ["dco2@cmp.local", "dpo@test.local", "someone@cmp.test"],
)
def test_a_development_domain_is_accepted_outside_production(address: str) -> None:
    """The seed creates every staff account under `cmp.local`, and the console's
    provisioning form must be able to do the same. `email-validator` reserves
    these names; the reservation is lifted everywhere but production."""
    from pydantic import TypeAdapter

    from cmp.validation import Email

    assert TypeAdapter(Email).validate_python(address) == address


@pytest.mark.parametrize("address", ["dco2cmp.local", "dco2@", "@cmp.local", "dco2@cmp..local"])
def test_a_malformed_address_is_still_refused(address: str) -> None:
    """Lifting the domain reservation must not loosen the syntax check."""
    from pydantic import TypeAdapter, ValidationError

    from cmp.validation import Email

    with pytest.raises(ValidationError):
        TypeAdapter(Email).validate_python(address)
