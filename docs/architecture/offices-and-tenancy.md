# Offices and tenancy

How two offices share one database without seeing each other's rows. The
decision is [ADR 0032](../decisions/0032-offices-are-logical-tenants-in-one-database.md);
this page is the mechanism, in the order a request meets it. The diagram is
[AR-09](../diagrams/hr-track/AR09-offices-as-logical-tenants-in-one-database.png).

## The office

`office` is a table: `office_id`, `office_uuid`, `office_code` (`rnd`,
`hr`), `name`, `contact` (sealed), `grievance_route`, `created_at`.
Migration 0051 inserts the two rows. A third office is an `INSERT` and
assigned accounts, not a migration.

Every governance record names its office with `office_id int NOT NULL
REFERENCES office(office_id)`:

| Table | Set when | Backfill |
|---|---|---|
| `project` | created | `rnd` |
| `purpose` | created | `rnd` |
| `notice_template` | created | `rnd` |
| `hr_category`, `template_version` (through its template) | created | — (new) |
| `notice` | created, from its project | `rnd` |
| `consent_link` | minted, from its notice | `rnd` |
| `export_log` | written, from its project | `rnd` |
| `rights_request` | received (nullable: shared intake), claimed or transferred | `rnd` |
| `breach` | logged | `rnd` |

Children carry no column of their own and are policed through their parent:
`consent_artefact` and `consent_purpose_grant` through `consent_link`;
`export_line` through `export_log`; `notice_language`, `notice_purpose`
through `notice`; `notice_template_language`, `notice_template_purpose`
through `notice_template`; `project_site`, `project_processor`, `project_approval`,
`project_status_history`, `import_batch`, `collection` through `project`,
`data_asset` through `collection` and `asset_consent` through `data_asset`
(half its rows name no consent, so not through the link); `rights_request_holder`,
`rights_request_item`, `rights_item_execution`, `rights_ticket_message`,
`rights_response_file`, `rights_request_attachment` through
`rights_request`; every `breach_*` table through `breach`;
`template_version_language`, `template_version_purpose` through
`template_version`; `category_processor`, `hr_poc_category` through
`hr_category`.

Not policed: `auth_user` and `person_type_history` (one person, both
tracks), `audit_log` (one chain; the read is filtered), `processor`,
`processor_respondent`, `data_source`, `collection_owner_processor`,
`delegation`, `nomination`, `legal_hold`, `message_template`,
`message_copy`, `restricted_country`, `breach_temporary_access`. These
hold no office-specific consent evidence or are deliberately shared.
`legal_hold` carries no office scope in its queries yet (`list_holds()`
returns every hold); only the matrix, which gives it to the DPO alone,
keeps it within one office, and increment 7 scopes it before the Legal
PoC holds it (open point F-21).

## Who belongs where

`auth_user.office_id` (nullable) names the office an officer works in:

| Role | `office_id` | `app.office` for the session |
|---|---|---|
| `dpo` | `rnd` (backfilled) | `rnd` |
| `legal` | `hr` | `hr` |
| `rnd_user`, `dco`, `rco`, `dco_admin` | `rnd` (backfilled; the administrator sets it on provisioning) | `rnd` |
| `hr_user` | `hr` | `hr` |
| `admin` | NULL | `all` |
| `data_subject` (every code or SSO sign-in) | — | `all` |
| `breach_holder` | — | `all` |
| no session (public routes: `/c/{token}`, `/auth/*`, the public rights form, `/holder-tickets/*`) | — | `all` |
| worker, beat, migrations, seed, `reseal.py`, `docs/tools/*` | — | `all` |

Role scoping *inside* an office stays application scope: an HR PoC's
categories, a collection owner's sites, an R&D user's own projects. The
office is the wall between offices; the query is the wall within one.

