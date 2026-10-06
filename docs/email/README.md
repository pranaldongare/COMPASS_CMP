# Email

How the platform sends email: the one path every message takes, the five
settings that point it at a mail server, the template every email is laid out
in, what happens when the server says no, and how to check a deployment
before anybody waits on a sign-in code.

| Document | What it holds |
|---|---|
| This page | How email works, the settings, the template, failures and retries, operating it |
| [messages.md](messages.md) | **Every message the platform sends** - when, to whom, its subject, its variables, and the code that sends it (generated from the code) |
| [domain/messages.md](../domain/messages.md) | The messages as the office sees them, and how their words are edited |

## The settings: five, and nothing else

In `backend/api/.env`:

| Setting | Example | What it does |
|---|---|---|
| `SMTP_SERVER` | `smtp.corp.example` | The mail server. **Empty: nothing is sent** - each email is written to `var/outbox.log` and laid out in `var/outbox-html/` (local and test only; production refuses to start without a server) |
| `SMTP_PORT` | `25` | The port, which also decides how the connection is protected (below) |
| `SMTP_USERNAME` | `svc-cmp` | The login. Empty: no login, for a relay that accepts this machine without one |
| `SMTP_PASSWORD` | `…` | The password. Never logged, printed or returned |
| `SENDER_EMAIL` | `privacy@corp.example` | The address every email comes from, shown as "`ORGANISATION_NAME` Privacy Office". **Must be real in production** - the API refuses `example.org` and `example.com` |

```bash
SMTP_SERVER=smtp.corp.example
SMTP_PORT=25
SMTP_USERNAME=svc-cmp
SMTP_PASSWORD=...
SENDER_EMAIL=privacy@corp.example
```

Restart the API and the worker after changing them: the worker is what sends.

**The port decides the connection:**

| `SMTP_PORT` | Connection | What happens |
|---|---|---|
| `465` | SSL | Encrypted from the first byte |
| `587` | STARTTLS | Connects, upgrades to encryption, then logs in. A server that cannot upgrade is refused, never used unencrypted |
| `25` (or any other) | Plain | No encryption, as an internal relay expects - and so is any login over it, so this is for a relay on a trusted network |

On 465 and 587 the server's certificate is verified against the machine's
system authorities. A relay whose certificate an internal authority signed
needs that authority added to the system's certificates.

**From a standalone script.** A script that sends mail with its own names
maps onto these: `SMTP_SERVER` and `SMTP_PORT` as they are, `ORG_ID` is
`SMTP_USERNAME`, `ORG_PASSWORD` is `SMTP_PASSWORD`, `SENDER_EMAIL` as it is,
and `TEST_RECIPIENT` is the `--to` of `scripts/send_test_email.py`. The
settings refuse a name they do not know, so `ORG_ID` and `ORG_PASSWORD` have
to be renamed. (Names from before 2026-10-06 - `SMTP_HOST`,
`NOTIFICATION_EMAIL_FROM`, `EMAIL_TRANSPORT`, `SMTP_USE_TLS` - still load,
so an older `.env` keeps working; use the five above.)

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
| 5 | The email goes | `infrastructure/email/transport.py` | Laid out in the template (`layout.py`) and sent to `SMTP_SERVER`, or written to the outbox when it is empty; raises on failure |

So adding a message is a message in `core/messages.py` and a task that calls
`deliver()` - never a new SMTP call, never a new template. The full list is
[messages.md](messages.md).

## The template

Every email has the same look, built by `infrastructure/email/layout.py`
from the message's plain text - so the Privacy Office edits words in
**Message templates**, never markup, and every message, theirs or the
default, comes out laid out the same way:

| Part | What it shows |
|---|---|
| Header | The organisation's name on the console's indigo-to-blue band, with "Privacy Office" |
| Title | The subject, as the email's heading |
| Content | The message, laid out (below) |
| Footer | "`ORGANISATION_NAME` Privacy Office", that the message was sent automatically by the consent management platform under the DPDP Act, 2023, and the year |

How the message's text is laid out:

