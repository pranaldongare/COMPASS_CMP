# Glossary

The vocabulary of the Act, and of this platform. Where the platform's word
differs from the Act's, both are given.

## People and roles

**Data fiduciary.** The organisation deciding why and how personal data is
processed; the operator of this platform. The Act's term.

**Data principal.** The person the personal data is about. The platform's
code and older documents also say *data subject*; the role enum value is
`data_subject`. She has no password: her sign-in is a one-time code to her
mobile or email.

**Data Protection Officer (DPO).** Oversees every project, publishes notices,
approves projects, runs the rights queue, and reads the audit trail. Role
`dpo`.

**Administrator.** Provisions accounts and roles, sees the audit trail, and is
the independent reviewer for a grievance about the DPO. Role `admin`.

**Data Collection Owner (DCO).** Accountable for collection at a third party's
sites: registers rigs and sites, mints consent links, exports and imports.
Role `dco`.

**DCO Admin.** Routes third-party collection: an approved project naming a
third-party processor lands with them to assign sources and sites. Role
`dco_admin`.

**Research Collection Owner (RCO).** A DCO for collection the organisation
does itself, in-house. Role `rco`.

**R&D User.** Registers a project, states its purposes, names its collectors,
authors its notice, and uploads approval proofs. Role `rnd_user`.

**Staff.** Every role except the data principal and the temporary ticket
holder. Staff sign in with a password and then a code sent to their email.

**Temporary ticket holder (`breach_holder`).** Somebody inside the
organisation with no console login, asked to act on a breach or, since 0049,
to answer a rights ticket, who is given one for it: they sign in like staff, but reach only the tickets addressed to them,
notifications and their profile. Never given by hand; see *temporary access*.

**Nominee.** A person a data principal names, while well, to exercise her
rights if she dies or cannot act (s.14). Named by mobile with an optional
email; must accept through a link and a code before the nomination is in
effect.

**Respondent.** The person who answers a holder's ticket for a processor. For
an in-house processor a respondent is an account on the platform and the
ticket reaches them in the console; an address on the organisation's own
domains with no login is given a temporary login for it. For a third party it
is a name and an address, sent a link to the portal and a one-time code to
open the ticket there.

**Delegation (Delegate, in the console).** One member of staff standing in
for another for a period, without handing over the job. The rows the delegator is assigned to
become visible to the delegate for that period.

## Registry

**Purpose.** One reason for processing, with its lawful basis, data
categories, retention period and erasure trigger. Consent is recorded against
purposes, never in aggregate.

**Processor.** A party that collects or handles data: a third-party lab or a
team of the fiduciary's own (`is_in_house`). A project names its processors;
the DPO decides each.

**Data source.** A rig, device or system that captures data, belonging to one
processor and owned by one person. A site is a source standing somewhere.

## Projects and collection

**Project.** The unit of governance: a study or programme with purposes,
processors, a notice and an approval. States: `in_draft`,
`pending_approval`, `approved`, `closed` (`under_process` survives as a
historical value).

**Approval.** The DPO's decision on a project, with the proofs an R&D user
uploaded (security, ethics, and so on).

**Collection site.** Where a source is deployed for a project. Its owner - the
source's owner, or a named override for this site - is who the project follows
and who may mint consent links for it.

**Consent link.** A capability URL, `/c/{token}`, through which a data
principal reaches a site's notice. Minted for a site, expiring, replaceable
("remint"), and never derivable from the database, which stores only its
fingerprint. It serves the notice in force: publishing a new notice moves
every live link to it, and a consent already given keeps the notice it was
given under.

## Notices and consent

**Notice.** What the data principal is shown before she decides: the project,
the purposes, the data categories, retention, her rights. Versioned; frozen on
publication; one rendition per language, each approved before it can be
served.

**Notice template.** A notice the DPO writes before a project exists, with an
ID like `TPL-0007` (0044). The R&D User attaches it with **Use a notice
template**, which makes the project's own draft notice from it, approved and
published like any other. Nothing on a template is approved or served, and a
change to it changes no notice made from it. A template is retired, never
deleted; a retired one cannot be used.

