# 0013. Every account is a data principal; staff is a role the session acts with

Status: accepted. September 2026. Migration 0025. Amended 2026-09-21: the
contact rules are enforced on keyed hashes (below).

## Context

A member of staff is also a natural person whose data the organisation
processes: a DPO consents to a study, an administrator has a file the rights
process may reach. The platform modelled one row with one role, and the
data-principal portal pointed anybody with a staff role at the console. So the
DPO's own consents could be given only under a second, personal identity, or
not at all — and the day she left, deactivating her staff account switched off
every standing she had, consents and rights included, which the Act gives her
whether or not she still works here.

Investigating this found something worse. The portal's code sign-in looked a
contact up and minted a session with whatever role the row held. A code to a
staff mailbox — no password, no second factor — produced a full staff session:
`role: dpo`, every power of the role, `/audit` and `/users` answering 200. The
portal displayed "this portal is for data principals"; the API behind it did
not. ADR 0006's second factor for every staff role was bypassed by reading one
email.

## Decision

- **The session carries the role it acts with, and every permission check
  reads the session.** A sign-in by one-time code — the portal, a consent
  link — always mints a `data_subject` session, whatever the account's role.
  A sign-in by password and second factor mints the account's role. The row
  is untouched; `account_role` on the session records what it says, for
  display only. The permission matrix, navigation, writes and every
  `Require*` gate already read `session.role`, so nothing downstream needed
  to change, and a code is now worth exactly what a data principal can do.
- **Any account may act as a data principal.** The portal and the consent
  link accept a member of staff's contact and give them a data principal's
  session and no more; the code request answers identically whether or not
  the contact is registered, as before.
- **Deactivating a member of staff ends the role and keeps the person.** The
  row becomes `data_subject`, the password is removed, `person_type` becomes
  `ex_employee`, and the account stays active. They reach their own consents
  and rights as any data principal does. Reactivating them as staff is a role
  change and a password reset, as for anybody.
- **A second email, confirmed before it can sign anyone in.** One more column
  pair on the account, added by the person from their account page, sent a
  code, and searched by the sign-in lookup only once the code has come back.
  A mobile added or changed the same way is likewise unconfirmed until it
  answers. An address identifies one person whichever column holds it: a
  unique index on the new column and a trigger across the diagonal, raising
  as a unique violation so the application reports a conflict.

## Consequences

- Closing the bypass and enabling the feature are one change, and a security
  test pins it: a code to the seeded DPO's address yields `role: data_subject`,
  `account_role: dpo`, the principal's navigation, and 403 from every staff
  endpoint.
- The console shows a portal session its "this console is for staff" page,
  correctly: the session *is* a data principal's. A DPO who wants the console
  signs in there, with the password and code, and the new session replaces the
  cookie.
- `pending` now means "the row's own role is not yet usable": a console
  account whose owner has not set a password, or a data principal
  mid-registration. It does not stop a member of staff with an unactivated
  console account from acting as a data principal, because that is not what
  is pending. Suspended and deactivated still switch everything off.
- A member of staff acting as a data principal has no date of birth on record
  unless they add one; the account page offers to. Until then the minor rules
  treat the age as unknown, as for any principal without one.
- The register's "Deactivate" reads "End staff access" for a staff row and
  says what is kept. Counts by status no longer include ex-staff among the
  deactivated: they are active data principals with `person_type`
  `ex_employee`.
- A member of staff who wants to keep reaching their consents after leaving
  must add and confirm a personal contact before the corporate mailbox goes.
  An administrator can set a mobile on their behalf; nobody else can add an
  email for them. A number set that way is sent its own code
  (`contact_added_for_you`), lasting hours rather than minutes because nobody
  is waiting at a code box — otherwise the number sits unconfirmed on the
  account with nothing having told its owner it is there.
- The account routes under `/me` that are about the *person* rather than about
  being a data principal — the profile, the contacts, the person type — admit
  every full session rather than a data principal's alone. A member of staff on
  the console is the same person as on the portal, and a card that shows a
  contact as unconfirmed with no way to confirm it is a dead end. The routes
  that are about being a data principal keep their gate.

## Revisit when

A deployment needs a staff member's principal standing to end with their
employment, or needs more than two email addresses per person. The first is a
policy flag on `end_staff_access`; the second is a contacts table replacing
the two columns.

## Amended · 2026-09-21

The contacts are sealed since 0028, so "a unique index on the new column and a
trigger across the diagonal" are now on the hashes beside the columns:
`auth_user_secondary_email_hash_key`, and `cmp_contact_belongs_to_one_person()`
comparing `email_hash` with `secondary_email_hash` (renamed from `*_idx` in
0029). The rule, and the unique violation the application reports as a
conflict, are unchanged. The code sign-in lookup matches a confirmed
secondary address by its hash (`users.by_contact`). See [ADR 0017](0017-lookup-by-keyed-hash-and-name-ngrams.md).
