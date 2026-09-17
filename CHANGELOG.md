# Changelog

Notable changes to the platform, newest first. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Dates are the dates
the work landed on `refactor/frontend-architecture`; nothing has been tagged
as a release yet.

## [Unreleased]

### Security
- **A one-time code is worth exactly a data principal's session.** The
  portal's code sign-in minted a session with whatever role the account held,
  so a code to a staff mailbox - no password, no second factor - produced a
  full staff session with every power of the role. Every code sign-in now
  acts as `data_subject` whatever the row says; the row's role is carried as
  `account_role` for display only ([ADR 0013](docs/decisions/0013-every-account-is-a-data-principal.md)).
- Task arguments are withheld from Celery's task events. Celery puts a repr of
  every argument into `task-sent` and `task-received`, and anything reading
  those events renders it - the arguments here are one-time codes and personal
  contacts. The events now carry the number of arguments and nothing else,
  while the worker still receives the real ones.
- One-time code verification is atomic: the check, the consumption and the
  attempt count are one Redis script, so two requests carrying the same code
  cannot both succeed.
- A failed request on a capability path no longer writes the token to the
  failure log, and the nginx access log scrubs consent and nomination tokens
  in every location (the earlier scrubbing variable was set and never used).
- A consent is recorded only against a serving the server itself witnessed:
  the moment comes from the server's record of rendering the notice to that
  person, and the request body's `served_at` is ignored ([ADR 0011](docs/decisions/0011-server-held-notice-serving.md)).
- Export CSV cells that begin with a formula character are written as text.

### Fixed
- The dashboard's "Needs you today" showed things a role could not act on:
  the administrator saw data principals mid-sign-up as "accounts awaiting
  activation", plus lockouts and suspensions; the DPO saw draft notices,
  access denials, and grievances already escalated away from them. Each row
  now names an action the role has (staff invitations to resend, grievances
  to escalate), and a test keeps it that way.
- A nominee saw nothing of the request they raised. Found on a running stack:
  a request filed on a death trigger had been answered and closed a week
  earlier, and the nominee's account showed an empty list - while the
  acknowledgement they had been sent told them the response would be waiting
  there. Every route that returns a request filtered on the subject, and the
  subject of their request is the principal.
- A mobile an administrator put on somebody's account was never sent a code, so
  it stayed unconfirmed with nothing having told its owner it was there — and a
  member of staff who noticed on the console had no way to confirm it, because
  the contact routes refused every session but a data principal's.
- A duplicate mobile on `PATCH /users/{uuid}` answered 500. It is reported as
  the conflict it is, like the same clash on a person's own edit.
- The console's account page no longer scrolls sideways on a phone. A session's
  user-agent is one unbroken string and the column holding it defaulted to
  `min-width: auto`, so the page grew wider than the screen and controls were
  hit-tested away from where they were drawn.
- Refusing a notice upload now names what was uploaded instead. "That is not a
  .docx file" left somebody holding a document Word had produced with nothing
  to change; the refusal now says it is a PDF, an image or a `.doc`, and for a
  `.doc` it names the Save As that fixes it. What is accepted has not changed:
  the wording is read out of the document, so a PDF or a scan still cannot be.
- A provisioned account can be activated at all. Two faults made the flow the
  console pointed people at impossible: a password reset was refused for any
  account that was not already active, and a provisioned one is `pending`; and
  setting the password left the status alone, so sign-in refused a password
  that was correct. Setting the first password now activates the account, and
  a pending account may ask for the code that does it. Suspended and
  deactivated accounts are still refused in silence.
- Staff who sign in from a link land on the page it named: the console now
  carries the destination through the second-factor step, which dropped it
  and opened the dashboard after every code.
- Two first consents for the same person and notice can no longer both
  become roots: capture serialises per pair and migration 0023 adds the
  database's own unique index.
- Downloading an export returns the bytes generated at the time, kept in
  storage (`export_log.file_ref`), rather than a re-render that drifted with
  later edits.
