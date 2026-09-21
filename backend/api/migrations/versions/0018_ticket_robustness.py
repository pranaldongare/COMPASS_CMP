"""A ticket that can be withdrawn, reassigned and reminded, and files with names.

Three gaps the ticket lifecycle had, each of which a person was covering by
hand or by memory:

* A ticket issued in error had no way out but a fake return. `withdrawn` is
  a status of its own: not a return, not a gap in the response.
* A reminder is a fact about the ticket, not a note somebody remembers to
  write. `last_reminded_at` and `reminders_sent` let the daily pass send
  reminders on a cadence without sending two in a day.
* A file kept only its hash and its storage reference, so it came back down
  under a generic name. The name it was uploaded with is kept alongside.

The message kinds gain `status` for what the platform writes on a thread when
the office withdraws, reassigns or reminds - so the thread tells the whole
story, not only the conversation.

Revision ID: 0018
Revises: 0017
"""

from __future__ import annotations

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

# Adding a value to a PostgreSQL enum cannot run inside a transaction block on
# older servers and cannot be undone at all; it goes first, alone, and stays.
NEW_STATUS = "ALTER TYPE rights_ticket_status ADD VALUE IF NOT EXISTS 'withdrawn';"

UPGRADE = """
ALTER TABLE rights_request_holder
  ADD COLUMN return_evidence_name varchar(255),
  ADD COLUMN last_reminded_at     timestamptz,
  ADD COLUMN reminders_sent       int NOT NULL DEFAULT 0;

ALTER TABLE rights_ticket_message
  ADD COLUMN evidence_name varchar(255);
ALTER TABLE rights_ticket_message DROP CONSTRAINT ticket_message_kind;
ALTER TABLE rights_ticket_message
  ADD CONSTRAINT ticket_message_kind
  CHECK (kind IN ('brief', 'instruction', 'message', 'return', 'escalation', 'status'));
"""

DOWNGRADE = """
ALTER TABLE rights_ticket_message DROP CONSTRAINT ticket_message_kind;
ALTER TABLE rights_ticket_message
  ADD CONSTRAINT ticket_message_kind
  CHECK (kind IN ('brief', 'instruction', 'message', 'return', 'escalation'));
ALTER TABLE rights_ticket_message DROP COLUMN IF EXISTS evidence_name;
ALTER TABLE rights_request_holder
  DROP COLUMN IF EXISTS reminders_sent,
  DROP COLUMN IF EXISTS last_reminded_at,
  DROP COLUMN IF EXISTS return_evidence_name;
"""


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(NEW_STATUS)
    op.execute(UPGRADE)


def downgrade() -> None:
    # The enum value stays: PostgreSQL cannot remove one, and a row may hold it.
    op.execute(DOWNGRADE)
