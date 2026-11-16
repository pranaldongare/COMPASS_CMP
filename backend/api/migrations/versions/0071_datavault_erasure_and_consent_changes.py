"""Telling DataVault to erase, and of every consent change (2026-11-13).

0070 asked DataVault what it holds of a person. Two more calls follow it, both
from the contract DataVault was handed on 2026-11-04 (ADR 0039):

* **Erasure.** On an erasure request, the DPO or the Legal PoC presses "Erase
  in DataVault": the assets the last check listed go to
  `POST {erasure address}/erasures` under one `erasure_id`, and DataVault
  answers each `erased`, `pending`, `failed` or `not_held`. Nothing about it
  runs by itself: a pending asset is asked about again when somebody presses
  "Check status", which repeats the same instruction.
* **Consent changes.** A withdrawal, in full or in part, a consent given
  again, and a consent whose validity has run out, each go to
  `POST {erasure address}/consent-changes` without anybody pressing anything,
  and are retried until DataVault answers.

What this adds:

* `datavault_connection` gains where those two calls go (`erasure_url`), how
  a person, a consent and a project are named in every call (`id_format`:
  the numbers the console shows, or uuids, the administrator's to switch),
  whether consent changes are sent at all (`consent_changes`), and where they
  start: the consents on record when the administrator first switched them on
  are never read (`consent_changes_after`), and a validity that had run out
  by then is never reported (`consent_changes_since`), so switching on tells
  DataVault nothing about the past.
* `datavault_check_asset` gains whether DataVault gave the consent as a number
  (`consent_ref_is_number`): an erasure sends each asset back with the consent
  as DataVault gave it, a number as a number and a text as a text.
* `datavault_erasure` - one instruction: the request, the check its list came
  from, who sent it, how often it has been asked about, and why the last ask
  was not answered. `datavault_erasure_asset` - each asset in it, as sent, and
  what DataVault last said of it.
* `datavault_consent_change` - the messages, queued before they are sent so
  that one that could not be delivered is not lost. `change_id` is the
  message's `sequence`. `datavault_consent_noted` - the consents the platform
  has already read for DataVault, so each is read once.

Every one of the new tables hangs off a row that is one office's, and is
policed through it (`office_isolation`, as 0051 does it): an erasure through
its request, its assets through the erasure, a message and a noted consent
through the consent.

Revision ID: 0071
Revises: 0070
"""

from __future__ import annotations

import os

from alembic import op

revision = "0071"
down_revision = "0070"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

_ALL = "current_setting('app.office', true) = 'all'"


def _through(table: str, parent: str, column: str) -> str:
    """Police `table` through the `parent` row its `column` names."""
    rule = f"{_ALL} OR EXISTS (SELECT 1 FROM {parent} p WHERE p.{column} = {table}.{column})"
    return f"""
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
CREATE POLICY office_isolation ON {table} USING ({rule}) WITH CHECK ({rule});
"""


