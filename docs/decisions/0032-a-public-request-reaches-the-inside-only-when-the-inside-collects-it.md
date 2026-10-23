# 0032. A public request reaches the inside only when the inside collects it

**Status:** proposed · 2026-10-23. A proof of concept on branch
`poc/option2-sqs-relay`: `backend/relay` (the bridge and the collector),
`cmp.api.middleware.relay_open_sealed`, the relayed-session rule in
`cmp.api.dependencies.sessions`, `RELAY_INGRESS_KEY`. If accepted, it
amends [ADR 0016](0016-personal-data-sealed-by-a-separate-key-service.md)
(see *Decision*). ADR 0016 has not been edited yet.

## Context

The data principal's portal is to run on AWS
([portal deployment](../deployment/portal-frontend-aws.md)). That plan put
the portal in the same VPC as the API and the key service, or one peered with
it. The organisation's answer is that the API, the database and the key
service stay inside its own network. **That network accepts no inbound
connection of any kind.** It allows outbound HTTPS only, through its proxy,
from a fixed set of public addresses.

So the portal cannot call the API, and it cannot reach the key service to
open the values it shows (ADR 0016). The key service must not be reachable
from outside anyway, because it authenticates nobody. Something inside has to
fetch the work.

The options considered were these:

1. A VPN or Direct Connect into the network. This is an inbound path, and it
   was refused.
2. A queue on AWS that the inside polls. This is the one chosen.
3. A reverse tunnel opened from inside, such as SSH or a vendor connector. It
   is a long-lived outbound connection that carries inbound traffic, which the
   network team treats as inbound.

## Decision

- **Requests travel through Amazon SQS, collected from inside.** A *bridge*
  runs beside the portal on each AWS instance. The portal's `/api` rewrite
  points at it. The bridge puts each request on a request queue and waits for
  the reply on its own reply queue. A *collector* inside long-polls the
  request queue over outbound HTTPS, through the proxy. It calls the API and
  sends the reply back. Nothing on AWS holds an inside address. Bodies over
  256 KiB travel as objects in S3, which the reader deletes. A lifecycle rule
  removes any left behind within a day.
- **What AWS holds is sealed by us.** The bridge seals each request to the
  collector's X25519 public key, using ECIES in the shape of HPKE, with
  AES-256-GCM. The collector seals the reply under a key derived for that one
  request, which only the asking bridge holds. Every seal is bound to its
  request id and its kind. SQS and S3 hold ciphertext only. Their own
  encryption at rest (SSE-SQS, SSE-S3) is a second layer, not the one relied
  on, so no customer-managed KMS key is used. The reason is that requests are
  personal data in transit: contacts, one-time codes, session cookies,
  uploaded documents.
- **The collector enforces the relay's rules.** Anyone allowed to send to the
  request queue can seal a request, so the collector treats every message as
  untrusted. It re-applies the bridge's checks and adds its own:
  - the public route allow-list: 58 routes, and every staff route refused;
  - the header and cookie filter;
  - the deadline;
  - replies only to a configured reply queue;
  - a first check for sealed values in the query and the body.
- **The API opens sealed values in relayed replies, and only there.** A portal
  on AWS cannot reach the key service. So when a request carries the
  collector's shared secret (`X-CMP-Relay-Key`, matched against
  `RELAY_INGRESS_KEY`), the API opens every `SE::` value in its JSON reply
  itself, in one call to the key service. Every other reply is served as
  stored, exactly as before. **This amends ADR 0016**, which says the API does
  not decrypt its responses. On acceptance, ADR 0016 gains an *Amended*
  section pointing here. The relay key is the only signal the API trusts that
  a request is relayed; no other header marks one.
- **The collector never reaches the key service.** It holds the ingress
  secret, not a key-service address. What it gets is the replies the API
  chose to open for the requests it relayed.
