"""Mobile first: a data principal and a nominee are reached on a mobile.

A data principal's account was keyed on an email, with a mobile as an optional
extra. From 2026-09-06 it is the other way round: the mobile is required and
the email optional, because the one-time codes that *are* her sign-in should
go to the thing she carries, and a nominee is somebody who must be reachable
when the principal cannot be. Staff keep an email: their sign-in is a password
plus an emailed code, and their accounts are issued, not self-registered.

Two shapes, one table, so the requirement is a rule per role rather than a
column constraint. It is held by a BEFORE INSERT trigger, not a CHECK: accounts
that exist without a mobile were created under the old rule, and a check that
grandfathers them only until they are next updated - which is what NOT VALID
does - would turn the first profile edit, revocation or acceptance on an old
row into a 500. New rows are held to the rule; old rows stay editable.

Verification is recorded per medium. Sign-up authenticates every medium the
principal gave, and the timestamps are what say so.

The nominee's single `nominee_contact` becomes a mobile and an optional email.
Rows written before this carry an email or a mobile in that one column, and
are sorted by shape; a legacy email-only nominee keeps working, and the same
insert-time rule holds new nominations to a mobile.

Revision ID: 0015
Revises: 0014
"""

from __future__ import annotations

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

UPGRADE = """
ALTER TABLE auth_user ALTER COLUMN email DROP NOT NULL;

ALTER TABLE auth_user
  ADD CONSTRAINT auth_user_staff_email_required
  CHECK (role = 'data_subject' OR email IS NOT NULL);

CREATE OR REPLACE FUNCTION cmp_subject_needs_mobile() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.role = 'data_subject' AND NEW.mobile IS NULL THEN
    RAISE EXCEPTION 'a data principal needs a mobile'
      USING ERRCODE = 'check_violation', CONSTRAINT = 'auth_user_subject_mobile_required';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_subject_needs_mobile
  BEFORE INSERT ON auth_user
  FOR EACH ROW EXECUTE FUNCTION cmp_subject_needs_mobile();

ALTER TABLE auth_user
  ADD COLUMN mobile_verified_at timestamptz,
  ADD COLUMN email_verified_at  timestamptz;

ALTER TABLE nomination
  ADD COLUMN nominee_mobile varchar(20),
  ADD COLUMN nominee_email  varchar(255);

UPDATE nomination
   SET nominee_email  = CASE WHEN position('@' in nominee_contact) > 0 THEN nominee_contact END,
       nominee_mobile = CASE WHEN position('@' in nominee_contact) = 0 THEN nominee_contact END;

ALTER TABLE nomination DROP COLUMN nominee_contact;

ALTER TABLE nomination
  ADD CONSTRAINT nomination_some_contact
  CHECK (nominee_mobile IS NOT NULL OR nominee_email IS NOT NULL);

CREATE OR REPLACE FUNCTION cmp_nominee_needs_mobile() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.nominee_mobile IS NULL THEN
    RAISE EXCEPTION 'a nominee needs a mobile'
      USING ERRCODE = 'check_violation', CONSTRAINT = 'nomination_mobile_required';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_nominee_needs_mobile
  BEFORE INSERT ON nomination
  FOR EACH ROW EXECUTE FUNCTION cmp_nominee_needs_mobile();
"""

# The way back. An account that has no email cannot satisfy the old NOT NULL,
# so it is given one built from its mobile, at a domain that cannot deliver.
DOWNGRADE = """
DROP TRIGGER IF EXISTS trg_nominee_needs_mobile ON nomination;
DROP FUNCTION IF EXISTS cmp_nominee_needs_mobile();
ALTER TABLE nomination DROP CONSTRAINT IF EXISTS nomination_some_contact;
ALTER TABLE nomination ADD COLUMN nominee_contact varchar(255);
UPDATE nomination SET nominee_contact = coalesce(nominee_mobile, nominee_email);
ALTER TABLE nomination ALTER COLUMN nominee_contact SET NOT NULL;
ALTER TABLE nomination DROP COLUMN nominee_mobile, DROP COLUMN nominee_email;

ALTER TABLE auth_user DROP COLUMN mobile_verified_at, DROP COLUMN email_verified_at;
DROP TRIGGER IF EXISTS trg_subject_needs_mobile ON auth_user;
DROP FUNCTION IF EXISTS cmp_subject_needs_mobile();
ALTER TABLE auth_user DROP CONSTRAINT IF EXISTS auth_user_staff_email_required;
UPDATE auth_user SET email = mobile || '@mobile.invalid' WHERE email IS NULL;
ALTER TABLE auth_user ALTER COLUMN email SET NOT NULL;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
