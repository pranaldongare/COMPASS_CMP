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
| [breach.md](breach.md) | The breach notice, breach tickets, the DPO's duty alerts, reports to the organisation's board, and the public link |
| [oversight.md](oversight.md) | The audit trail failing its check, DataVault not taking an instruction, a sensitive setting changed |

The six module files are **generated from the code** by
`docs/tools/generate-email-docs.py`. Each one lists every email of its module,
then gives each one end to end: when it is sent, to whom, its CC, its
attachment, the default subject and body, the SMS where there is one, the
variables, the Celery task that sends it and where it is queued from. They
cannot drift: `--check` fails when one is out of date.

## The rules

### 1. One path

Every message - all 86 - goes the same way:

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
| The organisation's board | The addresses chosen for that report when it was finalised: the board's list, less any the sender left out, with any added for that report alone (0064) |

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
| A report to the organisation's board, and the officers' mail when its list changes | A report goes to the addresses chosen for it and may name a person; the list-changed mail names an address on the list and is the officers' check on it (0064) |

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

### 4. Attachments: only what the recipient owns, or what was written for it

Emails carry no files by default. Four may (`ATTACHABLE`), and each carries only
something its recipient owns or that was written for it:

| Email | Attachment |
|---|---|
| Consent receipt | Her own consent record, `consent-record.txt`: what she agreed to and refused, when, how, against which notice version and language, and the fingerprint of the exact text she was shown |
| Ticket message (to a rights ticket's holder) | The file the Privacy Office put on that message, for that holder |
| A report to the organisation's board | The report as a PDF, to the addresses chosen for it when it was finalised |
| A report for the regulator is ready | The report as a PDF, to the addresses chosen for it, for its information; a report to CERT-In finalised before a *yes* waits for the first *yes* |

Those two reports are the one place somebody else's personal data travels as an
attachment. A report finalised for a regulator goes to the board with its
findings, in the mail and as a PDF, and the 72-hour report's findings on who
caused the breach may name a person
([ADR 0037](../decisions/0037-a-public-report-waits-apart-and-the-platform-mails-the-organisations-board.md)
counts the cost). Neither may be copied. A **rights
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
| [Consent](consent.md) | 4 | The data principal; an HR activity's participants and respondents |
| [Rights requests](rights.md) | 17 | The requester, the nominee, the holder's responder (inside the organisation in full; outside, the link and the code), every DPO, every administrator |
| [Breaches](breach.md) | 13 | The people affected, the ticket holder, the breach office's officers, the officers of both offices when the board's list changes, the organisation's board, and the reporter |

## Who keeps the words (2026-11-20)

Every message's subject and body can be changed in **Message templates**. Who
may change them is set per message in the catalogue (`Junction.editors`), and
the API refuses anybody else (403):

| Role | Reads | Changes |
|---|---|---|
| Administrator | every message | every message |
| Data Protection Officer | every message | every message |
| Legal PoC | every message | the messages with legal weight (`LEGAL_REVIEWED`): consent receipts and withdrawals, the HR track's messages, what a requester is told of her request and its outcome, nominations, breach notices to people, reports to the organisation's board, and the incident reporter's acknowledgements |

The console shows a message the reader does not keep read-only, naming who
does. Every change to a message's words or copies is told to every
administrator and officer (**A platform setting was changed**).

Every message carrying a one-time code says, in the same words, not to share
it, and that the organisation never asks for it. Every code text (SMS) follows
the DLT shape: "Your OTP to … is {code}. It is valid for … Do not share it … -
{organisation}".

## The review of 2026-11-20

Every audited event was checked for whether anybody is told of it. 32 messages
were added (54 → 86 emails, 21 → 27 texts):

| Who | New |
|---|---|
| Every member of staff | password changed, reset or first set; second sign-in step reset; sign-in paused after failed attempts; signed out everywhere; account reactivated |
| Anybody with an account | a contact added, replaced or removed - to the contacts already there, never naming the new one (email and text) |
| A data principal | her nominee made a request for her (incapacity only, as before); her nomination was declined; her request is in progress (email and text) |
| A nominee | the nomination was withdrawn (email and text) |
| An R&D User | a collector they asked for was decided; a processor or source their project uses was suspended; a site deactivated; a participant withdrew |
| A Data Collection Owner | the same suspensions, deactivations and withdrawals; the new collector of every project when a source's owner changes in the registry |
| An officer (DPO, Legal PoC) | a collector waiting for approval; retained items past their retention floor; consent validity run out; a breach recorded or confirmed; CERT-In marked or a report deadline extended; a breach ticket holder wrote; a board or regulator report not delivered; breach notices not delivered (once per six hours per breach) |
| An administrator | named reviewer of a grievance; rights requests overdue (daily); DataVault refused an instruction (once a day per instruction) |
| Everybody who answers for the platform | the audit trail failed its check; a sensitive setting changed (DataVault connection, portal address, breach settings, a message's words or copies) |
| A breach ticket holder | a new message from the Privacy Office (naming no breach, BD-18); temporary access ended |
| HR PoCs and respondents | a template version approved or retired; added or removed as a category's respondent |

The **Note from the Privacy Office** now goes by text as well, to a person with
a mobile only, and names the event as a person reads it.

Left out on purpose:

| What | Why |
|---|---|
| A legal hold, to the person | Telling her could tip off the investigation or litigation the hold is for; her erasure response says what was kept |
| A field agent assigned to a site | The agent is a free-text reference with no contact on the platform |
| An HR activity's first invitation to employees | There is no list of participants before they consent; the HR PoC shares the link. Sending it needs a decision on where the list comes from |
| CERT-In set aside | It mails nobody, by decision (2026-11-07) |
| An incident report dismissed, to the reporter | ADR 0042: the reporter is only acknowledged |

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
