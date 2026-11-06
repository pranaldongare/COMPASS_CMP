"""A breach ticket's date may move, with a reason (2026-11-06).

The date a ticket is to be answered by was fixed when it was assigned, and the
person answering could only miss it. Either side may now change it, saying why.

`breach_ticket.answer_by` stays the one date the lists and the counts read. It
joins the read markers as a column that may change; every change also writes a
`breach_ticket_event` of kind `date_changed`, with the date before, the date
after and the sealed reason, in the same statement as far as the service goes
and by trigger as far as the database goes: the row refuses a new date nothing
recorded.

The kind does not move a ticket's state.

Revision ID: 0061
Revises: 0060
"""

from __future__ import annotations

from alembic import op

revision = "0061"
down_revision = "0060"
branch_labels = None
depends_on = None

UPGRADE = """
ALTER TABLE breach_ticket_event
  ADD COLUMN date_before date,
  ADD COLUMN date_after date;
COMMENT ON COLUMN breach_ticket_event.date_before IS
  'On a date_changed event: the date it replaced, or NULL if there was none';
COMMENT ON COLUMN breach_ticket_event.date_after IS 'On a date_changed event: the new date';

ALTER TABLE breach_ticket_event DROP CONSTRAINT breach_ticket_event_kind;
ALTER TABLE breach_ticket_event ADD CONSTRAINT breach_ticket_event_kind CHECK (
  kind IN ('returned', 'sent_back', 'closed', 'withdrawn', 'reopened', 'date_changed'));
ALTER TABLE breach_ticket_event DROP CONSTRAINT breach_ticket_event_reason;
ALTER TABLE breach_ticket_event ADD CONSTRAINT breach_ticket_event_reason CHECK (
  kind NOT IN ('sent_back', 'withdrawn', 'reopened', 'date_changed') OR reason IS NOT NULL);
ALTER TABLE breach_ticket_event ADD CONSTRAINT breach_ticket_event_date CHECK (
  (kind = 'date_changed') = (date_after IS NOT NULL));

-- The date moves only with the event that says so: the service writes the
-- event first, in the same transaction.
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
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'only the read markers and the date of a breach ticket may change'
      USING ERRCODE = 'restrict_violation';
  END IF;
  IF NEW.answer_by IS DISTINCT FROM OLD.answer_by AND (
       NEW.answer_by IS NULL OR NEW.answer_by IS DISTINCT FROM (
         SELECT e.date_after FROM breach_ticket_event e
          WHERE e.ticket_id = NEW.ticket_id AND e.kind = 'date_changed'
          ORDER BY e.event_id DESC LIMIT 1)) THEN
    RAISE EXCEPTION 'a breach ticket''s date changes only with the event that records it'
      USING ERRCODE = 'restrict_violation';
  END IF;
  RETURN NEW;
END;
$$;
"""

#: Nothing below can carry a date_changed event: the columns that say what moved
#: go, and the older code and a second upgrade both trip on the row that stays.
GUARD = """DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM breach_ticket_event WHERE kind = 'date_changed') THEN
    RAISE EXCEPTION 'dates were changed; downgrading would lose them';
  END IF;
END $$;"""

DOWNGRADE = """
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
ALTER TABLE breach_ticket_event DROP CONSTRAINT breach_ticket_event_date;
ALTER TABLE breach_ticket_event DROP CONSTRAINT breach_ticket_event_reason;
ALTER TABLE breach_ticket_event ADD CONSTRAINT breach_ticket_event_reason CHECK (
  kind NOT IN ('sent_back', 'withdrawn', 'reopened') OR reason IS NOT NULL) NOT VALID;
ALTER TABLE breach_ticket_event DROP CONSTRAINT breach_ticket_event_kind;
ALTER TABLE breach_ticket_event ADD CONSTRAINT breach_ticket_event_kind CHECK (
  kind IN ('returned', 'sent_back', 'closed', 'withdrawn', 'reopened')) NOT VALID;
ALTER TABLE breach_ticket_event DROP COLUMN date_after, DROP COLUMN date_before;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute("SELECT set_config('app.office', 'all', false)")
    op.execute(GUARD)
    op.execute(DOWNGRADE)
