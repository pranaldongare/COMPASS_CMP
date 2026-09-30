"""The breach register and its obligations (S3-01).

A personal data breach under s.2(u) starts duties that run in parallel on
separate clocks: CERT-In within six hours of noticing a reportable cyber
incident, and - once the event is determined to be a personal data breach -
an initial intimation to the Board and notices to every affected principal
without delay, and the Board's detailed report within 72 hours of becoming
aware (Rule 7). Nothing in the platform recorded any of it.

`breach` is the record: three times kept apart because each anchors a
different duty, all entered by the DPO and never defaulted to the moment of
saving; where it occurred; open or closed. Only its status changes, by
trigger, and each change is a row in `breach_status_history`.

`breach_determination` is whether the event is a personal data breach - a
person's judgement, recorded with its reasoning, never computed. A revision
is a new row; the latest is current. *Yes* carries the moment the
organisation became aware, which anchors every DPDP clock.

`breach_assessment` holds the facts Rule 7 asks for, revised by new rows as
knowledge grows. The exposed data categories are a list, each with whether it
was sealed and whether its key was exposed, because DKMS seals fields and not
relationships and one yes-or-no would be too coarse.

`breach_obligation` is one row per duty, with its due time stored when it is
created and never recomputed. `breach_obligation_event` is everything that
happens to a duty afterwards - completed with the regulator's reference, not
applicable after a determination of *no*, reinstated after a later *yes*,
extended by the Board, reopened when more people are found. Both are
append-only. The duty's state is read from its events.

Every free-text field is sealed; the trail records that text was given, never
the text (ADR 0015).

Revision ID: 0034
Revises: 0033
"""

from __future__ import annotations

import os

from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

