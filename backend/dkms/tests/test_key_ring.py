"""The key ring: the active master key plus the retired ones, and what is refused.

Rotation only works if every version number means exactly one key. The ring is
built from two settings - `DKMS_KEY_VERSION` with `DKMS_MASTER_KEY`, and the
JSON in `DKMS_PREVIOUS_KEYS` - and until these checks existed nothing stopped
the second from naming the first's number. When it did, the retired key won,
and new ciphertext was sealed under retired material while its header named
the active version. These tests walk rotation end to end through the settings,
and then each way a ring is refused at startup.

Every key here is synthetic: a repeated byte, base64-encoded.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Iterator

import pytest
from app.config import Settings, get_settings
from app.dkms.base import DkmsError
from app.dkms.local import LocalAesProvider
from app.dkms.types import DataType
from pydantic import ValidationError

OLD, MIDDLE, NEW = b"o" * 32, b"m" * 32, b"n" * 32


def b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode()


def settings(*, active: bytes, version: int, previous: dict[str, str]) -> Settings:
    """Settings as the service would read them, without a developer's `.env`."""
    return Settings(
        _env_file=None,
        DKMS_MASTER_KEY=b64(active),
        DKMS_KEY_VERSION=version,
        DKMS_PREVIOUS_KEYS=json.dumps(previous),
    )


def provider_from(s: Settings) -> LocalAesProvider:
    """What `app.main.build_provider` builds, for the local scheme."""
    return LocalAesProvider(
        s.master_key_bytes, version=s.key_version, previous=s.previous_key_bytes
    )


# --------------------------------------------------------------- rotation works
def test_rotation_through_the_settings_round_trips() -> None:
    """v1, then v2 with v1 retired, then v3 with both retired - each step reads all."""
    v1 = provider_from(settings(active=OLD, version=1, previous={}))
    sealed_v1 = v1.encrypt("Anuj Kumar", DataType.NAME)

    v2 = provider_from(settings(active=MIDDLE, version=2, previous={"1": b64(OLD)}))
    sealed_v2 = v2.encrypt_bytes("anuj@example.org", DataType.EMAIL)
    assert v2.decrypt(sealed_v1, DataType.NAME) == "Anuj Kumar"
    assert v2.decrypt_bytes(sealed_v2, DataType.EMAIL) == "anuj@example.org"

    v3 = provider_from(settings(active=NEW, version=3, previous={"1": b64(OLD), "2": b64(MIDDLE)}))
    sealed_v3 = v3.encrypt("+91 98765 43210", DataType.MOBILE)
    assert v3.decrypt(sealed_v1, DataType.NAME) == "Anuj Kumar"
    assert v3.decrypt_bytes(sealed_v2, DataType.EMAIL) == "anuj@example.org"
    assert v3.decrypt(sealed_v3, DataType.MOBILE) == "+91 98765 43210"


def test_new_ciphertext_is_sealed_under_the_active_key_and_version() -> None:
    """The property the collision broke: header and key agree, and both are current.

    Read back by a provider that holds only the active key. If the write had
    used a retired key, this provider could not open it.
    """
    s = settings(active=NEW, version=2, previous={"1": b64(OLD)})
    sealed = provider_from(s).encrypt_bytes("Amruta Shukla", DataType.NAME)

    assert base64.b64decode(sealed)[2] == 2  # the version byte in the header
    only_active = LocalAesProvider(NEW, version=2)
    assert only_active.decrypt_bytes(sealed, DataType.NAME) == "Amruta Shukla"
    with pytest.raises(DkmsError):
        LocalAesProvider(OLD, version=2).decrypt_bytes(sealed, DataType.NAME)


def test_a_historical_version_opens_after_its_key_is_retired() -> None:
    sealed_by_v4 = LocalAesProvider(OLD, version=4).encrypt("Ruth", DataType.NAME)
    later = provider_from(settings(active=NEW, version=9, previous={"4": b64(OLD)}))

    assert later.decrypt(sealed_by_v4, DataType.NAME) == "Ruth"


