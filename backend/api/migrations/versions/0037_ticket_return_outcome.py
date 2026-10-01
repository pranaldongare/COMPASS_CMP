"""What a returned ticket says was done (review 2026-10-01, DPDP-1).

A holder's ticket coming back was taken as the holder having done what it was
asked: the erasure executor recorded the holder's copy as erased, and a
correction could close as complete, on any return - including one whose
summary said "unable to erase". A return now carries the holder's outcome:
`done`, `partial` or `failed`. Only `done` counts as done.

NULL is a return recorded before this revision, when there was no question to
answer; it is read as done, which is how it was treated then. Nothing is
backfilled: the platform does not know what those holders would have said.

Revision ID: 0037
Revises: 0036
"""

from __future__ import annotations

from alembic import op

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
ALTER TABLE rights_request_holder ADD COLUMN return_outcome varchar(8);
ALTER TABLE rights_request_holder ADD CONSTRAINT holder_return_outcome
  CHECK (return_outcome IS NULL OR return_outcome IN ('done', 'partial', 'failed'));
COMMENT ON COLUMN rights_request_holder.return_outcome IS
  'What the holder says it did with the ticket: done, partial or failed. NULL is a return from before 0037, read as done';
"""
    )


def downgrade() -> None:
    op.execute(
        """
ALTER TABLE rights_request_holder DROP CONSTRAINT IF EXISTS holder_return_outcome;
ALTER TABLE rights_request_holder DROP COLUMN IF EXISTS return_outcome;
"""
    )
