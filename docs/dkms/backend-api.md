# DKMS — the backend

Where encryption happens in the platform API, what the key service's own API
is, which endpoints carry personal data, and the places the backend
decrypts. Companion to [the field list](pii-tables-and-fields.md) and
[the frontend document](frontend-layer.md); why the key sits in a separate
service at all is [ADR 0016](../decisions/0016-personal-data-sealed-by-a-separate-key-service.md),
and the threat model is [encryption at rest](../security/encryption-at-rest.md).

## The rule

**The backend encrypts. The backend does not decrypt for a response** -
with one exception, the anonymous nomination link, which has no session for
a portal's decrypt route to accept. Every repository write of a column in
`ENCRYPTED_FIELDS` goes through `seal()`; every read returns the row as
stored — `SE::…` — and the API serves exactly that. Opening values is the
portals' job. The places the backend opens a value itself are listed at the
end: each hands a value to a person outside the browser, or needs the
plaintext to compute a hash.

```
           write                                    read
  router → service → repository.seal()      repository → router → SE::… on the wire
                          │                                            │
                          ▼                                            ▼
              POST /bulk_encrypt                                 the portal opens it
```

## The key service

A separate FastAPI service, `backend/dkms`, on port **32688**. Five
endpoints: three that act on batches of records, two that answer "what
should I look for".

```
POST /bulk_encrypt        POST /bulk_decrypt        POST /bulk_hash
{
  "data":   [ {"NAME": "Amruta Shukla"}, {"EMAIL": "a@x.org"} ],
  "key":    {"NAME": "NAME", "EMAIL": "EMAIL"},
  "method": "string"                       // or "bytes"
}
→ { "data": [ {"NAME": "SE::…"}, {"EMAIL": "SE::…"} ] }
```

`/bulk_encrypt` takes two more options that turn one call into everything a
row needs: `with_hash` returns `<field>_hash` beside each encrypted field,
and `with_ngrams` returns `<field>_ngrams`. Both are taken from the
plaintext, which is why they are offered here - encrypting is the one moment
both forms exist. Off by default, so the contract is what it always was
unless it is asked for.

`/bulk_hash` does the hashing alone, for a caller that has no ciphertext to
write: a backfill, or a second system that stores its own index.

```
POST /search                          POST /search_ngram
{ "term": "a@x.org", "type": "EMAIL" }  { "term": "shu", "type": "NAME" }
→ { "hash": "…", "sql": "<field>_hash = :hash" }
→ { "ngrams": ["…","…"], "sql": "<field>_ngrams @> :ngrams" }
```

The service holds keys, not rows: it cannot search anything, and says so by
answering with the tokens a caller's own `WHERE` clause needs. `/search` is
for a whole value - an address, a number - and `/search_ngram` for part of
one, which is refused below three characters rather than answered with an
empty list that would read as "nothing matched".

Optional on the bulk calls, defaults behaving as the plain contract does:
`on_error` (`fail` | `skip`), `skip_encrypted`. Aliases `/encrypt/bulk` and
`/decrypt/bulk` answer the same. `GET /health` and `GET /types` are the
operational surface.

## Standing behind this with another key service

`backend/dkms` is a working implementation, not a requirement. Another
service can take its place, and what it has to provide is smaller than what
this one offers:

| Needed | Why |
|---|---|
| `POST /bulk_encrypt` | every write of a personal column |
| `POST /bulk_decrypt` | the portals' `/dkms/decrypt` route, the worker addressing a message, the export |
| `{data, key, method}` accepted, `{data}` returned | the contract. The API's request-time client and the portals' route send exactly this and nothing more |

`/bulk_hash`, `/search` and `/search_ngram` are **not** called by the
platform: it computes the same hashes locally from `BLIND_INDEX_KEY`, so
that a sign-in and a search still work when the service is unreachable.
They are there for anything else that stores its own index.

`on_error` and `skip_encrypted` are this implementation's extensions. The
request-time client (`DkmsClient._call`) sends neither, and arranges what
they did on its own side: only values that need the work travel — an
already sealed value is held back from an encrypt, and only sealed values
are sent to a decrypt, so a row written before sealing was switched on
passes through untouched rather than failing a batch. What `on_error="fail"`
meant survives as a check on the answer, on every encrypt and on a decrypt
asked to fail: a value that travelled and came back unchanged raises
`DkmsUnavailable`, naming the field. (The row helpers decrypt with
`on_error="skip"`, so a value the service hands back unopened is left as it
was.)

