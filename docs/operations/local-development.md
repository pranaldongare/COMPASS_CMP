# Local development

Everything needed to run the platform on one machine, sign in as every role,
and read the codes it sends. Windows is the primary development platform; the
commands are the same on macOS and Linux unless noted.

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.12 | managed by `uv` |
| uv | current | `pip install uv` or the installer |
| Node.js | 22 | the Dockerfiles use `node:22-alpine`; on Windows, `fnm` makes switching painless |
| Docker Desktop | current | for PostgreSQL 16 and Redis 7, or install both natively |
| Git | current | |

Native alternatives to Docker on Windows: PostgreSQL 16 or 17 via `winget`, and
Memurai (Redis-compatible). The application does not care which.

## 1. Datastores

```bash
cd cmp_backend
docker compose -f docker/docker-compose.yml -p cmp up -d db redis
```

The compose project is named `cmp`; its volumes are `cmp_pgdata` and
`cmp_redisdata`. The development database is **`cmp_dev`**. If the volume
already holds an older database called `cmp` from a previous project, leave it
alone; the backend's `.env` points at `cmp_dev`, and `reset_dev.py` only ever
touches the database it is configured for.

## 2. Backend

```bash
cd cmp_backend
cp .env.example .env            # POSTGRES_DB=cmp_dev, PUBLIC_BASE_URL, CONSOLE_BASE_URL - see below
uv sync --all-extras --dev
uv run alembic upgrade head     # 24 migrations
uv run python scripts/seed.py   # one coherent world; refuses outside local/test
uv run python -m cmp --port 8000
```

`python -m cmp` rather than `uvicorn cmp.main:app`: psycopg's async mode
cannot run on Windows' default event loop, and the module entrypoint supplies
the right one. On Linux the two are equivalent.

Settings worth checking in `.env` for local work:

| Key | Local value | Why |
|---|---|---|
| `ENVIRONMENT` | `local` | enables `/docs`, the outbox, the seed and reset scripts |
| `POSTGRES_DB` | `cmp_dev` | see above |
| `PUBLIC_BASE_URL` | `http://localhost:3001` | where the links in emails land: consent links, nomination acceptance |
| `CONSOLE_BASE_URL` | `http://localhost:3000` | where staff links land: tickets, requests |
| `MFA_REQUIRED_ROLES` | every staff role | the default; leave it |
| `EMAIL_TRANSPORT`, `SMS_TRANSPORT` | `console` | nothing is sent; see the outbox |

The interactive API reference is at `http://127.0.0.1:8000/docs`.

## 3. Workers

Two processes, in two terminals:

```bash
cd cmp_backend
uv run celery -A cmp.tasks.app worker -Q high_priority,email,documents,reports,notifications,default -l info --pool=solo
uv run celery -A cmp.tasks.app beat -l info
```

`--pool=solo` is for Windows. Run exactly one beat. Without the worker,
one-time codes are never delivered, so sign-in appears to hang at the code
step.

## 4. The two portals

```bash
cd cmp_internal_ui && cp .env.example .env.local && npm install && npm run dev   # http://localhost:3000
cd cmp_public_ui   && cp .env.example .env.local && npm install && npm run dev   # http://localhost:3001
```

Leave `NEXT_PUBLIC_API_URL` unset in both. Each portal proxies `/api` to the
backend so the session cookie is first-party; pointing the browser at the API
directly makes every sign-in look broken. Each portal's `.env.local` names the
other (`NEXT_PUBLIC_SUBJECT_PORTAL_URL`, `NEXT_PUBLIC_STAFF_PORTAL_URL`) so
the wrong kind of account is redirected rather than refused.

## Signing in

Seeded by `scripts/seed.py`. The password for every staff account is
`SeedPassw0rd!2026`, and every staff sign-in then asks for a code.

| Role | Email |
|---|---|
| DPO | `dpo@cmp.local` |
| Administrator | `admin@cmp.local` |
| DCO | `dco@cmp.local` |
| DCO Admin | `dcoadmin@cmp.local` |
| RCO | `rco@cmp.local` |
| R&D User | `rnd@cmp.local` |
| Data principal | mobile `+919000000001`, email `subject@cmp.local`; no password |

**Reading a code.** In `local` and `test`, every email and SMS is appended to
`cmp_backend/var/outbox.log` instead of being sent. The newest entry is at the
bottom:

```bash
tail -n 20 cmp_backend/var/outbox.log
```

A code is valid for ten minutes (five for MFA) and five attempts. Five codes
per contact per hour; if you hit that during manual testing, clear the
counters:

```bash
docker exec cmp-redis-1 redis-cli --scan --pattern 'rate:*' | xargs -r docker exec -i cmp-redis-1 redis-cli del
```

## Looking at the database

```bash
cd cmp_backend
uv run python scripts/db.py                 # tables with row counts
uv run python scripts/db.py rights_request  # describe one
uv run python scripts/db.py "select reference, status from rights_request order by 1"
```

Read-only by construction: every statement runs in a transaction that is
rolled back.

## Starting over

```bash
cd cmp_backend
uv run python scripts/reset_dev.py    # drops the public schema of the configured DB, migrates, seeds
```

It asks for confirmation and refuses outside `local` and `test`. It has no
`--force`, on purpose.

## Checks before you push

```bash
cd cmp_backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
cd cmp_internal_ui && npm run verify
cd cmp_public_ui && npm run verify
```

All four are clean on the integration branch as of 2026-09-10, `mypy
--strict` included. Anything reported is new.

## Things that bite

- **A "broken" sign-in with no error** is nearly always the cookie: the
  browser is on `127.0.0.1` while the proxy expects `localhost`, or
  `NEXT_PUBLIC_API_URL` is set. Use `localhost` for both portals.
- **Every button does nothing** in the console: Next.js refuses dev assets
  from an origin it does not recognise. `allowedDevOrigins` in
  `next.config.ts` lists `localhost` and `127.0.0.1`; use one of those.
- **Playwright and pytest must not run at the same time** against one
  database. Both write audit rows, and the chain's advisory lock serialises
  them into timeouts.
- **Killing processes by name** on Windows: matching on `celery` takes beat
  down with the worker, and matching on `node` takes both portals. Kill by
  port or PID.
- **Sessions expire** after thirty idle minutes. The browser tests re-run
  their sign-in project first for that reason.
