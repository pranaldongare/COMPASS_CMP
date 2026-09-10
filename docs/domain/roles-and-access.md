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
| DPO | dashboard, projects, approvals, notices, purposes, sites, collections, processors, sources, links, consents, exports, imports, requests, audit, users, messages, cover, notifications, profile |
| Administrator | dashboard, users, messages, processors, sources, requests, audit, cover, notifications, profile |
| DCO, DCO Admin, RCO | dashboard, projects, sites, sources, links, consents, exports, imports, collections, cover, notifications, profile |
| R&D User | dashboard, projects, notices, processors, approvals, imports, collections, notifications, profile |
| Data principal | consents, requests, notifications, profile |

Tickets reach a respondent through their dashboard and the console's tickets
page; the section is not in the navigation because most staff never hold one.

## Second factors

Every staff role signs in with a password and then a six-digit code sent to
the account's email, for five minutes and five attempts. The list is
`MFA_REQUIRED_ROLES`, derived from the role enum by default so that a role
added later is covered on arrival; a deployment may narrow it and answers for
that. Data principals have no password: their sign-in *is* a code, to the
mobile or the email they chose. See
[ADR 0006](../decisions/0006-mfa-for-every-staff-role.md).

## Cover

A member of staff arranges cover for a period: a delegate who then sees and
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
