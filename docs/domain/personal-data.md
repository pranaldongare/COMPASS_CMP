# Personal data: where it is, and which API touches it

Every place this platform holds something about a person, and every endpoint
that accepts or returns it. Written for the questions that have to be answered
quickly and exactly: what do we hold, where does it go, who can see it, and
which call would expose it.

The counts here are measured, not remembered. **159 of the API's 245
operations** carry personal data; **20 of those need no session**. They come
from joining three artefacts the repository already keeps current, and the
last section says how to redo the join after a change.

## What counts as personal data here

The DPDP Act's terms, plus two categories the Act does not name but that this
document must cover because the system holds them.

| Kind | What it means here |
|---|---|
| **Data principal's personal data** | Anything about the individual the data is about: her name, contacts, date of birth, the consents she gave, the rights requests she made, the assets collected from her |
| **Staff personal data** | Members of staff are people too. Their names, work contacts, roles, sessions, delegations and every action attributed to them in the audit trail |
| **Credentials** | Passwords, one-time codes, session tokens, link tokens. Not personal data in the Act's sense, but they are the keys to it, so they are inventoried with it |
| **Free text** | Fields nobody can constrain: a request in the principal's own words, a ticket reply, a reason for a refusal. They must be treated as though they contain personal data, because sooner or later they do |
| **Files** | Approval proofs, response documents, evidence, export CSVs, imported manifests. The same reasoning as free text, with the addition that a file leaves the system as a file |

Two things are *not* personal data here, and are called out because their
column names suggest otherwise. A **purpose**, a **project**, a **notice** and a
**data source** have a `name`, and none of them is a person. A **processor** has
a `legal_name`, and it is an organisation — but `processor_respondent.name`
and `.contact` are a named human being at that organisation, and those are.

## The shape of it

```
                        auth_user  ──  the person
                            │
        ┌───────────────────┼───────────────────┬──────────────────┐
        │                   │                   │                  │
  consent_artefact     rights_request      nomination         delegation
   (+ grants, the         (+ holders,      (her nominee)     (staff cover)
    ip, the notice         tickets, items,
    hash she saw)          files, the text
        │                  she wrote)
        │
   export_line ── who was disclosed to whom
        │
   asset_consent ── her appearances in collected assets
```

Everything else in the schema — purposes, processors, sites, sources, notices —
describes *processing*, and touches a person only through the tables above and
through the `created_by` / `approved_by` / `owner_user_id` columns that name the
member of staff who acted.

## Where it lives: the database

34 objects, of which **22 carry personal data** and 12 do not. Each table below
lists only its personal-data columns; the full column list, with types,
defaults, constraints and triggers, is in
[docs/reference/database/table_reference.md](../reference/database/table_reference.md).

### The person

**`auth_user`** — one row per human being, whatever role they hold. A member of
staff and a data principal are the same kind of row; the `role` column is the
only difference, and deactivating a member of staff converts the row rather
than deleting it.

| Column | Type | What it is |
|---|---|---|
| `uuid` | uuid | The identifier every API uses. Pseudonymous, and stable for the life of the person |
| `username` | varchar(120) | Optional login name |
| `full_name` | varchar(200) | **Required.** The only mandatory personal datum on the row |
| `email` | varchar(255) | Primary address. Signs in, receives codes and messages |
| `secondary_email` | varchar(255) | A second address the person added themselves |
| `mobile` | varchar(20) | Signs in, receives SMS codes |
| `organization_id` | varchar(60) | Employee or student number, where the fiduciary uses one |
| `dob` | date | **Date of birth.** Drives the section 9 test for whether this is a child's account |
| `person_type` | person_type | Employee, student, ex-employee, external — an employment/affiliation fact |
| `role` | user_role | Staff role, or `data_subject` |
| `status` | user_status | pending / active / suspended / deactivated |
| `password_hash` | varchar(255) | Argon2. Staff only; a data principal has none and never gets one |
| `email_verified_at`, `mobile_verified_at`, `secondary_email_verified_at` | timestamptz | When a code sent to that contact came back. NULL means the contact signs nobody in |
| `registered_via_link_id` | integer | The consent link the account was created from, where it was |

**`person_type_history`** — `auth_user_id`, `from_type`, `to_type`, `reason`
(free text), `changed_by`. Why somebody stopped being an employee is an
opinion about a person, written by another person.

**`delegation`** — `delegator_user_id`, `delegate_user_id`, `reason` (free
text). Who covered for whom, for how long, and why.

### Consent

**`consent_artefact`** — the evidence that a named person agreed to something.

| Column | Type | What it is |
|---|---|---|
| `auth_user_id` | integer | Whose consent this is |
| `ip_address` | inet | **The address she consented from.** The only device datum the platform keeps about a data principal |
| `served_at`, `affirmative_action_at` | timestamptz | When the notice was shown to her, and when she acted. The first is the server's own record, never the client's claim |
| `notice_content_hash` | text | The exact text she was shown, frozen |
| `action_type` | action_type | What she did |
| `is_withdrawal` | boolean | Whether this artefact withdraws an earlier one |

**`consent_purpose_grant`** — `consent_id`, `purpose_id`, `granted`. Purpose by
purpose, what she allowed and what she refused. Refusal is recorded, not
merely absent.

**`consent_link`** — not personal data itself, but `token` (a keyed digest) and
`token_sealed` (encrypted under a key derived from the application secret) are
what let a holder open the consent form as a site, and the link signs an
existing data principal in.

**`v_current_consent`** — a view over `consent_artefact`; the same columns,
the same exposure.

### Rights

**`rights_request`** — 46 columns, of which these are personal:

| Column | What it is |
|---|---|
| `subject_user_id` | The data principal, where she has an account |
| `submitted_name`, `submitted_contact` | What a public requester typed. `submitted_contact` is **required** — a request with no way back is not a request |
| `request_text` | **Her own words.** Unbounded free text |
| `reference` | The public reference she quotes |
| `verification_note` | Why identity was or was not accepted |
| `refusal_reason`, `remedy_text`, `response_text` | The office's words about her case |
| `response_file_ref`, `response_file_hash`, `download_expires_at` | The response document and the window it can be fetched in |
| `trigger_evidence_ref`, `trigger_evidence_hash` | Evidence of a death or incapacity that invoked a nomination |
| `about_dpo`, `reviewer_user_id`, `grievance_upheld` | A grievance about the DPO, and the administrator reviewing it |
| `consent_id` | The consent the request is about |

**`rights_request_holder`** — the team asked to answer, and the person there who
did: `responder_name`, `responder_contact`, `responder_user_id`, `instruction`,
`brief`, `contact_log` (jsonb, every contact attempt), `return_summary`,
`return_evidence_ref/hash/name`, `sent_back_reason`, `office_read_at`,
`holder_read_at`.

**`rights_ticket_message`** — `author_user_id`, `body` (free text, both
directions), `evidence_ref`, `evidence_hash`, `evidence_name`.

**`rights_request_item`** — `asset_consent_id`, `other_subjects` (how many other
people appear in the same asset), `decision`, `basis`, `retain_until`.

**`rights_response_file`** — `file_ref`, `file_hash`, `file_name`,
`content_type`, `size_bytes`, `uploaded_by`.

**`nomination`** — `principal_user_id`, `nominee_name`, `nominee_email`,
`nominee_mobile`, `nominee_user_id`, `accept_token_hash`, and `rights` (which
rights the nominee may exercise). A nominee is a second living person on the
row.

### Collection and disclosure

**`export_line`** — `auth_user_id`, `consent_id`. **This is the disclosure
record**: one row per person per export. It is what answers "who was my data
shared with", and what derives the holders of her data when she makes a rights
request.

