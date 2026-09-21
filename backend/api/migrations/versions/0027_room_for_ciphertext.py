"""The personal columns become text, so ciphertext fits in them.

Personal data is encrypted on its way into the database through the key
service, and ciphertext is longer than what it hides: about four thirds of the
plaintext plus a 45-byte envelope, in base64. A name that fit in varchar(200)
does not fit once sealed, and `consent_artefact.ip_address` was `inet`, which
holds an address and nothing else.

So every column in `cmp.infrastructure.dkms.fields.ENCRYPTED_FIELDS` that had a
type narrower than `text` becomes `text`. Nothing about the values changes -
`ALTER TYPE varchar -> text` rewrites no rows - and the application's own
validation still bounds what arrives (`Name`, `Mobile` and the rest in
`cmp.schemas.common`). What is being removed is a limit the database enforced
on the plaintext, which it cannot see any more.

The columns the platform looks rows up by - `email`, `mobile`, `username`,
`submitted_contact`, the nominee's contacts - are deliberately not here. They
stay plaintext and keep their types, for the reason `LOOKUP_FIELDS` gives beside
each one: randomised ciphertext cannot be searched or uniquely indexed.

`v_current_consent` is defined as `SELECT ca.*` over the artefact table, and
PostgreSQL will not alter the type of a column a view depends on. The view is
dropped and recreated with the same definition around the change, in the same
transaction, so it is never absent to a reader.

The downgrade narrows the types back. It will refuse if any row holds a value
too long for the old type - which, once anything has been sealed, is every row -
and that refusal is correct: narrowing a column of ciphertext to varchar(200)
would truncate it into something that never decrypts again.

Revision ID: 0027
Revises: 0026
"""

from __future__ import annotations

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None

#: (table, column, old type) for every encrypted column that was narrower than
#: text. `text` columns - request_text, body, the reasons - need nothing.
WIDENED: list[tuple[str, str, str]] = [
    ("auth_user", "full_name", "character varying(200)"),
    ("auth_user", "organization_id", "character varying(60)"),
    ("nomination", "nominee_name", "character varying(200)"),
    ("rights_request", "submitted_name", "character varying(200)"),
    ("rights_request_holder", "responder_name", "character varying(200)"),
    ("rights_request_holder", "responder_contact", "character varying(255)"),
    ("rights_ticket_message", "evidence_name", "character varying(255)"),
    ("rights_response_file", "file_name", "character varying(255)"),
    ("processor_respondent", "name", "character varying(200)"),
    ("processor_respondent", "contact", "character varying(255)"),
    ("import_batch", "file_name", "character varying(255)"),
]

#: The view over the artefacts, as 0001 defined it. Dropped and recreated
#: around the type change because PostgreSQL refuses to alter a column a view
#: depends on; same text both times, so nothing about it changes.
VIEW = """
CREATE VIEW v_current_consent AS
SELECT ca.* FROM consent_artefact ca
WHERE NOT EXISTS (
  SELECT 1 FROM consent_artefact s WHERE s.supersedes_consent_id = ca.consent_id);
"""

UPGRADE = (
    "\n".join(
        f"ALTER TABLE {table} ALTER COLUMN {column} TYPE text;" for table, column, _ in WIDENED
    )
    + """
DROP VIEW v_current_consent;
ALTER TABLE consent_artefact ALTER COLUMN ip_address TYPE text USING ip_address::text;
"""
    + VIEW
    + """
COMMENT ON COLUMN consent_artefact.ip_address IS
  'The address she consented from, sealed by the key service; text rather than inet because ciphertext is not an address';
COMMENT ON COLUMN auth_user.full_name IS
  'Sealed by the key service on write; the portals decrypt. Length is bounded by the API, not the column';
"""
)

DOWNGRADE = (
    "\n".join(
        f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {old};" for table, column, old in WIDENED
    )
    + """
DROP VIEW v_current_consent;
ALTER TABLE consent_artefact ALTER COLUMN ip_address TYPE inet USING ip_address::inet;
"""
    + VIEW
    + """
COMMENT ON COLUMN consent_artefact.ip_address IS NULL;
COMMENT ON COLUMN auth_user.full_name IS NULL;
"""
)


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