UPGRADE = f"""
ALTER TABLE datavault_connection
  ADD COLUMN erasure_url text,
  ADD COLUMN id_format text NOT NULL DEFAULT 'numeric',
  ADD COLUMN consent_changes boolean NOT NULL DEFAULT false,
  ADD COLUMN consent_changes_after int,
  ADD COLUMN consent_changes_since timestamptz,
  ADD CONSTRAINT datavault_connection_id_format CHECK (id_format IN ('numeric', 'uuid')),
  ADD CONSTRAINT datavault_connection_changes_have_url
    CHECK (NOT consent_changes OR erasure_url IS NOT NULL);
COMMENT ON COLUMN datavault_connection.erasure_url IS
  'The address /erasures and /consent-changes are appended to; NULL: neither call is made';
COMMENT ON COLUMN datavault_connection.id_format IS
  'How a person, a consent and a project are named in every call: numeric (the IDs the console shows) or uuid';
COMMENT ON COLUMN datavault_connection.consent_changes IS
  'Whether DataVault is told of consent changes by itself';
COMMENT ON COLUMN datavault_connection.consent_changes_after IS
  'The highest consent on record when consent changes were first switched on: none up to it is ever read';
COMMENT ON COLUMN datavault_connection.consent_changes_since IS
  'When consent changes were first switched on: a validity that ran out before it is never reported';

ALTER TABLE datavault_check_asset ADD COLUMN consent_ref_is_number boolean;
COMMENT ON COLUMN datavault_check_asset.consent_ref_is_number IS
  'Whether DataVault gave consent_ref as a JSON number; NULL: checked before this was kept';

CREATE TABLE datavault_erasure (
  erasure_id     serial PRIMARY KEY,
  erasure_uuid   uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  request_id     int NOT NULL REFERENCES rights_request(request_id) ON DELETE CASCADE,
  check_id       int NOT NULL REFERENCES datavault_check(check_id) ON DELETE CASCADE,
  id_format      text NOT NULL,
  sent_by        int NOT NULL REFERENCES auth_user(id),
  sent_at        timestamptz NOT NULL DEFAULT now(),
  asks           int NOT NULL DEFAULT 0,
  last_asked_at  timestamptz,
  last_asked_by  int REFERENCES auth_user(id),
  answered_at    timestamptz,
  failure        text,
  CONSTRAINT datavault_erasure_id_format CHECK (id_format IN ('numeric', 'uuid'))
);
COMMENT ON TABLE datavault_erasure IS
  'One instruction to DataVault to erase assets, on an erasure request';
COMMENT ON COLUMN datavault_erasure.erasure_uuid IS
  'The erasure_id DataVault is given; repeating it asks for the state and starts nothing new';
COMMENT ON COLUMN datavault_erasure.check_id IS 'The check whose list of assets it was drawn from';
COMMENT ON COLUMN datavault_erasure.id_format IS
  'How the person and the request were named in it. Fixed once DataVault has answered it, so a repeat says the same';
COMMENT ON COLUMN datavault_erasure.asks IS 'How many times it has been sent, the first included';
COMMENT ON COLUMN datavault_erasure.answered_at IS 'When DataVault last answered it; NULL: not yet';
COMMENT ON COLUMN datavault_erasure.failure IS
  'Why the last ask was not answered, as a short code; NULL when it was';
CREATE INDEX idx_datavault_erasure_request ON datavault_erasure (request_id, erasure_id DESC);

CREATE TABLE datavault_erasure_asset (
  row_id        serial PRIMARY KEY,
  erasure_id    int NOT NULL REFERENCES datavault_erasure(erasure_id) ON DELETE CASCADE,
  position      int NOT NULL,
  asset_ref     text NOT NULL,
  consent_sent  jsonb,
  status        text NOT NULL DEFAULT 'unanswered',
  status_at     timestamptz,
  completed_at  timestamptz,
  reason        text,
  CONSTRAINT datavault_erasure_asset_once UNIQUE (erasure_id, asset_ref),
  CONSTRAINT datavault_erasure_asset_status
    CHECK (status IN ('unanswered', 'pending', 'erased', 'failed', 'not_held'))
);
COMMENT ON TABLE datavault_erasure_asset IS
  'An asset named in an erasure instruction, and what DataVault last said of it';
COMMENT ON COLUMN datavault_erasure_asset.asset_ref IS 'DataVault''s own identifier for the asset';
COMMENT ON COLUMN datavault_erasure_asset.consent_sent IS
  'The consent it was sent with, as DataVault gave it at the check: a JSON number or a JSON text';
COMMENT ON COLUMN datavault_erasure_asset.status IS
  'unanswered until DataVault says: pending, or one of the final erased, failed, not_held';
COMMENT ON COLUMN datavault_erasure_asset.completed_at IS 'When DataVault says it was erased';
COMMENT ON COLUMN datavault_erasure_asset.reason IS
  'Why DataVault did not erase it, in its words; the contract asks for no personal data in it';
CREATE INDEX idx_datavault_erasure_asset ON datavault_erasure_asset (erasure_id, position);

CREATE TABLE datavault_consent_change (
  change_id        serial PRIMARY KEY,
  message_uuid     uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  consent_id       int NOT NULL REFERENCES consent_artefact(consent_id),
  chain_root_id    int NOT NULL REFERENCES consent_artefact(consent_id),
  change           text NOT NULL,
  action           text NOT NULL,
  purposes_granted text[] NOT NULL DEFAULT '{{}}',
  purposes_removed text[] NOT NULL DEFAULT '{{}}',
  effective_at     timestamptz NOT NULL,
  queued_at        timestamptz NOT NULL DEFAULT now(),
  attempts         int NOT NULL DEFAULT 0,
  last_attempt_at  timestamptz,
  next_attempt_at  timestamptz NOT NULL DEFAULT now(),
  failure          text,
  delivered_at     timestamptz,
  result           text,
  assets_affected  int,
  superseded_at    timestamptz,
  CONSTRAINT datavault_consent_change_kind
    CHECK (change IN ('withdrawn', 'partly_withdrawn', 'expired', 'granted_again')),
  CONSTRAINT datavault_consent_change_action CHECK (action IN ('restrict', 'lift_restriction')),
  CONSTRAINT datavault_consent_change_result
    CHECK (result IS NULL OR result IN ('applied', 'duplicate', 'stale')),
  CONSTRAINT datavault_consent_change_delivery_whole
    CHECK ((delivered_at IS NULL) = (result IS NULL))
);
COMMENT ON TABLE datavault_consent_change IS
  'A consent change DataVault is told of: queued first, sent after, retried until it answers';
COMMENT ON COLUMN datavault_consent_change.change_id IS
  'Also the message''s sequence: it grows with every message';
COMMENT ON COLUMN datavault_consent_change.consent_id IS 'The consent in force when it was queued';
COMMENT ON COLUMN datavault_consent_change.chain_root_id IS
  'The first consent of the chain - the same person and notice - which names the chain';
COMMENT ON COLUMN datavault_consent_change.purposes_granted IS
  'Every purpose the assets may be used for after it, by code: the whole state, not a difference';
COMMENT ON COLUMN datavault_consent_change.purposes_removed IS 'The purposes it took away, by code';
COMMENT ON COLUMN datavault_consent_change.failure IS
  'Why the last try was not answered, as a short code; NULL once delivered';
COMMENT ON COLUMN datavault_consent_change.result IS
  'DataVault''s answer: applied, duplicate or stale - each counts as delivered';
COMMENT ON COLUMN datavault_consent_change.superseded_at IS
  'Set aside unsent: a later message for the same chain carries the whole state';
CREATE INDEX idx_datavault_consent_change_due ON datavault_consent_change (next_attempt_at)
  WHERE delivered_at IS NULL AND superseded_at IS NULL;
CREATE INDEX idx_datavault_consent_change_chain
  ON datavault_consent_change (chain_root_id, change_id DESC);

CREATE TABLE datavault_consent_noted (
  consent_id int PRIMARY KEY REFERENCES consent_artefact(consent_id),
  noted_at   timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE datavault_consent_noted IS
  'The consents already read for what DataVault must be told: each is read once';
{_through("datavault_erasure", "rights_request", "request_id")}
{_through("datavault_erasure_asset", "datavault_erasure", "erasure_id")}
{_through("datavault_consent_change", "consent_artefact", "consent_id")}
{_through("datavault_consent_noted", "consent_artefact", "consent_id")}
"""