**`export_log`** — `exported_by`, `file_ref`, `file_hash`, `row_count`. The CSV
itself contains names, emails, mobiles, organisation ids and granted purposes —
see *Files*, below.

**`asset_consent`** — `consent_id`, `subject_role` (whether she is the subject
of the asset or a bystander in it), `disposition`. Her appearances in collected
material.

**`data_asset`** — `storage_ref`, `source_asset_ref`, `has_unmapped_subjects`.
The asset is the personal data; this row points at it.

**`collection`** — `agent_ref`, the field agent who collected.

**`import_batch`** — `file_name`, `file_hash`, `error_report` (jsonb; rejected
lines, which can quote what was in them), `imported_by`.

### Staff acting, and the record of it

**`audit_log`** — `actor_user_id`, `subject_user_id`, `entity_type`,
`entity_id`, `detail_json`. Append-only and hash-chained: **nothing here can be
edited or deleted by anyone**, which is deliberate and is also why
`detail_json` must never be given a free-text field somebody could paste a
principal's data into.

**`processor_respondent`** — `name`, `contact`, `user_id`. A named person at a
third party who answers tickets.

**`project_approval`** — `reference_no`, `proof_file_ref`, `proof_file_hash`,
`uploaded_by`. The proof document is an institutional approval, and often names
investigators.

**`project_processor`** — `decision_reason`, `added_by`, `decided_by`.
**`project_status_history`** — `reason`, `actor_user_id`.
**`project`** — `created_by`, `dco_user_id`.
**`project_site`** — `dco_override_user_id`, `dco_override_by`.
**`data_source`** — `owner_user_id`.
**`notice`** — `approved_by`, `dpo_contact` (a role mailbox, published in the
notice), `note` (an instruction to the collector, **never served to a data
principal**), `recipients_text`.
**`notice_language`** — `created_by`, `approved_by`.
**`notice_purpose`** — `overridden_by`.
**`purpose`** — `created_by`.
**`message_template`** — `updated_by`, `subject`, `body`. The templates carry
placeholders, not data; rendering one puts a person's name and contact into a
message.
**`consent_link`** — `created_by`, `revoked_by`.

### Tables with no personal data at all

`alembic_version`, `processor` (an organisation), and the reference and join
rows that carry only foreign keys and configuration: `purpose` and
`notice_purpose` apart from the two columns named above. Everything else in the
schema appears in the lists above.

## Where it lives: everywhere that is not the database

A data map that stops at the schema is wrong. Five other places hold personal
data, and two of them leave the building by design: the files somebody
downloads, and the messages the platform sends.

### Redis

Namespaced keys, every one with a TTL. Nothing here is a record of what
happened; it is state that must disappear on its own.

| Key | Holds | Lifetime |
|---|---|---|
| `sess:<fingerprint>` | A session: `user_id`, `user_uuid`, `role`, `account_role`, **`ip_address`**, **`user_agent`** (truncated to 300 chars), `created_at`, `last_seen_at`, `mfa_verified`, `csrf_token` | 8 hours absolute (`SESSION_TTL_S`), 30 minutes idle (`SESSION_IDLE_TIMEOUT_S`); a session still owing its second factor lives `MFA_TTL_S` |
| `usess:<user_id>` | The set of a person's live sessions, so signing out everywhere works | With the sessions |
| `otp:<scope>:<identity>` | A **keyed digest** of a one-time code, never the code. The identity is the email or mobile it was sent to | 10 minutes (`OTP_TTL_S`), 5 attempts; a staff invitation lasts `STAFF_INVITE_TTL_H` hours, 48 by default |
| `otpa:<scope>:<identity>` | Attempts against that code | With the code |
| `mfa:*`, `lfail:*`, `lock:*` | Second-factor state, failed sign-ins, lockouts — each keyed by a login | The staff second factor is 5 minutes (`MFA_TTL_S`) and 5 attempts; 5 failed sign-ins in 30 minutes lock the account for 30 |
| `rate:*` | Rate-limit counters, keyed by contact or address | The window |
| `nsrv:*` | That the server showed a particular notice, in a particular rendition, to a particular person through a particular link — the fact a consent is checked against | Six hours (`NOTICE_SERVING_TTL`); past it, a consent is refused as `notice_stale` |

The session token in the cookie is never stored: Redis holds a fingerprint of
it. A dump of Redis yields sessions you cannot resume and codes you cannot use.

### Files on disk

Under `UPLOAD_ROOT` (`backend/api/var/uploads` in development), four
directories, all of which contain personal data:

| Directory | What is in it | Who put it there |
|---|---|---|
| `exports/` | **The export CSV**: one line per person — name, email, mobile, organisation id, person type, consent status, granted purposes, the consent link URL and the notice version they agreed to | A collection owner or the DPO |
| `responses/` | The document answering a rights request, and the principal's own uploads | The office |
| `rights/` | Ticket evidence, return evidence, trigger evidence (a death certificate, for instance) | The office and the holders |
| `approvals/` | Institutional approval proofs for a project | The R&D User |

A cell that begins with a formula character is written as text, so an export
opened in a spreadsheet cannot execute what a name field contained.

### Logs

| Log | What it may contain | Control |
|---|---|---|
| Access log | Method, path, status, request id, duration | Consent and nomination tokens are scrubbed from the path, in the application and again in the shipped nginx configuration |
| Application log | Structured events; identifiers, not contents | A domain error on a capability path logs no token |
| Celery task events | The name of a task and **the number of its arguments** | The arguments themselves are withheld: they are one-time codes and contacts, and anything that renders task events would print them |
| `var/outbox.log` | **Development only.** Every email and SMS the platform would have sent, in full — addresses, names and codes | It exists because there is no real transport locally. It is a plain file; treat it as a live mailbox |

### The messages themselves

Every email and SMS the platform sends carries personal data out of it by
design: a name, a reference, a link, a one-time code. The catalogue of what is
sent, to whom, and on what event is
[domain/messages.md](messages.md).

### The browsers

Both portals keep exactly one thing in the browser: `cmp-theme`, light or dark.
No personal data is stored client-side; the session is an `HttpOnly` cookie the
JavaScript cannot read.

## The API, endpoint by endpoint

159 of 245 operations accept or return personal data. Each table gives the
fields by name, so "which call would expose a mobile number" is a search rather
than a reading.

**How to read the columns.** *Who may call it* is the permission matrix's own
answer, not a summary of it: `every row` is `ALL`, `rows in scope` is `SCOPED`,
`own rows` is `OWN`. A role absent from the cell cannot call the endpoint at
all. *Personal data in* includes path and query parameters as well as the body.
*Personal data out* is the union of the 2xx response schemas, resolved through
every `$ref`, so a field nested three models deep still appears.

**Two things the columns do not show.** Out of scope answers **404, never 403** —
a row the caller may not see does not exist as far as the response is
concerned, so listing endpoints leak no row counts. And the *fields* listed are
what the schema permits; a response only carries what the caller's scope
selected.

### Authentication — `/auth/*`

11 operations carry personal data.

