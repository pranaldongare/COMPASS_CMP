# Documentation map

Everything written about COMPASS CMP, and where to start depending on what
you need. Documents live in three places, deliberately:

| Where | What belongs there |
|---|---|
| `docs/` (this tree) | What crosses project boundaries: the system as a whole, the product behaviour it implements, how to run and operate it, and the decisions that shaped it |
| `cmp_backend/docs/` | The API's internals: layers, request lifecycle, the database, security mechanisms |
| Each project's `README.md` | How to run and work on that one project |

## Start here

**New to the codebase**

1. [Architecture - system overview](architecture/system-overview.md): the three deployables, the two datastores, and how a request travels
2. [Repository layout](architecture/repository-layout.md): where things live and what each directory owns
3. [Glossary](glossary.md): the vocabulary of the DPDP Act and of this platform
4. [Local development](operations/local-development.md): a working system on your machine in one sitting

**Working on a feature**

- [Domain model](architecture/domain-model.md): the tables, the state machines, and the invariants the database holds
- [Roles and access](domain/roles-and-access.md): the seven roles and what each may reach
- Behaviour, by obligation: [consent lifecycle](domain/consent-lifecycle.md), [collection and routing](domain/collection-and-routing.md), [rights requests](domain/rights-requests.md)
- [API](architecture/api.md): route families, the error contract, pagination, identifiers
- [Testing](operations/testing.md): what each suite proves and how to run it without fighting the rate limiter
- [Contributing](../CONTRIBUTING.md): the checks a change must pass and how commits are written

**Running it somewhere**

- [Deployment](operations/deployment.md): processes, containers, order of operations, what production refuses
- [Runbook](operations/runbook.md): restarts, rebuilding a development database, an audit chain that does not verify, rate-limit buckets

**Understanding why**

- [Decisions](decisions/README.md): the architecture decision records, one per choice that would otherwise be re-litigated
- [Reviews](reviews/2026-09-10-implementation-review.md): what an external review found, what was done about each finding, and why the suites had not caught it
- [Changelog](../CHANGELOG.md): what changed, by area and date

## The backend's own documents

| Document | Answers |
|---|---|
| [architecture/overview.md](../cmp_backend/docs/architecture/overview.md) | Why the API is layered the way it is, and why there is no ORM |
| [architecture/layers.md](../cmp_backend/docs/architecture/layers.md) | What each layer may and may not do |
| [architecture/dependency-rules.md](../cmp_backend/docs/architecture/dependency-rules.md) | The import graph and how it stays acyclic |
| [architecture/request-lifecycle.md](../cmp_backend/docs/architecture/request-lifecycle.md) | Middleware order, dependencies, the transaction boundary |
| [architecture/rights.md](../cmp_backend/docs/architecture/rights.md) | The rights module's design: clock, state machine, tickets, scope, nominations |
| [database/schema.md](../cmp_backend/docs/database/schema.md) | Table groups and the shapes that are not obvious |
| [database/migrations.md](../cmp_backend/docs/database/migrations.md) | The revision chain, and how to add one |
| [database/transactions.md](../cmp_backend/docs/database/transactions.md) | What must commit together, and the timeouts |
| [operations/configuration.md](../cmp_backend/docs/operations/configuration.md) | Settings, and what production refuses to start on |
| [operations/deployment.md](../cmp_backend/docs/operations/deployment.md) | The API's processes and health endpoints |
| [operations/monitoring.md](../cmp_backend/docs/operations/monitoring.md) | Logs, metrics, what to alert on |
| [security/authentication.md](../cmp_backend/docs/security/authentication.md) | Passwords, MFA, one-time codes, the two populations |
| [security/authorization.md](../cmp_backend/docs/security/authorization.md) | The matrix, scopes, 403 versus 404 |
| [security/sessions.md](../cmp_backend/docs/security/sessions.md) | Server-side sessions and the first-party proxy |
| [security/csrf.md](../cmp_backend/docs/security/csrf.md) | The double-submit defence |
| [security/rate-limiting.md](../cmp_backend/docs/security/rate-limiting.md) | The bounded surfaces and why the counters live in Redis |
| [security/audit.md](../cmp_backend/docs/security/audit.md) | The append-only, hash-chained trail |

## The projects' own documents

- [cmp_backend/README.md](../cmp_backend/README.md): the API
- [cmp_internal_ui/README.md](../cmp_internal_ui/README.md): the staff console
- [cmp_public_ui/README.md](../cmp_public_ui/README.md): the data-principal portal

## Historical documents

[docs/history/](history/README.md) keeps earlier design documents that no
longer describe the system: a generated low-level design from before the two
portals were split, a proposal for restructuring the backend, and a frontend
gap analysis whose gaps have since been closed. They are kept because they
explain how the code came to be shaped, and marked so nobody mistakes them for
the present.

## Keeping this current

A document that is wrong is worse than none: it is read with trust. So:

- A change to behaviour changes the document that describes it, in the same
  commit. The reviewer checks both.
- A choice that somebody could reasonably have made differently gets an ADR in
  [decisions/](decisions/README.md), written when the choice is made.
- Every user-visible change gets a line in the [changelog](../CHANGELOG.md).
- Counts (endpoints, tables, tests) are quoted sparingly and only where they
  carry meaning; where quoted, they are measured, not remembered.
- `cmp_backend/openapi.json` and each portal's `src/types/api-schema.d.ts`
  are generated from the running API. Regenerate them rather than editing.
