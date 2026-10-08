# Messages the platform sends

Every email and SMS the platform sends is a **junction**: a named moment at
which it writes to a person, with the channels it uses, the variables its
words may carry, and a default subject and body. The administrator and the
DPO can replace the words for any junction from the console, per channel;
the defaults are what is sent until they do. The catalogue lives in
`backend/api/src/cmp/core/messages.py`.

## The junctions

There are 41, in the order of the catalogue. Who each is sent to, the task
that sends it and the code that queues it are listed per module in
[docs/notifications/](../notifications/README.md).

| Group | Junction | Channels | Sent when |
|---|---|---|---|
| Sign-in | `mfa_code` | email | a member of staff has entered a correct password |
| Sign-in | `login_code` | email, SMS | a data principal asks to sign in |
| Sign-in | `registration_code` | email, SMS | a data principal signs up on the portal, one per contact given |
| Sign-in | `consent_code` | email, SMS | a contact is given through a consent link |
| Sign-in | `password_reset` | email | a member of staff asks to reset their password |
| Sign-in | `staff_invitation` | email | an administrator provisions a staff account |
| Sign-in | `contact_confirmation` | email, SMS | a person adds a mobile or a second email to their own account |
| Sign-in | `contact_added_for_you` | email, SMS | an administrator puts a mobile on somebody's account; the code lasts hours, not minutes |
| Consent | `consent_receipt` | email, SMS | consent is recorded through a link |
| Consent | `withdrawal_confirmation` | email, SMS | some or all purposes are withdrawn |
| Rights | `rights_acknowledgement` | email, SMS | a rights request is received |
| Rights | `rights_verification_code` | email, SMS | a public-form request needs its contact confirmed |
| Rights | `rights_response_ready` | email, SMS | a response can be read from her account |
| Rights | `rights_response` | email, SMS | the response itself is sent |
| Rights | `rights_closed` | email, SMS | a request is refused, reclassified, unverified, or a grievance decided |
| Rights | `nomination_code` | email, SMS | a nominee proves a recorded contact before accepting or declining |
| Rights | `nomination_invitation` | email, SMS | somebody is nominated |
| Rights | `nomination_accepted` | email, SMS | a nominee accepts |
| Rights | `holder_instruction` | email, SMS | a ticket is sent to a holder inside the organisation: a member of staff, or a colleague given a temporary login. A holder outside it is sent `holder_ticket_link` instead |
| Rights | `ticket_reminder` | email, SMS | a ticket's date is near, today or past |
| Rights | `ticket_message` | email, SMS | a message is written on a ticket thread |
| Rights | `holder_ticket_link` | email | anything happens on an outside holder's ticket - sent, written on, moved or reopened (0049): says what happened, the date to answer by and the link to the ticket on the portal, and nothing of the request |
| Rights | `holder_ticket_code` | email | somebody opens an outside holder's ticket link: the code, to the address on the ticket, that opens it |
| Staff | `office_note` | email | the office resends a notification from the console |
| Breach | `breach_notice` | email, SMS | the DPO sends an approved notice about a personal data breach to the people it touched - only once it is recorded as a breach; the email carries all five Rule 7(1) contents, the SMS points to her account, where the same notice is. `breach_reference` is the breach reference (`BR-`), never the incident's |
| Breach | `breach_notice_direct` | email, SMS | the same notice to a person the breach touched who has no account, named in a list sent to the Privacy Office (0045): all five Rule 7(1) contents by email, and by SMS |
| Breach | `breach_ticket_waiting` | email | a breach ticket is assigned to a member of staff, sent back, or reopened (S3-08): says only that a ticket from the Privacy Office is waiting in the console, and names no breach - no reference, no title, no words (BD-18) |
| Breach | `breach_ticket_access` | email | somebody without a console login is asked to act on a breach - by the DPO, or as a colleague by a holder - or asked again after an administrator ended their login (S3-09): says the Privacy Office has given them temporary console access to answer a ticket - when the matter is closed they can still read it, no longer answer it (2026-10-06) - with the reset link, the code and how long it lasts. A login that already signs in is sent `breach_ticket_waiting` instead. Sent by the sign-in service, like `staff_invitation`, never from breach code, and names no breach (BD-18) |
| Projects | `project_submitted` | email | an R&D User submits a project for approval; to every active DPO |
| Projects | `project_approved` | email | the Privacy Office approves a project, which publishes its notice; to the R&D User who owns it |
| Projects | `project_sent_back` | email | the Privacy Office sends a project back to draft, with its reason; to the R&D User who owns it |
| Projects | `project_closed` | email | a project is closed and its consent links stop working; to the R&D User who owns it |
| Projects | `project_collector_assigned` | email | a project's site or data source is assigned to a Data Collection Owner; to them |
| Rights | `rights_request_received` | email | a rights request arrives, from the portal, the public form or a nominee; to every active DPO, with its reference, kind and due date and never her words |
| Rights | `rights_due_digest` | email | daily, when open requests are overdue or at risk of missing their date; to every active DPO, and only when there is something on it |
| Rights | `rights_grievance_about_dpo` | email | a grievance concerns the DPO's own decisions; to every active administrator, so somebody independent reviews it |
| Breach | `breach_duty_due` | email | a breach duty with a deadline - the organisation's board, CERT-In, the Board's report - is about to fall due, and again if overdue; to every active DPO, once per stage per duty |
| Breach | `breach_ticket_returned` | email | the holder of a breach ticket returns it with their answer; to every active DPO |
| Accounts | `staff_role_changed` | email | an administrator changes a member of staff's role; to them |
| Accounts | `staff_access_ended` | email | an administrator ends a member of staff's console access; to them. A consent or request they made as a person is unaffected |
| Accounts | `delegation_arranged` | email | cover is arranged; to the person away and to the colleague acting for them |

