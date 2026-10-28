"""The Legal office's registry: categories, their processors, the HR PoCs (ADR 0033).

The HR track's consent is governed per category of HR activity - wellness,
CSR, background verification - not per project. A category is the Legal
office's registry row; the processors that hold data collected under it are
named on it with a default respondent; the HR PoCs who may run activities
under it are assigned to it:

  | Table | Holds |
  |---|---|
  | `hr_category` | the category: a short stable code, a name, active or retired; its office |
  | `category_processor` | a processor holding the category's data, as `hrms`, `database` or `vendor`, with the account that answers for it; removed by date, never deleted |
  | `hr_poc_category` | an HR PoC assigned to a category; a working assignment, removed when it ends |
  | `notice_template.category_id` | a Legal office template belongs to exactly one category; a DPO office template to none |

The office wall (0051) covers the new tables: `hr_category` names its office,
the other two are policed through it. `cmp_office_visible()` is the same test
as the policies, for the queries: scope in the query stays the mechanism and
the policies the backstop (ADR 0032), and in local development the policies do
not bind at all.

Nothing to backfill: every existing template is the DPO office's and keeps no
category.

Revision ID: 0052
Revises: 0051
"""

from __future__ import annotations

import os

from alembic import op

revision = "0052"
down_revision = "0051"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

_ALL = "current_setting('app.office', true) = 'all'"
_MINE = (
    "(SELECT o.office_id FROM office o WHERE o.office_code = current_setting('app.office', true))"
)

