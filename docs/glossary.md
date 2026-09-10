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

**Cover (delegation).** One member of staff standing in for another for a
period, without handing over the job. The rows the delegator is assigned to
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
asset: active, erased, redacted, retained, quarantined.

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
appended to instead of being sent: `cmp_backend/var/outbox.log`. Where
one-time codes and acceptance links are read from during development and
browser tests.

**Partial session.** The state between a correct password and the second
factor. It authorises the MFA verification route and nothing else.

**Audit trail.** The append-only, SHA-256 hash-chained log of every write, in
the same transaction as the write. `GET /audit/verify` names the first row
that does not verify.

**Scope.** Which rows a role may see, compiled into the SQL `WHERE` clause:
`ALL`, `SCOPED` (assigned to them), `OWN` (theirs or about them), `NONE`. A row
outside scope is a 404, never a 403.
