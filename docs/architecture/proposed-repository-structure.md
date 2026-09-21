# A proposed repository structure

**Status: a proposal.** Nothing here has been done. It is written to be argued
with, and the last section lists the four decisions that are yours rather than
mine.

The repository works. Four deployables build, test and ship; the documentation
is unusually good; the backend's internal layering is sound and enforced. This
is not a rescue. It is the restructure a codebase earns when it has grown from
one service to four and the shape of the folder has not caught up.

## What is there today, measured

```
COMPASS_CMP/                      920 tracked files
  cmp_backend/          319       API + worker + migrations   36,101 lines src, 13,818 tests
  cmp_internal_ui/      285       staff console, port 3000
  cmp_public_ui/        173       data-principal portal, port 3001
  cmp_dkms/              22       key service, port 8100      (added this week)
  docs/                  39       cross-cutting documentation
  api_docs/              27       generated from openapi.json
  database_schema/       26       generated from the database
  api_access_control/    23       hand-reviewed permission reference
  .github/                1       CI
  .baseline_routes.txt    4 lines, unexplained
  README · CONTRIBUTING · CHANGELOG
```

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
diverged by a few lines each, and it is no longer obvious which differences are
deliberate.

This is not theoretical. Adding the DKMS layer this week meant writing five
files and then copying them across. A bug fixed in one portal's toast provider
is a bug still live in the other, and nothing fails to tell you.

**2. Four deployables, four naming conventions.**

`cmp_backend` names a tier. `cmp_internal_ui` and `cmp_public_ui` name an
audience. `cmp_dkms` names a product. The `cmp_` prefix is repeated inside a
repository already called COMPASS_CMP. A newcomer cannot tell from the root
which of these is a Next application and which is a Python service.

**3. Three reference trees sit as peers of the deployables.**

`api_docs/`, `database_schema/` and `api_access_control/` are documentation —
two generated, one hand-reviewed. At the root they read as projects. The
practical cost: `docs/README.md` has to explain that three of the eight
top-level directories are really part of the documentation, which is a
signpost compensating for a layout.

**4. Two Python toolchains, chosen by accident.**

`cmp_backend` uses `uv` with a lockfile. `cmp_dkms` uses `venv` + `pip` +
`requirements.txt`, because that is what was asked for when it was built. Both
are defensible; having both, undocumented, is not.

## The proposal

Three top-level directories with one meaning each, which is the whole idea:
**`apps/` is what you deploy, `packages/` is what they share, `docs/` is what
explains them.** Everything else at the root is repository furniture.

```
compass/
│
├── apps/                        ← every deployable, one folder each
│   ├── api/                     the platform API, the worker, the migrations
│   │   ├── src/cmp/             (unchanged inside: the layering is good)
│   │   ├── migrations/
│   │   ├── tests/{unit,integration,security}/
│   │   ├── scripts/
│   │   └── README.md
│   ├── dkms/                    the key service
│   ├── console/                 the staff console            :3000
│   │   ├── src/{app,features,styles}/
│   │   ├── e2e/
│   │   └── README.md
│   └── portal/                  the data-principal portal    :3001
│       ├── src/{app,features,styles}/
│       ├── e2e/
│       └── README.md
│
├── packages/                    ← shared, imported by name, never copied
│   ├── ui/                      primitives, charts, layout, tokens, themes
│   ├── web-core/                providers, proxy, lib/, test harness, schemas
│   ├── api-types/               generated api-schema.d.ts + the curated types
│   ├── dkms-client/             the browser/server decrypt layer, once
│   └── tsconfig/                one TypeScript and lint preset, extended by each app
│
├── docs/                        ← the only place documentation lives
│   ├── architecture/            system overview, layers, this file
│   ├── decisions/               ADRs 0001-0014
│   ├── domain/                  behaviour by obligation, personal-data.md
│   ├── operations/              local development, deployment, runbook, testing
│   ├── security/                authn, authz, sessions, csrf, audit  (from apps/api)
│   ├── reference/               ← the three trees, as what they are
│   │   ├── api/                 generated from openapi.json
│   │   ├── database/            generated from the schema
│   │   └── access-control/      hand-reviewed
│   ├── history/
│   └── README.md                the map
│
├── tools/                       ← things that build or check the repo
│   ├── generate-api-docs.py
│   ├── generate-schema-docs.py
│   └── personal-data-scan.py
│
├── .github/workflows/
├── package.json                 workspaces: apps/console, apps/portal, packages/*
├── CHANGELOG.md · CONTRIBUTING.md · README.md
└── .gitignore
```

### The rules that keep it that way

