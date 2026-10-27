# HR track: the implementation plan

Eight increments, in order. Each names what it builds, the files it touches,
and the acceptance criteria that gate the next one. An increment is done
when its criteria pass, the repository's gate passes
(`CONTRIBUTING.md`), and the documents it changes are updated in the same
pull request. Branch: `sprint-4/hr-track` off `sprint-3/breach-and-correction`.

The behaviour is [hr-track.md](../domain/hr-track.md); the wall is
[offices-and-tenancy.md](../architecture/offices-and-tenancy.md); the schema
is [hr-track-migration-plan.md](../database/hr-track-migration-plan.md);
the decisions are ADRs
[0032](../decisions/0032-offices-are-logical-tenants-in-one-database.md),
[0033](../decisions/0033-hr-consent-is-governed-by-an-approved-template-version.md),
[0034](../decisions/0034-an-employee-link-signs-in-through-the-organisations-sso.md).

Do the increments in this order. 1 before anything else: every later table
arrives with its policy, and the tests that prove the wall exist before
there is anything HR-specific behind it.

---

## Increment 1 · Offices and the wall (ADR 0032)

**Builds.** Migration 0051; the two roles as enum values and `Role`
members; the office in the request context, the session and the pool;
policies; the view; the parity and enforcement tests. No HR feature yet.

**Touches.**

| Area | Files |
|---|---|
| Migration | `backend/api/migrations/versions/0051_offices_and_row_level_security.py` |
| Enums, roles | `src/cmp/core/enums.py` (nothing new: `user_role` is `Role`), `src/cmp/core/permissions.py` (`Role.LEGAL`, `Role.HR_USER`, `ROLE_TITLES`; give each new role a short `NAV_BY_ROLE` row now - `("dashboard", *PERSONAL)` - and no matrix grants yet; `auth/authorization/permissions.py::verify_resources` checks the roster against `MATRIX` at import and `tests/security/test_matrix_integrity.py` checks the roles, so run both before moving on) |
| Context | `src/cmp/core/context.py` (`RequestContext.office`, `bind_actor(..., office)`), `src/cmp/api/dependencies/authentication.py` (pass `session.office`) |
| Sessions | `src/cmp/auth/sessions/service.py` (`Session.office`; `create(..., office=)`), `src/cmp/auth/authentication/service.py` (staff sign-in reads `auth_user.office_id`; `open_principal_session` passes `None`) |
| Pool | `src/cmp/db/pool.py` (`_apply_office(conn)` at the top of `connection()` and `transaction()`; `_reset(conn)` → `RESET app.office`; `AsyncConnectionPool(..., reset=_reset)`) |
| Owners | `migrations/env.py`, `scripts/seed.py`, `scripts/reseal.py`, `docs/tools/generate-schema-docs.py` and any tool that connects: `SELECT set_config('app.office', 'all', false)` first |
| Users | `src/cmp/api/routers/v1/users.py`, `src/cmp/domain/users/service.py`, `src/cmp/db/repositories/users.py`: `office_uuid` on `POST /users` and in `UserOut`; required for the office roles, refused otherwise; `GET /offices` (any staff) for the picker |
| Audit | `src/cmp/domain/audit/service.py`: `record()` adds `office` to `detail_json` when the context has one; the trail's list for an officer filters on it (`db/repositories/audit.py`) |
| Tests | `tests/integration/enforcement/test_office_isolation.py`, `tests/integration/database/test_office_policy_parity.py`, `tests/security/test_office_scope.py` (minimal now: a `legal` session answers 404 on an `rnd` project), `tests/security/test_matrix_integrity.py` (two roles more: staff is everyone who is not a data principal still holds) |
| Docs | `docs/architecture/offices-and-tenancy.md` (in this pack), `migrations.md` line, `roles-and-access.md` (two rows, scope note), `glossary.md` (Office), ADR index, changelog |

**Acceptance.**

1. `alembic upgrade head`, `downgrade -1`, `upgrade head` clean on a
   scratch database; `upgrade head → downgrade base → upgrade head` clean.
2. Every existing test passes unchanged except where a fixture must now
   pass an office (document each such edit in the PR).
3. `test_office_isolation.py`: a raw connection set to `hr` reads 0 rows
   from each of `project`, `purpose`, `notice_template`, `notice`,
   `consent_link`, `consent_artefact`, `consent_purpose_grant`,
   `export_log`, `export_line`, `rights_request` (non-null office),
   `breach` on the seeded database, and an `INSERT` of an `rnd` row under
   `hr` fails with the policy violation; the reverse for `rnd`; unset and
   `''` read nothing; `all` reads everything; `v_current_consent` honours
   the setting.
