# Monitoring

## Logs

Structured, JSON in production, via structlog. Every line carries `request_id`.

The correlation id is minted by the first middleware and bound to a contextvar,
so a log line from the bottom of the stack carries it without anybody threading
it through four hundred signatures. A client-supplied `X-Request-ID` is honoured
so a caller can correlate across systems — sanitised and bounded first, because it
reaches a log line.

## What to alert on

| Signal | Means |
|---|---|
| `auth.login_locked_out` rate rising | Credential stuffing |
| `auth.access_denied` rate rising | Probing, or a permission change broke a workflow |
| `cmp.maintenance.verify_audit_chain` reporting a break | Investigate immediately — the trail has been tampered with or corrupted |
| `notification.batch_partial` | A transport is failing for some recipients |
| `upload.path_escape` | Traversal attempt, or a corrupted reference |
| Queue depth on `high_priority` | Somebody is waiting for a sign-in code |
| `after_commit.hook_failed` or `task.dispatch_failed` | A notification was due after a commit and the broker did not take it; the row exists, the message did not go |
| `sms.gateway_refused` | The SMS gateway answered non-2xx; codes to mobiles are not arriving |
| Redis `used_memory` near `maxmemory` | Redis runs `noeviction`; at the limit it refuses writes and sign-in fails with 503 rather than silently evicting sessions |
| `cmp.maintenance.sweep_rights_requests` failing | Unverified requests are not being closed and ticket due dates are not being marked; a clock is running unwatched |
| Rights requests past a checkpoint on the dashboard | The office is late; the response period is published and binding |
| `/ready` answering 503 with `encryption` not ok | The API cannot reach the key service: writes of personal data answer 503, and no message can be addressed |
| `message.not_sent` | The worker could not open a message's sealed recipient. The task retries five times, then the message is dropped; see the [runbook](runbook.md#no-message-of-any-kind-is-sent-and-the-request-said-one-was) |
| `dkms.unreachable` or `dkms.error` (API or worker) | The key service did not answer, or answered non-2xx. The line names the URL, never a value |
| `dkms.refused` | The key service refused a batch (422): a wrong data type for a value, or ciphertext it cannot open. Not transient |
| `[dkms] … unreachable` or `answered <status>` in a portal's server log | That portal cannot open what it is served; people see `SE::…` |
| The key service's `GET /health` failing | Everything above, at once |
| `python scripts/reseal.py --check` exiting 1 | Plaintext in a sealed column. Run it after any change to sealing and on a schedule; it only reads |

The audit chain alert is the one that matters most and fires least. Treat it as a
page, not a ticket.

## The key service

`GET /health` on port 32688 answers `{"status": "ok", "provider": …,
"workers": …, "max_records": …}`. It checks nothing beyond the process
being up; the API's `/ready` is what proves the API can reach it.

It logs `dkms.ready` at startup with the provider and pool size, and never
logs a value, plaintext or sealed.

## Metrics

Prometheus at `/metrics`, if the instrumentator is installed. Untemplated
handlers are excluded, which is what keeps a consent token out of a metric label
— an unbounded label set is both a memory leak and a credential in a scrape
endpoint.

## The task monitor

Celery publishes an event for every task sent, received, started and finished.
**Flower** renders them: which tasks ran, on which queue, how long they took,
which failed and what they raised, and which workers are alive with what they
are working on now.

Locally, against the worker already running:

```bash
cd backend/api
celery -A cmp.tasks.app:celery_app flower \
  --address=127.0.0.1 --port=5555 --basic-auth=you:a-real-password
```

Always with `--basic-auth`, and always on the loopback. Flower can revoke and
terminate running tasks and has no notion of roles: everybody who reaches it can
do everything it can do. Putting it on a routable address means putting your own
proxy and your own authentication in front of it first.

### Task arguments do not appear in it

`cmp.tasks.dispatch` replaces the repr Celery puts in those events with the
number of arguments and nothing else, so Flower shows `(3 argument(s)
withheld)`. The arguments are one-time codes, mobile numbers and email
addresses — `send_login_code(uuid, contact, code)` is a live credential and a
personal contact — and the event stream has none of the controls the rest of
the platform has.

The worker still receives the real arguments; it has to, in order to run the
task. What is withheld is what is *said about* the message to everything
listening. `tests/unit/tasks/test_dispatch_redaction.py` holds both halves,
because a redaction that reached the message body would be a sign-in code
nobody could send.

To trace one task, take its `request_id` from Flower's headers and search the
API log for it: the structured log has the rest, behind the controls that log
already has.

## What is deliberately not logged

Passwords, one-time codes, session tokens, consent link tokens, the contents
of a data asset, and the arguments of a Celery task — which carry the first two
of those (see the task monitor, above). The access log scrubs `/c/{token}` to `/c/[token]`, because a
link in a log file is a credential in a file that gets shipped to an aggregator
and read by people who were never meant to hold it.

## Reading the audit trail

`GET /audit` with filters, or the console's Audit trail screen. Each entry
resolves its `entity_type`/`entity_id` into a label and a link, so "Notice
published" says *which* notice.

For "what happened to this person's data", filter by `subject`. That is the DSAR
query, and it is backed by `idx_audit_subject`. For one rights request,
`GET /requests/{uuid}/trail` reads the same rows by reference.