**Known gap, under review: the worker's path is not contract-only yet.**
`unseal_values_sync` in `client.py` - the synchronous call that opens a
message's recipient and template variables, and that migration 0030's
backfill used - still sends `"on_error": "fail"` in its `/bulk_decrypt`
body. A service that forbids unknown fields refuses that with a 422, the
message task retries, and nothing is sent. Until it changes, a replacement
service has to tolerate that one extra field.

**The one thing to know about the ciphertext.** The platform prefers to read
a value's data type off the envelope this implementation writes — `'D' 'K'
version type_id …` — because that lets a portal open a value knowing nothing
about the field it came from. A service writing a different envelope is
supported where there is a field name to go by: both portals fall back to
the field's own name (`lib/dkms/field-types.ts`), and a field in neither
envelope nor list is reported by name in the portal log — `[dkms] sealed
value(s) no type could be read for` — rather than left silently sealed on
the page. On the backend, `unseal` and `unseal_many` name each column's
type from `ENCRYPTED_FIELDS` anyway, and `unseal_value` falls back to it
when the envelope does not parse.

**Known gap, under review:** `unseal_values_sync` has no field name to fall
back to - it is handed bare strings - so a value that begins `SE::` but
whose envelope it cannot read raises `DkmsUnavailable` ("carry no readable
envelope"). Against a service writing a different envelope, that is every
message: the recipient cannot be opened, the task retries, and no email or
SMS goes out.

**Two keys.** `DKMS_MASTER_KEY` encrypts; `DKMS_HASH_KEY` hashes. Separate,
so a hash says nothing about an encryption key and either can be rotated
alone. The hash key is shared with the platform - `BLIND_INDEX_KEY` is the
same string - for one reason worth stating plainly: the platform computes
the same hashes locally, so that people can still sign in when this service
is unreachable. That makes the labels and the normalisation a contract
between two codebases; `tests/test_searchable.py` pins them on one side and
`tests/unit/infrastructure/` on the other.

**The envelope.** `'D' 'K' version type_id nonce ciphertext+tag`, base64url,
prefixed `SE::`. AES-256-GCM with a per-type key derived from
`DKMS_MASTER_KEY` by HKDF, so a value sealed as a `NAME` cannot be opened as
an `EMAIL`. The type id in byte 3 is what lets a reader open a value knowing
nothing about which column it came from.

## Where the backend touches it

| Module | Role |
|---|---|
| [`infrastructure/dkms/fields.py`](../../backend/api/src/cmp/infrastructure/dkms/fields.py) | The map: `ENCRYPTED_FIELDS` (table → column → type), `BLIND_INDEXED` (the eight `*_hash` columns), `NGRAM_INDEXED` (the three `*_ngrams` columns, with the reason each earns one), `LOOKUP_FIELDS` (now only `minor_until`), `TYPE_IDS`, and `PREFIX` - `"SE::"`, the one constant every "is this ciphertext" asks |
| [`infrastructure/dkms/client.py`](../../backend/api/src/cmp/infrastructure/dkms/client.py) | The HTTP client. Fails closed: `DkmsUnavailable` (503) rather than writing plaintext. `unseal_values_sync` for the worker, which has no event loop |
| [`infrastructure/dkms/rows.py`](../../backend/api/src/cmp/infrastructure/dkms/rows.py) | `seal` / `seal_many` / `unseal` / `unseal_value` / `opened` — one call per row however many columns |
| [`infrastructure/dkms/blind.py`](../../backend/api/src/cmp/infrastructure/dkms/blind.py) | Both hashes, computed locally: `index_of(kind, value)` for the whole-value lookup, `ngrams_of(value)` and `search_ngrams(term)` for the substring one, and the normalisation each uses. The key service computes the same values from the same key; this exists so a sign-in and a search still work when it is unreachable |
| Repositories | The only callers of `seal()`. A write that bypassed one would store plaintext, which is why the seal is here and not in a service |

Settings: `DKMS_URL` (default `http://localhost:32688`), `DKMS_ENABLED`
(default **false**), `DKMS_TIMEOUT_S` (5 s), `DKMS_BATCH_SIZE` (500 records
a call), `BLIND_INDEX_KEY`. The API and the worker are separate processes
with separate environments, and **both** need `DKMS_ENABLED=true` and the
same `DKMS_URL`: the worker is the one that opens a message's recipient.
The API refuses to start in production with `DKMS_ENABLED` off or
`BLIND_INDEX_KEY` at its development value; the key service refuses its own
development keys anywhere but `local` and `test`. `BLIND_INDEX_KEY` must equal the key service's
`DKMS_HASH_KEY` - nothing checks that, and a mismatch shows as searches and
sign-ins that find nobody.

