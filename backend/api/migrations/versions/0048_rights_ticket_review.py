"""A holder's answer is reviewed before it counts (2026-10-08).

A returned ticket counted the moment it came back: it settled the request and,
for an erasure, marked the holder's copy gone - though nobody at the office
had read it. Now the DPO reviews each answer and accepts it, or sends it
back; only an accepted answer counts. `accepted_at` / `accepted_by` record the
acceptance. An answer the office records on a holder's behalf is accepted as
it is recorded - the office wrote it.

Every return already in the database was taken as counting when it came, so
each is marked accepted as of its return: nothing that was settled unsettles.

Revision ID: 0048
Revises: 0047
"""

from __future__ import annotations

from alembic import op

revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """ALTER TABLE rights_request_holder
             ADD COLUMN accepted_at timestamptz,
             ADD COLUMN accepted_by int REFERENCES auth_user(id)"""
    )
    op.execute(
        "COMMENT ON COLUMN rights_request_holder.accepted_at IS "
        "'When the office accepted the returned answer; only an accepted answer counts'"
    )
    op.execute(
        """UPDATE rights_request_holder SET accepted_at = returned_at
            WHERE ticket_status = 'returned' AND accepted_at IS NULL"""
    )
    op.execute(
        """ALTER TABLE rights_request_holder ADD CONSTRAINT holder_accepted_is_returned
             CHECK (accepted_at IS NULL OR ticket_status = 'returned')"""
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE rights_request_holder DROP CONSTRAINT IF EXISTS holder_accepted_is_returned"
    )
    op.execute(
        "ALTER TABLE rights_request_holder DROP COLUMN IF EXISTS accepted_by, "
        "DROP COLUMN IF EXISTS accepted_at"
    )
