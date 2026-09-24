# Authentication

Two populations, two mechanisms, and the difference is deliberate.

## Staff

Password sign-in, Argon2id, and then a second factor for **every** staff role: a
code to the account's email. It began with the two roles whose compromise is
unbounded, the DPO and the administrator; since 2026-09-06 it covers every
internal role, because the others can still mint consent links, read consent
records and move data. The list is `MFA_REQUIRED_ROLES`, derived from the role
enum by default; a deployment may narrow it, and answers for that.

A **partial session** exists between password verification and MFA. It authorises
exactly one route, the verify endpoint; every other endpoint answers 401 with
`mfa_required` until it is promoted. It is a distinct dependency type
(`PartialUser`) rather than a flag on the full one, because a flag is one missed
`if` away from an MFA bypass.

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
