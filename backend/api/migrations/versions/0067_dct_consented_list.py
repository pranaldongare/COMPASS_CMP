"""The consented list the Data Collection Tool loads (2026-11-11).

A second kind of project export, beside `project_export`, written to the DCT's
data contract (version 1): one row per person whose consent is fully in force,
and only what a collection agent needs to recognise and tag them. The DCT
refuses `project_export`, which carries withdrawn people, contacts in full and
timestamps it cannot read. `export_type` gains `dct_consented_list`.

Not `consented_list`: that value names per-site lists from before 0010, and an
export is a disclosure record, so an old row must keep meaning what it meant.

An enum value cannot be removed, so the way down leaves it; nothing else
changed.

Revision ID: 0067
Revises: 0066
"""

from __future__ import annotations

from alembic import op

revision = "0067"
down_revision = "0066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # An enum value has to be committed before anything can reference it.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE export_type ADD VALUE IF NOT EXISTS 'dct_consented_list'")


def downgrade() -> None:
    # PostgreSQL cannot drop an enum value, and rows may name it.
    pass
