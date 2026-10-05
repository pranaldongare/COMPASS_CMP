"""A breach-only login, and the record of every one (S3-09).

Some of the people a breach needs have no console login: an engineer who is a
data principal on the platform, or nobody on it at all. They are given one for
that breach only (BD-04, ADR 0023): the role `breach_holder`, which reaches its
own tickets, the shared Tickets page and the personal pages, and nothing else.

`breach_temporary_access` is one row per grant: whose account, on which breach,
for which ticket, whether the account was made for it, and the role it held
before - so ending the grant can put things back. It ends once, when the
breach closes, when the DPO withdraws that ticket, or when an administrator
deactivates the account, and records which. One open grant per person per
breach, by partial unique index. Nothing else about a grant ever changes, and
no grant is deleted.

The enum value goes first, alone and outside the transaction, as 0018's did:
PostgreSQL will not use a value added in the same transaction, and cannot take
one away - the downgrade leaves it.

Revision ID: 0041
Revises: 0040
"""

from __future__ import annotations

import os

from alembic import op

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

NEW_ROLE = "ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'breach_holder';"

UPGRADE = """
CREATE TABLE breach_temporary_access (
  access_id       serial PRIMARY KEY,
  access_uuid     uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  breach_id       int NOT NULL REFERENCES breach(breach_id),
  user_id         int NOT NULL REFERENCES auth_user(id),
  ticket_id       int NOT NULL REFERENCES breach_ticket(ticket_id),
  -- An account made for this breach is switched off at the end; one that
  -- already existed goes back to the role it held.
  account_created boolean NOT NULL,
  previous_role   user_role,
  granted_by      int NOT NULL REFERENCES auth_user(id),
  granted_at      timestamptz NOT NULL DEFAULT now(),
  ended_at        timestamptz,
  ended_by        int REFERENCES auth_user(id),
  end_cause       varchar(24),
  CONSTRAINT breach_temporary_access_cause CHECK (
    end_cause IS NULL
    OR end_cause IN ('breach_closed', 'ticket_withdrawn', 'account_deactivated')
  ),
  CONSTRAINT breach_temporary_access_ended CHECK ((ended_at IS NULL) = (end_cause IS NULL))
);
COMMENT ON TABLE breach_temporary_access IS
  'A breach-only login: one grant of the breach_holder role for one breach (S3-09, ADR 0023). Ends once; never deleted';
COMMENT ON COLUMN breach_temporary_access.previous_role IS
  'The role the account held before the grant, for an account that already existed; NULL for one made for the breach';
COMMENT ON COLUMN breach_temporary_access.end_cause IS
  'breach_closed, ticket_withdrawn or account_deactivated';
CREATE UNIQUE INDEX breach_temporary_access_open
  ON breach_temporary_access (breach_id, user_id) WHERE ended_at IS NULL;
CREATE INDEX idx_breach_temporary_access_user ON breach_temporary_access (user_id);

-- A grant is written once and ended once: the three end columns may go from
-- NULL to a value, and nothing else may change. Never deleted.
CREATE OR REPLACE FUNCTION cmp_breach_temporary_access_end_once() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'temporary access is never deleted' USING ERRCODE = 'restrict_violation';
  END IF;
  IF NEW.access_id IS DISTINCT FROM OLD.access_id
     OR NEW.access_uuid IS DISTINCT FROM OLD.access_uuid
     OR NEW.breach_id IS DISTINCT FROM OLD.breach_id
     OR NEW.user_id IS DISTINCT FROM OLD.user_id
     OR NEW.ticket_id IS DISTINCT FROM OLD.ticket_id
     OR NEW.account_created IS DISTINCT FROM OLD.account_created
     OR NEW.previous_role IS DISTINCT FROM OLD.previous_role
     OR NEW.granted_by IS DISTINCT FROM OLD.granted_by
     OR NEW.granted_at IS DISTINCT FROM OLD.granted_at
     OR OLD.ended_at IS NOT NULL THEN
    RAISE EXCEPTION 'a grant of temporary access is written once and ended once'
      USING ERRCODE = 'restrict_violation';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_breach_temporary_access_end_once
  BEFORE UPDATE OR DELETE ON breach_temporary_access
  FOR EACH ROW EXECUTE FUNCTION cmp_breach_temporary_access_end_once();
"""

DOWNGRADE = """
DROP TABLE IF EXISTS breach_temporary_access;
DROP FUNCTION IF EXISTS cmp_breach_temporary_access_end_once();
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
  EXECUTE format('REVOKE DELETE, TRUNCATE ON TABLE breach_temporary_access FROM %I', r);
END $$;
"""


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(NEW_ROLE)
    op.execute(UPGRADE)
    op.execute(_harden(APP_ROLE))


def downgrade() -> None:
    # The enum value stays: PostgreSQL cannot remove one, and a row may hold it.
    op.execute(DOWNGRADE)
