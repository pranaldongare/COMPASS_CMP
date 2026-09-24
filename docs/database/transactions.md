# Transactions

## The unit of work

`db/pool.py` offers two context managers:

* `connection()` — a connection for reads.
* `transaction()` — a connection inside a transaction, committed on clean exit
  and rolled back on any exception.

A router that writes opens `transaction()` and hands the connection to a service.
The service does everything inside it.

## What must be in one transaction

**A change and its audit row.** Always. This is what makes the audit trail a
property rather than a convention — there is no window in which the change exists
and the record of it does not.

**A transition and its side effects.** `pending_approval → approved` publishes
the project's notice. Both happen together, or a project would be approved with
an unpublished notice. (`under_process` used to sit in the middle of this and
no longer does; nothing transitions to it.)

**An import.** A manifest either lands or does not. Splitting it across a queue
would make `partial` mean two different things.

**An export and its lines.** The disclosure record and the file must agree.

## Timeouts

Set on the connection, not left to hope:

| Setting | Default | Stops |
|---|---|---|
| `db_statement_timeout_ms` | 15,000 | A runaway query holding a worker |
| `db_lock_timeout_ms` | 5,000 | A blocked write queueing behind a long read |
| `idle_in_transaction_session_timeout` | 30,000 (fixed, `db/pool.py`) | A transaction left open while its caller waits on something else |

The third is not a setting, and it matters more than it used to: a transaction
waiting on the key service (below) is idle in transaction for as long as the
call takes.

## Sealing happens inside the transaction

Personal columns are encrypted by the key service, a separate process reached
over HTTP ([ADR 0016](../decisions/0016-personal-data-sealed-by-a-separate-key-service.md)).
The repositories do it: a write of a sealed table calls `seal()` on the
caller's connection, just before its `INSERT` or `UPDATE`
(`db/repositories/users.py`, `rights.py`, `consent.py`, `registry.py` and the
rest), and `seal()` is a POST to `/bulk_encrypt` (`infrastructure/dkms/client.py`).
So a write that carries personal data holds its transaction, its row locks and
its pooled connection open across a network round trip: one call per row or
per batch of up to `DKMS_BATCH_SIZE` (500) records, each bounded by
`DKMS_TIMEOUT_S` (5 s).

Three consequences:

**It fails closed, and the whole unit of work goes.** A key service that
cannot be reached raises `DkmsUnavailable`, a 503, and the transaction rolls
back: the change and its audit row together, as with any other failure. There
is no fallback to writing plaintext.

**The audit lock can be held across the call.** The chain trigger takes
`pg_advisory_xact_lock('cmp_audit_chain')` on the first audit insert of a
transaction and keeps it until commit
([ADR 0005](../decisions/0005-audit-chain-position-inside-the-lock.md)). A
transaction that records an audit row and *then* seals something waits on the
key service with that lock held, and every other audited write on the
platform waits with it. `PATCH /me` does this today: it records
`user.contact_changed` (`api/routers/v1/me.py:166`) and then adds a secondary
email, which seals it (`me.py:176` → `users.set_secondary_email` →
`db/repositories/users.py:339`). Nothing enforces "seal before the first
audit row"; keep new code in that order.

**Reading is mostly outside.** The API serves rows as stored and the portals
open them, so a read transaction does not call the key service. The
exceptions are the places the backend must act on a value (`opened()`,
`unseal_value()`): a message's recipient, a greeting, an export's lines, a
rights package.

## Side effects that open a sealed value

A message's recipient and the name in it may be sealed. They are opened in the
worker, at `deliver()`, after the commit and synchronously
(`infrastructure/messaging/__init__.py`, `unseal_values_sync`). If the key
service cannot be reached there, the task raises `DkmsUnavailable` and Celery
retries it with the same backoff as a transport failure
(`tasks/authentication/otp.py`, `RETRY_KW`). The request that queued the
message has already answered "a code has been sent"; the retry is what keeps
that true. See [ADR 0012](../decisions/0012-side-effects-after-commit.md).

## Migrations and the reseal script

0028 and 0030 call the key service from inside the migration's transaction,
with the tables locked by `ADD COLUMN`; `scripts/reseal.py` opens one
transaction per column and seals it batch by batch. Both are in
[migrations.md](migrations.md).

## Row locks

`require_for_update` takes `FOR UPDATE` on a project before a transition reads
its facts, so two concurrent transitions cannot both see the same starting state
and both succeed.

## Tests run in a rolled-back transaction

Each integration test gets a connection whose transaction is rolled back
afterwards, so tests neither see nor leave each other's rows — and the suite can
run against a database with real data in it without touching it.

## Side effects wait for the commit

A service that needs a task queued calls `dispatch_optional` inside its
transaction. The call is recorded by `cmp.core.after_commit` and made after
the unit of work commits; if the transaction rolls back nothing is queued.
`pool.transaction()` opens the unit of work, so a script or a test that
opened its own connection sees the queueing happen at once, as before.
`dispatch_required` still queues immediately: for a sign-in code the queueing
is the outcome. The reasoning and the deferred outbox are in
[ADR 0012](../decisions/0012-side-effects-after-commit.md).
