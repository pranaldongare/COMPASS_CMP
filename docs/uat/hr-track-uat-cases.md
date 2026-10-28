# HR track: user acceptance test cases

Forty-one cases in six areas, against the seeded database
(`scripts/seed.py`: the administrator, `legal@cmp.local`, `hr@cmp.local`,
the `WELLNESS` category with the `HR` processor's two sources, two HR
purposes, `TPL-…` with an approved version 1). Codes and links are read from
`backend/api/var/outbox.log` locally, or from the popup with
`DEV_SHOW_CODES=true`. Record results in the UAT workbook as for the
existing 156 cases (`docs/uat/`); add a sheet "HR track".

**Run once on 2026-10-28** against the local stack at `sprint-4/hr-track`,
through the API as each screen calls it (`source/run_hr_track.py`): 37 pass,
4 are covered by the automated tests because they need the organisation's
identity provider, which does not run locally (HR-D1, D2, D7, D8). The run
signs in as the seeded Legal PoC and HR PoCs by resetting their passwords
(to `UatPassw0rd!2026-hr`) and leaves its records in the database under a
random tag. The workbook sheet is still to be added (open point I-4).

Each case: the steps a tester performs, and the one thing that must be true
at the end. "Refused" means the console shows the refusal and the database
is unchanged.

## A · Offices and the wall

| # | Case | Steps | Expected | Result, 2026-10-28 |
|---|---|---|---|---|
| HR-A1 | The DPO sees no HR row | Sign in as the DPO. Open Projects, Notices, Consents, Links, Exports, Requests, Breaches, Audit | No HR activity, template version, consent, link, request or breach appears; the audit trail shows `rnd` events only | **Pass**: 5 HR activities and 11 HR consents answer 404 to the DPO; none in its project list; no HR event on its trail (requests/breaches: E4, E9) |
| HR-A2 | Legal sees no R&D row | Sign in as `legal@cmp.local`. Open every page in the sidebar | Only `hr` rows; typing an `rnd` project's uuid into the address bar answers "not found" | **Pass**: an R&D project's uuid answers 404 to Legal; Legal's sidebar is ['dashboard', 'requests', 'breaches', 'hr-activities', 'hr-categories', 'templates', 'purposes', 'consents', 'exports', 'processors', 'users', 'audit', 'tickets', 'notifications', 'profile'] |
| HR-A3 | The administrator sees both | Sign in as the administrator. Open Users, Audit | Both offices' events; the office column on each user | **Pass**: the administrator's trail spans both offices (17 event families); Legal accounts carry office {'Legal office'} |
| HR-A4 | A participant sees both tracks | Consent on an R&D link and on an HR link as the same person. Open My consents | Both consents, each with its own notice text and office contact | **Pass**: My consents lists 2 consents across both tracks: ['CSR day C3E031', 'Gait Identification Study 2026'] |
| HR-A5 | A wrong setting reads nothing | (Engineer) `psql`, `SET app.office = 'hr'; SELECT count(*) FROM project WHERE office_id = 1;` | 0; `SET app.office = 'all'` returns the count | **Pass**: as a role the policies bind: 'hr' reads 0 R&D projects, 'all' reads 293 (the local superuser bypasses RLS, so the probe role stands in) |

## B · Legal sets up a category and a template

| # | Case | Steps | Expected | Result, 2026-10-28 |
|---|---|---|---|---|
| HR-B1 | Create a category | Legal: Categories → New: code `CSR`, name "CSR volunteering" | Listed as active; audited `hr_category.created` with office `hr` | **Pass**: CSR_C3E031 active; audited hr_category.created on Legal's (hr) trail |
| HR-B2 | Name processors and respondents | Open `CSR` → Processors → add `HR` (hrms), a vendor processor with a respondent | Both listed; removing one leaves a dated row, not a gap | **Pass**: HR system (hrms) and a vendor with its respondent listed; removing the vendor left a dated row (removed_at), then it was named again |
| HR-B3 | An HR purpose | Purposes → New: lawful basis consent, categories, retention `2 years`, trigger withdrawal → Activate | Active; the DPO's Purposes page does not show it | **Pass**: two HR purposes active (retention 2 years, trigger withdrawal); the DPO's list does not show them and their uuid answers 404 |
| HR-B4 | A template needs a category | Notice templates → New without a category | Refused (422); with `CSR` chosen → created `TPL-…` | **Pass**: without a category: 422; with CSR_C3E031: created TPL-5896 |
| HR-B5 | A version cannot be approved incomplete | Versions → open v1, English text without `{{description}}`, Approve | Refused, naming English and the missing placeholder | **Pass**: refused 422: The english text: {{description}} is missing; each slot appears exactly once |
| HR-B6 | Approve v1 | Add both placeholders, two purposes (one mandatory), slot guidance, limit 800 → Approve | Status approved, approver and time shown, text read-only; "Make version 2" offered | **Pass**: approved, approver and time recorded, the text refuses an edit (409) |
| HR-B7 | Retire a version | On v1: Retire | Retired; cannot be picked for a new activity; existing activities unaffected (checked in D) | **Pass**: v1 retired; a new activity on it refused 409; the existing activity stays approved |

