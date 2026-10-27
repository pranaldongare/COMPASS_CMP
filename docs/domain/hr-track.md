# The HR track

How an HR activity that needs consent is set up, consented to, withdrawn
from, and answered for - governed by the Legal office rather than the DPO.
The decisions are [ADR 0032](../decisions/0032-offices-are-logical-tenants-in-one-database.md)
(offices as tenants), [ADR 0033](../decisions/0033-hr-consent-is-governed-by-an-approved-template-version.md)
(the template version) and
[ADR 0034](../decisions/0034-an-employee-link-signs-in-through-the-organisations-sso.md)
(SSO on employee links). The mechanism behind the office wall is
[offices-and-tenancy.md](../architecture/offices-and-tenancy.md); the schema
is [hr-track-migration-plan.md](../database/hr-track-migration-plan.md).
The diagrams this page refers to are under
[diagrams/hr-track/](../diagrams/hr-track/README.md).

## Two offices, one platform

| | R&D track · DPO office | HR track · Legal office |
|---|---|---|
| Governance unit | project: a study | activity: an instance of a category |
| Where legal sign-off sits | on each project | on the template version, once |
| Notice text | composed per project, or imported | locked sections + chosen purposes + the description |
| Purposes | attached per notice, activated by the DPO | chosen from the version's list; mandatory ones fixed |
| Approval path | `in_draft → pending_approval → approved` (DPO) | `in_draft → approved` by the HR PoC, guarded by the version |
| Consent link | per collection site, by its owner | one open link per activity |
| Participants | external principals, employees in some studies | employees, candidates, vendors, visitors |
| Where the data lives | collections and assets; exports | HRMS, the HR database, vendors; the consented list by export |
| Holders for a rights request | exports and assets | the category's processors, plus exports |
| Rights requests and breaches | the DPO's queue and register | Legal's queue and register |

Shared and unchanged: the consent evidence model, one participant account
for both tracks, the two portals, sealing, the audit chain, notifications,
administration, delegation, temporary logins, SMTP and SMS.

## The people

| Who | Role | What they do on the HR track |
|---|---|---|
| Legal PoC | `legal` (new) | Categories, HR purposes, templates and their versions, the category's processors and respondents; every HR register and the HR audit trail; HR rights requests, breaches and legal holds |
| HR PoC | `hr_user` (new) | Creates activities in the categories assigned to them, mints and shares the link, watches the activity's register by name, downloads records, exports the consented list; answers tickets addressed to them |
| Participant | `data_subject` | Employee (SSO), candidate, vendor or visitor (one-time code); consents, withdraws, raises requests |
| Administrator | `admin` | Provisions `legal` and `hr_user` accounts, assigns an HR PoC to categories, configures the identity provider, ends temporary access, names the reviewer for a grievance about the Legal office |
| DPO | `dpo` | Nothing on the HR track. Sees no HR row |

Role titles (`ROLE_TITLES`): `legal` → "Legal PoC", `hr_user` → "HR PoC".
Both are staff for `RequireStaff`; both need the emailed second factor
(`MFA_REQUIRED_ROLES` derives from the enum).

## 1. Legal sets up a category and a template (UC-01 A, UF-01)

1. **Category.** `POST /hr/categories` {code, name, description}. Codes
   are short and stable (`WELLNESS`, `CSR`, `BGV`, `COMMS`, `ENGAGEMENT`).
   Retired with `POST /hr/categories/{uuid}/status`, never deleted.
2. **Processors and respondents.** `PUT /hr/categories/{uuid}/processors`
   names, from the processor register, who will hold data collected under
   the category - the HRMS and the HR database as in-house processors, the
   vendors as third parties - each with a role (`hrms`, `database`,
   `vendor`) and a default respondent. The HR PoC is the default
   respondent unless another account is named.
3. **HR purposes.** `POST /purposes` as today, by `legal`; the purpose is
   created in the `hr` office with every field a purpose has (lawful basis,
   data categories, retention, erasure trigger, lapse behaviour).
4. **Template.** `POST /notice-templates` by `legal` creates it in the
   `hr` office under a category (`category_uuid` required on the HR track).
   The Rule 3 links and the office contact are Legal's.
5. **A version.** `POST /notice-templates/{uuid}/versions` opens
   version *n* as a draft: the locked text per language with the two
   placeholders `{{purposes}}` and `{{description}}` exactly once each;
   the purpose list with `is_mandatory` and order; the description slot's
   guidance and `max_length`; `reconsent_required`. A draft is edited in
   place.
