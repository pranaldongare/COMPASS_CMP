"""Who a report goes to, and a CERT-In mark set aside at any time (2026-11-07).

The product owner's answers of 2026-11-07 (ADR 0037). Three changes, as 0063
bundled three.

* **An address for one send, and a mandatory entry on the board's list.**
  `breach_board_recipient` gains `one_off`: an address the sender added for
  one report alone. It is never on the list, so the list, its uniqueness and
  Breach settings read only the rows where it is false; it lives in this table
  so that a delivery, the worker's job and the claim key read it as they read
  any entry. It gains `mandatory` too: an entry that goes with every report
  finalised while it is set, and cannot be taken off the list while it is set.
  The mark moves only with a `breach_board_recipient_event`, which says who
  moved it and when, by trigger, in 0061's idiom for a ticket's date. An entry
  is written once, and taken off once.
* **Who each finalised version went to.** `breach_report_addressee` is the set
  the sender chose when finalising, written before the version is frozen and
  never after. Every delivery now names an addressee of its report, by foreign
  key, so nothing is mailed to anyone a report was not addressed to. Every
  report finalised so far went to whoever its deliveries name, and that is
  what the backfill records. A report to CERT-In finalised before a yes has
  addressees and no deliveries: its mail waits for the yes.
* **A CERT-In mark set aside at any time.** 0034 made every not_applicable and
  reinstated event cite a determination, because validation was what set a
  DPDP duty aside or brought it back. CERT-In stands on its own test: a person
  marks it and a person sets it aside with a reason, and that may now happen
  before any validation, so there may be no determination to cite, and a mark
  made again after such a set-aside has none either. A CHECK cannot see the
  duty's kind, so it becomes a trigger, in 0039's shape, that keeps the rule
  for every duty validation moves. Every row already written cites one, 0063's
  backfill included, so nothing is backfilled.

The way down is refused once anybody has chosen anything: a one-off address
read by the older code would be on the list and mailed every report, a mark or
a held mail would be lost, and an entry a sender left out of a version would
be mailed it by the older Try again, which sends a version to everybody on
the list it has not reached. A version that went to everybody on the list as
it stood, as every version finalised before this migration did, is no choice:
its addressees are what the backfill wrote. Otherwise everything goes back as
it was, but for the CHECK, which comes back NOT VALID: a CERT-In event already
written without a determination is evidence and stays, and the narrower rule
binds the rows written after. Nobody should VALIDATE it.

Revision ID: 0064
Revises: 0063
"""

from __future__ import annotations

import os

from alembic import op

revision = "0064"
down_revision = "0063"
branch_labels = None
depends_on = None

APP_ROLE = os.getenv("CMP_DB_APP_ROLE", "cmp_app")

_ALL = "current_setting('app.office', true) = 'all'"


def _child_policy(table: str, parent: str, column: str, key: str) -> str:
    rule = f"{_ALL} OR EXISTS (SELECT 1 FROM {parent} p WHERE p.{key} = {table}.{column})"
    return f"""
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
CREATE POLICY office_isolation ON {table} USING ({rule}) WITH CHECK ({rule});
"""


