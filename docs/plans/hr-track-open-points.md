# HR track: open points

What the design leaves to be settled, with who settles it and what the
agent does meanwhile. The agent appends to this file whenever an increment
has to make a call the documents do not make; the product owner reads it
at each increment's review.

| # | Point | Owner | Until it is settled, the agent |
|---|---|---|---|
| OP-1 | The identity provider: protocol (OIDC assumed), discovery URL, the claim that carries the employee ID, whether candidates or vendors ever appear in the directory | IT / product owner | builds against the OIDC profile in ADR 0034 with the claim names as settings, and tests with the stub provider in `tests/support/oidc_stub.py` |
| OP-2 | Dependents under 18 in wellness activities | Legal | leaves the s.9 refusal as it is; a category that needs dependents waits for the guardian route |
| OP-3 | Whether a BGV notice states a consequence of refusal, and in what words | Legal | reserves nothing in the schema; the words, if wanted, are a locked section of the version |
| OP-4 | Re-consent mechanics: whether HR may process under the new terms before the participant re-consents | Legal | keeps the old artefact in force and the old terms with it; the re-consent request is a notification, not a change of standing |
| OP-5 | Public-form requests: shared intake versus a default office with transfer | Product owner | builds the shared intake (`office_id IS NULL`) as specified |
| OP-6 | Phase 2 integration: a machine credential for HRMS events and a consent-check API, over the SQS relay | Product owner, against ADR 0003 | builds nothing; the withdrawal notice by email is the phase 1 contract |
| OP-7 | `max_uses` on consent links is never consumed in the portal flow (observed 2026-10-26, pre-existing) | Product owner | leaves it; a one-line note in `06-known-gaps.md` |
| OP-8 | Self-registration always records `person_type = external` (pre-existing); increment 5 changes it only when the sign-up arrived from a link whose category sets a default | Product owner | as stated |
| OP-9 | Re-importing a Word notice can delete catalogue purposes referenced only by a template or a version (pre-existing; `importer._discard_orphans` checks `notice_purpose` only) | Engineer | extends the "still used" check to `notice_template_purpose` and `template_version_purpose` in increment 3, with a test |
| OP-10 | The `change_summary` Legal may want on a version for the re-consent message | Legal | adds the column in 0053 only if asked before increment 3 lands; otherwise the version's title is used |

## Appended by the agent

_(date · increment · the call made · why · what would change it)_

### Decided with the product owner before increment 1 (2026-10-27)

| # | Increment | The call | Why | What would change it |
|---|---|---|---|---|
| A-1 | 1 | The enforcement tests prove the wall under a non-superuser role (`CREATE ROLE` + `SET LOCAL ROLE` inside the rolled-back transaction); outside `local`/`test` the API refuses to start if its database user is a superuser or holds `BYPASSRLS`. ADR 0032 amended | Local development and the suite connect as the `postgres:16` image's superuser (`cmp`, `dev-services.yml`), which no policy binds even with `FORCE`; acceptance 3 and HR-A5 could not pass, and production's role is not yet split (`04-database.md`) | Running local development as a non-superuser, which makes the wall live locally too |
| A-2 | 1 | The mechanism is the architecture page's: `set_config('app.office', <office_code> \| 'all', false)` on checkout, `RESET app.office` on return, policies compare `office_id` with the `office_code` lookup. ADR 0032 amended to match | The ADR (transaction-local, `office_id::text`, reads in a read-only transaction) and the architecture page disagreed; `connection()` is autocommit, and HR-A5 sets a code | - |
| A-3 | 1 | An audit row records the office **of the record it is about**, not of the actor. An officer's trail shows its office's rows **and** rows with no office (pre-0051 history, sign-ins, user administration); the DPO, the Legal PoC and the administrator all read those. "For us Legal == DPO": the Legal PoC holds the DPO's standing on its track | From the context alone, consents captured on HR links (principal sessions) and worker or administrator actions would carry no office and be missing from Legal's trail, and a strict `= 'rnd'` filter would hide all history from the DPO | A rule that office-less rows belong to one office only |
| A-4 | 1 | `office_id` is written explicitly by the service for top-level records (`project`, `purpose`, `notice_template`, `breach`, `rights_request`); a trigger fills it on `notice`, `consent_link` and `export_log` from the parent and refuses a mismatch. No column default. Rights requests are written `rnd` until increment 7 routes them | A default of `rnd` would guess; the migration plan's rule is "a guard that refuses rather than a backfill that guesses" | - |
| A-5 | 1 | A Redis session minted before 0051 (no `office` field) is treated as expired; changing an account's office ends its sessions | Read as `None`, an old DPO session would run as `'all'` | - |
| A-6 | 1 | `legal` and `hr_user` are added to `MFA_REQUIRED_ROLES` in `.env.example`; every deployed environment must add them too | The env files list the roles explicitly, so the code default (every staff role) never applies; the new roles would sign in with a password alone | - |
| A-7 | 1 | Both new roles get the own-ticket grants (`ticket`, `breach_ticket`: OWN + write) every staff role holds | The navigation row `("dashboard", *PERSONAL)` puts Tickets in their menu; without the grant the matrix-integrity test fails and HR-E8/E9 cannot run | - |
| A-8 | 1 | The UAT cases live in `docs/uat/hr-track-uat-cases.md`, beside the existing UAT pack, not under `docs/operations/` | The repository keeps UAT in `docs/uat/` | - |