| Method | Endpoint | Who may call it | Personal data in | Personal data out |
|---|---|---|---|---|
| POST | `/auth/login` | **public** — the request carries its own credential (password, link token, one-time code) | `login`, `password` | `mfa_required`, `user_uuid` |
| GET | `/auth/me` | any signed-in session, own record | — | `account_role`, `dob`, `email`, `email_verified_at`, `full_name`, `is_minor`, `mfa_verified`, `mobile`, `mobile_verified_at`, `person_type`, `role`, `secondary_email`, `secondary_email_verified_at`, `session_expires_at` |
| POST | `/auth/mfa/verify` | any signed-in session, conditionally | `code` | — |
| POST | `/auth/otp/request` | **public** — no session | `contact` | — |
| POST | `/auth/otp/verify` | **public** — the request carries its own credential (password, link token, one-time code) | `code`, `contact` | — |
| POST | `/auth/password/change` | any signed-in session, own record | `current_password`, `new_password` | — |
| POST | `/auth/password/reset/confirm` | **public** — the request carries its own credential (password, link token, one-time code) | `code`, `email`, `new_password` | — |
| POST | `/auth/password/reset/request` | **public** — no session | `email` | — |
| POST | `/auth/register` | **public** — no session | `dob`, `email`, `full_name`, `mobile` | — |
| POST | `/auth/register/verify` | **public** — the request carries its own credential (password, link token, one-time code) | `email_code`, `mobile`, `mobile_code` | — |
| GET | `/auth/sessions` | any signed-in session, own record | — | `ip_address`, `last_seen_at`, `mfa_verified`, `user_agent` |

### The data principal's own records — `/me/*`

21 operations carry personal data.

| Method | Endpoint | Who may call it | Personal data in | Personal data out |
|---|---|---|---|---|
| GET | `/me` | any signed-in session, own record | — | `dob`, `email`, `email_verified_at`, `full_name`, `is_minor`, `mobile`, `mobile_verified_at`, `organization_id`, `person_type`, `secondary_email`, `secondary_email_verified_at` |
| PATCH | `/me` | any signed-in session, own record | `dob`, `full_name`, `mobile`, `secondary_email` | `dob`, `email`, `email_verified_at`, `full_name`, `is_minor`, `mobile`, `mobile_verified_at`, `organization_id`, `person_type`, `secondary_email`, `secondary_email_verified_at` |
| GET | `/me/consents` | Principal own rows | — | `affirmative_action_at`, `consent_uuid`, `granted_count`, `is_withdrawal` |
| GET | `/me/consents/{consent_uuid}` | Principal own rows | `consent_uuid` | — |
| GET | `/me/consents/{consent_uuid}/grants` | Principal own rows | `consent_uuid` | — |
| GET | `/me/consents/{consent_uuid}/history` | Principal own rows | `consent_uuid` | — |
| GET | `/me/consents/{consent_uuid}/notice` | Principal own rows | `consent_uuid` | — |
| GET | `/me/consents/{consent_uuid}/trail` | Principal own rows | `consent_uuid` | — |
| POST | `/me/consents/{consent_uuid}/withdraw` | Principal own rows | `consent_uuid` | — |
| POST | `/me/contact/verify` | any signed-in session, own record | `code`, `contact` | — |
| POST | `/me/contacts/code` | any signed-in session, own record | `contact` | — |
| GET | `/me/nominations` | Principal own rows | — | `nominee_email`, `nominee_mobile`, `nominee_name` |
| POST | `/me/nominations` | Principal own rows | `nominee_email`, `nominee_mobile`, `nominee_name` | `nominee_email`, `nominee_mobile`, `nominee_name` |
| DELETE | `/me/nominations/{nomination_uuid}` | Principal own rows | — | `nominee_email`, `nominee_mobile`, `nominee_name` |
| GET | `/me/nominee-of` | Principal own rows | — | `contact`, `principal_name` |
| POST | `/me/person-type` | DPO own rows, Admin own rows, Principal own rows | `person_type`, `reason` | — |
| GET | `/me/requests` | Principal own rows | — | `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_purposes`, `consent_uuid`, `content_type`, `download_available`, `download_expires_at`, `file_name`, `file_uuid`, `refusal_reason`, `remedy_text`, `request_text`, `response_files`, `response_text`, `size_bytes` |
| POST | `/me/requests` | Principal own rows | `consent_uuid`, `request_text` | `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_purposes`, `consent_uuid`, `content_type`, `download_available`, `download_expires_at`, `file_name`, `file_uuid`, `refusal_reason`, `remedy_text`, `request_text`, `response_files`, `response_text`, `size_bytes` |
| GET | `/me/requests/{request_uuid}` | Principal own rows | — | `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_purposes`, `consent_uuid`, `content_type`, `download_available`, `download_expires_at`, `file_name`, `file_uuid`, `refusal_reason`, `remedy_text`, `request_text`, `response_files`, `response_text`, `size_bytes` |
| POST | `/me/requests/{request_uuid}/dispute` | Principal own rows | — | `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_purposes`, `consent_uuid`, `content_type`, `download_available`, `download_expires_at`, `file_name`, `file_uuid`, `refusal_reason`, `remedy_text`, `request_text`, `response_files`, `response_text`, `size_bytes` |
| GET | `/me/requests/{request_uuid}/files/{file_uuid}` | Principal own rows | `file_uuid` | — |

### The consent link — `/c/{token}/*`

6 operations carry personal data.

| Method | Endpoint | Who may call it | Personal data in | Personal data out |
|---|---|---|---|---|
| GET | `/c/{token}` | **public** — the request carries its own credential (password, link token, one-time code) | `token` | — |
| POST | `/c/{token}/consent` | Principal own rows | `action_type`, `grants`, `served_at`, `token` | — |
| GET | `/c/{token}/notice` | **public** — the request carries its own credential (password, link token, one-time code) | `token` | — |
| POST | `/c/{token}/otp` | **public** — the request carries its own credential (password, link token, one-time code) | `contact`, `token` | — |
| POST | `/c/{token}/otp/verify` | **public** — the request carries its own credential (password, link token, one-time code) | `code`, `contact`, `token` | — |
| POST | `/c/{token}/register` | **public** — the request carries its own credential (password, link token, one-time code) | `email`, `full_name`, `mobile`, `organization_id`, `person_type`, `token` | — |

### The public rights surface — `/rights/*`

8 operations carry personal data.

| Method | Endpoint | Who may call it | Personal data in | Personal data out |
|---|---|---|---|---|
| GET | `/rights/nominations/{token}` | **public** — the request carries its own credential (password, link token, one-time code) | `token` | `nominee_name`, `principal_name` |
| POST | `/rights/nominations/{token}/accept` | **public** — the request carries its own credential (password, link token, one-time code) | `code`, `token` | — |
| POST | `/rights/nominations/{token}/code` | **public** — the request carries its own credential (password, link token, one-time code) | `token` | — |
| POST | `/rights/nominations/{token}/decline` | **public** — the request carries its own credential (password, link token, one-time code) | `code`, `token` | — |
| POST | `/rights/nominee/requests` | **public** — the request carries its own credential (password, link token, one-time code) | `code`, `evidence`, `request_text` | — |
| POST | `/rights/nominee/start` | **public** — the request carries its own credential (password, link token, one-time code) | `contact` | — |
| POST | `/rights/requests` | **public** — the request carries its own credential (password, link token, one-time code) | `contact`, `request_text` | — |
| POST | `/rights/requests/verify` | **public** — the request carries its own credential (password, link token, one-time code) | `code` | — |

### Rights requests, the office's side — `/requests/*`

35 operations carry personal data.

