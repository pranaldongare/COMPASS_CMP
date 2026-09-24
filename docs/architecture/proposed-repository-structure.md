# A proposed repository structure

**Status: partly carried out.** Phase 1 (the four services under `backend/`
and `frontend/`) landed in `89b1e8e`, phase 2 (every document under `docs/`)
in `209e1da`, and phase 5 (one Python toolchain: `pip` and a virtualenv for
both services, no containers) in `879bfc1`. Phases 3 and 4 - the
`frontend/shared` package and the reconciling of near-duplicates - are still
open, and this document is still the proposal for them. The body below is
left as it was argued: its "today, measured" tree and its paths describe the
repository before phase 1. The current tree is
[repository-layout.md](repository-layout.md), and the commands phases 1, 2
and 5 followed are in
[history/restructure-runbook.md](../history/restructure-runbook.md).

**The shape you asked for:** three layers at the root and nothing else.
Everything the server does under one folder, everything the browser does under
another, and **every document in the repository under `docs/`** — including the
three reference trees and the backend's own seventeen internal documents, which
today sit in two other places.

```
compass/
├── backend/      every server-side thing: the API, the worker, the key service
├── frontend/     every browser-side thing: both portals and the code they share
├── docs/         every document, generated or written
└── .github/  README.md  CONTRIBUTING.md  CHANGELOG.md  .gitignore
```

Four entries. A person opening this repository for the first time can say what
the system is before scrolling.

## What is there today, measured

```
COMPASS_CMP/                      921 tracked files
  cmp_backend/          319       API + worker + migrations   36,101 lines src, 13,818 tests
  cmp_internal_ui/      285       staff console, port 3000
  cmp_public_ui/        173       data-principal portal, port 3001
  cmp_dkms/              22       key service, port 32688     (added this week)
  docs/                  39       cross-cutting documentation
  api_docs/              27       generated from openapi.json
  database_schema/       26       generated from the database
  api_access_control/    23       hand-reviewed permission reference
  .github/                1       CI
  .baseline_routes.txt    4 lines, unexplained
  README · CONTRIBUTING · CHANGELOG
```

Eight top-level directories, of which four are deployables, three are
documentation wearing a project's clothes, and one is CI. Plus a stray file.

## What actually hurts

Four things, each with the evidence rather than an opinion.

**1. The two portals are one application wearing two coats.**

| Measure | Count |
|---|---|
| Files in `cmp_internal_ui/src` | 232 |
| Files at the same path in `cmp_public_ui/src` | 102 |
| **Byte-for-byte identical** | **65** |

`proxy.ts`, the entire `providers/` stack, `schemas/`, `test/`, the generated
`api-schema.d.ts`, `components/ui/primitives.tsx`, `components/ui/charts.tsx` —
identical files, maintained by copying. The remaining 37 shared paths are
near-duplicates: `lib/config/index.ts`, `app-shell.tsx`, `auth-provider.tsx`,
diverged by a few lines each, and it is no longer obvious which of those
differences are deliberate.

Not theoretical: adding the DKMS layer this week meant writing five files and
then copying them across. A bug fixed in one portal's toast provider is still
live in the other, and nothing tells you.

**2. Documentation lives in three places.** `docs/` (39 files),
`cmp_backend/docs/` (17 files), and three root directories that are references
rather than projects (76 files). `docs/README.md` currently spends two whole
sections explaining where the other documentation is — a signpost compensating
for a layout.

**3. Four deployables, four naming conventions.** `cmp_backend` names a tier.
`cmp_internal_ui` and `cmp_public_ui` name an audience. `cmp_dkms` names a
product. The `cmp_` prefix repeats the name of the repository it is inside.

**4. Two Python toolchains, chosen by accident.** `cmp_backend` uses `uv` with
a lockfile; `cmp_dkms` uses `venv` + `pip` + `requirements.txt`. Both are
defensible; having both, undocumented, is not.

---

# The complete tree, for approval

Every directory that exists today, placed where it would go. Nothing is
invented: each line is a folder that exists now, or holds files that exist now,
or is marked **new**.

The right-hand column is the decision. `moved` is a `git mv` and nothing else.
`shared` means files currently duplicated in both portals that would live in one
place. **new** means a file that would have to be written.

## `backend/` — everything the server does