| In the text | In the email |
|---|---|
| Paragraphs, separated by a blank line | Paragraphs, 15px with generous spacing |
| A six-digit code alone on its line | The code, large and spaced, in a highlighted box |
| A link alone on its line | A button, with the address written beneath it. A short line ending ":" just above it ("Set your password here:") becomes the button's label |
| A link inside a sentence | A link |
| A short first line with more beneath it ("What happened") | A heading over its paragraph |
| Lines starting "- " | A bulleted list |
| "If you were not expecting this message…" | Small print under a rule, last |

Each email goes out **twice over in one message**: the laid-out HTML, and
the plain text with the same footer in words, for a mail client that shows no
HTML and for spam filters, which trust a message that has both. The layout is
tables and inline styles - what Outlook, Gmail and phone mail apps render
alike - 600px wide and narrowing on a phone, with no images, scripts or
remote files, so nothing is blocked and nothing loads from elsewhere when it
is opened. Everything in the text is escaped before it becomes markup: a
person's name or a breach notice's words are text, never HTML.

**Seeing it.** With `SMTP_SERVER` empty, every email is also saved as an HTML
file in `backend/api/var/outbox-html/` - open one in a browser to see exactly
what would be sent.

## What goes out

| Header | Value |
|---|---|
| From | `ORGANISATION_NAME Privacy Office <SENDER_EMAIL>` |
| To | The one recipient - opened from its sealed form only at this moment |
| Subject | The message's subject, with its values filled in |
| Date | When it was sent, in UTC |
| Message-ID | Unique, on the sender's domain; returned and logged so a delivery can be traced |
| Auto-Submitted | `auto-generated` (RFC 3834), so an out-of-office reply is not sent back to an address nobody reads |
| Body | `multipart/alternative`: the plain text, then the laid-out HTML |

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
| STARTTLS or AUTH not offered on that port | `EmailRejected` | No | `email.rejected` reason "not supported by the server" |
| The server's certificate does not verify | `EmailRejected` | No | `email.rejected` reason "certificate not trusted" |
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

`scripts/send_test_email.py` sends one sample - with a code box and a button,
in the template - through the same transport and settings as every platform
message:

```bash
cd backend/api
.venv/bin/python scripts/send_test_email.py --to you@corp.example
```

It prints what it will use - the server, port and connection, the login name
and the sender, never the password - then sends, and exits 0 if the server
accepted it, 1 if not, with the reason:

| It says | Means | Do |
|---|---|---|
| `Accepted : <id@corp.example>` | The server took it | Check the inbox (and spam) |
| `Refused : … login …` | Wrong `SMTP_USERNAME` or `SMTP_PASSWORD`, or the account may not send | Fix the login; ask mail admins whether SMTP AUTH is enabled for it |
| `Refused : … does not support …` | The port does not match what the server offers | Use 587 for STARTTLS, 465 for SSL, or 25 for a plain relay |
| `Refused : … certificate …` | The server's certificate is signed by an internal authority | Add that authority to the machine's system certificates |
| `Refused : … refused the message (code 550)` | The sender is not allowed, often `SENDER_EMAIL` on a domain the server does not send for | Use an address the server may send as |
| `Not sent : the server is unreachable or busy` | Wrong server or port, a firewall, or the server is down | Check `SMTP_SERVER`, `SMTP_PORT`, and that this machine can reach it |
| `Written to var/outbox.log` + `Open it : …html` | `SMTP_SERVER` is empty | Set it; open the HTML file to see the layout meanwhile |

## The code

| File (backend/api/…) | What it holds |
|---|---|
| `src/cmp/infrastructure/email/transport.py` | The transports, `compose()`, `EmailRejected`, `build_email_transport()` |
| `src/cmp/infrastructure/email/layout.py` | The template: header, footer, and the text laid out |
| `src/cmp/infrastructure/messaging/__init__.py` | `deliver()`: opening sealed values, rendering, choosing the channel |
| `src/cmp/core/messages.py` | Every message's default words, variables and channels |
| `src/cmp/tasks/` | The Celery tasks that send them, with their retry policy |
| `src/cmp/core/config.py` | The five settings, and the production checks |
| `scripts/send_test_email.py` | The test send |
| `tests/unit/infrastructure/test_smtp_transport.py`, `test_email_layout.py` | How it connects, what it sends, which failures are retried, and the layout |
| `docs/tools/generate-email-docs.py` | Writes [messages.md](messages.md) from the code; `--check` says when it is stale |
