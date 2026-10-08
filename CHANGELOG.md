# Changelog

Notable changes to the platform, newest first. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Dates are the dates
the work landed on `refactor/frontend-architecture`; nothing has been tagged
as a release yet.

## [Unreleased]

### Added
- **Rights tickets, redesigned: a guided path and a review step**
  (2026-10-08). The holders card is a path - find who holds the data, choose
  who answers, send tickets, wait for answers, review answers - over one
  table (holder, state, answer by, last activity, next) and one ticket dialog
  with what the holder was asked, their answer, the messages and what may be
  done now: the main action first, the rest under More. The server says each
  ticket's state in words, whether it is overdue (its date has passed, the
  end of that day) and its moves; the console holds no copy of the rules. A
  holder's answer now waits for the DPO to **accept** it or **send it back**,
  and only an accepted answer counts toward closing the request or an erasure
  being done (migration 0048). A withdrawn ticket can be **reopened** with a
  new date, and a holder found by mistake **removed** before it is sent
  anything. *Escalate* is now **Send final reminder**, offered only once a
  ticket is overdue; overdue tickets are reminded every day. The summary's
  Next points at the holders card while a holder needs the office, and
  *Move to awaiting holders*, which sending tickets does by itself, is no
  longer a button. *My tasks* groups rights tickets into to do, waiting on
  the Privacy Office and done; giving the answer is its own form - what was
  done, what you hold, proof - and writing to the office no longer closes the
  window. Holders are told when the office records or accepts their answer,
  and when a ticket moves away from them. Plain words throughout: no table
  names on screen, *in the console* for *on the portal*. Phase 2 - external
  holders answering on the portal by a one-time code, temporary logins,
  per-holder instructions - is planned in
  `docs/domain/rights-tickets-redesign.md`.
- **Log an incident asks what is known so far** (2026-10-08). Eleven
  optional questions under the incident's details: is it a cyber attack
  (Yes - reportable to CERT-In / No / Not known yet; yes creates the CERT-In
  duty at once), where it started, how it was found, systems affected, what
  happened, how much is affected, countries involved, kinds of personal data,
  whose data, our entities involved or affected, and third parties involved -
  all free text but the first. Kept as logged, sealed, shown under the
  breach's Details. Migration 0047; the status-only trigger now holds every
  column but the status.
- **Emails for every module, with copies and files** (2026-10-08).
  `docs/notifications/` is the notification strategy for email: the rules,
  the plan, and one file per module - users, projects, consent, rights,
  breach - giving each email end to end (when, to, CC, attachment, the
  default subject and body, the task and where it is queued from), generated
  from the code. Thirteen new emails: a project submitted (every DPO),
  approved, sent back or closed (its owner, with the reason), a collector
  assigned (the DCO); a rights request arriving from outside (every DPO,
  never her words), a daily list of requests overdue or due within a week,
  a grievance about the DPO (every administrator); a breach duty about to fall
  due and again overdue, once each, checked every five minutes, and a breach
  ticket answered (every DPO); a role changed, console access ended, cover
  arranged (the people concerned). Every email may now carry copies: the
  Privacy Office sets up to five per email in Message templates → Copy to,
  never on one with a code, a link or a person's own record (migration 0046,
  `message_copy`, sealed). Emails may carry files, only what the recipient
  owns: her consent record on the consent receipt, the office's file on a
  rights ticket message to its holder; a rights response stays
  download-only.
- **A breach's people from a list sent to us** (2026-10-07). A breach whose
  people were not on the platform could never close: the notice is owed to
  everyone listed, and nobody could be listed. On People & notices, Add
  people from a list takes one of two CSV templates - people (name, email,
  mobile) or asset IDs (the platform's or the capture tool's, with the
  source code where two sources share one). Check the file counts what it
  would add and names every unreadable row, writing nothing; Add takes the
  rest. Somebody already on the platform is listed as themselves; anybody
  else is kept as a contact of that breach alone - name, email and mobile
  sealed, listed once by blind index - and is sent the notice by email and
  SMS in its own words (no account to point to). People in an asset who
  consented to nothing cannot be traced and are counted. Contacts count
  toward Principals notified like everyone listed, so the duty completes and
  the breach can close. The file is not kept, only its sealed name, hash and
  counts. Migration 0045: `breach_upload`, `breach_contact`;
  `breach_notice_delivery` addresses an account or a contact. Four routes
  under `/breaches/{uuid}/affected/upload` and `/affected/contacts`.