4. `test_office_policy_parity.py`: `pg_policies` names exactly the tables
   the architecture page lists.
5. A request with no session (`GET /c/{token}`) still resolves a link; the
   worker's maintenance tasks still run (`tests/unit/tasks`).
6. `GET /auth/me` for a DPO carries `office: "rnd"`.

---

## Increment 2 · The Legal office's registry (ADR 0033, part 1)

**Builds.** Migration 0052; categories, category processors, HR PoC
assignments; the `legal` role's grants on them; the HR purpose path.

**Touches.**

| Area | Files |
|---|---|
| Migration | `0052_hr_categories.py` |
| Permissions | `core/permissions.py`: resources `hr_category` (`legal` ALL+w, `hr_user` SCOPED, `admin` ALL), `purpose` (`legal` ALL+w on `hr`-office rows - the office wall does the narrowing; the matrix row is ALL+w), `notice_template` (`legal` ALL+w), `user` (`legal` ALL read); `NAV_BY_ROLE[Role.LEGAL]` and `[Role.HR_USER]` |
| Domain | `src/cmp/domain/hr/__init__.py`, `domain/hr/categories.py` (create, update, status, set processors, assign PoC); audit events `hr_category.created/updated/retired/reactivated/processors_set`, `user.categories_set`; `ENTITY_TYPES` += `hr_category`, `category_processor`, `hr_poc_category` |
| Repositories | `db/repositories/hr_categories.py`; `repositories/entities.py` nouns |
| API | `api/routers/v1/hr_categories.py`: `GET/POST /hr/categories`, `GET/PUT /hr/categories/{uuid}`, `POST .../status`, `PUT .../processors`, `GET .../processors`; `PUT /users/{uuid}/categories` (admin), `GET /users/hr-pocs?category=` |
| Guards | `api/dependencies/common.py`: `RequireLegal`, `HrCategoryReader`, `HrCategoryWriter` |
| Purposes | `routers/v1/registry.py`: purpose routes accept `legal` (write) as they accept `dpo`; the office comes from the session; `activate`/`retire` by `legal` on `hr` purposes |
| Templates | `routers/v1/notice_templates.py`: writes by `RequireRole(Role.DPO, Role.LEGAL)`; `category_uuid` required when the caller's office is `hr` (`trg_hr_template_has_category` backs it) |
| Console | `features/hr-categories/` (list, detail with processors and PoCs), `features/users/` (office and category pickers), nav rows |
| Tests | `tests/integration/test_hr_categories.py`; `tests/security/test_hr_scope.py` (an HR PoC sees only assigned categories; a DPO answers 404 on `/hr/categories/{uuid}`; a `legal` session answers 404 on an `rnd` template) |

**Acceptance.**

1. A `legal` account can create a category, name two processors with
   respondents, and create an HR purpose and activate it; the DPO cannot
   see any of it (404), and the audit trail shows the office on each event.
2. An HR PoC assigned to `WELLNESS` lists that category and not `CSR`.
3. A template created by `legal` without a category is refused 422; by the
   DPO with a category is refused 422.
4. Matrix integrity and BOLA suites pass with the new resources.

---

## Increment 3 · Template versions (ADR 0033, part 2)

**Builds.** Migration 0053; the version lifecycle; approval that freezes
and hashes; the composer (used in increment 4, tested here).

**Touches.**

