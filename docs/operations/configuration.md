# Configuration

Four processes read settings: the platform API (and its Celery worker, which
reads the same file but is a separate process with its own environment), the
key service, and the two portals.

| Process | Settings | Template |
|---|---|---|
| API, worker, beat | `backend/api/src/cmp/core/config.py`, 83 fields | `backend/api/.env.example` |
| Key service | `backend/dkms/app/config.py`, 14 fields | `backend/dkms/.env.example` |
| Console, portal | `process.env` in `next.config.ts`, `src/lib/config`, `src/proxy.ts`, `src/app/dkms/decrypt/route.ts` | `frontend/*/.env.example` |

The API's `Settings` refuses an unknown variable (`extra="forbid"`): a typo
fails at startup. `backend/api/.env.example` lists 60 of the 83 fields. The
other 23 have code defaults nobody has needed to change, and are set by
their upper-case name like any other:

`SERVICE_NAME`, `VERSION`, `ROOT_PATH`, `DB_POOL_TIMEOUT_S`,
`DB_LOCK_TIMEOUT_MS`, `COOKIE_NAME`, `CSRF_COOKIE_NAME`, `CSRF_HEADER_NAME`,
`COOKIE_DOMAIN`, `OTP_LENGTH`, `OTP_REQUESTS_PER_CONTACT_PER_HOUR`,
`OTP_REQUESTS_PER_TOKEN_PER_HOUR`, `MFA_TTL_S`, `MFA_MAX_VERIFY_ATTEMPTS`,
`ALLOWED_PROOF_MIME`, `ALLOWED_MANIFEST_MIME`, `DEFAULT_PAGE_SIZE`,
`MAX_PAGE_SIZE`, `PUBLIC_LINK_RATE_PER_MINUTE`, `EXTERNAL_HTTP_RETRIES`,
`STORAGE_BUCKET`, `STORAGE_PREFIX`, `STORAGE_REGION`.

## Production refuses to start on

The API (`_production_guards` in `core/config.py`):

| Condition | Why |
|---|---|
| `SECRET_KEY` is the development default or under 32 bytes | Sessions and cursors are signed with it; a known key means forgeable sessions |
| `POSTGRES_PASSWORD` is `cmp`, `postgres` or empty | A default password is not a password |
| `COOKIE_SECURE` is false | The session travels in cleartext on the first `http://` hop |
| `DEBUG` is true | Turns a handled failure into a traceback carrying local variables |
| `CORS_ORIGINS` contains `*` | With `allow_credentials`, that hands the session to any origin |
| `EMAIL_TRANSPORT` is not `smtp` | The console transport writes nothing outside local/test; a code nobody receives is a sign-in nobody completes |
| `SMS_TRANSPORT` is not `http` | The same, for the data principal's primary sign-in; and `SMS_HTTP_URL` must be `https://` |
| `DKMS_ENABLED` is false | Personal data would be written in the clear, and nothing would ever report it |
| `BLIND_INDEX_KEY` starts `dev-only` or is under 32 bytes | Every lookup hash could be recomputed by anyone holding this repository |

The key service (`assert_shippable` in `backend/dkms/app/config.py`), in any
`ENVIRONMENT` other than `local` or `test`:

| Condition | Why |
|---|---|
| `DKMS_MASTER_KEY` is the key in `.env.example` | Everything sealed under it is readable by anyone holding this repository |
| `DKMS_HASH_KEY` is the key in `.env.example`, or under 32 characters | The same, for every hash |
| `CORS_ORIGINS` contains `*` | No browser should reach a decryption service |

A service that boots with a known secret key is worse than one that does not
boot: the second failure is loud and costs ten minutes.

## Groups

