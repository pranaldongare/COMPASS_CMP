"""Analytics, reports and the management role (2026-11-23, ADR 0045).

* **`management`** joins `user_role`: a read-only login for the people the
  organisation reports to. It works across both offices, so its account names
  none (`auth_user_office_by_role` is unchanged: management is not an office
  role).
* **`analytics_target`**: the target and the amber line of a metric, set by
  the administrator in the console. A metric with no row uses the default its
  catalogue entry carries (`cmp.core.metrics`).
* **`analytics_setting`**: one row. The small-number threshold - a count of
  people below it is shown as "fewer than N", never as itself. 1 for testing:
  nothing is withheld.
* **`report`**: every report generated, kept until somebody deletes it: what
  it is, for which period and office, the file (by reference, with its
  SHA-256), and who asked or which schedule made it. Its file is frozen: a
  report is not regenerated, it is made again.
* **`report_schedule`**: a report made on a cadence and mailed to the roles
  named, resolved to the active accounts that may read it when it runs.

Both are policed by office: a session of one office reads that office's
reports; a report of both offices is read only by a session of no office.

Revision ID: 0074
Revises: 0073
"""

from __future__ import annotations

import os

from alembic import op

revision = "0074"
down_revision = "0073"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

NEW_ROLE = "ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'management';"

UPGRADE = """
CREATE TABLE analytics_target (
  metric_key  varchar(64) PRIMARY KEY,
  target      numeric NOT NULL,
  amber       numeric,
  updated_by  int NOT NULL REFERENCES auth_user(id),
  updated_at  timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE analytics_target IS
  'The administrator''s target and amber line for a metric; none: the catalogue default';

CREATE TABLE analytics_setting (
  setting_id              int PRIMARY KEY DEFAULT 1 CHECK (setting_id = 1),
  small_number_threshold  int NOT NULL DEFAULT 1 CHECK (small_number_threshold BETWEEN 1 AND 100),
  updated_by              int REFERENCES auth_user(id),
  updated_at              timestamptz NOT NULL DEFAULT now()
);
INSERT INTO analytics_setting (setting_id) VALUES (1);

CREATE TABLE report_schedule (
  schedule_id      serial PRIMARY KEY,
  schedule_uuid    uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  kind             varchar(48) NOT NULL,
  title            text NOT NULL,
  params           jsonb NOT NULL DEFAULT '{{}}'::jsonb,
  format           varchar(8) NOT NULL,
  cadence          varchar(12) NOT NULL,
  recipient_roles  text[] NOT NULL DEFAULT '{{}}',
  office_id        int REFERENCES office(office_id),
  active           boolean NOT NULL DEFAULT true,
  created_by       int NOT NULL REFERENCES auth_user(id),
  created_role     user_role NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT now(),
  last_run_at      timestamptz,
  next_run_at      timestamptz NOT NULL,
  CONSTRAINT report_schedule_format CHECK (format IN ('pdf', 'xlsx', 'csv')),
  CONSTRAINT report_schedule_cadence CHECK (cadence IN ('weekly', 'monthly', 'quarterly'))
);
CREATE INDEX idx_report_schedule_due ON report_schedule (next_run_at) WHERE active;

CREATE TABLE report (
  report_id       serial PRIMARY KEY,
  report_uuid     uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  kind            varchar(48) NOT NULL,
  title           text NOT NULL,
  params          jsonb NOT NULL DEFAULT '{{}}'::jsonb,
  office_id       int REFERENCES office(office_id),
  format          varchar(8) NOT NULL,
  status          varchar(12) NOT NULL DEFAULT 'queued',
  file_ref        text,
  file_sha256     text,
  file_bytes      int,
  error           text,
  requested_by    int REFERENCES auth_user(id),
  requested_role  user_role NOT NULL,
  schedule_id     int REFERENCES report_schedule(schedule_id) ON DELETE SET NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  ready_at        timestamptz,
  CONSTRAINT report_format CHECK (format IN ('pdf', 'xlsx', 'csv')),
  CONSTRAINT report_status CHECK (status IN ('queued', 'ready', 'failed')),
  CONSTRAINT report_ready_has_a_file CHECK (
    status <> 'ready' OR (file_ref IS NOT NULL AND file_sha256 IS NOT NULL)
  )
);
CREATE INDEX idx_report_created ON report (created_at DESC);
CREATE INDEX idx_report_kind ON report (kind, created_at DESC);
CREATE INDEX idx_report_office ON report (office_id);
CREATE INDEX idx_report_schedule_office ON report_schedule (office_id);

-- The wall (ADR 0032): a report of one office is that office's; a report of
-- both - management's combined figures, the administrator's - is read only by
-- a session of no office. An officer's session never reads the other office's
-- figures through a report.
ALTER TABLE report ENABLE ROW LEVEL SECURITY;
ALTER TABLE report FORCE ROW LEVEL SECURITY;
CREATE POLICY office_isolation ON report USING ({rule}) WITH CHECK ({rule});
ALTER TABLE report_schedule ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_schedule FORCE ROW LEVEL SECURITY;
CREATE POLICY office_isolation ON report_schedule USING ({rule}) WITH CHECK ({rule});
""".format(
    rule="current_setting('app.office', true) = 'all' OR office_id = "
    "(SELECT o.office_id FROM office o WHERE o.office_code = current_setting('app.office', true))"
)

DOWNGRADE = """
DROP TABLE IF EXISTS report;
DROP TABLE IF EXISTS report_schedule;
DROP TABLE IF EXISTS analytics_setting;
DROP TABLE IF EXISTS analytics_target;
"""


def _grants(role: str) -> str:
    return f"""
DO $$
DECLARE r text := '{role}';
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN RETURN; END IF;
  EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE analytics_target TO %I', r);
  EXECUTE format('GRANT SELECT, UPDATE ON TABLE analytics_setting TO %I', r);
  EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE report_schedule TO %I', r);
  EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE report TO %I', r);
  EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE report_schedule_schedule_id_seq TO %I', r);
  EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE report_report_id_seq TO %I', r);
END $$;
"""


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(NEW_ROLE)
    op.execute(UPGRADE)
    op.execute(_grants(APP_ROLE))


def downgrade() -> None:
    # The enum value stays: PostgreSQL cannot remove one, and a row may hold it.
    op.execute(DOWNGRADE)