| Area | Files |
|---|---|
| Migration | `0053_template_versions.py` |
| Domain | `domain/notices/versions.py` (open, edit draft, set language, set purposes, approve, retire); `domain/notices/composer.py` (`compose(locked_text, purposes, description) -> str`, placeholder rules, length and link checks, `hash_text`) |
| Repositories | `db/repositories/template_versions.py` |
| API | `routers/v1/notice_templates.py`: `GET/POST /notice-templates/{uuid}/versions`, `GET /notice-templates/{uuid}/versions/{n}`, `PUT .../languages/{code}`, `PUT .../purposes`, `POST .../approve`, `POST .../status`, `GET .../preview?description=` (renders the composition with a sample description) |
| Audit | `template_version.opened/updated/approved/retired` |
| Console | `features/notice-templates/`: a Versions tab (list, draft editor with the locked text, the two placeholder chips, purposes with mandatory toggles, slot guidance and limit, the re-consent flag; Approve with a confirm; Preview) |
| Tests | `tests/unit/domain/test_composer.py` (placeholders exactly once, description limit, no links, hash stable); `tests/integration/test_template_versions.py`; `tests/integration/enforcement/test_template_version_freeze.py` (raw SQL `UPDATE` on an approved version's text fails) |

**Acceptance.**

1. Approving a draft with a purpose still `draft` → 409 naming it; with a
   language lacking a placeholder → 422 naming the language and the
   placeholder; otherwise the version is `approved`, `content_hash` is set
   per language, and a raw `UPDATE` of `locked_text` fails.
2. Opening version 2 copies version 1's content as a draft; version 1 is
   untouched.
3. `GET …/preview` returns the composed text and its hash; the same inputs
   give the same hash.

---

## Increment 4 · Activities (ADR 0033, part 3)

**Builds.** The activity: creation in one transaction, the HR transition in
the state machine, the implicit site, the published notice, the open link;
registers for the HR PoC and Legal; close, upgrade, re-consent.

**Touches.**

| Area | Files |
|---|---|
| State machine | `domain/projects/state_machine.py`: `ProjectFacts` gains `office`, `template_version_approved`, `template_version_hash_matches`, `purposes_within_version`, `mandatory_purposes_included`, `description_within_slot`; `_transitions()` for `IN_DRAFT` returns the HR transition (`to=APPROVED`, `actors={Role.HR_USER}`, `publishes_notice=True`) when `office == "hr"` and `_submit` when `rnd`. Keep the module pure |
| Domain | `domain/hr/activities.py` (`create`, `upgrade`, `close` delegating to `projects.service`), `domain/consent/service.create_link` (accepts `audience_mode`), `domain/notices/service.publish` unchanged |
| Repositories | `db/repositories/projects.py`: `scope_predicate` gains `Role.HR_USER` → `EXISTS (hr_poc_category …)` on `p.category_id`; `Role.LEGAL` → `TRUE` (the wall narrows it); facts query reads the new columns |
| API | `routers/v1/hr_activities.py`: `GET/POST /hr/activities`, `GET /hr/activities/{uuid}`, `POST .../upgrade`, `POST .../close`, `GET .../consents` (the activity's register by name), `GET .../link`; reuse `/consents`, `/consent-records`, `/exports` with the HR PoC's scope |
| Permissions | `project`, `notice`, `link`, `consent`, `export`, `site`: `hr_user` SCOPED (+w on project, link, export), `legal` ALL; `collection`, `import`, `asset`: none for either |
| Messages | `core/messages.py`: `hr_reconsent_request` (email + SMS: the activity, the link, why) |
| Console | `features/hr-activities/` (wizard: category → version → purposes with mandatory locked → description with counter and guidance → audience and expiry → create; detail page in the slide-A look: summary card, Consents, Link, Exports tabs; Upgrade; Close) |
| Dashboard | `db/repositories/dashboard.py`, `domain/dashboard`: Legal's and the HR PoC's **Needs attention** and figures |
| Tests | `tests/unit/domain/test_hr_transition.py` (every fact combination); `tests/integration/test_hr_activities.py` (one transaction: a failing purpose check leaves no project, notice, site or link); `tests/integration/enforcement/test_activity_version_coherent.py`; `tests/security/test_hr_scope.py` extended (HR PoC A answers 404 on HR PoC B's activity in another category; the DPO on any) |

**Acceptance.**

1. The seed's HR PoC creates an activity from `TPL-… v1` with the
   mandatory purpose plus one optional and a description: response 201
   with the link path; the database holds one `project` (`approved`), one
   `notice` (`published`, `template_version_id` set), one `project_site`
   owned by the HR PoC, one `consent_link` (`audience_mode` as sent); the
   audit shows four events in one transaction.
2. The same request with a purpose outside the version → 422, nothing
   written; with the mandatory purpose omitted → 422; with a description
   containing `{{` or a URL → 422; with a retired version → 409.
3. `GET /projects/{uuid}/transitions` for the HR PoC on an `hr` draft lists
   `approved` with the version requirements; for an R&D user on an `rnd`
   draft lists `pending_approval` as before (unit test covers both).
4. Upgrade to version 2 flagged `reconsent_required`: a new notice version
   is published, the link moves, each participant with a current artefact
   is queued `hr_reconsent_request` after commit; version 1 artefacts keep
   their hash.
5. Legal sees every HR activity and consent; the DPO sees none.

---

## Increment 5 · SSO on employee links (ADR 0034)

**Builds.** Migration 0054; the OIDC client; the start and callback routes;
matching and creation; the gates; the portal page; person types from the
category.

**Touches.**

| Area | Files |
|---|---|
| Migration | `0054_link_audience_and_person_types.py` |
| Settings | `core/config.py` (`sso_*`; production refusals), `.env.example`, `docs/operations/configuration.md` |
| Infrastructure | `infrastructure/identity/__init__.py`, `infrastructure/identity/oidc.py` (discovery cached, `authorize_url(state, nonce, verifier)`, `exchange(code, verifier)`, `validate_id_token(token, nonce)` using `PyJWT` + `cryptography` already present; JWKS cached with kid rotation), `infrastructure/identity/state.py` (Redis `sso:*`) |
| Auth | `auth/authentication/service.py`: `sso_sign_in(claims, link)` - match on `organization_id_hash`, conflict detection on email hash, create as `employee`, `open_principal_session`; audit `auth.sso_signed_in`, `auth.sso_account_created`, `auth.sso_identity_conflict` |
| API | `routers/public/consent.py`: `GET /c/{token}` returns `audience_mode`; `GET /c/{token}/sso/start`; `routers/v1/auth.py`: `GET /auth/sso/callback`; `/c/{token}/otp` on an `sso` link → the same neutral acknowledgement, no code sent |
| Links | `routers/v1/projects.py` `POST /sites/{uuid}/agent` and the HR activity creation accept `audience_mode` |
| Registration | `auth/authentication/service.register` reads the link's category `default_person_type` when `next` names a link; `PersonType` +2 |
| Readiness | `/ready` checks discovery when `SSO_ENABLED` |
| Portal | `features/public-consent/`: the `sso` branch of the identify step ("Continue with your organisation account"), the callback landing, the mobile gate reused from `account`, error page for a provider that did not answer (UX-3 wording) |
| Edge | `docs/deployment/portal-frontend-aws.md` §7.8: allow the callback path through WAF rules |
| Tests | `tests/unit/infrastructure/test_oidc.py` (token validation against a local JWKS: wrong issuer, audience, nonce, expired, bad signature all refused); `tests/integration/test_sso_link.py` with a stub provider (`tests/support/oidc_stub.py`): first sign-in creates an employee with the ID; second matches; conflict refused and audited; mobile gate enforced; the session is `data_subject` with `account_role` preserved; `tests/security/test_code_sign_in_is_a_principal.py` gains the SSO case; `tests/http` covers the new personal column |

**Acceptance.**

1. On an `sso` link, an employee with no account ends with an active
   `employee` account carrying her employee ID (hash matches), a
   `data_subject` session, and a consent artefact after the mobile and
   date-of-birth gates; the same employee on a second `sso` link is matched
   without a new row.
2. A tampered ID token (any of the five faults) answers the neutral invalid
   page and writes no account.
3. `GET /c/{token}/otp` on an `sso` link answers 202 and sends nothing.
4. A provider that times out answers "the service did not answer" with
   Try again, never "invalid link".
5. An `rnd` site's link can be minted `sso` and behaves identically.

---

## Increment 6 · Withdrawal reaches the HR holders, and holders from the category

**Builds.** The respondent lookup; the `hr_withdrawal_notice` junction; the
third holder source.

**Touches.**

| Area | Files |
|---|---|
| Domain | `domain/consent/service.withdraw`: after the artefact, `hr_respondents_of(activity)`; `dispatch_optional(send_hr_withdrawal_notice, …)` per respondent, inside the transaction, run after commit |
| Messages | `core/messages.py`: `Message.HR_WITHDRAWAL_NOTICE` (email only, copyable, no attachment; variables: activity, reference, principal id or employee id, purposes, instruction); `tasks/notifications/withdrawal.py`: `send_hr_withdrawal_notice` |
| Holders | `db/repositories/holdings.py`: `_HOLDINGS` gains the `activity_processor` branch (person → current artefact → link → site → project → category → `category_processor` live rows); `domain/rights/service.derive_holders` labels the source; `RightsHolderSource.ACTIVITY_PROCESSOR` |
| Docs | `docs/notifications/consent.md` regenerates (`generate-email-docs.py`); `docs/notifications/hr.md` (in this pack) |
| Tests | `tests/integration/test_hr_withdrawal_notice.py` (one email per respondent, none to the DPO, nothing on a rolled-back withdrawal, the participant's own confirmation unchanged); `tests/integration/test_rights_flows.py` gains a case: holders for an HR participant include the category's processors with `derived_from = activity_processor` |

**Acceptance.**

1. Withdrawing one purpose on an HR activity emails the HR PoC and each
   category processor's respondent once, names no participant name, and
   the outbox shows the rows only after commit.
2. `POST /requests/{uuid}/holders/derive` for an HR participant lists the
   HRMS, the HR database and the vendor, each `activity_processor`, beside
   any export-derived holder; confirming and ticketing them works
   unchanged.

---

## Increment 7 · Rights requests and breaches by office

**Builds.** Migration 0055; routing on receipt; the shared intake; claim
and transfer; `legal` on breaches; the grievance about the Legal office.

**Touches.**

| Area | Files |
|---|---|
| Migration | `0055_rights_and_breaches_by_office.py` |
| Rights | `domain/rights/service.create` (`office_for(subject)`; the portal passes `office` when both; `channel = public_form` → NULL), `claim`, `transfer`; `routers/v1/rights.py`: `POST /requests/{uuid}/claim`, `POST /requests/{uuid}/transfer`; `GET /requests` for an officer: its office's rows plus the shared intake; `db/repositories/rights.py` |
| Breaches | `routers/v1/breaches.py` and `domain/breach/*`: `legal` holds `breach` (hidden) and `legal_hold` as the DPO does; `log_incident` sets `office_id` from the session, or asks (`office_uuid`) when the administrator logs; `about_dpo` generalises to `about_office` (keep the column, document the meaning) |
| Permissions | `rights_request`, `legal_hold`, `breach`: `legal` ALL+w; `admin` SCOPED on grievances about either office |
| Messages | `rights_request_received` goes to the office's officers (`legal` for `hr`); `rights_transfer_received` (new, email, to the receiving office); `rights_due_digest` per office |
| Portal | `features/rights/`: when the person has standing in both offices, a "Which office?" step with "both" |
| Console | Legal's Rights and Breaches pages are the DPO's pages, scoped by the session; a **Claim** button on intake rows; **Transfer** in the request's actions with a reason |
| Tests | `tests/integration/test_rights_by_office.py` (routing table: HR only, R&D only, both → two requests same D0, unknown → intake visible to both; claim once; transfer keeps `due_at`, writes the four columns, audited, emails); `tests/integration/test_breach_by_office.py`; `tests/security/test_breach_is_hidden.py` gains `legal`; `tests/integration/enforcement/test_rights_office_moves.py` |

**Acceptance.**

1. The routing table in `hr-track.md` §5 holds for every row, by test.
2. A transfer changes `office_id`, records from/by/at/reason, leaves
   `received_at` and `due_at` untouched, and the receiving office is
   emailed; a second transfer back works; an `UPDATE` of `office_id`
   without the transfer columns fails at the trigger.
3. A `legal` session logs an incident, validates, tickets and closes a
   breach on the `hr` office; the DPO answers 404 on its uuid; the
   organisation's board duty and CERT-In clocks behave as today.

---

## Increment 8 · Finish: consoles, docs, UAT, references

**Builds.** What the earlier increments left for the end, and the regenerated
references.

| Item | Where |
|---|---|
| Legal's dashboard, the HR PoC's dashboard, both roles' `DAILY_WORK` | `frontend/console/src/components/layout/nav.ts`, `features/dashboard/` |
| Console help pages for the two roles | `features/help/` |
| Regenerate `backend/api/openapi.json`, both portals' `api-schema.d.ts` (`npm run api:check`), `docs/reference/api/`, `docs/reference/database/`, `docs/domain/pii-fields-and-endpoints.md`, `docs/domain/personal-data.md` endpoint tables, `docs/notifications/*.md`, `docs/email/messages.md` | the commands in `docs/README.md` → Tools |
| Access-control reference | `docs/reference/access-control/`: the two new module pages (`hr_categories.md`, `hr_activities.md`), the matrices, `endpoint_permissions.json`, a re-review line in its README |
| UAT | [`docs/uat/hr-track-uat-cases.md`](../uat/hr-track-uat-cases.md) executed once against the seed; defects filed as issues |
| Changelog, docs map, glossary, roles-and-access, migrations.md, ADR index | the lines in `hr-track-doc-deltas.md` |
| Memory for the next sprint | `docs/plans/hr-track-open-points.md`: whatever was deferred, with the increment it belongs to |

**Acceptance.** `docs/tools/check-links.py` clean; `generate-email-docs.py
--check` and `personal-data-scan.py --check` clean; every UAT case has a
result; the proposed CI workflow's steps pass locally.

---

## Out of scope, deliberately

Machine credentials, the consent-check API and HRMS events over the SQS
relay (phase 2; needs its own ADR against ADR 0003); legacy HR consent
import; languages other than English on the HR track; the guardian route
for minors (dependents in wellness activities wait for it); SSO for the
staff console; the DCT.
