# Roles and access

Eight roles. Six are staff and sign in on the console with a password and an
emailed code; the seventh is the data principal, who signs in on the portal
with a code alone; the eighth, the temporary ticket holder, is a breach-only
login that signs in like staff but reaches nothing except the tickets
addressed to it (S3-09). What each may reach is a static matrix in
`backend/api/src/cmp/core/permissions.py`, consulted before any work is done,
and the rows each may see are a scope compiled into every query.

## The roles

| Role | Enum value | Who they are | What they mainly do |
|---|---|---|---|
| Data Protection Officer | `dpo` | The Privacy Office | Composes and approves notices, activates purposes, approves projects and publishes their notices, sees every register, runs the rights queue, reads the audit trail |
| Administrator | `admin` | Provisions the platform | Creates accounts and assigns roles, sees the audit trail, arranges cover for anyone, edits the words of every message the platform sends, and is the independent reviewer for a grievance about the DPO |
| Data Collection Owner | `dco` | Accountable for a third party's collection | Registers data sources and sites under their processors, mints and replaces consent links, exports and imports, answers tickets addressed to them |
| DCO Admin | `dco_admin` | Routes third-party collection | Receives an approved project that names a third-party processor, attaches sources, registers sites and names who runs them |
| Research Collection Owner | `rco` | A DCO for in-house collection | The same as a DCO, restricted to the organisation's own sources and sites |
| R&D User | `rnd_user` | Owns a study | Registers the project, names the collectors, brings the notice as a filled-in document or a copy of an approved one, uploads approval proofs, asks to add a collector after approval |
| Data principal | `data_subject` | The person the data is about | Reads and withdraws her consents, sees her disclosures, makes and follows rights requests, names a nominee |
| Temporary ticket holder | `breach_holder` | Somebody inside the organisation, with no console login, asked to act on a breach | Answers the breach tickets addressed to them and brings in colleagues; nothing else. Never given by hand: set when the DPO (or a holder) asks them by email, put back when their last ticket on an open breach ends ([ADR 0023](../decisions/0023-breach-tickets-and-breach-only-logins.md)) |

## The matrix

Each cell is a scope, and `+w` means the role may also write. A blank cell is
denied: no wildcard, no inheritance.

| Resource | DPO | Admin | DCO | DCO Admin | RCO | R&D | Principal | Temporary holder |
|---|---|---|---|---|---|---|---|---|
| user | all | all +w | | | | | | |
| purpose | all +w | all | all | all | all | all | | |
| processor | all +w | all +w | all | all | all | all | | |
| data_source | all +w | all +w | all +w | all +w | all +w | all | | |
| project | all +w | | scoped +w | scoped +w | scoped +w | own +w | | |
| approval | all | | scoped | scoped | scoped | own +w | | |
| site | all +w | | scoped +w | scoped +w | scoped +w | own | | |
| notice | all +w | | scoped | scoped | scoped | own +w | | |
| link | all +w | | scoped +w | scoped +w | scoped +w | | | |
| consent | all | | scoped | scoped | scoped | own | | |
| export | all +w | | scoped +w | scoped +w | scoped +w | | | |
| import | all +w | | scoped +w | scoped +w | scoped +w | own | | |
| collection | all | | scoped | scoped | scoped | own | | |
| asset | all | | scoped | scoped | scoped | own | | |
| audit | all | all | | | | | | |
| message_template | all +w | all +w | | | | | | |
| rights_request | all +w | scoped +w | | | | | | |
| legal_hold | all +w | | | | | | | |
| restricted_country | all +w | all | | | | | | |
| breach | all +w | | | | | | | |
| ticket | own +w | own +w | own +w | own +w | own +w | own +w | | own +w |
| breach_ticket | own +w | own +w | own +w | own +w | own +w | own +w | | own +w |
| me | | | | | | | own +w | |

The R&D User's write on a notice is narrower than the row can say. They bring
one, by uploading the filled-in document, re-uploading a corrected one, or
copying a notice the Privacy Office has approved. Composing one, editing its
wording, attaching or narrowing its purposes and writing the text of a rendition
are the office's, on routes guarded by role rather than by this resource. The
split is by act rather than by resource, which is why the table alone does not
show it; a unit test pins which route is on which side.