**Consent artefact.** The record of one decision on one notice: which purposes
were granted and which refused, one grant row each, with the hash of the exact
text she was served and the moment it was served. Append-only.

**Withdrawal.** A new artefact that supersedes an earlier one. The earlier
record is never edited; the supersession chain is the history.

**Consent status.** Derived on every read, never stored: `consented`,
`partial`, `declined` or `withdrawn`, from the grants of the artefact currently
in force.

## Exchange

**Export.** A file leaving the platform to a processor, with a **disclosure
record** naming every person in it - the basis of "who was my data shared
with" (s.11(1)(b)).

**Import batch.** A manifest of collected assets arriving from a source,
validated dry before it is written, upserted on the source's own reference.

**Collection.** The set of assets a site collected under a project, reconciled
against consents.

**Data asset.** One collected thing - a recording, an image - that may hold
more than one person.

**Asset consent.** The junction row saying which consent covers which person
in which asset. A **bystander** is a row with no consent: somebody in frame
who never agreed, kept visible precisely so they can be dealt with.

**Disposition.** What has been decided about a person's appearance in an
asset: active, erased, redacted, retained, quarantined. Since S2-03 it reads
erased or redacted only once the item is **executed**; until then an applied
erasure reads quarantined.

**Executed (erasure).** A scope item whose every store has been confirmed:
the holder's copy by its answer saying it did all of it, once the DPO has
accepted it, and for an erasure the platform's
pointer to the asset cleared. Recorded as `executed_at`, from the append-only
attempts in `rights_item_execution`. Applied is not executed.

**Destination (export).** Where an export row goes: the processor running the
site the consent was given at, and that processor's country. Recorded on each
`export_line` (S2-04).

**Restricted country.** A country the Government has notified under s.16 that
personal data may not be transferred to. Kept as data by the Privacy Office
(`/restricted-countries`), listed once and lifted once; an export with a row
going there is refused.

**Legal hold.** A record that stops erasure of one asset, or of everything
about one person, until the DPO releases it. Placed once, released once, with
a sealed reason; an item it covers records `held` and goes no further.

## Rights

**Rights request.** A record with a clock, of type access, erasure or
grievance (ss.11 to 13), about everything held on her, never one project or
consent. Received from the portal, the public form, a nominee, or logged by
the DPO from an email. Identified by a reference like `RR-2026-000042`. Since
2026-10-07 a correction is not a request: she corrects her name from her
account. Requests of type correction made before then are handled as they
were.

**Request documents.** Files the data principal sends with her own request -
a proof of who she is, a letter, a screenshot (`rights_request_attachment`,
0043). Up to ten, while the request is open; kept as they came, never
replaced or removed.

**D0 and D.** Receipt, and the published response period after it (90 days by
default, the Rule 14 limit). The checkpoints between them - acknowledge,
tickets issued, halfway, collate - are computed from the two.

**Holder.** A party that holds the person's data: derived from exports and
assets, confirmed by the DPO. One ticket per holder.

**Ticket.** The instruction to a holder to return what it holds, and the
**thread** on which the holder and the Privacy Office write to each other.
Reaches a holder with a console login in My tasks, one inside the
organisation with no login through a temporary login, and anyone else by a
link to the portal opened with a one-time code (see *holder link*). Can be
sent back, withdrawn and reopened, reassigned, reminded, and given a final
reminder once overdue. An answer counts only once the Privacy Office accepts
it (see *review*).

**Holder link.** How a holder outside the organisation reaches its ticket
(0049): a link to the portal, `/ticket/{token}`, which shows nothing of the
request. A one-time code, sent only to the address on the ticket, opens that
ticket for an hour. A ticket sent to somebody else gets a new link and the old
one stops working.

**Review (accept).** A holder's answer arrives as *Answered - review*. The DPO
accepts it or sends it back, and only an accepted answer counts toward
closing the request or toward an erasure being executed (`accepted_at`,
0048). An answer the office records on a holder's behalf is accepted as it
is recorded.

