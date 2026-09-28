# Backend developer guide

Everything a developer needs to work on the API, in one place and in reading
order: how the code is laid out, how a request travels through it, how each
security control works, how tables are made and used, and how to add a
feature from the table up. It is written from the code as it stands - paths,
function names and the reasons the code gives in its own comments - and it
links to the reference pages elsewhere in `docs/` for depth.

Read it in order the first time. Afterwards, each page stands alone.

| # | Page | What you will know afterwards |
|---|---|---|
| 1 | [Codebase tour](01-codebase-tour.md) | What each package under `backend/api/src/cmp` does, and which may import which |
| 2 | [How a request works](02-how-a-request-works.md) | Startup, the middleware in the order a request meets it, one staff write and one public consent traced hop by hop, the error contract, pagination, background tasks |
| 3 | [Security, end to end](03-security.md) | Both sign-in paths, sessions, CSRF, the permission matrix and scopes, rate limits, encryption of personal data, the audit chain, capability tokens, headers, secrets, logging |
| 4 | [The database](04-database.md) | Where the schema lives, how a migration is written, the conventions every table follows, what the database itself refuses, sealed columns, the pool and transactions, repositories |
| 5 | [Adding a feature](05-adding-a-feature.md) | The steps and commands, from a new table to a tested, documented endpoint |
| 6 | [Known gaps](06-known-gaps.md) | Where the code today departs from the rules the rest of the docs state, so you are not surprised |

## The whole thing on one page

```
 browser ── console :3000 / portal :3001 (Next.js)
               │  same-origin /api/* rewrite; cookies stay first-party
               ▼
 API :8000 (FastAPI, backend/api)
   middleware ─ request id · security headers · body limit · access log · gzip · CORS
   router     ─ api/routers/v1/*.py, api/routers/public/*.py
                 dependencies: session from cookie → CSRF on writes → principal → role/matrix guard
   transaction() ─ one database transaction per write, opened by the router
   service    ─ domain/<area>/service.py: the rules, the writes, the audit row
   repository ─ db/repositories/*.py: hand-written SQL, scope in the WHERE clause,
                personal fields sealed by the key service before they are written
               │                         │                          │
               ▼                         ▼                          ▼
        PostgreSQL (cmp)        key service :32688          Redis /0 sessions, limits, codes
        triggers enforce        (backend/dkms) seals and    Redis /1 Celery broker ─► worker
        append-only, freezes    opens personal fields                 sends mail/SMS
```

Three ideas carry most of the design, and you will meet each of them on every
page:

1. **The database is the last line.** Evidence tables are append-only by
   trigger, a published notice is frozen by trigger, and the audit trail is
   hash-chained by trigger. Code that tries to break a rule gets an error
   from PostgreSQL, not a quiet success.
2. **Personal data is sealed at rest and served sealed.** A name, an email or
   a mobile is encrypted by the key service before it reaches a table, found
   again through a keyed hash, and sent to the browser still sealed; the
   portals open it in their own server for the page that shows it.
3. **Scope is a WHERE clause.** Who may see a row is decided in the SQL that
   fetches it, so a row outside your scope is a 404, never a 403 that would
   confirm it exists.

## Before you start

- A working local system: [local development](../operations/local-development.md).
- The vocabulary: [glossary](../glossary.md).
- Demo data to click through: `python scripts/seed.py` then
  `python scripts/seed_demo.py` in `backend/api`.
- How the checks are run: [testing](../operations/testing.md) and
  [CONTRIBUTING](../../CONTRIBUTING.md).
