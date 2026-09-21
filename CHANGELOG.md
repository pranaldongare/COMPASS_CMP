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

### Changed
- **The API is installed with `pip`, and nothing ships as a container.** `uv`
  and its lockfile are gone; `backend/api/requirements.txt` carries the runtime
  pinned to the exact versions the lockfile held on the day of the change, so
  nothing moved version in the move, and `requirements-dev.txt` adds the suite,
  the tools and the project itself editable. `pyproject.toml` keeps every
  `[tool.*]` block and reads its dependencies from `requirements.txt`, so there
  is one list. The Dockerfiles for all three deployables, the compose stack, the
  nginx configuration and the `.dockerignore` files are removed; the two
  documents that described deploying them are in `docs/history/`. One Docker
  file remains, `backend/api/dev-services.yml`, and it starts PostgreSQL and
  Redis and nothing else — it exists because the machine this is developed on
  has no other PostgreSQL, and it is written to adopt the database that already
  exists rather than start an empty one beside it. Three comments that said the
  proxy enforced the body-size cap now say the application does, because it
  does. Verified under `venv` + `pip` alone: 1154 backend tests, lint, format
  and types all pass. `.github/workflows/ci.yml` still installs with `uv` and
  builds the deleted image; the corrected file is `docs/tools/ci.yml.proposed`.
- **The repository is three layers.** `backend/` holds everything the server
  does — the platform API (was `cmp_backend`) and the key service (was
  `cmp_dkms`). `frontend/` holds everything the browser does — the staff console
  (was `cmp_internal_ui`) and the data-principal portal (was `cmp_public_ui`).
  `docs/` holds every document: the API's seventeen internal documents that sat
  under `cmp_backend/docs/`, and the three reference trees — `api_docs/`,
  `database_schema/`, `api_access_control/` — that sat at the root looking like
  projects, now `docs/reference/{api,database,access-control}/`. The generators
  are in `docs/tools/`, joined by `check-links.py`, which asserts every relative
  link in every document resolves (555 of them do). Nothing inside any service
  changed: every project already resolved its own paths, so the whole move was
  four `git mv`s and seven files that pointed between projects. All four suites
  match their pre-move counts. `.github/workflows/ci.yml` still names the old
  paths — that file cannot be pushed from the environment the work was done in;
  the nine changes are in `docs/tools/ci-paths.md`.
- **The interactive API docs load again.** `/docs` and `/redoc` are documents
  that fetch Swagger UI from a CDN and start it with an inline script, and the
  API's `default-src 'none'` blocked every part of that, so the page rendered
  empty with four policy violations in the browser console. The middleware's
  own docstring had claimed the docs were an exception; now they are, narrowly
  — those two paths, the sources that page actually loads, and nothing else.
  Every other response keeps the strict policy, and the docs do not exist in
  production at all.
- **Either portal's dev server can be reached by IP.** `DEV_ORIGINS` adds
  origins to `allowedDevOrigins`, for testing from another machine on the
  network, where the address differs per machine and cannot be committed.
- **A notice has no maximum length any more.** The rendition a data principal
  reads was capped at 20,000 characters, which is not what its column holds —
  `notice_language.rendered_text` is `text` — but a number somebody chose. A
  fiduciary running many purposes across several recipients writes a long
  notice because section 5 requires it to, and refusing that is refusing the
  lawful document. The floor stays: an empty rendition is still nothing, and
  publication still refuses a notice without one. What bounds it now is the
  request body limit, which is the honest place for it.
- **A project cannot be approved while its purposes are unactivated.** The
  purposes an uploaded document creates arrive as drafts and only the Privacy
  Office activates them. Nothing checked for that outside publication, which
  happens inside the officer's own approval: so the author submitted, the
  officer was told the one thing in the way was the language, approved the
  language, was offered the move as allowed, and the move then failed from
  inside the transaction on a purpose no screen had named. It is now a
  requirement on the approval, which turns that into a disabled button with a
  sentence, and on a project submitted before this landed into a 409 rather
  than an error after the click. The submission is deliberately left alone:
  the author cannot activate a purpose, so blocking them there would park the
  project in a draft they cannot leave, waiting on a review nobody has asked
  for yet.
- **The dead ends are gone.** Registering a project opens it, rather than
  closing onto a list with a toast telling you to do something on a page you
  are not on. A notice's breadcrumb returns to its own project instead of to
  every notice, which needed the project on the notice response. The empty
  states that said there was nothing and offered nothing - collection sites,
  the notice's purposes, its renditions - carry the control that fills them.
  The three messages naming a place in bold now say whose job it is, since
  the reader often cannot do it themselves and two of those places are not in
  their navigation. And one thing has one name: what the dashboard called a
  translation awaiting approval is notice text awaiting approval, which is
  what the notice calls it and what the button does.