- **Notice templates** (2026-10-07). The DPO writes notices before the
  projects that will use them exist, as many as they like: New notice
  template sits on the DPO's dashboard and at the top of Notices, and the
  templates are listed in Notices' new Templates tab. Each template has a name, the Rule 3 links and
  DPO contact, an audience, purposes from the register and its text in each
  language, under an ID the database mints (`TPL-0007`). Nothing on a template
  is approved or served; it is edited in place and retired, never deleted.
  The DPO gives the ID to the study's R&D User, who on their project chooses
  Use a notice template, looks the ID up to see what it carries, and makes the
  project's own draft notice from it - a copy, with the project's own code and
  nothing approved, then approved and published as usual. The notice shows
  the template it came from; the template's page lists the notices made from
  it, and a later change to the template reaches none of them. Migration
  0044: `notice_template`, `notice_template_purpose`,
  `notice_template_language`, `notice.template_id`. Nine DPO-only routes under
  `/notice-templates`, `GET /notice-templates/by-code/{code}` for whoever brings
  notices, and `POST /projects/{uuid}/notices/from-template`.
- **Documents with a rights request** (2026-10-07). Signed in, a data
  principal can send documents with her request - a proof of who she is, a
  letter, a screenshot: PDF, PNG, JPEG, text or Word, 25 MB each, at most ten,
  while the request is open. The portal sends them once the request is
  recorded, and one refused does not undo it; her request card lists them.
  The DPO sees them under the request text, each downloadable, every download
  on the trail. Migration 0043: `rights_request_attachment`, append-only by
  trigger and grant, the name sealed (FILE_NAME), traced to her for a
  database breach. `POST /me/requests/{uuid}/attachments` (her own, open
  request; checked before the file is stored) and
  `GET /requests/{uuid}/attachments/{attachment_uuid}`.
- **Email: five settings, one designed template, and a document of every
  message** (2026-10-06). Email is configured by `SMTP_SERVER`, `SMTP_PORT`,
  `SMTP_USERNAME`, `SMTP_PASSWORD` and `SENDER_EMAIL`, and nothing else: with
  no server it goes to the local outbox; the port decides the connection
  (465 SSL, 587 STARTTLS - refused if the server cannot - 25 plain); a login
  only when a username is set. Every email is laid out in one template -
  the organisation's header, the subject as its title, the content with
  codes in a highlighted box, links as buttons, headings, lists and small
  print, and a footer - sent as HTML with the plain text beside it, escaped
  throughout; in development each is saved to `var/outbox-html/` to open in a
  browser. A refusal no retry will mend - a wrong login, a 5xx, an untrusted
  certificate - is `EmailRejected` and fails at once; an unreachable or busy
  server is still retried. Production refuses an empty `SMTP_SERVER` or a
  placeholder sender. `scripts/send_test_email.py` sends a sample.
  `docs/email/` explains it all in tables, and `docs/email/messages.md` -
  generated from the code - lists all 25 messages with the task and line
  that send each and where it is queued from.
- **Files kept with an incident** (2026-10-06). Log an incident takes the
  email that reported it, a screenshot, a chat or a log - each marked Email,
  Proof, Chat or Other - and sends them once the incident is logged; the
  breach page's new **Attachments** tab adds more while it is open. PDF, PNG,
  JPEG, text, CSV, .eml, .msg or Word, 25 MB each. Evidence: the name and note
  are sealed, the hash and size kept, and a file is never replaced or removed
  (append-only by trigger and grant); every download is audited and carries
  both hashes. Migration 0042 (`breach_attachment`); routes
  `POST /breaches/{uuid}/attachments` and
  `GET /breaches/{uuid}/attachments/{attachment_uuid}`, the DPO's and hidden.
- **The first thing each role starts, on its dashboard** (2026-10-06): the
  DPO's **Log an incident** - thirty minutes run from first noticed - an R&D
  User's **Register a project** and an administrator's **Provision an
  account**, each opening the same form as its page. The collection roles get
  none: what they begin belongs to a project or a site.
- **The breach register can be searched and filtered** (2026-10-06). Search
  by either reference (INC- or BR-), the title or where it occurred; filter by
  validation, duties overdue or due within 24 hours, recent activity (24
  hours, 7 days, 30 days), and tickets open or past their answer-by; sort by
  the most recent activity or by what is due soonest. The filters are kept in
  the address. The register now carries each incident's `last_activity_at`
  (from the audit trail: the breach, its notices and its tickets) and its
  `tickets_open` and `tickets_overdue`, shown as two new columns.
- **The seed accounts on the console's sign-in page, in development.** With
  `DEV_SHOW_CODES` on, a **Development accounts** panel lists the seed logins
  that are active and still have the seed password, with the password and a
  **Use** button. Checked against each account's current password
  (`GET /dev/seed-accounts`, development only): a changed password or an
  account the seed did not make is never shown. `DEV_SEED_PASSWORD` and
  `DEV_SEED_LOGINS` configure it; `scripts/seed.py` reads the same password.
