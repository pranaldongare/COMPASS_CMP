"""One published notice per project.

A project collects under one notice at a time: the one a data principal is
shown, and the one a new consent is recorded against. Publishing superseded only
earlier versions of the *same code*, so a notice that arrived under a code of its
own - "New notice", "Use an existing notice", an uploaded document - could be
published beside the one already in force, leaving a project with two.

`domain/notices/service.publish` now supersedes every other published notice on
the project before publishing, and moves the replaced notice's live consent
links to the new one. This index makes the rule the database's as well: a
second published notice on one project is refused whatever wrote it.

It refuses to apply over data that already breaks the rule rather than choose
which notice to keep - that choice is the Privacy Office's.

Revision ID: 0033
Revises: 0032
"""

from __future__ import annotations

from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None

GUARD = """
DO $$
DECLARE
  offenders text;
BEGIN
  SELECT string_agg(p.project_name || ' (' || x.n || ')', ', ')
    INTO offenders
    FROM (SELECT project_id, count(*) AS n FROM notice
           WHERE status = 'published' GROUP BY project_id HAVING count(*) > 1) x
    JOIN project p ON p.project_id = x.project_id;
  IF offenders IS NOT NULL THEN
    RAISE EXCEPTION USING
      MESSAGE = 'Projects with more than one published notice: ' || offenders,
      HINT = 'Decide with the Privacy Office which notice stays in force, set the '
             'others to superseded, then re-run the migration.';
  END IF;
END
$$;
"""

UPGRADE = """
CREATE UNIQUE INDEX uq_notice_one_published_per_project
  ON notice (project_id) WHERE status = 'published';
COMMENT ON INDEX uq_notice_one_published_per_project IS
  'A project collects under one notice at a time; publishing supersedes the rest.';
"""

DOWNGRADE = """
DROP INDEX IF EXISTS uq_notice_one_published_per_project;
"""


def upgrade() -> None:
    op.execute(GUARD)
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
