# 0003. Server-side sessions in Redis, reached through a first-party proxy

Status: accepted.

## Context

A token a script can read is a token a script can steal. The console and the
portal are browser applications, and a browser application will eventually
render something a stranger wrote.

## Decision

- A session is an opaque id in an `HttpOnly`, `SameSite=Lax` cookie. The
  session's contents live in Redis with an absolute and an idle timeout.
  There is no bearer token and no JWT.
- Unsafe requests carry a double-submit CSRF header copied from a readable
  cookie.
- Each portal proxies `/api` from its own origin to the API, so the cookie is
  first-party. `NEXT_PUBLIC_API_URL` stays unset; a browser never calls the
  API's origin directly.
- Sign-in with a second factor pending yields a **partial session** that
  authorises the verification route and nothing else.
- Sessions are listable and revocable per user, from Redis, by the
  administrator.

## Consequences

- "Who am I" costs one request to `/auth/me` on first paint, and the client
  holds no identity of its own.
- A cross-origin deployment of a portal looks like a broken sign-in with no
  error. The local-development page says so first.
- Revoking a session is immediate; there is nothing to wait to expire.
- Redis is a hard dependency at sign-in, which is why the API is fail-fast on
  it.

## Revisit when

A non-browser client needs the API. That is a new credential type, not a
change to this one.