```
compass/
│
├── backend/
│   │
│   ├── api/                                    ← cmp_backend/            moved
│   │   ├── src/cmp/
│   │   │   ├── main.py  __main__.py
│   │   │   ├── bootstrap/                      factory, lifespan, container
│   │   │   ├── api/
│   │   │   │   ├── routers/v1/                 audit, auth, consents, dashboard,
│   │   │   │   │                               delegations, exchange, me, messages,
│   │   │   │   │                               notices, projects, registry, rights,
│   │   │   │   │                               system, users
│   │   │   │   ├── routers/public/             consent (/c/{token}), rights
│   │   │   │   ├── dependencies/               sessions, csrf, authz, paging, filters
│   │   │   │   ├── middleware/                 context, headers, body limit, access log
│   │   │   │   └── errors/                     one error contract
│   │   │   ├── auth/
│   │   │   │   ├── identity/                   Principal — who is calling
│   │   │   │   ├── authentication/             password, MFA, one-time codes
│   │   │   │   ├── authorization/              roles, resources, scopes, policy
│   │   │   │   ├── sessions/                   server-side, in Redis
│   │   │   │   └── rate_limit/                 limits, lockout, locks
│   │   │   ├── domain/                         the only layer that writes
│   │   │   │   ├── audit/  consent/  delegations/  exchange/  messaging/
│   │   │   │   ├── notices/{assets}/  projects/  registry/
│   │   │   │   └── rights/  shared/  users/
│   │   │   ├── db/
│   │   │   │   ├── pool.py  sql.py  redis.py
│   │   │   │   └── repositories/               one per table cluster
│   │   │   ├── infrastructure/
│   │   │   │   ├── dkms/                       the client for backend/dkms
│   │   │   │   └── email/  sms/  storage/  external/  messaging/
│   │   │   ├── tasks/                          Celery
│   │   │   │   └── authentication/  notifications/  maintenance/  exchange/
│   │   │   ├── validation/  schemas/
│   │   │   └── core/                           config, permissions, errors,
│   │   │                                       pagination — imports nothing local
│   │   ├── migrations/versions/                0001 … 0026, raw SQL, both ways
│   │   ├── tests/
│   │   │   ├── unit/{api,auth,core,domain,infrastructure,tasks,validation}/
│   │   │   ├── integration/{auth,database,enforcement}/
│   │   │   ├── security/                       BOLA, BFLA, CSRF, rate limits
│   │   │   └── fixtures/
│   │   ├── scripts/                            seed, create_admin, reset_dev, db
│   │   ├── openapi.json                        generated
│   │   ├── pyproject.toml  .env.example
│   │   └── README.md                           how to run this service
│   │
│   └── dkms/                                   ← cmp_dkms/               moved
│       ├── app/
│       │   ├── main.py  config.py  engine.py  schemas.py
│       │   ├── api/routes.py                   /bulk_encrypt  /bulk_decrypt
│       │   └── dkms/                           base, local, sdk, types
│       ├── tests/
│       ├── requirements.txt  requirements-dev.txt  .env.example
│       └── README.md
```

Nothing inside either service changes. Every Python import path below `src/` is
exactly what it is today; the layering, the domain packages, the migration
chain and the three test suites are untouched. Only the two directories above
them move.

## `frontend/` — everything the browser does

