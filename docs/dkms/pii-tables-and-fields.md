# DKMS — the personal data, table by table and field by field

What the platform holds about people, which column it sits in, what protects
it, and what has to happen before it can be read. Written by hand from the
field map the code itself uses
([`cmp/infrastructure/dkms/fields.py`](../../backend/api/src/cmp/infrastructure/dkms/fields.py)),
which is the authority - where this page and that file disagree, the file is
right - and checked against it on 2026-10-08, at migration 0049. The
narrative version, every store and not only the database, is
[personal-data.md](../domain/personal-data.md); the endpoints are in
[the backend document](backend-api.md). Adding a column is
[its own checklist](adding-a-personal-field.md).

## How to read the tables

| Column | Meaning |
|---|---|
| **Sealed** | The value in the row is ciphertext, `SE::…`. Written through `seal()`, never written in the clear |
| **Type** | Which of the 13 DKMS data types it is sealed as. The type is in the envelope, so a reader needs to know nothing but that it holds ciphertext |
| **Hash** | A keyed-hash column beside it, `*_hash` = `HMAC-SHA256(normalised value, BLIND_INDEX_KEY)`. What the platform looks rows up by *whole*, since ciphertext cannot be searched |
| **Runs** | A `*_ngrams text[]` beside it, holding the hashed three-character runs of the value, with a GIN index. What a search by *part* of a value matches, with `@>` |
| **Plain** | Deliberately in the clear, with the reason |

The 13 types and their ids (byte 3 of every envelope):

| Id | Type | Id | Type | Id | Type |
|---|---|---|---|---|---|
| 1 | `NAME` | 6 | `ORG_ID` | 11 | `FILE_NAME` |
| 2 | `EMAIL` | 7 | `PERSON_TYPE` | 12 | `GOVT_ID` |
| 3 | `MOBILE` | 8 | `ADDRESS` | 13 | `GENERIC` |
| 4 | `CONTACT` | 9 | `IP` | | |
| 5 | `DOB` | 10 | `FREE_TEXT` | | |

---

## 1. Sealed columns — 78 across 29 tables

### `auth_user` — the person

| Column | Type | Hash column | What it is |
|---|---|---|---|
| `full_name` | NAME | `full_name_ngrams` (runs) | The name shown everywhere a person appears; searched by part of it |
| `email` | EMAIL | `email_hash` | Primary address: sign-in, every code, every notice |
| `secondary_email` | EMAIL | `secondary_email_hash` | A second address she asked us to use |
| `mobile` | MOBILE | `mobile_hash` | Primary number: sign-in, OTP, consent codes |
| `username` | NAME | `username_hash` | Optional staff sign-in alias |
| `organization_id` | ORG_ID | `organization_id_hash` | Employee number |
| `dob` | DOB | — | Date of birth. See `minor_until` below |

### `nomination` — who may act for her (s.14)

| Column | Type | Hash column |
|---|---|---|
| `nominee_name` | NAME | `nominee_name_ngrams` (runs) |
| `nominee_email` | EMAIL | `nominee_email_hash` |
| `nominee_mobile` | MOBILE | `nominee_mobile_hash` |

### `rights_request` — what she asked for (s.11–13)

| Column | Type | Hash column | What it is |
|---|---|---|---|
| `submitted_name` | NAME | `submitted_name_ngrams` (runs) | The name on the form, searched by part of it before it is matched to an account |
| `submitted_contact` | CONTACT | `submitted_contact_hash` | Where the answer goes; `CONTACT` because it may be either kind |
| `request_text` | FREE_TEXT | — | Her words |
| `verification_note` | FREE_TEXT | — | How identity was established, in the DPO's words |
| `refusal_reason` | FREE_TEXT | — | Why it was refused |
| `remedy_text` | FREE_TEXT | — | What a grievance decision ordered |
| `response_text` | FREE_TEXT | — | The answer sent to her |

### `rights_request_holder` — the team asked to answer

| Column | Type |
|---|---|
| `responder_name` | NAME |
| `responder_contact` | CONTACT |
| `instruction` | FREE_TEXT |
| `return_summary` | FREE_TEXT |
| `sent_back_reason` | FREE_TEXT |

Two **jsonb** columns on this table carry sealed values inside them:
`brief` (the subject's name and contacts, copied as the account row holds
them, opened only for the prose of the mail) and `contact_log` (each line's
`to`, sealed as the holder row holds it). Neither is a sealed *column*; both
carry ciphertext their reader opens like any other value.

### The rest