A structure without rules is a structure that drifts back. Four, each of which
can be enforced by a check rather than a reviewer's memory.

1. **An app never imports another app.** Two apps needing the same code is the
   definition of a package. (`packages/` exists for exactly this, and the
   65 identical files are its first inhabitants.)
2. **A package never imports an app.** Dependencies point one way; a cycle is a
   build failure, not a discussion.
3. **A package is named for what it is, not for who uses it.** `ui`, not
   `shared`; `api-types`, not `common`. A folder called `shared` or `utils`
   becomes the place things go to stop being findable.
4. **Documentation lives in `docs/`.** Not beside the code it describes, not at
   the root. `apps/*/README.md` is the exception and holds one thing: how to
   run *that* app.

### What moves where

| Today | Becomes | Note |
|---|---|---|
| `cmp_backend/` | `apps/api/` | Contents unchanged |
| `cmp_backend/docs/` | `docs/{architecture,security,database,operations}/` | Merged into the one tree |
| `cmp_internal_ui/` | `apps/console/` | Minus what moves to `packages/` |
| `cmp_public_ui/` | `apps/portal/` | Same |
| `cmp_dkms/` | `apps/dkms/` | Contents unchanged |
| `api_docs/` | `docs/reference/api/` | Generator to `tools/` |
| `database_schema/` | `docs/reference/database/` | Generator to `tools/` |
| `api_access_control/` | `docs/reference/access-control/` | |
| `docs/scripts/` | `tools/` | With the other generators |
| `.baseline_routes.txt` | deleted, or `tools/` with a comment | Four lines nobody has explained |

### The 65 files, specifically

The first package is not a design exercise; it is a list that already exists.

| To `packages/web-core` | To `packages/ui` | To `packages/api-types` |
|---|---|---|
| `proxy.ts` | `components/ui/primitives.tsx` | `api-schema.d.ts` (generated) |
| `providers/*` (5 files) | `components/ui/charts.tsx` | `types/{consent,exchange,meta,envelope,primitives,enums}.ts` |
| `schemas/*` (5 files) | `styles/*` | `api-contract.test-d.ts` |
| `test/{server,render}.ts` | | |
| `features/dkms/*` (4 files) | | |

The near-duplicates are the interesting half. `lib/config/index.ts`,
`auth-provider.tsx` and `app-shell.tsx` differ *on purpose* — one console, one
portal. Those become a shared module with the difference passed in, and the
work of splitting them is where you find out which differences were deliberate
and which were drift. Budget for that; it is the only genuinely thoughtful part
of the migration.

## How it would be done

Five phases, each one landing on its own and leaving the repository working.
Nothing here is a big-bang weekend.

| Phase | What | Risk | Rough size |
|---|---|---|---|
| 1 | `git mv` the four projects into `apps/`, rename them, fix CI paths and the `.env.example` references | Low — a rename, history preserved | Half a day |
| 2 | Move the three reference trees under `docs/reference/`, the generators into `tools/` | Low — paths in two scripts and the docs map | Two hours |
| 3 | Create `packages/ui`, `web-core`, `api-types`; move the **65 identical files**; point both apps at them | Medium — npm workspaces, path aliases, both test suites | Two days |
| 4 | Reconcile the 37 near-duplicates, one at a time, deciding each difference | Medium — this is judgement, not mechanics | Two to three days |
| 5 | Settle the Python toolchain, and the API's own `docs/` folding into `docs/` | Low | Half a day |

**Do it with `git mv`, one phase per commit, and no content edits in the same
commit as a move.** A rename plus an edit is a diff nobody can review; a rename
alone is a diff anybody can. The history follows the file either way, but only
one of those can be read.

**What tells you it worked:** after phase 3, `cp` between the two apps stops
being a thing anybody does, and the suites still pass unchanged. After phase 4,
`git grep -l "useToast" apps/` returns one file.

## What I would not change

Restructuring is a good time to break working things, so it is worth naming
what should be left alone.

- **The backend's internal layering.** `api → domain → db`, with `core`
  importing nothing local, is enforced by a test and works. It does not become
  better inside `apps/api/`; it just moves.
- **Raw SQL and the migration chain.** 0001 to 0026, both directions, is an
  asset. Renumbering or squashing it for tidiness would destroy the one record
  of how the schema came to be.
- **Tests beside their app.** Unit, integration and security tests belong to
  `apps/api`; the Playwright suites belong to the apps they drive. A top-level
  `tests/` would separate a test from the thing it tests.
- **The documentation's voice.** The docs explain *why*, which is rare and
  expensive to rebuild. Moving files must not turn into rewriting them.
