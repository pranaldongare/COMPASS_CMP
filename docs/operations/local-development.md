# Local development

Everything needed to run the platform on one machine, sign in as every role,
and read the codes it sends. Windows is the primary development platform; the
commands are the same on macOS and Linux unless noted.

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.12 | `python3.12 -m venv` and `pip`; nothing else manages it |
| Node.js | 22 | on Windows, `fnm` makes switching painless |
| PostgreSQL | 16 | natively, or from `dev-services.yml` below |
| Redis | 7 | the same |
| Docker Desktop | current | **only** if you have no other PostgreSQL and Redis |
| Git | current | |

Native alternatives on Windows: PostgreSQL 16 or 17 via `winget`, and Memurai
(Redis-compatible). The application does not care which.

## 1. Datastores

If PostgreSQL and Redis are already on the machine, point `backend/api/.env`
at them and skip this step. Otherwise:

```bash
cd backend/api
docker compose -f dev-services.yml up -d
```

That file starts PostgreSQL and Redis and nothing else. It is the one Docker
file in the repository, and it exists for exactly this case. The compose
project is named `compass`; its volumes are `compass_pgdata` and
`compass_redisdata`, and `down` without `-v` keeps them.

## 2. Backend

```bash
cd backend/api
python3.12 -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env            # PUBLIC_BASE_URL, CONSOLE_BASE_URL - see below
alembic upgrade head            # 26 migrations
python scripts/seed.py          # one coherent world; refuses outside local/test
python -m cmp --port 8000
```

Every command from here on assumes the virtualenv is active in that terminal.
`requirements.txt` is the runtime pinned to exact versions; `-dev` adds the
suite and the tools, and installs this package editable so `import cmp`
resolves to `src/cmp`.

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
cd backend/api
celery -A cmp.tasks.app worker -Q high_priority,email,documents,reports,notifications,default -l info --pool=solo
celery -A cmp.tasks.app beat -l info
```

`--pool=solo` is for Windows. Run exactly one beat. Without the worker,
one-time codes are never delivered, so sign-in appears to hang at the code
step.

## 4. The two portals

```bash
cd frontend/console && cp .env.example .env.local && npm install && npm run dev   # http://localhost:3000
cd frontend/portal   && cp .env.example .env.local && npm install && npm run dev   # http://localhost:3001
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
`backend/api/var/outbox.log` instead of being sent. The newest entry is at the
bottom:

```bash
tail -n 20 backend/api/var/outbox.log
```

A code is valid for ten minutes (five for MFA) and five attempts. Five codes
per contact per hour; if you hit that during manual testing, clear the
counters:

```bash
redis-cli --scan --pattern 'rate:*' | xargs -r redis-cli del
# or, if Redis is the container: docker exec compass-redis-1 redis-cli --scan --pattern 'rate:*' | xargs -r docker exec -i compass-redis-1 redis-cli del
```

## Looking at the database

```bash
cd backend/api
python scripts/db.py                 # tables with row counts
python scripts/db.py rights_request  # describe one
python scripts/db.py "select reference, status from rights_request order by 1"
```

Read-only by construction: every statement runs in a transaction that is
rolled back.

## Starting over

```bash
cd backend/api
python scripts/reset_dev.py    # drops the public schema of the configured DB, migrates, seeds
```

It asks for confirmation and refuses outside `local` and `test`. It has no
`--force`, on purpose.

## Checks before you push

```bash
cd backend/api && . .venv/bin/activate && ruff check . && ruff format --check . && mypy src && pytest
cd frontend/console && npm run verify
cd frontend/portal && npm run verify
```

All four are clean on the integration branch as of 2026-09-17, `mypy
--strict` included. Anything reported is new.

## Things that bite

- **A "broken" sign-in with no error** is nearly always the cookie: the
  browser is on `127.0.0.1` while the proxy expects `localhost`, or
  `NEXT_PUBLIC_API_URL` is set. Use `localhost` for both portals.
- **Every button does nothing** in the console: Next.js refuses dev assets
  from an origin it does not recognise. `allowedDevOrigins` in
  `next.config.ts` lists `localhost` and `127.0.0.1`; use one of those, or
  name the origin you are reaching it by:

  ```bash
  DEV_ORIGINS=192.168.1.42 npm run dev      # or a comma-separated list
  ```

  Reaching either portal by IP also means the origin is not a *secure
  context*, so the browser ignores `Cross-Origin-Opener-Policy` and says so in
  the console. That warning is expected over plain HTTP and changes nothing;
  only HTTPS, or `localhost`, silences it.
- **Playwright and pytest must not run at the same time** against one
  database. Both write audit rows, and the chain's advisory lock serialises
  them into timeouts.
- **Killing processes by name** on Windows: matching on `celery` takes beat
  down with the worker, and matching on `node` takes both portals. Kill by
  port or PID.
- **Sessions expire** after thirty idle minutes. The browser tests re-run
  their sign-in project first for that reason.