```
├── frontend/
│   │
│   ├── console/                                ← cmp_internal_ui/        moved
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── (app)/                      the authenticated shell
│   │   │   │   │   ├── dashboard/  projects/[uuid]/  approvals/
│   │   │   │   │   ├── notices/[uuid]/  purposes/[uuid]/
│   │   │   │   │   ├── sites/  sources/  processors/  links/
│   │   │   │   │   ├── consents/[uuid]/  collections/[uuid]/
│   │   │   │   │   ├── exports/  imports/[uuid]/
│   │   │   │   │   ├── requests/[uuid]/  tickets/  messages/
│   │   │   │   │   ├── users/  audit/  delegate/
│   │   │   │   │   └── notifications/  account/
│   │   │   │   ├── sign-in/{verify,reset}/
│   │   │   │   └── dkms/decrypt/route.ts       3 lines; the handler is shared
│   │   │   ├── features/                       console-only
│   │   │   │   ├── projects/  notices/  registry/  consent/  exchange/
│   │   │   │   └── rights/  audit/  users/  messages/  delegations/  dashboard/
│   │   │   ├── components/                     console-only, e.g. audit-detail
│   │   │   └── app-config.ts                   what differs from the portal   new
│   │   ├── e2e/
│   │   │   ├── support/                        sessions, outbox, layout
│   │   │   └── __screenshots__/visual/
│   │   ├── public/
│   │   ├── next.config.ts  package.json  .env.example
│   │   └── README.md
│   │
│   ├── portal/                                 ← cmp_public_ui/          moved
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── (app)/                      my-consents, my-requests,
│   │   │   │   │                               notifications, account
│   │   │   │   ├── c/[token]/                  the consent flow
│   │   │   │   ├── rights/{nominee,nominations/[token]}/
│   │   │   │   ├── sign-in/  sign-up/
│   │   │   │   └── dkms/decrypt/route.ts       3 lines; the handler is shared
│   │   │   ├── features/                       portal-only
│   │   │   │   └── public-consent/  my-consents/  rights/
│   │   │   ├── components/                     portal-only
│   │   │   └── app-config.ts                                              new
│   │   ├── e2e/support/
│   │   ├── public/
│   │   ├── next.config.ts  package.json  .env.example
│   │   └── README.md
│   │
│   ├── shared/                                 the 65 identical files, once
│   │   │
│   │   ├── ui/                                 the design system
│   │   │   ├── primitives.tsx  charts.tsx      identical today          shared
│   │   │   ├── dialog.tsx  status.tsx  graphics.tsx
│   │   │   ├── layout/                         app shell, nav, page header
│   │   │   ├── forms/                          Field, useApiForm, FormError
│   │   │   ├── feedback/                       error boundary, empty state
│   │   │   └── styles/                         tokens, themes, base, print
│   │   │
│   │   ├── core/                               the shell both apps need
│   │   │   ├── proxy.ts                        identical today          shared
│   │   │   ├── providers/                      query, toast, theme, error   5 files
│   │   │   ├── auth/                           auth provider, require-section
│   │   │   ├── lib/                            api client, errors, format,
│   │   │   │                                   query keys, security, permissions
│   │   │   ├── schemas/                        contacts, files, primitives  5 files
│   │   │   └── test/                           MSW server, render helper
│   │   │
│   │   ├── api-types/                          one contract, two consumers
│   │   │   ├── api-schema.d.ts                 generated from openapi.json
│   │   │   ├── consent.ts  exchange.ts  meta.ts  envelope.ts  primitives.ts
│   │   │   ├── enums.ts  identity.ts  projects.ts  rights.ts  notices.ts
│   │   │   ├── registry.ts  audit.ts  dashboard.ts  public.ts
│   │   │   └── api-contract.test-d.ts          the curated types, checked
│   │   │
│   │   ├── dkms-client/                        added to both by hand this week
│   │   │   ├── api.ts                          decryptRecords, isEncrypted
│   │   │   ├── use-decrypted.ts                one call for a whole list
│   │   │   └── route-handler.ts                what each app's route.ts calls  new
│   │   │
│   │   └── config/                             one TypeScript and lint preset  new
│   │       └── base.json  next.json  eslint.config.mjs
│   │
│   └── package.json                            npm workspaces: console, portal,
│                                               shared/*                       new
```

## `docs/` — every document in the repository

