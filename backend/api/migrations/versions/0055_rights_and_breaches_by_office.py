"""Rights requests and breaches by office: claim and transfer (ADR 0032, 0033).

A rights request belongs to the office whose notices the person holds a
consent on - or, until somebody knows, to neither: the shared intake,
`office_id IS NULL`, which both offices' queues show. An office claims a
request from the intake, or transfers one it holds to the other office with
a reason; the clock never moves:

  | Column | Holds |
  |---|---|
  | `rights_request.claimed_at`, `claimed_by` | when and by whom it left the shared intake |
  | `rights_request.transferred_from_office_id`, `transferred_at`, `transferred_by`, `transfer_reason` | the last transfer: from which office, when, by whom, why (sealed) - all four or none |

`cmp_rights_request_office_moves()` is the rule: `office_id` changes only
from NULL with `claimed_at` and `claimed_by` set in the same statement (a
claim), or with a new `transferred_at` and the other three (a transfer); any
other change to it is refused. A second transfer must stamp a new time, so
"the four columns are set" cannot be met by a first transfer's leftovers
(open point F-12).

A legal hold names its office too (open point F-21), so each office lists
and releases its own: `legal_hold.office_id`, NOT NULL, policed like every
office-bearing table and fixed once written. Every hold placed so far is the
DPO office's - nobody else could place one - so the column is added with
`rnd` as its default and the default dropped; no row is updated, which the
hold's own trigger would refuse for a released one.

`rights_holder_source.activity_processor` arrived in 0054 (open point F-23).
Breaches already name their office (0051); nothing here changes them.

Revision ID: 0055
Revises: 0054
"""

from __future__ import annotations

from alembic import op

revision = "0055"
down_revision = "0054"
branch_labels = None
depends_on = None

UPGRADE = """
ALTER TABLE rights_request
  ADD COLUMN claimed_at timestamptz,
  ADD COLUMN claimed_by int REFERENCES auth_user(id),
  ADD COLUMN transferred_from_office_id int REFERENCES office(office_id),
  ADD COLUMN transferred_at timestamptz,
  ADD COLUMN transferred_by int REFERENCES auth_user(id),
  ADD COLUMN transfer_reason text,
  ADD CONSTRAINT rights_request_claimed CHECK ((claimed_at IS NULL) = (claimed_by IS NULL)),
  ADD CONSTRAINT rights_request_transfer_whole CHECK (
        (transferred_from_office_id IS NULL) = (transferred_at IS NULL)
    AND (transferred_at IS NULL) = (transferred_by IS NULL)
    AND (transferred_at IS NULL) = (transfer_reason IS NULL));
COMMENT ON COLUMN rights_request.transfer_reason IS
  'Why the last transfer moved the request to this office; sealed, FREE_TEXT';
COMMENT ON COLUMN rights_request.claimed_at IS
  'When an office took the request from the shared intake';

CREATE FUNCTION cmp_rights_request_office_moves() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.office_id IS NOT DISTINCT FROM OLD.office_id THEN
    RETURN NEW;
  END IF;
  -- A claim: out of the shared intake, with who and when.
  IF OLD.office_id IS NULL AND NEW.office_id IS NOT NULL
     AND NEW.claimed_at IS NOT NULL AND NEW.claimed_by IS NOT NULL
     AND OLD.claimed_at IS NULL THEN
    RETURN NEW;
  END IF;
  -- A transfer: from one office to another, with a new stamp and its reason.
  IF OLD.office_id IS NOT NULL AND NEW.office_id IS NOT NULL
     AND NEW.transferred_from_office_id = OLD.office_id
     AND NEW.transferred_at IS DISTINCT FROM OLD.transferred_at
     AND NEW.transferred_at IS NOT NULL
     AND NEW.transferred_by IS NOT NULL
     AND NEW.transfer_reason IS NOT NULL THEN
    RETURN NEW;
  END IF;
  RAISE EXCEPTION
    USING MESSAGE = 'A rights request changes office only by a claim or a transfer',
          ERRCODE = '42501';
END;
$$;
CREATE TRIGGER trg_rights_request_office_moves
  BEFORE UPDATE OF office_id ON rights_request
  FOR EACH ROW EXECUTE FUNCTION cmp_rights_request_office_moves();

DO $$
BEGIN
  EXECUTE format(
    'ALTER TABLE legal_hold ADD COLUMN office_id int NOT NULL DEFAULT %s REFERENCES office(office_id)',
    (SELECT office_id FROM office WHERE office_code = 'rnd'));
END $$;
ALTER TABLE legal_hold ALTER COLUMN office_id DROP DEFAULT;
CREATE INDEX idx_legal_hold_office ON legal_hold (office_id);
COMMENT ON COLUMN legal_hold.office_id IS
  'The office whose hold it is: the asset''s project''s, or the placing officer''s for a person';
CREATE TRIGGER trg_legal_hold_office_fixed BEFORE UPDATE OF office_id ON legal_hold
  FOR EACH ROW EXECUTE FUNCTION cmp_office_is_fixed();
ALTER TABLE legal_hold ENABLE ROW LEVEL SECURITY;
ALTER TABLE legal_hold FORCE ROW LEVEL SECURITY;
CREATE POLICY office_isolation ON legal_hold USING ({rule}) WITH CHECK ({rule});
""".format(
    rule="current_setting('app.office', true) = 'all' OR office_id = "
    "(SELECT o.office_id FROM office o WHERE o.office_code = current_setting('app.office', true))"
)

DOWNGRADE = """
DROP POLICY IF EXISTS office_isolation ON legal_hold;
ALTER TABLE legal_hold NO FORCE ROW LEVEL SECURITY;
ALTER TABLE legal_hold DISABLE ROW LEVEL SECURITY;
DROP TRIGGER IF EXISTS trg_legal_hold_office_fixed ON legal_hold;
ALTER TABLE legal_hold DROP COLUMN office_id;
DROP TRIGGER IF EXISTS trg_rights_request_office_moves ON rights_request;
DROP FUNCTION IF EXISTS cmp_rights_request_office_moves();
ALTER TABLE rights_request
  DROP CONSTRAINT IF EXISTS rights_request_transfer_whole,
  DROP CONSTRAINT IF EXISTS rights_request_claimed,
  DROP COLUMN transfer_reason,
  DROP COLUMN transferred_by,
  DROP COLUMN transferred_at,
  DROP COLUMN transferred_from_office_id,
  DROP COLUMN claimed_by,
  DROP COLUMN claimed_at;
"""


def upgrade() -> None:
    op.execute("SELECT set_config('app.office', 'all', false)")
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute("SELECT set_config('app.office', 'all', false)")
    op.execute(
        """DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM rights_request WHERE transferred_at IS NOT NULL) THEN
            RAISE EXCEPTION 'requests were transferred; downgrading would lose where they came from';
          END IF;
          IF EXISTS (SELECT 1 FROM legal_hold h JOIN office o USING (office_id)
                      WHERE o.office_code <> 'rnd') THEN
            RAISE EXCEPTION 'the Legal office placed holds; downgrading would give them to the DPO';
          END IF;
        END $$;"""
    )
    op.execute(DOWNGRADE)
