# Messages the platform sends

Every email and SMS the platform sends is a **junction**: a named moment at
which it writes to a person, with the channels it uses, the variables its
words may carry, and a default subject and body. The administrator and the
DPO can replace the words for any junction from the console, per channel;
the defaults are what is sent until they do. The catalogue lives in
`cmp_backend/src/cmp/core/messages.py`.

## The junctions

| Group | Junction | Channels | Sent when |
|---|---|---|---|
| Sign-in | `mfa_code` | email | a member of staff has entered a correct password |
| Sign-in | `login_code` | email, SMS | a data principal asks to sign in |
| Sign-in | `registration_code` | email, SMS | a data principal signs up on the portal, one per contact given |
| Sign-in | `consent_code` | email, SMS | a contact is given through a consent link |
| Sign-in | `password_reset` | email | a member of staff asks to reset their password |
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

The channel is chosen by the shape of the contact: an address gets the email
words, a number gets the SMS words. SMS bodies are separate and short, at
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
sign-in code has to go out whatever else is wrong.

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

The transports themselves (`EMAIL_TRANSPORT`, `SMS_TRANSPORT`) are described
in [configuration.md](../../cmp_backend/docs/operations/configuration.md).
