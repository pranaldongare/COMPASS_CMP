"""The organisation's board within thirty minutes of first noticed (S3-07).

An internal policy asks that the organisation's board hear of an incident
within thirty minutes of its being first noticed (BD-02). The register had a
clock for CERT-In and for every Rule 7 duty, and none for that.

`org_board` is a fifth kind of duty, created for every incident when it is
logged, anchored at `detected_at`, its due time stored then from
`BREACH_ORG_BOARD_MINUTES`. It is not a DPDP duty: validation never sets it
aside or moves it. A person reports to the board; the DPO records when, and to
whom - `reported_to`, sealed like every narrative on the register, and
required on a completion of this duty by trigger as well as by the service.

Incidents logged before this revision get no such duty (BD-11): the policy
applies from the day the platform tracks it, and a duty created now would be
born hours or days overdue for something nobody could have recorded.

Revision ID: 0039
Revises: 0038
"""

from __future__ import annotations

from alembic import op

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None

UPGRADE = """
ALTER TABLE breach_obligation DROP CONSTRAINT breach_obligation_kind;
ALTER TABLE breach_obligation ADD CONSTRAINT breach_obligation_kind CHECK (
  kind IN ('cert_in', 'board_intimation', 'board_report', 'principals', 'org_board')
);

ALTER TABLE breach_obligation_event ADD COLUMN reported_to text;
COMMENT ON COLUMN breach_obligation_event.reported_to IS
  'Whom the organisation''s board was told through, on a completion of the org_board duty. Sealed (FREE_TEXT); required for that duty by trg_breach_org_board_reported_to';

-- A report to the organisation's board is recorded with whom it was made to.
-- The service asks for it; this holds when something else writes the row.
CREATE OR REPLACE FUNCTION cmp_breach_org_board_reported_to() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.kind = 'completed' AND NEW.reported_to IS NULL AND EXISTS (
       SELECT 1 FROM breach_obligation
        WHERE obligation_id = NEW.obligation_id AND kind = 'org_board') THEN
    RAISE EXCEPTION 'a report to the organisation''s board records whom it was made to'
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_breach_org_board_reported_to
  BEFORE INSERT ON breach_obligation_event
  FOR EACH ROW EXECUTE FUNCTION cmp_breach_org_board_reported_to();
"""

DOWNGRADE = """
DROP TRIGGER IF EXISTS trg_breach_org_board_reported_to ON breach_obligation_event;
DROP FUNCTION IF EXISTS cmp_breach_org_board_reported_to();
ALTER TABLE breach_obligation_event DROP COLUMN IF EXISTS reported_to;
-- NOT VALID: an org_board duty already recorded is evidence and stays; the
-- narrower rule applies to rows written after the downgrade.
ALTER TABLE breach_obligation DROP CONSTRAINT breach_obligation_kind;
ALTER TABLE breach_obligation ADD CONSTRAINT breach_obligation_kind CHECK (
  kind IN ('cert_in', 'board_intimation', 'board_report', 'principals')
) NOT VALID;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
