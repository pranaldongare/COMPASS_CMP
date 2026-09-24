# System overview

COMPASS CMP is a consent management platform built to India's **Digital
Personal Data Protection Act 2023** and the DPDP Rules 2025. A data fiduciary
registers the projects it collects personal data for, states their purposes,
publishes notices, collects consent purpose by purpose at named sites, records
every disclosure, and answers a data principal's rights requests inside a
published period. Everything it does is arranged so that it can be proved,
years later, to somebody who was not there.

## The pieces

```mermaid
flowchart LR
  subgraph People
    S[Data principal<br/>browser or phone]
    T[Staff<br/>DPO, owners, admin]
  end
  subgraph Portals
    P[frontend/portal<br/>Next.js, port 3001]
    C[frontend/console<br/>Next.js, port 3000]
  end
  subgraph Backend
    A[backend/api API<br/>FastAPI, port 8000]
    W[Celery worker]
    B[Celery beat]
    K[backend/dkms key service<br/>FastAPI, port 32688]
  end
  subgraph Stores
    PG[(PostgreSQL 16)]
    R[(Redis 7)]
    F[(File storage)]
  end
  S --> P
  T --> C
  P -- "/api proxied, first-party cookie" --> A
  C -- "/api proxied, first-party cookie" --> A
  A --> PG
  A --> R
  A --> F
  A -- "seal on write" --> K
  W -- "open a recipient" --> K
  P -- "open, server side" --> K
  C -- "open, server side" --> K
  A -- "queue" --> R
  R -- "tasks" --> W
  B -- "schedule" --> R
  W --> PG
  W --> F
  W -- "email / SMS" --> S
  W -- "email" --> T
```

| Component | Directory | Runs as | Talks to |
|---|---|---|---|
| API | `backend/api/` | `python -m cmp` in a virtualenv | PostgreSQL, Redis, file storage, the key service |
| Worker | `backend/api/` | `celery worker` on six queues | PostgreSQL, Redis, the key service, the email and SMS transports |
| Beat | `backend/api/` | `celery beat`, exactly one instance | Redis |
| Key service | `backend/dkms/` | `python3 -m app.main` in its own virtualenv, port 32688 | nothing; it is called |
| Staff console | `frontend/console/` | Next.js on port 3000 | the API, through its own `/api` proxy; the key service, from its server |
| Data-principal portal | `frontend/portal/` | Next.js on port 3001 | the API, through its own `/api` proxy; the key service, from its server |
| PostgreSQL | native, or `dev-services.yml` | 32 tables, 39 enums, 27 triggers, one view | |
| Redis | native, or `dev-services.yml` | three logical databases: sessions and limits, broker, results | |

## Two audiences, two portals

Staff and data principals never share a screen. The **staff console** holds
the registers, the project and notice workflows, the collection model, the
disclosure register, the DPO's rights queue and the audit trail. The
**data-principal portal** holds the public consent flow reached from a consent
link, self-registration and one-time-code sign-in, the public rights pages, and
her own records: consents, disclosures, requests, nominations. Each portal
points the wrong kind of account at the other. The split is a deployment
boundary as much as a design one: nothing a member of staff uses ships to the
public origin.

There are four services: the API (with its worker and beat), the key service,
and the two portals.

Both portals proxy `/api/*` to the API from `next.config.ts`. The session
cookie is `HttpOnly` and `SameSite=Lax`, and a browser on one origin calling an
API on another silently drops it. The proxy keeps every call first-party, which
is why `NEXT_PUBLIC_API_URL` stays unset in local development.

## How a request travels

1. The browser calls `/api/...` on its own origin; Next.js forwards it to the API.
2. Middleware: trusted host, CORS, gzip, then the request id (first, so every
   later line can be correlated), security headers, the body limit, the access
   log with the consent token scrubbed.
3. Dependencies resolve the session from the cookie, check the CSRF header on
   unsafe verbs, resolve the principal, and consult the permission matrix.
4. The router opens one transaction and calls one domain service. The service
   applies the rules, writes, and records the audit row in the same
   transaction.
5. The repository runs hand-written SQL in which the caller's scope is part of
   the `WHERE` clause, so a row outside scope is never selected. A write of a
   personal column is **sealed** first: the repository hands the row to
   `seal()`, which makes one call to the key service for all of its personal
   columns. A lookup by a sealed value - an email at sign-in, a contact on the
   public rights form - compares its keyed hash in the `*_hash` column beside
   it; a search by part of a name compares hashed three-character runs in the
   `*_ngrams` column. Every function
   that returns a row of some entity returns the same shape, whether it read,
   inserted or updated it: a write whose `RETURNING` cannot reach what the
   response needs reads the row back rather than handing back the statement,
   because a shape that depends on which function produced it fails response
   validation in one route and not its neighbour.
