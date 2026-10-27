# HR track: user acceptance test cases

Thirty cases in six areas, against the seeded database
(`scripts/seed.py`: the administrator, `legal@cmp.local`, `hr@cmp.local`,
the `WELLNESS` category with the `HR` processor's two sources, two HR
purposes, `TPL-…` with an approved version 1). Codes and links are read from
`backend/api/var/outbox.log` locally, or from the popup with
`DEV_SHOW_CODES=true`. Record results in the UAT workbook as for the
existing 156 cases (`docs/uat/`); add a sheet "HR track".

Each case: the steps a tester performs, and the one thing that must be true
at the end. "Refused" means the console shows the refusal and the database
is unchanged.

## A · Offices and the wall

| # | Case | Steps | Expected |
|---|---|---|---|
| HR-A1 | The DPO sees no HR row | Sign in as the DPO. Open Projects, Notices, Consents, Links, Exports, Requests, Breaches, Audit | No HR activity, template version, consent, link, request or breach appears; the audit trail shows `rnd` events only |
| HR-A2 | Legal sees no R&D row | Sign in as `legal@cmp.local`. Open every page in the sidebar | Only `hr` rows; typing an `rnd` project's uuid into the address bar answers "not found" |
| HR-A3 | The administrator sees both | Sign in as the administrator. Open Users, Audit | Both offices' events; the office column on each user |
| HR-A4 | A participant sees both tracks | Consent on an R&D link and on an HR link as the same person. Open My consents | Both consents, each with its own notice text and office contact |
| HR-A5 | A wrong setting reads nothing | (Engineer) `psql`, `SET app.office = 'hr'; SELECT count(*) FROM project WHERE office_id = 1;` | 0; `SET app.office = 'all'` returns the count |

## B · Legal sets up a category and a template

| # | Case | Steps | Expected |
|---|---|---|---|
| HR-B1 | Create a category | Legal: Categories → New: code `CSR`, name "CSR volunteering" | Listed as active; audited `hr_category.created` with office `hr` |
| HR-B2 | Name processors and respondents | Open `CSR` → Processors → add `HR` (hrms), a vendor processor with a respondent | Both listed; removing one leaves a dated row, not a gap |
| HR-B3 | An HR purpose | Purposes → New: lawful basis consent, categories, retention `2 years`, trigger withdrawal → Activate | Active; the DPO's Purposes page does not show it |
| HR-B4 | A template needs a category | Notice templates → New without a category | Refused (422); with `CSR` chosen → created `TPL-…` |
| HR-B5 | A version cannot be approved incomplete | Versions → open v1, English text without `{{description}}`, Approve | Refused, naming English and the missing placeholder |
| HR-B6 | Approve v1 | Add both placeholders, two purposes (one mandatory), slot guidance, limit 800 → Approve | Status approved, approver and time shown, text read-only; "Make version 2" offered |
| HR-B7 | Retire a version | On v1: Retire | Retired; cannot be picked for a new activity; existing activities unaffected (checked in D) |

## C · The HR PoC creates an activity and shares the link

| # | Case | Steps | Expected |
|---|---|---|---|
| HR-C1 | Scope by category | Sign in as `hr@cmp.local` (assigned `WELLNESS` only). Activities → New | Only `WELLNESS` offered; `CSR` absent |
| HR-C2 | Mandatory purposes locked | Pick `TPL-… v1`; try to untick the mandatory purpose | The control is locked; the optional one toggles |
| HR-C3 | Description rules | Type `{{name}}` or a URL; type past the limit | Refused with the rule named; the counter shows the limit |
| HR-C4 | Create, employees | Name "Wellness Week Nov 2026", description, audience Employees (SSO), expiry +30 days → Create | Activity page opens; the link shown once with Copy; status Approved; no approval step anywhere |
| HR-C5 | One transaction | (Engineer) create with a purpose outside the version via the API | 422; no project, notice, site or link row exists for it |
| HR-C6 | Create, non-employees | Same with audience Others (OTP) | Link minted with `otp` |
| HR-C7 | The register | After D-cases: open the activity → Consents | Each participant by name with status; Download PDF works; Export writes a disclosure |
| HR-C8 | Close | Close the activity | Link revoked; opening it answers "not valid" |

