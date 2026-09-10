# 0007. Mobile required, email optional, for data principals and nominees

Status: accepted. Migration 0015, September 2026. Supersedes email as the
identity of a data principal.

## Context

The people whose consent is collected at a field site have a mobile far more
reliably than an email, and a one-time code to a mobile is a factor they can
answer standing at the rig. The platform originally keyed a data principal on
email, which made the common case the awkward one.

## Decision

- A data principal registers with a name, a **mobile** (required), an email
  (optional) and a date of birth. A code goes to every contact given, and
  each must be answered before the account is hers. `email` on `auth_user`
  is nullable; a trigger requires a mobile for the data principal role and a
  CHECK requires an email for staff.
- Sign-in sends a code to whichever registered contact she chooses.
- A nominee is named by mobile with an optional email, and accepts a
  nomination by choosing one of those contacts, receiving a code there, and
  entering it. The acceptance link alone accepts nothing.
- Verification timestamps are kept per medium.

The rule is a `BEFORE INSERT` trigger rather than a `NOT VALID` CHECK: a
`NOT VALID` constraint is validated on every later `UPDATE` of a legacy row,
which turned revoking an old nomination into a 500.

## Consequences

- An SMS transport is a production dependency, not an option.
- Every fixture that creates a data principal supplies a mobile.
- The browser suite reads two codes at sign-up and one at sign-in from the
  outbox.
- Contacts are normalised (E.164 for mobiles, lower-cased emails) and masked
  in every message and page.

## Revisit when

A deployment serves people without a mobile. Email-only registration would be
a configuration switch on the same schema.
