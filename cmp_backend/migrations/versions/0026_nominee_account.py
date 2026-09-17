"""The account a nominee accepted with, recorded on the nomination.

A nomination names a person by contact, because a nominee may be a stranger to
the platform when they are named. Accepting changes that: it proves a recorded
contact, and either finds an account holding it or makes one. Nothing wrote
that down, so every question afterwards - which nominations name me, may I see
the request I raised - was answered by comparing contact strings.

That comparison is fragile in ways that only appear later. A mobile stored
un-normalised on an old row does not equal the same number stored in E.164. A
nominee who changes their number, or who holds the recorded address as their
*second* email, stops matching a nomination that is still in force. And each
new query has to repeat the join by hand, which is how two of them come to
disagree.

So the account is recorded once, at acceptance. The contacts stay on the row:
they are what the principal recorded and what a code is sent to, and they must
not follow the nominee's later edits. The backfill matches what the old
comparison matched, so no row loses a link it already had in effect.

Revision ID: 0026
Revises: 0025
"""

from __future__ import annotations

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None

UPGRADE = """
ALTER TABLE nomination
  ADD COLUMN nominee_user_id integer REFERENCES auth_user(id);

COMMENT ON COLUMN nomination.nominee_user_id IS
  'The account the nominee accepted with, set at acceptance; NULL for a nomination never accepted, or accepted before this column existed and matching no account';

-- Read on every sign-in of a nominee, to answer "who has nominated me".
CREATE INDEX nomination_nominee_user_id_idx
  ON nomination (nominee_user_id) WHERE nominee_user_id IS NOT NULL;

-- Backfill: exactly what the contact comparison matched, and nothing wider.
-- An accepted nomination whose recorded contact is somebody's primary mobile
-- or primary email is that person's. The count guard means a contact that
-- somehow reaches two accounts links to neither, rather than picking one.
UPDATE nomination n
   SET nominee_user_id = (
       SELECT u.id FROM auth_user u
        WHERE (n.nominee_mobile IS NOT NULL AND u.mobile = n.nominee_mobile)
           OR (n.nominee_email IS NOT NULL AND lower(u.email) = lower(n.nominee_email))
        LIMIT 1
   )
 WHERE n.accepted_at IS NOT NULL
   AND (SELECT count(*) FROM auth_user u
         WHERE (n.nominee_mobile IS NOT NULL AND u.mobile = n.nominee_mobile)
            OR (n.nominee_email IS NOT NULL AND lower(u.email) = lower(n.nominee_email))) = 1;
"""

DOWNGRADE = """
DROP INDEX IF EXISTS nomination_nominee_user_id_idx;
ALTER TABLE nomination DROP COLUMN IF EXISTS nominee_user_id;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
