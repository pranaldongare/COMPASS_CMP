# COMPASS CMP

A consent management platform built to India's **Digital Personal Data
Protection Act 2023** and the DPDP Rules 2025: notices, purpose-by-purpose
consent, the collection that follows, and the rights a data principal can
exercise afterwards, all recorded so that what happened can be proved years
later.

Three deployable projects in one repository, one API:

| Path | Stack | What it is |
|---|---|---|
| [`cmp_backend/`](cmp_backend) | FastAPI 0.141, PostgreSQL 16, Redis 7, Celery 5, Python 3.12 | The API: 238 endpoints, 32 tables, raw SQL over psycopg 3, no ORM, 24 raw-SQL migrations |
| [`cmp_internal_ui/`](cmp_internal_ui) | Next.js 16, React 19, Tailwind 4, TanStack Query | The staff console on port 3000: password and emailed code sign-in, the registers, the DPO's rights queue, a respondent's tickets |
| [`cmp_public_ui/`](cmp_public_ui) | the same | The data principal's portal on port 3001: the consent link, sign-up, code sign-in, the rights pages, her own consents and requests |

Documentation starts at [docs/README.md](docs/README.md). The short version
of the architecture is
[docs/architecture/system-overview.md](docs/architecture/system-overview.md);
the vocabulary is in [docs/glossary.md](docs/glossary.md).

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
The short form, with Docker Desktop for the datastores and Node 22:

```bash
# datastores
cd cmp_backend && docker compose -f docker/docker-compose.yml -p cmp up -d db redis

# API, migrations, seed
cp .env.example .env                      # POSTGRES_DB=cmp_dev, PUBLIC_BASE_URL=http://localhost:3001, CONSOLE_BASE_URL=http://localhost:3000
uv sync --all-extras --dev
uv run alembic upgrade head
uv run python scripts/seed.py             # refuses outside local/test
uv run python -m cmp --port 8000

# workers, two terminals
uv run celery -A cmp.tasks.app worker -Q high_priority,email,documents,reports,notifications,default -l info --pool=solo
uv run celery -A cmp.tasks.app beat -l info

# the two portals
cd ../cmp_internal_ui && cp .env.example .env.local && npm install && npm run dev    # http://localhost:3000
cd ../cmp_public_ui   && cp .env.example .env.local && npm install && npm run dev    # http://localhost:3001
```

Leave `NEXT_PUBLIC_API_URL` unset in both portals: each proxies `/api` so
the session cookie stays first-party. The API reference is at
`http://127.0.0.1:8000/docs`.

The whole backend can also run as containers from
`cmp_backend/docker/docker-compose.yml` (`db`, `redis`, `migrate`, `api`,
`worker`, `beat`, and `nginx` under the `proxy` profile); see
[docs/operations/deployment.md](docs/operations/deployment.md).

## Seeded accounts

Created by `scripts/seed.py`, which refuses to run outside `local` and
`test`. The password for every staff account is `SeedPassw0rd!2026`, and
every staff sign-in then asks for a code, which a local deployment writes to
`cmp_backend/var/outbox.log`.

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
cd cmp_backend && uv run pytest                       # unit, integration, security; needs PostgreSQL and Redis
cd cmp_internal_ui && npm run verify                  # typecheck, lint, vitest
cd cmp_public_ui && npm run verify
cd cmp_internal_ui && npx playwright test --workers=1 # browser, against the running stack
cd cmp_public_ui && npx playwright test --workers=1
```

What each suite covers, the counts, and the rules for running them together
are in [docs/operations/testing.md](docs/operations/testing.md).

## Repository layout

```
cmp_backend/       the API, migrations, Celery tasks, operator scripts, docker/, its own docs/
cmp_internal_ui/   the staff console
cmp_public_ui/     the data principal's portal
docs/              architecture, domain workflows, operations, decisions, glossary, history
CHANGELOG.md       what changed, by date
CONTRIBUTING.md    how a change lands
```

Package by package: [docs/architecture/repository-layout.md](docs/architecture/repository-layout.md).

## Configuration

Every setting is documented in `cmp_backend/.env.example` and explained in
[configuration.md](cmp_backend/docs/operations/configuration.md). Production
refuses to start on a development `SECRET_KEY`, a default database password,
`COOKIE_SECURE=false`, `DEBUG=true` or a wildcard CORS origin. Secrets belong
in a secret manager; `.env` is ignored in every directory of the tree.
