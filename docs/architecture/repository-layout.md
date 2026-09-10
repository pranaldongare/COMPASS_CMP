# Repository layout

One repository, three deployable projects, and the documents that describe
them. The projects share a backend and a design system but are built, tested
and deployed separately.

```
COMPASS_CMP/
  README.md                 what this is and how to run it
  CONTRIBUTING.md           the checks a change must pass; how commits are written
  CHANGELOG.md              what changed, by area and date
  docs/                     cross-cutting documentation (this tree)
  cmp_backend/              the API, the worker, the migrations
  cmp_internal_ui/          the staff console, port 3000
  cmp_public_ui/            the data-principal portal, port 3001
```

## `cmp_backend/`

```
cmp_backend/
  src/cmp/
    main.py               ASGI entrypoint; `python -m cmp` supplies the event loop
    bootstrap/            assembly: factory, lifespan, middleware, routers, container
    api/
      routers/v1/         audit, auth, consents, dashboard, delegations, exchange,
                          me, notices, projects, registry, rights, system, users
      routers/public/     consent (the /c/{token} flow), rights (public pages,
                          nominations, the nominee's entry point, the notice viewer)
      dependencies/       sessions, csrf, authentication, authorization, paging, filters
      middleware/         request context, security headers, body limit, access log
      errors/             one error contract: responses, handlers, status mapping
    auth/
      identity/           Principal - who is calling
      authentication/     password, MFA, one-time codes, password reset
      authorization/      roles, resources, scopes, evaluator, policy
      sessions/           server-side sessions in Redis
      rate_limit/         limits, lockout, distributed locks
    domain/               one package per aggregate; the only layer that writes
      audit/ consent/ delegations/ exchange/ notices/ projects/ registry/
      rights/ shared/ users/
    validation/           the constrained types every request model is built from,
                          contact normalisation, the choice-or-422 helper
    db/
      pool.py sql.py redis.py
      repositories/       one per table cluster, plus the audit entity resolver
    infrastructure/       email, sms, storage, outbound HTTP - swappable adapters
    core/                 config, enums, permissions, security, errors, pagination,
                          logging - imports nothing local
    tasks/                Celery: authentication, notifications, maintenance, exchange
  migrations/versions/    0001 to 0023, every one raw SQL, both directions
  tests/
    unit/                 pure functions; no I/O
    integration/          a real PostgreSQL and Redis; each test rolls back
    security/             BOLA, BFLA, CSRF, rate limits, authentication, registration
  scripts/                seed, create_admin, reset_dev, healthcheck, db
  docker/                 Dockerfile, docker-compose.yml, nginx, initdb
  docs/                   the API's internals, security and operations
  openapi.json            generated from the application; the API reference
  var/                    local only, ignored: uploads, the outbox, the beat schedule
```

The layering rule - a layer may only call the layer below it - is in
[layers.md](../../cmp_backend/docs/architecture/layers.md), and the import
graph in
[dependency-rules.md](../../cmp_backend/docs/architecture/dependency-rules.md).

## `cmp_internal_ui/` and `cmp_public_ui/`

Both portals share one shape:

```
<portal>/
  src/
    proxy.ts              the first thing that touches a request: CSP nonce,
                          cookie-presence redirect (Next 16's middleware)
    app/                  routes; (app)/ is the authenticated shell
    features/<name>/      one folder per business area
      api.ts              thin endpoint functions - no React
      queries.ts          useQuery hooks, keyed from lib/query/keys
      mutations.ts        useMutation hooks and what they invalidate
      schemas.ts          zod form schemas mirroring the API's validation
      components/         the feature's forms, cards and dialogs
    components/           ui primitives, data display, forms, layout, security
    lib/                  api client, errors, query keys, permissions, security,
                          config, formatting
    providers/            error boundary, query, theme, toast, auth
    schemas/              shared zod primitives: contacts, files, security
    types/                curated API types per domain; api-schema.d.ts is generated
    styles/               tokens, themes, base, utilities, print
    test/                 MSW server, fixtures, render helpers
  e2e/                    Playwright specs and support (sessions, outbox, layout)
  next.config.ts          the /api proxy, allowed dev origins, headers
```

| Portal | Routes |
|---|---|
| `cmp_internal_ui` | dashboard, projects, approvals, notices, purposes, sites, sources, processors, links, consents, exports, imports, collections, requests, tickets, users, audit, cover, notifications, account; sign-in with MFA and reset |
| `cmp_public_ui` | `c/[token]` (the consent flow), sign-up, sign-in, rights, rights/nominee, rights/nominations/[token]; signed in: my-consents, my-requests, notifications, account |

## Where to find a thing

| Looking for | Start at |
|---|---|
| What a role may do | `cmp_backend/src/cmp/core/permissions.py` (`MATRIX`, `NAV_BY_ROLE`) |
| A state machine | `domain/projects/state_machine.py`, `domain/rights/state_machine.py` |
| The rights clock | `domain/rights/clock.py` |
| A table's shape | the migration that created it, under `migrations/versions/` |
| A setting | `core/config.py`, documented in `cmp_backend/.env.example` |
| A scheduled task | `tasks/app.py` (`beat_schedule`) |
| A queue | `tasks/app.py` (`task_routes`) |
| An error code | `core/errors.py` |
| An email or SMS wording | `infrastructure/email/templates.py`, `tasks/authentication/otp.py` |
| A console page's data | `cmp_internal_ui/src/features/<area>/queries.ts` |
| A form's validation | `src/features/<area>/schemas.ts` in either portal |
| How a browser test signs in | `e2e/auth.setup.ts` and `e2e/support/` in either portal |

## Generated files

| File | Generated by | When to regenerate |
|---|---|---|
| `cmp_backend/openapi.json` | `uv run python -c "from cmp.main import app; import json; json.dump(app.openapi(), open('openapi.json','w'), indent=2)"` | Any route or schema change |
| `src/types/api-schema.d.ts` in each portal | `npm run api:types`, against the running API | After regenerating the OpenAPI document |
| `e2e/__screenshots__/` in `cmp_internal_ui` | `npx playwright test visual.spec.ts --project=visual --update-snapshots` | A deliberate visual change, reviewed image by image |

## Local, ignored files

| Path | Holds |
|---|---|
| `cmp_backend/.env`, `<portal>/.env.local` | Local settings; created from the `.env.example` beside each |
| `cmp_backend/var/outbox.log` | Every email and SMS the local system "sent": codes, links, notices |
| `cmp_backend/var/uploads/` | Files stored by the local storage backend |
| `<portal>/e2e/.auth/` | Browser sessions saved by the Playwright setup project |
| `<portal>/test-results/`, `playwright-report/` | Failure artefacts |

None of these are committed; `.gitignore` in each project covers them.