Copying reaches wider than the rest of their notice read. "Use an existing
notice" offers every approved or published notice on the platform
(`GET /notices/copy-sources`), whichever project it is on and whoever wrote it,
because text the office has approved for one study is what the next should
start from; the copy is a draft on their own project and its legal approval
does not come with it. Everywhere else an R&D User sees only their own
projects' notices, and another project's draft is never copyable.

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

`breach` goes one step further. A role with no grant on it is answered **404**
on every breach route, not the 403 every other resource gives - the register,
a breach that exists and a write all read as "not there" - because that a
breach is being handled is itself what the grant withholds
([breaches.md](breaches.md), [ADR 0021](../decisions/0021-a-breach-is-recorded-and-its-duties-tracked-never-submitted.md)).

`breach_ticket` (S3-08) is the other side of that: a ticket addressed to me,
OWN for every staff role like `ticket`, with the holder in the `WHERE` clause -
another person's ticket is 404. Holding one opens the ticket and nothing of the
register: the managing routes stay under `breach`, and answer every holder but
the DPO 404 ([ADR 0023](../decisions/0023-breach-tickets-and-breach-only-logins.md)).

## Navigation

The console draws its navigation from `GET /auth/me`, which returns the
sections the server computed for the role. The client holds no copy of the
matrix, so it cannot drift into showing a button that answers 403.

| Role | Sections |
|---|---|
| DPO | dashboard, projects, approvals, notices, purposes, sites, collections, processors, sources, consents, links, exports, imports, requests, breaches, audit, users, messages, delegate, tickets, notifications, profile |
| Administrator | dashboard, users, messages, processors, sources, requests, audit, delegate, tickets, notifications, profile |
| DCO, DCO Admin, RCO | dashboard, projects, sites, sources, links, consents, exports, imports, collections, delegate, tickets, notifications, profile |
| R&D User | dashboard, projects, notices, processors, approvals, imports, collections, tickets, notifications, profile |
| Data principal | consents, requests, notifications, profile |
| Temporary ticket holder | tickets, notifications, profile |

A temporary ticket holder has no dashboard: the console sends it from
`/dashboard` to **My tasks**, reading `nav` rather than its role.

Tickets are in every staff role's navigation, because any staff account can
be named a respondent; the page is empty until one is addressed to them.

The server decides *which* sections a role has; the console decides their
order. Since October 2026 each role's sidebar opens with **Your work** - its
daily destinations in the order the work runs (`DAILY_WORK` in
`components/layout/nav.ts`) - and the rest follow in their groups (UX review
2026-10-05):

| Role | Your work |
|---|---|
| DPO | Dashboard, Rights requests, Breaches, My tasks, Projects, Notices |
| R&D User | Dashboard, My projects, Approval documents, My tasks, Notices |
| DCO Admin | Dashboard, Collection sites, Data sources, My tasks, Consent links, Projects |
| DCO, RCO | Dashboard, My projects, Collection sites, Consent links, My tasks, Collections |
| Administrator | Dashboard, Users, Grievances about the DPO, Message templates, Processors, Data sources, Audit trail |

Profile and notifications are not in the sidebar: the account menu holds
**My profile** and sign-out, and the bell opens notifications. Pages are
named by what they hold: **My tasks** (tickets), **Approval documents**,
**Message templates**, **Delegations**. On the portal the menu is My
consents, My requests, **My nominations** (its own page since October 2026,
not the foot of My requests) and **Updates**.

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
switched off as before. For a temporary ticket holder the button reads "End
temporary access" and removes their breach-only login instead (below); it
never marks them an ex-employee.

**A person may correct their own name** from the account page, on either
portal (**Change** beside it). It is `PATCH /me` with the name alone: sealed on
save, its search runs recomputed so the register still finds them by part of
it, and audited as `user.updated` without the name (ADR 0015). An empty name is
refused. Nothing else changes with it - not how they sign in, not their role.
The other profile fields stay as they are: date of birth is asked once when
missing, person type and the primary email, organisation id and username are
not edited from the profile. A new name does not yet reach processors that were
sent the old one in an export; that is deferred with the rest of correction
(S3-05).

**A person may add a second email and a mobile** from the account page —
either portal's, since the account is the same one. Each is confirmed by a
code sent to it, and until the code comes back it cannot sign anyone in — a
typed contact is a claim, and a claim is not a way in. An address belongs to
one account whichever column holds it. A member of staff who wants to keep
reaching their own consents after leaving adds a personal address while the
corporate one still works.