- **The API is the authority that no sealed value comes in.** The opener
  opens any `SE::` string in a relayed reply, under the type its own envelope
  names, and nothing ties the value to its row or owner. `seal()` passes an
  already-sealed value through untouched, which internal copies rely on. So
  any input the API stores or echoes back (a name, an attachment's file name,
  the User-Agent kept with a session, a message's body) would let someone
  submit another person's ciphertext and read it back opened. When the relay
  key matches, the API therefore reads the request with its own parser before
  the route runs, and refuses with 422 `sealed_value_refused` any request
  with `SE::` in:
  - a query parameter's name or value, decoded;
  - any header value except `Cookie`;
  - a form body (multipart or urlencoded): every field name, text value and
    upload file name, as the routes' own parser reads them;
  - any other body: every key and string of its JSON, or else the body as
    UTF-8 and as latin-1.

  What it cannot read is not let through unread: JSON too deeply nested to
  walk is refused, and a form the parser cannot read goes to the route, which
  fails on it. Only the bytes of an uploaded file are not searched; they come
  back only as a download, never inside JSON, which is all the API opens. The
  collector's own check stays as the first gate. It is not the guarantee,
  because it parses multipart with a different library, and the review found
  bodies the two read differently (a file name, a part's transfer encoding,
  the form's character set).
- **Only a data principal's session is honoured through the relay.** The
  console and the portal share the session cookie's name, and a few routes on
  the allow-list accept any signed-in user (`/auth/me`, `/auth/sessions`,
  `/notifications`, which for a DPO returns the staff feed). The API marks
  every relayed request, and its session lookup refuses with 401 a session
  whose effective role is not `data_subject`. The check is on the session's
  role, not the account's: a member of staff signed in on the portal with a
  code holds a data principal's session and keeps working. Staff routes are
  also not on the allow-list.
- **A deadline on every request, and writes at most once.**
  - **The deadline.** The bridge gives each request 25 s, or 50 s for any
    `multipart/form-data` request. After that plus 2 s, it answers 504.
  - **The front door waits longer.** The ALB's idle timeout and, with
    CloudFront, its origin response timeout must each exceed the longest
    deadline + 5 s. Both are 60 s by default. The upload deadline may be
    raised only together with them. Were the front door to give up first, the
    browser would show a failure that the inside could still record.
  - **On AWS's clock.** The bridge stamps the deadline with its clock, kept on
    AWS's by Amazon Time Sync. The collector measures it against AWS's clock,
    not its own: it reads the timestamps SQS puts on each message, keeps the
    median offset of its clock from AWS's over the last 20 or so first
    receives, and counts the time left as the deadline minus its own time
    corrected by that offset. It logs the offset on every request, and warns
    (`relay.clock_skew`) when it is over 1 s.
  - **Nothing past it.** The collector never starts a request past its
    deadline, and never replies to one.
  - **Time for a write.** A write starts only with at least 18 s left;
    otherwise the answer is 503 `deadline_too_close`. The time left is checked
    again after the write's message is deleted, and the API's timeout is
    taken from the time left at the call. This stops a consent the person saw
    fail from being recorded later.
  - **Message order.** A write's message is deleted before the API is
    called; a read's after its reply is sent. Neither is retried after a
    collector dies: the visibility timeout (180 s) is longer than the queue's
    retention (60 s). A request id seen recently is dropped.
- **Exactly one bridge per reply queue.** SQS cannot hand a bridge only its
  own replies. A bridge delivers a reply it is waiting for; deletes one it
  gave up on or forgot (it remembers about 10,000 ids for about 5 minutes),
  or one received 5 times or more, as `late_reply`; and hands anything else
  straight back to the queue as `foreign_reply`, a warning that another
  bridge shares the queue. Ping replies go the same way. Sharing a queue is a
  misconfiguration. Reply queues are fixed in configuration, two for two
  portal instances.
- **The collector drains when stopped.** It finishes what its workers are
  handling, hands back anything received after the stop
  (`ChangeMessageVisibility` 0) for the next collector, and takes nothing
  more. Its unit allows 120 s for that.
- **The collector has no stored AWS secret.** It proves itself with a client
  certificate from the organisation's CA, through IAM Roles Anywhere.
  - **Trust.** The trust policy is pinned to that trust anchor and the
    certificate's CN, and optionally (`CollectorIssuerCN`) to its issuer's CN.
  - **Revocation.** Roles Anywhere does not fetch CRLs or ask OCSP. The
    issuing CA's CRL is imported against the trust anchor and kept current
    before each `nextUpdate`, outside the stack (README, *Revoking or
    replacing the collector certificate*).
  - **Where calls may come from.** The role denies every call from outside
    the organisation's egress addresses.
  - **Credentials.** They last an hour and go to one process
    (`credential_process`, never `serve`).
- **The bridge knows when the inside is unreachable.** It pings the inside
  every 10 s. While pings fail, it answers new requests at once with 503
  `inside_unreachable`, instead of making each visitor wait 25 s.
- **The recommended front door is an ALB with WAF, without CloudFront,** so
  TLS from the browser ends in ap-south-1, in India. The bridge takes the
  visitor's address `RELAY_CLIENT_IP_HOP` entries from the right of
  `X-Forwarded-For`: 1 behind the ALB alone, 2 behind CloudFront -> ALB,
  because the ALB then appends CloudFront's address after the visitor's.

## Consequences

- **The organisation opens nothing inbound.** It allows three names outbound,
  on 443, through its proxy:
  - `sqs.ap-south-1.amazonaws.com`;
  - the bucket's own `s3` host;
  - `rolesanywhere.ap-south-1.amazonaws.com`.

  None of them may be TLS-inspected. For `rolesanywhere` that is a rule of
  secrecy, not of breakage: the credential helper trusts the operating
  system's store, where an inspecting proxy's root sits, so an inspected call
  still succeeds and the proxy reads the role's credentials in the response.
- **Both hosts must keep their clocks by NTP:** the bridge on Amazon Time
  Sync, the collector on the organisation's internal time server (no new
  egress). Measuring on AWS's clock absorbs a steady offset on the collector,
  not a clock that jumps, and it takes the bridge's clock as AWS's. Unchecked
  skew would refuse writes and expire pings (the portal reports the inside
  down), or let a write finish after the browser was told it failed.
- **Every call from the portal takes longer:** about two SQS round trips plus
  the proxy, which adds tens to low hundreds of milliseconds. A page that
  makes several calls in sequence feels it.
- **The relay's deadlines bind the front door.** An upload gets 50 s, not
  longer, unless the ALB's and CloudFront's timeouts are raised with it. The
  portal's own proxy and client timeouts are longer than the bridge's wait.
- **The client address depends on the topology.** A wrong
  `RELAY_CLIENT_IP_HOP` records every visitor under a CloudFront or load
  balancer address, in the audit trail and in the per-address sign-in budget,
  which one person could then spend for everyone. It is to be confirmed in
  staging with a header echo.
- **A request can be lost but a write is never repeated by the relay.** If
  the collector dies during an API call, or is killed after its 120 s drain,
  the person sees an error, and a write may or may not have happened. Reads
  are not retried either. A standard queue can still, rarely, hand one
  message to two collectors at once. Then a write could run twice. A FIFO
  queue or API idempotency keys would close that, and neither is built.
- **Opening values is now partly the API's job,** for one caller. Whoever
  holds `RELAY_INGRESS_KEY` and can reach the API is served opened values. The
  secret must be held like a password, on the collector's host and the API
  only. In exchange, the API also takes on two checks for relayed requests:
  sealed values in any input it parses, and the session's role.
- **The portal's own `/dkms/decrypt` route has nothing to reach on AWS.** It
  stays in the code. A value the API did not open, for example because the
  key service failed during the reply, shows as ciphertext, as it does today
  when the key service is down. The route's open question (SEC-1, under ADR
  0016) does not travel to AWS with the portal. It stays open for the
  console and for any portal still deployed inside.
