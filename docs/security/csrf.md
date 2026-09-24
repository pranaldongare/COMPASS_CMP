# CSRF

## The problem

The session cookie is HttpOnly, which is right — script cannot read it. The cost
is that the browser attaches it to **any** request to this origin, including one
triggered by a form on a site the user did not expect to be acting on their
behalf.

## The defence

Double-submit. A second token arrives two ways:

* as a cookie the page **can** read (`cmp_csrf`, not HttpOnly);
* as a header the page had to set deliberately (`X-CSRF-Token`).

A cross-site attacker can cause the cookie to be sent — that is the whole problem
— but cannot read it to copy into the header, because the same-origin policy
stops them.

## Two decisions

**Checked on unsafe verbs only** — POST, PUT, PATCH, DELETE. Requiring a header
on GET breaks every link a browser can follow, and a GET that changes state is a
bug this would only paper over.

**Compared against the session's stored token**, not against the cookie.
Comparing cookie to header would pass for an attacker who could set both, which
is exactly the position a subdomain takeover puts them in.

## Constant time

`hmac.compare_digest`. A comparison that returns early on the first differing
byte leaks the token one byte at a time to anyone patient enough.

## Failing closed

An absent, empty or whitespace-only header fails. This is the case a naive
`stored == supplied` gets wrong: both are empty for a request with no header at
all, and an equality check passes.

`tests/security/test_csrf.py` asserts each of these, including the empty case.

## Not covered: the portals' own `/dkms/decrypt`

Everything above is the API's. Each portal also serves one route of its own,
`POST /dkms/decrypt` (`frontend/{console,portal}/src/app/dkms/decrypt/route.ts`,
the same file in both), which takes sealed values the page was served and
asks the key service to open them
([ADR 0016](../decisions/0016-personal-data-sealed-by-a-separate-key-service.md)).
It does not pass through the API, so none of the checks on this page apply to
it. What it does today:

- **No CSRF token.** It does not read `X-CSRF-Token`, and the client does not
  send one (`src/lib/dkms/api.ts`).
- **Presence of a session cookie, not a session.** It answers 401 when there is
  no `cmp_session` cookie (`route.ts:77-81`) and otherwise does not check it.
  The cookie's value is never sent to the API. The portal's `proxy.ts` skips
  `/dkms`, so nothing in front of it checks either.
- **No rate limit**, and up to 5,000 records per call.
- **No CORS headers**, so a page on another origin cannot read what it answers.

The design note in the route says the browser only sends ciphertext the API
already served it, having passed the permission matrix and the scope. The
route does not check that: it will open any `SE::` value in the body.

**This is an open question, under review.** Whether the route should validate
the session, require the CSRF header, be rate-limited or be bound to what the
API served has not been decided. Until it is, treat the route as able to open
any ciphertext for anyone who sends a `cmp_session` cookie of any value. The
wider picture is in [encryption-at-rest.md](encryption-at-rest.md).
