# 0014. A nominee follows the request they raised, and reading is not acting

**Status:** accepted · 2026-09-17

## Context

Section 14 of the Act lets a data principal name a nominee to exercise her
rights if she dies or cannot act. The platform implemented the asking: the
nominee accepts a link, proves a contact she recorded, and files a request
from the public nominee page. The request is stored with the **principal** as
its subject, which is right — it is her record that is being asked about.

Every route that returns a request or its status filters on
`subject_user_id = caller`. The nominee is by construction not that person:
`nominate()` refuses a self-nomination. So there was no endpoint, anywhere,
that would tell the nominee what became of the request he had raised, and no
page that showed it.

Found on a running stack. A nominee had invoked a nomination on a death
trigger and filed an access request. The office answered and closed it a week
later with a response and a released file. Signed in, he saw an empty request
list. The acknowledgement he had been sent said the response "will be
available to you signed in, from your own account" — a promise the platform
could not keep for him.

Two things were already right and shaped the fix. Every progress message about
a nominee-channel request already goes to the nominee and never to the
principal, who may be exactly as incapacitated as claimed: the response text
had reached him in full by SMS. And a signed-in nominee could already see the
nomination naming him, and the reference of the request he had raised — the
reference, and nothing beside it, which reads as nothing having happened.

## Decision

**The request he raised reads to him as it does to her.** State, clock, path,
response text, and the files released with it, on the same download window and
the same hash check. He is the person exercising the right; a right to ask
without a right to be told the answer is not a right. It discloses nothing he
was not already sent.

**Reading is not acting.** Being signed in is enough to read what became of
his own request. Making another in her name is not: that still needs the
nominee page and a code to a contact she recorded. Disputing a response makes
a new request, so it stays on the acting side and is absent from his view.

**Revocation stops what comes next and unasks nothing.** A nomination revoked
after it was invoked keeps its request visible to him, marked plainly as no
longer in effect. One revoked before he ever acted disappears, as before. The
principal can end his authority; she cannot retract a question he lawfully
asked, or the answer he is owed for it.

**On incapacity the principal is acknowledged too.** Her account stays open
and the request appears in her own list either way. Somebody exercising her
rights in her name is a thing she should hear from us rather than discover,
and incapacity is the claim she might be in a position to dispute. On a death
claim there is nobody to write to.

**The nominee is linked by account, not by string.** Acceptance records which
account accepted (`nomination.nominee_user_id`, migration 0026). Matching by
comparing contact strings already missed a second email and would break the
day he changed his mobile — and the contacts on the nomination must not follow
his later edits, because they are what she recorded and what a code is sent
to.

## Consequences

- The predicate for "a request I raised as a nominee" is a second repository
  function rather than a loosening of `subject_request`. "Mine" keeps meaning
  the rows whose subject I am, so a later reader of that predicate is not
  misled ([ADR 0004](0004-scope-in-the-where-clause.md)).
- The request card is shared by both readers rather than copied, so the two
  views cannot drift — and the one that drifted would have been the nominee's.
- A nominee with no account is unchanged and still served by message alone:
  a nomination that names an email only creates no account, because a data
  principal's needs a mobile ([ADR 0007](0007-mobile-first-contacts.md)).
  Every message about the request already goes to him.
- The audit trail names him. A download he makes is recorded with him as the
  actor and the principal as the subject, which is what the record should say.

## Revisit when

A deployment needs a nominee's sight of a request to end with the nomination,
or needs a nominee to dispute a response without a fresh code. The first is
the status filter on the nominee's list; the second means deciding that a
session is proof enough to act, which this record deliberately does not.