`POST /users` requires `office_uuid` for `dpo`, `legal`, `rnd_user`, `dco`,
`rco`, `dco_admin`, `hr_user` and refuses it for the rest; a role change
keeps the account's office when the new role works in it, and otherwise
needs one named. Each of those roles is held to its track's office
(`OFFICE_OF_ROLE` in `core/permissions.py`, open point F-20): the Legal PoC
and the HR PoC to `hr`, the rest to `rnd`; another is refused (422). Any role
change clears an HR PoC's category assignments as it clears a collection
owner's processors.

## Where the office is set

Nothing in the routers changes. The office travels in the request context
and is applied by the pool:

1. `cmp.core.context.RequestContext` gains `office: str | None`.
   `bind_actor()` gains an `office` argument; `current_principal` and
   `partial_principal` pass the session's office. The session
   (`auth/sessions/service.py`) gains `office: str | None`, set at sign-in
   from `auth_user.office_id` for a staff session and left `None` for a
   principal session.
2. `cmp.db.pool.connection()` and `transaction()` run, as the first
   statement on the checked-out connection,
   `SELECT set_config('app.office', %s, false)` with the context's office
   code, or `'all'` when the context has none. Session-level, because
   `connection()` is autocommit and a transaction-local setting would end
   with the statement that set it.
3. Both context managers run `RESET app.office` on the way back
   (`_forget_office`), whether the body finished or raised, so the setting
   can never survive to the next request that draws that connection. On the
   request's own task, not as the pool's `reset` callback: `psycopg_pool`
   runs that callback on a worker task of the event loop that opened the
   pool, which the test suite's per-test event loops never run, and a
   connection whose reset never runs never returns. A connection that
   bypasses the pool (psql, a one-off script) has no setting and reads
   nothing from a policed table until it sets `'all'`.
4. The worker's tasks use the same `transaction()` with an empty context, so
   they run as `'all'`. Migrations, the seed and `reseal.py` run as the
   table owner and begin with `SELECT set_config('app.office', 'all',
   false)`: `FORCE ROW LEVEL SECURITY` binds the owner too.
5. No policy binds a superuser or a role with `BYPASSRLS`. Locally the API,
   the tests and the tools connect as the database container's superuser
   (`cmp` in `dev-services.yml`), so the wall is set but not enforced there;
   the enforcement tests prove it under a non-superuser role (below).
   Outside `local` and `test`, the API refuses to start when its database
   user is a superuser or holds `BYPASSRLS`
   (`cmp.db.pool.assert_policies_bind`).

## The policies

For a table with its own column:

```sql
ALTER TABLE project ENABLE ROW LEVEL SECURITY;
ALTER TABLE project FORCE ROW LEVEL SECURITY;
CREATE POLICY office_isolation ON project
  USING (
    current_setting('app.office', true) = 'all'
    OR office_id = (SELECT office_id FROM office WHERE office_code = current_setting('app.office', true))
  )
  WITH CHECK (
    current_setting('app.office', true) = 'all'
    OR office_id = (SELECT office_id FROM office WHERE office_code = current_setting('app.office', true))
  );
```

`office` itself is not policed, so the subquery always resolves; the planner
evaluates it once per statement. An unset or empty setting matches neither
branch: deny by default.

For a child, the same two clauses with `EXISTS (SELECT 1 FROM consent_link l
WHERE l.link_id = consent_artefact.link_id)`: the parent's own policy
filters the subquery, so a child is visible exactly when its parent is.

`rights_request` allows one more case: `office_id IS NULL` (the shared
intake) is visible to both offices' sessions.

`v_current_consent` is dropped and recreated `WITH (security_invoker =
true)` in the same migration; without it the view runs with its owner's
rights and reads through the wall.

