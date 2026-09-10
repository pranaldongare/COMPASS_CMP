# 0005. The audit chain position is drawn inside the advisory lock

Status: accepted. Migration 0014, September 2026.

## Context

The audit log is a SHA-256 hash chain: each row's hash covers the previous
row's hash. The chain trigger serialised writers with a transaction-scoped
advisory lock, but the row's position, `log_id`, came from a column default
evaluated **before** the trigger took the lock. Under concurrent sign-ins
two transactions could draw positions 1501 and 1502, then take the lock in
the other order, and the chain verified as broken at 1502 although nothing
had been tampered with.

Found by running the browser suite in parallel against a development
database; `GET /audit/verify` reported a break at a row nobody had touched.

## Decision

Drop the column default. The trigger draws the position from the sequence
after acquiring `pg_advisory_xact_lock(hashtext('cmp_audit_chain'))`, so
position and predecessor are chosen under the same lock and the chain order
is the commit order.

Existing rows are not rewritten; the evidence tables forbid it, and the rows
are genuine. The development database was rebuilt. A production chain broken
before this migration would verify from the row after the break, and the
finding is recorded rather than repaired.

## Consequences

- Every audited write serialises on one lock for the duration of the
  insert. That is a few milliseconds and was already true of the trigger.
- The parallel browser suite still cannot share a database with the backend
  suite: the lock turns the two into timeouts, which is a test-orchestration
  rule, not a defect.
- `tests/integration/test_audit_chain_position.py` runs concurrent writers
  and verifies the chain afterwards.

## Revisit when

Audit write volume makes one lock a bottleneck. Partitioning the chain by
subject would be the next step, and is a schema change, not a code change.
