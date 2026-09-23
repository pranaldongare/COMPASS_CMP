# DKMS — the frontend layer

How the two portals open the personal values the API serves sealed, how a
person is searched for when the column holding their name is ciphertext,
which APIs that covers, the three files that do it, the one setting, and how
it was checked end to end. Companion to
[the field list](pii-tables-and-fields.md) and
[the backend document](backend-api.md); the narrative on what is sealed and
why is [personal-data.md](../domain/personal-data.md). Verified against the
running stack on 2026-09-22.

## The arrangement in one paragraph

The platform API encrypts personal columns on write and **serves them as
stored** - `SE::…` - on every endpoint, list or detail, GET or the body a
POST returns. It never decrypts for a response. Each portal's API client
walks every JSON response it receives, collects every `SE::` string wherever
it sits (a field, a nested object, an element of an array), and opens them
all in **one** call to the portal's own `/dkms/decrypt` route. That route
runs in the portal's server, requires the session cookie, and forwards the
batch to the key service named by `DKMS_URL` as
`POST ${DKMS_URL}/bulk_decrypt` with exactly `{ data, key, method }`. The
page receives plaintext and never learns any of this happened.

```
browser page ──► GET /api/users ─────────────► API ──► rows with SE::…
      ▲                                                     │
      │  plaintext            axios response interceptor ◄──┘
      │                              │  decryptDeep(): every SE:: in the body
      │                              ▼
      │                 POST /dkms/decrypt  (this portal's server route)
      │                              │  session cookie required
      │                              ▼
      └──────────────────  POST ${DKMS_URL}/bulk_decrypt  {data, key, method}
```

## Which APIs

**All of them.** There is no per-endpoint list to maintain because the
interceptor is on the one client every feature uses
([`lib/api/client.ts`](../../frontend/console/src/lib/api/client.ts)); no
component, hook or feature constructs a request itself, and the two things
that bypass it are file downloads (binary, nothing to open) and the decrypt
route itself. An endpoint added tomorrow is covered the day it is added.

The endpoints that *actually answered with sealed values* during the
end-to-end walk below - 23 in the console, 5 in the portal - and so were
proven to decrypt on a real page:

| Console (staff) | Portal (data principal) |
|---|---|
| `/auth/me`, `/dashboard`, `/notifications` | `/auth/me`, `/notifications` |
| `/users` | `/me/requests` |
| `/projects`, `/projects/{uuid}`, `/projects/{uuid}/approvals`, `/projects/{uuid}/history`, `/projects/{uuid}/processors`, `/projects/{uuid}/sites`, `/approvals` | `/me/nominations`, `/me/nominee-of` |
| `/notices/{uuid}/languages` | |
| `/consents`, `/consents/{uuid}` | |
| `/requests`, `/requests/{uuid}`, `/tickets`, `/tickets/{uuid}` | |
| `/processors/{uuid}/respondents`, `/sources` | |
| `/exports`, `/imports`, `/imports/{uuid}` | |
| `/audit`, `/delegations` | |

The remaining documented PII endpoints are writes whose responses were
checked by the backend's HTTP suite (`tests/http`, every one of the 159) and
pass through the same interceptor when a page calls them.

## Searching for somebody whose name is encrypted

The portals do the decryption. They do **not** do the searching, and the
distinction is worth being precise about because it is easy to assume
otherwise: a search box sends the term to the API exactly as the person
typed it, and the API turns it into hashes and runs the query. The browser
never holds a hash, never holds the key, and never sees a row it was not
allowed to see.

```
"priya"  ─►  GET /api/users?q=priya          the term, as typed
                    │
                    │  the API hashes it: index_of() for a whole contact,
                    │  search_ngrams() for part of a name
                    ▼
             WHERE email_hash = … OR full_name_ngrams @> …
                    │
                    ▼
             rows, names still SE::…  ─►  the interceptor opens them  ─►  the table
```

**What a person can search by**, and what the fields say:

| Typed | Matched against | Field |
|---|---|---|
| Part of a name, three characters up | the hashed runs beside the name | `Name, or a whole email, mobile or id` (users), `Name, email or mobile` (the audit About picker) |
| A whole email, mobile, username or employee id | that value's own hash | the same boxes |
| A reference, a uuid, a project | the plaintext column, as before | the requests list |

Half an address matches nothing, deliberately: a contact carries no runs, so
all its hash ever leaks is equality. A term under three characters produces
no runs and falls back to the exact comparisons, rather than matching every
row — an empty set is contained in every set, and a search box that answered
"everyone" to two characters would be worse than one that answered nothing.

**Nothing in the portals changed to make this work.** The search boxes
already sent `q`; what changed is what the API does with it. That is the
property worth keeping: a portal knows which values are personal only
because they arrive with a prefix, and it knows nothing at all about how
they are found.

## The three files