- **The three reference trees themselves.** Generated and hand-reviewed
  references that are actually current are worth more than most code. They move
  and are otherwise untouched.

## Three smaller things worth doing anyway

Independent of the restructure, and cheap.

1. **Fold the two near-empty domain packages.** `domain/registry` is 10 lines,
   `domain/users` is 11, against `domain/rights` at 3,820 across 6 files. Those
   two are import shims pretending to be aggregates. Either give them their
   service layer or fold them into their callers.
2. **Split `domain/rights`.** 3,820 lines in one package, with `service.py`
   carrying most of it, is the one place in the backend where the layering is
   sound but the file is not. Clock, tickets, scope and nominations are four
   things.
3. **Add `CODEOWNERS`.** With four apps and a shared package tree, "who reviews
   a change to `packages/ui`" should be answerable by the repository rather
   than by asking.

## The four decisions that are yours

I have a recommendation for each; none of them is mine to take.

| Decision | Options | My recommendation |
|---|---|---|
| **Monorepo tooling** | npm workspaces (built in, no new tool) · pnpm + Turborepo (faster, caches, another tool) | **npm workspaces.** Two Next apps and four packages do not need a build orchestrator, and the one you do not install cannot break |
| **Python toolchain** | `uv` everywhere · `venv` + `pip` + `requirements.txt` everywhere | **One of them, written down.** You asked for venv + pip on the new service, so make that the standard and convert `apps/api`, or keep `uv` and convert `apps/dkms`. Not both |
| **Naming** | `apps/console` + `apps/portal` · keep `internal-ui` / `public-ui` | **`console` and `portal`.** They are the words the documentation and the team already use in prose |
| **Timing** | All five phases now · phases 1–2 now, 3–4 when the portals next need shared work | **Phases 1–2 now, 3–4 next.** The renames are cheap and stop the bleeding of "which folder is this"; the package split is where the real value is and deserves its own window |

## What this is worth

The honest summary: phases 1 and 2 buy legibility — a newcomer reads the root
and knows what the system is. Phase 3 and 4 buy something measurable, which is
that a fix applied once is applied everywhere. Sixty-five files are currently
maintained by copying, and the count goes up every time either portal gains a
feature: it went up by five this week, when the DKMS layer was added to both by
hand.

That is the argument. The structure above is conventional on purpose — `apps/`
and `packages/` is what most people mean by a well-kept monorepo, and a
convention a new engineer already knows is worth more than a better layout they
have to learn.

---

# The complete tree, for approval

Every directory that exists today, placed where it would go. Nothing is
invented: each line is either a folder that exists now, a folder that holds
files which exist now, or is marked **new**.

Read the right-hand column as the decision. `moved` is a `git mv` and nothing
else. `shared` means the files are currently duplicated in both portals and
would live in one place. **new** means a file that does not exist yet and would
have to be written.

