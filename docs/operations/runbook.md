# Runbook

What to do when something is wrong, ordered by how often it comes up. Every
API error carries a `request_id`; ask for it first, then search the log.

## Someone cannot sign in

| Symptom | Cause | Do |
|---|---|---|
| "Account locked" | five failed passwords in thirty minutes | wait thirty minutes, or clear `rate:login:<email>` in Redis if you are sure it is them |
| The code never arrives (staff) | worker not running, the email transport is `console`, **or the key service cannot be reached from the worker** | `curl <api>/ready` - the `encryption` check names the URL and the reason; then the worker is consuming `high_priority`; in local, read `var/outbox.log` |
| The code never arrives (data principal) | as above, or the SMS transport | the same; the sign-in page offers the other contact if one is on file |
| "Too many codes" | five per contact per hour | wait, or clear `rate:otp_request:<contact>` |
| Signed in, then everything answers 401 `mfa_required` | the second factor was never completed | finish the code step; the partial session is worth nothing else |
| Signed in on the wrong portal | a staff account on the portal or a principal on the console | each portal points the wrong kind of account at the other |
| Works on `localhost`, not on `127.0.0.1` | the cookie is first-party to one origin | use the proxied origin |

## No message of any kind is sent, and the request said one was

Every message is addressed to a contact that is **sealed in the database**.
The worker opens it through the key service on the way out - that is the one
step between "a code was queued" and "a code was sent" - so a key service it
cannot reach means no email and no SMS, anywhere, while every request
carries on answering normally. Validation is unaffected: sign-in, "is this
contact taken" and the searches match on the blind index and never need the
key service. So the symptom is precisely: **nothing arrives, everything else
works.**

1. `curl <api>/ready`. The `encryption` check is `ok: false` with the URL and
   the reason - `unreachable`, `answered 404`, or the wrong host entirely.
   That is the whole diagnosis in one line.
2. The worker has its own environment. It is the process that opens the
   recipient, so **its** `DKMS_URL` and **its** `DKMS_ENABLED` are the ones
   that matter for messages; `grep message.not_sent` in its log names the
   service it tried. `DKMS_ENABLED` defaults to *false* in code: unset
   there, the task fails with "N value(s) are sealed but DKMS_ENABLED is
   false", or "the recipient of '…' is still sealed after opening … Check
   DKMS_ENABLED and DKMS_URL in this process's environment".
3. The service must also hold the key the data was sealed with - the API's
   own `DKMS_URL`. A reachable service with a different key answers 4xx and
   opens nothing.
4. Fix the setting and **restart the worker and the API**; each reads it at
   start. Every message task retries a key-service failure five times, with
   jittered exponential backoff from 5 seconds (`max_retries=5`,
   `retry_backoff=5`): at most about two and a half minutes. A message queued during a
   longer outage is dropped after the last retry; the person asks for a new
   code.

## A portal shows `SE::…` where a name should be

The API serves personal fields sealed; each portal opens them in its own
server, at `/dkms/decrypt`, which calls the key service at that portal's
`DKMS_URL`. A value that stays sealed on the page is one of three things.
Check them in order:

1. **Unset or unreachable.** The portal's own log says `[dkms] DKMS_URL is
   not set`, or `[dkms] <url>/bulk_decrypt unreachable: …`. Run
   `curl <DKMS_URL>/health` **on the machine running the portal**. A key
   service bound to `127.0.0.1` is unreachable from any other host; set its
   `HOST` to the interface callers use, behind a firewall rule.
2. **A different service.** The log says `answered <status>`: the service
   answered but does not hold the master key the API sealed with. The
   portal's `DKMS_URL` must name the same service as the API's, or one with
   the same `DKMS_MASTER_KEY` and `DKMS_PREVIOUS_KEYS`.
3. **Not restarted.** `DKMS_URL` is read when the portal's server starts.

In the browser's network tab, `/dkms/decrypt` answering 503 is case 1 or 2;
401 means the session cookie is missing (`NEXT_PUBLIC_SESSION_COOKIE` must
match the API's `COOKIE_NAME`).

## Sign-in or a search finds nobody who is there

Every lookup of a sealed column - sign-in by email or mobile, "is this
contact taken", a nomination by the nominee's contact, the name searches -
compares a keyed hash computed **in the API** under `BLIND_INDEX_KEY` with
the `*_hash` or `*_ngrams` column stored beside the value. The key service
is not involved, so this works while it is down.

- **`BLIND_INDEX_KEY` changed** since the rows were written - or differs
  between the API and the process that wrote them (a script, a migration
  run from another shell). Every stored hash was computed under the old key
  and matches nothing. Put the old key back. Nothing in the repository
  recomputes the hashes of rows already sealed; rotating this key is a
  planned operation, described in
  [encryption-at-rest.md](../security/encryption-at-rest.md).
- **The key service's `DKMS_HASH_KEY` differs** from `BLIND_INDEX_KEY`. The
  platform never asks the service for a hash, so its own lookups still
  work; any *other* caller of the service's `/search`, `/search_ngram` or
  `/bulk_hash` gets hashes that match no row. Make them equal.
- **A name search under three characters** is refused, by design: the name
  index is made of three-character runs.
- **A row written by hand with SQL** has no hash unless whoever wrote it
  computed one. A CHECK refuses an account's email, secondary email,
  mobile, username or organisation id, and a nominee's email or mobile,
  without its hash; nothing checks the name `*_ngrams` columns.

Rows written while `DKMS_ENABLED` was false are still findable: the hash is
computed whether sealing is on or not. They are plaintext at rest, which is
the next section.

## Plaintext in a sealed column: `scripts/reseal.py`

Sealing happens on write. Rows written before `DKMS_ENABLED` was true - or
before a column joined `ENCRYPTED_FIELDS` - stay plaintext until resealed.
The read path accepts both, so nothing breaks; the data is simply not
protected.

```bash
cd backend/api && . .venv/bin/activate
python scripts/reseal.py --check          # report only; exit 1 if any plaintext is left
python scripts/reseal.py                  # seal it
python scripts/reseal.py --table auth_user
```

- It refuses (exit 2) with `DKMS_ENABLED` false, and needs the key service
  reachable at `DKMS_URL`.
- It needs the **table owner's** database role, not the application's: on
  `rights_ticket_message`, `consent_artefact`, `project_status_history` and
  `person_type_history` it disables the append-only trigger for the
  duration of its transaction and re-enables it before committing.
- One transaction per column, in batches of 200 rows. A failure rolls back
  that column only; run it again. It is idempotent: a value already `SE::`
  is skipped.
- For a column with a hash beside it, the hash is recomputed from the
  plaintext in the same `UPDATE`.
- It does not re-encrypt ciphertext under a new master key version, and it
  does not recompute hashes of rows already sealed.

Run `--check` after switching sealing on, after a migration adds a sealed
column, and whenever you want proof that nothing is in the clear.

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

## An export is refused: "This export cannot go"

`transfer_refused` (422). Every row's destination - the processor running its
site - was checked under s.16 and at least one failed; the message names each.

- **"… has no recorded location - record its country first."** Edit the
  processor on the Processors page and give its two-letter country. Unknown is
  refused on purpose: a transfer the platform cannot place is not one it can
  call lawful.
- **"… is in XX, restricted by <notification>."** The country is on the
  restricted list. Nothing is to be done at the export: either the site must be
  run by a processor elsewhere, or the restriction lifted when the Government
  lifts it (Processors page, *Restricted countries*, DPO only).
- **"… is in XX, and PURPOSE does not permit a transfer outside India."** A
  purpose the people in the file granted says their data stays in India. That
  is what their notice told them; the purpose, not the export, is where to
  look.

The refusal is in the audit trail as `export.refused`, with the processors and
causes and none of the people.

## An erasure is not finishing

An applied erasure or redaction is quarantined at once and erased only when
every store holding it is confirmed (S2-03). The request's scope card shows
each store as it stands; the same rows are `rights_item_execution`.

- **"Waiting - no holder has been asked for this asset's copy."** The asset's
  source belongs to a processor with no holder on this request. Derive the
  holders, confirm the one for that processor, and issue its ticket.
- **"Waiting for the holder's ticket to come back."** The holder has not
  returned. Chase or escalate it as for any ticket; the return carries the
  item on by itself. A return can only be recorded while the request is open:
  if the holder answers after the response went out, the item stays waiting -
  record what happened on the request and escalate to the DPO.
- **"Failed (…)".** A store raised; the class name is recorded, never the
  message. It is retried by the 02:30 sweep and on every ticket return, or
  press **Try again now** (`POST /requests/{uuid}/scope/{item}/execute`).
  Something that fails every time is a defect: the worker and API logs carry
  `rights.erasure_failed` with the item.
- **"Stopped until the hold is released."** A legal hold covers the asset or
  the person. Nothing is erased while it stands. Only the DPO places and
  releases one (`/legal-holds`); releasing it carries the item on at once.

What is never erased, by design: consent artefacts, the audit trail, the
export files processors were sent and the response packages she was given
([ADR 0019](../decisions/0019-erasure-reaches-every-store-but-the-record.md)).
Backups are not covered yet: there are none (P-03), and whether one holding an
erased item is scrubbed or left to expire is waiting on Legal.

## Somebody asks what happened to a record

Open the record on the console and press **Audit trail**, or on the Audit
trail page use **About** to find the person or record by name. The summary
strip shows the shape (which areas, which events, which days) before the
rows; **Export CSV** takes the same rows away, and the export is recorded.
Details in [audit-trail.md](../domain/audit-trail.md).

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

## A data principal cannot record her consent

- **"Read the notice before recording a decision"** (`notice_not_served`):
  the server has no record of rendering the notice to her through this link
  in this language within six hours. Reloading the notice page writes one.
  If it recurs immediately, Redis is not accepting writes; see below.
- **"This page has been open too long"** (`notice_stale`): the same, after
  six hours. Reload.
- **"That language rendition is not legally approved"**: the rendition she
  chose has no approval stamp; the DPO approves it on the notice.

## The API is up but everything answers 503

`/ready` says which dependency is missing. The API is fail-fast at startup;
a 503 stream means a datastore vanished after start. Fix the datastore; the
pool reconnects.

- **`encryption` not ok:** the key service is unreachable from the API, or
  answered an error. The detail names the URL and the reason. Writes that
  carry personal data answer 503 "The encryption service is unavailable".
  Sign-in lookups keep working and reads still answer, sealed - but the
  portals cannot open them, and no message can be sent.
- **`migrations` not ok, naming two revisions:** the database is behind the
  code. Run `alembic upgrade head` from the release's `backend/api`, in its
  virtualenv, with the same `.env` the API uses.
- **Writes to Redis fail with OOM:** Redis is at `maxmemory` and runs with
  `noeviction` on purpose, so it refuses rather than evicting live sessions
  and codes. Raise `maxmemory` or find what is filling it (`redis-cli
  --bigkeys`); rate counters and codes expire within the hour, sessions
  within eight.

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

## Migrations 0028 and 0030: the ones that call the key service

Every other migration is SQL. These two backfill hashes in Python, inside
the migration's transaction:

- **0028** adds the `*_hash` columns (named `*_idx` until 0029) and fills
  them from the lookup columns. A value already sealed is opened through the
  key service to be hashed.
- **0030** adds the name `*_ngrams` columns on `auth_user`,
  `rights_request` and `nomination`, and fills them by opening every name.

Plaintext rows are hashed where they are; only sealed values need the key
service. So, before running them against a database with sealed rows in it:

1. The key service is reachable at the `DKMS_URL` of the shell running
   `alembic`, and holds the master key the rows were sealed with. If it is
   not, the migration fails and rolls back - which is right: a half-filled
   index is rows nobody can find.
2. `DKMS_ENABLED=true` in that shell. With it false, a sealed value cannot
   be opened and the migration fails naming the setting.
3. `BLIND_INDEX_KEY` in that shell is the one the API will run with. The
   hashes are computed under it; a different key writes hashes the API will
   never match.
4. Expect the tables locked for the duration. The columns are added first,
   and `ALTER TABLE` holds its exclusive lock until the migration commits,
   so `auth_user`, `nomination` and `rights_request` refuse reads and writes
   while every row is hashed. Run them in a maintenance window, with the API
   and worker stopped.

## Disk is filling

- `uploads`: proofs, notice documents, ticket attachments and response
  files. Nothing here is deleted by the application.
- `var/outbox.log` in local: grows with every code sent. Truncate it.
- Redis: sessions and codes expire on their own; a rate counter lasts an
  hour.

## Resetting a development machine

```bash
cd backend/api && . .venv/bin/activate && python scripts/reset_dev.py
```

Never on staging or production; the script refuses, and the refusal is the
point.

## Where the logs are

| Process | Where |
|---|---|
| API | stdout, JSON in production, every line with `request_id` |
| worker, beat | stdout |
| key service | stdout; `dkms.ready` at start names the provider and pool |
| a portal's server | stdout; `[dkms] …` lines when a decrypt fails, never a value |
| a reverse proxy, if one is in front | its own access log; scrub `/c/{token}` to `/c/[token]` there too, as the application does |
| what was sent to whom | `audit_log` entries of type notification, and in local the outbox |

Signals worth an alert are listed in
[monitoring.md](../operations/monitoring.md).
