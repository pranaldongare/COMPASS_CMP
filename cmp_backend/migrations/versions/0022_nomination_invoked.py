"""What a nomination was invoked for.

A nominee acts by reporting an event - the principal has died, or cannot
act - and the request then carries it. The nomination itself did not, so
neither the principal (still able to sign in, where the event is incapacity)
nor the nominee could see from their own page that it had been used, or for
what. The event, the moment and the request are now on the nomination.

Revision ID: 0022
Revises: 0021
"""

from __future__ import annotations

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None

UPGRADE = """
ALTER TABLE nomination
  ADD COLUMN invoked_at         timestamptz,
  ADD COLUMN invoked_event      rights_trigger_event,
  ADD COLUMN invoked_request_id integer REFERENCES rights_request(request_id);
"""

DOWNGRADE = """
ALTER TABLE nomination
  DROP COLUMN IF EXISTS invoked_request_id,
  DROP COLUMN IF EXISTS invoked_event,
  DROP COLUMN IF EXISTS invoked_at;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
