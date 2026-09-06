"""Rights requests: access, correction, erasure, grievance - and nomination.

Sections 11 to 14 of the Act give a data principal four things to ask for and
one person to name. Until now the platform *answered* two of them from its own
records - `/me/consents` and `/me/disclosures` - and told her how to ask for the
rest. This revision makes the asking a record: received when, verified how,
answered by when, and what every holder of her data was told to do about it.

Four tables, and why each is its own:

* **`rights_request`** is the request and its clock. The response period is
  copied onto the row at receipt (`due_at`) rather than computed from a setting
  on every read, because a period changed in configuration must not move the
  deadline of a request already running under the old one. The clock starts on
  receipt, not on verification - otherwise a slow verification quietly eats the
  window.

* **`rights_request_holder`** is one row per party that holds her data, and the
  ticket issued to it. Holders are *derived* - from `export_line` (who received a
  file with her in it) and `asset_consent` (which collected assets she appears
  in) - and then confirmed by the DPO, who adds what the records miss. The
  ticket lives on the same row because there is exactly one per holder.

* **`rights_request_item`** is the erasure scope: one row per appearance of her
  in a collected asset, each with a decision and its legal basis. Disposition
  is applied to `asset_consent`, never to `data_asset` - an asset holding three
  people does not get deleted because one of them asked (decision D-09), so
  her junction row is what changes and the other two are untouched.

* **`nomination`** is section 14: somebody she names, while well, to exercise
  her rights if she dies or cannot. Pending until the nominee accepts - a
  nomination he has never heard of cannot safely be acted on - and revocable by
  her at any time.

What is deliberately *not* here: consent artefacts are never erased by any of
this. They are the evidence that past processing was lawful, and s.6(4) depends
on their surviving. An erasure request changes what is held, not what was
agreed.

Revision ID: 0013
"""

from __future__ import annotations

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


ENUMS = """
CREATE TYPE rights_request_type AS ENUM ('access', 'correction', 'erasure', 'grievance');

-- Five states. Verification and classification are facts recorded on the row,
-- not states of their own: a request stays `received` until both are settled,
-- and moves to `in_progress` once. Closure carries an outcome.
CREATE TYPE rights_request_status AS ENUM
  ('received', 'in_progress', 'awaiting_holders', 'collating', 'closed');

CREATE TYPE rights_request_outcome AS ENUM (
  'complete',                 -- answered in full
  'partial',                  -- answered on time with a named gap
  'no_records',               -- nothing held anywhere; a complete answer
  'refused',                  -- not an access request, or refused with reasons
  'not_verified',             -- identity could not be established
  'reclassified_withdrawal',  -- she meant withdrawal, handled under s.6(4)
  'upheld',                   -- a grievance, found for her
  'not_upheld'                -- a grievance, reasoned against
);

CREATE TYPE rights_request_channel AS ENUM ('portal', 'public_form', 'staff_logged', 'nominee');
CREATE TYPE rights_verification_method AS ENUM ('session', 'code', 'manual');
CREATE TYPE rights_verification_status AS ENUM ('pending', 'verified', 'failed');
CREATE TYPE rights_holder_source AS ENUM ('export_line', 'asset_consent', 'manual');
CREATE TYPE rights_ticket_status AS ENUM ('pending', 'issued', 'escalated', 'returned', 'unreturned');
CREATE TYPE rights_item_state AS ENUM ('proposed', 'decided', 'instructed', 'applied');
CREATE TYPE rights_scope_decision AS ENUM ('erase', 'redact', 'retain', 'quarantine');
CREATE TYPE rights_trigger_event AS ENUM ('death', 'incapacity');
CREATE TYPE nomination_status AS ENUM ('pending', 'active', 'declined', 'revoked');
"""


