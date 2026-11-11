"""People a breach affected, typed in by mail ID or mobile number (2026-11-11).

A list of the people affected came only as a file, and the one other way to
add somebody by hand found only people with an account. Whoever runs a breach
often has a handful of addresses in an email instead: they are now typed in,
comma-separated, and taken as a list is - a mail ID or mobile number that is
an account's lists that account, and any other is kept as this breach's
contact. What was typed is recorded as a list is, with no file:
`breach_upload.kind` gains `typed`.

Revision ID: 0066
Revises: 0065
"""

from __future__ import annotations

from alembic import op

revision = "0066"
down_revision = "0065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """ALTER TABLE breach_upload DROP CONSTRAINT breach_upload_kind;
           ALTER TABLE breach_upload ADD CONSTRAINT breach_upload_kind
             CHECK (kind IN ('contacts', 'assets', 'typed'))"""
    )


def downgrade() -> None:
    op.execute(
        """ALTER TABLE breach_upload DROP CONSTRAINT breach_upload_kind;
           ALTER TABLE breach_upload ADD CONSTRAINT breach_upload_kind
             CHECK (kind IN ('contacts', 'assets')) NOT VALID"""
    )
