# cmp-relay: the public-ingress relay

**Status: proof of concept** ([ADR 0032](../../docs/decisions/0032-a-public-request-reaches-the-inside-only-when-the-inside-collects-it.md), proposed).

The data principal's portal is going to run on AWS. The API, the database and
the key service stay inside the organisation's network, and that network
accepts no inbound connection. The relay joins the two through Amazon SQS. A
**bridge** beside the portal on AWS puts each `/api` call on a queue as a
sealed message. A **collector** inside asks that queue for work over outbound
HTTPS, which is the only kind of connection the network allows. It checks each
request, calls the API, and sends the sealed reply back. Nothing on AWS knows
an inside address. Every connection across the boundary is opened from
inside. SQS and S3 hold only ciphertext.

- [How a request travels](#how-a-request-travels)
- [What crosses, and what is refused](#what-crosses-and-what-is-refused)
- [Sealing](#sealing)
- [Deadlines, writes and duplicates](#deadlines-writes-and-duplicates)
- [Reply queues: one bridge each](#reply-queues-one-bridge-each)
- [Run it on this machine](#run-it-on-this-machine)
- [Tests](#tests)
- [Configuration](#configuration)
- [Deploying](#deploying)
- [Revoking or replacing the collector certificate](#revoking-or-replacing-the-collector-certificate)
- [Network requirements for the collector](#network-requirements-for-the-collector)
- [Known limits of the proof of concept](#known-limits-of-the-proof-of-concept)

## How a request travels

```text
 browser
    |  HTTPS
    v
 ALB + WAF -> portal (Next.js :3001)       (or CloudFront + WAF -> ALB -> portal)
                              |  /api/* rewrite, /api removed (API_ORIGIN)
                              v
                        bridge 127.0.0.1:8080                       AWS, ap-south-1
                        1. allow-list check (404 if not public)
                        2. seal to the collector's public key
                        3. body > 256 KiB -> sealed object req/<rid>
                              |
                              |  sqs:SendMessage
                              v
              +--------------------------------------+
              |  request queue      (ciphertext)     |    bodies bucket
              |  reply queue A / B  (ciphertext)     |    req/<rid>, res/<rid>
              +--------------------------------------+    (ciphertext, 1-day expiry)
                   ^                         |
   sqs:SendMessage |                         | sqs:ReceiveMessage (long poll, 20 s)
     (sealed reply)|                         |   outbound HTTPS via the proxy
 ==================|=========================|================  organisation boundary
                   |                         v                  (no inbound, ever)
                 collector (inside)
                 4. open; drop if past deadline (on AWS's clock) or a duplicate
                 5. allow-list, header filter (again); sealed-value check
                 6. write: refuse if < 18 s left; delete the message; check again
                    |  http, X-CMP-Relay-Key, X-Forwarded-For = visitor
                    v
                 API :8000 -> PostgreSQL, Redis, DKMS
                 7. relayed requests only: refuses SE:: in any input (422) and
                    any session but a data principal's (401); opens the SE::
                    values in the JSON reply
```

The browser waits on the bridge. The bridge waits for a reply on its own reply
queue. The reply names the request id in a clear message attribute, so the
bridge can find the waiting request and the key to open the reply with. A
reply is never addressed to anyone but the bridge that asked.

The bridge also pings the inside every 10 s (`kind=ping`). The collector
answers by calling the API's `/health`. While pings fail, new requests get an
immediate 503 `inside_unreachable` ("We can't reach our records right now.
Nothing was saved; please try again shortly."), so nobody waits 25 seconds
for a reply that cannot come.

## What crosses, and what is refused

| | Crosses | Refused |
|---|---|---|
| **Routes** | The 58 method-and-path pairs the portal calls (`allowlist.PUBLIC_ROUTES`): sign-up and code sign-in, the consent link, her own records, rights requests and nominations, an outside holder's ticket, reference data. `GET /dev/codes` and `/dev/seed-accounts` only with `RELAY_ENVIRONMENT=local` and `RELAY_ALLOW_DEV_ROUTES=true`. | Everything else, with 404 `not_found`: every staff route, `/auth/login`, the second factor, `/metrics`, `/docs`, `/openapi.json`, `/health`. Also any path with `//`, `..`, a backslash, or an encoded `/`, `\` or `.`. |
| **Sessions** | A data principal's session, or none where a route needs none. A member of staff who signs in on the portal with a code holds a data principal's session, and it crosses like anyone's. | A staff session (signed in at the console with a password and a second factor): 401 from the API, on every route that crosses. |
| **Request headers** | `Accept`, `Accept-Language`, `Content-Type`, `User-Agent`, `X-Request-ID`, the CSRF header. | Everything else, including `Authorization`, `Host`, any `X-Forwarded-*`, and `X-CMP-*`. |
| **Cookies** | `cmp_session`, `cmp_csrf`, `cmp_ticket` (`RELAY_COOKIE_NAMES`). | Every other cookie, such as analytics. |
| **Reply headers** | `Content-Type`, `Content-Disposition`, `Content-Language`, cache headers, every `Set-Cookie`, `Retry-After`, `X-Request-ID` and the API's own hash and export headers. | Everything else, including `Location`, `Server` and CORS headers. |
| **Sealed values** | The bytes of an uploaded file, which are not searched. | `SE::` in any other input: 422 `sealed_value_refused` ([below](#no-sealed-values-in)). |

The collector sets these itself: one `X-Forwarded-For` holding the visitor's
address (validated, or left out), `X-CMP-Relay-Key` and
`Accept-Encoding: identity`. The relay key is the only thing the API trusts to
mark a request as relayed; no other header does.

Three places check, each for what it can judge:

- **The bridge** checks the allow-list first, so a refused request never costs
  a queue round trip.
- **The collector** treats every message as untrusted input, because anyone
  allowed to send to the request queue can seal a request. It applies the
  route allow-list, the header and cookie filter, the deadline and the reply
  queue list again, and runs a first check for sealed values.
- **The API** is the authority on its own input and on sessions. It knows
  which session a cookie names, and only it parses a body exactly as its
  routes will.

### No sealed values in

The API opens the sealed values in a relayed reply, because a portal on AWS
cannot reach the key service. Three facts make that dangerous without a rule
on input:

- **The opener opens any `SE::` string** in a relayed JSON reply, under the
  type its own envelope names. Nothing ties a value to its row or its owner.
- **`seal()` passes an already-sealed value through untouched.** That is on
  purpose: the API copies sealed values between columns.
- **So any input the API stores or echoes back is a channel.** A person who
  holds someone else's ciphertext (from a backup, a log, an export) submits it
  as her own name, an attachment's file name, the User-Agent kept with her
  session, or a message's body, and reads it back opened.

So the API, when the relay key matches, reads the whole request with its own
parser before the route runs, and refuses with 422 `sealed_value_refused` any
request with the prefix `SE::` in:

- a query parameter's name or value, decoded;
- any header value except `Cookie` (the relay key is already removed);
- a `multipart/form-data` or `application/x-www-form-urlencoded` body: every
  field name, every text value and every upload's file name, as Starlette's
  form parser (the routes' own) reads them;
- any other body: every key and string of its JSON, or, when it is not JSON,
  the body as UTF-8 and as latin-1.

What it cannot read is not let through unread. JSON nested too deeply to walk
is refused. A form the parser cannot read is handed to the route, which fails
on the same parser with its own error. Otherwise the body is replayed to the
route unchanged. Because the check is on the input, not per route, a new input
that a route stores or echoes is covered without a change here.

Only the bytes of an uploaded file are not searched. They are the person's own
document, and they come back only as a download, never inside JSON, which is
the only kind of reply the API opens.

The collector refuses the prefix in the query and the body before the API is
called (raw or percent-encoded), so most such requests never reach it. That
check is a first gate, not the guarantee. It reads multipart with a different
library from the API's, and two parsers can read one body differently: a file
name, a part's transfer encoding, the form's character set.

### Only a data principal's session

The console and the portal use the same session cookie name, and a few routes
on the allow-list accept any signed-in user: `/auth/me`, `/auth/sessions` and
`/notifications`, which for a DPO returns the staff feed. So the API marks
every relayed request, and its session lookup refuses with 401 any session
whose effective role is not `data_subject`. A stolen console session therefore
reaches nothing from the internet through the portal.

The check is on the session's role, not the account's. A member of staff who
signs in on the portal with a code holds a data principal's session (her
account role stays what it is), and is served like anyone else.

## Sealing

`sealing.py` is ECIES over X25519, shaped like HPKE base mode:

- **The collector has a long-lived key pair.** The private half stays
  inside. The bridge is configured with the public half.
- **Each request has its own keys.** The bridge makes a fresh ephemeral key
  for every request. Through HKDF-SHA256 it derives two AES-256-GCM keys: one
  for the request, one for the reply. The ephemeral private key is discarded
  at once. The reply key stays in the bridge's memory until the reply comes or
  the request times out.
- **The collector derives the same two keys** from its private key and the
  ephemeral public key carried in the message.
- **Everything is bound to its request.** Every seal authenticates the request
  id and a four-byte kind marker as associated data. A blob cannot be moved
  to another request, or opened as another kind (request, reply, request
  body, reply body).

What it gives:

- AWS holds ciphertext only. SSE-SQS and SSE-S3 are a second layer.
- A reply can be read only by the bridge that asked.
- A reply that opens came from a collector.

What it does not give is authenticity of requests. The public key is public;
the allow-list, the deadline and the API's own authorisation are what decide.

**Rotation:**

1. Generate a new pair.
2. Give the collector the new key as `RELAY_COLLECTOR_PRIVATE_KEY_FILE` and
   the old one as `RELAY_COLLECTOR_PREVIOUS_KEY_FILE`, then restart it.
3. Give the bridges the new public key.
4. When every bridge has restarted, drop the old key.

## Deadlines, writes and duplicates

- **A deadline on every request.** The bridge sets `deadline_ms` = now + 25 s
  (`RELAY_DEADLINE_S`), or now + 50 s for any `multipart/form-data` request
  (`RELAY_UPLOAD_DEADLINE_S`): an attachment, a holder's message or answer, a
  nominee's request. It waits until the deadline plus 2 s, then answers 504
  `inside_timeout`.
- **The front door waits longer than the bridge.** The ALB's idle timeout
  and, with CloudFront, its origin response timeout must each be more than the
  longest deadline + 5 s. Both are 60 s by default, which fits 25 s and 50 s.
  If the front door gave up first, the browser would get its generic 504
  while the collector could still record the write, and the person's retry
  would make it twice. Raise `RELAY_UPLOAD_DEADLINE_S` only together with
  those timeouts.
- **Time is measured on AWS's clock.** The bridge stamps the deadline with
  its own clock, which Amazon Time Sync keeps on AWS's. The collector does not
  trust its own clock for it. It asks SQS for the timestamps AWS puts on each
  message (`SentTimestamp`, `ApproximateFirstReceiveTimestamp`,
  `ApproximateReceiveCount`), and keeps an estimate of how far its clock is
  from AWS's: the median of the last 20 or so samples of its own time at
  receive minus `ApproximateFirstReceiveTimestamp`, taken from messages
  received for the first time. The time left is `deadline_ms` minus (its own
  now minus that offset). Every `relay.handled` line carries `offset_ms` and
  an unclamped `queued_ms`. An offset over 1 s logs a warning,
  `relay.clock_skew`, at most once a minute. The offset includes the time the
  receive's answer took to arrive, so the collector can count that much more
  time left than there is: a fraction of a second, inside the 0.5 s margin
  below and the bridge's 2 s grace. Both hosts must still run NTP
  ([network requirements](#network-requirements-for-the-collector)).
- **Nothing runs late.** The collector drops a request whose deadline has
  passed (0.5 s or less left): it deletes the message, never runs the request
  and never replies. The browser has already been told it failed. A consent
  the person saw fail must not be recorded later.
- **A write needs time left.** A write (POST, PUT, PATCH, DELETE) starts only
  with at least 18 s left (`RELAY_WRITE_BUDGET_S`). Otherwise the answer is
  503 `deadline_too_close`, and nothing was saved. The time left is checked
  before the write's message is deleted and again just after, because the
  delete is a call to SQS and can be slow. With 0.5 s or less left the
  collector then stops without a reply (outcome `expired`); with less than
  the write budget it replies 503 `deadline_too_close` without calling the
  API. The API is called with a timeout of the time left at that moment,
  minus 0.5 s. The difference between `RELAY_DEADLINE_S` and the write budget
  (7 s by default, 32 s for an upload) is all the time a write has to be
  collected.
- **Writes are at most once; reads are not retried either.** A write's
  message is deleted *before* the API is called, so a crash cannot replay it.
  A read's message is deleted after its reply is sent, but a read whose
  collector dies is not run again: its message could only reappear after the
  180 s visibility timeout, which is past both the queue's 60 s retention and
  the request's deadline. Either way the browser gets 504, and the person
  retries.
- **Duplicates are dropped.** An in-process LRU of recent request ids catches
  a message that SQS delivers twice to the same collector.
- **Replies go only to known queues.** The collector replies only to a queue
  on `RELAY_REPLY_QUEUE_URLS`. A request naming any other queue is deleted
  and logged.
- **Stopping the collector drains it.** On SIGTERM each worker finishes the
  request it is handling and sends its reply; none runs past its deadline. A
  worker whose long poll (up to 20 s) returns after the stop does not handle
  what it received: it hands each message back to the queue at once
  (`ChangeMessageVisibility` 0), so the next collector takes it, and it polls
  no more. The unit allows 120 s for this (`TimeoutStopSec`), more than the
  longest request plus its reply. With one collector, collection pauses while
  it drains and restarts, and a request whose deadline passes meanwhile gets
  the bridge's 504.

## Reply queues: one bridge each

Each bridge long-polls its own reply queue (`RELAY_REPLY_QUEUE_URL`).
**Exactly one bridge may poll a reply queue. Never share one.** SQS cannot
hand a bridge only its own replies, so a bridge decides what to do with each
reply it receives:

- **One it is waiting for:** delivered.
- **One it gave up on or forgot:** deleted, and logged as `late_reply`. The
  bridge remembers the request ids it gave up on for about 5 minutes, up to
  about 10,000 of them. A reply received 5 times or more
  (`ApproximateReceiveCount`) is deleted the same way.
- **Anything else:** handed back to the queue at once
  (`ChangeMessageVisibility` 0), and logged as a warning, `foreign_reply`.

Ping replies are treated the same way: one taken by the wrong bridge goes
back to the queue for its owner, instead of being lost and making the owner
mark the inside down. A `foreign_reply` means another bridge polls this
queue, which is a misconfiguration to fix, not a load to tune for. Both
bridges keep working, but each receives some of the other's replies and hands
them back, so answers are slower; under load a reply can reach its fifth
receive and be deleted, and then the browser gets 504, after a write that
happened.

The stack makes two queues, for two portal instances. How an instance gets
its queue is fixed at install, in `/etc/compass/relay-bridge.env`. The
[portal deployment](../../docs/deployment/portal-frontend-aws.md#77-auto-scaling-group)
runs an Auto Scaling group of 2 to 6 instances, which does not fit that, so
while the relay is in use the group must be pinned: minimum, desired and
maximum all 2 (one per queue); no scaling policy; the `AZRebalance` process
suspended (it launches before it terminates); instance refresh with a maximum
healthy percentage of 100 (it terminates before it launches). Assign a queue
to a slot only one live instance can hold, never by Availability Zone: two
instances can be in one zone.

The production design for an Auto Scaling group is a queue per instance,
created at boot and named after the instance, with the collector accepting
that name pattern in this account and the queue removed when the instance
terminates. It is a follow-up, not built.

## Run it on this machine

The local stack is already running: API on 127.0.0.1:8000, DKMS, the portal
on 3001, and Postgres and Redis in Docker. This adds the relay beside it. The
normal portal on 3001 keeps talking to the API directly. A second portal on
3005 goes through the relay. Every command runs from `backend/relay`, and all
logs and generated files go in `var/` (gitignored).

1. **Install** (Python 3.12):

   ```sh
   python3.12 -m venv .venv
   .venv/bin/python -m pip install -r requirements-dev.txt
   mkdir -p var
   ```

2. **Start the AWS emulator** (moto: SQS and S3 on one port):

   ```sh
   nohup .venv/bin/moto_server -H 127.0.0.1 -p 5000 >> var/moto.log 2>&1 < /dev/null &
   ```

   macOS's AirPlay Receiver sometimes holds port 5000. If it does, use 5050
   here and in step 4. moto keeps everything in memory, so after a restart,
   run step 4 again.

3. **Make the keys.** This creates the collector's key pair and the ingress
   secret, each mode 0600 under `keys/` (gitignored):

   ```sh
   .venv/bin/python -m cmp_relay.keys generate --out keys
   .venv/bin/python -m cmp_relay.keys ingress-key --out keys/ingress.key
   ```

4. **Make the queues and the bucket.** This prints the settings, and writes
   them to `var/bridge-a.env`, `var/bridge-b.env` and `var/collector.env`. It
   is idempotent.

   ```sh
   .venv/bin/python -m cmp_relay.provision --endpoint-url http://127.0.0.1:5000 \
       --keys-dir keys --env-dir var
   ```

5. **Give the API the ingress secret, then restart the API.** The API does
   not reload. Stop it by PID, and start it again on its own.

   ```sh
   echo "RELAY_INGRESS_KEY=$(cat keys/ingress.key)" >> ../api/.env
   kill -TERM $(lsof -nP -iTCP:8000 -sTCP:LISTEN -t)
   # wait for port 8000 to be free, then:
   (cd ../api && nohup .venv/bin/python -m cmp --port 8000 >> var/api.log 2>&1 < /dev/null &)
   curl -s 127.0.0.1:8000/ready
   ```

   The worker and beat do not read this setting, so leave them running.

6. **Start the collector.** `RELAY_API_ORIGIN=http://127.0.0.1:8000` is
   already in its env file.

   ```sh
   (set -a; . var/collector.env; set +a
    nohup .venv/bin/python -m cmp_relay.collector >> var/collector.log 2>&1 < /dev/null &)
   ```

7. **Start the bridge** on 127.0.0.1:8080:

   ```sh
   (set -a; . var/bridge-a.env; set +a
    nohup .venv/bin/python -m cmp_relay.bridge >> var/bridge-a.log 2>&1 < /dev/null &)
   curl -s 127.0.0.1:8080/__relay/health        # the bridge's own view of the inside
   curl -s 127.0.0.1:8080/meta/enums | head -c 200; echo   # a real call, through SQS
   curl -s -o /dev/null -w '%{http_code}\n' 127.0.0.1:8080/auth/login   # 404: not public
   ```

8. **Run a second portal on 3005, pointed at the bridge.** Next.js 16 allows
   one `next dev` per directory, because it locks `.next/dev`, so run it from
   a copy. On APFS, `cp -c` clones the files instantly and takes no extra
   disk space.

   ```sh
   rm -rf var/portal-relay
   cp -Rc ../../frontend/portal var/portal-relay && rm -rf var/portal-relay/.next
   (cd var/portal-relay && API_ORIGIN=http://127.0.0.1:8080 DKMS_URL=http://127.0.0.1:9 \
     nohup node node_modules/next/dist/bin/next dev --port 3005 >> ../portal-relay.log 2>&1 < /dev/null &)
   ```

   Open <http://localhost:3005>. Every `/api` call now goes through
   bridge → SQS → collector → API, and the normal portal on 3001 is
   unchanged. `DKMS_URL` points at nothing on purpose: a portal on AWS cannot
   reach the key service, so a name showing as `SE::…` means a reply was not
   opened. The copy does not follow edits to `frontend/portal`. After
   changing the portal, copy it again.

9. **Watch and stop.** There is one JSON line per request in
   `var/bridge-a.log` (`relay.request`) and `var/collector.log`
   (`relay.handled`). Each line has the route template and never the path. To
   stop, `kill -TERM` the PIDs of the collector, the bridge, the 3005 portal
   and moto (`ps -eo pid,command | grep -E 'cmp_relay|moto_server|portal-relay'`).
   To turn the API's side off again, empty `RELAY_INGRESS_KEY` in
   `../api/.env` and restart the API.

10. **Run the browser checks through the relay**, against the portal on 3005,
    with steps 2 to 8 running:

    ```sh
    cd ../../frontend/portal
    E2E_BASE_URL=http://127.0.0.1:3005 E2E_VIA_RELAY=1 \
      npx playwright test --project=chromium \
      e2e/sealed-never-shown.spec.ts e2e/staff-as-principal.spec.ts
    ```

    `E2E_VIA_RELAY=1` is required, because it changes what the two specs
    expect. With it, `sealed-never-shown` requires that no relayed reply
    carries a sealed value at all; without it, it requires the API to have
    served sealed values, and fails on 3005. `staff-as-principal` expects 404
    instead of 403 from staff routes, because the relay refuses them before
    the API sees them. `E2E_BASE_URL` also stops Playwright building and
    serving a portal of its own. The specs read sign-in codes from the API's
    development outbox, so they need the seeded accounts.

**To try a second bridge** (the multi-instance case), start a second bridge on
8081 with `var/bridge-b.env`, which names the other reply queue. Then run a
third portal copy with `API_ORIGIN=http://127.0.0.1:8081`. Never start two
bridges with the same env file: they would share a reply queue
([one bridge each](#reply-queues-one-bridge-each)).

## Tests

```sh
.venv/bin/python -m pytest                   # everything
.venv/bin/python -m pytest tests/test_core.py
.venv/bin/python -m ruff check . && .venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy --strict src tests
```

Five files, no network beyond loopback and no AWS: moto stands in for SQS and
S3, in process.

- **`test_core.py`**: the shared core and the two command-line tools. For
  sealing: round trips, binding to the request id and kind, wrong keys,
  tampering, rotation and redaction. For the envelope: round trips and
  strict refusals. For the allow-list: every public route, staff routes,
  traversal and encoded separators, dev routes, header and cookie filtering,
  and the collector's sealed-value check for query, JSON, form and multipart
  bodies. For configuration: required settings, local-only settings, key
  files and ranges. For `keys`: modes, refusing to overwrite or follow
  symlinks. For `provision`: it runs against moto twice, to check it is
  idempotent.
- **`test_bridge.py`**: the bridge against moto, with a small fake collector
  in a thread. Round trips with status, headers and every `Set-Cookie`;
  routes refused before SQS; the body limit; large bodies through S3, sealed;
  504 at the deadline; late replies and replies that do not open; the ping
  and the 503 while the inside is down; the health endpoint; the client
  address from `X-Forwarded-For`; header and cookie filtering both ways; dev
  routes; the log line.
- **`test_collector.py`**: the collector against moto and a fake API, with
  the test playing the bridge. What reaches the API and what never does (404
  off the list, 422 for a sealed value); expiry and the write budget; when a
  write's and a read's message is deleted; duplicate ids; replies only to
  listed queues; messages that do not open, are malformed or name another
  id; pings; bodies through S3 both ways; the API failing, slow or
  redirecting; one log line per message with nothing secret in it; workers
  that survive errors and stop when told.
- **`test_collector_cookies.py`**: the collector's HTTP client keeps no
  cookie between requests. It is the regression test for the cookie jar that
  signed anonymous visitors in as whoever had signed in last.
- **`test_end_to_end.py`**: the real bridge and the real collector joined by
  moto, with a small API served by uvicorn on loopback and shortened clocks.
  Every message and object handed to AWS is recorded, to check that AWS only
  ever holds ciphertext. Also: a 20 MB upload arriving byte-identical through
  S3, each visitor's own cookies, concurrent requests, refusals before the
  API, a write too close to its deadline, the 503 when the collector or the
  API is down, and an API slower than the deadline being cut off.

The API's side (the sealed-value check, the session rule and the opening) is
tested in `backend/api`, in `tests/unit/api/test_relay_open_sealed.py`. The
portal's browser checks through the relay are step 10 of
[Run it on this machine](#run-it-on-this-machine).

## Configuration

Every setting is read once at start (`src/cmp_relay/config.py`). A missing or
malformed setting stops the process with a sentence naming it.
[`.env.example`](.env.example) lists them all with their local values.

| Setting | Side | Default | What it is |
|---|---|---|---|
| `RELAY_ENVIRONMENT` | both | `production` | `local`, `test`, `staging` or `production`. Only `local` and `test` allow the two settings below. |
| `RELAY_ENDPOINT_URL` | both | unset | A local emulator. Refused outside local and test. |
| `RELAY_ALLOW_DEV_ROUTES` | both | `false` | Lets `/dev/codes` and `/dev/seed-accounts` cross. Local only. |
| `RELAY_REGION` | both | `ap-south-1` | |
| `RELAY_REQUEST_QUEUE_URL` | both | required | Stack output `RequestQueueUrl`. |
| `RELAY_BUCKET` | both | required | Stack output `BodiesBucketName`. |
| `RELAY_COOKIE_NAMES` | both | `cmp_session,cmp_csrf,cmp_ticket` | Must match the API's cookie names. |
| `RELAY_CSRF_HEADER` | both | `X-CSRF-Token` | |
| `RELAY_BRIDGE_HOST` / `_PORT` | bridge | `127.0.0.1` / `8080` | The portal's `API_ORIGIN` points here. |
| `RELAY_REPLY_QUEUE_URL` | bridge | required | This instance's own reply queue. Never the same as another running instance's. |
| `RELAY_COLLECTOR_PUBLIC_KEY` | bridge | required | Base64, from `keys generate` or `keys public`. |
| `RELAY_DEADLINE_S` | bridge | `25` | 2–120. Plus 5 s, it must stay under the front door's timeouts. |
| `RELAY_UPLOAD_DEADLINE_S` | bridge | `50` | For any `multipart/form-data` request. At least the deadline. Plus 5 s, it must stay under the front door's timeouts (60 s by default); raise it only with them. |
| `RELAY_MAX_BODY_BYTES` | bridge | 26 MiB | A larger body gets 413. |
| `RELAY_REPLY_POLLERS` | bridge | `2` | Threads long-polling the reply queue. |
| `RELAY_PING_INTERVAL_S` | bridge | `10` | How often the inside is checked. |
| `RELAY_CLIENT_IP_HOP` | bridge | `1` | Which `X-Forwarded-For` entry, counted from the right, is the visitor: one per proxy in front of the portal. `1` behind an ALB alone (recommended), `2` behind CloudFront -> ALB ([why](#in-front-of-the-portal)). |
| `RELAY_COLLECTOR_PRIVATE_KEY_FILE` | collector | required | Mode 0600. |
| `RELAY_COLLECTOR_PREVIOUS_KEY_FILE` | collector | unset | The key being rotated out. |
| `RELAY_API_ORIGIN` | collector | `http://127.0.0.1:8000` | |
| `RELAY_INGRESS_KEY_FILE` | collector | required | At least 32 characters. The API's `RELAY_INGRESS_KEY` is its contents. |
| `RELAY_REPLY_QUEUE_URLS` | collector | required | Every reply queue, comma-separated (stack output `ReplyQueueUrls`). |
| `RELAY_WORKERS` | collector | `8` | Requests handled at once. |
| `RELAY_WRITE_BUDGET_S` | collector | `18` | A write starts only with this many seconds left. Must stay well under `RELAY_DEADLINE_S`. |

AWS credentials come from the standard chain:

- **The bridge:** the EC2 instance role.
- **The collector:** IAM Roles Anywhere through `credential_process`.
- **Against the emulator:** any dummy pair.

## Deploying

The AWS side is one CloudFormation stack,
[`deploy/cloudformation.yaml`](deploy/cloudformation.yaml) (cfn-lint clean).
It creates:

- the request queue and two reply queues;
- the bodies bucket and its TLS-only policy;
- the bridge's role, instance profile and a managed policy;
- the collector's role, trust anchor and Roles Anywhere profile;
- four alarms: two on the request queue (a request waiting over 30 s, over
  100 waiting), which mean the collector is not collecting or not keeping up;
  one on each reply queue (a reply waiting over 30 s), which means that
  instance's bridge is not collecting its replies.

The alarms do not see a collector that collects and then drops every request
without a reply, for example when a reply queue is missing from
`RELAY_REPLY_QUEUE_URLS`, or a bridge still seals to a retired collector key.
Both queues stay empty while the bridge answers 503. The portal's own Target
5xx and CloudFront 5xx alarms
([portal deployment, section 10](../../docs/deployment/portal-frontend-aws.md#10-monitoring-logs-and-alarms))
are the backstop there, and the collector's `relay.handled` lines name the
outcome.

```sh
aws cloudformation deploy --region ap-south-1 \
  --stack-name cmp-relay-production \
  --template-file deploy/cloudformation.yaml \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    EnvironmentName=production \
    OrgEgressCidrs=203.0.113.10/32,203.0.113.11/32 \
    CollectorCertificateCN=cmp-relay-collector.example.org \
    CollectorIssuerCN="Example Org Relay Issuing CA" \
    OrgCaCertificatePem="$(cat issuing-ca.pem)" \
    AlarmTopicArn=arn:aws:sns:ap-south-1:111122223333:compass-oncall
aws cloudformation describe-stacks --region ap-south-1 --stack-name cmp-relay-production \
  --query 'Stacks[0].Outputs' --output table
```

`CollectorIssuerCN` is optional. Given, the collector's role also requires
the certificate's issuer CN to match. Use it when the trust anchor is a root,
or a CA that issues more than this one certificate. Best of all, have a sub-CA
that issues for the relay and nothing else, and make it both the trust anchor
and the issuer CN.

### In front of the portal

- **Recommended: an ALB with AWS WAF attached, and no CloudFront.** TLS from
  the browser then ends at the ALB in ap-south-1, in India. With CloudFront it
  ends at whichever edge location is nearest the visitor, which can be
  abroad. Leave `RELAY_CLIENT_IP_HOP` at `1`: the ALB appends the visitor's
  address to `X-Forwarded-For`, and the portal's `/api` rewrite adds nothing.
- **With CloudFront -> ALB -> portal, set `RELAY_CLIENT_IP_HOP=2`.**
  CloudFront appends the visitor, then the ALB appends CloudFront's own
  address. With `1`, every visitor would be recorded as one of a few
  CloudFront addresses: in the audit trail, and in the per-address sign-in
  budget, which one person's wrong codes would then spend for everyone behind
  the same address.
- **Either way the count assumes the ALB's defaults:**
  `routing.http.xff_header_processing.mode` `append`, and
  `routing.http.xff_client_port.enabled` off (with ports in the entries, no
  entry parses as an address, and every visitor is recorded under the
  portal's own address). Confirm the hop in staging with a header echo
  ([portal deployment, section 12](../../docs/deployment/portal-frontend-aws.md#12-must-be-resolved-before-go-live)).
- **Timeouts.** The ALB's idle timeout and, with CloudFront, its origin
  response timeout must each be more than the longest relay deadline + 5 s.
  The defaults (60 s, and 25 s and 50 s deadlines) fit. To allow longer
  uploads, raise `RELAY_UPLOAD_DEADLINE_S` together with both timeouts (check
  CloudFront's quota for the origin response timeout first), never on its
  own.

### On each portal instance (the bridge)

- Install the relay into `/opt/compass/relay/.venv`
  (`pip install -r requirements.txt` and `pip install --no-deps .`).
- Write `/etc/compass/relay-bridge.env` with that instance's own
  `RELAY_REPLY_QUEUE_URL`, never another running instance's
  ([one bridge each](#reply-queues-one-bridge-each)), and
  `RELAY_CLIENT_IP_HOP=2` if CloudFront is in front.
- Install [`deploy/systemd/cmp-relay-bridge.service`](deploy/systemd/cmp-relay-bridge.service).
- Keep the clock on Amazon Time Sync (chrony's default on Amazon Linux 2023).
  The bridge's clock stamps every deadline.
- Give the instance the bridge's permissions. An instance has one role, so
  either attach the stack's `BridgeAccessPolicyArn` to the portal's existing
  role ([portal deployment, 7.5](../../docs/deployment/portal-frontend-aws.md#75-instance-role-and-launch-template)),
  or use `BridgeInstanceProfileName` and add the portal's own permissions to
  it.
- **Build the portal with `API_ORIGIN=http://127.0.0.1:8080`.** It is a
  build-time value, so a restart does not change it
  ([portal deployment, section 6](../../docs/deployment/portal-frontend-aws.md#6-configuration-what-is-fixed-at-build-what-is-read-at-start)).
- The portal no longer needs network access to the API or to DKMS. It needs
  SQS and S3: through the NAT, or better through an SQS interface endpoint
  and the S3 gateway endpoint in its VPC.
- Pin the Auto Scaling group to one instance per reply queue
  ([one bridge each](#reply-queues-one-bridge-each)).

### Inside (the collector)

- Install the relay the same way, plus `aws_signing_helper` (IAM Roles
  Anywhere credential helper) at `/usr/local/bin/`.
- Have the organisation's CA issue a client certificate whose CN equals
  `CollectorCertificateCN` (and whose issuer CN equals `CollectorIssuerCN`,
  if set).
- Copy [`deploy/aws-config.collector.example`](deploy/aws-config.collector.example)
  to `/etc/compass/relay/aws-config` and fill in the three ARNs from the stack
  outputs. With the key in a TPM, the unit also needs `/dev/tpmrm0` and the
  `tss` group (`SupplementaryGroups=tss`): see the comment on `PrivateDevices`
  in the unit.
- Put `collector.key` and `ingress.key` from `python -m cmp_relay.keys` in
  `/etc/compass/relay/`, owned by `compass-relay`, mode 0600.
- Write `/etc/compass/relay-collector.env`.
- Install [`deploy/systemd/cmp-relay-collector.service`](deploy/systemd/cmp-relay-collector.service),
  with the real proxy in `HTTPS_PROXY`. Its `TimeoutStopSec=120` is the drain
  ([Stopping the collector](#deadlines-writes-and-duplicates)); keep it above
  `RELAY_UPLOAD_DEADLINE_S` + 60 s.
- Keep the host's clock by NTP against the organisation's internal time
  server.
- On the API, set `RELAY_INGRESS_KEY` to the contents of `ingress.key`.
- Import the issuing CA's CRL against the trust anchor, and automate keeping
  it current ([next section](#revoking-or-replacing-the-collector-certificate)).

## Revoking or replacing the collector certificate

IAM Roles Anywhere never fetches a CRL from a distribution point and never
asks OCSP. A certificate the CA has revoked keeps getting `CollectorRole`
credentials until it expires, unless that CA's CRL has been imported against
the trust anchor. So without the steps below, the old certificate and key (on
a reimaged host, in a backup) stay usable from the organisation's egress
addresses. Whoever holds them cannot open a request, but can take requests
off the queue, and every request taken is lost to the real collector.

**Import the CRL once, and keep it current.**

```sh
aws rolesanywhere import-crl --region ap-south-1 \
  --name cmp-relay-production-collector-ca \
  --crl-data fileb://issuing-ca.crl \
  --trust-anchor-arn <TrustAnchorArn> --enabled
# each time the CA publishes a new CRL:
aws rolesanywhere list-crls --region ap-south-1            # find its crlId
aws rolesanywhere update-crl --region ap-south-1 --crl-id <crlId> \
  --crl-data fileb://issuing-ca.crl
```

Automate the update on the CA's publication schedule, so it always runs before
the imported CRL's `nextUpdate`. Run it from a job with
`rolesanywhere:UpdateCrl`, not with `CollectorRole`. A trust anchor takes at
most two CRLs. The CRL is not a resource in the stack: it can be larger than
a parameter allows (4 KB), and it changes on the CA's schedule, not the
stack's.

**On renewal, decommissioning or a suspected key compromise:**

1. Issue the new certificate (same CN; same issuer if `CollectorIssuerCN` is
   set). Replace `collector.crt` and `collector.key` and restart the collector.
2. Revoke the old certificate at the CA, and update the imported CRL at once.
3. The CRL stops new sessions only. Credentials already issued to the old
   certificate last up to an hour. To end them now, use "Revoke active
   sessions" on `CollectorRole` in IAM, then restart the collector so it
   fetches fresh credentials.

Roles Anywhere also warns of a certificate's expiry (45 days ahead by
default) through EventBridge and AWS Health. Route those to the on-call topic.

## Network requirements for the collector

- **Inbound:** none. No port opens on the collector or anywhere inside.
- **Outbound, only through the organisation's proxy, port 443:**
  - `sqs.ap-south-1.amazonaws.com`: the queues;
  - `<bucket>.s3.ap-south-1.amazonaws.com`: large bodies. The stack outputs
    this exact name as `BodiesBucketHost`. Requests are virtual-hosted, so
    `s3.ap-south-1.amazonaws.com` alone is not enough, and a wildcard for
    `*.s3...` is not needed;
  - `rolesanywhere.ap-south-1.amazonaws.com`: hourly credentials.
- **Outbound, direct:** the API (`RELAY_API_ORIGIN`), listed in `NO_PROXY`.
- **NTP, inside:** the organisation's internal time server. No new egress.
- **TLS 1.2 or later, and no TLS inspection of these three names** (set them
  no-decrypt on the proxy). `--no-verify-ssl` is never acceptable.
  - For SQS and S3, inspection breaks the calls: boto3 trusts its own
    certificate bundle, not the operating system's, so it refuses the
    proxy's certificate.
  - For `rolesanywhere`, inspection does **not** break the call, and that is
    the danger. `aws_signing_helper` trusts the operating system's store,
    where an inspecting proxy's root certificate normally sits. The request's
    signature covers the request, not the connection, so it still succeeds,
    and the proxy sees the response: the role's one-hour credentials. Check
    the proxy's policy for this name; the helper will not report it.
- **Synchronised clocks on both hosts.** The bridge stamps each deadline with
  its own clock. The collector measures it on AWS's clock
  ([above](#deadlines-writes-and-duplicates)), which absorbs a steady offset
  in its own clock, but not one that jumps, and it takes the bridge's clock
  to be AWS's. So:
  - the bridge keeps chrony on Amazon Time Sync;
  - the collector runs NTP against the internal time server, and a
    `relay.clock_skew` warning (offset over 1 s) means it is not working.

  Where that does not hold (the bridge's clock off AWS's, or the collector's
  jumping), a deadline that looks nearer than it is refuses writes as too
  close and expires pings, so the bridge reports the inside down; one that
  looks further away lets a write finish after the browser was told it
  failed. AWS's own signatures tolerate minutes of skew, so they give no
  warning.
- **A fixed egress address.** The collector role refuses every call from
  outside `OrgEgressCidrs`. Behind Zscaler, that means a dedicated egress IP.
- **Not yet confirmed (test in staging):**
  - whether S3 refuses a request whose `Host` differs from its SNI;
  - whether the `aws:SourceIp` condition on the collector role sees the
    organisation's egress address through the proxy. If it does not, every
    call is denied, which fails closed;
  - that the proxy does not inspect `rolesanywhere`, read from its policy
    (the helper succeeds either way).

## Known limits of the proof of concept

- **One reply queue per bridge instance, fixed in configuration.** The stack
  makes two queues, for two portal instances, and the Auto Scaling group must
  be pinned to two. Two bridges on one queue hand each other's replies back
  and forth (`foreign_reply`), which slows answers and can lose some. A queue
  per instance, created at boot, is the production design and is not built
  ([one bridge each](#reply-queues-one-bridge-each)).
- **A request can be lost.** A write's message is deleted before the API is
  called, and a read is not retried. If the collector crashes, or is killed
  because its drain ran past `TimeoutStopSec`, a write in flight may or may
  not have happened, and the browser gets 504. The person retries. Lost is
  preferred over twice.
- **Duplicates are possible across collectors.** A standard queue is
  at-least-once. In the rare case of SQS delivering one message to two
  collectors at once, both may run it, because the duplicate check is per
  process. A FIFO queue or API idempotency keys would close this.
- **A reply can be lost after the API acted.** A bridge restarted while a
  request is in flight (an upload can wait up to 52 s, the bridge unit allows
  30 s to stop) cannot deliver the reply, but the collector may still record
  the request.
- **The deadlines depend on settings on both sides.** The front door's
  timeouts must stay above the bridge's deadlines, and `RELAY_DEADLINE_S` well
  above the collector's `RELAY_WRITE_BUDGET_S`. Neither process can see the
  other's settings, so neither can refuse a wrong combination.
- **Certificate revocation is manual until automated.** Roles Anywhere checks
  only the CRL imported against the trust anchor, and that import has to be
  kept current by a job the organisation runs.
- **No streaming.** Both sides hold each body in memory whole, up to
  `RELAY_MAX_BODY_BYTES`. Server-sent events and websockets cannot cross.
- **The API opens sealed values for relayed replies** (ADR 0032). This
  amends ADR 0016, under which the API never decrypted its responses.
  Whoever holds `RELAY_INGRESS_KEY` and can reach the API is served opened
  values.
- **Each request adds latency:** about one SQS round trip each way, plus the
  proxy. A request does not wait for the 20-second long poll: a waiting
  receive returns as soon as a message arrives.
