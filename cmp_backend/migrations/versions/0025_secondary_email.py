"""A second email address a person adds themselves.

One more way to reach her, and one more way for her to sign in - once a code
sent to it has come back. It exists for the person whose first address is not
theirs to keep: a member of staff is also a data principal, and the day they
leave, the corporate mailbox goes with them. The consents they gave and the
rights they hold do not.

An address identifies exactly one person, whichever column holds it. The
unique index covers the new column; the trigger covers the diagonal, so a
secondary address can never be somebody else's primary and a primary can never
be somebody else's secondary. It raises with the unique-violation error code so
the application reports it as the conflict it is.

Revision ID: 0025
Revises: 0024
"""

from __future__ import annotations

from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None

UPGRADE = """
ALTER TABLE auth_user
  ADD COLUMN secondary_email             varchar(255),
  ADD COLUMN secondary_email_verified_at timestamptz;

COMMENT ON COLUMN auth_user.secondary_email IS
  'A second address the person added themselves; signs them in only once a code sent to it has come back';
COMMENT ON COLUMN auth_user.secondary_email_verified_at IS
  'When a code sent to secondary_email came back; NULL means it never has';

-- Case-insensitive, like the lookup that reads it.
CREATE UNIQUE INDEX auth_user_secondary_email_lower_key
  ON auth_user (lower(secondary_email));

-- The same address twice on one row says nothing and would let the second copy
-- sit unconfirmed beside a confirmed first.
ALTER TABLE auth_user ADD CONSTRAINT auth_user_secondary_email_differs
  CHECK (secondary_email IS NULL OR email IS NULL OR lower(secondary_email) <> lower(email));

-- The diagonal: no address on one row's primary may be another row's secondary,
-- or the reverse. Two rows would then answer the same sign-in.
CREATE OR REPLACE FUNCTION cmp_contact_belongs_to_one_person() RETURNS trigger AS $$
BEGIN
  IF NEW.secondary_email IS NOT NULL AND EXISTS (
       SELECT 1 FROM auth_user u
        WHERE u.id <> NEW.id AND lower(u.email) = lower(NEW.secondary_email)) THEN
    RAISE EXCEPTION 'that address belongs to another account'
      USING ERRCODE = 'unique_violation';
  END IF;
  IF NEW.email IS NOT NULL AND EXISTS (
       SELECT 1 FROM auth_user u
        WHERE u.id <> NEW.id AND lower(u.secondary_email) = lower(NEW.email)) THEN
    RAISE EXCEPTION 'that address belongs to another account'
      USING ERRCODE = 'unique_violation';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_contact_belongs_to_one_person
  BEFORE INSERT OR UPDATE OF email, secondary_email ON auth_user
  FOR EACH ROW EXECUTE FUNCTION cmp_contact_belongs_to_one_person();
"""

DOWNGRADE = """
DROP TRIGGER IF EXISTS trg_contact_belongs_to_one_person ON auth_user;
DROP FUNCTION IF EXISTS cmp_contact_belongs_to_one_person();
ALTER TABLE auth_user DROP CONSTRAINT IF EXISTS auth_user_secondary_email_differs;
DROP INDEX IF EXISTS auth_user_secondary_email_lower_key;
ALTER TABLE auth_user
  DROP COLUMN IF EXISTS secondary_email_verified_at,
  DROP COLUMN IF EXISTS secondary_email;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
