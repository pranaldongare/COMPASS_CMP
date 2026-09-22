# DKMS — the implementation plan

What was built, in the order it was built, what each phase proved, and what
a team carrying this into another environment has to do. The design
decisions behind each choice are in
[the backend document](backend-api.md) and
[the frontend document](frontend-layer.md); this is the plan.

**Status: phases 1–9 complete** (September 2026). Phase 10 is the standing
work — what a new field, a new endpoint or a new environment costs.

## The goal, stated once

Personal data is **encrypted before it reaches the database** and
**decrypted only in the frontend layer**. The platform API stores and serves
ciphertext and never holds the plaintext it is protecting; a portal opens a
value at the moment a person reads it. Lookups keep working because a blind
index sits beside every column the platform searches by.

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
- **Given up, deliberately:** partial search on a person. Whole contact,
  reference, uuid and project still work; a few letters of a name do not,
  and the fields say so.

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

---

## Phase 10 — the standing work

### A new personal field

1. Add it to `ENCRYPTED_FIELDS` with its type.
2. Make the column `text` in a migration. If anything looks the row up by
   it whole, add a `*_hash` column and `BLIND_INDEXED` entry. If staff will
   search by *part* of it, add a `*_ngrams text[]` with a GIN index and an
   `NGRAM_INDEXED` entry — and write down why the leak is worth it.
3. Write it through the repository, so `seal()` applies.
4. Add its name to `contract.SEALED` in the HTTP suite.
5. If the frontend shows it, nothing to do — the interceptor is generic.

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
2. `DKMS_MASTER_KEY` and `BLIND_INDEX_KEY`: generated, stored in the secret
   store, **never rotated casually** — the master key opens existing rows and
   the index key is what makes existing indexes match. Rotating either is a
   re-seal, not a config change.
3. `DKMS_URL` in three places, all naming the same service: the platform
   API, the console, the portal. The **worker** has its own environment and
   is the process that opens a recipient — a message fails if only the API
   is pointed correctly.
4. `curl <api>/ready` — the `encryption` check names the URL and the reason.
5. Run `scripts/reseal.py --check` against the database before serving.

### What breaks, and how it shows

| Failure | Symptom | Where to look |
|---|---|---|
| Key service unreachable from the **worker** | No email or SMS at all; every request still answers normally | `/ready`, then `message.not_sent` in the worker log |
| Unreachable from a **portal** | Pages render with `SE::…` where names should be | The portal log: `[dkms] <url> unreachable` |
| A **different master key** | Nothing opens; 4xx from the service | Compare the API's `DKMS_URL` with the portals' |
| A **different index key** | Sign-in fails for existing accounts, "is this taken" says no | `BLIND_INDEX_KEY`; a change here needs a re-index |
| Writes failing 503 | The API cannot reach the service | Fails closed on purpose — it will not store plaintext |

---

## The map

| Document | What it holds |
|---|---|
| [pii-tables-and-fields.md](pii-tables-and-fields.md) | Every personal column: which are sealed, as what type, which carry a blind index, which are plaintext and why |
| [backend-api.md](backend-api.md) | Where encryption happens, the key service's contract, the 159 endpoints, the four places the backend decrypts |
| [frontend-layer.md](frontend-layer.md) | How the portals decrypt, which APIs it covers, the three files, the one setting, what breaks it |
| [personal-data.md](../domain/personal-data.md) | The narrative inventory — every store, not only the database |
| [pii-fields-and-endpoints.md](../domain/pii-fields-and-endpoints.md) | The generated list: 54 columns by table, 159 endpoints by module |
| [runbook.md](../operations/runbook.md) | What to do when messages stop arriving |
