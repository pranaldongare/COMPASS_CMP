"""The portal's address, kept by the administrator (2026-11-16).

Every link the platform hands out to a person - a consent link copied in the
console, the public link for reporting a breach, the links in its mail -
starts with the address of the data principal's portal. That address was
configuration (`PUBLIC_BASE_URL`, and `NEXT_PUBLIC_SUBJECT_PORTAL_URL` on the
console), fixed when a process starts. Until the deployment has a domain name
its address is an IP that keeps changing, and every change meant editing two
files and restarting three services, or handing out links that go nowhere.

One table, one row: `portal_address.portal_url`, the address every such link
starts with. NULL - as it is after this migration - means the configured one
is used, so nothing changes until the administrator sets it. It belongs to no
office.

Revision ID: 0072
Revises: 0071
"""

from __future__ import annotations

import os

from alembic import op

revision = "0072"
down_revision = "0071"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

UPGRADE = """
CREATE TABLE portal_address (
  address_id  smallint PRIMARY KEY DEFAULT 1,
  portal_url  text,
  updated_by  int REFERENCES auth_user(id),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT portal_address_one_row CHECK (address_id = 1),
  CONSTRAINT portal_address_is_an_origin
    CHECK (portal_url IS NULL OR portal_url ~ '^https?://[^/?#@[:space:]]+$')
);
COMMENT ON TABLE portal_address IS
  'One row: the address links to the data principal''s portal start with; kept by the administrator';
COMMENT ON COLUMN portal_address.portal_url IS
  'Scheme, host and port, no path; NULL: the configured address (PUBLIC_BASE_URL) is used';
COMMENT ON COLUMN portal_address.updated_by IS 'Who last set it';
COMMENT ON COLUMN portal_address.updated_at IS 'When it was last set';
INSERT INTO portal_address DEFAULT VALUES;
"""

DOWNGRADE = """
DROP TABLE IF EXISTS portal_address;
"""


def _grants(role: str) -> str:
    return f"""
DO $$
DECLARE r text := '{role}';
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN RETURN; END IF;
  EXECUTE format('GRANT SELECT, UPDATE ON TABLE portal_address TO %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE)
    op.execute(_grants(APP_ROLE))


def downgrade() -> None:
    op.execute(DOWNGRADE)