| Method | Endpoint | Who may call it | Personal data in | Personal data out |
|---|---|---|---|---|
| GET | `/requests` | DPO every row, Admin rows in scope | — | `consent_project`, `consent_uuid`, `subject_name`, `subject_uuid`, `submitted_contact`, `submitted_name` |
| POST | `/requests` | DPO yes, Admin yes | `contact`, `request_text`, `subject_uuid` | `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_project_uuid`, `consent_purposes`, `consent_uuid`, `consent_withdrawn`, `download_expires_at`, `nominee_contact`, `nominee_name`, `refusal_reason`, `remedy_text`, `request_text`, `response_file_hash`, `response_text`, `reviewer_name`, `reviewer_uuid`, `subject_email`, `subject_mobile`, `subject_name`, `subject_uuid`, `submitted_contact`, `submitted_name`, `trigger_evidence_hash`, `verification_note`, `verified_by_name` |
| GET | `/requests/{request_uuid}` | DPO every row, Admin rows in scope | — | `brief`, `confirmed_by_name`, `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_project_uuid`, `consent_purposes`, `consent_uuid`, `consent_withdrawn`, `contact_log`, `content_type`, `decided_by_name`, `disposition`, `download_expires_at`, `evidence`, `file_name`, `file_uuid`, `instruction`, `nominee_contact`, `nominee_name`, `other_subjects`, `refusal_reason`, `remedy_text`, `request_text`, `responder_contact`, `responder_name`, `responder_user_name`, `responder_user_uuid`, `response_file_hash`, `response_files`, `response_text`, `return_evidence_hash`, `return_evidence_name`, `return_summary`, `reviewer_name`, `reviewer_uuid`, `seen_at`, `sent_back_reason`, `size_bytes`, `subject_email`, `subject_mobile`, `subject_name`, `subject_role`, `subject_uuid`, `submitted_contact`, `submitted_name`, `trigger_evidence_hash`, `verification_note`, `verified_by_name` |
| POST | `/requests/{request_uuid}/acknowledge` | DPO every row, Admin rows in scope | — | `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_project_uuid`, `consent_purposes`, `consent_uuid`, `consent_withdrawn`, `download_expires_at`, `nominee_contact`, `nominee_name`, `refusal_reason`, `remedy_text`, `request_text`, `response_file_hash`, `response_text`, `reviewer_name`, `reviewer_uuid`, `subject_email`, `subject_mobile`, `subject_name`, `subject_uuid`, `submitted_contact`, `submitted_name`, `trigger_evidence_hash`, `verification_note`, `verified_by_name` |
| POST | `/requests/{request_uuid}/classify` | DPO every row, Admin rows in scope | — | `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_project_uuid`, `consent_purposes`, `consent_uuid`, `consent_withdrawn`, `download_expires_at`, `nominee_contact`, `nominee_name`, `refusal_reason`, `remedy_text`, `request_text`, `response_file_hash`, `response_text`, `reviewer_name`, `reviewer_uuid`, `subject_email`, `subject_mobile`, `subject_name`, `subject_uuid`, `submitted_contact`, `submitted_name`, `trigger_evidence_hash`, `verification_note`, `verified_by_name` |
| POST | `/requests/{request_uuid}/decide` | DPO conditional, Admin conditional | `remedy_text`, `response_text` | — |
| POST | `/requests/{request_uuid}/escalate` | DPO every row, Admin rows in scope | — | `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_project_uuid`, `consent_purposes`, `consent_uuid`, `consent_withdrawn`, `download_expires_at`, `nominee_contact`, `nominee_name`, `refusal_reason`, `remedy_text`, `request_text`, `response_file_hash`, `response_text`, `reviewer_name`, `reviewer_uuid`, `subject_email`, `subject_mobile`, `subject_name`, `subject_uuid`, `submitted_contact`, `submitted_name`, `trigger_evidence_hash`, `verification_note`, `verified_by_name` |
| POST | `/requests/{request_uuid}/event` | DPO every row, Admin rows in scope | — | `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_project_uuid`, `consent_purposes`, `consent_uuid`, `consent_withdrawn`, `download_expires_at`, `nominee_contact`, `nominee_name`, `refusal_reason`, `remedy_text`, `request_text`, `response_file_hash`, `response_text`, `reviewer_name`, `reviewer_uuid`, `subject_email`, `subject_mobile`, `subject_name`, `subject_uuid`, `submitted_contact`, `submitted_name`, `trigger_evidence_hash`, `verification_note`, `verified_by_name` |
| GET | `/requests/{request_uuid}/files/{file_uuid}` | DPO every row, Admin rows in scope | `file_uuid` | — |
| POST | `/requests/{request_uuid}/holders` | DPO every row, Admin rows in scope | `responder_contact`, `responder_name` | `brief`, `confirmed_by_name`, `contact_log`, `evidence`, `instruction`, `responder_contact`, `responder_name`, `responder_user_name`, `responder_user_uuid`, `return_evidence_hash`, `return_evidence_name`, `return_summary`, `seen_at`, `sent_back_reason` |
| POST | `/requests/{request_uuid}/holders/derive` | DPO every row, Admin rows in scope | — | `brief`, `confirmed_by_name`, `contact_log`, `evidence`, `instruction`, `responder_contact`, `responder_name`, `responder_user_name`, `responder_user_uuid`, `return_evidence_hash`, `return_evidence_name`, `return_summary`, `seen_at`, `sent_back_reason` |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/confirm` | DPO every row, Admin rows in scope | `responder_contact`, `responder_name` | `brief`, `confirmed_by_name`, `contact_log`, `evidence`, `instruction`, `responder_contact`, `responder_name`, `responder_user_name`, `responder_user_uuid`, `return_evidence_hash`, `return_evidence_name`, `return_summary`, `seen_at`, `sent_back_reason` |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/contact` | DPO every row, Admin rows in scope | — | `brief`, `confirmed_by_name`, `contact_log`, `evidence`, `instruction`, `responder_contact`, `responder_name`, `responder_user_name`, `responder_user_uuid`, `return_evidence_hash`, `return_evidence_name`, `return_summary`, `seen_at`, `sent_back_reason` |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/escalate` | DPO every row, Admin rows in scope | — | `brief`, `confirmed_by_name`, `contact_log`, `evidence`, `instruction`, `responder_contact`, `responder_name`, `responder_user_name`, `responder_user_uuid`, `return_evidence_hash`, `return_evidence_name`, `return_summary`, `seen_at`, `sent_back_reason` |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/reassign` | DPO every row, Admin rows in scope | `responder_contact`, `responder_name` | `brief`, `confirmed_by_name`, `contact_log`, `evidence`, `instruction`, `responder_contact`, `responder_name`, `responder_user_name`, `responder_user_uuid`, `return_evidence_hash`, `return_evidence_name`, `return_summary`, `seen_at`, `sent_back_reason` |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/remind` | DPO every row, Admin rows in scope | — | `brief`, `confirmed_by_name`, `contact_log`, `evidence`, `instruction`, `responder_contact`, `responder_name`, `responder_user_name`, `responder_user_uuid`, `return_evidence_hash`, `return_evidence_name`, `return_summary`, `seen_at`, `sent_back_reason` |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/return` | DPO every row, Admin rows in scope | `evidence` | `brief`, `confirmed_by_name`, `contact_log`, `evidence`, `instruction`, `responder_contact`, `responder_name`, `responder_user_name`, `responder_user_uuid`, `return_evidence_hash`, `return_evidence_name`, `return_summary`, `seen_at`, `sent_back_reason` |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/send-back` | DPO every row, Admin rows in scope | `reason` | `brief`, `confirmed_by_name`, `contact_log`, `evidence`, `instruction`, `responder_contact`, `responder_name`, `responder_user_name`, `responder_user_uuid`, `return_evidence_hash`, `return_evidence_name`, `return_summary`, `seen_at`, `sent_back_reason` |
| GET | `/requests/{request_uuid}/holders/{holder_uuid}/thread` | DPO every row, Admin rows in scope | — | `author_name`, `body`, `brief`, `confirmed_by_name`, `contact_log`, `evidence`, `evidence_hash`, `evidence_name`, `instruction`, `responder_contact`, `responder_name`, `responder_user_name`, `responder_user_uuid`, `return_evidence_hash`, `return_evidence_name`, `return_summary`, `seen_at`, `sent_back_reason` |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/thread` | DPO every row, Admin rows in scope | `body`, `evidence` | `author_name`, `body`, `brief`, `confirmed_by_name`, `contact_log`, `evidence`, `evidence_hash`, `evidence_name`, `instruction`, `responder_contact`, `responder_name`, `responder_user_name`, `responder_user_uuid`, `return_evidence_hash`, `return_evidence_name`, `return_summary`, `seen_at`, `sent_back_reason` |
| POST | `/requests/{request_uuid}/holders/{holder_uuid}/withdraw` | DPO every row, Admin rows in scope | `reason` | `brief`, `confirmed_by_name`, `contact_log`, `evidence`, `instruction`, `responder_contact`, `responder_name`, `responder_user_name`, `responder_user_uuid`, `return_evidence_hash`, `return_evidence_name`, `return_summary`, `seen_at`, `sent_back_reason` |
| POST | `/requests/{request_uuid}/intent` | DPO every row, Admin rows in scope | — | `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_project_uuid`, `consent_purposes`, `consent_uuid`, `consent_withdrawn`, `download_expires_at`, `nominee_contact`, `nominee_name`, `refusal_reason`, `remedy_text`, `request_text`, `response_file_hash`, `response_text`, `reviewer_name`, `reviewer_uuid`, `subject_email`, `subject_mobile`, `subject_name`, `subject_uuid`, `submitted_contact`, `submitted_name`, `trigger_evidence_hash`, `verification_note`, `verified_by_name` |
| POST | `/requests/{request_uuid}/refuse` | DPO every row, Admin rows in scope | `reason` | `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_project_uuid`, `consent_purposes`, `consent_uuid`, `consent_withdrawn`, `download_expires_at`, `nominee_contact`, `nominee_name`, `refusal_reason`, `remedy_text`, `request_text`, `response_file_hash`, `response_text`, `reviewer_name`, `reviewer_uuid`, `subject_email`, `subject_mobile`, `subject_name`, `subject_uuid`, `submitted_contact`, `submitted_name`, `trigger_evidence_hash`, `verification_note`, `verified_by_name` |
| POST | `/requests/{request_uuid}/respond` | DPO every row, Admin rows in scope | `files`, `response_text` | `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_project_uuid`, `consent_purposes`, `consent_uuid`, `consent_withdrawn`, `download_expires_at`, `nominee_contact`, `nominee_name`, `refusal_reason`, `remedy_text`, `request_text`, `response_file_hash`, `response_text`, `reviewer_name`, `reviewer_uuid`, `subject_email`, `subject_mobile`, `subject_name`, `subject_uuid`, `submitted_contact`, `submitted_name`, `trigger_evidence_hash`, `verification_note`, `verified_by_name` |
| POST | `/requests/{request_uuid}/reviewer` | Admin rows in scope | `reviewer_uuid` | `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_project_uuid`, `consent_purposes`, `consent_uuid`, `consent_withdrawn`, `download_expires_at`, `nominee_contact`, `nominee_name`, `refusal_reason`, `remedy_text`, `request_text`, `response_file_hash`, `response_text`, `reviewer_name`, `reviewer_uuid`, `subject_email`, `subject_mobile`, `subject_name`, `subject_uuid`, `submitted_contact`, `submitted_name`, `trigger_evidence_hash`, `verification_note`, `verified_by_name` |
| POST | `/requests/{request_uuid}/scope/derive` | DPO every row, Admin rows in scope | — | `decided_by_name`, `disposition`, `other_subjects`, `subject_role` |
| PUT | `/requests/{request_uuid}/scope/{item_uuid}` | DPO every row, Admin rows in scope | — | `decided_by_name`, `disposition`, `other_subjects`, `subject_role` |
| POST | `/requests/{request_uuid}/scope/{item_uuid}/apply` | DPO every row, Admin rows in scope | — | `decided_by_name`, `disposition`, `other_subjects`, `subject_role` |
| POST | `/requests/{request_uuid}/tickets` | DPO every row, Admin rows in scope | `instruction` | `brief`, `confirmed_by_name`, `contact_log`, `evidence`, `instruction`, `responder_contact`, `responder_name`, `responder_user_name`, `responder_user_uuid`, `return_evidence_hash`, `return_evidence_name`, `return_summary`, `seen_at`, `sent_back_reason` |
| POST | `/requests/{request_uuid}/transition` | DPO every row, Admin rows in scope | `reason` | `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_project_uuid`, `consent_purposes`, `consent_uuid`, `consent_withdrawn`, `download_expires_at`, `nominee_contact`, `nominee_name`, `refusal_reason`, `remedy_text`, `request_text`, `response_file_hash`, `response_text`, `reviewer_name`, `reviewer_uuid`, `subject_email`, `subject_mobile`, `subject_name`, `subject_uuid`, `submitted_contact`, `submitted_name`, `trigger_evidence_hash`, `verification_note`, `verified_by_name` |
| POST | `/requests/{request_uuid}/verification/code` | DPO every row, Admin rows in scope | — | `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_project_uuid`, `consent_purposes`, `consent_uuid`, `consent_withdrawn`, `download_expires_at`, `nominee_contact`, `nominee_name`, `refusal_reason`, `remedy_text`, `request_text`, `response_file_hash`, `response_text`, `reviewer_name`, `reviewer_uuid`, `subject_email`, `subject_mobile`, `subject_name`, `subject_uuid`, `submitted_contact`, `submitted_name`, `trigger_evidence_hash`, `verification_note`, `verified_by_name` |
| POST | `/requests/{request_uuid}/verification/confirm` | DPO every row, Admin rows in scope | `code` | `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_project_uuid`, `consent_purposes`, `consent_uuid`, `consent_withdrawn`, `download_expires_at`, `nominee_contact`, `nominee_name`, `refusal_reason`, `remedy_text`, `request_text`, `response_file_hash`, `response_text`, `reviewer_name`, `reviewer_uuid`, `subject_email`, `subject_mobile`, `subject_name`, `subject_uuid`, `submitted_contact`, `submitted_name`, `trigger_evidence_hash`, `verification_note`, `verified_by_name` |
| POST | `/requests/{request_uuid}/verification/fail` | DPO every row, Admin rows in scope | — | `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_project_uuid`, `consent_purposes`, `consent_uuid`, `consent_withdrawn`, `download_expires_at`, `nominee_contact`, `nominee_name`, `refusal_reason`, `remedy_text`, `request_text`, `response_file_hash`, `response_text`, `reviewer_name`, `reviewer_uuid`, `subject_email`, `subject_mobile`, `subject_name`, `subject_uuid`, `submitted_contact`, `submitted_name`, `trigger_evidence_hash`, `verification_note`, `verified_by_name` |
| POST | `/requests/{request_uuid}/verification/manual` | DPO every row, Admin rows in scope | — | `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_project_uuid`, `consent_purposes`, `consent_uuid`, `consent_withdrawn`, `download_expires_at`, `nominee_contact`, `nominee_name`, `refusal_reason`, `remedy_text`, `request_text`, `response_file_hash`, `response_text`, `reviewer_name`, `reviewer_uuid`, `subject_email`, `subject_mobile`, `subject_name`, `subject_uuid`, `submitted_contact`, `submitted_name`, `trigger_evidence_hash`, `verification_note`, `verified_by_name` |
| POST | `/requests/{request_uuid}/withdrawal` | DPO every row, Admin rows in scope | — | `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_project_uuid`, `consent_purposes`, `consent_uuid`, `consent_withdrawn`, `download_expires_at`, `nominee_contact`, `nominee_name`, `refusal_reason`, `remedy_text`, `request_text`, `response_file_hash`, `response_text`, `reviewer_name`, `reviewer_uuid`, `subject_email`, `subject_mobile`, `subject_name`, `subject_uuid`, `submitted_contact`, `submitted_name`, `trigger_evidence_hash`, `verification_note`, `verified_by_name` |

