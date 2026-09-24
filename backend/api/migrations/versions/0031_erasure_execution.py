"""Erasure that erases: what was done to each store, and what stops it (S2-03).

An erasure decision changed her disposition on `asset_consent` and nothing
else; a scope item could be "applied" with every copy of the asset still where
it was. Three things now make the difference between decided and done.

`rights_item_execution` is the record of carrying an item out, one row per
attempt at each store that holds it: the holder's copy of the asset, which the
platform cannot reach and a returned ticket has to confirm, and the platform's
own pointer to it. A row says done, waiting, failed or held, and why. It is
evidence of the erasure, so it is append-only like the thread and the trail -
a retry is a new row, and the history of a stubborn store is kept.

`rights_request_item.executed_at` is when the last applicable store was done.
It is what S2-02's guard reads before a response may call itself complete.

`legal_hold` stops erasure of what it covers - an asset, or everything about a
person - until it is released. A hold is placed once and released once; nothing
else about it changes, which a trigger holds. The reason is sealed like every
other reason the office writes.

Revision ID: 0031
Revises: 0030
"""

from __future__ import annotations

import os

from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

UPGRADE = """
ALTER TABLE rights_request_item ADD COLUMN executed_at timestamptz;
COMMENT ON COLUMN rights_request_item.executed_at IS
  'When every store holding the item was confirmed erased (S2-03). NULL until then, whatever the disposition says';

CREATE TABLE rights_item_execution (
  execution_id   serial PRIMARY KEY,
  execution_uuid uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  item_id        int NOT NULL REFERENCES rights_request_item(item_id),
  store          varchar(20) NOT NULL,
  status         varchar(10) NOT NULL,
  -- Why, in the platform's own words: which holder confirmed, which hold
  -- stopped it, what failed. Never a value about the person.
  detail         jsonb NOT NULL DEFAULT '{}'::jsonb,
  attempted_by   int REFERENCES auth_user(id),
  attempted_at   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT item_execution_store CHECK (store IN ('holder_copy', 'platform_pointer', 'legal_hold')),
  CONSTRAINT item_execution_status CHECK (status IN ('done', 'waiting', 'failed', 'held'))
);
CREATE INDEX idx_item_execution_item ON rights_item_execution (item_id, store, execution_id);
CREATE TRIGGER trg_item_execution_append_only
  BEFORE UPDATE OR DELETE ON rights_item_execution
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();

CREATE TABLE legal_hold (
  hold_id          serial PRIMARY KEY,
  hold_uuid        uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  asset_id         int REFERENCES data_asset(asset_id),
  subject_user_id  int REFERENCES auth_user(id),
  reason           text NOT NULL,
  placed_by        int NOT NULL REFERENCES auth_user(id),
  placed_at        timestamptz NOT NULL DEFAULT now(),
  released_by      int REFERENCES auth_user(id),
  released_at      timestamptz,
  CONSTRAINT legal_hold_covers_one CHECK ((asset_id IS NULL) <> (subject_user_id IS NULL)),
  CONSTRAINT legal_hold_release_attributed CHECK ((released_at IS NULL) = (released_by IS NULL))
);
CREATE INDEX idx_legal_hold_asset ON legal_hold (asset_id) WHERE released_at IS NULL;
CREATE INDEX idx_legal_hold_subject ON legal_hold (subject_user_id) WHERE released_at IS NULL;
COMMENT ON TABLE legal_hold IS
  'Stops erasure of an asset, or of everything about a person, until released (S2-03)';

-- Placed once, released once. A hold whose target or reason could be edited
-- after the fact would be a hold nobody could rely on having existed.
CREATE OR REPLACE FUNCTION cmp_legal_hold_release_only() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'legal_hold rows are never deleted' USING ERRCODE = 'restrict_violation';
  END IF;
  IF OLD.released_at IS NOT NULL THEN
    RAISE EXCEPTION 'a released hold does not change' USING ERRCODE = 'restrict_violation';
  END IF;
  IF NEW.hold_id IS DISTINCT FROM OLD.hold_id
     OR NEW.hold_uuid IS DISTINCT FROM OLD.hold_uuid
     OR NEW.asset_id IS DISTINCT FROM OLD.asset_id
     OR NEW.subject_user_id IS DISTINCT FROM OLD.subject_user_id
     OR NEW.reason IS DISTINCT FROM OLD.reason
     OR NEW.placed_by IS DISTINCT FROM OLD.placed_by
     OR NEW.placed_at IS DISTINCT FROM OLD.placed_at THEN
    RAISE EXCEPTION 'only the release of a hold may be recorded' USING ERRCODE = 'restrict_violation';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_legal_hold_release_only
  BEFORE UPDATE OR DELETE ON legal_hold
  FOR EACH ROW EXECUTE FUNCTION cmp_legal_hold_release_only();
"""

DOWNGRADE = """
DROP TABLE IF EXISTS legal_hold;
DROP FUNCTION IF EXISTS cmp_legal_hold_release_only();
DROP TABLE IF EXISTS rights_item_execution;
ALTER TABLE rights_request_item DROP COLUMN IF EXISTS executed_at;
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
  EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON TABLE rights_item_execution FROM %I', r);
  EXECUTE format('REVOKE DELETE, TRUNCATE ON TABLE legal_hold FROM %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE)
    op.execute(_harden(APP_ROLE))


def downgrade() -> None:
    op.execute(DOWNGRADE)