## Writing a row: three things at once

A write of a personal column produces up to three values, and all of them
come from the plaintext, in the repository, at the one moment it exists:

```
full_name = "Amruta Shukla"
   │
   ├─ seal()        → full_name        = "SE::REsBAQNY0o7r…"   the value at rest
   ├─ index_of()    → <column>_hash    = "9f3c…"  (64 hex)     found whole
   └─ ngrams_of()   → <column>_ngrams  = {"a1b2…", "c3d4…", …} found by part
```

Which columns get which is `BLIND_INDEXED` and `NGRAM_INDEXED`; a column in
neither is sealed and never searched. A repository that writes a name
without its runs produces a row nobody can find, so the write and the
hashing are one statement, never two.

The key service does the same arithmetic — `/bulk_encrypt` with `with_hash`
and `with_ngrams` returns all three in one call — for any other system
storing its own copy. The platform does not call it for this: migration
0030's backfill opened each existing name with `unseal_values_sync` and
computed the runs locally with `ngrams_of`, the same function the
repositories write with.

## Finding a row: which lookup answers which question

| The question | The clause | Where |
|---|---|---|
| "Sign this person in" / "is this address taken" | `email_hash = %s` | `users.credentials_by_login`, `by_contact` |
| "Which request did this contact send" | `submitted_contact_hash = %s` | `rights.search` |
| "Find the nomination naming this person" | `nominee_email_hash = %s`, `nominee_mobile_hash = %s` | `rights.nominations_naming` |
| "Who is this, I have part of the name" | `full_name_ngrams @> %s` | `users.list_users`, `audit_lookup.lookup` |
| "Which request is this, I have part of the name" | `submitted_name_ngrams @> %s` or the matched account's `full_name_ngrams` | `rights.search`, `audit_lookup.lookup` |

The first three are exact and leak only equality. The last two are
candidates — a row holding the runs of "ana" might be "banana" — and leak
letter statistics, which is why only three columns have them
([ADR 0017](../decisions/0017-lookup-by-keyed-hash-and-name-ngrams.md)).
Both are computed the same way on the way in and on the way out, so a
search never needs to decrypt anything to decide what to compare.

`rights.search` answers `GET /requests?q=`, which the console's requests
list does not send today; the audit trail's About picker is where a request
is found by name in practice. `nominee_name_ngrams` is written with every
nomination and read by no query yet.

## The endpoints that carry personal data — 159

By module, as the documentation generator counts them:

| Module | Endpoints | Module | Endpoints |
|---|---|---|---|
| `/requests/*` — rights, the office's side | 35 | `/consents/*` | 4 |
| `/me/*` — a principal's own records | 21 | `/tickets/*` | 4 |
| `/projects/*` | 17 | `/collections/*` | 3 |
| `/users/*` | 13 | `/links/*` | 3 |
| `/auth/*` | 11 | `/imports/*` | 3 |
| `/rights/*` — public | 8 | `/processors/*` | 2 |
| `/c/{token}/*` — the consent link | 6 | `/exports/*` | 2 |
| `/notices/*` | 5 | `/approvals` | 1 |
| `/audit/*` | 5 | `/dashboard` | 1 |
| `/messages/*` | 5 | `/sites/*` | 1 |
| `/sources/*` | 5 | `/delegations/*` | 4 |