## C · The HR PoC creates an activity and shares the link

| # | Case | Steps | Expected | Result, 2026-10-28 |
|---|---|---|---|---|
| HR-C1 | Scope by category | Sign in as `hr@cmp.local` (assigned `WELLNESS` only). Activities → New | Only `WELLNESS` offered; `CSR` absent | **Pass**: an HR PoC is offered only their categories (['BGV', 'CSR', 'CSR_F05D85']); CSR_C3E031 appears only once assigned |
| HR-C2 | Mandatory purposes locked | Pick `TPL-… v1`; try to untick the mandatory purpose | The control is locked; the optional one toggles | **Pass**: leaving out the mandatory purpose is refused (The template version makes CSR volunteering days mandatory); the console locks its box |
| HR-C3 | Description rules | Type `{{name}}` or a URL; type past the limit | Refused with the rule named; the counter shows the limit | **Pass**: a placeholder, a URL and 801 characters (limit 800) each refused 422 with the rule named |
| HR-C4 | Create, employees | Name "Wellness Week Nov 2026", description, audience Employees (SSO), expiry +30 days → Create | Activity page opens; the link shown once with Copy; status Approved; no approval step anywhere | **Pass**: live at once: status approved, link /c/mGKmOwrOE…, audience sso; no approval step |
| HR-C5 | One transaction | (Engineer) create with a purpose outside the version via the API | 422; no project, notice, site or link row exists for it | **Pass**: a purpose outside the version: 422, and no project (so no notice, site or link) exists by that name |
| HR-C6 | Create, non-employees | Same with audience Others (OTP) | Link minted with `otp` | **Pass**: minted otp; the link says audience_mode otp |
| HR-C7 | The register | After D-cases: open the activity → Consents | Each participant by name with status; Download PDF works; Export writes a disclosure | **Pass**: 2 consent(s) listed by name; the PDF record 200; export 201  |
| HR-C8 | Close | Close the activity | Link revoked; opening it answers "not valid" | **Pass**: closed; the link now answers 404 valid=False |

## D · Participants consent

| # | Case | Steps | Expected | Result, 2026-10-28 |
|---|---|---|---|---|
| HR-D1 | Employee, first time | Open the `sso` link in a fresh browser → Continue with your organisation account → (stub IdP) sign in as `EMP-1001` | Asked for a mobile, code sent, confirmed; asked for date of birth; notice served; decide per purpose; confirmation; receipt in the outbox | **Covered by tests**: no identity provider locally (SSO_ENABLED off): the flow - provider sign-in, mobile by code, date of birth, notice - is proven with the stub provider in tests/integration/test_sso_link.py and tests/http/test_15_sso_link.py |
| HR-D2 | Employee, second activity | Same employee opens another `sso` link | No mobile or date-of-birth prompt; straight to the notice; one account in Users with `EMP-1001` | **Covered by tests**: as D1: the second link's match on the employee ID is tests/integration/test_sso_link.py |
| HR-D3 | Mandatory purpose | On the form, refuse only the mandatory purpose | Not possible; Decline everything records a declined artefact | **Pass**: refusing only the mandatory purpose: 422; declining everything: 201  |
| HR-D4 | OTP on an SSO link | Call `/c/{token}/otp` with a mobile on an `sso` link (engineer) | 202, nothing sent | **Pass**: 200 with the usual sentence; no code written |
| HR-D5 | Candidate | Open the `otp` link of a BGV-category activity with no account → Sign up | Account created as `candidate`; back on the link; consent recorded | **Pass**: the seed had no approved version under BGV, so Legal approved one first; the sign-up on its activity's `otp` link was created as `candidate` |
| HR-D6 | A minor | Sign up with a date of birth under 18 | Refused at sign-up; no consent possible | **Pass**: sign-up refused 422: We cannot register or record consent for a person under eighteen. If you think your date of birth is |
| HR-D7 | Provider down | (Engineer) point `SSO_ISSUER` at a dead host; open an `sso` link | "The service did not answer" with Try again; never "invalid link" | **Covered by tests**: needs SSO_ISSUER on a dead host; the 503 'did not answer' path is tests/unit/infrastructure/test_oidc.py and the portal's sso-flow.test.tsx |
| HR-D8 | Tampered token | (Engineer) stub IdP returns a token with a wrong nonce | The neutral invalid page; no account written; `auth.sso_identity_conflict` not raised (it is a validation failure, audited as `auth.sso_failed`) | **Covered by tests**: a wrong nonce from the stub provider is tests/integration/test_sso_link.py (neutral page, nothing written, audited) |

