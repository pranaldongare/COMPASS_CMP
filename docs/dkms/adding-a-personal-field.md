# DKMS — adding a personal field

Everything that changes together when a column that holds something about a
person joins the platform, in the order it is done. Each step says where it
lives and what catches it if it is skipped - and three of them are caught by
nothing, which is why this page exists. Companion to
[the field list](pii-tables-and-fields.md), [the backend](backend-api.md)
and [the frontend layer](frontend-layer.md); the two decisions it follows
are [ADR 0016](../decisions/0016-personal-data-sealed-by-a-separate-key-service.md)
and [ADR 0017](../decisions/0017-lookup-by-keyed-hash-and-name-ngrams.md).

## First, three questions

| Question | If yes |
|---|---|
| Is it about a person - or free text, or a file name, which sooner or later is? | It is sealed. The rest of this page applies |
| Does the platform **find rows by it whole** - sign-in, "is this taken", a code sent to it, a match on a contact? | It also gets a keyed hash, `<column>_hash` |
| Will staff type **part of it** into a search box, and be unable to do their job otherwise? | It also gets hashed runs, `<column>_ngrams`. Almost always no: the runs leak letter statistics, a contact never has them, and a fourth column needs its reason written down |

A column that cannot be sealed at all - because SQL compares it, as
`minor_until` is compared for the section 9 test - goes in `LOOKUP_FIELDS`
with its reason instead, and not in `ENCRYPTED_FIELDS`.

## The checklist

### 1. The field map — `backend/api/src/cmp/infrastructure/dkms/fields.py`

- `ENCRYPTED_FIELDS[table][column] = DataType.X`. Pick the type the value
  *is*, not the column's name: a contact that may be either kind is
  `CONTACT`. The type is written into every envelope and a value sealed as
  one type cannot be opened as another, so changing it later means
  re-sealing every row.
- If it is found whole: `BLIND_INDEXED[table][column] = "<column>_hash"`.
- If it is searched by part: `NGRAM_INDEXED[table][column] = "<column>_ngrams"`,
  with the reason in the comment above the map.

Caught by `tests/unit/infrastructure/test_dkms_field_map.py`: a type the key
service does not have (it parses `backend/dkms/app/dkms/types.py`), a column
in both `ENCRYPTED_FIELDS` and `LOOKUP_FIELDS`, a lookup exclusion with no
reason, `GENERIC` anywhere. And by `test_hash_columns_match_the_database.py`:
every `BLIND_INDEXED` entry must end `_hash`. That file also pins the map to
exactly the eight columns migration 0029 renamed, so **a ninth hash column
fails it** until its expectation is widened to include the new migration.

A new type is a change to the key service as well: `DataType` and
`TYPE_IDS` in `backend/dkms/app/dkms/types.py`, the same two in
`fields.py`, and `TYPE_BY_ID` in both portals' `lib/dkms/deep.ts`.

### 2. The hash kind — `backend/api/src/cmp/infrastructure/dkms/blind.py`

A hashed column is hashed as one of the kinds in `Kind` - `email`,
`mobile`, `username`, `contact`, `text`, `ip` - and the kind decides the
normalisation: lowercased, E.164, `@`-decides-which, or as typed. Use an
existing kind. A new one changes `normalise()` here **and** `LABELS` and
`normalise()` in the key service's `backend/dkms/app/dkms/searchable.py`,
because the platform and the service must compute the same hash from the
same value; `backend/dkms/tests/test_searchable.py` pins one side and
`tests/unit/infrastructure/` the other.

### 3. The migration — `backend/api/migrations/versions/`

- The column becomes `text`. Ciphertext is about 4/3 the length plus 45
  bytes, so a `varchar(20)` that held a mobile cannot hold its ciphertext.
  A view over the column is dropped and recreated around the change, as
  0027 did.
- `<column>_hash text`, and anything that constrained the value moves onto
  the hash: a unique constraint becomes a unique index on the hash (0028's
  `<table>_<column>_idx_key`, renamed `_hash_key` by 0029), and a CHECK
  that the hash is present whenever the value is -
  `CHECK (<column> IS NULL OR <column>_hash IS NOT NULL)`, named like
  `auth_user_email_indexed`. A trigger that compared the value compares the
  hash instead, as 0028 rewrote `trg_contact_belongs_to_one_person`.
- `<column>_ngrams text[]` with `CREATE INDEX idx_<table>_<column>_ngrams …
  USING gin`, as 0030 did. GIN, because the question is "does this array
  contain all of these".
- **The backfill is Python, in the migration**, because the key is not in
  the database. Hash from the plaintext with `index_of` / `ngrams_of`
  imported from the application, so the migration and the code agree. Rows
  already sealed are opened first with `unseal_values_sync`, as 0030 does,
  and an unreachable key service fails the migration - a half-filled index
  is a search that silently misses rows.
- `downgrade()` undoes it; run `alembic downgrade -1` and `upgrade head`
  before committing, and add the revision to
  [migrations.md](../database/migrations.md).

### 4. The repository write — `backend/api/src/cmp/db/repositories/`

- Pass the value through `seal(table, row)` (or `seal_many`) in the
  repository, never in a service or router - the repositories are the one
  layer every write goes through.
