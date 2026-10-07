"""Files a data principal attaches to her request (2026-10-07).

A request often rests on a document - an ID card, a letter, a screenshot of
what she was sent. She attached nothing: the platform had no way to, so it
went by email, beside a record that could not point at it.
`rights_request_attachment` keeps each file with its request: stored through
the storage seam with its hash, its size, its type and the name it came with
(sealed), and who added it and when.

Kept as it came: rows are append-only by trigger and grant, and a file is
never replaced or removed. Erasure of the person reaches these files through
the request they belong to, like the rest of it.

Revision ID: 0043
Revises: 0042
"""

from __future__ import annotations

import os

from alembic import op

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

UPGRADE = """
CREATE TABLE rights_request_attachment (
  attachment_id   serial PRIMARY KEY,
  attachment_uuid uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  request_id      int NOT NULL REFERENCES rights_request(request_id),
  file_name       text NOT NULL,
  storage_ref     text NOT NULL,
  sha256          char(64) NOT NULL,
  size_bytes      int NOT NULL,
  content_type    varchar(120) NOT NULL,
  added_by        int NOT NULL REFERENCES auth_user(id),
  added_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT rights_request_attachment_size CHECK (size_bytes > 0)
);
COMMENT ON TABLE rights_request_attachment IS
  'A file the data principal attached to her request. Append-only; never replaced or removed';
COMMENT ON COLUMN rights_request_attachment.file_name IS 'The name it was uploaded with. Sealed (FILE_NAME)';
COMMENT ON COLUMN rights_request_attachment.sha256 IS 'The hash of the file as uploaded; a download carries it beside the hash of what was read';
CREATE INDEX idx_rights_request_attachment ON rights_request_attachment (request_id, attachment_id);
CREATE TRIGGER trg_rights_request_attachment_append_only
  BEFORE UPDATE OR DELETE ON rights_request_attachment
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();
"""

DOWNGRADE = """
DROP TABLE IF EXISTS rights_request_attachment;
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
  EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON TABLE rights_request_attachment FROM %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE)
    op.execute(_harden(APP_ROLE))


def downgrade() -> None:
    op.execute(DOWNGRADE)