6. **Approve.** `POST /notice-templates/{uuid}/versions/{n}/approve`:
   refused unless every purpose on the list is `active`, every language has
   text with both placeholders, and the template is active. On success the
   version is frozen (`cmp_template_version_freeze`), each language's
   `content_hash` is computed and stored, and `template_version.approved`
   is audited. A later change is version *n+1*.
7. **Retire.** A version is retired (`POST …/versions/{n}/status`); a
   retired version starts no new activity, and activities already on it
   continue.

Legal's dashboard opens on **Needs attention**: draft versions older than
seven days, HR rights requests due within seven days or overdue, HR breach
duties, tickets addressed to them.

## 2. The HR PoC creates an activity (UC-01 B, UF-02, AR-05)

`POST /hr/activities` with:

| Field | Rule |
|---|---|
| `category_uuid` | one the HR PoC is assigned to (`hr_poc_category`) |
| `template_version_uuid` | approved, not retired, of a template in that category |
| `purpose_uuids` | ⊆ the version's list and ⊇ its mandatory purposes; the console shows the mandatory ones pre-selected and locked |
| `name` | the activity's name, shown on the notice and in registers |
| `description` | the only free text: English, ≤ the slot's `max_length`, no `{{`, no URL; rendered in the `{{description}}` slot |
| `audience_mode` | `sso` (employees) or `otp` (everyone else) |
| `link_expires_at` | in the future |

In one transaction the service (`domain/hr/activities.py`):

1. re-verifies the version against its approval hash
   (`template_version_language.content_hash`), so a version edited by hand
   in the database cannot be used;
