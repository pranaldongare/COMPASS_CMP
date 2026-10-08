# Notification management strategy: email

How the platform tells people things by email, module by module: what is sent,
when, to whom, who is copied, what is attached, and why each of those is what
it is. [Email](../email/README.md) explains the mail server, the settings and
the template; this folder explains the messages.

| Document | What it holds |
|---|---|
| This page | The strategy: the rules every email follows, and the index |
| [implementation-plan.md](implementation-plan.md) | The plan of 2026-10-08 and what was built |
| [users.md](users.md) | Sign-in, sign-up, contacts, staff invitations, role changes, access ended, cover arranged, office notes |
| [projects.md](projects.md) | A project submitted, approved, sent back, closed; a collector assigned |
| [consent.md](consent.md) | Consent given and withdrawn |
| [rights.md](rights.md) | Rights requests: the requester's emails, the nominee's, the holders' tickets, and the office's alerts |
| [breach.md](breach.md) | The breach notice, breach tickets, and the DPO's duty alerts |

The five module files are **generated from the code** by
`docs/tools/generate-email-docs.py`. Each one lists every email of its module,
then gives each one end to end: when it is sent, to whom, its CC, its
attachment, the default subject and body, the SMS where there is one, the
variables, the Celery task that sends it and where it is queued from. They
cannot drift: `--check` fails when one is out of date.

## The rules

### 1. One path

Every email - all 41 - goes the same way:

| # | Step | Where (backend/api/src/cmp/…) |
|---|---|---|
| 1 | Something happens and its transaction writes it | the module's service in `domain/` |
| 2 | The module asks who is told, and queues one task per recipient | `domain/alerts` for staff alerts; the module itself for the rest |
| 3 | The task is queued **after the commit** (`dispatch_optional`) - an email never goes out for something that was rolled back, and one that cannot be queued never undoes the act | `tasks/dispatch.py` |
| 4 | The worker runs it and calls `deliver(Message.X, to=…, attachments=…, **values)` | `tasks/notifications/*.py` |
| 5 | `deliver()` opens the sealed recipient, the values and any copy addresses, renders the office's words (or the default), adds the copies and files the rules allow, and sends | `infrastructure/messaging` |
| 6 | The transport lays it out in the template and sends it to `SMTP_SERVER` | `infrastructure/email` |

No code sends an email any other way. A new email is a junction in
`core/messages.py` and a task that calls `deliver()` - nothing else.

### 2. To: exactly one person per email

Each email is addressed to **one** person. When several people are told the
same thing - every DPO about a new request - each gets their own email, from
their own task, so one bad address never stops the others and nobody sees who
else was told.

| Who | How the address is found |
|---|---|
| A data principal | Her primary contact on her account (or the contact on the request or the list) |
| A member of staff | Their primary email on their account |
| Every DPO / every administrator | Every **active** account holding the role |
| A project's owner | The R&D User who created it |
| A project's collector | The project's Data Collection Owner, as its site and source make it |
| A rights ticket's holder | The responder named on the ticket: a staff account's email, a temporary login's, or - outside the organisation - the address on the ticket, sent the link only |
| A breach's people | Each person listed: an account's email, or a contact from an uploaded list |

Addresses are sealed at rest and stay sealed in the task queue; only
`deliver()` opens them, at the moment of sending.

### 3. CC: the Privacy Office's choice, within a fixed rule

The decision and its reasons: [ADR 0029](../decisions/0029-copies-and-files-never-on-a-code-a-link-or-her-own-record.md).

**The deployment may add its own.** `EMAIL_CC_ADDRESSES` in
`backend/api/.env` - up to five addresses, comma-separated - is copied on
every copyable email, after the office's, under the same rule. Message
templates says how many there are ([email/README.md](../email/README.md)).

**Test mode sends nothing to anybody real.** On a UAT or test server,
`EMAIL_REDIRECT_TO` sends every email and every text only to the addresses
it names, saying at the top whom each was for. Production refuses to start
with it set.

**No email is copied by default.** The Privacy Office may copy an email to up
to **five** addresses - a team mailbox that follows the work up, an approvals
inbox - in **Message templates → Copy to**, per email. The copies get the same
email, in `Cc`.

Only emails about the work between the office, its staff and its holders may
be copied (`COPYABLE` in `core/messages.py`). Two kinds never are, whatever is
set:

