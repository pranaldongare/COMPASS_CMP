# Roles and access

Seven roles. Six are staff and sign in on the console with a password and an
emailed code; the seventh is the data principal, who signs in on the portal
with a code alone. What each may reach is a static matrix in
`cmp_backend/src/cmp/core/permissions.py`, consulted before any work is done,
and the rows each may see are a scope compiled into every query.

## The roles

| Role | Enum value | Who they are | What they mainly do |
|---|---|---|---|
| Data Protection Officer | `dpo` | The Privacy Office | Approves projects, publishes notices, sees every register, runs the rights queue, reads the audit trail |
| Administrator | `admin` | Provisions the platform | Creates accounts and assigns roles, sees the audit trail, arranges cover for anyone, edits the words of every message the platform sends, and is the independent reviewer for a grievance about the DPO |
| Data Collection Owner | `dco` | Accountable for a third party's collection | Registers data sources and sites under their processors, mints and replaces consent links, exports and imports, answers tickets addressed to them |
| DCO Admin | `dco_admin` | Routes third-party collection | Receives an approved project that names a third-party processor, attaches sources, registers sites and names who runs them |
| Research Collection Owner | `rco` | A DCO for in-house collection | The same as a DCO, restricted to the organisation's own sources and sites |
| R&D User | `rnd_user` | Owns a study | Registers the project, names purposes and collectors, authors the notice, uploads approval proofs, asks to add a collector after approval |
| Data principal | `data_subject` | The person the data is about | Reads and withdraws her consents, sees her disclosures, makes and follows rights requests, names a nominee |

## The matrix

Each cell is a scope, and `+w` means the role may also write. A blank cell is
denied: no wildcard, no inheritance.

| Resource | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal |
|---|---|---|---|---|---|---|---|
| user | all | all +w | | | | | |
| purpose | all +w | all | all | all | all | all | |
| processor | all +w | all +w | all | all | all | all | |
| data_source | all +w | all +w | all +w | all +w | all +w | all | |
| project | all +w | | scoped +w | scoped +w | scoped +w | own +w | |
| approval | all | | scoped | scoped | scoped | own +w | |
| site | all +w | | scoped +w | scoped +w | scoped +w | own | |
| notice | all +w | | scoped | scoped | scoped | own +w | |
| link | all +w | | scoped +w | scoped +w | scoped +w | | |
| consent | all | | scoped | scoped | scoped | own | |
| export | all +w | | scoped +w | scoped +w | scoped +w | | |
| import | all +w | | scoped +w | scoped +w | scoped +w | own | |
| collection | all | | scoped | scoped | scoped | own | |
| asset | all | | scoped | scoped | scoped | own | |
| audit | all | all | | | | | |
| message_template | all +w | all +w | | | | | |
| rights_request | all +w | scoped +w | | | | | |
| ticket | own +w | own +w | own +w | own +w | own +w | own +w | |
| me | | | | | | | own +w |

Where a cell says "own" for the R&D user, it means the projects they created
and everything hanging off them. "Scoped" for a collection owner means the
projects and sites they are the owner of, resolved through the site's owner
override or its source's owner - and, for a period of cover, the rows of the
colleague they are covering for. The administrator's scope on rights requests
is exactly the grievances escalated to them.

| Scope | Means |
|---|---|
| `ALL` | every row |
| `SCOPED` | rows assigned to them |
| `OWN` | rows they created or that are about them |
| `NONE` | no rows |

A row outside scope is never selected, so it answers 404. 403 is reserved for
a row the caller can see but may not act on, and is audited. The reasoning is
in [ADR 0004](../decisions/0004-scope-in-the-where-clause.md).

## Navigation

The console draws its navigation from `GET /auth/me`, which returns the
sections the server computed for the role. The client holds no copy of the
matrix, so it cannot drift into showing a button that answers 403.

| Role | Sections |
|---|---|
| DPO | dashboard, projects, approvals, notices, purposes, sites, collections, processors, sources, consents, links, exports, imports, requests, audit, users, messages, delegate, tickets, notifications, profile |
| Administrator | dashboard, users, messages, processors, sources, requests, audit, delegate, tickets, notifications, profile |
| DCO, DCO Admin, RCO | dashboard, projects, sites, sources, links, consents, exports, imports, collections, delegate, tickets, notifications, profile |
| R&D User | dashboard, projects, notices, processors, approvals, imports, collections, tickets, notifications, profile |
| Data principal | consents, requests, notifications, profile |

Tickets are in every staff role's navigation, because any staff account can
be named a respondent; the page is empty until one is addressed to them.
Since September 2026 the cover section is labelled **Delegate**.

## Staff are data principals too

