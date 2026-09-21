# COMPASS CMP

A consent management platform built to India's **Digital Personal Data
Protection Act 2023** and the DPDP Rules 2025: notices, purpose-by-purpose
consent, the collection that follows, and the rights a data principal can
exercise afterwards, all recorded so that what happened can be proved years
later.

Three deployable projects in one repository, one API:

| Path | Stack | What it is |
|---|---|---|
| [`backend/api/`](backend/api) | FastAPI 0.141, PostgreSQL 16, Redis 7, Celery 5, Python 3.12 | The API: 245 endpoints, 32 tables, raw SQL over psycopg 3, no ORM, 26 raw-SQL migrations |
| [`frontend/console/`](frontend/console) | Next.js 16, React 19, Tailwind 4, TanStack Query | The staff console on port 3000: password and emailed code sign-in, the registers, the DPO's rights queue, a respondent's tickets |
| [`frontend/portal/`](frontend/portal) | the same | The data principal's portal on port 3001: the consent link, sign-up, code sign-in, the rights pages, her own consents and requests |

Documentation starts at [docs/README.md](docs/README.md). The short version
of the architecture is
[docs/architecture/system-overview.md](docs/architecture/system-overview.md);
the vocabulary is in [docs/glossary.md](docs/glossary.md). The endpoint-by-endpoint
request, validation and response reference, followed by access details for all
seven roles, starts at [docs/reference/api/README.md](docs/reference/api/README.md). The database
is drawn and listed, table by table, in
[docs/reference/database/README.md](docs/reference/database/README.md). Which role may call
each endpoint, on which rows and under what conditions, is
[docs/reference/access-control/README.md](docs/reference/access-control/README.md).

## What the system does

A **data fiduciary** registers a project, states the purposes it will process
personal data for, and publishes a notice. A **data principal** reads that
notice at a collection site, through a link on her phone, and agrees or
refuses purpose by purpose. Data is then collected at sites owned by
accountable people, exported to processors with a disclosure record, and
imported back as assets reconciled against consent. Later she may ask what is
held, have it corrected or erased, complain, or name a nominee to act for
her, and the Privacy Office must answer within a published period.

Five decisions carry most of the weight, each recorded under
[docs/decisions/](docs/decisions/README.md):

- **Consent is per purpose, never in aggregate.** One grant row per purpose;
  status is derived, never stored.
- **Withdrawal supersedes; it never edits.** A new record points at the one it
  replaces. The chain is the history.
- **The evidence is enforced by the database.** Notices freeze on
  publication, evidence tables refuse `UPDATE` and `DELETE` by trigger and by
  revoked grant, and the audit log is a SHA-256 hash chain that reports
  "sound up to exactly here".
- **Scope lives in the query.** A row outside a role's scope is never
  selected, so it is a 404, and the console holds no copy of the permission
  matrix.
- **A rights request is a record with a clock.** Received, verified, every
  holder of her data ticketed, decided per appearance, answered on time even
  if partial.

## Running it locally

The full walkthrough, with what to do when a sign-in looks broken, is
[docs/operations/local-development.md](docs/operations/local-development.md).
The short form, with Python 3.12, Node 22, and PostgreSQL 16 + Redis 7 - which
the one Docker file in the repository provides if you have them no other way:

```bash
# datastores - skip if you have PostgreSQL and Redis already; point .env at them
cd backend/api && docker compose -f dev-services.yml up -d

# API, migrations, seed
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env                      # PUBLIC_BASE_URL=http://localhost:3001, CONSOLE_BASE_URL=http://localhost:3000
alembic upgrade head
python scripts/seed.py                    # refuses outside local/test
python -m cmp --port 8000

# workers, two terminals (activate the venv in each)
celery -A cmp.tasks.app worker -Q high_priority,email,documents,reports,notifications,default -l info --pool=solo
celery -A cmp.tasks.app beat -l info

# what the workers are doing, optional
celery -A cmp.tasks.app:celery_app flower --address=127.0.0.1 --port=5555 --basic-auth=you:a-password

# the key service, its own venv
cd ../dkms && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env && .venv/bin/python -m app.main                                  # http://127.0.0.1:8100

# the two portals
cd ../../frontend/console && cp .env.example .env.local && npm install && npm run dev  # http://localhost:3000
cd ../portal            && cp .env.example .env.local && npm install && npm run dev  # http://localhost:3001
```

Leave `NEXT_PUBLIC_API_URL` unset in both portals: each proxies `/api` so
the session cookie stays first-party. The API reference is at
`http://127.0.0.1:8000/docs`.

Everything runs as a process on your machine. There are no images to build and
no proxy to configure; how the platform was once meant to be containerised is
kept in [docs/history/](docs/history/README.md) for the record.

## Seeded accounts

Created by `scripts/seed.py`, which refuses to run outside `local` and
`test`. The password for every staff account is `SeedPassw0rd!2026`, and
every staff sign-in then asks for a code, which a local deployment writes to
`backend/api/var/outbox.log`.

| Role | Sign-in |
|---|---|
| Data Protection Officer | `dpo@cmp.local` |
| Administrator | `admin@cmp.local` |
| Data Collection Owner | `dco@cmp.local` |
| DCO Admin | `dcoadmin@cmp.local` |
| Research Collection Owner | `rco@cmp.local` |
| R&D User | `rnd@cmp.local` |
| Data principal | mobile `+919000000001` or `subject@cmp.local`; a code, no password |

## Tests

```bash
cd backend/api && . .venv/bin/activate && pytest     # unit, integration, security; needs PostgreSQL and Redis
cd frontend/console && npm run verify                  # typecheck, lint, vitest
cd frontend/portal && npm run verify
cd frontend/console && npx playwright test --workers=1 # browser, against the running stack
cd frontend/portal && npx playwright test --workers=1
```

What each suite covers, the counts, and the rules for running them together
are in [docs/operations/testing.md](docs/operations/testing.md).

## Repository layout

```
backend/api/       the API, migrations, Celery tasks, operator scripts, dev-services.yml
frontend/console/   the staff console
frontend/portal/     the data principal's portal
docs/              architecture, domain workflows, operations, decisions, glossary, history
CHANGELOG.md       what changed, by date
CONTRIBUTING.md    how a change lands
```

Package by package: [docs/architecture/repository-layout.md](docs/architecture/repository-layout.md).

## Configuration

Every setting is documented in `backend/api/.env.example` and explained in
[configuration.md](docs/operations/configuration.md). Production
refuses to start on a development `SECRET_KEY`, a default database password,
`COOKIE_SECURE=false`, `DEBUG=true` or a wildcard CORS origin. Secrets belong
in a secret manager; `.env` is ignored in every directory of the tree.
