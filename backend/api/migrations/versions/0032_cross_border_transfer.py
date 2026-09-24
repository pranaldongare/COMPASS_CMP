"""Cross-border control, enforced at export (S2-04).

Section 16 lets a fiduciary transfer personal data outside India except to a
country the Government has notified as restricted. A purpose carried a
`cross_border_permitted` flag and nothing read it: no processor said where it
was, no export said where it went, and nothing stood between the two.

`processor.location_country` is where a processor is (ISO 3166-1 alpha-2).
Unknown is allowed in the column and refused at export: a transfer the platform
cannot place is a transfer it cannot say is lawful.

`restricted_country` is the Government's list, kept as data the Privacy Office
maintains rather than code anybody deploys: a country, the notification that
listed it, and - once - when it was lifted. A country is listed at most once at
a time.

Each `export_line` records where that person's row went - the processor
running the site the consent was given at, and its country, as they were at
the moment of the export - and `export_log.transfer_basis` records the
decision for each destination and the ground it rested on. The line was the
disclosure record already; now it says to whom, which also gives holder
derivation back the processor it lost when exports stopped naming one site.

Revision ID: 0032
Revises: 0031
"""

from __future__ import annotations

import os

from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

UPGRADE = """
ALTER TABLE processor ADD COLUMN location_country char(2);
ALTER TABLE processor ADD CONSTRAINT processor_location_is_iso
  CHECK (location_country IS NULL OR location_country ~ '^[A-Z]{2}$');
COMMENT ON COLUMN processor.location_country IS
  'Where the processor is, ISO 3166-1 alpha-2. Unknown is refused at export (S2-04)';

CREATE TABLE restricted_country (
  country_id       serial PRIMARY KEY,
  country_uuid     uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  country_code     char(2) NOT NULL,
  notification_ref text NOT NULL,
  listed_by        int NOT NULL REFERENCES auth_user(id),
  listed_at        timestamptz NOT NULL DEFAULT now(),
  lifted_by        int REFERENCES auth_user(id),
  lifted_at        timestamptz,
  CONSTRAINT restricted_country_is_iso CHECK (country_code ~ '^[A-Z]{2}$'),
  CONSTRAINT restricted_country_lift_attributed CHECK ((lifted_at IS NULL) = (lifted_by IS NULL)),
  CONSTRAINT restricted_country_not_india CHECK (country_code <> 'IN')
);
CREATE UNIQUE INDEX uq_restricted_country_active
  ON restricted_country (country_code) WHERE lifted_at IS NULL;
COMMENT ON TABLE restricted_country IS
  'Countries the Government has notified under s.16 - data, maintained by the Privacy Office';

-- Listed once, lifted once: a list whose past entries could be edited could
-- not say what was restricted on the day an export was refused or allowed.
CREATE OR REPLACE FUNCTION cmp_restricted_country_lift_only() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'restricted_country rows are never deleted' USING ERRCODE = 'restrict_violation';
  END IF;
  IF OLD.lifted_at IS NOT NULL THEN
    RAISE EXCEPTION 'a lifted restriction does not change' USING ERRCODE = 'restrict_violation';
  END IF;
  IF NEW.country_id IS DISTINCT FROM OLD.country_id
     OR NEW.country_uuid IS DISTINCT FROM OLD.country_uuid
     OR NEW.country_code IS DISTINCT FROM OLD.country_code
     OR NEW.notification_ref IS DISTINCT FROM OLD.notification_ref
     OR NEW.listed_by IS DISTINCT FROM OLD.listed_by
     OR NEW.listed_at IS DISTINCT FROM OLD.listed_at THEN
    RAISE EXCEPTION 'only the lifting of a restriction may be recorded' USING ERRCODE = 'restrict_violation';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_restricted_country_lift_only
  BEFORE UPDATE OR DELETE ON restricted_country
  FOR EACH ROW EXECUTE FUNCTION cmp_restricted_country_lift_only();

-- Where each row went, as it was at the moment of the export. NULL on lines
-- written before this migration: that was never recorded.
ALTER TABLE export_line
  ADD COLUMN destination_processor_id int REFERENCES processor(processor_id),
  ADD COLUMN destination_country char(2);
CREATE INDEX idx_export_line_destination ON export_line (destination_processor_id);

ALTER TABLE export_log ADD COLUMN transfer_basis jsonb;
COMMENT ON COLUMN export_log.transfer_basis IS
  'Each destination of the export, its country, and the ground the transfer rested on (S2-04)';
"""

DOWNGRADE = """
ALTER TABLE export_log DROP COLUMN IF EXISTS transfer_basis;
DROP INDEX IF EXISTS idx_export_line_destination;
ALTER TABLE export_line DROP COLUMN IF EXISTS destination_country,
                        DROP COLUMN IF EXISTS destination_processor_id;
DROP TABLE IF EXISTS restricted_country;
DROP FUNCTION IF EXISTS cmp_restricted_country_lift_only();
ALTER TABLE processor DROP CONSTRAINT IF EXISTS processor_location_is_iso;
ALTER TABLE processor DROP COLUMN IF EXISTS location_country;
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
  EXECUTE format('REVOKE DELETE, TRUNCATE ON TABLE restricted_country FROM %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute(UPGRADE)
    op.execute(_harden(APP_ROLE))


def downgrade() -> None:
    op.execute(DOWNGRADE)
