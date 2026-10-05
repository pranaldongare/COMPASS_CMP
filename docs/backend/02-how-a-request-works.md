# 2. How a request works

Paths are under `backend/api/src/cmp/`.

## Startup

`bootstrap/application.py` builds the app:

```python
app = FastAPI(..., lifespan=lifespan, default_response_class=ORJSONResponse,
    root_path=settings.root_path,
    docs_url=None if settings.is_production else "/docs", ...)
bootstrap_middleware.install(app)
api_errors.install(app)
bootstrap_routers.install(app)
container.warm()
_install_metrics(app)
```

The lifespan (`bootstrap/lifespan.py`) opens exactly three things and fails
fast if any is missing:

1. the PostgreSQL pool (`db/pool.py` `open_pool()`), after a direct probe
   connection so a wrong password is a clear error, not a pool timeout;
2. Redis (`db/redis.py` `open_redis()`), with a ping;
3. the schema version from `alembic_version`, which `/ready` compares with
   the migrations on disk.

The key service is not contacted at startup; `/ready` checks it. Redis is
three logical databases: `/0` sessions, limits and codes, `/1` the Celery
broker, `/2` task results.

Routers are mounted in the order of `ROUTERS` in `api/routers/__init__.py`:
`system` and `auth`, then the public consent and rights routers, then the
signed-in ones. `/dev/codes` is added only when `DEV_SHOW_CODES` is on, which
is refused outside local/test; it answers each browser tab with the codes
its own requests caused, matched on the `X-CMP-Dev-Client` header, which the
request context carries into Celery task headers. `/metrics` (Prometheus) is installed last and
ignores untemplated paths, so a consent token never becomes a metric label.

## The middleware a request passes through

Starlette runs the middleware added **last** first. Measured from
`app.user_middleware`, a request meets them in this order:

| Order | Middleware | What it does |
|---|---|---|
| 1 | Prometheus | Timing and counts per route template |
| 2 | `RequestContextMiddleware` (`api/middleware/request_context.py`) | Adopts a clean `X-Request-ID` or mints one, binds request id, client address and user agent into a context variable every log line and audit row reads, and echoes the id on the response |
| 3 | `SecurityHeadersMiddleware` | `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, a `default-src 'none'` CSP, COOP/CORP, `Cache-Control: no-store` on `/auth`, `/me`, `/c/` and any request with a cookie, HSTS in production |
| 4 | `BodyLimitMiddleware` | 413 when `Content-Length` exceeds `MAX_UPLOAD_BYTES` (25 MB), or when the bytes actually read do - a chunked body has no length to check |
| 5 | `AccessLogMiddleware` | One `request.completed` line, with tokens in `/c/<token>` and `/rights/nominations/<token>` replaced by `[token]` |
| 6 | GZip | Responses over 1 KB |
| 7 | CORS | Credentials allowed for `CORS_ORIGINS` |
| 8 | TrustedHost | Only when `TRUSTED_HOSTS` is set to something other than `*` |

Then the route's dependencies run, then the handler. The exception handlers
sit inside all of this, so an error response still gets its request id,
security headers and access-log line.

## A staff write, hop by hop: `POST /projects`

An R&D user registers a project from the console. The browser calls
`/api/projects` on the console's own origin; the Next.js rewrite forwards it
to the API as `POST /projects` with the session and CSRF cookies.

**1. The route** - `api/routers/v1/projects.py`:

```python
@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(body: ProjectIn, principal: CurrentUser) -> dict[str, Any]:
    if principal.role is not Role.RND_USER:
        raise Forbidden("Only an R&D User may register a project")
    async with transaction() as conn:
        return await service.create(conn, actor_id=principal.user_id, ...)
