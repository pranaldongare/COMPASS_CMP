# DKMS — the implementation plan

What was built, in the order it was built, what each phase proved, and what
a team carrying this into another environment has to do. The design
decisions behind each choice are in
[the backend document](backend-api.md) and
[the frontend document](frontend-layer.md), and the two decisions are
[ADR 0016](../decisions/0016-personal-data-sealed-by-a-separate-key-service.md)
and [ADR 0017](../decisions/0017-lookup-by-keyed-hash-and-name-ngrams.md);
this is the plan.

**Status: phases 1–10 complete** (September 2026), with two known gaps in
phase 10 still under review. Phase 11 is the standing work — what a new
field, a new endpoint or a new environment costs.

## The goal, stated once

Personal data is **encrypted before it reaches the database** and
**decrypted only in the frontend layer**. The platform API stores and serves
ciphertext and never holds the plaintext it is protecting; a portal opens a
value at the moment a person reads it - except where the backend hands a
value to somebody outside the browser, which
[the backend document](backend-api.md#where-the-backend-decrypts) lists.
Lookups keep working because a keyed hash (`*_hash`) sits beside every
column the platform finds rows by, and hashed runs (`*_ngrams`) beside the
three names staff search by part of.

Two properties follow, and both are testable:

1. No endpoint serves a personal value in the clear. *(Backend HTTP suite,
   all 159 endpoints, every response.)*
2. No page shows ciphertext. *(Browser specs, both portals, every role.)*

---

## Phase 1 — the key service

A separate FastAPI service (`backend/dkms`), port 32688, AES-256-GCM with
per-type keys derived from one master key by HKDF.

- The contract is exactly `{data, key, method}` in, `{data}` out, for
  `/bulk_encrypt` and `/bulk_decrypt`. Any service that implements it can
  stand in this place.
- The envelope carries its own type id, so a reader opens a value knowing
  only that it is one.
- No CORS, no user auth: it is reachable by the platform API and the
  portals' server sides, never by a browser.

**Proved by:** its own suite; `GET /health` and `GET /types`.

## Phase 2 — sealing on write

`ENCRYPTED_FIELDS` names every table, column and type. `seal()` is called in
the **repositories** — the one layer every write passes through — so a
service or router cannot bypass it.

- 25 columns first: names, free text, reasons, file names, the consent IP.
- Migration 0027 widened them to `text` (ciphertext is longer than a
  varchar(20) mobile), recreating the one view that depended on a column.

**Proved by:** the integration suite; a query for plaintext in a sealed
column returns nothing.

## Phase 3 — decryption in the frontend

One response interceptor on the one API client each portal has. It walks
every JSON body, collects the `SE::` values wherever they sit, and opens
them in **one** call to the portal's own `/dkms/decrypt` route, which
forwards to `${DKMS_URL}/bulk_decrypt`.

- The browser never reaches the key service: `DKMS_URL` is server-only.
  Otherwise every session would hold a decrypt-anything oracle.
- No page, hook or feature knows any of this happens.

**Proved by:** `client.test.ts` in both portals (the real client against a
fake network); the browser specs.

## Phase 4 — the eight lookup columns

`email`, `secondary_email`, `mobile`, `username`, `organization_id`,
`nominee_email`, `nominee_mobile`, `submitted_contact` were plaintext
because the platform finds rows by them. Each got a blind index —
`HMAC-SHA256(normalised value, BLIND_INDEX_KEY)` — and the value itself was
sealed.

- Migration 0028: the index columns, a Python backfill (the HMAC needs a key
  the database does not hold), every uniqueness rule and the one
  cross-column trigger moved onto the indexes, the columns widened.
- `dob` sealed; the s.9 test moved to `minor_until`, the one date kept in
  the clear.
- **Given up, for the time being:** partial search on a person. Whole
  contact, reference, uuid and project still worked; a few letters of a
  name did not. Phase 9 brought it back for names.

**Proved by:** sign-in, "is this taken", code delivery and the nomination
flows, all against sealed rows.

## Phase 5 — the audit trail

The one store nothing can be erased from, so nothing erasable goes in
([ADR 0015](../decisions/0015-nothing-erasable-in-a-trail-nobody-can-erase.md)).

- The client address is written as its blind index; the invited email is not
  written at all; free-text reasons became `reason_given: true`, with the
  reason in the sealed row it belongs to.
- Rows written before this stand as written: the chain hashes
  `detail_json`, so rewriting them would break the property the trail exists
  for.

**Proved by:** a static test that fails the build on the next string that
would carry a reason; the CSV export carries no address of anybody.

## Phase 6 — the rows already there

`scripts/reseal.py`: every sealed column, every plaintext row, in batches,
idempotent, setting the append-only triggers aside inside its own
transaction. `--check` reports what is left.

**Proved by:** `--check` reports zero; the HTTP suite asks the same question
of every sealed column after everything it writes.

## Phase 7 — the tests, and what they found

- **Backend, over HTTP:** a world built through the API, then all 159
  documented endpoints called, every response checked against one contract.
- **Portals:** the interceptor against a fake network; browser specs on the
  pages that show people, which require the API to have answered sealed
  before asserting the page shows the person.
- **The database, after all of it:** one query per sealed column.

Four real defects, each fixed where it was found:

| Found | Was |
|---|---|
| A ticket's `brief` | Copied the subject's name and contacts into jsonb in the clear |
| A holder's `contact_log` | Stored the address a message went to, opened |
| The audit lookup and search | Pattern-matched sealed columns: found nothing, scanned for it |
| Five entity labels | Concatenated a sealed name with plaintext in SQL — a string nobody can open, and it made the key service refuse the whole batch it travelled in |

The last one is now a static test over the repositories' SQL.

## Phase 8 — the hash columns are called `*_hash`

0028 named them `*_idx`, after what an index is built on rather than what
the column holds, and six ordinary btree indexes in the schema end the same
way. Migration 0029 renames all eight; a test holds the field map and the
migration together so the two cannot drift into an undefined column at
sign-in.

The schema reference was rebuilt at the same time, and is now **generated**
- `docs/tools/generate-schema-docs.py` reads the catalogue and writes the
inventory, the column reference, the enum reference and every diagram. It
had been hand-built at 0026 and described a schema that no longer existed.

## Phase 9 — search comes back

Sealing the names took a search away: the users list, the requests list and
the audit trail's About picker were narrowed to whole contacts, and a member
of staff holding a half-legible name on a piece of paper had no way to find
the person.

The key service gained three endpoints - `/bulk_hash`, `/search`,
`/search_ngram` - and `/bulk_encrypt` gained `with_hash` and `with_ngrams`,
so one call returns the ciphertext and everything the row needs beside it.
Migration 0030 added `*_ngrams text[]` with GIN indexes to three name
columns and backfilled them by decrypting each name through the key service,
hashing it, and writing the hashes back. The three searches use `@>`.

**The trade-off, recorded rather than buried:** a set of runs leaks letter
statistics that a single hash does not, so it is three name columns and
never a contact. [The field list](pii-tables-and-fields.md#2a-searching-by-part-of-a-name)
carries the reasoning.

**As built, narrower than planned:** the users register and the audit
trail's About picker use the runs. `GET /requests?q=` does too, but the
console's requests list has no search box to send it, and
`nominee_name_ngrams` is written and not yet searched.

## Phase 10 — any key service, and failures that say what they are

The brief was always that any service implementing `{data, key, method}`
could take the place of `backend/dkms`, and a report from a Windows worker
showed what silence costs: every sign-in died on "`'mfa_code' is not sent by
sms`" because `DKMS_ENABLED` was false in the worker and a sealed address
had been read as a phone number.

- **Contract and nothing else, from the API.** The request-time client
  stopped sending `on_error` and relying on `skip_encrypted`; only values
  that need the work travel, and a value that comes back unchanged from a
  "fail" call is reported by field name.
- **Foreign ciphertext in the portals.** The walker falls back to the
  field's name (`lib/dkms/field-types.ts`, a hand-kept mirror of
  `ENCRYPTED_FIELDS`) when it cannot read the envelope, and names - never
  quotes - any field it still cannot label.
- **Three silences became three sentences** in the worker: sealed values
  with `DKMS_ENABLED` off, a `SE::` value with no readable envelope, and a
  recipient still sealed after opening each raise `DkmsUnavailable` with the
  cause, before a channel is chosen. `fields.PREFIX` is the one "is this
  ciphertext" test.

**Proved by:** `deep.test.ts` in both portals against a deliberately
foreign envelope; `test_a_message_says_when_it_cannot_be_addressed.py`; the
reported failure reproduced and answered with the setting to change; the
backend suite; sign-in by sealed email and by sealed mobile, staff MFA
delivered.

**Known gaps, under review.** The worker's `unseal_values_sync` still sends
`"on_error": "fail"`, and it cannot open a value whose envelope it cannot
parse, having no field name to fall back to. So against a different key
service, the API and the portals work and messages do not.
[The backend document](backend-api.md#standing-behind-this-with-another-key-service)
has the detail.

---

## Phase 11 — the standing work

### A new personal field

[Adding a personal field](adding-a-personal-field.md) is the whole
checklist, each step with where it lives and what fails if it is skipped.
In short: the field map, a migration (`text`, and `*_hash` or `*_ngrams`
where rows are found by it), the repository write, `scripts/reseal.py` for
rows already there, the field-name fallback in both portals, the HTTP
contract for any alias it is served under, and the generated documents.

### A new endpoint

Nothing, if it goes through a repository and the typed client. The HTTP
suite will fail if it carries personal data and is not exercised; that is
the reminder.

### A label or a message that names a person

Do not concatenate in SQL. Return the pieces (`label_parts`) and join them
after opening, or open the value at the one point the message is sent.

### A new environment

1. Run the key service where the API and both portals' servers can reach it.
   It binds `127.0.0.1` by default — set `HOST` to the interface its callers
   use, and firewall it: **it authenticates nobody**.
2. `DKMS_MASTER_KEY` on the key service; `DKMS_HASH_KEY` on the key
   service and `BLIND_INDEX_KEY` on the API and worker, **the same string**.
   Generated, stored in the secret store, **never rotated casually** — the
   master key opens existing rows and the hash key is what makes existing
   `*_hash` and `*_ngrams` values match. Rotating either is a re-seal or a
   re-hash of every row, not a config change.
3. `DKMS_URL` in four places, all naming the same service: the platform
   API, the worker, the console, the portal. `DKMS_ENABLED=true` in two:
   the API and the **worker**, which has its own environment, is the
   process that opens a recipient, and defaults to false.
4. `curl <api>/ready` — the `encryption` check names the URL and the reason.
5. Run `scripts/reseal.py --check` against the database before serving.

### Verification, at the end of any change to this

```bash
cd backend/api && pytest                     # every suite, encryption on
python scripts/reseal.py --check             # zero plaintext rows in sealed columns
psql -d cmp -c "select count(*) from auth_user where email not like 'SE::%'"   # 0
```

And on the running stack: sign in with an email whose stored form is `SE::…`,
receive the code at it, open the users list and see names, and find somebody
there by three letters of their name.

### What breaks, and how it shows

| Failure | Symptom | Where to look |
|---|---|---|
| Key service unreachable from the **worker** | No email or SMS at all; every request still answers normally | `/ready`, then `message.not_sent` in the worker log |
| `DKMS_ENABLED` unset in the **worker** | The same silence | The worker log: "value(s) are sealed but DKMS_ENABLED is false" |
| A **different key service** behind the worker | The same silence | "carry no readable envelope", or a 422 for the `on_error` the worker still sends — the phase 10 gaps |
| Unreachable from a **portal** | Pages render with `SE::…` where names should be | The portal log: `[dkms] <url> unreachable` |
| A **different master key** | Nothing opens; 4xx from the service | Compare the API's `DKMS_URL` with the portals' |
| A **different index key** | Sign-in fails for existing accounts, "is this taken" says no | `BLIND_INDEX_KEY`; a change here needs a re-index |
| Writes failing 503 | The API cannot reach the service | Fails closed on purpose — it will not store plaintext |

---

## The map

| Document | What it holds |
|---|---|
| [pii-tables-and-fields.md](pii-tables-and-fields.md) | Every personal column: which are sealed, as what type, which carry a `*_hash` or `*_ngrams`, which are plaintext and why |
| [adding-a-personal-field.md](adding-a-personal-field.md) | Everything that changes together when a column joins the list |
| [backend-api.md](backend-api.md) | Where encryption happens, the key service's contract, the 159 endpoints, the places the backend decrypts |
| [frontend-layer.md](frontend-layer.md) | How the portals decrypt, which APIs it covers, the four files, the one setting, what breaks it |
| [personal-data.md](../domain/personal-data.md) | The narrative inventory — every store, not only the database |
| [pii-fields-and-endpoints.md](../domain/pii-fields-and-endpoints.md) | The generated list: 54 columns by table, 159 endpoints by module |
| [runbook.md](../operations/runbook.md) | What to do when messages stop arriving |
