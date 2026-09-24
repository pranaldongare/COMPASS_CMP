# CMP — Consent Management Platform (staff console)

The staff console for the CMP backend. Next.js 16 (App Router), React 19,
TypeScript strict, Tailwind 4, TanStack Query.

Everything a data principal uses - the public consent flow, sign-up, the
public rights pages, her own consents and requests - lives in
[`../portal`](../portal), a separate
deployment on its own port. This console has no route for any of it. A data
subject who signs in here is pointed at that portal
(`NEXT_PUBLIC_SUBJECT_PORTAL_URL`), and the sign-in page links to it.

---

## Running it

```bash
npm install
cp .env.example .env.local     # leave NEXT_PUBLIC_API_URL unset: /api is proxied to the API
                               # set DKMS_URL=http://localhost:32688 - the template has a placeholder
npm run dev                    # http://localhost:3000
```

The API and the key service must be running (see the backend README, or
[docs/operations/local-development.md](../../docs/operations/local-development.md)
for the whole stack). Node 22. `npm run verify` runs the type check, the linter
and the unit tests together.

**`DKMS_URL` is required.** The API serves personal fields sealed (`SE::…`);
the client sends every sealed value in a response to `/dkms/decrypt` on this
origin, and that route - server-side, never in the browser - posts them to
`${DKMS_URL}/bulk_decrypt`. It is not `NEXT_PUBLIC_`: the browser never
learns where the key service is. Unset, wrong, or unreachable from this
server, and every name and contact on the page shows as `SE::…`; the dev
server's terminal says `[dkms] … unreachable` or `answered <status>`. It is
read at startup, so restart after changing it. Every variable is in
[configuration.md](../../docs/operations/configuration.md#the-portals).

> If every button appears to do nothing in development, check the browser console
> for `403` on `/_next/static/chunks/*`. Next 15.2+ refuses dev assets from an
> origin it does not recognise, and `localhost` and `127.0.0.1` are different
> origins to that check — the page renders, nothing hydrates, and the failure is
> silent. `allowedDevOrigins` in `next.config.ts` lists both.

| Script | Does |
|---|---|
| `npm run dev` | Development server |
| `npm run build` | Production build — fails on a type or lint error |
| `npm run verify` | typecheck + lint + unit tests |
| `npm test` | Vitest |
| `npm run e2e` | Playwright, against a real browser and a real API |
| `npm run api:types` | Regenerate types from the live OpenAPI document |
| `npm run api:check` | `api:types`, then the type check: fails when the curated types disagree with the API |

---

## How it is put together

```
src/
  proxy.ts                the first thing that touches a request: CSP nonce,
                          cookie-presence redirect (Next 16's middleware.ts)
  app/                    routes
    dkms/decrypt/         route handler: opens sealed values through the key
                          service, for a request carrying a session cookie
    (app)/                authenticated — RequireAuth, AppShell, RequireSection
                          dashboard, projects, approvals, notices, purposes,
                          processors, sources, sites, links, consents, exports,
                          imports, collections, requests (the rights queue),
                          tickets (a respondent's own), users, audit, cover,
                          notifications, profile
    sign-in/              staff password + MFA step-up, reset; each page
                          behind AuthPageGate
  features/<name>/        one folder per business area:
    api.ts                thin endpoint functions - no React
    queries.ts            useQuery hooks, keyed from lib/query/keys
    mutations.ts          useMutation hooks and what they invalidate
    schemas.ts            zod form schemas, mirroring the API's validation
    components/           the feature's own forms and dialogs
    index.ts              the barrel pages import from
  components/
    ui/                   primitives, status badges, charts, dialog, graphics
    data-display/         resource list, activity feed, audit detail
    forms/                useApiForm, file input, checkbox group
    layout/               the app shell and the auth layout
    security/             Can, RequireSection, SessionWarning, AuthPageGate
                          (sends a visitor who is already signed in, or
                          halfway through the code step, to where they
                          belong) - courtesies, never a boundary
    feedback/             the error boundary
  lib/
    api/                  axios: credentials, CSRF, request id, error normalisation
    errors/               ApiError - the API's error contract, as a type
    query/                every query key, and the shared hook options
    permissions/          reads me.nav; holds no copy of the matrix
    security/             public routes, sanitising, session timeout
    config/  format/      environment with defaults; dates, durations, hashes
  providers/              error boundary, query, theme, toast, auth - in that order
  schemas/                shared zod primitives (contacts, files, security)
  types/                  curated API types per domain, contract-tested against
                          the generated api-schema.d.ts
  styles/                 tokens → themes → bridge → base → utilities → print
  test/                   MSW server, fixtures, render helpers
```

Design tokens live in `src/styles/tokens.css`; `globals.css` only imports the
style layers in dependency order.

### The rules the frontend follows

**It holds no copy of the permission matrix.** Navigation comes from `me.nav`,
computed by the server. A local copy drifts, and a drifted copy shows people
buttons that 403 on click.

**It holds no copy of the state machine.** The project transition controls are
rendered entirely from `GET /projects/{uuid}/transitions`: which transitions
exist for this role, whether each is allowed, and what is blocking the others. A
blocked transition renders as a *disabled button with its reason* rather than
being hidden — hiding it leaves the user unable to work out what to fix.

**The session is never touched by JavaScript.** It is an HttpOnly cookie, so
"who am I" is answered by asking `GET /auth/me`. That costs one request on first
paint and removes the entire "XSS exfiltrates the token" class. The cost is CSRF,
which the double-submit header in `api-client.ts` pays.

**Errors are parsed once.** Every failure becomes an `ApiError` carrying the
server's code, field and request id. Components branch on `isValidation`,
`isConflict`, `needsMfa`; nobody reads a response body.

**Nothing 4xx is retried.** A 403 will still be a 403 on the fourth attempt, and
retrying produces three more audited access denials in the DPO's log. Mutations
are never retried at all — they write to append-only tables, and a retried export
would corrupt the disclosure record.

---

## Design system

Tokens live in `src/styles/tokens.css` and nowhere else. Colour is OKLCH, so equal
lightness steps look equal and the palette stays balanced when inverted for dark
mode instead of turning muddy.

Three states, not two: light, dark and **system**, with a live media-query
listener so an OS that switches at sunset switches the app too. The class is
applied by an inline script before first paint, so there is no white flash.

**Colour never carries meaning alone.** Every status badge shows its label, so the
information survives greyscale printing and colour-blindness. Withdrawal is amber
rather than red — it is a right being exercised, not an error.

---

## Testing

```bash
npm test                                    # unit
E2E_API_URL=http://127.0.0.1:8000 E2E_STAFF_LOGIN=dpo@cmp.local E2E_STAFF_PASSWORD='SeedPassw0rd!2026' \
  npx playwright test --workers=1           # end-to-end, serially
```

The suite builds the console and serves it on `127.0.0.1:3100` itself; the
API, the worker and the key service must be running, and `.env.local` must
carry a working `DKMS_URL`. Without `E2E_STAFF_LOGIN` and
`E2E_STAFF_PASSWORD` the session-cookie tests in `auth.spec.ts` skip; without
`E2E_API_URL` on `127.0.0.1`, a `controls.spec.ts` test fails on the cookie's
origin. The rest of the variables are in
[docs/operations/testing.md](../../docs/operations/testing.md#browser-tests).

The browser suite has five Playwright projects: `setup` signs in every role
once and saves the sessions, then `chromium`, `mobile`, `localhost-cookies` and
`visual` run the specs (account contacts, audit, auth, controls, detail pages,
forms, links, messages, navigation coverage, notice review, notice upload,
routing, sealed values never shown, visual). Run it serially and never
alongside pytest; the why is in
[docs/operations/testing.md](../../docs/operations/testing.md).

Unit tests cover the pieces where a mistake is invisible in review: error
classification, and the formatting of values a data subject reads (a retention
period rendered as `P3Y` instead of "3 years" is a notice nobody understands).
`src/lib/api/client.test.ts` proves a response's sealed values come out of the
client opened, in one call to `/dkms/decrypt`, and that a response with
nothing sealed makes no call.

End-to-end tests run in a real browser because that is the only place the things
being tested exist: the HttpOnly cookie and the CSRF header. They assert the security properties too — that an unauthenticated
visitor never sees a flash of the page before redirecting, and that a failed
sign-in does not reveal whether the account exists.

The public-surface tests run **serially**. That surface is rate limited per
address, and parallel workers share one address from the API's point of view;
running them concurrently makes them contend with a control that is working
correctly and produces failures that look like application bugs.
