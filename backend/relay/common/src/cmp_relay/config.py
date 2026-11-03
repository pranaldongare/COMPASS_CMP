"""The settings both sides read, and the rules every setting is read by.

Every setting comes from the environment and is checked once at start. A setting
that is missing or malformed stops the process with a sentence saying which,
rather than failing on the first request. Each side's own settings are in its
own module - `bridge_config` on AWS, `collector_config` inside - and its own
`.env.example` (`bridge/`, `collector/`) lists them all, these included.

Shared by both sides:

    RELAY_ENVIRONMENT          local | staging | production (default production)
    RELAY_REGION               AWS region (default ap-south-1)
    RELAY_ENDPOINT_URL         local emulator only (moto, LocalStack); unset on AWS
    RELAY_REQUEST_QUEUE_URL    the request queue
    RELAY_BUCKET               the bucket for bodies too large for a message
    RELAY_COOKIE_NAMES         cookies that may cross (cmp_session,cmp_csrf,cmp_ticket,
                               cmp_sso_pending)
    RELAY_CSRF_HEADER          the CSRF header's name (X-CSRF-Token)
    RELAY_ALLOW_DEV_ROUTES     true only with RELAY_ENVIRONMENT=local: /dev/codes,
                               /dev/seed-accounts and the SSO stand-in's /dev/sso/*

AWS credentials come from the standard chain: an instance profile for the
bridge on EC2; IAM Roles Anywhere (`credential_process`) for the collector;
any dummy pair against the local emulator.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

ENVIRONMENTS = ("local", "test", "staging", "production")


class ConfigError(ValueError):
    """A setting that is missing or wrong. The message names it."""


def get_str(env: Mapping[str, str], name: str, default: str | None = None) -> str:
    value = env.get(name, default)
    if value is None or not str(value).strip():
        raise ConfigError(f"{name} is required")
    return str(value).strip()


def get_opt(env: Mapping[str, str], name: str) -> str | None:
    value = env.get(name)
    return value.strip() if value and value.strip() else None


def get_float(env: Mapping[str, str], name: str, default: float, low: float, high: float) -> float:
    raw = env.get(name)
    try:
        value = float(raw) if raw not in (None, "") else default
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number") from exc
    if not low <= value <= high:
        raise ConfigError(f"{name} must be between {low} and {high}")
    return value


def get_int(env: Mapping[str, str], name: str, default: int, low: int, high: int) -> int:
    return int(get_float(env, name, default, low, high))


def get_bool(env: Mapping[str, str], name: str) -> bool:
    return env.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def get_list(env: Mapping[str, str], name: str, default: str = "") -> tuple[str, ...]:
    raw = env.get(name, default)
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def read_secret_file(env: Mapping[str, str], name: str, required: bool = True) -> str | None:
    path = get_opt(env, name)
    if path is None:
        if required:
            raise ConfigError(f"{name} is required")
        return None
    file = Path(path)
    if not file.is_file():
        raise ConfigError(f"{name} names {path}, which is not a readable file")
    value = file.read_text().strip()
    if not value:
        raise ConfigError(f"{name} names an empty file")
    return value


@dataclass(frozen=True)
class Common:
    environment: str
    region: str
    endpoint_url: str | None
    request_queue_url: str
    bucket: str
    cookie_names: frozenset[str]
    csrf_header: str
    allow_dev_routes: bool

    @property
    def is_local(self) -> bool:
        return self.environment in ("local", "test")


def common_settings(env: Mapping[str, str]) -> Common:
    environment = get_str(env, "RELAY_ENVIRONMENT", "production").lower()
    if environment not in ENVIRONMENTS:
        raise ConfigError(f"RELAY_ENVIRONMENT must be one of {', '.join(ENVIRONMENTS)}")
    endpoint_url = get_opt(env, "RELAY_ENDPOINT_URL")
    if endpoint_url and environment not in ("local", "test"):
        raise ConfigError("RELAY_ENDPOINT_URL is for a local emulator only")
    allow_dev = get_bool(env, "RELAY_ALLOW_DEV_ROUTES")
    if allow_dev and environment not in ("local", "test"):
        raise ConfigError("RELAY_ALLOW_DEV_ROUTES is for local development only")
    return Common(
        environment=environment,
        region=get_str(env, "RELAY_REGION", "ap-south-1"),
        endpoint_url=endpoint_url,
        request_queue_url=get_str(env, "RELAY_REQUEST_QUEUE_URL"),
        bucket=get_str(env, "RELAY_BUCKET"),
        cookie_names=frozenset(
            get_list(env, "RELAY_COOKIE_NAMES", "cmp_session,cmp_csrf,cmp_ticket,cmp_sso_pending")
        ),
        csrf_header=get_str(env, "RELAY_CSRF_HEADER", "X-CSRF-Token"),
        allow_dev_routes=allow_dev,
    )