## D · Participants consent

| # | Case | Steps | Expected |
|---|---|---|---|
| HR-D1 | Employee, first time | Open the `sso` link in a fresh browser → Continue with your organisation account → (stub IdP) sign in as `EMP-1001` | Asked for a mobile, code sent, confirmed; asked for date of birth; notice served; decide per purpose; confirmation; receipt in the outbox |
| HR-D2 | Employee, second activity | Same employee opens another `sso` link | No mobile or date-of-birth prompt; straight to the notice; one account in Users with `EMP-1001` |
| HR-D3 | Mandatory purpose | On the form, refuse only the mandatory purpose | Not possible; Decline everything records a declined artefact |
| HR-D4 | OTP on an SSO link | Call `/c/{token}/otp` with a mobile on an `sso` link (engineer) | 202, nothing sent |
| HR-D5 | Candidate | Open the `otp` link of a BGV-category activity with no account → Sign up | Account created as `candidate`; back on the link; consent recorded |
| HR-D6 | A minor | Sign up with a date of birth under 18 | Refused at sign-up; no consent possible |
| HR-D7 | Provider down | (Engineer) point `SSO_ISSUER` at a dead host; open an `sso` link | "The service did not answer" with Try again; never "invalid link" |
| HR-D8 | Tampered token | (Engineer) stub IdP returns a token with a wrong nonce | The neutral invalid page; no account written; `auth.sso_identity_conflict` not raised (it is a validation failure, audited as `auth.sso_failed`) |

## E · Withdrawal, rights, breaches

| # | Case | Steps | Expected |
|---|---|---|---|
| HR-E1 | Withdraw one purpose | As `EMP-1001`, My consents → the wellness consent → Withdraw the optional purpose | Status partial; her confirmation sent; `hr_withdrawal_notice` to the HR PoC and each category respondent, naming `EMP-1001` and no name |
| HR-E2 | Withdraw all | Withdraw everything | Status withdrawn; the register reads withdrawn; the HR PoC's export no longer lists her |
| HR-E3 | Upgrade with re-consent | Legal approves v2 flagged material; HR PoC upgrades the activity | New notice version; each current participant gets `hr_reconsent_request`; old artefacts keep their text |
| HR-E4 | Rights request, HR only | As a candidate with HR standing only: My requests → New (access) | Reference issued; appears in Legal's queue, not the DPO's |
| HR-E5 | Both offices | As `EMP-1001` who also consented on R&D: New request | Asked which office, or both; "both" makes two references with the same D0 |
| HR-E6 | Shared intake | Public rights form, unknown contact | Visible to both offices under Intake; Legal claims it; it leaves the DPO's view |
| HR-E7 | Transfer | Legal transfers E4's request to the DPO with a reason | Request in the DPO's queue, due date unchanged, the DPO emailed, audited |
| HR-E8 | Holders | On E4: Derive holders | HRMS, HR database and the vendor listed as `activity_processor`; tickets reach the HR PoC's My tasks |
| HR-E9 | Breach on the HR office | Legal: Log an incident; validate yes; ticket the HR PoC; record the board report; close | Every clock as today; the DPO's Breaches page does not show it |

## F · Administration

| # | Case | Steps | Expected |
|---|---|---|---|
| HR-F1 | Provision Legal | Users → Provision: role Legal PoC, office Legal | Invitation sent; office shown on the row; role title "Legal PoC" |
| HR-F2 | Assign categories | On an HR PoC: Categories → add `CSR` | The HR PoC now sees `CSR` activities; audited `user.categories_set` |
| HR-F3 | Office required | Provision an HR PoC without an office | Refused (422) |
| HR-F4 | Grievance about Legal | A participant files a grievance about the Legal office | Escalated to the administrator, who names a reviewer, as for the DPO |
