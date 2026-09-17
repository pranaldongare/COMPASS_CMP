# DPDP Act 2023 — implementation and gap assessment

**Assessment date:** 17 September 2026  
**Scope:** repository code and configuration at commit `77027b7`, not
undocumented organisational processes, contracts or production infrastructure.  
**Conclusion:** the product implements a strong consent ledger and substantial
data-principal-rights case management, but it is **not yet a complete DPDP
compliance system**. The highest-risk missing capabilities are breach response,
verifiable parental/guardian consent, execution of erasure and lifecycle rules,
and controls for cross-border processing.

This is an engineering assessment, not legal advice. Legal should confirm the
organisation's role, exemptions, designation as a Significant Data Fiduciary
(SDF), commencement notifications, and the rules in force for each deployment.

## Authority and method

The requirements are mapped to the enacted [Digital Personal Data Protection
Act, 2023 on India Code](https://www.indiacode.nic.in/handle/123456789/19698),
especially sections 4–17. The Act leaves formats, periods, exemptions and some
operational details to rules and government notifications. This review does not
turn a repository default into a statement of law. In particular, the configured
90-day response periods are product policy until Legal confirms the applicable
rule and commencement position.

Evidence ratings used below are **Implemented** (enforced code path and persisted
evidence), **Partial** (useful workflow but the statutory outcome is not assured),
**Not implemented**, and **Organisational / conditional** (not provable from code
or dependent on a designation, notification or factual determination).

## Executive gap register

| Priority | Gap | Act anchor | Current evidence | Required next outcome |
|---|---|---|---|---|
| **P0** | No personal-data-breach register, triage, affected-person population, or notification workflow | s.8(6) | Security logging and audit-chain verification exist, but no breach domain, schema, API, notification, or runbook was found | Create incident intake and immutable breach records; determine affected principals; record Board and individual notices, timestamps and evidence; add an operator runbook and exercises |
| **P0** | No verifiable parent/lawful-guardian consent | s.9(1) | Date of birth is stored and some minor purposes are blocked, but the consent service explicitly says parental consent is not collected; unknown age is allowed to proceed | Add guardian identity/authority verification, guardian-to-child linkage, notice service to guardian, consent/withdrawal evidence and ageing-out; fail closed where age/authority is unresolved |
| **P0** | Erasure and retention do not delete all applicable personal data | ss.8(7), 8(8), 12(3) | Rights scope changes junction dispositions; the retention task quarantines or counts `erase_due`; documentation says it does not perform deletion and backups are out of scope | Build an inventory-driven execution workflow for primary stores, uploaded objects, processor copies, derived data and backups, with legal holds, verification, retry and completion evidence |
| **P1** | Cross-border control is descriptive, not enforced | s.16 | A purpose has only a `cross_border_permitted` boolean; no destination, restricted-country list, transfer decision, or export guard uses it | Record destination and processor location; maintain the government restriction policy; block exports/transfers that fail it; preserve the decision and legal basis |
| **P1** | Correction/completion/updating is case management only | s.12(1)–(2) | A `correction` request type and ticket/response workflow exist, but no controlled mutation of authoritative records or propagation confirmation was found | Add field-level proposed/current values, authority routing, approvals, application to source records, processor propagation and proof returned to the principal |
| **P1** | Consent Manager interoperability is absent | s.6(7)–(9) | Consent is managed directly; no registered Consent Manager identity, protocol, request, receipt or revocation integration exists | Decide whether integrations are in scope; if so, add authenticated delegated requests and portable, auditable receipts and withdrawals |
| **P1** | Child safeguards are incomplete beyond consent | s.9(2)–(3) | A purpose flag controls whether minors may grant; a UI-only check objects to combining that flag with cross-border permission | Enforce a server-side child-risk assessment, detrimental-effect prohibition, and tracking/behavioural-monitoring/targeted-advertising prohibition for all processors and purposes |
| **P1** | General security safeguards are not evidenced end to end | s.8(5) | RBAC, sessions, rate limits, secure headers, append-only audit and integrity checks are strong; production encryption/key management, vulnerability management, restore tests, incident drills and processor assurance are not established here | Produce a control matrix and production evidence for encryption, keys, patching, scanning, backups/restore, monitoring, response tests and processor controls |
| **P1** | Purpose cessation and full retention schedules are not automated | ss.8(7)–(8) | The scheduled task acts only where `consent_validity_period` elapsed; `retention_period` and triggers such as purpose served/inactivity are registry metadata | Calculate every applicable cessation event, notify processors, stop processing, erase when required, and prove completion; cover accounts, contacts, messages, audit exceptions and uploaded files |
| **P2** | Accuracy/completeness/consistency control is not explicit before decisions or disclosure | s.8(3) | Import validation and correction tickets help, but no general pre-decision/pre-disclosure quality gate or attestation was found | Define material decisions/disclosures and enforce validation, provenance, conflict resolution and approval before each |
| **P2** | Processor contracts and oversight are represented only minimally | ss.8(1)–(2), 8(5)–(8) | Processor records contain a contract reference and `security_confirmed_at`; ticketing can ask processors to act | Version agreements and instructions, locations/sub-processors, safeguards, incidents, deletion/return duties, assurance reviews and termination evidence |
| **P2** | SDF obligations have no dedicated workflow | s.10 | No India-based DPO appointment register, independent auditor record, DPIA, periodic audit or due-date workflow was found | If designated as an SDF, add governance evidence and recurring DPIA/audit/remediation workflows; otherwise document non-applicability and monitor designation |
| **P2** | Statutory configuration has no legal-version register | ss.40, 1(2) and dependent provisions | Legal assumptions are embedded in comments, defaults and fixed enums | Record jurisdictional policy version, effective dates, source notification, approvals and migration impact; make changing statutory periods/policies auditable |

## Requirement-by-requirement assessment

### Sections 4 and 7 — lawful processing and certain legitimate uses: **Partial**

Purposes store a lawful basis and a section 7 classification, and the database
requires a section 7 clause when `legitimate_use_s7` is chosen. This is useful
inventory evidence. It is not a full legality control: the enum includes a
generic `s7_other`, no workflow proves the facts required by the chosen clause
or periodically revalidates them, and processing outside consent/export paths is
not centrally gated against the registry.

**Close by:** use only Legal-approved clauses, attach evidence and review dates,
and require an active lawful-purpose decision at every collection, disclosure
and processor-export boundary.

### Sections 5 and 6 — notice and consent: **Largely implemented, with gaps**

Implemented controls include versioned multilingual notices; approval and
publication; immutable published text and hashes; server-stamped proof that
notice preceded affirmative action; explicit answers for every purpose;
purpose-granular grants; withdrawal artefacts linked to earlier consent; and
withdrawal, rights and Board routes in the notice model.

Remaining gaps are material. Mandatory purposes can be configured in a
consent-based notice, risking conditional rather than freely given consent
unless they are genuinely separate section 7 processing. Withdrawal is
recorded, but cessation and erasure across processors are not assured. There is
no external Consent Manager interface. The fixed language list does not prove
that every language required for a deployment is available. Existing data is
not covered by a campaign proving that a required later notice was supplied.

### Section 8 — general obligations of a Data Fiduciary: **Partial**

Strong evidence includes processor and data-source registries, purpose/retention
metadata, disclosure/export lines, processor respondents, transactional audit
records, hash-chain verification, least-privilege roles, session and OTP
protection, rate limiting, file hashing, and structured rights workflows.

Unmet outcomes are breach notification, complete lifecycle execution,
production security assurance, data-quality gates before material decisions or
disclosures, and complete processor oversight. A notice carries DPO contact and
grievance/Board routes, but code cannot establish that the deployed contact is a
real accountable person or that requests received outside the application enter
the same workflow.

### Section 9 — processing children's data: **Not compliant end to end**

The implementation correctly derives under-18 status and does not silently call
an unknown age “adult.” It blocks a known minor from granting a purpose not
marked for minors. However, a purpose marked for minors can be granted directly
by the child without verifiable parental consent. The code documents this
limitation. A legacy or consent-link account may have unknown age and can grant.

There is no enforceable model for parental authority, guardian withdrawal,
detrimental effects, tracking/behavioural monitoring or targeted advertising.
The internal UI's cross-border/minor refinement is not a backend boundary and
can be bypassed by an API client.

### Section 10 — Significant Data Fiduciaries: **Conditional; not implemented**

The ordinary `dpo` role and project approvals are not substitutes for SDF
requirements. If notified as an SDF, repository evidence is missing for an
India-based DPO responsible to the governing body, independent data auditor,
periodic DPIAs, periodic audits, and tracked remediation. Legal must own the
designation decision; the product should preserve evidence and deadlines.

### Section 11 — access: **Substantially implemented**

The workflow receives a request, verifies identity, discovers internal and
processor holders, issues tickets, collates responses and produces a downloadable
package containing consent, notice, disclosure and holder-return information. It
supports partial responses without falsely calling them complete.

Validate the package against information prescribed by current rules and test
completeness against every production store. “No record” and partial responses
need sampled assurance, not only a successful workflow transition.

### Section 12 — correction, completion, updating and erasure: **Partial**

Erasure distinguishes deletion, redaction, retention floor and quarantine. It
changes relationship/disposition records and tickets external holders but does
not itself remove the underlying asset. Correction has the same weakness: a case
can close without a structured, verifiable update to each authoritative source.
Do not report completion until each system returns execution evidence or the
response clearly records a lawful exception.

### Section 13 — grievance redressal: **Substantially implemented**

The platform supports grievance requests and a response clock, links a grievance
to the disputed request, separates a grievance about the DPO from the DPO,
records decisions/remedies, and provides the Board route. Confirm the deployed
period, escalation text and Board URL against current rules, and ensure email,
paper and help-desk grievances enter the same clock.

### Section 14 — nomination: **Substantially implemented**

The principal can nominate, the nominee accepts using a recorded contact, the
principal can revoke, and invocation for death or incapacity is recorded. The
DPO records trigger evidence. The legal standard for that evidence remains an
open organisational decision and should be published, versioned and tested.

### Sections 15–17 — principal duties, cross-border processing and exemptions: **Partial / organisational**

Authentication, anti-enumeration and audit trails help investigate impersonation
and abuse, but principal duties do not justify blocking a genuine request without
a reviewed policy. Cross-border metadata is not enforcement. Exemptions and
legal holds need approved, reasoned decisions with scope and expiry; a generic
retention basis or free-text response is not sufficient by itself.

## Existing capability map

| Capability present | Contribution | Limitation |
|---|---|---|
| Purpose registry and notice builder | Purpose, categories, lawful basis, retention, processors and rendered notice | Several fields are descriptive rather than runtime gates |
| Consent artefact and purpose grants | Notice, affirmative action, grant/refusal and withdrawal evidence | Processor cessation and erasure are not automatically completed |
| Disclosure/export ledger | Identifies recipients for access and erasure discovery | Cross-border destination/policy is absent |
| Data asset and subject junctions | Reverse lookup and person-specific dispositions | Underlying bytes are not erased/redacted by the workflow |
| Rights request/ticket state machine | Access, correction, erasure, grievance, nomination, clocks and evidence exchange | Correction/erasure execution remains external or manual |
| Audit chain | Transactional, append-only accountability with daily verification | Not a breach-management system |
| RBAC, sessions, OTP and rate limits | Application-level access safeguards | Does not evidence infrastructure and operational safeguards |
| Scheduled maintenance | Expired links, retention quarantine, audit verification and stale-request handling | Retention coverage and execution are incomplete |

## Remediation sequence

### 0–30 days: prevent false assurance

1. Assign Legal, Privacy, Security and Engineering owners to every P0/P1 item.
2. Ensure `closed` never implies source data was corrected/erased unless
   execution evidence exists.
3. Disable known-minor consent capture until a guardian flow exists; decide a
   fail-closed migration path for unknown ages before further processing.
4. Establish a manual breach runbook immediately, with current statutory
   contacts and escalation times.
5. Inventory all stores and processors, including backups, logs, outboxes,
   object storage and analytics—not merely PostgreSQL entities.

### 31–90 days: close statutory-operation gaps

1. Deliver breach management and notification evidence.
2. Deliver the guardian/child model and server-side child safeguards.
3. Add correction and erasure execution adapters, acknowledgements and retries.
4. Implement lifecycle events from purpose cessation, withdrawal, inactivity and
   retention expiry, including legal holds and processor propagation.
5. Enforce cross-border destination policy at disclosure/export time.

### 91–180 days: assurance and governance

1. Complete the security-control evidence matrix and conduct restore and breach
   exercises.
2. Version processor contracts/assessments and statutory configuration.
3. Add Consent Manager interoperability if the operating model requires it.
4. Add SDF workflows if designated, or retain an approved non-applicability
   assessment and designation-monitoring owner.
5. Run reconciliation tests: sample a principal and prove the notice,
   consent/lawful basis, copies/disclosures, rights response and disposition agree.

## Definition of “gap closed”

A checkbox or database column is not sufficient. An item closes only when there
is an enforced path, tests for refusal and failure, persisted evidence, an
operator runbook, monitoring, a named organisational owner, and Legal approval
of the interpretation applied by that path.
