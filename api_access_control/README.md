# Module and endpoint API access reference

Reviewed on **2026-09-17** against commit **`1757d5069ba723f260c88c45419c1286261a127f`**, branch **`refactor/frontend-architecture`**.

This folder answers: **which role can call each API, on which records, and under what additional conditions?** It expands the existing `api_docs` using the actual route guards, permission matrix, service checks and repository scopes.

- [Module overview](module_permissions.md): access counts for every role, grouped by module.
- [Endpoint permission matrix](endpoint_permissions.md): one row per method/path, with all seven roles and anonymous access.
- [Roles and scopes](roles_and_scopes.md): role meanings, static read/write grants, ownership rules and session behavior.
- [Implementation notes](implementation_notes.md): places where generic documentation and implemented controls differ.
- [Machine-readable endpoint inventory](endpoint_permissions.json): guards, roles, conditions and source references.

**Coverage: 17 modules, 241 documented operations over 211 OpenAPI paths, plus 3 registered system operations excluded from OpenAPI (244 total operations).** No framework-generated Swagger/ReDoc/OpenAPI routes or middleware-generated OPTIONS responses are counted.

## Module details

| Module | Operations | Detailed access rules |
| --- | --- | --- |
| Audit | 3 | [Open module](modules/audit.md) |
| Auth | 14 | [Open module](modules/auth.md) |
| Consent | 12 | [Open module](modules/consent.md) |
| Dashboard | 3 | [Open module](modules/dashboard.md) |
| Delegations | 5 | [Open module](modules/delegations.md) |
| Exchange | 19 | [Open module](modules/exchange.md) |
| Me | 26 | [Open module](modules/me.md) |
| Messages | 5 | [Open module](modules/messages.md) |
| Notices | 22 | [Open module](modules/notices.md) |
| Projects | 27 | [Open module](modules/projects.md) |
| Public Consent | 6 | [Open module](modules/public_consent.md) |
| Public Information | 10 | [Open module](modules/public_information.md) |
| Registry | 23 | [Open module](modules/registry.md) |
| Rights | 43 | [Open module](modules/rights.md) |
| System | 8 | [Open module](modules/system.md) |
| Tickets | 5 | [Open module](modules/tickets.md) |
| Users | 13 | [Open module](modules/users.md) |

## How to use this reference

1. Open the module, then locate the exact **HTTP method and path**. GET and POST at the same path can have different permissions.
2. Check the role row and read the conditions. A permitted role can still be refused for another owner’s record, expired capability, missing code or invalid lifecycle state.
3. Follow the source links for the code that enforces the rule. Links are pinned to the reviewed commit, so later branch changes do not silently change the evidence.

Staff roles are DPO, Admin, DCO, DCO Admin, RCO and R&D. `data_subject` means the data principal. A staff account using a portal OTP session acts as `data_subject`; the session role determines access.

Paths here are backend paths as declared, without an invented `/v1` prefix. A frontend proxy may expose them under `/api`. Public access means no application role is required; token/code and business checks are still listed. All examples and role decisions are documentation only.

## Validation and maintenance

The inventory was matched by method and path against every operation in `cmp_backend/openapi.json` and the registered router source. All 241 documented operations match exactly once; the three excluded system routes are separately identified. Role dependencies were resolved against `core/permissions.py`, explicit route-role denials were applied, and the service/repository exceptions in the notes were reviewed. This is static source validation, not execution against a live database or a complete security audit.

This is a snapshot, not a new authorization system or a change to the existing generated API docs. Recheck it whenever route signatures, the permission matrix, service checks, state machines or SQL scopes change. Access means role/assignment eligibility; this folder does not list real user names.
