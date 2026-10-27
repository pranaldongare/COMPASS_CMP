# 0032. Offices are logical tenants in one database, enforced by row-level security

**Status:** proposed · 2026-10-26. For the HR track. Builds on
[ADR 0002](0002-evidence-enforced-in-the-database.md),
[ADR 0004](0004-scope-in-the-where-clause.md) and
[ADR 0013](0013-every-account-is-a-data-principal.md); amends
[ADR 0026](0026-a-rights-request-is-access-erasure-or-a-grievance-about-everything.md)
and [ADR 0028](0028-a-notice-template-is-copied-never-served.md).

## Context

The platform is gaining a second track. R&D data-collection projects are
governed by the DPO office; HR consent activities (wellness, CSR, background
verification, communications, engagement) are governed by a Legal office that
approves templates once and is not in any per-activity loop, and that runs the
rights requests and breaches of its own track. The DPO must not see the HR
registers - who took part in a wellness programme is itself sensitive - and
Legal must not see R&D.

Two facts are already fixed. Every account is a data principal (ADR 0013): an
employee can be in a study and a wellness programme, "My consents" shows both,
and a rights request is about everything the fiduciary holds (ADR 0026,
s.11). And SRI-B is one data fiduciary, one legal entity, with one breach
register and one audit trail the Board can ask for. A database or a schema per
office would give the same person two accounts and two consent lists, split the
audit chain, and double the migration chain, the seed and the triggers, for an
isolation that is only needed between two internal functions. A second
deployment would do all of that twice over.

The question is therefore not *where* the two offices' rows live but *how hard
the wall between them is inside one database*. Scope lives in the query
(ADR 0004), and every officer query will carry the office predicate; a
predicate a future route forgets would leak one office's register to the other.
The platform's rule for evidence is that a guarantee that holds only through
Python is not a guarantee (ADR 0002). The DCT already uses PostgreSQL row-level
security for its tenants.

## Decision

- **One database, one schema, one migration chain.** No office has a schema,
  a database or a deployment of its own.
- **An office is data.** A table `office` (`office_code` `rnd` and `hr`, a
  name, its contact and its grievance route). A third office is a row and
  assigned accounts, not a migration or an enum value.
- **Every governance record names its office.** `office_id NOT NULL` on
  `project`, `purpose`, `notice_template` and its versions, `hr_category`,
  `notice`, `rights_request` and `breach`. `consent_link` and `export_log`
  carry it too, set when the link is minted or the export written, so the
  evidence that hangs off them is reachable only through a visible parent.
  Existing rows are backfilled as `rnd`.
- **Officers belong to an office.** `auth_user.office_id` for the officer
  roles (`dpo`, `legal`); the role names stay, the scope comes from the
  office. Collection and author roles (`rnd_user`, `dco`, `rco`, `dco_admin`)
  work in `rnd`; `hr_user` works in `hr`, narrowed further by its categories.
  The administrator, every data principal, an outside ticket holder, the
  worker, beat, the migrations, the seed and `reseal.py` run across all
  offices, bounded as they are today - by the account, the ticket, or the
  matrix.
- **The office is set once per unit of work.** The office travels in the
  request context; the database layer's `connection()` and `transaction()`
  run `SELECT set_config('app.office', '<office_code>' | 'all', false)` as
  the first statement on every connection they hand out, and
  `RESET app.office` before the connection goes back. Session-level, because `connection()` is
  autocommit and a transaction-local setting would end with the statement
  that set it; the reset on return is what keeps it from reaching the next
  request that draws the connection. The setting holds the office code
  (`rnd`, `hr`), not an integer id.
- **PostgreSQL enforces it.** Each office-bearing table gets
  `ENABLE` and `FORCE ROW LEVEL SECURITY` and one policy, for every command:

  ```sql
  USING (current_setting('app.office', true) = 'all'
         OR office_id = (SELECT office_id FROM office
                         WHERE office_code = current_setting('app.office', true)))
  WITH CHECK (the same)
  ```

  An unset setting answers no rows: deny by default. `FORCE` binds the table
  owner too - but no policy binds a superuser or a role with `BYPASSRLS`.
  Local development and the test suite connect as the database container's
  superuser, so there the wall is not enforced: the enforcement tests switch
  to a non-superuser role inside their rolled-back transaction to prove it,
  and outside `local` and `test` the API refuses to start when its database
  user is a superuser or has `BYPASSRLS`. Child tables without a column of their own
  (`consent_artefact`, `consent_purpose_grant`, `export_line`,
  `rights_request_holder`, the `breach_*` tables, the `notice_*` and
  `template_version_*` tables) get an `EXISTS` policy on their parent, which
  the parent's policy filters in turn.
- **The view keeps the wall.** `v_current_consent` is recreated
  `WITH (security_invoker = true)` (PostgreSQL 16), otherwise it runs with
  its owner's rights and reads through the policies.
- **Scope in the query stays the mechanism; the policies are the backstop.**
  Repositories keep compiling the caller's scope into the `WHERE` clause, so a
  row outside scope is still a 404 and the policies never become the reason a
  query is slow. Role scoping inside an office - an HR PoC's categories, a
  collection owner's sites - stays application scope alone.
- **One of everything that is evidence.** The audit hash chain stays single;
  `audit_log` is not policed (its rows are written by triggers as the owner),
  each row records the office of the record it is about, and the trail's
  read is filtered by office for an officer and not for the administrator.
  A row about no office-bearing record (history from before the offices,
  sign-ins, user administration) is read by both officers and the
  administrator: the Legal PoC holds the DPO's standing on its track.
  One breach register, one rights clock, one DKMS key, one participant
  account. A transfer between offices (AR-08) is an update of `office_id`
  with a reason, audited - possible only because the rows share a table.
- **Tests, the way this codebase likes them.** `tests/integration/enforcement/`
  gains raw-SQL cases: a connection set to `hr` reads zero `rnd` rows on every
  policed table and cannot insert one, and the reverse; an unset connection
  reads nothing; the view honours the setting. A parity test lists the
  policed tables against the office-bearing ones so a new table cannot
  arrive without a policy, as the enum parity test already does for Python
  and PostgreSQL.

## Consequences

- The person is one row and sees both tracks; the offices see only their own.
  "About everything" (ADR 0026) now means everything within one office's
  remit, with the routing and transfer rules of AR-08.
- A forgotten predicate in a future officer route returns nothing rather than
  the other office's rows. The failure is loud (an empty register) instead of
  silent.
- Every connection drawn from the pool pays one `set_config` and one `RESET`.
  Policies compare an indexed integer column against a one-row lookup of the
  setting; the planner evaluates it once per statement.
- Migrations that touch policed tables begin with `set_config('app.office',
  'all', false)`; the seed and `reseal.py` do the same. A migration that forgets
  fails on the first row rather than succeeding on the wrong rows - when it
  runs as a role the policies bind.
- The database role the API runs as in production must not be a superuser
  and must not hold `BYPASSRLS`; the startup check enforces it.
- The DCT and the CMP now isolate tenants the same way, so one explanation
  serves both and the SQL can be shared.
- Templates on the HR track are versioned, approved by Legal and scoped to a
  category (ADR 0028's "revisit when"); the copy is a composition rather than a
  verbatim copy, and nothing in the mechanism of "copied, never served" changes.

## Revisit when

A second legal entity joins the platform. Each fiduciary has its own breach
duties and its own DPO, so the tenant key would become the entity, with offices
inside it; `office` gains an `entity_id` and the policies compare on both. Or
an office needs its own encryption key for its registers, which would mean a
key per office in the DKMS and an office-aware `seal()`.
