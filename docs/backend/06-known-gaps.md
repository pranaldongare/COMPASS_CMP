# 6. Known gaps

Where the code today departs from the rules the rest of `docs/` states. Found
while writing this guide by reading the code against the documents
(2026-09-28). Each is something to know, not something to copy; each is
listed for a decision, and none has been changed yet.

Paths are under `backend/api/src/cmp/`.

## Security

| Gap | Where | Why it matters |
|---|---|---|
| The portals' decrypt route checks only that a session cookie is present | `frontend/*/src/app/dkms/decrypt/route.ts` | It does not ask the API whether the session is valid; noted in [csrf](../security/csrf.md) |
| `/metrics` has no authentication | `bootstrap/application.py` | Fine behind a private network; not on a public one |

## Layering

| Gap | Where |
|---|---|
| SQL outside repositories, in two maintenance sweeps (routers, domain services and `auth` are clean since 2026-10-05 and `tests/unit/test_layer_boundaries.py` keeps them so; the retention sweep is rewritten under S4-01) | `tasks/maintenance/assets.py`, `tasks/maintenance/retention.py` |
| A repository imports another's predicates | `db/repositories/consent.py`, `exchange.py` and `dashboard.py` import from `projects.py` |
| `domain` imports `auth` (codes, rate limits), and `domain`, `auth` and `api` import `tasks` inside functions | `domain/consent/service.py`, `domain/rights/service.py` |

## Documents that disagree with the code

- **Middleware order.** [Request lifecycle](../architecture/request-lifecycle.md),
  [system overview](../architecture/system-overview.md) and the comment in
  `bootstrap/middleware.py` say TrustedHost, CORS and GZip run first. In
  Starlette the last one added runs first, so they run *after* the request
  context, security headers, body limit and access log - see
  [how a request works](02-how-a-request-works.md#the-middleware-a-request-passes-through).
- **The permission matrix has 22 resources.** [Authorization](../security/authorization.md)
  says 19, and the `resources.py` docstring says seventeen.
- **A partial session reaches two routes** (`/auth/mfa/verify` and
  `/auth/mfa/resend`), not one as [authentication](../security/authentication.md) says.
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
- **`migrations.md` and CONTRIBUTING** give `alembic revision -m` without
  `--rev-id`, which does not produce the numbered house style.
- **`backend/api/README.md`** still describes `seed.py` as "a user per role";
  since 2026-09-25 it creates only the administrator.
- **The schema reference README** quotes 93 foreign keys in one place and 102
  in another (102 is right), and `generate-schema-docs.py` does not write
  `schema.sql` though its docstring says it does.

When you fix one of these, fix the document in the same commit and remove the
line here.