### Tickets a holder answers — `/tickets/*`

4 operations carry personal data.

| Method | Endpoint | Who may call it | Personal data in | Personal data out |
|---|---|---|---|---|
| GET | `/tickets` | DPO own rows, Admin own rows, DCO own rows, DCO Admin own rows, RCO own rows, R&D own rows | — | `brief`, `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_purposes`, `consent_uuid`, `instruction`, `return_evidence_hash`, `return_evidence_name`, `return_summary`, `sent_back_reason`, `subject_name` |
| GET | `/tickets/{holder_uuid}` | DPO own rows, Admin own rows, DCO own rows, DCO Admin own rows, RCO own rows, R&D own rows | — | `author_name`, `body`, `brief`, `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_purposes`, `consent_uuid`, `evidence_hash`, `evidence_name`, `instruction`, `return_evidence_hash`, `return_evidence_name`, `return_summary`, `sent_back_reason`, `subject_name` |
| POST | `/tickets/{holder_uuid}/messages` | DPO own rows, Admin own rows, DCO own rows, DCO Admin own rows, RCO own rows, R&D own rows | `body`, `evidence` | `author_name`, `body`, `brief`, `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_purposes`, `consent_uuid`, `evidence_hash`, `evidence_name`, `instruction`, `return_evidence_hash`, `return_evidence_name`, `return_summary`, `sent_back_reason`, `subject_name` |
| POST | `/tickets/{holder_uuid}/return` | DPO own rows, Admin own rows, DCO own rows, DCO Admin own rows, RCO own rows, R&D own rows | `evidence` | `brief`, `consent_at`, `consent_notice_code`, `consent_notice_version`, `consent_project`, `consent_purposes`, `consent_uuid`, `instruction`, `return_evidence_hash`, `return_evidence_name`, `return_summary`, `sent_back_reason`, `subject_name` |

