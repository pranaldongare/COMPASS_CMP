"""Settings, and the two that production refuses to start without."""

from __future__ import annotations

import base64
import json
import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#: The key in `.env.example`. Named here so the startup check can refuse it
#: rather than comparing against a string spelled out in two places.
DEV_MASTER_KEY = "ZGV2LW9ubHktbWFzdGVyLWtleS0zMi1ieXRlcy1sb25nISE="

#: The hashing key, in the clear rather than base64, because the platform
#: holds the same string under `BLIND_INDEX_KEY` and the two must be typed
#: identically into two .env files by a person.
DEV_HASH_KEY = "dev-only-blind-index-key-32-bytes-long!"


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
    key_version: int = Field(1, alias="DKMS_KEY_VERSION", ge=1, le=255)
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
        if len(raw) < 32:
            raise ValueError("DKMS_MASTER_KEY must decode to at least 32 bytes")
        return v

    @property
    def master_key_bytes(self) -> bytes:
        return base64.b64decode(self.master_key)

    @property
    def previous_key_bytes(self) -> dict[int, bytes]:
        parsed = json.loads(self.previous_keys or "{}")
        return {int(k): base64.b64decode(v) for k, v in parsed.items()}

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