- **Breach-only logins, and colleagues who follow the same flow (S3-09,
  [ADR 0023](docs/decisions/0023-breach-tickets-and-breach-only-logins.md)).**
  A breach ticket can go to somebody with no console login: the DPO chooses
  **Someone without a console login** and gives a name, an internal email and
  optionally a mobile. Active staff get an ordinary ticket; a data principal's
  account becomes `breach_holder` while the grant lasts; nobody at the address
  gets a new pending account made for the breach. They are sent
  `breach_ticket_access` (reset link and code, naming no breach), set a
  password, sign in with the emailed second factor - always required for this
  role - and land on **My tasks**: tickets, notifications and profile, nothing
  else. A holder can **Add a colleague** with a note while their ticket is
  open; the colleague gets their own ticket under the same domain check and
  lookup, and the adder's answer never says whether an account existed. Access
  ends when the breach closes, when the DPO withdraws the ticket, or when an
  administrator chooses **End temporary access**; `person_type` is never
  touched (since 2026-10-06 the login stays, read only, until an
  administrator removes it - see Changed).
  The role is never given by hand. The Tickets card marks temporary logins and
  their state. Migration 0041 (`breach_holder` enum value;
  `breach_temporary_access`); route `POST /breach-tickets/{uuid}/colleagues`.
- **Breach tickets (S3-08,
  [ADR 0023](docs/decisions/0023-breach-tickets-and-breach-only-logins.md)).**
  The DPO asks the people who must act on a recorded breach: **Assign a
  ticket** to a member of staff on `BREACH_TICKET_EMAIL_DOMAINS`, with an
  instruction and an optional answer-by date. They find it on **Tickets** - the
  breach reference, the instruction and the thread, nothing else from the
  register - write and return it (done, partial or failed); only the DPO closes,
  sends back, withdraws or reopens one, and a breach does not close while a
  ticket is open. Their email names no breach (`breach_ticket_waiting`). One
  ticket per person per breach; every word sealed; the trail carries no words.
  Dashboards count returned and overdue breach tickets and list each holder's
  own. Migration 0040; routes `/breaches/{uuid}/tickets/*` (DPO, hidden) and
  `/breach-tickets/*` (resource `breach_ticket`, OWN).
- **The organisation's board within thirty minutes of first noticed (S3-07,
  [ADR 0022](docs/decisions/0022-an-incident-first-and-a-breach-on-a-yes.md)).**
  Every incident logged now owes the organisation's board a report: a duty
  anchored at first noticed and due `BREACH_ORG_BOARD_MINUTES` (30) later,
  stored then. Validation never touches it. **Brief for the organisation's
  board** drafts what to say - counts, clocks, nobody's name - and prints; the
  DPO records when the board was told and to whom (`reported_to`, sealed,
  required by trigger). It counts on the dashboard and blocks closing like any
  duty. Migration 0039; incidents logged before it have no such duty.
- **An incident first; a breach is recorded on a yes (S3-06,
  [ADR 0022](docs/decisions/0022-an-incident-first-and-a-breach-on-a-yes.md)).**
  "Record a breach" is now **Log an incident**, with an `INC-` reference from
  its own sequence; the determination is presented as **validation**; and the
  first *yes* records the breach - a `BR-` reference in `breach_recording`,
  once, never withdrawn - in the same transaction as the duties it starts.
  Sending the principals' notice is refused until then
  (`breach_not_recorded`); deriving, drafting and the Board's documents are
  not. Principals and the Board are given the BR. Migration 0038 backfills
  existing breaches with a *yes* under their existing `BR-` string.
- **My nominations** has its own page on the portal, and the console's
  navigation opens each role's sidebar with **Your work** - its daily
  destinations in order. Dashboards gained **Approved projects ready to
  collect** (DCO, RCO) and **Waiting for DPO review** (R&D User) (UX review
  2026-10-05).
- Filters the dashboard links need: `GET /requests?due_soon=1`,
  `GET /notices?languages=unapproved`, `GET /users?person=<uuid>`.
- **A person corrects their own name from the profile**, on the portal and
  the console (**Change** beside the name). `PATCH /me` already accepted it; the
  pages now offer it. The name is sealed, stays searchable by part, and the
  change is audited without the name. The rest of correction (S3-05) is
  deferred to a later release.
- **The Board and CERT-In (S3-04).** **Documents for the Board** drafts the
  initial intimation (Rule 7(2)(a)) and the detailed report with all six items
  of 7(2)(b) from the register, at any point, naming what it does not yet hold;
  item (vi), the account of notices, says in words when none has gone. The
  platform never submits: the DPO files through the regulator's channel and
  records the submission with its reference, as for CERT-In's six-hour duty.
  The DPO's dashboard lists every open breach with each duty's clock and counts
  **Breach duties overdue** and **outstanding**. `GET
  /breaches/{uuid}/board/intimation` and `.../board/report`.
