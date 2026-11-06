"""The breach tables held to their word (2026-11-06).

Three things 0058 to 0062 left open.

* **Grants.** 0003's default privileges give `cmp_app` everything on a new
  table, and 0058 and 0059 only added to them, so the application's role keeps
  rights the triggers refuse. Taken back in the shape of 0036: the delivery
  account is append-only, the reports and the board's list are never deleted,
  and the settings row is one row, which only ever changes.
* **A finalised report gains no section.** `trg_breach_report_section_frozen`
  guards UPDATE and DELETE. A section inserted later would still appear in the
  report and its PDF, and change what the board was mailed.
* **Duties from the old rule.** Until 0058 every logged incident took an
  `org_board` duty at once and a no left it alone. Now a no sets that duty aside,
  and nothing can complete it short of a yes, so an incident validated no before
  this change could never close without a second no. Each such duty still
  outstanding is set aside here, citing that no. `recorded_by` stays NULL:
  nobody pressed anything, and no audit row is written for the same reason.
  An incident not validated yet keeps its duty until it is.

The events stay on the way down: they are append-only, and they say only what
the no already said. The grants and the rule go back as they were.

Revision ID: 0063
Revises: 0062
"""

from __future__ import annotations

import os

from alembic import op

revision = "0063"
down_revision = "0062"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

UPGRADE = """
CREATE FUNCTION cmp_breach_report_section_no_late_words() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM breach_report r
              WHERE r.report_id = NEW.report_id AND r.finalised_at IS NOT NULL) THEN
    RAISE EXCEPTION 'a finalised report does not change; write a new version'
      USING ERRCODE = 'restrict_violation';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_breach_report_section_no_late_words
  BEFORE INSERT ON breach_report_section
  FOR EACH ROW EXECUTE FUNCTION cmp_breach_report_section_no_late_words();
"""

DOWNGRADE = """
DROP TRIGGER IF EXISTS trg_breach_report_section_no_late_words ON breach_report_section;
DROP FUNCTION IF EXISTS cmp_breach_report_section_no_late_words();
"""

#: Outstanding as `clock.fold` reads it: no event yet, or the last one that moves
#: the state put it back. An extension moves only the date.
SET_ASIDE = """
INSERT INTO breach_obligation_event (obligation_id, kind, determination_id)
SELECT o.obligation_id, 'not_applicable', latest.determination_id
  FROM breach_obligation o
  JOIN LATERAL (
         SELECT d.determination_id, d.outcome FROM breach_determination d
          WHERE d.breach_id = o.breach_id
          ORDER BY d.determination_id DESC LIMIT 1
       ) latest ON true
  LEFT JOIN LATERAL (
         SELECT e.kind FROM breach_obligation_event e
          WHERE e.obligation_id = o.obligation_id AND e.kind <> 'extended'
          ORDER BY e.event_id DESC LIMIT 1
       ) moved ON true
 WHERE o.kind = 'org_board'
   AND latest.outcome = 'no'
   AND (moved.kind IS NULL OR moved.kind IN ('reinstated', 'reopened'));
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
  EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON TABLE breach_report_delivery FROM %I', r);
  EXECUTE format('REVOKE DELETE, TRUNCATE ON TABLE incident_report FROM %I', r);
  EXECUTE format('REVOKE DELETE, TRUNCATE ON TABLE breach_report FROM %I', r);
  EXECUTE format('REVOKE DELETE, TRUNCATE ON TABLE breach_report_section FROM %I', r);
  EXECUTE format('REVOKE DELETE, TRUNCATE ON TABLE breach_board_recipient FROM %I', r);
  EXECUTE format('REVOKE INSERT, DELETE, TRUNCATE ON TABLE breach_settings FROM %I', r);
END $$;
"""


def _restore(role: str) -> str:
    """What 0003's default privileges gave and `_harden` took: never TRUNCATE."""
    return f"""
DO $$
DECLARE r text := {role!r};
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
    RETURN;
  END IF;
  EXECUTE format('GRANT UPDATE, DELETE ON TABLE breach_report_delivery TO %I', r);
  EXECUTE format('GRANT DELETE ON TABLE incident_report TO %I', r);
  EXECUTE format('GRANT DELETE ON TABLE breach_report TO %I', r);
  EXECUTE format('GRANT DELETE ON TABLE breach_report_section TO %I', r);
  EXECUTE format('GRANT DELETE ON TABLE breach_board_recipient TO %I', r);
  EXECUTE format('GRANT INSERT, DELETE ON TABLE breach_settings TO %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute("SELECT set_config('app.office', 'all', false)")
    op.execute(UPGRADE)
    op.execute(SET_ASIDE)
    op.execute(_harden(APP_ROLE))


def downgrade() -> None:
    op.execute(DOWNGRADE)
    op.execute(_restore(APP_ROLE))
