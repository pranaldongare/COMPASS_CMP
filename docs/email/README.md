# Email

How the platform sends email: the one path every message takes, the settings
that point it at a mail server, what happens when the server says no, and how
to check a deployment before anybody waits on a sign-in code.

| Document | What it holds |
|---|---|
| This page | How email works, the settings, failures and retries, operating it |
| [messages.md](messages.md) | **Every message the platform sends** - when, to whom, its subject, its variables, and the code that sends it (generated from the code) |
| [domain/messages.md](../domain/messages.md) | The junctions as the office sees them, and how their words are edited |

## The one path

Nothing in the platform talks to a mail server except one class. Every
message - a sign-in code, a consent receipt, a breach notice - takes the same
five steps:

| # | Step | Where (backend/api/src/cmp/…) | What happens |
|---|---|---|---|
| 1 | Something happens | a service in `domain/` or `auth/` | A request commits: an account invited, a request received, a breach ticket assigned |
| 2 | A task is queued | `tasks/dispatch.py` (`dispatch_required`, `dispatch_optional`) | After the transaction commits, never inside it (ADR 0012). A sign-in code is *required*: if the broker is down the request fails. A notification is *optional*: the row is written and the failure logged |
| 3 | The worker runs the task | `tasks/authentication/otp.py`, `tasks/notifications/*.py` | Each task names one message and its values, and calls `deliver()` |
| 4 | The words are made | `infrastructure/messaging/__init__.py` (`deliver`) | Opens a sealed recipient or value through the key service; picks the channel from the contact (an `@` is email); renders the office's words from **Message templates**, or the default in `core/messages.py` |
| 5 | The email goes | `infrastructure/email/transport.py` (`build_email_transport().send`) | The configured transport delivers it, or raises |

So adding a message is a junction in `core/messages.py` and a task that calls
`deliver()` - never a new SMTP call. The full list is [messages.md](messages.md).

## Transports

`EMAIL_TRANSPORT` chooses one. The default delivers nothing, on purpose: a
misconfigured staging box that writes to a file is a far better failure than
one that emails real people the first time somebody signs in.

| `EMAIL_TRANSPORT` | Class | Delivers | Use |
|---|---|---|---|
| `console` (default) | `ConsoleEmailTransport` | Appends to `backend/api/var/outbox.log`; with `DEV_SHOW_CODES` the code pops up in the browser tab that asked | Local development and test. Refuses to run in staging or production |
| `smtp` | `SmtpEmailTransport` | A real mail server | Staging and production. **Required in production** - the API refuses to start otherwise |
| `null` | `NullEmailTransport` | Nothing; keeps what it was given | Tests that check behaviour, not delivery |

## Settings

In `backend/api/.env`. Only `EMAIL_TRANSPORT=smtp` and the server's details
are needed; everything else has a sensible default.

| Setting | Default | What it does |
|---|---|---|
| `EMAIL_TRANSPORT` | `console` | `console`, `smtp` or `null` (above) |
| `SMTP_HOST` (or `SMTP_SERVER`) | `localhost` | The mail server's name or address |
| `SMTP_PORT` | `587` | 587 for STARTTLS, 465 for SSL, 25 for a plain internal relay |
| `SMTP_SECURITY` | follows `SMTP_USE_TLS` | `starttls`, `ssl` or `none` (below) |
| `SMTP_USE_TLS` | `true` | Kept for existing settings: true means `starttls`, false means `none`, when `SMTP_SECURITY` is unset |
| `SMTP_USERNAME` | empty | The login. Empty: no login, for a relay that accepts the platform by address |
| `SMTP_PASSWORD` | empty | The password. Never logged, printed or returned; kept as a secret in the settings |
| `SMTP_CA_FILE` | empty | A CA bundle to trust as well as the system's, for a relay whose certificate an internal authority signed. Verification is never switched off |
| `SMTP_TIMEOUT_S` | `EXTERNAL_HTTP_TIMEOUT_S` (10) | Seconds before a stalled server is given up on - never infinite |
| `NOTIFICATION_EMAIL_FROM` (or `SENDER_EMAIL`) | `privacy@example.org` | The address every email comes from. **Must be real in production** - the API refuses `example.org` and `example.com` |
| `NOTIFICATION_EMAIL_FROM_NAME` | empty | The name beside it. Empty: "`ORGANISATION_NAME` Privacy Office" |
| `ORGANISATION_NAME` | `COMPASS` | The organisation's name in every message (`{organisation}`) and the default sender name |

**From a standalone script.** A script that sends mail with its own variable
names maps onto these:

| Script variable | Platform setting |
|---|---|
| `SMTP_SERVER` | `SMTP_HOST` - or keep `SMTP_SERVER`, which is read as it |
| `SMTP_PORT` | `SMTP_PORT` |
| `ORG_ID` | `SMTP_USERNAME` |
| `ORG_PASSWORD` | `SMTP_PASSWORD` |
| `SENDER_EMAIL` | `NOTIFICATION_EMAIL_FROM` - or keep `SENDER_EMAIL`, which is read as it |
| `TEST_RECIPIENT` | the `--to` of `scripts/send_test_email.py` |

`ORG_ID` and `ORG_PASSWORD` are not read under those names - they are too
general to claim, and the settings refuse an unknown variable - so rename them.

### The three ways to connect

| `SMTP_SECURITY` | Usual port | What happens | When |
|---|---|---|---|
| `starttls` | 587 | Connects in the clear, upgrades with STARTTLS, then logs in. A server that cannot upgrade is refused, never used unencrypted | Most mail services, Office 365, Gmail |
| `ssl` | 465 | Encrypted from the first byte | A server that offers SMTPS |
| `none` | 25 | Plain. A login over it is sent in the clear | An internal relay on a trusted network only |

