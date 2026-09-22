"""The blind-index columns are called what they are: `*_hash`.

0028 added a keyed hash beside each column the platform looks rows up by, and
called it `*_idx`. The name described the *use* - it is what an index is
built on - and hid the *content*, which is `HMAC-SHA256(normalised value,
BLIND_INDEX_KEY)`. Six ordinary btree indexes in this schema also end in
`_idx`, so the name additionally collided with a convention it was not part
of, and every reader had to know which kind they were looking at.

`*_hash` says what the column holds. Nothing else changes: same values, same
uniqueness, same lookups, no backfill. PostgreSQL carries indexes,
constraints and defaults across a `RENAME COLUMN`, so the rename is the whole
migration; what follows it here is cosmetic - the index and constraint names
that quote the old column name, and the one trigger function whose body does.

The eight, in three tables:

    auth_user       email, secondary_email, mobile, username, organization_id
    nomination      nominee_email, nominee_mobile
    rights_request  submitted_contact

Revision ID: 0029
Revises: 0028
"""

from __future__ import annotations

from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None

#: (table, old column, new column). The only eight columns this touches; an
#: ordinary index whose *name* ends in `_idx` is not in this list and is not
#: renamed.
COLUMNS: list[tuple[str, str, str]] = [
    ("auth_user", "email_idx", "email_hash"),
    ("auth_user", "secondary_email_idx", "secondary_email_hash"),
    ("auth_user", "mobile_idx", "mobile_hash"),
    ("auth_user", "username_idx", "username_hash"),
    ("auth_user", "organization_id_idx", "organization_id_hash"),
    ("nomination", "nominee_email_idx", "nominee_email_hash"),
    ("nomination", "nominee_mobile_idx", "nominee_mobile_hash"),
    ("rights_request", "submitted_contact_idx", "submitted_contact_hash"),
]

#: Index names that quote the old column name. Renaming an index changes no
#: plan and takes no lock beyond the catalogue; leaving them would mean a
#: `\d auth_user` that disagrees with itself.
INDEXES: list[tuple[str, str]] = [
    ("auth_user_email_idx_key", "auth_user_email_hash_key"),
    ("auth_user_secondary_email_idx_key", "auth_user_secondary_email_hash_key"),
    ("auth_user_mobile_idx_key", "auth_user_mobile_hash_key"),
    ("auth_user_username_idx_key", "auth_user_username_hash_key"),
    ("auth_user_organization_id_idx_key", "auth_user_organization_id_hash_key"),
    ("idx_nomination_nominee_email_idx", "idx_nomination_nominee_email_hash"),
    ("idx_nomination_nominee_mobile_idx", "idx_nomination_nominee_mobile_hash"),
    ("idx_rights_request_contact_idx", "idx_rights_request_contact_hash"),
]

#: The one function whose body names the columns. Replaced rather than
#: renamed: a plpgsql body is text, and the rename does not reach into it.
TRIGGER_FN = """
CREATE OR REPLACE FUNCTION cmp_contact_belongs_to_one_person() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.secondary_email_{suffix} IS NOT NULL AND EXISTS (
       SELECT 1 FROM auth_user u
        WHERE u.id <> NEW.id AND u.email_{suffix} = NEW.secondary_email_{suffix}) THEN
    RAISE EXCEPTION 'that address belongs to another account'
      USING ERRCODE = 'unique_violation';
  END IF;
  IF NEW.email_{suffix} IS NOT NULL AND EXISTS (
       SELECT 1 FROM auth_user u
        WHERE u.id <> NEW.id AND u.secondary_email_{suffix} = NEW.email_{suffix}) THEN
    RAISE EXCEPTION 'that address belongs to another account'
      USING ERRCODE = 'unique_violation';
  END IF;
  RETURN NEW;
END $$;
"""

#: The CHECKs whose definitions name the columns. A constraint's expression is
#: stored parsed, so the rename rewrites it; only the constraint *names* that
#: say `idx` would be left, and none of these do. Kept here because the
#: `secondary_email_differs` CHECK is the one rule that compares two hashes,
#: and a reader looking for it should find it named in this migration.
CHECKS_UNCHANGED = (
    "auth_user_secondary_email_differs",
    "auth_user_email_indexed",
    "auth_user_secondary_email_indexed",
    "auth_user_mobile_indexed",
    "auth_user_username_indexed",
    "auth_user_organization_id_indexed",
    "nomination_email_indexed",
    "nomination_mobile_indexed",
    "rights_request_contact_indexed",
)


def _rename(
    columns: list[tuple[str, str, str]], indexes: list[tuple[str, str]], *, suffix: str
) -> None:
    for table, old, new in columns:
        op.execute(f"ALTER TABLE {table} RENAME COLUMN {old} TO {new}")
    for old, new in indexes:
        op.execute(f"ALTER INDEX IF EXISTS {old} RENAME TO {new}")
    op.execute(TRIGGER_FN.format(suffix=suffix))


def upgrade() -> None:
    _rename(COLUMNS, INDEXES, suffix="hash")


def downgrade() -> None:
    _rename(
        [(t, new, old) for t, old, new in COLUMNS],
        [(new, old) for old, new in INDEXES],
        suffix="idx",
    )
