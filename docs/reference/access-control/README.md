# Module and endpoint API access reference

Reviewed on **2026-09-17** against commit **`1757d5069ba723f260c88c45419c1286261a127f`**, branch **`refactor/frontend-architecture`**; amended the same day at **`c7d3f6ba15a5cfdc6f9df6632c9c7e336c9936fa`** for the audit trail's four new endpoints (summary, vocabulary, lookup, export). **Re-reviewed on 2026-09-24 at `daca825864313166693c3f2973d50ec5c05d4170`:** no route, guard, matrix or scope change since `1757d50` apart from three that are now recorded: the staff notification feed is scoped by the project predicate (`79b7fac`), the audit lookup matches sealed people by keyed hash and name runs (`f5fffcc`), and `/ready` checks the key service (`ce9a984`). The OpenAPI path set is unchanged. Evidence links not touched by that review stay pinned to `1757d50` and their line numbers may have drifted.

**Re-reviewed on 2026-10-28 for the HR track (increments 1-8, ADR 0032-0034), on branch `sprint-4/hr-track`:** every table gains the Legal PoC and HR PoC columns from `endpoint_permissions.json`; the two HR modules have pages of their own; the inventory now lists every OpenAPI operation, including eleven it had missed (`GET /offices`, the consent-record PDFs, the registry's Excel import). An officer's `ALL` is its office's all ([roles and scopes](roles_and_scopes.md#what-scopes-mean-in-this-code)). Evidence links for these entries point at `HEAD`.

**Re-reviewed on 2026-11-06 for the breach workflow ([ADR 0037](../../decisions/0037-a-public-report-waits-apart-and-the-platform-mails-the-organisations-board.md)), on branch `integration/hr-track-sqs-relay`:** two modules are new, Breach settings and Incident reports; Breaches and Breach tickets gain the intake, the reports, the options for finding people and a ticket's date; `POST /breaches/{breach_uuid}/obligations/{duty}/complete` is gone. **Amended on 2026-11-07:** `POST /breaches/{breach_uuid}/cert-in/not-applicable` and `GET /breaches/intake/{report_uuid}` are new, `GET /breaches/intake` is a page, and `GET /notifications` shows the Legal PoC and the HR PoC as the conditional access `CurrentUser` always gave them. **Amended again on 2026-11-07, for the product owner's six answers** (ADR 0037 as amended, commits `8c770c1` to `bfbee4b`): three operations are new, `GET /breaches/{breach_uuid}/reports/recipients`, `PUT /breach-settings/board-recipients/{recipient_uuid}/mandatory` and `POST /requests/{request_uuid}/public-reports/erase`; the rules change on finalising and resending a report, the CERT-In set-aside and re-mark, a validation of *yes*, filing, the board's list, a request's detail and response, and the public form's code. **Amended on 2026-11-08, for the review of that build** (`285d077`): no operation added; the rules change on a request's detail (`code_channel`, an account's email only once proved, `complete_blocked_by` for the administrator), the erasure of a dismissed reporter's name (a hold on any account the contact is on), the response, the public form's verify (no 429 from the tries), Try again's re-read of the board's duty and the first *yes*'s held report to CERT-In. **Amended again on 2026-11-08, for the second review of that build** (`0923a5b`, `ef0f0cc`): no operation added; an account's email counts only once a code to it came back, and a request with no address to look by says so (erase 409 `no_proved_email`); Send a code and Confirm on a request with no account are the officers' (403 `officers_only`); a sign-in code is bound to its contact, and the reset, the second factor, a consent link's code and a nomination stamp what their code went to, while the public form's verify and Confirm stamp nothing; the public verify's malformed body is a 422; the request trail's code at submission and an SSO sign-in that stamps nothing are open. **Amended a third time on 2026-11-08, for the third review of that build** (`32d483a`): no operation added; a nomination stamps only a nominee account it makes and links one already there with no stamp, and its code lives under the contact it went to, one at a time; a sign-in by code, a consent link's code, a password reset, a nominee's request and finishing a sign-up answer a code of the wrong length and a spent budget as a wrong code, the limit per address staying the 429, and finishing a sign-up with nothing left to answer is refused; the reports overview serves why the first *yes* withheld a report to CERT-In; a *yes* passes over a board report still sending; a consent link's stamp on an unfinished sign-up and the verification method the administrator reads on a request are open. **Amended a fourth time on 2026-11-08, for the fourth review of that build** (`bd6cef1`): no operation added; finishing a sign-up answers every refusal as an unknown mobile, on `mobile_code`, a code left out included, and its failures count against the address, that limit its only 429; a nominee's request refuses a code that is not digits with the schema's 422. **Amended a fifth time on 2026-11-08, for the fifth review of that build** (`7bdb710`): no operation added; starting a sign-up refuses a child's date of birth before the contact is looked up, the same 422 whoever holds it, and resumes only a data principal's unfinished sign-up, a member of staff's or a breach holder's account still pending its first password answering 409 `contact_taken` with nothing sent; a nominee's request checks its code first and spends it only once the request is accepted, so a request refused for its kind, right or event leaves the code.

This tree is reviewed by hand, not generated. When a route's guard, scope or conditions change, update the module page, the two matrices and `endpoint_permissions.json` together; `api_docs/` (the request and response shapes) regenerates from `openapi.json` instead.

This folder answers: **which role can call each API, on which records, and under what additional conditions?** It expands the existing `api_docs` using the actual route guards, permission matrix, service checks and repository scopes.

- [Module overview](module_permissions.md): access counts for every role, grouped by module.
- [Endpoint permission matrix](endpoint_permissions.md): one row per method/path, with all eight roles and anonymous access.
- [Roles and scopes](roles_and_scopes.md): role meanings, static read/write grants, ownership rules and session behavior.
- [Implementation notes](implementation_notes.md): places where generic documentation and implemented controls differ.
- [Machine-readable endpoint inventory](endpoint_permissions.json): guards, roles, conditions and source references.

**Coverage: 25 modules, 394 documented operations over 345 OpenAPI paths, plus 3 registered system operations excluded from OpenAPI (397 total operations).** The breach module (S3-01 onward) is recorded in `endpoint_permissions.json`'s `amended` list; its evidence links point at `HEAD`. No framework-generated Swagger/ReDoc/OpenAPI routes or middleware-generated OPTIONS responses are counted.

## Module details

| Module | Operations | Detailed access rules |
| --- | --- | --- |
| Audit | 7 | [Open module](modules/audit.md) |
| Auth | 15 | [Open module](modules/auth.md) |
| Breach settings | 5 | [Open module](modules/breach_settings.md) |
| Breach tickets | 7 | [Open module](modules/breach_tickets.md) |
| Breaches | 53 | [Open module](modules/breaches.md) |
| Consent | 15 | [Open module](modules/consent.md) |
| Cross-border transfers | 3 | [Open module](modules/cross_border_transfers.md) |
| Dashboard | 3 | [Open module](modules/dashboard.md) |
| Delegations | 6 | [Open module](modules/delegations.md) |
| Exchange | 19 | [Open module](modules/exchange.md) |
| HR activities | 6 | [Open module](modules/hr_activities.md) |
| HR categories | 7 | [Open module](modules/hr_categories.md) |
| Incident reports | 2 | [Open module](modules/incident_reports.md) |
| Legal holds | 3 | [Open module](modules/legal_holds.md) |
| Me | 30 | [Open module](modules/me.md) |
| Messages | 6 | [Open module](modules/messages.md) |
| Notices | 44 | [Open module](modules/notices.md) |
| Projects | 27 | [Open module](modules/projects.md) |
| Public Consent | 9 | [Open module](modules/public_consent.md) |
| Public Information | 18 | [Open module](modules/public_information.md) |
| Registry | 29 | [Open module](modules/registry.md) |
| Rights | 53 | [Open module](modules/rights.md) |
| System | 8 | [Open module](modules/system.md) |
| Tickets | 5 | [Open module](modules/tickets.md) |
| Users | 17 | [Open module](modules/users.md) |

## How to use this reference

1. Open the module, then locate the exact **HTTP method and path**. GET and POST at the same path can have different permissions.
2. Check the role row and read the conditions. A permitted role can still be refused for another owner’s record, expired capability, missing code or invalid lifecycle state.
3. Follow the source links for the code that enforces the rule. Links are pinned to the commit each rule was reviewed at, so later branch changes do not silently change the evidence.

Staff roles are DPO, Admin, DCO, DCO Admin, RCO, R&D, Legal PoC and HR PoC. `data_subject` means the data principal. A staff account using a portal OTP session acts as `data_subject`; the session role determines access.

Paths here are backend paths as declared, without an invented `/v1` prefix. A frontend proxy may expose them under `/api`. Public access means no application role is required; token/code and business checks are still listed. All examples and role decisions are documentation only.

## Validation and maintenance

The inventory was matched by method and path against every operation in `backend/api/openapi.json` and the registered router source. All 394 documented operations match exactly once; the three excluded system routes are separately identified. Role dependencies were resolved against `core/permissions.py`, explicit route-role denials were applied, and the service/repository exceptions in the notes were reviewed. This is static source validation, not execution against a live database or a complete security audit.

The portals' own `POST /dkms/decrypt` is served by Next.js, not the API, and is outside this inventory; see [implementation notes](implementation_notes.md#the-portals-decrypt-route-is-not-an-api-operation).

This is a snapshot, not a new authorization system or a change to the existing generated API docs. Recheck it whenever route signatures, the permission matrix, service checks, state machines or SQL scopes change. Access means role/assignment eligibility; this folder does not list real user names.
