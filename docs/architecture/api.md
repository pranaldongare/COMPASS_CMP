# The API

One FastAPI service, 233 endpoints over 204 paths, all under the API's root
with no version prefix. The interactive reference is at `/docs` in local
development, and `cmp_backend/openapi.json` is the same document, regenerated
from the application whenever a route or schema changes. This page is the map;
the reference is the territory.

## Route families

| Family | Audience | What it covers |
|---|---|---|
| `/auth/*` | staff and data principals | password sign-in, MFA, self-registration and its verification, one-time-code sign-in, sessions, password reset |
| `/c/{token}/*` | public | the consent flow: validate the link, register, confirm contacts, read the notice, record consent |
| `/rights`, `/rights/*`, `/notice/{uuid}` | public | the rights information page, the public request form and its verification, nomination acceptance, the nominee's entry point, the public notice viewer |
| `/me/*` | the signed-in data principal | profile, consents and their history, disclosures, requests, files, disputes, nominations, notifications |
| `/projects/*`, `/approvals/*`, `/sites/*` | staff | projects and their transitions, processors and their decisions, approvals and proofs, sites, owners, agents and links |
| `/purposes/*`, `/processors/*`, `/sources/*` | staff | the registry: purposes, processors and their respondents, data sources and their owners |
| `/notices/*` | staff | notices, purposes on a notice, language renditions, checklist, publication, document import |
| `/links/*`, `/consents/*` | staff | consent links, the consent register, artefacts, grants, history |
| `/exports/*`, `/imports/*`, `/collections/*`, `/assets/*` | staff | the disclosure register, import batches, collections and their exceptions, assets and their subjects |
| `/requests/*`, `/tickets/*` | DPO, administrator; respondents for tickets | the rights register and every action on a request; a respondent's own tickets |
| `/delegations/*` | staff | cover: arranging it, ending it, what I hold |
| `/users/*` | administrator, DPO | accounts, roles, sessions |
| `/audit/*` | DPO, administrator | search the trail, open one entry, verify the chain |
| `/dashboard`, `/notifications/*`, `/meta/*` | signed in | the role-aware landing aggregate, notification resend, enumerations and version |
| `/health`, `/ready`, `/metrics` | operators | liveness, readiness, Prometheus |

Public routers are mounted before authenticated ones so that `/c/{token}` can
never be shadowed by a path parameter on another router.

## Authentication on the wire

- A session is an `HttpOnly`, `SameSite=Lax` cookie, `cmp_session`, holding
  an opaque id; the session itself lives in Redis. There is no bearer token.
- Unsafe verbs carry the double-submit CSRF header `X-CSRF-Token`, copied by
  the page from the readable cookie `cmp_csrf`.
- A staff sign-in returns `mfa_required: true` and a **partial session** that
  authorises only `/auth/mfa/verify`. Every other route answers 401 with code
  `mfa_required` until the code is verified.
- Both portals reach the API through their own `/api` proxy so the cookie is
  first-party. A direct cross-origin call from a browser will lose it.

Details: [sessions.md](../../cmp_backend/docs/security/sessions.md),
[csrf.md](../../cmp_backend/docs/security/csrf.md),
[authentication.md](../../cmp_backend/docs/security/authentication.md).

## Conventions every route follows

**Identifiers are uuids.** No integer primary key appears in a path, a body,
an export or a log. `/c/{token}` is the one capability-shaped exception.

**Lists are cursor-paginated.** `limit` and `cursor`; never an offset, which
skips or repeats rows while a collection campaign is writing. Cursors are
HMAC-signed because they are interpolated into the next query's comparison.

**Unknown query parameters are refused** with 400. A filter that is silently
ignored returns every row to somebody who asked for some.

**Scope is in the query.** A row outside the caller's scope is never selected,
so it answers 404. 403 is reserved for a row the caller can see but may not
act on, and every 403 is audited.

**Enumerated fields arrive as plain strings** and are converted inside the
service through one helper, so an unknown value answers 422 with the valid
choices named, never 500. See
[ADR 0008](../decisions/0008-unknown-choices-are-422.md).

**The server keeps the facts that make a record evidence.** The consent call
does not carry `served_at`: the server recorded the serving when it rendered
the notice, and refuses a consent without one. The field is still accepted
from older clients and ignored. See
[ADR 0011](../decisions/0011-server-held-notice-serving.md).

**Readiness is specific.** `GET /ready` names the deployed schema revision
and the one this build expects, and answers 503 when they differ.

## The error contract

Every error, from a validation failure to a rate limit, has one shape:

```json
{
  "error": {
    "code": "transition_blocked",
    "message": "Identity is not verified",
    "field": null,
    "request_id": "63c282acee7f4718b3a1c0c1a9f2e6d4"
  }
}
```

| Status | Codes seen most |
|---|---|
| 400 | `otp_invalid`, `registration_incomplete`, `bad_request` |
| 401 | `unauthenticated`, `mfa_required` |
| 403 | `forbidden`, `csrf_failed` |
| 404 | `not_found` - including rows outside scope |
| 409 | `conflict`, `transition_not_permitted`, `transition_blocked`, `already_verified`, `site_exists`, `item_applied`, `no_holders`, `language_unapproved` |
| 422 (consent) | `notice_not_served` when no serving of the notice to this person exists; `notice_stale` when it is older than six hours |
| 422 | `validation_failed`, with `field` naming the input |
| 429 | `rate_limited`, with a `Retry-After` header the browser may read |
| 503 | `service_unavailable` - a datastore could not be reached |

The `request_id` is the correlation id the first middleware minted; quote it
when reporting a failure and the log line is one search away.

## Neutral answers

Some routes deliberately answer the same way whatever happened, because the
difference would tell a stranger something about who is registered:

- `POST /auth/register`: identical whether the contact is new or already an
  account
- `POST /auth/otp/request`: identical whether the contact is registered
- `POST /rights/requests`: a reference is issued either way; a code goes only
  to a contact on file
- `POST /rights/requests/verify` and `POST /rights/nominee/start`: the same
  sentence for an unknown reference and a wrong code
- `GET /rights/nominations/{token}`: every failure is the same 404

## Rate limits and lockout

Bounded surfaces and their keys are listed in
[rate-limiting.md](../../cmp_backend/docs/security/rate-limiting.md). The
ones a developer meets first: five sign-in failures lock an account for
thirty minutes; five one-time codes per contact per hour; five attempts per
code. All counters live in Redis under `rate:*`, which is why a test suite
clears its own buckets rather than waiting an hour.

## Generated artefacts

| Artefact | Command |
|---|---|
| `cmp_backend/openapi.json` | `uv run python -c "from cmp.main import app; import json; json.dump(app.openapi(), open('openapi.json','w'), indent=2)"` from `cmp_backend/` |
| `src/types/api-schema.d.ts` in each portal | `npm run api:types` while the API is running |

The portals' hand-curated types in `src/types/*.ts` are contract-tested
against the generated schema, so a field renamed on the server fails a unit
test on the client rather than a page at runtime.
