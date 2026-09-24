# The consent lifecycle

From a notice a lawyer drafted to a record that can be produced years later.
Every step below exists to make the last one possible.

## 1. The notice

A notice belongs to a project and says what the data principal needs to know
before deciding: who is collecting, why (the purposes, each with its data
categories, retention and rights), and how to withdraw or complain. It is
written in the console by the Privacy Office, or brought by the R&D User as
the filled-in legal template, a `.docx` whose
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

## 3. Who is signing

**The link authenticates; it does not enrol.** She gives one contact, her
mobile by default or her email instead, and confirms it with a six-digit code.
The artefact is then bound to an account that already exists, which is what
lets her find it, read it and withdraw it afterwards. A set of details typed
once at a collection site could not do any of that.

Somebody with no account is offered one: the screen links to sign-up carrying
the link's own address, so she returns to the same consent link once the
account is hers, rather than having to find it again at a counter.

A code is sent only to a contact the register knows — a member of staff's
included, since every account may act as a data principal; the session the code
earns carries a data principal's powers and no others. The reply does not say
whether a contact was known - it is
the same sentence either way, so the form cannot be used to ask whether a
number is registered. That is also why the offer to create an account is shown
to everyone rather than only to the people who need it.

Self-registration on the portal is where the details are given: name,
**mobile** (required), email (optional) and her date of birth. A code goes to
each contact she gave, and each must answer before the account is hers. A
contact already registered is recognised rather than duplicated; a staff
account arriving through a consent link is refused.

Date of birth matters because of s.9: whether she is a **minor** is derived
from it in the database (`cmp_is_minor`, over `minor_until`). Section 9(1)
asks for a parent's or guardian's verifiable consent before *any* processing of
a child's data, and the guardian route does not exist yet, so the platform has
one lawful answer to a child: no. Sign-up and the link's own registration
(`POST /c/{token}/register`, which asks for the date too) create no account for
a child, and `capture` records no consent from one - whatever the purpose's
`permitted_for_minors` says, because that flag is s.9(3) and never stood in for
the guardian. The refusal names no guardian route, since there is none to offer.

**An unknown age is not an adult.** Most accounts were created through a link
that never asked, and `cmp_is_minor` answers NULL for them. `capture` refuses
them too (`age_required`, nothing written) until a date of birth is given, and
the portal asks for it at the next sign-in, before any page but the two that
must always open - withdrawing a consent and making a request are not consents.
On this page the question comes between confirming the code and serving the
notice. The rule lives in `cmp.domain.users.age`. See
[ADR 0007](../decisions/0007-mobile-first-contacts.md) for why the mobile
comes first.

## 4. Serving the notice

`GET /c/{token}/notice?language_code=` renders the rendition she chose and
stamps `served_at` **on the server**. The server also keeps its own record of
that serving, bound to her account, the link and the rendition, for six
hours. Her consent is recorded against that record and nothing else: a
client cannot supply the moment, and a consent for which no serving exists is
refused with `notice_not_served`
([ADR 0011](../decisions/0011-server-held-notice-serving.md)). Changing
language serves again and records again, because she is now reading a
different text.

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
column: `consented`, `partial`, `declined` and `withdrawn` are derived from
its grants on every read. **Withdrawn means a withdrawal left nothing
granted.** An artefact written by withdrawing one purpose of several is marked
`is_withdrawal` - that records the act - but reads `partial`, is exported with
the purposes still granted, and its remaining purposes can be withdrawn in
turn from the portal.

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
  was my data shared with". The file is kept as generated, so a later
  download is the bytes the processor was given.
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
| One root artefact per person and notice | partial unique index (migration 0023) and a per-pair advisory lock in `capture` |
| The serving moment is the server's | the serving record in Redis, required by `capture` |
| Consent evidence is append-only | statement trigger and revoked grant (migrations 0002, 0003) |
| Status is derived, never stored | `v_current_consent` |
| No consent from a child, or from an unknown age | `cmp.domain.users.age`, from `cmp_is_minor(minor_until)`, before `capture` writes anything |

`tests/integration/enforcement/` bypasses the service layer on purpose and
writes SQL directly, because a guarantee that only holds through Python is
not a guarantee.
