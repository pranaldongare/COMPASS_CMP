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

The reasoning: a data subject who could set a password would have an account
worth phishing, and would reuse a password they use elsewhere. One who receives a
code per sign-in has nothing worth stealing between sessions.

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
  An `@` makes a contact an address; anything else is a mobile.
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

Stored as a **keyed hash, scoped to their purpose** — never in plaintext, and a
code issued for staff MFA cannot be replayed against the consent flow. Whoever
can read Redis should not thereby be able to complete somebody else's sign-in.

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