UPGRADE = """
-- The list: an address for one send, and an entry every report must carry.
ALTER TABLE breach_board_recipient
  ADD COLUMN one_off   boolean NOT NULL DEFAULT false,
  ADD COLUMN mandatory boolean NOT NULL DEFAULT false;
COMMENT ON COLUMN breach_board_recipient.one_off IS
  'Added by the sender for one report alone. Never on the list: the list, its uniqueness and Breach settings read only rows where this is false';
COMMENT ON COLUMN breach_board_recipient.mandatory IS
  'Goes with every report finalised while set; cannot be taken off the list while set; changes only with a breach_board_recipient_event';
ALTER TABLE breach_board_recipient
  ADD CONSTRAINT breach_board_recipient_one_off_stays
    CHECK (NOT one_off OR (removed_at IS NULL AND NOT mandatory)),
  ADD CONSTRAINT breach_board_recipient_mandatory_is_listed
    CHECK (NOT mandatory OR removed_at IS NULL);
DROP INDEX uq_breach_board_recipient_active;
CREATE UNIQUE INDEX uq_breach_board_recipient_active ON breach_board_recipient (email_hash)
  WHERE removed_at IS NULL AND NOT one_off;

CREATE TABLE breach_board_recipient_event (
  event_id     serial PRIMARY KEY,
  recipient_id int NOT NULL REFERENCES breach_board_recipient(recipient_id),
  kind         varchar(10) NOT NULL,
  recorded_by  int NOT NULL REFERENCES auth_user(id),
  recorded_at  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT breach_board_recipient_event_kind CHECK (kind IN ('mandatory', 'optional'))
);
COMMENT ON TABLE breach_board_recipient_event IS
  'Each time an entry on the organisation''s board list was made mandatory, or optional again: who and when. Append-only';
CREATE INDEX idx_breach_board_recipient_event ON breach_board_recipient_event (recipient_id, event_id);
CREATE TRIGGER trg_breach_board_recipient_event_append_only
  BEFORE UPDATE OR DELETE ON breach_board_recipient_event
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();

-- An entry is written once. Its removal is written once. Its mark moves only
-- with the event that records it: the service writes the event first, in the
-- same transaction.
CREATE FUNCTION cmp_breach_board_recipient_read_only() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'an entry on the board list is never deleted'
      USING ERRCODE = 'restrict_violation';
  END IF;
  IF NEW.recipient_id IS DISTINCT FROM OLD.recipient_id
     OR NEW.recipient_uuid IS DISTINCT FROM OLD.recipient_uuid
     OR NEW.full_name IS DISTINCT FROM OLD.full_name
     OR NEW.email IS DISTINCT FROM OLD.email
     OR NEW.email_hash IS DISTINCT FROM OLD.email_hash
     OR NEW.added_by IS DISTINCT FROM OLD.added_by
     OR NEW.added_at IS DISTINCT FROM OLD.added_at
     OR NEW.one_off IS DISTINCT FROM OLD.one_off THEN
    RAISE EXCEPTION 'only the removal and the mark of a board list entry may change'
      USING ERRCODE = 'restrict_violation';
  END IF;
  IF OLD.removed_at IS NOT NULL AND (NEW.removed_at IS DISTINCT FROM OLD.removed_at
                                     OR NEW.removed_by IS DISTINCT FROM OLD.removed_by) THEN
    RAISE EXCEPTION 'an entry taken off the board list stays off'
      USING ERRCODE = 'restrict_violation';
  END IF;
  IF NEW.mandatory IS DISTINCT FROM OLD.mandatory AND NEW.mandatory IS DISTINCT FROM (
       SELECT e.kind = 'mandatory' FROM breach_board_recipient_event e
        WHERE e.recipient_id = NEW.recipient_id
        ORDER BY e.event_id DESC LIMIT 1) THEN
    RAISE EXCEPTION 'a board list entry''s mark changes only with the event that records it'
      USING ERRCODE = 'restrict_violation';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_breach_board_recipient_read_only
  BEFORE UPDATE OR DELETE ON breach_board_recipient
  FOR EACH ROW EXECUTE FUNCTION cmp_breach_board_recipient_read_only();

-- Who each finalised version was sent to.
CREATE TABLE breach_report_addressee (
  addressee_id serial PRIMARY KEY,
  report_id    int NOT NULL REFERENCES breach_report(report_id),
  recipient_id int NOT NULL REFERENCES breach_board_recipient(recipient_id),
  mandatory    boolean NOT NULL DEFAULT false,
  CONSTRAINT breach_report_addressee_once UNIQUE (report_id, recipient_id)
);
COMMENT ON TABLE breach_report_addressee IS
  'Who one version of a report is addressed to, as the sender chose them when finalising: entries on the list and one-off addresses. Written before the version is frozen, never after';
COMMENT ON COLUMN breach_report_addressee.mandatory IS
  'Whether the entry was mandatory when the version was finalised';
"""

#: Before the foreign key and the triggers: every report finalised so far went
#: to whoever its deliveries name, each pair once however many attempts it had.
BACKFILL = """
INSERT INTO breach_report_addressee (report_id, recipient_id)
SELECT DISTINCT d.report_id, d.recipient_id FROM breach_report_delivery d ORDER BY 1, 2;
"""

ADDRESSED = """
ALTER TABLE breach_report_delivery ADD CONSTRAINT breach_report_delivery_addressed
  FOREIGN KEY (report_id, recipient_id) REFERENCES breach_report_addressee (report_id, recipient_id);

CREATE FUNCTION cmp_breach_report_addressee_no_late_names() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM breach_report r
              WHERE r.report_id = NEW.report_id AND r.finalised_at IS NOT NULL) THEN
    RAISE EXCEPTION 'a finalised report goes to whom it went; write a new version'
      USING ERRCODE = 'restrict_violation';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_breach_report_addressee_no_late_names
  BEFORE INSERT ON breach_report_addressee
  FOR EACH ROW EXECUTE FUNCTION cmp_breach_report_addressee_no_late_names();
CREATE TRIGGER trg_breach_report_addressee_append_only
  BEFORE UPDATE OR DELETE ON breach_report_addressee
  FOR EACH STATEMENT EXECUTE FUNCTION cmp_append_only();
"""

CERT_IN = """
-- Validation sets the DPDP duties and the organisation's board aside and brings
-- them back, and each such event cites the determination that did it. CERT-In
-- stands on its own test: a person marks it and a person sets it aside, at any
-- time (2026-11-07), so its events may cite none. A CHECK cannot see the duty's
-- kind, which is on breach_obligation.
ALTER TABLE breach_obligation_event
  DROP CONSTRAINT breach_obligation_event_cites_determination;
CREATE FUNCTION cmp_breach_obligation_event_cites_determination() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.kind IN ('not_applicable', 'reinstated') AND NEW.determination_id IS NULL
     AND NOT EXISTS (SELECT 1 FROM breach_obligation
                      WHERE obligation_id = NEW.obligation_id AND kind = 'cert_in') THEN
    RAISE EXCEPTION 'a duty validation sets aside or brings back cites the determination that did it'
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_breach_obligation_event_cites_determination
  BEFORE INSERT ON breach_obligation_event
  FOR EACH ROW EXECUTE FUNCTION cmp_breach_obligation_event_cites_determination();
COMMENT ON COLUMN breach_obligation_event.determination_id IS
  'The determination that set the duty aside or brought it back. Required on not_applicable and reinstated events by trg_breach_obligation_event_cites_determination, except on a cert_in duty, which validation never moves';
"""