- **Two more processes and two more keys to run.**
  - The bridge runs on each portal instance, and the collector inside.
  - The collector's key pair has a rotation procedure (current and previous
    key).
  - The client certificate must be renewed before it expires, or the
    collector stops and the bridge reports the inside unreachable. On renewal
    the old certificate must be revoked and the imported CRL updated, or the
    old certificate keeps working until it expires. Keeping the CRL current is
    a job the organisation has to automate.
- **What it costs in AWS is small.** Each relayed call is about six SQS
  requests (send, receive, delete, both ways), plus idle long polls and the
  pings. That comes to a few million requests a month at rest, a few dollars
  at the standard-queue price. On top of that come data transfer out to the
  organisation, and S3 only for bodies over 256 KiB. IAM Roles Anywhere adds
  no charge with the organisation's own CA.
- **Bodies are held in memory whole on both sides,** up to 26 MiB. Nothing
  streams, so server-sent events and websockets cannot cross.
- **Each portal instance needs its own reply queue, and the portal's Auto
  Scaling group must fit that.** The stack makes two queues. Until there is a
  queue per instance, created at boot (the production design, not built), the
  group is pinned to two instances, with no scaling policy, AZ rebalancing
  suspended and instance refresh terminating before it launches. Two bridges
  on one queue slow each other and can lose replies.
- **Four alarms watch the queues:** a request or a reply waiting over 30 s,
  and over 100 requests waiting. They cannot see a collector that collects
  and drops every request without a reply (a reply queue it does not list, a
  bridge sealing to a retired key); the portal's 5xx alarms are the backstop
  for that.

## Revisit when

- the organisation allows a private inbound path (Direct Connect,
  Site-to-Site VPN, PrivateLink into its network), so the portal can call the
  API directly;
- the decrypt route's review (SEC-1) concludes, if its answer changes who
  should open values;
- traffic outgrows a static reply queue per instance (a queue per instance,
  created at boot, is the next step), or the portal needs streaming;
- writes need exactly-once delivery (FIFO, or idempotency keys in the API);
- the staging tests of the proxy (S3 `Host` against SNI, `aws:SourceIp` seen
  through the proxy, no inspection of `rolesanywhere`) or of the client
  address (a header echo through the real front door) fail.