- Notifications are queued after the transaction commits and dropped on
  rollback, so a worker cannot act on a row that does not exist
  ([ADR 0012](docs/decisions/0012-side-effects-after-commit.md)).
- Consent receipts and withdrawal confirmations go to a verified contact,
  email first and otherwise the mobile, instead of an email that a
  mobile-only principal does not have.
- Recording a second decision on the same notice (a supersession through
  the consent link) answered 500: the earlier artefact's uuid reached the
  audit detail as a UUID object. Found while walking the new capture path
  end to end; now tested.
- Readiness compares the deployed schema with the migration head this build
  ships and answers 503 with both named, instead of accepting any row.
- Production refuses to start unless the email transport is SMTP and the SMS
  transport is the HTTP gateway; the console transports raise outside local
  and test instead of reporting delivery.

### Added
- **The audit trail can be asked questions.** Filters by data principal,
  member of staff, consent record, processor, data source, project, notice,
  site or rights request (found by name, resolved server-side), by area,
  event, record type, actor role and period, and a free-text search over the
  recorded details; a summary strip (counts by area, event, role and day)
  over the same rows; a CSV export that is itself recorded in the trail; the
  question in the address bar so it can be shared; and an **Audit trail**
  button on consent, project, notice and request pages that arrives
  pre-filtered. The filter vocabulary is served by the API, so a new event or
  table appears in the filters the day it lands; the console's own list of
  tables, eight behind the truth, is gone
  ([audit-trail.md](docs/domain/audit-trail.md)).
- **A nominee can follow the request they raised, to the end.** Section 14
  makes them the person exercising the right, and the request now reads to
  them as it does to the principal: the state, the clock, the path, the
  response and the files released with it, from the nomination card on their
  own account page. Reading is not acting - making another request in her
  name, or disputing a response, still needs the nominee page and a code to a
  contact she recorded. A nomination revoked after it was invoked keeps its
  request in view, marked as no longer in effect. On an incapacity claim the
  principal is acknowledged too. Acceptance now records which account
  accepted (migration 0026), so the nominee is matched by account rather than
  by comparing contact strings
  ([ADR 0014](docs/decisions/0014-a-nominee-follows-the-request-they-raised.md)).
- **A mobile an administrator sets is sent a code.** Creating an account with
  a number, or changing one on the register, now writes to that number:
  `contact_added_for_you` says an administrator added it and carries a code to
  confirm it with, valid for `STAFF_INVITE_TTL_H` hours because nobody is
  waiting at a code box for it. Until the code comes back the number signs
  nobody in, as for any contact. A quota already spent withholds the message
  rather than refusing the edit, and the console says what was sent.
- **The console has the contacts card too.** A member of staff can see which
  of their contacts are confirmed, add or change a mobile, and add a personal
  email, from the console's own account page rather than only from the
  portal's. The routes under `/me` that are about the person rather than about
  being a data principal — the profile, the contacts, the person type — now
  admit any signed-in session; the rest of `/me` stays the data principal's
  ([ADR 0013](docs/decisions/0013-every-account-is-a-data-principal.md)).
- **A member of staff is also a data principal.** Their corporate address
  signs them in on the data-principal portal and through a consent link, with
  a code like anybody's, into a session that acts as a data principal and
  nothing more; the portal says which account is in use. Deactivating a
  member of staff now ends the role and keeps the person: the row becomes a
  data principal, the password goes, `person_type` becomes `ex_employee`, and
  they still reach their own consents and rights ("End staff access" on the
  register).
- **A second email and a mobile, added by the person.** From the account
  page, each confirmed by a code sent to it (`contact_confirmation`) before it
  can sign them in; `PATCH /me`, `POST /me/contacts/code`,
  `POST /me/contact/verify`, `DELETE /me/secondary-email`. An address belongs
  to one account whichever column holds it (migration 0025).