6. PostgreSQL holds the invariants: CHECK constraints, append-only triggers,
   the notice freeze, the audit hash chain, and a revoked `UPDATE` grant on
   evidence tables.
7. The response goes back with each personal field as it is stored: sealed,
   a string starting `SE::`. The API does not open it.
8. The portal's API client sees sealed values in the response and sends them,
   in one batch, to its own server route `/dkms/decrypt`. That route checks for
   a session and calls `${DKMS_URL}/bulk_decrypt`; the page receives
   plaintext. The browser never learns where the key service is.

The key service, [`backend/dkms`](../../backend/dkms/README.md), holds the key
that personal fields are encrypted under. It is a separate process from the
API because the API holds the database, and a single compromise should not be
both. The API seals through it; each portal opens through its own server side,
so no browser ever holds a key; the worker opens a recipient's contact at the
moment a message is sent. The keyed hashes are computed by the API itself,
under `BLIND_INDEX_KEY`, so sign-in does not stop when the key service does.
Everything about it is under [docs/dkms/](../dkms/README.md); the choice is
[ADR 0016](../decisions/0016-personal-data-sealed-by-a-separate-key-service.md),
and lookups by hash are
[ADR 0017](../decisions/0017-lookup-by-keyed-hash-and-name-ngrams.md).

Side effects that a person is not waiting for - a code, an acknowledgement, a
ticket, a report - are queued to Celery and delivered by the worker. Codes go
on `high_priority`, so a sign-in never waits behind an export.

The detail is in
[request-lifecycle.md](../architecture/request-lifecycle.md).

## The four workflows

| Workflow | Starts with | Ends with | Document |
|---|---|---|---|
| Collection set-up | An R&D user registers a project and names its purposes and collectors | A DPO approves it; a collection owner registers sites and mints consent links | [collection-and-routing.md](../domain/collection-and-routing.md) |
| Consent | A data principal opens a consent link | A consent artefact per purpose, superseded only by a later withdrawal | [consent-lifecycle.md](../domain/consent-lifecycle.md) |
| Exchange | A collection owner exports a file or imports a manifest | A disclosure record naming every person in the file; assets reconciled to consents | [collection-and-routing.md](../domain/collection-and-routing.md#exports-imports-and-assets) |
| Rights | A data principal, a stranger on the public form, or a nominee asks | A response released inside the published period, with every holder's ticket returned or escalated | [rights-requests.md](../domain/rights-requests.md) |

## What is enforced where

| Kind of rule | Example | Held by |
|---|---|---|
| Shape | a mobile number, a uuid, a bounded string | Pydantic models, from `cmp.validation` |
| Rule | may this project move to that state; may this role do this | the domain services and the permission matrix |
| Invariant | a published notice cannot change; an audit row cannot be edited; a consent artefact carries the hash of the text served | PostgreSQL triggers and constraints |

The third layer is the one that survives a bug, a migration and a `psql`
session. See [ADR 0002](../decisions/0002-evidence-enforced-in-the-database.md).

## Environments

| Environment | Set by | Differences |
|---|---|---|
| `local` | default | Email and SMS are written to `backend/api/var/outbox.log`; `/docs` is served; cookies need not be `Secure` |
| `test` | the test suites | As local, with the outbox |
| `production` | `ENVIRONMENT=production` | The API refuses to start on the development secret key, a default database password, insecure cookies, `DEBUG`, a wildcard CORS origin, an email transport other than `smtp` or an SMS transport other than `http`, `DKMS_ENABLED` off, or a development or short `BLIND_INDEX_KEY`. The key service refuses the development `DKMS_MASTER_KEY` or `DKMS_HASH_KEY`. `/docs` and `/openapi.json` are not served |

## Ports and URLs, locally

| What | URL |
|---|---|
| API | http://127.0.0.1:8000, interactive docs at `/docs` |
| Staff console | http://localhost:3000 |
| Data-principal portal | http://localhost:3001 |
| Key service | http://127.0.0.1:32688, `GET /health` |
| PostgreSQL | 127.0.0.1:5432, database `cmp` |
| Redis | 127.0.0.1:6379 |

The backend's `PUBLIC_BASE_URL` must name the portal and `CONSOLE_BASE_URL`
the console: every link the platform puts in a message is built from them.
The API's `DKMS_URL` and each portal's server-only `DKMS_URL` must name the
same key service: a value sealed under one key opens under no other.

`GET /ready` on the API answers 503 when PostgreSQL, Redis, the schema
revision or the key service is not as it should be.
