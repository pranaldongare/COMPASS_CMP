"""Notice templates: the DPO's notices, before there is a project (2026-10-07).

The Privacy Office writes notices ahead of the studies that will use them, and
until now could not: a notice belongs to a project, and the project did not
exist yet. A template is that notice without a project - the Rule 3 links and
the DPO contact, who it addresses, the purposes it carries and the text of each
language - with a short ID (`TPL-0007`) the DPO gives the study's R&D User.

A template is never served and never consented to. It is not evidence, so it
stays editable, and it is only ever *copied*: attaching one to a project makes
that project's own draft notice from it (`notice.template_id` records which),
and that notice is approved and published like any other. Two projects that
use one template have two notices, so "which text, for which project" keeps
one answer. Why not a `notice` with no project: a published notice is consent
evidence and every notice read is scoped through its project (ADR 0004);
a projectless one breaks both.

A template is retired, never deleted: the notices made from it point at it.

Revision ID: 0044
Revises: 0043
"""

from __future__ import annotations

from alembic import op

revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None

UPGRADE = """
CREATE SEQUENCE notice_template_code_seq;

CREATE TABLE notice_template (
  template_id          serial PRIMARY KEY,
  template_uuid        uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  template_code        varchar(20) NOT NULL UNIQUE
                         DEFAULT 'TPL-' || lpad(nextval('notice_template_code_seq')::text, 4, '0'),
  title                varchar(200) NOT NULL,
  withdraw_url         text NOT NULL,
  exercise_rights_url  text NOT NULL,
  board_complaint_url  text NOT NULL,
  dpo_contact          varchar(255) NOT NULL,
  applicable_to        notice_audience,
  note                 text,
  status               varchar(20) NOT NULL DEFAULT 'active',
  created_by           int NOT NULL REFERENCES auth_user(id),
  created_at           timestamptz NOT NULL DEFAULT now(),
  updated_at           timestamptz NOT NULL DEFAULT now(),
  retired_at           timestamptz,
  CONSTRAINT notice_template_status CHECK (status IN ('active', 'retired')),
  CONSTRAINT notice_template_retired_at CHECK ((status = 'retired') = (retired_at IS NOT NULL))
);
ALTER SEQUENCE notice_template_code_seq OWNED BY notice_template.template_code;
COMMENT ON TABLE notice_template IS
  'A notice the DPO writes before a project exists. Never served; copied into a project as its draft notice';
COMMENT ON COLUMN notice_template.template_code IS
  'The ID the DPO gives an R&D User to attach it, minted by the database';

CREATE TABLE notice_template_purpose (
  template_purpose_id  serial PRIMARY KEY,
  template_id          int NOT NULL REFERENCES notice_template(template_id),
  purpose_id           int NOT NULL REFERENCES purpose(purpose_id),
  display_order        int NOT NULL DEFAULT 0,
  is_mandatory         boolean NOT NULL DEFAULT false,
  CONSTRAINT notice_template_purpose_once UNIQUE (template_id, purpose_id)
);

CREATE TABLE notice_template_language (
  template_language_id serial PRIMARY KEY,
  template_id          int NOT NULL REFERENCES notice_template(template_id),
  language_code        language_code NOT NULL,
  rendered_text        text NOT NULL,
  updated_by           int NOT NULL REFERENCES auth_user(id),
  updated_at           timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT notice_template_language_once UNIQUE (template_id, language_code)
);

ALTER TABLE notice ADD COLUMN template_id int REFERENCES notice_template(template_id);
COMMENT ON COLUMN notice.template_id IS
  'The template this notice was made from, if any. The notice is a copy: changing the template changes nothing here';
CREATE INDEX idx_notice_template ON notice (template_id) WHERE template_id IS NOT NULL;
"""

DOWNGRADE = """
ALTER TABLE notice DROP COLUMN IF EXISTS template_id;
DROP TABLE IF EXISTS notice_template_language;
DROP TABLE IF EXISTS notice_template_purpose;
DROP TABLE IF EXISTS notice_template;
DROP SEQUENCE IF EXISTS notice_template_code_seq;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
