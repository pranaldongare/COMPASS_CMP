"""Centralised, validated configuration.

Every setting is read once at import time and validated by pydantic. A malformed
environment fails the process at startup rather than at the first request that
happens to touch the bad value.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from cmp.core.permissions import Role

Environment = Literal["local", "test", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="forbid",  # an unknown env var is a typo, not a feature
        case_sensitive=False,
    )

    # ---------------------------------------------------------------- service
    environment: Environment = "local"
    service_name: str = "cmp-api"
    version: str = "0.1.0"
    debug: bool = False
    root_path: str = ""

    # ---------------------------------------------------------------- database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "cmp"
    postgres_user: str = "cmp"
    postgres_password: SecretStr = SecretStr("cmp")
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10
    db_pool_timeout_s: float = 10.0
    db_statement_timeout_ms: int = 15_000
    db_lock_timeout_ms: int = 5_000

    # ---------------------------------------------------------------- redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ---------------------------------------------------------------- security
    secret_key: SecretStr = SecretStr("dev-only-change-me-dev-only-change-me-32")
    session_ttl_s: int = 60 * 60 * 8  # absolute session lifetime
    session_idle_timeout_s: int = 60 * 30  # sliding idle timeout
    cookie_name: str = "cmp_session"
    csrf_cookie_name: str = "cmp_csrf"
    csrf_header_name: str = "X-CSRF-Token"
    cookie_secure: bool = True
    cookie_domain: str | None = None
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # Account protection — R-AUT-03
    login_max_attempts: int = 5
    login_lockout_window_s: int = 60 * 30
    login_lockout_duration_s: int = 60 * 30

    # OTP — public consent flow and data-subject sign-in
    otp_length: int = 6
    otp_ttl_s: int = 60 * 10
    otp_max_verify_attempts: int = 5
    otp_requests_per_contact_per_hour: int = 5
    otp_requests_per_token_per_hour: int = 20

    # How long the code in a staff invitation lasts. Hours, not minutes: nobody
    # is waiting at a code box for this one. The account is provisioned while
    # the administrator has the details to hand, and its owner reads the mail
    # when they next look - which may be after a weekend.
    staff_invite_ttl_h: int = 48

    # MFA — every staff role steps up with a code sent to the account's email.
    # It started as the two roles whose compromise is unbounded, the DPO and the
    # administrator; on 2026-09-06 it became every internal role, because the
    # others can still mint consent links, see consent records and move data.
    # The data subject is not in the list: she has no password to step up from,
    # and her sign-in *is* a one-time code. Derived from the role enum rather
    # than listed, so a role added later is covered on the day it arrives. A
    # deployment may narrow it through MFA_REQUIRED_ROLES, and answers for that.
    mfa_required_roles: Annotated[tuple[str, ...], NoDecode] = tuple(
        role.value for role in Role if role is not Role.DATA_SUBJECT
    )
    mfa_ttl_s: int = 60 * 5
    mfa_max_verify_attempts: int = 5

    #: The data principal's portal, as reached from outside: the base of every
    #: link the platform puts in a message to a person - a nomination's
    #: acceptance link, "withdraw here", "sign in to see your request". Port
    #: 3001 in development; the console is 3000 and has none of those pages,
    #: so a link built on the wrong one is a 404 in somebody's inbox.
    public_base_url: str = "http://localhost:3001"
    #: The staff console's public origin: the base of a link that sends a
    #: member of staff to a ticket or a request. Distinct from the portal above,
    #: which is where data principals and nominees go.
    console_base_url: str = "http://localhost:3000"

    # ---------------------------------------------------------------- CORS
    cors_origins: Annotated[tuple[str, ...], NoDecode] = ("http://localhost:3000",)
    trusted_hosts: Annotated[tuple[str, ...], NoDecode] = ("*",)

    # ---------------------------------------------------------------- DKMS
    #
    # The key service. A separate process holding the key that makes this
    # database readable, so that a compromise of the API is not both.
    dkms_url: str = "http://localhost:32688"
    dkms_timeout_s: float = 5.0
    #: Records per call. The service refuses past DKMS_MAX_RECORDS; staying
    #: well under it keeps one slow batch from holding a connection open.
    dkms_batch_size: int = 500
    #: Switchable for a development database of plaintext rows, and for the
    #: tests that are about something else. Refused in production below: a
    #: deployment that silently stores plaintext is the exact failure the
    #: service exists to prevent.
    dkms_enabled: bool = False

    #: Development only: show each one-time code the console transports write
    #: in a popup on the portal that asked for it, so signing in does not mean
    #: reading `var/outbox.log` - which, on a phone or a second machine opened
    #: by IP, is not something the person at the screen can do. Off unless
    #: asked for, honoured only where the console transports are in use, and
    #: refused outright outside local and test: shown on the screen that asks
    #: for it, a code proves nothing about who is holding the phone.
    dev_show_codes: bool = False
    #: The key the blind indexes are computed under. Separate from SECRET_KEY on
    #: purpose: rotating the session secret must not change every index, and
    #: the index key never leaves this process. 32+ bytes.
    blind_index_key: SecretStr = SecretStr("dev-only-blind-index-key-32-bytes-long!")

    # ---------------------------------------------------------------- uploads
    max_upload_bytes: int = 25 * 1024 * 1024  # 25 MB — approval proof, import manifest
    upload_root: str = "./var/uploads"
    allowed_proof_mime: Annotated[tuple[str, ...], NoDecode] = (
        "application/pdf",
        "image/png",
        "image/jpeg",
    )
    allowed_manifest_mime: Annotated[tuple[str, ...], NoDecode] = (
        "text/csv",
        "application/json",
        "application/vnd.ms-excel",
        "text/plain",
    )

    # ---------------------------------------------------------------- limits
    default_page_size: int = 50
    max_page_size: int = 200
    public_link_rate_per_minute: int = 60

    # ------------------------------------------------------------------ rights
    # "D" - the response period we publish for a rights request, in days. Rule
    # 14 sets an outer limit of ninety days and requires the period to be
    # published, so ninety is the default and the value here is what the rights
    # page and every acknowledgement state. Copied onto each request at receipt,
    # so changing it does not move a clock already running.
    rights_response_period_days: int = 90
    # Grievances may run on a different period from requests. Same default.
    grievance_response_period_days: int = 90
    # The relative checkpoints on the clock: acknowledge, ticket the holders,
    # and stop collecting to collate - as days after receipt, and before D.
    rights_acknowledge_within_days: int = 2
    rights_tickets_within_days: int = 5
    rights_collate_before_days: int = 5
    # How long a released response stays downloadable from her dashboard.
    rights_download_ttl_days: int = 30
    # A request from the public form whose contact never verified is closed as
    # unverified after this many days, and audited. The neutral reply she got
    # said nothing either way; this is where the record says so too.
    rights_unverified_close_days: int = 7
    # How long a nominee has to accept a nomination before the link lapses.
    nomination_accept_ttl_days: int = 30

    # ---------------------------------------------------------------- external
    #: How the organisation names itself in messages ({organisation}).
    organisation_name: str = "COMPASS"
    notification_email_from: str = "privacy@example.org"
    external_http_timeout_s: float = 10.0  # never infinite — checklist §13
    external_http_retries: int = 3

    # ------------------------------------------------------------- transports
    # Which adapter each seam in `cmp.infrastructure` uses. All three default to
    # the local, non-delivering option on purpose: a misconfigured staging box
    # that quietly writes to a file is a far better failure than one that starts
    # emailing and texting real people the first time somebody signs in.
    email_transport: Literal["console", "smtp", "null"] = "console"
    sms_transport: Literal["console", "http", "null"] = "console"
    storage_backend: Literal["local", "object"] = "local"

    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_use_tls: bool = True

    # The HTTP SMS transport: a JSON POST to a gateway of the deployment's
    # choosing, authenticated with a bearer token. Provider-specific shapes
    # (Twilio, MSG91, ...) are a thin adapter service in front of this, so the
    # platform carries no provider SDK and no provider credentials.
    sms_http_url: str = ""
    sms_http_token: SecretStr = SecretStr("")
    sms_http_sender: str = ""

    # Object storage. The reference recorded in the database stays relative, so
    # bucket and region live here and never reach a table that gets exported.
    storage_bucket: str = ""
    storage_prefix: str = ""
    storage_region: str | None = None

    # ---------------------------------------------------------------- logging
    log_level: str = "INFO"
    log_json: bool = True

    @field_validator(
        "cors_origins",
        "trusted_hosts",
        "mfa_required_roles",
        "allowed_proof_mime",
        "allowed_manifest_mime",
        mode="before",
    )
    @classmethod
    def _split_csv(cls, v: object) -> object:
        """Accept `a,b,c` from the environment.

        These fields are annotated `NoDecode` so pydantic-settings hands us the
        raw string instead of trying to JSON-parse it first. Without that, a
        perfectly ordinary `CORS_ORIGINS=http://a,http://b` in a .env file fails
        at startup with a JSON decoding error that names neither the field nor
        the cause.
        """
        if isinstance(v, str):
            return tuple(part.strip() for part in v.split(",") if part.strip())
        return v

    @model_validator(mode="after")
    def _production_guards(self) -> Settings:
        """Refuse to boot production with development defaults."""
        if self.environment == "production":
            weak = self.secret_key.get_secret_value()
            if weak.startswith("dev-only") or len(weak) < 32:
                raise ValueError("SECRET_KEY must be a real 32+ byte secret in production")
            if self.postgres_password.get_secret_value() in {"cmp", "postgres", ""}:
                raise ValueError("POSTGRES_PASSWORD must not be a default in production")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production")
            if self.debug:
                raise ValueError("DEBUG must be false in production")
            if "*" in self.cors_origins:
                raise ValueError("CORS_ORIGINS must be explicit in production")
            # A transport that does not deliver is a sign-in nobody can
            # complete. In production the choice has to be explicit and real.
            if self.email_transport != "smtp":
                raise ValueError("EMAIL_TRANSPORT must be smtp in production")
            if self.sms_transport != "http":
                raise ValueError("SMS_TRANSPORT must be http in production")
            # The switch exists for a development database of plaintext rows.
            # Off in production means personal data written in the clear, with
            # nothing in the system ever reporting it - which is the failure
            # the key service exists to prevent.
            if not self.dkms_enabled:
                raise ValueError("DKMS_ENABLED must be true in production")
            bik = self.blind_index_key.get_secret_value()
            if bik.startswith("dev-only") or len(bik) < 32:
                raise ValueError("BLIND_INDEX_KEY must be a real 32+ byte secret in production")
        if self.dev_show_codes and self.environment not in ("local", "test"):
            # Not production-only: a staging deployment real people sign in
            # to must not print their codes on the screen either.
            raise ValueError("DEV_SHOW_CODES is for local development only")
        if self.sms_transport == "http" and not self.sms_http_url.startswith("https://"):
            raise ValueError("SMS_HTTP_URL must be an https:// gateway when SMS_TRANSPORT=http")
        return self

    @property
    def dsn(self) -> str:
        pwd = self.postgres_password.get_secret_value()
        return (
            f"postgresql://{self.postgres_user}:{pwd}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings: Annotated[Settings, "process-wide singleton"] = get_settings()
