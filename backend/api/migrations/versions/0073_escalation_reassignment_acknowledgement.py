"""A report nobody takes up is escalated; a breach moves to the other office;
the reporter is acknowledged (2026-11-17, ADR 0042).

Three things asked together, each small:

* **Escalation.** A report from the public link that neither office has
  claimed or dismissed within half an hour is mailed to management:
  `breach_escalation_recipient`, a list of its own, apart from the
  organisation's board. `incident_report_escalation` remembers that a report
  was escalated, once, and to how many addresses.
* **Reassignment.** An incident or breach is one office's, and until now its
  office never changed. It may now move to the other office, with who, when
  and why, as a rights request does (0055): `breach.transferred_*`. Nothing
  else about it moves: its status, its clocks, its duties, its people and its
  tickets go with it as they stand. `cmp_breach_office_moves()` replaces the
  fixed-office trigger on `breach`, and `cmp_breach_status_only()` lets the
  stamp change in the statement that moves the office, and at no other time.
* **Acknowledgement.** `incident_report_acknowledgement`: each time an officer
  sent the reporter the word that their report was looked into, and no more
  than that.

Revision ID: 0073
Revises: 0072
"""

from __future__ import annotations

import os

from alembic import op

revision = "0073"
down_revision = "0072"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

UPGRADE = """
CREATE TABLE breach_escalation_recipient (
  recipient_id   serial PRIMARY KEY,
  recipient_uuid uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  full_name      text,
  email          text NOT NULL,
  email_hash     text NOT NULL,
  added_by       int NOT NULL REFERENCES auth_user(id),
  added_at       timestamptz NOT NULL DEFAULT now(),
  removed_by     int REFERENCES auth_user(id),
  removed_at     timestamptz,
  CONSTRAINT breach_escalation_recipient_removal_whole
    CHECK ((removed_by IS NULL) = (removed_at IS NULL))
);
COMMENT ON TABLE breach_escalation_recipient IS
  'Management told when a report from the public link waits unclaimed for half an hour. Apart from the organisation''s board';
COMMENT ON COLUMN breach_escalation_recipient.full_name IS 'Sealed (NAME)';
COMMENT ON COLUMN breach_escalation_recipient.email IS 'Sealed (EMAIL)';
COMMENT ON COLUMN breach_escalation_recipient.email_hash IS 'Blind index of the address: listed once';
COMMENT ON COLUMN breach_escalation_recipient.removed_at IS 'When it was taken off the list; the row is kept';
CREATE UNIQUE INDEX uq_breach_escalation_recipient_active
  ON breach_escalation_recipient (email_hash) WHERE removed_at IS NULL;

CREATE TABLE incident_report_escalation (
  report_id    int PRIMARY KEY REFERENCES incident_report(report_id),
  escalated_at timestamptz NOT NULL DEFAULT now(),
  addresses    int NOT NULL,
  CONSTRAINT incident_report_escalation_addresses CHECK (addresses > 0)
);
COMMENT ON TABLE incident_report_escalation IS
  'A waiting report was escalated to management: once per report, when, and to how many addresses';
CREATE TRIGGER trg_incident_report_escalation_append_only
  BEFORE UPDATE OR DELETE ON incident_report_escalation
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();

CREATE TABLE incident_report_acknowledgement (
  acknowledgement_id serial PRIMARY KEY,
  report_id          int NOT NULL REFERENCES incident_report(report_id),
  sent_by            int NOT NULL REFERENCES auth_user(id),
  sent_at            timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE incident_report_acknowledgement IS
  'Each time an officer sent the reporter an acknowledgement of their report: who and when. Append-only';
CREATE INDEX idx_incident_report_acknowledgement
  ON incident_report_acknowledgement (report_id, acknowledgement_id);
CREATE TRIGGER trg_incident_report_acknowledgement_append_only
  BEFORE UPDATE OR DELETE ON incident_report_acknowledgement
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();

ALTER TABLE breach
  ADD COLUMN transferred_from_office_id int REFERENCES office(office_id),
  ADD COLUMN transferred_at timestamptz,
  ADD COLUMN transferred_by int REFERENCES auth_user(id),
  ADD COLUMN transfer_reason text,
  ADD CONSTRAINT breach_transfer_whole CHECK (
        (transferred_from_office_id IS NULL) = (transferred_at IS NULL)
    AND (transferred_at IS NULL) = (transferred_by IS NULL)
    AND (transferred_at IS NULL) = (transfer_reason IS NULL));
COMMENT ON COLUMN breach.transferred_from_office_id IS
  'The office the last reassignment took it from';
COMMENT ON COLUMN breach.transferred_at IS 'When it was last reassigned to this office';
COMMENT ON COLUMN breach.transferred_by IS 'Who reassigned it';
COMMENT ON COLUMN breach.transfer_reason IS
  'Why the last reassignment moved it to this office; sealed, FREE_TEXT';

-- A breach changes office only by a reassignment: from one office to
-- another, with a new stamp, who and why.
CREATE FUNCTION cmp_breach_office_moves() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.office_id IS NOT DISTINCT FROM OLD.office_id THEN
    RETURN NEW;
  END IF;
  IF NEW.office_id IS NOT NULL
     AND NEW.transferred_from_office_id = OLD.office_id
     AND NEW.transferred_at IS DISTINCT FROM OLD.transferred_at
     AND NEW.transferred_at IS NOT NULL
     AND NEW.transferred_by IS NOT NULL
     AND NEW.transfer_reason IS NOT NULL THEN
    RETURN NEW;
  END IF;
  RAISE EXCEPTION
    USING MESSAGE = 'A breach changes office only by a reassignment',
          ERRCODE = '42501';
END;
$$;
-- The row itself: only its status changes, and - with its office, in the
-- one statement of a reassignment - the stamp of that reassignment.
CREATE OR REPLACE FUNCTION cmp_breach_status_only() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  moves text[] := ARRAY['status', 'office_id', 'transferred_from_office_id',
                        'transferred_at', 'transferred_by', 'transfer_reason'];
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'breach rows are never deleted' USING ERRCODE = 'restrict_violation';
  END IF;
  IF (to_jsonb(NEW) - moves) IS DISTINCT FROM (to_jsonb(OLD) - moves)
     OR (NEW.office_id IS NOT DISTINCT FROM OLD.office_id
         AND (to_jsonb(NEW) - 'status') IS DISTINCT FROM (to_jsonb(OLD) - 'status'))
     OR (NEW.office_id IS DISTINCT FROM OLD.office_id
         AND NEW.status IS DISTINCT FROM OLD.status) THEN
    RAISE EXCEPTION 'only the status of a breach may change' USING ERRCODE = 'restrict_violation';
  END IF;
  RETURN NEW;
END;
$$;
DROP TRIGGER trg_breach_office_fixed ON breach;
CREATE TRIGGER trg_breach_office_moves
  BEFORE UPDATE OF office_id ON breach
  FOR EACH ROW EXECUTE FUNCTION cmp_breach_office_moves();
"""

