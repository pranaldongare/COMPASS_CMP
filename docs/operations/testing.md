# Testing

Seven suites, each answering a different question. Counts are as of
2026-09-24 and change with every feature; the commands do not.

| Suite | Where | Runs against | Count |
|---|---|---|---|
| Backend unit | `backend/api/tests/unit` | nothing; pure functions | 511 |
| Backend integration | `backend/api/tests/integration` | real PostgreSQL, Redis and key service | 296 |
| Backend security | `backend/api/tests/security` | the ASGI app with real datastores | 367 |
| Backend HTTP | `backend/api/tests/http` | the ASGI app over HTTP, real datastores and key service; **commits** | 69 |
| Key service | `backend/dkms/tests` | the service in-process; nothing else | 55 |
| Portal unit | `src/**/*.test.ts*` in each portal | vitest with MSW | 174 console, 133 portal |
| Browser | `e2e/` in each portal | the running stack in a real browser | 190 console and 71 portal test runs across the Playwright projects |

### Which suites need the key service

The backend suites read `backend/api/.env`, where `DKMS_ENABLED=true`. With
it on, every write of a personal column goes to the key service at
`DKMS_URL`, so the integration, security and HTTP suites need it running.
Two suites need it on, not merely reachable:
`tests/http` asserts that every personal field leaves the API as `SE::…`,
and `tests/integration/test_search_over_sealed_names.py` asserts a name is
stored sealed. The unit suite switches the setting per test where it
matters and needs nothing running. The key service's own suite needs
nothing either. The browser suites need it for the pages to open what they
are served.

## Backend

```bash
cd backend/api
pytest                           # everything, tests/http included - see below
pytest tests/unit                # no datastores needed
pytest -k rights                 # by name
pytest --cov                     # with coverage
```

Plain `pytest` runs `tests/http` too, and that suite **commits** its rows
into whatever database `.env` names. Run against the development database
`cmp` often, and its registers fill with test processors and people, seeded
rows fall off the first page of a list, and the browser suites start
failing. To keep the development database clean, run the HTTP suite on a
scratch database and the rest without it:

```bash
createdb -h 127.0.0.1 -U cmp cmp_http          # once
POSTGRES_DB=cmp_http alembic upgrade head      # after every new migration
POSTGRES_DB=cmp_http pytest tests/http
pytest --ignore=tests/http                     # unit, integration, security on cmp
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

**HTTP** tests (`tests/http/`) drive the whole application over HTTP -
`httpx` on the ASGI app, the real database and Redis, a session minted per
role - and are the proof that personal data leaves the API sealed. Every
response passes `contract.call()`: each field named in `contract.SEALED` is
`SE::…` or null, nothing under a contact's name looks like an address, and
the (method, path) is recorded. Three tests at the end (`test_zz_coverage.py`)
close the loop: every one of the 159 endpoints the documentation lists as
carrying personal data was called during the run; every endpoint that
answered with a sealed field is in that list; and every sealed column in the
database holds only ciphertext after everything the suite wrote. Adding an
endpoint that carries personal data means adding it to the suite, or the
build fails.

Two things about these tests are unlike the integration tier. They **commit**:
the application owns its connections, so nothing is rolled back, and every
run leaves a world behind - a project, a processor, a source, people named
`*@http-suite.test` and mobiles under `+9198765`. Against the shared
development database that accumulates (a hundred runs is a hundred
processors on the registry's second page); the scratch database above is
the answer.

And they **touch the public forms**, which limit by address per hour; the
suite drops the loopback address's `rate:*_ip:*` buckets when it starts, and
nobody else's. `.ledger.json` beside the tests is a copy of the run's ledger
for reading afterwards, not an input: the coverage test reads the in-process
set, so a stale file cannot make a missing endpoint look covered.

Static checks:

```bash
ruff check . && ruff format --check . && mypy src
```

All three are clean as of 2026-09-17; anything reported is new.

## Key service

```bash
cd backend/dkms && . .venv/bin/activate      # requirements-dev.txt installed
pytest tests                                 # 55 tests, nothing running needed
ruff check app tests && mypy app
```

`test_provider.py` covers the envelope, the type bound into it, tampering
and retired keys; `test_searchable.py` the exact hashes and the n-grams,
including the normalisation the platform's `cmp.infrastructure.dkms.blind`
also applies; `test_api.py` the HTTP contract, the record limit and the
refusals.

## Portal unit tests

```bash
cd frontend/console && npm run verify   # typecheck, lint, vitest
cd frontend/portal && npm run verify
```

Node 22. They cover what a review cannot see: error classification, the
formatting of values a data principal reads, the zod schemas mirroring the
API's validation, and the contract between the hand-curated types and the
generated OpenAPI schema (`npm run api:check` regenerates that schema from a
running API and type-checks against it).

`src/lib/api/client.test.ts`, in both portals, runs the real axios client
against MSW at the network boundary and proves the other half of the sealing
arrangement: a JSON body with `SE::…` values anywhere in it comes out of the
client opened, in one call to this origin's `/dkms/decrypt`, with nothing
else changed - and a body with nothing sealed makes no call at all.
`e2e/sealed-never-shown.spec.ts` in each portal then checks the same thing
on the screen: on the pages that show people, the API answered with sealed
values and not one reached the page.

## Browser tests

```bash
cd frontend/console && E2E_API_URL=http://127.0.0.1:8000 E2E_STAFF_LOGIN=dpo@cmp.local E2E_STAFF_PASSWORD='SeedPassw0rd!2026' npx playwright test --workers=1
cd frontend/portal && E2E_CONSENT_TOKEN=<token> npx playwright test --workers=1
```

The stack must be running: the key service, the API and the worker. Each
suite builds the portal and serves it itself, on `127.0.0.1:3100` (console)
or `127.0.0.1:3201` (portal), reusing a server already on that port; the
dev servers on 3000 and 3001 are left alone. The build reads the portal's
`.env.local`, so its `DKMS_URL` must name the running key service or
`sealed-never-shown.spec.ts` fails. Codes are read from
`backend/api/var/outbox.log` by `e2e/support/outbox.ts`.

| Variable | Suite | Default | Without it |
|---|---|---|---|
| `E2E_STAFF_LOGIN`, `E2E_STAFF_PASSWORD` | console | none | the `auth.spec.ts` "session cookie" tests skip. A seeded staff account works |
| `E2E_API_URL` | console | `NEXT_PUBLIC_API_URL`, then `http://localhost:8000` | `controls.spec.ts` calls the API directly with the saved session, whose cookie is scoped to `127.0.0.1`; on `localhost` the DCO test fails. Set `http://127.0.0.1:8000` |
| `E2E_PASSWORD` | console | `SeedPassw0rd!2026` | the seed's staff password is used by `auth.setup.ts` |
| `E2E_CONSENT_TOKEN` | portal | none | the consent journey in `consent-flow.spec.ts` skips. The token is the last segment of an active link's `url_path` from `GET /links` |
| `E2E_OUTBOX` | both | `backend/api/var/outbox.log` | |
| `E2E_PORT` | both | 3100 console, 3201 portal | |
| `E2E_BASE_URL` | both | `http://127.0.0.1:<E2E_PORT>` | set, the suite uses that server and builds nothing |
| `E2E_SHOTS` | portal | empty | `rights.spec.ts` takes no screenshots |

The console suite has five projects. `setup` signs in every role once, with
its emailed code, and saves the sessions; `chromium` and `mobile` run the
specs (account contacts, audit, auth, controls, detail pages, forms, links,
messages, navigation coverage, notice review, notice upload, routing, sealed
values never shown); `localhost-cookies` re-runs the auth spec
on the other origin; `visual` takes the screenshots. The suites read one-time
codes from the outbox by shape (a code on its own line, "code is 123456", or
a line opening with the code), so rewording a message on the Messages page
that drops all three shapes will make them fail; keep one. The portal suite covers the
consent flow, sign-up with two codes, the rights pages including nomination
acceptance, the data principal's own pages, a member of staff signing in as a data
principal, and sealed values never reaching the page. `expectNoSidewaysScroll` in
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

`.github/workflows/ci.yml` does not currently pass. It still names the old
directories (`cmp_backend`, `cmp_internal_ui`, `cmp_public_ui`), installs
with `uv` from `cmp_backend/uv.lock`, and builds an image from a Dockerfile;
none of those exist any more. The replacement is
[`docs/tools/ci.yml.proposed`](../tools/ci.yml.proposed), not yet applied;
[ci-paths.md](../tools/ci-paths.md) says why it cannot be pushed from here.

What the proposed workflow runs: backend lint, format and `mypy`;
migrations up, down and up; a diff of the committed `openapi.json` against
the one the code generates; the backend pytest suites with coverage; both
portals' typecheck, lint, vitest and production build; a dependency audit, a
static security scan and a secret scan.

What it does not run:

- **The key service's suite.** There is no job for `backend/dkms`.
- **A key service for the backend suites.** Its test job sets no
  `DKMS_ENABLED` and starts no key service, so sealing is off. Its "full
  suite" step runs plain `pytest`, which includes `tests/http`; that suite,
  and `test_search_over_sealed_names.py`, assert sealed values and will
  fail there as written.
- **The browser suites.** They need the whole stack and the outbox, and run
  locally as above.
