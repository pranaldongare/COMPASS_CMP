"""Notices to the people a breach touched, and the account of each (S3-03).

Rule 7(1) prescribes what every affected principal is told - what happened,
the consequences likely for her, what has been and is being done, what she can
do, and whom to ask - through her user account and the contact she registered.
Rule 7(2)(b)(vi) then asks the Board's report for an account of those notices.

`breach_notice` is a version of the words. A draft may be edited; approval
freezes it (`cmp_breach_notice_frozen`), and it cannot be approved with any of
the five contents empty (`breach_notice_complete`). One draft per breach at a
time. An updated notice, when the facts change, is a new version.

`breach_notice_delivery` is the account: one row per state per attempt per
channel per person per version - queued, delivered or failed, and why, never
the address. Append-only. `breach_notice_delivery_once` makes a resend
idempotent: two sends at once cannot both queue the same attempt, and a
worker that records the same outcome twice records it once.

The words are sealed, like every narrative the office writes about a breach:
they repeat the assessment, which is, and a draft may name somebody before it
is corrected. A word not yet written is NULL, so the completeness check still
reads through the ciphertext.

Revision ID: 0036
Revises: 0035
"""

from __future__ import annotations

import os

from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

UPGRADE = """
CREATE TABLE breach_notice (
  notice_id         serial PRIMARY KEY,
  notice_uuid       uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  breach_id         int NOT NULL REFERENCES breach(breach_id),
  version           int NOT NULL,
  -- Rule 7(1)(a) to (e).
  what_happened     text,
  consequences      text,
  measures          text,
  protective_steps  text,
  contact           text,
  created_by        int NOT NULL REFERENCES auth_user(id),
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  approved_by       int REFERENCES auth_user(id),
  approved_at       timestamptz,
  CONSTRAINT breach_notice_version UNIQUE (breach_id, version),
  CONSTRAINT breach_notice_approval_attributed CHECK ((approved_at IS NULL) = (approved_by IS NULL)),
  CONSTRAINT breach_notice_complete CHECK (
    approved_at IS NULL OR (
      what_happened IS NOT NULL AND consequences IS NOT NULL AND measures IS NOT NULL
      AND protective_steps IS NOT NULL AND contact IS NOT NULL
    )
  )
);
CREATE UNIQUE INDEX uq_breach_notice_one_draft ON breach_notice (breach_id) WHERE approved_at IS NULL;
COMMENT ON TABLE breach_notice IS
  'A version of the words sent to the people a breach touched (Rule 7(1)). Frozen once approved';

-- A draft is the office's to edit; an approved notice is what people were
-- sent, and does not change. A correction is a new version.
CREATE OR REPLACE FUNCTION cmp_breach_notice_frozen() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'breach notices are never deleted' USING ERRCODE = 'restrict_violation';
  END IF;
  IF OLD.approved_at IS NOT NULL THEN
    RAISE EXCEPTION 'an approved breach notice does not change; write a new version'
      USING ERRCODE = 'restrict_violation';
  END IF;
  IF NEW.notice_id IS DISTINCT FROM OLD.notice_id
     OR NEW.notice_uuid IS DISTINCT FROM OLD.notice_uuid
     OR NEW.breach_id IS DISTINCT FROM OLD.breach_id
     OR NEW.version IS DISTINCT FROM OLD.version
     OR NEW.created_by IS DISTINCT FROM OLD.created_by
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'only the words and the approval of a draft may change'
      USING ERRCODE = 'restrict_violation';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_breach_notice_frozen
  BEFORE UPDATE OR DELETE ON breach_notice
  FOR EACH ROW EXECUTE FUNCTION cmp_breach_notice_frozen();

CREATE TABLE breach_notice_delivery (
  delivery_id    serial PRIMARY KEY,
  delivery_uuid  uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  notice_id      int NOT NULL REFERENCES breach_notice(notice_id),
  auth_user_id   int NOT NULL REFERENCES auth_user(id),
  channel        varchar(8) NOT NULL,
  attempt        int NOT NULL,
  status         varchar(10) NOT NULL,
  -- Why a delivery failed, as an error class and a count. Never an address.
  detail         jsonb NOT NULL DEFAULT '{}'::jsonb,
  recorded_at    timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT breach_notice_delivery_channel CHECK (channel IN ('portal', 'email', 'sms')),
  CONSTRAINT breach_notice_delivery_status CHECK (status IN ('queued', 'delivered', 'failed')),
  CONSTRAINT breach_notice_delivery_attempt CHECK (attempt >= 1),
  -- Her account is written to in the same transaction as the send: it is
  -- delivered or it is not there.
  CONSTRAINT breach_notice_delivery_portal_at_once CHECK (channel <> 'portal' OR status = 'delivered'),
  CONSTRAINT breach_notice_delivery_once UNIQUE (notice_id, auth_user_id, channel, attempt, status)
);
CREATE INDEX idx_breach_notice_delivery_person ON breach_notice_delivery (auth_user_id);
COMMENT ON TABLE breach_notice_delivery IS
  'The account of notices to principals, per version, person and channel (Rule 7(2)(b)(vi))';
CREATE TRIGGER trg_breach_notice_delivery_append_only
  BEFORE UPDATE OR DELETE ON breach_notice_delivery
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();
"""

DOWNGRADE = """
DROP TABLE IF EXISTS breach_notice_delivery;
DROP TABLE IF EXISTS breach_notice;
DROP FUNCTION IF EXISTS cmp_breach_notice_frozen();
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
  EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON TABLE breach_notice_delivery FROM %I', r);
  EXECUTE format('REVOKE DELETE, TRUNCATE ON TABLE breach_notice FROM %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE)
    op.execute(_harden(APP_ROLE))


def downgrade() -> None:
    op.execute(DOWNGRADE)
