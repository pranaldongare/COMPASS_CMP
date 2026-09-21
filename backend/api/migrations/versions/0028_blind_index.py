"""The lookup columns get a blind index, so they can be sealed too.

Eight personal columns stayed plaintext after 0027 because the platform finds
rows by them: sign-in by email or username, a code sent to a mobile, "is this
address taken", a nomination found by the nominee's contact, a public request
verified through the contact it gave. Randomised ciphertext cannot answer any of
those. A blind index can: `HMAC-SHA256(normalised value, BLIND_INDEX_KEY)`,
deterministic so it can be unique-indexed and looked up, keyed so it reveals
nothing without the key.

This revision adds the index column beside each lookup column, fills it from
the plaintext that is still present, moves every uniqueness rule from the value
to the index, rewrites the one trigger that compared addresses across columns,
and widens the value columns to `text` so the ciphertext that will replace them
fits. It does not seal anything itself: `scripts/reseal.py` does that, and can
run at any time afterwards, because from this revision on every lookup goes
through the index and no longer cares what the value column holds.

Date of birth is the odd one. `cmp_is_minor(dob)` is the section 9 test, a date
comparison in SQL, and a sealed date cannot be compared. So the test moves to
`minor_until`, the date eighteen years after birth, kept in the clear - it says
when a person stops being a child and nothing else - and `dob` becomes text so
it can be sealed like the rest. `cmp_is_minor` keeps its name and takes the new
column.

**The backfill runs in Python.** Computing an HMAC under a key this database
does not hold is not something the SQL here can do, so the index values are
computed by the application's own `index_of` and written row by row inside the
same transaction. Every other migration in this chain is SQL alone; this one
says why it is not.

The downgrade puts the columns back as they were. It will refuse if any row
already holds ciphertext where a varchar(20) mobile or a date of birth used to
be, and that refusal is correct.

Revision ID: 0028
Revises: 0027
"""

from __future__ import annotations

import sys
from pathlib import Path

from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None

# The application's own index function, so the migration and the code agree.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from cmp.infrastructure.dkms.blind import index_of  # noqa: E402
from cmp.infrastructure.dkms.client import unseal_values_sync  # noqa: E402

#: (table, value column, index column, kind)
INDEXED: list[tuple[str, str, str, str]] = [
    ("auth_user", "email", "email_idx", "email"),
    ("auth_user", "secondary_email", "secondary_email_idx", "email"),
    ("auth_user", "mobile", "mobile_idx", "mobile"),
    ("auth_user", "username", "username_idx", "username"),
    # Sealed in 0027's wake, and UNIQUE - which a randomised ciphertext defeats
    # silently. Its index restores the rule.
    ("auth_user", "organization_id", "organization_id_idx", "text"),
    ("nomination", "nominee_email", "nominee_email_idx", "email"),
    ("nomination", "nominee_mobile", "nominee_mobile_idx", "mobile"),
    ("rights_request", "submitted_contact", "submitted_contact_idx", "contact"),
]

#: The value columns, and the type each had before it became text.
WIDENED: list[tuple[str, str, str]] = [
    ("auth_user", "email", "character varying(255)"),
    ("auth_user", "secondary_email", "character varying(255)"),
    ("auth_user", "mobile", "character varying(20)"),
    ("auth_user", "username", "character varying(120)"),
    ("nomination", "nominee_email", "character varying(255)"),
    ("nomination", "nominee_mobile", "character varying(20)"),
    ("rights_request", "submitted_contact", "character varying(255)"),
]

ADD_COLUMNS = (
    "\n".join(f"ALTER TABLE {t} ADD COLUMN {idx} text;" for t, _, idx, _ in INDEXED)
    + """
ALTER TABLE auth_user ADD COLUMN minor_until date;
UPDATE auth_user SET minor_until = dob + INTERVAL '18 years' WHERE dob IS NOT NULL;
COMMENT ON COLUMN auth_user.minor_until IS
  'The date this person stops being a child under s.9: date of birth plus eighteen years. Kept in the clear so the test stays a comparison; dob itself is sealed';
"""
)