#: Nothing below can carry a choice about who a report goes to: a one-off
#: address would read as on the list, a mark or a held mail would go, and an
#: entry left out of a version would be mailed it by 0063's Try again. Left
#: out is an entry on the list when the version was finalised whose address
#: none of the version's addressees has; matched by address, so an entry
#: taken off and put back is the same one.
GUARD = """DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM breach_board_recipient WHERE one_off)
     OR EXISTS (SELECT 1 FROM breach_board_recipient_event)
     OR EXISTS (SELECT 1 FROM breach_report_addressee a
                 WHERE NOT EXISTS (SELECT 1 FROM breach_report_delivery d
                                    WHERE d.report_id = a.report_id
                                      AND d.recipient_id = a.recipient_id))
     OR EXISTS (SELECT 1 FROM breach_report r
                  JOIN breach_board_recipient x
                    ON NOT x.one_off
                   AND x.added_at <= r.finalised_at
                   AND (x.removed_at IS NULL OR x.removed_at > r.finalised_at)
                 WHERE r.finalised_at IS NOT NULL
                   AND NOT EXISTS (SELECT 1 FROM breach_report_addressee a
                                     JOIN breach_board_recipient y
                                       ON y.recipient_id = a.recipient_id
                                    WHERE a.report_id = r.report_id
                                      AND y.email_hash = x.email_hash)) THEN
    RAISE EXCEPTION 'choices were made about who reports go to; downgrading would lose them';
  END IF;
END $$;"""

DOWNGRADE = """
DROP TRIGGER IF EXISTS trg_breach_obligation_event_cites_determination ON breach_obligation_event;
DROP FUNCTION IF EXISTS cmp_breach_obligation_event_cites_determination();
COMMENT ON COLUMN breach_obligation_event.determination_id IS NULL;
-- NOT VALID: a CERT-In event already written without a determination is
-- evidence and stays; the narrower rule binds rows written after the downgrade.
ALTER TABLE breach_obligation_event ADD CONSTRAINT breach_obligation_event_cites_determination CHECK (
  kind NOT IN ('not_applicable', 'reinstated') OR determination_id IS NOT NULL
) NOT VALID;
ALTER TABLE breach_report_delivery DROP CONSTRAINT breach_report_delivery_addressed;
DROP TABLE breach_report_addressee;
DROP FUNCTION cmp_breach_report_addressee_no_late_names();
DROP TRIGGER trg_breach_board_recipient_read_only ON breach_board_recipient;
DROP FUNCTION cmp_breach_board_recipient_read_only();
DROP TABLE breach_board_recipient_event;
ALTER TABLE breach_board_recipient
  DROP CONSTRAINT breach_board_recipient_mandatory_is_listed,
  DROP CONSTRAINT breach_board_recipient_one_off_stays;
DROP INDEX uq_breach_board_recipient_active;
CREATE UNIQUE INDEX uq_breach_board_recipient_active ON breach_board_recipient (email_hash)
  WHERE removed_at IS NULL;
ALTER TABLE breach_board_recipient DROP COLUMN mandatory, DROP COLUMN one_off;
"""


def _grants(role: str) -> str:
    """Added to and read, never changed: 0003's default privileges would give
    the rest, as 0063 found."""
    return f"""
DO $$
DECLARE r text := {role!r};
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
    RAISE NOTICE 'Role % does not exist; skipping grants', r;
    RETURN;
  END IF;
  EXECUTE format('GRANT SELECT, INSERT ON TABLE breach_report_addressee TO %I', r);
  EXECUTE format('GRANT SELECT, INSERT ON TABLE breach_board_recipient_event TO %I', r);
  EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON TABLE breach_report_addressee FROM %I', r);
  EXECUTE format(
    'REVOKE UPDATE, DELETE, TRUNCATE ON TABLE breach_board_recipient_event FROM %I', r);
  EXECUTE format(
    'GRANT USAGE, SELECT ON SEQUENCE breach_report_addressee_addressee_id_seq TO %I', r);
  EXECUTE format(
    'GRANT USAGE, SELECT ON SEQUENCE breach_board_recipient_event_event_id_seq TO %I', r);
END $$;
"""


def upgrade() -> None:
    op.execute("SELECT set_config('app.office', 'all', false)")
    op.execute(UPGRADE)
    op.execute(BACKFILL)
    op.execute(ADDRESSED)
    op.execute(CERT_IN)
    op.execute(_child_policy("breach_report_addressee", "breach_report", "report_id", "report_id"))
    op.execute(_grants(APP_ROLE))


def downgrade() -> None:
    op.execute("SELECT set_config('app.office', 'all', false)")
    op.execute(GUARD)
    op.execute(DOWNGRADE)
