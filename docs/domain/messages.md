# Messages the platform sends

Every email and SMS the platform sends is a **junction**: a named moment at
which it writes to a person, with the channels it uses, the variables its
words may carry, and a default subject and body. The administrator and the
DPO can replace the words for any junction from the console, per channel;
the defaults are what is sent until they do. The catalogue lives in
`backend/api/src/cmp/core/messages.py`.

## The junctions

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
| Rights | `holder_instruction` | email, SMS | a ticket is issued to a holder |
| Rights | `ticket_reminder` | email, SMS | a ticket's date is near, today or past |
| Rights | `ticket_message` | email, SMS | a message is written on a ticket thread |
| Staff | `office_note` | email | the office resends a notification from the console |

The channel is chosen by the shape of the contact, once it has been opened
(below): an address gets the email words, a number gets the SMS words. SMS bodies are separate and short, at
most 480 characters, because a phone screen is not an inbox.

## Editing the words

The console's **Messages** page (administrator and DPO) lists every junction
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

The transports themselves (`EMAIL_TRANSPORT`, `SMS_TRANSPORT`) are described
in [configuration.md](../operations/configuration.md).