def test_a_zero_padded_identifier_still_names_its_version() -> None:
    """`"04"` is version 4. Accepted, as long as it does not collide with anything."""
    sealed_by_v4 = LocalAesProvider(OLD, version=4).encrypt("Ruth", DataType.NAME)
    later = provider_from(settings(active=NEW, version=9, previous={"04": b64(OLD)}))

    assert later.decrypt(sealed_by_v4, DataType.NAME) == "Ruth"


# ------------------------------------------------------- collisions are refused
@pytest.mark.parametrize("ident", ["2", "02", "002"])
def test_a_retired_key_under_the_active_number_is_refused(ident: str) -> None:
    """Including the aliases that only become the same number after `int()`."""
    with pytest.raises(ValidationError, match="which is DKMS_KEY_VERSION"):
        settings(active=NEW, version=2, previous={ident: b64(OLD)})


def test_two_spellings_of_one_retired_version_are_refused() -> None:
    with pytest.raises(ValidationError, match="names version 1 twice"):
        settings(active=NEW, version=3, previous={"1": b64(OLD), "01": b64(MIDDLE)})


def test_the_same_identifier_twice_in_the_json_is_refused() -> None:
    """`json.loads` would keep the last silently; the settings do not."""
    raw = f'{{"1": "{b64(OLD)}", "1": "{b64(MIDDLE)}"}}'
    with pytest.raises(ValidationError, match="more than once"):
        Settings(
            _env_file=None,
            DKMS_MASTER_KEY=b64(NEW),
            DKMS_KEY_VERSION=2,
            DKMS_PREVIOUS_KEYS=raw,
        )


def test_the_provider_refuses_a_collision_too() -> None:
    """For callers that build the provider without going through the settings."""
    with pytest.raises(DkmsError, match="both the active key and a retired one"):
        LocalAesProvider(NEW, version=1, previous={1: OLD})


# -------------------------------------------- malformed identifiers and keys
@pytest.mark.parametrize("ident", ["0", "-1", "+1", " 1", "1_0", "1.0", "v1", "", "256", "٣"])
def test_an_identifier_that_is_not_a_valid_version_is_refused(ident: str) -> None:
    with pytest.raises(ValidationError, match="DKMS_PREVIOUS_KEYS has the version"):
        settings(active=NEW, version=1, previous={ident: b64(OLD)})


@pytest.mark.parametrize("length", [0, 16, 31])
def test_a_short_retired_key_is_refused(length: int) -> None:
    with pytest.raises(ValidationError, match="at least 32 bytes"):
        settings(active=NEW, version=2, previous={"1": b64(b"o" * length)})


@pytest.mark.parametrize("length", [16, 31])
def test_a_short_active_key_is_refused(length: int) -> None:
    with pytest.raises(ValidationError, match="DKMS_MASTER_KEY must decode to at least 32"):
        settings(active=b"n" * length, version=1, previous={})


def test_a_retired_key_that_is_not_base64_is_refused() -> None:
    with pytest.raises(ValidationError, match="not valid base64"):
        settings(active=NEW, version=2, previous={"1": "not base64 at all!"})


@pytest.mark.parametrize("raw", ["[]", '"x"', "{not json", '{"1": 5}'])
def test_a_ring_that_is_not_an_object_of_strings_is_refused(raw: str) -> None:
    with pytest.raises(ValidationError, match="DKMS_PREVIOUS_KEYS"):
        Settings(
            _env_file=None,
            DKMS_MASTER_KEY=b64(NEW),
            DKMS_KEY_VERSION=2,
            DKMS_PREVIOUS_KEYS=raw,
        )


def test_the_provider_refuses_a_short_retired_key_too() -> None:
    with pytest.raises(DkmsError, match="retired key for version 1"):
        LocalAesProvider(NEW, version=2, previous={1: b"short"})


# ------------------------------------------------------------ at startup
@pytest.fixture
def fresh_settings() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_the_service_will_not_load_a_colliding_ring(
    monkeypatch: pytest.MonkeyPatch, fresh_settings: None
) -> None:
    """The same refusal, reached the way the service reaches it: from the environment."""
    monkeypatch.setenv("DKMS_KEY_VERSION", "1")
    monkeypatch.setenv("DKMS_PREVIOUS_KEYS", json.dumps({"01": b64(OLD)}))

    with pytest.raises(ValidationError, match="which is DKMS_KEY_VERSION"):
        get_settings()
