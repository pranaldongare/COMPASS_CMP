# Contributing

How to make a change that lands. Read
[docs/README.md](docs/README.md) first if the platform is new to you; the
rules below assume you know what a consent artefact is and why it cannot be
edited.

## Branches and commits

- Work on a branch off `refactor/frontend-architecture` (the integration
  branch today) and open a pull request against it.
- One change per commit, in the imperative, saying what the change does for
  someone: `feat(rights): send a returned ticket back`. Prefixes in use are
  `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `build`, with the area
  in brackets (`api`, `web`, `rights`, `auth`, `console`, `registry`).
- Never commit `.env`, `.env.local`, `var/outbox.log`, `.auth/` or build
  output.

## Before you open a pull request

```bash
cd backend/api && . .venv/bin/activate && ruff check . && ruff format --check . && mypy src && pytest --ignore=tests/http
cd backend/api && POSTGRES_DB=cmp_http .venv/bin/pytest tests/http
cd backend/dkms && . .venv/bin/activate && ruff check app tests && mypy app && pytest tests
cd frontend/console && npm run verify
cd frontend/portal && npm run verify
```

The backend suites need the key service running. `tests/http` commits
what it writes, so it runs on a scratch database (`cmp_http`) rather than
the development one; setting that up is two commands in
[testing.md](docs/operations/testing.md#backend).

Run the browser suites when you touched a page or a route they cover, one at
a time and never alongside pytest:

```bash
cd frontend/console && npx playwright test --workers=1
cd frontend/portal && npx playwright test --workers=1
```

[docs/operations/testing.md](docs/operations/testing.md) says what each suite
covers and how to read a failure.

## Rules a review will hold you to

**Only a service writes.** A router parses and calls a service; a repository
runs SQL. A write anywhere else bypasses the audit recorder. The layer
rules are in
[docs/architecture/layers.md](docs/architecture/layers.md).

**Evidence is never edited.** A correction to a consent, a notice, a
disclosure or an audit row is a new row. If a change needs to touch an
evidence table in place, it is the wrong change.

**Scope goes in the query.** A new list endpoint compiles the caller's scope
into its `WHERE`; a new resource is a row in `core/permissions.py`. Out of
scope answers 404.

**No integer id on the wire.** Paths, bodies, exports and logs use the uuid.

**Enumerated input goes through `choice()`.** An unknown value must be a 422
with the choices named, never a 500.

**Neutral answers stay neutral.** Registration, code requests and the public
rights form must not reveal whether a contact is known.

**The frontends hold no copy of the matrix or the state machine.**
Navigation comes from `/auth/me`; transition controls come from the
transitions endpoint.

**Nothing 4xx is retried** by the clients, and mutations never are.

## Changing the schema

1. `alembic revision -m "what it does"` and write the SQL by hand,
   both directions.
2. If the change adds a rule, add it as a constraint or trigger and add a
   test under `tests/integration/enforcement/` that breaks it with raw SQL.
3. Prefer a `BEFORE INSERT` trigger to a `NOT VALID` CHECK for a rule that
   legacy rows would fail; the latter is re-validated on every later update.
4. If it adds an enumeration, add the `StrEnum` in `core/enums.py`; the
   parity test compares the two.
5. Run `alembic downgrade -1` and `upgrade head` before you commit.
6. Add the revision to
   [migrations.md](docs/database/migrations.md).
7. Regenerate the database reference from a scratch database built from
   the chain, and commit what changed under `docs/reference/database/`:

   ```bash
   cd backend/api && . .venv/bin/activate      # psycopg comes from here
   createdb -h 127.0.0.1 -U cmp cmp_ref && POSTGRES_DB=cmp_ref alembic upgrade head
   cd ../.. && python docs/tools/generate-schema-docs.py --database cmp_ref
   ```

   A database with sealed rows makes 0028 and 0030 call the key service; a
   fresh `cmp_ref` has none, so it does not.

If the change adds or moves a column that holds personal data, it also has
to be sealed, hashed where it is looked up, resealed on existing rows, and
proved by the HTTP suite. The steps are in
[adding-a-personal-field.md](docs/dkms/adding-a-personal-field.md); missing
one either fails `tests/http` or leaves plaintext at rest.

## Changing the API

1. Update the response model; the repository's select list; the service.
2. Regenerate `backend/api/openapi.json` (the command is in
   [docs/architecture/api.md](docs/architecture/api.md)).
3. In each portal that uses the route, `npm run api:check` regenerates the
   schema types and fails on a mismatch with the hand-curated types.
4. If the route is new, add its resource to the matrix and a case to the
   security suite.
5. If it carries personal data, regenerate
   [pii-fields-and-endpoints.md](docs/domain/pii-fields-and-endpoints.md)
   (`python3 docs/tools/pii-fields-and-endpoints.py`) and call the route from
   `tests/http`. `test_zz_coverage.py` classifies every route in
   `openapi.json` with `docs/tools/personal-data-scan.py`, and fails for a
   personal-data route the suite never called, and for one that answered
   with a sealed field that the scan does not count.

## Documentation

A change to behaviour changes a document. The map in
[docs/README.md](docs/README.md) says which; the rule of thumb is: a
workflow change updates the domain page, a schema change updates
migrations.md, the domain model and the generated database reference, a
setting updates configuration.md and the `.env.example` of the process
that reads it, a decision that would be expensive to reverse gets an ADR.
Add a line to [CHANGELOG.md](CHANGELOG.md) under Unreleased.

## Continuous integration

`.github/workflows/ci.yml` runs on pushes to `main` and
`refactor/frontend-architecture` and on pull requests, and currently fails:
it still names `cmp_backend` and the old portal directories and installs
with `uv`. Its replacement, [`docs/tools/ci.yml.proposed`](docs/tools/ci.yml.proposed),
has not been applied; [ci-paths.md](docs/tools/ci-paths.md) says why.

Until then, the commands above are the gate. The proposed workflow adds: the
migration chain up, down and up; a check that the committed `openapi.json`
matches what the code generates (regenerate it when you change a route);
both portals' production builds; and dependency, static and secret scans.
It has no job for `backend/dkms` and starts no key service, so it does not
yet run the key service's suite or pass `tests/http`. Browser suites are not
in CI and stay a local step.

## Rules the review added

Three habits, from the September 2026 review
([disposition](docs/reviews/2026-09-10-implementation-review.md)):

- **If two requests can carry the same thing, write the race.** A code, a
  first capture, a token: the test opens a second connection or races
  coroutines. One caller at a time proves nothing about single use.
- **If a comment says the server holds a fact, the test checks the server
  held it**, not that the client echoed it.
- **Side effects go through `dispatch_optional` inside the transaction** and
  run after it commits. Never call `apply_async` from a service.
