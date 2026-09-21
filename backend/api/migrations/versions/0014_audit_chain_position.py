"""The audit chain draws its position inside the lock.

Migration 0002 serialised chain construction with a transaction-level advisory
lock, so that no two rows could read the same predecessor. It left one thing
outside the lock: the row's position. `log_id` came from the column default,
which PostgreSQL evaluates when the row is formed - before the trigger runs,
and therefore before the wait. Two inserts that formed their rows in one order
and were granted the lock in the other then chained in lock order while
carrying ids in the other order. `cmp_audit_verify()` walks by id, and reported
a break.

It is not a theoretical race. Four sign-ins arriving together produced three
rows that each named the same predecessor, because the row with the highest id
had committed first and stayed "the last row" for every insert that followed.
Nothing had been tampered with; the trail said something had.

This revision moves the draw inside the lock: the trigger assigns `log_id` from
the sequence once it holds the lock, and the column default is dropped so the
position can come from nowhere else. Whatever a statement supplies for `log_id`
is discarded. Ids are now in exactly the order the rows were chained, which is
the order verification assumes.

Rows already chained out of order stay as they are. The trail is append-only,
and a break that was not tampering is still a break to explain rather than
erase: `GET /audit/verify` names the first such row.

Revision ID: 0014
Revises: 0013
"""

from __future__ import annotations

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

AUDIT_CHAIN_FN = """
CREATE OR REPLACE FUNCTION cmp_audit_chain() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  prev_hash text;
  payload   text;
BEGIN
  -- Serialise chain construction. Two concurrent inserts that both read the same
  -- predecessor would produce two rows claiming the same position, and the chain
  -- would verify against neither.
  PERFORM pg_advisory_xact_lock(hashtext('cmp_audit_chain'));

  -- The position is drawn here, inside the lock - not by a column default, which
  -- would draw it before the wait. Rows are chained in the order the lock was
  -- granted, so that is the order their ids must have. Whatever the statement
  -- supplied for log_id is discarded.
  NEW.log_id := nextval(pg_get_serial_sequence('audit_log', 'log_id'));

  SELECT detail_json ->> '_hash' INTO prev_hash
  FROM audit_log ORDER BY log_id DESC LIMIT 1;

  payload := concat_ws('|',
    NEW.event_type,
    coalesce(NEW.actor_user_id::text, ''),
    coalesce(NEW.subject_user_id::text, ''),
    NEW.entity_type,
    NEW.entity_id::text,
    to_char(NEW.occurred_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.USOF'),
    coalesce(NEW.detail_json - '_hash' - '_prev', '{}'::jsonb)::text
  );

  NEW.detail_json := coalesce(NEW.detail_json, '{}'::jsonb)
    || jsonb_build_object(
         '_prev', prev_hash,
         '_hash', encode(digest(concat_ws('|', coalesce(prev_hash, ''), payload), 'sha256'), 'hex')
       );
  RETURN NEW;
END;
$$;

-- The sequence stays owned by the column; only the default goes. From here on
-- the trigger is the one place a position is given.
ALTER TABLE audit_log ALTER COLUMN log_id DROP DEFAULT;
"""

# The way back: 0002's function, and the default it relied on. Rows chained
# under 0014 verify the same either way - the payload and the digest have not
# changed, only when the position is drawn.
REVERT = """
ALTER TABLE audit_log ALTER COLUMN log_id
  SET DEFAULT nextval('audit_log_log_id_seq'::regclass);

CREATE OR REPLACE FUNCTION cmp_audit_chain() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  prev_hash text;
  payload   text;
BEGIN
  PERFORM pg_advisory_xact_lock(hashtext('cmp_audit_chain'));

  SELECT detail_json ->> '_hash' INTO prev_hash
  FROM audit_log ORDER BY log_id DESC LIMIT 1;

  payload := concat_ws('|',
    NEW.event_type,
    coalesce(NEW.actor_user_id::text, ''),
    coalesce(NEW.subject_user_id::text, ''),
    NEW.entity_type,
    NEW.entity_id::text,
    to_char(NEW.occurred_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.USOF'),
    coalesce(NEW.detail_json - '_hash' - '_prev', '{}'::jsonb)::text
  );

  NEW.detail_json := coalesce(NEW.detail_json, '{}'::jsonb)
    || jsonb_build_object(
         '_prev', prev_hash,
         '_hash', encode(digest(concat_ws('|', coalesce(prev_hash, ''), payload), 'sha256'), 'hex')
       );
  RETURN NEW;
END;
$$;
"""


def upgrade() -> None:
    op.execute(AUDIT_CHAIN_FN)


def downgrade() -> None:
    op.execute(REVERT)