```

`ProjectIn` subclasses `Schema`, so an unknown field is a 422. It is
validated before the handler runs.

**2. The dependencies** behind `CurrentUser`:

- `session_from_request` (`api/dependencies/sessions.py`) reads the
  `cmp_session` cookie and loads the session from Redis
  (`auth/sessions/service.py` `load()`), sliding the idle window unless the
  request carries `X-CMP-Background: 1`. On POST, PUT, PATCH and DELETE it
  compares the `X-CSRF-Token` header with the token stored in the session,
  and answers 403 `csrf_failed` if they differ.
- `current_principal` (`api/dependencies/authentication.py`) refuses a
  session still waiting for its second factor (401 `mfa_required`), binds the
  actor into the request context for the audit layer, and returns a frozen
  `Principal(user_id, uuid, role, session)`.
- Other routes add a guard: `RequireRole(...)` aliases such as `RequireDPO`
  and `RequireStaff`, or `RequireResource("legal_hold", write=True)`, which
  checks the role against `core/permissions.py` `MATRIX`. This route checks
  the role inline instead.

**3. The transaction** - `db/pool.py`:

```python
async with get_pool().connection() as conn:
    await conn.set_autocommit(False)
    try:
        with after_commit.unit_of_work():
            async with conn.transaction():
                yield conn
```

It commits on a clean exit and rolls back on any exception. Work deferred
with `after_commit` - chiefly `dispatch_optional` messages - runs only after
the commit, so a mail is never sent about a change that rolled back. Reads
use `connection()`, which is autocommit.

**4. The service** - `domain/projects/service.py` `create()` checks the
request is complete, looks up each processor (a suspended one is a 422 on
`processor_uuids`), then writes the project, its processors and its first
status-history row, and records `project.created` in the audit trail - all
on the same connection.

**5. The repository** - `db/repositories/projects.py`:

```python
row = await fetch_one(conn, """
    INSERT INTO project (project_name, internal_project_name, description,
                         requesting_team, created_by, dco_user_id)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING project_id, project_uuid, project_name, ... created_at, updated_at
    """, (...))
```

Values are always bound parameters. A repository writing a personal column
seals it first (see [the database](04-database.md#personal-data-in-tables)).

**6. The audit row** - `domain/audit/service.py` `record()` checks the
entity type against a closed list, adds the request id and a keyed hash of
the client address, and inserts into `audit_log` on the caller's
connection. A database trigger chains it to the previous row
([security](03-security.md#the-audit-trail)). The change and its audit row
commit together or not at all.

**7. The response** - the service returns a dict; FastAPI validates it
against `ProjectOut` (`Out`, extra fields dropped), so the internal integer
id never leaves the process. 201, serialised with orjson.

## A public request: a consent link

A data principal opens `https://portal/c/<token>` from a message.

1. **`GET /c/{token}`** (`api/routers/public/consent.py`) sets
   `Referrer-Policy: no-referrer` and `no-store`, rate-limits the caller's
   address (60 a minute), and calls `resolve_link()`
   (`domain/consent/service.py`). The link is found by the HMAC of the token
   - the raw token is never stored - and every reason it might be unusable
   (unknown, expired, used up, revoked, notice or project or site no longer
   live) gives the same 404 `link_invalid`, so the answer reveals nothing.
2. **`POST /c/{token}/register`, `/otp`, `/otp/verify`** register or
   recognise the person and prove their contact with a one-time code; the
   last step opens a session with the data-principal role and sets the
   cookies.
3. **`GET /c/{token}/notice`**, signed in, renders the approved text and
   records in Redis that this notice, in this language, was shown to this
   person through this link (`nsrv:<user>:<link>:<language>`, six hours).
4. **`POST /c/{token}/consent`** checks that record - no record is 422
   `notice_not_served`, a changed or expired one is `notice_stale` - so a
   consent can only be recorded against a notice the server itself showed.
   The body's own `served_at` is ignored. Every purpose must be answered,
   the person must be an adult, and an advisory lock on (person, notice)
   serialises two clicks. It writes the consent artefact and its grants, an
   audit row, and a receipt message after commit.

The decision behind step 3 is [ADR 0011](../decisions/0011-server-held-notice-serving.md).

## The error contract

Every error has one shape (`api/errors/responses.py`):

