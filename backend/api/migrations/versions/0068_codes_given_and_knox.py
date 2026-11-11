"""Purpose and data source codes are given, not typed; Knox approvals (2026-11-11).

**Codes.** A purpose and a data source each carried a code the person creating
it had to invent, unique across both offices, which they cannot see. They are
now numbered the way a notice template is (0044, 0062): `PUR-0001` and
`SRC-0001`, from a sequence, as the column's default. A code given by hand is
still accepted where the API is sent one, so the seed and any tool that names
its own codes keep working; the console no longer asks. Each sequence starts
past the highest number already in that shape, so a code typed as `PUR-0007`
before today is never issued again.

**Knox.** `approval_type` gains `knox`, recorded with its reference, date and
proof like a security or legal approval (the product owner, 2026-11-11).

PostgreSQL cannot drop an enum value, so the way down leaves `knox`; it puts
the codes back to being required.

Revision ID: 0068
Revises: 0067
"""

from __future__ import annotations

import os

from alembic import op

revision = "0068"
down_revision = "0067"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

UPGRADE = """
CREATE SEQUENCE purpose_code_seq;
SELECT setval('purpose_code_seq', coalesce(
  (SELECT max(substring(purpose_code FROM '^PUR-([0-9]{1,15})$')::bigint) FROM purpose), 0) + 1,
  false);
ALTER TABLE purpose ALTER COLUMN purpose_code
  SET DEFAULT 'PUR-' || cmp_next_number('purpose_code_seq');
ALTER SEQUENCE purpose_code_seq OWNED BY purpose.purpose_code;

CREATE SEQUENCE data_source_code_seq;
SELECT setval('data_source_code_seq', coalesce(
  (SELECT max(substring(source_code FROM '^SRC-([0-9]{1,15})$')::bigint) FROM data_source), 0) + 1,
  false);
ALTER TABLE data_source ALTER COLUMN source_code
  SET DEFAULT 'SRC-' || cmp_next_number('data_source_code_seq');
ALTER SEQUENCE data_source_code_seq OWNED BY data_source.source_code;
"""

DOWNGRADE = """
ALTER TABLE purpose ALTER COLUMN purpose_code DROP DEFAULT;
ALTER TABLE data_source ALTER COLUMN source_code DROP DEFAULT;
DROP SEQUENCE IF EXISTS purpose_code_seq;
DROP SEQUENCE IF EXISTS data_source_code_seq;
"""


def _grants(role: str) -> str:
    return f"""
DO $$
DECLARE r text := {role!r};
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
    RAISE NOTICE 'Role % does not exist; skipping grants', r;
    RETURN;
  END IF;
  EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE purpose_code_seq, data_source_code_seq TO %I', r);
END $$;
"""


def upgrade() -> None:
    # An enum value has to be committed before anything can reference it.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE approval_type ADD VALUE IF NOT EXISTS 'knox'")
    op.execute("SELECT set_config('app.office', 'all', false)")
    op.execute(UPGRADE)
    op.execute(_grants(APP_ROLE))


def downgrade() -> None:
    op.execute(DOWNGRADE)