MOVE_CONSTRAINTS = """
-- Uniqueness moves from the value to its index. A unique index ignores NULLs,
-- as the old ones did.
ALTER TABLE auth_user DROP CONSTRAINT IF EXISTS auth_user_email_key;
ALTER TABLE auth_user DROP CONSTRAINT IF EXISTS auth_user_mobile_key;
ALTER TABLE auth_user DROP CONSTRAINT IF EXISTS auth_user_username_key;
ALTER TABLE auth_user DROP CONSTRAINT IF EXISTS auth_user_organization_id_key;
DROP INDEX IF EXISTS auth_user_secondary_email_lower_key;
DROP INDEX IF EXISTS idx_user_email_lower;
CREATE UNIQUE INDEX auth_user_email_idx_key           ON auth_user (email_idx);
CREATE UNIQUE INDEX auth_user_mobile_idx_key          ON auth_user (mobile_idx);
CREATE UNIQUE INDEX auth_user_username_idx_key        ON auth_user (username_idx);
CREATE UNIQUE INDEX auth_user_organization_id_idx_key ON auth_user (organization_id_idx);
CREATE UNIQUE INDEX auth_user_secondary_email_idx_key ON auth_user (secondary_email_idx);
CREATE INDEX idx_nomination_nominee_email_idx  ON nomination (nominee_email_idx);
CREATE INDEX idx_nomination_nominee_mobile_idx ON nomination (nominee_mobile_idx);
CREATE INDEX idx_rights_request_contact_idx    ON rights_request (submitted_contact_idx);

-- A contact without its index would escape every rule above, silently. These
-- make a write that forgets the index fail instead - which is what a raw SQL
-- write that bypasses the repositories deserves.
ALTER TABLE auth_user ADD CONSTRAINT auth_user_email_indexed
  CHECK (email IS NULL OR email_idx IS NOT NULL);
ALTER TABLE auth_user ADD CONSTRAINT auth_user_secondary_email_indexed
  CHECK (secondary_email IS NULL OR secondary_email_idx IS NOT NULL);
ALTER TABLE auth_user ADD CONSTRAINT auth_user_mobile_indexed
  CHECK (mobile IS NULL OR mobile_idx IS NOT NULL);
ALTER TABLE auth_user ADD CONSTRAINT auth_user_username_indexed
  CHECK (username IS NULL OR username_idx IS NOT NULL);
ALTER TABLE auth_user ADD CONSTRAINT auth_user_organization_id_indexed
  CHECK (organization_id IS NULL OR organization_id_idx IS NOT NULL);
ALTER TABLE nomination ADD CONSTRAINT nomination_email_indexed
  CHECK (nominee_email IS NULL OR nominee_email_idx IS NOT NULL);
ALTER TABLE nomination ADD CONSTRAINT nomination_mobile_indexed
  CHECK (nominee_mobile IS NULL OR nominee_mobile_idx IS NOT NULL);
ALTER TABLE rights_request ADD CONSTRAINT rights_request_contact_indexed
  CHECK (submitted_contact IS NULL OR submitted_contact_idx IS NOT NULL);

-- "An address belongs to one account whichever column holds it" - now said
-- with the indexes, since the addresses themselves are about to be sealed. The
-- trigger is re-armed on the index columns: it is the index that changes when
-- an address does, and a trigger on the value column would also block the
-- ALTER TYPE below.
DROP TRIGGER IF EXISTS trg_contact_belongs_to_one_person ON auth_user;
CREATE OR REPLACE FUNCTION cmp_contact_belongs_to_one_person() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.secondary_email_idx IS NOT NULL AND EXISTS (
       SELECT 1 FROM auth_user u
        WHERE u.id <> NEW.id AND u.email_idx = NEW.secondary_email_idx) THEN
    RAISE EXCEPTION 'that address belongs to another account'
      USING ERRCODE = 'unique_violation';
  END IF;
  IF NEW.email_idx IS NOT NULL AND EXISTS (
       SELECT 1 FROM auth_user u
        WHERE u.id <> NEW.id AND u.secondary_email_idx = NEW.email_idx) THEN
    RAISE EXCEPTION 'that address belongs to another account'
      USING ERRCODE = 'unique_violation';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_contact_belongs_to_one_person
  BEFORE INSERT OR UPDATE OF email_idx, secondary_email_idx ON auth_user
  FOR EACH ROW EXECUTE FUNCTION cmp_contact_belongs_to_one_person();

-- The section 9 test, on the date a person stops being a child. Dropped and
-- recreated: PostgreSQL will not rename a parameter through OR REPLACE.
DROP FUNCTION cmp_is_minor(date);
CREATE FUNCTION cmp_is_minor(until date) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT CASE WHEN until IS NULL THEN NULL ELSE until > CURRENT_DATE END;
$$;
"""

