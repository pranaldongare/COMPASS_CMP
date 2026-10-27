"""Offices, and the wall between them (ADR 0032).

A second consent track is coming, governed by a Legal office beside the DPO
office. Both live in this database, and neither may see the other's
registers. So the office becomes data and PostgreSQL enforces it:

  | Change | What |
  |---|---|
  | `office` | one row per office: `rnd` (the DPO office) and `hr` (the Legal office); a third office is an INSERT |
  | `office_id` | on `project`, `purpose`, `notice_template`, `notice`, `consent_link`, `export_log`, `breach` (NOT NULL) and `rights_request` (nullable: the shared intake); every existing row is `rnd` |
  | `auth_user.office_id` | the office an officer, an author or a collection owner works in; NULL for the administrator, a data principal and a breach-only login, by CHECK |
  | `user_role` | gains `legal` (Legal PoC) and `hr_user` (HR PoC) |
  | policies | `ENABLE` + `FORCE ROW LEVEL SECURITY` and one `office_isolation` policy on each office-bearing table, and on each child through its parent |
  | `v_current_consent` | recreated `WITH (security_invoker = true)`, so the view reads through the policies rather than around them |

The setting the policies read is `app.office`: an office code, or `all`.
The pool sets it on every connection it hands out (`cmp.db.pool`); a
connection that never sets it reads nothing from a policed table. No policy
binds a superuser or a role with BYPASSRLS, which is why the enforcement
tests switch to a role of their own and why the API refuses to start as one
outside `local` and `test`.

The backfill writes no row. Each column is added with the `rnd` office as a
constant default, which PostgreSQL records once in the catalogue rather than
on every row, and the default is then dropped: so no append-only trigger
fires on `export_log`, no published notice is touched, and nothing that is
evidence changes. Only `auth_user`, whose office depends on the role, is
updated.

Three rules beside the policies:

- `notice`, `consent_link` and `export_log` take their office from their
  parent when it is not given, and refuse one that differs
  (`cmp_office_from_parent`).
- A record's office never changes once written, except a rights request's,
  which moves by a claim or a transfer (0055) (`cmp_office_is_fixed`).
- An account holds an office exactly when its role works in one
  (`auth_user_office_by_role`).

The enum values go first, alone and outside the transaction, as 0041's did;
the downgrade leaves them.

Revision ID: 0051
Revises: 0050
"""

from __future__ import annotations

import os

from alembic import op

revision = "0051"
down_revision = "0050"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

NEW_ROLES = (
    "ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'legal';",
    "ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'hr_user';",
)

#: The tables that name their office, and whether a row may have none.
OWN = (
    ("project", False),
    ("purpose", False),
    ("notice_template", False),
    ("notice", False),
    ("consent_link", False),
    ("export_log", False),
    ("breach", False),
    ("rights_request", True),
)

#: The tables that carry no office of their own: (table, parent, column on
#: the table, key on the parent). A child is visible exactly when its parent
#: is, because the parent's own policy filters the subquery.
CHILDREN = (
    ("consent_artefact", "consent_link", "link_id", "link_id"),
    ("consent_purpose_grant", "consent_artefact", "consent_id", "consent_id"),
    ("export_line", "export_log", "export_id", "export_id"),
    ("notice_language", "notice", "notice_id", "notice_id"),
    ("notice_purpose", "notice", "notice_id", "notice_id"),
    ("notice_template_language", "notice_template", "template_id", "template_id"),
    ("notice_template_purpose", "notice_template", "template_id", "template_id"),
    ("project_site", "project", "project_id", "project_id"),
    ("project_processor", "project", "project_id", "project_id"),
    ("project_approval", "project", "project_id", "project_id"),
    ("project_status_history", "project", "project_id", "project_id"),
    ("import_batch", "project", "project_id", "project_id"),
    ("collection", "project", "project_id", "project_id"),
    ("data_asset", "collection", "collection_id", "collection_id"),
    # Through the asset, not the consent: half the rows record an asset whose
    # consent is not known.
    ("asset_consent", "data_asset", "asset_id", "asset_id"),
    ("rights_request_holder", "rights_request", "request_id", "request_id"),
    ("rights_request_item", "rights_request", "request_id", "request_id"),
    ("rights_item_execution", "rights_request_item", "item_id", "item_id"),
    ("rights_ticket_message", "rights_request_holder", "holder_id", "holder_id"),
    ("rights_response_file", "rights_request", "request_id", "request_id"),
    ("rights_request_attachment", "rights_request", "request_id", "request_id"),
    ("breach_affected", "breach", "breach_id", "breach_id"),
    ("breach_affected_revision", "breach", "breach_id", "breach_id"),
    ("breach_assessment", "breach", "breach_id", "breach_id"),
    ("breach_attachment", "breach", "breach_id", "breach_id"),
    ("breach_contact", "breach", "breach_id", "breach_id"),
    ("breach_determination", "breach", "breach_id", "breach_id"),
    ("breach_notice", "breach", "breach_id", "breach_id"),
    ("breach_notice_delivery", "breach_notice", "notice_id", "notice_id"),
    ("breach_obligation", "breach", "breach_id", "breach_id"),
    ("breach_obligation_event", "breach_obligation", "obligation_id", "obligation_id"),
    ("breach_recording", "breach", "breach_id", "breach_id"),
    ("breach_status_history", "breach", "breach_id", "breach_id"),
    ("breach_ticket", "breach", "breach_id", "breach_id"),
    ("breach_ticket_event", "breach_ticket", "ticket_id", "ticket_id"),
    ("breach_ticket_message", "breach_ticket", "ticket_id", "ticket_id"),
    ("breach_upload", "breach", "breach_id", "breach_id"),
)

