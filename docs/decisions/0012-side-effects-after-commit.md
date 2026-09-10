# 0012. Side effects wait for the commit; a durable outbox is deferred

Status: accepted. September 2026.

## Context

Services queued Celery tasks while their transaction was open. A worker
could pick up a receipt for an artefact not yet visible, and a rollback
after the queueing still sent the message. The review recommended a
transactional outbox: an event row in the same transaction, relayed by a
worker, with delivery tracking and deduplication.

## Decision

Two halves, one taken now.

**Taken.** `cmp.core.after_commit` gives a unit of work a list of deferred
hooks. `pool.transaction()` opens one; `dispatch_optional` registers the
queueing there instead of doing it; the hooks run after the commit, in
order, and are dropped on rollback. Outside a unit of work the queueing
happens at once, as before. `dispatch_required` still queues immediately
because for a sign-in code the queueing is the outcome and a 503 is the
right answer when it fails.

**Deferred.** A durable outbox table and relay. What it adds over the
deferral is survival of a broker outage at the moment of flushing and a
place to deduplicate per recipient. What it costs is a table, a relay task,
a delivery-state model and a second path to reason about. The deferral
closes the two failure modes that were confirmed; the remaining one is
logged at error, as it was, and is alertable.

## Consequences

- A notification never describes a row that does not exist.
- The task id is logged when the task is actually queued, not returned to
  the caller.
- The audit-chain lock is held for no longer than before; nothing in the
  deferral runs inside the transaction.
- The gap: a broker unreachable during the flush loses that message with an
  `after_commit.hook_failed` or `task.dispatch_failed` error line. The
  checkpoint reminders in the rights module re-raise what matters.

## Revisit when

A dropped receipt or ticket notification is unacceptable rather than
inconvenient. Then: an `outbox` table written by `defer`, a relay task on the
`default` queue, `event_id` on every message, and the worker deduplicating
on it.
