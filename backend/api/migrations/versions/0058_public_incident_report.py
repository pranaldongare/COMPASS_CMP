"""An incident reported from outside, and who hears of it (2026-11-06).

Anybody who sees something may now report it, through one public link, with
no account. The register could not take that as it stood: a breach names the
office that holds it and the officer who logged it, and an incident logged
there starts its clocks. A stranger's report has neither, and nothing should
run on it until somebody has read it. So it waits apart:

* `incident_report` - what the reporter said, sealed, with the name and the
  email they proved by a code. It takes its `INC-` number when it arrives,
  from the same sequence an incident logged in the console draws on, and
  keeps it when it becomes one. Its outcome is written once: an office
  **claims** it, which logs the incident under that number in that office
  (`breach_id`), or **dismisses** it with a reason. Until then both offices
  see it - it belongs to neither, like a rights request in the shared intake.
  Nothing in it is an office's, so it carries no office and no policy.
* `breach_settings` - one row: which roles are told a report has arrived.
* `breach_board_recipient` - the addresses of the organisation's board, kept
  by the administrator, the DPO and Legal. An address taken off the list stays,
  with who took it off and when: reports already mailed name it.

Revision 0057 is the DataVault branch's and has not landed here. Neither line
is re-pointed at the other when it does: Alembic stores only the head and takes
every ancestor as applied, so a database already at this line's head would
never run the revision a re-point slipped in below it. An Alembic merge revision
joins them, with `down_revision = ("0057", "0063")` or the heads at the time, and
each database then applies the side it lacks.

Revision ID: 0058
Revises: 0056
"""

from __future__ import annotations

import os

from alembic import op

revision = "0058"
down_revision = "0056"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

TEXT = (
    "origin",
    "discovery",
    "affected_systems",
    "incident_details",
    "impact_scale",
    "countries_involved",
    "data_nature",
    "subject_types",
    "entities_involved",
    "third_parties",
)

_COLUMNS = ",\n  ".join(f"{c} text" for c in TEXT)