TABLES = """
CREATE SEQUENCE rights_request_ref_seq;

CREATE TABLE nomination (
  nomination_id     serial PRIMARY KEY,
  nomination_uuid   uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  principal_user_id int NOT NULL REFERENCES auth_user(id),
  nominee_name      varchar(200) NOT NULL,
  nominee_contact   varchar(255) NOT NULL,
  -- Which of her rights he may exercise. Partial scope is allowed: naming
  -- somebody to ask for access is not the same decision as letting them ask
  -- for erasure.
  rights            rights_request_type[] NOT NULL,
  status            nomination_status NOT NULL DEFAULT 'pending',
  -- The acceptance link is a capability. Only its keyed digest is stored.
  accept_token_hash text,
  accept_expires_at timestamptz,
  accepted_at       timestamptz,
  declined_at       timestamptz,
  revoked_at        timestamptz,
  created_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT nomination_rights_not_empty CHECK (cardinality(rights) >= 1),
  CONSTRAINT nomination_status_dates CHECK (
    (status = 'active'   AND accepted_at IS NOT NULL) OR
    (status = 'declined' AND declined_at IS NOT NULL) OR
    (status = 'revoked'  AND revoked_at  IS NOT NULL) OR
    (status = 'pending'))
);

-- One live nomination per person. Whether more than one nominee should be
-- allowed is an open question for Legal; until it is answered the safe default
-- is the one that cannot produce two people claiming the same standing.
CREATE UNIQUE INDEX uq_nomination_live
  ON nomination (principal_user_id) WHERE status IN ('pending', 'active');
CREATE INDEX idx_nomination_principal ON nomination (principal_user_id);

CREATE TABLE rights_request (
  request_id          serial PRIMARY KEY,
  request_uuid        uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  -- The reference she quotes. Human-readable and never reused.
  reference           varchar(24) NOT NULL UNIQUE,
  request_type        rights_request_type NOT NULL,
  -- What it arrived as, kept when the DPO reclassifies it.
  original_type       rights_request_type,
  status              rights_request_status NOT NULL DEFAULT 'received',
  outcome             rights_request_outcome,
  channel             rights_request_channel NOT NULL,
  -- NULL until the contact matches somebody we hold records for. A request
  -- from a contact we do not know is still recorded - the neutral reply must
  -- not depend on whether it was.
  subject_user_id     int REFERENCES auth_user(id),
  submitted_name      varchar(200),
  submitted_contact   varchar(255) NOT NULL,
  request_text        text NOT NULL,
  received_at         timestamptz NOT NULL DEFAULT now(),
  -- Frozen at receipt. See the module docstring.
  due_at              timestamptz NOT NULL,
  acknowledged_at     timestamptz,
  verification_method rights_verification_method,
  verification_status rights_verification_status NOT NULL DEFAULT 'pending',
  verified_at         timestamptz,
  verified_by         int REFERENCES auth_user(id),
  verification_note   text,
  classified_at       timestamptz,
  classified_by       int REFERENCES auth_user(id),
  refusal_reason      text,
  -- Erasure only: she confirmed she means erasure, not withdrawal.
  intent_confirmed_at timestamptz,
  -- A grievance about a request, or a re-run ordered by a grievance.
  linked_request_id   int REFERENCES rights_request(request_id),
  -- Section 14: the nominee acting, and the event that lets him.
  nomination_id       int REFERENCES nomination(nomination_id),
  trigger_event       rights_trigger_event,
  trigger_evidence_ref  text,
  trigger_evidence_hash text,
  trigger_evidenced_at  timestamptz,
  -- Section 13: a complaint about the DPO cannot be reviewed by the DPO.
  about_dpo           boolean NOT NULL DEFAULT false,
  reviewer_user_id    int REFERENCES auth_user(id),
  escalated_at        timestamptz,
  grievance_upheld    boolean,
  remedy_text         text,
  response_text       text,
  response_file_ref   text,
  response_file_hash  text,
  responded_at        timestamptz,
  responded_by        int REFERENCES auth_user(id),
  -- The response is fetched from her dashboard, authenticated and for a while.
  download_expires_at timestamptz,
  closed_at           timestamptz,
  created_by          int REFERENCES auth_user(id),
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT rights_closed_has_outcome CHECK (status <> 'closed' OR outcome IS NOT NULL),
  CONSTRAINT rights_refusal_has_reason CHECK (outcome <> 'refused' OR refusal_reason IS NOT NULL),
  CONSTRAINT rights_verified_is_attributed CHECK (
    verification_status <> 'verified'
    OR (verified_at IS NOT NULL AND verification_method IS NOT NULL)),
  CONSTRAINT rights_nominee_has_nomination CHECK (channel <> 'nominee' OR nomination_id IS NOT NULL),
  CONSTRAINT rights_due_after_receipt CHECK (due_at > received_at)
);

CREATE INDEX idx_rights_request_subject    ON rights_request (subject_user_id);
CREATE INDEX idx_rights_request_status_due ON rights_request (status, due_at);
CREATE INDEX idx_rights_request_linked     ON rights_request (linked_request_id);

CREATE TABLE rights_request_holder (
  holder_id         serial PRIMARY KEY,
  holder_uuid       uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  request_id        int NOT NULL REFERENCES rights_request(request_id),
  -- NULL for a holder the DPO named that the registry does not know.
  processor_id      int REFERENCES processor(processor_id),
  label             varchar(200) NOT NULL,
  derived_from      rights_holder_source NOT NULL,
  -- What named this holder: the exports and assets, by uuid, so the DPO can
  -- see why a party is on the list before confirming it.
  evidence          jsonb NOT NULL DEFAULT '{}'::jsonb,
  confirmed_at      timestamptz,
  confirmed_by      int REFERENCES auth_user(id),
  ticket_status     rights_ticket_status NOT NULL DEFAULT 'pending',
  instruction       text,
  responder_name    varchar(200),
  responder_contact varchar(255),
  issued_at         timestamptz,
  due_at            timestamptz,
  escalated_at      timestamptz,
  returned_at       timestamptz,
  return_summary    text,
  return_evidence_ref  text,
  return_evidence_hash text,
  created_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT holder_issued_has_date CHECK (ticket_status = 'pending' OR issued_at IS NOT NULL),
  CONSTRAINT holder_returned_has_date CHECK (ticket_status <> 'returned' OR returned_at IS NOT NULL)
);

CREATE INDEX idx_rights_holder_request ON rights_request_holder (request_id);
-- A processor is one holder per request; a manual holder may repeat a label.
CREATE UNIQUE INDEX uq_rights_holder_processor
  ON rights_request_holder (request_id, processor_id) WHERE processor_id IS NOT NULL;

CREATE TABLE rights_request_item (
  item_id           serial PRIMARY KEY,
  item_uuid         uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  request_id        int NOT NULL REFERENCES rights_request(request_id),
  asset_consent_id  int NOT NULL REFERENCES asset_consent(asset_consent_id),
  holder_id         int REFERENCES rights_request_holder(holder_id),
  -- How many other people appear in the same asset, at derivation. Zero means
  -- ordinary erasure; anything else means redaction, because deleting the
  -- file would erase their validly given consent along with her contribution.
  other_subjects    int NOT NULL DEFAULT 0,
  state             rights_item_state NOT NULL DEFAULT 'proposed',
  decision          rights_scope_decision,
  basis             text,
  -- A retention floor that binds even against her request (Rule 6, Rule 8(3)).
  -- Stated in the response, and erased when it passes.
  retain_until      date,
  floor_passed_at   timestamptz,
  decided_at        timestamptz,
  decided_by        int REFERENCES auth_user(id),
  applied_at        timestamptz,
  created_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (request_id, asset_consent_id),
  CONSTRAINT item_decision_has_basis CHECK (decision IS NULL OR basis IS NOT NULL),
  CONSTRAINT item_retain_has_until CHECK (decision IS DISTINCT FROM 'retain' OR retain_until IS NOT NULL),
  CONSTRAINT item_decided_is_attributed CHECK (decision IS NULL OR decided_at IS NOT NULL)
);

CREATE INDEX idx_rights_item_request ON rights_request_item (request_id);
CREATE INDEX idx_rights_item_floor
  ON rights_request_item (retain_until) WHERE decision = 'retain' AND floor_passed_at IS NULL;

COMMENT ON TABLE rights_request IS
  'A data principal''s request under ss.11-14 of the DPDP Act, and its clock. '
  'The clock starts on receipt, not on verification.';
COMMENT ON COLUMN rights_request.due_at IS
  'Copied from the published response period at receipt. A period changed later '
  'does not move a request already running.';
COMMENT ON TABLE rights_request_item IS
  'The erasure scope: one row per appearance of the principal in a collected '
  'asset. Disposition is applied to asset_consent, never to data_asset.';
"""


