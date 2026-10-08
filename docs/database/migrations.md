# Migrations

Alembic for ordering and reversibility. **Every migration is raw SQL**, with
two exceptions, 0028 and 0030, whose backfills are Python.

## Why raw SQL

The schema is exact types, constraints, triggers and grants.
Autogenerate reproduces none of that faithfully, and the difference between
`text` and `varchar(200)`, or a missing trigger, is not visible in a diff of
models.

## The two that are not

0028 and 0030 fill a column that SQL cannot compute: a keyed hash under
`BLIND_INDEX_KEY`, which the database does not hold, and for 0030 the hash of
a name that is already sealed and has to be opened through the key service
first. So each imports the application's own `cmp.infrastructure.dkms.blind`
and `client.unseal_values_sync` and writes row by row, inside the migration's
transaction. The DDL around the backfill is still SQL. The reasons are in
[ADR 0001](../decisions/0001-no-orm-raw-sql.md)'s amendment and
[ADR 0017](../decisions/0017-lookup-by-keyed-hash-and-name-ngrams.md).

What that asks of whoever runs them:

- **The same `BLIND_INDEX_KEY` as the API.** The migration reads it from its
  own environment. Production refuses the development key, but nothing
  refuses a *different* real key, and hashes computed under the wrong one
  are rows that nobody can sign in to or find. It must also equal the key
  service's `DKMS_HASH_KEY`.
- **The key service reachable, with `DKMS_ENABLED=true` and `DKMS_URL` set,**
  whenever a column being backfilled already holds `SE::` values. 0028 opens
  a sealed `organization_id`; 0030 opens every sealed name. If the service
  cannot be reached, the migration fails, and that is deliberate: a
  half-filled index is a search that silently misses rows.
- **Time with the tables locked.** `ADD COLUMN` takes an exclusive lock that
  is held until the migration commits, and the backfill (one key-service call
  per batch of 500 in 0030) runs inside it. Stop the API and the worker
  first, as for any migration against a shared server (below).

On an empty database, the CI database included, there is nothing to backfill
and neither migration calls the key service. The steps for a real one are in
the [runbook](../operations/runbook.md).

## The chain

