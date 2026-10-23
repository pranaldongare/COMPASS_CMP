# Configuration

Four processes read settings: the platform API (and its Celery worker, which
reads the same file but is a separate process with its own environment), the
key service, and the two portals.

| Process | Settings | Template |
|---|---|---|
| API, worker, beat | `backend/api/src/cmp/core/config.py`, 96 fields | `backend/api/.env.example` |
| Key service | `backend/dkms/app/config.py`, 14 fields | `backend/dkms/.env.example` |
| Console, portal | `process.env` in `next.config.ts`, `src/lib/config`, `src/proxy.ts`, `src/app/dkms/decrypt/route.ts` | `frontend/*/.env.example` |

The API's `Settings` refuses an unknown variable (`extra="forbid"`): a typo
fails at startup. `backend/api/.env.example` lists 69 of the 96 fields. Of
the other 27, four are email settings the template sets under their newer
names (`SMTP_HOST` as `SMTP_SERVER`, `NOTIFICATION_EMAIL_FROM` as
`SENDER_EMAIL`) or keeps only as legacy (`EMAIL_TRANSPORT`, `SMTP_USE_TLS`).
The remaining 23 have code defaults nobody has needed to change, and are set
by their upper-case name like any other:

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
| `SMTP_SERVER` is empty | Email would go to the local outbox, which writes nothing outside local/test; a code nobody receives is a sign-in nobody completes |
| `SENDER_EMAIL` is on `example.org` or `example.com` | Mail from a placeholder address is mail a real server may refuse and nobody can reply to |
| `SMS_TRANSPORT` is not `http` | The same, for the data principal's primary sign-in; and `SMS_HTTP_URL` must be `https://` |
| `DKMS_ENABLED` is false | Personal data would be written in the clear, and nothing would ever report it |
| `BLIND_INDEX_KEY` starts `dev-only` or is under 32 bytes | Every lookup hash could be recomputed by anyone holding this repository |
| `RELAY_INGRESS_KEY` is set and under 32 characters | Whoever presents it is served opened personal values ([the public relay](#the-public-relay)). Empty, the relay's opening is off, which production allows |
| `BREACH_TICKET_EMAIL_DOMAINS` is empty or only `cmp.local` | "Internal" is only as good as the list: empty, nobody could hold a breach ticket; the development domain alone, nobody real could (S3-08). The organisation's own list is needed before production (decided 2026-10-06) |

In any environment, the API and the worker also refuse `STORAGE_BACKEND=object`:
the object backend is a stub, and a deployment set that way used to start,
report ready and fail the first upload (review SCALE-5).

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
| Lockout | 5 attempts / 30 min window / 30 min lockout, per account however it is named (`LOGIN_*`). Per address: `AUTH_FAILURES_PER_ADDRESS` 30 failed attempts across every account in `AUTH_FAILURES_WINDOW_S` 900, at staff sign-in, code sign-in and password reset; successes do not count |
| OTP & MFA | 6 digits, 10 minutes, 5 verify attempts; MFA codes live 5 minutes; `MFA_REQUIRED_ROLES` defaults to every staff role ([ADR 0006](../decisions/0006-mfa-for-every-staff-role.md)) |
| Provisioning | `STAFF_INVITE_TTL_H` 48 — how long the code in a staff invitation lasts, in hours. It is the reset flow's own code, so an expired invitation needs no separate path: "Forgotten your password?" sends a working replacement |
| URLs | `PUBLIC_BASE_URL` (the data-principal portal, port 3001: consent and acceptance links, and an outside holder's ticket link) and `CONSOLE_BASE_URL` (the staff console, port 3000: ticket and request links) |
| Messages | `ORGANISATION_NAME`, the `{organisation}` every message may name and the sender's name; the words themselves are edited in the console ([messages.md](../domain/messages.md)) |
| Rights | `RIGHTS_RESPONSE_PERIOD_DAYS` 90, `GRIEVANCE_RESPONSE_PERIOD_DAYS` 90, acknowledge 2, tickets 5, collate 5 before, download 30, unverified close 7, nomination accept 30. `HOLDER_TICKET_SESSION_S` 3600 and `HOLDER_TICKET_COOKIE` `cmp_ticket`: how long an outside holder's ticket stays open in its browser after the one-time code, and the cookie holding it (0049); the portal's decrypt route also reads `NEXT_PUBLIC_TICKET_COOKIE`, which must match |
| Breach | `BREACH_WITHOUT_DELAY_TARGET_HOURS`, unset: the internal target for a duty Rule 7 says is due "without delay" - the Board's initial intimation and the notices to principals - in hours from awareness. The Rule sets no hours and the number is Legal's and the Programme's to choose; while it is unset the register shows the time elapsed and flags nothing ([breaches.md](../domain/breaches.md)). The 6 hours for CERT-In and 72 for the Board's report are statute and are not settings. `BREACH_ORG_BOARD_MINUTES`, 30: the internal policy for telling the organisation's board, in minutes from first noticed; read when an incident is logged and stored as its duty's due time, so a change moves nothing already running ([ADR 0022](../decisions/0022-an-incident-first-and-a-breach-on-a-yes.md)). `BREACH_TICKET_EMAIL_DOMAINS`, `cmp.local`: the email domains, comma-separated, that make a person internal enough to hold a breach ticket; checked for every assignee and every colleague ([ADR 0023](../decisions/0023-breach-tickets-and-breach-only-logins.md)). Since 0049 the same list decides how a rights ticket's holder is reached: an internal address gets a console login, any other a link on the portal ([rights-requests.md](../domain/rights-requests.md#how-a-holder-is-reached)) |
| Uploads | `MAX_UPLOAD_BYTES` 25 MB under `UPLOAD_ROOT`; proofs are PDF, PNG, JPEG only |
| API | 50 default page size, 200 max; public link 60/min |
| Outbound HTTP | `EXTERNAL_HTTP_TIMEOUT_S` 10, `EXTERNAL_HTTP_RETRIES` 3 |
| Logging | `LOG_LEVEL`, `LOG_JSON` (false for a terminal) |
| Email | Five settings: `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SENDER_EMAIL`; and `EMAIL_CC_ADDRESSES` (empty), up to five addresses copied on every email that may be copied, checked at startup; and `EMAIL_REDIRECT_TO` (empty), test mode - every email and text goes only to up to five addresses, saying whom it was for; production refuses to start with it set. `SMTP_SERVER` empty writes to the outbox; the port decides the connection (465 SSL, 587 STARTTLS, 25 plain). See [email/README.md](../email/README.md) |
| Transports | `SMS_TRANSPORT` (`console`, `http`, `null`), `STORAGE_BACKEND` (`local`; `object` is not built, and any environment refuses to start with it - until 2026-10-05 it started and failed the first upload). With more than one API or worker replica, `UPLOAD_ROOT` must be one durable volume they all mount: a proof saved by one replica is read back by another. The `http` SMS transport POSTs `{"to","body","from"}` as JSON with a bearer token to `SMS_HTTP_URL`; put a provider-specific adapter in front of it |
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

Only `NEXT_PUBLIC_*` reaches the browser. `NEXT_PUBLIC_*` values and
`API_ORIGIN` are fixed when the portal is built (`next build`), so a change
needs a new build. The rest is read when the server starts, so a change needs
a restart.

| Variable | Where | Default | What it does |
|---|---|---|---|
| `DKMS_URL` | both, server only | none | The key service `src/app/dkms/decrypt/route.ts` posts to (`${DKMS_URL}/bulk_decrypt`). **Required**: unset, every decrypt answers 503. Must be a service holding the master key the API sealed with, and reachable from the portal's server. `.env.example` carries the placeholder `http://<ip>:32688`; locally it is `http://localhost:32688` |
| `NEXT_PUBLIC_SESSION_COOKIE` | both | `cmp_session` | The session cookie the decrypt route and `proxy.ts` look for. Must match the API's `COOKIE_NAME`. Not in `.env.example` |
| `NEXT_PUBLIC_TICKET_COOKIE` | both | `cmp_ticket` | The cookie an outside holder's ticket page carries after its code (0049); the decrypt route accepts it as it accepts a session. Must match the API's `HOLDER_TICKET_COOKIE` |
| `NEXT_PUBLIC_DEV_SHOW_CODES` | both, development | unset | `true` shows each one-time code in a popup, read from the API's development-only route; the API ignores it outside local/test |
| `API_ORIGIN` | both, `next.config.ts` | `http://127.0.0.1:8000` | Where `/api` is proxied to. **Fixed at `next build`**: the rewrite is written into the build output, and a different value at `next start` is ignored (checked 2026-10-14, [deployment](../deployment/portal-frontend-aws.md#6-configuration-what-is-fixed-at-build-what-is-read-at-start)) |
| `NEXT_PUBLIC_API_URL` | both | `/api` | Leave unset. Set, every request is cross-origin and the session cookie is dropped |
| `NEXT_PUBLIC_APP_NAME` | both | per portal | |
| `NEXT_PUBLIC_CSRF_HEADER`, `NEXT_PUBLIC_CSRF_COOKIE` | both | `X-CSRF-Token`, `cmp_csrf` | Must match the API's `CSRF_HEADER_NAME` and `CSRF_COOKIE_NAME` |
| `NEXT_PUBLIC_SUBJECT_PORTAL_URL` | console | `http://localhost:3001` in development; **none for `next build`** | Where a data principal who lands on the console is sent, and the origin of every consent link the console shows. Inlined at build time: `next build` refuses to run without it, and warns when it points at localhost or plain http (`src/lib/config/deployment.ts`). Until 2026-10-05 a build without it defaulted to localhost and sent people to their own computers (review ARCH-6) |
| `NEXT_PUBLIC_STAFF_PORTAL_URL` | portal | `http://localhost:3000` in development; **none for `next build`** | Where staff who land on the portal are sent. The same build-time check |
| `DEV_ORIGINS` | both, development | empty | Extra origins the dev server serves its assets to, comma-separated |

### The public relay

When the data principal's portal runs on AWS and reaches the API only through
Amazon SQS (`backend/relay`: a bridge beside the portal, a collector inside
the network that accepts no inbound connection), two settings on the API's
side matter. The relay's own settings are in `backend/relay/.env.example`.

| Setting | Set in | Default | What it does |
|---|---|---|---|
| `RELAY_INGRESS_KEY` | the API's `.env` | empty: off | The secret the collector presents in `X-CMP-Relay-Key`. A request carrying it is a public, relayed request (`api/middleware/relay_open_sealed.py`): its input is searched for `SE::` before the route runs (422 `sealed_value_refused`), a staff session on it is refused (401), and the `SE::` values in its JSON reply are opened by the API before the reply leaves, because a portal on AWS cannot reach the key service its decrypt route would otherwise call. A wrong key, or none, is served as stored, exactly as before; the header is removed before any route sees it either way. **Must equal the contents of the collector's `RELAY_INGRESS_KEY_FILE`**: copy the file `python -m cmp_relay.keys ingress-key` writes, never generate a second value. 32+ characters in production. Only the API reads it, not the worker |
| `FORWARDED_ALLOW_IPS` | the API process's environment (the service unit, the shell), **not** `.env` | `127.0.0.1` | uvicorn's, not the API's: the addresses whose `X-Forwarded-For` uvicorn believes. Put in `.env` it stops the API at startup, because `Settings` refuses a key it does not know |

**Opening is narrow on purpose.** ADR 0016 has the portal's server open sealed
values; with the relay the API does it, but only for a reply it is serving to a
request that came through the relay with the key. The collector never reaches
the key service. If the key service is down the reply goes out as stored and
the page shows ciphertext, which is the failure the portal's own decrypt route
has today. Only `application/json` is opened; downloads stream through
untouched. Two rules keep it from becoming a way to decrypt anything:

- **No sealed value in.** The opener opens every `SE::` string in a relayed
  reply, whoever's it is, and `seal()` passes an already-sealed value through
  untouched. So any input the API stores or echoes back (a name, an
  attachment's file name, the User-Agent kept with a session, a message's
  body) would carry someone else's ciphertext in and bring it back opened. The API
  therefore searches every relayed request with its own parser, the one its
  routes use, before the route runs: query parameter names and values
  (decoded), every header value except `Cookie`, JSON keys and strings, form
  field names and values and upload file names; any other body as UTF-8 and as
  latin-1. `SE::` anywhere is 422 `sealed_value_refused`. JSON nested too deep
  to walk is refused too; a form the parser cannot read goes to the route,
  which fails on it with its own error. Only the bytes of an uploaded file are
  not searched: they are the person's own document, and they come back only as
  a download, never inside JSON. The collector runs a check of its own first,
  but the API's is the one relied on: only the API parses input exactly as its
  routes do.
- **Only a data principal's session.** A relayed request carrying a staff
  session - one signed in at the console with a password and a second factor -
  is refused with 401 on every route, including those both portals share
  (`/auth/me`, `/auth/sessions`, `/notifications`). The check is on the
  session's effective role, so a member of staff who signs in on the portal
  with a code, and so holds a data principal's session, is served as anyone
  else. The staff routes themselves are not on the relay's allow-list (404).

**The visitor's address.** The collector sends every relayed request with
exactly one `X-Forwarded-For`: the visitor's address as the bridge read it,
replacing whatever the visitor sent. The bridge takes the entry
`RELAY_CLIENT_IP_HOP` counts from the right of the header it receives, and
each proxy in front of the portal appends the address it was connected from:

- **An ALB with WAF and no CloudFront: `1`, the default.** The ALB appends the
  visitor. This is the recommended shape for the relay, because TLS from the
  browser then ends in ap-south-1, in India, not at whichever CloudFront edge
  is nearest the visitor.
- **CloudFront -> ALB -> portal: `2`.** CloudFront appends the visitor, then
  the ALB appends CloudFront's own address. With `1` every visitor would be
  recorded as one of a few CloudFront addresses, and one person's failed
  sign-ins would spend the per-address budget (`AUTH_FAILURES_PER_ADDRESS`)
  for everyone behind the same one.

Either count assumes the ALB's defaults (`routing.http.xff_header_processing.mode`
`append`, `routing.http.xff_client_port.enabled` off; the portal's `/api`
rewrite adds no entry), and is to be confirmed in staging with a header echo
([portal-frontend-aws.md §12](../deployment/portal-frontend-aws.md#12-must-be-resolved-before-go-live)).
What the API records from the collector's header:

- *Outside production* `client_ip` takes the socket address, which uvicorn
  replaces with the `X-Forwarded-For` value only for a connection from an
  address in `FORWARDED_ALLOW_IPS`. A collector on the API's own host, calling
  `http://127.0.0.1:8000`, needs nothing set. A collector on another host
  needs its address there (comma-separated for several), or every relayed
  request is recorded as coming from the collector - one address, which the
  per-address sign-in budget (`AUTH_FAILURES_PER_ADDRESS`) then charges for
  every visitor at once. Never `*`: any caller on the inside network could
  then choose the address written to the audit trail.
- *In production* `client_ip` reads the first `X-Forwarded-For` entry itself,
  from any caller ([ADR 0018](../decisions/0018-pip-and-a-virtualenv-no-containers.md)).
  The collector's single header makes that the visitor for relayed traffic.
  A caller that reaches the API directly can still set its own; that is the
  open item in [portal-frontend-aws.md §12](../deployment/portal-frontend-aws.md#12-must-be-resolved-before-go-live),
  which the relay narrows to the inside network but does not close.

**Timeouts on the way in.** The bridge waits for a reply until the deadline
plus 2 s: 25 s for a request, 50 s for any `multipart/form-data` request
(`RELAY_DEADLINE_S`, `RELAY_UPLOAD_DEADLINE_S` in `backend/relay/.env.example`).
Everything in front of it must wait longer, or the browser is shown a failure
while the inside may still record the write, and the person's retry makes it
twice:

- **The front door.** The ALB's idle timeout and, with CloudFront in front,
  its origin response timeout must each exceed the longest deadline + 5 s.
  Both are 60 s by default, which fits 25 s and 50 s. Raise
  `RELAY_UPLOAD_DEADLINE_S` only together with both.
- **The portal.** `next.config.ts` raises the rewrite proxy's limits
  (`experimental.proxyClientMaxBodySize` 26 MB, `proxyTimeout` 180 s) and the
  client gives a file upload a 180-second timeout, so a 25 MB upload is not cut
  at Next's 10 MB default or timed out at 30 s. Both are above the bridge's
  wait, so neither is the one that gives up first; the front door's 60 s is the
  limit that binds.

## Transports default to not delivering

`console` for email and SMS, `local` for storage. A misconfigured staging box
that writes to a file is a far better failure than one that emails and texts real
people the first time somebody signs in.

Set `SMTP_SERVER` and the other four email settings to deliver email for
real - they, the template every email is laid out in, and a test send are in
[email/README.md](../email/README.md) - and `SMS_TRANSPORT=http` with the gateway URL and token. Outside
local and test the console transports raise rather than pretend; in
production the settings refuse to load at all.

## Secrets

Belong in a secret manager. `.env` is gitignored from every directory in the
tree, and `.env.example` carries placeholders only. `DKMS_MASTER_KEY`,
`DKMS_HASH_KEY`, `BLIND_INDEX_KEY` and `RELAY_INGRESS_KEY` are secrets like
`SECRET_KEY`. Two are shared by two processes: the hash key (the key service's
`DKMS_HASH_KEY` and the API's `BLIND_INDEX_KEY`), and the relay's ingress key
(the API's `RELAY_INGRESS_KEY` and the file the collector reads).