UPGRADE = f"""
CREATE TABLE incident_report (
  report_id        serial PRIMARY KEY,
  report_uuid      uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  reference        varchar(24) NOT NULL UNIQUE,
  reporter_name    text NOT NULL,
  reporter_email   text NOT NULL,
  title            text NOT NULL,
  -- When they say they noticed it. Theirs: nothing is anchored on it.
  noticed_at       timestamptz,
  {_COLUMNS},
  cyber_attack     varchar(8),
  received_at      timestamptz NOT NULL DEFAULT now(),
  breach_id        int UNIQUE REFERENCES breach(breach_id),
  claimed_by       int REFERENCES auth_user(id),
  claimed_at       timestamptz,
  dismissed_by     int REFERENCES auth_user(id),
  dismissed_at     timestamptz,
  dismissal_reason text,
  CONSTRAINT incident_report_cyber_attack CHECK (cyber_attack IN ('yes', 'no', 'unknown')),
  CONSTRAINT incident_report_claim_whole CHECK (
    (breach_id IS NULL) = (claimed_by IS NULL) AND (claimed_by IS NULL) = (claimed_at IS NULL)),
  CONSTRAINT incident_report_dismissal_whole CHECK (
    (dismissed_by IS NULL) = (dismissed_at IS NULL)
    AND (dismissed_at IS NULL) = (dismissal_reason IS NULL)),
  CONSTRAINT incident_report_one_outcome CHECK (claimed_at IS NULL OR dismissed_at IS NULL)
);
COMMENT ON TABLE incident_report IS
  'An incident reported through the public link, waiting for an office. Both see it until one claims or dismisses it';
COMMENT ON COLUMN incident_report.reference IS
  'INC-YYYY-NNNN, from breach_incident_ref_seq; the incident it becomes keeps it';
COMMENT ON COLUMN incident_report.reporter_name IS 'Sealed (NAME)';
COMMENT ON COLUMN incident_report.reporter_email IS 'Proved by a code before the report was taken. Sealed (EMAIL)';
COMMENT ON COLUMN incident_report.title IS 'Sealed (FREE_TEXT)';
COMMENT ON COLUMN incident_report.dismissal_reason IS 'Why it was not taken up. Sealed (FREE_TEXT)';
CREATE INDEX idx_incident_report_waiting ON incident_report (received_at)
  WHERE claimed_at IS NULL AND dismissed_at IS NULL;

-- What was reported stays as it was said; the outcome is written once.
CREATE FUNCTION cmp_incident_report_outcome_once() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  outcome text[] := ARRAY['breach_id', 'claimed_by', 'claimed_at',
                          'dismissed_by', 'dismissed_at', 'dismissal_reason'];
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'incident reports are never deleted' USING ERRCODE = 'restrict_violation';
  END IF;
  IF OLD.claimed_at IS NOT NULL OR OLD.dismissed_at IS NOT NULL THEN
    RAISE EXCEPTION 'an incident report has its outcome' USING ERRCODE = 'restrict_violation';
  END IF;
  IF (to_jsonb(NEW) - outcome) IS DISTINCT FROM (to_jsonb(OLD) - outcome) THEN
    RAISE EXCEPTION 'only the outcome of an incident report may change'
      USING ERRCODE = 'restrict_violation';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_incident_report_outcome_once
  BEFORE UPDATE OR DELETE ON incident_report
  FOR EACH ROW EXECUTE FUNCTION cmp_incident_report_outcome_once();

CREATE TABLE breach_settings (
  settings_id  smallint PRIMARY KEY DEFAULT 1,
  intake_roles text[] NOT NULL DEFAULT ARRAY['dpo', 'legal'],
  updated_by   int REFERENCES auth_user(id),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT breach_settings_one_row CHECK (settings_id = 1)
);
COMMENT ON TABLE breach_settings IS 'One row: how the office has set the breach workflow up';
COMMENT ON COLUMN breach_settings.intake_roles IS
  'Roles whose active accounts are mailed when a report arrives through the public link';
INSERT INTO breach_settings DEFAULT VALUES;

CREATE TABLE breach_board_recipient (
  recipient_id   serial PRIMARY KEY,
  recipient_uuid uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  full_name      text,
  email          text NOT NULL,
  email_hash     text NOT NULL,
  added_by       int NOT NULL REFERENCES auth_user(id),
  added_at       timestamptz NOT NULL DEFAULT now(),
  removed_by     int REFERENCES auth_user(id),
  removed_at     timestamptz,
  CONSTRAINT breach_board_recipient_removal_whole CHECK ((removed_by IS NULL) = (removed_at IS NULL))
);
COMMENT ON TABLE breach_board_recipient IS
  'The organisation''s board: where its reports are mailed. Taken off, never deleted';
COMMENT ON COLUMN breach_board_recipient.full_name IS 'Optional. Sealed (NAME)';
COMMENT ON COLUMN breach_board_recipient.email IS 'Sealed (EMAIL); email_hash is its blind index';
CREATE UNIQUE INDEX uq_breach_board_recipient_active ON breach_board_recipient (email_hash)
  WHERE removed_at IS NULL;
"""

DOWNGRADE = """
DROP TABLE IF EXISTS breach_board_recipient;
DROP TABLE IF EXISTS breach_settings;
DROP TABLE IF EXISTS incident_report;
DROP FUNCTION IF EXISTS cmp_incident_report_outcome_once();
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
  EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE incident_report TO %I', r);
  EXECUTE format('GRANT SELECT, UPDATE ON TABLE breach_settings TO %I', r);
  EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE breach_board_recipient TO %I', r);
  EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE incident_report_report_id_seq TO %I', r);
  EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE breach_board_recipient_recipient_id_seq TO %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE)
    op.execute(_grants(APP_ROLE))


def downgrade() -> None:
    op.execute(
        """DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM incident_report) THEN
            RAISE EXCEPTION 'incidents were reported; downgrading would lose them';
          END IF;
        END $$;"""
    )
    op.execute(DOWNGRADE)
