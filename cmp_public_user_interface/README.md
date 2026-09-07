# CMP — Consent Portal (data-principal frontend)

The data principal's side of the CMP backend: the public consent flow, self-
registration, the public rights pages, and a signed-in view of her own consents
and rights requests. Next.js 16 (App Router), React 19, TypeScript strict,
Tailwind 4, TanStack Query.

Split out of `cmp_internal_user_interface`, which is the staff console alone. The two
share a backend, a design system and most of `src/lib`, but nothing a member of
staff uses ships here, and nothing a data principal uses ships there.

---

## Running it

```bash
npm install
cp .env.example .env.local     # leave NEXT_PUBLIC_API_URL unset: /api is proxied to the API
npm run dev                    # http://localhost:3001
```

The API must be running (see the backend README). The backend's
`PUBLIC_BASE_URL` should point here, because the links it puts in emails - a
nominee's acceptance link, for one - land on this portal.

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
  c/[token]/            the public consent flow - the one screen a data subject must use
  sign-up/              data-principal self-registration (mobile, optional email, dual code)
  sign-in/              one-time code to the registered mobile or email. No password.
  rights/               public rights information and requests (Rule 9, 14)
  rights/nominee/       a nominee acting under s.14
  rights/nominations/   the nominee's accept / decline link
  (app)/my-consents/    her consents, the frozen notice text, withdrawal
  (app)/my-requests/    her rights requests, nominations, disputes
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
(`NEXT_PUBLIC_STAFF_PORTAL_URL`) and offered sign-out. That is a courtesy, not
a boundary: the permission matrix on the server is what protects the data.

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

The end-to-end suite signs in once as the seeded data principal
(`subject@cmp.local`) with a code read from `cmp_backend/var/outbox.log`, and
drives sign-up, the consent link, the public rights pages and her own pages.
The DPO's half of a rights request is exercised by the staff console's suite.
