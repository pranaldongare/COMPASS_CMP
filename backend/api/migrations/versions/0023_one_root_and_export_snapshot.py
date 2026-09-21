"""One consent root per person and notice; the export file kept as written.

Two findings from the September 2026 review, both about records that were
weaker than their documentation said.

**One root.** `uq_artefact_supersedes_once` (0002) stops two artefacts naming
the same predecessor, so a chain cannot fork. It says nothing about two
artefacts with *no* predecessor: two first captures racing for the same person
and notice both found nothing current and both wrote a root, and
`v_current_consent` then held two live records for one pair. The service now
takes a per-(person, notice) advisory lock before it reads what is current;
this index is the database's own word on it, so the guarantee does not depend
on every future writer remembering the lock.

**The export file.** `export_log` recorded a hash of the CSV and the download
re-rendered the rows from the live tables, so a person renamed after the export
changed the bytes and the hash no longer matched the file a processor was
actually given. The file is now stored at generation (`file_ref`) and the
download serves those bytes. Older exports have no file and are re-rendered as
before; the hash comparison tells the two apart.

Revision ID: 0023
Revises: 0022
"""

from __future__ import annotations

from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None

UPGRADE = """
DO $$
DECLARE
  n integer;
BEGIN
  SELECT count(*) INTO n FROM (
    SELECT auth_user_id, notice_id
    FROM consent_artefact
    WHERE supersedes_consent_id IS NULL
    GROUP BY auth_user_id, notice_id
    HAVING count(*) > 1
  ) dup;
  IF n > 0 THEN
    RAISE EXCEPTION
      'migration 0023 refused: % (person, notice) pairs hold more than one root consent artefact; '
      'resolve them (a withdrawal superseding the duplicate) before applying',
      n;
  END IF;
END $$;

CREATE UNIQUE INDEX uq_artefact_one_root_per_notice
  ON consent_artefact (auth_user_id, notice_id)
  WHERE supersedes_consent_id IS NULL;

ALTER TABLE export_log ADD COLUMN file_ref text;
COMMENT ON COLUMN export_log.file_ref IS
  'Storage reference of the CSV exactly as generated; NULL for exports that predate 0023';
"""

DOWNGRADE = """
ALTER TABLE export_log DROP COLUMN IF EXISTS file_ref;
DROP INDEX IF EXISTS uq_artefact_one_root_per_notice;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