**Scope item.** For an erasure, one row per appearance of the person in an
asset, each decided: erase, redact, retain or quarantine.

**Grievance.** A complaint (s.13), usually about how a request was handled;
linked to that request. A grievance about the DPO is escalated to the
administrator, who names an independent reviewer.

**Board.** The Data Protection Board of India, the route beyond the fiduciary.
Named in every response that does not uphold what was asked.

## Breaches

**Personal data breach.** Section 2(u): any unauthorised processing of
personal data, or accidental disclosure, acquisition, sharing, use,
alteration, destruction or loss of access to it, that compromises its
confidentiality, integrity or availability. Whether an event is one is a
person's **validation** (the *determination* in the code) - *pending*, *yes* or
*no*, with reasoning - which the platform records and never computes, least of
all from encryption.

**Incident.** An event logged on the register as it was noticed, before anyone
has validated whether it is a personal data breach. It becomes a recorded
breach on the first validation of *yes* ([ADR 0022](decisions/0022-an-incident-first-and-a-breach-on-a-yes.md)).

**Incident reference.** `INC-YYYY-NNNN`, issued when an incident is logged and
quoted until it is recorded as a breach. An incident logged before October
2026 carries the `BR-` string it was given.

**Breach reference.** `BR-YYYY-NNNN`, issued once by the first validation of
*yes* and never withdrawn. It is what principals and the Board are given, and
BR numbers count recorded breaches only.

**Detected, became aware, began.** Three times on a breach, kept apart and
entered by the DPO. *Detected* is when it was first noticed and starts the
CERT-In clock; *became aware* is when the organisation knew a personal data
breach had occurred, is recorded with a validation of *yes*, and starts
every DPDP clock; *began* is when it started, if known.

**Duty (obligation).** One statutory obligation a breach creates, with its own
clock: CERT-In in six hours from detection; the Board's initial intimation and
the notices to principals **without delay**; the Board's detailed report in 72
hours from awareness or the date the Board allows. A due time is stored when the
duty is created and never recomputed; what happens afterwards - done, not
applicable, reinstated, extended - is a new row.

**Without delay.** Rule 7's words for the Board's initial intimation and the
notices to principals. There are no statutory hours, so the duty has no due
time: the register shows the time since awareness, flagged against an internal
target (`BREACH_WITHOUT_DELAY_TARGET_HOURS`) once Legal sets one.

**Organisation's board.** The organisation's own board, which internal policy
says hears of every incident within 30 minutes of its being first noticed
(`BREACH_ORG_BOARD_MINUTES`). A duty on every incident from logging; a person
reports, and the DPO records when and to whom. Not a regulator, and not a DPDP
duty: validation never touches it.

**Breach ticket holder.** The person a breach ticket is addressed to: a member
of staff, or a temporary ticket holder. They see the breach reference, what
they are asked, the thread and the state - nothing else from the register -
and can bring in a colleague, who gets a ticket of their own. Not a rights
request's *holder*, which is a party holding the person's data.

**Breach contact.** Somebody a breach touched who has no account, named in a
list sent to the Privacy Office (`breach_contact`, 0045). Told by email and
SMS, with nothing in an account to point to, and counted toward *Principals
notified* like everyone else listed.

**Temporary access.** A temporary login: one grant of the `breach_holder`
role for one breach or one rights ticket, to an address on the organisation's
own domains. A breach grant ends when the breach closes or the DPO withdraws
that person's ticket; a rights grant ends when the request closes, or the
ticket is withdrawn or sent to somebody else. The login stays, read only, so
they can still read their ticket. An administrator's End temporary access
removes the login: an account made for a ticket is switched off, and one that
was a data principal's goes back to being one.

**CERT-In.** The Indian Computer Emergency Response Team. Its Directions of
April 2022, under IT Act s.70B, require a reportable cyber incident to be
reported within six hours of noticing it - in force now, and parallel to DPDP.

## Platform