The audit trail: `audit_log` is written by `cmp.domain.audit.service.record`
on the caller's connection. Its rows are not policed; `detail_json` gains
`office` - the office of the record the event is about, not the office of
whoever acted - for every event about an office-bearing record, so a consent
captured on an HR link by a data principal, or a worker's sweep of an HR
breach, is on Legal's trail. The trail's list query for an officer adds
`(detail_json->>'office' = %s OR detail_json->>'office' IS NULL)`: a row
about no office-bearing record (history from before 0051, sign-ins, user
administration) is read by both officers, since the Legal PoC holds the
DPO's standing on its track. The administrator reads all.

## In the query as well

The policies do not bind a superuser, and locally everything connects as
one (above). From 0052 the queries that read an office's registry carry the
same test themselves, as `cmp_office_visible(office_id)`: a SQL function,
`STABLE` and a single expression the planner inlines, true when
`app.office` is `all` or names the row's office. Scope in the query stays
the mechanism and the policies the backstop (ADR 0032), and the local
console shows what production will:

| Read | Where |
|---|---|
| Purposes: one, the list, versions, comparison | `db/repositories/registry.py` (`_PURPOSE_IN_OFFICE`) |
| Notice templates: by uuid, by code, the list | `db/repositories/notice_templates.py` (`_IN_OFFICE`) |
| Categories, and an HR PoC's own | `db/repositories/hr_categories.py` (`scope_predicate`, `categories_of_user`) |
| The notification feed, a holder's tickets for the office, a resend | `office_clause()` on the trail (`dashboard.staff_feed`, `audit.ticket_events_for_office`, `audit.breach_ticket_events_for_office`, `audit.by_uuid`) |
| Projects and activities, and everything read through them: sites, notices, links, consents, exports, collections, the dashboards | `projects.scope_predicate` and `site_scope_predicate` wrap every role's scope in `cmp_office_visible(p.office_id)`; `notices._project_scope`, `consent._project_scope` and `exchange._scope` do the same for an ALL or OWN scope (increment 4) |
| An activity's template version, by uuid | `template_versions.by_uuid` |

Rights requests and breaches still rely on the policies alone; they hold no
Legal office rows until increment 7, which adds the predicate.

An HR PoC's scope inside the Legal office is the categories assigned to
them (`hr_poc_category`), in every one of those reads (open point F-4): an
activity, its site, its notice, its link, its consents and its exports are
theirs exactly when its category is.

A write lands in the caller's office: the router passes `principal.office`
to the service (a purpose, a template, a category), and a principal with
no office is refused. A Legal office template names a category of its own
office and a DPO office template none (`cmp_template_category_fits()`);
a template is never copied onto a project unless it is the DPO office's.

## What it costs

One `set_config` per checkout and one `RESET` per return - two round trips
that the pool already pays for `_SESSION_SETUP`-style settings. Policies
compare an indexed integer against a one-row subquery. The enforcement
tests measure nothing; `tests/integration/test_office_isolation_plans.py`
asserts with `EXPLAIN` that the register queries still use their indexes
under a policy.

## Tests

`tests/integration/enforcement/test_office_isolation.py`, raw SQL on a
second connection, as the other enforcement tests do, after `SET LOCAL ROLE`
to a non-superuser role created for the test inside the same rolled-back
transaction (the suite's own user is a superuser, which no policy binds):

- a connection set to `hr` reads zero `rnd` rows on every policed table and
  cannot `INSERT` or `UPDATE` one (`WITH CHECK` refuses), and the reverse;
- an unset connection and an empty-string connection read nothing;
- `v_current_consent` honours the setting;
- `rights_request` with `office_id IS NULL` is visible to both;
- a connection set to `all` reads everything.

`tests/integration/database/test_office_policy_parity.py`: the set of
tables with a `policy office_isolation` in `pg_policies` equals the set of
office-bearing tables and their listed children, so a table added later
cannot arrive without a policy.

`tests/security/test_office_scope.py`: through the API, a `legal` session
answers 404 on every `rnd` project, notice, link, consent, export, request
and breach uuid, and a `dpo` session the reverse; `/audit` for each shows
only its office; the administrator sees both.
