# 6. Known gaps

Where the code today departs from the rules the rest of `docs/` states. Found
while writing this guide by reading the code against the documents
(2026-09-28), and kept since: a gap that has been fixed is removed. The
routers, domain services and `auth` were cleared of their own SQL and audit
writes on 2026-10-05, and `tests/unit/test_layer_boundaries.py` keeps them so.
Each line left is something to know, not something to copy, and is listed
for a decision.

Paths are under `backend/api/src/cmp/`.

## Security

| Gap | Where | Why it matters |
|---|---|---|
| The portals' decrypt route checks only that a `cmp_session` or `cmp_ticket` cookie is present (SEC-1, open) | `frontend/*/src/app/dkms/decrypt/route.ts` | It checks the value of neither and does not ask the API; accepting an outside holder's ticket cookie since 0049 keeps the gap open. Noted in [csrf](../security/csrf.md) |
| `/metrics` has no authentication | `bootstrap/application.py` | Fine behind a private network; not on a public one |

## Layering

| Gap | Where |
|---|---|
| SQL outside repositories, in two maintenance sweeps (routers, domain services and `auth` are clean since 2026-10-05 and `tests/unit/test_layer_boundaries.py` keeps them so; the retention sweep is rewritten under S4-01) | `tasks/maintenance/assets.py`, `tasks/maintenance/retention.py` |
| A repository imports another's predicates | `db/repositories/consent.py`, `exchange.py` and `dashboard.py` import from `projects.py` |
| `domain` imports `auth` (codes, rate limits), and `domain`, `auth` and `api` import `tasks` inside functions | `domain/consent/service.py`, `domain/rights/service.py` |

## Documents that disagree with the code

- **A request for a host we do not serve is logged before it is refused.**
  TrustedHost, CORS and GZip are registered before our middleware, and
  Starlette runs the last one added first, so they run *after* the request
  context, security headers, body limit and access log - see
  [how a request works](02-how-a-request-works.md#the-middleware-a-request-passes-through).
  The docstrings once claimed the opposite; since 2026-10-08 they say what
  happens. Harmless, but the intent was to refuse first.
- **There is no self-service "sign out everywhere".** All sessions end on a
  password change or reset and on the administrator's actions only.
- **Unknown query parameters are refused on about fifteen routes**, not
  everywhere as [API conventions](../architecture/api.md) implies.
- **The error envelope** omits `field` when empty rather than sending `null`,
  and [API conventions](../architecture/api.md) does not list 413,
  `bad_cursor`/`bad_sort`/`bad_limit`, `link_invalid` or 502.
- **`schema.md`** leaves `message_template` out of its table groups and
  describes `PATCH /me`'s date of birth as unchecked (it now uses
  `DateOfBirth`).
- **CONTRIBUTING** gives `alembic revision -m` without `--rev-id`, which
  does not produce the numbered house style.
- **`backend/api/README.md`** still describes `seed.py` as "a user per role";
  since 2026-09-25 it creates only the administrator.
- **The personal-data inventory cannot see the rights trail.**
  `GET /requests/{request_uuid}/trail` serves the request's trail with the sealed
  names of who acted, and answers `list[dict]` with no response model, so
  `docs/tools/personal-data-scan.py` finds no field to list and
  [personal-data.md](../domain/personal-data.md#keeping-this-document-true) leaves
  it out; so do `/requests/{request_uuid}/linked/trail` and the principal's
  `/me/requests/{request_uuid}/trail`, which answer through the same `_trail` in
  `api/routers/v1/rights.py`. The HTTP suite's coverage test fails when the suite
  calls a route that answers with a sealed value the documentation does not list,
  which is how it was found (2026-11-08);
  `tests/http/test_19_dismissed_reporter_rights.py` does not call it for that
  reason. A response model on the three routes closes it.

When you fix one of these, fix the document in the same commit and remove the
line here.
