# CMP — Consent Portal (data-principal frontend)

The data principal's side of the CMP backend: the public consent flow, self-
registration, the public rights pages, and a signed-in view of her own consents
and rights requests. Next.js 16 (App Router), React 19, TypeScript strict,
Tailwind 4, TanStack Query.

Split out of the staff console, which is now `frontend/console`. The two
share a backend, a design system and most of `src/lib`, but nothing a member of
staff uses ships here, and nothing a data principal uses ships there.

---

## Running it

```bash
npm install
cp .env.example .env.local     # leave NEXT_PUBLIC_API_URL unset: /api is proxied to the API
                               # set DKMS_URL=http://localhost:32688 - the template has a placeholder
npm run dev                    # http://localhost:3001
```

The API and the key service must be running (see the backend README, or
[docs/operations/local-development.md](../../docs/operations/local-development.md)
for the whole stack). Node 22. The backend's
`PUBLIC_BASE_URL` should point here, because the links it puts in emails - a
nominee's acceptance link, for one - land on this portal.

**`DKMS_URL` is required.** The API serves personal fields sealed (`SE::…`);
the client sends every sealed value in a response to `/dkms/decrypt` on this
origin, and that route - server-side, never in the browser - posts them to
`${DKMS_URL}/bulk_decrypt`. It is not `NEXT_PUBLIC_`: the browser never
learns where the key service is. Unset, wrong, or unreachable from this
server, and her own name shows as `SE::…`; the dev server's terminal says
`[dkms] … unreachable` or `answered <status>`. It is read at startup, so
restart after changing it. Every variable is in
[configuration.md](../../docs/operations/configuration.md#the-portals).

| Script | Does |
|---|---|
| `npm run dev` | Development server, on port 3001 |
| `npm run build` | Production build — fails on a type or lint error |
| `npm run verify` | typecheck + lint + unit tests |
| `npm test` | Vitest |
| `npm run e2e` | Playwright, against a real browser and a real API |

---

## What is here

```
src/app/
  dkms/decrypt/         route handler: opens sealed values through the key
                        service, for a request carrying a session cookie
  c/[token]/            the public consent flow - the one screen a data subject must use
  sign-up/              data-principal self-registration (mobile, optional email, dual code)
  sign-in/              one-time code to the registered mobile or email. No password.
  sign-in/verify/       forwards to the console's code step, query string and
                        all: staff type it and carry it in ?next=
  rights/               public rights information and requests (Rule 9, 14)
  rights/nominee/       a nominee acting under s.14
  rights/nominations/   the nominee's accept / decline link
  (app)/my-consents/    her consents, the frozen notice text, withdrawal
  (app)/my-requests/    her rights requests, the files released with a
                        response, nominations (hers and those naming her),
                        disputes
  (app)/account/        her profile and sessions
  (app)/notifications/  her own events
src/features/
  public-consent/       the consent flow's steps
  my-consents/          /me/consents*, /me/disclosures
  rights/               the public and /me halves of the rights API
  auth/                 registration and one-time codes - nothing with a password
  account/ notifications/ meta/
```

A staff account that signs in here is told where the console is
(`NEXT_PUBLIC_STAFF_PORTAL_URL`) and offered sign-out. `AuthPageGate`
(`src/components/security/`) sits on sign-in and sign-up: a visitor who is
already signed in goes where she was going, and a member of staff goes to
the console, or to its code step when the code is outstanding. That is a
courtesy, not a boundary: the permission matrix on the server is what
protects the data.

The rules the consent flow follows - nothing pre-ticked, accept and decline of
equal prominence, every purpose answered, `served_at` from the server, an
invalid link that says nothing about why - are unchanged from the original
frontend README and matter more than anything else in this tree.

---

## Testing

```bash
npm test                                    # unit
npm run e2e                                 # end-to-end
E2E_CONSENT_TOKEN=<token> npm run e2e       # includes the consent journey
```

The end-to-end suite (specs: consent-flow, rights, sealed-never-shown,
signup, staff-as-principal, subject) signs in once as the seeded data
principal (mobile `+919000000001`) with a code read from
`backend/api/var/outbox.log`, and drives sign-up with two codes, the consent
link, the public rights pages, nomination acceptance, her own pages, a
member of staff signing in as a data principal, and checks that no sealed
value reaches the page. Run it with `--workers=1` and never alongside pytest.
The DPO's half of a rights request is exercised by the staff console's suite.

It builds the portal and serves it on `127.0.0.1:3201` itself; the API, the
worker and the key service must be running, and `.env.local` must carry a
working `DKMS_URL`. Without `E2E_CONSENT_TOKEN` the consent journey skips;
the token is the last segment of an active link's `url_path` from
`GET /links`. The other variables are in
[docs/operations/testing.md](../../docs/operations/testing.md#browser-tests).
