# 1. Codebase tour

All paths on this page are under `backend/api/src/cmp/` unless they say
otherwise.

## The packages

| Package | Its job | Look here first |
|---|---|---|
| `main.py`, `__main__.py` | The ASGI target `cmp.main:app`; `python -m cmp --port 8000` runs uvicorn | - |
| `bootstrap/` | Builds the application: `create_app`, the lifespan, middleware, router mounting, adapter warm-up | `bootstrap/application.py` |
| `api/` | The HTTP edge. Routers (`routers/v1/*` for signed-in callers, `routers/public/*` for links and forms), dependencies (session, CSRF, principal, guards, paging, filters), middleware, and the error handlers | `api/routers/v1/projects.py` |
| `schemas/` | The base classes every request and response model uses: `Schema` (requests, unknown fields refused), `Out` (responses, unknown fields dropped), `Page[T]` | `schemas/common.py` |
| `validation/` | Constrained types (`ShortText`, `Mobile`, `DateOfBirth` …), `choice()` for enum fields, contact normalisation | - |
| `auth/` | Who you are and what you may do: password and MFA, one-time codes, password reset, sessions in Redis, roles, the authorisation evaluator, rate limiting and lockout | `auth/authentication/service.py` |
| `domain/` | One package per area - `projects`, `notices`, `consent`, `exchange`, `rights`, `registry`, `users`, `delegations`, `messaging`, `audit`. The business rules and state machines live here | `domain/projects/service.py` |
| `db/` | The connection pool and `transaction()`, SQL helpers, Redis, and `repositories/` - thirteen modules of hand-written SQL | `db/pool.py`, `db/sql.py` |
| `infrastructure/` | Adapters to the outside: email and SMS transports, file storage, message delivery (`deliver()`), and the key-service client that seals and opens personal fields | `infrastructure/dkms/` |
| `core/` | Settings, the exception classes, the permission matrix and navigation, pagination cursors, the request context, enums, token and hash helpers | `core/permissions.py`, `core/errors.py` |
| `tasks/` | The Celery app, the dispatch helpers, and the tasks: notifications (codes, receipts, tickets) and nightly maintenance | `tasks/app.py`, `tasks/dispatch.py` |

Next to `src/` in `backend/api` you will find `migrations/` (the schema, see
[the database](04-database.md)), `scripts/` (seeds, reset, reseal, an admin
bootstrap, a read-only DB inspector), `tests/` (`unit`, `integration`,
`security`, `http`), and `openapi.json`, generated from the running code.

The key service is a separate small FastAPI app in `backend/dkms`. The two
Next.js apps are `frontend/console` (staff) and `frontend/portal` (data
principals).

## Which layer may call which

The intended direction, from
[dependency rules](../architecture/dependency-rules.md):

```
bootstrap → api → auth / tasks → domain → db → infrastructure → validation → core
```

- `core` imports nothing else from the application; everything may import it.
- A router talks to a service; a service talks to repositories; a repository
  talks to the database and, for sealing, to `infrastructure/dkms`.
- Nothing in `domain` or `db` knows about HTTP.

**How it is kept:** by review. There is no import-linter; the pre-commit hooks
are ruff, mypy and the unit tests. Two checks run at import time:
`auth/authorization/permissions.py` refuses to load if the resource roster and
the permission matrix disagree, and `api/errors/mapping.py` refuses to load if
an exception class in `core/errors.py` lacks a status or code.

The direction is not perfectly kept today - some routers write through
repositories and record audit rows themselves, and a few services import from
`auth` and `tasks` inside functions. [Known gaps](06-known-gaps.md) lists
them. Follow the rule in new code; do not copy the exceptions.

## Where to find things

| You want | Look in |
|---|---|
| The URL for a feature | `api/routers/v1/<area>.py` - the request and response models are defined in the same file |
| The rule behind a refusal | `domain/<area>/service.py` |
| The SQL | `db/repositories/<area>.py` |
| Who may call a route | the guard in the route signature, and `core/permissions.py` (`MATRIX`, `NAV_BY_ROLE`) |
| A status code and error code | `core/errors.py` |
| Which fields are personal | `infrastructure/dkms/fields.py` (`ENCRYPTED_FIELDS`, `BLIND_INDEXED`, `NGRAM_INDEXED`) |
| A table's shape | the migration that created it, or the generated [table reference](../reference/database/table_reference.md) |
| A setting and its default | `core/config.py`, documented in [configuration](../operations/configuration.md) |
| Every endpoint and who may call it | [API reference](../reference/api/README.md) and [access control](../reference/access-control/README.md) |