2. composes the notice text per language - locked text with the chosen
   purpose blocks and the description substituted - and creates `notice`
   (code of the project's own, `office_id = hr`, `template_version_id`),
   `notice_language` (approved, since the legal text is the version's) and
   `notice_purpose` (the chosen subset, `is_mandatory` copied);
3. creates the `project` (`office_id = hr`, `category_id`,
   `template_version_id`, `description`, `created_by` = the HR PoC);
4. registers one `project_site` under the in-house HR processor with the HR
   PoC as `dco_override_user_id`, so the existing site-owner rules hand the
   project to them;
5. publishes the notice (`notices.publish`, unchanged) and moves the
   project `in_draft → approved` through the state machine's new HR
   transition (`actors = {hr_user}`, requirements = the version checks);
6. mints the consent link with `audience_mode` (`consent.create_link`,
   unchanged but for the new column);
7. audits `activity.created`, `notice.published`, `project.transitioned`,
   `link.created`.

`cmp_link_coherent()` holds without change: the site belongs to an approved
project with a published notice. The response carries the link as a path;
the console shows it once with **Copy**, as for every link.

**Afterwards** the HR PoC may: close the activity (`/projects/{uuid}/close`,
which revokes the link); upgrade it to a newer approved version
(`POST /hr/activities/{uuid}/upgrade` → a new notice version composed as
above, links moved by publication, and if `reconsent_required` a re-consent
notice to every participant with a current artefact); re-mint or revoke the
link as today. The description cannot be edited in place: changing it is an
upgrade to the same version with a new description, which is a new notice
version.

## 3. The participant consents (UC-01 C, UF-03, UF-04, AR-06)

`GET /c/{token}` returns, in addition to today's fields, `audience_mode`.

**`otp` link** - exactly today's path: a contact, a code, sign-up if there is
no account (`/sign-up?next=/c/{token}`), the date of birth asked once, the
notice served, the decision captured. Self-registration gains the person
type from the link's category: `candidate` for a BGV category, `visitor`
for a visitor one, `vendor` or `external` otherwise - a hint written on the
account, never a permission.

**`sso` link** - the portal offers "Continue with your organisation account"
and nothing else:

1. `GET /c/{token}/sso/start` stores the state and redirects to the
   identity provider.
2. The provider signs the person in with corporate credentials.
3. `GET /auth/sso/callback?code=&state=` validates the ID token, matches
   the account on the employee ID hash or creates it as `employee`, mints a
   data-principal session (`open_principal_session`), and redirects to
   `/c/{token}`.
4. The mobile gate: an account with no confirmed mobile is asked for one
   and confirms it by code (`POST /me/contacts/code`,
   `POST /me/contact/verify`). The date-of-birth gate follows as today.
5. `GET /c/{token}/notice` serves and stamps; `POST /c/{token}/consent`
   captures. Nothing in capture changes.

A failed assertion (bad signature, nonce, audience, expired) answers the
same neutral page as an invalid link. A provider that does not answer is
reported as such with "Try again" (UX-3). The audit records
`auth.sso_signed_in`, `auth.sso_account_created` and
`auth.sso_identity_conflict`, never the claims.

## 4. Withdrawal reaches the HR holders (UC-02 E, UF-05, AR-07)

Withdrawal is unchanged in its evidence. New: when the artefact's notice is
on the `hr` office, `consent.withdraw` also looks up the activity's
respondents - the HR PoC (the site's owner) and the default respondent of
each `category_processor` - and queues one `hr_withdrawal_notice` per
respondent, after commit, through the outbox. The message names the
activity, the participant's employee ID or principal ID (never the name),
the purposes withdrawn, and the instruction to stop processing. It is
email only, copyable by the office, and carries no file. The participant's
own confirmation is unchanged.

Phase 2, out of this scope: an event to the HRMS over the SQS relay and a
consent-check API. Both need a machine credential, which the platform
deliberately has none of (ADR 0003); that is its own decision.

## 5. Rights requests and breaches by office (UC-02 F–G, UF-06, AR-08)

`rights_request.office_id` and `breach.office_id` place a record with one
office. On receipt the service decides the office from the person's
standing - the offices whose notices she holds a current artefact on:

| Standing | Office |
|---|---|
| HR only | `hr` (Legal) |
| R&D only | `rnd` (DPO) |
| both | the portal asks her which, or both: one request per office, each with its own reference and the same D0 |
| none known yet (public form before verification; a stranger) | **shared intake**: `office_id IS NULL`, visible to both offices' queues until one verifies and claims it (`POST /requests/{uuid}/claim`) |

An office may **transfer** a request it holds
(`POST /requests/{uuid}/transfer` {office, reason}): `office_id` changes,
`transferred_from` and the sealed reason are recorded, the move is audited
and the other office is emailed; D0, the checkpoints and the response period
do not move. Holders derived before the transfer stay; the receiving office
derives its own.

Holder derivation (`holdings.holders_of_person`) gains a third source for the
`hr` office: the `category_processor` rows of every activity the person has
a current artefact on, `derived_from = activity_processor`. Tickets, the
review step, outside-holder links and temporary logins are unchanged; the
HR PoC answers in the console as any respondent does.

Breaches: logged by whichever office noticed it, placed on an office at
logging; `legal` holds `breach` on the `hr` office with every power the DPO
has on `rnd`. A grievance about the Legal office escalates to the
administrator as a grievance about the DPO does.

## 6. What Legal and the HR PoC see

| Register | Legal PoC | HR PoC |
|---|---|---|
| Categories, templates, versions | all, write | read, their categories |
| Activities | all | theirs (their categories) |
| Consents | all HR consents, by name | the activity's, by name |
| Consent records (PDF, ZIP) | yes | yes, their activities |
| Exports | all HR exports; may export | their activities; may export |
| Rights requests, breaches, legal holds | all HR; write | tickets addressed to them |
| Audit trail | `hr` office rows | no |
| Users | read | no |

Navigation (`NAV_BY_ROLE`): `legal` - dashboard, requests, breaches,
tickets, hr-categories, notices (templates), purposes, hr-activities,
consents, exports, processors, audit, delegate, personal; `hr_user` -
dashboard, hr-activities, links, consents, exports, tickets, delegate,
personal. `DAILY_WORK` in the console's `nav.ts` gains both rows.

## Invariants, and where they live

| Invariant | Held by |
|---|---|
| An officer sees only its office's rows, whatever the query says | row-level security policies (ADR 0032), `tests/integration/enforcement/test_office_isolation.py` |
| An approved template version never changes | `cmp_template_version_freeze()` |
| An activity names an approved version of a template in its category | `cmp_activity_version_coherent()` (BEFORE INSERT/UPDATE on `project` where `office_id = hr`) |
| The chosen purposes are within the version's list and include its mandatory ones | the activity service, and `trg_hr_notice_purposes_in_version` on `notice_purpose` |
| The description is inside the slot and contains no placeholder | the composer (Pydantic + service); `CHECK project_description_length` |
| The served text is the version's locked text with the slots filled | the composer's hash recorded on `notice_language.content_hash`; the version's hash on `template_version_language.content_hash`; `consent_artefact.notice_content_hash` as today |
| A consent link on an `hr` project is minted for its one site | `cmp_link_coherent()` unchanged |
| An employee account carries a unique employee ID | `organization_id_hash` unique index (0028) |
| A request belongs to one office, or to the shared intake until claimed | `rights_request.office_id` nullable, `CHECK` that a claimed request names the claimer |
