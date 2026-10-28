"""Template versions: the unit Legal approves on the HR track (ADR 0033).

A Legal office template gains versions. A version is the legal text Legal
signs off once - the locked text per language with two slots, `{{purposes}}`
and `{{description}}`, the purposes an activity may choose from with the
ones it must carry, the description slot's guidance and limit, and whether
moving to it needs participants to consent again - and it is `draft`, then
`approved`, then `retired`:

  | Table | Holds |
  |---|---|
  | `template_version` | the version: number, status, the slot's guidance and limit, the re-consent flag; the Rule 3 links, the office contact and the audience, frozen with it (open point F-3); who approved it and when |
  | `template_version_language` | the locked text per language; its hash, set at approval |
  | `template_version_purpose` | the purposes an activity may choose, which are mandatory, and their order |
  | `project.category_id`, `template_version_id`, `activity_description` | an activity: a project of the Legal office, made from an approved version (increment 4) |
  | `notice.template_version_id` | the version an activity's notice was composed from |
  | `consent_link.audience_mode` | `sso` or `otp`; here rather than in 0054, because increment 4's links carry it (open point F-2) |

Approval freezes a version as publication freezes a notice
(`cmp_template_version_freeze`): once it is not a draft, its text, its
purposes and its fields never change, and the only move left is to
`retired`. The placeholders are the service's rule, not the database's: a
text rule belongs where the text is composed.

An activity names an approved version of a template in its own category,
checked when the activity is written and when its version changes - not on
every update, so retiring a version does not stop its activities being
closed (open point F-1). An R&D project names none of the three. A
purpose on an activity's notice is on its version's list.

Versions are the Legal office's: a DPO office template is not versioned
(ADR 0028). The office wall covers the three new tables through
`notice_template`.

Nothing to backfill.

Revision ID: 0053
Revises: 0052
"""

from __future__ import annotations

import os

from alembic import op

revision = "0053"
down_revision = "0052"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

_ALL = "current_setting('app.office', true) = 'all'"

