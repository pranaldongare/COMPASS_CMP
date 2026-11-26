# 0047: A retention review asks the ones responsible, and proves the answer

- Status: accepted
- Date: 2026-11-26
- Migration: 0076
- Related: [0035](0035-a-public-request-reaches-the-inside-only-when-the-inside-collects-it.md)
  (the relay), [0045](0045-analytics-are-figures-counted-from-the-record.md)
  (the figures), [0046](0046-an-employee-is-checked-with-verifyemail-at-sign-in.md)
  (the last decision of this kind)

## Context

A purpose says how long a consent lasts (`consent_validity_period`) and how
long the data may be kept after it (`retention_period`). Only the first was
acted on: the night quarantined the assets of consents whose validity had
run out (`apply_retention_lapse`). Nobody was asked to erase anything when a
retention period passed, nobody answered, and nothing proved it was done.

The product owner proposed (2026-11-26) that the platform raise a notice to
each one responsible - DPO with the DCO Admin and DCO, Legal with HR, the
third parties - "something like a ticket, but not mixed with rights or breach
tickets". Their answers to the questions this raised:

1. **Retention starts at the consent's end** - its withdrawal, or its
   validity running out.
2. **Anonymisation is allowed**, wherever erasure is not possible, with a
   clear reason.
3. **Outside holders answer by a link**, as on rights and breach tickets.
4. **Consent again:** yes, once the DCO Admin or the HR PoC confirms it, and
   only while the project is active.
5. **The automatic quarantine stays**, as the first step.
6. **Telling people before erasure:** configurable per purpose, on to begin
   with.

## Decision

1. **A register of its own.** `retention_review` is one cohort: one kind
   (`validity` or `retention`), one project or HR activity, one purpose, one
   month due. A cohort of thousands is one review with a count, not a ticket
   each; the people are `retention_review_person`, by consent. It is the
   project's office's (`office_isolation`), read by its officer (resource
   `retention`: the DPO, Legal), and never appears among rights requests or
   breaches.
2. **The night finds them** (`cmp.maintenance.retention_reviews`, 02:45, after
   the quarantine). A validity review is made up to the furthest reminder day
   ahead (90 days) and kept for 30 days after; a retention review once the
   data falls due within that horizon, or already has. The sweep is
   idempotent: a consent is in one review of each kind once. A person under a
   legal hold is kept out (`held`) and comes back when it is released; a
   person who consented again leaves (`renewed`). *Look again now* does the
   night's work at once.
3. **Who is asked** (`retention_action`, one per one responsible):
   - the **owner**: an HR activity's HR PoC; a project collected by a third
     party, its office's DCO Admin; collected in-house, its R&D User;
   - every **processor holding the data** - by the exports that carried the
     consents, the assets its sources captured, and an HR activity's
     category processors - in the console when its respondent has a login,
     otherwise by an emailed link. A processor with no respondent is listed
     with nobody to ask, for the officer to set aside or chase by hand.

   A validity review asks its owner at once, while there is time to invite
   the people again, and only while the project is active. A retention
   review asks everyone when it falls due. Nobody is given fewer than seven
   days.
4. **What an answer is.** Validity: invite them again, or not. Retention:
   *erased*, *anonymised* (a reason is required), *kept* (a reason and a date
   after today are required), or *not held*. The database refuses an
   anonymisation or a keeping without its reason. The reason is sealed.
5. **The officer accepts or sends back** each answer; *not needed* sets an
   action aside. Accepting a validity owner's yes sends each person in the
   review the project's live consent link (`RETENTION_RECONSENT_INVITE`). A
   review closes only when every action is accepted or set aside.
6. **Reminders and escalation** (`retention_setting`, one row): the owner and the officers at
   90, 30 and 7 days before; the one asked on the day their answer falls
   due; the officers once it is 14 days late. Each at most once.
7. **People are told before erasure** where the purpose says so
   (`purpose.notify_before_erasure`, default on), 48 hours ahead, by email and
   text (`RETENTION_ERASURE_NOTICE`), once.
8. **An outside processor's link** is a holder ticket's (0049) in every way
   but its key: the link alone shows the reference, the processor and where
   the code goes; the code goes to the respondent's address, never one
   typed, and opens an hour on that one action in the same HttpOnly,
   SameSite=Strict cookie, under its own Redis key (`rtl`). The portal page
   is `/retention/{token}`; its calls, `/retention-links/{token}/*`, cross by
   the bridge, SQS and the collector and are on the relay's allow-list
   (ADR 0035). Every failure is the same 404; the token is scrubbed from
   the access log.
9. **Proof.** A closed review has a certificate, PDF or CSV: the consents by
   number, why each ended and when, every answer with its reason, who
   accepted it, who closed the review. Every download is on the trail
   (`retention.certificate_downloaded`), as is every step before it, against
   the review - never a person. Analytics counts reviews opened, closed and
   closed on time, answers overdue, and data kept past retention
   (`retention.*`).
10. **Nothing is erased by the review itself.** Erasure is the holder's act,
    answered and accepted. The quarantine still runs by itself; DataVault is
    still told of consent changes (0071). Asking DataVault to erase a
    review's assets by itself (the `datavault` action kind exists for it) and
    evidence files on an answer are left for later.

## Consequences

- A purpose's retention is acted on and proved, per cohort, without one
  ticket per person.
- The owner of a third-party project is its office's first DCO Admin: an
  office with several should say which, when that matters.
- People are numbers everywhere in a review. An officer who needs a name
  opens the consent.
