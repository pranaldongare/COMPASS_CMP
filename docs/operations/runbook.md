# Runbook

What to do when something is wrong, ordered by how often it comes up. Every
API error carries a `request_id`; ask for it first, then search the log.

## Someone cannot sign in

| Symptom | Cause | Do |
|---|---|---|
| "Account locked" | five failed passwords in thirty minutes | wait thirty minutes, or clear `rate:login:<email>` in Redis if you are sure it is them |
| The code never arrives (staff) | worker not running, or the email transport is `console` | check the worker is consuming `high_priority`; in local, read `var/outbox.log` |
| The code never arrives (data principal) | as above, or the SMS transport | the same; the sign-in page offers the other contact if one is on file |
| "Too many codes" | five per contact per hour | wait, or clear `rate:otp_request:<contact>` |
| Signed in, then everything answers 401 `mfa_required` | the second factor was never completed | finish the code step; the partial session is worth nothing else |
| Signed in on the wrong portal | a staff account on the portal or a principal on the console | each portal points the wrong kind of account at the other |
| Works on `localhost`, not on `127.0.0.1` | the cookie is first-party to one origin | use the proxied origin |

## A data principal reports a problem with her record

- **She cannot see a consent.** Consents are listed per notice from
  `v_current_consent`; a superseded artefact is under history. If the link she
  used was for a different account (a different mobile), the consent is on
  that account.
- **She withdrew and still sees "consented".** Withdrawal writes a new
  artefact; the current view resolves the chain. If the page is stale,
  reload; if the database disagrees, read the chain with `scripts/db.py` and
  look for the artefact whose `supersedes_consent_id` is the old one.
- **She was shared with someone and does not see it.** Disclosures come from
  `export_line`. An export that failed after the file was written cannot
  exist: the record and the file are one transaction.

## A rights request is stuck

- **It will not move to in progress.** Read `GET /requests/{uuid}/transitions`;
  the blocked reasons are the missing prerequisites (not verified, not
  classified, intent not confirmed, event not evidenced, reviewer not
  assigned).
- **A ticket was issued and nobody was told.** For an in-house respondent the
  ticket is on their dashboard, not in email; check the processor's
  respondents. For a third party, check the notifications queue and the
  transport.
- **The office's bell shows unread messages on a closed request.** Threads
  stay readable after closure; reading them clears the count.
- **The sweep did not close an unverified request.** It runs at 02:30 and
  closes requests past `RIGHTS_UNVERIFIED_CLOSE_DAYS`. Check beat is running
  and there is exactly one of it.

## The audit chain reports a break

`GET /audit/verify` or the 03:00 task names the first row that does not
verify. Treat it as a page.

1. Do not write to the database until you know why.
2. Read the named row and its predecessor with `scripts/db.py`. A row whose
   `prev_hash` does not match the previous row's `hash` was inserted out of
   order or altered.
3. If the rows were altered, that is an incident: preserve the volume, take a
   snapshot, and escalate to the DPO.
4. If the break dates from before migration 0014 and under concurrent load,
   it is the historical defect that migration fixed (the chain position was
   drawn before the lock). The rows are genuine but out of order; verify from
   the row after the break to confirm the rest is sound, and record the
   finding.

## The API is up but everything answers 503

`/ready` says which dependency is missing. The API is fail-fast at startup;
a 503 stream means a datastore vanished after start. Fix the datastore; the
pool reconnects.

## The worker is running but nothing happens

- It must consume the queue the task was put on. The full list:
  `high_priority`, `email`, `documents`, `reports`, `notifications`,
  `default`. A worker started with a shorter `-Q` silently leaves the rest to
  pile up.
- Beat must be running for the scheduled tasks, and only one of it. Two beats
  double every scheduled job.
- Tasks are idempotent; re-running one that half-completed is safe by design.

## A migration failed halfway

Every migration is one transaction; a failed one rolled back. Read the
error, fix the cause, run `alembic upgrade head` again. Migration 0004 and
0015 deliberately refuse to apply while rows that break the new rule exist;
fix the rows first. `alembic downgrade -1` is supported by every migration if
you need to step back.

## Disk is filling

- `uploads`: proofs, notice documents, ticket attachments and response
  files. Nothing here is deleted by the application.
- `var/outbox.log` in local: grows with every code sent. Truncate it.
- Redis: sessions and codes expire on their own; a rate counter lasts an
  hour.

## Resetting a development machine

```bash
cd cmp_backend && uv run python scripts/reset_dev.py
```

Never on staging or production; the script refuses, and the refusal is the
point.

## Where the logs are

| Process | Where |
|---|---|
| API | stdout, JSON in production, every line with `request_id` |
| worker, beat | stdout |
| nginx | its access log, with `/c/{token}` scrubbed to `/c/[token]` |
| what was sent to whom | `audit_log` entries of type notification, and in local the outbox |

Signals worth an alert are listed in
[monitoring.md](../../cmp_backend/docs/operations/monitoring.md).