#: (table, parent, column on the table, key on the parent): the office is
#: the parent's.
FROM_PARENT = (
    ("notice", "project", "project_id", "project_id"),
    ("consent_link", "notice", "notice_id", "notice_id"),
    ("export_log", "project", "project_id", "project_id"),
)

#: The roles that work in an office. Everyone else works across both.
OFFICE_ROLES = ("dpo", "legal", "rnd_user", "dco", "rco", "dco_admin", "hr_user")

#: The office of the setting: the row whose code it names. `office` is not
#: policed, so this always resolves; the planner runs it once per statement.
_MINE = (
    "(SELECT o.office_id FROM office o WHERE o.office_code = current_setting('app.office', true))"
)
_ALL = "current_setting('app.office', true) = 'all'"


def _own_policy(table: str, nullable: bool) -> str:
    shared = "office_id IS NULL OR " if nullable else ""
    rule = f"{_ALL} OR {shared}office_id = {_MINE}"
    return f"""
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
CREATE POLICY office_isolation ON {table} USING ({rule}) WITH CHECK ({rule});
"""


def _child_policy(table: str, parent: str, column: str, key: str) -> str:
    rule = f"{_ALL} OR EXISTS (SELECT 1 FROM {parent} p WHERE p.{key} = {table}.{column})"
    return f"""
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
CREATE POLICY office_isolation ON {table} USING ({rule}) WITH CHECK ({rule});
"""


GUARD = """
DO $$
BEGIN
  IF current_setting('server_version_num')::int < 160000 THEN
    RAISE EXCEPTION 'offices need PostgreSQL 16 or later (this is %)',
      current_setting('server_version');
  END IF;
END $$;
"""

OFFICE = """
CREATE TABLE office (
  office_id        serial PRIMARY KEY,
  office_uuid      uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  office_code      varchar(12) NOT NULL UNIQUE,
  name             varchar(120) NOT NULL,
  contact          text,
  grievance_route  text,
  created_at       timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE office IS
  'A governance office: rnd (the DPO office) or hr (the Legal office). Every governance record names one; an officer sees only its own (ADR 0032)';
COMMENT ON COLUMN office.office_code IS
  'What app.office holds for a session of this office, and what the policies compare';
COMMENT ON COLUMN office.contact IS 'The office''s contact, sealed (CONTACT)';
INSERT INTO office (office_code, name) VALUES ('rnd', 'DPO office'), ('hr', 'Legal office');
"""

