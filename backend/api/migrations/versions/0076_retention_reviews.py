"""Retention reviews: acting when a consent ends and when its data must go
(2026-11-26, ADR 0047).

A purpose says how long a consent lasts (`consent_validity_period`) and how
long the data may be kept once the consent has ended (`retention_period`; the
product owner, 2026-11-26: the period runs from the consent's end). Until now
only the first was acted on, by quarantine in the night (`apply_retention_lapse`,
which stays). Nothing asked anybody to erase, and nothing proved it was done.

* `retention_setting` - one row: when the people responsible are reminded
  (days before), how long before an erasure a person is told, how long
  holders have to act, when an overdue action is escalated.
* `purpose.notify_before_erasure` - tell each person before their data is
  erased (default yes, configurable per purpose).
* `retention_review` - one per kind (`validity`: a consent's validity is
  running out; `retention`: its data must be erased or anonymised), project or
  HR activity, purpose and month due. Not one per person: a cohort of
  thousands is one review with a count. Its own register - not a rights or a
  breach ticket.
* `retention_review_person` - who is in it: the consent, the person, when it
  falls due, and whether a legal hold keeps them out, or they renewed.
* `retention_action` - what each one responsible is asked to do and what they
  answered: the project's DCO Admin or the activity's HR PoC (`owner`), each
  processor holding the data (`processor`, in the console or by link), and
  DataVault (`datavault`, by the platform).

Reviews and their rows belong to their project's office (`office_isolation`).

Revision ID: 0076
Revises: 0075
"""

from __future__ import annotations

import os

from alembic import op

revision = "0076"
down_revision = "0075"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

_OFFICE = (
    "current_setting('app.office', true) = 'all' "
    "OR office_id = (SELECT o.office_id FROM office o "
    "WHERE o.office_code = current_setting('app.office', true))"
)

