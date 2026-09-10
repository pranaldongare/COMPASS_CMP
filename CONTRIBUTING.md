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
- Never commit `.env`, `.env.local`, `var/outbox.log`, `.auth/`, build
  output, or anything under `cmp_frontent/` (a leftover directory of ignored
  files).

## Before you open a pull request

```bash
cd cmp_backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
cd cmp_internal_ui && npm run verify
cd cmp_public_ui && npm run verify
```

Run the browser suites when you touched a page or a route they cover, one at
a time and never alongside pytest:

```bash
cd cmp_internal_ui && npx playwright test --workers=1
cd cmp_public_ui && npx playwright test --workers=1
```

[docs/operations/testing.md](docs/operations/testing.md) says what each suite
covers and how to read a failure.

## Rules a review will hold you to

**Only a service writes.** A router parses and calls a service; a repository
runs SQL. A write anywhere else bypasses the audit recorder. The layer
rules are in
[cmp_backend/docs/architecture/layers.md](cmp_backend/docs/architecture/layers.md).

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

1. `uv run alembic revision -m "what it does"` and write the SQL by hand,
   both directions.
2. If the change adds a rule, add it as a constraint or trigger and add a
   test under `tests/integration/enforcement/` that breaks it with raw SQL.
3. Prefer a `BEFORE INSERT` trigger to a `NOT VALID` CHECK for a rule that
   legacy rows would fail; the latter is re-validated on every later update.
4. If it adds an enumeration, add the `StrEnum` in `core/enums.py`; the
   parity test compares the two.
5. Run `alembic downgrade -1` and `upgrade head` before you commit.
6. Add the revision to
   [migrations.md](cmp_backend/docs/database/migrations.md).

## Changing the API

1. Update the response model; the repository's select list; the service.
2. Regenerate `cmp_backend/openapi.json` (the command is in
   [docs/architecture/api.md](docs/architecture/api.md)).
3. In each portal that uses the route, `npm run api:check` regenerates the
   schema types and fails on a mismatch with the hand-curated types.
4. If the route is new, add its resource to the matrix and a case to the
   security suite.

## Documentation

A change to behaviour changes a document. The map in
[docs/README.md](docs/README.md) says which; the rule of thumb is: a
workflow change updates the domain page, a schema change updates
migrations.md and the domain model, a setting updates configuration.md and
`.env.example`, a decision that would be expensive to reverse gets an ADR.
Add a line to [CHANGELOG.md](CHANGELOG.md) under Unreleased.

## Continuous integration

A GitHub Actions workflow lives at `cmp_backend/.github/workflows/ci.yml`:
lint, format, `mypy`, migrations up-down-up, the three pytest suites with
coverage, a dependency audit and a static security scan. Two things to know:

- GitHub only runs workflows from `.github/workflows/` at the repository
  root, so on this monorepo the file is not currently triggered. Moving it
  to the root, with `working-directory: cmp_backend`, is the fix, and adding
  the two portals' `npm run verify` is the obvious next step.
- Until then, the commands above are the gate, run locally.