- Compute the hash and the runs **from the plaintext, in the same
  statement**: `index_of(kind, value)` into `<column>_hash`,
  `ngrams_of(value)` into `<column>_ngrams`. `users.create` and
  `rights.create` are the pattern; an update recomputes them with the value
  (`users.py`, `full_name_ngrams = COALESCE(%s, full_name_ngrams)`). A row
  written without its hash or runs is a row nobody can find.
- A value copied from another sealed row arrives as ciphertext. Open it
  with `unseal_value` before hashing, as `rights.create` does for a copied
  contact, or re-seal it under this column's type, as `add_respondent`
  does.
- In SQL: look it up with `<column>_hash = %s`, search it with
  `<column>_ngrams @> %s` (add the clause only when `search_ngrams(term)`
  is non-empty, or a two-letter term matches every row), and never
  `ILIKE`, `ORDER BY` or `||` it. Ciphertext sorts arbitrarily, and a sealed
  value glued to text is a string nobody can open that sinks the whole
  decrypt batch it travels in. Return `label_parts` instead of a
  concatenated label.

Caught by `tests/unit/infrastructure/test_no_sealed_column_is_concatenated.py`
(the `||`), `tests/integration/test_search_over_sealed_names.py` (the
pattern, for the three names), and the HTTP suite (step 7). A missing hash
on write is caught by the migration's CHECK.

### 5. Where the backend needs the plaintext

Nothing, if the value only goes to a page: the API serves it sealed and the
portal opens it. If the backend has to *act* on it - address a message, put
it in a URL or a file - open it with `opened()` or `unseal_value()` at that
one point, and add the place to
[the backend document's list](backend-api.md#where-the-backend-decrypts).
`deliver()` opens a recipient and every template variable on its own.

### 6. The rows already there — `backend/api/scripts/reseal.py`

It walks `ENCRYPTED_FIELDS`, so a new column in a table it already knows is
picked up. It is **not** automatic for:

- a new table - add its primary key to `PRIMARY_KEY`;
- a hashed column - add its kind to `INDEX_KIND`, so the hash is recomputed
  in the same `UPDATE` as the seal;
- an append-only table - add its trigger to `APPEND_ONLY`, so the script can
  set it aside inside its own transaction;
- `*_ngrams` - the script does not write runs at all. The migration's
  backfill is the only thing that does.

Then `python scripts/reseal.py --table <table>` and
`python scripts/reseal.py --check`, which exits 1 while anything is left.

### 7. The HTTP suite — `backend/api/tests/http/contract.py`

`contract.SEALED` is built from `ENCRYPTED_FIELDS`, so the column's own name
is checked in every response from the moment step 1 lands. What it cannot
derive is an **alias**: a response that serves the value under another name
(`owner_name`, `subject_email`, `*_by_name`) needs that name added to
`SEALED` by hand. An endpoint new to the value must also be called by the
suite; `test_zz_coverage.py` fails when a documented personal-data endpoint
was never called, and checks every sealed column holds only ciphertext after
the run.

### 8. Both portals — `frontend/{console,portal}/src/lib/dkms/field-types.ts`

Add the column, and every alias from step 7, to `TYPE_BY_FIELD` with the
same type as `ENCRYPTED_FIELDS`, **in both portals**. This is the fallback
the walker uses when the envelope is not this implementation's; with this
service it is never consulted, so leaving it out breaks nothing today and
breaks the page the day another key service stands behind this one.
**Nothing checks it.** Leave out a name that is somebody else's field on
other tables - `name` and `contact` are why the list is not generated.

Nothing else in the portals changes: the interceptor opens every `SE::` in
every response before any page sees it.

### 9. The documents

- `docs/tools/personal-data-scan.py`: teach the classifier the field name
  if it looks personal; it reports it UNCLASSIFIED and exits non-zero
  otherwise.
- `docs/tools/pii-fields-and-endpoints.py`: add the column to `COLUMNS`, and
  to the sealed list in its prose, which is hand-kept. Then regenerate
  [pii-fields-and-endpoints.md](../domain/pii-fields-and-endpoints.md):
  `python3 docs/tools/pii-fields-and-endpoints.py`.
- [pii-tables-and-fields.md](pii-tables-and-fields.md), by hand: the row,
  its type, its hash or runs, and the counts in section 4.
- [personal-data.md](../domain/personal-data.md), if the table or the store
  is new to it.
- The schema reference, against a scratch database replayed from the chain:

  ```bash
  createdb cmp_ref && POSTGRES_DB=cmp_ref alembic upgrade head
  python3 docs/tools/generate-schema-docs.py --database cmp_ref
  ```

- `backend/api/openapi.json`, if a response gained the field
  ([CONTRIBUTING.md](../../CONTRIBUTING.md#changing-the-api) has the
  command), and `npm run api:check` in each portal.

## Done when

```bash
cd backend/api && pytest                 # the field map, the SQL, the HTTP contract
python scripts/reseal.py --check         # zero plaintext rows
cd frontend/console && npm run verify    # and in frontend/portal
```

and on the running stack the new value shows as `SE::…` in the database, in
the clear on the page, and - if it has a hash or runs - finds its row.
