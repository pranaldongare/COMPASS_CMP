# COMPASS DKMS

Bulk field encryption and decryption for personal data. A separate service, on
its own port, holding one secret and doing one thing with it.

Separate on purpose. The platform API holds the database; this holds the key
that makes the database readable. Putting both in one process means one
compromise is both, and it means the key rotates on the platform's release
schedule rather than its own.

```
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 -m app.main                 # http://127.0.0.1:8100
```

`GET /health` says what it is running. `GET /docs` is the interactive reference.

## The two operations

Both take a batch of records and a mapping of field names to data types. **Only
the fields named in `key` are touched**; every other field passes through
exactly as it arrived.

### `POST /encrypt/bulk`

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

### `POST /decrypt/bulk`

The same body, with encrypted values in, plaintext out. The data type in `key`
must be the one the value was written under.

### `method`

| Value | Uses | Returns |
|---|---|---|
| `string` (default) | `encrypt()` / `decrypt()` | `SE::`-prefixed string |
| `bytes` | `encrypt_bytes()` / `decrypt_bytes()` | base64, no prefix |

Both carry identical bytes. A value written one way reads back the other, so a
column that changes form does not orphan its rows.

### Two optional fields

Neither changes the contract: leave them out and the behaviour is the original.

| Field | Default | What it does |
|---|---|---|
| `on_error` | `fail` | `fail` refuses the whole batch with a 422 naming the record index, the field and why. `skip` leaves that one value as it arrived and reports it in `errors` — what a migration over rows of unknown vintage needs |
| `skip_encrypted` | `true` | On encrypt, a value that is already `SE::` ciphertext is left alone. A batch run twice is not encrypted twice, which one decrypt would not undo |

## Data types

`GET /types` publishes the roster. It comes from
[docs/domain/personal-data.md](../docs/domain/personal-data.md), the inventory
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
`DKMS_PREVIOUS_KEYS` as `{"1": "<base64>"}`. New writes use the new key, old
ciphertext still opens, and you re-encrypt at leisure. A test walks it.

**The property that shapes everything above it:** ciphertext is randomised, so
the same address encrypts differently every time. That is correct for data at
rest and it means **an encrypted column cannot be looked up, joined, sorted or
uniquely indexed**. Any field the platform searches by — the email you sign in
with, the mobile a code goes to — needs a deterministic blind index alongside
the ciphertext before it can be encrypted. See *Integration* below.

## Parallelism

`cryptography` calls OpenSSL, which releases the GIL, so a thread pool here is
real parallelism rather than turn-taking. The pool is built once at startup;
records are cut into chunks (`DKMS_CHUNK_SIZE`, default 64) and each chunk is
one task. Chunks rather than records because the hand-off costs more than one
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

- Starting on the `.env.example` master key outside `local`/`test`. Everything
  encrypted under it is readable by anyone holding this repository.
- A wildcard in `CORS_ORIGINS`.

## Integration

| Side | How |
|---|---|
| Platform API | `cmp.infrastructure.dkms` — a client that batches a write's personal fields into one call rather than one call per field |
| Portals | Decryption happens in the portal's **server** layer (`/api/dkms/decrypt`), not in the browser. The browser never holds a key, and a decrypt is a request an authenticated session makes for rows it was already allowed to read |

The fields worth encrypting, and the ones that cannot be until they have a
blind index, are listed in
[docs/domain/personal-data.md](../docs/domain/personal-data.md).

## Checks

```
.venv/bin/python -m pytest tests     # 35 tests
.venv/bin/python -m ruff check app tests
.venv/bin/python -m mypy app
```
