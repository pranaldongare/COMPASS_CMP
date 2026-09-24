# COMPASS DKMS

Bulk field encryption and decryption for personal data, and the keyed hashes
that let a sealed column still be looked up. A separate service, on its own
port, holding two secrets: the master key everything is sealed under, and
the hashing key.

Separate on purpose. The platform API holds the database; this holds the key
that makes the database readable. Putting both in one process means one
compromise is both, and it means the key rotates on the platform's release
schedule rather than its own.

```
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt   # requirements.txt alone to run it; -dev adds pytest, ruff, mypy
cp .env.example .env
python -m app.main                    # http://127.0.0.1:32688
```

Start it before the platform API, the worker and `scripts/seed.py`: with
`DKMS_ENABLED=true` every personal field they write is sealed through it.

`GET /health` says what it is running. `GET /docs` is the interactive reference.
The service listens on **32688**. The platform API's `DKMS_URL` defaults to
`http://localhost:32688`. Each portal's `DKMS_URL` is required and has no
default; its `.env.example` carries the placeholder `http://<ip>:32688`, which
locally becomes `http://localhost:32688`.

It binds `127.0.0.1` by default. A portal or API on another machine cannot
reach loopback, and every decrypt then fails; set `HOST` to the interface the
callers use, and put a firewall rule in front of it - the service
authenticates nobody.