WIDEN = (
    """
-- Two CHECKs read the values. "Secondary differs from primary" is restated on
-- the indexes. "Date of birth is plausible" cannot be restated on ciphertext;
-- the API's own validation (a date, after 1900, before today) is where that
-- rule lives now.
ALTER TABLE auth_user DROP CONSTRAINT IF EXISTS auth_user_secondary_email_differs;
ALTER TABLE auth_user ADD CONSTRAINT auth_user_secondary_email_differs
  CHECK (secondary_email_idx IS NULL OR email_idx IS NULL OR secondary_email_idx <> email_idx);
ALTER TABLE auth_user DROP CONSTRAINT IF EXISTS dob_is_plausible;
"""
    + "\n".join(f"ALTER TABLE {t} ALTER COLUMN {c} TYPE text;" for t, c, _ in WIDENED)
    + """
ALTER TABLE auth_user ALTER COLUMN dob TYPE text USING dob::text;
COMMENT ON COLUMN auth_user.dob IS
  'Date of birth, sealed by the key service; text because ciphertext is not a date. The s.9 test reads minor_until';
"""
)

NARROW = (
    "\n".join(f"ALTER TABLE {t} ALTER COLUMN {c} TYPE {old};" for t, c, old in WIDENED)
    + """
ALTER TABLE auth_user ALTER COLUMN dob TYPE date USING dob::date;
COMMENT ON COLUMN auth_user.dob IS NULL;
ALTER TABLE auth_user DROP CONSTRAINT IF EXISTS auth_user_secondary_email_differs;
ALTER TABLE auth_user ADD CONSTRAINT auth_user_secondary_email_differs
  CHECK (secondary_email IS NULL OR email IS NULL OR lower(secondary_email) <> lower(email));
ALTER TABLE auth_user ADD CONSTRAINT dob_is_plausible
  CHECK (dob IS NULL OR (dob > DATE '1900-01-01' AND dob < CURRENT_DATE));
"""
)

