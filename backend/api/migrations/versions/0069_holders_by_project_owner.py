"""A rights request's holders also come from who owns the project or activity (2026-11-12).

"Find who holds the data" read three records - an export that carried her
consent to a processor, an asset a processor's source captured, an HR
activity's category processors - and where a project had none of them yet it
found nobody: an empty list, on a person with consents on record. Every
consent is given against a project or an activity, and somebody here answers
for each: a DCO Admin, who routes a project's collection, and the HR PoC who
runs an activity (the product owner, 2026-11-12). They are the first to ask
where her data went, so they are now found too, one holder per project or
activity, answered in the console.

* `rights_holder_source` gains `project_owner`: the holder that answers for
  a project or an activity itself, where no processor is on record for it.
* `rights_request_holder.project_id` names the project or activity such a
  holder stands for. One per request, so finding twice refreshes the row
  rather than adding a second - as `(request_id, processor_id)` does for a
  processor.
* `rights_request.holders_derived_at` records that the records have been
  read for this request. Until then the page has nothing to say about
  consents nobody is named for; after it, it lists them.

PostgreSQL cannot drop an enum value, so the way down leaves `project_owner`
and removes the rest; it refuses while a holder of that kind exists, since
the row would then say it was derived from nothing.

Revision ID: 0069
Revises: 0068
"""

from __future__ import annotations

from alembic import op

revision = "0069"
down_revision = "0068"
branch_labels = None
depends_on = None

UPGRADE = """
ALTER TABLE rights_request_holder
  ADD COLUMN project_id int REFERENCES project(project_id);
COMMENT ON COLUMN rights_request_holder.project_id IS
  'The project or activity whose owner this holder is (derived_from = project_owner); NULL otherwise';
CREATE UNIQUE INDEX rights_holder_one_per_project
  ON rights_request_holder (request_id, project_id) WHERE project_id IS NOT NULL;
ALTER TABLE rights_request_holder
  ADD CONSTRAINT holder_project_is_an_owner
  CHECK ((project_id IS NOT NULL) = (derived_from = 'project_owner'));

ALTER TABLE rights_request ADD COLUMN holders_derived_at timestamptz;
COMMENT ON COLUMN rights_request.holders_derived_at IS
  'When the office last read the records for who holds her data; NULL: not yet';
"""

DOWNGRADE = """
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM rights_request_holder WHERE project_id IS NOT NULL) THEN
    RAISE EXCEPTION 'Holders derived from a project owner exist; remove them before downgrading';
  END IF;
END $$;
ALTER TABLE rights_request DROP COLUMN holders_derived_at;
ALTER TABLE rights_request_holder DROP CONSTRAINT holder_project_is_an_owner;
DROP INDEX rights_holder_one_per_project;
ALTER TABLE rights_request_holder DROP COLUMN project_id;
"""


def upgrade() -> None:
    # An enum value has to be committed before anything can reference it.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE rights_holder_source ADD VALUE IF NOT EXISTS 'project_owner'")
    op.execute("SELECT set_config('app.office', 'all', false)")
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute("SELECT set_config('app.office', 'all', false)")
    op.execute(DOWNGRADE)
