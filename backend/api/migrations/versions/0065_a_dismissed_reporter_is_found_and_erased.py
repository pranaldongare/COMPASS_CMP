"""A dismissed report's reporter is found by a rights request, and erased (2026-11-07).

The product owner's fifth answer of 2026-11-07 (ADR 0037). A report from the
public link that an office dismissed has no incident behind it, so no record
of accountability stands on it, and the person who sent it may ask what is
held about them and have their name and email taken off it.

* **Found by the address.** `incident_report` gains `reporter_email_hash`, the
  same blind index as `auth_user.email_hash`, so a verified request finds the
  reports its subject sent without opening a single sealed value. It is written
  with the report and never after.
* **Erased once.** `reporter_name` and `reporter_email` may now be NULL, but
  only together with the index and only by an erasure, which names when, who
  and the rights request it was done under, and which only a dismissed report
  allows. `cmp_incident_report_outcome_once` keeps its name and its trigger, so
  reseal and the catalogue test read it as before: its new body lets a
  dismissed, unerased row be blanked once and changes nothing else about it.
  The number, the words, the reason and who dismissed it stay.

**The backfill runs in Python** because the key is not in the database: each
address is opened through the key service, as 0028 and 0030 opened theirs, and
its index written back. A key service that cannot be reached fails the
migration, which is right: a half-filled index is a search that silently misses
rows. A value still in the clear (a row written with DKMS off) is hashed as it
stands. The trigger is set aside for the length of this transaction, as
`scripts/reseal.py` sets it aside, because it refuses any change to a waiting
row's words. Production has never run 0058, so it holds no rows and the
backfill does nothing there.

The way down is refused once anybody has been erased: going down would need
their name and address back.

Revision ID: 0065
Revises: 0064
"""

from __future__ import annotations

import sys
from pathlib import Path

from alembic import op

revision = "0065"
down_revision = "0064"
branch_labels = None
depends_on = None

# The application's own hashing and unsealing, so the migration and the code
# agree about every index they compute.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from cmp.infrastructure.dkms.blind import index_of  # noqa: E402
from cmp.infrastructure.dkms.client import unseal_values_sync  # noqa: E402

ADD = """
ALTER TABLE incident_report
  ADD COLUMN reporter_email_hash        text,
  ADD COLUMN reporter_erased_at         timestamptz,
  ADD COLUMN reporter_erased_by         int REFERENCES auth_user(id),
  ADD COLUMN reporter_erased_request_id int REFERENCES rights_request(request_id);
"""

#: No address without its index and no index without the address, and both go
#: only by an erasure: stronger than 0028's `<column>_indexed`, which allowed an
#: index on its own.
CONSTRAIN = """
ALTER TABLE incident_report
  ALTER COLUMN reporter_name  DROP NOT NULL,
  ALTER COLUMN reporter_email DROP NOT NULL,
  ADD CONSTRAINT incident_report_reporter_until_erased CHECK (
        (reporter_erased_at IS NULL) = (reporter_name IS NOT NULL)
    AND (reporter_erased_at IS NULL) = (reporter_email IS NOT NULL)
    AND (reporter_erased_at IS NULL) = (reporter_email_hash IS NOT NULL)),
  ADD CONSTRAINT incident_report_erasure_whole CHECK (
        (reporter_erased_at IS NULL) = (reporter_erased_by IS NULL)
    AND (reporter_erased_at IS NULL) = (reporter_erased_request_id IS NULL)),
  ADD CONSTRAINT incident_report_erased_once_dismissed CHECK (
        reporter_erased_at IS NULL OR dismissed_at IS NOT NULL);
CREATE INDEX idx_incident_report_reporter_email_hash ON incident_report (reporter_email_hash)
  WHERE dismissed_at IS NOT NULL;
COMMENT ON COLUMN incident_report.reporter_name IS
  'Sealed (NAME). NULL once erased under a rights request, which only a dismissed report allows';
COMMENT ON COLUMN incident_report.reporter_email IS
  'Proved by a code before the report was taken. Sealed (EMAIL); reporter_email_hash is its blind index. NULL once erased';
COMMENT ON COLUMN incident_report.reporter_email_hash IS
  'index_of(''email'', address), the same index as auth_user.email_hash: how a rights request finds a dismissed report. NULL once erased';
COMMENT ON COLUMN incident_report.reporter_erased_at IS
  'When the reporter''s name and email were erased, under reporter_erased_request_id, by reporter_erased_by. The number, the words, the reason and who dismissed it stay';
"""

