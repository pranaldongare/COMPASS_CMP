# Authentication

Two populations, two mechanisms, and the difference is deliberate. A third,
narrower one serves an outside holder answering a rights ticket
([below](#outside-holders-of-a-rights-ticket)).

## Staff

Password sign-in, Argon2id, and then a second factor for **every** staff role: a
code to the account's email. It began with the two roles whose compromise is
unbounded, the DPO and the administrator; since 2026-09-06 it covers every
internal role, because the others can still mint consent links, read consent
records and move data. The list is `MFA_REQUIRED_ROLES`, derived from the role
enum by default; a deployment may narrow it, and answers for that.

A **temporary ticket holder** (`breach_holder`, S3-09; since 0049 also a
colleague given a rights ticket with no console login) signs in the same way -
a password set through the reset flow's code, then the emailed second factor -
and needs the second factor whatever `MFA_REQUIRED_ROLES` says: `requires_mfa`
answers yes for it before reading the list, because a temporary login made
by the platform rather than an administrator is not one a deployment should be
able to leave on a password alone. It is not staff: `RequireStaff` excludes it.
It keeps its password when its part is over - the breach closes, the request
closes, or its ticket is withdrawn or sent to somebody else - to read its ticket;
an administrator's **End temporary access** clears it, and the account cannot
sign in again until a new grant sends a new code
([ADR 0023](../decisions/0023-breach-tickets-and-breach-only-logins.md)).

A **partial session** exists between password verification and MFA. It authorises
exactly two routes, `POST /auth/mfa/verify` and `POST /auth/mfa/resend`; every
other endpoint answers 401 with
`mfa_required` until it is promoted. It is a distinct dependency type
(`PartialUser`) rather than a flag on the full one, because a flag is one missed
`if` away from an MFA bypass.

## Outside holders of a rights ticket

A vendor or third-party processor asked to answer a rights ticket has no
account and is given none (0049, `domain/rights/holder_link.py`). Its ticket
comes as a link to the portal, `/ticket/{token}`. The link alone shows the
reference, the holder's name and where a code will go, masked. The code goes
to the address on the ticket - never one typed on the page - so holding the
link is not enough: the holder must also read that mailbox. The code (scope
`holder_ticket`) opens an hour on that one ticket in the HttpOnly,
`SameSite=Strict` cookie `cmp_ticket`; Redis keeps its fingerprint at `hts:*`,
naming the holder and the link. Every call names the link in its path as
well, and the two must agree, so a link sent to somebody else since shuts the
old hour. It mints no session: no role, no matrix, nothing beyond the
`/holder-tickets/{token}/*` routes. Every way a link can fail answers the
same 404.

## Data subjects

**No password at all.** `password_hash` is nullable for exactly this reason. A
data subject registers with a mobile and, if she likes, an email (since
2026-09-06: mobile first, because the codes that *are* her sign-in should go to
the thing she carries). Every contact given is authenticated with its own code
before the account is hers - at self-registration and through a consent link
alike - and a later sign-in sends a code to whichever of the two she chooses.
Mobiles are normalised to digits with a leading plus, so "+91 90000 00001" and
"+919000000001" are one number; that normalised form is what is sealed and
what is hashed (below).

**A sign-in code is bound to the contact it went to** (2026-11-08). It is issued
under the account and the contact's keyed hash (`login_code_identity`, so Redis
holds no address), and it verifies only when that same contact is typed again:
another contact of the same account answers 400 `otp_invalid`, as a wrong code
does. Keyed on the account alone, a code sent to the mobile also verified with the
account's email typed beside it, and stamped that email proved although no code
had gone there. The portal sends the contact it asked the code for; a code issued
before the change, within its ten minutes, is refused once. A sign-in stamps the
contact typed - the mobile, the email or the second email, never another
([what a code proves](#what-a-code-proves)).

The reasoning: a data subject who could set a password would have an account
worth phishing, and would reuse a password they use elsewhere. One who receives a
code per sign-in has nothing worth stealing between sessions.

## Employees on a consent link

A consent link minted `audience_mode = sso` signs a person in through the
organisation's identity provider instead of a code
([ADR 0034](../decisions/0034-an-employee-link-signs-in-through-the-organisations-sso.md)):

1. `GET /c/{token}/sso/start` writes the sign-in's state, nonce and PKCE
   verifier to Redis (`sso:state:*`, ten minutes) and answers the provider's
   authorisation URL; the portal sends the browser there.
2. The provider returns to `GET /auth/sso/callback?code=&state=` (through the
   portal's `/api/` path). The state is taken once; unknown or used, 404.
3. The code is exchanged with the verifier, and the ID token validated:
   signature against the provider's published keys (refetched on an unknown
   key id), issuer, audience, expiry, nonce; `none` and HMAC are refused.
4. The account is matched on the employee ID's keyed hash
   (`organization_id_hash`) and nothing else. A match is signed in; no match
   holds the assertion, sealed, until the person confirms a mobile by code
   (`POST /c/{token}/sso/mobile`, `/verify`), then creates the account as an
   active `employee` with the asserted name, address and ID. An asserted
   address already on another account, or a confirmed mobile that is, is
   refused with one neutral sentence and audited
   (`auth.sso_identity_conflict`): the administrator resolves it.
5. The session is a data principal's (`open_principal_session`, ADR 0013),
   whatever the account's role: the organisation's word on a consent link is
   worth exactly what a code is.

The callback sends the browser back to the link with `?sso=` saying what
happened; a failed assertion lands on the same neutral page as an invalid
link, and a provider that does not answer is reported as that, with "Try
again". A code is never sent on an `sso` link, and nobody registers by form
on one. An employee ID is never accepted from an unauthenticated form
(`POST /c/{token}/register` ignores one, open point F-8). The audit records
`auth.sso_signed_in`, `auth.sso_account_created`,
`auth.sso_identity_conflict` and `auth.sso_assertion_refused`, never the
claims.

## How an account is found

The contacts and the username are sealed, so ciphertext that differs on every
write is what the table holds
([ADR 0016](../decisions/0016-personal-data-sealed-by-a-separate-key-service.md)).
Nothing is looked up by the value. Every lookup computes the **keyed hash** of
what was typed, `HMAC-SHA256(kind:normalised value)` under `BLIND_INDEX_KEY`,
and compares it with the `*_hash` column beside the sealed one
([ADR 0017](../decisions/0017-lookup-by-keyed-hash-and-name-ngrams.md)):

- Password sign-in: `email_hash` or `username_hash`
  (`users.credentials_by_login`).
- A code sign-in, a consent link, "is this address taken": `email_hash`,
  `mobile_hash` or `secondary_email_hash` (`users.by_contact`, `medium_of`).
  An `@` makes a contact an address; anything else is a mobile. The second
  email is matched only once proved; the email and the mobile are matched
  proved or not, which is open
  ([breaches.md](../domain/breaches.md#open-questions)).
- "That is already the address on your account": the hashes, not the strings.

The normalisation is part of the contract. Emails are stripped and
lower-cased, mobiles go through `normalise_mobile`, usernames are
lower-cased (`infrastructure/dkms/blind.py`). The key service computes the
same hashes under `DKMS_HASH_KEY`, which must be the same string. Change
either and every stored hash stops matching, so nobody can sign in until the
column is recomputed.

The hash is computed in this process, so finding the account and checking a
password do not need the key service. **Sending to a stored address does.**
The staff second factor goes to the account's email, which is sealed and is
opened in the worker at the moment of sending; with the key service
unreachable the task retries, and the code arrives when it is back. A staff
invitation opens the address in the API, because it goes into the reset link
as well, so the invitation fails with a 503 instead. A data principal's
sign-in code goes to the contact she typed, which was never sealed, and does
not wait. `/ready` reports the key service as its `encryption` check.

## Passwords

| Property | Value | Why |
|---|---|---|
| Algorithm | Argon2id | Memory-hard; a GPU farm is a poor investment against it |
| Minimum length | 12 | Length beats composition rules — people remember a passphrase and write down `P@ss1!` |
| Maximum length | 128 | Argon2 is deliberately expensive; unbounded input is unbounded work per request |
| Salt | per hash | Identical passwords must not be visibly identical in the table |
| Rehash | on sign-in | Cost parameters rise; existing hashes upgrade on next successful use |

`verify_password` returns `False` on a malformed hash rather than raising. A
corrupted row should be a failed sign-in, not a 500 with the hash in the
traceback.

## One-time codes

Six digits, ten minutes, five verify attempts, five requests per contact per
hour. The attempt cap is what makes six digits strong enough: unbounded, a
million guesses is minutes of scripted work.

**Verification is one atomic step.** The digest comparison, the deletion on
success and the attempt count on failure run as a single Redis script, so two
requests carrying the same correct code cannot both be told yes. Until
September 2026 the check was a `GET` and the delete a later pipeline, and an
external review reproduced two concurrent callers both succeeding; the
integration suite now races eight verifications of one code and expects one.
A flow with more to check before it acts first checks the code with
`consume=False`, which counts a wrong try but deletes nothing, and spends it at
the end by a check that consumes it, so the one yes still holds: a report from the
public link, and a nominee's request, which since 7bdb710 spends its code only
once the request is accepted, so a request refused for its right, its event or its
kind leaves the code for the next try
([rights-requests.md](../domain/rights-requests.md#nominees)). **Finishing a
sign-up is not one atomic step** (`POST /auth/register/verify`): it checks every
code waiting without spending it, and once all have passed discards them in calls
of their own, so two finishes at once with the right pair can both be told yes and
both open a session - on the same account, and only for somebody holding both
codes.

Stored as a **keyed hash, scoped to their purpose** — never in plaintext, and a
code issued for staff MFA cannot be replayed against the consent flow. Whoever
can read Redis should not thereby be able to complete somebody else's sign-in.

**A refused code says nothing of who is registered** (2026-11-08). Where anybody
can type a contact or a reference - a sign-in by code (`POST /auth/otp/verify`), a
consent link's code (`POST /c/{token}/otp/verify`), a password reset
(`POST /auth/password/reset/confirm`), a nominee's request
(`POST /rights/nominee/requests`), finishing a sign-up
(`POST /auth/register/verify`) and the public rights form
(`POST /rights/requests/verify`) - a wrong code, a code of the wrong length and a
spent budget of five tries all answer 400 `otp_invalid`, "Invalid or expired
code", as a contact nobody holds does; a body the schema refuses (a code of fewer
than four or more than ten digits, or not digits) is 422 for every caller alike,
before anything is looked up. Told apart, they said whom the register knows: the
length was checked only once an account had been found, and the fifth try ended in
429 "Too many incorrect attempts" only where a code had been sent, which is only
to a contact somebody holds. The fifth wrong try still discards the code, so
guessing stays bounded. A nominee's request has refused a code that is not digits
with the 422 since bd6cef1; its form checked only the length before, and such a
code answered the neutral 400. What answers 429 on those routes is the limit per
address: 30 failures in fifteen minutes at the sign-in, the reset and finishing a
sign-up, each counted apart (`AUTH_FAILURES_PER_ADDRESS`), ten requests an hour at
a nominee's request and 30 an hour at the rights form; a consent link's tries
never answer 429. Where a code goes to whatever address was typed or to the one a
link names - the public link's report, a holder ticket, a nomination - the answer
has nothing of the register to give away, and a code of the wrong length still
answers "Invalid code" and the fifth wrong try 429.

**Finishing a sign-up answers every refusal as it answers an unknown mobile**
(bd6cef1): 400 `otp_invalid`, "Invalid or expired code", on `mobile_code`, whether
the mobile is nobody's or on an account that cannot finish a sign-up (a member of
staff's, or a suspended or deactivated one), the account has nothing left to
answer, a code it is waiting for was left out, or a code for either contact is
wrong, of the wrong length or past its budget. Every code waiting is checked
before any is spent, so a wrong email code does not burn a right mobile code. Its
failures count against the address, at a door of their own (`sign_up_fail_ip`),
and that limit is its only 429: once an address has spent it, even the right codes
are refused until the window passes. Before, a code left out answered 422 "Enter
the code we sent to your email as well" before any code was checked, a refusal
came on the field of the contact waiting (`email_code` when only the email was),
and nothing limited the asking, so anybody could tell from a mobile nobody holds
an unfinished sign-up and an account whose email had not answered. Starting a
sign-up still tells an unfinished sign-up from a new mobile, through an email
already taken and through where its codes go (below). The sign-up page sends a code for every contact it
was given, so the one answer costs it nothing, and since that answer cannot say
that a code was cancelled, the page says to everybody that each code expires in
ten minutes or after five wrong tries, and offers **Send the codes again** (67b3dc0).
Since 1f9fa41 it also says that the codes go to the contacts given when the sign-up
began, and with a mobile alone it keeps a box, to be left empty otherwise, for the
code to an email given then.
Refusing an account with nothing left to answer closed a hole (32d483a): from
2026-09-06 until 2026-11-08 the mobile alone, with no code, opened a session on
any data principal's account whose every contact had answered once, since no code
was outstanding to check.

**Starting a sign-up refuses a child's date before the contact is looked up**
(7bdb710). `POST /auth/register` refuses a child's date of birth before it looks
the contact up: 422 `minor_not_permitted` on `dob`, the same for a contact nobody
holds, a sign-up never finished and any account, and nothing is sent or written.
Only the limit per contact, five an hour, comes first, so the try still counts
against the contact. Checked after the lookup, a child's date answered 202 for an
unfinished sign-up, 422 for a contact nobody holds and 409 for an account, so a
stranger could tell an unfinished sign-up from a new contact. Only a data
principal's unfinished sign-up is resumed: its codes are sent again, and it answers
202. Any other account found - by the mobile, or else the
email - answers 409 `contact_taken`, naming the field, as any account does, by
product decision
([03-security.md](../backend/03-security.md#data-principal-sign-in)), and nothing
is sent to it. That now includes a member of staff invited and not yet given a
password and a breach holder's temporary login, both `pending` until a password
is set. Their way into the console is the invitation or a password reset. Like
any account, they can sign in to the portal by a code, as a data principal, which
is what the sign-up page's notice on that 409 offers them: a code to sign in goes
to any account `active` or `pending` (`request_subject_otp`), and only a data
principal's `pending` row is held back when the code comes back
(`verify_subject_otp`), so the session opened is a data principal's, with the
account's own role kept as `account_role`
([03-security.md](../backend/03-security.md#two-populations)).
Before, every `pending` account was resumed, so such a person was mailed or texted
sign-up codes nobody had asked them for and no sign-up could use. A resumed
sign-up keeps what it was started with: it is found by the mobile typed again, or
else the email, and its codes go to the contacts it was first given, never to any
typed since, so a mistyped contact cannot be corrected by signing up again, and
the sign-up page no longer offers **Change the details** as if it could (1f9fa41;
open, [breaches.md](../domain/breaches.md#open-questions)). An email added now to
a sign-up begun with a mobile alone is neither stored nor sent a code: the step
still says a code has gone to it and will not confirm until its box holds six
digits, though the server asks no code of it, and the account then opens without
that email.

**Starting a sign-up still tells an unfinished sign-up from a new mobile**, in two
ways, both from a resume that ignores the contacts typed now (open,
[breaches.md](../domain/breaches.md#open-questions)). First, by the answer: the
email is looked up only when the mobile matches nobody. With an email already on
another account - a member of staff's, or the caller's own finished account - a data principal's
unfinished sign-up's mobile answers 202 and is resumed without the email being
looked at, where a mobile nobody holds answers 409 `contact_taken` on `email`, and
a mobile on an account 409 on `mobile`; so one taken email sorts mobiles into all
three, five tries an hour per contact. Second, by delivery: a resumed sign-up's
codes go to the contacts it was first given, so an email the caller holds receives
a code when the mobile is new - on a new sign-up, or on the caller's own sign-up
found by that email - and none when the mobile is somebody's unfinished sign-up,
though the answer is the same 202.

## What a code proves

A code that comes back proves the contact it went to, and the flows below stamp
that contact proved on the account (`users.mark_contact_verified`, which sets
`email_verified_at`, `mobile_verified_at` or `secondary_email_verified_at` and
writes no audit row; each flow keeps its own). A rights request finds a dismissed
report from the public link by an account's email only once the email carries
that stamp, and by its second email only once that one does
([rights-requests.md](../domain/rights-requests.md#reports-from-the-public-link)),
so which flow stamps what decides what a request finds (2026-11-08). A stamp also
counts where it always did: a consent receipt, a withdrawal's confirmation and an
HR activity's request to consent again go to a stamped email before a stamped
mobile (`consent.receipt_contact`), and the account page shows a stamped contact
as confirmed.

| Flow | Stamps |
|---|---|
| A sign-in by code (`POST /auth/otp/verify`) | The contact typed, which the code is bound to: the mobile, the email or the second email |
| A password reset, a staff invitation and a breach holder's invitation (`POST /auth/password/reset/confirm`) | The email, where all three send the code |
| The staff second factor (`POST /auth/mfa/verify`) | The email; the code never goes to the mobile |
| A consent link's code (`POST /c/{token}/otp/verify`) | The contact typed - the mobile, the email or the second email - on whatever account `users.by_contact` finds for it, a sign-up not yet finished included: the owner of an address typed into somebody else's sign-up, answering a code to it on a link, stamps it on that sign-up, which a sign-in by its other contact can then finish (open, [breaches.md](../domain/breaches.md#open-questions)) |
| A nomination accepted (`POST /rights/nominations/{token}/accept`) | Only a nominee account it makes, for whoever accepted: the contact the code went to. The code is issued under the nomination and that contact, and asking for one to the other contact replaces it in the same write, so one code is live and which contact it proves is where it lives, never a record kept beside it. An account already there is linked to the nomination and stamped with nothing (below) |
| Registration (`POST /auth/register/verify`) | Each medium answered |
| Confirming a contact from the account (`POST /me/contact/verify`) | That contact |
| An account created by SSO (`POST /c/{token}/sso/mobile/verify`) | The mobile, by its code, and the address the identity provider asserted |

These stamp nothing:

- **The public rights form's code and an officer's Confirm**
  (`POST /rights/requests/verify`, `POST /requests/{uuid}/verification/confirm`).
  The code proves that whoever made the request holds the address it went to, not
  that the account's holder does. `users.by_contact` attaches a public-form request
  to an account carrying that address unproved - a nominee's account, whose email
  the principal typed - so a stamp there would let that account's later requests
  find the dismissed reports of the address's owner.
- **A nomination accepted on an account already there**
  (`POST /rights/nominations/{token}/accept`), for the same reason: the account is
  the one `users.by_contact` finds by either contact the principal recorded, which
  may carry the address unproved, and the code proves only that whoever accepted
  holds the contact it went to. Stamped there, as it was between 0923a5b and
  32d483a on 2026-11-08, the address's owner accepting by it handed that account
  their dismissed reports. The nomination is still linked to that account, so its
  holder follows the requests the nominee later raises; that is open
  ([breaches.md](../domain/breaches.md#open-questions)).
- **An SSO sign-in to an account already there** (`GET /auth/sso/callback`): only
  creating one stamps. Whether the assertion should stamp the address, as creation
  does, is open ([breaches.md](../domain/breaches.md#open-questions)).
- The flows with no account in them: the public link's report code, a holder
  ticket's code, a nominee's request, declining a nomination, and the development
  sign-in mock.

Nothing was backfilled. An account whose email none of these flows has reached
finds no dismissed report by it until one does, and the request's **Reports from
the public link** card says that no email address proved to be the requester's is
held: an account from before the stamps (0015) that has not signed in by email
since, a staff or breach holder account activated before 2026-11-08 until its next
second factor, a nominee's account whose code went to the mobile or that was there
before the nomination, an account whose email was never stamped and whose mobile
was changed and not confirmed (read until 2026-11-08 as one from before the
stamps), and a sign-up nobody finished.

## Lockout

Five failures in thirty minutes locks the account for thirty minutes.

Keyed on the **account, not the address**. An attacker rotates addresses; a
legitimate user behind a corporate NAT should not be locked out because a
colleague mistyped their password.

## What is never logged

The code, the password, the session token, the consent link token. What *is*
logged is that a delivery happened and an obscured recipient — enough to answer
"did it go out", not enough to be a contact list.

The audit trail does not carry the contact either. `user.invited` and
`user.created` record the role, and the person by `subject_user_id`
([ADR 0015](../decisions/0015-nothing-erasable-in-a-trail-nobody-can-erase.md)).