DOWNGRADE = """
DROP TABLE IF EXISTS datavault_consent_noted;
DROP TABLE IF EXISTS datavault_consent_change;
DROP TABLE IF EXISTS datavault_erasure_asset;
DROP TABLE IF EXISTS datavault_erasure;
ALTER TABLE datavault_check_asset DROP COLUMN IF EXISTS consent_ref_is_number;
ALTER TABLE datavault_connection
  DROP CONSTRAINT IF EXISTS datavault_connection_changes_have_url,
  DROP CONSTRAINT IF EXISTS datavault_connection_id_format,
  DROP COLUMN IF EXISTS consent_changes_since,
  DROP COLUMN IF EXISTS consent_changes_after,
  DROP COLUMN IF EXISTS consent_changes,
  DROP COLUMN IF EXISTS id_format,
  DROP COLUMN IF EXISTS erasure_url;
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
  EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE datavault_erasure TO %I', r);
  EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE datavault_erasure_asset TO %I', r);
  EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE datavault_consent_change TO %I', r);
  EXECUTE format('GRANT SELECT, INSERT ON TABLE datavault_consent_noted TO %I', r);
  EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE datavault_erasure_erasure_id_seq TO %I', r);
  EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE datavault_erasure_asset_row_id_seq TO %I', r);
  EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE datavault_consent_change_change_id_seq TO %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE)
    op.execute(_grants(APP_ROLE))


def downgrade() -> None:
    op.execute(DOWNGRADE)