Every account may act as a data principal, a member of staff's included. On
the data-principal portal and through a consent link, a one-time code to any
registered contact signs its owner in — and the session it earns **acts as
`data_subject` whatever the account's role**. The permission matrix,
navigation and every gate read the session, so a DPO signed in on the portal
sees her own consents, requests and rights and is refused everything else. The
row is untouched; the session records `account_role` so the portal can say
"you are using your staff account as a data principal". A password and code on
the console are what buy the staff role. See
[ADR 0013](../decisions/0013-every-account-is-a-data-principal.md), which also
records the bypass this closed.

**Deactivating a member of staff ends the role and keeps the person.** The
register's button reads "End staff access" for a staff row: the role becomes
`data_subject`, the password goes, `person_type` becomes `ex_employee`, and the
account stays active so they still reach the consents they gave and the rights
they hold. A data principal's account, having nothing to be kept as, is
switched off as before.

**A person may add a second email and a mobile** from the account page —
either portal's, since the account is the same one. Each is confirmed by a
code sent to it, and until the code comes back it cannot sign anyone in — a
typed contact is a claim, and a claim is not a way in. An address belongs to
one account whichever column holds it. A member of staff who wants to keep
reaching their own consents after leaving adds a personal address while the
corporate one still works.

**An administrator may set somebody's mobile** on the register, and the number
is sent a code the same way: the person learns it is on their account and
confirms it from their account page, and until they do it signs nobody in. The
code lasts `STAFF_INVITE_TTL_H` hours rather than ten minutes, because nobody
is waiting at a code box for it, and it is withheld rather than the edit
refused if that number's hourly quota is already spent.

The routes this rests on — `GET`/`PATCH /me`, `POST /me/contacts/code`,
`POST /me/contact/verify`, `DELETE /me/secondary-email`, `POST /me/person-type`
— admit any signed-in session rather than a data principal's alone: the person
is the same on both portals, and their contacts are theirs to confirm from
either. The rest of `/me` — consents, requests, disclosures, notifications — is
the data principal's surface and stays gated.

## How a staff account begins

There is no self-registration. An administrator provisions the account, which
is created `pending` and holds a random password nobody knows — an initial
password sent by email would be a live credential sitting in a mailbox.

Creating it sends an invitation to the address on the account: the role in
words, a link to the console's reset page with the address already filled in,
and a six-digit code that lasts `STAFF_INVITE_TTL_H` hours. Setting a password
with that code is what activates the account, and until then sign-in refuses
it. If the invitation expires, "Forgotten your password?" sends a working
replacement, because the invitation carries the reset flow's own code rather
than a second kind; an administrator can also send it again from the register,
but only while the account is still pending.

## What the dashboard asks of each role

Each role's landing page opens with **Needs you today**: counts of things
that role can act on, from the page each row opens. The rule is strict, and
tested: a count the role can only look at is not on the list. Lockouts
clear themselves; a suspended source was suspended on purpose; a draft
notice is its author's to finish; refusals in the log are the audit trail's.
Those stay in the queues and statistics further down.

| Role | Needs you today |
|---|---|
| DPO | tickets past their date; rights requests overdue and due within seven days; requests awaiting verification; teams that have written on their tickets; grievances about the DPO not yet escalated; retention floors passed; tickets addressed to them; translations awaiting approval; projects pending approval; new collectors awaiting a decision |
| Administrator | staff invitations not yet accepted (resend them); grievances about the DPO to review; tickets addressed to them |
| DCO, RCO | tickets past their date; tickets addressed to them; imports that did not reconcile; assets with unmapped subjects |
| DCO Admin | tickets past their date; sites awaiting a data source; sources with nobody accountable; processors with no collection set up; tickets addressed to them |
| R&D User | projects needing something from them; tickets addressed to them |

A data principal who has not finished her own sign-up is not the
administrator's to activate, so she is not counted; a grievance about the
DPO that has been escalated is the administrator's, so the DPO no longer
sees it.

## Second factors

Every staff role signs in with a password and then a six-digit code sent to
the account's email, for five minutes and five attempts. The list is
`MFA_REQUIRED_ROLES`, derived from the role enum by default so that a role
added later is covered on arrival; a deployment may narrow it and answers for
that. Data principals have no password: their sign-in *is* a code, to the
mobile or the email they chose. See
[ADR 0006](../decisions/0006-mfa-for-every-staff-role.md).

## Delegation

The console calls it **Delegate**. A member of staff arranges cover for a period: a delegate who then sees and
acts on the delegator's rows for that period only, in their own name, with
every action audited as theirs. Cover ends at the end of the period or when
either party ends it. The administrator can arrange it for anyone; nobody can
arrange cover that widens what the delegator themselves could do.

## How the matrix is kept honest

- `auth/authorization/permissions.py` asserts at import that the resource
  roster and the matrix agree in both directions; the process fails to start
  otherwise.
- `tests/security/test_matrix_integrity.py` holds the invariants: no
  resource names a role twice, a data principal cannot touch the registry,
  staff is everyone who is not a data principal.
- `tests/security/test_bola.py` and its neighbours walk uuids across scopes
  and expect 404, never a row.