#: The one write a dismissed report allows after its outcome: its reporter
#: blanked, once. The hash is in neither list, so it is written only with the
#: row, which this trigger never sees.
OUTCOME_ONCE = """
CREATE OR REPLACE FUNCTION cmp_incident_report_outcome_once() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  outcome text[] := ARRAY['breach_id', 'claimed_by', 'claimed_at',
                          'dismissed_by', 'dismissed_at', 'dismissal_reason'];
  erasure text[] := ARRAY['reporter_name', 'reporter_email', 'reporter_email_hash',
                          'reporter_erased_at', 'reporter_erased_by', 'reporter_erased_request_id'];
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'incident reports are never deleted' USING ERRCODE = 'restrict_violation';
  END IF;
  -- A dismissed report's reporter is erased once, under a rights request: the
  -- name, the address and its index go, and nothing else moves.
  IF OLD.dismissed_at IS NOT NULL AND OLD.reporter_erased_at IS NULL
     AND NEW.reporter_erased_at IS NOT NULL THEN
    IF NEW.reporter_name IS NOT NULL OR NEW.reporter_email IS NOT NULL
       OR NEW.reporter_email_hash IS NOT NULL
       OR (to_jsonb(NEW) - erasure) IS DISTINCT FROM (to_jsonb(OLD) - erasure) THEN
      RAISE EXCEPTION 'erasing a reporter blanks their name and address and changes nothing else'
        USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
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
"""

GUARD = """DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM incident_report WHERE reporter_erased_at IS NOT NULL) THEN
    RAISE EXCEPTION 'a reporter was erased; going down would need their name and address back';
  END IF;
END $$;"""

#: 0058's body, word for word: what was reported stays as it was said.
DOWNGRADE = """
CREATE OR REPLACE FUNCTION cmp_incident_report_outcome_once() RETURNS trigger
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
DROP INDEX idx_incident_report_reporter_email_hash;
ALTER TABLE incident_report
  DROP CONSTRAINT incident_report_erased_once_dismissed,
  DROP CONSTRAINT incident_report_erasure_whole,
  DROP CONSTRAINT incident_report_reporter_until_erased,
  ALTER COLUMN reporter_name  SET NOT NULL,
  ALTER COLUMN reporter_email SET NOT NULL,
  DROP COLUMN reporter_erased_request_id,
  DROP COLUMN reporter_erased_by,
  DROP COLUMN reporter_erased_at,
  DROP COLUMN reporter_email_hash;
COMMENT ON COLUMN incident_report.reporter_name IS 'Sealed (NAME)';
COMMENT ON COLUMN incident_report.reporter_email IS 'Proved by a code before the report was taken. Sealed (EMAIL)';
"""

#: How many addresses are opened in one call to the key service, as 0030 does.
BATCH = 500


def _backfill() -> None:
    """Every report's address gets its index, in this transaction."""
    conn = op.get_bind()
    conn.exec_driver_sql(
        "ALTER TABLE incident_report DISABLE TRIGGER trg_incident_report_outcome_once"
    )
    rows = conn.exec_driver_sql(
        "SELECT report_id, reporter_email FROM incident_report ORDER BY report_id"
    ).fetchall()
    for start in range(0, len(rows), BATCH):
        batch = rows[start : start + BATCH]
        values = [str(value) for _, value in batch]
        # Only what is sealed goes to the key service; a value in the clear is
        # hashed as it stands.
        sealed = [v for v in values if v.startswith("SE::")]
        opened = dict(zip(sealed, unseal_values_sync(sealed), strict=True)) if sealed else {}
        for (report_id, _), value in zip(batch, values, strict=True):
            conn.exec_driver_sql(
                "UPDATE incident_report SET reporter_email_hash = %s WHERE report_id = %s",
                (index_of("email", opened.get(value, value)), report_id),
            )
    conn.exec_driver_sql(
        "ALTER TABLE incident_report ENABLE TRIGGER trg_incident_report_outcome_once"
    )


def upgrade() -> None:
    op.execute(ADD)
    _backfill()
    op.execute(CONSTRAIN)
    op.execute(OUTCOME_ONCE)


def downgrade() -> None:
    op.execute(GUARD)
    op.execute(DOWNGRADE)
