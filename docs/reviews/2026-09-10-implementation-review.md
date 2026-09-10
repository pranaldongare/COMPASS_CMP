# Implementation review of 10 September 2026: disposition

An external source review (Codex, GPT-6 Astra) of commit `8123417` made ten
recommendations. This page records, for each, what was found when it was
checked against the code, what was done, what was not and why, and why our
own testing had not caught it. The review's four "reproduced offline" items
were all confirmed here by reading the code, and each now has a test that
would have failed before the fix.

## Why our testing missed these

The suites that were green at the time answered "does each flow behave as
specified for one caller at a time" and "does each role see only its rows".
They did not ask four other questions, and every confirmed finding sits in
one of them:

1. **Two callers at once.** The OTP race and the first-consent race are
   only visible with concurrent requests. The one concurrency test in the
   suite (the audit chain, from an earlier incident) was written for that
   incident alone.
2. **What is written to logs.** No test captured log output. The access-log
   scrubbing was tested by reading the middleware; the error handlers and
   the nginx format were never exercised.
3. **Does the code keep the promise the comment makes.** `served_at` was
   documented as server-stamped and it was, on the way out; nothing checked
   that it came back unchanged, because the portal always sent it back
   unchanged. Readiness was documented as "migrations current" and checked
   for a row. Tests written from the documentation confirmed the
   documentation.
4. **Deployment configuration.** Compose, nginx and the CI file are not
   under test, and the CI file's location meant it never ran to tell us.

The remedy is not only the fixes below but the kinds of test now present:
a real race, a log recorder, a check that the served moment in the artefact
equals the one the server issued, a check that the expected schema head is
the newest migration on disk, and a workflow that runs.

## Disposition

| # | Finding | Verified | Done | Tests |
|---|---|---|---|---|
| 1 | OTP verification is not atomic | Confirmed: `GET`, compare in Python, `DEL` in a later pipeline | The check, the consumption and the attempt count are one Lua script in Redis. `consume=False` uses the same script without the delete. | `tests/integration/auth/test_otp_atomic.py` races eight verifications of one code and expects one success |
| 2 | Capability tokens reach the failure log and the nginx log | Confirmed: handlers logged `request.url.path`; nginx set `$loggable_uri` and logged `$uri` | Handlers scrub through `safe_path`, which now also covers `/rights/nominations/{token}`. nginx maps `$uri` to `$loggable_uri` in the http block and every log format uses it. | `tests/unit/api/test_error_log_scrubbing.py` |
| 3 | Consent is not bound to a serving the server witnessed | Confirmed: `served_at` came from the request body | `serve_notice` writes a server-held record (person, link, rendition, moment, hash) in Redis for six hours; `capture` requires it, takes the moment from it, and re-checks language approval. The body field is accepted and ignored for older clients; the portal no longer sends it. | `tests/integration/test_consent_serving.py` |
| 4 | No real SMS transport; console reports delivery in production; receipts addressed to a possibly absent email | Confirmed on all three | An HTTP SMS transport (JSON POST with a bearer token to an https gateway); console transports raise outside local/test; production refuses to boot unless email is `smtp` and SMS is `http`; receipts go to a verified contact, email first, else mobile. Provider-specific SDKs are not added: a thin adapter service in front of the gateway keeps provider credentials out of this codebase. Object storage remains a stub that refuses to start, and is documented as such. | `tests/unit/core/test_production_guards.py`, `TestReceiptContact` |
| 5 | Side effects queued before commit | Confirmed | Optional side effects are deferred until the unit of work commits and dropped on rollback (`cmp.core.after_commit`). Required ones (a sign-in code) still queue at once, because the queueing *is* the outcome. A durable outbox table is **deferred**: it adds a table, a relay and delivery tracking, and the remaining gap (a broker outage at the moment of flushing) is logged at error as before. Recorded in [ADR 0012](../decisions/0012-side-effects-after-commit.md). | `tests/unit/core/test_after_commit.py` |
| 6 | CI never runs | Confirmed: the workflow sat under `cmp_backend/.github` | Moved to the repository root with a working directory, a build context for the image, both portals (typecheck, lint, vitest, build), an OpenAPI freshness diff, the security suite, and a smoke test that asserts the exit code. Triggers include the integration branch. | The workflow itself; first run will tell |
| 7 | Readiness accepts any migration; shared DB role; Redis evicts live keys | Confirmed on all three | Readiness compares the deployed revision with the head shipped in the image and answers 503 with both named. Redis runs `noeviction`. The runtime-role split is **deferred**: migrations 0005 to 0021 grant nothing to `cmp_app`, so switching the API to it would fail on the first table created after 0003; it is listed as a production hardening item with that specific gap. | `tests/unit/core/test_readiness.py` |
| 8 | Two first captures can both write a root | Confirmed by reading; not reproduced against PostgreSQL by the reviewer | `capture` takes `pg_advisory_xact_lock(person, notice)` before reading what is current, so the second becomes a supersession; migration 0023 adds a unique partial index so the database refuses a second root regardless. Request idempotency keys are **deferred**. | `TestFirstCapturesSerialise`; `tests/integration/enforcement/test_one_root_per_notice.py` |
| 9 | Export bytes re-rendered on download; formula injection | Confirmed | The CSV is stored at generation (`export_log.file_ref`, migration 0023) and served back as written; older exports re-render as before and the hash says which. Free-text cells beginning with a formula character are prefixed with an apostrophe; mobiles, emails, uuids and timestamps are validated formats and left alone. | `tests/integration/test_export_snapshot.py`, `tests/unit/domain/test_export_csv.py` |
| 10 | Duplication and size | Not disputed | Node pinned to 22 in both portals. Workspace packages for the shared frontend code, splitting the rights service and router, and a load test of the audit lock are **deferred** as maintainability work to do behind the regression suites, not alongside a security fix. README counts were regenerated in the documentation overhaul the same day. | |

## Found on the way

Walking the repaired capture path end to end against the running API showed
that a **second decision on the same notice** through the consent link had
always answered 500: the earlier artefact's uuid went into the audit detail
as a UUID object, and no test had ever recorded a supersession through
`capture` (withdrawal, which is tested, passes a string). Fixed, and
`TestSecondDecision` now records two decisions through the service. It is
the same lesson as item 3: the path the documentation describes is not the
path the tests walked.

## Rejected, with reasons

Nothing in the review was rejected as wrong. Three recommendations were
narrowed:

- **A provider SDK for SMS.** No provider has been chosen and no credentials
  exist. The HTTP transport plus an adapter is the shape that keeps both out
  of the platform; the guard makes the absence loud.
- **A transactional outbox table.** Post-commit deferral closes the two
  failure modes the review named. The durable half is worth doing when a
  broker outage during a flush is a risk the deployment cannot tolerate; the
  decision record says how.
- **Separate migration and runtime database roles.** The right change, but
  not a one-line one on this schema; doing it half-way would break the API
  on the first request. It needs a migration that grants the runtime role
  what 0005 to 0022 created, then the compose and pool changes, then a test
  that the runtime role cannot disable a trigger.

## Follow-ups

| Item | Where tracked |
|---|---|
| Durable outbox and recipient-level deduplication | [ADR 0012](../decisions/0012-side-effects-after-commit.md) |
| Runtime database role with least privilege across every table | [deployment.md](../operations/deployment.md), production hardening |
| Idempotency keys on consent capture | this page |
| Shared frontend packages; splitting the rights modules | this page |
| Load test of the audit-chain lock | [ADR 0005](../decisions/0005-audit-chain-position-inside-the-lock.md) |
| Object storage backend | stub; refuses to start when selected |