- **The Privacy Office composes a notice; the R&D User brings one.** Seven
  routes moved: writing a notice from nothing, editing its wording, attaching,
  narrowing or removing a purpose, and writing the text of a rendition are the
  office's. The author keeps the three that matter to them - upload the
  filled-in document, upload a corrected one, or start from a notice the office
  has approved - and the console offers those two in that order, with
  composing gone from their view. The copy picker widens from published notices
  to approved ones as well, since a notice written as a model is never
  published, and approved means the office signed its text off.
- **The officer activates a purpose from the notice that carries it.** The
  publication checklist named a purpose code and stopped there, and the only
  control that acted on it was a row in the purposes register, reached by a
  different route and filtered by hand, nine times for one imported document.
  Each draft purpose now carries its own control on the notice, and every
  blocking line links to the card that clears it. The decisions stay separate,
  because what is signed off is each purpose and one control over the set would
  be a click rather than a review.
- **Every blocker is reported, not only the first.** A transition that cannot
  run now lists all of its unmet requirements. Clearing one to be told about the
  next reads as the system inventing objections, when the list was always there.
- **The officer's draft queue is work they can do.** It listed every draft with
  the action "Review and publish the notice", and following that row landed on a
  project whose card reads "There is nothing for your role to do at this stage",
  because the only move out of draft is the author's. It now lists only the
  drafts whose purposes are not activated, which is the one thing there that is
  theirs, and says so. Nobody is waiting on it, so it stays a queue rather than
  becoming a row in **Needs you today**.

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
- `backend/api/openapi.json` regenerated from the running application.
- Every README and backend document brought up to the current counts, the
  22-migration chain, Node 22, the two portals and the rights module.

### Added
- **A key service, and the two layers that use it.** `backend/dkms` is a separate
  FastAPI deployable holding one secret and doing one thing with it:
  `POST /encrypt/bulk` and `POST /decrypt/bulk` take an array of records and a
  mapping of field names to DKMS data types, encrypt only the fields named, and
  pass everything else through. `method` picks the form — `string` for the
  `SE::` prefix, `bytes` for base64 — and both carry the same envelope.
  AES-256-GCM, a key derived per data type by HKDF, and the type bound into the
  ciphertext as additional authenticated data, so a value written as `MOBILE`
  refuses to open as `NAME` rather than returning plausible rubbish. The thread
  pool is real parallelism, because OpenSSL releases the GIL: 15,000 values in
  74 ms across 14 workers, measured. Separate from the platform API on purpose —
  that process holds the database, this one holds the key that makes it
  readable. Installed with `python -m venv` and `pip install -r
  requirements.txt`; 35 tests, including the caller's own example asserted
  verbatim and key rotation walked end to end.
- **`cmp.infrastructure.dkms`**, the platform API's client. Batches a write's
  personal fields into one call rather than one per field, and **fails closed**:
  if the key service cannot be reached the write fails rather than quietly
  storing plaintext. `fields.py` is the field map — which column holds which
  kind of personal data — with a second list naming every personal column that
  *cannot* be encrypted yet and why, so a plaintext column is a decision on the
  record rather than an oversight. Production now refuses to start with
  `DKMS_ENABLED=false`.
- **Decryption in each portal's server layer**, at `/dkms/decrypt`, with a
  `useDecrypted()` hook that decrypts a whole list in one call. The browser
  never holds a key and never learns where the service is: it sends back
  ciphertext the API already served it, which means the permission matrix and
  the scope have already run, and gets plaintext. A page that cannot decrypt
  says so rather than rendering a blank where a name should be.
- **An inventory of the personal data this platform holds.**
  [docs/domain/personal-data.md](docs/domain/personal-data.md) lists every table
  and column that carries something about a person, the four stores that are
  not the database — Redis, the file store, the logs, the messages that leave —
  and all 159 of the 245 API operations that accept or return personal data,
  each with the fields by name and the permission matrix's own answer for who
  may call it. The 20 operations that answer without a session are pulled out
  separately, with what stops each being an oracle. It is a join over
  `openapi.json`, `endpoint_permissions.json` and `schema_inventory.json`, so
  `docs/scripts/personal_data_scan.py` regenerates the endpoint tables; the
  script exits non-zero on a field name it has not been taught to classify,
  which is the one thing a document like this cannot notice on its own.