| File (same in both portals) | Role |
|---|---|
| [`src/lib/dkms/deep.ts`](../../frontend/console/src/lib/dkms/deep.ts) | The walker: finds every `SE::`, reads the data type off byte 3 of the envelope, batches, puts plaintext back in place. A refused batch is retried one value at a time so one bad value costs only itself; an unreachable service leaves values as they arrived, visibly |
| [`src/lib/dkms/api.ts`](../../frontend/console/src/lib/dkms/api.ts) | `decryptRecords()`: the call to `/dkms/decrypt`; error messages name the service and its answer |
| [`src/app/dkms/decrypt/route.ts`](../../frontend/console/src/app/dkms/decrypt/route.ts) | The server route: session required, the pure contract to `${DKMS_URL}/bulk_decrypt`, 10 s bound, one diagnostic log line on failure naming the host and never a value |

Configuration is one variable per portal, **required, no fallback**:

```
# frontend/console/.env.local, frontend/portal/.env.local
DKMS_URL=http://<ip>:32688
```

The service it names must be the one the API encrypts with (the API's own
`DKMS_URL`), reachable from the portal's server, and the portal restarted
after the change. Each failure looks the same on the page - `SE::…` where a
name should be - so the portal's log says which: `[dkms] … unreachable`,
`answered 422`, or `DKMS_URL is not set`.

## What breaks it, and the guard for each

| Failure | Symptom | Guard |
|---|---|---|
| A sealed column **concatenated in SQL** with other text (`u.full_name \|\| ' — ' \|\| p.project_name`) | A string that starts `SE::` but is not an envelope; the key service refused the whole batch, and every name on the notifications page stayed sealed | Labels that name a person return `label_parts` (the name sealed among plain pieces) and the reader joins them after opening; `tests/unit/infrastructure/test_no_sealed_column_is_concatenated.py` fails the build on the next `\|\|` against a sealed column |
| A value the service **cannot open** (wrong key, tampered) | Would have sunk the batch | The walker retries one by one; the bad value stays as it arrived and is counted in the log, never quoted |
| Service **unreachable** / not configured | 503 from the route | The page still renders with the ciphertext showing; both logs name the host |
| Browser reaching the key service directly | Not possible: `DKMS_URL` is server-only, not `NEXT_PUBLIC_`; the service has no CORS | By construction |
| A **type id** the walker does not know | Value skipped, stays sealed | `TYPE_BY_ID` in `deep.ts` mirrors the service's `TYPE_IDS` (13 types); `deep.test.ts` reads real envelopes |
| A search finding **nobody** when somebody exists | The row's runs are missing or were written under a different key | The runs are written with the row, in the repository; `BLIND_INDEX_KEY` and the key service's `DKMS_HASH_KEY` must match. `tests/integration/test_search_over_sealed_names.py` covers the write, the rename and the miss |
| A search finding **everybody** | A term too short to have runs, with the clause still applied | The clause is added only when the term yields runs; pinned by a test that searches for two characters and expects nothing |

## How it was checked end to end

A browser, signed in as each role, following every link once, with three
counters on the wire: API responses whose body contains `"SE::`, calls to
`/dkms/decrypt` and their status, and pages whose rendered text contains
`SE::`. Against the running stack on 2026-09-22:

| Signed in as | Pages | Sealed API responses | Decrypt calls (failed) | Pages showing `SE::` |
|---|---|---|---|---|
| DPO (console) | 200 | 489 over 23 endpoints | 489 (0) | **0** |
| Administrator | 80 | 86 over 6 | 86 (0) | 0 |
| DCO | 22 | 62 over 14 | 62 (0) | 0 |
| R&D user | 47 | 148 over 11 | 148 (0) | 0 |
| Data principal (portal) | 8 | 16 over 5 | 16 (0) | **0** |

Every sealed response produced exactly one decrypt call; none failed; no page
showed ciphertext. The first run of the same walk found the SQL
concatenation above (1 failed batch, 3 pages showing `SE::`), which is what
this document's guards close.

**The search, walked the same way** on 2026-09-22, against the same sealed
rows: typing `priya`, `men` and `Anjali` into the console's users list each
returned the one person whose encrypted name contains it, and `zzz-nobody`
returned none; the audit About picker found the same person by six letters;
a fragment of the domain every test address shares found nobody, which is
the boundary - contacts are matched whole.

The standing tests: `src/lib/api/client.test.ts` (both portals) runs the
real client against MSW - a sealed body comes out opened in one call, nothing
else changed; `e2e/sealed-never-shown.spec.ts` (both portals) checks the
pages that always show a person: the API answered sealed, the page shows the
person; `e2e/audit.spec.ts` finds a data principal by part of her name in a
real browser; the backend's `tests/http` asserts every one of the 159 PII
endpoints serves `SE::…` or null and never plaintext; and
`tests/integration/test_search_over_sealed_names.py` covers the searches
themselves - a fragment finds, a rename is findable under the new name, a
short term finds nobody rather than everybody, and the column holds hashes
and never a name.
