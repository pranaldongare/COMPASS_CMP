# Local development

Everything needed to run the platform on one machine, sign in as every role,
and read the codes it sends. Five processes and two datastores, started in
this order: PostgreSQL and Redis, the key service, the API and its worker,
then the two portals. The key service comes before the seed, because the
seed writes personal data and personal data is sealed through it on the way
in. Windows is the primary development platform; the
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

## 2. Key service

```bash
cd backend/dkms
python3.12 -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env            # development keys; refused outside local/test
python -m app.main              # http://127.0.0.1:32688
```

Its own virtualenv and its own terminal. `curl http://127.0.0.1:32688/health`
answers `{"status": "ok", ...}` when it is up. The development `DKMS_HASH_KEY`
in its `.env.example` is the same string as `BLIND_INDEX_KEY` in the API's;
keep them equal if you change either
([configuration.md](configuration.md#the-key-service)).

## 3. Backend

```bash
cd backend/api
python3.12 -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env            # PUBLIC_BASE_URL, CONSOLE_BASE_URL - see below
alembic upgrade head            # 32 migrations; 0028 and 0030 call the key service
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
| `POSTGRES_DB` | `cmp` | the database `dev-services.yml` creates |
| `PUBLIC_BASE_URL` | `http://localhost:3001` | where the links in emails land: consent links, nomination acceptance |
| `CONSOLE_BASE_URL` | `http://localhost:3000` | where staff links land: tickets, requests |
| `MFA_REQUIRED_ROLES` | every staff role | the default; leave it |
| `EMAIL_TRANSPORT`, `SMS_TRANSPORT` | `console` | nothing is sent; see the outbox |
| `DKMS_ENABLED` | `true` | personal fields are sealed; the key service must be up for any write |
| `DKMS_URL` | `http://localhost:32688` | the key service from step 2 |
| `BLIND_INDEX_KEY` | the `.env.example` value | must equal the key service's `DKMS_HASH_KEY` |

`curl http://127.0.0.1:8000/ready` checks PostgreSQL, Redis, the migration
head and the key service (`encryption`) in one call.

The interactive API reference is at `http://127.0.0.1:8000/docs`.

## 4. Workers

Two processes, in two terminals:

```bash
cd backend/api
celery -A cmp.tasks.app worker -Q high_priority,email,documents,reports,notifications,default -l info --pool=solo
celery -A cmp.tasks.app beat -l info
```

`--pool=solo` is for Windows. Run exactly one beat. Without the worker,
one-time codes are never delivered, so sign-in appears to hang at the code
step. The worker reads the same `.env` but is its own process: it opens the
sealed address of every message, so it needs `DKMS_ENABLED=true` and a
reachable `DKMS_URL` as much as the API does.

## 5. The two portals

```bash
cd frontend/console && cp .env.example .env.local && npm install && npm run dev   # http://localhost:3000
cd frontend/portal   && cp .env.example .env.local && npm install && npm run dev   # http://localhost:3001
```

Leave `NEXT_PUBLIC_API_URL` unset in both. Each portal proxies `/api` to the
backend so the session cookie is first-party; pointing the browser at the API
directly makes every sign-in look broken. Each portal's `.env.local` names the
other (`NEXT_PUBLIC_SUBJECT_PORTAL_URL`, `NEXT_PUBLIC_STAFF_PORTAL_URL`) so
the wrong kind of account is redirected rather than refused.

**Set `DKMS_URL` in both `.env.local` files** before starting them. The
template carries the placeholder `http://<ip>:32688`; locally it is
`http://localhost:32688`. It is server-only - each portal's
`/dkms/decrypt` route calls the key service, the browser never does - and
is read at startup, so restart the portal after changing it. Wrong or
unset, every name and contact on the page shows as `SE::…`.

## Signing in

`scripts/seed.py` creates **one account, the administrator** -
`admin@cmp.local`, password `SeedPassw0rd!2026` - and the configuration the
rest is set up against: three processors (two third-party, one in-house),
their five data sources, two purposes, and an approved project with a
published notice (English and Hindi) and a live consent link, printed at the
end of the run. Each is a table at the top of the script; edit it and re-run.

Every other account is created by the administrator: **Users → Invite** in
the console. The invitation carries a code that sets the password (with
`DEV_SHOW_CODES=true` it pops up on the page). Invite a DPO first: the
project and the notice are the DPO's to open, not the administrator's.

Re-running the seed never deletes anything, so a database seeded before
2026-09-25 keeps its `dpo@`, `dco@`, `rnd@`, `rco@`, `dcoadmin@` and
`subject@cmp.local` accounts. **The browser suites sign in as those**; on a
freshly seeded database, invite them first (same addresses, password
`SeedPassw0rd!2026`) or the suites' setup step fails.

**Reading a code.** In `local` and `test`, every email and SMS is appended to
`backend/api/var/outbox.log` instead of being sent. The newest entry is at the
bottom:

```bash
tail -n 20 backend/api/var/outbox.log
```

**Or have the portal show it.** From a phone, or another machine opening the
portal by IP, the outbox is out of reach. Switch on the development popup
and each code appears in the top-right corner of the page that asked for it,
with who it went to and a Copy button:

```bash
# backend/api/.env
DEV_SHOW_CODES=true
# frontend/console/.env.local and frontend/portal/.env.local
NEXT_PUBLIC_DEV_SHOW_CODES=true
```

Restart the API, the worker and both `npm run dev`. The API refuses to start
with `DEV_SHOW_CODES` outside `ENVIRONMENT=local`/`test`, and `/dev/codes`
does not exist unless it is on - a code shown on the screen that asks for it
proves nothing about who holds the phone, so this never goes near a real
deployment.

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
cd backend/dkms && . .venv/bin/activate && ruff check app tests && mypy app && pytest tests
cd frontend/console && npm run verify
cd frontend/portal && npm run verify
```

The backend `pytest` needs the key service running, and it includes
`tests/http`, which commits rows to the database it runs against; see
[testing.md](testing.md#backend) for running that suite on a scratch
database.

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
- **`SE::…` where a name should be** in either portal: that portal's
  `DKMS_URL` is unset, wrong, or unreachable from its server. The portal's
  own terminal says `[dkms] ... unreachable` or `answered <status>`. See the
  [runbook](runbook.md#a-portal-shows-se-where-a-name-should-be).
- **A write answers 503 "The encryption service is unavailable"**, and
  `/ready` says `encryption` is not ok: the key service is not running.
- **Playwright and pytest must not run at the same time** against one
  database. Both write audit rows, and the chain's advisory lock serialises
  them into timeouts.
- **Killing processes by name** on Windows: matching on `celery` takes beat
  down with the worker, and matching on `node` takes both portals. Kill by
  port or PID.
- **Sessions expire** after thirty idle minutes. The browser tests re-run
  their sign-in project first for that reason.