UPGRADE = f"""
CREATE TABLE template_version (
  version_id          serial PRIMARY KEY,
  version_uuid        uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  template_id         int NOT NULL REFERENCES notice_template(template_id),
  version             int NOT NULL,
  status              varchar(12) NOT NULL DEFAULT 'draft',
  reconsent_required  boolean NOT NULL DEFAULT false,
  slot_guidance       text,
  slot_max_length     int NOT NULL DEFAULT 1200,
  withdraw_url        text NOT NULL,
  exercise_rights_url text NOT NULL,
  board_complaint_url text NOT NULL,
  dpo_contact         varchar(255) NOT NULL,
  applicable_to       notice_audience,
  created_by          int NOT NULL REFERENCES auth_user(id),
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  approved_by         int REFERENCES auth_user(id),
  approved_at         timestamptz,
  retired_by          int REFERENCES auth_user(id),
  retired_at          timestamptz,
  CONSTRAINT template_version_once UNIQUE (template_id, version),
  CONSTRAINT template_version_number CHECK (version >= 1),
  CONSTRAINT template_version_status CHECK (status IN ('draft', 'approved', 'retired')),
  CONSTRAINT template_version_approved CHECK ((status = 'draft') = (approved_at IS NULL)),
  CONSTRAINT template_version_approver CHECK ((approved_at IS NULL) = (approved_by IS NULL)),
  CONSTRAINT template_version_retired CHECK ((status = 'retired') = (retired_at IS NOT NULL)),
  CONSTRAINT template_version_retirer CHECK ((retired_at IS NULL) = (retired_by IS NULL)),
  CONSTRAINT template_version_slot CHECK (slot_max_length BETWEEN 100 AND 4000),
  CONSTRAINT template_version_audience CHECK (status = 'draft' OR applicable_to IS NOT NULL)
);
COMMENT ON TABLE template_version IS
  'A version of a Legal office template: the legal text Legal approves once; frozen when approved (ADR 0033)';
COMMENT ON COLUMN template_version.slot_max_length IS
  'The longest description an activity may write into {{description}}, in characters';
COMMENT ON COLUMN template_version.reconsent_required IS
  'Set by Legal when the change is material: an activity moved to it asks its participants again';
CREATE INDEX idx_template_version_template ON template_version (template_id);
CREATE TRIGGER trg_template_version_touch BEFORE UPDATE ON template_version
  FOR EACH ROW EXECUTE FUNCTION cmp_touch_updated_at();

CREATE TABLE template_version_language (
  version_language_id serial PRIMARY KEY,
  version_id          int NOT NULL REFERENCES template_version(version_id),
  language_code       language_code NOT NULL,
  locked_text         text NOT NULL,
  content_hash        text,
  updated_by          int NOT NULL REFERENCES auth_user(id),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT template_version_language_once UNIQUE (version_id, language_code)
);
COMMENT ON COLUMN template_version_language.content_hash IS
  'sha256 of locked_text, set when the version is approved; an activity re-checks it before use';

CREATE TABLE template_version_purpose (
  version_purpose_id  serial PRIMARY KEY,
  version_id          int NOT NULL REFERENCES template_version(version_id),
  purpose_id          int NOT NULL REFERENCES purpose(purpose_id),
  is_mandatory        boolean NOT NULL DEFAULT false,
  display_order       int NOT NULL DEFAULT 0,
  CONSTRAINT template_version_purpose_once UNIQUE (version_id, purpose_id)
);

ALTER TABLE project
  ADD COLUMN category_id int REFERENCES hr_category(category_id),
  ADD COLUMN template_version_id int REFERENCES template_version(version_id),
  ADD COLUMN activity_description text,
  ADD CONSTRAINT project_description_length
    CHECK (activity_description IS NULL OR char_length(activity_description) <= 4000);
COMMENT ON COLUMN project.template_version_id IS
  'An activity''s approved template version (ADR 0033); NULL for every R&D project';
CREATE INDEX idx_project_category ON project (category_id) WHERE category_id IS NOT NULL;
CREATE INDEX idx_project_template_version ON project (template_version_id)
  WHERE template_version_id IS NOT NULL;

ALTER TABLE notice ADD COLUMN template_version_id int REFERENCES template_version(version_id);
CREATE INDEX idx_notice_template_version ON notice (template_version_id)
  WHERE template_version_id IS NOT NULL;

ALTER TABLE consent_link ADD COLUMN audience_mode varchar(4) NOT NULL DEFAULT 'otp',
  ADD CONSTRAINT consent_link_audience_mode CHECK (audience_mode IN ('sso', 'otp'));
COMMENT ON COLUMN consent_link.audience_mode IS
  'How the link signs a person in: sso through the organisation (employees) or otp by a code (ADR 0034)';

-- A version is the Legal office's: its template names a category, which a
-- DPO office template never does (0052).
CREATE FUNCTION cmp_template_version_of_category() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM notice_template t
                  WHERE t.template_id = NEW.template_id AND t.category_id IS NOT NULL) THEN
    RAISE EXCEPTION 'template_version: a DPO office template is not versioned (ADR 0028)'
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_template_version_of_category BEFORE INSERT ON template_version
  FOR EACH ROW EXECUTE FUNCTION cmp_template_version_of_category();

-- Once approved, a version never changes: its fields, its text and its
-- purposes. The one move left is approved -> retired, with who and when.
CREATE FUNCTION cmp_template_version_freeze() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.status = 'draft' THEN
    RETURN NEW;
  END IF;
  IF OLD.status = 'approved' AND NEW.status = 'retired'
     AND NEW.template_id = OLD.template_id
     AND NEW.version = OLD.version
     AND NEW.reconsent_required = OLD.reconsent_required
     AND NEW.slot_guidance IS NOT DISTINCT FROM OLD.slot_guidance
     AND NEW.slot_max_length = OLD.slot_max_length
     AND NEW.withdraw_url = OLD.withdraw_url
     AND NEW.exercise_rights_url = OLD.exercise_rights_url
     AND NEW.board_complaint_url = OLD.board_complaint_url
     AND NEW.dpo_contact = OLD.dpo_contact
     AND NEW.applicable_to IS NOT DISTINCT FROM OLD.applicable_to
     AND NEW.approved_by = OLD.approved_by
     AND NEW.approved_at = OLD.approved_at THEN
    RETURN NEW;
  END IF;
  RAISE EXCEPTION
    USING MESSAGE = 'An approved template version is frozen; open the next version instead',
          ERRCODE = '42501';
END;
$$;
CREATE TRIGGER trg_template_version_freeze BEFORE UPDATE ON template_version
  FOR EACH ROW EXECUTE FUNCTION cmp_template_version_freeze();

CREATE FUNCTION cmp_template_version_part_freeze() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  target int := CASE TG_OP WHEN 'DELETE' THEN OLD.version_id ELSE NEW.version_id END;
  parent varchar(12);
BEGIN
  SELECT status INTO parent FROM template_version WHERE version_id = target;
  IF parent IS DISTINCT FROM 'draft' THEN
    RAISE EXCEPTION
      USING MESSAGE = 'An approved template version is frozen; open the next version instead',
            ERRCODE = '42501';
  END IF;
  IF TG_OP = 'UPDATE' AND NEW.version_id <> OLD.version_id THEN
    RAISE EXCEPTION
      USING MESSAGE = 'A version''s text or purpose does not move to another version',
            ERRCODE = '42501';
  END IF;
  RETURN CASE TG_OP WHEN 'DELETE' THEN OLD ELSE NEW END;
END;
$$;
CREATE TRIGGER trg_template_version_language_freeze
  BEFORE INSERT OR UPDATE OR DELETE ON template_version_language
  FOR EACH ROW EXECUTE FUNCTION cmp_template_version_part_freeze();
CREATE TRIGGER trg_template_version_purpose_freeze
  BEFORE INSERT OR UPDATE OR DELETE ON template_version_purpose
  FOR EACH ROW EXECUTE FUNCTION cmp_template_version_part_freeze();

-- An activity is a project of the Legal office made from an approved
-- version of a template in its category; an R&D project names none of it.
-- Checked when the activity is written and when its version or category
-- changes, never on its other updates (open point F-1).
CREATE FUNCTION cmp_activity_version_coherent() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  rnd int := (SELECT office_id FROM office WHERE office_code = 'rnd');
  v_status varchar(12);
  v_category int;
BEGIN
  IF TG_OP = 'UPDATE'
     AND NEW.template_version_id IS NOT DISTINCT FROM OLD.template_version_id
     AND NEW.category_id IS NOT DISTINCT FROM OLD.category_id THEN
    RETURN NEW;
  END IF;
  IF NEW.office_id = rnd THEN
    IF NEW.category_id IS NOT NULL OR NEW.template_version_id IS NOT NULL
       OR NEW.activity_description IS NOT NULL THEN
      RAISE EXCEPTION 'project: an R&D project names no category, version or description'
        USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
  END IF;
  IF NEW.category_id IS NULL OR NEW.template_version_id IS NULL THEN
    RAISE EXCEPTION 'project: an activity names its category and template version'
      USING ERRCODE = 'check_violation';
  END IF;
  SELECT v.status, t.category_id INTO v_status, v_category
    FROM template_version v JOIN notice_template t ON t.template_id = v.template_id
   WHERE v.version_id = NEW.template_version_id;
  IF v_status IS DISTINCT FROM 'approved' THEN
    RAISE EXCEPTION 'project: an activity is made from an approved template version'
      USING ERRCODE = 'check_violation';
  END IF;
  IF v_category IS DISTINCT FROM NEW.category_id THEN
    RAISE EXCEPTION 'project: the version''s template belongs to another category'
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_activity_version_coherent
  BEFORE INSERT OR UPDATE OF template_version_id, category_id ON project
  FOR EACH ROW EXECUTE FUNCTION cmp_activity_version_coherent();

-- A purpose on an activity's notice is one its version offers.
CREATE FUNCTION cmp_hr_notice_purposes_in_version() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  v int := (SELECT template_version_id FROM notice WHERE notice_id = NEW.notice_id);
BEGIN
  IF v IS NOT NULL AND NOT EXISTS (
       SELECT 1 FROM template_version_purpose
        WHERE version_id = v AND purpose_id = NEW.purpose_id) THEN
    RAISE EXCEPTION 'notice_purpose: the purpose is not on the notice''s template version'
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_hr_notice_purposes_in_version BEFORE INSERT ON notice_purpose
  FOR EACH ROW EXECUTE FUNCTION cmp_hr_notice_purposes_in_version();

ALTER TABLE template_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE template_version FORCE ROW LEVEL SECURITY;
CREATE POLICY office_isolation ON template_version
  USING ({_ALL} OR EXISTS (SELECT 1 FROM notice_template p
                           WHERE p.template_id = template_version.template_id))
  WITH CHECK ({_ALL} OR EXISTS (SELECT 1 FROM notice_template p
                                WHERE p.template_id = template_version.template_id));

ALTER TABLE template_version_language ENABLE ROW LEVEL SECURITY;
ALTER TABLE template_version_language FORCE ROW LEVEL SECURITY;
CREATE POLICY office_isolation ON template_version_language
  USING ({_ALL} OR EXISTS (SELECT 1 FROM template_version p
                           WHERE p.version_id = template_version_language.version_id))
  WITH CHECK ({_ALL} OR EXISTS (SELECT 1 FROM template_version p
                                WHERE p.version_id = template_version_language.version_id));

ALTER TABLE template_version_purpose ENABLE ROW LEVEL SECURITY;
ALTER TABLE template_version_purpose FORCE ROW LEVEL SECURITY;
CREATE POLICY office_isolation ON template_version_purpose
  USING ({_ALL} OR EXISTS (SELECT 1 FROM template_version p
                           WHERE p.version_id = template_version_purpose.version_id))
  WITH CHECK ({_ALL} OR EXISTS (SELECT 1 FROM template_version p
                                WHERE p.version_id = template_version_purpose.version_id));
"""

