"""The reports a breach calls for, drafted here and told to the board (2026-11-06).

Each report the office writes about a breach now has a home: the one mailed to
the organisation's board, and the drafts of what goes to the DPDP Board and to
CERT-In, for the first intimation, the 72-hour report and a closure.

* `breach_report` - one version of one kind of report. A draft may be edited;
  **finalising** freezes it (`cmp_breach_report_frozen`) and mails the
  organisation's board. **Filing** then records, once, that a person sent it to
  the regulator: when, and the reference returned. The platform never sends it
  there (ADR 0021 stands). One draft per kind at a time; a correction is a new
  version.
* `breach_report_section` - its words, section by section, sealed.
* `breach_report_delivery` - the account of what was mailed to the board, one
  row per state per attempt per address, shaped like `breach_notice_delivery`.
  Why it failed as an error class, never the address.
* `breach_attachment` gains `report_id` and two kinds: `approval`, the proof
  the report was approved internally, and `sent_mail`, the proof it was sent.
  They are evidence like any other, and appear with the rest.

Revision ID: 0059
Revises: 0058
"""

from __future__ import annotations

import os

from alembic import op

revision = "0059"
down_revision = "0058"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

_ALL = "current_setting('app.office', true) = 'all'"

CHILDREN = (
    ("breach_report", "breach", "breach_id", "breach_id"),
    ("breach_report_section", "breach_report", "report_id", "report_id"),
    ("breach_report_delivery", "breach_report", "report_id", "report_id"),
)


def _child_policy(table: str, parent: str, column: str, key: str) -> str:
    rule = f"{_ALL} OR EXISTS (SELECT 1 FROM {parent} p WHERE p.{key} = {table}.{column})"
    return f"""
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
CREATE POLICY office_isolation ON {table} USING ({rule}) WITH CHECK ({rule});
"""


UPGRADE = """
CREATE TABLE breach_report (
  report_id         serial PRIMARY KEY,
  report_uuid       uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  breach_id         int NOT NULL REFERENCES breach(breach_id),
  kind              varchar(16) NOT NULL,
  version           int NOT NULL,
  created_by        int NOT NULL REFERENCES auth_user(id),
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  finalised_by      int REFERENCES auth_user(id),
  finalised_at      timestamptz,
  -- When a person sent it to the regulator, as entered, and what came back.
  filed_at          timestamptz,
  filed_reference   varchar(200),
  filed_by          int REFERENCES auth_user(id),
  filed_recorded_at timestamptz,
  CONSTRAINT breach_report_kind CHECK (
    kind IN ('org_board', 'board_intimation', 'cert_in', 'board_report', 'closure')),
  CONSTRAINT breach_report_version UNIQUE (breach_id, kind, version),
  CONSTRAINT breach_report_finalised_whole CHECK ((finalised_at IS NULL) = (finalised_by IS NULL)),
  CONSTRAINT breach_report_filed_whole CHECK (
    (filed_at IS NULL) = (filed_by IS NULL) AND (filed_at IS NULL) = (filed_recorded_at IS NULL)),
  CONSTRAINT breach_report_filed_after_finalised CHECK (filed_at IS NULL OR finalised_at IS NOT NULL),
  CONSTRAINT breach_report_board_is_not_filed CHECK (kind <> 'org_board' OR filed_at IS NULL)
);
CREATE UNIQUE INDEX uq_breach_report_one_draft ON breach_report (breach_id, kind)
  WHERE finalised_at IS NULL;
COMMENT ON TABLE breach_report IS
  'A version of a report on a breach. Frozen once finalised, which mails the organisation''s board';
COMMENT ON COLUMN breach_report.filed_at IS
  'When a person sent it to the regulator, as entered. The platform never sends it there';
COMMENT ON COLUMN breach_report.filed_reference IS 'What the regulator returned';

CREATE TABLE breach_report_section (
  section_id   serial PRIMARY KEY,
  report_id    int NOT NULL REFERENCES breach_report(report_id),
  ordinal      smallint NOT NULL,
  section_key  varchar(32) NOT NULL,
  body         text,
  CONSTRAINT breach_report_section_once UNIQUE (report_id, section_key)
);
COMMENT ON TABLE breach_report_section IS 'A report''s words, a section at a time. Frozen with the report';
COMMENT ON COLUMN breach_report_section.body IS
  'Sealed (FREE_TEXT). NULL where nothing is written, so completeness reads through the seal';

-- A draft is the office's to edit; what was finalised is what the board was
-- sent, and does not change. Filing is written once, after it.
CREATE FUNCTION cmp_breach_report_frozen() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  filing text[] := ARRAY['filed_at', 'filed_reference', 'filed_by', 'filed_recorded_at'];
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'breach reports are never deleted' USING ERRCODE = 'restrict_violation';
  END IF;
  IF OLD.filed_at IS NOT NULL THEN
    RAISE EXCEPTION 'a filed report does not change' USING ERRCODE = 'restrict_violation';
  END IF;
  IF OLD.finalised_at IS NOT NULL
     AND (to_jsonb(NEW) - filing) IS DISTINCT FROM (to_jsonb(OLD) - filing) THEN
    RAISE EXCEPTION 'a finalised report does not change; write a new version'
      USING ERRCODE = 'restrict_violation';
  END IF;
  IF NEW.report_id IS DISTINCT FROM OLD.report_id
     OR NEW.report_uuid IS DISTINCT FROM OLD.report_uuid
     OR NEW.breach_id IS DISTINCT FROM OLD.breach_id
     OR NEW.kind IS DISTINCT FROM OLD.kind
     OR NEW.version IS DISTINCT FROM OLD.version
     OR NEW.created_by IS DISTINCT FROM OLD.created_by
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'only the state of a report may change' USING ERRCODE = 'restrict_violation';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_breach_report_frozen
  BEFORE UPDATE OR DELETE ON breach_report
  FOR EACH ROW EXECUTE FUNCTION cmp_breach_report_frozen();

CREATE FUNCTION cmp_breach_report_section_frozen() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'a report''s sections are never deleted' USING ERRCODE = 'restrict_violation';
  END IF;
  IF EXISTS (SELECT 1 FROM breach_report r
              WHERE r.report_id = OLD.report_id AND r.finalised_at IS NOT NULL) THEN
    RAISE EXCEPTION 'a finalised report does not change; write a new version'
      USING ERRCODE = 'restrict_violation';
  END IF;
  IF NEW.report_id IS DISTINCT FROM OLD.report_id
     OR NEW.section_key IS DISTINCT FROM OLD.section_key
     OR NEW.ordinal IS DISTINCT FROM OLD.ordinal THEN
    RAISE EXCEPTION 'only the words of a section may change' USING ERRCODE = 'restrict_violation';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_breach_report_section_frozen
  BEFORE UPDATE OR DELETE ON breach_report_section
  FOR EACH ROW EXECUTE FUNCTION cmp_breach_report_section_frozen();

CREATE TABLE breach_report_delivery (
  delivery_id   serial PRIMARY KEY,
  delivery_uuid uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  report_id     int NOT NULL REFERENCES breach_report(report_id),
  recipient_id  int NOT NULL REFERENCES breach_board_recipient(recipient_id),
  attempt       int NOT NULL,
  status        varchar(10) NOT NULL,
  detail        jsonb NOT NULL DEFAULT '{}'::jsonb,
  recorded_at   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT breach_report_delivery_status CHECK (status IN ('queued', 'delivered', 'failed')),
  CONSTRAINT breach_report_delivery_attempt CHECK (attempt >= 1),
  CONSTRAINT breach_report_delivery_once UNIQUE (report_id, recipient_id, attempt, status)
);
CREATE INDEX idx_breach_report_delivery ON breach_report_delivery (report_id, recipient_id);
COMMENT ON TABLE breach_report_delivery IS
  'The account of what was mailed to the organisation''s board, per report and address';
CREATE TRIGGER trg_breach_report_delivery_append_only
  BEFORE UPDATE OR DELETE ON breach_report_delivery
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();

ALTER TABLE breach_attachment ALTER COLUMN kind TYPE varchar(12);
ALTER TABLE breach_attachment ADD COLUMN report_id int REFERENCES breach_report(report_id);
COMMENT ON COLUMN breach_attachment.report_id IS
  'The report this proves: its internal approval, or that it was sent';
ALTER TABLE breach_attachment DROP CONSTRAINT breach_attachment_kind;
ALTER TABLE breach_attachment ADD CONSTRAINT breach_attachment_kind CHECK (
  kind IN ('email', 'proof', 'chat', 'other', 'approval', 'sent_mail'));
ALTER TABLE breach_attachment ADD CONSTRAINT breach_attachment_proves_a_report CHECK (
  (kind IN ('approval', 'sent_mail')) = (report_id IS NOT NULL));
CREATE INDEX idx_breach_attachment_report ON breach_attachment (report_id)
  WHERE report_id IS NOT NULL;
"""

