# DKMS — the backend

Where encryption happens in the platform API, what the key service's own API
is, which endpoints carry personal data, and the four places the backend
decrypts. Companion to [the field list](pii-tables-and-fields.md) and
[the frontend document](frontend-layer.md).

## The rule

**The backend encrypts. The backend does not decrypt for a response.**
Every repository write of a column in `ENCRYPTED_FIELDS` goes through
`seal()`; every read returns the row as stored — `SE::…` — and the API
serves exactly that. Opening values is the portals' job. The four exceptions
are messages, tickets, exports and response packages, listed at the end,
each handing a value to a person outside the browser.

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
| [`infrastructure/dkms/fields.py`](../../backend/api/src/cmp/infrastructure/dkms/fields.py) | The map: `ENCRYPTED_FIELDS` (table → column → type), `BLIND_INDEXED`, `LOOKUP_FIELDS`, `TYPE_IDS` |
| [`infrastructure/dkms/client.py`](../../backend/api/src/cmp/infrastructure/dkms/client.py) | The HTTP client. Fails closed: `DkmsUnavailable` (503) rather than writing plaintext. `unseal_values_sync` for the worker, which has no event loop |
| [`infrastructure/dkms/rows.py`](../../backend/api/src/cmp/infrastructure/dkms/rows.py) | `seal` / `seal_many` / `unseal` / `unseal_value` / `opened` — one call per row however many columns |
| [`infrastructure/dkms/blind.py`](../../backend/api/src/cmp/infrastructure/dkms/blind.py) | `index_of(kind, value)` and the normalisation each kind uses |
| Repositories | The only callers of `seal()`. A write that bypassed one would store plaintext, which is why the seal is here and not in a service |

Settings: `DKMS_URL` (default `http://localhost:32688`), `DKMS_ENABLED`,
`DKMS_TIMEOUT_S`, `BLIND_INDEX_KEY`. Both keys are refused at startup in
production if left at their development values.

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

## The four places the backend decrypts

Each hands a value to a person who is not looking at a browser, so there is
nothing downstream to open it.

| Where | What is opened | Why |
|---|---|---|
| [`infrastructure/messaging.deliver()`](../../backend/api/src/cmp/infrastructure/messaging/__init__.py) | The recipient, and any name in the template | An email cannot be addressed to ciphertext. **This is the step that makes a sign-in code depend on the key service** |
| `rights/service._ticket_address()` | A holder's contact | The ticket's mail goes to a person |
| `exchange/service` — the export CSV | The consents in the file | The file is read outside the platform |
| `rights/service` — the response package | What is released to the data principal | As above |

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
task retries on it, and `/ready` carries an `encryption` check so one curl
answers "can this API reach the key service". The runbook entry is
[No message of any kind is sent](../operations/runbook.md).