```
compass/
│
├── apps/
│   │
│   ├── api/                                    ← cmp_backend/            moved
│   │   ├── src/cmp/
│   │   │   ├── main.py  __main__.py
│   │   │   ├── bootstrap/                      factory, lifespan, container
│   │   │   ├── api/
│   │   │   │   ├── routers/v1/                 14 modules
│   │   │   │   ├── routers/public/             consent, rights
│   │   │   │   ├── dependencies/               sessions, csrf, authz, paging
│   │   │   │   ├── middleware/                 context, headers, body, access log
│   │   │   │   └── errors/                     one error contract
│   │   │   ├── auth/
│   │   │   │   ├── identity/  authentication/  authorization/
│   │   │   │   └── sessions/  rate_limit/
│   │   │   ├── domain/                         the only layer that writes
│   │   │   │   ├── audit/  consent/  delegations/  exchange/
│   │   │   │   ├── messaging/  notices/{assets}/  projects/
│   │   │   │   ├── registry/  rights/  shared/  users/
│   │   │   ├── db/
│   │   │   │   ├── pool.py  sql.py  redis.py
│   │   │   │   └── repositories/               one per table cluster
│   │   │   ├── infrastructure/
│   │   │   │   ├── dkms/                       client for apps/dkms
│   │   │   │   ├── email/  sms/  storage/  external/  messaging/
│   │   │   ├── tasks/
│   │   │   │   └── authentication/  notifications/  maintenance/  exchange/
│   │   │   ├── validation/  schemas/
│   │   │   └── core/                           imports nothing local
│   │   ├── migrations/versions/                0001 … 0026, raw SQL
│   │   ├── tests/
│   │   │   ├── unit/{api,auth,core,domain,infrastructure,tasks,validation}/
│   │   │   ├── integration/{auth,database,enforcement}/
│   │   │   ├── security/
│   │   │   └── fixtures/
│   │   ├── scripts/                            seed, create_admin, reset_dev, db
│   │   ├── openapi.json                        generated
│   │   ├── pyproject.toml
│   │   ├── .env.example
│   │   └── README.md                           how to run this app, nothing else
│   │
│   ├── dkms/                                   ← cmp_dkms/               moved
│   │   ├── app/
│   │   │   ├── main.py  config.py  engine.py  schemas.py
│   │   │   ├── api/routes.py
│   │   │   └── dkms/                           base, local, sdk, types
│   │   ├── tests/
│   │   ├── requirements.txt  requirements-dev.txt
│   │   ├── .env.example
│   │   └── README.md
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
│   │   │   │   └── dkms/decrypt/route.ts       3 lines, calls the package
│   │   │   ├── features/                       console-only
│   │   │   │   ├── projects/  notices/  registry/  consent/
│   │   │   │   ├── exchange/  rights/  audit/  users/
│   │   │   │   ├── messages/  delegations/  dashboard/
│   │   │   ├── components/                     console-only: audit-detail, …
│   │   │   └── app-config.ts                   what differs from the portal   new
│   │   ├── e2e/
│   │   │   ├── support/                        sessions, outbox, layout
│   │   │   └── __screenshots__/visual/
│   │   ├── public/
│   │   ├── next.config.ts  package.json  .env.example
│   │   └── README.md
│   │
│   └── portal/                                 ← cmp_public_ui/          moved
│       ├── src/
│       │   ├── app/
│       │   │   ├── (app)/                      my-consents, my-requests,
│       │   │   │                               notifications, account
│       │   │   ├── c/[token]/                  the consent flow
│       │   │   ├── rights/{nominee,nominations/[token]}/
│       │   │   ├── sign-in/  sign-up/
│       │   │   └── dkms/decrypt/route.ts       3 lines, calls the package
│       │   ├── features/                       portal-only
│       │   │   ├── public-consent/  my-consents/  rights/
│       │   ├── components/                     portal-only
│       │   └── app-config.ts                                              new
│       ├── e2e/support/
│       ├── public/
│       ├── next.config.ts  package.json  .env.example
│       └── README.md
```

```
compass/  (continued)
│
├── packages/                                   everything below is currently
│   │                                           duplicated in both portals
│   │
│   ├── ui/                                     the design system
│   │   ├── src/
│   │   │   ├── primitives.tsx                  identical today          shared
│   │   │   ├── charts.tsx                      identical today          shared
│   │   │   ├── dialog.tsx  status.tsx  graphics.tsx
│   │   │   ├── layout/                         app-shell, nav, page header
│   │   │   ├── forms/                          Field, useApiForm, FormError
│   │   │   ├── feedback/                       error boundary, empty state
│   │   │   └── styles/                         tokens, themes, base, print
│   │   └── package.json
│   │
│   ├── web-core/                               the shell every Next app needs
│   │   ├── src/
│   │   │   ├── proxy.ts                        identical today          shared
│   │   │   ├── providers/                      query, toast, theme, error    5 files
│   │   │   ├── auth/                           auth-provider, require-section
│   │   │   ├── lib/
│   │   │   │   ├── api/                        the fetch client, envelope
│   │   │   │   ├── errors/  format/  query/  security/  permissions/
│   │   │   ├── schemas/                        contacts, files, primitives   5 files
│   │   │   └── test/                           MSW server, render helper
│   │   └── package.json
│   │
│   ├── api-types/                              one contract, two consumers
│   │   ├── src/
│   │   │   ├── api-schema.d.ts                 generated from openapi.json
│   │   │   ├── consent.ts  exchange.ts  meta.ts  envelope.ts
│   │   │   ├── primitives.ts  enums.ts  identity.ts  projects.ts
│   │   │   ├── rights.ts  notices.ts  registry.ts  audit.ts  dashboard.ts
│   │   │   └── api-contract.test-d.ts          the curated types, checked
│   │   └── package.json
│   │
│   ├── dkms-client/                            added to both by hand this week
│   │   ├── src/
│   │   │   ├── api.ts                          decryptRecords, isEncrypted
│   │   │   ├── use-decrypted.ts                one call for a whole list
│   │   │   └── route-handler.ts                the POST each app re-exports   new
│   │   └── package.json
│   │
│   └── tsconfig/                                                          new
│       ├── base.json  next.json  eslint.config.mjs
│       └── package.json
│
├── docs/
│   ├── README.md                               the map
│   ├── glossary.md
│   ├── architecture/
│   │   ├── system-overview.md  repository-layout.md  domain-model.md  api.md
│   │   ├── layers.md  dependency-rules.md  request-lifecycle.md   ← apps/api/docs
│   │   └── rights.md                                              ← apps/api/docs
│   ├── security/                                                  ← apps/api/docs
│   │   ├── authentication.md  authorization.md  sessions.md
│   │   ├── csrf.md  rate-limiting.md  audit.md
│   ├── database/                                                  ← apps/api/docs
│   │   ├── schema.md  migrations.md  transactions.md
│   ├── domain/
│   │   ├── roles-and-access.md  consent-lifecycle.md
│   │   ├── collection-and-routing.md  rights-requests.md
│   │   ├── messages.md  audit-trail.md  personal-data.md
│   ├── operations/
│   │   ├── local-development.md  deployment.md  runbook.md  testing.md
│   │   ├── configuration.md  monitoring.md                        ← apps/api/docs
│   ├── decisions/                              ADR 0001 … 0014
│   ├── reviews/                                implementation review, DPDP gap
│   ├── reference/                              generated and hand-reviewed
│   │   ├── api/                                ← api_docs/              moved
│   │   ├── database/                           ← database_schema/       moved
│   │   └── access-control/                     ← api_access_control/    moved
│   └── history/
│
├── tools/                                      what builds or checks the repo
│   ├── generate-api-docs.py                    ← api_docs/generate.py
│   ├── personal-data-scan.py                   ← docs/scripts/
│   ├── schema-diagrams/                        ← database_schema/source/
│   │                                           the Graphviz sources the SVGs
│   │                                           are drawn from (10 .dot files)
│   └── README.md                               what each tool regenerates    new
│
├── .github/workflows/ci.yml
├── package.json                                workspaces: apps/*, packages/*  new
├── README.md  CONTRIBUTING.md  CHANGELOG.md
└── .gitignore
```

