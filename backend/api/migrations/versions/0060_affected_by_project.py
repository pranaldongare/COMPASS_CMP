"""Finding the people a breach affected by project or activity (2026-11-06).

The list was derived from a processor, a data source or the platform's own
tables, and a person running a breach cannot be asked which tables were
exposed. It is now derived from what they know: the project or activity, the
vendor, the data source. `breach_affected.found_by` gains `project`.

`platform` stays allowed: people already listed that way stay listed that way,
and nothing writes it any more.

Revision ID: 0060
Revises: 0059
"""

from __future__ import annotations

from alembic import op

revision = "0060"
down_revision = "0059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """ALTER TABLE breach_affected DROP CONSTRAINT breach_affected_found_by;
           ALTER TABLE breach_affected ADD CONSTRAINT breach_affected_found_by CHECK (
             found_by IN ('processor', 'data_source', 'platform', 'dpo', 'upload', 'project'))"""
    )


def downgrade() -> None:
    op.execute(
        """ALTER TABLE breach_affected DROP CONSTRAINT breach_affected_found_by;
           ALTER TABLE breach_affected ADD CONSTRAINT breach_affected_found_by CHECK (
             found_by IN ('processor', 'data_source', 'platform', 'dpo', 'upload')) NOT VALID"""
    )
