"""Who a breach touched, derived and revised (S3-02).

Rule 7(1) asks for a notice to *each* affected principal, to the best of the
fiduciary's knowledge - and knowledge grows. So the list is kept as
revisions: each confirmation by the DPO is a `breach_affected_revision`,
recording what it was derived from (a processor, a data source, tables of
the platform's own database within a window) and how many it found, added by
hand and left out; and each person it added for the first time is a
`breach_affected` row naming that revision.

A person is listed once per breach (`breach_affected_once`) and never
removed: a notice already sent cannot be unsent, and listing too many is the
safe side of Rule 7. A later revision adds only people not already listed,
each of whom S3-03 notifies. Both tables are append-only; the evidence on a
row names exports, assets and tables - never a value about the person.

Revision ID: 0035
Revises: 0034
"""

from __future__ import annotations

import os

from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

UPGRADE = """
CREATE TABLE breach_affected_revision (
  revision_id    serial PRIMARY KEY,
  revision_uuid  uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  breach_id      int NOT NULL REFERENCES breach(breach_id),
  revision       int NOT NULL,
  -- What the list was derived from, as asked: [{kind, processor_uuid |
  -- source_uuid | tables, from, to, found}]. Never a person.
  scopes         jsonb NOT NULL DEFAULT '[]'::jsonb,
  derived        int NOT NULL,
  added_by_hand  int NOT NULL,
  excluded       int NOT NULL,
  newly_listed   int NOT NULL,
  note           text,
  confirmed_by   int NOT NULL REFERENCES auth_user(id),
  confirmed_at   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT breach_affected_revision_number UNIQUE (breach_id, revision),
  CONSTRAINT breach_affected_revision_scopes_list CHECK (jsonb_typeof(scopes) = 'array'),
  CONSTRAINT breach_affected_revision_counts CHECK (
    derived >= 0 AND added_by_hand >= 0 AND excluded >= 0 AND newly_listed >= 0
  )
);
COMMENT ON TABLE breach_affected_revision IS
  'One confirmation of who a breach touched, to the best of current knowledge (Rule 7(1), S3-02)';
CREATE TRIGGER trg_breach_affected_revision_append_only
  BEFORE UPDATE OR DELETE ON breach_affected_revision
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();

CREATE TABLE breach_affected (
  affected_id    serial PRIMARY KEY,
  affected_uuid  uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  breach_id      int NOT NULL REFERENCES breach(breach_id),
  revision_id    int NOT NULL REFERENCES breach_affected_revision(revision_id),
  auth_user_id   int NOT NULL REFERENCES auth_user(id),
  found_by       varchar(12) NOT NULL,
  -- Which exports, assets or tables put her on the list. Ids, never values.
  evidence       jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT breach_affected_found_by CHECK (found_by IN ('processor', 'data_source', 'platform', 'dpo')),
  CONSTRAINT breach_affected_once UNIQUE (breach_id, auth_user_id)
);
CREATE INDEX idx_breach_affected_revision ON breach_affected (revision_id);
CREATE INDEX idx_breach_affected_person ON breach_affected (auth_user_id);
CREATE TRIGGER trg_breach_affected_append_only
  BEFORE UPDATE OR DELETE ON breach_affected
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();
"""

DOWNGRADE = """
DROP TABLE IF EXISTS breach_affected;
DROP TABLE IF EXISTS breach_affected_revision;
"""


def _harden(role: str) -> str:
    return f"""
DO $$
DECLARE r text := {role!r};
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
    RAISE NOTICE 'Role % does not exist; skipping grant hardening', r;
    RETURN;
  END IF;
  EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON TABLE breach_affected_revision,
                  breach_affected FROM %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE)
    op.execute(_harden(APP_ROLE))


def downgrade() -> None:
    op.execute(DOWNGRADE)
