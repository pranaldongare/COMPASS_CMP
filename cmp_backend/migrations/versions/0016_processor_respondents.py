"""Respondents on a processor, and the channel a holder's ticket travels by.

A rights request goes out to the parties that hold the person's data as a
ticket per holder. Until now the responder was typed onto the holder by hand,
per request, and every ticket was an email - whoever the holder was. Two
things were wrong with that. A holder that is one of our own teams should not
be reached by email at all: the person answering has an account here, and the
ticket should be in front of them when they sign in. And a holder that is a
third party is reached by email, but nothing recorded that the mail was sent,
chased, or answered - the DPO tracked that in her inbox, not on the request.

So a processor now carries its respondents: who answers a ticket for it, and
at what address. For a processor that is in-house the respondent is an
account (`user_id` set), and a ticket addressed to them travels by the portal;
for a third party it is a name and an address, and the ticket travels by
email. A holder records which respondent it went to, the account where there
is one, the channel, and a log of every contact made on it.

Respondents are removed by stamping `removed_at`, never deleted: a holder on a
closed request still points at the person it was sent to.

Revision ID: 0016
Revises: 0015
"""

from __future__ import annotations

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

UPGRADE = """
CREATE TABLE processor_respondent (
  respondent_id   serial PRIMARY KEY,
  respondent_uuid uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  processor_id    int NOT NULL REFERENCES processor(processor_id),
  name            varchar(200) NOT NULL,
  contact         varchar(255) NOT NULL,
  -- Set for a respondent who has an account here: an in-house team's
  -- contact. A ticket to them goes to the portal, not to an inbox.
  user_id         int REFERENCES auth_user(id),
  created_at      timestamptz NOT NULL DEFAULT now(),
  removed_at      timestamptz
);
CREATE INDEX idx_processor_respondent_live
  ON processor_respondent (processor_id) WHERE removed_at IS NULL;
-- One live row per account per processor. A name-and-address respondent may
-- repeat; an account may not.
CREATE UNIQUE INDEX uq_processor_respondent_user
  ON processor_respondent (processor_id, user_id)
  WHERE user_id IS NOT NULL AND removed_at IS NULL;

ALTER TABLE rights_request_holder
  ADD COLUMN respondent_id     int REFERENCES processor_respondent(respondent_id),
  ADD COLUMN responder_user_id int REFERENCES auth_user(id),
  ADD COLUMN channel           varchar(10) NOT NULL DEFAULT 'email',
  ADD COLUMN contact_log       jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD CONSTRAINT holder_channel CHECK (channel IN ('portal', 'email')),
  ADD CONSTRAINT holder_portal_has_account
    CHECK (channel <> 'portal' OR responder_user_id IS NOT NULL);
CREATE INDEX idx_rights_holder_responder
  ON rights_request_holder (responder_user_id) WHERE responder_user_id IS NOT NULL;
"""

DOWNGRADE = """
DROP INDEX IF EXISTS idx_rights_holder_responder;
ALTER TABLE rights_request_holder
  DROP CONSTRAINT IF EXISTS holder_portal_has_account,
  DROP CONSTRAINT IF EXISTS holder_channel,
  DROP COLUMN IF EXISTS contact_log,
  DROP COLUMN IF EXISTS channel,
  DROP COLUMN IF EXISTS responder_user_id,
  DROP COLUMN IF EXISTS respondent_id;
DROP TABLE IF EXISTS processor_respondent;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
