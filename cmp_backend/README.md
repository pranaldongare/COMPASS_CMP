# CMP backend

The API of the consent management platform: FastAPI 0.141 on Python 3.12,
PostgreSQL 16, Redis 7, Celery 5. 233 endpoints over 31 tables, every query
hand-written SQL over psycopg 3, every migration raw DDL. The repository-wide
documentation is under [../docs/](../docs/README.md); this README is the
backend's own front door.

## Running it

Two datastores, natively or as containers:

```bash
docker compose -f docker/docker-compose.yml -p cmp up -d db redis
```

The compose project is `cmp`. The development database is `cmp_dev`; if the
`cmp_pgdata` volume carries an older database named `cmp` from another
project, leave it be.

Then:

```bash
uv sync --all-extras --dev
cp .env.example .env               # POSTGRES_DB=cmp_dev; PUBLIC_BASE_URL and CONSOLE_BASE_URL to the two portals
uv run alembic upgrade head        # 22 migrations: 31 tables, 39 enums, triggers, grants
uv run python scripts/seed.py      # one coherent world: a user per role, processors, sources, sites, a project through to approved, a live link

uv run python -m cmp --port 8000
uv run celery -A cmp.tasks.app worker -Q high_priority,email,documents,reports,notifications,default -l info --pool=solo
uv run celery -A cmp.tasks.app beat -l info
```

`http://127.0.0.1:8000/docs` is the interactive reference outside production.

> **Why `python -m cmp` and not `uvicorn cmp.main:app`?** psycopg's async
> mode cannot run on Windows' `ProactorEventLoop`, and uvicorn builds its loop
> through a `loop_factory` that bypasses the policy. The module entrypoint
> supplies the loop. On Linux the two are equivalent; production uses
> gunicorn (see `docker/Dockerfile`).

### Development codes

One-time codes and MFA codes are hashed before storage and never logged. In
`local` and `test` only, every delivered message is appended to
`var/outbox.log`; that is where a code is read from during development and by
the browser suites. The guard is on `settings.environment`, checked before
anything is formatted, so a production process never writes one.

## Architecture

```
HTTP  ->  middleware  ->  router  ->  permission guard  ->  service  ->  repository  ->  PostgreSQL
          request id      parse       role + scope          rules        raw SQL        triggers
          audit ctx       validate    in the WHERE          all writes   psycopg        constraints
          headers         no SQL      clause                audit.record()              grants
```

| Layer | Directory | May do | May not do |
|---|---|---|---|
| API | `src/cmp/api/` | parse, validate shape, resolve role | business logic, SQL |
| Domain | `src/cmp/domain/` | business rules, transitions, **all writes** | touch HTTP |
| Repository | `src/cmp/db/` | SQL | business logic |
| Database | `migrations/` | constraints, triggers, grants | |

**There is no ORM, deliberately** ([ADR 0001](../docs/decisions/0001-no-orm-raw-sql.md)).
The migrations are the schema; a model layer would be a second copy that
drifts.

**Only services write.** A router that writes bypasses `audit.record()`. The
audit row and the change it describes share one transaction, so a change
that rolled back leaves no audit row, and one that committed cannot be
missing one.

The layers in detail: [docs/architecture/layers.md](docs/architecture/layers.md)
and [dependency-rules.md](docs/architecture/dependency-rules.md). A request's
path: [request-lifecycle.md](docs/architecture/request-lifecycle.md).

## What the database enforces

The application refuses these first, to give a better error. The database
refuses them too, because "the application always calls the service layer"
is a claim about a codebase, and a codebase changes
([ADR 0002](../docs/decisions/0002-evidence-enforced-in-the-database.md)).

| Guarantee | Mechanism |
|---|---|
| Consent evidence, disclosures, history and the audit log are append-only | trigger and revoked grant |
| Audit rows are hash-chained, in commit order | `cmp_audit_chain()`, position drawn inside the advisory lock; `GET /audit/verify` walks it |
| A published notice is frozen | `cmp_notice_freeze()` |
| The artefact carries the hash of the text served; served precedes action | `cmp_consent_coherent()`, `CHECK served_before_action` |
| One artefact superseded once | partial unique index |
| Bystanders may exist, visibly | nullable `consent_id` on `asset_consent` with a CHECK |
| Data categories are itemised (Rule 3(b)(i)) | `CHECK cardinality(...) >= 1` |
| Links only for approved projects | `cmp_link_coherent()` |
| A data principal and a nominee have a mobile; staff have an email | `BEFORE INSERT` triggers and a CHECK |
| A minor cannot consent to a purpose not permitted for minors | `cmp_is_minor(dob)`, checked in the consent service |

`tests/integration/enforcement/` breaks each of these with raw SQL, on
purpose.

## Conventions

- **Identifiers on the wire are uuids.** The integer key never appears in a
  URL, a body, an export or a log. `/c/{token}` is the one capability-shaped
  exception.