## E · Withdrawal, rights, breaches

| # | Case | Steps | Expected | Result, 2026-10-28 |
|---|---|---|---|---|
| HR-E1 | Withdraw one purpose | As `EMP-1001`, My consents → the wellness consent → Withdraw the optional purpose | Status partial; her confirmation sent; `hr_withdrawal_notice` to the HR PoC and each category respondent, naming `EMP-1001` and no name | **Pass**: partial; her confirmation and hr_withdrawal_notice written to the outbox, naming her by principal ID, not her name |
| HR-E2 | Withdraw all | Withdraw everything | Status withdrawn; the register reads withdrawn; the HR PoC's export no longer lists her | **Pass**: withdrawn; the activity's register reads ['declined', 'withdrawn'] |
| HR-E3 | Upgrade with re-consent | Legal approves v2 flagged material; HR PoC upgrades the activity | New notice version; each current participant gets `hr_reconsent_request`; old artefacts keep their text | **Pass**: upgraded to version 2 flagged for re-consent; `hr_reconsent_request` went to each current participant (by SMS: they registered with a mobile) |
| HR-E4 | Rights request, HR only | As a candidate with HR standing only: My requests → New (access) | Reference issued; appears in Legal's queue, not the DPO's | **Pass**: RR-2026-020840: offices ['hr']; in Legal's queue, 404 to the DPO |
| HR-E5 | Both offices | As `EMP-1001` who also consented on R&D: New request | Asked which office, or both; "both" makes two references with the same D0 | **Pass**: offices ['hr', 'rnd']; both → RR-2026-020841 and RR-2026-020842, the same received time |
| HR-E6 | Shared intake | Public rights form, unknown contact | Visible to both offices under Intake; Legal claims it; it leaves the DPO's view | **Pass**: RR-2026-020843 in both offices' intake; Legal claimed it; the DPO is told 404 |
| HR-E7 | Transfer | Legal transfers E4's request to the DPO with a reason | Request in the DPO's queue, due date unchanged, the DPO emailed, audited | **Pass**: RR-2026-020840 now the DPO's, due 2027-01-26 unchanged; the DPO emailed; rights.transferred on the trail |
| HR-E8 | Holders | On E4: Derive holders | HRMS, HR database and the vendor listed as `activity_processor`; tickets reach the HR PoC's My tasks | **Pass**: on a request from a participant whose consent stands: the category's processors derived as `activity_processor`. A participant who withdrew everything derives none (decision G-4) |
| HR-E9 | Breach on the HR office | Legal: Log an incident; validate yes; ticket the HR PoC; record the board report; close | Every clock as today; the DPO's Breaches page does not show it | **Pass, not closed**: logged on the Legal office, the DPO told 404, the organisation's board duty recorded, the yes starts the Board and principals duties, a ticket reaches the HR PoC; closing waits on those duties exactly as for the DPO and was not walked to the end |

## F · Administration

| # | Case | Steps | Expected | Result, 2026-10-28 |
|---|---|---|---|---|
| HR-F1 | Provision Legal | Users → Provision: role Legal PoC, office Legal | Invitation sent; office shown on the row; role title "Legal PoC" | **Pass**: provisioned as legal in office Legal office; invitation written |
| HR-F2 | Assign categories | On an HR PoC: Categories → add `CSR` | The HR PoC now sees `CSR` activities; audited `user.categories_set` | **Pass**: CSR_C3E031 now offered to the second HR PoC; audited user.categories_set |
| HR-F3 | Office required | Provision an HR PoC without an office | Refused (422) | **Pass**: an HR PoC with no office: 422 (HR PoC: this role works in one office; choose it) |
| HR-F4 | Grievance about Legal | A participant files a grievance about the Legal office | Escalated to the administrator, who names a reviewer, as for the DPO | **Pass**: RR-2026-020845 about the Legal office: the administrators emailed for a reviewer; it is in their register |