| Rev | Contains |
|---|---|
| `0001` | Baseline: 22 tables, 25 enums, the `v_current_consent` view, indexes, CHECKs |
| `0002` | Enforcement: append-only triggers, the SHA-256 audit chain, notice freeze rules |
| `0003` | Least privilege: revokes `UPDATE`/`DELETE` from the application role on evidence tables |
| `0004` | Two defects found by exercising 0001/0002 against a real server |
| `0005` | Site ownership: a collection owner is who owns the site's source; per-notice Rule 3 overrides |
| `0006` | Delegation: cover arrangements between staff for a period |
| `0007` | The collection model: `collection`, `data_asset`, `asset_consent`, bystanders, dispositions |
| `0008` | A per-site owner override, recorded as a named exception |
| `0009` | Processor amendments: `project_processor` with the DPO's decision per processor, and requests to add one after approval |
| `0010` | One export per project, with the disclosure record written alongside the file |
| `0011` | Recoverable consent links: re-mint with a reason; the fingerprint is all that is stored |
| `0012` | Date of birth on a data principal; `cmp_is_minor()` |
| `0013` | Rights requests: the request, holders, scope items, nominations, the reference sequence |
| `0014` | The audit chain position is drawn inside the advisory lock ([ADR 0005](../decisions/0005-audit-chain-position-inside-the-lock.md)) |
| `0015` | Mobile-first contacts: nullable email, mobile required for principals and nominees by trigger, verification per medium ([ADR 0007](../decisions/0007-mobile-first-contacts.md)) |
| `0016` | Respondents per processor: portal tickets for in-house teams, email for third parties |
| `0017` | A ticket is a thread: the brief, and append-only `rights_ticket_message` |
| `0018` | Ticket robustness: withdraw, reassign, remind; file names on messages |
| `0019` | A request confined to one consent |
| `0020` | Sending a returned ticket back |
| `0021` | Response files released with the response, hashed and time-boxed |
| `0022` | A nomination records the request that invoked it and the trigger event |
| `0023` | One root consent artefact per (person, notice), by unique partial index; `export_log.file_ref` keeps the CSV as generated. Refuses to apply while duplicate roots exist |
| `0024` | `message_template`: the office's replacement words per message junction and channel |
| `0025` | `secondary_email` and `secondary_email_verified_at` on `auth_user`; a case-insensitive unique index; a CHECK that it differs from `email`; `cmp_contact_belongs_to_one_person()` so an address is nobody else's primary or secondary, raising as a unique violation |
| `0026` | `nomination.nominee_user_id`: the account the nominee accepted with, so the person is matched by account rather than by comparing contact strings. Backfilled for accepted nominations whose recorded contact reaches exactly one account |
| `0027` | Room for ciphertext: every column in `ENCRYPTED_FIELDS` narrower than `text` becomes `text`; `consent_artefact.ip_address` goes from `inet` to `text`, with `v_current_consent` dropped and recreated around it in the same transaction ([ADR 0016](../decisions/0016-personal-data-sealed-by-a-separate-key-service.md)) |
| `0028` | The blind index: a keyed hash beside each of the eight lookup columns, backfilled **in Python**; every uniqueness rule moves from the value to the hash; `*_indexed` CHECKs require the hash wherever the value is present; the contact trigger compares hashes; `minor_until` added and `cmp_is_minor()` reads it; `dob` becomes sealed `text` and `dob_is_plausible` is dropped ([ADR 0017](../decisions/0017-lookup-by-keyed-hash-and-name-ngrams.md)) |
| `0029` | The hash columns are renamed `*_idx` → `*_hash`, with the indexes that quote the name and the one trigger function whose body does. No data changes |
| `0030` | `*_ngrams text[]` with a GIN index on `auth_user.full_name`, `rights_request.submitted_name` and `nomination.nominee_name`: hashed three-character runs, so a name can be searched by part. Backfilled **in Python**, opening each sealed name through the key service |
| `0031` | Erasure that erases (S2-03): `rights_item_execution`, append-only, one row per attempt at each store that holds a scope item; `rights_request_item.executed_at`; `legal_hold`, placed once and released once by trigger (`cmp_legal_hold_release_only`), its reason sealed. Raw SQL; nothing to backfill |
| `0032` | Cross-border control (S2-04): `processor.location_country`; `restricted_country`, the s.16 list as data, listed once and lifted once by trigger, one active listing per country, never India; `export_line.destination_processor_id` and `destination_country`; `export_log.transfer_basis`. Raw SQL; nothing to backfill - earlier lines never recorded a destination |
| `0033` | One published notice per project: the partial unique index `uq_notice_one_published_per_project`. Refuses to apply over a project that already has two, naming it, rather than choosing which to keep. Publishing now supersedes every other published notice on the project and moves its live links |
| `0034` | The breach register (S3-01): `breach`, only its status changes (`cmp_breach_status_only`); append-only `breach_status_history`, `breach_determination` (outcome, reasoning, awareness for *yes*), `breach_assessment` (revisions, categories with sealed/key-exposed per category), `breach_obligation` (one per duty per breach, due time stored once) and `breach_obligation_event` (completed, not applicable, reinstated, extended, reopened). Every narrative column sealed. Raw SQL; nothing to backfill |
| `0035` | Who a breach touched (S3-02): `breach_affected_revision`, one per confirmation, with its scopes, counts and a sealed note; `breach_affected`, one row per person per breach (`breach_affected_once`) naming the revision that first listed them. Both append-only. Raw SQL; nothing to backfill |
| `0036` | Notices to the people a breach touched (S3-03): `breach_notice`, versions of the five Rule 7(1) contents, sealed, a draft editable and an approved one frozen (`cmp_breach_notice_frozen`), refused approval with any content NULL (`breach_notice_complete`), one draft per breach; `breach_notice_delivery`, append-only, one row per state per attempt per channel per person, `breach_notice_delivery_once` making a resend and a repeated outcome idempotent. Raw SQL; nothing to backfill |
| `0037` | What a returned ticket says was done (review DPDP-1): `rights_request_holder.return_outcome`, `done`, `partial` or `failed` by CHECK. NULL is a return from before 0037, read as done; nothing backfilled. Raw SQL |
| `0038` | An incident first; a breach recorded on a yes (S3-06, ADR 0022): `breach_incident_ref_seq` (logging issues `INC-`); `breach_recording`, one per breach, carrying the `BR-` reference from `breach_ref_seq`, the yes that recorded it, who and when - append-only by trigger and grant. Backfills a recording for each existing breach with a yes, from the first, carrying its existing `BR-` string; no `breach` row is touched. Downgrade drops the table and the sequence. Raw SQL |
| `0039` | The organisation's board within thirty minutes of first noticed (S3-07, ADR 0022): `breach_obligation.kind` gains `org_board`; `breach_obligation_event.reported_to` (sealed FREE_TEXT); `trg_breach_org_board_reported_to` refuses a completion of that duty without it. No backfill: incidents logged before 0039 have no such duty. Downgrade drops the trigger and column and restores the narrower CHECK as NOT VALID, so a duty already recorded stays. Raw SQL |
| `0040` | Breach tickets (S3-08, ADR 0023): `breach_ticket` (one per person per breach; only the read markers change, by `cmp_breach_ticket_read_only`; sealed instruction; optional `answer_by`; `parent_ticket_id` for S3-09's colleagues), `breach_ticket_event` (returned with an outcome and sealed summary; sent back, withdrawn, reopened with a sealed reason; closed - by CHECK; append-only) and `breach_ticket_message` (the thread, shaped like `rights_ticket_message`; append-only). Grants revoked as in 0017. Downgrade drops the three. Raw SQL |
| `0041` | Breach-only logins (S3-09, ADR 0023): `user_role` gains `breach_holder`, added alone first in an autocommit block and never removed; `breach_temporary_access`, one grant of the role per person per breach (`breach_temporary_access_open`, partial unique on the open ones), with the previous role, whether the account was made for it, and an end written once with its cause (`cmp_breach_temporary_access_end_once`; never deleted). Downgrade drops the table and function; the enum value stays, as in 0018. Raw SQL |
| `0042` | Files kept with an incident (2026-10-06): `breach_attachment` - kind (`email`, `proof`, `chat`, `other`), sealed `file_name` and `note`, `storage_ref`, `sha256`, `size_bytes`, `content_type`, who and when; append-only by trigger (`cmp_append_only`) and grant. Downgrade drops it. Raw SQL |
| `0043` | Documents a requester sends with a rights request (2026-10-07): `rights_request_attachment` - sealed `file_name`, `storage_ref`, `sha256`, `size_bytes` (> 0), `content_type`, who and when; append-only by trigger (`cmp_append_only`) and grant. Downgrade drops it. Raw SQL |
| `0044` | Notice templates (2026-10-07): `notice_template` (`template_code` minted from `notice_template_code_seq` as `TPL-0000`; `status` active/retired with `retired_at` by CHECK), `notice_template_purpose`, `notice_template_language`; `notice.template_id` (nullable FK, indexed). Editable, never deleted. Downgrade drops them. Raw SQL |
| `0045` | A breach's people from an uploaded list (2026-10-07): `breach_upload` (kind contacts/assets, sealed `file_name`, `sha256`, counts; no file kept) and `breach_contact` (sealed `full_name`, `email`, `mobile`; `email_hash`/`mobile_hash` unique per breach), both append-only by trigger and grant; `breach_affected.found_by` gains `upload`; `breach_notice_delivery.auth_user_id` nullable, `contact_id` added, exactly one by CHECK, no `portal` to a contact, `breach_notice_delivery_once` now `UNIQUE NULLS NOT DISTINCT` over both. Downgrade removes contact deliveries and upload-found rows (dev only). Raw SQL |
| `0046` | Who an email is copied to (2026-10-08): `message_copy` - `key`, sealed `address`, `address_hash` unique per key, who added it and when. Configuration, replaced as a set. Downgrade drops it. Raw SQL |
| `0047` | What is known when an incident is logged (2026-10-08): `breach` gains `origin`, `discovery`, `affected_systems`, `incident_details`, `impact_scale`, `countries_involved`, `data_nature`, `subject_types`, `entities_involved`, `third_parties` (text, sealed, optional) and `cyber_attack` (`yes`/`no`/`unknown`, CHECK); `cmp_breach_status_only` rewritten to compare the whole row but `status`. Downgrade restores the old function and drops the columns. Raw SQL |

## What 0004 fixed

**The empty-array CHECK.** `array_length(x, 1) >= 1` passes on an empty array,
because `array_length` returns NULL and a CHECK passes on NULL. Replaced with
`cardinality()`, behind a guard that refuses to apply if offending rows exist.

**A `format()` specifier in `cmp_append_only()`.** A bare `%` raised
"unrecognized format() type specifier". The statement was still refused — the
trigger worked — but the message was useless to whoever hit it.

## Guards that refuse

0004 refuses to apply while a purpose with no categories exists, 0015
refuses while a data principal or a nominee has no mobile, and 0023 refuses
while a person holds two root artefacts for one notice. 0028 and 0030 fail if
a value they must hash is sealed and the key service cannot open it. A
migration that fails loudly beats one that deletes data to satisfy itself; fix
the rows, then run it again.

Two downgrades refuse too. 0027's narrows the columns back to their old
`varchar` widths and 0028's turns `dob` back into a `date` and the mobiles
into `varchar(20)`; once anything is sealed, a row holds a value too long or
not a date, and PostgreSQL refuses the cast. That is correct: narrowing
ciphertext would truncate it into something that never decrypts again.

## Triggers rather than NOT VALID checks

0015 first tried a `NOT VALID` CHECK for the mobile rule and it broke the
update of every legacy row that lacked one, since Postgres validates such a
constraint on `UPDATE`. A `BEFORE INSERT` trigger applies the rule to new rows
only, which is what was meant.

## Reversibility is tested

The CI workflow runs `upgrade → downgrade → upgrade` on every push. The rollback path is
proven to work **before** it is needed, which is the only time anyone finds out
otherwise.

It is proven on an empty database. A database whose personal columns have been
sealed cannot go below 0028, for the reason under *Guards that refuse*; its
way back is a restore, not a downgrade.

**Never rehearse that against a database you care about.** `downgrade base`
drops every column and table the chain added, in reverse, and it does exactly
what it says on the development database too. To run the check by hand, give
it a database of its own:

```bash
docker exec compass-db-1 createdb -U cmp cmp_ci      # or createdb, natively
POSTGRES_DB=cmp_ci alembic upgrade head
POSTGRES_DB=cmp_ci alembic downgrade base
POSTGRES_DB=cmp_ci alembic upgrade head
docker exec compass-db-1 dropdb -U cmp cmp_ci
```

And stop the API and the worker first if they share the server: a DDL waiting
on a lock their pooled connections hold runs into `DB_STATEMENT_TIMEOUT_MS` and
fails part-way, which leaves the schema at whichever revision it reached.
This paragraph exists because that happened, on 21 September 2026, to the
development database: the downgrade reached 0018 before the upgrade stalled,
and the columns and two tables added by 0019–0026 came back empty.

## The env is synchronous

`migrations/env.py` uses a sync engine. psycopg's async mode cannot run under
Alembic's runner, and a migration is not a place to be clever about event loops.

## Sealing what the migrations did not

0027 and 0028 change types and add hashes; they do not encrypt the rows
already there. `scripts/reseal.py` does that, and can run at any time after
0028, since from that revision on every lookup reads the hash and no longer
cares what the value column holds. It is idempotent: a value already `SE::` is
skipped. `--check` reports plaintext left in sealed columns and changes
nothing; `--table` limits it to one table.

Three things about it belong here rather than only in the runbook:

- It refuses to run with `DKMS_ENABLED=false`.
- For the four append-only tables it writes to (`consent_artefact`,
  `rights_ticket_message`, `project_status_history`,
  `person_type_history`), it disables the append-only trigger for the length
  of that column's transaction and re-enables it before the commit
  (reseal.py:85-98). That needs the table owner: the application role cannot
  `ALTER TABLE`, and 0003 revoked its `UPDATE` on those tables. This bypass
  is under review; see the amendment to
  [ADR 0002](../decisions/0002-evidence-enforced-in-the-database.md).
- It works one transaction per column, so a table being resealed is locked
  against writes until that column is done.

How to run it is in the [runbook](../operations/runbook.md).

## Adding one

```bash
alembic revision -m "what it does"      # inside backend/api's .venv
```

Then write the SQL by hand. Both directions. Test the downgrade before you commit
the upgrade. If a column holds personal data, add it to `ENCRYPTED_FIELDS` and
give it `text`: ciphertext is about four thirds of the plaintext plus 45 bytes.