**What sends a code is the state she is left in, not the difference.** A
contact she gives that is still unconfirmed afterwards is sent one, whether or
not the digits changed; one that has already answered a code is left exactly
as it was, because re-sending would take away a way of signing in to no
purpose. The rule used to be about the change, which made the commonest case
silent: an account often already carries an unconfirmed number, the edit box
opens pre-filled with it, and the natural act of opening it and pressing save
sent nothing at all. The page says which of the two happened, reading the
answer off the saved row rather than guessing from what was typed.

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

**The one exception: a breach-only login** (S3-09,
[ADR 0023](../decisions/0023-breach-tickets-and-breach-only-logins.md)). When
the DPO asks somebody to act on a recorded breach and they have no console
login - or a ticket holder brings in a colleague who has none - the server
gives them one without an administrator. It is bounded three ways: to one
breach, to an address on `BREACH_TICKET_EMAIL_DOMAINS`, and to the role
`breach_holder`, which reaches only the tickets addressed to it, notifications
and the profile. The address is looked up by its keyed hash:

| The address belongs to | Then |
|---|---|
| an active member of staff | an ordinary ticket |
| a data principal's account | that account becomes `breach_holder` while the grant lasts; its previous role is kept on the grant |
| nobody | a new account: `pending`, `employee`, `breach_holder`, marked as made for this breach |

They are sent "Temporary console access for a breach ticket" - the reset
link and code, exactly as an invitation, naming no breach - set a password,
and sign in with a password and an emailed code like all staff. The role is
never given by hand: `POST /users` and the change-role route refuse it, and no
staff picker offers it. An administrator may give such a person a real role;
ending the grant then leaves that role alone.

When the breach closes or the DPO withdraws their ticket, their part is over
but the login stays, so they can still read their ticket; nothing on it can be
written (decided 2026-10-06). The one off switch is an administrator's **End
temporary access**: an account made for a breach is switched off, one that was
a data principal's goes back to `data_subject`, the password is cleared,
`person_type` is untouched, and every session is revoked.

## What the dashboard asks of each role

Each role's landing page opens with **Needs attention**: counts of things
that role can act on, from the page each row opens. The rule is strict, and
tested: a count the role can only look at is not on the list. Lockouts
clear themselves; a suspended source was suspended on purpose; refusals in the
log are the audit trail's. Those stay in the queues and statistics further down.

