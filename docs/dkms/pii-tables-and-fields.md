# DKMS — the personal data, table by table and field by field

What the platform holds about people, which column it sits in, what protects
it, and what has to happen before it can be read. Generated from the field
map the code itself uses
([`cmp/infrastructure/dkms/fields.py`](../../backend/api/src/cmp/infrastructure/dkms/fields.py))
and checked against the database on 2026-09-22. The narrative version is
[personal-data.md](../domain/personal-data.md); the endpoint list is
[the API document](backend-api.md).

## How to read the tables

| Column | Meaning |
|---|---|
| **Sealed** | The value in the row is ciphertext, `SE::…`. Written through `seal()`, never written in the clear |
| **Type** | Which of the 13 DKMS data types it is sealed as. The type is in the envelope, so a reader needs to know nothing but that it holds ciphertext |
| **Index** | A blind index column beside it, `HMAC-SHA256(normalised value)`. What the platform looks rows up by, since ciphertext cannot be searched |
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

## 1. Sealed columns — 33 across 14 tables

### `auth_user` — the person

| Column | Type | Index | What it is |
|---|---|---|---|
| `full_name` | NAME | — | The name shown everywhere a person appears |
| `email` | EMAIL | `email_idx` | Primary address: sign-in, every code, every notice |
| `secondary_email` | EMAIL | `secondary_email_idx` | A second address she asked us to use |
| `mobile` | MOBILE | `mobile_idx` | Primary number: sign-in, OTP, consent codes |
| `username` | NAME | `username_idx` | Optional staff sign-in alias |
| `organization_id` | ORG_ID | `organization_id_idx` | Employee number |
| `dob` | DOB | — | Date of birth. See `minor_until` below |

### `nomination` — who may act for her (s.14)

| Column | Type | Index |
|---|---|---|
| `nominee_name` | NAME | — |
| `nominee_email` | EMAIL | `nominee_email_idx` |
| `nominee_mobile` | MOBILE | `nominee_mobile_idx` |

### `rights_request` — what she asked for (s.11–13)

| Column | Type | Index | What it is |
|---|---|---|---|
| `submitted_name` | NAME | — | The name on the form |
| `submitted_contact` | CONTACT | `submitted_contact_idx` | Where the answer goes; `CONTACT` because it may be either kind |
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
| `import_batch` | `file_name` | FILE_NAME | The manifest somebody uploaded |
| `consent_artefact` | `ip_address` | IP | Where the consent was given from (s.6 evidence) |
| `processor_respondent` | `name` | NAME | A named person at a processor |
| `processor_respondent` | `contact` | CONTACT | How to reach them |
| `delegation` | `reason` | FREE_TEXT | Why cover was arranged |
| `person_type_history` | `reason` | FREE_TEXT | Why a person's type changed |
| `project_processor` | `decision_reason` | FREE_TEXT | Why a processor was accepted or refused |
| `project_status_history` | `reason` | FREE_TEXT | Why a project moved state |

---

## 2. The eight lookup columns, and how they stay findable

Randomised ciphertext cannot be searched, and the platform has to find rows
by these: sign-in, "is this address taken", a code to a mobile, a nomination
found by the nominee's contact, a public request verified by the contact it
gave. Each carries a **blind index** beside it —
`HMAC-SHA256(normalised value, BLIND_INDEX_KEY)`, deterministic so it can be
unique-indexed and looked up, opaque without the key. Every lookup goes
through the index; the value beside it is ciphertext and is opened only to
send something to it.

| Table | Sealed column | Index column | Normalised as |
|---|---|---|---|
| `auth_user` | `email` | `email_idx` | lowercased |
| `auth_user` | `secondary_email` | `secondary_email_idx` | lowercased |
| `auth_user` | `mobile` | `mobile_idx` | E.164 |
| `auth_user` | `username` | `username_idx` | lowercased |
| `auth_user` | `organization_id` | `organization_id_idx` | as typed (case is part of it) |
| `nomination` | `nominee_email` | `nominee_email_idx` | lowercased |
| `nomination` | `nominee_mobile` | `nominee_mobile_idx` | E.164 |
| `rights_request` | `submitted_contact` | `submitted_contact_idx` | `@` decides email or mobile |

**What this costs.** Partial search is gone. A person is found by the
*whole* email, mobile, username or employee number; by reference, uuid or
project as before; **not** by a few letters of a name. The users list, the
requests list and the audit lookup all say so in their fields.

---

## 3. Plaintext by decision, with the reason

| Where | What | Why |
|---|---|---|
| `auth_user.minor_until` | The date a person stops being a child | `cmp_is_minor()` is a date comparison in SQL and decides the s.9 case. It says that date and nothing else; `dob` itself is sealed |
| `audit_log.detail_json → ip` | The blind index of the address, not the address | The trail is hash-chained and append-only. An address written there would outlive every right to have it removed ([ADR 0015](../decisions/0015-nothing-erasable-in-a-trail-nobody-can-erase.md)) |
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
| Tables holding personal data | 20 |
| Personal columns | 54 |
| **Sealed columns** | **33** in 14 tables |
| Blind-indexed | 8 |
| Plaintext by decision | 1 (`minor_until`) |
| Plaintext by nature (ids, flags, hashes, paths) | 12 |
| API endpoints carrying any of it | 159 |

The full 54-column listing with the endpoints that carry each is in
[pii-fields-and-endpoints.md](../domain/pii-fields-and-endpoints.md),
regenerated by `docs/tools/pii-fields-and-endpoints.py`.
