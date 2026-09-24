# Reading the audit trail

Every write to the platform records one entry in `audit_log`, in the same
transaction as the change, hash-chained so that tampering is detectable.
How the trail is protected is the backend's
[audit.md](../security/audit.md). This page is about
asking it questions, which is what the DPO and the administrator do on the
console's **Audit trail** page.

## What an entry says

| Field | Meaning |
|---|---|
| Event | What happened, as `area.event`: `consent.given`, `rights.ticket_issued`, `auth.login_failed`. Every event the code can record is listed in `Event` in `cmp/domain/audit/service.py`. |
| Actor | Who did it: a member of staff, a data principal, or the system (a scheduled task). |
| About | The data principal the event concerns, where there is one: her consent, her request, her account. |
| Record | The row the event was recorded against, as a table and a key, resolved at read time into a name and a link. "No longer exists" means the row was deleted since; the trail outlives what it describes. |
| Recorded details | What the service chose to record: a reference, the purposes granted, the outcome, and `reason_given: true` where somebody gave a reason - the words themselves are in the sealed row they belong to. The client's address as its keyed hash, never the address. Never a credential, a code, a token, an email or the contents of an asset. |

## Asking a question

The page's filters are the API's, and they compose. Each becomes a chip, each
chip removes only itself, and the whole question lives in the address bar so
it can be bookmarked or handed to a colleague.

| Filter | Asks | On the API |
|---|---|---|
| Search | anything the trail recorded: a request reference, a purpose name, an event's name | `q` |
| About | a person found by part of their name or by their whole email or mobile, or a record found by name: data principal, member of staff, consent record, processor, data source, project, notice, collection site, rights request | `subject`, `actor`, or `entity_type` + `entity` |
| Area | the part of the platform: sign-in and access, consent, rights requests, notices, ... | `event_group` |
| Event | one kind of event, within an area or across all | `event_type` |
| Record type | every event recorded against one table, whichever row | `entity_type` |
| Actor role | events done by one role: what did administrators do this month | `actor_role` |
| From, To | a period, in whole days | `from`, `to` |

The **About** picker asks the server for matches as you type; each answer
says which filter it feeds, so `asha@example.org` as a data principal filters
on the events about her, and `priya@example.org` as staff filters on what she
did. Names and contacts are sealed in the database, so the lookup never
compares them: it compares keyed hashes of what was typed. Three letters or
more of a name find a person through the hashed runs kept beside it - the
answers are candidates, so `ana` may bring up a Banani as well as an Ana. An
email, a mobile or a staff username has to be typed **whole**; half an
address matches nothing, by design. A rights request is found by its
reference, by the contact on it, or by part of the name on the form or on
the account it was matched to. A record - a project, a notice, a processor
- is found by part of its name, which is not personal and not sealed.
Picking one clears the other two of that trio, because "about this consent
record" and "about this person" are different questions. How the hashes
work is in [the DKMS field list](../dkms/pii-tables-and-fields.md#2a-searching-by-part-of-a-name).

**Search** is a contains-match over the event type and the recorded details.
It does not look at names or addresses, for the same reason. It is not
indexed; on a large trail, set the dates first.

Some questions, and how to ask them:

- *What happened to this consent record?* Open the record; the **Audit
  trail** button on its page arrives here pre-filtered. The same button is on
  projects, notices and rights requests.
- *Everything about this data principal.* About: Data principal, her email or
  mobile in full.
- *What has this DCO done since Monday?* About: Member of staff, their email;
  From: Monday.
- *Every refused request last month.* Area: Sign-in and access; Event:
  Access denied; From and To.
- *Who touched this processor's sources?* About: Data source, the rig's
  name, one at a time; or Record type: Data source, Area: Data sources.
- *Find a rights request by reference.* Search: `RR-2026-000042`; every
  event about it carries the reference in its details.

## The summary

Above the list, the same filters produce counts: how many entries, over what
span, by area, the most common events, by the actor's role, and per day for
the last thirty. They are computed by the server over exactly the rows the
list would show, so the numbers and the page never disagree. Use them to see
the shape before reading rows: a spike of sign-in failures on one day, or a
data principal whose events are all withdrawals.

## Export

**Export CSV** downloads the rows the current filters select, newest first,
up to 10,000 of them, with the recorded details as JSON in one column and
every free-text cell neutralised against spreadsheet formulas. The download
is itself recorded in the trail, as `audit.exported`, with the filters used:
taking a copy of the evidence is an act on it.

## Verify chain

Recomputes the SHA-256 chain and names the first row that does not verify.
The 03:00 maintenance task does the same daily. A break is a page, not a
ticket; the runbook says what to do.

## What the trail does not answer

- **Reads.** Viewing a record is not written to the trail, except downloads
  of files and the trail itself. The access log holds reads.
- **The contents of a record.** The trail says what was done to which row by
  whom; the row itself says what it holds.
- **Anything before the platform.** The first entry is the first write.
- **Anything a person could ask to have erased.** The trail is the one
  store nothing can be removed from, so since 21 September 2026 nothing
  erasable goes in ([ADR 0015](../decisions/0015-nothing-erasable-in-a-trail-nobody-can-erase.md)):
  the person is named by id, the office's reasons stay in their own sealed
  rows, and the client address is written as its keyed hash. Rows from
  before that date still carry raw addresses and, on eleven of them, an
  email; the chain covers `detail_json`, so they stand as written.
- **"What was the address?"** The keyed hash answers "was this the same
  address as that?" and "did this address appear?", and nothing more. The
  page has no way to type an address in; an investigator computes its hash
  under `BLIND_INDEX_KEY` and searches the details for that.

## For the data principal

She reads the same rows, filtered to the events that concern her, on her
portal's notifications page. The office's working on her request is not
shown to her; the outcome is. The rule is `SUBJECT_VISIBLE` in the audit
repository.
