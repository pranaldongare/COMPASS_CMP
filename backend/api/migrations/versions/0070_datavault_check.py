"""Asking DataVault what it holds of a person, for a rights request (2026-11-13).

DataVault is the store the labs' assets live in. When a rights request comes
in, the office that answers it has to know what is held there; until now it
asked a DCO Admin, who looked. The platform now asks DataVault itself:
`GET {base}/lookup?request_id=..&person_id=..`, pressed by the DPO or Legal
on the request ("Check in DataVault"), or sent by the platform when the
holders it finds include a DCO Admin.

Three tables, and nothing else in the schema is touched:

* `datavault_connection` - one row: where DataVault is and the key it asks
  for, kept by the administrator. The key is encrypted with the application's
  own key (`seal_token`), as a consent link's token is; it is never served.
* `datavault_check` - one row per call: for which request, by whom (nobody:
  the platform), when, and whether DataVault answered.
* `datavault_check_asset` - what an answered check listed: DataVault's asset
  identifier, the consent and project it named (kept as sent, and matched to
  ours where they are this person's), its `mid` and its `datapath`.

A check is its request's office's, as every row hanging off a request is:
`datavault_check` is policed through `rights_request`, and its assets through
the check (`office_isolation`, as 0051 does it). The connection belongs to no
office. A check belongs to its request and goes when the request does. This is its
own line of tables: the names of the earlier DataVault branch (revision 0057,
never landed here) are not reused.

Revision ID: 0070
Revises: 0069
"""

from __future__ import annotations

import os

from alembic import op

revision = "0070"
down_revision = "0069"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

UPGRADE = """
CREATE TABLE datavault_connection (
  connection_id  smallint PRIMARY KEY DEFAULT 1,
  base_url       text,
  api_key_sealed bytea,
  api_key_header text NOT NULL DEFAULT 'X-API-Key',
  enabled        boolean NOT NULL DEFAULT false,
  updated_by     int REFERENCES auth_user(id),
  updated_at     timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT datavault_connection_one_row CHECK (connection_id = 1),
  CONSTRAINT datavault_connection_enabled_has_url CHECK (NOT enabled OR base_url IS NOT NULL)
);
COMMENT ON TABLE datavault_connection IS
  'One row: where DataVault is reached and with what key; kept by the administrator';
COMMENT ON COLUMN datavault_connection.base_url IS
  'The address the lookup is appended to; NULL: not set up';
COMMENT ON COLUMN datavault_connection.api_key_sealed IS
  'The key DataVault asks for, encrypted with the application key; never served';
COMMENT ON COLUMN datavault_connection.api_key_header IS 'The header the key is sent in';
COMMENT ON COLUMN datavault_connection.enabled IS
  'Whether the platform may call DataVault at all';
INSERT INTO datavault_connection DEFAULT VALUES;

CREATE TABLE datavault_check (
  check_id    serial PRIMARY KEY,
  check_uuid  uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  request_id  int NOT NULL REFERENCES rights_request(request_id) ON DELETE CASCADE,
  asked_by    int REFERENCES auth_user(id),
  asked_at    timestamptz NOT NULL DEFAULT now(),
  outcome     text NOT NULL,
  failure     text,
  asset_count int NOT NULL DEFAULT 0,
  CONSTRAINT datavault_check_outcome CHECK (outcome IN ('answered', 'failed')),
  CONSTRAINT datavault_check_failure_whole CHECK ((outcome = 'failed') = (failure IS NOT NULL))
);
COMMENT ON TABLE datavault_check IS
  'One call to DataVault for a rights request: what it holds of the person';
COMMENT ON COLUMN datavault_check.asked_by IS
  'Who pressed Check in DataVault; NULL: the platform, when holders were found';
COMMENT ON COLUMN datavault_check.failure IS
  'Why it was not answered, as a short code (timeout, status_503, unreadable); never a body';
CREATE INDEX idx_datavault_check_request ON datavault_check (request_id, check_id DESC);

CREATE TABLE datavault_check_asset (
  row_id      serial PRIMARY KEY,
  check_id    int NOT NULL REFERENCES datavault_check(check_id) ON DELETE CASCADE,
  position    int NOT NULL,
  asset_ref   text NOT NULL,
  consent_ref text,
  project_ref text,
  consent_id  int REFERENCES consent_artefact(consent_id),
  project_id  int REFERENCES project(project_id),
  mid         text,
  datapath    text
);
COMMENT ON TABLE datavault_check_asset IS 'An asset DataVault listed in answer to a check';
COMMENT ON COLUMN datavault_check_asset.asset_ref IS 'DataVault''s own identifier for the asset';
COMMENT ON COLUMN datavault_check_asset.consent_ref IS 'The consent as DataVault named it';
COMMENT ON COLUMN datavault_check_asset.project_ref IS 'The project as DataVault named it';
COMMENT ON COLUMN datavault_check_asset.consent_id IS
  'Our consent, where what DataVault named is one of this person''s; NULL otherwise';
COMMENT ON COLUMN datavault_check_asset.project_id IS
  'Our project, where what DataVault named is one; NULL otherwise';
COMMENT ON COLUMN datavault_check_asset.mid IS 'DataVault''s mid for the asset, as sent';
COMMENT ON COLUMN datavault_check_asset.datapath IS 'Where DataVault keeps the asset, as sent';
CREATE INDEX idx_datavault_check_asset_check ON datavault_check_asset (check_id, position);

ALTER TABLE datavault_check ENABLE ROW LEVEL SECURITY;
ALTER TABLE datavault_check FORCE ROW LEVEL SECURITY;
CREATE POLICY office_isolation ON datavault_check
  USING (current_setting('app.office', true) = 'all'
         OR EXISTS (SELECT 1 FROM rights_request p WHERE p.request_id = datavault_check.request_id))
  WITH CHECK (current_setting('app.office', true) = 'all'
         OR EXISTS (SELECT 1 FROM rights_request p WHERE p.request_id = datavault_check.request_id));
ALTER TABLE datavault_check_asset ENABLE ROW LEVEL SECURITY;
ALTER TABLE datavault_check_asset FORCE ROW LEVEL SECURITY;
CREATE POLICY office_isolation ON datavault_check_asset
  USING (current_setting('app.office', true) = 'all'
         OR EXISTS (SELECT 1 FROM datavault_check p WHERE p.check_id = datavault_check_asset.check_id))
  WITH CHECK (current_setting('app.office', true) = 'all'
         OR EXISTS (SELECT 1 FROM datavault_check p WHERE p.check_id = datavault_check_asset.check_id));
"""

DOWNGRADE = """
DROP TABLE IF EXISTS datavault_check_asset;
DROP TABLE IF EXISTS datavault_check;
DROP TABLE IF EXISTS datavault_connection;
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
  EXECUTE format('GRANT SELECT, UPDATE ON TABLE datavault_connection TO %I', r);
  EXECUTE format('GRANT SELECT, INSERT ON TABLE datavault_check TO %I', r);
  EXECUTE format('GRANT SELECT, INSERT ON TABLE datavault_check_asset TO %I', r);
  EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE datavault_check_check_id_seq TO %I', r);
  EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE datavault_check_asset_row_id_seq TO %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE)
    op.execute(_grants(APP_ROLE))


def downgrade() -> None:
    op.execute(DOWNGRADE)
