# Testing

Four suites, each answering a different question. Counts are as of
2026-09-10 and change with every feature; the commands do not.

| Suite | Where | Runs against | Count |
|---|---|---|---|
| Backend unit | `cmp_backend/tests/unit` | nothing; pure functions | 360 |
| Backend integration | `cmp_backend/tests/integration` | real PostgreSQL and Redis | 203 |
| Backend security | `cmp_backend/tests/security` | the ASGI app with real datastores | 343 |
| Portal unit | `src/**/*.test.ts*` in each portal | vitest with MSW | 139 console, 108 portal |
| Browser | `e2e/` in each portal | the running stack in a real browser | 48 console and 20 portal tests, run across five Playwright projects |

## Backend

```bash
cd cmp_backend
uv run pytest                    # everything
uv run pytest tests/unit         # no datastores needed
uv run pytest -k rights          # by name
uv run pytest --cov              # with coverage
```

**Unit** tests are the state machines over every (from, to, role)
combination, the permission matrix, the clock arithmetic, the crypto
primitives, contact normalisation, `choice()`.

**Integration** tests use the database in `.env` and roll back after every
test; the `seeded` fixture builds the same world as `scripts/seed.py`, and
every integration test gets a Redis connection whether it asks or not,
because recording a consent through the service needs one. Three kinds of
test deserve attention:

- `enforcement/` bypasses the service layer and writes raw SQL to prove
  each trigger, CHECK, index and revoked grant refuses what it should.
- `database/` compares the Postgres enumerations to the Python ones in both
  directions and checks the migration chain.
- The concurrency tests (`enforcement/test_audit_chain_position.py`,
  `test_consent_serving.py`, `auth/test_otp_atomic.py`) open a second
  connection or race coroutines for real. They exist because every
  confirmed finding of the September 2026 review was invisible to a
  one-caller-at-a-time suite; see
  [the review disposition](../reviews/2026-09-10-implementation-review.md).

Rate-limit buckets live in Redis under `rate:*`; tests that need a fresh
bucket clear their own through the `redis_conn` fixture rather than waiting
an hour.

**Security** tests walk the matrix: every resource for every role, uuids
across scopes expecting 404, mass assignment, CSRF, lockout, the neutral
answers, the second factor. `test_matrix_integrity.py` holds the invariants
the matrix itself must keep.

Static checks:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

All three are clean as of 2026-09-10; anything reported is new.

## Portal unit tests

```bash
cd cmp_internal_ui && npm run verify   # typecheck, lint, vitest
cd cmp_public_ui && npm run verify
```

Node 22. They cover what a review cannot see: error classification, the
formatting of values a data principal reads, the zod schemas mirroring the
API's validation, and the contract between the hand-curated types and the
generated OpenAPI schema (`npm run api:check` regenerates that schema from a
running API and type-checks against it).

## Browser tests

```bash
cd cmp_internal_ui && npx playwright test --workers=1
cd cmp_public_ui && npx playwright test --workers=1
E2E_CONSENT_TOKEN=<token> npx playwright test --workers=1   # portal: includes the consent journey
```

The stack must be running: API, worker, beat, and the portal under test.
Codes are read from `cmp_backend/var/outbox.log` by `e2e/support/outbox.ts`.

The console suite has five projects. `setup` signs in every role once, with
its emailed code, and saves the sessions; `chromium` and `mobile` run the
specs (auth, controls, detail pages, forms, links, navigation coverage,
notice upload, routing); `localhost-cookies` re-runs the auth spec on the
other origin; `visual` takes the screenshots. The portal suite covers the
consent flow, sign-up with two codes, the rights pages including nomination
acceptance, and the data principal's own pages. `expectNoSidewaysScroll` in
`e2e/support/layout.ts` is asserted on every page the mobile project visits.

### Rules for running them

- **Serially.** The public surfaces are rate limited per address and per
  contact, and parallel workers share one address.
- **Never alongside pytest** on the same database. Both write audit rows,
  and the chain's advisory lock turns the two into timeouts that look like
  application bugs.
- **Clear the rate buckets first** if a previous run was interrupted:
  `rate:*` in Redis db 0.
- **Re-run `setup` after a pause.** Sessions idle out after thirty minutes,
  and a stale saved session fails every spec at once with a redirect to
  sign-in.
- **The seed must be present.** The routing spec expects the CIT (DCO) and
  SE (RCO) sites; `scripts/seed.py` builds them.

## Reading a failure

- A backend 500 in a browser test shows as a dropped proxy connection. Read
  the API log for the `request_id` the page shows.
- A 422 with `choices` in the message is the enumerated-value guard doing its
  job; fix the input.
- A 429 in a suite means the bucket from a previous run is still full.
- An audit-chain break reported by `verify_audit_chain` during a test run
  means two suites shared a database.

## What is not covered

- The email and SMS transports are exercised only through the outbox; SMTP
  and the SMS provider are not tested here.
- Load. The advisory locks on the audit chain and per (person, notice)
  serialise writes; their throughput has not been measured.
- The HTTP SMS gateway: the transport is unit-tested by shape only, since no
  gateway exists in a test environment.

## Continuous integration

`.github/workflows/ci.yml` at the repository root runs on every push to
`main` and the integration branch and on every pull request: backend lint,
format and `mypy`; migrations up, down and up; a diff of the committed
`openapi.json` against the one the code generates; the three pytest suites
with coverage; both portals' typecheck, lint, vitest and production build; a
dependency audit, a static security scan and a secret scan; and the API
image built, scanned, and started without a database to assert that it
exits non-zero rather than serving. Browser tests are not in CI yet; they
need the whole stack and the outbox, and run locally as above.