DOWNGRADE = """
DROP TRIGGER IF EXISTS trg_hr_notice_purposes_in_version ON notice_purpose;
DROP FUNCTION IF EXISTS cmp_hr_notice_purposes_in_version();
DROP TRIGGER IF EXISTS trg_activity_version_coherent ON project;
DROP FUNCTION IF EXISTS cmp_activity_version_coherent();
ALTER TABLE consent_link DROP CONSTRAINT IF EXISTS consent_link_audience_mode;
ALTER TABLE consent_link DROP COLUMN audience_mode;
ALTER TABLE notice DROP COLUMN template_version_id;
ALTER TABLE project DROP CONSTRAINT IF EXISTS project_description_length;
ALTER TABLE project DROP COLUMN activity_description;
ALTER TABLE project DROP COLUMN template_version_id;
ALTER TABLE project DROP COLUMN category_id;
DROP TABLE template_version_purpose;
DROP TABLE template_version_language;
DROP TABLE template_version;
DROP FUNCTION IF EXISTS cmp_template_version_part_freeze();
DROP FUNCTION IF EXISTS cmp_template_version_freeze();
DROP FUNCTION IF EXISTS cmp_template_version_of_category();
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
  EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE template_version TO %I', r);
  EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE template_version_language,
    template_version_purpose TO %I', r);
  EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE template_version_version_id_seq,
    template_version_language_version_language_id_seq,
    template_version_purpose_version_purpose_id_seq TO %I', r);
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
          IF EXISTS (SELECT 1 FROM project WHERE template_version_id IS NOT NULL)
             OR EXISTS (SELECT 1 FROM notice WHERE template_version_id IS NOT NULL) THEN
            RAISE EXCEPTION 'activities are made from template versions; downgrading would orphan them';
          END IF;
          IF EXISTS (SELECT 1 FROM consent_link WHERE audience_mode <> 'otp') THEN
            RAISE EXCEPTION 'links sign people in by SSO; downgrading would turn them into code links';
          END IF;
        END $$;"""
    )
    op.execute(DOWNGRADE)
