# COMPASS complete database schema

Generated from the catalogue of a scratch database built by replaying migrations **0001 → 0035**, on 2026-09-30. Rebuild it with `python3 docs/tools/generate-schema-docs.py --database <db>`; nothing here is maintained by hand.

## Open the diagrams

- **[Complete schema SVG](complete_schema.svg)** — every table/view column, type, primary key, unique-constraint membership, nullability and all 122 foreign-key constraints.
- [Relationship overview SVG](schema_overview.svg) — all tables and relationships with compact cards.
- [Enum reference SVG](enums.svg) — all 39 PostgreSQL enum types and values.
- [Column and constraint reference](table_reference.md) — exact defaults, comments, foreign keys, CHECKs, indexes and triggers.
- [Enum values as text](enum_reference.md).

The complete SVG is a large, zoomable vector drawing. Open it in a browser or vector editor and zoom in. Hover a relationship for its foreign-key name, source/target columns and constraint definition. For a smaller drawing, use the module SVGs below.

## Module SVGs

| Module | Application tables / views | Diagram |
| --- | --- | --- |
| Identity | `auth_user`, `person_type_history`, `delegation` | [Open SVG](modules/identity.svg) |
| Registry | `purpose`, `processor`, `processor_respondent`, `data_source` | [Open SVG](modules/registry.svg) |
| Projects | `project`, `project_processor`, `project_approval`, `project_site`, `project_status_history` | [Open SVG](modules/projects.svg) |
| Notices | `notice`, `notice_language`, `notice_purpose` | [Open SVG](modules/notices.svg) |
| Consent | `consent_link`, `consent_artefact`, `consent_purpose_grant`, `v_current_consent` | [Open SVG](modules/consent.svg) |
| Exchange | `export_log`, `export_line`, `import_batch`, `collection`, `data_asset`, `asset_consent` | [Open SVG](modules/exchange.svg) |
| Rights | `rights_request`, `rights_request_holder`, `rights_request_item`, `rights_ticket_message`, `rights_response_file`, `rights_item_execution`, `legal_hold`, `nomination` | [Open SVG](modules/rights.svg) |
| Breach | `breach`, `breach_status_history`, `breach_determination`, `breach_assessment`, `breach_obligation`, `breach_obligation_event`, `breach_affected_revision`, `breach_affected` | [Open SVG](modules/breach.svg) |
| Platform | `audit_log`, `message_template`, `restricted_country` | [Open SVG](modules/platform.svg) |

Module diagrams include full local tables and their outgoing foreign keys. Referenced tables outside the module appear as key-only context; incoming relationships from other modules are shown in the complete diagram.

## Verified inventory

| Object | Count |
| --- | --- |
| Application Tables | 43 |
| Metadata Tables | 1 |
| Views | 1 |
| Table Columns | 542 |
| Foreign Keys | 122 |
| Enums | 39 |
| Triggers | 38 |
| Checks | 65 |

The Alembic `alembic_version` table is included separately as migration metadata. Its one column and the view's derived columns are additional to the 542 application-table columns; the inventory above comes from PostgreSQL's catalogues after replaying the full migration chain.

Since **0027–0030** the personal columns are `text` rather than `varchar(n)` - ciphertext is longer than the plaintext it replaces - and each column the platform looks rows up by carries a `*_hash` column beside it holding `HMAC-SHA256(normalised value, BLIND_INDEX_KEY)`. Three name columns additionally carry `*_ngrams text[]` with a GIN index: the hashed three-character runs that let staff search by part of a name without the name being readable. `auth_user.minor_until` is the one date kept in the clear, for the section 9 test. What each column holds and why is in [docs/dkms/](../../dkms/README.md).

**0031** (S2-03) adds the record of carrying an erasure out: `rights_item_execution`, one append-only row per attempt at each store that holds an item, and `rights_request_item.executed_at`; and `legal_hold`, which stops erasure of an asset or a person until it is released - placed once and released once, by trigger, with a sealed reason.

**0032** (S2-04) adds where data goes: `processor.location_country` (ISO 3166-1 alpha-2), `restricted_country` - the Government's s.16 list, kept as data, listed once and lifted once by trigger, one active listing per country - and on each `export_line` the destination processor and its country, with the export's `transfer_basis`.

**0033** adds one rule, not a table: `uq_notice_one_published_per_project`, a partial unique index allowing one published notice per project.

**0034** (S3-01) adds the breach register: `breach`, whose status alone may change (`cmp_breach_status_only`); and, append-only, its status history, its determinations (whether it is a personal data breach under s.2(u), with the moment of awareness), its assessment revisions, one `breach_obligation` per statutory duty with its due time stored once, and `breach_obligation_event` for everything that happens to a duty afterwards. Every narrative column is sealed.

**0035** (S3-02) adds who a breach touched: `breach_affected_revision`, one per confirmation with its scopes and counts, and `breach_affected`, each person once per breach with the revision that first listed them. Both append-only.

## Reading relationships and keys

- Arrow direction is **referencing child column → referenced parent key**. A solid line means all FK columns are NOT NULL; a dashed line means at least one is nullable. A dotted green line is a view dependency, not an FK.
- `PK` = primary key; `FK` = foreign key; `UQ` = member of a declared unique constraint, which can be composite; `?` = nullable column. Not every UQ-marked column is unique on its own. Unique expression/partial indexes are listed in the column reference and SQL.
- Repeated arrows between tables represent distinct foreign-key constraints, for example created-by versus approved-by. The full SVG includes all 122 constraints, including circular and self-referencing ones.
- Types are displayed compactly (`int4`, `int8`, `varchar`, `timestamptz`, `bool`); the exact PostgreSQL types are in the column reference. View nullability is derived and is not asserted by the diagram.
- Arrow styles express foreign-key nullability, not universal one-to-many cardinality. Composite uniqueness, partial indexes and trigger rules must also be considered; these are retained in the supporting SQL/reference.

## Sources and reproduction

- [Catalog inventory JSON](schema_inventory.json) includes tables, columns, constraints, indexes, enum values, views, dependencies, triggers, sequences and application functions.
- [Schema-only SQL](schema.sql) is PostgreSQL’s schema dump after replaying the migrations, including functions and triggers. It contains no application data or passwords. Owner and privilege statements are omitted; use the original migration grant rules for deployment permissions.
- The [Graphviz sources](source/complete_schema.dot) are written by the generator, not by hand. Render with `dot -Tsvg source/complete_schema.dot -o complete_schema.svg`, or with `@viz-js/viz` where Graphviz is not installed; `generate-schema-docs.py` renders them itself when `dot` is on the path. The 0031 and 0032 diagrams were rendered with `@viz-js/viz`, which embeds the same Graphviz.

The schema was reconstructed in an isolated, disposable PostgreSQL 16 database from all 32 repository `upgrade()` functions. No existing application database was migrated or queried for user data. This is the repository’s migration-head schema, not a claim that every deployment has applied that revision. Empty-data replay validates DDL shape; it does not exercise migrations’ data-dependent backfill/guard branches on production data.

Redis stores sessions, OTP/MFA codes, rate counters, caches and Celery queues/results; those are not relational PostgreSQL tables. Uploaded documents/media are stored outside PostgreSQL, with references/hashes held in the tables. Generic audit entity IDs, array membership and JSON references are not invented as foreign-key constraints in this diagram.