| Group | Notable |
|---|---|
| Database | `POSTGRES_HOST`, `_PORT`, `_DB` (`cmp`), `_USER`, `_PASSWORD`; pool 2–10; 15s statement timeout, 5s lock timeout — never infinite |
| Redis / Celery | `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`: three logical databases, so a broker flush does not drop sessions |
| Session | 8h absolute, 30min idle; HttpOnly, Secure, SameSite=Lax |
| Lockout | 5 attempts / 30 min window / 30 min lockout |
| OTP & MFA | 6 digits, 10 minutes, 5 verify attempts; MFA codes live 5 minutes; `MFA_REQUIRED_ROLES` defaults to every staff role ([ADR 0006](../decisions/0006-mfa-for-every-staff-role.md)) |
| Provisioning | `STAFF_INVITE_TTL_H` 48 — how long the code in a staff invitation lasts, in hours. It is the reset flow's own code, so an expired invitation needs no separate path: "Forgotten your password?" sends a working replacement |
| URLs | `PUBLIC_BASE_URL` (the data-principal portal, port 3001: consent and acceptance links) and `CONSOLE_BASE_URL` (the staff console, port 3000: ticket and request links) |
| Messages | `ORGANISATION_NAME`, the `{organisation}` every message may name; `NOTIFICATION_EMAIL_FROM`; the words themselves are edited in the console ([messages.md](../domain/messages.md)) |
| Rights | `RIGHTS_RESPONSE_PERIOD_DAYS` 90, `GRIEVANCE_RESPONSE_PERIOD_DAYS` 90, acknowledge 2, tickets 5, collate 5 before, download 30, unverified close 7, nomination accept 30 |
| Uploads | `MAX_UPLOAD_BYTES` 25 MB under `UPLOAD_ROOT`; proofs are PDF, PNG, JPEG only |
| API | 50 default page size, 200 max; public link 60/min |
| Outbound HTTP | `EXTERNAL_HTTP_TIMEOUT_S` 10, `EXTERNAL_HTTP_RETRIES` 3 |
| Logging | `LOG_LEVEL`, `LOG_JSON` (false for a terminal) |
| Transports | `EMAIL_TRANSPORT` (`console`, `smtp`, `null`), `SMS_TRANSPORT` (`console`, `http`, `null`), `STORAGE_BACKEND` (`local`; `object` is a stub that refuses on use). The `http` SMS transport POSTs `{"to","body","from"}` as JSON with a bearer token to `SMS_HTTP_URL`; put a provider-specific adapter in front of it |
| Key service | See below |

## The key service

Personal fields are sealed through a separate process, `backend/dkms`, on
the way into the database, and opened only in the portals' server layer
([ADR 0016](../decisions/0016-personal-data-sealed-by-a-separate-key-service.md)).
Lookup columns carry a keyed hash beside the ciphertext
([ADR 0017](../decisions/0017-lookup-by-keyed-hash-and-name-ngrams.md)).
Keys, rotation and what each one protects are in
[encryption-at-rest.md](../security/encryption-at-rest.md).

### The API and the worker

| Setting | Default in code | `.env.example` | What it does |
|---|---|---|---|
| `DKMS_ENABLED` | `false` | `true` | On: every write of a personal column is sealed through the key service. Must be true in the API **and** in the worker: the worker opens the recipient of every message, and with it false there a message to a sealed address raises naming this setting |
| `DKMS_URL` | `http://localhost:32688` | the same | Where the key service is |
| `DKMS_TIMEOUT_S` | 5 | 5 | Per call |
| `DKMS_BATCH_SIZE` | 500 | 500 | Records per call; the service refuses past its `DKMS_MAX_RECORDS` |
| `BLIND_INDEX_KEY` | a `dev-only-…` string | the same | The key every lookup hash and name n-gram is computed under, in this process. **Must equal the key service's `DKMS_HASH_KEY`, to the character.** Separate from `SECRET_KEY` so that rotating sessions does not change every index |

The platform computes every hash itself, so sign-in and search keep working
while the key service is down. The key service computes the same hashes for
any other caller (`POST /search`, `/search_ngram`, `/bulk_hash`). Two
different keys mean two different hashes for one person, and neither side
finds the other's rows.

Changing `BLIND_INDEX_KEY` after rows exist makes every stored hash
unfindable. Nothing in the repository recomputes them; see
[encryption-at-rest.md](../security/encryption-at-rest.md) before changing it.

### The key service itself

All read from `backend/dkms/.env` (unknown variables are ignored).