- **Pagination is by signed cursor**, never offset.
- **Unknown query parameters are 400**, never ignored.
- **Out of scope is 404.** Scope is compiled into the `WHERE`; 403 is for a
  row you can see but may not act on, and is audited
  ([ADR 0004](../docs/decisions/0004-scope-in-the-where-clause.md)).
- **Unknown enumerated values are 422** with the choices named, through
  `cmp.validation.choice()` ([ADR 0008](../docs/decisions/0008-unknown-choices-are-422.md)).
- **One error shape:** `{"error": {"code", "message", "field", "request_id"}}`.

## Testing

```bash
uv run pytest                        # everything; integration and security need PostgreSQL and Redis
uv run pytest tests/unit             # pure functions, no I/O
uv run pytest tests/integration      # real datastores; rolls back per test
uv run pytest tests/security         # BOLA, BFLA, mass assignment, CSRF, rate limits, the matrix
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

The project state machine is asserted over every (from, to, role)
combination, not only the legal ones; the rights state machine likewise. Do
not run pytest while a Playwright suite is running against the same database:
both write audit rows, and the chain's lock turns them into timeouts. More in
[../docs/operations/testing.md](../docs/operations/testing.md).

## Operations

| Endpoint | Purpose |
|---|---|
| `GET /health` | liveness; touches nothing |
| `GET /ready` | readiness: database, Redis, migrations current; 503 when not |
| `GET /metrics` | Prometheus; never templated by consent token |
| `GET /audit/verify` | walks the hash chain and names the first row that does not verify |

Scheduled work (Celery beat, exactly one instance):

| Task | Schedule | Idempotent because |
|---|---|---|
| `expire_consent_links` | every 15 min | matches only rows still active |
| `apply_retention_lapse` | 02:00 | matches only `disposition = 'active'` |
| `sweep_rights_requests` | 02:30 | closes only unverified requests past the window; marks only tickets past due |
| `verify_audit_chain` | 03:00 | read-only |
| `flag_unmapped_assets` | every 6 h at :30 | reconciliation only; flags, never deletes |

Celery runs with `acks_late` and `reject_on_worker_lost`, so delivery is
at-least-once and every task is idempotent; imports upsert on
`(source, source_reference)`.

Operator scripts:

```bash
uv run python scripts/seed.py          # development data; refuses outside local/test
uv run python scripts/create_admin.py  # the bootstrap administrator; refuses if one exists
uv run python scripts/reset_dev.py     # drop and rebuild the configured database; local/test only, asks first
uv run python scripts/healthcheck.py   # post-deploy checks; read-only, safe in production
uv run python scripts/db.py [table|SQL] # read the database; every statement rolled back
```

## Layout

```
src/cmp/
  main.py            ASGI entrypoint
  bootstrap/         assembly: factory, lifespan, middleware, routers, container
  api/
    routers/v1/      audit, auth, consents, dashboard, delegations, exchange, me,
                     notices, projects, registry, rights, system, users
    routers/public/  consent (the /c/{token} flow), rights (the public pages)
    dependencies/    sessions, csrf, authentication, authorization, paging, filters
    middleware/      request context, security headers, body limit, access log
    errors/          one error contract
  auth/              identity, authentication (password, MFA, OTP), authorization
                     (roles, resources, scopes, evaluator, policy), sessions, rate limits
  domain/            one package per aggregate; the only layer that writes:
                     projects, notices, consent, exchange, registry, users, rights, audit, shared
  validation/        constrained types, choice(), contact normalisation
  db/                pool, SQL helpers, one repository per table cluster
  infrastructure/    email, sms, storage, outbound HTTP; swappable adapters
  core/              config, enums, constants, permissions, security, errors, pagination
  tasks/             Celery: authentication, notifications, maintenance, exchange, rights

migrations/          22 raw-SQL Alembic revisions (docs/database/migrations.md)
tests/               unit/, integration/ (with enforcement/, database/, auth/), security/
scripts/             seed, create_admin, reset_dev, healthcheck, db
docs/                architecture, security, database, operations (this service's own)
docker/              Dockerfile, docker-compose.yml, nginx
openapi.json         the generated API document; regenerate after a route change
```

### Where to start reading

| Question | Where |
|---|---|
| How is the app assembled? | `bootstrap/application.py` |
| What happens to a request? | [docs/architecture/request-lifecycle.md](docs/architecture/request-lifecycle.md) |
| Who may do what? | `core/permissions.py`, then [../docs/domain/roles-and-access.md](../docs/domain/roles-and-access.md) |
| How does a project move state? | `domain/projects/state_machine.py` |
| How does a rights request work? | [docs/architecture/rights.md](docs/architecture/rights.md) |
| What makes the audit trail evidence? | [docs/security/audit.md](docs/security/audit.md) |
| Why no ORM? | [docs/architecture/overview.md](docs/architecture/overview.md) |