- **Notify the people a breach touched (S3-03).** The DPO drafts the five
  things Rule 7(1) requires - filled first from the assessment - and approves
  them; approval is refused while any is empty. Send writes the notice to each
  listed person's account at once (her portal's notifications link to a new
  **Personal data breach notices** page) and queues her email and SMS, which the
  worker sends through the new `breach_notice` junction and records. A resend
  adds only what is missing, an update is a new version sent to everyone, and
  every attempt on every channel is on the record - the account the Board's
  report needs. *Principals notified* completes by delivery and reopens for
  people listed later. Migration 0036; `/breaches/{uuid}/notices`,
  `GET /me/breach-notices`.
- **Who a breach touched, derived (S3-02).** A breach's page derives the
  people it touched from where it happened - everyone in files exported to a
  processor, everyone captured in a data source's assets, or everyone with a
  row in the chosen tables of the platform's own database within a window -
  previews them, and the DPO confirms the list as a revision, leaving out whom
  the records wrongly include and adding by hand whom they cannot show. Nobody
  listed is removed; a later revision adds only the newly found. Processor and
  source derivation read the same holdings relation a rights request reads,
  moved to `db/repositories/holdings.py` and read from both ends. Migration
  0035; `GET/POST /breaches/{uuid}/affected`, `POST .../affected/preview`.
- **The breach register and its duties (S3-01).** There was no breach concept
  at all. The DPO now records a breach as it was noticed - `detected_at`,
  `began_at` and, with a determination of *yes*, `became_aware_at`, all
  entered and never defaulted - and where it occurred. Whether it is a personal
  data breach under s.2(u) is a determination a person records with reasoning,
  never computed from encryption; revisions are new rows. The assessment holds
  every fact Rule 7 asks for, revised by new rows, and per data category whether
  it was sealed and whether its key was exposed. Each statutory duty is its own
  record with a due time stored once: CERT-In six hours from detection (marked
  separately), the Board's initial intimation and the principals' notices
  without delay, the Board's detailed report 72 hours from awareness or the date
  the Board allows. A submission is recorded with the regulator's reference; the
  platform never submits. A breach closes only when determined and every duty is
  done or not applicable. DPO only, and hidden: every other role gets 404.
  Migration 0034; `/breaches`; console **Breaches**;
  [ADR 0021](docs/decisions/0021-a-breach-is-recorded-and-its-duties-tracked-never-submitted.md),
  [breaches.md](docs/domain/breaches.md). "Without delay" is flagged against
  `BREACH_WITHOUT_DELAY_TARGET_HOURS`, left unset until Legal chooses a number.

- **Structure across both apps: tabs, a menu, collapsible cards.** New
  accessible primitives - `Tabs` (arrow keys, one tab stop, the tab kept in
  the address), `Menu` (the menu-button pattern) and `CollapsibleCard`
  (remembered per browser) - with no new dependency. The header gains an
  account menu (profile, help manual, theme, sign out); the console sidebar's
  groups fold away, keeping the group of the current page open; Your account
  is tabbed (Contacts, Active sessions, and in the console Password), with
  sessions as a table naming the device, a "Show all" fold and "End all other
  sessions"; a rights request's clock and path and a project's history fold
  away. The mobile sign-out browser test, which could not reach the sidebar
  drawer, now signs out through the account menu and passes.
- **A help manual in the console and the portal** (`/help`). Laid out like a
  product manual - a numbered table of contents that follows the reader,
  numbered steps, notes and warnings, questions and answers, a glossary, and a
  closing "Have any questions? Contact us" panel with the Privacy Office's
  address from the public `/rights` answer. Every instruction quotes the
  screen's own words as a label. The console's 24 sections open filtered to
  the reader's role; the portal's 15 are written for data principals. Both
  search as you type, work on a phone, and are open without signing in - the
  sign-in pages link to them - and the console's header and command palette
  open it.
- **A backend developer guide** (`docs/backend/`): one folder, in reading
  order, written from the code - the package map, a staff write and a
  public consent traced hop by hop, every security control, how tables are
  created and what the database refuses, adding a feature from migration to
  documented endpoint, and a list of where the code departs today from the
  rules the other documents state.
- **Demo data through the API** (`scripts/seed_demo.py`). After `seed.py`,
  it builds ten and more of everything - staff invited by the administrator
  and activated by their invitation codes, processors, sources, purposes,
  projects with published notices, sites, consent links, data principals who
  register through the links and consent (some in part, one declining, two
  later withdrawing), exports, imports, rights requests, nominations and
  cover - each through its endpoint as the role whose job it is, so the
  permission matrix, sealing and audit apply. The application runs
  in-process; codes are read off the task queue. Runs once per database,
  local/test only.
