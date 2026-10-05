# 3. Security, end to end

Every control, as the code implements it. Paths are under
`backend/api/src/cmp/` unless they say otherwise. The reference pages in
[security/](../security/) go deeper on each; where they disagree with the
code, [known gaps](06-known-gaps.md) says so.

## Two populations

There are seven roles (`core/permissions.py`): `dpo`, `dco`, `dco_admin`,
`rco`, `rnd_user`, `admin` - the **staff** - and `data_subject`, the
**data principals**. Staff sign in to the console with a password and a
second factor. Data principals have no password; they prove a contact with a
one-time code.

A member of staff is also a person, and may use the portal as one. A code
sign-in always opens a session whose **role** is `data_subject`; the
account's own role travels beside it as `account_role`, for display only.
Every permission check reads `role`. So a code sent to a staff mailbox gives a
principal's session, never a staff one - which is what closed the MFA bypass
described in [ADR 0013](../decisions/0013-every-account-is-a-data-principal.md).

## Staff sign-in

**Passwords** are Argon2id (`core/security.py`: time cost 2, 19 MiB,
parallelism 1), 12-128 characters. `verify_password` still hashes a dummy
value when there is no account, so a missing account takes as long as a
wrong password. A hash made with old parameters is upgraded at the next
sign-in.

**`POST /auth/login`** (`auth/authentication/service.py` `authenticate()`):

1. Refuses a locked login first (429 with `Retry-After`).
2. Finds the account by the keyed hash of what was typed, email or username.
3. Gives the same answer - "Those credentials are not valid" - for no such
   account, a wrong password, an inactive account and a data-principal
   account. Status is checked only after the password is right, so the reply
   never confirms an account exists.