COLUMNS = (
    """
DO $$
DECLARE
  rnd int := (SELECT office_id FROM office WHERE office_code = 'rnd');
  t text;
BEGIN
  -- A constant default is written to the catalogue, not to the rows: no
  -- UPDATE runs, so no evidence trigger fires and no evidence changes.
  FOREACH t IN ARRAY ARRAY['project', 'purpose', 'notice_template', 'notice',
                           'consent_link', 'export_log', 'breach'] LOOP
    EXECUTE format(
      'ALTER TABLE %I ADD COLUMN office_id int NOT NULL DEFAULT %s REFERENCES office(office_id)',
      t, rnd);
    EXECUTE format('ALTER TABLE %I ALTER COLUMN office_id DROP DEFAULT', t);
    EXECUTE format('CREATE INDEX idx_%s_office ON %I (office_id)', t, t);
  END LOOP;
  -- Nullable: a request whose office is not known yet is the shared intake.
  EXECUTE format(
    'ALTER TABLE rights_request ADD COLUMN office_id int DEFAULT %s REFERENCES office(office_id)',
    rnd);
  ALTER TABLE rights_request ALTER COLUMN office_id DROP DEFAULT;
  CREATE INDEX idx_rights_request_office ON rights_request (office_id);
END $$;

COMMENT ON COLUMN rights_request.office_id IS
  'The office that answers the request; NULL while it is in the shared intake';

ALTER TABLE auth_user ADD COLUMN office_id int REFERENCES office(office_id);
COMMENT ON COLUMN auth_user.office_id IS
  'The office this account works in; NULL for the administrator, a data principal and a breach-only login';
UPDATE auth_user SET office_id = (SELECT office_id FROM office WHERE office_code = 'rnd')
 WHERE role IN ('dpo', 'rnd_user', 'dco', 'rco', 'dco_admin');
CREATE INDEX idx_auth_user_office ON auth_user (office_id) WHERE office_id IS NOT NULL;
"""
    + f"""
ALTER TABLE auth_user ADD CONSTRAINT auth_user_office_by_role CHECK (
  (office_id IS NOT NULL) = (role IN ({", ".join(f"'{r}'" for r in OFFICE_ROLES)}))
);
"""
)

TRIGGERS = """
-- A notice is its project's office's, a link its notice's, an export its
-- project's. Given, it must agree; not given, it is filled.
CREATE OR REPLACE FUNCTION cmp_office_from_parent() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  parent_office int;
BEGIN
  EXECUTE format('SELECT office_id FROM %I WHERE %I = $1', TG_ARGV[0], TG_ARGV[2])
    INTO parent_office USING (to_jsonb(NEW) ->> TG_ARGV[1])::int;
  IF parent_office IS NULL THEN
    RAISE EXCEPTION '%: its % is not one this session can see', TG_TABLE_NAME, TG_ARGV[0]
      USING ERRCODE = 'foreign_key_violation';
  END IF;
  IF NEW.office_id IS NULL THEN
    NEW.office_id := parent_office;
  ELSIF NEW.office_id <> parent_office THEN
    RAISE EXCEPTION '%: its office must be its %''s', TG_TABLE_NAME, TG_ARGV[0]
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END;
$$;

-- An office is written once. A request moves by a claim or a transfer, which
-- 0055 allows; nothing else moves.
CREATE OR REPLACE FUNCTION cmp_office_is_fixed() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.office_id IS DISTINCT FROM OLD.office_id THEN
    RAISE EXCEPTION '%: a record''s office never changes', TG_TABLE_NAME
      USING ERRCODE = 'restrict_violation';
  END IF;
  RETURN NEW;
END;
$$;
"""

DOWNGRADE = """
DROP VIEW v_current_consent;
CREATE VIEW v_current_consent AS
SELECT ca.* FROM consent_artefact ca
WHERE NOT EXISTS (
  SELECT 1 FROM consent_artefact s WHERE s.supersedes_consent_id = ca.consent_id);

ALTER TABLE auth_user DROP CONSTRAINT auth_user_office_by_role;
ALTER TABLE auth_user DROP COLUMN office_id;
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['project', 'purpose', 'notice_template', 'notice',
                           'consent_link', 'export_log', 'breach', 'rights_request'] LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_office_fixed ON %I', t, t);
    EXECUTE format('ALTER TABLE %I DROP COLUMN office_id', t);
  END LOOP;
END $$;
DROP TRIGGER IF EXISTS trg_notice_office_from_parent ON notice;
DROP TRIGGER IF EXISTS trg_consent_link_office_from_parent ON consent_link;
DROP TRIGGER IF EXISTS trg_export_log_office_from_parent ON export_log;
DROP FUNCTION IF EXISTS cmp_office_from_parent();
DROP FUNCTION IF EXISTS cmp_office_is_fixed();
DROP TABLE office;
"""

