# The consent lifecycle

From a notice a lawyer drafted to a record that can be produced years later.
Every step below exists to make the last one possible.

## 1. The notice

A notice belongs to a project and says what the data principal needs to know
before deciding: who is collecting, why (the purposes, each with its data
categories, retention and rights), and how to withdraw or complain. It is
written in the console or imported from the legal template, a `.docx` whose
cells the parser reads: the language of the notice, the purposes and their
categories, the retention period, the erasure trigger. A document with a
placeholder still in it is refused, as is a language the platform does not
store, by name.

A notice has **versions** and, per version, one **rendition per language**.
Each rendition is approved by someone with legal standing before it may be
served. A checklist says what a version still lacks before it can be
published: renditions approved, purposes activated by the DPO, the rights
route present.

**Publication freezes the notice.** The trigger `cmp_notice_freeze()` refuses
any change to a published notice or its renditions. A correction is a new
version; the old one survives, because consents recorded against it must be
able to say exactly what was shown.

## 2. The link and the site

A data principal never types an address. She opens a **consent link** minted
for a collection site by its owner, on the data-principal portal, at
`/c/{token}`. The link resolves to the site, its project and the notice
version it was minted for; an invalid, expired, exhausted or revoked link
says only that it is not valid, and never why.

## 3. Registration

Her details, if she is new: name, **mobile** (required), email (optional),
and for self-registration on the portal her date of birth. A code goes to
each contact she gave, and each must answer before the account is hers. A
contact already registered is recognised rather than duplicated; a staff
account arriving through a consent link is refused.

Date of birth matters because of s.9: whether she is a **minor** is derived
from it in the database (`cmp_is_minor`), and a minor cannot grant a purpose
the registry has not marked as permitted for minors. Where the date is
unknown the account is recorded as such, not assumed adult. See
[ADR 0007](../decisions/0007-mobile-first-contacts.md) for why the mobile
comes first.

## 4. Serving the notice

`GET /c/{token}/notice?language_code=` renders the rendition she chose and
stamps `served_at` **on the server**. That timestamp is what her consent must
carry; a client-supplied one could claim the notice was shown at any
convenient moment. Changing language serves again and stamps again, because
she is now reading a different text.

## 5. The decision

The consent form shows every purpose with accept and decline of equal
prominence, nothing pre-ticked, and every purpose must be answered. Recording
consent writes one **consent artefact** and one **grant row per purpose**,
with:

- the notice version and language served, and the SHA-256 of the exact text
  (INV-4, enforced by `cmp_consent_coherent()`);
- `served_at` from step 4 and the moment of the action, with the database
  refusing an action before the serving (s.5(1));
- how the action was taken: a checkbox, a button, a signature, a verbal
  recording.

Consent is **per purpose, never in aggregate**. The artefact has no status
column: `consented`, `partial`, `declined` are derived from its grants on
every read.

## 6. Withdrawal

Withdrawing writes a **new artefact** that supersedes the earlier one
(`supersedes_consent_id`), for all purposes or some. The earlier record is
never edited - the table refuses `UPDATE` at the trigger level and the
application role's grant is revoked - so the chain of artefacts is the
history, and `v_current_consent` resolves it to the one in force for each
(person, notice) pair. She withdraws from her portal page, with the frozen
notice text beside the decision she is changing.

## 7. What follows a consent

- **Exports** include only people whose current consent covers the purpose;
  each export writes a disclosure record naming them, which she sees as "who
  was my data shared with".
- **Assets** collected at the site are reconciled to consents through
  `asset_consent`; a person in frame with no consent is kept visible as a
  bystander.
- **Retention** lapses on the purpose's schedule: the 02:00 maintenance task
  applies the lapse behaviour the purpose declared, matching only rows still
  active so it is safe to rerun.
- **Rights requests** derive who holds her data from the exports and assets
  above, and an erasure request can be confined to one consent's chain.

## What she can see

On the portal, signed in with a code to her mobile or email: every consent
with its status, the words she actually saw for each, the supersession
history, the disclosures, and the withdrawal control. On the console, staff
see the consent register within their scope - counts and artefacts, never a
way to alter one.

## Invariants, and where they live

| Invariant | Held by |
|---|---|
| A published notice and its renditions never change | `cmp_notice_freeze()` |
| An artefact carries the hash of the text served | `cmp_consent_coherent()` |
| The notice was served before the action | `CHECK served_before_action` |
| An artefact is superseded at most once | partial unique index |
| Consent evidence is append-only | statement trigger and revoked grant (migrations 0002, 0003) |
| Status is derived, never stored | `v_current_consent` |
| A minor cannot grant a purpose not permitted for minors | the consent service, from `cmp_is_minor(dob)` |

`tests/integration/enforcement/` bypasses the service layer on purpose and
writes SQL directly, because a guarantee that only holds through Python is
not a guarantee.
