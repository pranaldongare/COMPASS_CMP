"""What is known when an incident is logged (2026-10-08).

Log an incident asked for a title, when it was noticed and began, and where it
happened. The Privacy Office's intake asks more, and every answer is optional -
at the moment of logging, much is not known yet:

| Column | Asks |
|---|---|
| `origin` | Where it started |
| `discovery` | How and where it was found |
| `affected_systems` | The systems, applications, databases, servers or networks involved |
| `incident_details` | What happened, as far as is known |
| `impact_scale` | How much is affected: records, people, files |
| `countries_involved` | Countries involved, where data crossed a border |
| `data_nature` | The kinds of personal data: identifying, sensitive |
| `subject_types` | Whose data: participants, employees, customers |
| `entities_involved` | Which of the organisation's own entities are involved or affected |
| `third_parties` | Vendors, service providers, processors or partners involved |
| `cyber_attack` | Whether it is a cyber attack: yes, no, or not known yet. Yes makes it reportable to CERT-In, as Mark reportable to CERT-In does |

All but `cyber_attack` are free text, sealed (FREE_TEXT) like every narrative
about a breach - any of them may name a person or a company. They are the
incident *as logged*: like the rest of the row they never change afterwards;
what is learned later is the assessment's.

`cmp_breach_status_only` named every column that may not change, so a new
column would have been changeable. It now compares the whole row but its
status, which keeps every column - these and any later one - fixed.

Revision ID: 0047
Revises: 0046
"""

from __future__ import annotations

from alembic import op

revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None

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

STATUS_ONLY = """
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
"""

OLD_STATUS_ONLY = """
CREATE OR REPLACE FUNCTION cmp_breach_status_only() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'breach rows are never deleted' USING ERRCODE = 'restrict_violation';
  END IF;
  IF NEW.breach_id IS DISTINCT FROM OLD.breach_id
     OR NEW.breach_uuid IS DISTINCT FROM OLD.breach_uuid
     OR NEW.reference IS DISTINCT FROM OLD.reference
     OR NEW.title IS DISTINCT FROM OLD.title
     OR NEW.detected_at IS DISTINCT FROM OLD.detected_at
     OR NEW.began_at IS DISTINCT FROM OLD.began_at
     OR NEW.location_kind IS DISTINCT FROM OLD.location_kind
     OR NEW.location_processor_id IS DISTINCT FROM OLD.location_processor_id
     OR NEW.location_source_id IS DISTINCT FROM OLD.location_source_id
     OR NEW.location_detail IS DISTINCT FROM OLD.location_detail
     OR NEW.recorded_by IS DISTINCT FROM OLD.recorded_by
     OR NEW.recorded_at IS DISTINCT FROM OLD.recorded_at THEN
    RAISE EXCEPTION 'only the status of a breach may change' USING ERRCODE = 'restrict_violation';
  END IF;
  RETURN NEW;
END;
$$;
"""


def upgrade() -> None:
    for column in TEXT:
        op.execute(f"ALTER TABLE breach ADD COLUMN {column} text")
        op.execute(
            f"COMMENT ON COLUMN breach.{column} IS 'As logged; optional; sealed (FREE_TEXT)'"
        )
    op.execute(
        """ALTER TABLE breach ADD COLUMN cyber_attack varchar(8)
             CONSTRAINT breach_cyber_attack CHECK (cyber_attack IN ('yes', 'no', 'unknown'))"""
    )
    op.execute(
        "COMMENT ON COLUMN breach.cyber_attack IS "
        "'As logged: yes, no or unknown. Yes made it reportable to CERT-In'"
    )
    op.execute(STATUS_ONLY)


def downgrade() -> None:
    op.execute(OLD_STATUS_ONLY)
    op.execute("ALTER TABLE breach DROP COLUMN IF EXISTS cyber_attack")
    for column in TEXT:
        op.execute(f"ALTER TABLE breach DROP COLUMN IF EXISTS {column}")
