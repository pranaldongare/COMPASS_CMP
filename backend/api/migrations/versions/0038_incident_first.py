"""An incident is logged first; a breach is recorded on the first yes (S3-06).

The register took every report as a breach from the first keystroke: it gave
each one a `BR-` reference, so the numbers counted suspicions, and a notice to
principals could go out before anyone had decided there was anything to tell.
The order the office works in is the other way round (ADR 0022): an incident
is logged as noticed, the DPO team validates whether it is a personal data
breach under s.2(u), and only a *yes* records one.

`breach.reference` is now the incident's reference, `INC-YYYY-NNNN`, quoted
from logging onwards and drawn from a new sequence. The breach reference,
`BR-YYYY-NNNN`, is issued by the first *yes*, from the existing
`breach_ref_seq`, and lives in `breach_recording` - one row per breach, never
withdrawn: a later *no* sets duties aside, and the recording stays.

A row logged before this revision keeps the `BR-` string it was given as its
incident reference. Where one of its determinations is a *yes*, the recording
is backfilled from the first of them, carrying the same string, so a breach
already quoted to the Board keeps the number it was quoted by. No `breach`
row is touched.

Revision ID: 0038
Revises: 0037
"""

from __future__ import annotations

import os

from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

UPGRADE = """
CREATE SEQUENCE breach_incident_ref_seq;

COMMENT ON COLUMN breach.reference IS
  'The incident reference, INC-YYYY-NNNN, quoted from logging onwards. A row logged before 0038 carries the BR- string it was given. The breach reference is in breach_recording';

CREATE TABLE breach_recording (
  recording_id     serial PRIMARY KEY,
  recording_uuid   uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  breach_id        int NOT NULL UNIQUE REFERENCES breach(breach_id),
  reference        varchar(24) NOT NULL UNIQUE,
  determination_id int NOT NULL REFERENCES breach_determination(determination_id),
  recorded_by      int NOT NULL REFERENCES auth_user(id),
  recorded_at      timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE breach_recording IS
  'An incident recorded as a personal data breach, by the first determination of yes. One per breach; never withdrawn (ADR 0022)';
COMMENT ON COLUMN breach_recording.reference IS
  'The breach reference, BR-YYYY-NNNN, from breach_ref_seq: what principals and the Board are given. BR numbers count recorded breaches only';
COMMENT ON COLUMN breach_recording.determination_id IS
  'The determination of yes that recorded it. A later no sets the DPDP duties aside and leaves this row';
COMMENT ON COLUMN breach_recording.recorded_by IS
  'Who made that determination';
COMMENT ON COLUMN breach_recording.recorded_at IS
  'When it was recorded: the moment of that determination';
CREATE TRIGGER trg_breach_recording_append_only
  BEFORE UPDATE OR DELETE ON breach_recording
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();

-- Rows logged before this revision: a breach with a yes keeps its BR string.
INSERT INTO breach_recording (breach_id, reference, determination_id, recorded_by, recorded_at)
SELECT b.breach_id, b.reference, d.determination_id, d.determined_by, d.determined_at
  FROM breach b
  JOIN LATERAL (
        SELECT determination_id, determined_by, determined_at
          FROM breach_determination
         WHERE breach_id = b.breach_id AND outcome = 'yes'
         ORDER BY determination_id
         LIMIT 1
       ) d ON true;
"""

DOWNGRADE = """
DROP TABLE IF EXISTS breach_recording;
DROP SEQUENCE IF EXISTS breach_incident_ref_seq;
COMMENT ON COLUMN breach.reference IS NULL;
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
  EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON TABLE breach_recording FROM %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE)
    op.execute(_harden(APP_ROLE))


def downgrade() -> None:
    op.execute(DOWNGRADE)