**Junction.** A named moment at which the platform writes to a person: a
sign-in code, a consent receipt, a ticket. Each has default words per channel
that the administrator or the DPO may replace from the console's Message
templates page. See [messages.md](domain/messages.md).

**Copy to.** Up to five addresses an email is copied to, set per message in
Message templates (`message_copy`, 0046). Only messages between the office
and its staff or holders can be copied; never one that carries a code or a
link, or a person's own record.

**Outbox.** In local and test environments, the file every email and SMS is
appended to instead of being sent: `backend/api/var/outbox.log`. Where
one-time codes and acceptance links are read from during development and
browser tests.

**Partial session.** The state between a correct password and the second
factor. It authorises the MFA verification route and nothing else.

**Audit trail.** The append-only, SHA-256 hash-chained log of every write, in
the same transaction as the write. `GET /audit/verify` names the first row
that does not verify. Read on the console by person, record, area, event and
period; see [audit-trail.md](domain/audit-trail.md). Nothing erasable goes into
it: a person is named by id, the client's address is written as its keyed
hash, and where a reason was given the entry says `reason_given: true` while
the words stay in their own sealed column
([ADR 0015](decisions/0015-nothing-erasable-in-a-trail-nobody-can-erase.md)).
Rows written before 21 September 2026 still carry raw addresses and cannot be
rewritten.

**Scope.** Which rows a role may see, compiled into the SQL `WHERE` clause:
`ALL`, `SCOPED` (assigned to them), `OWN` (theirs or about them), `NONE`. A row
outside scope is a 404, never a 403.

## Encryption

**Key service (DKMS).** The separate process, `backend/dkms` on port 32688,
that holds the key personal fields are encrypted under. The API seals through
it, the worker opens a recipient's contact through it, and each portal's
server opens responses through it. No browser ever reaches it. See
[docs/dkms/](dkms/README.md) and
[ADR 0016](decisions/0016-personal-data-sealed-by-a-separate-key-service.md).

**Sealed.** Encrypted by the key service, before the database sees it. A sealed
value is a string starting `SE::`, and it is different every time the same
value is sealed. The API stores and serves personal fields sealed.

**Open.** Turn a sealed value back into plaintext. A portal opens a response in
its own server route, `/dkms/decrypt`; the backend opens a value only to act on
it - send a code, write a CSV - and never into a response. In the code,
`unseal` and `opened`.

**Data type.** What the key service is told a field is when it seals it:
`NAME`, `EMAIL`, `MOBILE`, `CONTACT`, `DOB`, `FREE_TEXT` and so on. The type is
written into the sealed value, and a value opens only under the type it was
sealed as. The list is `DataType` in `infrastructure/dkms/fields.py`.

**Keyed hash (blind index).** `HMAC-SHA256` of a normalised value, kept in a
`<column>_hash` column beside a sealed column the platform finds rows by: an
email, a mobile, a username, a contact. The same value always gives the same
hash, so it can be compared and uniquely indexed; without the key it cannot be
reversed or guessed at. See
[ADR 0017](decisions/0017-lookup-by-keyed-hash-and-name-ngrams.md).

**`BLIND_INDEX_KEY`.** The key the keyed hashes are computed under, in the API.
It must equal `DKMS_HASH_KEY` in the key service: the API computes the hashes
itself, so sign-in survives the key service being down, and the key service
computes the same ones for any other caller. Separate from the key that seals.

**N-gram search.** Finding a sealed name by part of it. The name is cut into
overlapping runs of three characters, each run is hashed like a keyed hash,
and the set is kept in `<column>_ngrams`. A search term needs three characters
or more, and matches rows whose set holds every run of it. Only three name
columns carry one, because a set of runs leaks more than a single hash.

**Reseal.** `backend/api/scripts/reseal.py`: seal the values written before a
column was sealed, and recompute the keyed hash beside each. A row already
sealed is skipped, so it can run at any time; `--check` only reports.

**`minor_until`.** The date a person turns eighteen, kept in the clear beside a
sealed date of birth, because the s.9 test is a date comparison in SQL and a
sealed date cannot be compared.