## What the tree is claiming, in four sentences

**The root answers "what is this system".** Four apps, five packages, one
documentation tree, one tools folder. Nothing at the root is a mystery, and
`.baseline_routes.txt` is gone.

**`apps/api` and `apps/dkms` are unchanged inside.** Every Python path below
`src/` is exactly what it is today. The restructure does not touch the
backend's layering, its domain packages, its migrations or its tests — only the
two directories above them.

**The two Next apps keep what makes them different and lose what does not.**
What stays: routes, the features that are genuinely theirs, the components only
one of them has. What leaves: the providers, the fetch client, the schemas, the
test harness, the primitives, the types — 65 files that are identical today and
37 more that differ only by drift.

**`app-config.ts` is where the difference lives.** Where `auth-provider.tsx`,
`app-shell.tsx` and `lib/config/index.ts` differ between the portals today, the
shared module takes the difference as configuration and each app supplies it in
one small file. That is the piece of real design work in this proposal, and it
is also where you find out which of the current differences were decisions.

## Two details worth approving explicitly

**The DKMS route handler.** Next requires a `route.ts` inside `app/`, so it
cannot live wholly in a package. The package exports the handler and each app's
file is three lines:

```ts
// apps/console/src/app/dkms/decrypt/route.ts
import { createDecryptHandler } from "@compass/dkms-client/route-handler";
export const POST = createDecryptHandler();
```

**The `docs/security/` and `docs/database/` folders come from `apps/api/docs`.**
Today the backend keeps seventeen documents about its own internals, and
`docs/README.md` has a whole section pointing at them. Merging them removes the
signpost. The counter-argument is real — documentation next to the code it
describes is easier to keep current — so this is the one move in the tree I would
most readily drop if you disagree.

## Names, for approval

| Proposed | Instead of | Why |
|---|---|---|
| `apps/api` | `cmp_backend` | It is the API; "backend" names a tier, not a thing |
| `apps/console` | `cmp_internal_ui` | The word the docs and the team already use |
| `apps/portal` | `cmp_public_ui` | Same |
| `apps/dkms` | `cmp_dkms` | The `cmp_` prefix repeats the repository's own name |
| `packages/web-core` | — | Named for what it is; not `shared`, not `common` |
| `docs/reference/` | three root folders | They are reference documentation, not projects |

## Approve, or tell me which lines are wrong

The tree above is the whole proposal made concrete. If it is right, phase 1
(the four `git mv`s and the CI paths) is about half a day and changes no code.
If a line is wrong — a name, a package boundary, the `apps/api/docs` merge —
say which, and I will redraw it before anything moves.
