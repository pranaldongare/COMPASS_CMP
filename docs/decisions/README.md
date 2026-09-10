# Architecture decision records

One file per decision that shaped the platform and would be expensive to
reverse. Each record says what was decided, why, what it costs, and what
would make us revisit it. Newer records may supersede older ones; the older
one stays and points forward.

| # | Decision | Status |
|---|---|---|
| [0001](0001-no-orm-raw-sql.md) | No ORM: hand-written SQL over psycopg 3 and raw-SQL migrations | accepted |
| [0002](0002-evidence-enforced-in-the-database.md) | Evidence is enforced by the database, not the application | accepted |
| [0003](0003-server-side-sessions-and-first-party-proxy.md) | Server-side sessions in Redis, reached through a first-party proxy | accepted |
| [0004](0004-scope-in-the-where-clause.md) | Scope is compiled into the query; out of scope is 404, not 403 | accepted |
| [0005](0005-audit-chain-position-inside-the-lock.md) | The audit chain position is drawn inside the advisory lock | accepted |
| [0006](0006-mfa-for-every-staff-role.md) | An emailed second factor for every staff role | accepted |
| [0007](0007-mobile-first-contacts.md) | Mobile required, email optional, for data principals and nominees | accepted |
| [0008](0008-unknown-choices-are-422.md) | An unknown enumerated value is a 422 with the choices named | accepted |
| [0009](0009-two-portals-by-audience.md) | Two portals, split by audience, one API | accepted |
| [0010](0010-rights-clock-and-defaults.md) | The rights clock starts at receipt, and the open questions have defaults | accepted |

## Writing one

Copy the shape of any record here: **Context**, **Decision**,
**Consequences**, **Revisit when**. Number it next in sequence, add a row
above, and link it from the page whose behaviour it explains. A decision that
is reversed gets a new record marking the old one superseded; do not edit
history.