- **The console finds its way faster.** A command palette (⌘K / Ctrl+K)
  jumps to any page the role has - read from the same `me.nav` the sidebar
  is, so it offers nothing the server did not grant - with the pages visited
  last and a theme and sign-out action. The header gains a breadcrumb, a
  search trigger and a notifications bell, and the desktop sidebar folds to
  a rail of icons, remembered per browser. The sidebar, breadcrumb and
  palette read one list of destinations (`components/layout/nav.ts`).
- **List searches follow the typing.** The shared search box searches once
  typing pauses and at once on Enter, clears with × or Escape, and follows
  the search in force when its chip is removed; Projects now uses it. The
  users register still searches on Enter only - it matches whole contacts,
  and a fragment would only send pieces of someone's email. Data sources no
  longer shows an empty box over a list a link had filtered.
- **The portal narrows her requests.** From six requests up, "Your requests"
  offers All / Open / Closed with counts (open as the server says,
  `closed_at`) and a search by reference, kind or words, done in the browser.
  A jump between a grievance and the request it disputes widens the filter
  when the card it goes to is hidden.
- **Cross-border control, enforced at export (S2-04).** A purpose carried
  `cross_border_permitted` and nothing read it. Each export row now has a
  destination - the processor running its site - and a processor has a
  `location_country`; before anything is written every destination is checked.
  India goes as domestic; abroad goes under s.16 only if the country is not on
  the restricted list and every purpose the people granted permits it; a
  processor with no recorded country is refused, as decided with the product
  owner. One failing destination refuses the whole export (422
  `transfer_refused`, every cause named), audited in its own transaction with
  the processors and none of the people. An export that goes records each
  destination, country and ground on `export_log.transfer_basis`, and each
  `export_line` its processor and country. The Government's list is data the
  DPO keeps - `/restricted-countries`, listed with its notification and lifted
  once, never India, one active listing per country; its contents are Legal's.
  Migration 0032, [ADR 0020](docs/decisions/0020-cross-border-transfer-checked-at-export.md).
  The console's processor form takes a country, the list shows it, and the
  Processors page carries the restricted list for whoever may keep it. The
  seed's processors are in India.
- **Erasure that erases (S2-03).** An erasure decision used to change her
  disposition on `asset_consent` and nothing else; the recording stayed at the
  lab and the platform kept its pointer to it. Applying a decision now
  quarantines at once - out of use, recoverable if the decision was a mistake -
  and an executor (`cmp.domain.rights.erasure`) carries an erase, a redaction
  or a retention past its floor out store by store. The platform never holds
  an asset's bytes, so the stores are the holder's copy, done when the holder
  of the asset's source returns its ticket, and, for an erasure, the
  platform's pointer, `data_asset.storage_ref`, cleared - a redaction keeps
  the asset for the others in it. Every attempt is a row in
  `rights_item_execution`, append-only: done, waiting, failed or held, and
  why, never a value about her. Only when every store is done does the item
  get `executed_at` and her disposition read erased or redacted, which is what
  S2-02's guard reads before a response may be complete. Anything waiting or
  failed is retried by the daily sweep, on every ticket return, and on
  `POST /requests/{uuid}/scope/{item}/execute`, and stays on the request until
  it succeeds. **Legal holds** (`/legal-holds`, DPO only, resource
  `legal_hold`) stop erasure of an asset or a person, with a sealed reason;
  placed once and released once, by trigger, and release carries on at once.
  Consent artefacts, the audit trail, the export files processors were sent
  and the response packages she was given are never touched - the record of
  what happened ([ADR 0019](docs/decisions/0019-erasure-reaches-every-store-but-the-record.md)) -
  and the response says so. Migration 0031. The console's scope card shows
  each store as it stands, with "Try again now" and placing or releasing a hold.
  Backups are not covered: there are none yet (P-03), and whether one holding
  an erased item is scrubbed or left to expire is waiting on Legal.
  `docs/tools/personal-data-scan.py` and `pii-fields-and-endpoints.py` no
  longer drop a module they were not told about.
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
- **Three requests, about everything** (DPO, 2026-10-07). A new rights
  request is access, erasure or a grievance - correction is no longer offered
  on any form or channel, nor as a reclassification; a correction to a name is
  made from the account. A request is about everything held on the person:
  the portal's consent picker and "Ask about this consent" are gone, and the
  API refuses `consent_uuid` on a new request. Requests made before - a
  correction, or one confined to a consent - are shown and handled to the end
  as they were.
