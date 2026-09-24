# Module and endpoint API access reference

Reviewed on **2026-09-17** against commit **`1757d5069ba723f260c88c45419c1286261a127f`**, branch **`refactor/frontend-architecture`**; amended the same day at **`c7d3f6ba15a5cfdc6f9df6632c9c7e336c9936fa`** for the audit trail's four new endpoints (summary, vocabulary, lookup, export). **Re-reviewed on 2026-09-24 at `daca825864313166693c3f2973d50ec5c05d4170`:** no route, guard, matrix or scope change since `1757d50` apart from three that are now recorded: the staff notification feed is scoped by the project predicate (`79b7fac`), the audit lookup matches sealed people by keyed hash and name runs (`f5fffcc`), and `/ready` checks the key service (`ce9a984`). The OpenAPI path set is unchanged. Evidence links not touched by that review stay pinned to `1757d50` and their line numbers may have drifted.

This tree is reviewed by hand, not generated. When a route's guard, scope or conditions change, update the module page, the two matrices and `endpoint_permissions.json` together; `api_docs/` (the request and response shapes) regenerates from `openapi.json` instead.

This folder answers: **which role can call each API, on which records, and under what additional conditions?** It expands the existing `api_docs` using the actual route guards, permission matrix, service checks and repository scopes.

- [Module overview](module_permissions.md): access counts for every role, grouped by module.
- [Endpoint permission matrix](endpoint_permissions.md): one row per method/path, with all seven roles and anonymous access.
- [Roles and scopes](roles_and_scopes.md): role meanings, static read/write grants, ownership rules and session behavior.
- [Implementation notes](implementation_notes.md): places where generic documentation and implemented controls differ.
- [Machine-readable endpoint inventory](endpoint_permissions.json): guards, roles, conditions and source references.

**Coverage: 19 modules, 253 documented operations over 221 OpenAPI paths, plus 3 registered system operations excluded from OpenAPI (256 total operations).** No framework-generated Swagger/ReDoc/OpenAPI routes or middleware-generated OPTIONS responses are counted.

## Module details

| Module | Operations | Detailed access rules |
| --- | --- | --- |
| Audit | 7 | [Open module](modules/audit.md) |
| Auth | 14 | [Open module](modules/auth.md) |
| Consent | 12 | [Open module](modules/consent.md) |
| Cross-border transfers | 3 | [Open module](modules/cross_border_transfers.md) |
| Dashboard | 3 | [Open module](modules/dashboard.md) |
| Delegations | 6 | [Open module](modules/delegations.md) |
| Exchange | 19 | [Open module](modules/exchange.md) |
| Legal holds | 3 | [Open module](modules/legal_holds.md) |
| Me | 26 | [Open module](modules/me.md) |
| Messages | 5 | [Open module](modules/messages.md) |
| Notices | 22 | [Open module](modules/notices.md) |
| Projects | 27 | [Open module](modules/projects.md) |
| Public Consent | 6 | [Open module](modules/public_consent.md) |
| Public Information | 10 | [Open module](modules/public_information.md) |
| Registry | 23 | [Open module](modules/registry.md) |
| Rights | 44 | [Open module](modules/rights.md) |
| System | 8 | [Open module](modules/system.md) |
| Tickets | 5 | [Open module](modules/tickets.md) |
| Users | 13 | [Open module](modules/users.md) |

## How to use this reference

1. Open the module, then locate the exact **HTTP method and path**. GET and POST at the same path can have different permissions.
2. Check the role row and read the conditions. A permitted role can still be refused for another owner’s record, expired capability, missing code or invalid lifecycle state.
3. Follow the source links for the code that enforces the rule. Links are pinned to the commit each rule was reviewed at, so later branch changes do not silently change the evidence.

Staff roles are DPO, Admin, DCO, DCO Admin, RCO and R&D. `data_subject` means the data principal. A staff account using a portal OTP session acts as `data_subject`; the session role determines access.

Paths here are backend paths as declared, without an invented `/v1` prefix. A frontend proxy may expose them under `/api`. Public access means no application role is required; token/code and business checks are still listed. All examples and role decisions are documentation only.

## Validation and maintenance

The inventory was matched by method and path against every operation in `backend/api/openapi.json` and the registered router source. All 253 documented operations match exactly once; the three excluded system routes are separately identified. Role dependencies were resolved against `core/permissions.py`, explicit route-role denials were applied, and the service/repository exceptions in the notes were reviewed. This is static source validation, not execution against a live database or a complete security audit.

The portals' own `POST /dkms/decrypt` is served by Next.js, not the API, and is outside this inventory; see [implementation notes](implementation_notes.md#the-portals-decrypt-route-is-not-an-api-operation).

This is a snapshot, not a new authorization system or a change to the existing generated API docs. Recheck it whenever route signatures, the permission matrix, service checks, state machines or SQL scopes change. Access means role/assignment eligibility; this folder does not list real user names.
