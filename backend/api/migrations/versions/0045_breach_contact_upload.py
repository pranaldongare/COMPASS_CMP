"""Who a breach touched, from a list somebody sends us (2026-10-07).

A breach could only list people the platform already had an account for,
derived from its records or picked by hand, and the principals' duty
completes only when everyone listed has been sent the notice - so a breach
whose people are not on the platform could never be closed. In practice the
list arrives from outside: a processor or a team sends the people affected,
by name, email and mobile; or sends the IDs of the assets affected, and the
people are read from those.

* `breach_upload` - one row per file taken: its kind (`contacts` or
  `assets`), its sealed name and hash, and what it came to: rows read, people
  on the platform it matched, contacts it added, rows already listed or
  repeated, rows that could not be read, and - for assets - subjects in them
  who cannot be traced. The file itself is not kept: it is a list of contacts
  in the clear, and the contacts that matter are now sealed in the rows.
* `breach_contact` - a person the list names who has no account: name,
  email and mobile, sealed, with blind indexes so one contact is listed once
  per breach. Only ever added to, like the list of accounts.
* `breach_affected.found_by` gains `upload`: a person with an account whom an
  uploaded list matched.
* `breach_notice_delivery` addresses an account or a contact, exactly one;
  a contact is never written to an account (`portal`). Its once-only rule now
  counts a missing account or contact as a value (NULLS NOT DISTINCT), so a
  contact's attempt is recorded once, as an account's always was.

Revision ID: 0045
Revises: 0044
"""

from __future__ import annotations

import os

from alembic import op

revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

UPGRADE = """
CREATE TABLE breach_upload (
  upload_id      serial PRIMARY KEY,
  upload_uuid    uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  breach_id      int NOT NULL REFERENCES breach(breach_id),
  kind           varchar(10) NOT NULL,
  file_name      text NOT NULL,
  sha256         char(64) NOT NULL,
  rows_read      int NOT NULL,
  matched_people int NOT NULL,
  new_contacts   int NOT NULL,
  already_listed int NOT NULL,
  unreadable     int NOT NULL,
  untraceable    int NOT NULL DEFAULT 0,
  added_by       int NOT NULL REFERENCES auth_user(id),
  added_at       timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT breach_upload_kind CHECK (kind IN ('contacts', 'assets')),
  CONSTRAINT breach_upload_counts CHECK (
    rows_read >= 0 AND matched_people >= 0 AND new_contacts >= 0
    AND already_listed >= 0 AND unreadable >= 0 AND untraceable >= 0)
);
COMMENT ON TABLE breach_upload IS
  'A list of the people a breach touched, or of its assets, as sent to us. The file is not kept';
COMMENT ON COLUMN breach_upload.file_name IS 'The name it was uploaded with. Sealed (FILE_NAME)';
CREATE INDEX idx_breach_upload ON breach_upload (breach_id, upload_id);
CREATE TRIGGER trg_breach_upload_append_only
  BEFORE UPDATE OR DELETE ON breach_upload
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();

CREATE TABLE breach_contact (
  contact_id    serial PRIMARY KEY,
  contact_uuid  uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  breach_id     int NOT NULL REFERENCES breach(breach_id),
  upload_id     int NOT NULL REFERENCES breach_upload(upload_id),
  full_name     text,
  email         text,
  mobile        text,
  email_hash    text,
  mobile_hash   text,
  added_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT breach_contact_reachable CHECK (email IS NOT NULL OR mobile IS NOT NULL),
  CONSTRAINT breach_contact_email_once UNIQUE (breach_id, email_hash),
  CONSTRAINT breach_contact_mobile_once UNIQUE (breach_id, mobile_hash)
);
COMMENT ON TABLE breach_contact IS
  'Somebody a breach touched who has no account, from an uploaded list. Only ever added to';
COMMENT ON COLUMN breach_contact.full_name IS 'Sealed (NAME)';
COMMENT ON COLUMN breach_contact.email IS 'Sealed (EMAIL); email_hash is its blind index';
COMMENT ON COLUMN breach_contact.mobile IS 'Sealed (MOBILE); mobile_hash is its blind index';
CREATE INDEX idx_breach_contact ON breach_contact (breach_id, contact_id);
CREATE TRIGGER trg_breach_contact_append_only
  BEFORE UPDATE OR DELETE ON breach_contact
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();

ALTER TABLE breach_affected DROP CONSTRAINT breach_affected_found_by;
ALTER TABLE breach_affected ADD CONSTRAINT breach_affected_found_by
  CHECK (found_by IN ('processor', 'data_source', 'platform', 'dpo', 'upload'));

ALTER TABLE breach_notice_delivery ALTER COLUMN auth_user_id DROP NOT NULL;
ALTER TABLE breach_notice_delivery
  ADD COLUMN contact_id int REFERENCES breach_contact(contact_id);
ALTER TABLE breach_notice_delivery ADD CONSTRAINT breach_notice_delivery_one_recipient
  CHECK (num_nonnulls(auth_user_id, contact_id) = 1);
ALTER TABLE breach_notice_delivery ADD CONSTRAINT breach_notice_delivery_portal_is_an_account
  CHECK (channel <> 'portal' OR auth_user_id IS NOT NULL);
ALTER TABLE breach_notice_delivery DROP CONSTRAINT breach_notice_delivery_once;
ALTER TABLE breach_notice_delivery ADD CONSTRAINT breach_notice_delivery_once
  UNIQUE NULLS NOT DISTINCT (notice_id, auth_user_id, contact_id, channel, attempt, status);
CREATE INDEX idx_breach_notice_delivery_contact ON breach_notice_delivery (contact_id)
  WHERE contact_id IS NOT NULL;
"""

DOWNGRADE = """
ALTER TABLE breach_notice_delivery DISABLE TRIGGER trg_breach_notice_delivery_append_only;
DELETE FROM breach_notice_delivery WHERE contact_id IS NOT NULL;
ALTER TABLE breach_notice_delivery ENABLE TRIGGER trg_breach_notice_delivery_append_only;
DROP INDEX IF EXISTS idx_breach_notice_delivery_contact;
ALTER TABLE breach_notice_delivery DROP CONSTRAINT breach_notice_delivery_once;
ALTER TABLE breach_notice_delivery ADD CONSTRAINT breach_notice_delivery_once
  UNIQUE (notice_id, auth_user_id, channel, attempt, status);
ALTER TABLE breach_notice_delivery DROP CONSTRAINT breach_notice_delivery_portal_is_an_account;
ALTER TABLE breach_notice_delivery DROP CONSTRAINT breach_notice_delivery_one_recipient;
ALTER TABLE breach_notice_delivery DROP COLUMN contact_id;
ALTER TABLE breach_notice_delivery ALTER COLUMN auth_user_id SET NOT NULL;

ALTER TABLE breach_affected DISABLE TRIGGER trg_breach_affected_append_only;
DELETE FROM breach_affected WHERE found_by = 'upload';
ALTER TABLE breach_affected ENABLE TRIGGER trg_breach_affected_append_only;
ALTER TABLE breach_affected DROP CONSTRAINT breach_affected_found_by;
ALTER TABLE breach_affected ADD CONSTRAINT breach_affected_found_by
  CHECK (found_by IN ('processor', 'data_source', 'platform', 'dpo'));

DROP TABLE IF EXISTS breach_contact;
DROP TABLE IF EXISTS breach_upload;
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
  EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON TABLE breach_upload FROM %I', r);
  EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON TABLE breach_contact FROM %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE)
    op.execute(_harden(APP_ROLE))


def downgrade() -> None:
    op.execute(DOWNGRADE)
