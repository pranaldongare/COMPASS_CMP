# Repository layout

Three layers at the root and nothing else: everything the server does, everything
the browser does, and every document.

```
compass/
  backend/                  every server-side thing
    api/                    the platform API, the worker, the migrations
    dkms/                   the key service: bulk field encryption
  frontend/                 every browser-side thing
    console/                the staff console, port 3000
    portal/                 the data-principal portal, port 3001
  docs/                     every document in the repository
    architecture/           the system, the API's internals, this file
    security/  database/    the mechanisms, the schema
    domain/                 behaviour by obligation
    operations/             running it, locally and elsewhere
    decisions/              ADRs, one per choice worth not re-litigating
    reviews/  history/
    reference/              generated and hand-reviewed references
      api/  database/  access-control/
    tools/                  what regenerates and checks the above
  .github/                  CI
  README.md  CONTRIBUTING.md  CHANGELOG.md
```

Four rules keep it that way:

1. **`frontend/` never imports from `backend/`, and the reverse.** They talk
   over HTTP. The only thing that crosses is the generated `api-schema.d.ts`,
   and it crosses by being generated rather than imported.
2. **`console/` and `portal/` never import each other.** Two apps needing the
   same code is the definition of a shared package.
3. **Documentation lives in `docs/`.** The exception is one `README.md` per
   service, holding one thing: how to run that service.
4. **Generated artefacts are regenerated, never edited.** `docs/tools/` holds
   the generators; `docs/tools/check-links.py` asserts every relative link in
   every document still resolves.

## `backend/api/`

```
backend/api/
  src/cmp/
    main.py               ASGI entrypoint; `python -m cmp` supplies the event loop
    bootstrap/            assembly: factory, lifespan, middleware, routers, container
    api/
      routers/v1/         audit, auth, consents, dashboard, delegations, exchange,
                          me, messages, notices, projects, registry, rights, system, users
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
      audit/ consent/ delegations/ exchange/ messaging/ notices/ projects/ registry/
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
  migrations/versions/    0001 to 0026, every one raw SQL, both directions
  tests/
    unit/                 pure functions; no I/O
    integration/          a real PostgreSQL and Redis; each test rolls back
    security/             BOLA, BFLA, CSRF, rate limits, authentication, registration
  scripts/                seed, create_admin, reset_dev, healthcheck, db
  dev-services.yml        PostgreSQL and Redis for development; the one Docker file
  requirements*.txt       the runtime, pinned; and the tools on top of it
  docs/                   the API's internals, security and operations
  openapi.json            generated from the application; the API reference
  var/                    local only, ignored: uploads, the outbox, the beat schedule
```

The layering rule - a layer may only call the layer below it - is in
[layers.md](../architecture/layers.md), and the import
graph in
[dependency-rules.md](../architecture/dependency-rules.md).

## `frontend/console/` and `frontend/portal/`

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
| `frontend/console` | dashboard, projects, approvals, notices, purposes, sites, sources, processors, links, consents, exports, imports, collections, requests, tickets, users, audit, cover, notifications, account; sign-in with MFA and reset |
| `frontend/portal` | `c/[token]` (the consent flow), sign-up, sign-in, rights, rights/nominee, rights/nominations/[token]; signed in: my-consents, my-requests, notifications, account |

## Where to find a thing

| Looking for | Start at |
|---|---|
| What a role may do | `backend/api/src/cmp/core/permissions.py` (`MATRIX`, `NAV_BY_ROLE`) |
| A state machine | `domain/projects/state_machine.py`, `domain/rights/state_machine.py` |
| The rights clock | `domain/rights/clock.py` |
| A table's shape | the migration that created it, under `migrations/versions/` |
| A setting | `core/config.py`, documented in `backend/api/.env.example` |
| A scheduled task | `tasks/app.py` (`beat_schedule`) |
| A queue | `tasks/app.py` (`task_routes`) |
| An error code | `core/errors.py` |
| An email or SMS wording | `infrastructure/email/templates.py`, `tasks/authentication/otp.py` |
| A console page's data | `frontend/console/src/features/<area>/queries.ts` |
| A form's validation | `src/features/<area>/schemas.ts` in either portal |
| How a browser test signs in | `e2e/auth.setup.ts` and `e2e/support/` in either portal |

## Generated files

| File | Generated by | When to regenerate |
|---|---|---|
| `backend/api/openapi.json` | `python -c "from cmp.main import app; import json; json.dump(app.openapi(), open('openapi.json','w'), indent=2)"` in the API's venv | Any route or schema change |
| `src/types/api-schema.d.ts` in each portal | `npm run api:types`, against the running API | After regenerating the OpenAPI document |
| `e2e/__screenshots__/` in `frontend/console` | `npx playwright test visual.spec.ts --project=visual --update-snapshots` | A deliberate visual change, reviewed image by image |

## Local, ignored files

| Path | Holds |
|---|---|
| `backend/api/.env`, `<portal>/.env.local` | Local settings; created from the `.env.example` beside each |
| `backend/api/var/outbox.log` | Every email and SMS the local system "sent": codes, links, notices |
| `backend/api/var/uploads/` | Files stored by the local storage backend |
| `<portal>/e2e/.auth/` | Browser sessions saved by the Playwright setup project |
| `<portal>/test-results/`, `playwright-report/` | Failure artefacts |

None of these are committed; `.gitignore` in each project covers them.
