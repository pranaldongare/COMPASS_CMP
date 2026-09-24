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

**Staff.** Every role except the data principal. Staff sign in with a password
and then a code sent to their email.

**Nominee.** A person a data principal names, while well, to exercise her
rights if she dies or cannot act (s.14). Named by mobile with an optional
email; must accept through a link and a code before the nomination is in
effect.

**Respondent.** The person who answers a holder's ticket for a processor. For
an in-house processor a respondent is an account on the platform and the
ticket reaches them in the console; for a third party it is a name and an
address, reached by email.

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
principal reaches a site's notice. Minted for a site, tied to a notice
version, expiring, replaceable ("remint"), and never derivable from the
database, which stores only its fingerprint.

## Notices and consent

**Notice.** What the data principal is shown before she decides: the project,
the purposes, the data categories, retention, her rights. Versioned; frozen on
publication; one rendition per language, each approved before it can be
served.

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
the holder's copy by its returned ticket, and for an erasure the platform's
pointer to the asset cleared. Recorded as `executed_at`, from the append-only
attempts in `rights_item_execution`. Applied is not executed.

**Legal hold.** A record that stops erasure of one asset, or of everything
about one person, until the DPO releases it. Placed once, released once, with
a sealed reason; an item it covers records `held` and goes no further.

## Rights

**Rights request.** A record with a clock, of type access, correction, erasure
or grievance (ss.11 to 13), received from the portal, the public form, a
nominee, or logged by the DPO from an email. Identified by a reference like
`RR-2026-000042`.

**D0 and D.** Receipt, and the published response period after it (90 days by
default, the Rule 14 limit). The checkpoints between them - acknowledge,
tickets issued, halfway, collate - are computed from the two.

**Holder.** A party that holds the person's data: derived from exports and
assets, confirmed by the DPO. One ticket per holder.

**Ticket.** The instruction to a holder to return what it holds, and the
**thread** on which the holder and the Privacy Office write to each other.
Travels by the console for an in-house respondent and by email for a third
party. Can be returned, sent back, withdrawn, reassigned, reminded and, if the
date is missed, escalated once.

**Scope item.** For an erasure, one row per appearance of the person in an
asset, each decided: erase, redact, retain or quarantine.

**Grievance.** A complaint (s.13), usually about how a request was handled;
linked to that request. A grievance about the DPO is escalated to the
administrator, who names an independent reviewer.

**Board.** The Data Protection Board of India, the route beyond the fiduciary.
Named in every response that does not uphold what was asked.

## Platform

**Junction.** A named moment at which the platform writes to a person: a
sign-in code, a consent receipt, a ticket. Each has default words per channel
that the administrator or the DPO may replace from the console's Messages
page. See [messages.md](domain/messages.md).

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