### Consents and links, the office's side

9 operations carry personal data.

| Method | Endpoint | Who may call it | Personal data in | Personal data out |
|---|---|---|---|---|
| GET | `/consents` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope, R&D own rows | — | `action_type`, `affirmative_action_at`, `consent_status`, `consent_uuid`, `granted_count`, `is_withdrawal`, `refused_count`, `served_at`, `subject_email`, `subject_mobile`, `subject_name`, `subject_uuid` |
| GET | `/consents/{consent_uuid}` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope, R&D own rows | `consent_uuid` | `action_type`, `affirmative_action_at`, `consent_uuid`, `is_withdrawal`, `served_at`, `subject_email`, `subject_mobile`, `subject_name`, `subject_uuid` |
| GET | `/consents/{consent_uuid}/assets` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope, R&D own rows | `consent_uuid` | `disposition`, `has_unmapped_subjects`, `storage_ref`, `subject_role` |
| GET | `/consents/{consent_uuid}/grants` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope, R&D own rows | `consent_uuid` | `granted` |
| GET | `/links` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope | — | `registrations`, `url_path` |
| GET | `/links/{link_uuid}` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope | — | `url_path` |
| GET | `/links/{link_uuid}/stats` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope | — | `consents`, `registrations`, `withdrawals` |
| GET | `/projects/{project_uuid}/consents` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope, R&D own rows | — | `action_type`, `affirmative_action_at`, `consent_status`, `consent_uuid`, `granted_count`, `is_withdrawal`, `refused_count`, `served_at`, `subject_email`, `subject_mobile`, `subject_name`, `subject_uuid` |
| GET | `/projects/{project_uuid}/links` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope | — | `url_path` |

### Exports, imports, collections and assets

10 operations carry personal data.

| Method | Endpoint | Who may call it | Personal data in | Personal data out |
|---|---|---|---|---|
| GET | `/collections` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope, R&D own rows | — | `mapped_asset_count` |
| GET | `/collections/{collection_uuid}` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope, R&D own rows | — | `mapped_asset_count` |
| GET | `/collections/{collection_uuid}/assets` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope, R&D own rows | — | `bystander_count`, `has_unmapped_subjects`, `storage_ref`, `subject_count` |
| GET | `/exports` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope | — | `exported_by_name` |
| GET | `/exports/{export_uuid}` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope | — | `exported_by_name` |
| POST | `/imports` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope | `manifest` | — |
| POST | `/imports/validate` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope | `manifest` | — |
| GET | `/imports/{batch_uuid}` | any signed-in session, conditionally | — | `file_name`, `imported_by_name`, `imported_by_uuid` |
| GET | `/projects/{project_uuid}/exports` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope | — | `exported_by_name` |
| POST | `/projects/{project_uuid}/exports` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope | — | `exported_by_name` |

### The staff register — `/users/*`

13 operations carry personal data.

| Method | Endpoint | Who may call it | Personal data in | Personal data out |
|---|---|---|---|---|
| GET | `/users` | DPO every row, Admin every row | `person_type`, `role` | `email`, `full_name`, `mobile`, `organization_id`, `person_type`, `role`, `username` |
| POST | `/users` | Admin every row | `email`, `full_name`, `mobile`, `organization_id`, `person_type`, `role`, `username` | `email`, `full_name`, `mobile`, `organization_id`, `person_type`, `role`, `username` |
| GET | `/users/collection-owners` | DPO every row, Admin every row, DCO every row, DCO Admin every row, RCO every row, R&D every row | — | `email`, `full_name`, `role` |
| GET | `/users/staff` | DPO every row, Admin every row | — | `email`, `full_name`, `role` |
| GET | `/users/{user_uuid}` | DPO every row, Admin every row | `user_uuid` | `email`, `full_name`, `mobile`, `organization_id`, `person_type`, `role`, `username` |
| PATCH | `/users/{user_uuid}` | Admin every row | `full_name`, `mobile`, `organization_id`, `user_uuid` | `email`, `full_name`, `mobile`, `organization_id`, `person_type`, `role`, `username` |
| POST | `/users/{user_uuid}/deactivate` | Admin every row | `user_uuid` | — |
| POST | `/users/{user_uuid}/invite` | Admin every row | `user_uuid` | — |
| POST | `/users/{user_uuid}/mfa/reset` | Admin every row | `user_uuid` | — |
| GET | `/users/{user_uuid}/person-type-history` | DPO every row, Admin every row | `user_uuid` | `changed_by_name`, `changed_by_uuid`, `from_type`, `reason`, `to_type` |
| POST | `/users/{user_uuid}/reactivate` | Admin every row | `user_uuid` | — |
| POST | `/users/{user_uuid}/role` | Admin every row | `reason`, `role`, `user_uuid` | — |
| DELETE | `/users/{user_uuid}/sessions` | Admin every row | `user_uuid` | — |

### Delegation — `/delegations/*`

4 operations carry personal data.