```json
{ "error": { "code": "not_found", "message": "Project not found",
             "request_id": "4c0d1e8e…", "field": "processor_uuids" } }
```

`field` appears only when one field is at fault. A validation failure is 422
`validation_failed` with an `errors` array. Raise one of the classes in
`core/errors.py` and the handler does the rest:

| Class | Status | Default code |
|---|---|---|
| `BadRequest`, `UnknownFilter` | 400 | `bad_request`, `unknown_filter` |
| `Unauthenticated`, `MfaRequired` | 401 | `unauthenticated`, `mfa_required` |
| `Forbidden` | 403 | `forbidden` |
| `NotFound`, `LinkInvalid` | 404 | `not_found`, `link_invalid` |
| `Conflict`, `TransitionNotPermitted`, `NoticeImmutable`, `PurposeInUse` | 409 | own codes |
| `ValidationFailed`, `NoticeIncomplete`, `ConsentDefective`, `ImportRejected`, `TransferRefused` | 422 | own codes |
| `RateLimited` | 429 | `rate_limited`, with `Retry-After` |
| `UpstreamError`, `ServiceUnavailable`, `DkmsUnavailable` | 502 / 503 | own codes |

Any raise may pass a more specific `code=`; the frontends switch on codes,
never on messages.

**403 or 404.** A row outside your scope is not selected, so
`db/sql.py` `require_one()` raises 404 - a 403 would confirm it exists.
`Forbidden` is for something you can see but may not do.

## Lists, identifiers, personal fields

- **Paging is by cursor.** `core/pagination.py`: `limit` 1-200 (default 50),
  `sort` from a per-route allow-list, and an HMAC-signed cursor of (sort
  value, row id). Repositories build it with `keyset_clause` and
  `build_page`. The envelope is `{items, next_cursor, total}`. A few small
  lists return a plain array.
- **Identifiers.** URLs and bodies use UUIDs. Integer primary keys stay
  inside the process.
- **Personal fields leave the API sealed** - `SE::…` strings. The console and
  portal open them in their own server route (`src/app/dkms/decrypt/route.ts`)
  for the page that shows them. The API opens values only to act on them: to
  deliver a message, write an export or a response package, or build the
  audit CSV.

## Work that happens later: Celery

- **The app** (`tasks/app.py`): JSON only, `acks_late`, prefetch 1, six
  queues. The eight one-time-code tasks go to `high_priority`, other
  notifications to `notifications`, maintenance to `default`.
- **Queueing** (`tasks/dispatch.py`):
  - `dispatch_required(task, ...)` queues now and turns a broker failure into
    a 503. Use it where queueing *is* the outcome - sending a code.
  - `ensure_broker()` gives that 503 *before* anybody is looked up. The three
    neutral forms - sign-in by code, password reset, a consent link's code -
    call it first: `dispatch_required` runs only for a registered contact, so
    on its own an outage was a 503 for her and a 200 for a stranger, and the
    form answered "is this number registered?" (review UX-3).
  - `dispatch_optional(task, ...)` waits for the transaction to commit, then
    queues, and logs rather than fails if the broker is down. Use it for
    receipts and notices about a change.
  - Both keep the arguments out of Celery's events, so codes and contacts do
    not appear in monitoring.
- **Delivery**: a task calls `infrastructure/messaging` `deliver()`, which
  opens the sealed recipient, renders the wording, and hands it to the email
  or SMS transport. Locally both transports append to
  `backend/api/var/outbox.log`.
- **Scheduled** (Celery beat): expire consent links every 15 minutes,
  retention lapse 02:00, rights-request sweep 02:30, audit-chain
  verification 03:00, unmapped assets every six hours.

Worker command, from `backend/api`:

```bash
celery -A cmp.tasks.app worker -Q high_priority,email,documents,reports,notifications,default -l info --pool=solo
```

## Further reading

[API conventions](../architecture/api.md) ·
[request lifecycle](../architecture/request-lifecycle.md) ·
[transactions](../database/transactions.md) ·
[layers](../architecture/layers.md)