| Never copied | Why |
|---|---|
| An email carrying a **code or a link** - sign-in, sign-up, password reset, invitation, nomination, temporary access, an outside holder's ticket link or its code | A copy would hand somebody else the key to the account, or to the ticket |
| An email to a **person about her own data** - a consent receipt, a withdrawal, a rights response, a breach notice | A copy would disclose her data to somebody she did not choose |

Copy addresses are sealed (`message_copy`, migration 0046), listed once per
email, and every change is on the audit trail with the count - never an
address. An SMS is never copied.

**A holder outside the organisation is sent the link, not the request**
(0049, 2026-10-08). Every email about a rights ticket to an address outside
`BREACH_TICKET_EMAIL_DOMAINS` is **Ticket link to an outside holder**: what
happened, the date, and the link to the ticket on the portal. What is asked,
about whom, what was written and any file are behind a one-time code sent to
the same address (**Code to open a ticket**). A holder inside the organisation
is sent the ticket in full, with a link to it in the console.

### 4. Attachments: only what the recipient already owns

Emails carry no files by default. Two may (`ATTACHABLE`), and each carries only
something its recipient owns:

| Email | Attachment |
|---|---|
| Consent receipt | Her own consent record, `consent-record.txt`: what she agreed to and refused, when, how, against which notice version and language, and the fingerprint of the exact text she was shown |
| Ticket message (to a rights ticket's holder) | The file the Privacy Office put on that message, for that holder |

Personal data of anyone else never travels as an attachment. A **rights
response** in particular stays **download-only** from her account: the
download is audited and its window closes, neither of which an attachment
could do. At most 10 MB of files per email; an SMS carries none.

### 5. Subject and body: the office's words, the platform's layout

Every email has a default subject and body in `core/messages.py`, shown in
full in the module files. The Privacy Office may replace the words of any of
them in **Message templates**, using only the variables that email provides;
the platform lays every one out the same way - header, title, content, footer
(see [Email](../email/README.md#the-template)).

What an email never contains: a person's words from a request, a breach's
details in a staff ticket email (BD-18), a code in the log. Staff alerts name
the thing - a project, a request reference, a breach reference - and link to
the console, where the detail is.

### 6. When it fails

A message task retries an outage with backoff (5 tries, up to 5 minutes
apart); a refusal no retry will mend - a wrong login, a refused address - fails
at once (see [Email](../email/README.md#when-the-server-says-no)). An alert
that is lost is lost quietly: what it is about is still on the record, and
still in the console's bell. A breach notice is the exception: every outcome
is recorded, because the principals' duty counts them.

### 7. Timed alerts

| Alert | How often | Said |
|---|---|---|
| Rights requests due soon or overdue | Daily, 02:30 UTC, with the rights sweep | Once a day, only when there is something to list (overdue, or due within 7 days) |
| A breach duty about to fall due, or overdue | Every 5 minutes (`alert-breach-duties`) | Once per duty when it enters the last sixth of its window (at least 5 minutes before), once more when it is overdue |

## The emails, by module

| Module | Emails | Who they go to |
|---|---|---|
| [Users and accounts](users.md) | 12 | The person signing in or up; staff being invited, reset, changed, ended, covered; whoever the office resends a note to |
| [Projects](projects.md) | 5 | Every DPO (submitted), the owner (approved, sent back, closed), the collector (assigned) |
| [Consent](consent.md) | 2 | The data principal |
| [Rights requests](rights.md) | 16 | The requester, the nominee, the holder's responder (inside the organisation in full; outside, the link and the code), every DPO, every administrator |
| [Breaches](breach.md) | 6 | Each person a breach touched, the ticket holder, every DPO |

## Adding an email

1. Add a `Message` member and a `Junction` in `core/messages.py`: title, when,
   group (which decides its module file), channels, variables, the default
   words, and `to=` in words. Add it to `COPYABLE` only if it is work between
   the office and its staff or holders; to `ATTACHABLE` only if what it
   carries belongs to its recipient.
2. Add a task that calls `deliver(Message.X, …)` and list it in
   `tasks/notifications/__init__.py`.
3. Queue it from the module's service with `dispatch_optional`, one per
   recipient, sealed values only.
4. Run `docs/tools/generate-email-docs.py`. The tests fail if a message is sent
   by nothing, or a task is not registered.