VIEW = """
DROP VIEW v_current_consent;
CREATE VIEW v_current_consent WITH (security_invoker = true) AS
SELECT ca.* FROM consent_artefact ca
WHERE NOT EXISTS (
  SELECT 1 FROM consent_artefact s WHERE s.supersedes_consent_id = ca.consent_id);
COMMENT ON VIEW v_current_consent IS
  'The head of every consent chain. security_invoker: the caller''s office policies apply (ADR 0032)';
"""


def _grants(role: str) -> str:
    """The application role reads the new table and the recreated view; a
    deployment's own default privileges may already say so."""
    return f"""
DO $$
DECLARE r text := {role!r};
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
    RAISE NOTICE 'Role % does not exist; skipping grants', r;
    RETURN;
  END IF;
  EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE office TO %I', r);
  EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE office_office_id_seq TO %I', r);
  EXECUTE format('GRANT SELECT ON v_current_consent TO %I', r);
END $$;
"""


def _policies() -> str:
    parts = [_own_policy(t, nullable) for t, nullable in OWN]
    parts += [_child_policy(*c) for c in CHILDREN]
    return "\n".join(parts)


def _drop_policies() -> str:
    tables = [t for t, _ in OWN] + [c[0] for c in CHILDREN]
    return "\n".join(
        f"DROP POLICY IF EXISTS office_isolation ON {t};\n"
        f"ALTER TABLE {t} NO FORCE ROW LEVEL SECURITY;\n"
        f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY;"
        for t in tables
    )


def _trigger_ddl() -> str:
    parts = [TRIGGERS]
    for table, parent, column, key in FROM_PARENT:
        parts.append(
            f"CREATE TRIGGER trg_{table}_office_from_parent BEFORE INSERT ON {table}"
            f" FOR EACH ROW EXECUTE FUNCTION cmp_office_from_parent('{parent}', '{column}', '{key}');"
        )
    for table, _ in OWN:
        if table == "rights_request":
            continue
        parts.append(
            f"CREATE TRIGGER trg_{table}_office_fixed BEFORE UPDATE OF office_id ON {table}"
            " FOR EACH ROW EXECUTE FUNCTION cmp_office_is_fixed();"
        )
    return "\n".join(parts)


def upgrade() -> None:
    op.execute(GUARD)
    with op.get_context().autocommit_block():
        for statement in NEW_ROLES:
            op.execute(statement)
    # FORCE binds the owner too: everything below runs across both offices.
    op.execute("SELECT set_config('app.office', 'all', false)")
    op.execute(OFFICE)
    op.execute(COLUMNS)
    op.execute(_trigger_ddl())
    op.execute(_policies())
    op.execute(VIEW)
    op.execute(_grants(APP_ROLE))


def downgrade() -> None:
    # The enum values stay: PostgreSQL cannot remove one, and a row may hold it.
    # Nothing may belong to another office, or the downgrade would merge them.
    # Set first: under a role the policies bind, the checks would see nothing.
    op.execute("SELECT set_config('app.office', 'all', false)")
    op.execute(
        """DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM auth_user WHERE role IN ('legal', 'hr_user')) THEN
            RAISE EXCEPTION 'accounts hold the legal or hr_user role; change them before downgrading';
          END IF;
          IF EXISTS (SELECT 1 FROM project p JOIN office o USING (office_id) WHERE o.office_code <> 'rnd')
             OR EXISTS (SELECT 1 FROM purpose p JOIN office o USING (office_id) WHERE o.office_code <> 'rnd')
             OR EXISTS (SELECT 1 FROM notice_template t JOIN office o USING (office_id) WHERE o.office_code <> 'rnd')
             OR EXISTS (SELECT 1 FROM breach b JOIN office o USING (office_id) WHERE o.office_code <> 'rnd')
             OR EXISTS (SELECT 1 FROM rights_request r JOIN office o USING (office_id) WHERE o.office_code <> 'rnd') THEN
            RAISE EXCEPTION 'records belong to an office other than rnd; downgrading would merge the offices';
          END IF;
        END $$;"""
    )
    op.execute(_drop_policies())
    op.execute(DOWNGRADE)
