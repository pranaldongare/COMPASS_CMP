"""Rights tickets for holders outside the console (2026-10-08).

Two kinds of holder had no way to answer but by email, the office copying
their answer in by hand:

* **External** - a vendor, a third-party processor. Its ticket now comes as a
  link to the portal; the holder proves the address on the ticket with a
  one-time code and answers there, with files. Each email to it carries the
  link and nothing of the request. `rights_request_holder` gains:

  | Column | Holds |
  |---|---|
  | `link_token` | the link's keyed fingerprint (`token_fingerprint`), looked up when it is opened - the token itself is never stored in the clear |
  | `link_token_sealed` | the token, AES-GCM sealed (`seal_token`), so a reminder can carry the same link; as `consent_link.token_sealed` |
  | `link_issued_at` | when the current link was made; a ticket sent to somebody else gets a new one and the old stops working |

* **Internal, with no console login** - a colleague on one of the
  organisation's own domains. They are given a temporary login, as a breach
  ticket's holder is (S3-09), and the ticket is in their My tasks.
  `breach_temporary_access` - the one record of such logins, and the
  administrator's one off switch - now also records a grant for a rights
  ticket: `holder_id`, with `breach_id` and `ticket_id` then empty (exactly one
  of the two, by CHECK). A rights grant ends when the request closes
  (`request_closed`), the ticket is withdrawn (`ticket_withdrawn`) or sent to
  somebody else (`reassigned`). The table keeps its name: renaming the record
  of every grant made so far buys nothing.

Revision ID: 0049
Revises: 0048
"""

from __future__ import annotations

from alembic import op

revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None

END_ONCE = """
CREATE OR REPLACE FUNCTION cmp_breach_temporary_access_end_once() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'temporary access is never deleted' USING ERRCODE = 'restrict_violation';
  END IF;
  IF NEW.access_id IS DISTINCT FROM OLD.access_id
     OR NEW.access_uuid IS DISTINCT FROM OLD.access_uuid
     OR NEW.breach_id IS DISTINCT FROM OLD.breach_id
     OR NEW.holder_id IS DISTINCT FROM OLD.holder_id
     OR NEW.user_id IS DISTINCT FROM OLD.user_id
     OR NEW.ticket_id IS DISTINCT FROM OLD.ticket_id
     OR NEW.account_created IS DISTINCT FROM OLD.account_created
     OR NEW.previous_role IS DISTINCT FROM OLD.previous_role
     OR NEW.granted_by IS DISTINCT FROM OLD.granted_by
     OR NEW.granted_at IS DISTINCT FROM OLD.granted_at
     OR OLD.ended_at IS NOT NULL THEN
    RAISE EXCEPTION 'a grant of temporary access is written once and ended once'
      USING ERRCODE = 'restrict_violation';
  END IF;
  RETURN NEW;
END;
$$;
"""

OLD_END_ONCE = END_ONCE.replace("     OR NEW.holder_id IS DISTINCT FROM OLD.holder_id\n", "")


def upgrade() -> None:
    op.execute(
        """ALTER TABLE rights_request_holder
             ADD COLUMN link_token varchar(64) UNIQUE,
             ADD COLUMN link_token_sealed bytea,
             ADD COLUMN link_issued_at timestamptz"""
    )
    op.execute(
        "COMMENT ON COLUMN rights_request_holder.link_token IS "
        "'The portal link''s keyed fingerprint, for an external holder; the token is never stored'"
    )
    op.execute(
        "COMMENT ON COLUMN rights_request_holder.link_token_sealed IS "
        "'The link token, AES-GCM sealed, so a reminder carries the same link'"
    )
    op.execute(
        """ALTER TABLE rights_request_holder ADD CONSTRAINT holder_link_whole
             CHECK ((link_token IS NULL) = (link_token_sealed IS NULL)
                    AND (link_token IS NULL) = (link_issued_at IS NULL))"""
    )

    op.execute(
        """ALTER TABLE breach_temporary_access
             ALTER COLUMN breach_id DROP NOT NULL,
             ALTER COLUMN ticket_id DROP NOT NULL,
             ADD COLUMN holder_id int REFERENCES rights_request_holder(holder_id)"""
    )
    op.execute(
        """ALTER TABLE breach_temporary_access ADD CONSTRAINT temporary_access_for_one_ticket
             CHECK ((breach_id IS NOT NULL AND ticket_id IS NOT NULL AND holder_id IS NULL)
                 OR (breach_id IS NULL AND ticket_id IS NULL AND holder_id IS NOT NULL))"""
    )
    op.execute("ALTER TABLE breach_temporary_access DROP CONSTRAINT breach_temporary_access_cause")
    op.execute(
        """ALTER TABLE breach_temporary_access ADD CONSTRAINT breach_temporary_access_cause
             CHECK (end_cause IS NULL OR end_cause IN (
               'breach_closed', 'ticket_withdrawn', 'account_deactivated',
               'request_closed', 'reassigned'))"""
    )
    op.execute(
        """CREATE UNIQUE INDEX rights_temporary_access_open
             ON breach_temporary_access (holder_id, user_id)
             WHERE ended_at IS NULL AND holder_id IS NOT NULL"""
    )
    op.execute(
        "COMMENT ON TABLE breach_temporary_access IS "
        "'A temporary login: one grant of the breach_holder role for one breach (S3-09) or, "
        "since 0049, one rights ticket. Ends once; never deleted'"
    )
    op.execute(
        "COMMENT ON COLUMN breach_temporary_access.end_cause IS "
        "'breach_closed, request_closed, ticket_withdrawn, reassigned or account_deactivated'"
    )
    op.execute(END_ONCE)


def downgrade() -> None:
    # A rights grant cannot be put back as a breach one: refuse rather than lose it.
    op.execute(
        """DO $$ BEGIN
             IF EXISTS (SELECT 1 FROM breach_temporary_access WHERE holder_id IS NOT NULL) THEN
               RAISE EXCEPTION 'rights tickets hold temporary logins; end and keep them first';
             END IF;
           END $$"""
    )
    op.execute(OLD_END_ONCE)
    op.execute("DROP INDEX IF EXISTS rights_temporary_access_open")
    op.execute("ALTER TABLE breach_temporary_access DROP CONSTRAINT breach_temporary_access_cause")
    op.execute(
        """ALTER TABLE breach_temporary_access ADD CONSTRAINT breach_temporary_access_cause
             CHECK (end_cause IS NULL
                    OR end_cause IN ('breach_closed', 'ticket_withdrawn', 'account_deactivated'))"""
    )
    op.execute(
        "ALTER TABLE breach_temporary_access DROP CONSTRAINT temporary_access_for_one_ticket"
    )
    op.execute(
        """ALTER TABLE breach_temporary_access DROP COLUMN holder_id,
             ALTER COLUMN breach_id SET NOT NULL,
             ALTER COLUMN ticket_id SET NOT NULL"""
    )
    op.execute(
        "COMMENT ON TABLE breach_temporary_access IS "
        "'A breach-only login: one grant of the breach_holder role for one breach (S3-09, "
        "ADR 0023). Ends once; never deleted'"
    )
    op.execute(
        "COMMENT ON COLUMN breach_temporary_access.end_cause IS "
        "'breach_closed, ticket_withdrawn or account_deactivated'"
    )
    op.execute(
        """ALTER TABLE rights_request_holder DROP CONSTRAINT IF EXISTS holder_link_whole,
             DROP COLUMN IF EXISTS link_issued_at,
             DROP COLUMN IF EXISTS link_token_sealed,
             DROP COLUMN IF EXISTS link_token"""
    )
