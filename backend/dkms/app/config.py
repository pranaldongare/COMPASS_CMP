"""Settings, and the two that production refuses to start without."""

from __future__ import annotations

import base64
import json
import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#: The key in `.env.example`. Named here so the startup check can refuse it
#: rather than comparing against a string spelled out in two places.
DEV_MASTER_KEY = "ZGV2LW9ubHktbWFzdGVyLWtleS0zMi1ieXRlcy1sb25nISE="

#: The hashing key, in the clear rather than base64, because the platform
#: holds the same string under `BLIND_INDEX_KEY` and the two must be typed
#: identically into two .env files by a person.
DEV_HASH_KEY = "dev-only-blind-index-key-32-bytes-long!"

#: The shortest master key, active or retired, that the service accepts. A
#: master key is not handed to AES directly: it is the input to HKDF-SHA256,
#: which derives the 32-byte AES-256 key for each type and version. Input
#: shorter than the key it is stretched into cannot carry 256 bits of secret,
#: so 32 bytes is the floor. Longer is allowed - the development key is 35 -
#: and changes nothing about the derived keys' length.
MIN_MASTER_KEY_BYTES = 32

#: The envelope carries the key version in one unsigned byte, and 0 is never
#: issued, so every version - active or retired - is between these two.
MIN_KEY_VERSION, MAX_KEY_VERSION = 1, 255


