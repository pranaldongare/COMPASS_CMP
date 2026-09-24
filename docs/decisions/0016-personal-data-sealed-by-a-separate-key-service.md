# 0016. Personal data is sealed by a separate key service, and opened only where a person reads it

**Status:** accepted · 2026-09-21

## Context

Until 21 September 2026 every personal value the platform held was plaintext
in PostgreSQL: names, contacts, dates of birth, a rights request in the
person's own words, the address a consent was given from. Access control
decided who could *ask for* a row. Anyone who got the rows another way (a
dump, a backup, a stolen disk, a read-only injection) got all of it.

The brief was that personal data be encrypted before it reaches the
database, and decrypted in the frontend layer rather than in the platform API,
so that the API stores and serves ciphertext and never holds the plaintext it
is protecting.

## Decision

- **A separate process holds the key.** `backend/dkms` is its own FastAPI
  service on port 32688. It derives one AES-256-GCM key per data type and key
  version from `DKMS_MASTER_KEY` with HKDF, and answers `/bulk_encrypt` and
  `/bulk_decrypt` for batches of records. The API holds no encryption key, so
  a compromise of the API alone is not a compromise of the key, and the
  service holds no rows.
- **Sealed on the way in, by the repositories.** Every write of a column in
  `ENCRYPTED_FIELDS` (`cmp.infrastructure.dkms.fields`) passes through
  `seal()` before it is bound: one call per row or per batch, however many
  columns. The repositories are the only callers, because a write that
  bypassed one would store plaintext. The value stored is `SE::` and a
  base64url envelope carrying the key version and the data type.
- **Served as stored; opened by the portals' servers.** The API does not
  decrypt its responses. Each portal walks every JSON response in its API
  client, collects every `SE::` value, and opens them in one request to its
  own server route, `POST /dkms/decrypt`, which forwards them to the key
  service at the server-only `DKMS_URL`. The browser never learns where the
  key service is.
- **The backend opens a value only to act on it.** The recipient and the
  greeting of a message (in the worker, at `deliver()`), a ticket's address,
  the export CSV, a rights response package, an invitation's reset link.
  Never to put it in a response.
- **Fail closed.** A write the key service cannot seal is a 503 and a
  rollback, never plaintext. A message whose recipient cannot be opened is
  retried. `DKMS_ENABLED=false` exists for development, and production
  refuses to start with it.
- **Migration 0027** widened the columns to `text`, because ciphertext is
  longer than what it hides, and made `consent_artefact.ip_address` `text`
  rather than `inet`. The lookup columns followed in 0028, behind a keyed
  hash ([ADR 0017](0017-lookup-by-keyed-hash-and-name-ngrams.md)).
  `scripts/reseal.py` seals the rows written before.

## Consequences

- A copy of the database holds ciphertext and keyed hashes. What it exposes,
  and what is still in the clear elsewhere (Redis keys, task arguments, the
  export files, audit rows from before
  [ADR 0015](0015-nothing-erasable-in-a-trail-nobody-can-erase.md)), is in
  [encryption-at-rest.md](../security/encryption-at-rest.md).
- **Losing `DKMS_MASTER_KEY` loses the data.** Every sealed column, the consent
  evidence among them, becomes unreadable. Backing the key up is a deployment
  obligation this repository does not meet on its own.
- The key service is a dependency of every write that carries personal data
  and of every page that shows it. `/ready` reports it. Its HTTP call happens
  inside the database transaction of the write, which can hold the audit
  chain's lock across a network round trip
  ([ADR 0005](0005-audit-chain-position-inside-the-lock.md), amended;
  [transactions.md](../database/transactions.md)).
- **The key service authenticates nobody.** Anyone who can reach it can open
  any ciphertext. It binds loopback by default and must be firewalled to its
  callers when it does not.
- **The portals' decrypt route checks only that a session cookie is
  present.** It does not validate the session, check a CSRF token, rate-limit
  or confirm that the values it is asked to open are ones the API served that
  caller (`frontend/*/src/app/dkms/decrypt/route.ts`). Its design note relies
  on the API having served only rows the caller may read, and the route does
  not enforce that. **This is an open question, under review**, and is not
  settled by this record; see [csrf.md](../security/csrf.md#not-covered-the-portals-own-dkmsdecrypt).
- A substring search over a sealed column matches nothing. Exact lookups and
  name search came back through hashes
  ([ADR 0017](0017-lookup-by-keyed-hash-and-name-ngrams.md)).
- The database can no longer check a sealed value: `dob_is_plausible` went
  when `dob` became sealed text, and length limits are the API's
  ([schema.md](../database/schema.md)).
- Resealing history touched the append-only tables. How, and why that is under
  review, is in the amendment to
  [ADR 0002](0002-evidence-enforced-in-the-database.md).
- Rotating the master key is supported for new writes (`DKMS_KEY_VERSION`,
  `DKMS_PREVIOUS_KEYS`), but no tool re-encrypts existing rows, so a retired
  key is needed for as long as anything it wrote survives.

## Revisit when

A vendor key-management service replaces the local scheme (`DKMS_PROVIDER=sdk`
exists for this); the decrypt route's review concludes; or a consumer outside
the two portals needs plaintext, which would need its own trust decision
rather than a copy of this route.