| Table | Column | Type | What it is |
|---|---|---|---|
| `rights_ticket_message` | `body` | FREE_TEXT | What was written on a ticket |
| `rights_ticket_message` | `evidence_name` | FILE_NAME | The file a holder attached |
| `rights_response_file` | `file_name` | FILE_NAME | A file released with a response |
| `rights_request_attachment` | `file_name` | FILE_NAME | The name a document the requester sent was uploaded with (2026-10-07) |
| `import_batch` | `file_name` | FILE_NAME | The manifest somebody uploaded |
| `consent_artefact` | `ip_address` | IP | Where the consent was given from (s.6 evidence) |
| `processor_respondent` | `name` | NAME | A named person at a processor |
| `processor_respondent` | `contact` | CONTACT | How to reach them |
| `delegation` | `reason` | FREE_TEXT | Why cover was arranged |
| `person_type_history` | `reason` | FREE_TEXT | Why a person's type changed |
| `project_processor` | `decision_reason` | FREE_TEXT | Why a processor was accepted or refused |
| `project_status_history` | `reason` | FREE_TEXT | Why a project moved state |
| `legal_hold` | `reason` | FREE_TEXT | Why the office stopped an erasure (S2-03) |

### The breach register (S3-01)

Every narrative the office writes about a breach, since any of it may name
somebody - whose laptop, which account, who caused it.

| Table | Column | Type | What it is |
|---|---|---|---|
| `breach` | `title` | FREE_TEXT | The few words the office knows it by |
| `breach` | `location_detail` | FREE_TEXT | Where it occurred, in words |
| `breach` | `origin`, `discovery`, `affected_systems`, `incident_details`, `impact_scale`, `countries_involved`, `data_nature`, `subject_types`, `entities_involved`, `third_parties` | FREE_TEXT | What is known when an incident is logged (0047); any may name a person or a company |
| `breach_status_history` | `reason` | FREE_TEXT | Why it was reopened |
| `breach_determination` | `reasoning` | FREE_TEXT | Why it is, or is not, a personal data breach |
| `breach_assessment` | `nature_extent` | FREE_TEXT | Rule 7(1)(a), 7(2)(a) |
| `breach_assessment` | `likely_impact` | FREE_TEXT | Rule 7(2)(a) |
| `breach_assessment` | `consequences` | FREE_TEXT | Rule 7(1)(b) |
| `breach_assessment` | `circumstances` | FREE_TEXT | Rule 7(2)(b)(ii) |
| `breach_assessment` | `mitigation` | FREE_TEXT | Rule 7(1)(c), 7(2)(b)(iii) |
| `breach_assessment` | `protective_steps` | FREE_TEXT | Rule 7(1)(d) |
| `breach_assessment` | `caused_by_findings` | FREE_TEXT | Rule 7(2)(b)(iv): it may name an employee |
| `breach_assessment` | `remedial_measures` | FREE_TEXT | Rule 7(2)(b)(v) |
| `breach_assessment` | `contact_point` | FREE_TEXT | Rule 7(1)(e): who answers questions |
| `breach_obligation_event` | `note` | FREE_TEXT | A note on a duty's submission or extension |
| `breach_obligation_event` | `reported_to` | FREE_TEXT | Whom the organisation's board was told through, on that duty's completion (S3-07) |
| `breach_ticket` | `instruction` | FREE_TEXT | What the holder is asked, or the adding colleague's note (S3-08) |
| `breach_ticket_event` | `summary` | FREE_TEXT | The holder's account of what was done, with a return |
| `breach_ticket_event` | `reason` | FREE_TEXT | Why the DPO sent a ticket back, withdrew or reopened it |
| `breach_ticket_message` | `body` | FREE_TEXT | A message on a breach ticket's thread |
| `breach_ticket_message` | `evidence_name` | FILE_NAME | The name a file on the thread was uploaded with |
| `breach_attachment` | `file_name` | FILE_NAME | The name a file kept with an incident was uploaded with (2026-10-06) |
| `breach_attachment` | `note` | FREE_TEXT | What the file is, in a few words |
| `breach_contact` | `full_name` | NAME | Somebody a breach touched with no account, from an uploaded list (2026-10-07) |
| `breach_contact` | `email` | EMAIL | Their email; blind index `email_hash` |
| `breach_contact` | `mobile` | MOBILE | Their mobile; blind index `mobile_hash` |
| `breach_upload` | `file_name` | FILE_NAME | The name an uploaded list came with |
| `message_copy` | `address` | EMAIL | Who the office copies an email to - a mailbox, possibly a person's; blind index `address_hash` (2026-10-08) |
| `breach_affected_revision` | `note` | FREE_TEXT | What a revision of who it touched is based on (S3-02) |
| `breach_notice` | `what_happened` | FREE_TEXT | Rule 7(1)(a), as told to everyone it touched (S3-03) |
| `breach_notice` | `consequences` | FREE_TEXT | Rule 7(1)(b) |
| `breach_notice` | `measures` | FREE_TEXT | Rule 7(1)(c) |
| `breach_notice` | `protective_steps` | FREE_TEXT | Rule 7(1)(d) |
| `breach_notice` | `contact` | FREE_TEXT | Rule 7(1)(e) |

---

## 2. The eleven lookup columns and their hash columns