| Method | Endpoint | Who may call it | Personal data in | Personal data out |
|---|---|---|---|---|
| GET | `/delegations` | DPO every row, Admin every row | — | `delegate_email`, `delegate_name`, `delegate_role`, `delegate_uuid`, `delegator_email`, `delegator_name`, `delegator_role`, `delegator_uuid`, `reason` |
| POST | `/delegations` | DPO conditional, Admin conditional, DCO conditional | `delegate_user_uuid`, `delegator_user_uuid`, `reason` | — |
| GET | `/delegations/held` | any signed-in session, own record | — | `delegate_email`, `delegate_name`, `delegate_role`, `delegate_uuid`, `delegator_email`, `delegator_name`, `delegator_role`, `delegator_uuid`, `reason` |
| GET | `/delegations/mine` | any signed-in session, own record | — | `delegate_email`, `delegate_name`, `delegate_role`, `delegate_uuid`, `delegator_email`, `delegator_name`, `delegator_role`, `delegator_uuid`, `reason` |

### Projects, approvals and sites

10 operations carry personal data.

| Method | Endpoint | Who may call it | Personal data in | Personal data out |
|---|---|---|---|---|
| GET | `/approvals` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope, R&D own rows | — | `proof_file_hash`, `uploaded_by_name`, `uploaded_by_uuid` |
| GET | `/projects` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope, R&D own rows | — | `created_by_name`, `dco_name` |
| POST | `/projects` | R&D own rows | — | `created_by_name`, `dco_name` |
| GET | `/projects/{project_uuid}` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope, R&D own rows | — | `created_by_name`, `dco_name` |
| PUT | `/projects/{project_uuid}` | R&D own rows | — | `created_by_name`, `dco_name` |
| POST | `/projects/{project_uuid}/approvals` | R&D own rows | `proof` | — |
| POST | `/projects/{project_uuid}/close` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope | `reason` | — |
| POST | `/projects/{project_uuid}/processors/{processor_uuid}/decision` | DPO every row | `reason` | — |
| POST | `/projects/{project_uuid}/transition` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope, R&D own rows | `reason` | — |
| PUT | `/sites/{site_uuid}/owner` | DPO every row, DCO Admin rows in scope, R&D own rows | `owner_user_uuid` | — |

### Notices

10 operations carry personal data.

| Method | Endpoint | Who may call it | Personal data in | Personal data out |
|---|---|---|---|---|
| GET | `/notices/{notice_uuid}` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope, R&D own rows | — | `dpo_contact` |
| PUT | `/notices/{notice_uuid}` | DPO every row | `dpo_contact` | `dpo_contact` |
| POST | `/notices/{notice_uuid}/publish` | DPO every row | — | `dpo_contact` |
| GET | `/notices/{notice_uuid}/purposes` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope, R&D own rows | — | `overridden_by_name` |
| GET | `/notices/{notice_uuid}/versions` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope, R&D own rows | — | `dpo_contact` |
| GET | `/projects/{project_uuid}/notices` | DPO every row, DCO rows in scope, DCO Admin rows in scope, RCO rows in scope, R&D own rows | — | `dpo_contact` |
| POST | `/projects/{project_uuid}/notices` | DPO every row | `dpo_contact` | `dpo_contact` |
| POST | `/projects/{project_uuid}/notices/copy` | DPO every row, R&D own rows | — | `dpo_contact` |
| POST | `/projects/{project_uuid}/notices/import` | DPO every row, R&D own rows | `document` | `dpo_contact` |
| POST | `/projects/{project_uuid}/notices/import/validate` | DPO every row, R&D own rows | `document` | — |

### Purposes, processors and sources

7 operations carry personal data.

| Method | Endpoint | Who may call it | Personal data in | Personal data out |
|---|---|---|---|---|
| GET | `/processors/{processor_uuid}/respondents` | DPO every row, Admin every row, DCO every row, DCO Admin every row, RCO every row, R&D every row | — | `contact`, `user_role`, `user_uuid` |
| POST | `/processors/{processor_uuid}/respondents` | DPO every row, Admin every row | `contact`, `user_uuid` | `contact`, `user_role`, `user_uuid` |
| GET | `/sources` | DPO every row, Admin every row, DCO every row, DCO Admin every row, RCO every row, R&D every row | — | `owner_name`, `owner_role`, `owner_user_uuid` |
| POST | `/sources` | DPO every row, Admin every row, DCO every row, DCO Admin every row, RCO every row | — | `owner_name`, `owner_role`, `owner_user_uuid` |
| GET | `/sources/{source_uuid}` | DPO every row, Admin every row, DCO every row, DCO Admin every row, RCO every row, R&D every row | — | `owner_name`, `owner_role`, `owner_user_uuid` |
| PUT | `/sources/{source_uuid}` | DPO every row, Admin every row, DCO every row, DCO Admin every row, RCO every row | — | `owner_name`, `owner_role`, `owner_user_uuid` |
| PUT | `/sources/{source_uuid}/owner` | DPO every row, Admin every row, DCO every row, DCO Admin every row, RCO every row | `owner_user_uuid` | — |

### Message templates — `/messages/*`

5 operations carry personal data.

| Method | Endpoint | Who may call it | Personal data in | Personal data out |
|---|---|---|---|---|
| GET | `/messages` | DPO every row, Admin every row | — | `body`, `sample`, `updated_by_name` |
| GET | `/messages/{key}` | DPO every row, Admin every row | — | `body`, `sample`, `updated_by_name` |
| DELETE | `/messages/{key}/{channel}` | DPO every row, Admin every row | — | `body`, `sample`, `updated_by_name` |
| PUT | `/messages/{key}/{channel}` | DPO every row, Admin every row | `body` | `body`, `sample`, `updated_by_name` |
| POST | `/messages/{key}/{channel}/preview` | DPO every row, Admin every row | `body` | `body` |

### The audit trail — `/audit/*`

5 operations carry personal data.

| Method | Endpoint | Who may call it | Personal data in | Personal data out |
|---|---|---|---|---|
| GET | `/audit` | DPO every row, Admin every row | `actor_role` | `actor_name`, `actor_role`, `actor_uuid`, `subject_name`, `subject_uuid` |
| GET | `/audit/export.csv` | DPO every row, Admin every row | `actor_role` | — |
| GET | `/audit/lookup` | DPO every row, Admin every row | — | `hint` |
| GET | `/audit/summary` | DPO every row, Admin every row | `actor_role` | — |
| GET | `/audit/{log_uuid}` | DPO every row, Admin every row | — | `actor_name`, `actor_role`, `actor_uuid`, `subject_name`, `subject_uuid` |

### Dashboard

1 operation carry personal data.

| Method | Endpoint | Who may call it | Personal data in | Personal data out |
|---|---|---|---|---|
| GET | `/dashboard` | any signed-in session, conditionally | — | `role` |


## The public surface

20 operations answer without a session. They are the ones worth re-reading
after any change, because everything else is behind an authenticated role.
Eighteen rows below: two of them group sibling endpoints that take the same
token and are protected the same way.