DOWNGRADE = """
DROP INDEX IF EXISTS idx_breach_attachment_report;
ALTER TABLE breach_attachment DROP CONSTRAINT IF EXISTS breach_attachment_proves_a_report;
ALTER TABLE breach_attachment DROP CONSTRAINT breach_attachment_kind;
ALTER TABLE breach_attachment DROP COLUMN report_id;
ALTER TABLE breach_attachment ADD CONSTRAINT breach_attachment_kind CHECK (
  kind IN ('email', 'proof', 'chat', 'other'));
ALTER TABLE breach_attachment ALTER COLUMN kind TYPE varchar(8);
DROP TABLE IF EXISTS breach_report_delivery;
DROP TABLE IF EXISTS breach_report_section;
DROP TABLE IF EXISTS breach_report;
DROP FUNCTION IF EXISTS cmp_breach_report_section_frozen();
DROP FUNCTION IF EXISTS cmp_breach_report_frozen();
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
  EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE breach_report TO %I', r);
  EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE breach_report_section TO %I', r);
  EXECUTE format('GRANT SELECT, INSERT ON TABLE breach_report_delivery TO %I', r);
  EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE breach_report_report_id_seq TO %I', r);
  EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE breach_report_section_section_id_seq TO %I', r);
  EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE breach_report_delivery_delivery_id_seq TO %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute("SELECT set_config('app.office', 'all', false)")
    op.execute(UPGRADE)
    op.execute("\n".join(_child_policy(*c) for c in CHILDREN))
    op.execute(_grants(APP_ROLE))


def downgrade() -> None:
    op.execute("SELECT set_config('app.office', 'all', false)")
    op.execute(
        """DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM breach_report) THEN
            RAISE EXCEPTION 'reports were written; downgrading would lose them';
          END IF;
        END $$;"""
    )
    op.execute(DOWNGRADE)
