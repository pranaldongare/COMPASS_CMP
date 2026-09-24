# Architecture decision records

One file per decision that shaped the platform and would be expensive to
reverse. Each record says what was decided, why, what it costs, and what
would make us revisit it. Newer records may supersede older ones; the older
one stays and points forward.

| # | Decision | Status |
|---|---|---|
| [0001](0001-no-orm-raw-sql.md) | No ORM: hand-written SQL over psycopg 3 and raw-SQL migrations | accepted; amended 2026-09-22 |
| [0002](0002-evidence-enforced-in-the-database.md) | Evidence is enforced by the database, not the application | accepted; amended 2026-09-21 |
| [0003](0003-server-side-sessions-and-first-party-proxy.md) | Server-side sessions in Redis, reached through a first-party proxy | accepted |
| [0004](0004-scope-in-the-where-clause.md) | Scope is compiled into the query; out of scope is 404, not 403 | accepted |
| [0005](0005-audit-chain-position-inside-the-lock.md) | The audit chain position is drawn inside the advisory lock | accepted; amended 2026-09-21 |
| [0006](0006-mfa-for-every-staff-role.md) | An emailed second factor for every staff role | accepted |
| [0007](0007-mobile-first-contacts.md) | Mobile required, email optional, for data principals and nominees | accepted; amended 2026-09-21 |
| [0008](0008-unknown-choices-are-422.md) | An unknown enumerated value is a 422 with the choices named | accepted |
| [0009](0009-two-portals-by-audience.md) | Two portals, split by audience, one API | accepted |
| [0010](0010-rights-clock-and-defaults.md) | The rights clock starts at receipt, and the open questions have defaults | accepted |
| [0011](0011-server-held-notice-serving.md) | The serving of a notice is the server's record, not the client's claim | accepted |
| [0012](0012-side-effects-after-commit.md) | Side effects wait for the commit; a durable outbox is deferred | accepted; amended 2026-09-22 |
| [0013](0013-every-account-is-a-data-principal.md) | Every account is a data principal; staff is a role the session acts with, and a code sign-in is worth exactly that | accepted; amended 2026-09-21 |
| [0014](0014-a-nominee-follows-the-request-they-raised.md) | A nominee follows the request they raised, and reading is not acting | accepted |
| [0015](0015-nothing-erasable-in-a-trail-nobody-can-erase.md) | Nothing erasable goes into a trail nobody can erase | accepted |
| [0016](0016-personal-data-sealed-by-a-separate-key-service.md) | Personal data is sealed by a separate key service, and opened only where a person reads it | accepted |
| [0017](0017-lookup-by-keyed-hash-and-name-ngrams.md) | Sealed values are found by keyed hash, and names by hashed runs | accepted |
| [0018](0018-pip-and-a-virtualenv-no-containers.md) | pip and a virtualenv; nothing ships as a container | accepted |
| [0019](0019-erasure-reaches-every-store-but-the-record.md) | Erasure reaches every store that holds an item, and never the record of what happened | accepted |

## Writing one

Copy the shape of any record here: **Context**, **Decision**,
**Consequences**, **Revisit when**. Number it next in sequence, add a row
above, and link it from the page whose behaviour it explains. A decision that
is reversed gets a new record marking the old one superseded; do not edit
history. A decision that still stands but is narrowed by a later one keeps its
text and gains a dated **Amended** section at the end, saying what changed and
pointing to the record or commit that changed it, with a pointer on its
Status line.
