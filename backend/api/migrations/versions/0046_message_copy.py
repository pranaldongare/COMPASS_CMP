"""Copies of a message, as the Privacy Office sets them (2026-10-08).

An email went to one recipient. The office wants some copied - a ticket to a
holder copied to the team mailbox that follows it up, a project waiting for
approval copied to the approvals mailbox - and chooses which, per message, in
Message templates. `message_copy` is that choice: one row per address per
message, the address sealed (EMAIL) with a blind index so one address is
listed once per message.

A copy is never allowed on a message that carries a code or a link, nor on
one written to a data principal about herself: copying either hands somebody
else what is hers. That rule is the catalogue's (`cmp.core.messages.COPYABLE`)
and the service's; this table holds only what the office chose within it.

Configuration, not evidence: rows are replaced when the office changes its
mind, and every change is on the trail.

Revision ID: 0046
Revises: 0045
"""

from __future__ import annotations

from alembic import op

revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None

UPGRADE = """
CREATE TABLE message_copy (
  copy_id       serial PRIMARY KEY,
  key           varchar(64) NOT NULL,
  address       text NOT NULL,
  address_hash  text NOT NULL,
  added_by      int REFERENCES auth_user(id),
  added_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT message_copy_once UNIQUE (key, address_hash)
);
COMMENT ON TABLE message_copy IS
  'Who an email is copied to, per message, as the office chose. Never a message with a code, a link or a principal''s own record';
COMMENT ON COLUMN message_copy.address IS 'Sealed (EMAIL); address_hash is its blind index';
CREATE INDEX idx_message_copy_key ON message_copy (key);
"""

DOWNGRADE = """
DROP TABLE IF EXISTS message_copy;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