For the DPO the first two rows can be about a breach: **Breach duties
overdue** (a duty past its due time, or past the internal target for "without
delay" once one is set) and **Breach duties outstanding**, both opening the
register. Below them, **Open breaches** lists each open breach with every
duty's state and clock (S3-04). No other role's dashboard carries any of it:
the server sends the list to the DPO alone. **Breach tickets returned** and
**Breach tickets past their answer-by** (S3-08) follow, opening the register.
Every staff dashboard's **Tickets addressed to you** lists its reader's open
breach tickets beside their rights tickets, by the breach reference alone.

The DPO's queues include one of draft projects, which is not a contradiction:
it lists only the drafts whose purposes are waiting to be activated, which is
the one thing on a draft that is theirs. Nobody is held up by it - the author
submits when they are ready, and the activation gates the officer's own
approval - so it is work brought forward, and it is a queue rather than a row in
**Needs attention**.

Each row opens the subset it counts - `/sources?unowned=1`,
`/requests?due_soon=1`, `/notices?languages=unapproved` - and each queue is in
order of urgency: the DPO's start with tickets already past their date, then
the rights clock, then what others are waiting on, then decisions, then work
brought forward. A queue at its 25-row limit says **25+**. A DCO or RCO also
sees **Approved projects ready to collect**, so a quiet day shows what they
can start; an R&D user's projects with the DPO are under **Waiting for DPO
review**, apart from **Needs your action** (UX review 2026-10-05).

| Role | Needs attention |
|---|---|
| DPO | breach duties past their due time; breach tickets returned or past their answer-by; tickets past their date; rights requests overdue and due within seven days; requests awaiting verification; teams that have written on their tickets; grievances about the DPO not yet escalated; retention floors passed; tickets addressed to them; notice text awaiting approval; projects pending approval; new collectors awaiting a decision |
| Administrator | staff invitations not yet accepted (resend them); grievances about the DPO to review; tickets addressed to them |
| DCO, RCO | tickets past their date; tickets addressed to them; imports that did not reconcile; assets with unmapped subjects |
| DCO Admin | tickets past their date; sites awaiting a data source; sources with nobody accountable; processors with no collection set up; tickets addressed to them |
| R&D User | projects needing something from them; tickets addressed to them |
| Temporary ticket holder | no dashboard: the console sends it to **My tasks**, where its breach tickets are |

Every staff dashboard also lists the breach tickets addressed to its reader,
and the DPO's shows the open breaches above the queues.

A data principal who has not finished her own sign-up is not the
administrator's to activate, so she is not counted; a grievance about the
DPO that has been escalated is the administrator's, so the DPO no longer
sees it.

## The bell

The notifications page and the bell over it are derived from the audit
trail, not a table of their own, and each reader sees only what they could
open.

- **A data principal** sees the events about herself that she is meant to
  see: the outcome of her request, not the office's working on it
  (`SUBJECT_VISIBLE` in the audit repository).
- **Staff** see six kinds of event - a project moving state, a notice
  published, an import rejected, an export generated, a consent withdrawn,
  an account locked out. One that belongs to a project - the project itself,
  a notice on it, an import or an export for it - is shown to exactly the
  people who could see that project in the project register, by the same
  scope predicate. One with no project goes by role: the DPO sees withdrawals
  and lockouts; the administrator sees lockouts only, because a withdrawal
  links to a consent record and the administrator's role does not read
  those; every other role sees neither.
- **Tickets.** Every member of staff - and a temporary ticket holder - also
  sees what happened on the tickets addressed to them, and the DPO what respondents did on everyone's. A
  respondent's link opens the ticket, not the request page their role may
  not reach. Breach tickets (S3-08) the same: a holder hears what the office
  did and wrote on theirs, linking to `/tickets?breach_ticket=`; the DPO hears
  what holders wrote and returned, and whom they added as a colleague
  (S3-09), linking to the breach.

The rule the bell keeps is the dashboard's: no link in it leads to a page
that answers 403 or 404 for the person reading it. It is held where the link
is made: a staff link is kept only when the reader's own menu (`nav_for`) has
the section it lands in, so a DCO's "Notice published" and an R&D user's
"Export generated" read the same but carry no link to a section the role does
not have. The same holds on the dashboard and in the audit trail, and a test
checks every link template against the pages the console and portal actually
have.

## Finding a person in the register

The staff register's search box (`GET /users?q=`) takes part of a name, from
three letters up, or a whole email, mobile, username or employee number.
Names and contacts are sealed, so neither is compared as text: the name is
matched through hashed runs of three characters kept beside it, and a
contact through a keyed hash of the whole value. Half an address finds
nobody, deliberately; a two-letter term matches only the exact contacts,
never everybody. The mechanism, and what the runs cost, is in
[the DKMS field list](../dkms/pii-tables-and-fields.md#2a-searching-by-part-of-a-name).
The list is not in alphabetical order, and cannot be: ciphertext does not
sort.

## Second factors

Every staff role signs in with a password and then a six-digit code sent to
the account's email, for five minutes and five attempts. The list is
`MFA_REQUIRED_ROLES`, derived from the role enum by default so that a role
added later is covered on arrival; a deployment may narrow it and answers for
that. A temporary ticket holder always needs the code, whatever the list
says: it is checked in code, not configuration. Data principals have no
password: their sign-in *is* a code, to the mobile or the email they chose -
and a code sign-in on the portal is a data principal's session whatever the
account's role, a breach-only login's included. See
[ADR 0006](../decisions/0006-mfa-for-every-staff-role.md).

## Delegation

The console calls it **Delegate**. A member of staff arranges cover for a period: a delegate who then sees and
acts on the delegator's rows for that period only, in their own name, with
every action audited as theirs. Cover ends at the end of the period or when
either party ends it. The administrator can arrange it for anyone; nobody can
arrange cover that widens what the delegator themselves could do. The form
offers the colleagues `GET /delegations/candidates` names - the active
accounts in the caller's role - because the users register it once read is
the DPO's and the administrator's alone, and everyone else was offered nobody.

## How the matrix is kept honest

- `auth/authorization/permissions.py` asserts at import that the resource
  roster and the matrix agree in both directions; the process fails to start
  otherwise.
- `tests/security/test_matrix_integrity.py` holds the invariants: no
  resource names a role twice, a data principal cannot touch the registry,
  staff is everyone who is not a data principal.
- `tests/security/test_bola.py` and its neighbours walk uuids across scopes
  and expect 404, never a row.