| Endpoint | Anonymous? | What it takes | What stops it being an oracle |
|---|---|---|---|
| `POST /auth/register` | Yes | `full_name`, `email`, `mobile`, `dob` | Rate-limited per contact and address; the account is `pending` until codes to both contacts come back |
| `POST /auth/register/verify` | Carries codes | `mobile`, `email_code`, `mobile_code` | Five attempts, ten minutes, one atomic check-and-consume |
| `POST /auth/login` | Carries the password | `login`, `password` | Five failures locks the account for 30 minutes; the reply does not distinguish a wrong password from an unknown login |
| `POST /auth/otp/request` | Yes | `contact` | **The reply is the same sentence whether or not the contact is registered**, so it cannot be used to ask whether a number is on the register |
| `POST /auth/otp/verify` | Carries the code | `contact`, `code` | Ten minutes, five attempts, one atomic check-and-consume; a verified code mints a `data_subject` session **whatever role the account holds** |
| `POST /auth/password/reset/request` | Yes | `email` | Neutral reply, rate-limited |
| `POST /auth/password/reset/confirm` | Carries the code | `email`, `code`, `new_password` | Single-use code |
| `GET /c/{token}` | Link token | the token | Returns the project, the site and the languages available, and **no personal data**; an invalid link renders no notice content. The response sets `Referrer-Policy: no-referrer`, so the token cannot leak through a referer header, and it is rate-limited per address |
| `GET /c/{token}/notice` | Link token | the token | Returns the notice text; `note` is projected out, because it is an instruction to the collector |
| `POST /c/{token}/otp` | Link token | `contact` | The token is presented, never stored in the clear; the reply is neutral |
| `POST /c/{token}/otp/verify` | Link token + code | `contact`, `code` | Signs in an **existing** data principal; it does not create one |
| `POST /c/{token}/register` | Link token | `full_name`, `email`, `mobile`, `organization_id`, `person_type` | Creates the account the link will then authenticate |
| `POST /c/{token}/consent` | Link token, and a session it minted | `grants`, `action_type`, `served_at` | `served_at` in the body is **ignored**: the moment comes from the server's own record of showing her the notice |
| `POST /rights/requests` | Carries a verification code | `contact`, `request_text` | Rate-limited; verification happens before anything is answered |
| `POST /rights/requests/verify` | Carries the code | `code` | Five attempts, ten minutes |
| `GET /rights/nominations/{token}` | Nomination token | — | Returns `principal_name` and `nominee_name` — **the one anonymous read that returns two people's names**, and the token is single-purpose, expiring and hashed at rest |
| `POST /rights/nominations/{token}/accept`, `/decline`, `/code` | Nomination token | `code` | As above |
| `POST /rights/nominee/start`, `/requests` | Carries a code or a token | `contact`, `request_text`, `evidence` | The nominee proves the trigger event before acting |

## What protects it

The controls that are already in the code, so that a review does not have to
rediscover them.

| Control | Where |
|---|---|
| A password is Argon2, and `password_hash` appears in **no** response schema | `auth_user`, and the absence is the point |
| A one-time code is never stored — Redis holds a keyed digest, and the check, the consumption and the attempt count are one atomic script | `cmp/auth/authentication/otp.py` |
| A session token is never stored; Redis is keyed by its fingerprint | `cmp/auth/sessions/service.py` |
| A consent link's token is a keyed digest, plus a sealed copy encrypted under a key derived from the application secret, so the URL can be shown again without being readable at rest | `consent_link.token`, `.token_sealed` |
| A nomination's acceptance token is hashed | `nomination.accept_token_hash` |
| A code sign-in acts as `data_subject` whatever the account's role, so a code to a staff mailbox cannot produce a staff session | [ADR 0013](../decisions/0013-every-account-is-a-data-principal.md) |
| Out of scope is 404, not 403; every real 403 is audited | [ADR 0004](../decisions/0004-scope-in-the-where-clause.md) |
| Scope is compiled into the `WHERE` clause, so an out-of-scope row is never selected in the first place | `cmp/db/repositories/*` |
| Tokens are scrubbed from access logs, in the application and in nginx | `cmp/api/middleware/access_log.py` |
| Celery task events carry the argument *count*, not the arguments | `cmp/tasks/dispatch.py` |
| Export CSV cells beginning with a formula character are written as text | `cmp/domain/exchange/service.py` |
| A notice's collector `note` is projected out of every public payload, and a test asserts it | `tests/integration/test_reported_fixes.py` |
| The audit trail is append-only and hash-chained; a trigger refuses an `UPDATE` | [domain/audit-trail.md](audit-trail.md) |
| Consent is recorded only against a serving the **server** witnessed | [ADR 0011](../decisions/0011-server-held-notice-serving.md) |

## Encrypting it: the DKMS layer

A separate service, [`backend/dkms`](../../backend/dkms/README.md), holds the key and
does the encrypting. Separate because this API holds the database: one
compromise should not be both, and the key should rotate on its own schedule.

| Layer | What it does |
|---|---|
| `backend/dkms` | `POST /encrypt/bulk` and `/decrypt/bulk` over a batch of records and a mapping of field names to data types. AES-256-GCM, a key derived per data type, the type bound into the ciphertext as AAD |
| `cmp.infrastructure.dkms` | The platform API's client. One call per batch, never per field. **Fails closed**: if the service cannot be reached, the write fails rather than storing plaintext |
| `/dkms/decrypt` in each portal | Decryption in the portal's **server**, so the browser never holds a key. The page sends back ciphertext the API already served it — which means it already passed the permission matrix — and gets plaintext |
| `useDecrypted()` | One call for a whole list. A table of two hundred rows costs one round trip, not two hundred |

**Which fields.** `cmp/infrastructure/dkms/fields.py` is this document made
executable: `ENCRYPTED_FIELDS` per table, and `LOOKUP_FIELDS` for the personal
columns that **cannot** be encrypted yet, each with its reason. A unit test
holds the two lists apart and checks the vocabulary against the service's own.

**Why the second list exists.** DKMS ciphertext is randomised — the same
address encrypts differently every time, which is the property that makes it
safe at rest. It also means an encrypted column cannot be looked up, joined,
sorted or uniquely indexed. `auth_user.email` is what you sign in with and is
unique across the register; `mobile` is where a code is sent; `submitted_contact`
is how a public request is verified and matched. Encrypting those without a
deterministic blind index beside them would not be a stricter system, it would
be a broken sign-in. The blind index is the next piece of work, and until it
lands those columns stay in plaintext **by decision, written down**, rather than
by oversight.

## Answering a data principal

Which endpoint satisfies which section, when she asks.

| She asks | The platform answers with |
|---|---|
| What do you hold about me? | `GET /me`, `GET /me/consents`, `GET /me/disclosures`, `GET /me/requests` |
| Who did you share it with? | `GET /me/disclosures` — built from `export_line`, which is written in the same transaction as the export |
| Show me what I agreed to | `GET /me/consents/{uuid}/notice` — the frozen text, by content hash, not today's wording |
| I withdraw | `POST /me/consents/{uuid}/withdraw` |
| Correct this | `PATCH /me`, and `POST /requests` for anything the office holds |
| Erase it | `POST /me/requests` with `request_type=erasure`; the scope is derived into `rights_request_item`, one row per appearance |
| Act on my behalf | `POST /me/nominations`, then the nominee's own token flow |
| I am not satisfied | `POST /me/requests/{uuid}/dispute`, which raises a grievance; one about the DPO is escalated to an administrator |

## Keeping this document true

It is produced by joining three artefacts the repository already regenerates:

| Source | What it contributes |
|---|---|
| `backend/api/openapi.json` | Every operation, and every field of every request and response schema |
| `docs/reference/access-control/endpoint_permissions.json` | The gate on each route, and the matrix's answer per role |
| `docs/reference/database/schema_inventory.json` | Every table, column, type and comment |

To redo the join after a change, regenerate those three
([CONTRIBUTING.md](../../CONTRIBUTING.md) says how), then re-run the classifier
in `docs/scripts/personal_data_scan.py`, which prints the per-module tables
above and flags any field name it has not been taught to classify. A new field
that looks personal and is not in its lists is the one thing this document
cannot catch on its own, so the script fails loudly rather than quietly
omitting it.