### Found in analysis, for later increments (owner to answer before that increment)

| # | Increment | Finding | Owner | Until settled, the agent |
|---|---|---|---|---|
| F-1 | 3/4 | `cmp_activity_version_coherent()` as written checks for an approved version on every `UPDATE` of `project`; retiring a version would block closing and every other update on the activities that use it (contradicts `hr-track.md` §1.7) | Engineer | checks on `INSERT` and when `template_version_id` changes only |
| F-2 | 4 | `consent_link.audience_mode` is needed by increment 4's `create_link` but arrives in 0054 (increment 5) | Engineer | adds the column in 0053; 0054 keeps the person types and the rest |
| F-3 | 3/4 | Notice fields the HR track does not specify: `applicable_to` (publication refuses it empty), the contact (the portal labels it "Data Protection Officer"), the Rule 3 links (on the editable template, outside the frozen version), the recipients list (today from sites only) | Legal | freezes them onto the version at approval; the contact is the HR office's |
| F-4 | 4 | HR PoC scope: by category for projects, but notices, links and consents are scoped by site owner (`site_scope_predicate` lists roles) | Engineer | scopes by category everywhere |
| F-5 | 4 | Re-consent after an upgrade: a version-2 consent today starts a second chain beside the version-1 one (supersession is per person and notice) | Legal | leaves both standing (OP-4) unless told to supersede |
| F-6 | 2/3 | `purpose_code` and `(notice_code, version)` are unique across both offices; under the wall a "code taken" check cannot see the other office's codes (a 23505 or a leak by error) | Engineer | prefixes generated HR codes by office |
| F-7 | 5 | `trg_subject_needs_mobile` refuses a `data_subject` without a mobile, so "create the employee, then ask for the mobile" fails on insert | Engineer | holds the validated assertion in Redis until the mobile is confirmed, then creates the account in one insert |
| F-8 | 5 | Account pre-hijack: the unauthenticated `POST /c/{token}/register` accepts `organization_id`, so anyone can pre-create an account with someone else's employee ID that their first SSO sign-in would then match | Engineer | closes the input before matching ships |
| F-9 | 5 | The callback must be `${PUBLIC_BASE_URL}/api/auth/sso/callback`: the portal forwards only `/api/*` to the API | IT | uses the `/api/` path in `SSO_REDIRECT_URL` and the configuration page |
| F-10 | 5 | The corporate email may already be on an account with no employee ID (including a staff account), and the mobile may be on another account (a 409 dead end today) | Product owner | refuses neutrally and leaves it to the administrator |
| F-11 | 5 | `auth_user.sso_subject` (0054) is in no ADR, domain or plan text | Engineer | drops it unless increment 5 finds a need |
| F-12 | 7 | Transfer: the policy refuses an `hr` session writing `office_id = rnd`, and the 0055 trigger's "with its four transfer columns" is vacuous after a first transfer | Engineer | runs the transfer statement as `'all'` inside the service, and checks the transfer columns changed |
| F-13 | 6/7 | A ticket addressed to an account of the other office (an `rnd` DCO on an HR breach, AR-08's lead office) is invisible under the policy | Engineer | runs the ticket holder's routes as `'all'`, bounded by the ticket's addressee |
| F-14 | 6 | The seed's one processor with two sources gives one holder, not "HRMS, HR database and vendor" (holders are per processor) | Engineer | seeds them as two processors |
| F-15 | 6 | Who answers a category-processor holder: the processor's registry respondent (today's rule) or the category's default respondent | Legal | the category's respondent, falling back to the HR PoC |
| F-16 | 6 | A vendor without an account cannot be a default respondent (`respondent_user_id` names an account) | Product owner | as stated |
| F-17 | 2/7 | Rights requests and breaches are DPO-only in code, not only in the matrix (`db/repositories/rights.py::scope_predicate`, `domain/rights/state_machine.py::actors_for`, 38 routes on `RequireDPO`/`RequireDPOorAdmin`, alerts and digests to every DPO); increments 2 and 7 are larger than the plan reads | - | widens each by office as the increment lands |
| F-18 | - | The branch `poc/option2-sqs-relay` carries its own ADR 0032 | Product owner | keeps 0032 for offices; the relay's record is renumbered when it lands |
