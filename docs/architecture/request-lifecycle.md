# Request lifecycle

What happens between a socket and a row, in order.

```
CLIENT
  │
  ▼
TrustedHost → CORS → GZip                      bootstrap/middleware.py
  │   a request for a host we do not serve is refused before it reaches
  │   anything that logs or allocates
  ▼
RequestContext                                 api/middleware/request_context.py
  │   mints or adopts a request id, binds it to a contextvar
  │   FIRST, because everything after — including the failure of anything
  │   after — needs somewhere to record which request it was
  ▼
SecurityHeaders                                api/middleware/security_headers.py
  ▼
BodyLimit                                      api/middleware/body_limit.py
  │   refuses an oversized body before anything parses it
  ▼
AccessLog                                      api/middleware/access_log.py
  │   one structured line; the consent token is scrubbed from the path
  ▼
Router match                                   api/routers/{v1,public}/
  ▼
Dependencies                                   api/dependencies/
  │   session ← cookie          sessions.py
  │   CSRF on unsafe verbs      csrf.py
  │   Principal ← session       authentication.py
  │   matrix + row scope        authorization.py
  │   cursor, limit, sort       pagination.py
  │   unknown filters refused   filters.py
  ▼
Domain service, in ONE transaction             domain/*/service.py
  │   validates, mutates, and writes the audit row together;
  │   registers side effects to run after the commit
  ▼
Repository                                     db/repositories/
  │   hand-written SQL; scope is a WHERE predicate
  │   a write: personal columns sealed first     infrastructure/dkms/rows.py
  │     seal() → one call to the key service      POST /bulk_encrypt
  │   a lookup by a sealed value: its keyed hash  infrastructure/dkms/blind.py
  │     `*_hash = %s`, or `*_ngrams @> %s` for part of a name
  ▼
PostgreSQL
      CHECK constraints · triggers · append-only · revoked grants
  │
  ▼  the response, personal fields as stored: `SE::…`
Portal API client                              src/lib/api/client.ts
  │   finds the sealed values; one batch per response
  ▼
Portal server route                            src/app/dkms/decrypt/route.ts
  │   no session, no decryption; nothing logged
  ▼
Key service                                    POST ${DKMS_URL}/bulk_decrypt
      plaintext back to the page, never to the API
```

## Ordering that is load-bearing

**Request context first.** A 500 with no correlation id is a 500 nobody can match
to the report that produced it.

**Body limit above the routes.** Parsing two gigabytes to discover it is too
large is the denial-of-service this prevents.

**Public routers before authenticated ones.** So `/c/{token}` can never be
shadowed by a path parameter on another router.

## The transaction boundary

One transaction per request that writes, opened by the router and passed to the
service. The service does everything inside it — including `audit.record()` —
so a change and its audit row commit together or not at all.

The key service is called inside the transaction, before the statement that
binds the sealed value. If it cannot be reached the call raises
`DkmsUnavailable`, a `ServiceUnavailable`: the transaction rolls back, nothing
is written, and the caller gets 503 `service_unavailable` rather than a row
with a personal field in the clear.

Side effects wait for the commit. A service registers them with `defer()`
(`core/after_commit.py`) and they run only once the transaction has
committed, so a message never describes a row that was rolled back
([ADR 0012](../decisions/0012-side-effects-after-commit.md)). The worker then
opens the recipient's sealed contact at the moment of sending; if the key
service is down the task raises `DkmsUnavailable` and Celery retries it, with
backoff, up to five times, so a short outage makes a message late rather than
lost.

A dependency never opens one. A guard that wrote an audit row would be writing
outside the transaction the service is about to start, so denials are audited by
the layer that has the connection.

## 403 versus 404

**403 means visible but not permitted.** Anything outside your scope is 404,
because a 403 would confirm the row exists — and existence is exactly what the
scope was meant to withhold. This is why scope is a predicate in the query rather
than a check after it: there is nothing to answer 403 *about*.