UPGRADE = f"""
-- The test the office policies make, for a query's WHERE clause. STABLE and a
-- single expression, so the planner inlines it.
CREATE FUNCTION cmp_office_visible(candidate int) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT {_ALL} OR candidate = {_MINE}
$$;
COMMENT ON FUNCTION cmp_office_visible(int) IS
  'True when a row of this office is visible to the session''s app.office (ADR 0032)';

CREATE TABLE hr_category (
  category_id    serial PRIMARY KEY,
  category_uuid  uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  office_id      int NOT NULL REFERENCES office(office_id),
  category_code  varchar(24) NOT NULL UNIQUE,
  name           varchar(120) NOT NULL,
  description    text,
  status         varchar(12) NOT NULL DEFAULT 'active',
  created_by     int NOT NULL REFERENCES auth_user(id),
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now(),
  retired_at     timestamptz,
  CONSTRAINT hr_category_status CHECK (status IN ('active', 'retired')),
  CONSTRAINT hr_category_retired_at CHECK ((status = 'retired') = (retired_at IS NOT NULL)),
  CONSTRAINT hr_category_code_shape CHECK (category_code ~ '^[A-Z][A-Z0-9_]{{1,23}}$')
);
COMMENT ON TABLE hr_category IS
  'A kind of HR activity the Legal office governs (ADR 0033): its templates and the processors that hold its data';
COMMENT ON COLUMN hr_category.category_code IS
  'Short and stable: WELLNESS, CSR, BGV. Upper case, digits and underscores';
CREATE INDEX idx_hr_category_office ON hr_category (office_id);
CREATE TRIGGER trg_hr_category_touch BEFORE UPDATE ON hr_category
  FOR EACH ROW EXECUTE FUNCTION cmp_touch_updated_at();
CREATE TRIGGER trg_hr_category_office_fixed BEFORE UPDATE OF office_id ON hr_category
  FOR EACH ROW EXECUTE FUNCTION cmp_office_is_fixed();

CREATE TABLE category_processor (
  category_processor_id  serial PRIMARY KEY,
  category_processor_uuid uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  category_id            int NOT NULL REFERENCES hr_category(category_id),
  processor_id           int NOT NULL REFERENCES processor(processor_id),
  processor_role         varchar(12) NOT NULL,
  respondent_user_id     int REFERENCES auth_user(id),
  added_by               int NOT NULL REFERENCES auth_user(id),
  added_at               timestamptz NOT NULL DEFAULT now(),
  removed_at             timestamptz,
  removed_by             int REFERENCES auth_user(id),
  CONSTRAINT category_processor_role CHECK (processor_role IN ('hrms', 'database', 'vendor')),
  CONSTRAINT category_processor_removed CHECK ((removed_at IS NULL) = (removed_by IS NULL))
);
COMMENT ON TABLE category_processor IS
  'A processor holding data collected under a category, with the account that answers for it; removed by date, never deleted';
COMMENT ON COLUMN category_processor.respondent_user_id IS
  'Who answers for this processor on the category''s requests and withdrawals; NULL means the activity''s HR PoC';
CREATE UNIQUE INDEX category_processor_live ON category_processor (category_id, processor_id)
  WHERE removed_at IS NULL;
CREATE INDEX idx_category_processor_category ON category_processor (category_id);

CREATE TABLE hr_poc_category (
  assignment_id  serial PRIMARY KEY,
  user_id        int NOT NULL REFERENCES auth_user(id),
  category_id    int NOT NULL REFERENCES hr_category(category_id),
  assigned_by    int NOT NULL REFERENCES auth_user(id),
  assigned_at    timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT hr_poc_category_once UNIQUE (user_id, category_id)
);
COMMENT ON TABLE hr_poc_category IS
  'An HR PoC assigned to a category: the categories they may run activities in';
CREATE INDEX idx_hr_poc_category_category ON hr_poc_category (category_id);

ALTER TABLE notice_template ADD COLUMN category_id int REFERENCES hr_category(category_id);
COMMENT ON COLUMN notice_template.category_id IS
  'The category of a Legal office template; NULL for every DPO office template';
CREATE INDEX idx_notice_template_category ON notice_template (category_id)
  WHERE category_id IS NOT NULL;

-- A DPO office template has no category; any other office's names one of its
-- own. Read under the caller's office, so a category the session cannot see
-- is refused like one that does not exist.
CREATE FUNCTION cmp_template_category_fits() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  rnd int := (SELECT office_id FROM office WHERE office_code = 'rnd');
  category_office int;
BEGIN
  IF NEW.office_id = rnd THEN
    IF NEW.category_id IS NOT NULL THEN
      RAISE EXCEPTION 'notice_template: a DPO office template has no category'
        USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
  END IF;
  IF NEW.category_id IS NULL THEN
    RAISE EXCEPTION 'notice_template: a Legal office template names its category'
      USING ERRCODE = 'check_violation';
  END IF;
  SELECT office_id INTO category_office FROM hr_category WHERE category_id = NEW.category_id;
  IF category_office IS DISTINCT FROM NEW.office_id THEN
    RAISE EXCEPTION 'notice_template: its category belongs to another office'
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_hr_template_has_category
  BEFORE INSERT OR UPDATE OF category_id, office_id ON notice_template
  FOR EACH ROW EXECUTE FUNCTION cmp_template_category_fits();

ALTER TABLE hr_category ENABLE ROW LEVEL SECURITY;
ALTER TABLE hr_category FORCE ROW LEVEL SECURITY;
CREATE POLICY office_isolation ON hr_category
  USING ({_ALL} OR office_id = {_MINE}) WITH CHECK ({_ALL} OR office_id = {_MINE});

ALTER TABLE category_processor ENABLE ROW LEVEL SECURITY;
ALTER TABLE category_processor FORCE ROW LEVEL SECURITY;
CREATE POLICY office_isolation ON category_processor
  USING ({_ALL} OR EXISTS (SELECT 1 FROM hr_category p
                           WHERE p.category_id = category_processor.category_id))
  WITH CHECK ({_ALL} OR EXISTS (SELECT 1 FROM hr_category p
                                WHERE p.category_id = category_processor.category_id));

ALTER TABLE hr_poc_category ENABLE ROW LEVEL SECURITY;
ALTER TABLE hr_poc_category FORCE ROW LEVEL SECURITY;
CREATE POLICY office_isolation ON hr_poc_category
  USING ({_ALL} OR EXISTS (SELECT 1 FROM hr_category p
                           WHERE p.category_id = hr_poc_category.category_id))
  WITH CHECK ({_ALL} OR EXISTS (SELECT 1 FROM hr_category p
                                WHERE p.category_id = hr_poc_category.category_id));
"""

DOWNGRADE = """
DROP TRIGGER IF EXISTS trg_hr_template_has_category ON notice_template;
DROP FUNCTION IF EXISTS cmp_template_category_fits();
ALTER TABLE notice_template DROP COLUMN category_id;
DROP TABLE hr_poc_category;
DROP TABLE category_processor;
DROP TABLE hr_category;
DROP FUNCTION IF EXISTS cmp_office_visible(int);
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
  EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE hr_category, category_processor TO %I', r);
  EXECUTE format('GRANT SELECT, INSERT, DELETE ON TABLE hr_poc_category TO %I', r);
  EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE hr_category_category_id_seq,
    category_processor_category_processor_id_seq, hr_poc_category_assignment_id_seq TO %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute("SELECT set_config('app.office', 'all', false)")
    op.execute(UPGRADE)
    op.execute(_grants(APP_ROLE))


def downgrade() -> None:
    op.execute("SELECT set_config('app.office', 'all', false)")
    op.execute(
        """DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM notice_template WHERE category_id IS NOT NULL) THEN
            RAISE EXCEPTION 'templates belong to categories; downgrading would orphan them';
          END IF;
        END $$;"""
    )
    op.execute(DOWNGRADE)