Every setting is in `.env.example` and in
[configuration.md](../../docs/operations/configuration.md#the-key-service-itself).
The design is in [docs/dkms/](../../docs/dkms/README.md) and
[ADR 0016](../../docs/decisions/0016-personal-data-sealed-by-a-separate-key-service.md);
keys, rotation and the threat model in
[encryption-at-rest.md](../../docs/security/encryption-at-rest.md).

## Encrypt and decrypt

Both take a batch of records and a mapping of field names to data types. **Only
the fields named in `key` are touched**; every other field passes through
exactly as it arrived. A batch larger than `DKMS_MAX_RECORDS` (5000) is
refused with 413.

### `POST /bulk_encrypt`

```json
{
    "data": [
        {"employeeID": "E-0001", "fullName": "Amruta Shukla", "emailId": "amruta@example.org"},
        {"employeeID": "E-0002", "fullName": "Anuj Kumar", "emailId": "anuj@example.org"}
    ],
    "key": {"fullName": "NAME", "emailId": "EMAIL"},
    "method": "string"
}
```

```json
{
    "data": [
        {"employeeID": "E-0001", "fullName": "SE::REsBAcxeNgor...", "emailId": "SE::REsBAjWbQ-kh..."},
        {"employeeID": "E-0002", "fullName": "SE::REsBAQIJuiQJ...", "emailId": "SE::REsBArzU-zE3..."}
    ],
    "method": "string", "records": 2, "values": 4, "skipped": 0, "errors": [],
    "took_ms": 1.6, "provider": "local-aes-gcm", "workers": 14
}
```

### `POST /bulk_decrypt`

The same body, with encrypted values in, plaintext out. The data type in `key`
must be the one the value was written under.

### `method`

| Value | Uses | Returns |
|---|---|---|
| `string` (default) | `encrypt()` / `decrypt()` | `SE::`-prefixed string |
| `bytes` | `encrypt_bytes()` / `decrypt_bytes()` | base64, no prefix |

Both carry identical bytes. A value written one way reads back the other, so a
column that changes form does not orphan its rows.

### Optional fields

None changes the contract: leave them out and the behaviour is the original.
The contract itself is `{data, key, method}`, and the platform sends nothing
more, so any service that implements it can stand behind this one.

| Field | Default | What it does |
|---|---|---|
| `on_error` | `fail` | `fail` refuses the whole batch with a 422 naming the record index, the field and why. `skip` leaves that one value as it arrived and reports it in `errors` — what a migration over rows of unknown vintage needs |
| `skip_encrypted` | `true` | On encrypt, a value that is already `SE::` ciphertext is left alone. A batch run twice is not encrypted twice, which one decrypt would not undo |
| `with_hash` | `false` | On encrypt, also return `<field>_hash`: the exact-match hash of each value, for the caller to store beside the ciphertext |
| `with_ngrams` | `false` | On encrypt, also return `<field>_ngrams`: the hashed character runs that make substring search possible. Only for fields searched by part of a value; they leak more than the exact hash |
| `ngram_size` | 3 | Characters per run, 2–8 |

## Hashing and search

Ciphertext is randomised, so the same address encrypts differently every
time. That is right for data at rest and means **a sealed column cannot be
looked up, joined, sorted or uniquely indexed**. So beside each sealed
lookup column the caller stores a keyed hash,
`HMAC-SHA256(normalised value)` under `DKMS_HASH_KEY`: deterministic, so it
can be indexed and compared; keyed, so it says nothing without the key
([ADR 0017](../../docs/decisions/0017-lookup-by-keyed-hash-and-name-ngrams.md)).

The platform API computes the same hashes itself, under its
`BLIND_INDEX_KEY`, so that sign-in keeps working while this service is
down. **`DKMS_HASH_KEY` must equal the platform's `BLIND_INDEX_KEY`, to the
character**; two keys mean two hashes for one person, and neither side
finds the other's rows. These endpoints are for any other caller.

Values are normalised before hashing, by the platform's rules: an email is
trimmed and lowercased, a mobile goes to its canonical form, a contact is
an email if it has an `@` and a mobile otherwise.

### `POST /bulk_hash`

The hashing alone, for a caller with no ciphertext to write. The same
`data` and `key` as encrypt, plus `with_ngrams` and `ngram_size`; each named
field is replaced by its hash.

```json
{"data": [{"e": "a@x.org"}], "key": {"e": "EMAIL"}}
```

```json
{"data": [{"e": "d50844f9ccfc...d0a8"}], "records": 1, "values": 1, "took_ms": 0.008}
```

Usually unnecessary: `/bulk_encrypt` with `with_hash` returns the ciphertext
and the hash together, the one moment both forms exist.

### `POST /search`

The hash of one whole term, for `WHERE <field>_hash = :hash`.

```json
{"term": "Amruta@Example.org ", "type": "EMAIL"}
```

```json
{"term_normalised": "amruta@example.org", "hash": "978ace4d...0b00", "sql": "<field>_hash = :hash"}
```

Half an address hashes to something no row holds; that is what the next one
is for.

### `POST /search_ngram`

The hashed runs a row must contain, all of them, for the term to be inside
it: `WHERE <field>_ngrams @> :ngrams`, answered by a GIN index.

```json
{"term": "shu", "type": "NAME", "ngram_size": 3}
```

```json
{"term_normalised": "shu", "ngrams": ["6f4f2910..."], "ngram_size": 3, "sql": "<field>_ngrams @> :ngrams"}
```

The answer is candidates, not certainties: a row holding every run of
"ana" and "nan" may be "banana" or "ananas", so a caller that needs certainty
opens the candidates and checks. A term shorter than the run length is
refused with 422 rather than answered with an empty list.

## Data types

`GET /types` publishes the roster. It comes from
[docs/domain/personal-data.md](../../docs/domain/personal-data.md), the inventory
of what this platform holds about people.

`NAME` · `EMAIL` · `MOBILE` · `CONTACT` · `DOB` · `ORG_ID` · `PERSON_TYPE` ·
`ADDRESS` · `IP` · `FREE_TEXT` · `FILE_NAME` · `GOVT_ID` · `GENERIC`

**The type is bound into the ciphertext**, as additional authenticated data. A
value written as `MOBILE` will not open as `NAME` even for somebody holding
every key — the tag check fails and the service says so. A wrong key mapping is
a refusal, not a column of plausible rubbish.

## What it does underneath

One master key. Each data type gets its own key, derived by HKDF-SHA256, so a
compromise limited to one type stays limited to it. Each value is AES-256-GCM
under a fresh 12-byte nonce. The envelope is

```
| 'D' | 'K' | key version | type id | nonce (12) | ciphertext + tag |
```

base64url-encoded behind `SE::`, or standard-base64 for the bytes form. The
header is the AAD, so flipping the version or the type byte produces a refusal
rather than a different plaintext.

**Rotation.** Raise `DKMS_KEY_VERSION` and put the old key in
`DKMS_PREVIOUS_KEYS` as `{"1": "<base64>"}`. New writes use the new key and
old ciphertext still opens. A test walks it. Nothing in the repository
re-encrypts old ciphertext under the new version: `scripts/reseal.py` seals
plaintext and skips anything already `SE::`. Rotating the hashing key is a
different operation, because every stored hash changes; both are in
[encryption-at-rest.md](../../docs/security/encryption-at-rest.md).

## Parallelism

`cryptography` calls OpenSSL, which releases the GIL, so a thread pool here is
real parallelism rather than turn-taking. The pool is built once at startup;
records are cut into chunks (`DKMS_CHUNK_SIZE`, default 64) and each chunk is
one task. The pool has `DKMS_POOL_WORKERS` threads, or one per core up to 32
when that is 0. Chunks rather than records because the hand-off costs more than one
short string; chunks rather than one slice per worker because then the longest
record decides when everybody finishes.

Order is preserved: `data[3]` out is `data[3]` in. Records are copied, never
mutated.

Measured on this machine, 14 workers: **5,000 records × 3 fields = 15,000
values in 74 ms**, about 200,000 values a second.

## A vendor SDK

There is none in this repository, so the service runs on the local scheme
above. When one arrives:

```
DKMS_PROVIDER=sdk
DKMS_SDK_MODULE=vendor_dkms
DKMS_SDK_FACTORY=get_client
```

`app/dkms/sdk.py` adapts any client exposing `encrypt`, `decrypt`,
`encrypt_bytes` and `decrypt_bytes`. If the names differ, that one file changes
and nothing above it knows. A deployment that asks for the SDK and cannot load
it **fails at startup**, not on the first record of the first batch.

## What production refuses

Outside `ENVIRONMENT=local` or `test`, the service will not start on:

- The `.env.example` master key. Everything encrypted under it is readable by
  anyone holding this repository.
- The `.env.example` hashing key, or one under 32 characters. Every hash
  computed under it can be recomputed by anyone holding this repository.
- A wildcard in `CORS_ORIGINS`.

## Integration

| Side | How |
|---|---|
| Platform API | `cmp.infrastructure.dkms` — `seal()` at every repository write of a personal column, one call per row; `unseal*()` only where the backend hands a value to a person (messages, tickets, exports, the response package). The lookup hashes and name n-grams are computed locally in `blind.py` under `BLIND_INDEX_KEY` |
| Portals | Every API response is walked by the client and every `SE::` value opened in one call to `/dkms/decrypt`, which runs in the portal's **server** layer, not the browser, and posts to `${DKMS_URL}/bulk_decrypt`. The browser never holds a key, and a decrypt is a request an authenticated session makes for rows it was already allowed to read |

Which fields are sealed, and which carry a hash or n-grams beside them, is in
[docs/dkms/pii-tables-and-fields.md](../../docs/dkms/pii-tables-and-fields.md);
the platform's side of the service is
[docs/dkms/backend-api.md](../../docs/dkms/backend-api.md).

## Checks

With `requirements-dev.txt` installed; nothing else needs to be running.

```
.venv/bin/python -m pytest tests     # 55 tests
.venv/bin/python -m ruff check app tests
.venv/bin/python -m mypy app
```