UPGRADE = """
CREATE SEQUENCE breach_ref_seq;

CREATE TABLE breach (
  breach_id             serial PRIMARY KEY,
  breach_uuid           uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  -- What the office quotes to the Board and to CERT-In. Never reused.
  reference             varchar(24) NOT NULL UNIQUE,
  title                 text NOT NULL,
  -- When it was first noticed. Anchors CERT-In.
  detected_at           timestamptz NOT NULL,
  -- When it started, as first recorded. An assessment may revise it.
  began_at              timestamptz,
  location_kind         varchar(12) NOT NULL,
  location_processor_id int REFERENCES processor(processor_id),
  location_source_id    int REFERENCES data_source(source_id),
  location_detail       text,
  status                varchar(8) NOT NULL DEFAULT 'open',
  recorded_by           int NOT NULL REFERENCES auth_user(id),
  recorded_at           timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT breach_location_kind CHECK (location_kind IN ('platform', 'processor', 'data_source', 'other')),
  CONSTRAINT breach_status CHECK (status IN ('open', 'closed')),
  CONSTRAINT breach_began_before_detected CHECK (began_at IS NULL OR began_at <= detected_at),
  CONSTRAINT breach_location_named CHECK (
    (location_kind = 'processor') = (location_processor_id IS NOT NULL)
    AND (location_kind = 'data_source') = (location_source_id IS NOT NULL)
  )
);
COMMENT ON TABLE breach IS
  'A suspected or confirmed personal data breach (s.8(6), Rule 7). Only status changes; see breach_status_history';
COMMENT ON COLUMN breach.detected_at IS
  'When it was first noticed, as entered by the DPO. Anchors the CERT-In clock';

-- Only the status of a breach moves. Everything else about it was entered
-- once, and the clocks stored from it would disagree with an edited value.
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
CREATE TRIGGER trg_breach_status_only
  BEFORE UPDATE OR DELETE ON breach
  FOR EACH ROW EXECUTE FUNCTION cmp_breach_status_only();

CREATE TABLE breach_status_history (
  history_id   serial PRIMARY KEY,
  breach_id    int NOT NULL REFERENCES breach(breach_id),
  from_status  varchar(8),
  to_status    varchar(8) NOT NULL,
  reason       text,
  changed_by   int NOT NULL REFERENCES auth_user(id),
  changed_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_breach_status_history ON breach_status_history (breach_id, history_id);
CREATE TRIGGER trg_breach_status_history_append_only
  BEFORE UPDATE OR DELETE ON breach_status_history
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();

CREATE TABLE breach_determination (
  determination_id   serial PRIMARY KEY,
  determination_uuid uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  breach_id          int NOT NULL REFERENCES breach(breach_id),
  outcome            varchar(8) NOT NULL,
  reasoning          text NOT NULL,
  -- When the organisation became aware a personal data breach had occurred.
  -- Anchors every DPDP duty (Rule 7(1), 7(2)). Entered, never defaulted.
  became_aware_at    timestamptz,
  determined_by      int NOT NULL REFERENCES auth_user(id),
  determined_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT breach_determination_outcome CHECK (outcome IN ('pending', 'yes', 'no')),
  CONSTRAINT breach_determination_aware_when_yes CHECK ((outcome = 'yes') = (became_aware_at IS NOT NULL))
);
CREATE INDEX idx_breach_determination ON breach_determination (breach_id, determination_id);
CREATE TRIGGER trg_breach_determination_append_only
  BEFORE UPDATE OR DELETE ON breach_determination
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();

CREATE TABLE breach_assessment (
  assessment_id      serial PRIMARY KEY,
  assessment_uuid    uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  breach_id          int NOT NULL REFERENCES breach(breach_id),
  revision           int NOT NULL,
  began_at           timestamptz,
  nature_extent      text,
  likely_impact      text,
  consequences       text,
  -- [{"category": ..., "sealed": bool, "key_exposed": bool}]: a label per
  -- category and two facts about it. Never a value about a person.
  categories         jsonb NOT NULL DEFAULT '[]'::jsonb,
  circumstances      text,
  mitigation         text,
  protective_steps   text,
  caused_by_findings text,
  remedial_measures  text,
  contact_point      text,
  revised_by         int NOT NULL REFERENCES auth_user(id),
  revised_at         timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT breach_assessment_revision UNIQUE (breach_id, revision),
  CONSTRAINT breach_assessment_categories_list CHECK (jsonb_typeof(categories) = 'array')
);
CREATE TRIGGER trg_breach_assessment_append_only
  BEFORE UPDATE OR DELETE ON breach_assessment
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();

CREATE TABLE breach_obligation (
  obligation_id    serial PRIMARY KEY,
  obligation_uuid  uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  breach_id        int NOT NULL REFERENCES breach(breach_id),
  kind             varchar(20) NOT NULL,
  -- Stored when the duty is created and never recomputed. NULL is "without
  -- delay", which has no statutory hours.
  due_at           timestamptz,
  -- The moment the clock runs from: detection for CERT-In, awareness for the
  -- rest. NULL for a duty created not applicable.
  anchored_at      timestamptz,
  determination_id int REFERENCES breach_determination(determination_id),
  created_by       int NOT NULL REFERENCES auth_user(id),
  created_at       timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT breach_obligation_kind CHECK (kind IN ('cert_in', 'board_intimation', 'board_report', 'principals')),
  CONSTRAINT breach_obligation_once UNIQUE (breach_id, kind)
);
CREATE TRIGGER trg_breach_obligation_append_only
  BEFORE UPDATE OR DELETE ON breach_obligation
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();

CREATE TABLE breach_obligation_event (
  event_id         serial PRIMARY KEY,
  event_uuid       uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  obligation_id    int NOT NULL REFERENCES breach_obligation(obligation_id),
  kind             varchar(16) NOT NULL,
  -- When the thing was done, as entered: a submission made at 09:00 and
  -- recorded at 11:00 was made at 09:00.
  occurred_at      timestamptz,
  -- What the regulator returned: an acknowledgement or a filing number.
  reference        varchar(200),
  note             text,
  -- A new due time: the date the Board allowed, or the clock of a duty
  -- reinstated by a later determination. Stored, never recomputed.
  due_at           timestamptz,
  anchored_at      timestamptz,
  requested_at     timestamptz,
  determination_id int REFERENCES breach_determination(determination_id),
  recorded_by      int REFERENCES auth_user(id),
  recorded_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT breach_obligation_event_kind CHECK (
    kind IN ('completed', 'not_applicable', 'reinstated', 'extended', 'reopened')
  ),
  CONSTRAINT breach_obligation_event_completed_when CHECK (kind <> 'completed' OR occurred_at IS NOT NULL),
  CONSTRAINT breach_obligation_event_extension CHECK (
    kind <> 'extended' OR (due_at IS NOT NULL AND requested_at IS NOT NULL)
  ),
  CONSTRAINT breach_obligation_event_cites_determination CHECK (
    kind NOT IN ('not_applicable', 'reinstated') OR determination_id IS NOT NULL
  )
);
CREATE INDEX idx_breach_obligation_event ON breach_obligation_event (obligation_id, event_id);
CREATE TRIGGER trg_breach_obligation_event_append_only
  BEFORE UPDATE OR DELETE ON breach_obligation_event
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();
"""

DOWNGRADE = """
DROP TABLE IF EXISTS breach_obligation_event;
DROP TABLE IF EXISTS breach_obligation;
DROP TABLE IF EXISTS breach_assessment;
DROP TABLE IF EXISTS breach_determination;
DROP TABLE IF EXISTS breach_status_history;
DROP TABLE IF EXISTS breach;
DROP FUNCTION IF EXISTS cmp_breach_status_only();
DROP SEQUENCE IF EXISTS breach_ref_seq;
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
  EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON TABLE breach_status_history,
                  breach_determination, breach_assessment, breach_obligation,
                  breach_obligation_event FROM %I', r);
  EXECUTE format('REVOKE DELETE, TRUNCATE ON TABLE breach FROM %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE)
    op.execute(_harden(APP_ROLE))


def downgrade() -> None:
    op.execute(DOWNGRADE)
