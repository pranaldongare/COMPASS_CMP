"""The words of a message, as the office chose them.

Every message the platform sends has a default subject and body in the code
(`cmp.core.messages`). This table holds what the administrator or the DPO put
in their place: one row per (junction, channel), present only where the
default was replaced. Absence means the default. Deleting a row is "reset to
default", so the table is mutable on purpose and is not evidence; the audit
trail records who changed which message and when.

Revision ID: 0024
Revises: 0023
"""

from __future__ import annotations

import os

from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

UPGRADE = """
CREATE TABLE message_template (
  template_id  serial PRIMARY KEY,
  key          varchar(64) NOT NULL,
  channel      varchar(8)  NOT NULL,
  -- NULL for an SMS, which has no subject.
  subject      text,
  body         text NOT NULL,
  updated_by   int REFERENCES auth_user(id),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT message_template_channel CHECK (channel IN ('email', 'sms')),
  CONSTRAINT message_template_one_per_channel UNIQUE (key, channel),
  CONSTRAINT message_template_body_present CHECK (length(btrim(body)) > 0)
);
COMMENT ON TABLE message_template IS
  'Subject and body an administrator or the DPO set for one message junction and channel; absent means the code default';
"""

DOWNGRADE = """
DROP TABLE IF EXISTS message_template;
"""


def _grant(role: str) -> str:
    return f"""
DO $$
DECLARE r text := {role!r};
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
    RAISE NOTICE 'Role % does not exist; skipping grants', r;
    RETURN;
  END IF;
  EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE message_template TO %I', r);
  EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE message_template_template_id_seq TO %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE)
    op.execute(_grant(APP_ROLE))


def downgrade() -> None:
    op.execute(DOWNGRADE)
