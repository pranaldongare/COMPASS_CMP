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
