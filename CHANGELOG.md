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

### Added
- **Part of a name finds a person again, without the name leaving its seal.**
  Sealing the names had narrowed the users list, the requests search and the
  audit trail's About picker to whole contacts. Migration 0030 adds
  `full_name_ngrams`, `submitted_name_ngrams` and `nominee_name_ngrams` —
  `text[]` of the keyed hashes of every three-character run, under GIN —
  backfilled by opening each sealed name once through the key service. A search
  asks for every run of the term in one row: three characters up, case, spacing
  and accent composition ignored. What that costs is written beside the field
  map: a set of runs leaks letter statistics a single hash does not, so it is
  three name columns and never a contact; a contact is still matched whole.
- **The key service hashes and answers searches.** `/bulk_hash` hashes the named
  fields of a batch; `/search` says what to look for when the whole value is
  known, `/search_ngram` when part of it is, and a term under three characters
  is refused rather than answered with an empty list. `/bulk_encrypt` gained
  `with_hash` and `with_ngrams`, both off by default. The hashes are the
  platform's to the byte — the labels and the normalisation are a contract
  between the two codebases, so people can still sign in while the service is
  unreachable — under `DKMS_HASH_KEY`, which must equal the API's
  `BLIND_INDEX_KEY` and is refused at startup outside development if it is
  still the example one.
- **The database reference is generated, not written.**
  `docs/tools/generate-schema-docs.py` reads PostgreSQL's catalogues on a
  scratch database replayed from the migration chain and writes the inventory,
  the column and enum references and the source of all eleven diagrams. At
  0030: 32 tables, 426 columns, 42 CHECKs.
- **Personal data is encrypted on its way into the database, and opened only
  where a person reads it.** Every repository write of a column in
  `ENCRYPTED_FIELDS` goes through `seal()` — one call to the key service per
  row, however many columns — and the database holds `SE::…` where the value
  was: names, employee ids, a request in the principal's own words, the
  office's notes and reasons, ticket messages, file names, the address a
  consent came from. Migration 0027 widened those columns to `text`, recreating
  `v_current_consent` around the one it depended on. The API serves the
  ciphertext as stored. Each portal's API client walks every JSON response,
  reads the data type off each envelope, and opens every sealed value in one
  call to its own `/dkms/decrypt` — so no page knows which of its fields are
  sealed, and a table of two hundred rows is one round trip. The backend opens
  a value in exactly four places, each where it hands one to a person: the
  greeting in a message, the contact a ticket goes to, the export CSV, and the
  response package. The key service listens on `32688` at `/bulk_encrypt` and
  `/bulk_decrypt`; its first paths still answer. Walked live: a public rights
  request lands as `SE::` in the row, comes off the wire as `SE::`, and reads
  as the person wrote it on the console page; a staff invitation greets its
  recipient by name.
- **The lookup columns are sealed too, behind a blind index.** `email`,
  `secondary_email`, `mobile`, `username`, the nominee's contacts and a
  request's `submitted_contact` were left plaintext because the platform
  finds rows by them - sign-in, "is this address taken", a code to a mobile,
  a nomination found by the nominee's contact. Each now carries an index
  column beside it, `HMAC-SHA256(normalised value, BLIND_INDEX_KEY)`,
  deterministic so it can be unique-indexed and looked up and opaque without
  the key; every lookup goes through the index and the value itself is
  ciphertext (migration 0028: the columns, a Python backfill, every uniqueness
  rule and the one cross-column trigger moved onto the indexes). Date of birth
  is sealed and the section 9 test moves to `minor_until`, the one date kept
  in the clear. What was given up is partial search (given back by migration
  0030, above): the users list, the requests list and the audit lookup find a
  person by the whole contact, or
  by reference, uuid and project as before, and not by a few letters of a
  name; the fields say so. `scripts/reseal.py` sealed every row written before
  the switch, and `--check` reports zero plaintext.
- **The audit trail carries no words of anybody.** The client address is
  written as its blind index; the invited email is not written (the row's
  `user_id` names the person); the free-text reasons that eight events copied
  into `detail_json` are replaced by `reason_given`, with the reason itself in
  the sealed row it belongs to. A static test fails the build on the next
  string that would carry one ([ADR 0015](docs/decisions/0015-nothing-erasable-in-a-trail-nobody-can-erase.md)).
  Rows from before stand as written: the chain hashes `detail_json`, so
  rewriting them would break the property the trail exists for.
