# 0027. A breach can reach people with no account: contacts from a list sent to the office

**Status:** accepted · 2026-10-07. Migration 0045, commit c517f4e. Amends
[ADR 0021](0021-a-breach-is-recorded-and-its-duties-tracked-never-submitted.md)
(who it touched is no longer only accounts).

## Context

ADR 0021 derives who a breach touched from the platform's own records - a
processor's exports, a source's assets, its tables in a window - and lets
the DPO add people by hand. Every one of those is an account. The
principals' duty under Rule 7(1) completes only when everyone listed has
been sent the notice, and the platform tells people by writing to their
account and queueing an email and an SMS.

In practice the people a breach touches are often not on the platform at
all: a processor's own participants, a team's contact list. The list then
arrives from outside, by email, as a spreadsheet. Such a breach could list
nobody it touched, and so could never close; or the office told them by
hand, outside the record the Board's report is drawn from.

Making each of them an account was the obvious way in, and the wrong one.
An account is a standing on the platform: it can sign in, appears in the
user register, and is reached by everything that reaches accounts. A person
named once in a processor's spreadsheet has asked for none of that.

## Decision

- **The DPO adds people from a list** (`domain/breach/lists.py`), in one of
  two forms, each from a template downloaded on the breach's page:
  - **people** - `name`, `email`, `mobile` per row, either contact or both,
    the name optional;
  - **asset IDs** - the platform's asset ID or the capture tool's own
    reference, with the source's code where two sources share one. Each
    asset leads to the people who consented in it. People in an asset who
    consented to nothing cannot be traced; they are counted, and said.
- **Checked, then taken.** *Check the file* writes nothing: it counts what
  the file would add and names each unreadable row by number. Taking it adds
  the rows that can be read. A row already listed, or repeated, is skipped
  rather than refused, so a corrected file can be sent again.
- **Matched to accounts by blind index.** A row whose email or mobile is an
  account's, by the keyed hash of each ([ADR 0017](0017-lookup-by-keyed-hash-and-name-ngrams.md)),
  lists that account (`breach_affected.found_by` `upload`). It is told as
  any listed account is, the notice written to the account as well.
- **Anybody else is a contact of this breach alone** (`breach_contact`):
  name, email and mobile sealed, with blind indexes so a contact is listed
  once per breach. No account is made, and the contact is not shared with
  any other breach or module.
- **Only ever added to.** `breach_contact` and `breach_upload` are
  append-only by trigger and grant, like every list of who a breach touched.
  A contact is never removed: listing too many is the safe side of Rule 7.
- **The uploaded file is not kept.** It is a list of contacts in the clear,
  and what matters is now sealed in the rows. Its sealed name, its hash and
  what it came to are kept (`breach_upload`), and listed under *Lists taken*.
- **A contact is told by email and SMS.** Never by a portal notification,
  since there is no account to write it to: a delivery addresses an account
  or a contact, exactly one (`breach_notice_delivery_one_recipient`), and a
  portal delivery must be an account's
  (`breach_notice_delivery_portal_is_an_account`).
- **They count.** *Principals notified* is owed to the accounts listed and
  the contacts alike (`notices.listed_count`). Each contact's outcome counts
  toward the duty exactly as an account's does, and contacts added after the
  duty completed reopen it.

## Consequences

- A breach whose people are not on the platform can now be told and closed,
  and the Board's report can say who was told and how, from the register.
- The platform now holds personal data of people with no account: names,
  emails and mobiles, sealed. They are in the inventory
  ([personal-data.md](../domain/personal-data.md)).
- **Nothing erases or retires a contact.** No code in `domain/rights` or
  the retention task (`tasks/maintenance/retention.py`) reads
  `breach_contact`, and the table refuses update and delete. A contact
  cannot reach her own record either: she has no account to make a request
  from, and nothing links the row to an account made later. Whether the office keeps
  these rows for as long as the breach record, and how a contact's access or
  erasure request would be answered, is not decided.
- A list matched to the wrong account cannot be undone: the account stays
  listed and is told. Checking the file first is the guard.
- A contact's email and SMS are their own messages (*Personal data breach
  notice, to someone with no account*): the email carries the five things
  Rule 7(1) requires with no account to point to, and the SMS says what
  happened, what they can do and whom to ask.

## Revisit when

Legal sets a retention period for breach records, which would have to say
what becomes of contacts; a contact asks for access or erasure; processors
send lists by an interface rather than a file; or the office wants a
contact matched to an account made later.