| Setting | Default | What it does |
|---|---|---|
| `ENVIRONMENT` | `local` | Outside `local` and `test` the refusals above apply |
| `DKMS_MASTER_KEY` | the development key | Base64, at least 32 bytes decoded. Every data type's key is derived from it |
| `DKMS_KEY_VERSION` | 1 | The version new ciphertext is written under, 1–255 |
| `DKMS_PREVIOUS_KEYS` | `{}` | JSON of version → base64 key, so what retired keys wrote still opens |
| `DKMS_HASH_KEY` | the development key | The hashing key, in the clear. Must equal the API's `BLIND_INDEX_KEY` |
| `DKMS_PROVIDER` | `local` | `local` (AES-256-GCM, shipped here) or `sdk` (a vendor client; fails at startup if it cannot load) |
| `DKMS_SDK_MODULE`, `DKMS_SDK_FACTORY` | `dkms`, `get_client` | Read only when `DKMS_PROVIDER=sdk` |
| `DKMS_POOL_WORKERS` | 0 | Threads in the pool; 0 is one per core, up to 32 |
| `DKMS_CHUNK_SIZE` | 64 | Records handed to one worker at a time |
| `DKMS_MAX_RECORDS` | 5000 | A larger request is refused with 413 |
| `HOST` | `127.0.0.1` | Bind address. A caller on another machine cannot reach loopback: bind the interface it uses, and firewall it — the service authenticates nobody |
| `PORT` | 32688 | |
| `CORS_ORIGINS` | empty | Empty on purpose: no browser should call it |

### The portals

Only `NEXT_PUBLIC_*` reaches the browser. Everything is read when the server
starts, so a change needs a restart.

| Variable | Where | Default | What it does |
|---|---|---|---|
| `DKMS_URL` | both, server only | none | The key service `src/app/dkms/decrypt/route.ts` posts to (`${DKMS_URL}/bulk_decrypt`). **Required**: unset, every decrypt answers 503. Must be a service holding the master key the API sealed with, and reachable from the portal's server. `.env.example` carries the placeholder `http://<ip>:32688`; locally it is `http://localhost:32688` |
| `NEXT_PUBLIC_SESSION_COOKIE` | both | `cmp_session` | The session cookie the decrypt route and `proxy.ts` look for. Must match the API's `COOKIE_NAME`. Not in `.env.example` |
| `API_ORIGIN` | both, `next.config.ts` | `http://127.0.0.1:8000` | Where `/api` is proxied to |
| `NEXT_PUBLIC_API_URL` | both | `/api` | Leave unset. Set, every request is cross-origin and the session cookie is dropped |
| `NEXT_PUBLIC_APP_NAME` | both | per portal | |
| `NEXT_PUBLIC_CSRF_HEADER`, `NEXT_PUBLIC_CSRF_COOKIE` | both | `X-CSRF-Token`, `cmp_csrf` | Must match the API's `CSRF_HEADER_NAME` and `CSRF_COOKIE_NAME` |
| `NEXT_PUBLIC_SUBJECT_PORTAL_URL` | console | `http://localhost:3001` | Where a data principal who lands on the console is sent |
| `NEXT_PUBLIC_STAFF_PORTAL_URL` | portal | `http://localhost:3000` | Where staff who land on the portal are sent |
| `DEV_ORIGINS` | both, development | empty | Extra origins the dev server serves its assets to, comma-separated |

## Transports default to not delivering

`console` for email and SMS, `local` for storage. A misconfigured staging box
that writes to a file is a far better failure than one that emails and texts real
people the first time somebody signs in.

Set `EMAIL_TRANSPORT=smtp` explicitly, along with the SMTP settings, to deliver
for real, and `SMS_TRANSPORT=http` with the gateway URL and token. Outside
local and test the console transports raise rather than pretend; in
production the settings refuse to load at all.

## Secrets

Belong in a secret manager. `.env` is gitignored from every directory in the
tree, and `.env.example` carries placeholders only. `DKMS_MASTER_KEY`,
`DKMS_HASH_KEY` and `BLIND_INDEX_KEY` are secrets like `SECRET_KEY`; the
hash key is the one secret two processes must share.