### Fixed
- **A project showed no notice, however many it had.** `NoticeOut` gained the
  project a notice belongs to, so its page could lead back there, and both
  fields are required. Four of the repository's six notice-row producers did
  not select them - the two list queries had no join to `project`, and the two
  write queries could not have one, because `RETURNING` cannot reach another
  table. `GET /projects/{uuid}/notices` therefore failed response validation and
  answered 500 for every staff role, as did a notice's version history. A
  notice row now carries its project wherever it comes from, the two writes
  reading the row back rather than returning the bare statement. The data
  principal's own route was never affected, which is what made it look like a
  permissions problem rather than a broken response.
- **A list that fails to load no longer reads as a list with nothing in it.**
  The project page drew the same "No notice yet" panel for an empty project and
  for a query that had just answered 500, so the notice somebody had uploaded a
  moment earlier appeared not to have been saved at all. A failed query now says
  so, with the reason.
- **A consent link was copied out of the console pointing at the console.** The
  API returns the link as a path, deliberately - which host serves `/c/{token}`
  is deployment configuration. All three places that showed one put
  `window.location.origin` in front of it, which is the console's own origin:
  port 3000 in development, where that route does not exist. So every link
  minted, reminted or copied was handed to a collector as a host that 404s, and
  nothing about the URL looked wrong. They now use
  `NEXT_PUBLIC_SUBJECT_PORTAL_URL`, the same origin the console already sends a
  data principal to from its sign-in page, through one helper rather than three
  string templates. A unit test pins it, because the failure is invisible from
  inside the console: the string is well-formed and the token in it is correct.
- **One page of every list in ten was refused as a malformed cursor.** A
  cursor carries a twelve-byte signature after a `.`, and the decoder found the
  separator by looking for the last `.` in the decoded bytes. Roughly one
  signature in twenty-two contains that byte, so the split fell inside the
  signature, the check failed, and a cursor the service had issued seconds
  earlier came back as malformed. It affected every paginated list, about 4.6%
  of the time, and survived because a single round trip passes 95% of the time
  and it never reproduced twice. The split is by length now, which is safe
  because the signature is fixed-width.
- **The console stopped contradicting the system it describes.** A review of
  the project, notice and purpose journey found seven screens saying things
  that are not true: five project states where four are reachable, a progress
  bar that printed "In Draft" twice because a dead state shares its label, two
  empty states placing approvals in a state nothing reaches, a dialog still
  asking for a Data Collection Owner the form no longer has, and a sites page
  claiming a site is required before a notice can name recipients, which the
  publication checklist deliberately does not require. The status filter no
  longer offers the unreachable state, and the publication checklist names
  what a reader sees on screen rather than the database column behind it.
- **Publish was offered to people the API refuses.** An R&D User with a
  complete notice was shown the button and got an error on pressing it.
  Publication is the Privacy Office's, and the notice now says so instead.
- An R&D User's project page asked for the project's consent links on every
  visit and was refused every time: they own the project but hold no grant on
  `link`. A red line in their browser console, and an audited denial in ours,
  for a card they cannot see. The page now asks only when the role may read
  them, decided from what the server already says the role may write.
- **"Save changes" on a draft project did nothing at all.** No request, no
  message, and the dialog stayed open, which is how it was reported. The form
  was judged against the rule that belongs to *registering* a project — that
  somebody be named as collecting — on a field the edit dialog has no control
  for, so validation failed before the submit began, and the message for that
  field is rendered inside the same block as the missing control, so even the
  error was invisible. Registration and editing now have their own rules, and
  both modes are covered by tests. Reachable only by an R&D User, on a draft.
- **Re-saving a contact already on the account sent no code, while the screen
  said it had.** A member of staff signed in to the portal as the data
  principal they also are, opened the account page, pressed save on the mobile
  already shown there, and waited at a code box for a message that was never
  going to arrive. A code went out only when the digits *changed*, and the
  commonest case is the one where they do not: an administrator had set the
  number on the register, so the edit box opens pre-filled with it. A code now
  goes to any contact left unconfirmed, whether or not it changed; a contact
  that has already answered one keeps its confirmation and is sent nothing,
  including a second email, which used to unconfirm itself on every save. Both
  account pages now say which of the two happened, read off the saved row.
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
  roles ([monitoring.md](docs/operations/monitoring.md)).
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
- **Two portals**: the data principal's portal (`frontend/portal`, port 3001)
  split out of the staff console (`frontend/console`, port 3000). Nothing a
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
