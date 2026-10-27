# HR track: the migration plan

Six revisions, `0051` to `0056`, in this order; each is raw SQL in house
style ([04-database.md](../backend/04-database.md#what-a-migration-looks-like)),
both directions, with a guard that refuses rather than a backfill that
guesses. Every new personal column is `text`, sealed, and listed in
`ENCRYPTED_FIELDS`. Every new enum value has its `StrEnum` and
`BY_PG_TYPE` entry. When all six are applied, regenerate
`docs/reference/database/` from a scratch database and add each revision's
line to [migrations.md](migrations.md) (the lines are in
[hr-track-doc-deltas.md](../plans/hr-track-doc-deltas.md)).

The dual-identifier pattern holds everywhere: `<entity>_id serial PRIMARY
KEY`, `<entity>_uuid uuid NOT NULL UNIQUE DEFAULT gen_random_uuid()`.

## 0051 · Offices and the wall (ADR 0032)

**Creates**

```sql
CREATE TABLE office (
  office_id        serial PRIMARY KEY,
  office_uuid      uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  office_code      varchar(12) NOT NULL UNIQUE,
  name             varchar(120) NOT NULL,
  contact          text,                       -- sealed, CONTACT
  grievance_route  text,
  created_at       timestamptz NOT NULL DEFAULT now()
);
INSERT INTO office (office_code, name) VALUES ('rnd', 'DPO office'), ('hr', 'Legal office');
```

**Adds `office_id`** (`int REFERENCES office(office_id)`) to `project`,
`purpose`, `notice_template`, `notice`, `consent_link`, `export_log`,
`breach` as `NOT NULL` after a backfill `UPDATE … SET office_id = (SELECT
office_id FROM office WHERE office_code = 'rnd')`; to `rights_request` as
nullable with the same backfill; to `auth_user` as nullable, backfilled to
`rnd` for every row whose role is in (`dpo`, `rnd_user`, `dco`, `rco`,
`dco_admin`). Index each.

**Enum.** `ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'legal';` and
`'hr_user'`, each in its own `autocommit_block()` before the rest, as 0041
did; the values are never removed on downgrade.

**Policies.** `ENABLE` + `FORCE ROW LEVEL SECURITY` and
`CREATE POLICY office_isolation` on the nine office-bearing tables and on
every child listed in
[offices-and-tenancy.md](../architecture/offices-and-tenancy.md#the-office),
with the `EXISTS` form for children. `rights_request`'s policy allows
`office_id IS NULL`. Write the policy SQL once in a PL/pgSQL `DO` block that
loops over a list of `(table, parent, fk)` triples, so the migration reads
as the list rather than as forty copies.

**The view.** `DROP VIEW v_current_consent; CREATE VIEW v_current_consent
WITH (security_invoker = true) AS …` (the same body as 0027).

**Refuses** if `current_setting('server_version_num')::int < 160000`:
`security_invoker` on a view needs PostgreSQL 15, `FORCE` with the policies
as written was tested on 16, and the platform states 16.

**Downgrade** drops the policies, disables RLS, recreates the view without
`security_invoker`, drops the columns and the table. The enum values stay.

**Python with it:** `Role.LEGAL = "legal"`, `Role.HR_USER = "hr_user"`,
`ROLE_TITLES`; `RequestContext.office`, `bind_actor(…, office)`;
`Session.office`; `pool.connection()`/`transaction()` set the setting,
`open_pool(reset=_reset)`; migrations' `env.py`, `scripts/seed.py`,
`scripts/reseal.py` and `docs/tools/*` that open a connection set `'all'`.

## 0052 · The Legal office's registry (ADR 0033)

```sql
CREATE TABLE hr_category (
  category_id    serial PRIMARY KEY,
  category_uuid  uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  office_id      int NOT NULL REFERENCES office(office_id),
  category_code  varchar(24) NOT NULL UNIQUE,
  name           varchar(120) NOT NULL,
  description    text,
  status         varchar(12) NOT NULL DEFAULT 'active',
  created_by     int NOT NULL REFERENCES auth_user(id),
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now(),
  retired_at     timestamptz,
  CONSTRAINT hr_category_status CHECK (status IN ('active', 'retired')),
  CONSTRAINT hr_category_retired_at CHECK ((status = 'retired') = (retired_at IS NOT NULL))
);

CREATE TABLE category_processor (
  category_processor_id serial PRIMARY KEY,
  category_id      int NOT NULL REFERENCES hr_category(category_id),
  processor_id     int NOT NULL REFERENCES processor(processor_id),
  processor_role   varchar(12) NOT NULL,            -- hrms | database | vendor
  respondent_user_id int REFERENCES auth_user(id),  -- default respondent; NULL = the activity's HR PoC
  added_by         int NOT NULL REFERENCES auth_user(id),
  added_at         timestamptz NOT NULL DEFAULT now(),
  removed_at       timestamptz,
  CONSTRAINT category_processor_role CHECK (processor_role IN ('hrms', 'database', 'vendor'))
);
CREATE UNIQUE INDEX category_processor_live ON category_processor (category_id, processor_id) WHERE removed_at IS NULL;

CREATE TABLE hr_poc_category (
  assignment_id  serial PRIMARY KEY,
  user_id        int NOT NULL REFERENCES auth_user(id),
  category_id    int NOT NULL REFERENCES hr_category(category_id),
  assigned_by    int NOT NULL REFERENCES auth_user(id),
  assigned_at    timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT hr_poc_category_once UNIQUE (user_id, category_id)
);

ALTER TABLE notice_template ADD COLUMN category_id int REFERENCES hr_category(category_id);
CREATE INDEX idx_notice_template_category ON notice_template (category_id) WHERE category_id IS NOT NULL;
```

Trigger `trg_hr_template_has_category`: a `notice_template` whose
`office_id` is `hr` must name a category; one whose office is `rnd` must
not. Policies on the three new tables (`hr_category` by `office_id`; the
other two through `hr_category`). `cmp_touch_updated_at()` on
`hr_category`.

`processor_role` and `status` are `varchar` with CHECKs rather than enum
types, as `notice_template.status` is in 0044.

## 0053 · Template versions (ADR 0033)

```sql
CREATE TABLE template_version (
  version_id          serial PRIMARY KEY,
  version_uuid        uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  template_id         int NOT NULL REFERENCES notice_template(template_id),
  version             int NOT NULL,
  status              varchar(12) NOT NULL DEFAULT 'draft',       -- draft | approved | retired
  reconsent_required  boolean NOT NULL DEFAULT false,
  slot_guidance       text,
  slot_max_length     int NOT NULL DEFAULT 1200 CHECK (slot_max_length BETWEEN 100 AND 4000),
  created_by          int NOT NULL REFERENCES auth_user(id),
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  approved_by         int REFERENCES auth_user(id),
  approved_at         timestamptz,
  retired_by          int REFERENCES auth_user(id),
  retired_at          timestamptz,
  CONSTRAINT template_version_once UNIQUE (template_id, version),
  CONSTRAINT template_version_status CHECK (status IN ('draft', 'approved', 'retired')),
  CONSTRAINT template_version_approved CHECK ((status = 'draft') = (approved_at IS NULL)),
  CONSTRAINT template_version_approver CHECK ((approved_at IS NULL) = (approved_by IS NULL)),
  CONSTRAINT template_version_retired CHECK ((status = 'retired') = (retired_at IS NOT NULL))
);

CREATE TABLE template_version_language (
  version_language_id serial PRIMARY KEY,
  version_id      int NOT NULL REFERENCES template_version(version_id),
  language_code   language_code NOT NULL,
  locked_text     text NOT NULL,
  content_hash    text,                      -- set at approval
  updated_by      int NOT NULL REFERENCES auth_user(id),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT template_version_language_once UNIQUE (version_id, language_code)
);

CREATE TABLE template_version_purpose (
  version_purpose_id serial PRIMARY KEY,
  version_id      int NOT NULL REFERENCES template_version(version_id),
  purpose_id      int NOT NULL REFERENCES purpose(purpose_id),
  is_mandatory    boolean NOT NULL DEFAULT false,
  display_order   int NOT NULL DEFAULT 0,
  CONSTRAINT template_version_purpose_once UNIQUE (version_id, purpose_id)
);

ALTER TABLE project ADD COLUMN category_id int REFERENCES hr_category(category_id),
                    ADD COLUMN template_version_id int REFERENCES template_version(version_id),
                    ADD COLUMN activity_description text;
ALTER TABLE project ADD CONSTRAINT project_description_length
  CHECK (activity_description IS NULL OR char_length(activity_description) <= 4000);
ALTER TABLE notice ADD COLUMN template_version_id int REFERENCES template_version(version_id);
```

**Triggers**

- `cmp_template_version_freeze()` (BEFORE UPDATE on `template_version`,
  `template_version_language`, `template_version_purpose`; BEFORE
  INSERT/DELETE on the two children): once the version's `status` is not
  `draft`, nothing changes except `status` (`approved → retired`),
  `retired_by/at` and `updated_at`. Modelled on `cmp_notice_freeze()`.
- `cmp_activity_version_coherent()` (BEFORE INSERT/UPDATE on `project`):
  on the `hr` office, `category_id` and `template_version_id` are NOT NULL,
  the version is `approved`, and its template belongs to that category; on
  `rnd`, all three new columns are NULL.
- `trg_hr_notice_purposes_in_version` (BEFORE INSERT on `notice_purpose`):
  if the notice names a `template_version_id`, the purpose must be on that
  version's list.

Policies: `template_version` through `notice_template`; the two children
through `template_version`.

The `{{purposes}}` and `{{description}}` placeholders are required by the
service at approval, not by the database: a text rule belongs where the
text is composed.

## 0054 · Link audience and person types (ADR 0034)

```sql
ALTER TABLE consent_link ADD COLUMN audience_mode varchar(4) NOT NULL DEFAULT 'otp'
  CHECK (audience_mode IN ('sso', 'otp'));
ALTER TYPE person_type ADD VALUE IF NOT EXISTS 'candidate';   -- autocommit block
ALTER TYPE person_type ADD VALUE IF NOT EXISTS 'visitor';     -- autocommit block
ALTER TABLE hr_category ADD COLUMN default_person_type person_type;
ALTER TABLE auth_user ADD COLUMN sso_subject text;            -- sealed, FREE_TEXT: the provider's `sub`, for the audit of a conflict
ALTER TABLE auth_user ADD COLUMN sso_subject_hash text;
ALTER TABLE auth_user ADD CONSTRAINT auth_user_sso_subject_indexed CHECK (sso_subject IS NULL OR sso_subject_hash IS NOT NULL);
CREATE UNIQUE INDEX auth_user_sso_subject_hash_key ON auth_user (sso_subject_hash) WHERE sso_subject_hash IS NOT NULL;
```

`PersonType` gains `CANDIDATE` and `VISITOR`. `sso_subject` and its hash go
through [adding-a-personal-field.md](../dkms/adding-a-personal-field.md).
The downgrade drops the columns; the enum values stay.

## 0055 · Rights and breaches by office

```sql
ALTER TABLE rights_request
  ADD COLUMN transferred_from_office_id int REFERENCES office(office_id),
  ADD COLUMN transfer_reason text,                 -- sealed, FREE_TEXT
  ADD COLUMN transferred_at timestamptz,
  ADD COLUMN transferred_by int REFERENCES auth_user(id),
  ADD COLUMN claimed_at timestamptz,
  ADD COLUMN claimed_by int REFERENCES auth_user(id);
ALTER TABLE rights_request ADD CONSTRAINT rights_request_transfer_whole
  CHECK ((transferred_from_office_id IS NULL) = (transferred_at IS NULL)
     AND (transferred_at IS NULL) = (transferred_by IS NULL)
     AND (transferred_at IS NULL) = (transfer_reason IS NULL));
ALTER TABLE rights_request ADD CONSTRAINT rights_request_claimed
  CHECK ((claimed_at IS NULL) = (claimed_by IS NULL));
ALTER TYPE rights_holder_source ADD VALUE IF NOT EXISTS 'activity_processor';   -- autocommit block, first
```

`rights_request_holder.derived_from` is the enum type `rights_holder_source`
(`export_line`, `asset_consent`, `manual`), so the new value is added in its
own `autocommit_block()` before the rest, as 0041 did for `user_role`, and
`RightsHolderSource` in `core/enums.py` gains `ACTIVITY_PROCESSOR`. Trigger `trg_rights_request_office_moves`:
`office_id` may change only from NULL (a claim) or together with the four
`transferred_*` columns in one statement (a transfer); any other change to
`office_id` is refused.

## 0056 · The notification junction and settings

No DDL beyond what `message_template` and `message_copy` already allow: the
new junction `hr_withdrawal_notice` and `hr_reconsent_request` are rows in
the code's catalogue (`core/messages.py`), not in the schema. This revision
exists only if a table is needed for the SSO state; it is not - the state
lives in Redis (`sso:*`). **Skip 0056 unless increment 5 finds a need; keep
the number free rather than renumbering.**

## The seed

`scripts/seed.py` gains, behind the same `local`/`test` guard: the two
office rows (0051 inserts them; the seed asserts they exist), one `legal`
account (`legal@cmp.local`) and one `hr_user` (`hr@cmp.local`) invited the
way the DPO is, the in-house processor `HR` with two sources (`HRMS`, `HR
database`), the category `WELLNESS` with those processors, two HR purposes,
one template with an approved version 1 (locked English text with both
placeholders, two purposes, one mandatory), and no activity: creating one is
UAT case HR-02's job.

## Order of operations on a shared server

Stop the API and the worker before 0051: `ADD COLUMN … NOT NULL` with a
backfill holds an exclusive lock on each of the nine tables until the
migration commits. 0051 against a seeded development database with sealed
rows calls no key service: no sealed column is read.