- **Flower, for watching the task queues.** Which tasks ran, on which queue, how
  long they took, which failed and what they raised. Behind a compose profile
  (`--profile monitoring`) and in the dev dependency group, so it is never in
  the runtime image; bound to the loopback and refusing to start without
  `FLOWER_BASIC_AUTH`, because it can revoke and terminate tasks and has no
  roles ([monitoring.md](cmp_backend/docs/operations/monitoring.md)).
- **A provisioned staff account now invites its owner.** Creating one sends
  `staff_invitation` to the address on the account: their role in words, a
  link to the reset page with the address filled in, and a code that lasts
  `STAFF_INVITE_TTL_H` hours (48 by default). It is the reset flow's own code,
  so an expired invitation is replaced by "Forgotten your password?" rather
  than by a second mechanism. `POST /users/{uuid}/invite` sends it again while
  the account is pending; the console offers it on the register.
- **Configurable messages.** Every email and SMS the platform sends is a
  named junction with default words per channel; the administrator and the
  DPO edit subject and body from the console's Messages page, with variable
  chips, a preview on sample values, and reset to default. Saves and resets
  are audited. `GET/PUT/DELETE /messages/...` (migration 0024). A message
  cannot be sent except through a junction, and three tests keep the list
  complete ([messages.md](docs/domain/messages.md)).
- Every default message reworded: the code on its own line and in the
  subject, what it is for, how long it lasts, what to do if it was not you;
  SMS bodies written separately and short. `ORGANISATION_NAME` names the
  organisation in them.
- Consent receipts list the purposes agreed to; consent-link codes name the
  project.
- An HTTP SMS transport: a JSON POST with a bearer token to an https gateway
  (`SMS_TRANSPORT=http`, `SMS_HTTP_URL`, `SMS_HTTP_TOKEN`, `SMS_HTTP_SENDER`).
- The CI workflow at the repository root, where GitHub runs it, covering the
  backend, both portals, an OpenAPI freshness check and an asserted image
  smoke test.
- `docs/reviews/2026-09-10-implementation-review.md`: the disposition of the
  external review that found the above, and why the suites had not.
- Redis runs with `noeviction` in the compose file: every key there is state.
- Node 22 required by both portals' `engines`.
- A documentation set under `docs/`: system overview, repository layout,
  domain model, API map, the four workflows, roles and access, local
  development, testing, deployment, runbook, ten architecture decision
  records, a glossary, and this changelog.
- `CONTRIBUTING.md`.

### Changed
- **A consent link now authenticates rather than enrols.** The first step asks
  for one contact - mobile by default, email instead - and confirms it with a
  code, where it used to take a name, a mobile and an email and create an
  account from them. The artefact is bound to a data principal who already
  exists and can therefore find it, read it and withdraw it. Somebody without
  an account is linked to sign-up carrying the consent link, and returns to it
  signed in. A code is sent only to a contact on the register, while the reply
  stays the same sentence either way, so the form cannot be used to ask whether
  a number is registered.
- The three low-level design documents moved from `LLD/` to `docs/history/`
  with banners stating what they describe and when.
- `cmp_backend/openapi.json` regenerated from the running application.
- Every README and backend document brought up to the current counts, the
  22-migration chain, Node 22, the two portals and the rights module.

## 2026-09-10

### Added
- **Dashboard**: the landing page answers what needs the signed-in person
  today, first: requests past a checkpoint, tickets awaiting them, unread
  threads.
- **Rights**: files released with the response, downloadable for a bounded
  period (migration 0021).
- **Rights**: the register names the request an unread message is on; the
  office's bell counts unread ticket messages (`GET /requests/attention`).
- **Rights**: a returned ticket can be sent back with a reason, and each side
  is told what the other did (migration 0020).
- **Rights**: a request confined to one consent, from her consent page
  (migration 0019).
- **Rights**: a ticket can be withdrawn, reassigned and reminded; dates on the
  console are shown as felt ("due in 3 days") (migration 0018).
- **Rights**: a nomination records the request that invoked it and the trigger
  event; death closes the principal's account, incapacity does not
  (migration 0022).