4. Counts failures in Redis against the account - one counter whether it was
   named by email or by username, keyed on its uuid (a login that names no
   account, on the login's keyed hash): five in 30 minutes lock it for 30
   minutes (`LOGIN_MAX_ATTEMPTS`, `LOGIN_LOCKOUT_*`). A success, or a password
   reset, clears the count. Failures also count against the address, across
   accounts: 30 in 15 minutes and that address is refused at sign-in, code
   sign-in and password reset (`AUTH_FAILURES_*`).
5. Opens a **partial session** and sends a six-digit code to the account's
   email.

**The second factor.** `MFA_REQUIRED_ROLES` defaults to every staff role. The
code lives five minutes, allows five attempts, and can be resent three times
in ten minutes. A partial session is refused everywhere (401 `mfa_required`)
except `POST /auth/mfa/verify` and `/auth/mfa/resend`. Verifying promotes the
session in place to a full eight-hour one.

**Invitation and reset share one code.** An administrator creating an
account gives it a random unusable password and status `pending`, and sends
an invitation carrying a code - the same kind of code a password reset sends,
valid 48 hours instead of 15 minutes. Setting a password with that code
activates the account and signs out every existing session.

## Data-principal sign-in

**One-time codes** (`auth/authentication/otp.py`) serve eight flows - portal
sign-in, consent link, staff MFA, contact confirmation, rights verification,
nominee verification, registration and nomination acceptance:

- A code is six digits from `secrets`.
- Redis keeps only `HMAC(SECRET_KEY, "<scope>:<code>")` at
  `otp:<scope>:<identity>`, so a code from one flow is useless in another.
- Checking and spending the code is one Lua script, so two requests with the
  same code cannot both succeed.
- The fifth wrong attempt discards the code.
- A wrong code and an expired one get the same answer.

**Requesting a code** answers neutrally whether or not the contact is known,
and sends one only to a known, active or pending account. **Registering**
refuses a contact already in use with 409 `contact_taken` - a deliberate
trade of enumeration for a clear sign-up - and refuses anyone under 18.

**Through a consent link**, one proven contact signs an existing person in;
a new registration must prove every contact it gave. See
[how a request works](02-how-a-request-works.md#a-public-request-a-consent-link).

## Sessions

- **The token** is 32 random bytes in the `cmp_session` cookie. Redis stores
  the session at `sess:<HMAC(token)>`, never the token itself.
- **The session holds** the user and role, the account's own role,
  `created_at`/`last_seen_at`/`expires_at`, the client address and user
  agent, whether MFA is done, and its own CSRF token.

| Cookie | HttpOnly | Secure | SameSite | Lifetime |
|---|---|---|---|---|
| `cmp_session` | yes | `COOKIE_SECURE` (true except in local `.env`) | `lax` | 8 h (5 min while partial) |
| `cmp_csrf` | **no** - the page must read it | same | `lax` | same |

- **Two limits**: eight hours absolute (`SESSION_TTL_S`) and 30 minutes idle
  (`SESSION_IDLE_TIMEOUT_S`). Each request slides the idle window, except one
  carrying `X-CMP-Background: 1`, which the console sends on its timed
  refreshes so an open tab can still time out.
- **Ending sessions**: `POST /auth/logout` ends this one;
  `DELETE /auth/sessions/{id}` ends one of your own; a password change or
  reset, deactivation, a role change, an MFA reset and an administrator's
  force sign-out end all of a person's sessions.
- **The first-party proxy**: the browser never calls the API's origin. Each
  Next.js app rewrites `/api/*` to the API
  (`frontend/*/next.config.ts`), so the cookies are same-site and `lax` is
  enough ([ADR 0003](../decisions/0003-server-side-sessions-and-first-party-proxy.md)).

## CSRF

Double submit, checked against the session. On POST, PUT, PATCH and DELETE,
`session_from_request` (`api/dependencies/sessions.py`) compares the
`X-CSRF-Token` header with the CSRF token stored in the Redis session, using
a constant-time comparison. The frontends copy the `cmp_csrf` cookie into
that header in their axios interceptor. Routes that do not load the session
through this dependency - the unauthenticated forms, and one cookie route,
see [known gaps](06-known-gaps.md) - are not checked.

## Authorisation

**The matrix.** `core/permissions.py` `MATRIX` maps 22 resources × 7 roles
to a `Grant(scope, write)`. A resource or role missing from a row is denied.

**Scopes** say *which rows*:

| Scope | Meaning |
|---|---|
| `ALL` | every row (the DPO, mostly) |
| `SCOPED` | rows you are responsible for - a DCO or RCO's own projects and sites, a DCO Admin's third-party projects - plus those of anyone you are currently covering for |
| `OWN` | rows you created (an R&D user's projects) |
| `NONE` | nothing |

The repository compiles the scope into SQL, for example
`db/repositories/projects.py` `scope_predicate()`: `TRUE`, `FALSE`,
`p.created_by = %s`, or the DCO clause with
`cmp_delegators_of(me)` - a SQL function that returns whoever you cover for
right now.

**Guards** in route signatures (`api/dependencies/common.py`):
`CurrentUser`, `RequireRole` aliases (`RequireDPO`, `RequireAdmin`,
`RequireStaff`, `RequireDataSubject` …) and `RequireResource` aliases
(`ProjectReader`, `LegalHoldWriter` …). A guard answers 403 for a role that
has no grant; the repository's WHERE clause answers 404 for a row out of
scope.

**Navigation.** `NAV_BY_ROLE` lists each role's console sections.
`GET /auth/me` returns `nav` and `writes` for the session's role, and the
console draws its menu and hides buttons from them. The frontend's
`RequireSection` and `Can` only hide things; the API is the boundary.

## Rate limits

A sliding window in Redis (`auth/rate_limit/service.py`): a sorted set per
bucket and identity, trimmed to the window, counted, expired. If Redis is
down the limiter **refuses** (503) - except the two public rights-form
buckets, which let requests through.

| Bucket | Keyed on | Limit |
|---|---|---|
| login lockout | typed login | 5 failures → 30 min lock |
| `mfa_resend` | user | 3 / 10 min |
| `subject_otp`, `subject_register` | contact | 5 / hour |
| `pwreset` | email | 3 / hour |
| `public_link` | address | 60 / minute |
| `consent_otp_contact` / `consent_otp_token` | contact / link | 5 / hour, 20 / hour |
| `rights_public_contact` / `rights_public_ip` | contact / address | 5 / hour, 20 / hour |
| nomination buckets | address or nomination | 5-60 per window |
| one code | the code | 5 attempts, then discarded |

Full table: [rate limiting](../security/rate-limiting.md).

## Personal data encrypted at rest

**The key service** (`backend/dkms`) encrypts with AES-256-GCM, a key per data
type derived by HKDF from the master key. A sealed value is:

```
SE:: + base64url( "DK" | key version | type id | 12-byte nonce | ciphertext + tag )
```

The four-byte header is authenticated, so a value sealed as a name cannot be
opened as an email. The key service listens on 127.0.0.1 and authenticates
nobody; the network is its boundary.

**Sealing happens in repositories, on write.** `infrastructure/dkms/fields.py`
names every personal column and its type. `seal(table, row)` sends just those
columns in one batch; a value already sealed is left alone. If the key service
is down the write fails with 503 - nothing is written in the clear.

**Finding a sealed value.** Ciphertext cannot be searched, so beside each
lookup column sits a keyed hash - `email_hash` =
`HMAC(BLIND_INDEX_KEY, "email:" + normalised email)` (`infrastructure/dkms/blind.py`).
Sign-in, "is this contact taken" and exact searches compare hashes. Three name
columns also keep hashed three-letter fragments (`full_name_ngrams`) for
partial name search.

**Opening.** The API serves sealed values. The portals open them in their own
server route and only for the page. The backend opens values only to act:
delivering a message, writing an export, a rights response package or the
audit CSV. Hashes, n-grams, password hashes and token fingerprints are never
opened - they cannot be.

More: [encryption at rest](../security/encryption-at-rest.md),
[the DKMS documents](../dkms/README.md),
[adding a personal field](../dkms/adding-a-personal-field.md).

## The audit trail

- **Written in the same transaction** as the change it describes
  (`domain/audit/service.py` `record()`), with the request id and a keyed
  hash of the client address - never the raw address ([ADR 0015](../decisions/0015-nothing-erasable-in-a-trail-nobody-can-erase.md)).
- **Chained by the database.** A `BEFORE INSERT` trigger takes an advisory
  lock, reads the previous row's hash and stores
  `sha256(previous hash | event | actor | subject | entity | time | detail)`
  in the new row's `detail_json` as `_hash`, with `_prev`.
- **Append-only by trigger.** An UPDATE or DELETE on `audit_log` - or on any
  evidence table - raises an error. Production also revokes those privileges
  from the application's database role.
- **Verified** by `cmp_audit_verify()`, from `GET /audit/verify` and nightly at
  03:00; the first broken link is reported.
- **Never in `detail_json`:** names, contacts, codes, tokens, free-text
  reasons. Record that a reason was given, not the reason.

## Capability tokens

A consent link, a nominee's acceptance link and a session are all bearer
tokens: 32 random bytes, stored only as `HMAC(SECRET_KEY, token)`. A consent
link also keeps a sealed copy so the collector can copy the URL again.
Tokens are kept out of logs (`safe_path()` replaces them with `[token]`), out
of metrics labels, out of referrers (`no-referrer` on those pages) and out of
Celery's events. Rotating `SECRET_KEY` invalidates all of them, and every
pending one-time code.

## Headers and the browser

The API sends a `default-src 'none'` CSP, `X-Frame-Options: DENY`, `nosniff`,
`no-referrer`, COOP/CORP, `no-store` on anything personal, and HSTS in
production; `/docs` is off in production. The Next.js apps add a per-request
nonce CSP (`src/proxy.ts`) and the same frame and referrer rules.

## Secrets and the production guard

`core/config.py` refuses to start in production with a development
`SECRET_KEY` or `BLIND_INDEX_KEY` (or one under 32 characters), a default
database password, insecure cookies, debug on, `*` in CORS, the console mail
or SMS transport, or encryption switched off. `DEV_SHOW_CODES` is refused
outside local/test in every environment. The key service has its own
refusals for development keys.

## Logging

JSON lines through structlog (`core/logging.py`), each with the request id,
actor and role. Keys such as `password`, `token`, `code`, `otp`, `cookie` and
`authorization` are replaced with `[redacted]`; transports log an obscured
address (`ab***@domain`); one-time codes are never logged. The request id is
on every response and error body and is carried into Celery tasks, so one
request can be followed through the worker.