```
├── docs/
│   ├── README.md                               the map — and it gets shorter,
│   │                                           because there is one tree to map
│   ├── glossary.md
│   │
│   ├── architecture/
│   │   ├── system-overview.md                  the deployables, the datastores,
│   │   │                                       how a request travels
│   │   ├── repository-layout.md                what each folder owns
│   │   ├── domain-model.md  api.md
│   │   ├── layers.md                           ← cmp_backend/docs/       moved
│   │   ├── dependency-rules.md                 ← cmp_backend/docs/       moved
│   │   ├── request-lifecycle.md                ← cmp_backend/docs/       moved
│   │   └── rights.md                           ← cmp_backend/docs/       moved
│   │
│   ├── security/                               ← cmp_backend/docs/security/
│   │   ├── authentication.md  authorization.md  sessions.md
│   │   └── csrf.md  rate-limiting.md  audit.md
│   │
│   ├── database/                               ← cmp_backend/docs/database/
│   │   └── schema.md  migrations.md  transactions.md
│   │
│   ├── domain/                                 behaviour, by obligation
│   │   ├── roles-and-access.md  consent-lifecycle.md
│   │   ├── collection-and-routing.md  rights-requests.md
│   │   └── messages.md  audit-trail.md  personal-data.md
│   │
│   ├── operations/
│   │   ├── local-development.md  deployment.md  runbook.md  testing.md
│   │   ├── configuration.md                    ← cmp_backend/docs/       moved
│   │   └── monitoring.md                       ← cmp_backend/docs/       moved
│   │
│   ├── decisions/                              ADR 0001 … 0014
│   ├── reviews/                                implementation review,
│   │                                           DPDP Act gap assessment
│   │
│   ├── reference/                              generated and hand-reviewed
│   │   ├── api/                                ← api_docs/               moved
│   │   │   ├── README.md  modules/  roles/
│   │   ├── database/                           ← database_schema/        moved
│   │   │   ├── README.md  table_reference.md  enum_reference.md
│   │   │   ├── schema.sql  schema_inventory.json
│   │   │   ├── *.svg  modules/*.svg            the drawings
│   │   │   └── source/                         10 Graphviz .dot sources
│   │   └── access-control/                     ← api_access_control/     moved
│   │       ├── README.md  endpoint_permissions.{md,json}
│   │       ├── roles_and_scopes.md  module_permissions.md
│   │       └── modules/                        17 per-module pages
│   │
│   ├── tools/                                  what regenerates the above
│   │   ├── generate-api-docs.py                ← api_docs/generate.py    moved
│   │   ├── personal-data-scan.py               ← docs/scripts/           moved
│   │   └── README.md                           what each tool regenerates  new
│   │
│   └── history/                                superseded design documents
│
├── .github/workflows/ci.yml
├── README.md  CONTRIBUTING.md  CHANGELOG.md
└── .gitignore
```

`.baseline_routes.txt` — four lines, unexplained — is deleted, or moved to
`docs/tools/` with a sentence saying what it baselines.

## The rules that keep it that way

A structure without rules drifts back. Four, each enforceable by a check rather
than a reviewer's memory.

1. **`frontend/` never imports from `backend/`, and the reverse.** They talk
   over HTTP. The only thing that crosses is the generated
   `api-schema.d.ts`, and it crosses by being generated, not imported.
2. **`console/` and `portal/` never import each other.** Two apps needing the
   same code is the definition of `shared/` — which is why the 65 identical
   files are its first inhabitants.
3. **`shared/` never imports from `console/` or `portal/`.** Dependencies point
   one way; a cycle is a build failure, not a discussion.
4. **Every document is under `docs/`.** The exception is one `README.md` per
   service, and it holds one thing: how to run that service.

## What moves where

| Today | Becomes | Note |
|---|---|---|
| `cmp_backend/` | `backend/api/` | Contents unchanged |
| `cmp_backend/docs/` (17 files) | `docs/{architecture,security,database,operations}/` | Merged into the one tree |
| `cmp_dkms/` | `backend/dkms/` | Contents unchanged |
| `cmp_internal_ui/` | `frontend/console/` | Minus what moves to `shared/` |
| `cmp_public_ui/` | `frontend/portal/` | Same |
| the 65 identical files | `frontend/shared/{ui,core,api-types,dkms-client}/` | The point of the exercise |
| `api_docs/` | `docs/reference/api/` | Generator to `docs/tools/` |
| `database_schema/` | `docs/reference/database/` | |
| `api_access_control/` | `docs/reference/access-control/` | |
| `docs/scripts/` | `docs/tools/` | |
| `.baseline_routes.txt` | deleted, or `docs/tools/` with a comment | |

## How it would be done

Five phases. Each lands on its own and leaves the repository working; none is a
big-bang weekend.

| Phase | What | Risk | Rough size |
|---|---|---|---|
| 1 | `git mv` the four services into `backend/` and `frontend/`, rename them, fix CI paths and `.env.example` references | Low — a rename; history preserved | Half a day |
| 2 | Move all documentation under `docs/`: the backend's 17, the three reference trees, the generators | Low — paths in two scripts and the docs map | Two to three hours |
| 3 | Create `frontend/shared/`; move the **65 identical files**; point both apps at them | Medium — npm workspaces, path aliases, both suites | Two days |
| 4 | Reconcile the 37 near-duplicates, one at a time, deciding each difference | Medium — judgement, not mechanics | Two to three days |
| 5 | Settle on one Python toolchain across `backend/api` and `backend/dkms` | Low | Half a day |