Randomised ciphertext cannot be searched, and the platform has to find rows
by these: sign-in, "is this address taken", a code to a mobile, a nomination
found by the nominee's contact, a public request verified by the contact it
gave, a person on a breach's uploaded list or an office copy address that
must not be added twice. Each carries a **keyed hash** beside it, named `*_hash` —
`HMAC-SHA256(normalised value, BLIND_INDEX_KEY)`, deterministic so it can be
unique-indexed and looked up, opaque without the key. Every lookup goes
through the index; the value beside it is ciphertext and is opened only to
send something to it.

| Table | Sealed column | Hash column | Normalised as |
|---|---|---|---|
| `auth_user` | `email` | `email_hash` | lowercased |
| `auth_user` | `secondary_email` | `secondary_email_hash` | lowercased |
| `auth_user` | `mobile` | `mobile_hash` | E.164 |
| `auth_user` | `username` | `username_hash` | lowercased |
| `auth_user` | `organization_id` | `organization_id_hash` | as typed (case is part of it) |
| `nomination` | `nominee_email` | `nominee_email_hash` | lowercased |
| `nomination` | `nominee_mobile` | `nominee_mobile_hash` | E.164 |
| `rights_request` | `submitted_contact` | `submitted_contact_hash` | `@` decides email or mobile |
| `breach_contact` | `email` | `email_hash` | lowercased |
| `breach_contact` | `mobile` | `mobile_hash` | E.164 |
| `message_copy` | `address` | `address_hash` | lowercased |

**What this costs.** A contact is matched *whole*: a complete address, a
complete number, a complete username or employee number. Half an address
matches nothing, which is the point - all an exact hash ever leaks is
equality.

## 2a. Searching by part of a name

Three columns carry a second index, `*_ngrams`: the value cut into
overlapping runs of three characters, each hashed under the same key, stored
as a `text[]` with a GIN index on it. A search hashes the runs of the term
and asks for rows holding all of them (`@>`), so "shu" finds "Amruta
Shukla". The answer is candidates, not certainty - a row holding the runs of
"ana" might be "banana" - which for a search box is what is wanted.

| Table | Sealed column | Runs column | Where it is used |
|---|---|---|---|
| `auth_user` | `full_name` | `full_name_ngrams` | the staff register (`GET /users?q=`), the audit trail's About picker, and `GET /requests?q=` for the account a request was matched to |
| `rights_request` | `submitted_name` | `submitted_name_ngrams` | `GET /requests?q=`, and the About picker when it looks for a rights request |
| `nomination` | `nominee_name` | `nominee_name_ngrams` | written with every nomination; **no query reads it yet** |

Two of those uses are narrower than they sound. `GET /requests?q=` answers
in the API, but the console's requests list has no search box and never
sends `q`. And the nominee's runs are kept current so that a search can be
added without a backfill, but nothing searches them today.

**What the runs cost, stated plainly.** They leak more than an exact hash.
Anyone holding the column can count how often each run appears and compare
that against the letter statistics of a language; with enough rows, common
names can be recovered without the key. That is inherent to substring search
over encrypted data, not a flaw in this implementation. So the list above is
short by design, and a **contact is never in it** - contacts are searched
whole. Adding a fourth column means accepting that trade for that column,
and writing down why
([ADR 0017](../decisions/0017-lookup-by-keyed-hash-and-name-ngrams.md)).

---

## 3. Plaintext by decision, with the reason

| Where | What | Why |
|---|---|---|
| `auth_user.minor_until` | The date a person stops being a child | `cmp_is_minor()` is a date comparison in SQL and decides the s.9 case. It says that date and nothing else; `dob` itself is sealed |
| `audit_log.detail_json → ip` | The keyed hash of the address (`index_of("ip", …)`), not the address | The trail is hash-chained and append-only. An address written there would outlive every right to have it removed ([ADR 0015](../decisions/0015-nothing-erasable-in-a-trail-nobody-can-erase.md)) |
| `audit_log.detail_json` | No emails, no free-text reasons | Reasons live in the sealed row they belong to; the trail records `reason_given: true` |
| Ids, uuids, hashes, tokens | — | Identifiers and digests, personal only by reference |

Rows written before sealing were converted by
[`scripts/reseal.py`](../../backend/api/scripts/reseal.py); `--check`
reports zero plaintext, and the HTTP suite asks the same question of every
sealed column after everything it writes.

---

## 4. The whole inventory in numbers

| | |
|---|---|
| Tables holding personal data | 38 |
| Personal columns | 108 |
| **Sealed columns** | **78** in 29 tables |
| With a `*_hash` lookup column | 11 |
| With a `*_ngrams` search column | 3 |
| Plaintext by nature (ids, flags, hashes, tokens, storage paths, jsonb) | 30 - the other 108 − 78 |
| Plaintext by decision | 1 (`minor_until`, derived from `dob` and not counted in the 108) |
| API endpoints carrying any of it | 228, of 324 |

The full 108-column listing with the endpoints that carry each is in
[pii-fields-and-endpoints.md](../domain/pii-fields-and-endpoints.md),
regenerated by `docs/tools/pii-fields-and-endpoints.py`.