REVERT = """
DROP TABLE IF EXISTS rights_request_item;
DROP TABLE IF EXISTS rights_request_holder;
DROP TABLE IF EXISTS rights_request;
DROP TABLE IF EXISTS nomination;
DROP SEQUENCE IF EXISTS rights_request_ref_seq;
DROP TYPE IF EXISTS nomination_status;
DROP TYPE IF EXISTS rights_trigger_event;
DROP TYPE IF EXISTS rights_scope_decision;
DROP TYPE IF EXISTS rights_item_state;
DROP TYPE IF EXISTS rights_ticket_status;
DROP TYPE IF EXISTS rights_holder_source;
DROP TYPE IF EXISTS rights_verification_status;
DROP TYPE IF EXISTS rights_verification_method;
DROP TYPE IF EXISTS rights_request_channel;
DROP TYPE IF EXISTS rights_request_outcome;
DROP TYPE IF EXISTS rights_request_status;
DROP TYPE IF EXISTS rights_request_type;
"""


def upgrade() -> None:
    op.execute(ENUMS)
    op.execute(TABLES)


def downgrade() -> None:
    # Dropping these discards every request, ticket, decision and nomination
    # recorded since 0013. The audit trail keeps the events that describe them,
    # which is the record of what happened - but not the requests themselves.
    op.execute(REVERT)
