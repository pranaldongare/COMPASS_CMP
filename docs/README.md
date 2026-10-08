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
5. [Backend developer guide](backend/README.md): the API end to end, in reading order - the code layout, how a request travels, every security control, how tables are made and used, adding a feature from table to endpoint, and where the code departs from the rules today

**Working on a feature**

- [Domain model](architecture/domain-model.md): the tables, the state machines, and the invariants the database holds
- [Roles and access](domain/roles-and-access.md): the eight roles and what each may reach
- Behaviour, by obligation: [consent lifecycle](domain/consent-lifecycle.md), [collection and routing](domain/collection-and-routing.md), [rights requests](domain/rights-requests.md) (and [the ticket redesign](domain/rights-tickets-redesign.md) of 2026-10-08: the guided path, the review step, holders outside the console), [personal data breaches](domain/breaches.md), [messages the platform sends](domain/messages.md), [reading the audit trail](domain/audit-trail.md)
- [Personal data](domain/personal-data.md): every table, store and endpoint that holds or moves something about a person, and what protects it
- [PII fields and endpoints](domain/pii-fields-and-endpoints.md): the short form — the 108 personal columns by table, and every endpoint that carries one, by module
- [Notification management strategy](notifications/README.md): every module's emails end to end - when, to, CC, attachment, subject and body - in one file per module (users, projects, consent, rights, breach), the rules for copies and files, and the plan of 2026-10-08
- [Email](email/README.md): how every email goes out - the one path, the SMTP settings (STARTTLS, SSL or a plain relay), which failures are retried, testing a server with `scripts/send_test_email.py` - and [every message the platform sends](email/messages.md), generated from the code with the task and line that sends each
- [DKMS — encryption of personal data](dkms/README.md): the documents on the key service — the sealed fields table by table, the backend, the frontend layer that decrypts, and the implementation plan — and [adding a personal field](dkms/adding-a-personal-field.md), the steps a new sealed column takes
- [API](architecture/api.md): route families, the error contract, pagination, identifiers
- [Frontend](frontend/README.md): what is written about the two portals beyond how to run them. Chiefly [best practices](frontend/best-practices.md): the React and Next.js standard — each rule, how the portals meet it and where, what is deliberately different, and the decision matrix a pull request answers
- [Testing](operations/testing.md): what each suite proves and how to run it without fighting the rate limiter
- [User acceptance testing](uat/): the cycle's runbook and 156 step-by-step test cases in seven areas, breach included (Word), and the workbook testers record results and defects in (Excel), for the build at `833b58f` (pack v1.6, 8 October 2026)
- [Contributing](../CONTRIBUTING.md): the checks a change must pass and how commits are written

**Running it somewhere**

- [Local development](operations/local-development.md) is also how it runs anywhere: a virtualenv per Python service, `npm run dev` per portal, PostgreSQL and Redis beside them. Why there are no containers is [ADR 0018](decisions/0018-pip-and-a-virtualenv-no-containers.md); how it was once meant to be containerised is in [history/](history/README.md)
- [Runbook](operations/runbook.md): restarts, rebuilding a development database, an audit chain that does not verify, rate-limit buckets

**Understanding why**

- [Decisions](decisions/README.md): the architecture decision records, one per choice that would otherwise be re-litigated. The latest: [0016](decisions/0016-personal-data-sealed-by-a-separate-key-service.md), personal data sealed by a separate key service; [0017](decisions/0017-lookup-by-keyed-hash-and-name-ngrams.md), lookup by keyed hash and name n-grams; [0018](decisions/0018-pip-and-a-virtualenv-no-containers.md), pip and a virtualenv, no containers; [0019](decisions/0019-erasure-reaches-every-store-but-the-record.md), erasure reaches every store that holds an item, and never the record of what happened; [0020](decisions/0020-cross-border-transfer-checked-at-export.md), a transfer is checked at export, and an unknown place is refused; [0021](decisions/0021-a-breach-is-recorded-and-its-duties-tracked-never-submitted.md), a breach is recorded and its duties tracked, and the platform never submits to a regulator; [0022](decisions/0022-an-incident-first-and-a-breach-on-a-yes.md), an incident is logged first, a breach is recorded on a yes, and the organisation's board is told within 30 minutes; [0023](decisions/0023-breach-tickets-and-breach-only-logins.md), breach tickets reach internal staff only, through temporary logins that end with the breach; [0024](decisions/0024-a-rights-tickets-holder-is-reached-three-ways.md), a rights ticket's holder is reached three ways, and an outside holder answers by a link and a code; [0025](decisions/0025-a-holders-answer-counts-once-accepted-and-the-server-owns-the-moves.md), an answer counts once the Privacy Office accepts it; [0026](decisions/0026-a-rights-request-is-access-erasure-or-a-grievance-about-everything.md), a rights request is access, erasure or a grievance, about everything; [0027](decisions/0027-a-breach-can-reach-people-with-no-account.md), a breach can reach people with no account; [0028](decisions/0028-a-notice-template-is-copied-never-served.md), a notice template is copied, never served; [0029](decisions/0029-copies-and-files-never-on-a-code-a-link-or-her-own-record.md), copies and files never on a code, a link or her own record
- [Reviews, and what became of them](reviews/README.md): every review, the status of each finding, the parked backlog items the documents cite, and the decisions still open with their owners. The reviews themselves: the [implementation review](reviews/2026-09-10-implementation-review.md) of 2026-09-10 and the [frontend architecture review](reviews/2026-10-01-frontend-architecture-review.md) of 2026-10-01
- [DPDP Act gap assessment](reviews/2026-09-17-dpdp-act-gap-assessment.md): statutory requirement map, implemented capabilities, prioritised gaps and remediation sequence
- [Personal data inventory](domain/personal-data.md): what the platform holds about people, where, and which of the 325 operations touch it (229 do)
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
- `generate-email-docs.py`: the five [notifications/](notifications/README.md)
  module files and [email/messages.md](email/messages.md), from
  `core/messages.py` and the tasks that send each email; `--check` fails when
  one is stale
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