- **Every personal-data endpoint is tested over HTTP, and the build knows
  which ones.** `tests/http/` drives the application through `httpx` with the
  real database: a world is built through the API - purpose, processor,
  project, notice, source, site, link, a principal who registers and
  consents, an export, an import - and then every one of the 159 endpoints
  the documentation lists is called, over the office's rights flow, a
  nominee's, the tickets, the messages, the trail. Each response passes one
  contract: sealed fields are `SE::…` or null, nothing under a contact's name
  looks like an address, and the call is recorded. The last file asserts that
  the ledger covers the documented list, that nothing the suite saw sealed is
  undocumented, and that every sealed column in the database holds only
  ciphertext after all of it. Each portal's API client has the mirror test
  against MSW - a sealed body comes out opened in one call, nothing else
  changes - and a browser spec checks the pages that show people: the API
  answered sealed, the page shows the person. Found on the way and fixed:
  the ticket brief and the contact log copied a person's contacts into jsonb
  in the clear (now the sealed values, opened only for the mail's prose);
  a collection's assets 500ed when the manifest gave no `storage_ref`; the
  audit search still pattern-matched sealed names, finding nothing and
  scanning for it.
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

### Changed
- **The documents catch up with the key service.** Most of `docs/` had last
  been read for content before sealing existed; the move into `docs/` changed
  paths, not words. Every document was checked against the code at `daca825`
  and brought level: four services where three were drawn, 30 migrations,
  port 32688, the database named `cmp`, where sealing happens in a request and
  in a transaction, what the portals open, and every setting the four
  processes read. New: ADRs [0016](docs/decisions/0016-personal-data-sealed-by-a-separate-key-service.md)
  (the key service), [0017](docs/decisions/0017-lookup-by-keyed-hash-and-name-ngrams.md)
  (keyed hashes and name n-grams) and [0018](docs/decisions/0018-pip-and-a-virtualenv-no-containers.md)
  (no containers), with dated amendments to 0001, 0002, 0005, 0007, 0012 and
  0013; [docs/security/encryption-at-rest.md](docs/security/encryption-at-rest.md);
  and [docs/dkms/adding-a-personal-field.md](docs/dkms/adding-a-personal-field.md),
  the nine places a new personal column touches. The superseded coverage plan
  and the frontend decryption stub are removed, and the restructure runbook is
  in `docs/history/`. Where a document found the code short of its own
  intent - the portals' decrypt route, `reseal.py` and the append-only
  triggers, the worker's key-service request - it says so and marks it under
  review.
- **The keyed-hash columns are called `*_hash`.** 0028 named them `*_idx`, which
  described what an index is built on and hid what the column holds, and six
  ordinary btree indexes end in `_idx` too. Migration 0029 renames the eight
  columns, the indexes that quote them and the one trigger function whose body
  does; same values, same uniqueness, no backfill. A test holds `BLIND_INDEXED`
  and the migration together.
- **`/ready` reports the key service.** Nothing personal can be written or read
  without it, and no message can be addressed, so an API that cannot reach it
  is not ready. The `encryption` check names the URL and the reason.
- **Each portal decrypts with the key service `DKMS_URL` names, and only that
  one.** There is no fallback to a local instance: the service that opens a
  value is the one that sealed it. Unset, the route answers 503 and the log says
  what to set.
- **Only the contract travels to the key service.** `{data, key, method}` and
  nothing beyond it, from the API's request path and from both portals, so any
  service that implements the contract can stand behind this one. Only values
  needing the work are sent: an already sealed value is held back from an
  encrypt, only sealed values go to a decrypt, and a value that comes back
  unchanged is reported naming its field. The worker's synchronous path still
  sends `on_error`; see [docs/dkms/backend-api.md](docs/dkms/backend-api.md).
- `PUBLIC_BASE_URL` defaults to port 3001, the portal, in the setting and in
  `.env.example`. At 3000 every link the API put in a message to a person
  landed on the console, which has none of those pages.
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

### Fixed
- **An unknown age is no longer an adult, and a child is refused (S2-01).**
  `cmp_is_minor()` answers NULL when it does not know and says callers must not
  treat that as adult; the consent gate tested `is True`, so every account
  created through a link - none of which was asked - consented as one. Until
  the guardian route exists there is one lawful answer to a child under s.9(1),
  so `capture` now records nothing, grant or refusal, from an unknown age
  (`age_required`) or from a child (`consent_minor_not_permitted`), whatever the
  purpose's `permitted_for_minors` says - that flag is s.9(3) and never stood in
  for the guardian. Sign-up and `POST /c/{token}/register`, which now asks for a
  date of birth too, create no account for a child and spend no use of the
  link. The refusal names no guardian route, and sign-up's hint stops implying
  one. The portal asks an account with no date of birth for one at its next
  sign-in, before any page but consents and requests, which stay open because
  withdrawing and making a request are not consents; the consent-link page asks
  between the code and the notice. `PATCH /me` checks the date as sign-up does
  (in the past, after 1900) - since 0028 sealed the column the API is the only
  place that rule can live, and this route never applied it. The rule is one
  module, `cmp.domain.users.age`, and the test is always the database's. The
  seeded data principal is an adult, on a new database and an existing one.
  Both portals' generated API types are regenerated, catching up with three
  earlier `openapi.json` changes they had missed.
- **A message that cannot open its recipient says so, and is retried.** Every
  contact is sealed and the worker opens it on the way out, so a worker that
  cannot reach the key service sent nothing while every request answered "a
  code has been sent". `deliver()` now logs `message.not_sent` once, naming the
  junction and the service and never the address, and every message task
  retries on `DkmsUnavailable`; a service that blinks no longer loses somebody's
  sign-in code.
- **A sealed value nothing can open says why.** With `DKMS_ENABLED` false in the
  worker and the rows sealed, the ciphertext passed through as a contact, had no
  `@`, was taken for an SMS number, and every sign-in failed with "'mfa_code' is
  not sent by sms". Sealed values with the service switched off now raise
  naming the setting and both processes it must be true in; a value with the
  prefix whose envelope does not parse raises; and `deliver()` refuses a
  recipient still sealed after opening, before the channel is chosen. The prefix
  is one constant, `fields.PREFIX`.
- **Every response the portals receive opens.** Five audit-entity labels were
  built in SQL as a sealed name concatenated with plain text, a string that
  starts with the prefix and is not an envelope, and the key service refused the
  whole batch it sat in. A label that names a person now comes as
  `entity_label_parts`, the name sealed among plain pieces; a static test fails
  the build on the next `||` against a sealed column. The portals' walker
  retries a refused batch one value at a time, so one bad value no longer costs
  the rest.
- **A key service on another host is reachable, and says so when it is not.**
  The decrypt route sends exactly the contract, with a ten-second bound, and a
  failure logs one line naming the host and the status, never a value; the page
  renders with the ciphertext showing rather than failing on every screen. The
  key service binds to 127.0.0.1 by default, and its `.env.example` says when to
  bind the interface callers use.
- **Foreign ciphertext is labelled by its field.** The walker reads a value's
  type off this implementation's envelope; against another service's it read
  nothing and left the value sealed in silence. It now falls back to the field's
  name (`lib/dkms/field-types.ts`, a mirror of `ENCRYPTED_FIELDS`), and a field
  in neither is reported by name, once.
- **Every auth page sends its visitor where they belong.** A person already
  signed in reaches the page they were after; one halfway through the second
  factor goes to the code step; the code step with no session goes back to the
  start; a data principal on the console goes to the portal and staff on the
  portal go to the console. `AuthPageGate` in each portal acts on
  `useSessionState`. The portal's `/sign-in/verify`, which answered 404,
  forwards to the console's code step with its query string.
- **The notification bell links only to what its reader can open.** The staff
  feed was every event for every member of staff, and for an R&D user all 26 of
  its links opened pages the role cannot see. It is scoped by the project
  register's own predicate; events with no project go to the DPO in full and to
  the administrator only for lockouts.
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
