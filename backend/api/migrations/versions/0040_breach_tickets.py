"""Breach tickets: the DPO asks the people who must act, and they answer (S3-08).

A breach is handled by people the register did not reach: whoever runs the
system that leaked, whoever holds the log, whoever can confirm a deletion. The
DPO asked them by email and recorded nothing. Rights requests solved the same
problem with tickets (0013, 0017, 0020); a breach now has its own, on the same
model (ADR 0023, BD-03).

`breach_ticket` is one per person per breach (BD-14): who holds it, who assigned
it, what it opened with (the DPO's instruction, or - S3-09 - the note of the
colleague who added them; sealed), an optional answer-by date (BD-20), and the
two read markers - the only columns that ever change.

`breach_ticket_event` is what happens to a ticket afterwards, append-only: the
holder returns it (with an outcome and a sealed summary), the DPO sends it back,
closes it, withdraws it or reopens it (each but close with a sealed reason).
A ticket's state is read by folding its events, like a duty's.

`breach_ticket_message` is the thread, shaped like `rights_ticket_message`:
both sides write, a file may go with a message, and nothing written is changed
or removed.

Revision ID: 0040
Revises: 0039
"""

from __future__ import annotations

import os

from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

UPGRADE = """
CREATE TABLE breach_ticket (
  ticket_id        serial PRIMARY KEY,
  ticket_uuid      uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  breach_id        int NOT NULL REFERENCES breach(breach_id),
  holder_user_id   int NOT NULL REFERENCES auth_user(id),
  assigned_by      int NOT NULL REFERENCES auth_user(id),
  -- The ticket of the holder who added this one as a colleague (S3-09).
  parent_ticket_id int REFERENCES breach_ticket(ticket_id),
  instruction      text NOT NULL,
  answer_by        date,
  created_at       timestamptz NOT NULL DEFAULT now(),
  office_read_at   timestamptz,
  holder_read_at   timestamptz,
  CONSTRAINT breach_ticket_once UNIQUE (breach_id, holder_user_id)
);
COMMENT ON TABLE breach_ticket IS
  'A breach ticket: one person asked to act on one breach (S3-08, ADR 0023). Only the read markers change';
COMMENT ON COLUMN breach_ticket.instruction IS
  'What the ticket opened with: the DPO''s instruction, or the adding colleague''s note. Sealed (FREE_TEXT)';
COMMENT ON COLUMN breach_ticket.answer_by IS
  'Optional date the holder is asked to answer by (BD-20). Shown to both sides; counted on the DPO''s dashboard';
CREATE INDEX idx_breach_ticket_holder ON breach_ticket (holder_user_id);

-- Who, on which breach, opening with what: written once. The read markers
-- are the only thing that moves, and nothing is deleted.
CREATE OR REPLACE FUNCTION cmp_breach_ticket_read_only() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'breach tickets are never deleted' USING ERRCODE = 'restrict_violation';
  END IF;
  IF NEW.ticket_id IS DISTINCT FROM OLD.ticket_id
     OR NEW.ticket_uuid IS DISTINCT FROM OLD.ticket_uuid
     OR NEW.breach_id IS DISTINCT FROM OLD.breach_id
     OR NEW.holder_user_id IS DISTINCT FROM OLD.holder_user_id
     OR NEW.assigned_by IS DISTINCT FROM OLD.assigned_by
     OR NEW.parent_ticket_id IS DISTINCT FROM OLD.parent_ticket_id
     OR NEW.instruction IS DISTINCT FROM OLD.instruction
     OR NEW.answer_by IS DISTINCT FROM OLD.answer_by
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'only the read markers of a breach ticket may change'
      USING ERRCODE = 'restrict_violation';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_breach_ticket_read_only
  BEFORE UPDATE OR DELETE ON breach_ticket
  FOR EACH ROW EXECUTE FUNCTION cmp_breach_ticket_read_only();

CREATE TABLE breach_ticket_event (
  event_id      serial PRIMARY KEY,
  event_uuid    uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  ticket_id     int NOT NULL REFERENCES breach_ticket(ticket_id),
  kind          varchar(12) NOT NULL,
  outcome       varchar(8),
  summary       text,
  reason        text,
  actor_user_id int NOT NULL REFERENCES auth_user(id),
  occurred_at   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT breach_ticket_event_kind
    CHECK (kind IN ('returned', 'sent_back', 'closed', 'withdrawn', 'reopened')),
  -- What the holder says it did, with a return and only with one.
  CONSTRAINT breach_ticket_event_outcome
    CHECK ((kind = 'returned') = (outcome IS NOT NULL)
           AND (outcome IS NULL OR outcome IN ('done', 'partial', 'failed'))),
  CONSTRAINT breach_ticket_event_summary CHECK (kind <> 'returned' OR summary IS NOT NULL),
  CONSTRAINT breach_ticket_event_reason
    CHECK (kind NOT IN ('sent_back', 'withdrawn', 'reopened') OR reason IS NOT NULL)
);
COMMENT ON TABLE breach_ticket_event IS
  'What happened to a breach ticket after it was assigned. Append-only; its state is read by folding these';
COMMENT ON COLUMN breach_ticket_event.summary IS 'The holder''s account of what was done, with a return. Sealed (FREE_TEXT)';
COMMENT ON COLUMN breach_ticket_event.reason IS 'Why the DPO sent it back, withdrew or reopened it. Sealed (FREE_TEXT)';
CREATE INDEX idx_breach_ticket_event ON breach_ticket_event (ticket_id, event_id);
CREATE TRIGGER trg_breach_ticket_event_append_only
  BEFORE UPDATE OR DELETE ON breach_ticket_event
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();

CREATE TABLE breach_ticket_message (
  message_id     serial PRIMARY KEY,
  message_uuid   uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  ticket_id      int NOT NULL REFERENCES breach_ticket(ticket_id),
  -- NULL for what the platform wrote.
  author_user_id int REFERENCES auth_user(id),
  author_side    varchar(10) NOT NULL,
  kind           varchar(12) NOT NULL DEFAULT 'message',
  body           text NOT NULL,
  evidence_ref   text,
  evidence_hash  text,
  evidence_name  text,
  created_at     timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT breach_ticket_message_side CHECK (author_side IN ('office', 'holder', 'system')),
  CONSTRAINT breach_ticket_message_kind CHECK (kind IN ('instruction', 'message', 'return', 'status'))
);
COMMENT ON TABLE breach_ticket_message IS
  'A breach ticket''s thread. Append-only by trigger and grant; body and evidence_name sealed';
CREATE INDEX idx_breach_ticket_message ON breach_ticket_message (ticket_id, message_id);
CREATE TRIGGER trg_breach_ticket_message_append_only
  BEFORE UPDATE OR DELETE ON breach_ticket_message
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();
"""

DOWNGRADE = """
DROP TABLE IF EXISTS breach_ticket_message;
DROP TABLE IF EXISTS breach_ticket_event;
DROP TABLE IF EXISTS breach_ticket;
DROP FUNCTION IF EXISTS cmp_breach_ticket_read_only();
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
  EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON TABLE breach_ticket_event,
                  breach_ticket_message FROM %I', r);
  EXECUTE format('REVOKE DELETE, TRUNCATE ON TABLE breach_ticket FROM %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE)
    op.execute(_harden(APP_ROLE))


def downgrade() -> None:
    op.execute(DOWNGRADE)
