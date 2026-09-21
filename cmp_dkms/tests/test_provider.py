"""The scheme itself: round trips, and the four ways it refuses."""

from __future__ import annotations

import base64

import pytest
from app.dkms.base import DkmsError
from app.dkms.local import PREFIX, LocalAesProvider
from app.dkms.types import DataType

VALUES = [
    "Amruta Shukla",
    "amruta.shukla@example.org",
    "+91 98765 43210",
    "",  # empty is a value, not an absence
    "a" * 10_000,  # a long free-text answer
    "Ñoño Ünicode — ऋषि, 名前",  # not everything is ASCII
    "SE::looks-like-ciphertext-but-is-not",
]


@pytest.mark.parametrize("value", VALUES)
def test_a_string_round_trips(provider: LocalAesProvider, value: str) -> None:
    sealed = provider.encrypt(value, DataType.NAME)
    assert sealed.startswith(PREFIX)
    assert provider.decrypt(sealed, DataType.NAME) == value


@pytest.mark.parametrize("value", VALUES)
def test_the_bytes_form_round_trips_too(provider: LocalAesProvider, value: str) -> None:
    sealed = provider.encrypt_bytes(value, DataType.EMAIL)
    assert not sealed.startswith(PREFIX)
    base64.b64decode(sealed, validate=True)  # it really is base64
    assert provider.decrypt_bytes(sealed, DataType.EMAIL) == value


def test_the_two_forms_hold_the_same_envelope(provider: LocalAesProvider) -> None:
    """A value written as a string can be read as bytes, and the other way.

    They differ by prefix and base64 alphabet, and by nothing else. It matters
    because a column may change form - a varchar that becomes a blob - and the
    rows written before that must still open.
    """
    as_string = provider.encrypt("Anuj Kumar", DataType.NAME)
    envelope = base64.urlsafe_b64decode(as_string[len(PREFIX) :])
    as_bytes = base64.b64encode(envelope).decode()

    assert provider.decrypt_bytes(as_bytes, DataType.NAME) == "Anuj Kumar"


def test_the_same_value_encrypts_differently_every_time(provider: LocalAesProvider) -> None:
    """Randomised, which is the property that makes it safe at rest.

    And the property that means an encrypted column cannot be looked up: this
    test is also the reason `email` and `mobile` need a blind index before they
    can be encrypted, and the reason that is a design decision rather than a
    configuration one.
    """
    first = provider.encrypt("amruta@example.org", DataType.EMAIL)
    second = provider.encrypt("amruta@example.org", DataType.EMAIL)

    assert first != second
    assert provider.decrypt(first, DataType.EMAIL) == provider.decrypt(second, DataType.EMAIL)


def test_a_value_written_as_one_type_will_not_open_as_another(provider: LocalAesProvider) -> None:
    """The point of binding the type into the ciphertext.

    A mobile number that arrives in a field mapped to NAME is a mistake in the
    caller's key mapping, and this is where it surfaces - loudly, once, rather
    than as a column of plausible rubbish nobody notices for a year.
    """
    sealed = provider.encrypt("+91 98765 43210", DataType.MOBILE)

    with pytest.raises(DkmsError) as exc:
        provider.decrypt(sealed, DataType.NAME)
    assert "MOBILE" in str(exc.value) and "NAME" in str(exc.value)


def test_a_tampered_blob_is_refused(provider: LocalAesProvider) -> None:
    sealed = provider.encrypt("Amruta Shukla", DataType.NAME)
    body = list(base64.urlsafe_b64decode(sealed[len(PREFIX) :]))
    body[-1] ^= 0x01  # one bit of the tag
    tampered = PREFIX + base64.urlsafe_b64encode(bytes(body)).decode()

    with pytest.raises(DkmsError, match="does not decrypt"):
        provider.decrypt(tampered, DataType.NAME)


def test_another_master_key_cannot_read_it(provider: LocalAesProvider) -> None:
    sealed = provider.encrypt("Amruta Shukla", DataType.NAME)
    somebody_else = LocalAesProvider(b"x" * 32)

    with pytest.raises(DkmsError):
        somebody_else.decrypt(sealed, DataType.NAME)


def test_a_retired_key_still_opens_what_it_wrote() -> None:
    """Rotation, walked: write under v1, rotate to v2, read both."""
    old, new = b"o" * 32, b"n" * 32
    before = LocalAesProvider(old, version=1)
    sealed_by_v1 = before.encrypt("Anuj Kumar", DataType.NAME)

    after = LocalAesProvider(new, version=2, previous={1: old})
    assert after.decrypt(sealed_by_v1, DataType.NAME) == "Anuj Kumar"

    sealed_by_v2 = after.encrypt("Anuj Kumar", DataType.NAME)
    assert after.decrypt(sealed_by_v2, DataType.NAME) == "Anuj Kumar"
    # And the old service cannot read what the new one writes, which is the
    # half of rotation people forget to check.
    with pytest.raises(DkmsError, match="no key for version 2"):
        before.decrypt(sealed_by_v2, DataType.NAME)


def test_nonsense_in_is_an_error_not_a_crash(provider: LocalAesProvider) -> None:
    for junk in ["", "SE::", "SE::!!!!", "not-even-close"]:
        with pytest.raises(DkmsError):
            provider.decrypt(junk, DataType.NAME)


def test_a_short_master_key_is_refused() -> None:
    with pytest.raises(DkmsError, match="at least 32 bytes"):
        LocalAesProvider(b"too short")