- **The request page, for the DPO** (2026-10-07). Refusing at step 4 is a
  button that says what it does ("Refuse this request", with the reason it
  asks for), not a grey line of text. The next step - In progress and the
  other moves - comes straight after classification, before the holders, and
  the summary's next move links to it; the response card has its own group.
- **A breach's page is in tabs, like a project's.** It had grown to eight
  cards in one column. Closing it - with what still stands in the way - now
  sits at the top beside its details; the work is in tabs in the order it
  runs: Duties (the default), Validation, People & notices, Tickets,
  Assessment, and a new Activity tab with every close and reopening. Duties
  and Tickets turn red when something there is late; a prompt leads to
  Validation until it is done; `#tickets`, `#notices` and the other old
  addresses open the right tab. On a phone the details follow the tabs, and
  every tab row now scrolls its selected tab into view.
- **A breach-only login stays, read only, when the holder's part is over**
  (decided 2026-10-06, amending ADR 0023's BD-16). When the breach closes or
  the DPO withdraws a holder's ticket, the grant ends but the account is left
  as it is: they can still sign in and read their ticket, and every write is
  refused as before. A person with another role keeps it. The Tickets card
  shows **Temporary login · read only**; asking a kept login again sends the
  "ticket waiting" email. The administrator's **End temporary access** is the
  one off switch: it puts the account back (switched off if made for the
  breach, `data_subject` otherwise), clears the password and revokes the
  sessions. The after-commit async hooks S3-09 added for revocation are gone
  again; the users route revokes after its commit, as for any deactivation. The
  access email (`breach_ticket_access`) says so: "When the matter is closed you
  can still read the ticket, but no longer answer it", in place of "The access
  ends when the matter is closed".
- **The UX review of 2026-10-05, package 4: records lead with where they
  stand.** The project page is one workspace - the next move and its blockers
  beside the project's details, then tabs for Overview, Setup, Consent,
  Collections & exchanges (new: the project's collections and exports) and
  Activity; each action once, on its card; old `#sites`/`#notices` links still
  land, and register rows open the project at their card. A rights request
  opens on its due date, current step, who has it and the next move, with the
  cards grouped beneath and Clock and path folded. On the portal, My requests
  cards are summaries until "Show details", a response ready to download
  showing either way.
- **The UX review of 2026-10-05, packages 1-3 and 5.** Truthful states (four
  consent states counted apart; subtle text at 4.5:1 in both themes; buttons
  that name the act); links that open what they name (filtered dashboard
  rows, a requester's account, a request's or consent's own card); back that
  returns where you were (`?from=`, the row you opened, Help's way back);
  dialogs that keep typing; per-role navigation and urgency-ordered queues;
  and the wording table - see `docs/frontend/best-practices.md` §18 and
  `docs/domain/roles-and-access.md`.
- **Routers no longer write or audit.** Writes and audit rows moved into
  domain services and SQL into repositories; `test_layer_boundaries.py`
  holds the line (review ARCH-5).
- **Lists keep their filters and page in the URL** (UX-5); a transition
  refreshes the notice it published (ARCH-3); the type contract catches
  removed and newly nullable fields (ARCH-2); the 93 files the portals share
  cannot drift apart (ARCH-4, the guard; the package is a tooling decision).
- **"Use an existing notice" offers every approved notice.** An R&D User was
  offered only notices on projects they had created, so a researcher's first
  study could never start from text the Privacy Office had approved for a
  colleague's - and the copy route answered 404 for a colleague's notice.
  `GET /notices/copy-sources` lists every approved or published notice, from
  every project, for the DPO and R&D Users, with only what the picker shows
  and without the old 100-per-status cap; copying accepts such a source
  outside the caller's scope. Drafts stay their project's own, the copy still
  brings no legal approval, and nothing else an R&D User reads widens.
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
- **Log an incident offers every processor and data source, A to Z.** The
  pickers asked for the newest fifty, so an older processor - the seeded SEED
  among them - could not be chosen once the register grew. They now load the
  whole register by name (every page, 200 at a time), sort it A to Z ignoring
  case, and narrow it as you type. The same pickers set a scope in "Who it
  touched".
- **Sending on a ticket no longer leaves a "not saved" warning behind.** The
  dialog guard counted any typing since the dialog opened, so after a message
  was sent - or the DPO sent back or withdrew a ticket with a reason - closing
  the window asked about changes already saved. A save that keeps a dialog
  open now marks it clean (`useDialogSaved`, used by the ticket reply box and
  the DPO's ticket moves); typing again makes it ask again. And a holder's
  **Send** now closes the window, as a return does, with "Message sent" -
  on breach tickets and rights tickets alike; the DPO's window stays open.
- **Storage is checked before use.** `STORAGE_BACKEND=object` (a stub) is
  refused at start-up and `/ready` checks that storage can be written (SCALE-5).
- **A refused decrypt batch is narrowed down**, not retried value by value,
  and a throttled or failing key service is not asked again (SCALE-4).
- **Lists of people sort by the names people read**, not the ciphertext.
- **A production build must be told the other portal's address** (ARCH-6).
- **The consent link keeps a person's progress**: an outage is not an invalid
  link, a spent code is not asked for again, and the code step offers another
  code and another contact (UX-3); focus, the phone drawer and `lang=` (UX-4).
- **A breach notice lost before the worker saw it is sent again.** An email
  or SMS whose task the broker dropped after the commit stayed queued for ever,
  and Send skipped anything queued, so *Principals notified* could never
  complete. Send now queues again a delivery still queued fifteen minutes on.
  Found while weighing review finding SCALE-1 against the Sprint 3 code.
- **A returned ticket counts only when it says the work was done.** Any return
  used to count: a ticket returned "unable to erase" recorded the holder's copy
  as erased, and a correction could close complete on it. A return now says
  whether the holder did all of it, only part, or none - chosen, never
  defaulted, on the office's form and on the team's tickets page - and only
  "all of it" counts. Sending the ticket back asks again. Migration 0037
  (review 2026-10-01, DPDP-1).
- **A rejected import row changes nothing.** A manifest row wrote its
  collection before checking its consent reference, so a row reported as
  rejected could still create a collection or alter an existing one's declared
  count. Each row now runs in a savepoint (review 2026-10-01, SCALE-3).
- **An SMS gateway that hiccups no longer loses the message.** The HTTP SMS
  adapter raised httpx's own errors for a timeout or a dropped connection and
  `RuntimeError` for any non-2xx, none of which the message tasks retry, so a
  sign-in code to a mobile - or a breach notice - was lost on the first
  hiccup. A timeout, a lost connection, 429 and 5xx are now retried; any other
  refusal is not (review 2026-10-01, SCALE-2).
- **A failed request no longer reads as an answer on My consents.** The
  disclosures panel turned a failed request into "Not shared with anyone" - a
  false statement about her data under s.11(1)(b) - and the record trail into
  "Nothing recorded yet"; the purposes list and the served notice vanished.
  Each now says it could not load and offers Try again (review UX-2).
- **A notice with a mandatory purpose can be declined.** Decline everything
  answers every purpose No, and the server read that as refusing the mandatory
  purpose and turned it away - so the refusal the form recommended was
  impossible. Refusing everything is now a declined artefact; refusing only the
  mandatory purpose is still refused (review 2026-10-01, UX-1).
- `docs/tools/personal-data-scan.py --check` passes again. It had never been
  taught the keyed lookup hashes and name fragments migrations 0028-0030 added
  (`email_hash`, `full_name_ngrams`, `submitted_contact_hash`,
  `nominee_*_hash` and the rest). They are now a `derived` category - opaque
  without the key, but personal data an erasure must reach - and the personal
  data inventory lists the ones on `rights_request` and `nomination` it was
  missing.
- **A project has one notice in force.** Publishing superseded only earlier
  versions of the same notice code, so a notice brought in under a code of its
  own - "New notice", "Use an existing notice", an upload - could be published
  beside the one in force, leaving two, with consent links still serving the
  old text. Publishing now supersedes every other published notice on the
  project, and migration 0033 makes a second one impossible
  (`uq_notice_one_published_per_project`; it refuses to apply over data that
  already breaks the rule). The replaced notice's live consent links move to
  the new notice (decided with the product owner), so links already handed out
  keep working; consents already given keep the notice they were given under.
  Approving a project with several drafts publishes the newest, and another
  project's notice code is refused (`notice_code_taken`) - before, it made the
  notice a new version of that project's and could supersede it.
- **The project page offers its next move at the foot as well.** The "What
  happens next" moves and the header's actions are repeated in a "Next steps"
  card at the bottom of the page, so nobody scrolls back up to act; the top is
  unchanged.
- **Attaching purposes to a notice has one button.** "Attach" and "Done" sat
  side by side, and only one of them saved anything. "Attach" now adds the
  chosen purpose and keeps the dialog open for the next; the dialog's own
  close ends it.
- **Defects found preparing the first user acceptance cycle (13).**
  - *Withdrawing one purpose is not withdrawing the consent.* Every place that
    turned an artefact into a status read `is_withdrawal` alone, so a person
    who withdrew one of two purposes was shown, counted and exported as
    withdrawn, the purpose she still agreed to dropped out of exports, and the
    portal hid the control to withdraw the rest. Withdrawn now means a
    withdrawal left nothing granted - in the register, the project counts, the
    dashboards, exports and the rights brief, and on both frontends.
  - *A released legal hold lets the erasure finish.* The hold item stayed
    `held` after release, so the scope never completed; the next run records
    it done with the hold it waited for, and releasing a hold re-runs the
    erasures it had stopped. The console reads a done hold as "released".
  - *Cover can be arranged by the people who arrange it.* The grant-cover form
    listed colleagues from the users register, which only the DPO and the
    administrator can read, so a DCO or RCO was offered nobody.
    `GET /delegations/candidates` names the active accounts in the caller's own
    role.
  - *The audit CSV opens names.* Actor, subject and a label naming someone
    were written sealed (`SE::...`) into a file read outside the platform; they
    are opened in one key-service call for the file (`unseal_strings`).
  - *No link to a page the reader cannot open.* The bell, the dashboards and
    the audit trail linked every role to the same page for an event; a link now
    survives only when the reader's menu has its section. A subject's own
    account events link to `/account`, and a cover arrangement to `/delegate`.
  - *A polling tab no longer keeps a session awake.* The console's timed
    refreshes send `X-CMP-Background: 1`, which authenticates without sliding
    the idle window.
  - *Every role can be chosen.* The role list the console builds its forms
    from lacked DCO Admin and RCO.
  - *The portal says why a minor cannot sign up* on the date-of-birth field
    instead of a generic failure, the age prompt's "Add it now" goes to the
    account page, an under-18 account reads "we cannot record consent from
    you", and a nomination she is named in shows its real state rather than
    "In place" for every one.
- **Exports derive the holders of a person's data again.** Holder derivation
  for a rights request read the processor from the export's site, and since
  exports became one per project (0010) they name no site - so no export had
  derived a holder, and every rights request's holders came from assets alone.
  Each line now names its destination (0032) and the derivation, and the
  ticket's brief, read it from there.
- **A closed request never claims what did not happen (S2-02).** An erasure
  decision changes her disposition on `asset_consent` and deletes nothing, yet
  a request whose items were only applied could close as `complete` - which
  reads to her as "erased". A correction or erasure now closes complete only
  when what it asked for was carried out with evidence: every holder returned,
  every item done - a quarantine applied is its own evidence, an erase or a
  redaction needs the execution record S2-03 will write - and something done at
  all, not an empty scope nobody acted on. Otherwise it is `partial`, and the
  record she receives says what happened to each item ("quarantined: kept out
  of any use or release, not erased", "decided for erasure, not yet carried
  out") and names what is not yet done, in the file and in the mail. The
  partial headline no longer blames holders alone. The rule is one module,
  `cmp.domain.rights.execution`; the request detail serves its answer as
  `complete_blocked_by`, and the console's respond card holds Complete back
  with the server's reason instead of its own copy of the unreturned-holder
  rule. Access and grievance are unchanged.
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

### Security
- **A refused request keeps its evidence.** A failed sign-in's audit row was
  rolled back by the raise that followed it, and no 403 was ever recorded.
  Failed sign-ins and second-factor codes now commit their record before
  refusing (`with_evidence`), and every 403 - and the 404 a hidden breach
  answers with - is recorded as `auth.access_denied` (review 2026-10-01, SEC-3).
- **Guessing is counted by account and by address.** The lockout counts the
  account however it is named, not the text typed; failed attempts at sign-in,
  code sign-in and password reset also count against the address
  (`AUTH_FAILURES_PER_ADDRESS`); a code's failure count lives as long as the
  code; a password reset lifts the lockout.
- **A broker outage answers every code request alike.** Only a registered
  contact's request reached the queue, so an outage was a 503 for her and a 200
  for a stranger. The three neutral forms check the broker first.
- **The consent submission checks CSRF, and the body limit counts what
  arrives** - a chunked body is measured too (SEC-4).
- **One phone is one quota, however it is typed.** The sign-in code and
  public rights form throttles were keyed on the contact as typed while the
  lookup normalised it, so "+91 98765 00001", "+919876500001" and two other
  spellings were four quotas for one person - four times the codes, and four
  times the guesses. Every contact throttle now keys on the contact's keyed
  hash, the same identity the lookup finds, so rate keys no longer hold
  contacts in the clear either (review 2026-10-01, SEC-2).
- **The development code popup shows a code only in the tab that asked.**
  Every open portal and console polled one shared list, so a code asked for
  on one screen popped up on every screen on every machine - anyone testing
  alongside saw everyone else's codes. Each tab now sends an
  `X-CMP-Dev-Client` id; the API keeps it with the code (through the Celery
  task that sends it) and `/dev/codes` returns a tab's own codes only.
  Development only, as before: refused outside local/test.
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
