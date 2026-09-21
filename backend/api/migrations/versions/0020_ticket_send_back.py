"""A returned ticket can be sent back.

The office reads what a holder returned and is not satisfied - too thin,
the wrong data, a question left unanswered. Until now the only way on was a
message on the thread, which reopened nothing: the ticket stayed returned,
the request stayed collating, and the holder was under no obligation to
answer. Sending a ticket back reopens it with a reason and a date, and the
holder is told the way they are reached.

Revision ID: 0020
Revises: 0019
"""

from __future__ import annotations

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None

UPGRADE = """
ALTER TABLE rights_request_holder
  ADD COLUMN sent_back_at     timestamptz,
  ADD COLUMN sent_back_reason text,
  ADD COLUMN sent_back_count  int NOT NULL DEFAULT 0;
"""

DOWNGRADE = """
ALTER TABLE rights_request_holder
  DROP COLUMN IF EXISTS sent_back_count,
  DROP COLUMN IF EXISTS sent_back_reason,
  DROP COLUMN IF EXISTS sent_back_at;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
