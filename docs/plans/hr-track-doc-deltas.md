# HR track: the edits to existing documents

The new documents in this pack are whole files. These are the lines to add
to documents that already exist, each in the increment that makes them
true. Keep the existing files' voice; do not rewrite around the additions.

## `docs/decisions/README.md` (increment 1, 3, 5)

Append to the table:

```
| [0032](0032-offices-are-logical-tenants-in-one-database.md) | Offices are logical tenants in one database, enforced by row-level security | proposed 2026-10-26 |
| [0033](0033-hr-consent-is-governed-by-an-approved-template-version.md) | HR consent is governed by a template version Legal approves once; an activity inherits it and needs no approval of its own | proposed 2026-10-27 |
| [0034](0034-an-employee-link-signs-in-through-the-organisations-sso.md) | An employee consent link signs in through the organisation's SSO, and the account is matched on the employee ID | proposed 2026-10-27 |
```

Change each to `accepted` in the pull request that lands its increment, and
add to ADR 0013, 0026 and 0028 an *Amended 2026-10-…* section pointing at
the new record (two sentences each, as 0013's amendments do).

## `docs/README.md` (increment 1 onward)

Under **Working on a feature**, after the behaviour-by-obligation line:

```
- The HR track: [hr-track.md](domain/hr-track.md) - a second consent track governed by a Legal office: categories, approved template versions, activities, SSO on employee links, and how requests and breaches are routed by office; the wall between the offices is [offices-and-tenancy.md](architecture/offices-and-tenancy.md); the schema is [hr-track-migration-plan.md](database/hr-track-migration-plan.md); the plan, [hr-track-implementation-plan.md](plans/hr-track-implementation-plan.md)
```

Under **The API's internals**, a row:

```
| [architecture/offices-and-tenancy.md](architecture/offices-and-tenancy.md) | How two offices share one database and never see each other's rows |
```

Under **Reference** nothing changes: the generated references pick the new
tables and routes up when regenerated.

## `docs/glossary.md`

Under **People and roles**, after *Administrator*:

```
**Legal PoC.** The officer of the Legal office: governs the HR track as the
DPO governs the R&D track - categories, HR purposes, template versions, and
the HR track's rights requests and breaches. Role `legal`.

**HR PoC.** An HR point of contact who creates consent activities in the
categories the administrator assigned them, shares each activity's link,
and answers the tickets addressed to them. Role `hr_user`.
```

Under **Projects and collection**, after *Project*:

```
**Office.** The governance tenant: the DPO office (`rnd`) or the Legal office
(`hr`). Every project, purpose, template, notice, link, export, request and
breach names its office, and an officer sees only its own, enforced by
row-level security ([ADR 0032](decisions/0032-offices-are-logical-tenants-in-one-database.md)).

**Activity.** A project of the HR office: an instance of a category, made
from an approved template version by an HR PoC, approved as it is created,
with one open consent link ([ADR 0033](decisions/0033-hr-consent-is-governed-by-an-approved-template-version.md)).

**Category.** Legal's registry of kinds of HR activity (wellness, CSR,
background verification, …), each with its templates and the processors
that hold data collected under it.
```

Under **Notices and consent**, after *Notice template*:

```
**Template version.** On the HR track, the unit Legal approves: the locked
legal text per language with a purposes slot and a description slot, the
purpose list with its mandatory flags, and a re-consent flag. Frozen and
hashed on approval; an activity inherits the version it was created on.

**Description slot.** The one free text in an HR notice, written by the HR
PoC inside the limits the version sets, rendered inside the served text and
so inside the hash the consent artefact records.

**Audience mode.** Whether a consent link signs a person in through the
organisation's SSO (`sso`, employees) or by a one-time code (`otp`,
everyone else) ([ADR 0034](decisions/0034-an-employee-link-signs-in-through-the-organisations-sso.md)).
```

Under **Rights**, after *Holder*:

```
**Shared intake.** A rights request whose office is not yet known - the
public form before verification - visible to both offices until one
verifies and claims it. **Transfer**: an office hands a request to the
other with a reason; the clock does not move.
```

## `docs/database/migrations.md` (each increment)

Append to the chain table:

```
| `0051` | Offices and the wall (ADR 0032): `office` with its two rows; `office_id` on `project`, `purpose`, `notice_template`, `notice`, `consent_link`, `export_log`, `breach` (NOT NULL, backfilled `rnd`), on `rights_request` (nullable: the shared intake) and on `auth_user` (officers); `user_role` gains `legal` and `hr_user` in autocommit blocks, never removed; `ENABLE` + `FORCE ROW LEVEL SECURITY` and one `office_isolation` policy on every office-bearing table and on each child through its parent; `v_current_consent` recreated `WITH (security_invoker = true)`. Refuses below PostgreSQL 16. Raw SQL |
| `0052` | The Legal office's registry (ADR 0033): `hr_category` (active/retired by CHECK), `category_processor` (role hrms/database/vendor, default respondent, removed by date), `hr_poc_category`; `notice_template.category_id`, required on the `hr` office by trigger. Policies on the three. Raw SQL; nothing to backfill |
| `0053` | Template versions (ADR 0033): `template_version` (draft/approved/retired; approver and time by CHECK; `reconsent_required`; the description slot's guidance and limit), `template_version_language` (locked text, hash set at approval), `template_version_purpose`; frozen once approved by `cmp_template_version_freeze()`; `project.category_id`, `template_version_id`, `activity_description` and `notice.template_version_id`; `cmp_activity_version_coherent()` and `trg_hr_notice_purposes_in_version`. Raw SQL; nothing to backfill |
| `0054` | Link audience and person types (ADR 0034): `consent_link.audience_mode` (`sso`/`otp`, default `otp`); `person_type` gains `candidate` and `visitor` in autocommit blocks; `hr_category.default_person_type`; `auth_user.sso_subject` (sealed) with its unique hash. Raw SQL; nothing to backfill |
| `0055` | Rights and breaches by office: `rights_request` transfer columns (from, by, at, sealed reason, all or none by CHECK) and claim columns; `rights_holder_source` gains `activity_processor` in an autocommit block; `trg_rights_request_office_moves` allows `office_id` to change only by a claim from NULL or a transfer with its four columns. Raw SQL; nothing to backfill |
```

(`0056` is reserved and unused unless increment 5 needs a table; say so in
a one-line row if it stays unused, so the gap is explained.)

## `docs/domain/roles-and-access.md` (increments 1, 2, 4, 7)

In **The roles** table, after *Administrator*:

```
| Legal PoC | `legal` | The Legal office | Governs the HR track: categories, HR purposes, templates and their versions, the category's processors; sees every HR register and the HR audit trail; runs the HR track's rights queue, breaches and legal holds |
| HR PoC | `hr_user` | An HR point of contact | Creates activities in the categories assigned to them from an approved template version, chooses purposes, writes the description, mints and shares the open link, watches the activity's register by name, exports the consented list, answers tickets addressed to them |
```

Change the first sentence to "Ten roles. Eight are staff…". In **The
matrix**, two columns, from `core/permissions.py` once increment 4 lands
(copy the grants, do not paraphrase). After the matrix, a paragraph:

```
An officer's `ALL` is the office's all. The DPO and the Legal PoC hold the
same grants on the same resources; which rows those grants reach is decided
by the office on the account (`auth_user.office_id`), applied as the
`app.office` setting on every connection and enforced by row-level security
([offices-and-tenancy.md](../architecture/offices-and-tenancy.md)). An HR
PoC's scope within the HR office is the categories assigned to them
(`hr_poc_category`), compiled into the query as a collection owner's sites
are.
```

In **Navigation**, two rows, and in **What the dashboard asks of each
role**, two rows (from increment 8).

## `docs/architecture/domain-model.md` (increments 1–5)

The table groups: a row **Offices** (`office`), rows under **Projects** and
**Notices** for the new tables, the new enum values in the enumerations
table, and in **Rules the database holds**:

```
| An officer's connection reads and writes only its office's rows | row-level security, `office_isolation` on every office-bearing table (0051) |
| An approved template version never changes | `cmp_template_version_freeze()` |
| An HR activity names an approved version of a template in its category; an R&D project names none | `cmp_activity_version_coherent()` |
| A purpose on an HR notice is on its version's list | `trg_hr_notice_purposes_in_version` |
| A request changes office only by a claim or a transfer | `trg_rights_request_office_moves` |
```

Regenerate the mermaid ER section from the new schema rather than editing
it by hand; `generate-schema-docs.py` draws `complete_schema.svg`.

## `docs/architecture/request-lifecycle.md` (increment 1)

In the dependencies block, after `matrix + row scope`:

```
  │   office ← session        bind_actor(..., office): the office the
  │                            session acts in, or none
```

and in the Repository block:

```
  │   the pool sets app.office from the context on checkout and
  │   resets it on return; PostgreSQL's policies answer the rest
```

## `docs/security/authorization.md` (increment 1)

A section **Two offices** of one paragraph pointing at
`offices-and-tenancy.md`: scope in the query remains the mechanism, the
policies are the backstop, and a forgotten predicate returns nothing rather
than the other office's rows.

## `docs/security/authentication.md` (increment 5)

A section **Employees on a consent link**: the OIDC flow in five lines, the
matching rule, that the session is a data principal's (ADR 0013), and the
neutral failure page.

## `docs/operations/configuration.md` (increments 1 and 5)

In **Groups**:

```
| Offices | nothing to configure: the two offices are rows in `office`; the setting `app.office` is the pool's, never an environment variable |
| SSO | `SSO_ENABLED` false; `SSO_ISSUER`, `SSO_CLIENT_ID`, `SSO_CLIENT_SECRET`, `SSO_REDIRECT_URL` (`${PUBLIC_BASE_URL}/auth/sso/callback`), `SSO_SCOPES` `openid profile email`, `SSO_CLAIM_EMPLOYEE_ID` `employee_id`, `SSO_CLAIM_EMAIL` `email`, `SSO_CLAIM_NAME` `name`, `SSO_STATE_TTL_S` 600 ([ADR 0034](../decisions/0034-an-employee-link-signs-in-through-the-organisations-sso.md)) |
```

In **Production refuses to start on**:

```
| `SSO_ENABLED` is true with an empty `SSO_CLIENT_SECRET`, an `SSO_ISSUER` that is not HTTPS, or an `SSO_REDIRECT_URL` not under `PUBLIC_BASE_URL` | A consent link that hands the browser to an unverified issuer, or accepts a callback on another host, is a sign-in nobody can vouch for |
```

And the same keys in `backend/api/.env.example` with the development
values commented.

## `docs/domain/consent-lifecycle.md` (increments 4, 5)

In **1. The notice**, after the templates paragraph, two sentences: on the
HR track a notice is composed from an approved template version and
published as the activity is created; the rest of the lifecycle is
identical. In **3. Who is signing**, a paragraph on the `sso` audience mode
pointing at ADR 0034. In **6. Withdrawal**, one sentence: on the HR track
the activity's respondents are told.

## `docs/domain/rights-requests.md` (increment 7)

After **Where a request comes from**, a section **Which office answers**
that is the routing table from `hr-track.md` §5, and *transfer* and *claim*
in the actions list. In **Holders and tickets**, `activity_processor` as a
third source.

## `docs/domain/breaches.md` (increment 7)

One paragraph at the top: a breach belongs to an office; `legal` holds the
HR office's register with the DPO's powers; the administrator's view spans
both.

## `CHANGELOG.md` (each increment, under Unreleased → Added)

```
- **Offices as tenants** (ADR 0032): every governance record names its office (`rnd`, `hr`); an officer's connection is set to its office and PostgreSQL's row-level security refuses every other office's rows; two roles, Legal PoC and HR PoC. Migration 0051.
- **The HR track** (ADR 0033): Legal's categories, HR purposes and template versions approved once and frozen; an HR PoC creates an activity from an approved version - chosen purposes, one description, one open link - with no approval step; Legal's and the HR PoC's registers and dashboards. Migrations 0052, 0053.
- **SSO on employee links** (ADR 0034): a consent link's audience mode; an `sso` link signs the employee in through the organisation's identity provider and matches or creates the account on the employee ID; mobile and date of birth asked once; candidates and visitors as person types. Migration 0054.
- **Withdrawal reaches the HR holders**: the activity's respondents are told; holders for a rights request derived from the category's processors.
- **Rights requests and breaches by office**: routed on receipt by the person's standing, a shared intake for the unknown, claim and transfer with a reason and an unchanged clock; the Legal office's breach register. Migration 0055.
```

## `docs/reviews/README.md` (increment 8)

Under **Open decisions**, remove nothing; add a row for phase 2 (machine
credentials for HRMS events and a consent-check API, owner: product owner,
written in ADR 0034's consequences and `hr-track.md` §4).
