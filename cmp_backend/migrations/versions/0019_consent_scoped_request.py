"""A rights request confined to one consent.

A data principal can ask about one consent rather than everything the
platform holds about her: the access she wants is the data under that
consent, the erasure she wants is that data and no other. The consent she
named is kept on the request, and every step downstream - who holds it, what
is in scope, what a ticket asks, what the response attaches - is confined to
that consent's chain of grants and withdrawals.

Revision ID: 0019
Revises: 0018
"""

from __future__ import annotations

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None

UPGRADE = """
ALTER TABLE rights_request
  ADD COLUMN consent_id integer REFERENCES consent_artefact(consent_id);
CREATE INDEX rights_request_consent_idx
  ON rights_request (consent_id) WHERE consent_id IS NOT NULL;
"""

DOWNGRADE = """
DROP INDEX IF EXISTS rights_request_consent_idx;
ALTER TABLE rights_request DROP COLUMN IF EXISTS consent_id;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
