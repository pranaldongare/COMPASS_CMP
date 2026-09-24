# Documentation map

Everything written about COMPASS CMP, and where to start depending on what
you need. **Every document is in this tree.** The one exception is a
`README.md` per service, which holds a single thing: how to run that service.

## Start here

**New to the codebase**

1. [Architecture - system overview](architecture/system-overview.md): the four services - the API with its worker, the key service, the two portals - the two datastores, and how a request travels, sealed on the way in and opened in the portal
2. [Repository layout](architecture/repository-layout.md): where things live and what each directory owns —
   and [the restructuring proposal](architecture/proposed-repository-structure.md), carried out in its first two phases and its fifth; the shared frontend package it argues for is still open
3. [Glossary](glossary.md): the vocabulary of the DPDP Act and of this platform
4. [Local development](operations/local-development.md): a working system on your machine in one sitting

**Working on a feature**

- [Domain model](architecture/domain-model.md): the tables, the state machines, and the invariants the database holds
- [Roles and access](domain/roles-and-access.md): the seven roles and what each may reach
- Behaviour, by obligation: [consent lifecycle](domain/consent-lifecycle.md), [collection and routing](domain/collection-and-routing.md), [rights requests](domain/rights-requests.md), [messages the platform sends](domain/messages.md), [reading the audit trail](domain/audit-trail.md)
- [Personal data](domain/personal-data.md): every table, store and endpoint that holds or moves something about a person, and what protects it
- [PII fields and endpoints](domain/pii-fields-and-endpoints.md): the short form — the 54 personal columns by table, and every endpoint that carries one, by module
- [DKMS — encryption of personal data](dkms/README.md): the documents on the key service — the sealed fields table by table, the backend, the frontend layer that decrypts, and the implementation plan — and [adding a personal field](dkms/adding-a-personal-field.md), the steps a new sealed column takes
- [API](architecture/api.md): route families, the error contract, pagination, identifiers
- [Frontend](frontend/README.md): what is written about the two portals beyond how to run them. Chiefly [best practices](frontend/best-practices.md): the React and Next.js standard — each rule, how the portals meet it and where, what is deliberately different, and the decision matrix a pull request answers
- [Testing](operations/testing.md): what each suite proves and how to run it without fighting the rate limiter
- [Contributing](../CONTRIBUTING.md): the checks a change must pass and how commits are written

**Running it somewhere**

- [Local development](operations/local-development.md) is also how it runs anywhere: a virtualenv per Python service, `npm run dev` per portal, PostgreSQL and Redis beside them. Why there are no containers is [ADR 0018](decisions/0018-pip-and-a-virtualenv-no-containers.md); how it was once meant to be containerised is in [history/](history/README.md)
- [Runbook](operations/runbook.md): restarts, rebuilding a development database, an audit chain that does not verify, rate-limit buckets

**Understanding why**

- [Decisions](decisions/README.md): the architecture decision records, one per choice that would otherwise be re-litigated. The latest: [0016](decisions/0016-personal-data-sealed-by-a-separate-key-service.md), personal data sealed by a separate key service; [0017](decisions/0017-lookup-by-keyed-hash-and-name-ngrams.md), lookup by keyed hash and name n-grams; [0018](decisions/0018-pip-and-a-virtualenv-no-containers.md), pip and a virtualenv, no containers; [0019](decisions/0019-erasure-reaches-every-store-but-the-record.md), erasure reaches every store that holds an item, and never the record of what happened; [0020](decisions/0020-cross-border-transfer-checked-at-export.md), a transfer is checked at export, and an unknown place is refused
- [Reviews](reviews/2026-09-10-implementation-review.md): what an external review found, what was done about each finding, and why the suites had not caught it
- [DPDP Act gap assessment](reviews/2026-09-17-dpdp-act-gap-assessment.md): statutory requirement map, implemented capabilities, prioritised gaps and remediation sequence
- [Personal data inventory](domain/personal-data.md): what the platform holds about people, where, and which of the 253 operations touch it
- [Changelog](../CHANGELOG.md): what changed, by area and date

## Reference

Under [reference/](reference/). Two are produced from the code and regenerated
when it changes; the third is reviewed by hand against it:

- [reference/api/](reference/api/README.md): every operation by module, with
  validation, payload and response, and one page per role listing what it may
  reach — regenerate with `python3 docs/tools/generate-api-docs.py`
- [reference/database/](reference/database/README.md): the schema drawn, every
  table with its columns and constraints, every enumeration — generated from
  PostgreSQL's catalogues of a scratch database replayed from the migration
  chain: `POSTGRES_DB=cmp_ref alembic upgrade head`, then
  `python3 docs/tools/generate-schema-docs.py --database cmp_ref`
- [reference/access-control/](reference/access-control/README.md): which role
  may call each endpoint, on which rows, under what conditions, with the guard
  and the source line as evidence; hand-reviewed, amended when a route changes

## Tools

[tools/](tools/) holds what regenerates and checks this tree:

- `generate-api-docs.py`: reference/api/, from `backend/api/openapi.json`
- `generate-schema-docs.py`: reference/database/, from a database's
  catalogues (`--database cmp_ref`)
- `pii-fields-and-endpoints.py`: the tables in
  [pii-fields-and-endpoints.md](domain/pii-fields-and-endpoints.md)
- `personal-data-scan.py`: the endpoint tables in
  [personal-data.md](domain/personal-data.md), joined from the OpenAPI
  document, the access-control reference and the schema inventory; `--check`
  exits non-zero on a field that looks personal and is not classified
- `check-links.py`: asserts that every relative link in every document resolves
- [ci-paths.md](tools/ci-paths.md) and `ci.yml.proposed`: the changes
  `.github/workflows/ci.yml` still needs after the restructure, and the
  workflow with them made, not yet applied

## The API's internals

| Document | Answers |
|---|---|
| [architecture/api-internals.md](architecture/api-internals.md) | Why the API is layered the way it is, and why there is no ORM |
| [architecture/layers.md](architecture/layers.md) | What each layer may and may not do |
| [architecture/dependency-rules.md](architecture/dependency-rules.md) | The import graph and how it stays acyclic |
| [architecture/request-lifecycle.md](architecture/request-lifecycle.md) | Middleware order, dependencies, the transaction boundary |
| [architecture/rights-module.md](architecture/rights-module.md) | The rights module's design: clock, state machine, tickets, scope, nominations |
| [database/schema.md](database/schema.md) | Table groups and the shapes that are not obvious |
| [database/migrations.md](database/migrations.md) | The revision chain, and how to add one |
| [database/transactions.md](database/transactions.md) | What must commit together, and the timeouts |
| [operations/configuration.md](operations/configuration.md) | Settings, and what production refuses to start on |
| [operations/monitoring.md](operations/monitoring.md) | Logs, metrics, what to alert on |
| [security/authentication.md](security/authentication.md) | Passwords, MFA, one-time codes, the two populations |
| [security/authorization.md](security/authorization.md) | The matrix, scopes, 403 versus 404 |
| [security/sessions.md](security/sessions.md) | Server-side sessions and the first-party proxy |
| [security/csrf.md](security/csrf.md) | The double-submit defence |
| [security/rate-limiting.md](security/rate-limiting.md) | The bounded surfaces and why the counters live in Redis |
| [security/audit.md](security/audit.md) | The append-only, hash-chained trail |
| [security/encryption-at-rest.md](security/encryption-at-rest.md) | Personal fields sealed by the key service, opened only in the portals' server, found by keyed hash |

## The services' own documents

- [backend/api/README.md](../backend/api/README.md): the platform API
- [backend/dkms/README.md](../backend/dkms/README.md): the key service
- [frontend/console/README.md](../frontend/console/README.md): the staff console
- [frontend/portal/README.md](../frontend/portal/README.md): the data-principal portal

## Historical documents

[docs/history/](history/README.md) keeps earlier design documents that no
longer describe the system: a generated low-level design from before the two
portals were split, a proposal for restructuring the backend, two documents on
deploying the platform as containers, the runbook the repository was
restructured by, and a frontend gap analysis whose gaps have since been
closed. They are kept because they
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
- `backend/api/openapi.json` and each portal's `src/types/api-schema.d.ts`
  are generated from the running API. Regenerate them rather than editing.
