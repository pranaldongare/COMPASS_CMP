"""The processors a collection owner works for (2026-10-09).

A DCO saw every data source in the registry and could register a new one
under any third party; an RCO, under any in-house team. Nothing said which
processor somebody actually collects for. Now the administrator says so:

  | Column | Holds |
  |---|---|
  | `user_id` | the DCO or RCO |
  | `processor_id` | a processor they collect for - a third party for a DCO, in-house for an RCO |
  | `assigned_by` | the administrator who said so; NULL for rows this migration derived |
  | `assigned_at` | when |

One or more per person. A DCO or an RCO sees the data sources of these
processors and no others, and registers new ones only under them. A link is
a working assignment, not evidence: taking one away deletes the row, and the
audit trail (`user.processors_set`) keeps who changed it and when.

Filled from what is already true: every processor whose sources a DCO or an
RCO is accountable for today.

Revision ID: 0050
Revises: 0049
"""

from __future__ import annotations

from alembic import op

revision = "0050"
down_revision = "0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE collection_owner_processor (
             user_id      int NOT NULL REFERENCES auth_user(id),
             processor_id int NOT NULL REFERENCES processor(processor_id),
             assigned_by  int REFERENCES auth_user(id),
             assigned_at  timestamptz NOT NULL DEFAULT now(),
             PRIMARY KEY (user_id, processor_id)
           )"""
    )
    op.execute(
        "CREATE INDEX idx_collection_owner_processor_processor "
        "ON collection_owner_processor (processor_id)"
    )
    op.execute(
        "COMMENT ON TABLE collection_owner_processor IS "
        "'The processors a DCO or an RCO collects for; they see and register data sources "
        "under these only (0050)'"
    )
    op.execute(
        "COMMENT ON COLUMN collection_owner_processor.assigned_by IS "
        "'The administrator who assigned it; NULL when derived from source ownership by 0050'"
    )
    op.execute(
        """INSERT INTO collection_owner_processor (user_id, processor_id)
           SELECT DISTINCT s.owner_user_id, s.processor_id
             FROM data_source s
             JOIN auth_user u ON u.id = s.owner_user_id
             JOIN processor p ON p.processor_id = s.processor_id
            WHERE (u.role = 'dco' AND NOT p.is_in_house)
               OR (u.role = 'rco' AND p.is_in_house)"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS collection_owner_processor")