- **Rights**: a grievance carries the request it disputes.
- **Rights**: one Respond action on a ticket, with files on messages in both
  directions.

### Changed
- **Access**: what each role may reach was re-cut to match what the role is
  for; the matrix has 18 resources, including `rights_request` and `ticket`.

### Fixed
- The last ticket back moves the request off "awaiting holders".
- A closed request keeps its ticket threads readable.
- A stranger is told when a public request is closed as not verified.

## 2026-09-09

### Added
- Accepting a nomination gives the nominee an account to sign in with.
- **Registry**: a third party may be represented by one of the
  organisation's own accounts.

### Fixed
- A data principal with no email can sign in.

## 2026-09-08

### Added
- **Rights**: respondents per processor, portal tickets for in-house teams,
  mail tracked on the request (migration 0016).
- **Rights**: a ticket is a thread that opens with what the office already
  knows (migration 0017).
- **Rights**: every response carries her record, and the mail carries the
  response.
- A data principal sees the nominations that name her.
- The nominee is given the reference they need to act.
- Sign-up refuses a contact that is already registered, with a neutral
  answer.

### Fixed
- Development email domains are accepted when provisioning accounts.

## 2026-09-07

### Changed
- **Two portals**: the data principal's portal (`cmp_public_ui`, port 3001)
  split out of the staff console (`cmp_internal_ui`, port 3000). Nothing a
  member of staff uses ships on the portal, and the reverse.
- The whole lifecycle, backend to browser, made to pass on the new layout.

## 2026-09-06

### Added
- **Rights module**: access, correction, erasure and grievance requests with
  a clock from receipt, holders derived from disclosures and assets, one
  ticket per holder, erasure scope decided per appearance, nominees, and the
  public rights page (migration 0013).
- **MFA for every staff role**: a code to the account's email after the
  password, for all six staff roles; the default list is derived from the
  role enumeration.
- **Mobile-first contacts**: mobile required and email optional for data
  principals and nominees; every contact verified at sign-up; sign-in by
  code to the chosen contact; nomination acceptance needs a code
  (migration 0015).
- Notice import from the legal `.docx` template understands "English
  (en-IN)" and refuses an unknown language by name.

### Fixed
- The audit chain could report a break under concurrent writes because the
  chain position was drawn before the lock; the position is now drawn inside
  it (migration 0014).
- An unknown enumerated value in a request answered 500 and dropped the
  proxy connection; it now answers 422 with the choices named.
- The console overflowed sideways on a phone on the project page and the
  sites list.
- The seed builds the CIT (DCO) and SE (RCO) sites the routing tests expect.
- The sign-up link nobody could see.

## 2026-08-28

### Added
- Create a notice by uploading the document Legal drafted.
- A consent link that can be shared, and an export a field agent can use
  (migrations 0010, 0011).
- Date of birth on a data principal; minority derived in the database
  (migration 0012).
- A script for reading the database directly (`scripts/db.py`).

## 2026-08-26 to 2026-08-27

### Added
- The collection model: collections, assets, bystanders, dispositions, and
  who may see what under it (migration 0007).
- Site-based ownership for collection owners, with a per-site override, and
  cover arrangements (migrations 0005, 0006, 0008).
- Processor amendments after approval (migration 0009).
- Rule 3 overrides per notice; link re-mint; a manifest template; activity
  feeds; the refusal trail.
- Console: the import wizard, filter chips, site ownership, one activity
  renderer for every role.

### Fixed
- Two forms that could not be submitted; the sign-in form leaking the
  password into the URL.

## 2026-08-25

### Added
- The staff console's layered structure: one feature folder per business
  area, a validation layer mirroring the API's, a security layer, the
  password reset page, and the unit and browser suites.
- Backend `docs/`, operator scripts, and the security test suite.

## 2026-08 and earlier

- The baseline schema, enforcement triggers and least-privilege grants
  (migrations 0001 to 0004); the layered FastAPI service; the original
  single frontend. See `git log` before 2026-08-25.
