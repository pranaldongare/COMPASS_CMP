"""Asking the organisation whether an address is an active employee's (2026-11-25).

The organisation offered one call, VerifyEmail:

    POST {address}/VerifyEmail   {"MySingleID": "<email>"}
    200 {"MySingleID": "<email>", "IsActive": true, "Status": true}

It is asked when somebody on one of the organisation's own email domains signs
in: a member of staff on the console, before their code is sent, and a person
on the portal, after their code is entered. See ADR 0046.

* `employee_check_connection` - one row: where VerifyEmail is, the key it asks
  for (encrypted with the application key, never served), whether it is on,
  and whether staff on any other domain may sign in unchecked (on to begin
  with: testing uses addresses such as cmp.local).
* `organisation_domain` - the organisation's own email domains, kept by the
  administrator. One list: it is also what BREACH_TICKET_EMAIL_DOMAINS was -
  who counts as inside the organisation for breach and rights tickets - and
  that setting now only seeds it, here, once.
* `auth_user.employment_status` / `employment_checked_at` - the last answer
  for the account: `active`, `inactive` (left, or not known), or NULL (never
  asked, or the last call failed).

Revision ID: 0075
Revises: 0074
"""

from __future__ import annotations

import os

from alembic import op

revision = "0075"
down_revision = "0074"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

UPGRADE = """
CREATE TABLE employee_check_connection (
  connection_id        smallint PRIMARY KEY DEFAULT 1,
  base_url             text,
  api_key_sealed       bytea,
  api_key_header       text NOT NULL DEFAULT 'X-API-Key',
  enabled              boolean NOT NULL DEFAULT false,
  allow_other_domains  boolean NOT NULL DEFAULT true,
  updated_by           int REFERENCES auth_user(id),
  updated_at           timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT employee_check_connection_one_row CHECK (connection_id = 1),
  CONSTRAINT employee_check_connection_enabled_has_url CHECK (NOT enabled OR base_url IS NOT NULL)
);
COMMENT ON TABLE employee_check_connection IS
  'One row: where VerifyEmail is reached and with what key; kept by the administrator';
COMMENT ON COLUMN employee_check_connection.base_url IS
  'The address /VerifyEmail is appended to; NULL: not set up';
COMMENT ON COLUMN employee_check_connection.api_key_sealed IS
  'The key VerifyEmail asks for, encrypted with the application key; never served';
COMMENT ON COLUMN employee_check_connection.allow_other_domains IS
  'Staff whose email is on none of the organisation''s domains may sign in to the console '
  'unchecked; on for testing, to be switched off before production';
INSERT INTO employee_check_connection DEFAULT VALUES;

CREATE TABLE organisation_domain (
  domain     text PRIMARY KEY,
  added_by   int REFERENCES auth_user(id),
  added_at   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT organisation_domain_lower CHECK (domain = lower(domain)),
  CONSTRAINT organisation_domain_shape CHECK (domain ~ '^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$')
);
COMMENT ON TABLE organisation_domain IS
  'The organisation''s own email domains: who is checked with VerifyEmail, and who counts '
  'as inside the organisation for breach and rights tickets';

ALTER TABLE auth_user
  ADD COLUMN employment_status text,
  ADD COLUMN employment_checked_at timestamptz,
  ADD CONSTRAINT auth_user_employment_status
    CHECK (employment_status IS NULL OR employment_status IN ('active', 'inactive'));
COMMENT ON COLUMN auth_user.employment_status IS
  'What VerifyEmail last said of the account''s company address: active or inactive; '
  'NULL - never asked, or the last call failed';
"""

DOWNGRADE = """
ALTER TABLE auth_user DROP CONSTRAINT IF EXISTS auth_user_employment_status;
ALTER TABLE auth_user DROP COLUMN IF EXISTS employment_checked_at;
ALTER TABLE auth_user DROP COLUMN IF EXISTS employment_status;
DROP TABLE IF EXISTS organisation_domain;
DROP TABLE IF EXISTS employee_check_connection;
"""


def _seed() -> str:
    """The domains BREACH_TICKET_EMAIL_DOMAINS named, the one time: from here on
    the list is the administrator's."""
    raw = os.getenv("BREACH_TICKET_EMAIL_DOMAINS", "cmp.local")
    domains = sorted(
        {d.strip().lower().lstrip("@") for d in raw.replace(";", ",").split(",") if d.strip()}
    )
    rows = [d for d in domains if d.replace(".", "").replace("-", "").isalnum() and "." in d]
    if not rows:
        return ""
    values = ", ".join("('" + d.replace("'", "''") + "')" for d in rows)
    return f"INSERT INTO organisation_domain (domain) VALUES {values} ON CONFLICT DO NOTHING;"


def _grants(role: str) -> str:
    return f"""
DO $$
DECLARE r text := {role!r};
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
    RAISE NOTICE 'Role % does not exist; skipping grants', r;
    RETURN;
  END IF;
  EXECUTE format('GRANT SELECT, UPDATE ON TABLE employee_check_connection TO %I', r);
  EXECUTE format('GRANT SELECT, INSERT, DELETE ON TABLE organisation_domain TO %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE)
    seed = _seed()
    if seed:
        op.execute(seed)
    op.execute(_grants(APP_ROLE))


def downgrade() -> None:
    op.execute(DOWNGRADE)
