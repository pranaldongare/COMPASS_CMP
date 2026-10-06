"""Files attached to an incident: the email, the proof, the chat (2026-10-06).

An incident arrives with what showed it: the email that reported it, a
screenshot, a chat, a log. The DPO kept them in a mailbox, where the register
could not point at them. `breach_attachment` keeps them with the incident,
as evidence: each file stored through the storage seam with its hash, its
size and the name it was uploaded with (sealed), what kind of thing it is,
and an optional note (sealed) - who added it and when.

Evidence is never edited: rows are append-only by trigger and grant, and a
file is never replaced or removed. A file attached in error stays, with
another beside it; the trail says who added each.

Revision ID: 0042
Revises: 0041
"""

from __future__ import annotations

import os

from alembic import op

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

UPGRADE = """
CREATE TABLE breach_attachment (
  attachment_id   serial PRIMARY KEY,
  attachment_uuid uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  breach_id       int NOT NULL REFERENCES breach(breach_id),
  kind            varchar(8) NOT NULL,
  note            text,
  file_name       text NOT NULL,
  storage_ref     text NOT NULL,
  sha256          char(64) NOT NULL,
  size_bytes      int NOT NULL,
  content_type    varchar(120) NOT NULL,
  added_by        int NOT NULL REFERENCES auth_user(id),
  added_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT breach_attachment_kind CHECK (kind IN ('email', 'proof', 'chat', 'other')),
  CONSTRAINT breach_attachment_size CHECK (size_bytes > 0)
);
COMMENT ON TABLE breach_attachment IS
  'A file kept with an incident as evidence: an email, a proof, a chat. Append-only; never replaced or removed';
COMMENT ON COLUMN breach_attachment.file_name IS 'The name it was uploaded with. Sealed (FILE_NAME)';
COMMENT ON COLUMN breach_attachment.note IS 'What it is, in a few words. Optional; sealed (FREE_TEXT)';
COMMENT ON COLUMN breach_attachment.sha256 IS 'The hash of the file as uploaded; a download carries it beside the hash of what was read';
CREATE INDEX idx_breach_attachment ON breach_attachment (breach_id, attachment_id);
CREATE TRIGGER trg_breach_attachment_append_only
  BEFORE UPDATE OR DELETE ON breach_attachment
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();
"""

DOWNGRADE = """
DROP TABLE IF EXISTS breach_attachment;
"""


def _harden(role: str) -> str:
    return f"""
DO $$
DECLARE r text := {role!r};
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
    RAISE NOTICE 'Role % does not exist; skipping grant hardening', r;
    RETURN;
  END IF;
  EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON TABLE breach_attachment FROM %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE)
    op.execute(_harden(APP_ROLE))


def downgrade() -> None:
    op.execute(DOWNGRADE)
