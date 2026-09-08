"""A ticket is a conversation, and it opens with what we already know.

A holder's ticket on a rights request was a single instruction out and a
single return back, and the mail carried neither who the person was nor what
the platform already held from that holder - so every ticket began with the
team asking the Privacy Office for both. Now a ticket opens with a brief the
platform writes for it: the person's identity, and the consents, exports and
assets that name this holder on the platform, with the question being what
they hold *beyond* that. And a ticket is a thread: the holder and the Privacy
Office write to each other on it, every message is kept, and each side is
told when the other has written.

The thread is evidence. It is append-only at the trigger level and the
application role's grant to change it is revoked, like the audit log.

Revision ID: 0017
Revises: 0016
"""

from __future__ import annotations

import os

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

UPGRADE = """
CREATE TABLE rights_ticket_message (
  message_id     serial PRIMARY KEY,
  message_uuid   uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  holder_id      int NOT NULL REFERENCES rights_request_holder(holder_id),
  -- NULL for a message the platform wrote: the brief, the instruction.
  author_user_id int REFERENCES auth_user(id),
  author_side    varchar(10) NOT NULL,
  kind           varchar(20) NOT NULL DEFAULT 'message',
  body           text NOT NULL,
  evidence_ref   text,
  evidence_hash  text,
  created_at     timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ticket_message_side CHECK (author_side IN ('office', 'holder', 'system')),
  CONSTRAINT ticket_message_kind
    CHECK (kind IN ('brief', 'instruction', 'message', 'return', 'escalation'))
);
CREATE INDEX idx_ticket_message_holder ON rights_ticket_message (holder_id, message_id);
CREATE TRIGGER trg_ticket_message_append_only
  BEFORE UPDATE OR DELETE ON rights_ticket_message
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();

ALTER TABLE rights_request_holder
  -- What the platform knew when the ticket was issued: the person, and the
  -- records that name this holder. A snapshot, so the ticket reads the same
  -- later as it did on the day.
  ADD COLUMN brief          jsonb,
  ADD COLUMN office_read_at timestamptz,
  ADD COLUMN holder_read_at timestamptz;
"""

DOWNGRADE = """
ALTER TABLE rights_request_holder
  DROP COLUMN IF EXISTS holder_read_at,
  DROP COLUMN IF EXISTS office_read_at,
  DROP COLUMN IF EXISTS brief;
DROP TABLE IF EXISTS rights_ticket_message;
"""


def _revoke(role: str) -> str:
    return f"""
DO $$
DECLARE r text := {role!r};
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
    RAISE NOTICE 'Role % does not exist; skipping grant hardening', r;
    RETURN;
  END IF;
  EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON TABLE rights_ticket_message FROM %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE)
    op.execute(_revoke(APP_ROLE))


def downgrade() -> None:
    op.execute(DOWNGRADE)