RESTORE_CONSTRAINTS = """
ALTER TABLE auth_user DROP CONSTRAINT IF EXISTS auth_user_email_indexed;
ALTER TABLE auth_user DROP CONSTRAINT IF EXISTS auth_user_secondary_email_indexed;
ALTER TABLE auth_user DROP CONSTRAINT IF EXISTS auth_user_mobile_indexed;
ALTER TABLE auth_user DROP CONSTRAINT IF EXISTS auth_user_username_indexed;
ALTER TABLE auth_user DROP CONSTRAINT IF EXISTS auth_user_organization_id_indexed;
ALTER TABLE nomination DROP CONSTRAINT IF EXISTS nomination_email_indexed;
ALTER TABLE nomination DROP CONSTRAINT IF EXISTS nomination_mobile_indexed;
ALTER TABLE rights_request DROP CONSTRAINT IF EXISTS rights_request_contact_indexed;
DROP INDEX IF EXISTS auth_user_email_idx_key;
DROP INDEX IF EXISTS auth_user_mobile_idx_key;
DROP INDEX IF EXISTS auth_user_username_idx_key;
DROP INDEX IF EXISTS auth_user_organization_id_idx_key;
DROP INDEX IF EXISTS auth_user_secondary_email_idx_key;
DROP INDEX IF EXISTS idx_nomination_nominee_email_idx;
DROP INDEX IF EXISTS idx_nomination_nominee_mobile_idx;
DROP INDEX IF EXISTS idx_rights_request_contact_idx;
ALTER TABLE auth_user ADD CONSTRAINT auth_user_email_key UNIQUE (email);
ALTER TABLE auth_user ADD CONSTRAINT auth_user_mobile_key UNIQUE (mobile);
ALTER TABLE auth_user ADD CONSTRAINT auth_user_username_key UNIQUE (username);
ALTER TABLE auth_user ADD CONSTRAINT auth_user_organization_id_key UNIQUE (organization_id);
CREATE UNIQUE INDEX auth_user_secondary_email_lower_key ON auth_user (lower(secondary_email));
CREATE INDEX idx_user_email_lower ON auth_user (lower(email));

DROP TRIGGER IF EXISTS trg_contact_belongs_to_one_person ON auth_user;
CREATE OR REPLACE FUNCTION cmp_contact_belongs_to_one_person() RETURNS trigger
LANGUAGE plpgsql AS $$
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
END $$;
CREATE TRIGGER trg_contact_belongs_to_one_person
  BEFORE INSERT OR UPDATE OF email, secondary_email ON auth_user
  FOR EACH ROW EXECUTE FUNCTION cmp_contact_belongs_to_one_person();

DROP FUNCTION cmp_is_minor(date);
CREATE FUNCTION cmp_is_minor(birth date) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT CASE WHEN birth IS NULL THEN NULL ELSE birth > (CURRENT_DATE - INTERVAL '18 years') END;
$$;
"""

DROP_COLUMNS = (
    "\n".join(f"ALTER TABLE {t} DROP COLUMN IF EXISTS {idx};" for t, _, idx, _ in INDEXED)
    + "\nALTER TABLE auth_user DROP COLUMN IF EXISTS minor_until;\n"
)


def _backfill() -> None:
    """Every existing plaintext value gets its index, in this transaction."""
    conn = op.get_bind()
    for table, value_col, idx_col, kind in INDEXED:
        pk = {"auth_user": "id", "nomination": "nomination_id", "rights_request": "request_id"}[
            table
        ]
        rows = conn.exec_driver_sql(
            f"SELECT {pk}, {value_col} FROM {table} WHERE {value_col} IS NOT NULL"
        ).fetchall()
        # A value sealed before this revision - organization_id was, from 0027 on
        # - is opened through the key service to compute its index. If the
        # service is not reachable the migration fails here, which is right:
        # an index that cannot be computed is a row that cannot be found.
        values = [str(v) for _, v in rows]
        sealed = [v for v in values if v.startswith("SE::")]
        opened = dict(zip(sealed, unseal_values_sync(sealed), strict=True)) if sealed else {}
        for (pk_value, _), value in zip(rows, values, strict=True):
            plain = opened.get(value, value)
            conn.exec_driver_sql(
                f"UPDATE {table} SET {idx_col} = %s WHERE {pk} = %s",
                (index_of(kind, plain), pk_value),  # type: ignore[arg-type]
            )


def upgrade() -> None:
    op.execute(ADD_COLUMNS)
    _backfill()
    op.execute(MOVE_CONSTRAINTS)
    op.execute(WIDEN)


def downgrade() -> None:
    # The trigger on the index columns has to go before the value columns
    # change type, and the value-column trigger can only be re-armed after.
    op.execute("DROP TRIGGER IF EXISTS trg_contact_belongs_to_one_person ON auth_user;")
    op.execute(NARROW)
    op.execute(RESTORE_CONSTRAINTS)
    op.execute(DROP_COLUMNS)