**Use `git mv`, one phase per commit, and never a content edit in a commit that
moves files.** A rename plus an edit is a diff nobody can review; a rename alone
is a diff anybody can.

**What tells you it worked:** after phase 3, copying a file between the two
portals stops being something anyone does, and both suites still pass unchanged.
After phase 4, `git grep -l "useToast" frontend/` returns one file.

## What I would not change

A restructure is a good opportunity to break working things, so it is worth
naming what stays exactly as it is.

- **The backend's internal layering.** `api → domain → db`, with `core`
  importing nothing local, is kept by review and works. It does not become
  better inside `backend/api/`; it just moves.
- **Raw SQL and the migration chain.** 0001 to 0026, both directions, is the
  only record of how the schema came to be. Renumbering or squashing it for
  tidiness would destroy that.
- **Tests beside the thing they test.** The three Python suites belong to
  `backend/api`; the Playwright suites belong to the apps they drive. A
  top-level `tests/` would separate a test from its subject.
- **The documentation's voice.** These documents explain *why*, which is rare
  and expensive to rebuild. Moving files must not become rewriting them.
- **The reference trees' contents.** Generated and hand-reviewed references
  that are genuinely current are worth more than most code. They move and are
  otherwise untouched.

## Two details worth approving explicitly

**The DKMS route handler.** Next requires a `route.ts` inside `app/`, so it
cannot live wholly in `shared/`. The shared package exports the handler and each
app's file is three lines:

```ts
// frontend/console/src/app/dkms/decrypt/route.ts
import { createDecryptHandler } from "@compass/dkms-client/route-handler";
export const POST = createDecryptHandler();
```

**`app-config.ts` is where the two portals differ.** `auth-provider.tsx`,
`app-shell.tsx` and `lib/config/index.ts` differ between them today — one is a
console, one is a portal, and some of that difference is real. The shared module
takes the difference as configuration and each app supplies it in one small
file. This is the only genuinely thoughtful part of the migration, and it is
where you find out which of the current differences were decisions and which
were drift. Budget for it.

## Three smaller things worth doing anyway

Independent of the restructure, and cheap.

1. **Fold the two near-empty domain packages.** `domain/registry` is 10 lines
   and `domain/users` is 11, against `domain/rights` at 3,820 across 6 files.
   Those two are import shims pretending to be aggregates: give them a service
   layer or fold them into their callers.
2. **Split `domain/rights`.** 3,820 lines in one package is the one place where
   the layering is sound but the file is not. Clock, tickets, scope and
   nominations are four things.
3. **Add `CODEOWNERS`.** With two layers and a shared tree, "who reviews a
   change to `frontend/shared/ui`" should be answerable by the repository rather
   than by asking.

## The three decisions that are yours

| Decision | Options | My recommendation |
|---|---|---|
| **Frontend tooling** | npm workspaces (built in, no new tool) · pnpm + Turborepo (faster, caches, another tool) | **npm workspaces.** Two apps and four shared folders do not need a build orchestrator, and the tool you do not install cannot break |
| **Python toolchain** | `uv` for both services · `venv` + `pip` + `requirements.txt` for both | **One of them, written down.** You asked for venv + pip on the key service, so make that the standard and convert `backend/api` — or keep `uv` and convert `backend/dkms`. Not both |
| **Timing** | All five phases now · phases 1–2 now, 3–5 later | **Phases 1–2 now.** They are renames, they are cheap, and they deliver the shape you asked for. Phases 3–4 are where the duplication actually dies and deserve their own window |

## What this is worth

Phases 1 and 2 buy legibility: four entries at the root, one documentation
tree, and a `docs/README.md` that no longer has to explain where the other
documentation lives.

Phases 3 and 4 buy something measurable. Sixty-five files are maintained today
by copying, and the count rises every time either portal gains a feature — it
rose by five this week when the DKMS layer was added to both by hand. After the
split, a fix applied once is applied everywhere.

## Approve, or tell me which lines are wrong

The tree above is the whole proposal made concrete. If it is right, phase 1 —
four `git mv`s and the CI paths — is about half a day and changes no code. If a
line is wrong, a name, a boundary, or the merging of the backend's own `docs/`
into the one tree, say which and I will redraw it before anything moves.
