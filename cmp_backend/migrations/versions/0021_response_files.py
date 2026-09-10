"""Files released with a response.

The response to a rights request was one file the platform wrote - the
record, as JSON - and the office's words. The office often has more to give
back: the extract a holder returned, a corrected document, a letter. Those
are kept with the request, released with the response, and downloaded from
her account on the same window as the record itself.

Revision ID: 0021
Revises: 0020
"""

from __future__ import annotations

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None

UPGRADE = """
CREATE TABLE rights_response_file (
  file_id      serial PRIMARY KEY,
  file_uuid    uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
  request_id   integer NOT NULL REFERENCES rights_request(request_id),
  file_ref     text NOT NULL,
  file_hash    text NOT NULL,
  file_name    varchar(255) NOT NULL,
  size_bytes   integer NOT NULL,
  content_type varchar(120),
  uploaded_by  integer REFERENCES auth_user(id),
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX rights_response_file_request_idx ON rights_response_file (request_id);
"""

DOWNGRADE = """
DROP TABLE IF EXISTS rights_response_file;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