def parse_previous_keys(raw: str, *, active_version: int) -> dict[int, bytes]:
    """`DKMS_PREVIOUS_KEYS`, read strictly, or a `ValueError` saying why not.

    The provider builds one mapping of version to master key out of the active
    key and this ring. If the ring also names the active version, one of the
    two has to lose, and either way is wrong: let the retired key win and new
    ciphertext is written under retired material while its header claims the
    active version; let the active key win and whatever the retired key wrote
    under that number silently stops opening. A collision is therefore a
    configuration mistake, and the service refuses to start on it rather than
    choosing.

    The comparison is made after the identifiers become integers, because that
    is the form the provider and the envelope use. JSON keys are strings, so
    `"01"` and `"1"` are two keys to `json.loads` and one version to
    everything after it; both a clash with the active version and a clash
    between two retired entries are caught here. Identifiers must be plain
    decimal digits - `int()` would also accept `"+1"`, `" 1"` and `"1_0"`,
    none of which anybody means - and a JSON object that names the same
    identifier twice is refused rather than keeping whichever came last.

    Nothing here echoes a key's value, only its identifier, so the error is
    safe to land in a log.
    """

    def _no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        seen: dict[str, object] = {}
        for k, v in pairs:
            if k in seen:
                raise ValueError(f"DKMS_PREVIOUS_KEYS names version {k!r} more than once")
            seen[k] = v
        return seen

    try:
        parsed = json.loads(raw or "{}", object_pairs_hook=_no_duplicates)
    except json.JSONDecodeError as exc:
        raise ValueError("DKMS_PREVIOUS_KEYS is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError('DKMS_PREVIOUS_KEYS must be a JSON object, as {"1": "<base64>"}')

    ring: dict[int, bytes] = {}
    for ident, encoded in parsed.items():
        if not (ident.isascii() and ident.isdigit()):
            raise ValueError(
                f"DKMS_PREVIOUS_KEYS has the version {ident!r}, which is not a "
                "positive whole number written in digits"
            )
        version = int(ident)
        if not MIN_KEY_VERSION <= version <= MAX_KEY_VERSION:
            raise ValueError(
                f"DKMS_PREVIOUS_KEYS has the version {ident!r}, outside "
                f"{MIN_KEY_VERSION}-{MAX_KEY_VERSION}: the envelope holds the "
                "version in one byte and 0 is never issued"
            )
        if version == active_version:
            raise ValueError(
                f"DKMS_PREVIOUS_KEYS has the version {ident!r}, which is "
                f"DKMS_KEY_VERSION ({active_version}). A retired key cannot share "
                "a number with the active one: one of them would be used under "
                "the other's name. Give the active key a new number, or remove "
                "the entry if it is the active key repeated."
            )
        if version in ring:
            raise ValueError(
                f"DKMS_PREVIOUS_KEYS names version {version} twice, spelt "
                "differently; only one of them could ever be used"
            )
        if not isinstance(encoded, str):
            raise ValueError(f"DKMS_PREVIOUS_KEYS version {ident!r} is not a base64 string")
        try:
            material = base64.b64decode(encoded, validate=True)
        except Exception as exc:  # re-raised with a message a person can act on
            raise ValueError(f"DKMS_PREVIOUS_KEYS version {ident!r} is not valid base64") from exc
        if len(material) < MIN_MASTER_KEY_BYTES:
            raise ValueError(
                f"DKMS_PREVIOUS_KEYS version {ident!r} must decode to at least "
                f"{MIN_MASTER_KEY_BYTES} bytes"
            )
        ring[version] = material
    return ring


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["local", "test", "staging", "production"] = "local"

    provider: Literal["local", "sdk"] = Field("local", alias="DKMS_PROVIDER")
    sdk_module: str = Field("dkms", alias="DKMS_SDK_MODULE")
    sdk_factory: str = Field("get_client", alias="DKMS_SDK_FACTORY")

    master_key: str = Field(DEV_MASTER_KEY, alias="DKMS_MASTER_KEY")
    #: The key the exact and n-gram hashes are computed under. Separate from
    #: the master key so that a hash says nothing about an encryption key and
    #: either can be rotated alone - and shared with the platform, which
    #: computes the same hashes locally so that people can still sign in when
    #: this service is unreachable. It must equal the platform's
    #: `BLIND_INDEX_KEY`, to the character.
    hash_key: str = Field(DEV_HASH_KEY, alias="DKMS_HASH_KEY")
    key_version: int = Field(1, alias="DKMS_KEY_VERSION", ge=MIN_KEY_VERSION, le=MAX_KEY_VERSION)
    #: Retired master keys by version, so their ciphertext still opens.
    previous_keys: str = Field("{}", alias="DKMS_PREVIOUS_KEYS")

    #: 0 means one per core. OpenSSL releases the GIL, so these are real.
    pool_workers: int = Field(0, alias="DKMS_POOL_WORKERS", ge=0, le=128)
    max_records: int = Field(5000, alias="DKMS_MAX_RECORDS", ge=1)
    #: Records handed to a worker at a time. Small enough to spread the work,
    #: large enough that the hand-off is not most of it.
    chunk_size: int = Field(64, alias="DKMS_CHUNK_SIZE", ge=1)

    host: str = "127.0.0.1"
    port: int = 32688
    cors_origins: str = ""  # no browser calls this directly; see .env.example

    @field_validator("master_key")
    @classmethod
    def _decodable(cls, v: str) -> str:
        try:
            raw = base64.b64decode(v, validate=True)
        except Exception as exc:  # re-raised with a message a person can act on
            raise ValueError("DKMS_MASTER_KEY is not valid base64") from exc
        if len(raw) < MIN_MASTER_KEY_BYTES:
            raise ValueError(
                f"DKMS_MASTER_KEY must decode to at least {MIN_MASTER_KEY_BYTES} bytes"
            )
        return v

    @model_validator(mode="after")
    def _ring_is_consistent(self) -> Settings:
        """Refuse a key ring the provider could only resolve by guessing.

        An after-validator, because the check needs `key_version` and
        `previous_keys` together. Failing here makes a bad ring a settings
        validation error at startup, before a single value is sealed, rather
        than ciphertext written under the wrong key and found out months later
        when it will not open. See `parse_previous_keys` for what is refused.
        """
        parse_previous_keys(self.previous_keys, active_version=self.key_version)
        return self

    @property
    def master_key_bytes(self) -> bytes:
        return base64.b64decode(self.master_key)

    @property
    def previous_key_bytes(self) -> dict[int, bytes]:
        return parse_previous_keys(self.previous_keys, active_version=self.key_version)

    @property
    def hash_key_bytes(self) -> bytes:
        return self.hash_key.encode()

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def workers(self) -> int:
        return self.pool_workers or min(32, (os.cpu_count() or 4))

    def assert_shippable(self) -> None:
        """Two refusals, both about the same mistake in different clothes."""
        if self.environment in ("local", "test"):
            return
        if self.master_key == DEV_MASTER_KEY:
            raise RuntimeError(
                "refusing to start: DKMS_MASTER_KEY is the key from .env.example. "
                "Everything encrypted under it is readable by anyone with this "
                "repository."
            )
        if self.hash_key == DEV_HASH_KEY or len(self.hash_key) < 32:
            raise RuntimeError(
                "refusing to start: DKMS_HASH_KEY is the key from .env.example, or is "
                "too short. Every hash computed under it can be recomputed by anyone "
                "with this repository, which is the whole protection a blind index has."
            )
        if "*" in self.origins:
            raise RuntimeError("refusing to start: CORS_ORIGINS is a wildcard")


@lru_cache
def get_settings() -> Settings:
    return Settings()
