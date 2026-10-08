# 5. Adding a feature, end to end

The order work goes in, from a new table to a tested, documented endpoint.
Not every feature needs every step; skip what does not apply. Commands run
from `backend/api` with its virtualenv active unless they say otherwise.

## 1. The table - a migration

Alembic's default names a revision with a random hex id. This repository
numbers them, so give the next number yourself:

```bash
alembic revision --rev-id 0050 -m "what it does"
```

Then rewrite the generated file in house style
([the database](04-database.md#what-a-migration-looks-like)): a docstring
saying why, `Revises: 0049`, the SQL in `UPGRADE` and `DOWNGRADE` strings,
and `op.execute()`. Drop the generated `sqlalchemy` import if you do not use
it. In the SQL:

- `<entity>_id serial PRIMARY KEY` and `<entity>_uuid uuid NOT NULL UNIQUE DEFAULT gen_random_uuid()`
- `timestamptz` stamps named for the event, and a `*_by` beside any stamp a
  person sets, tied together with a named CHECK
- named CHECKs for the rules, indexes for the lookups, partial unique
  indexes for state-dependent uniqueness
- an append-only trigger (`EXECUTE FUNCTION cmp_append_only()`) if the table
  is evidence; a `cmp_touch_updated_at()` trigger if it has `updated_at`
- a real downgrade

Stop the API and the worker - pooled connections can hold locks your DDL
waits behind - then:

```bash
alembic upgrade head
alembic downgrade -1 && alembic upgrade head    # prove the downgrade
```

A new enum type needs its `StrEnum` in `src/cmp/core/enums.py` and an entry in
`BY_PG_TYPE`; the parity test fails otherwise.

## 2. Personal data, if the table holds any

Follow [adding a personal field](../dkms/adding-a-personal-field.md). In
short:

1. Make the column `text`, with `<column>_hash` and an `*_indexed` CHECK if
   it is looked up, and `<column>_ngrams` if it is searched by name.
2. Add it to `ENCRYPTED_FIELDS` (and `BLIND_INDEXED` / `NGRAM_INDEXED`) in
   `infrastructure/dkms/fields.py`.
3. Add the table to `scripts/reseal.py`.
4. Add the field to both portals' `lib/dkms/field-types.ts`.

## 3. The repository

`src/cmp/db/repositories/<area>.py`. Functions take `conn`, bind every value,
and use the helpers in `db/sql.py`:

- `seal()` and `index_of()` for personal columns.
- The area's scope predicate in the WHERE clause of every read, so an
  out-of-scope row is a 404.
- `keyset_clause` and `build_page` for a list, with `LIST_SORTS` naming the
  sortable fields.

## 4. The service

`src/cmp/domain/<area>/service.py` holds the rules. Raise from
`core/errors.py` with a specific `code=` the frontends can switch on. Write
through the repository and call `audit.record(conn, ...)` on the same
connection:

- add the entity type to `ENTITY_TYPES` and the event to `Event` in
  `domain/audit/service.py`;
- put no personal data in the audit detail.

A message about the change goes through `dispatch_optional` so it is sent
only after the commit. A new message is a `Message` and a `Junction` in the
catalogue, `core/messages.py` - and in `COPYABLE` if the office may copy it to
somebody, or `ATTACHABLE` if it may carry a file, only where that is allowed.
Its task sends it only through `deliver()` (`infrastructure/messaging`),
never a transport directly. `docs/tools/generate-email-docs.py` then writes
it into `docs/email/messages.md` and the module's page in
`docs/notifications/`; `--check` says when they are stale.

## 5. The route

`src/cmp/api/routers/v1/<area>.py` (or `public/` for an unauthenticated
form):

- Request model subclasses `Schema`; response model subclasses `Out`;
  lists return `Page[T]`.
- Use the constrained types in `schemas/common.py` and `validation/`, and
  `choice()` for enums.
- Put a guard in the signature: a `RequireRole` alias, or
  `RequireResource(...)`. A new resource needs:
  - its name in `auth/authorization/resources.py`;
  - a row in `core/permissions.py` `MATRIX`;
  - an entry in `NAV_BY_ROLE` if it is a new console section.
- Open `async with transaction() as conn:` for a write, or `connection()` for
  a read, and call one service function.

A new router module is exported in `api/routers/v1/__init__.py` and added to
`ROUTERS` in `api/routers/__init__.py`.

## 6. Tests

| Where | For |
|---|---|
| `tests/unit/` | Pure logic - validators, state machines |
| `tests/integration/` | Services and repositories against the database, each test in a transaction that is rolled back; rules the database enforces go in `tests/integration/enforcement/` |
| `tests/security/` | Who may and may not call the route; `test_bfla.py` is written against the matrix |
| `tests/http/` | The route over HTTP, if it carries personal data - `test_zz_coverage.py` fails if a personal-data route is never called |

```bash
ruff check . && ruff format --check . && mypy src && pytest --ignore=tests/http
POSTGRES_DB=cmp_http pytest tests/http      # commits rows: use the scratch database
```

The key service must be running. Integration tests share the development
database, so a row you created by hand can collide with a fixture on a
unique index; see [testing](../operations/testing.md).

A task is not rolled back with a test's rows: queued through Celery, it would
run against the live worker. So the root fixture `_no_real_tasks`
(`tests/conftest.py`) stops every `apply_async` in every test. A test that
needs to see what was sent captures the dispatch itself, with a `sent` or
`queued` fixture (`tests/integration/conftest.py` has `sent`); one that
simulates a broker outage patches the broker, which the fixture leaves
alone.

## 7. The generated documents

```bash
# the API description
python -c "from cmp.main import app; import json; json.dump(app.openapi(), open('openapi.json','w'), indent=2)"

# each portal's types, with the API running
cd frontend/console && npm run api:check
cd frontend/portal  && npm run api:check

# the API reference, and the personal-data tables if the route carries any
python3 docs/tools/generate-api-docs.py
python3 docs/tools/pii-fields-and-endpoints.py

# the messages, if a message was added or changed
backend/api/.venv/bin/python docs/tools/generate-email-docs.py

# the schema reference, from a scratch database at head
createdb -h 127.0.0.1 -U cmp cmp_ref && POSTGRES_DB=cmp_ref alembic upgrade head
python3 docs/tools/generate-schema-docs.py --database cmp_ref

python3 docs/tools/check-links.py
```

`docs/reference/access-control/` is kept by hand: add the endpoint to
`endpoint_permissions.json` and its module page. A new table goes in
`MODULES` in `docs/tools/generate-schema-docs.py` and in the chain table in
[migrations](../database/migrations.md).

## 8. The words

- The page in `docs/` that describes the behaviour changes in the same commit.
- A choice someone could reasonably have made differently gets an ADR in
  [decisions/](../decisions/README.md).
- A line in the [changelog](../../CHANGELOG.md).