DOWNGRADE = """
CREATE OR REPLACE FUNCTION cmp_breach_status_only() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'breach rows are never deleted' USING ERRCODE = 'restrict_violation';
  END IF;
  IF (to_jsonb(NEW) - 'status') IS DISTINCT FROM (to_jsonb(OLD) - 'status') THEN
    RAISE EXCEPTION 'only the status of a breach may change' USING ERRCODE = 'restrict_violation';
  END IF;
  RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS trg_breach_office_moves ON breach;
DROP FUNCTION IF EXISTS cmp_breach_office_moves();
CREATE TRIGGER trg_breach_office_fixed BEFORE UPDATE OF office_id ON breach
  FOR EACH ROW EXECUTE FUNCTION cmp_office_is_fixed();
ALTER TABLE breach
  DROP CONSTRAINT breach_transfer_whole,
  DROP COLUMN transferred_from_office_id,
  DROP COLUMN transferred_at,
  DROP COLUMN transferred_by,
  DROP COLUMN transfer_reason;
DROP TABLE IF EXISTS incident_report_acknowledgement;
DROP TABLE IF EXISTS incident_report_escalation;
DROP TABLE IF EXISTS breach_escalation_recipient;
"""


def _grants(role: str) -> str:
    return f"""
DO $$
DECLARE r text := '{role}';
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN RETURN; END IF;
  EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE breach_escalation_recipient TO %I', r);
  EXECUTE format('GRANT SELECT, INSERT ON TABLE incident_report_escalation TO %I', r);
  EXECUTE format('GRANT SELECT, INSERT ON TABLE incident_report_acknowledgement TO %I', r);
  EXECUTE format(
    'GRANT USAGE, SELECT ON SEQUENCE breach_escalation_recipient_recipient_id_seq TO %I', r);
  EXECUTE format(
    'GRANT USAGE, SELECT ON SEQUENCE incident_report_acknowledgement_acknowledgement_id_seq TO %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE)
    op.execute(_grants(APP_ROLE))


def downgrade() -> None:
    op.execute("SELECT set_config('app.office', 'all', false)")
    # As 0055 does for a request: a breach that moved stays where it went, and
    # dropping the stamp would lose where it came from.
    op.execute(
        """DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM breach WHERE transferred_at IS NOT NULL) THEN
            RAISE EXCEPTION 'breaches were reassigned; downgrading would lose where they came from';
          END IF;
        END $$;"""
    )
    op.execute(DOWNGRADE)
