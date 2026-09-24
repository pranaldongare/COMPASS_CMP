# Encryption at rest

Personal data is sealed before it reaches the database, by a separate process
that holds the key, and opened only where a person reads it. This page covers
the security side: what that protects against, what it does not, which keys
exist and where they live, and what is still in the clear. The decision is
[ADR 0016](../decisions/0016-personal-data-sealed-by-a-separate-key-service.md),
the lookup design is [ADR 0017](../decisions/0017-lookup-by-keyed-hash-and-name-ngrams.md),
and the mechanics (the service's contract, the fields, the frontend layer)
are in [docs/dkms/](../dkms/README.md).

## What it protects against

| Threat | Protected? | Why |
|---|---|---|
| A copy of the database: a dump, a backup, a stolen disk, a read-only SQL injection | **Yes**, for sealed columns | The rows hold `SE::` ciphertext and keyed hashes. Neither key is in the database |
| A compromise of the API process alone | **Partly** | The API holds no encryption key and serves ciphertext. It does hold `BLIND_INDEX_KEY`, and it can reach the key service, which opens anything for anyone who can reach it (below) |
| A compromise of the key service alone | **Yes**, for data it has not seen | It holds keys, not rows. It sees the values that pass through it |
| A person with a session reading rows outside their scope | **Not by this** | That is [authorisation](authorization.md). Sealing does nothing for a row the API chose to serve |
| Anyone who can reach the key service on the network | **No** | It authenticates nobody. Isolating it is the control (below) |
| Anyone who can call a portal's `/dkms/decrypt` | **Open question** | See [csrf.md](csrf.md#not-covered-the-portals-own-dkmsdecrypt); under review |

## What is sealed, and what is not

Sealed: every column in `ENCRYPTED_FIELDS`
(`backend/api/src/cmp/infrastructure/dkms/fields.py`). That is names, emails,
mobiles, usernames, employee ids and dates of birth on `auth_user`; the
nominee's name and contacts; a rights request's submitted name and contact and
every free-text field on it and on its holders and tickets; response and
import file names; the IP address on a consent artefact; the respondent's name
and contact; and the reason columns on history, delegation and processor
decisions. The table-by-table list is
[docs/dkms/pii-tables-and-fields.md](../dkms/pii-tables-and-fields.md).

Deliberately not sealed, in the database:

- `auth_user.minor_until`, the date a person stops being a child: kept so the
  section 9 test stays a date comparison. It says nothing else.
- The `*_hash` and `*_ngrams` columns. They are keyed hashes, not values, but
  they are not nothing: see *What the hashes give away*.
- Rows written before a column was sealed, until `scripts/reseal.py` has run.
  The read path accepts both, so nothing forces it; `reseal.py --check`
  reports what is left. How to run it is in the
  [runbook](../operations/runbook.md).

## The two keys

| Key | What it does | Where it lives | Refused in production if |
|---|---|---|---|
| `DKMS_MASTER_KEY` | Every encryption key, derived per data type and key version with HKDF; AES-256-GCM | The key service's environment (`backend/dkms/.env`) and nowhere else | It is the key from `.env.example` |
| `DKMS_HASH_KEY` = `BLIND_INDEX_KEY` | The exact hashes (`*_hash`), the name runs (`*_ngrams`) and the client address in the audit trail | The key service's environment **and** the API's (`backend/api/.env`), as the same string | It is the development key, or shorter than 32 characters (checked on both sides) |

The portals hold neither. They hold `DKMS_URL`, server-side only, and ask the
key service to open what they were served.

The hash key is in two places on purpose. The API computes the hashes itself
so that sign-in and search do not depend on the key service. The cost is that
a compromise of the API's environment yields the hash key, and that the two
copies must never differ: two different keys give two different hashes for one
person, and neither side finds the other's rows.

## What the hashes give away

A hash cannot be decrypted, but with the key anyone can recompute it. The
values it covers are not all hard to guess. An IPv4 address has 2^32
possibilities and a mobile number around 10^10; with `BLIND_INDEX_KEY`, both
can be enumerated in reasonable time. The hash is only as safe as that key.

Without the key, an exact hash reveals equality: which rows share an address.
The `*_ngrams` columns reveal more. Each is a set of hashed three-letter runs,
and counting how often each run occurs across a table can be matched against a
language's letter statistics. With enough rows, common names can be recovered
without the key. That is why there are three such columns, all names, and
never a contact.

## Rotation

**The master key** has versions. `DKMS_KEY_VERSION` says which version new
ciphertext is written under, and `DKMS_PREVIOUS_KEYS` keeps retired keys so
that what they wrote still opens. Adding a version and raising the number is
supported.

**No tool re-encrypts today.** `scripts/reseal.py` seals plaintext and skips
any value that already starts `SE::`, so it does not move old ciphertext to a
new version. After a rotation the old key has to stay in
`DKMS_PREVIOUS_KEYS` for as long as a single row written under it survives,
which without a re-encryption tool means indefinitely.

**The hash key cannot be rotated in place.** There is one hash key and no
notion of a version. Changing it changes every hash, so every sign-in and
every uniqueness rule stops matching until each hash is recomputed, which
means opening each sealed value and hashing it again. **No tool re-hashes
today.** 0028's backfill did this once, when the columns were created.
`reseal.py` computes a hash only for a value it is sealing for the first time.

## Losing a key

**The master key, with its previous versions, is the only way to read what it
sealed.** Lose it and every sealed column is gone for good: names, contacts,
the words of every rights request, the address on every consent artefact.
The consent evidence the platform exists to keep would survive as rows that
cannot be read. Nothing in this repository backs the key up or escrows it.
That is a deployment's job, and it has to be done before the first real row
is written.

**Losing the hash key** leaves the data readable but unfindable: nobody can
sign in, and no contact can be looked up, until a new key is chosen and every
hash recomputed. As above, no tool does that today.

## Isolating the key service

The key service **authenticates nobody**. Anyone who can reach its port can
open any ciphertext they hold (`/bulk_decrypt`) and compute any hash
(`/bulk_hash`, `/search`, `/search_ngram`). So it must be reachable only by
the API, the worker and the two portals' servers:

- It binds `127.0.0.1` by default (`HOST`). A caller on another machine needs
  `HOST=0.0.0.0` or a specific interface, and then a firewall rule admitting
  only those callers. `backend/dkms/.env.example` says so beside the setting.
- `CORS_ORIGINS` is empty, so no browser page can call it. A wildcard is
  refused outside local development.
- The portals' `DKMS_URL` is not `NEXT_PUBLIC_`: the browser never learns
  where the service is.

One leak remains. The API's public `GET /ready` reports the key service as its
`encryption` check, and on failure the `detail` names its URL and the
connection error (`infrastructure/dkms/client.py`, `healthcheck`). An
unauthenticated caller can learn the key service's address that way.

## Residual plaintext

What is still in the clear, outside the sealed columns. The full store-by-store
inventory is [docs/domain/personal-data.md](../domain/personal-data.md).

| Where | What | For how long |
|---|---|---|
| Redis `sess:*` | The session's IP address and user agent | The session (8 hours at most) |
| Redis `rate:*`, and `otp:*` for contact confirmation and consent links | The contact or IP the limit or code is keyed on | The window, an hour at most |
| The Celery broker (Redis) | Task arguments. Some carry a contact in the clear: a data principal's sign-in code goes to the contact she typed; a staff invitation carries the opened address and name; a contact confirmation carries the contact. Others carry it sealed and the worker opens it | Until the task runs |
| `exports/` on disk | The export CSV: names, emails, mobiles and employee ids, opened to write the file | As long as the export is kept |
| `responses/`, `rights/`, `approvals/` on disk | Uploaded and generated files. Their names are sealed in the database; the contents are not encrypted | As long as they are kept |
| `audit_log`, rows before 21 September 2026 | Raw client addresses (2,261 rows) and an email on eleven | For ever; the trail cannot be edited ([ADR 0015](../decisions/0015-nothing-erasable-in-a-trail-nobody-can-erase.md)) |
| `var/outbox.log`, development only | Every message, in full | Until deleted |
| The browser | Opened values on the page. The decrypt route sends `no-store` | The page |

## What fails when the key service is down

Sealing fails closed. A write that cannot be sealed is refused with a 503 and
rolled back rather than stored in the clear. A page still renders, with the
ciphertext showing where the value should be, and the portal's log names the
host it could not reach. A message whose recipient cannot be opened is
retried. `DKMS_ENABLED=false` switches sealing off for development, and
production refuses to start with it off. Where this happens inside a database
transaction, and what it holds while it waits, is in
[transactions.md](../database/transactions.md).
