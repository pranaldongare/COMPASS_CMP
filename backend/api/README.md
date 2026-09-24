# CMP backend

The API of the consent management platform: FastAPI 0.141 on Python 3.12,
PostgreSQL 16, Redis 7, Celery 5. 252 endpoints over 35 tables, every query
hand-written SQL over psycopg 3, every migration raw DDL. Personal fields are
sealed through the key service in [`../dkms`](../dkms) before they reach a
table. The repository-wide documentation is under
[docs/](../../docs/README.md); this README is the backend's own front door.

## Running it

Two datastores. If you have PostgreSQL 16 and Redis 7 already, point `.env` at
them. If not, the one Docker file in this repository starts exactly those two
and nothing else:

```bash
docker compose -f dev-services.yml up -d        # PostgreSQL + Redis, and only those
```

The key service next, because with `DKMS_ENABLED=true` (as in
`.env.example`) every personal field the seed writes is sealed through it.
Start it as [its README](../dkms/README.md) says; it listens on
`http://127.0.0.1:32688`, which is the `DKMS_URL` in `.env.example`.

Then a virtualenv, with pip:

```bash
python3.12 -m venv .venv
. .venv/bin/activate                # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt # the runtime, the tools, and this package (editable)

cp .env.example .env                # PUBLIC_BASE_URL and CONSOLE_BASE_URL to the two portals; DKMS_URL to the key service
alembic upgrade head                # 32 migrations: 35 tables, triggers, grants, the lookup hashes
python scripts/seed.py              # one coherent world: a user per role, processors, sources, sites, a project through to approved, a live link

python -m cmp --port 8000
celery -A cmp.tasks.app worker -Q high_priority,email,documents,reports,notifications,default -l info --pool=solo
celery -A cmp.tasks.app beat -l info
```

