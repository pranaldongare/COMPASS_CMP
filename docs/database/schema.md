# Schema

32 tables, 39 enums, 1 view, 27 triggers, 42 named CHECK constraints and 93
foreign keys, as of migration 0030. Those counts are read from the PostgreSQL
catalogs after replaying every migration, not maintained by hand.

The migrations are the source of truth: 0001 transcribed the original
`DATA-MODEL.md` specification (which is not in this repository) and 0002 to
0030 built the rest. This document explains the parts whose shape is not
obvious; the relationships are drawn in
[docs/architecture/domain-model.md](../architecture/domain-model.md),
and every column, constraint, index and trigger is listed and diagrammed in
[docs/reference/database/](../reference/database/README.md) — a snapshot, so check
its stated commit before trusting it against a later change.

## Table groups

| Group | Tables |
|---|---|
| Identity | `auth_user`, `person_type_history`, `delegation` |
| Registry | `purpose`, `processor`, `processor_respondent`, `data_source` |
| Projects | `project`, `project_status_history`, `project_approval`, `project_site`, `project_processor` |
| Notices | `notice`, `notice_purpose`, `notice_language` |
| Consent | `consent_link`, `consent_artefact`, `consent_purpose_grant` |
| Exchange | `export_log`, `export_line`, `import_batch`, `collection`, `data_asset`, `asset_consent` |
| Rights | `rights_request`, `rights_request_holder`, `rights_request_item`, `rights_ticket_message`, `rights_response_file`, `nomination` |
| Audit | `audit_log` |

## The view

`v_current_consent` resolves the supersession chain to the artefact that is
currently in force for each (subject, notice) pair. Consent status is **derived
from it on every read, never stored** — a denormalised status column is a second
copy of the truth and the copy goes stale the first time a grant changes without
it.

## Shapes worth explaining

**`consent_artefact` has no status column.** Status is derived from the grants:
all granted is `consented`, some is `partial`, none is `declined`, and
`is_withdrawal` is `withdrawn`.

**Withdrawal supersedes.** A withdrawal is a new artefact with
`supersedes_consent_id` pointing at the one it replaces. The earlier row is never
touched — and could not be, since the table refuses `UPDATE`.

**`asset_consent` allows a NULL `consent_id`.** That is the bystander: somebody
in frame who never consented. The row exists precisely so they can be found and
dealt with. Forbidding it would mean the unlawful state existed and was invisible.

**`password_hash` is nullable.** Data subjects have no password. See
[../security/authentication.md](../security/authentication.md).

**`email` is nullable too, since 0015.** A data principal is identified by
mobile first; a `BEFORE INSERT` trigger requires the mobile for that role and a
CHECK requires an email for staff. Verification is stamped per medium
(`mobile_verified_at`, `email_verified_at`). The same shape applies to a
nominee (`nominee_mobile`, `nominee_email`). Since 0028 the values are sealed,
and the rules that compare them compare their hashes (below).

**`audit_log.log_id` has no default, since 0014.** The chain trigger draws it
from the sequence inside the advisory lock, so chain order is commit order.

**`rights_request.reference` is minted by the database.** `RR-<year>-<seq>`,
unique, and the thing a person quotes. `due_at` is stamped at receipt and
never recomputed.

**One root per (person, notice), since 0023.** `uq_artefact_supersedes_once`
stops a chain forking; `uq_artefact_one_root_per_notice` stops two chains
starting. The service also takes a per-pair advisory lock before it reads
what is current, so a racing second capture becomes a supersession rather
than a constraint error.

**`export_log.file_ref`, since 0023,** is the CSV exactly as generated, kept
in storage; the download serves it back. Exports from before it re-render
and their `file_hash` says whether the result still matches.

**`asset_consent.disposition`** is where an erasure lands: the person's junction
row, never the asset, because an asset may hold several people.

## Sealed columns, and how they are still found

Since 0027 the personal columns hold ciphertext, written by the key service on
the way in and opened by the portals on the way out
([ADR 0016](../decisions/0016-personal-data-sealed-by-a-separate-key-service.md)).
`ENCRYPTED_FIELDS` in `cmp.infrastructure.dkms.fields` is the list; what each
column holds is in [docs/dkms/pii-tables-and-fields.md](../dkms/pii-tables-and-fields.md).
Four things follow for the schema:

**Personal columns are `text`.** A sealed value is `SE::` and base64url,
about four thirds of the plaintext plus 45 bytes, so a name that fit
`varchar(200)` does not fit once sealed. 0027 and 0028 widened them;
`consent_artefact.ip_address` went from `inet` to `text` and `auth_user.dob`
from `date` to `text`. The lengths are bounded by the API's validation now,
not the column.

**Uniqueness lives on the hash.** Randomised ciphertext differs on every
write, so a unique index on it would admit every duplicate. Beside each column
the platform looks rows up by sits `<column>_hash`, `HMAC-SHA256(normalised
value)` under `BLIND_INDEX_KEY`
([ADR 0017](../decisions/0017-lookup-by-keyed-hash-and-name-ngrams.md)):

| Table | Hashed columns |
|---|---|
| `auth_user` | `email_hash`, `secondary_email_hash`, `mobile_hash`, `username_hash`, `organization_id_hash` — each unique (`auth_user_*_hash_key`) |
| `nomination` | `nominee_email_hash`, `nominee_mobile_hash` — indexed, not unique |
| `rights_request` | `submitted_contact_hash` — indexed, not unique |

A `*_indexed` CHECK on each (`auth_user_email_indexed`,
`nomination_mobile_indexed`, `rights_request_contact_indexed` and the rest)
refuses a row that has the value and not its hash, so a raw write that forgets
the hash fails instead of escaping every rule above. It cannot check that the
hash is *right*: that depends on the writer using the same key and the same
normalisation. `auth_user_secondary_email_differs` and the
`cmp_contact_belongs_to_one_person()` trigger compare `email_hash` and
`secondary_email_hash`.

**A name can be searched by part.** `auth_user.full_name_ngrams`,
`rights_request.submitted_name_ngrams` and `nomination.nominee_name_ngrams`
(0030) are `text[]` of hashed three-character runs, with a GIN index each; a
search asks `@>` for every run of the term. Only these three: a set of runs
leaks letter frequencies that a single hash does not, so contacts and free
text never get one. `nominee_name_ngrams` is written but no query searches it
yet.

**Age is `minor_until`, in the clear.** A sealed date cannot be compared, so
0028 added `auth_user.minor_until` (date of birth plus eighteen years) and
`cmp_is_minor()` reads it. The `dob_is_plausible` CHECK went with the date
type, and the rule now lives only in the API. Registration applies it (a date
in 1900 or later, before today: `api/routers/v1/auth.py:64-79`); `PATCH /me`
takes a `date` with no such check (`api/routers/v1/me.py:73`), so since 0028
nothing stops an implausible date arriving that way.

## The deliberate deviation from DATA-MODEL.md

The document specifies:

```sql
CHECK (array_length(data_categories, 1) >= 1)
```

That constraint **admits an empty array**. `array_length` returns `NULL` for one,
`NULL >= 1` is `NULL`, and a CHECK passes on `NULL`. Reproduced with a real
`INSERT` before anything was changed.

Migration 0004 replaces it with `cardinality(...) >= 1`, behind a guard that
refuses to apply if offending rows already exist — a migration that fails loudly
beats one that deletes data to satisfy itself.

## Enum parity

`core/enums.py` mirrors all 39 PostgreSQL enum types.
`tests/integration/database/test_enum_parity.py` asserts members and order
against a live server, in both directions, so the mirror cannot drift silently.