Certificates are always verified, against the system's authorities and
`SMTP_CA_FILE` if set.

### Examples

```bash
# An internal relay on port 25 that wants a login
EMAIL_TRANSPORT=smtp
SMTP_HOST=smtp.corp.example
SMTP_PORT=25
SMTP_SECURITY=none
SMTP_USERNAME=svc-cmp
SMTP_PASSWORD=...
NOTIFICATION_EMAIL_FROM=privacy@corp.example

# Office 365
EMAIL_TRANSPORT=smtp
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_SECURITY=starttls
SMTP_USERNAME=privacy@corp.example
SMTP_PASSWORD=...
NOTIFICATION_EMAIL_FROM=privacy@corp.example
```

Restart the API and the worker after changing them: the worker is what sends.

## What goes out

Each email is plain text in UTF-8, one recipient, one connection:

| Header | Value |
|---|---|
| From | `NOTIFICATION_EMAIL_FROM_NAME <NOTIFICATION_EMAIL_FROM>` |
| To | The one recipient - opened from its sealed form only at this moment |
| Subject | The message's subject, with its values filled in |
| Date | When it was sent, in UTC |
| Message-ID | Unique, on the sender's domain; returned and logged so a delivery can be traced |
| Auto-Submitted | `auto-generated` (RFC 3834), so an out-of-office reply is not sent back to an address nobody reads |

## When the server says no

The transport tells a failure a retry can mend from one it cannot. Every
message task retries `OSError` with backoff (5 tries, from 5 seconds, at most
5 minutes apart); `EmailRejected` is not one, so it fails at once instead of
trying the same refused thing five more times.

| What went wrong | What it raises | Retried | Logged as |
|---|---|---|---|
| Server unreachable, connection dropped, timed out | the `OSError` itself | Yes | `email.unavailable` |
| A temporary refusal (4xx: busy, mailbox full, greylisted) | `SMTPResponseException` / `SMTPRecipientsRefused` | Yes | `email.deferred` |
| Wrong login (535) | `EmailRejected` | No | `email.rejected` reason "login refused" |
| Sender or recipient refused for good (5xx) | `EmailRejected` | No | `email.rejected` reason "refused" / "recipient refused" |
| STARTTLS or AUTH not offered | `EmailRejected` | No | `email.rejected` reason "not supported by the server" |
| The server's certificate does not verify | `EmailRejected` | No | `email.rejected` reason "certificate not trusted" - set `SMTP_CA_FILE` |
| Accepted | - | - | `email.delivered`, with the Message-ID |

A message that still fails after its retries is dropped and logged; the person
asks again (a new code, a resent invitation). A refused breach notice is also
recorded on the breach's notices card as a failed delivery.

## What is never written down

| Never | Instead |
|---|---|
| The password | Kept as a secret; unwrapped only to log in |
| The message's body (a code, a response) | Only the subject is logged |
| The full recipient | Obscured: `as***@corp.example` |
| A recipient in the database in the clear | Contacts are sealed at rest and opened only inside `deliver()` |

## Checking a deployment

`scripts/send_test_email.py` sends one test email through the same transport,
with the same settings, as every platform message:

```bash
cd backend/api
.venv/bin/python scripts/send_test_email.py --to you@corp.example
```

It prints what it will use - transport, server, port, how it connects, the
login name and the sender, never the password - then sends, and exits 0 if
the server accepted it, 1 if not, with the reason:

| It says | Means | Do |
|---|---|---|
| `Accepted : <id@corp.example>` | The server took it | Check the inbox (and spam) |
| `Refused : … login …` | Wrong `SMTP_USERNAME` or `SMTP_PASSWORD`, or the account may not send | Fix the login; ask mail admins whether SMTP AUTH is enabled for it |
| `Refused : … does not support …` | `SMTP_SECURITY` does not match the server | Try `starttls` on 587, `ssl` on 465, or `none` on 25 for a relay |
| `Refused : … certificate …` | The server's certificate is signed by an internal authority | Set `SMTP_CA_FILE` to that authority's certificate |
| `Refused : … refused the message (code 550)` | The sender is not allowed, often `NOTIFICATION_EMAIL_FROM` on a domain the server does not send for | Use an address the server may send as |
| `Not sent : the server is unreachable or busy` | Wrong host or port, a firewall, or the server is down | Check `SMTP_HOST`, `SMTP_PORT`, and that this machine can reach it |
| `Written to var/outbox.log` | `EMAIL_TRANSPORT` is still `console` | Set it to `smtp` |

## The code

| File (backend/api/…) | What it holds |
|---|---|
| `src/cmp/infrastructure/email/transport.py` | The transports, `EmailRejected`, `build_email_transport()` |
| `src/cmp/infrastructure/messaging/__init__.py` | `deliver()`: opening sealed values, rendering, choosing the channel |
| `src/cmp/core/messages.py` | Every message's default words, variables and channels |
| `src/cmp/tasks/` | The Celery tasks that send them, with their retry policy |
| `src/cmp/core/config.py` | The settings above, and the production checks |
| `scripts/send_test_email.py` | The test send |
| `tests/unit/infrastructure/test_smtp_transport.py` | How it connects, what it sends, and which failures are retried |
| `docs/tools/generate-email-docs.py` | Writes [messages.md](messages.md) from the code; `--check` says when it is stale |