The worker is a separate process with its own environment. It opens the
sealed address of every message it sends, so `DKMS_ENABLED` and `DKMS_URL`
must be right for it as well as for the API. `BLIND_INDEX_KEY` must equal the
key service's `DKMS_HASH_KEY`
([configuration.md](../../docs/operations/configuration.md#the-key-service)).

Every command after `activate` assumes the virtualenv is active. `requirements.txt`
is the runtime alone, pinned to exact versions; `requirements-dev.txt` adds the
suite, the linters and the type checker. To change a dependency, edit the line,
`pip install -r requirements-dev.txt` again, and run the suite.

`http://127.0.0.1:8000/docs` is the interactive reference outside production.

> **Why `python -m cmp` and not `uvicorn cmp.main:app`?** psycopg's async
> mode cannot run on Windows' `ProactorEventLoop`, and uvicorn builds its loop
> through a `loop_factory` that bypasses the policy. The module entrypoint
> supplies the loop. On Linux the two are equivalent; a deployment would run
> `gunicorn cmp.main:app` with uvicorn workers.

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

**There is no ORM, deliberately** ([ADR 0001](../../docs/decisions/0001-no-orm-raw-sql.md)).
The migrations are the schema; a model layer would be a second copy that
drifts.

**Only services write.** A router that writes bypasses `audit.record()`. The
audit row and the change it describes share one transaction, so a change
that rolled back leaves no audit row, and one that committed cannot be
missing one.

The layers in detail: [docs/architecture/layers.md](../../docs/architecture/layers.md)
and [dependency-rules.md](../../docs/architecture/dependency-rules.md). A request's
path: [request-lifecycle.md](../../docs/architecture/request-lifecycle.md).

## What the database enforces

The application refuses these first, to give a better error. The database
refuses them too, because "the application always calls the service layer"
is a claim about a codebase, and a codebase changes
([ADR 0002](../../docs/decisions/0002-evidence-enforced-in-the-database.md)).

| Guarantee | Mechanism |
|---|---|
| Consent evidence, disclosures, history and the audit log are append-only | trigger and revoked grant |
| Audit rows are hash-chained, in commit order | `cmp_audit_chain()`, position drawn inside the advisory lock; `GET /audit/verify` walks it |
| A published notice is frozen | `cmp_notice_freeze()` |
| The artefact carries the hash of the text served; served precedes action | `cmp_consent_coherent()`, `CHECK served_before_action` |
| One artefact superseded once, one root per person and notice | two partial unique indexes; capture also locks per pair |
| A consent is recorded against a serving the server witnessed | the serving record in Redis, required by `capture` |
| Bystanders may exist, visibly | nullable `consent_id` on `asset_consent` with a CHECK |
| Data categories are itemised (Rule 3(b)(i)) | `CHECK cardinality(...) >= 1` |
| Links only for approved projects | `cmp_link_coherent()` |
| A data principal and a nominee have a mobile; staff have an email | `BEFORE INSERT` triggers and a CHECK |
| No account or consent for a child; no consent from an unknown age | `cmp_is_minor(minor_until)`, checked by `cmp.domain.users.age` |

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
  ([ADR 0004](../../docs/decisions/0004-scope-in-the-where-clause.md)).
- **Unknown enumerated values are 422** with the choices named, through
  `cmp.validation.choice()` ([ADR 0008](../../docs/decisions/0008-unknown-choices-are-422.md)).
- **One error shape:** `{"error": {"code", "message", "field", "request_id"}}`.

## Testing

```bash
pytest                               # everything, tests/http included; all but unit need PostgreSQL, Redis and the key service
pytest tests/unit                    # pure functions, no I/O
pytest tests/integration             # real datastores; rolls back per test
pytest tests/security                # BOLA, BFLA, mass assignment, CSRF, rate limits, the matrix
POSTGRES_DB=cmp_http pytest tests/http   # every personal-data endpoint over HTTP; COMMITS, so a scratch database
ruff check . && ruff format --check . && mypy src
```

`tests/http` drives the application over HTTP and asserts that every
personal field leaves it sealed. It commits what it writes, so run it on a
scratch database (`createdb -h 127.0.0.1 -U cmp cmp_http`, then
`POSTGRES_DB=cmp_http alembic upgrade head`) and the rest with
`pytest --ignore=tests/http`.

The project state machine is asserted over every (from, to, role)
combination, not only the legal ones; the rights state machine likewise. Do
not run pytest while a Playwright suite is running against the same database:
both write audit rows, and the chain's lock turns them into timeouts. More in
[../docs/operations/testing.md](../../docs/operations/testing.md).

## Operations

| Endpoint | Purpose |
|---|---|
| `GET /health` | liveness; touches nothing |
| `GET /ready` | readiness: database, Redis, migrations current, key service reachable (`encryption`); 503 when not |
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
python scripts/seed.py                 # development data; refuses outside local/test
python scripts/create_admin.py         # the bootstrap administrator; refuses if one exists
python scripts/reset_dev.py            # drop and rebuild the configured database; local/test only, asks first
python scripts/healthcheck.py          # checks a running instance; read-only
python scripts/db.py [table|SQL]        # read the database; every statement rolled back
python scripts/reseal.py [--check] [--table T]   # seal plaintext left in sealed columns; --check only reports
```

`reseal.py` needs the key service and the table owner's role, and is
idempotent; when and how to run it is in the
[runbook](../../docs/operations/runbook.md#plaintext-in-a-sealed-column-scriptsresealpy).

## Layout

```
src/cmp/
  main.py            ASGI entrypoint
  bootstrap/         assembly: factory, lifespan, middleware, routers, container
  api/
    routers/v1/      audit, auth, consents, dashboard, delegations, exchange, me,
                     messages, notices, projects, registry, rights, system, users
    routers/public/  consent (the /c/{token} flow), rights (the public pages)
    dependencies/    sessions, csrf, authentication, authorization, paging, filters
    middleware/      request context, security headers, body limit, access log
    errors/          one error contract
  auth/              identity, authentication (password, MFA, OTP), authorization
                     (roles, resources, scopes, evaluator, policy), sessions, rate limits
  domain/            one package per aggregate; the only layer that writes:
                     projects, notices, consent, exchange, registry, users, rights,
                     messaging, audit, shared
  validation/        constrained types, choice(), contact normalisation
  db/                pool, SQL helpers, one repository per table cluster
  infrastructure/    email, sms, storage; messaging (the one path to a transport);
                     dkms (the key service client, the sealed-field map, the lookup hashes)
  core/              config, enums, constants, permissions, security, errors, pagination,
                     messages (every junction and its default words)
  tasks/             Celery: authentication, notifications, maintenance, exchange, rights

migrations/          32 Alembic revisions, raw SQL; 0028 and 0030 also backfill hashes in Python
tests/               unit/, integration/ (with enforcement/, database/, auth/), security/, http/
scripts/             seed, create_admin, reset_dev, healthcheck, db, reseal
dev-services.yml     PostgreSQL and Redis for development; the one Docker file
requirements*.txt    the runtime, pinned; and the tools on top of it
openapi.json         the generated API document; regenerate after a route change
```

### Where to start reading

| Question | Where |
|---|---|
| How is the app assembled? | `bootstrap/application.py` |
| What happens to a request? | [docs/architecture/request-lifecycle.md](../../docs/architecture/request-lifecycle.md) |
| Who may do what? | `core/permissions.py`, then [../docs/domain/roles-and-access.md](../../docs/domain/roles-and-access.md) |
| How does a project move state? | `domain/projects/state_machine.py` |
| How does a rights request work? | [docs/architecture/rights-module.md](../../docs/architecture/rights-module.md) |
| What makes the audit trail evidence? | [docs/security/audit.md](../../docs/security/audit.md) |
| Why no ORM? | [docs/architecture/api-internals.md](../../docs/architecture/api-internals.md) |
| How is personal data sealed? | `infrastructure/dkms/`, then [docs/dkms/README.md](../../docs/dkms/README.md) |