UPGRADE = f"""
CREATE TABLE retention_setting (
  setting_id          smallint PRIMARY KEY DEFAULT 1,
  reminder_days       int[] NOT NULL DEFAULT ARRAY[90, 30, 7],
  notice_hours        int NOT NULL DEFAULT 48,
  action_days         int NOT NULL DEFAULT 30,
  escalate_after_days int NOT NULL DEFAULT 14,
  updated_by          int REFERENCES auth_user(id),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT retention_setting_one_row CHECK (setting_id = 1),
  CONSTRAINT retention_setting_hours CHECK (notice_hours BETWEEN 0 AND 720),
  CONSTRAINT retention_setting_days CHECK (action_days BETWEEN 1 AND 365
                                            AND escalate_after_days BETWEEN 1 AND 365)
);
COMMENT ON TABLE retention_setting IS
  'One row: reminders, the notice before erasure, and how long holders have to act';
INSERT INTO retention_setting DEFAULT VALUES;

ALTER TABLE purpose ADD COLUMN notify_before_erasure boolean NOT NULL DEFAULT true;
COMMENT ON COLUMN purpose.notify_before_erasure IS
  'Tell each person before data held for this purpose is erased (ADR 0047)';

CREATE TABLE retention_review (
  review_id      serial PRIMARY KEY,
  review_uuid    uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  reference      text NOT NULL UNIQUE,
  kind           text NOT NULL,
  office_id      int NOT NULL REFERENCES office(office_id),
  project_id     int NOT NULL REFERENCES project(project_id),
  purpose_id     int NOT NULL REFERENCES purpose(purpose_id),
  cohort         date NOT NULL,
  status         text NOT NULL DEFAULT 'upcoming',
  reminded_days  int[] NOT NULL DEFAULT ARRAY[]::int[],
  reconsent      text,
  opened_at      timestamptz,
  closed_at      timestamptz,
  closed_by      int REFERENCES auth_user(id),
  close_note     text,
  created_at     timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT retention_review_kind CHECK (kind IN ('validity', 'retention')),
  CONSTRAINT retention_review_status CHECK (status IN ('upcoming', 'due', 'in_progress', 'closed')),
  CONSTRAINT retention_review_reconsent
    CHECK (reconsent IS NULL OR reconsent IN ('asked', 'confirmed', 'declined', 'sent')),
  CONSTRAINT retention_review_closed_whole CHECK ((status = 'closed') = (closed_at IS NOT NULL)),
  CONSTRAINT retention_review_one UNIQUE (kind, project_id, purpose_id, cohort)
);
COMMENT ON TABLE retention_review IS
  'A cohort whose consent validity runs out, or whose data must go, for one project and purpose';
COMMENT ON COLUMN retention_review.cohort IS 'The first day of the month the cohort falls due in';
COMMENT ON COLUMN retention_review.reconsent IS
  'Validity only: whether the people may be asked to consent again - asked of the owner, '
  'confirmed or declined by them, and sent';
CREATE INDEX idx_retention_review_status ON retention_review (status, cohort);

CREATE TABLE retention_review_person (
  member_id    serial PRIMARY KEY,
  review_id    int NOT NULL REFERENCES retention_review(review_id) ON DELETE CASCADE,
  kind         text NOT NULL,
  consent_id   int NOT NULL REFERENCES consent_artefact(consent_id),
  purpose_id   int NOT NULL REFERENCES purpose(purpose_id),
  auth_user_id int NOT NULL REFERENCES auth_user(id),
  due_at       timestamptz NOT NULL,
  ended_by     text NOT NULL,
  state        text NOT NULL DEFAULT 'in',
  notified_at  timestamptz,
  invited_at   timestamptz,
  office_id    int NOT NULL REFERENCES office(office_id),
  added_at     timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT retention_review_person_ended CHECK (ended_by IN ('withdrawal', 'validity')),
  CONSTRAINT retention_review_person_state CHECK (state IN ('in', 'held', 'renewed')),
  CONSTRAINT retention_review_person_once UNIQUE (kind, consent_id, purpose_id)
);
COMMENT ON TABLE retention_review_person IS
  'A person in a retention review: the consent, when it falls due, and whether a legal '
  'hold keeps them out or they consented again';
CREATE INDEX idx_retention_review_person_review ON retention_review_person (review_id, state);

CREATE TABLE retention_action (
  action_id        serial PRIMARY KEY,
  action_uuid      uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  review_id        int NOT NULL REFERENCES retention_review(review_id) ON DELETE CASCADE,
  kind             text NOT NULL,
  processor_id     int REFERENCES processor(processor_id),
  respondent_id    int REFERENCES processor_respondent(respondent_id),
  user_id          int REFERENCES auth_user(id),
  channel          text NOT NULL,
  label            text NOT NULL,
  status           text NOT NULL DEFAULT 'open',
  outcome          text,
  reason           text,
  keep_until       date,
  reconsent        boolean,
  evidence_name    text,
  evidence_ref     text,
  evidence_hash    text,
  link_token       text UNIQUE,
  link_token_sealed bytea,
  link_issued_at   timestamptz,
  due_at           timestamptz NOT NULL,
  answered_at      timestamptz,
  answered_by      int REFERENCES auth_user(id),
  accepted_at      timestamptz,
  accepted_by      int REFERENCES auth_user(id),
  sent_back_reason text,
  last_reminded_at timestamptz,
  escalated_at     timestamptz,
  office_id        int NOT NULL REFERENCES office(office_id),
  created_at       timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT retention_action_kind CHECK (kind IN ('owner', 'processor', 'datavault')),
  CONSTRAINT retention_action_channel CHECK (channel IN ('console', 'link', 'automatic', 'none')),
  CONSTRAINT retention_action_status
    CHECK (status IN ('open', 'answered', 'accepted', 'sent_back', 'not_needed')),
  CONSTRAINT retention_action_outcome
    CHECK (outcome IS NULL OR outcome IN ('erased', 'anonymised', 'kept', 'not_held', 'reviewed')),
  CONSTRAINT retention_action_reasoned
    CHECK (outcome IS NULL OR outcome NOT IN ('anonymised', 'kept') OR reason IS NOT NULL),
  CONSTRAINT retention_action_kept_until CHECK (outcome IS DISTINCT FROM 'kept' OR keep_until IS NOT NULL),
  CONSTRAINT retention_action_one UNIQUE NULLS NOT DISTINCT (review_id, kind, processor_id)
);
COMMENT ON TABLE retention_action IS
  'What one responsible holder is asked to do in a retention review, and what they answered';
COMMENT ON COLUMN retention_action.reason IS
  'Why data was anonymised rather than erased, or kept; sealed';
COMMENT ON COLUMN retention_action.reconsent IS
  'Validity, owner only: the project is active and the people may be asked to consent again';
CREATE INDEX idx_retention_action_user ON retention_action (user_id, status);
CREATE INDEX idx_retention_action_review ON retention_action (review_id);

ALTER TABLE retention_review ENABLE ROW LEVEL SECURITY;
ALTER TABLE retention_review FORCE ROW LEVEL SECURITY;
CREATE POLICY office_isolation ON retention_review USING ({_OFFICE}) WITH CHECK ({_OFFICE});
ALTER TABLE retention_review_person ENABLE ROW LEVEL SECURITY;
ALTER TABLE retention_review_person FORCE ROW LEVEL SECURITY;
CREATE POLICY office_isolation ON retention_review_person USING ({_OFFICE}) WITH CHECK ({_OFFICE});
ALTER TABLE retention_action ENABLE ROW LEVEL SECURITY;
ALTER TABLE retention_action FORCE ROW LEVEL SECURITY;
CREATE POLICY office_isolation ON retention_action USING ({_OFFICE}) WITH CHECK ({_OFFICE});
"""

DOWNGRADE = """
DROP TABLE IF EXISTS retention_action;
DROP TABLE IF EXISTS retention_review_person;
DROP TABLE IF EXISTS retention_review;
ALTER TABLE purpose DROP COLUMN IF EXISTS notify_before_erasure;
DROP TABLE IF EXISTS retention_setting;
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
  EXECUTE format('GRANT SELECT, UPDATE ON TABLE retention_setting TO %I', r);
  EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE retention_review TO %I', r);
  EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE retention_review_person TO %I', r);
  EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE retention_action TO %I', r);
  EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE retention_review_review_id_seq TO %I', r);
  EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE retention_review_person_member_id_seq TO %I', r);
  EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE retention_action_action_id_seq TO %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE)
    op.execute(_grants(APP_ROLE))


def downgrade() -> None:
    op.execute(DOWNGRADE)
