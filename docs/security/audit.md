# The audit trail

## What it guarantees

Every write to the platform records one entry, in the **same transaction** as the
change. A change that happened without an audit row is not a state the database
can reach.

## Append-only, four deep

1. No mutating route is registered on the resource.
2. The permission matrix grants no role write access.
3. `UPDATE` and `DELETE` are revoked from the application's database role
   (migration 0003).
4. A statement-level trigger refuses the statement (migration 0002).

Each layer alone would be a convention. Together they are a property.

## The hash chain

Each row carries a SHA-256 digest over its own canonical content **and its
predecessor's digest**.

Editing row N changes its digest, which no longer matches what N+1 recorded. So
verification does not answer "something changed" — it answers **"the trail is
sound up to exactly here"**, which is the answer somebody investigating actually
needs.

`GET /audit/verify` recomputes it. `cmp.maintenance.verify_audit_chain` runs it
daily, because a claim nobody checks is a claim nobody should believe.

Rows are chained in the order a transaction-level advisory lock is granted, and
since migration 0014 a row's `log_id` is drawn from the sequence *inside* that
lock rather than by a column default. The two orders are therefore one order,
which is what verification, walking by id, assumes. Before 0014, inserts
arriving together could carry ids in one order and predecessors in the other,
and verification reported a break that was not tampering. Rows written that way
stay as they are - the trail is append-only - and verification keeps naming the
first of them until the database is rebuilt.

## Reading it

The trail records `notice#42` — a table name and a surrogate key — because that
is the only reference guaranteed to stay valid. Codes get reused, projects get
renamed, people leave.

Precise, and unreadable. `db/repositories/entities.py` resolves the pair at read
time into a label, a public uuid and an in-app route: one query per entity type
on a page, never one per row. A row that no longer exists resolves to nothing
rather than an error — the trail outlives what it describes, and an evidence log
that fails to load because of one dangling reference is not a log.

A label that names a person comes in pieces. The name is a sealed column, and
ciphertext glued to plain text in SQL is a value nobody can open, so those
entity types (a consent record, a delegation, a nomination, a person-type
change, a request with a subject) return `entity_label_parts`: an array with
the name still sealed, which the console opens and joins. `entity_label` then
carries only the plain part, for a reader that ignores the parts.

## Asking it questions

`GET /audit` takes, and composes: `actor` and `actor_role`; `subject`; a
record as `entity_type` plus its public `entity` uuid (resolved to the id the
trail stores by `db/repositories/audit_lookup.py`; an unknown uuid matches
nothing, never everything); `event_type` or `event_group` (the part before
the dot); `from` and `to`; and `q`, a contains-match over the event type and
the recorded detail. `q` does not reach the names or addresses of actor and
subject: those columns are sealed, and a pattern matched against ciphertext
finds nothing. A person is found through `subject` or `actor`, chosen with the
lookup below. `q` is not indexed - the other filters are - so a large trail is
narrowed by date first.

`GET /audit/summary` counts the same rows by event, group, actor role and
day; `GET /audit/export.csv` downloads them (newest first, at most 10,000,
free-text cells neutralised against formulas) and records `audit.exported`
with the filters used; `GET /audit/lookup?kind=&q=` finds a person or a
record for the console's pickers; `GET /audit/vocabulary` serves
every entity type and event type with labels, so the console holds no list of
its own. All of it is the two supervising roles' to read, unscoped.

The lookup cannot match a sealed name or contact by pattern either
(`db/repositories/audit_lookup.py`). It finds a person by the whole email,
mobile or username typed, through its keyed hash; by uuid; or by three or more
characters of a name, through the hashed runs beside `full_name` and
`submitted_name`
([ADR 0017](../decisions/0017-lookup-by-keyed-hash-and-name-ngrams.md)). A
consent record is found by project name, uuid, or the person's whole contact;
a rights request by reference, contact or part of a name. The labels and hints
come back sealed and the console opens them.

## Denials are events too

`auth.access_denied` records a refused request with its cause (`detail.cause`,
the system's own sentence, never a person's words). An access-control
system that refuses correctly but silently tells an operator nothing about
somebody probing, or a role provisioned wrongly.

## What is not in it

Credentials, one-time codes, consent link tokens, and the contents of a data
asset. The trail says *what was done to which record by whom*, not what the
record contained.

And, since 21 September 2026, **nothing a person could ask to have erased**
([ADR 0015](../decisions/0015-nothing-erasable-in-a-trail-nobody-can-erase.md)).
The trail can never be edited, so anything personal written into it would
outlive every right its owner has to have it removed:

- **The client address is its blind index.** `detail.ip` is
  `HMAC-SHA256` of the address under `BLIND_INDEX_KEY`
  (`domain/audit/service.py`), not the address. It answers "was this the same
  address as that" and "did this known address appear", and nothing else.
- **A person is an id.** `subject_user_id` and `actor_user_id` name them;
  `user.invited` and `user.created` no longer carry the email, and a ticket's
  reassignment records respondent and account ids, not contacts.
- **A reason is `reason_given: true`.** The words stay in their own sealed
  row (`rights_request.refusal_reason`, `project_status_history.reason`,
  `delegation.reason` and the rest); the reader who needs them follows the
  entity there.

Rows written before that date still hold raw addresses, 2,261 of them, and an
email on eleven. They cannot be rewritten, and are not.

To ask whether a known address appears, compute its index under the
production `BLIND_INDEX_KEY` with the application's own `index_of("ip", …)`
and search `q` for it. There is no endpoint or script for this; it needs the
key, and so an operator with access to the API's environment.