Every one of them is exercised by `backend/api/tests/http/`, and every
response is checked against one contract: a field named in `contract.SEALED`
is `SE::…` or null, and nothing under a contact's name looks like an address.
The per-endpoint field list is
[pii-fields-and-endpoints.md](../domain/pii-fields-and-endpoints.md).

## Where the backend decrypts

Each hands a value to somebody who is not looking at a portal page, or
needs the plaintext to compute what is stored beside it. Nothing here is
handed to a session-bearing response.

| Where | What is opened | Why |
|---|---|---|
| [`infrastructure/messaging.deliver()`](../../backend/api/src/cmp/infrastructure/messaging/__init__.py) | The recipient, and every sealed template variable | An email cannot be addressed to ciphertext. **This is the step that makes a sign-in code depend on the key service** |
| `rights/service._ticket_address()` | A holder's contact | The ticket's mail goes to a person |
| `rights/service._tell_holder()`, `_tell_office()`; `opened_brief()` in `issue_tickets` and `reassign_holder` | The author's name on a ticket message; the subject's name and contacts in a brief | The prose of the mail |
| `exchange/service` — `_project_export`, `render` | The people in the export CSV | The file is read outside the platform |
| `rights/package.build_response()` | What is released to the data principal | As above |
| `rights/service.nomination_from_token()` → `GET /rights/nominations/{token}` | `principal_name`, `nominee_name` | **The one response.** The nominee has no session, and a portal's `/dkms/decrypt` refuses a request without one. The token is single-purpose, expiring and hashed at rest; the contacts are served masked |
| `auth/authentication/service.invite_staff()` | The invited address | It goes into the invitation's URL, which `deliver()` never sees |
| `api/routers/v1/registry.add_respondent()` | A staff account's name and email | The respondent row seals its own copy under its own types; ciphertext copied across would carry the wrong type |
| `db/repositories/rights.create()` | A contact copied off another row | Its `submitted_contact_hash` has to be computed from the plaintext |

Everything else — lists, detail pages, the audit feed, a ticket's brief,
the contact log — leaves sealed.

## What a sealed column changes in SQL

| Was | Is now |
|---|---|
| `WHERE lower(email) = lower(%s)` | `WHERE email_hash = %s` with `index_of("email", typed)` |
| `WHERE full_name ILIKE %s` | `full_name_ngrams @> %s` — the hashed runs of the term, all of which the row must hold. Part of a name finds a person again, from three characters up; a contact has no runs and is still matched whole |
| `u.full_name \|\| ' — ' \|\| p.project_name AS label` | `label_parts`: an array the reader joins **after** opening. A sealed value glued to plaintext is a string nobody can open, and it makes the key service refuse the batch it travels in. `tests/unit/infrastructure/test_no_sealed_column_is_concatenated.py` fails the build on the next one |
| `ORDER BY full_name` | By `created_at`, or by a plaintext column. Ciphertext sorts arbitrarily |
| `CHECK (email ~ '...')` | On the index instead; the format is validated before sealing |

## Failure, and what it looks like

`DkmsUnavailable` is a 503 and names the URL it tried. Writes fail rather
than storing plaintext. Messages are the one failure invisible from outside
— the request answers "a code has been sent" because it queued one — so
`deliver()` logs `message.not_sent` with the service named, every message
task retries on it (five times, backing off to five minutes), and `/ready`
carries an `encryption` check so one curl answers "can this API reach the
key service".

The worker's path refuses to carry ciphertext onward as if it were a value,
and says which of three things went wrong:

| Raised by | Message says | Usually |
|---|---|---|
| `unseal_values_sync` | *n* value(s) are sealed but `DKMS_ENABLED` is false | The worker's environment lacks `DKMS_ENABLED=true`; it defaults to false |
| `unseal_values_sync` | *n* value(s) begin with `SE::` but carry no readable envelope | Another key service's format, a column that truncated it, or text glued to it |
| `deliver()` | the recipient of '*message*' is still sealed after opening | Belt and braces: checked before the channel is chosen, so ciphertext is never mistaken for a mobile number |

The runbook entry is
[No message of any kind is sent](../operations/runbook.md#no-message-of-any-kind-is-sent-and-the-request-said-one-was).