The channel is chosen by the shape of the contact, once it has been opened
(below): an address gets the email words, a number gets the SMS words. SMS bodies are separate and short, at
most 480 characters, because a phone screen is not an inbox.

## Copies and files

From Message templates the office may copy an email to up to five addresses,
per message (`PUT /messages/{key}/copies`, kept in `message_copy`, 0046). Only
the messages in `COPYABLE` may be copied: the work between the office and its
staff or holders. Never one that carries a code or a link, because a copy
would hand the key to somebody else, and never one written to a data
principal about herself, because a copy would disclose her data. The service
refuses the rest.

Two messages may carry files by email (`ATTACHABLE`), and only files the
recipient already owns: `consent_receipt` carries her own consent record, and
`ticket_message` carries the file the office put on the message, to the
ticket's holder only.

## Editing the words

The console's **Message templates** page (administrator and DPO) lists every junction
with its variables, its default words, and the words in force. For each
channel the editor offers the subject (email only) and body, chips that
insert the variables the message provides, a preview rendered with sample
values, Save, and Reset to default. Every save and reset is recorded in the
audit trail with who and when, and the page shows both.

Rules a save must meet, each named in the refusal:

- placeholders are `{name}` and nothing else, and only names the message
  provides, plus `{organisation}`, `{portal_url}` and `{console_url}`, which
  every message may use;
- an email has a one-line subject; an SMS has none;
- an email body fits in 6,000 characters, an SMS in 480;
- the body is not empty.

A stored template that names a variable the code later stops providing does
not fail the message: the placeholder is sent as written and the message
still goes out. The next edit of that template will be refused until the
placeholder is removed.

## How a message is sent

```
service  --dispatch-->  Celery task  --deliver(Message.X, to, **vars)-->  render  -->  transport
                                                                            ^
                                             the office's words, from a Redis mirror of
                                             message_template (refreshed from the table,
                                             cleared by the API on every save or reset)
```

`deliver` in `cmp.infrastructure.messaging` is the only path to a transport,
and it takes a `Message` member, never free text. The worker reads the
office's replacements from a Redis mirror of the `message_template` table;
if the mirror is empty it reads the table and fills it for five minutes, and
if neither is reachable it sends the defaults and logs the failure, because a
sign-in code has to go out whatever else is wrong. The key service is the
exception to that rule: without it there is no address to send to.

## Addressing a sealed recipient

Every contact is sealed in the database, and so is every name a message
greets, so what a task hands to `deliver` is usually ciphertext, `SE::…`.
`deliver` opens the recipient and every sealed variable in one call to the
key service, at the one point every message passes through, and only then
chooses the channel and renders the words. This runs in the **worker**, a
separate process with its own environment, so the worker needs
`DKMS_ENABLED=true` and a `DKMS_URL` naming the service the data was sealed
with - the API having them is not enough.

When the recipient cannot be opened, nothing is sent, and it says so:

- `deliver` logs `message.not_sent` with the junction and the error - the
  service's URL, never the address or the code - and raises
  `DkmsUnavailable`.
- Every message task retries on it: five times, from five seconds and
  doubling, with jitter - about two and a half minutes in all. A key service
  that blinks delays a code; one that stays away longer loses it, and the
  person asks for another.
- The error names the cause: the service unreachable or answering an error;
  values sealed but `DKMS_ENABLED` false in this process; a value that
  begins `SE::` but carries no envelope this code can read; or a recipient
  still sealed after opening, which is refused before the channel is chosen
  so that ciphertext is never mistaken for a mobile number.
- `GET /ready` on the API carries an `encryption` check naming the URL it
  tried.

The request that asked for the message has already answered - "a code has
been sent" means one was queued - so this is the one failure invisible from
outside. The runbook has the steps:
[No message of any kind is sent, and the request said one was](../operations/runbook.md#no-message-of-any-kind-is-sent-and-the-request-said-one-was).
How the key service is set up is in [docs/dkms/](../dkms/README.md).

## Adding a junction

Three edits, and the console shows the new message on the day the code lands:

1. Add a member to `Message` and a `Junction` to `CATALOGUE` in
   `cmp/core/messages.py`: title, description, group, channels, variables
   with descriptions and samples, and the default words per channel.
2. Send it from a task with `deliver(Message.NEW_ONE, to=contact, **variables)`.
3. Run the unit suite.

Three tests hold the shape: every `Message` member has a junction whose
defaults use only declared variables and fit the channel limits; every
`deliver(...)` call in the codebase names a `Message` member statically; and
every member is delivered by some task, so a junction cannot be declared and
forgotten. Nothing outside `cmp.infrastructure.messaging` may build a
transport, which is what stops a message being sent around the catalogue.

## Settings

| Setting | Used as |
|---|---|
| `ORGANISATION_NAME` | `{organisation}` |
| `PUBLIC_BASE_URL` | `{portal_url}`, and the links in consent and rights messages |
| `CONSOLE_BASE_URL` | `{console_url}`, and the links in staff messages |
| `OTP_TTL_S`, `MFA_TTL_S` | `{minutes}` on the code messages |
| `DKMS_ENABLED`, `DKMS_URL` | Opening the recipient, in the worker's environment as well as the API's |

The transports themselves (the five email settings, `SMS_TRANSPORT`) are described
in [configuration.md](../operations/configuration.md); email - its settings,
failures and a test send - in [email/README.md](../email/README.md), with every
message, its task and the code that queues it in
[email/messages.md](../email/messages.md).
